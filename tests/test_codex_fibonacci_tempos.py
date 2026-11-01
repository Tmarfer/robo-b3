import pandas as pd

from robob3.backtest.codex_fibonacci import fibogap, preparar_entrada


def test_entrada_ocorre_apos_fechamento_do_tempo_selecionado():
    indice = pd.to_datetime(["2026-02-11 10:01", "2026-02-11 10:05"])
    barras = pd.DataFrame({"open": [1000, 1000]}, index=indice)
    setup = {
        "sinal_em": pd.Timestamp("2026-02-11 10:00"),
        "lado": 1,
        "stop": 900,
        "alvo": 1100,
        "nivel": 1000,
    }
    assert preparar_entrada(setup, barras, 1)["entrada_em"].endswith("10:01:00")
    assert preparar_entrada(setup, barras, 5)["entrada_em"].endswith("10:05:00")
    assert preparar_entrada(setup, barras, 15) is None


def test_fibogap_exige_primeira_hora_completa():
    indice = pd.date_range("2026-02-11 09:00", periods=61, freq="1min").delete(30)
    barras = pd.DataFrame({"open": 1000, "high": 1010, "low": 990, "close": 1000}, index=indice)
    anterior = next(pd.DataFrame({"high": [900], "low": [800]}).itertuples())
    assert list(fibogap(barras, anterior, 1)) == []
