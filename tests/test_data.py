import pandas as pd
import pytest
from conftest import linha

from robob3.data import avaliar_barras, ler_barras_mt5, reamostrar


@pytest.mark.parametrize("encoding", ["utf-16", "utf-8", "utf-8-sig"])
def test_le_csv_mt5(csv_mt5, encoding):
    p = csv_mt5(
        [
            linha("2024.01.02", "09:00:00", 100, 110, 95, 105),
            linha("2024.01.02", "09:01:00", 105, 106, 100, 101),
        ],
        encoding=encoding,
    )
    df = ler_barras_mt5(p)
    assert list(df.columns) == [
        "open", "high", "low", "close", "tick_volume", "real_volume", "spread"
    ]
    assert df.index[0] == pd.Timestamp("2024-01-02 09:00")
    assert df["high"].iloc[0] == 110


def test_rejeita_arquivo_que_nao_e_mt5(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="colunas ausentes"):
        ler_barras_mt5(p)


def test_relatorio_detecta_problemas(csv_mt5):
    p = csv_mt5(
        [
            linha("2024.01.02", "09:00:00", 100, 110, 95, 105),
            linha("2024.01.02", "09:01:00", 105, 106, 100, 101),
            linha("2024.01.02", "09:01:00", 105, 106, 100, 101),  # duplicado
            linha("2024.01.02", "09:05:00", 101, 99, 98, 100),  # lacuna de 3; high < open
            linha("2024.01.03", "09:00:00", 100, 101, 99, 100, v=0),  # outro dia: não é lacuna
        ]
    )
    rel = avaliar_barras(ler_barras_mt5(p))
    assert rel.pregoes == 2
    assert rel.timestamps_duplicados == 1
    assert rel.ohlc_inconsistente == 1
    assert rel.barras_volume_zero == 1
    assert rel.lacunas_intradiarias == 1
    assert rel.barras_faltando_total == 3
    assert rel.maiores_lacunas[0].inicio == "2024-01-02 09:01:00"


def _m1(inicio: str, n: int) -> pd.DataFrame:
    idx = pd.date_range(inicio, periods=n, freq="1min")
    base = pd.Series(range(n), index=idx, dtype=float) + 100
    return pd.DataFrame(
        {"open": base, "high": base + 2, "low": base - 1, "close": base + 1, "real_volume": 1.0}
    )


def test_reamostrar_m5():
    out = reamostrar(_m1("2024-01-02 09:00", 10), 5)
    assert list(out.index.strftime("%H:%M")) == ["09:00", "09:05"]
    primeira = out.iloc[0]
    assert primeira["open"] == 100 and primeira["close"] == 105
    assert primeira["high"] == 106 and primeira["low"] == 99
    assert primeira["real_volume"] == 5 and primeira["barras"] == 5


def test_reamostrar_nao_preenche_lacunas_nem_cruza_dias():
    df = pd.concat([_m1("2024-01-02 17:58", 2), _m1("2024-01-03 09:00", 3)])
    out = reamostrar(df, 15)
    assert len(out) == 2
    assert out["barras"].tolist() == [2, 3]


def test_reamostrar_recusa_duplicados_e_timeframe_invalido():
    df = _m1("2024-01-02 09:00", 3)
    with pytest.raises(ValueError, match="dividir 1440"):
        reamostrar(df, 7)
    with pytest.raises(ValueError, match="duplicados"):
        reamostrar(pd.concat([df, df.iloc[:1]]), 5)


def test_escrever_e_ler_formato_mt5_ida_e_volta(tmp_path):
    from robob3.data import escrever_barras_mt5

    df = _m1("2024-01-02 09:00", 3).assign(tick_volume=7, spread=0)
    p = escrever_barras_mt5(df, tmp_path / "sub" / "x.csv")
    lido = ler_barras_mt5(p)
    pd.testing.assert_frame_equal(
        lido[["open", "high", "low", "close"]], df[["open", "high", "low", "close"]],
        check_freq=False, check_names=False,
    )


def test_rates_para_df():
    import numpy as np

    from robob3.data.mt5_csv import rates_para_df

    dtype = [("time", "<i8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"),
             ("close", "<f8"), ("tick_volume", "<u8"), ("spread", "<i4"), ("real_volume", "<u8")]
    rates = np.array([(1704186000, 1, 2, 0.5, 1.5, 10, 0, 20)], dtype=dtype)  # 2024-01-02 09:00
    df = rates_para_df(rates)
    assert df.index[0] == pd.Timestamp("2024-01-02 09:00")
    assert list(df.columns) == [
        "open", "high", "low", "close", "tick_volume", "real_volume", "spread"
    ]
