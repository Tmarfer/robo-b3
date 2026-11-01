import pandas as pd
import pytest

from robob3.backtest.codex_retracao import sinais_retracao


def barras(fechamentos):
    idx = pd.date_range("2025-01-02 09:00", periods=len(fechamentos), freq="15min")
    return pd.DataFrame(
        {"open": fechamentos, "high": fechamentos, "low": fechamentos, "close": fechamentos},
        index=idx,
    )


def test_compra_so_depois_da_confirmacao_do_topo_e_no_fechamento_da_zona():
    dados = barras([1000, 1300, 1700, 1400, 1200, 1500, 2000, 1700, 1650])
    assert list(sinais_retracao(dados.iloc[:8])) == []
    sinais = list(sinais_retracao(dados))
    assert len(sinais) == 1
    assert sinais[0]["lado"] == 1 and sinais[0]["sinal_em"] == dados.index[8]
    assert sinais[0]["stop"] == pytest.approx(1461.4)
    assert sinais[0]["alvo"] == 2000 and sinais[0]["nivel"] == pytest.approx(1647.2)


def test_venda_e_o_espelho_da_compra():
    preco = [1000, 1300, 1700, 1400, 1200, 1500, 2000, 1700, 1650]
    sinais = list(sinais_retracao(barras([3000 - p for p in preco])))
    assert len(sinais) == 1 and sinais[0]["lado"] == -1
    assert sinais[0]["stop"] == pytest.approx(1538.6)
    assert sinais[0]["alvo"] == 1000 and sinais[0]["nivel"] == pytest.approx(1352.8)


def test_fechamento_alem_da_invalidacao_cancela_o_setup():
    dados = barras([1000, 1300, 1700, 1400, 1200, 1500, 2000, 1700, 1450, 1650])
    assert list(sinais_retracao(dados)) == []
