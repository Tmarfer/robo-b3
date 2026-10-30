from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from test_sessions import _barras, _dia

from robob3.cli import main
from robob3.data import (
    ajustar_rolagem,
    carregar_rolagens,
    escrever_barras_mt5,
    gaps_abertura,
    ler_barras_mt5,
)

CONFIG = Path(__file__).parents[1] / "config" / "rolagens.yaml"


@pytest.fixture
def serie_com_rolagem():
    """3 pregões; em 14/10 a série troca para o contrato seguinte, 2.000 pontos acima."""
    df = _barras(_dia("2026-10-12"), _dia("2026-10-13"), _dia("2026-10-14"))
    df.loc["2026-10-14", ["open", "high", "low", "close"]] += 2000
    return df


def test_aditivo_remove_o_salto_e_preserva_o_dia(serie_com_rolagem):
    ajustada, ajustes = ajustar_rolagem(serie_com_rolagem, [date(2026, 10, 14)])
    [a] = ajustes
    assert a.situacao == "aplicado" and a.salto == 2001  # +1 da sequência sintética
    # depois do ajuste, o salto da troca some; o de 13/10 (sem rolagem) não muda
    gaps = gaps_abertura(ajustada)["gap_pts"]
    assert gaps["2026-10-14"] == 0 and gaps["2026-10-13"] == 1
    # o dia da troca fica intacto; dentro de cada dia as diferenças em pontos não mudam
    pd.testing.assert_frame_equal(ajustada.loc["2026-10-14"], serie_com_rolagem.loc["2026-10-14"])
    d = ajustada.loc["2026-10-12", "close"] - serie_com_rolagem.loc["2026-10-12", "close"]
    assert (d == 2001).all()


def test_razao_preserva_variacao_percentual(serie_com_rolagem):
    ajustada, [a] = ajustar_rolagem(serie_com_rolagem, [date(2026, 10, 14)], metodo="razao")
    orig = serie_com_rolagem.loc["2026-10-13", "close"]
    adj = ajustada.loc["2026-10-13", "close"]
    pd.testing.assert_series_equal(adj.pct_change(), orig.pct_change())
    assert abs(gaps_abertura(ajustada).loc["2026-10-14", "gap_pct"]) < 1e-9


def test_datas_fora_do_periodo(serie_com_rolagem):
    _, ajustes = ajustar_rolagem(serie_com_rolagem, [date(2026, 10, 12), date(2026, 12, 16)])
    assert [a.situacao for a in ajustes] == ["fora do período", "fora do período"]


def test_config_versionada_coerente():
    win = carregar_rolagens("WIN", CONFIG)
    assert win.simbolo == "WIN$N"
    assert all(d.weekday() == 2 for d in win.datas)  # vencimentos do WIN caem na quarta
    assert all(d.month % 2 == 0 for d in win.datas)
    wdo = carregar_rolagens("WDO", CONFIG)
    assert date(2026, 3, 31) in wdo.pendentes and date(2026, 3, 31) not in wdo.datas
    with pytest.raises(ValueError, match="não está"):
        carregar_rolagens("XYZ", CONFIG)


def test_cli_ajustar_rolagem(serie_com_rolagem, tmp_path, capsys):
    cfg = tmp_path / "rol.yaml"
    cfg.write_text("WIN:\n  simbolo: WIN$N\n  regra: teste\n  datas: [2026-10-14]\n")
    bruto = escrever_barras_mt5(serie_com_rolagem, tmp_path / "WIN.csv")
    saida = tmp_path / "WIN_aj.csv"
    args = ["ajustar-rolagem", str(bruto), "--ativo", "WIN", "--saida", str(saida)]
    assert main(args + ["--config", str(cfg)]) == 0
    assert "2026-10-14: 6139 -> 8140, salto +2001" in capsys.readouterr().out
    assert gaps_abertura(ler_barras_mt5(saida)).loc["2026-10-14", "gap_pts"] == 0
