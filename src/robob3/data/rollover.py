"""Ajuste de rolagem (retroajuste) de séries contínuas não ajustadas, como WIN$N e WDO$N da Clear.

Para cada data de troca, o salto é medido entre o fechamento do último pregão antes da troca e a
abertura do dia da troca, e aplicado a todas as barras anteriores:

- **aditivo** (padrão): soma o salto em pontos. Preserva diferenças em pontos — dentro de um dia,
  stops, alvos e resultado em pontos ficam idênticos aos da série original.
- **razao**: multiplica por abertura/fechamento. Preserva variações percentuais.

Limitação: sem os dois contratos lado a lado, o salto medido inclui também o movimento de mercado
entre o fechamento e a abertura daquele dia, não só o diferencial entre contratos.

A série ajustada serve para indicadores que atravessam dias (médias, volatilidade, gaps). Preços
de execução no backtest devem continuar vindo da série original.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml

PRECOS = ["open", "high", "low", "close"]


@dataclass
class Ajuste:
    data: str
    fech_anterior: float | None
    abertura: float | None
    salto: float | None  # pontos (aditivo) ou fator (razão)
    situacao: str  # "aplicado" | "fora do período"


@dataclass
class Rolagens:
    simbolo: str
    regra: str
    datas: list[date]
    pendentes: list[date]


def carregar_rolagens(ativo: str, caminho: str | Path = "config/rolagens.yaml") -> Rolagens:
    with Path(caminho).open(encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    if ativo not in dados:
        raise ValueError(f"ativo {ativo!r} não está em {caminho} (há: {sorted(dados)})")
    d = dados[ativo]
    return Rolagens(d["simbolo"], d["regra"], list(d["datas"]), list(d.get("pendentes") or []))


def ajustar_rolagem(
    df: pd.DataFrame,
    datas: list[date],
    metodo: Literal["aditivo", "razao"] = "aditivo",
) -> tuple[pd.DataFrame, list[Ajuste]]:
    """Devolve a série retroajustada e a lista de ajustes (um por data de troca)."""
    if metodo not in ("aditivo", "razao"):
        raise ValueError("metodo deve ser 'aditivo' ou 'razao'")
    serie = df[~df.index.duplicated(keep="first")].sort_index()
    dias = serie.index.normalize()
    g = serie.groupby(dias)
    abertura, fechamento = g["open"].first(), g["close"].last()

    out = serie.copy()
    out[PRECOS] = out[PRECOS].astype(float)
    ajustes = []
    for d in sorted(pd.Timestamp(x) for x in datas):
        anteriores = fechamento.index[fechamento.index < d]
        if d not in abertura.index or anteriores.empty:
            ajustes.append(Ajuste(d.strftime("%Y-%m-%d"), None, None, None, "fora do período"))
            continue
        fech, ab = float(fechamento[anteriores[-1]]), float(abertura[d])
        antes = dias < d
        if metodo == "aditivo":
            salto = ab - fech
            out.loc[antes, PRECOS] += salto
        else:
            salto = ab / fech
            out.loc[antes, PRECOS] *= salto
        ajustes.append(Ajuste(d.strftime("%Y-%m-%d"), fech, ab, salto, "aplicado"))
    return out, ajustes
