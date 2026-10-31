import pandas as pd
import pytest

from robob3.backtest.codex_falso import atualizar, passos, simular


def dados(rows):
    return pd.DataFrame(
        rows,
        columns=["open", "high", "low", "close"],
        index=pd.date_range("2026-02-11 09:00", periods=len(rows), freq="1min"),
    )


def test_stop_movel_so_ativa_apos_quatro_ticks():
    pos = {
        "lado": 1,
        "entrada": 100,
        "stop_atual": 85,
        "trailing_ativado": False,
        "movimentos_stop": [],
    }
    atualizar(pos, 115, "2026-02-11 09:00")
    assert pos["stop_atual"] == 85
    atualizar(pos, 120, "2026-02-11 09:01")
    assert pos["stop_atual"] == 110
    atualizar(pos, 135, "2026-02-11 09:02")
    assert pos["stop_atual"] == 125
    atualizar(pos, 125, "2026-02-11 09:03")
    assert pos["stop_atual"] == 125


def test_venda_retorna_pela_maxima_e_stop_movel_protege_ganho():
    d = dados([(100, 110, 90, 100), (100, 120, 95, 100), (100, 100, 70, 90)])
    ops = simular(d, 3, "maxima-primeiro")
    assert len(ops) == 1
    op = ops[0]
    assert (op["lado"], op["gatilho"], op["entrada"], op["stop"]) == (-1, 105, 100, 115)
    assert op["motivo"] == "stop móvel"
    assert op["stop_atual"] == 80
    assert op["saida"] == 85
    assert op["resultado_brl"] == 2.5


def test_sequencias_hipoteticas_podem_resultar_em_operacoes_diferentes():
    d = dados([(100, 110, 90, 100), (100, 120, 80, 100), (100, 100, 95, 100)])
    alta = simular(d, 3, "maxima-primeiro")
    baixa = simular(d, 3, "minima-primeiro")
    assert alta[0]["lado"] == -1
    assert baixa[0]["lado"] == 1


def test_precos_precisam_respeitar_tick():
    with pytest.raises(ValueError, match="tick"):
        list(passos(100, 103))
