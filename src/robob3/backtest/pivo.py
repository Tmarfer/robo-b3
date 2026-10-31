"""Backtest da estratégia win-pivo-v1 (docs/estrategias/win-pivo-v1.md): reversão nos extremos do
pregão anterior ("Sneaky Pivot"). Sinal em barras M15 montadas do M5; execução no M5.

Implementa a especificação congelada em 31/10/2026. Qualquer mudança de regra é uma nova versão
da estratégia, não um ajuste aqui.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, time

import numpy as np
import pandas as pd

from robob3.backtest.orb import Operacao, ResultadoBacktest, _saida
from robob3.data.sessions import remover_pregoes_incompletos


@dataclass(frozen=True)
class ParametrosPivo:
    alvo: float = 1.0  # fração do caminho da entrada até a borda oposta da faixa anterior
    tol: float = 0.10  # tolerância, em fração da amplitude do pregão anterior
    tick: float = 5.0
    derrapagem: float = 5.0  # pontos contra, em entradas, stops e saída por tempo
    custo_lado: float = 0.25  # R$ por contrato por lado
    valor_ponto: float = 0.20  # R$ por ponto por contrato
    abertura: time = time(9, 0)
    barras_pivo: int = 2  # barras M15 de cada lado para um topo/fundo
    pregoes_busca: int = 10  # pregões anteriores (mesmo contrato) onde procurar o swing
    saida_tempo: time = time(17, 0)
    # "conservadora" = regra da especificação; "otimista" = só diagnóstico (ambíguas a favor)
    ambiguidade: str = "conservadora"


@dataclass(frozen=True)
class Setup:
    lado: str  # "C" ou "V"
    gatilho: float
    stop: float
    borda: float  # extremo oposto da faixa anterior (RH na compra, RL na venda)


def _m15(barras: pd.DataFrame) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return barras.resample("15min").agg(agg).dropna()


def _arred(x: float, tick: float) -> float:
    return round(x / tick) * tick


def pivos(m15: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    """Topos e fundos: máxima (mínima) maior (menor) que as das `n` barras de cada lado.
    As últimas `n` barras não podem ser pivô (faltam vizinhas à direita)."""
    h, low = m15["high"].to_numpy(), m15["low"].to_numpy()
    topos, fundos = [], []
    for j in range(n, len(m15) - n):
        viz = np.r_[j - n : j, j + 1 : j + n + 1]
        if h[j] > h[viz].max():
            topos.append(j)
        if low[j] < low[viz].min():
            fundos.append(j)
    return m15["high"].iloc[topos], m15["low"].iloc[fundos]


def niveis(historico: pd.DataFrame, p: ParametrosPivo) -> dict | None:
    """RH, RL, SH, SL e T a partir dos pregões anteriores (o último é o pregão anterior).
    `historico` já vem restrito ao contrato atual e aos `pregoes_busca` últimos pregões."""
    if historico.empty:
        return None
    ultimo = historico.index[-1].normalize()
    anterior = historico[historico.index >= ultimo]
    rh, rl = float(anterior["high"].max()), float(anterior["low"].min())
    topos, fundos = pivos(_m15(historico), p.barras_pivo)
    acima, abaixo = topos[topos > rh], fundos[fundos < rl]
    return {
        "RH": rh,
        "RL": rl,
        "SH": float(acima.iloc[-1]) if len(acima) else None,  # o mais recente
        "SL": float(abaixo.iloc[-1]) if len(abaixo) else None,
        "T": _arred(p.tol * (rh - rl), p.tick),
    }


def setups(b1, b2, nv: dict, p: ParametrosPivo) -> list[Setup]:
    """Setups armados depois de B1 e B2 (barras M15 das 09:00 e 09:15)."""
    out, t = [], nv["T"]
    if nv["SL"] is not None:
        piso = nv["SL"] - t
        if (
            b1.open > piso
            and min(b1.low, b2.low) <= nv["RL"] + t
            and b1.close >= piso
            and b2.close >= piso
        ):
            out.append(Setup("C", b2.high + p.tick, min(b1.low, b2.low) - p.tick, nv["RH"]))
    if nv["SH"] is not None:
        teto = nv["SH"] + t
        if (
            b1.open < teto
            and max(b1.high, b2.high) >= nv["RH"] - t
            and b1.close <= teto
            and b2.close <= teto
        ):
            out.append(Setup("V", b2.low - p.tick, max(b1.high, b2.high) + p.tick, nv["RL"]))
    return out


def _executar(
    m5: pd.DataFrame, i: int, lado: str, ref: float, stop: float, alvo: float, p: ParametrosPivo
) -> Operacao:
    """Entrada na barra `i` de `m5` com preço de referência `ref`, stop e alvo dados."""
    d = p.derrapagem
    ts, bar = m5.index[i], m5.iloc[i]
    entrada = ref + d if lado == "C" else ref - d
    if lado == "C":
        bate_stop, bate_alvo = bar.low <= stop, bar.high >= alvo
    else:
        bate_stop, bate_alvo = bar.high >= stop, bar.low <= alvo
    otimista, ambigua = p.ambiguidade == "otimista", False
    if otimista and bate_stop:  # diagnóstico: o extremo teria vindo antes da entrada
        ambigua, bate_stop = True, False
    if bate_stop:  # entrada e stop na mesma barra: considera stop
        fim = (stop - d if lado == "C" else stop + d), "stop", True, ts
    elif bate_alvo:  # para chegar ao alvo o preço passa antes pela entrada, do mesmo lado
        fim = alvo, "alvo", ambigua, ts
    else:
        fim = None
        for ts2, bar2 in m5.iloc[i + 1 :].iterrows():
            if ts2.time() >= p.saida_tempo:
                fim = (bar2.open - d if lado == "C" else bar2.open + d), "tempo", ambigua, ts2
                break
            r = _saida(lado, bar2, stop, alvo, d, otimista)
            if r:
                fim = r[0], r[1], ambigua or r[2], ts2
                break
        if fim is None:  # pregão acabou antes das 17:00
            ult_ts, ult = m5.index[-1], m5.iloc[-1]
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


def _alvo(lado: str, ref: float, borda: float, p: ParametrosPivo) -> float | None:
    caminho = borda - ref if lado == "C" else ref - borda
    if caminho <= 0:  # entrada já além da borda oposta: sem alvo possível
        return None
    return _arred(ref + p.alvo * caminho if lado == "C" else ref - p.alvo * caminho, p.tick)


def simular_dia(barras: pd.DataFrame, historico: pd.DataFrame, p: ParametrosPivo) -> Operacao | str:
    """Simula um pregão (barras M5) dado o histórico dos pregões anteriores do mesmo contrato."""
    base = pd.Timestamp.combine(barras.index[0].date(), p.abertura)
    if barras.index[0] != base:
        return "abre_fora_do_horario"
    esperadas = [base + pd.Timedelta(minutes=5 * k) for k in range(9)]  # B1-B3 completas
    if not all(t in barras.index for t in esperadas):
        return "barras_incompletas"
    nv = niveis(historico, p)
    if nv is None:
        return "sem_historico"
    m15 = _m15(barras.loc[esperadas[0] : esperadas[5]])
    b1, b2 = m15.iloc[0], m15.iloc[1]
    armados = setups(b1, b2, nv, p)
    if not armados:
        return "sem_setup"

    resto = barras[barras.index >= esperadas[6]]  # da barra M5 das 09:30 em diante
    vivos = list(armados)
    for i in range(3):  # as três barras M5 de B3 (09:30, 09:35, 09:40)
        bar = resto.iloc[i]
        disparados = []
        for s in list(vivos):
            if s.lado == "C":
                gat, perdeu = bar.high >= s.gatilho, bar.low <= s.stop
            else:
                gat, perdeu = bar.low <= s.gatilho, bar.high >= s.stop
            if gat:
                disparados.append(s)
            elif perdeu:  # foi ao stop antes de disparar: setup cancelado
                vivos.remove(s)
        if disparados:
            # dois disparos na mesma barra: vale o gatilho mais próximo da abertura
            s = min(disparados, key=lambda x: abs(x.gatilho - bar.open))
            ref = max(s.gatilho, bar.open) if s.lado == "C" else min(s.gatilho, bar.open)
            alvo = _alvo(s.lado, ref, s.borda, p)
            if alvo is None:
                return f"sem_alvo ({s.lado})"
            return _executar(resto, i, s.lado, ref, s.stop, alvo, p)
        if not vivos:
            return f"cancelado ({'+'.join(x.lado for x in armados)})"
    return f"sem_gatilho ({'+'.join(x.lado for x in vivos)})"


def _janelas(serie: pd.DataFrame, rolagens: list[date], p: ParametrosPivo):
    """Para cada pregão: (dia, (barras do dia, histórico do mesmo contrato), None) ou
    (dia, None, motivo de pular)."""
    grupos = dict(list(serie.groupby(serie.index.normalize())))
    dias = sorted(grupos)
    trocas = sorted(pd.Timestamp(d) for d in rolagens)
    for k, dia in enumerate(dias):
        troca = max((t for t in trocas if t <= dia), default=None)
        if troca is not None and dia == troca:
            yield dia, None, "rolagem"  # o pregão anterior é de outro contrato
            continue
        anteriores = [
            d for d in dias[max(0, k - p.pregoes_busca) : k] if troca is None or d >= troca
        ]
        if not anteriores:
            yield dia, None, "sem_historico"
            continue
        yield dia, (grupos[dia], pd.concat(grupos[d] for d in anteriores)), None


def backtest_pivo(
    df: pd.DataFrame,
    p: ParametrosPivo | None = None,
    inicio: str | None = None,
    fim: str | None = None,
    rolagens: list[date] | None = None,
) -> ResultadoBacktest:
    """Roda a estratégia dia a dia no período; o histórico anterior a `inicio` é usado só para as
    linhas de referência. Pregões cortados nas pontas do arquivo são descartados."""
    p = p or ParametrosPivo()
    serie, _ = remover_pregoes_incompletos(df)
    ini = pd.Timestamp(inicio) if inicio else None
    fim_ = pd.Timestamp(fim) if fim else None
    ops, sem = [], []
    for dia, dados, motivo in _janelas(serie, rolagens or [], p):
        if (ini is not None and dia < ini) or (fim_ is not None and dia > fim_):
            continue
        r = motivo or simular_dia(dados[0], dados[1], p)
        if isinstance(r, Operacao):
            ops.append(asdict(r))
        else:
            sem.append({"data": dia.strftime("%Y-%m-%d"), "motivo": r})
    colunas = list(Operacao.__dataclass_fields__)
    return ResultadoBacktest(
        pd.DataFrame(ops, columns=colunas), pd.DataFrame(sem, columns=["data", "motivo"]), p
    )


def entrada_aleatoria_pivo(
    df: pd.DataFrame, res: ResultadoBacktest, sorteios: int = 1000, semente: int = 42
) -> dict:
    """Comparação obrigatória: nos dias operados, mesma barra e preço de entrada, direção sorteada,
    mesmas distâncias de stop e alvo. Devolve o percentil da estratégia."""
    p = res.parametros
    if res.operacoes.empty:
        return {"sorteios": 0}
    serie, _ = remover_pregoes_incompletos(df)
    grupos = dict(list(serie.groupby(serie.index.normalize())))
    resultados = []
    for op in res.operacoes.itertuples():
        barras = grupos[pd.Timestamp(op.data)]
        i = list(barras.index.strftime("%H:%M")).index(op.hora_entrada)
        d_stop, d_alvo = abs(op.referencia - op.stop), abs(op.alvo - op.referencia)
        ref = op.referencia
        compra = _executar(barras, i, "C", ref, ref - d_stop, ref + d_alvo, p).resultado
        venda = _executar(barras, i, "V", ref, ref + d_stop, ref - d_alvo, p).resultado
        resultados.append([compra, venda])
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
