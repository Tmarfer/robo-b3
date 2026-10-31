"""Três experimentos independentes descritos em testes-codex/fichas-v1.md."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from robob3.backtest.manifesto import gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5

ESTRATEGIAS = ("medias-5-20", "macd-12-26-9", "estocastico-14-3-3")


def reamostrar_completas(df, minutos, base):
    if minutos == base:
        return df.copy()
    colunas = {"open": "first", "high": "max", "low": "min", "close": "last"}
    dados = df.resample(f"{minutos}min", origin="start_day").agg(colunas)
    contagem = df["close"].resample(f"{minutos}min", origin="start_day").count()
    return dados.loc[contagem == minutos // base].dropna()


def sinais(df, estrategia, rolagens):
    # Agrupa por contrato para que indicadores não atravessem saltos de rolagem.
    mudancas = pd.to_datetime(sorted(str(d) for d in rolagens))
    grupos = pd.Series(mudancas.searchsorted(df.index, side="right"), index=df.index)
    resultado = pd.Series(0, index=df.index, dtype="int8")
    for _, bloco in df.groupby(grupos):
        c = bloco.close
        if estrategia == "medias-5-20":
            a, b = c.rolling(5, min_periods=5).mean(), c.rolling(20, min_periods=20).mean()
            compra = (a > b) & (a.shift() <= b.shift())
            venda = (a < b) & (a.shift() >= b.shift())
        elif estrategia == "macd-12-26-9":
            a = (
                c.ewm(span=12, adjust=False, min_periods=12).mean()
                - c.ewm(span=26, adjust=False, min_periods=26).mean()
            )
            b = a.ewm(span=9, adjust=False, min_periods=9).mean()
            compra = (a > b) & (a.shift() <= b.shift())
            venda = (a < b) & (a.shift() >= b.shift())
        elif estrategia == "estocastico-14-3-3":
            minima, maxima = bloco.low.rolling(14).min(), bloco.high.rolling(14).max()
            bruto = 100 * (c - minima) / (maxima - minima).replace(0, np.nan)
            a = bruto.rolling(3).mean()
            b = a.rolling(3).mean()
            compra = (a > b) & (a.shift() <= b.shift()) & (a < 20) & (b < 20)
            venda = (a < b) & (a.shift() >= b.shift()) & (a > 80) & (b > 80)
        else:
            raise ValueError("Estratégia desconhecida")
        resultado.loc[bloco.index] = np.select([compra, venda], [1, -1], default=0).astype("int8")
    return resultado


def simular(df, estrategia, minutos, rolagens, inicio, fim):
    sinais_calc = sinais(df, estrategia, rolagens)
    trecho = df.loc[inicio:fim].copy()
    trecho["sinal"] = sinais_calc.loc[trecho.index]
    operacoes = []
    for dia, grupo in trecho.groupby(trecho.index.date):
        regs = list(grupo.itertuples())
        pos = None
        for i, b in enumerate(regs):
            ultimo = i == len(regs) - 1
            anterior = regs[i - 1] if i else None
            consecutivas = (
                anterior is not None and (b.Index - anterior.Index).total_seconds() == minutos * 60
            )
            sinal = int(anterior.sinal) if consecutivas else 0
            if pos is not None and sinal == -pos["lado"]:
                saida = b.open - pos["lado"] * 5
                fechar(pos, b, saida, "sinal", operacoes)
                pos = None
            if pos is None and sinal and not ultimo:
                entrada = b.open + sinal * 5
                pos = {
                    "data": str(dia),
                    "lado": sinal,
                    "entrada_em": str(b.Index),
                    "entrada": entrada,
                    "stop": entrada - sinal * 300,
                    "alvo": entrada + sinal * 600,
                }
            if pos is None:
                continue
            lado, stop, alvo = pos["lado"], pos["stop"], pos["alvo"]
            bate_stop = b.low <= stop if lado == 1 else b.high >= stop
            bate_alvo = b.high >= alvo if lado == 1 else b.low <= alvo
            abriu_stop = b.open <= stop if lado == 1 else b.open >= stop
            abriu_alvo = b.open >= alvo if lado == 1 else b.open <= alvo
            if abriu_stop:
                fechar(pos, b, b.open - lado * 5, "stop", operacoes, bate_alvo)
                pos = None
            elif abriu_alvo:
                fechar(pos, b, b.open, "alvo", operacoes)
                pos = None
            elif bate_stop:
                fechar(pos, b, stop - lado * 5, "stop", operacoes, bate_alvo)
                pos = None
            elif bate_alvo:
                fechar(pos, b, alvo, "alvo", operacoes)
                pos = None
            elif ultimo:
                fechar(pos, b, b.close - lado * 5, "fim do pregão", operacoes)
                pos = None
    return operacoes


def fechar(pos, barra, saida, motivo, ops, ambigua=False):
    pos.update(
        {
            "saida_em": str(barra.Index),
            "saida": saida,
            "motivo": motivo,
            "resultado_brl": round((saida - pos["entrada"]) * pos["lado"] * 0.2 - 0.5, 2),
            "ambigua": bool(ambigua),
        }
    )
    ops.append(pos)


def resumir(ops, tf):
    acumulado = pico = dd = 0.0
    anos = {}
    for op in ops:
        acumulado += op["resultado_brl"]
        pico = max(pico, acumulado)
        dd = min(dd, acumulado - pico)
        ano = op["data"][:4]
        anos[ano] = round(anos.get(ano, 0) + op["resultado_brl"], 2)
    ganho = sum(o["resultado_brl"] for o in ops if o["resultado_brl"] > 0)
    perda = -sum(o["resultado_brl"] for o in ops if o["resultado_brl"] < 0)
    return {
        "timeframe": f"M{tf}",
        "operacoes": len(ops),
        "resultado_brl": round(acumulado, 2),
        "por_ano": anos,
        "acerto_pct": round(sum(o["resultado_brl"] > 0 for o in ops) / len(ops) * 100, 2)
        if ops
        else None,
        "fator_lucro": round(ganho / perda, 3) if perda else None,
        "drawdown_max": round(dd, 2),
        "ambiguas": sum(o["ambigua"] for o in ops),
        "por_motivo": {
            m: sum(o["motivo"] == m for o in ops)
            for m in ("alvo", "stop", "sinal", "fim do pregão")
        },
    }


def executar():
    from robob3.backtest.manifesto import commit_atual

    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    caminhos = {
        "M1": Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv"),
        "M5": Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv"),
    }
    dados = {}
    for nome, caminho in caminhos.items():
        df = ler_barras_mt5(caminho)
        if df.index.has_duplicates or not df.index.is_monotonic_increasing:
            raise ValueError(f"{nome}: dados duplicados ou fora de ordem")
        # 10/02 é um dia parcial no M1; outubro de 2026 não integra qualquer etapa.
        dados[nome] = df.loc[:"2026-09-30"]
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    janelas = [
        ("desenvolvimento", "2023-03-31", "2025-12-30", "M5", [5, 15]),
        ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30", "M5", [5, 15]),
        ("2026-fev-set-comparavel", "2026-02-11", "2026-09-30", "M1", [1, 5, 15]),
    ]
    pacotes = {}
    for nome, _inicio, _fim, origem, tempos in janelas:
        pacotes[nome] = {
            tf: reamostrar_completas(dados[origem], tf, int(origem[1:])) for tf in tempos
        }
    saida = []
    for estrategia in ESTRATEGIAS:
        for nome, inicio, fim, origem, tempos in janelas:
            linhas = []
            operacoes = {}
            for tf in tempos:
                ops = simular(pacotes[nome][tf], estrategia, tf, rolagens, inicio, fim)
                linhas.append(resumir(ops, tf))
                operacoes[f"M{tf}"] = ops
            caminho = caminhos[origem]
            manifesto = montar_manifesto(
                estrategia=f"codex-{estrategia}",
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
                    "stop_pts": 300,
                    "alvo_pts": 600,
                },
                ambiguidade="conservadora",
                linhas=linhas,
                comando=["robob3", "backtest-codex-fichas"],
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
    Path("testes-codex/resultado-fichas.json").write_text(
        json.dumps(saida, ensure_ascii=False), encoding="utf-8"
    )
