import pandas as pd

from robob3.backtest.codex_fichas_trailing import mover_stop, simular


def test_trailing_ativa_a_300_e_nunca_recua():
    pos = {
        "lado": 1,
        "entrada": 1000,
        "stop_atual": 700,
        "trailing_ativado": False,
        "movimentos_stop": [],
    }
    assert not mover_stop(pos, 1295, "2025-01-02 09:00")
    assert pos["stop_atual"] == 700
    assert mover_stop(pos, 1300, "2025-01-02 09:05")
    assert pos["stop_atual"] == 1150
    assert mover_stop(pos, 1400, "2025-01-02 09:10")
    assert pos["stop_atual"] == 1250
    assert not mover_stop(pos, 1350, "2025-01-02 09:15")
    assert pos["stop_atual"] == 1250


def barras(low):
    idx = pd.date_range("2025-01-02 09:00", periods=3, freq="5min")
    return pd.DataFrame(
        {
            "open": [1000, 1000, 1000],
            "high": [1010, 1400, 1000],
            "low": [990, low, 1000],
            "close": [1000, 1100, 1000],
        },
        index=idx,
    )


def test_stop_vigente_tem_precedencia_na_barra_ambigua(monkeypatch):
    d = barras(700)
    monkeypatch.setattr(
        "robob3.backtest.codex_fichas_trailing.sinais",
        lambda *args: pd.Series([1, 0, 0], index=d.index),
    )
    op = simular(d, "medias-5-20", 5, [], "2025-01-02", "2025-01-02")[0]
    assert op["tipo_stop"] == "inicial" and op["ambigua"]
    assert op["resultado_brl"] == -61.5


def test_ativacao_e_reversao_na_barra_usam_hipotese_adversa(monkeypatch):
    d = barras(900)
    monkeypatch.setattr(
        "robob3.backtest.codex_fichas_trailing.sinais",
        lambda *args: pd.Series([1, 0, 0], index=d.index),
    )
    op = simular(d, "medias-5-20", 5, [], "2025-01-02", "2025-01-02")[0]
    assert op["tipo_stop"] == "móvel" and op["ambigua"]
    assert op["stop_atual"] == 1155 and op["resultado_brl"] == 28.5


def test_stop_de_venda_acompanha_para_baixo():
    pos = {
        "lado": -1,
        "entrada": 1000,
        "stop_atual": 1300,
        "trailing_ativado": False,
        "movimentos_stop": [],
    }
    assert mover_stop(pos, 700, "2025-01-02 09:00")
    assert pos["stop_atual"] == 850
    assert mover_stop(pos, 600, "2025-01-02 09:05")
    assert pos["stop_atual"] == 750
    assert not mover_stop(pos, 650, "2025-01-02 09:10")
