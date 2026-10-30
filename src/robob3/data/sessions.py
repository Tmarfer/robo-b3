"""Pregões: horário de abertura/fechamento por dia e detecção de pregões incompletos.

Um pregão é **incompleto** quando a primeira barra vem depois da abertura típica ou a última vem
antes do fechamento típico (com tolerância). Há dois tipos:

- **ponta**: 1º ou último dia do arquivo — corte da exportação (limite de barras, exportação
  durante o pregão). Esses são removidos por padrão.
- **interno**: dia no meio do período — pregão com horário especial oficial (ex.: Quarta-feira de
  Cinzas abre às 13:00) ou problema a investigar. Só são removidos se pedido explicitamente,
  depois de investigados: um pregão especial é um dia real de negociação.

Lacunas no meio do dia (leilão, pausa) **não** tornam o pregão incompleto: são eventos de mercado
e ficam no relatório de lacunas.

O horário esperado de cada dia vem dos **pregões vizinhos** (`janela` pregões antes e depois, sem o
próprio dia): o mais frequente de cada lado, e vale o mais tolerante dos dois. Assim, mudanças de
grade da B3 (ex.: fechamento 17:50 × 18:25 conforme o horário de verão dos EUA) não marcam
estações inteiras: no dia da troca, ele bate com um dos lados. Uma grade especial que dure mais que
`janela` pregões passa a ser tratada como regime normal. Com `abertura`/`fechamento` informados,
o horário esperado é fixo para todos os dias.
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
    ponta: bool  # 1º ou último dia do arquivo (corte da exportação)


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


def horarios_frequentes(resumo: pd.DataFrame, n: int = 3) -> tuple[list[str], list[str]]:
    """Os `n` horários de abertura e de fechamento mais comuns, como "HH:MM (dias)"."""

    def top(horas: pd.Series) -> list[str]:
        return [f"{_fmt(h)} ({c})" for h, c in horas.value_counts().head(n).items()]

    return top(_hora(resumo["primeira"])), top(_hora(resumo["ultima"]))


def _esperado_vizinhos(horas: pd.Series, janela: int, abertura: bool) -> pd.Series:
    """Horário esperado por dia a partir dos vizinhos; NaT se o dia não tiver vizinhos."""
    v = horas.to_numpy()
    minimo = max(1, (janela + 1) // 2)  # lado curto (início/fim do arquivo) é pouco confiável
    esperado = []
    for i in range(len(v)):
        lados = [v[max(0, i - janela) : i], v[i + 1 : i + 1 + janela]]
        confiaveis = [lado for lado in lados if len(lado) >= minimo]
        modas = []
        for lado in confiaveis or [lado for lado in lados if len(lado)]:
            m = pd.Series(lado).mode()
            modas.append(m.min() if abertura else m.max())
        if not modas:
            esperado.append(pd.NaT)
        else:
            # o mais tolerante: abertura mais tarde, fechamento mais cedo
            esperado.append(max(modas) if abertura else min(modas))
    return pd.Series(esperado, index=horas.index, dtype="timedelta64[ns]")


def detectar_incompletos(
    df: pd.DataFrame,
    abertura: time | None = None,
    fechamento: time | None = None,
    tolerancia_min: int = 5,
    janela: int = 5,
) -> tuple[list[PregaoIncompleto], str, str]:
    """Lista pregões incompletos e devolve a abertura/fechamento mais frequentes ("HH:MM")."""
    resumo = resumo_pregoes(df)
    if resumo.empty:
        return [], "", ""
    tip_ab, tip_fe = horarios_tipicos(resumo)
    ini, fim = _hora(resumo["primeira"]), _hora(resumo["ultima"])
    if abertura:
        ab = pd.Series(_para_delta(abertura), index=resumo.index)
    else:
        ab = _esperado_vizinhos(ini, janela, abertura=True).fillna(tip_ab)
    if fechamento:
        fe = pd.Series(_para_delta(fechamento), index=resumo.index)
    else:
        fe = _esperado_vizinhos(fim, janela, abertura=False).fillna(tip_fe)
    tol = pd.Timedelta(minutes=tolerancia_min)

    tarde, cedo = ini > ab + tol, fim < fe - tol

    incompletos = []
    for dia in resumo.index[tarde | cedo]:
        motivos = []
        if tarde[dia]:
            motivos.append(f"abre {_fmt(ini[dia])} (esperado {_fmt(ab[dia])})")
        if cedo[dia]:
            motivos.append(f"fecha {_fmt(fim[dia])} (esperado {_fmt(fe[dia])})")
        incompletos.append(
            PregaoIncompleto(
                data=dia.strftime("%Y-%m-%d"),
                primeira=_fmt(ini[dia]),
                ultima=_fmt(fim[dia]),
                barras=int(resumo.at[dia, "barras"]),
                motivo="; ".join(motivos),
                ponta=dia in (resumo.index[0], resumo.index[-1]),
            )
        )
    return incompletos, _fmt(tip_ab), _fmt(tip_fe)


def remover_pregoes_incompletos(
    df: pd.DataFrame,
    abertura: time | None = None,
    fechamento: time | None = None,
    tolerancia_min: int = 5,
    internos: bool = False,
    janela: int = 5,
) -> tuple[pd.DataFrame, list[PregaoIncompleto]]:
    """Devolve as barras sem os pregões incompletos e a lista do que foi removido.

    Por padrão remove só as pontas; `internos=True` remove também os do meio do período.
    """
    incompletos, _, _ = detectar_incompletos(df, abertura, fechamento, tolerancia_min, janela)
    removidos = [p for p in incompletos if p.ponta or internos]
    fora = pd.to_datetime([p.data for p in removidos])
    return df[~df.index.normalize().isin(fora)], removidos


def gaps_abertura(df: pd.DataFrame) -> pd.DataFrame:
    """Salto entre o fechamento de um pregão e a abertura do seguinte, por dia.

    Em série contínua (`WIN$N`, `WDO$N`), saltos grandes nas datas de vencimento indicam a
    rolagem e se a série é ajustada (sem salto) ou não; fora delas, eventos de mercado.
    Ordenado pelo tamanho do salto, maior primeiro.
    """
    limpo = df[~df.index.duplicated(keep="first")].sort_index()
    g = limpo.groupby(limpo.index.normalize())
    dia = pd.DataFrame({"abertura": g["open"].first(), "fechamento": g["close"].last()})
    dia["fech_anterior"] = dia["fechamento"].shift()
    dia["gap_pts"] = dia["abertura"] - dia["fech_anterior"]
    dia["gap_pct"] = 100 * dia["gap_pts"] / dia["fech_anterior"]
    dia.index.name = "data"
    dia = dia.dropna(subset=["fech_anterior"])
    return dia.reindex(dia["gap_pct"].abs().sort_values(ascending=False).index)
