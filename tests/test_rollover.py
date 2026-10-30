from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from test_sessions import _barras, _dia

from robob3.cli import main
from robob3.data import (
    ajustar_rolagem,
    candidatas_rolagem,
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


def _diario(precos: dict[str, float]) -> pd.DataFrame:
    """Dois candles por pregão (09:00 e 18:29) no preço do dia: o gap é a variação entre dias."""
    idx, vals = [], []
    for d, p in precos.items():
        idx += [pd.Timestamp(f"{d} 09:00"), pd.Timestamp(f"{d} 18:29")]
        vals += [p, p]
    s = pd.Series(vals, index=pd.DatetimeIndex(idx), dtype=float)
    return pd.DataFrame({"open": s, "high": s, "low": s, "close": s, "real_volume": 1.0})


def _serie(
    inicio: str, fim: str, saltos: dict[str, float], sem: tuple = (), ruido: float = 50
) -> pd.DataFrame:
    dias = [d for d in pd.bdate_range(inicio, fim).strftime("%Y-%m-%d") if d not in sem]
    p, precos = 100_000.0, {}
    for i, d in enumerate(dias):
        p += saltos.get(d, ruido if i % 2 else -ruido)  # ruído pequeno alternado
        precos[d] = p
    return _diario(precos)


def test_quarta_mais_proxima_do_15():
    from robob3.data.rollover import _quarta_mais_proxima_do_15

    # vencimentos do WIN observados em 2026 nos dados da Clear
    assert [_quarta_mais_proxima_do_15(2026, m) for m in (2, 4, 6, 8, 10)] == [
        date(2026, 2, 18),
        date(2026, 4, 15),
        date(2026, 6, 17),
        date(2026, 8, 12),
        date(2026, 10, 14),
    ]


def test_candidatas_win_com_feriado_no_vencimento():
    # 15/04 sem pregão (feriado fictício): a troca aparece no pregão seguinte, 16/04
    df = _serie(
        "2026-02-02",
        "2026-06-30",
        {"2026-02-18": 2000, "2026-04-16": 2000, "2026-06-17": 2000},
        sem=("2026-04-15",),
    )
    cands = candidatas_rolagem(df, "win")
    assert [(c.data, c.regra, c.confirmada) for c in cands] == [
        ("2026-02-18", "2026-02-18", True),
        ("2026-04-16", "2026-04-15", True),
        ("2026-06-17", "2026-06-17", True),
    ]


def test_candidatas_wdo_com_troca_mascarada():
    # 31/03 com salto pequeno e 01/04 com queda maior (como em março/2026): fica pendente
    saltos = {"2026-02-27": 35, "2026-03-31": 5, "2026-04-01": -25, "2026-04-30": 30}
    df = _serie("2026-02-02", "2026-05-15", saltos, ruido=4)
    cands = {c.data: c for c in candidatas_rolagem(df, "wdo")}
    assert list(cands) == ["2026-02-27", "2026-03-31", "2026-04-30"]  # maio não terminou
    assert cands["2026-02-27"].confirmada and cands["2026-04-30"].confirmada
    assert not cands["2026-03-31"].confirmada


def test_cli_rolagens_candidatas(tmp_path, capsys):
    df = _serie("2026-02-02", "2026-04-30", {"2026-02-18": 2000, "2026-04-15": -10})
    arq = escrever_barras_mt5(df, tmp_path / "WIN.csv")
    assert main(["rolagens-candidatas", str(arq), "--regra", "win"]) == 0
    out = capsys.readouterr().out
    assert "datas: [2026-02-18]" in out and "pendentes: [2026-04-15]" in out
