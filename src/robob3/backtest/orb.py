"""Backtest da estratégia win-orb-v1 (docs/estrategias/win-orb-v1.md), barra a barra.

Implementa a especificação congelada em 30/10/2026. Qualquer mudança de regra é uma nova versão
da estratégia, não um ajuste aqui.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import time

import numpy as np
import pandas as pd

from robob3.data.sessions import remover_pregoes_incompletos

# Períodos definidos na especificação, antes de qualquer teste.
PERIODOS = {
    "desenvolvimento": ("2023-03-31", "2025-12-30"),
    "fora-da-amostra": ("2026-01-02", "2026-10-29"),
}


@dataclass(frozen=True)
class ParametrosORB:
    stop: float = 200.0  # pontos
    alvo: float = 2.0  # múltiplo do stop
    tick: float = 5.0
    derrapagem: float = 5.0  # pontos contra, em entradas, stops e saída por tempo
    custo_lado: float = 0.25  # R$ por contrato por lado
    valor_ponto: float = 0.20  # R$ por ponto por contrato
    abertura: time = time(9, 0)
    barras_fa: int = 3
    minutos: int = 5
    fim_entradas: time = time(11, 55)  # última barra que pode disparar entrada
    saida_tempo: time = time(17, 0)


@dataclass
class Operacao:
    data: str
    lado: str  # "C" compra, "V" venda
    hora_entrada: str
    referencia: float  # gatilho, ou abertura da barra em caso de salto
    entrada: float  # referência + derrapagem
    stop: float
    alvo: float
    hora_saida: str
    saida: float
    motivo: str  # alvo | stop | tempo | fim_do_dia
    pontos: float
    resultado: float  # R$, já descontados os custos
    ambigua: bool  # usou uma hipótese conservadora da especificação


def _hora(ts: pd.Timestamp) -> time:
    return ts.time()


def _saida(lado, bar, stop, alvo, d):
    """Testa uma barra posterior à da entrada. Devolve (preço, motivo, ambígua) ou None."""
    o, h, low = bar.open, bar.high, bar.low
    if lado == "C":
        if o <= stop:
            return o - d, "stop", False
        if o >= alvo:
            return o, "alvo", False
        bate_stop, bate_alvo = low <= stop, h >= alvo
        if bate_stop:
            return stop - d, "stop", bate_alvo
        if bate_alvo:
            return alvo, "alvo", False
    else:
        if o >= stop:
            return o + d, "stop", False
        if o <= alvo:
            return o, "alvo", False
        bate_stop, bate_alvo = h >= stop, low <= alvo
        if bate_stop:
            return stop + d, "stop", bate_alvo
        if bate_alvo:
            return alvo, "alvo", False
    return None


def _executar(
    resto: pd.DataFrame, i: int, lado: str, ref: float, ambigua: bool, p: ParametrosORB
) -> Operacao:
    """Entrada na barra `i` de `resto` com preço de referência `ref`; segue até a saída."""
    d, dist = p.derrapagem, p.stop
    ts, bar = resto.index[i], resto.iloc[i]
    if lado == "C":
        entrada, stop, alvo = ref + d, ref - dist, ref + p.alvo * dist
        bate_stop, bate_alvo = bar.low <= stop, bar.high >= alvo
    else:
        entrada, stop, alvo = ref - d, ref + dist, ref - p.alvo * dist
        bate_stop, bate_alvo = bar.high >= stop, bar.low <= alvo

    if bate_stop:  # entrada e stop na mesma barra: considera stop
        fim = (stop - d if lado == "C" else stop + d), "stop", True, ts
    elif bate_alvo:  # entrada e alvo na mesma barra, sem stop: alvo
        fim = alvo, "alvo", ambigua, ts
    else:
        fim = None
        for ts2, bar2 in resto.iloc[i + 1 :].iterrows():
            if _hora(ts2) >= p.saida_tempo:
                fim = (bar2.open - d if lado == "C" else bar2.open + d), "tempo", ambigua, ts2
                break
            r = _saida(lado, bar2, stop, alvo, d)
            if r:
                fim = r[0], r[1], ambigua or r[2], ts2
                break
        if fim is None:  # pregão acabou antes das 17:00
            ult_ts, ult = resto.index[-1], resto.iloc[-1]
            fim = (ult.close - d if lado == "C" else ult.close + d), "fim_do_dia", ambigua, ult_ts

    saida, motivo, amb, ts_saida = fim
    pontos = saida - entrada if lado == "C" else entrada - saida
    return Operacao(
        data=ts.strftime("%Y-%m-%d"),
        lado=lado,
        hora_entrada=ts.strftime("%H:%M"),
        referencia=float(ref),
        entrada=float(entrada),
        stop=float(stop),
        alvo=float(alvo),
        hora_saida=ts_saida.strftime("%H:%M"),
        saida=float(saida),
        motivo=motivo,
        pontos=float(pontos),
        resultado=float(pontos * p.valor_ponto - 2 * p.custo_lado),
        ambigua=bool(amb),
    )


def _preparar(barras: pd.DataFrame, p: ParametrosORB) -> tuple[pd.DataFrame, pd.DataFrame] | str:
    """Separa faixa de abertura e barras seguintes, ou devolve o motivo de não operar."""
    barras = barras.sort_index()
    base = pd.Timestamp.combine(barras.index[0].date(), p.abertura)
    esperadas = [base + pd.Timedelta(minutes=p.minutos * k) for k in range(p.barras_fa)]
    if _hora(barras.index[0]) != p.abertura:
        return "abre_fora_do_horario"
    if not all(t in barras.index for t in esperadas):
        return "faixa_incompleta"
    return barras.loc[esperadas], barras[barras.index > esperadas[-1]]


def simular_dia(barras: pd.DataFrame, p: ParametrosORB) -> Operacao | str:
    """Simula um pregão. Devolve a operação ou o motivo de não operar."""
    prep = _preparar(barras, p)
    if isinstance(prep, str):
        return prep
    fa, resto = prep
    gat_c, gat_v = fa["high"].max() + p.tick, fa["low"].min() - p.tick
    for i, (ts, bar) in enumerate(resto.iterrows()):
        if _hora(ts) > p.fim_entradas:
            break
        compra, venda = bar.high >= gat_c, bar.low <= gat_v
        if not (compra or venda):
            continue
        ambigua = bool(compra and venda)
        if ambigua:  # os dois gatilhos na barra: vale o mais próximo da abertura
            compra = max(gat_c - bar.open, 0) <= max(bar.open - gat_v, 0)
        if compra:
            return _executar(resto, i, "C", max(gat_c, bar.open), ambigua, p)
        return _executar(resto, i, "V", min(gat_v, bar.open), ambigua, p)
    return "sem_gatilho"


@dataclass
class ResultadoBacktest:
    operacoes: pd.DataFrame
    sem_operacao: pd.DataFrame  # data, motivo
    parametros: ParametrosORB


def backtest_orb(
    df: pd.DataFrame,
    p: ParametrosORB | None = None,
    inicio: str | None = None,
    fim: str | None = None,
) -> ResultadoBacktest:
    """Roda a estratégia dia a dia. Pregões cortados nas pontas do arquivo são descartados."""
    p = p or ParametrosORB()
    serie, _ = remover_pregoes_incompletos(df)
    if inicio:
        serie = serie[serie.index >= pd.Timestamp(inicio)]
    if fim:
        serie = serie[serie.index < pd.Timestamp(fim) + pd.Timedelta(days=1)]
    ops, sem = [], []
    for dia, barras in serie.groupby(serie.index.normalize()):
        r = simular_dia(barras, p)
        if isinstance(r, Operacao):
            ops.append(asdict(r))
        else:
            sem.append({"data": dia.strftime("%Y-%m-%d"), "motivo": r})
    colunas = list(Operacao.__dataclass_fields__)
    return ResultadoBacktest(
        pd.DataFrame(ops, columns=colunas), pd.DataFrame(sem, columns=["data", "motivo"]), p
    )


def resumo(operacoes: pd.DataFrame) -> dict:
    """Métricas da especificação, em R$ por contrato (já com custos)."""
    if operacoes.empty:
        return {"operacoes": 0}
    r = operacoes["resultado"]
    ganhos, perdas = r[r > 0], r[r <= 0]
    curva = r.cumsum()
    drawdown = (curva - curva.cummax().clip(lower=0)).min()
    seq = maior = 0
    for v in r:
        seq = seq + 1 if v <= 0 else 0
        maior = max(maior, seq)
    por_ano = r.groupby(operacoes["data"].str[:4]).sum().round(2).to_dict()
    return {
        "operacoes": len(r),
        "resultado_brl": round(float(r.sum()), 2),
        "pontos": round(float(operacoes["pontos"].sum()), 1),
        "acerto_pct": round(100 * len(ganhos) / len(r), 1),
        "ganho_medio": round(float(ganhos.mean()), 2) if len(ganhos) else 0.0,
        "perda_media": round(float(perdas.mean()), 2) if len(perdas) else 0.0,
        "fator_lucro": round(float(ganhos.sum() / -perdas.sum()), 3) if perdas.sum() else None,
        "expectativa": round(float(r.mean()), 2),
        "maior_seq_perdas": maior,
        "drawdown_max": round(float(drawdown), 2),
        "ambiguas": int(operacoes["ambigua"].sum()),
        "por_ano": por_ano,
        "por_motivo": operacoes["motivo"].value_counts().to_dict(),
    }


def entrada_aleatoria(
    df: pd.DataFrame,
    res: ResultadoBacktest,
    sorteios: int = 1000,
    semente: int = 42,
) -> dict:
    """Comparação obrigatória: nos dias em que a estratégia operou, entra às 09:15 em direção
    sorteada, com os mesmos stop, alvo, saída e custos. Devolve o percentil da estratégia."""
    p = res.parametros
    if res.operacoes.empty:
        return {"sorteios": 0}
    serie, _ = remover_pregoes_incompletos(df)
    dias = set(res.operacoes["data"])
    resultados = []  # por dia: (resultado comprando, resultado vendendo) a mercado às 09:15
    for dia, barras in serie.groupby(serie.index.normalize()):
        if dia.strftime("%Y-%m-%d") not in dias:
            continue
        _, resto = _preparar(barras, p)
        ref = float(resto.iloc[0]["open"])
        resultados.append([_executar(resto, 0, lado, ref, False, p).resultado for lado in "CV"])
    m = np.array(resultados)
    rng = np.random.default_rng(semente)
    escolhas = rng.integers(0, 2, size=(sorteios, len(m)))
    totais = np.where(escolhas == 0, m[:, 0], m[:, 1]).sum(axis=1)
    estrategia = float(res.operacoes["resultado"].sum())
    return {
        "sorteios": sorteios,
        "estrategia_brl": round(estrategia, 2),
        "aleatorio_mediana_brl": round(float(np.median(totais)), 2),
        "aleatorio_p95_brl": round(float(np.percentile(totais, 95)), 2),
        "percentil_estrategia": round(float((totais < estrategia).mean() * 100), 1),
    }
