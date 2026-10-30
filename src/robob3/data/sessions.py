"""Pregões: horário de abertura/fechamento por dia e detecção de pregões incompletos.

Um pregão é **incompleto** quando a primeira barra vem depois da abertura típica ou a última vem
antes do fechamento típico (com tolerância). Isso pega os cortes das pontas de uma exportação —
1º dia cortado pelo limite de barras, último dia exportado durante o pregão.

Lacunas no meio do dia (leilão, pausa) **não** tornam o pregão incompleto: são eventos de mercado
e ficam no relatório de lacunas.

Abertura e fechamento típicos são o horário mais frequente nos dados (com empate, a abertura mais
cedo e o fechamento mais tarde). Se o horário da B3 mudar no período (ex.: horário de verão nos
EUA), a estação inteira aparece como incompleta: nesse caso, informar os horários explicitamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd


@dataclass
class PregaoIncompleto:
    data: str
    primeira: str
    ultima: str
    barras: int
    motivo: str


def resumo_pregoes(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por dia: horário da primeira e da última barra e quantidade de barras."""
    idx = df.index[~df.index.duplicated(keep="first")].sort_values()
    t = pd.Series(idx, index=idx)
    g = t.groupby(idx.normalize())
    out = pd.DataFrame({"primeira": g.min(), "ultima": g.max(), "barras": g.size()})
    out.index.name = "data"
    return out


def _hora(ts: pd.Series) -> pd.Series:
    return ts - ts.dt.normalize()


def _fmt(delta: pd.Timedelta) -> str:
    minutos = int(delta.total_seconds() // 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _para_delta(h: time) -> pd.Timedelta:
    return pd.Timedelta(hours=h.hour, minutes=h.minute, seconds=h.second)


def horarios_tipicos(resumo: pd.DataFrame) -> tuple[pd.Timedelta, pd.Timedelta]:
    abertura = _hora(resumo["primeira"]).mode().min()
    fechamento = _hora(resumo["ultima"]).mode().max()
    return abertura, fechamento


def detectar_incompletos(
    df: pd.DataFrame,
    abertura: time | None = None,
    fechamento: time | None = None,
    tolerancia_min: int = 5,
) -> tuple[list[PregaoIncompleto], str, str]:
    """Lista pregões incompletos e devolve também a abertura/fechamento usados ("HH:MM")."""
    resumo = resumo_pregoes(df)
    if resumo.empty:
        return [], "", ""
    tip_ab, tip_fe = horarios_tipicos(resumo)
    ab = _para_delta(abertura) if abertura else tip_ab
    fe = _para_delta(fechamento) if fechamento else tip_fe
    tol = pd.Timedelta(minutes=tolerancia_min)

    ini, fim = _hora(resumo["primeira"]), _hora(resumo["ultima"])
    tarde, cedo = ini > ab + tol, fim < fe - tol

    incompletos = []
    for dia in resumo.index[tarde | cedo]:
        motivos = []
        if tarde[dia]:
            motivos.append(f"abre {_fmt(ini[dia])} (esperado {_fmt(ab)})")
        if cedo[dia]:
            motivos.append(f"fecha {_fmt(fim[dia])} (esperado {_fmt(fe)})")
        incompletos.append(
            PregaoIncompleto(
                data=dia.strftime("%Y-%m-%d"),
                primeira=_fmt(ini[dia]),
                ultima=_fmt(fim[dia]),
                barras=int(resumo.at[dia, "barras"]),
                motivo="; ".join(motivos),
            )
        )
    return incompletos, _fmt(ab), _fmt(fe)


def remover_pregoes_incompletos(
    df: pd.DataFrame,
    abertura: time | None = None,
    fechamento: time | None = None,
    tolerancia_min: int = 5,
) -> tuple[pd.DataFrame, list[PregaoIncompleto]]:
    """Devolve as barras sem os pregões incompletos e a lista do que foi removido."""
    incompletos, _, _ = detectar_incompletos(df, abertura, fechamento, tolerancia_min)
    fora = pd.to_datetime([p.data for p in incompletos])
    return df[~df.index.normalize().isin(fora)], incompletos
