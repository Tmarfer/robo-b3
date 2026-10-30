"""Testes da win-orb-v1 contra a especificação (docs/estrategias/win-orb-v1.md).

Faixa de abertura de todos os cenários = a do exemplo do documento:
máxima 125.000, mínima 124.600 -> gatilho de compra 125.005, de venda 124.595.
"""

import json
from datetime import time

import pandas as pd
import pytest

from robob3.backtest import (
    Operacao,
    ParametrosORB,
    backtest_orb,
    entrada_aleatoria,
    resumo,
    simular_dia,
)

FA = {
    "09:00": (124850, 125000, 124700, 124900),
    "09:05": (124900, 124950, 124600, 124800),
    "09:10": (124800, 124980, 124650, 124900),
}
NEUTRO = 124900  # dentro da faixa e entre stop e alvo da compra do exemplo
P = ParametrosORB()  # stop 200, alvo 2x, derrapagem 5, custo R$ 0,25/lado


def _dia(data="2024-05-08", barras=None, neutro=NEUTRO, inicio="09:00", fim="18:20", fa=True):
    idx = pd.date_range(f"{data} {inicio}", f"{data} {fim}", freq="5min")
    linhas = {t: (neutro,) * 4 for t in idx}
    for hhmm, ohlc in {**(FA if fa else {}), **(barras or {})}.items():
        linhas[pd.Timestamp(f"{data} {hhmm}")] = ohlc
    df = pd.DataFrame.from_dict(linhas, orient="index", columns=["open", "high", "low", "close"])
    return df.sort_index().astype(float)


def test_exemplo_da_especificacao():
    dia = _dia(
        barras={
            "09:25": (124990, 125040, 124950, 125030),
            "10:40": (125300, 125420, 125280, 125400),
        }
    )
    op = simular_dia(dia, P)
    assert isinstance(op, Operacao)
    assert (op.lado, op.hora_entrada, op.referencia, op.entrada) == ("C", "09:25", 125005, 125010)
    assert (op.stop, op.alvo) == (124805, 125405)
    assert (op.hora_saida, op.saida, op.motivo) == ("10:40", 125405, "alvo")
    assert op.pontos == 395 and op.resultado == pytest.approx(78.50)
    assert not op.ambigua
    # sensibilidade de custo da especificação: R$ 0,50 por lado
    op2 = simular_dia(dia, ParametrosORB(custo_lado=0.50))
    assert op2.resultado == pytest.approx(78.00)


def test_exemplo_com_salto_mede_stop_e_alvo_da_abertura():
    dia = _dia(
        barras={
            "09:25": (125080, 125100, 125060, 125090),
            "10:40": (125300, 125420, 125280, 125400),
        }
    )
    op = simular_dia(dia, P)
    assert (op.referencia, op.entrada, op.stop, op.alvo) == (125080, 125085, 124880, 125480)
    # 125.420 não chega ao alvo de 125.480: sai por tempo na abertura das 17:00, com derrapagem
    assert (op.motivo, op.hora_saida, op.saida) == ("tempo", "17:00", NEUTRO - 5)
    assert op.pontos == NEUTRO - 5 - 125085


def test_stop_e_alvo_na_mesma_barra_conta_stop():
    dia = _dia(
        barras={
            "09:25": (124990, 125040, 124950, 125030),
            "10:00": (125000, 125450, 124700, 125000),
        }
    )
    op = simular_dia(dia, P)
    assert (op.motivo, op.saida, op.ambigua) == ("stop", 124805 - 5, True)


def test_entrada_e_stop_na_mesma_barra_conta_stop():
    dia = _dia(barras={"09:25": (124990, 125040, 124780, 124800)})
    op = simular_dia(dia, P)
    assert (op.hora_entrada, op.hora_saida, op.motivo, op.ambigua) == (
        "09:25",
        "09:25",
        "stop",
        True,
    )
    assert op.pontos == (124805 - 5) - 125010


def test_entrada_e_alvo_na_mesma_barra_sem_stop_conta_alvo():
    dia = _dia(barras={"09:25": (124990, 125410, 124950, 125400)})
    op = simular_dia(dia, P)
    assert (op.hora_saida, op.motivo, op.saida, op.ambigua) == ("09:25", "alvo", 125405, False)


def test_dois_gatilhos_na_mesma_barra_entra_no_mais_proximo_da_abertura():
    # abre a 125.000: compra está a 5 pontos, venda a 405 -> compra; stop dentro da barra -> stop
    dia = _dia(barras={"09:25": (125000, 125050, 124550, 124800)})
    op = simular_dia(dia, P)
    assert (op.lado, op.motivo, op.ambigua) == ("C", "stop", True)
    assert op.pontos == (124805 - 5) - 125010


def test_venda_e_salto_atraves_do_stop():
    # venda a 124.595 (entrada 124.590, stop 124.795); barra seguinte abre a 124.900, além do stop
    dia = _dia(barras={"09:30": (124650, 124660, 124580, 124590)})
    op = simular_dia(dia, P)
    assert (op.lado, op.referencia, op.entrada, op.stop, op.alvo) == (
        "V",
        124595,
        124590,
        124795,
        124195,
    )
    assert (op.hora_saida, op.motivo, op.saida) == ("09:35", "stop", NEUTRO + 5)


def test_sem_barra_das_17h_zera_no_fechamento_da_ultima():
    dia = _dia(barras={"09:25": (124990, 125040, 124950, 125030)}, fim="16:00")
    op = simular_dia(dia, P)
    assert (op.motivo, op.hora_saida, op.saida) == ("fim_do_dia", "16:00", NEUTRO - 5)


def test_dias_sem_operacao():
    cinzas = _dia(inicio="13:00", fa=False)
    assert simular_dia(cinzas, P) == "abre_fora_do_horario"
    sem_0905 = _dia().drop(pd.Timestamp("2024-05-08 09:05"))
    assert simular_dia(sem_0905, P) == "faixa_incompleta"
    assert simular_dia(_dia(), P) == "sem_gatilho"


def test_janela_de_entradas_termina_na_barra_das_11h55():
    rompe = (124990, 125040, 124950, 125030)
    assert simular_dia(_dia(barras={"12:00": rompe}), P) == "sem_gatilho"
    assert simular_dia(_dia(barras={"11:55": rompe}), P).hora_entrada == "11:55"
    p = ParametrosORB(fim_entradas=time(12, 0))
    assert simular_dia(_dia(barras={"12:00": rompe}), p).hora_entrada == "12:00"


@pytest.fixture
def quatro_dias():
    ganho = _dia(
        "2024-05-06",
        barras={
            "09:25": (124990, 125040, 124950, 125030),
            "10:40": (125300, 125420, 125280, 125400),
        },
    )
    cinzas = _dia("2024-05-07", inicio="13:00", fa=False)
    perda = _dia("2024-05-08", barras={"09:25": (124990, 125040, 124780, 124800)})
    nada = _dia("2025-05-09")
    return pd.concat([ganho, cinzas, perda, nada])


def test_backtest_e_resumo(quatro_dias):
    res = backtest_orb(quatro_dias, P)
    assert list(res.operacoes["data"]) == ["2024-05-06", "2024-05-08"]
    assert res.sem_operacao.to_dict("records") == [
        {"data": "2024-05-07", "motivo": "abre_fora_do_horario"},
        {"data": "2025-05-09", "motivo": "sem_gatilho"},
    ]
    perda = (124800 - 125010) * 0.20 - 0.50
    r = resumo(res.operacoes)
    assert r["operacoes"] == 2 and r["acerto_pct"] == 50.0
    assert r["resultado_brl"] == pytest.approx(78.50 + perda)
    assert r["fator_lucro"] == pytest.approx(78.50 / -perda, abs=1e-3)
    assert r["drawdown_max"] == pytest.approx(perda)
    assert r["maior_seq_perdas"] == 1 and r["ambiguas"] == 1
    assert r["por_ano"] == {"2024": round(78.50 + perda, 2)}


def test_backtest_respeita_periodo(quatro_dias):
    res = backtest_orb(quatro_dias, P, inicio="2024-05-07", fim="2024-05-31")
    assert list(res.operacoes["data"]) == ["2024-05-08"]


def test_entrada_aleatoria_reprodutivel(quatro_dias):
    res = backtest_orb(quatro_dias, P)
    a = entrada_aleatoria(quatro_dias, res, sorteios=200, semente=7)
    b = entrada_aleatoria(quatro_dias, res, sorteios=200, semente=7)
    assert a == b and a["sorteios"] == 200
    assert 0 <= a["percentil_estrategia"] <= 100
    assert a["estrategia_brl"] == pytest.approx(res.operacoes["resultado"].sum())


def test_cli_backtest_orb(quatro_dias, tmp_path, capsys, monkeypatch):
    from robob3.backtest import orb
    from robob3.cli import main
    from robob3.data import escrever_barras_mt5

    arq = escrever_barras_mt5(quatro_dias, tmp_path / "WIN_M5.csv")
    monkeypatch.setitem(orb.PERIODOS, "desenvolvimento", ("2024-01-01", "2025-12-31"))
    ops = tmp_path / "res" / "ops.csv"
    args = ["backtest-orb", str(arq), "--aleatorio", "50", "--operacoes", str(ops)]
    assert main([*args, "--manifesto", ""]) == 0
    out = capsys.readouterr().out
    assert '"operacoes": 2' in out and '"entrada_aleatoria"' in out and ops.exists()
    assert "manifesto:" not in out

    monkeypatch.setenv("ROBOB3_COMMIT", "a" * 40)
    monkeypatch.setenv("ROBOB3_ALTERADO", "0")
    pasta = tmp_path / "manifestos"
    grade = ["backtest-orb", str(arq), "--grade", "--aleatorio", "20", "--manifesto", str(pasta)]
    assert main(grade) == 0
    out = capsys.readouterr().out
    assert out.count("\n150,") == 3 and "200,2,2," in out

    # manifesto: uma linha por combinação, com tudo o que é preciso para refazer a rodada
    (arquivo,) = pasta.glob("win-orb-v1_desenvolvimento_conservadora_*.json")
    m = json.loads(arquivo.read_text())
    assert m["codigo"] == {"commit": "a" * 40, "codigo_alterado": False}
    assert m["dados"]["arquivo"] == "WIN_M5.csv" and len(m["dados"]["sha256"]) == 64
    assert m["custos"] == {
        "custo_lado_brl": 0.25,
        "sensibilidade_custo_lado_brl": 0.5,
        "derrapagem_pts": 5.0,
        "valor_ponto_brl": 0.2,
    }
    assert (m["trecho"], m["ativo"], m["timeframe"], m["ambiguidade"]) == (
        "desenvolvimento",
        "WIN$N",
        "M5",
        "conservadora",
    )
    assert m["entrada_aleatoria"] == {"sorteios": 20, "semente": 42}
    assert [(x["parametros"]["stop"], x["parametros"]["alvo"]) for x in m["linhas"]] == [
        (s, a) for s in (150, 200, 300) for a in (1.5, 2.0, 3.0)
    ]
    linha = m["linhas"][4]  # stop 200, alvo 2x
    assert linha["operacoes"] == 2 and "percentil_estrategia" in linha["entrada_aleatoria"]
    assert {"expectativa", "acerto_pct", "ambiguas", "resultado_custo_0.50"} <= set(linha)
    assert m["comando"][:3] == ["robob3", "backtest-orb", str(arq)]

    # fora da amostra exige confirmação explícita
    assert main(["backtest-orb", str(arq), "--periodo", "fora-da-amostra"]) == 2


def test_modo_otimista_resolve_barras_ambiguas_a_favor():
    otim = ParametrosORB(ambiguidade="otimista")
    # entrada e stop na mesma barra: otimista ignora o stop dessa barra e segue
    dia = _dia(
        barras={
            "09:25": (124990, 125040, 124780, 124800),
            "10:40": (125300, 125420, 125280, 125400),
        }
    )
    assert simular_dia(dia, P).motivo == "stop"
    op = simular_dia(dia, otim)
    assert (op.motivo, op.saida, op.ambigua) == ("alvo", 125405, True)
    # stop e alvo na mesma barra posterior: otimista conta alvo
    dia = _dia(
        barras={
            "09:25": (124990, 125040, 124950, 125030),
            "10:00": (125000, 125450, 124700, 125000),
        }
    )
    assert (simular_dia(dia, otim).motivo, simular_dia(dia, P).motivo) == ("alvo", "stop")
    # barra sem ambiguidade: os dois modos dão o mesmo resultado
    dia = _dia(
        barras={
            "09:25": (124990, 125040, 124950, 125030),
            "10:40": (125300, 125420, 125280, 125400),
        }
    )
    assert simular_dia(dia, otim) == simular_dia(dia, P)
