"""Variantes de fichas com trailing e hipótese adversa sobre barras ambíguas."""

import hashlib
import json
from pathlib import Path

import yaml

from robob3.backtest.codex_fichas import ESTRATEGIAS, fechar, reamostrar_completas, resumir, sinais
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def mover_stop(pos, preco, timestamp):
    lado = pos["lado"]
    if (preco - pos["entrada"]) * lado < 300:
        return False
    novo = preco - lado * 150
    if (novo - pos["stop_atual"]) * lado <= 0:
        return False
    pos["stop_atual"] = novo
    pos["trailing_ativado"] = True
    evento = {"t": str(timestamp), "preco": novo}
    if pos["movimentos_stop"] and pos["movimentos_stop"][-1]["t"] == evento["t"]:
        pos["movimentos_stop"][-1] = evento
    else:
        pos["movimentos_stop"].append(evento)
    return True


def simular(df, estrategia, minutos, rolagens, inicio, fim):
    valores = sinais(df, estrategia, rolagens)
    trecho = df.loc[inicio:fim].copy()
    trecho["sinal"] = valores.loc[trecho.index]
    ops = []
    for dia, grupo in trecho.groupby(trecho.index.date):
        regs = list(grupo.itertuples())
        pos = None
        for i, b in enumerate(regs):
            ultimo = i == len(regs) - 1
            anterior = regs[i - 1] if i else None
            consecutiva = (
                anterior is not None and (b.Index - anterior.Index).total_seconds() == minutos * 60
            )
            sinal = int(anterior.sinal) if consecutiva else 0
            if pos is not None and sinal == -pos["lado"]:
                pos["tipo_stop"] = None
                fechar(pos, b, b.open - pos["lado"] * 5, "sinal", ops)
                pos = None
            if pos is None and sinal and not ultimo:
                entrada = b.open + sinal * 5
                stop = entrada - sinal * 300
                pos = {
                    "data": str(dia),
                    "lado": sinal,
                    "entrada_em": str(b.Index),
                    "entrada": entrada,
                    "stop": stop,
                    "stop_atual": stop,
                    "alvo": None,
                    "trailing_ativado": False,
                    "movimentos_stop": [{"t": str(b.Index), "preco": stop}],
                }
            if pos is None:
                continue
            lado = pos["lado"]
            aberto = int(b.open)
            favoravel = int(b.high if lado == 1 else b.low)
            adverso = int(b.low if lado == 1 else b.high)
            if (aberto - pos["stop_atual"]) * lado <= 0:
                pos["tipo_stop"] = "móvel" if pos["trailing_ativado"] else "inicial"
                fechar(pos, b, aberto - lado * 5, "stop", ops)
                pos = None
                continue
            # Na abertura já sabemos esse preço; o trailing pode ter avançado em salto.
            mover_stop(pos, aberto, b.Index)
            stop = pos["stop_atual"]
            candidato = favoravel - lado * 150
            melhora = (favoravel - pos["entrada"]) * lado >= 300 and (candidato - stop) * lado > 0
            if (adverso - stop) * lado <= 0:
                pos["tipo_stop"] = "móvel" if pos["trailing_ativado"] else "inicial"
                fechar(pos, b, stop - lado * 5, "stop", ops, ambigua=bool(melhora))
                pos = None
                continue
            if melhora:
                if (adverso - candidato) * lado <= 0:
                    protegida = pos["entrada"] + lado * 150
                    pior = (
                        max(stop, protegida, adverso)
                        if lado == 1
                        else min(stop, protegida, adverso)
                    )
                    pos["stop_atual"] = pior
                    pos["trailing_ativado"] = True
                    pos["tipo_stop"] = "móvel"
                    pos["movimentos_stop"].append({"t": str(b.Index), "preco": pior})
                    fechar(pos, b, pior - lado * 5, "stop", ops, ambigua=True)
                    pos = None
                    continue
                mover_stop(pos, favoravel, b.Index)
            if ultimo:
                pos["tipo_stop"] = None
                fechar(pos, b, b.close - lado * 5, "fim do pregão", ops)
                pos = None
    return ops


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    arquivos = {
        "M1": Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv"),
        "M5": Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv"),
    }
    dados = {}
    for nome, caminho in arquivos.items():
        df = ler_barras_mt5(caminho)
        if df.index.has_duplicates or not df.index.is_monotonic_increasing:
            raise ValueError(f"{nome}: dados duplicados ou fora de ordem")
        dados[nome] = df.loc[:"2026-09-30"]
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    janelas = [
        ("desenvolvimento", "2023-03-31", "2025-12-30", "M5", [5, 15]),
        ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30", "M5", [5, 15]),
        ("2026-fev-set-comparavel", "2026-02-11", "2026-09-30", "M1", [1, 5, 15]),
    ]
    pacotes = {
        nome: {tf: reamostrar_completas(dados[origem], tf, int(origem[1:])) for tf in tempos}
        for nome, _, _, origem, tempos in janelas
    }
    saida = []
    for estrategia in ESTRATEGIAS:
        for nome, inicio, fim, origem, tempos in janelas:
            linhas = []
            operacoes = {}
            for tf in tempos:
                ops = simular(pacotes[nome][tf], estrategia, tf, rolagens, inicio, fim)
                resumo = resumir(ops, tf)
                resumo["stops_moveis"] = sum(o.get("tipo_stop") == "móvel" for o in ops)
                resumo["stops_iniciais"] = sum(o.get("tipo_stop") == "inicial" for o in ops)
                linhas.append(resumo)
                operacoes[f"M{tf}"] = ops
            caminho = arquivos[origem]
            manifesto = montar_manifesto(
                estrategia=f"codex-{estrategia}-trailing-v2",
                ativo="WIN$N",
                timeframe="grade M1/M5/M15",
                trecho=nome,
                periodo=(inicio, fim),
                dados={
                    "arquivo": caminho.name,
                    "sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
                },
                custos={
                    "custo_lado_brl": 0.25,
                    "derrapagem_pts": 5,
                    "valor_ponto_brl": 0.2,
                    "stop_inicial_pts": 300,
                    "ativacao_pts": 300,
                    "distancia_trailing_pts": 150,
                },
                ambiguidade="hipotese-adversa",
                linhas=linhas,
                comando=["robob3", "backtest-codex-fichas-trailing", "--confirmo-fora-da-amostra"],
            )
            destino = gravar_manifesto(manifesto, "data/backtests")
            saida.append(
                {
                    "estrategia": estrategia,
                    "periodo": nome,
                    "inicio": inicio,
                    "fim": fim,
                    "manifesto": str(destino),
                    "linhas": linhas,
                    "operacoes": operacoes,
                }
            )
            print(
                json.dumps(
                    {"estrategia": estrategia, "periodo": nome, "linhas": linhas},
                    ensure_ascii=False,
                ),
                flush=True,
            )
    Path("testes-codex/resultado-fichas-trailing.json").write_text(
        json.dumps(saida, ensure_ascii=False), encoding="utf-8"
    )
