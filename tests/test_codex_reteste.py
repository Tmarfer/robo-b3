import pandas as pd

from robob3.backtest.codex_reteste import buscar_sinal, executar_trade


def test_compra_somente_depois_de_duas_barras_e_reteste():
    idx = pd.date_range("2025-01-02 09:00", periods=3, freq="15min")
    d = pd.DataFrame(
        {
            "open": [100, 105, 110],
            "high": [110, 115, 112],
            "low": [101, 102, 95],
            "close": [105, 110, 105],
            "ema20": [100, 101, 102],
        },
        index=idx,
    )
    assert buscar_sinal(d, 100, 50) == (pd.Timestamp("2025-01-02 09:45"), 1)
    assert buscar_sinal(d.iloc[:2], 100, 50) is None
    d.loc[idx[2], "ema20"] = 99
    assert buscar_sinal(d, 100, 50) is None


def test_stop_prevalece_na_barra_ambigua_e_entrada_e_proxima_barra():
    idx = pd.to_datetime(["2025-01-02 09:45", "2025-01-02 17:00"])
    d = pd.DataFrame(
        {"open": [1000, 1000], "high": [1700, 1000], "low": [700, 1000], "close": [1000, 1000]},
        index=idx,
    )
    op = executar_trade(d, idx[0], 1, 1000)
    assert op["entrada"] == 1005 and op["saida"] == 700
    assert op["resultado_brl"] == -61.5
    assert op["motivo"] == "stop" and op["ambigua"]


def test_gap_de_stop_usa_abertura_com_derrapagem():
    idx = pd.to_datetime(["2025-01-02 09:45", "2025-01-02 09:50", "2025-01-02 17:00"])
    d = pd.DataFrame(
        {
            "open": [1000, 650, 1000],
            "high": [1010, 660, 1000],
            "low": [990, 640, 1000],
            "close": [1000, 650, 1000],
        },
        index=idx,
    )
    op = executar_trade(d, idx[0], 1, 1000)
    assert op["motivo"] == "stop" and op["saida"] == 645
