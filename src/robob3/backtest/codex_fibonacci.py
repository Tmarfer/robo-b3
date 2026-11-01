"""Adaptações exploratórias de três fichas Fibonacci; sinais causais em M15."""

import hashlib
import itertools
import json
import math
from pathlib import Path

import pandas as pd
import yaml

from robob3.backtest.codex_fichas import fechar, reamostrar_completas
from robob3.backtest.codex_fichas_trailing import mover_stop
from robob3.backtest.manifesto import commit_atual, gravar_manifesto, montar_manifesto
from robob3.data.mt5_csv import ler_barras_mt5

ARQUIVO = Path("data/raw/WIN-N_M5_clear-mt5_20261030.csv")
ESTRATEGIAS = ("fibogap", "pivo-123-fibo", "fibo-duas-etapas")


class Ziguezague:
    """Pivôs confirmados causalmente por uma reversão de fechamentos."""

    def __init__(self, distancia=300):
        self.distancia = distancia
        self.modo = 0
        self.minimo = self.maximo = None
        self.pivos = []

    def atualizar(self, ts, preco):
        preco = int(preco)
        if self.minimo is None:
            self.minimo = self.maximo = (preco, ts)
            return None
        if self.modo == 0:
            if preco < self.minimo[0]:
                self.minimo = (preco, ts)
            if preco > self.maximo[0]:
                self.maximo = (preco, ts)
            if preco - self.minimo[0] >= self.distancia:
                self.modo = 1
                extremo, tipo = self.minimo, "fundo"
                self.maximo = (preco, ts)
            elif self.maximo[0] - preco >= self.distancia:
                self.modo = -1
                extremo, tipo = self.maximo, "topo"
                self.minimo = (preco, ts)
            else:
                return None
        elif self.modo == 1:
            if preco > self.maximo[0]:
                self.maximo = (preco, ts)
            if self.maximo[0] - preco < self.distancia:
                return None
            extremo, tipo = self.maximo, "topo"
            self.modo, self.minimo = -1, (preco, ts)
        else:
            if preco < self.minimo[0]:
                self.minimo = (preco, ts)
            if preco - self.minimo[0] < self.distancia:
                return None
            extremo, tipo = self.minimo, "fundo"
            self.modo, self.maximo = 1, (preco, ts)
        pivo = {"tipo": tipo, "preco": extremo[0], "extremo_em": extremo[1], "confirmado_em": ts}
        self.pivos.append(pivo)
        return pivo


def cluster(pivos):
    """Escolhe a menor faixa de três projeções apenas com pivôs já confirmados."""
    if len(pivos) < 4:
        return None
    a, b, c, d = pivos[-4:]
    if [p["tipo"] for p in (a, b, c, d)] == ["fundo", "topo", "fundo", "topo"]:
        lado = 1
    elif [p["tipo"] for p in (a, b, c, d)] == ["topo", "fundo", "topo", "fundo"]:
        lado = -1
    else:
        return None
    av, bv, cv, dv = (p["preco"] * lado for p in (a, b, c, d))
    if not (av < cv < dv < bv):
        return None
    retracoes = [bv - r * (bv - av) for r in (0.382, 0.5, 0.618, 0.786)]
    extensoes = [dv - k * (dv - cv) for k in (1.272, 1.618)]
    projecao = dv - (bv - cv)
    faixa = min(
        ((max(t) - min(t), t) for t in itertools.product(retracoes, extensoes, [projecao])),
        key=lambda x: x[0],
    )
    largura, valores = faixa
    if largura > 100:
        return None
    pontos = [v * lado for v in valores]
    return {
        "lado": lado,
        "inferior": min(pontos),
        "superior": max(pontos),
        "centro": sum(pontos) / 3,
        "b": b["preco"],
        "confirmado_em": d["confirmado_em"],
    }


def fibogap(barras, anterior):
    if len(barras) < 5 or anterior is None:
        return
    primeira = barras.iloc[:4]
    if list(primeira.index.strftime("%H:%M")) != ["09:00", "09:15", "09:30", "09:45"]:
        return
    ab = float(primeira.iloc[0]["open"])
    if ab > anterior.high:
        a, b = float(anterior.low), float(primeira.high.max())
    elif ab < anterior.low:
        a, b = float(anterior.high), float(primeira.low.min())
    else:
        return
    low, high = sorted((a, b))
    amp = high - low
    if amp <= 0:
        return
    inferior, superior = low + 0.236 * amp, low + 0.764 * amp
    regs = list(barras.itertuples())
    for i in range(5, len(regs)):
        teste, atual = regs[i - 1], regs[i]
        if atual.Index.time() > pd.Timestamp("16:30").time():
            break
        if (atual.Index - teste.Index).total_seconds() != 900:
            continue
        compra = (
            teste.low <= low
            and teste.low >= low - 0.118 * amp
            and atual.low >= teste.low
            and atual.close > inferior
        )
        venda = (
            teste.high >= high
            and teste.high <= high + 0.118 * amp
            and atual.high <= teste.high
            and atual.close < superior
        )
        if compra == venda:
            continue
        yield {
            "sinal_em": atual.Index,
            "lado": 1 if compra else -1,
            "stop": teste.low - 5 if compra else teste.high + 5,
            "alvo": superior if compra else inferior,
            "nivel": inferior if compra else superior,
        }


def sinais_pivo(barras):
    zig = Ziguezague()
    descartados = set()
    for b in barras.itertuples():
        if b.Index.time() > pd.Timestamp("16:30").time():
            break
        zig.atualizar(b.Index, b.close)
        if len(zig.pivos) < 3:
            continue
        a, p2, c = zig.pivos[-3:]
        tipos = [p["tipo"] for p in (a, p2, c)]
        lado = (
            1
            if tipos == ["fundo", "topo", "fundo"]
            else (-1 if tipos == ["topo", "fundo", "topo"] else 0)
        )
        if not lado:
            continue
        av, bv, cv = a["preco"] * lado, p2["preco"] * lado, c["preco"] * lado
        chave = tuple((p["tipo"], p["extremo_em"]) for p in (a, p2, c))
        if chave in descartados or not av < cv < bv:
            continue
        if b.close * lado < av:
            descartados.add(chave)
        elif b.close * lado > bv:
            descartados.add(chave)
            yield {
                "sinal_em": b.Index,
                "lado": lado,
                "stop": c["preco"] - lado * 5,
                "alvo": p2["preco"] + lado * 0.618 * (bv - av),
                "nivel": p2["preco"],
            }


def sinais_duas(barras):
    zig = Ziguezague()
    zona = None
    for b in barras.itertuples():
        if b.Index.time() > pd.Timestamp("16:30").time():
            break
        novo = zig.atualizar(b.Index, b.close)
        if novo:
            zona = cluster(zig.pivos)
        if zona is None or b.Index <= zona["confirmado_em"]:
            continue
        lado = zona["lado"]
        toca = b.low <= zona["superior"] and b.high >= zona["inferior"]
        confirma = b.close > zona["superior"] if lado == 1 else b.close < zona["inferior"]
        if toca and confirma:
            stop = zona["inferior"] - 5 if lado == 1 else zona["superior"] + 5
            alvo = zona["centro"] + lado * 1.272 * abs(zona["b"] - zona["centro"])
            yield {
                "sinal_em": b.Index,
                "lado": lado,
                "stop": stop,
                "alvo": alvo,
                "nivel": zona["centro"],
            }
            zona = None


def arredondar(n, lado, tipo):
    """Stop para fora e alvo para dentro; todos os preços precisam respeitar tick."""
    para_cima = (tipo == "stop" and lado == -1) or (tipo == "alvo" and lado == -1)
    return int((math.ceil(n / 5) if para_cima else math.floor(n / 5)) * 5)


def preparar_entrada(setup, hoje):
    timestamp = setup["sinal_em"] + pd.Timedelta(minutes=15)
    if timestamp.time() > pd.Timestamp("16:45").time() or timestamp not in hoje.index:
        return None
    lado = setup["lado"]
    abertura = int(hoje.loc[timestamp, "open"])
    entrada = abertura + lado * 5
    stop = arredondar(setup["stop"], lado, "stop")
    alvo = arredondar(setup["alvo"], lado, "alvo")
    if (
        (abertura - stop) * lado <= 0
        or (alvo - abertura) * lado <= 0
        or (entrada - stop) * lado <= 0
        or (alvo - entrada) * lado <= 0
    ):
        return None
    return {
        "data": str(timestamp.date()),
        "lado": lado,
        "entrada_em": str(timestamp),
        "entrada": entrada,
        "stop": stop,
        "stop_atual": stop,
        "alvo": alvo,
        "nivel": round(setup["nivel"], 2),
        "sinal_em": str(setup["sinal_em"]),
        "trailing_ativado": False,
        "movimentos_stop": [{"t": str(timestamp), "preco": stop}],
    }


def saida(hoje, entrada, modo):
    pos = dict(entrada)
    pos["movimentos_stop"] = [x.copy() for x in entrada["movimentos_stop"]]
    if modo == "trailing":
        pos["alvo"] = None
    ops = []
    lado = pos["lado"]
    for ts, b in hoje.loc[pd.Timestamp(pos["entrada_em"]) :].iterrows():

        class Barra:
            Index = ts

        barra = Barra()
        abertura = int(b.open)
        if ts.time() == pd.Timestamp("17:00").time():
            fechar(pos, barra, abertura - lado * 5, "tempo", ops)
            break
        stop = pos["stop_atual"]
        favoravel = int(b.high if lado == 1 else b.low)
        adverso = int(b.low if lado == 1 else b.high)
        if (abertura - stop) * lado <= 0:
            fechar(pos, barra, abertura - lado * 5, "stop", ops)
            break
        if modo == "padrao":
            alvo = pos["alvo"]
            bate_stop = (adverso - stop) * lado <= 0
            bate_alvo = (favoravel - alvo) * lado >= 0
            if (abertura - alvo) * lado >= 0:
                fechar(pos, barra, abertura, "alvo", ops)
                break
            if bate_stop:
                fechar(pos, barra, stop - lado * 5, "stop", ops, ambigua=bool(bate_alvo))
                break
            if bate_alvo:
                fechar(pos, barra, alvo, "alvo", ops)
                break
        else:
            mover_stop(pos, abertura, ts)
            stop = pos["stop_atual"]
            candidato = favoravel - lado * 150
            melhora = (favoravel - pos["entrada"]) * lado >= 300 and (candidato - stop) * lado > 0
            if (adverso - stop) * lado <= 0:
                fechar(pos, barra, stop - lado * 5, "stop", ops, ambigua=bool(melhora))
                break
            if melhora:
                if (adverso - candidato) * lado <= 0:
                    protecao = pos["entrada"] + lado * 150
                    pior = (
                        max(stop, protecao, adverso) if lado == 1 else min(stop, protecao, adverso)
                    )
                    pos["stop_atual"] = pior
                    pos["trailing_ativado"] = True
                    pos["movimentos_stop"].append({"t": str(ts), "preco": pior})
                    fechar(pos, barra, pior - lado * 5, "stop", ops, ambigua=True)
                    break
                mover_stop(pos, favoravel, ts)
    if not ops:
        raise ValueError("Saída às 17h ausente")
    return ops[0]


def resumo(ops, modo):
    total = pico = dd = 0.0
    anos = {}
    for o in ops:
        total += o["resultado_brl"]
        pico = max(pico, total)
        dd = min(dd, total - pico)
        ano = o["data"][:4]
        anos[ano] = round(anos.get(ano, 0) + o["resultado_brl"], 2)
    ganhos = sum(max(0, o["resultado_brl"]) for o in ops)
    perdas = -sum(min(0, o["resultado_brl"]) for o in ops)
    return {
        "versao_saida": modo,
        "timeframe": "M5",
        "sinal": "M15",
        "operacoes": len(ops),
        "resultado_brl": round(total, 2),
        "por_ano": anos,
        "drawdown_max": round(dd, 2),
        "fator_lucro": round(ganhos / perdas, 3) if perdas else None,
        "acerto_pct": round(sum(o["resultado_brl"] > 0 for o in ops) * 100 / len(ops), 2)
        if ops
        else None,
        "ambiguas": sum(bool(o["ambigua"]) for o in ops),
        "por_motivo": {m: sum(o["motivo"] == m for o in ops) for m in ("alvo", "stop", "tempo")},
    }


def simular(df, rolagens, estrategia, inicio, fim):
    m15 = reamostrar_completas(df, 15, 5)
    dias = {str(d): g for d, g in df.groupby(df.index.date)}
    dias15 = {str(d): g for d, g in m15.groupby(m15.index.date)}
    ordenados = sorted(dias)
    rolls = {str(x) for x in rolagens}
    saidas = {"padrao": [], "trailing": []}
    estatisticas = {"rolagem": 0, "pregao_incompleto": 0, "sem_entrada": 0}
    for i in range(1, len(ordenados)):
        dia = ordenados[i]
        if not inicio <= dia <= fim:
            continue
        if dia in rolls:
            estatisticas["rolagem"] += 1
            continue
        hoje = dias[dia]
        if (
            dia not in dias15
            or hoje.index[0].strftime("%H:%M") != "09:00"
            or not any(hoje.index.strftime("%H:%M") == "17:00")
        ):
            estatisticas["pregao_incompleto"] += 1
            continue
        barras = dias15[dia]
        if list(barras.index[:4].strftime("%H:%M")) != ["09:00", "09:15", "09:30", "09:45"]:
            estatisticas["pregao_incompleto"] += 1
            continue
        if estrategia == "fibogap":
            ant = dias15.get(ordenados[i - 1])
            candidatos = fibogap(
                barras,
                next(ant.iloc[-1:].itertuples(), None) if ant is not None and len(ant) else None,
            )
        elif estrategia == "pivo-123-fibo":
            candidatos = sinais_pivo(barras)
        elif estrategia == "fibo-duas-etapas":
            candidatos = sinais_duas(barras)
        elif estrategia == "retracao-38-50":
            from robob3.backtest.codex_retracao import sinais_retracao

            candidatos = sinais_retracao(barras)
        else:
            raise ValueError("Estratégia desconhecida")
        entrada = None
        for c in candidatos:
            entrada = preparar_entrada(c, hoje)
            if entrada:
                break
        if entrada is None:
            estatisticas["sem_entrada"] += 1
            continue
        for modo in saidas:
            saidas[modo].append(saida(hoje, entrada, modo))
    return saidas, estatisticas


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
    for nome in ESTRATEGIAS:
        for periodo, inicio, fim in janelas:
            ops, exclusoes = simular(df, rolagens, nome, inicio, fim)
            linhas = [resumo(ops[modo], modo) for modo in ("padrao", "trailing")]
            manifesto = montar_manifesto(
                estrategia=f"codex-{nome}-v1",
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
                comando=["robob3", "backtest-codex-fibonacci", "--confirmo-fora-da-amostra"],
            )
            destino = gravar_manifesto(manifesto, "data/backtests")
            grupo = {
                "estrategia": nome,
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
                json.dumps(
                    {k: v for k, v in grupo.items() if k != "operacoes"}, ensure_ascii=False
                ),
                flush=True,
            )
    Path("testes-codex/resultado-fibonacci.json").write_text(
        json.dumps(resultados, ensure_ascii=False), encoding="utf-8"
    )
