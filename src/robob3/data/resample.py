"""Reamostragem de barras (ex.: M1 -> M5/M15) sem preencher lacunas."""

from __future__ import annotations

import pandas as pd

MINUTOS_DIA = 24 * 60


def reamostrar(df: pd.DataFrame, minutos: int) -> pd.DataFrame:
    """Agrega barras em janelas de `minutos`, alinhadas à meia-noite.

    Abertura = primeira, máxima = maior, mínima = menor, fechamento = último, volumes somados,
    spread = maior (conservador). A coluna `barras` diz quantas barras de origem formaram cada
    candle, para identificar candles incompletos. Janelas sem dados são descartadas.
    """
    if minutos <= 0 or MINUTOS_DIA % minutos:
        raise ValueError("`minutos` precisa dividir 1440 (ex.: 5, 15, 30, 60)")
    if df.index.has_duplicates:
        raise ValueError("Há timestamps duplicados; rode o relatório de qualidade e trate antes")

    regras = {"open": "first", "high": "max", "low": "min", "close": "last"}
    for c in ("tick_volume", "real_volume"):
        if c in df.columns:
            regras[c] = "sum"
    if "spread" in df.columns:
        regras["spread"] = "max"

    janelas = df.sort_index().resample(
        f"{minutos}min", label="left", closed="left", origin="start_day"
    )
    out = janelas.agg(regras)
    out["barras"] = janelas.size()
    return out[out["barras"] > 0].astype({"barras": int})
