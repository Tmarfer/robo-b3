"""Diagnóstico com sinal confirmado e ordem adversa dentro das barras M1."""

import hashlib
import json
from pathlib import Path

from robob3.backtest.codex_falso import ARQUIVO, FIM, INICIO, TICK, encerrar, resumir
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def sinal(barra, anterior):
    venda = barra.high >= anterior.high + TICK and barra.close <= anterior.high - TICK
    compra = barra.low <= anterior.low - TICK and barra.close >= anterior.low + TICK
    return 0 if compra == venda else (1 if compra else -1)


def simular(df, stop_ticks):
    if stop_ticks not in (3, 5):
        raise ValueError("Stop inválido")
    ops = []
    for dia, grupo in df.groupby(df.index.date):
        regs = list(grupo.itertuples())
        pos = None
        for i, b in enumerate(regs):
            ultimo = i == len(regs) - 1
            anterior = regs[i - 1] if i else None
            base = regs[i - 2] if i >= 2 else None
            consecutiva = (
                anterior is not None
                and base is not None
                and (b.Index - anterior.Index).total_seconds() == 60
                and (anterior.Index - base.Index).total_seconds() == 60
            )
            if pos is None and consecutiva and not ultimo:
                lado = sinal(anterior, base)
                if lado:
                    entrada = int(b.open) + lado * TICK
                    stop = entrada - lado * stop_ticks * TICK
                    pos = {
                        "data": str(dia),
                        "lado": lado,
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
            stop = pos["stop_atual"]
            if (aberto - stop) * lado <= 0:
                encerrar(
                    pos, b, aberto, "stop móvel" if pos["trailing_ativado"] else "stop inicial", ops
                )
                pos = None
                continue
            if (adverso - stop) * lado <= 0:
                encerrar(
                    pos, b, stop, "stop móvel" if pos["trailing_ativado"] else "stop inicial", ops
                )
                pos = None
                continue
            if (favoravel - pos["entrada"]) * lado >= 4 * TICK:
                max_stop = favoravel - lado * 2 * TICK
                if (max_stop - stop) * lado > 0:
                    if (adverso - max_stop) * lado <= 0:
                        protecao = pos["entrada"] + lado * 2 * TICK
                        pior = (
                            max(stop, protecao, adverso)
                            if lado == 1
                            else min(stop, protecao, adverso)
                        )
                        pos["stop_atual"] = pior
                        pos["trailing_ativado"] = True
                        pos["movimentos_stop"].append({"t": str(b.Index), "preco": pior})
                        encerrar(pos, b, pior, "stop móvel", ops)
                        pos = None
                        continue
                    pos["stop_atual"] = max_stop
                    pos["trailing_ativado"] = True
                    pos["movimentos_stop"].append({"t": str(b.Index), "preco": max_stop})
            if ultimo:
                encerrar(pos, b, int(b.close), "fim do pregão", ops)
                pos = None
    return ops


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    dados = ler_barras_mt5(ARQUIVO)
    if dados.index.has_duplicates or not dados.index.is_monotonic_increasing:
        raise ValueError("Dados duplicados ou fora de ordem")
    dados = dados.loc[INICIO:FIM]
    linhas, operacoes = [], {}
    for stop in (3, 5):
        ops = simular(dados, stop)
        linhas.append(resumir(ops, stop, "adverso-com-confirmacao"))
        operacoes[str(stop)] = ops
    manifesto = montar_manifesto(
        estrategia="win-codex-falso-confirmado-v2",
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
        ambiguidade="adverso",
        linhas=linhas,
        comando=["robob3", "backtest-codex-falso-adverso", "--confirmo-fora-da-amostra"],
    )
    caminho = gravar_manifesto(manifesto, "data/backtests")
    Path("testes-codex/resultado-falso-confirmado.json").write_text(
        json.dumps(
            {"manifesto": str(caminho), "linhas": linhas, "operacoes": operacoes},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"manifesto": str(caminho), "cenarios": linhas}, ensure_ascii=False, indent=2))
