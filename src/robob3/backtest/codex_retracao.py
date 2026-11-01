"""Adaptação exploratória da retração 38,2–50% em pivôs já confirmados."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from robob3.backtest.codex_fibonacci import ARQUIVO, Ziguezague, resumo, simular
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5


def sinais_retracao(barras):
    zig = Ziguezague(300)
    consumidos = set()
    for b in barras.itertuples():
        if b.Index.time() > pd.Timestamp("16:30").time():
            break
        zig.atualizar(b.Index, b.close)
        if len(zig.pivos) < 4:
            continue
        a, p2, c, d = zig.pivos[-4:]
        tipos = [p["tipo"] for p in (a, p2, c, d)]
        lado = (
            1
            if tipos == ["fundo", "topo", "fundo", "topo"]
            else (-1 if tipos == ["topo", "fundo", "topo", "fundo"] else 0)
        )
        if not lado:
            continue
        av, bv, cv, dv = (p["preco"] * lado for p in (a, p2, c, d))
        if not (av < cv < bv < dv):
            continue
        chave = tuple((p["tipo"], p["extremo_em"]) for p in (a, p2, c, d))
        if chave in consumidos:
            continue
        amplitude = dv - cv
        fechamento = b.close * lado
        borda_superior = dv - 0.382 * amplitude
        borda_inferior = dv - 0.5 * amplitude
        invalidacao = dv - 0.667 * amplitude
        if fechamento > dv or fechamento < invalidacao:
            consumidos.add(chave)
        elif borda_inferior <= fechamento <= borda_superior:
            consumidos.add(chave)
            yield {
                "sinal_em": b.Index,
                "lado": lado,
                "stop": (invalidacao - 5) * lado,
                "alvo": d["preco"],
                "nivel": ((borda_superior + borda_inferior) / 2) * lado,
            }


def executar():
    codigo = commit_atual()
    if not codigo["commit"] or codigo["codigo_alterado"] is not False:
        raise RuntimeError("É necessário commitar o código antes do backtest")
    df = ler_barras_mt5(ARQUIVO)
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        raise ValueError("Dados duplicados ou fora de ordem")
    df = df.loc[:"2026-09-30"]
    rolagens = yaml.safe_load(Path("config/rolagens.yaml").read_text())["WIN"]["datas"]
    janelas = [
        ("desenvolvimento", "2023-04-03", "2025-12-30"),
        ("2026-jan-set-exploratorio", "2026-01-02", "2026-09-30"),
    ]
    arquivo_hash = hashlib.sha256(ARQUIVO.read_bytes()).hexdigest()
    resultados = []
    for periodo, inicio, fim in janelas:
        ops, exclusoes = simular(df, rolagens, "retracao-38-50", inicio, fim)
        linhas = [resumo(ops[modo], modo) for modo in ("padrao", "trailing")]
        manifesto = montar_manifesto(
            estrategia="codex-retracao-38-50-v1",
            ativo="WIN$N",
            timeframe="sinal M15 / execução M5",
            trecho=periodo,
            periodo=(inicio, fim),
            dados={"arquivo": ARQUIVO.name, "sha256": arquivo_hash},
            custos={
                "custo_lado_brl": 0.25,
                "derrapagem_pts": 5,
                "valor_ponto_brl": 0.2,
                "ativacao_pts": 300,
                "distancia_trailing_pts": 150,
            },
            ambiguidade="hipotese-adversa",
            linhas=linhas,
            comando=["robob3", "backtest-codex-retracao", "--confirmo-fora-da-amostra"],
        )
        destino = gravar_manifesto(manifesto, "data/backtests")
        grupo = {
            "estrategia": "retracao-38-50",
            "periodo": periodo,
            "inicio": inicio,
            "fim": fim,
            "manifesto": str(destino),
            "linhas": linhas,
            "operacoes": ops,
            "exclusoes": exclusoes,
        }
        resultados.append(grupo)
        print(
            json.dumps({k: v for k, v in grupo.items() if k != "operacoes"}, ensure_ascii=False),
            flush=True,
        )
    Path("testes-codex/resultado-retracao.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
