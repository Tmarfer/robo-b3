"""Trailing 30/15 para Fibogap e retração, com entradas pareadas."""

import hashlib
import json
from pathlib import Path

import yaml

from robob3.backtest.codex_fibonacci import resumo, simular
from robob3.backtest.codex_fichas import reamostrar_completas
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5

FONTES = {
    1: Path("data/raw/WIN-N_M1_clear-mt5_20261029.csv"),
    5: Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv"),
}
JANELAS = [
    ("desenvolvimento", "2023-04-03", "2025-12-30", 5, (5, 15)),
    ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30", 5, (5, 15)),
    ("2026-fev-set-comparavel", "2026-02-11", "2026-09-30", 1, (1, 5, 15)),
]


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    dados = {n: ler_barras_mt5(p).loc[:"2026-09-30"] for n, p in FONTES.items()}
    hashes = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in FONTES.items()}
    resultados = []
    for periodo, inicio, fim, base, tempos in JANELAS:
        for minutos in tempos:
            barras = reamostrar_completas(dados[base], minutos, base)
            for estrategia in ("fibogap", "retracao-38-50"):
                ops, exclusoes = simular(
                    barras, rolagens, estrategia, inicio, fim, minutos, minutos, 30, 15
                )
                linhas = [
                    dict(resumo(ops["padrao"], "padrao"), timeframe=f"M{minutos}"),
                    dict(resumo(ops["trailing"], "trailing-30-15"), timeframe=f"M{minutos}"),
                ]
                manifesto = montar_manifesto(
                    estrategia=f"codex-{estrategia}-trailing-30-15-v1",
                    ativo="WIN$N",
                    timeframe=f"sinal M{minutos} / execução M{minutos}",
                    trecho=periodo,
                    periodo=(inicio, fim),
                    dados={"arquivo": FONTES[base].name, "sha256": hashes[base]},
                    custos={
                        "custo_lado_brl": 0.25,
                        "derrapagem_pts": 5,
                        "valor_ponto_brl": 0.2,
                        "ativacao_pts": 30,
                        "distancia_trailing_pts": 15,
                    },
                    ambiguidade="hipotese-adversa",
                    linhas=linhas,
                    comando=[
                        "robob3",
                        "backtest-codex-trailing-curto",
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
    Path("testes-codex/resultado-trailing-curto.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
