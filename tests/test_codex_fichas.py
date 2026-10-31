import pandas as pd

from robob3.backtest.codex_fichas import reamostrar_completas, simular, sinais


def test_sinais_nao_mudam_quando_barras_futuras_sao_acrescentadas():
    indice = pd.date_range("2025-01-02 09:00", periods=100, freq="5min")
    fechamento = [1000 + (i % 21 - 10) ** 2 for i in range(100)]
    d = pd.DataFrame(
        {
            "open": fechamento,
            "high": [v + 10 for v in fechamento],
            "low": [v - 10 for v in fechamento],
            "close": fechamento,
        },
        index=indice,
    )
    for nome in ("medias-5-20", "macd-12-26-9", "estocastico-14-3-3"):
        esperado = sinais(d.iloc[:70], nome, [])
        pd.testing.assert_series_equal(esperado, sinais(d, nome, []).iloc[:70])


def test_barra_incompleta_nao_vira_candle():
    idx = pd.to_datetime(
        ["2025-01-02 09:00", "2025-01-02 09:01", "2025-01-02 09:03", "2025-01-02 09:04"]
    )
    d = pd.DataFrame({"open": 1, "high": 2, "low": 0, "close": 1}, index=idx)
    assert reamostrar_completas(d, 5, 1).empty


def test_execucao_na_barra_seguinte_e_ambiguidade_conservadora(monkeypatch):
    idx = pd.date_range("2025-01-02 09:00", periods=4, freq="5min")
    d = pd.DataFrame(
        {
            "open": [1000, 1000, 1000, 1000],
            "high": [1010, 1700, 1010, 1010],
            "low": [990, 600, 990, 990],
            "close": [1000, 1000, 1000, 1000],
        },
        index=idx,
    )
    monkeypatch.setattr(
        "robob3.backtest.codex_fichas.sinais", lambda *args: pd.Series([1, 0, 0, 0], index=idx)
    )
    ops = simular(d, "medias-5-20", 5, [], "2025-01-02", "2025-01-02")
    assert len(ops) == 1
    assert ops[0]["entrada_em"] == "2025-01-02 09:05:00"
    assert ops[0]["motivo"] == "stop"
    assert ops[0]["ambigua"]
    assert ops[0]["resultado_brl"] == -61.5
