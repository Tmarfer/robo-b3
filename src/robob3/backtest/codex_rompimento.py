"""Experimento local, congelado em testes-codex/rompimento-v1.md."""

import hashlib
import json
import math
from pathlib import Path

from robob3.backtest.manifesto import gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def simular(df):
    operacoes = []
    barras = {}
    for dia, grupo in df.groupby(df.index.date):
        registros = list(grupo.itertuples())
        barras[str(dia)] = [
            {"t": str(b.Index), "o": b.open, "h": b.high, "l": b.low, "c": b.close}
            for b in registros
        ]
        pos = None
        for i, b in enumerate(registros):
            if i == 0:
                continue
            anterior = registros[i - 1]
            tinha_posicao = pos is not None
            if pos is None and i < len(registros) - 1:
                if (b.Index - anterior.Index).total_seconds() != 300:
                    continue
                gatilho = anterior.high + 5
                if b.high >= gatilho:
                    entrada = max(b.open, gatilho) + 5
                    pos = {
                        "data": str(dia),
                        "entrada_em": str(b.Index),
                        "entrada": entrada,
                        "gatilho": gatilho,
                        "stop": math.floor(entrada * 0.90 / 5) * 5,
                        "alvo": math.ceil(entrada * 1.03 / 5) * 5,
                    }
            if pos is None:
                continue
            stop = b.low <= pos["stop"]
            alvo = b.high >= pos["alvo"]
            motivo = None
            if tinha_posicao and b.open <= pos["stop"]:
                saida, motivo = b.open - 5, "stop"
            elif tinha_posicao and b.open >= pos["alvo"]:
                saida, motivo = b.open, "alvo"
            elif stop:
                saida, motivo = pos["stop"] - 5, "stop"
            elif alvo:
                saida, motivo = pos["alvo"], "alvo"
            elif i == len(registros) - 1:
                saida, motivo = b.close - 5, "fim do pregão"
            if motivo:
                pos.update(
                    {
                        "saida_em": str(b.Index),
                        "saida": saida,
                        "motivo": motivo,
                        "resultado_brl": round((saida - pos["entrada"]) * 0.2 - 0.5, 2),
                        "ambigua": bool(stop and (alvo or not tinha_posicao)),
                    }
                )
                operacoes.append(pos)
                pos = None
    return operacoes, barras


def executar_rodada(arquivo, periodo="desenvolvimento", confirmo=False):
    if periodo == "fora-da-amostra" and not confirmo:
        raise ValueError("Fora da amostra exige --confirmo-fora-da-amostra")
    periodos = {
        "desenvolvimento": ("2023-03-31", "2025-12-30"),
        "fora-da-amostra": ("2026-01-02", "2026-09-30"),
    }
    inicio, fim = periodos[periodo]
    caminho = Path(arquivo)
    dados = ler_barras_mt5(caminho)
    if dados.index.has_duplicates or not dados.index.is_monotonic_increasing:
        raise ValueError("Dados duplicados ou fora de ordem: teste interrompido")
    dados = dados.loc[inicio:fim]
    ops, barras = simular(dados)
    saldos, acumulado, pico, dd = {}, 0.0, 0.0, 0.0
    for op in ops:
        acumulado += op["resultado_brl"]
        pico = max(pico, acumulado)
        dd = min(dd, acumulado - pico)
        ano = op["data"][:4]
        saldos[ano] = round(saldos.get(ano, 0) + op["resultado_brl"], 2)
    ganhos = sum(o["resultado_brl"] for o in ops if o["resultado_brl"] > 0)
    perdas = -sum(o["resultado_brl"] for o in ops if o["resultado_brl"] < 0)
    linha = {
        "parametros": {"alvo_pct": 3, "stop_pct": 10},
        "operacoes": len(ops),
        "resultado_brl": round(acumulado, 2),
        "por_ano": saldos,
        "acerto_pct": round(100 * sum(o["resultado_brl"] > 0 for o in ops) / len(ops), 2)
        if ops
        else None,
        "fator_lucro": round(ganhos / perdas, 3) if perdas else None,
        "drawdown_max": round(dd, 2),
        "por_motivo": {
            m: sum(o["motivo"] == m for o in ops) for m in ("alvo", "stop", "fim do pregão")
        },
    }
    manifesto = montar_manifesto(
        estrategia="win-codex-rompimento-v1",
        ativo="WIN$N",
        timeframe="M5",
        trecho=periodo,
        periodo=(inicio, fim),
        dados={
            "arquivo": caminho.name,
            "sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
            "barras_periodo": len(dados),
        },
        custos={"custo_lado_brl": 0.25, "derrapagem_pts": 5, "valor_ponto_brl": 0.2},
        ambiguidade="conservadora",
        linhas=[linha],
        comando=["robob3", "backtest-codex-rompimento", str(caminho)]
        + (
            ["--periodo", "fora-da-amostra", "--confirmo-fora-da-amostra"]
            if periodo == "fora-da-amostra"
            else []
        ),
    )
    if not manifesto["codigo"]["commit"] or manifesto["codigo"]["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    destino = gravar_manifesto(manifesto, "data/backtests")
    resultado = "resultado-2026-jan-set.json" if periodo == "fora-da-amostra" else "resultado.json"
    Path("testes-codex", resultado).write_text(
        json.dumps(
            {"manifesto": str(destino), "resumo": linha, "operacoes": ops, "barras": barras},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"manifesto": str(destino), **linha}, ensure_ascii=False, indent=2))
