"""Rompimento falso com trailing; sequências de preço hipotéticas, não ticks."""

import hashlib
import json
from pathlib import Path

from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5

TICK = 5
INICIO, FIM = "2026-02-11", "2026-09-30"
ARQUIVO = Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv")


def passos(inicio, fim):
    if inicio % TICK or fim % TICK:
        raise ValueError("Preço fora do tick de 5 pontos")
    passo = TICK if fim > inicio else -TICK
    return range(inicio + passo, fim + passo, passo) if inicio != fim else ()


def encerrar(pos, barra, preco, motivo, operacoes):
    saida = preco - pos["lado"] * TICK
    pos.update(
        {
            "saida_em": str(barra.Index),
            "saida": saida,
            "motivo": motivo,
            "resultado_brl": round((saida - pos["entrada"]) * pos["lado"] * 0.2 - 0.5, 2),
        }
    )
    operacoes.append(pos)


def atualizar(pos, preco, timestamp):
    lado = pos["lado"]
    if (preco - pos["entrada"]) * lado < 4 * TICK:
        return
    novo = preco - lado * 2 * TICK
    if (novo - pos["stop_atual"]) * lado > 0:
        pos["stop_atual"] = novo
        pos["trailing_ativado"] = True
        evento = {"t": str(timestamp), "preco": novo}
        if pos["movimentos_stop"] and pos["movimentos_stop"][-1]["t"] == evento["t"]:
            pos["movimentos_stop"][-1] = evento
        else:
            pos["movimentos_stop"].append(evento)


def simular(df, stop_ticks, caminho):
    if stop_ticks not in (3, 5) or caminho not in ("maxima-primeiro", "minima-primeiro"):
        raise ValueError("Cenário inválido")
    ops = []
    for dia, grupo in df.groupby(df.index.date):
        barras = list(grupo.itertuples())
        pos = None
        for i, b in enumerate(barras):
            ultimo = i == len(barras) - 1
            anterior = barras[i - 1] if i else None
            consecutiva = anterior is not None and (b.Index - anterior.Index).total_seconds() == 60
            abriu, high, low, close = map(int, (b.open, b.high, b.low, b.close))
            usada = False
            if pos is not None:
                passou = (abriu - pos["stop_atual"]) * pos["lado"] <= 0
                if passou:
                    encerrar(
                        pos,
                        b,
                        abriu,
                        "stop móvel" if pos["trailing_ativado"] else "stop inicial",
                        ops,
                    )
                    pos = None
                    usada = True
                else:
                    atualizar(pos, abriu, b.Index)
            armado_alta = consecutiva and abriu >= anterior.high + TICK
            armado_baixa = consecutiva and abriu <= anterior.low - TICK
            extremos = [high, low] if caminho == "maxima-primeiro" else [low, high]
            anterior_preco = abriu
            for destino in [*extremos, close]:
                for preco in passos(anterior_preco, destino):
                    if pos is not None:
                        if (preco - pos["stop_atual"]) * pos["lado"] <= 0:
                            encerrar(
                                pos,
                                b,
                                preco,
                                "stop móvel" if pos["trailing_ativado"] else "stop inicial",
                                ops,
                            )
                            pos = None
                            usada = True
                        else:
                            atualizar(pos, preco, b.Index)
                    elif consecutiva and not usada and not ultimo:
                        if preco >= anterior.high + TICK:
                            armado_alta = True
                        if preco <= anterior.low - TICK:
                            armado_baixa = True
                        lado = (
                            -1
                            if armado_alta and preco <= anterior.high - TICK
                            else (1 if armado_baixa and preco >= anterior.low + TICK else 0)
                        )
                        if lado:
                            entrada = preco + lado * TICK
                            stop = entrada - lado * stop_ticks * TICK
                            pos = {
                                "data": str(dia),
                                "lado": lado,
                                "entrada_em": str(b.Index),
                                "entrada": entrada,
                                "gatilho": preco,
                                "stop": stop,
                                "stop_atual": stop,
                                "alvo": None,
                                "trailing_ativado": False,
                                "movimentos_stop": [{"t": str(b.Index), "preco": stop}],
                            }
                            usada = True
                anterior_preco = destino
            if ultimo and pos is not None:
                encerrar(pos, b, close, "fim do pregão", ops)
                pos = None
    return ops


def resumir(ops, stop_ticks, caminho):
    saldo = pico = dd = 0.0
    meses = {}
    for op in ops:
        saldo += op["resultado_brl"]
        pico = max(pico, saldo)
        dd = min(dd, saldo - pico)
        mes = op["data"][:7]
        meses[mes] = round(meses.get(mes, 0) + op["resultado_brl"], 2)
    ganhos = sum(o["resultado_brl"] for o in ops if o["resultado_brl"] > 0)
    perdas = -sum(o["resultado_brl"] for o in ops if o["resultado_brl"] < 0)
    return {
        "stop_ticks": stop_ticks,
        "caminho": caminho,
        "operacoes": len(ops),
        "resultado_brl": round(saldo, 2),
        "por_mes": meses,
        "acerto_pct": round(100 * sum(o["resultado_brl"] > 0 for o in ops) / len(ops), 2)
        if ops
        else None,
        "fator_lucro": round(ganhos / perdas, 3) if perdas else None,
        "drawdown_max": round(dd, 2),
        "por_motivo": {
            m: sum(o["motivo"] == m for o in ops)
            for m in ("stop inicial", "stop móvel", "fim do pregão")
        },
    }


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    dados = ler_barras_mt5(ARQUIVO)
    if dados.index.has_duplicates or not dados.index.is_monotonic_increasing:
        raise ValueError("Dados duplicados ou fora de ordem")
    dados = dados.loc[INICIO:FIM]
    cenarios = []
    operacoes = {}
    for caminho in ("maxima-primeiro", "minima-primeiro"):
        for stop_ticks in (3, 5):
            ops = simular(dados, stop_ticks, caminho)
            cenarios.append(resumir(ops, stop_ticks, caminho))
            operacoes[f"{caminho}-{stop_ticks}"] = ops
    manifesto = montar_manifesto(
        estrategia="win-codex-rompimento-falso-v2",
        ativo="WIN$N",
        timeframe="M1",
        trecho="2026-fev-set-exploratorio",
        periodo=(INICIO, FIM),
        dados={
            "arquivo": ARQUIVO.name,
            "sha256": hashlib.sha256(ARQUIVO.read_bytes()).hexdigest(),
            "barras_periodo": len(dados),
        },
        custos={"custo_lado_brl": 0.25, "derrapagem_pts": 5, "valor_ponto_brl": 0.2},
        ambiguidade="duas-sequencias-hipoteticas",
        linhas=cenarios,
        comando=["robob3", "backtest-codex-falso", "--confirmo-fora-da-amostra"],
    )
    caminho = gravar_manifesto(manifesto, "data/backtests")
    Path("testes-codex/resultado-falso-v2.json").write_text(
        json.dumps(
            {"manifesto": str(caminho), "linhas": cenarios, "operacoes": operacoes},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps({"manifesto": str(caminho), "cenarios": cenarios}, ensure_ascii=False, indent=2)
    )
