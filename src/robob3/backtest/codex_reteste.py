"""Hipótese exploratória: rompimento e reteste no M15, execução no M5."""

import hashlib
import json
from datetime import time
from pathlib import Path

import pandas as pd
import yaml

from robob3.backtest.codex_fichas import reamostrar_completas, resumir
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5

FONTE = Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv")
INICIO, FIM = "2023-04-03", "2025-12-30"


def preparar_sinais(barras, rolagens):
    m15 = reamostrar_completas(barras, 15, 5)
    limites = pd.to_datetime(sorted(str(x) for x in rolagens))
    grupos = pd.Series(limites.searchsorted(m15.index, side="right"), index=m15.index)
    m15["ema20"] = m15.groupby(grupos)["close"].transform(
        lambda s: s.ewm(span=20, adjust=False, min_periods=20).mean()
    )
    return m15


def buscar_sinal(barras, high, low):
    """Retorna o fechamento M15 e o lado apenas depois da confirmação e do reteste."""
    acima = abaixo = 0
    anterior = None
    for b in barras.itertuples():
        if b.Index.time() < time(9) or b.Index.time() > time(16, 30):
            continue
        if anterior is None or (b.Index - anterior.Index).total_seconds() != 900:
            acima = abaixo = 0
        if anterior is not None and pd.notna(b.ema20) and pd.notna(anterior.ema20):
            if (
                acima >= 2
                and b.low <= high
                and b.close > high
                and b.close > b.ema20 > anterior.ema20
            ):
                return b.Index + pd.Timedelta(minutes=15), 1
            if (
                abaixo >= 2
                and b.high >= low
                and b.close < low
                and b.close < b.ema20 < anterior.ema20
            ):
                return b.Index + pd.Timedelta(minutes=15), -1
        acima = acima + 1 if b.close > high else 0
        abaixo = abaixo + 1 if b.close < low else 0
        anterior = b
    return None


def executar_trade(regs, entrada_em, lado, nivel):
    if entrada_em not in regs.index or entrada_em.time() > time(16, 45):
        return None
    bar = regs.loc[entrada_em]
    entrada = int(bar.open) + lado * 5
    stop, alvo = entrada - lado * 300, entrada + lado * 600
    for ts, b in regs.loc[entrada_em:].iterrows():
        if ts.time() == time(17):
            saida, motivo, ambigua = int(b.open) - lado * 5, "tempo", False
            break
        abriu_stop = (b.open - stop) * lado <= 0
        abriu_alvo = (b.open - alvo) * lado >= 0
        bate_stop = b.low <= stop if lado == 1 else b.high >= stop
        bate_alvo = b.high >= alvo if lado == 1 else b.low <= alvo
        ambigua = bool(bate_stop and bate_alvo)
        if abriu_stop:
            saida, motivo = int(b.open) - lado * 5, "stop"
        elif abriu_alvo:
            saida, motivo = int(b.open), "alvo"
        elif bate_stop:
            saida, motivo = stop - lado * 5, "stop"
        elif bate_alvo:
            saida, motivo = alvo, "alvo"
        else:
            continue
        break
    else:
        raise ValueError("Pregão sem barra de saída às 17:00")
    return {
        "data": str(entrada_em.date()),
        "lado": lado,
        "entrada_em": str(entrada_em),
        "entrada": entrada,
        "stop": stop,
        "alvo": alvo,
        "nivel": nivel,
        "saida_em": str(ts),
        "saida": saida,
        "motivo": motivo,
        "ambigua": ambigua,
        "resultado_brl": round((saida - entrada) * lado * 0.2 - 0.5, 2),
    }


def simular(barras, rolagens):
    m15 = preparar_sinais(barras, rolagens)
    diarios = {str(d): g for d, g in barras.groupby(barras.index.date)}
    dias = sorted(diarios)
    rolls = {str(x) for x in rolagens}
    ops = []
    ignorados = {"rolagem": 0, "sem_17h": 0, "dia_anterior_incompleto": 0, "sem_sinal": 0}
    for i in range(1, len(dias)):
        dia = dias[i]
        if not INICIO <= dia <= FIM:
            continue
        anterior, hoje = diarios[dias[i - 1]], diarios[dia]
        if dia in rolls:
            ignorados["rolagem"] += 1
            continue
        if anterior.index[0].time() != time(9):
            ignorados["dia_anterior_incompleto"] += 1
            continue
        if not any(hoje.index.time == time(17)):
            ignorados["sem_17h"] += 1
            continue
        high, low = int(anterior.high.max()), int(anterior.low.min())
        sinais = m15.loc[dia]
        resultado = buscar_sinal(sinais, high, low)
        if resultado is None:
            ignorados["sem_sinal"] += 1
            continue
        entrada_em, lado = resultado
        op = executar_trade(hoje, entrada_em, lado, high if lado == 1 else low)
        if op:
            ops.append(op)
        else:
            ignorados["sem_sinal"] += 1
    return ops, ignorados


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    barras = ler_barras_mt5(FONTE)
    if barras.index.has_duplicates or not barras.index.is_monotonic_increasing:
        raise ValueError("Dados duplicados ou fora de ordem")
    barras = barras.loc[:FIM]
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    ops, ignorados = simular(barras, rolagens)
    resumo = resumir(ops, 15)
    resumo.update({"execucao": "M5", "ignorados": ignorados})
    manifest = montar_manifesto(
        estrategia="win-codex-reteste-media-v1",
        ativo="WIN$N",
        timeframe="sinal M15 / execução M5",
        trecho="desenvolvimento-exploratorio",
        periodo=(INICIO, FIM),
        dados={"arquivo": FONTE.name, "sha256": hashlib.sha256(FONTE.read_bytes()).hexdigest()},
        custos={
            "custo_lado_brl": 0.25,
            "derrapagem_pts": 5,
            "valor_ponto_brl": 0.2,
            "stop_pts": 300,
            "alvo_pts": 600,
        },
        ambiguidade="conservadora",
        linhas=[resumo],
        comando=["robob3", "backtest-codex-reteste"],
    )
    destino = gravar_manifesto(manifest, "data/backtests")
    Path("testes-codex/resultado-reteste-v1.json").write_text(
        json.dumps(
            {"manifesto": str(destino), "resumo": resumo, "operacoes": ops}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(json.dumps({"manifesto": str(destino), **resumo}, ensure_ascii=False, indent=2))
