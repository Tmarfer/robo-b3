"""Comparação de rompimento falso e reteste nos tempos disponíveis."""

import hashlib
import json
from pathlib import Path

import yaml

from robob3.backtest.codex_falso import resumir as resumo_falso
from robob3.backtest.codex_falso_adverso import simular as simular_falso
from robob3.backtest.codex_fichas import reamostrar_completas, resumir
from robob3.backtest.codex_reteste import simular as simular_reteste
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    fontes = {
        1: Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv"),
        5: Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv"),
    }
    dfs = {n: ler_barras_mt5(p).loc[:"2026-09-30"] for n, p in fontes.items()}
    hashes = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in fontes.items()}
    if any(df.index.has_duplicates or not df.index.is_monotonic_increasing for df in dfs.values()):
        raise ValueError("Dados duplicados ou fora de ordem")
    janelas = [
        ("desenvolvimento", "2023-04-03", "2025-12-30", 5, (5, 15)),
        ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30", 5, (5, 15)),
        ("2026-fev-set-comparavel", "2026-02-11", "2026-09-30", 1, (1, 5, 15)),
    ]
    resultados = []
    for periodo, inicio, fim, base, tempos in janelas:
        for minutos in tempos:
            barras = reamostrar_completas(dfs[base], minutos, base)
            for estrategia in ("falso", "reteste"):
                if estrategia == "falso":
                    ops = {
                        str(stop): simular_falso(barras.loc[inicio:fim], stop, minutos)
                        for stop in (3, 5)
                    }
                    linhas = [
                        dict(
                            resumo_falso(ops[str(stop)], stop, "adverso-com-confirmacao"),
                            timeframe=f"M{minutos}",
                        )
                        for stop in (3, 5)
                    ]
                    exclusoes = {}
                else:
                    operacoes, exclusoes = simular_reteste(
                        barras, rolagens, inicio, fim, minutos, minutos
                    )
                    ops = {"padrao": operacoes}
                    linhas = [dict(resumir(operacoes, minutos), timeframe=f"M{minutos}")]
                manifesto = montar_manifesto(
                    estrategia=f"codex-{estrategia}-mesmo-m{minutos}-v1",
                    ativo="WIN$N",
                    timeframe=f"M{minutos}",
                    trecho=periodo,
                    periodo=(inicio, fim),
                    dados={"arquivo": fontes[base].name, "sha256": hashes[base]},
                    custos={"custo_lado_brl": 0.25, "derrapagem_pts": 5, "valor_ponto_brl": 0.2},
                    ambiguidade="hipotese-adversa",
                    linhas=linhas,
                    comando=[
                        "robob3",
                        "backtest-codex-outros-tempos",
                        "--confirmo-fora-da-amostra",
                    ],
                )
                caminho = gravar_manifesto(manifesto, "data/backtests")
                grupo = {
                    "estrategia": estrategia,
                    "periodo": periodo,
                    "inicio": inicio,
                    "fim": fim,
                    "timeframe": f"M{minutos}",
                    "manifesto": str(caminho),
                    "linhas": linhas,
                    "operacoes": ops,
                    "exclusoes": exclusoes,
                }
                resultados.append(grupo)
                print(
                    json.dumps(
                        {k: v for k, v in grupo.items() if k != "operacoes"}, ensure_ascii=False
                    ),
                    flush=True,
                )
    Path("testes-codex/resultado-outros-tempos.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
