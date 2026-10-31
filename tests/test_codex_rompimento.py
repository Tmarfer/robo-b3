import pandas as pd
import pytest

from robob3.backtest.codex_rompimento import executar_rodada, simular


def barras(valores):
    return pd.DataFrame(
        valores,
        columns=["open", "high", "low", "close"],
        index=pd.date_range("2025-01-02 09:00", periods=len(valores), freq="5min"),
    )


def test_alvo_na_barra_depois_da_entrada():
    dados = barras(
        [
            (1000, 1010, 990, 1000),
            (1000, 1020, 995, 1015),
            (1020, 1060, 1015, 1050),
            (1050, 1055, 1045, 1050),
        ]
    )
    ops, _ = simular(dados)
    assert len(ops) == 1
    assert (ops[0]["entrada"], ops[0]["alvo"], ops[0]["saida"]) == (1020, 1055, 1055)
    assert ops[0]["motivo"] == "alvo"


def test_stop_prevalece_em_barra_ambigua():
    dados = barras(
        [
            (1000, 1010, 990, 1000),
            (1000, 1020, 995, 1015),
            (1020, 1070, 900, 1000),
            (1000, 1000, 990, 995),
        ]
    )
    ops, _ = simular(dados)
    assert ops[0]["motivo"] == "stop"
    assert ops[0]["saida"] == 910
    assert ops[0]["ambigua"]


def test_encerra_no_fim_e_nao_atravessa_lacuna():
    dados = barras([(1000, 1010, 990, 1000), (1000, 1020, 995, 1015), (1015, 1020, 1000, 1005)])
    ops, _ = simular(dados)
    assert ops[0]["motivo"] == "fim do pregão"
    assert ops[0]["saida"] == 1000
    dados.index = pd.to_datetime(["2025-01-02 09:00", "2025-01-02 09:10", "2025-01-02 09:15"])
    assert simular(dados)[0] == []


def test_fora_da_amostra_exige_confirmacao():
    with pytest.raises(ValueError, match="confirmo-fora-da-amostra"):
        executar_rodada("arquivo-nao-aberto.csv", "fora-da-amostra")
