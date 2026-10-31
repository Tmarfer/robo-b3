import pandas as pd

from robob3.backtest.codex_falso_adverso import simular


def dados(high_entrada):
    return pd.DataFrame(
        [(100, 110, 90, 100), (100, 120, 95, 100), (100, high_entrada, 70, 90), (90, 100, 80, 95)],
        columns=["open", "high", "low", "close"],
        index=pd.date_range("2026-02-11 09:00", periods=4, freq="min"),
    )


def test_sinal_confirmado_so_entra_na_barra_seguinte_e_stop_antigo_tem_precedencia():
    ops = simular(dados(110), 3)
    assert len(ops) == 1
    assert ops[0]["entrada_em"] == "2026-02-11 09:02:00"
    assert ops[0]["lado"] == -1 and ops[0]["entrada"] == 95
    assert ops[0]["motivo"] == "stop inicial"
    assert ops[0]["resultado_brl"] == -4.5


def test_trailing_diante_de_ambiguidade_usa_preco_adverso():
    ops = simular(dados(105), 3)
    assert ops[0]["motivo"] == "stop móvel"
    assert ops[0]["stop_atual"] == 85
    assert ops[0]["resultado_brl"] == 0.5
