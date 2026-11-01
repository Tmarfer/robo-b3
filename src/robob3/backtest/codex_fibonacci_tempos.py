"""Grade exploratória com sinais e execução no mesmo tempo gráfico."""

import hashlib
import json
from pathlib import Path

import yaml

from robob3.backtest.codex_fibonacci import ESTRATEGIAS, resumo, simular
from robob3.backtest.codex_fichas import reamostrar_completas
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    rolls = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    fontes = {
        1: Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv"),
        5: Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv"),
    }
    fontes_df = {n: ler_barras_mt5(path).loc[:"2026-09-30"] for n, path in fontes.items()}
    hashes = {n: hashlib.sha256(path.read_bytes()).hexdigest() for n, path in fontes.items()}
    for df in fontes_df.values():
        if df.index.has_duplicates or not df.index.is_monotonic_increasing:
            raise ValueError("Dados duplicados ou fora de ordem")
    janelas = [
        ("desenvolvimento", "2023-04-03", "2025-12-30", 5, (5, 15)),
        ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30", 5, (5, 15)),
        ("2026-fev-set-comparavel", "2026-02-11", "2026-09-30", 1, (1, 5, 15)),
    ]
    resultados = []
    for periodo, inicio, fim, base, tempos in janelas:
        for minutos in tempos:
            barras = reamostrar_completas(fontes_df[base], minutos, base)
            for estrategia in (*ESTRATEGIAS, "retracao-38-50"):
                ops, exclusoes = simular(barras, rolls, estrategia, inicio, fim, minutos, minutos)
                linhas = [
                    dict(resumo(ops[modo], modo), timeframe=f"M{minutos}", sinal=f"M{minutos}")
                    for modo in ("padrao", "trailing")
                ]
                manifesto = montar_manifesto(
                    estrategia=f"codex-{estrategia}-mesmo-m{minutos}-v1",
                    ativo="WIN$N",
                    timeframe=f"sinal M{minutos} / execução M{minutos}",
                    trecho=periodo,
                    periodo=(inicio, fim),
                    dados={"arquivo": fontes[base].name, "sha256": hashes[base]},
                    custos={
                        "custo_lado_brl": 0.25,
                        "derrapagem_pts": 5,
                        "valor_ponto_brl": 0.2,
                        "ativacao_pts": 300,
                        "distancia_trailing_pts": 150,
                    },
                    ambiguidade="hipotese-adversa",
                    linhas=linhas,
                    comando=[
                        "robob3",
                        "backtest-codex-fibonacci-tempos",
                        "--confirmo-fora-da-amostra",
                    ],
                )
                destino = gravar_manifesto(manifesto, "data/backtests")
                grupo = {
                    "estrategia": estrategia,
                    "periodo": periodo,
                    "inicio": inicio,
                    "fim": fim,
                    "timeframe": f"M{minutos}",
                    "manifesto": str(destino),
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
    Path("testes-codex/resultado-fibonacci-tempos.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
