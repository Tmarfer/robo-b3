"""Leitura dos CSV exportados pelo MT5 (Símbolos > Barras > Exportar barras).

Formato típico: separado por tabulação, cabeçalho `<DATE> <TIME> <OPEN> ...`, data `AAAA.MM.DD`,
muitas vezes em UTF-16. Os horários são os do servidor da corretora: o fuso precisa ser
confirmado e registrado; aqui os timestamps ficam sem fuso (naive).

A leitura não ordena nem remove duplicados: isso é papel do relatório de qualidade.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUNAS = {
    "<DATE>": "date",
    "<TIME>": "time",
    "<OPEN>": "open",
    "<HIGH>": "high",
    "<LOW>": "low",
    "<CLOSE>": "close",
    "<TICKVOL>": "tick_volume",
    "<VOL>": "real_volume",
    "<SPREAD>": "spread",
}


def _encoding(caminho: Path) -> str:
    inicio = caminho.read_bytes()[:4]
    if inicio.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if inicio.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "utf-8"


def ler_barras_mt5(caminho: str | Path) -> pd.DataFrame:
    """Lê um CSV de barras do MT5 e devolve DataFrame indexado por `time`."""
    caminho = Path(caminho)
    encoding = _encoding(caminho)
    with caminho.open(encoding=encoding) as f:
        cabecalho = f.readline()
    sep = "\t" if "\t" in cabecalho else ","

    df = pd.read_csv(caminho, sep=sep, encoding=encoding)
    df.columns = [c.strip() for c in df.columns]
    faltando = {"<DATE>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"} - set(df.columns)
    if faltando:
        raise ValueError(f"{caminho.name}: colunas ausentes {sorted(faltando)} — é export do MT5?")
    df = df.rename(columns=COLUNAS)

    texto = df["date"].astype(str).str.strip()
    if "time" in df.columns:
        texto = texto + " " + df["time"].astype(str).str.strip()
        df = df.drop(columns="time")
    df["time"] = _parse_datas(texto)
    df = df.drop(columns="date").set_index("time")

    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df


def _parse_datas(texto: pd.Series) -> pd.Series:
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return pd.to_datetime(texto, format=fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de data não reconhecido, ex.: {texto.iloc[0]!r}")


def escrever_barras_mt5(df: pd.DataFrame, caminho: str | Path) -> Path:
    """Grava barras no mesmo formato do export manual do MT5 (tabulação, UTF-8).

    `df` indexado por timestamp, com colunas open/high/low/close e opcionalmente
    tick_volume/real_volume/spread.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    inverso = {v: k for k, v in COLUNAS.items()}
    out = pd.DataFrame(
        {"<DATE>": df.index.strftime("%Y.%m.%d"), "<TIME>": df.index.strftime("%H:%M:%S")}
    )
    for c in ("open", "high", "low", "close", "tick_volume", "real_volume", "spread"):
        if c in df.columns:
            out[inverso[c]] = df[c].to_numpy()
    out.to_csv(caminho, sep="\t", index=False, encoding="utf-8")
    return caminho


def rates_para_df(rates) -> pd.DataFrame:
    """Converte o retorno de `MetaTrader5.copy_rates_*` (array estruturado) em DataFrame.

    O MT5 entrega `time` em segundos no horário do servidor (codificado como se fosse UTC);
    convertendo sem fuso, o resultado bate com o export manual.
    """
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    colunas = [c for c in COLUNAS.values() if c in df.columns and c not in ("date", "time")]
    return df.set_index("time")[colunas]
