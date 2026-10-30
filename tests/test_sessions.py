from datetime import time

import pandas as pd
import pytest

from robob3.cli import main
from robob3.data import (
    avaliar_barras,
    detectar_incompletos,
    escrever_barras_mt5,
    ler_barras_mt5,
    remover_pregoes_incompletos,
    resumo_pregoes,
)


def _dia(data: str, inicio: str = "09:00", fim: str = "18:29", sem: tuple = ()) -> pd.DatetimeIndex:
    idx = pd.date_range(f"{data} {inicio}", f"{data} {fim}", freq="1min")
    for a, b in sem:
        idx = idx[(idx < pd.Timestamp(f"{data} {a}")) | (idx > pd.Timestamp(f"{data} {b}"))]
    return idx


def _barras(*dias: pd.DatetimeIndex) -> pd.DataFrame:
    idx = dias[0].append(list(dias[1:]))
    base = pd.Series(range(len(idx)), index=idx, dtype=float) + 5000
    return pd.DataFrame(
        {"open": base, "high": base + 1, "low": base - 1, "close": base, "real_volume": 10.0}
    )


@pytest.fixture
def extracao():
    """Como a 1ª exportação do WDO: pontas cortadas, Cinzas e uma pausa real no meio de um dia."""
    return _barras(
        _dia("2026-02-13", inicio="15:35"),  # corte do limite de barras
        _dia("2026-02-18", inicio="13:00"),  # Quarta-feira de Cinzas: pregão oficial reduzido
        _dia("2026-02-19"),
        _dia("2026-10-26", sem=(("09:27", "09:41"),)),  # pausa: evento de mercado, fica
        _dia("2026-10-27"),
        _dia("2026-10-29", fim="13:50"),  # exportado durante o pregão
    )


def test_resumo_pregoes(extracao):
    r = resumo_pregoes(extracao)
    assert len(r) == 6
    assert r.loc["2026-02-13", "primeira"] == pd.Timestamp("2026-02-13 15:35")
    assert r.loc["2026-10-29", "ultima"] == pd.Timestamp("2026-10-29 13:50")
    assert r.loc["2026-02-19", "barras"] == 570


def test_detecta_pontas_e_preserva_pausa(extracao):
    incompletos, ab, fe = detectar_incompletos(extracao)
    assert (ab, fe) == ("09:00", "18:29")
    assert [p.data for p in incompletos] == ["2026-02-13", "2026-02-18", "2026-10-29"]
    assert [p.ponta for p in incompletos] == [True, False, True]
    assert "abre 15:35" in incompletos[0].motivo
    assert "fecha 13:50" in incompletos[2].motivo


def test_ultimo_dia_com_51pct_escapava_da_cobertura_baixa(extracao):
    rel = avaliar_barras(extracao)
    assert "2026-10-29" not in rel.pregoes_cobertura_baixa  # critério antigo não pegava
    assert "2026-10-29" in [p.data for p in rel.pregoes_incompletos]
    assert rel.lacunas_intradiarias == 1  # a pausa continua no relatório de lacunas
    texto = rel.to_texto()
    assert "pregoes_incompletos: 3" in texto
    assert "2026-02-18 13:00-18:29 (330 barras) [interno: investigar]" in texto


def _dias(df: pd.DataFrame) -> list[str]:
    return sorted(set(df.index.strftime("%Y-%m-%d")))


def test_remover_so_pontas_por_padrao(extracao):
    limpo, removidos = remover_pregoes_incompletos(extracao)
    assert [p.data for p in removidos] == ["2026-02-13", "2026-10-29"]
    assert _dias(limpo) == ["2026-02-18", "2026-02-19", "2026-10-26", "2026-10-27"]


def test_remover_internos_explicito(extracao):
    limpo, removidos = remover_pregoes_incompletos(extracao, internos=True)
    assert len(removidos) == 3
    assert _dias(limpo) == ["2026-02-19", "2026-10-26", "2026-10-27"]


def test_horarios_explicitos_e_tolerancia(extracao):
    # fechamento informado 18:24 (WIN): nenhum dia completo é marcado
    incompletos, _, fe = detectar_incompletos(extracao, fechamento=time(18, 24))
    assert fe == "18:24" and len(incompletos) == 3
    # abertura informada 15:30 com tolerância 5: o 1º dia (15:35) deixa de ser incompleto
    incompletos, _, _ = detectar_incompletos(extracao, abertura=time(15, 30))
    assert "2026-02-13" not in [p.data for p in incompletos]


def test_cli_remover_e_reamostrar(extracao, tmp_path, capsys):
    bruto = escrever_barras_mt5(extracao, tmp_path / "WDO.csv")
    limpo = tmp_path / "WDO_limpo.csv"
    assert main(["remover-incompletos", str(bruto), "--saida", str(limpo)]) == 0
    assert len(ler_barras_mt5(limpo)) == 330 + 570 * 2 + (570 - 15)

    m5 = tmp_path / "WDO_M5.parquet"
    args = ["reamostrar", str(bruto), "--minutos", "5", "--saida", str(m5), "--remover-incompletos"]
    assert main(args) == 0
    assert _dias(pd.read_parquet(m5)) == ["2026-02-18", "2026-02-19", "2026-10-26", "2026-10-27"]

    args += ["--remover-internos"]
    assert main(args) == 0
    assert _dias(pd.read_parquet(m5)) == ["2026-02-19", "2026-10-26", "2026-10-27"]

    assert main(["pregoes", str(bruto)]) == 0
    saida = capsys.readouterr().out
    assert "2026-02-13,15:35,18:29," in saida
