"""Relatório de qualidade de barras intradiárias.

Identifica problemas; não corrige nada. Lacunas podem ser legítimas (leilão, minuto sem negócio,
pregão reduzido) — o relatório aponta para alguém conferir.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import time

import pandas as pd

from robob3.data.sessions import PregaoIncompleto, detectar_incompletos


@dataclass
class Lacuna:
    inicio: str
    fim: str
    barras_faltando: int


@dataclass
class RelatorioQualidade:
    linhas: int = 0
    primeira: str | None = None
    ultima: str | None = None
    pregoes: int = 0
    ordenado: bool = True
    timestamps_duplicados: int = 0
    ohlc_inconsistente: int = 0
    precos_nao_positivos: int = 0
    barras_volume_zero: int = 0
    barras_por_pregao_min: int = 0
    barras_por_pregao_mediana: float = 0.0
    barras_por_pregao_max: int = 0
    abertura_tipica: str = ""
    fechamento_tipico: str = ""
    pregoes_incompletos: list[PregaoIncompleto] = field(default_factory=list)
    pregoes_cobertura_baixa: list[str] = field(default_factory=list)
    lacunas_intradiarias: int = 0
    barras_faltando_total: int = 0
    maiores_lacunas: list[Lacuna] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_texto(self) -> str:
        d = self.to_dict()
        listas = ("maiores_lacunas", "pregoes_incompletos")
        linhas = [f"{k}: {v}" for k, v in d.items() if k not in listas]
        linhas.append(f"pregoes_incompletos: {len(self.pregoes_incompletos)}")
        linhas += [
            f"  {p.data} {p.primeira}-{p.ultima} ({p.barras} barras) "
            f"[{'ponta' if p.ponta else 'interno: investigar'}]: {p.motivo}"
            for p in self.pregoes_incompletos
        ]
        linhas.append("maiores_lacunas:")
        linhas += [
            f"  {g.inicio} -> {g.fim} ({g.barras_faltando} barras)" for g in self.maiores_lacunas
        ]
        return "\n".join(linhas)


def avaliar_barras(
    df: pd.DataFrame,
    minutos: int = 1,
    limiar_cobertura: float = 0.5,
    top_lacunas: int = 10,
    abertura: time | None = None,
    fechamento: time | None = None,
    tolerancia_min: int = 5,
) -> RelatorioQualidade:
    """Avalia barras de `minutos` minutos indexadas por timestamp.

    `abertura`/`fechamento` vazios = horários mais frequentes nos dados (ver sessions.py).
    """
    if df.empty:
        return RelatorioQualidade()

    idx = df.index
    ordenado = bool(idx.is_monotonic_increasing)
    duplicados = int(idx.duplicated().sum())

    ohlc_ruim = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    nao_positivos = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    col_vol = "real_volume" if "real_volume" in df.columns else "tick_volume"
    vol_zero = int((df[col_vol] == 0).sum()) if col_vol in df.columns else 0

    limpo = df[~idx.duplicated(keep="first")].sort_index()
    dias = limpo.index.normalize()
    por_dia = limpo.groupby(dias).size()
    mediana = float(por_dia.median())
    baixa = por_dia[por_dia < limiar_cobertura * mediana]

    passo = pd.Timedelta(minutes=minutos)
    t = limpo.index.to_series()
    delta = t.diff()
    dia = t.dt.normalize()
    mesmo_dia = dia == dia.shift()
    eh_lacuna = (delta > passo) & mesmo_dia
    faltando = ((delta[eh_lacuna] / passo).round().astype(int) - 1)

    incompletos, ab, fe = detectar_incompletos(limpo, abertura, fechamento, tolerancia_min)

    maiores = faltando.sort_values(ascending=False).head(top_lacunas)
    lacunas = [
        Lacuna(str(fim - (n + 1) * passo), str(fim), int(n)) for fim, n in maiores.items()
    ]

    return RelatorioQualidade(
        linhas=len(df),
        primeira=str(limpo.index[0]),
        ultima=str(limpo.index[-1]),
        pregoes=len(por_dia),
        ordenado=ordenado,
        timestamps_duplicados=duplicados,
        ohlc_inconsistente=int(ohlc_ruim.sum()),
        precos_nao_positivos=int(nao_positivos.sum()),
        barras_volume_zero=vol_zero,
        barras_por_pregao_min=int(por_dia.min()),
        barras_por_pregao_mediana=mediana,
        barras_por_pregao_max=int(por_dia.max()),
        abertura_tipica=ab,
        fechamento_tipico=fe,
        pregoes_incompletos=incompletos,
        pregoes_cobertura_baixa=[d.strftime("%Y-%m-%d") for d in baixa.index],
        lacunas_intradiarias=int(eh_lacuna.sum()),
        barras_faltando_total=int(faltando.sum()),
        maiores_lacunas=lacunas,
    )
