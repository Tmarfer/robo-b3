"""Testes da win-pivo-v1 contra a especificação (docs/estrategias/win-pivo-v1.md).

Cenário montado à mão (M5, preços do WIN):
- 06/05: fundo isolado em 124.000 (10:00) e topo isolado em 126.500 (11:00) -> SL e SH.
- 07/05 (pregão anterior): máxima 125.600 e mínima 124.600 -> RH, RL; amplitude 1.000.
- 08/05: B1 e B2 testam a zona compradora (RL + T = 124.700) e B3 rompe a máxima de B2.
- 09/05: dia neutro (sem setup).
Com TOL = 10%: T = 100. Gatilho 124.805, stop 124.615, alvo (ALVO = 1) 125.600.
"""

from datetime import date

import pandas as pd
import pytest

from robob3.backtest.orb import Operacao
from robob3.backtest.pivo import (
    ParametrosPivo,
    backtest_pivo,
    entrada_aleatoria_pivo,
    niveis,
    simular_dia,
)

P = ParametrosPivo()  # alvo 1,0; tol 10%; derrapagem 5; custo R$ 0,25/lado
K = 250_000  # espelho de preços para montar a venda


def _dia(data, neutro, barras=None):
    idx = pd.date_range(f"{data} 09:00", f"{data} 18:20", freq="5min")
    linhas = {t: (neutro,) * 4 for t in idx}
    for hhmm, ohlc in (barras or {}).items():
        linhas[pd.Timestamp(f"{data} {hhmm}")] = ohlc
    df = pd.DataFrame.from_dict(linhas, orient="index", columns=["open", "high", "low", "close"])
    return df.sort_index().astype(float)


DIA3 = {
    "09:00": (124900, 124900, 124650, 124700),  # B1: desce até 124.650 (zona compradora)
    "09:05": (124700, 124750, 124680, 124720),
    "09:10": (124720, 124740, 124690, 124700),
    "09:15": (124700, 124760, 124620, 124740),  # B2: mínima 124.620, máxima 124.800
    "09:20": (124740, 124800, 124700, 124780),
    "09:25": (124780, 124790, 124740, 124750),
    "09:30": (124760, 124850, 124740, 124840),  # B3: rompe 124.805 -> compra
    "11:00": (124900, 125650, 124880, 125600),  # alvo 125.600
}


def _cenario(dia3=None):
    return pd.concat(
        [
            _dia(
                "2024-05-06",
                125000,
                {
                    "10:00": (125000, 125000, 124000, 125000),
                    "11:00": (125000, 126500, 125000, 125000),
                },
            ),
            _dia(
                "2024-05-07",
                125000,
                {
                    "10:00": (125000, 125600, 125000, 125000),
                    "14:00": (125000, 125000, 124600, 125000),
                },
            ),
            _dia("2024-05-08", 124900, {**DIA3, **(dia3 or {})}),
            _dia("2024-05-09", 125000),
        ]
    )


def _espelho(df):
    return pd.DataFrame(
        {
            "open": K - df["open"],
            "high": K - df["low"],
            "low": K - df["high"],
            "close": K - df["close"],
        }
    )


def _op(df, p=P, rolagens=None):
    res = backtest_pivo(df, p, rolagens=rolagens)
    ops = res.operacoes
    return (ops.iloc[0] if len(ops) else None), res


def test_linhas_de_referencia():
    df = _cenario()
    hist = df[df.index < "2024-05-08"]
    assert niveis(hist, P) == {"RH": 125600, "RL": 124600, "SH": 126500, "SL": 124000, "T": 100}


def test_compra_do_exemplo():
    op, res = _op(_cenario())
    assert (op.data, op.lado, op.hora_entrada) == ("2024-05-08", "C", "09:30")
    assert (op.referencia, op.entrada, op.stop, op.alvo) == (124805, 124810, 124615, 125600)
    assert (op.hora_saida, op.saida, op.motivo) == ("11:00", 125600, "alvo")
    assert op.pontos == 790 and op.resultado == pytest.approx(157.50)
    assert not op.ambigua
    motivos = dict(zip(res.sem_operacao["data"], res.sem_operacao["motivo"], strict=True))
    assert motivos["2024-05-09"] == "sem_setup"


def test_alvo_meio_caminho():
    op, _ = _op(_cenario(), ParametrosPivo(alvo=0.5))
    assert op.alvo == 125200  # 124.805 + 397,5, arredondado ao tick
    assert (op.saida, op.motivo) == (125200, "alvo")


def test_venda_e_o_espelho_da_compra():
    op, _ = _op(_espelho(_cenario()))
    assert (op.lado, op.hora_entrada) == ("V", "09:30")
    assert (op.referencia, op.stop, op.alvo) == (K - 124805, K - 124615, K - 125600)
    assert op.resultado == pytest.approx(157.50)


def test_stop_antes_do_gatilho_cancela():
    op, res = _op(_cenario({"09:30": (124700, 124750, 124600, 124650)}))
    assert op is None
    assert "cancelado (C)" in set(res.sem_operacao["motivo"])


def test_entrada_e_stop_na_mesma_barra_e_stop():
    df = _cenario({"09:30": (124760, 124850, 124600, 124700)})
    op, _ = _op(df)
    assert (op.motivo, op.saida, op.ambigua) == ("stop", 124610, True)
    assert op.resultado == pytest.approx(-40.50)  # 124.610 - 124.810 = -200 pts
    otim, _ = _op(df, ParametrosPivo(ambiguidade="otimista"))
    assert otim.motivo == "alvo" and otim.ambigua


def test_rolagem():
    _, res = _op(_cenario(), rolagens=[date(2024, 5, 8)])
    motivos = dict(zip(res.sem_operacao["data"], res.sem_operacao["motivo"], strict=True))
    assert motivos["2024-05-08"] == "rolagem"
    # troca em 07/05: o fundo de 06/05 é de outro contrato -> sem Swing Low -> sem compra
    op, res = _op(_cenario(), rolagens=[date(2024, 5, 7)])
    assert op is None


def test_pregao_sem_b1_b3_completas():
    df = _cenario()
    hist = df[df.index < "2024-05-08"]
    dia = df[df.index.normalize() == "2024-05-08"].drop(pd.Timestamp("2024-05-08 09:20"))
    assert simular_dia(dia, hist, P) == "barras_incompletas"
    assert isinstance(simular_dia(df[df.index.normalize() == "2024-05-08"], hist, P), Operacao)


def test_entrada_aleatoria_pivo():
    df = _cenario()
    res = backtest_pivo(df, P)
    a = entrada_aleatoria_pivo(df, res, sorteios=200, semente=7)
    assert a == entrada_aleatoria_pivo(df, res, sorteios=200, semente=7)
    assert a["sorteios"] == 200 and 0 <= a["percentil_estrategia"] <= 100
    assert a["estrategia_brl"] == pytest.approx(157.50)


def test_cli_backtest_pivo(tmp_path, capsys, monkeypatch):
    import json

    from robob3.backtest import orb
    from robob3.cli import main
    from robob3.data import escrever_barras_mt5

    arq = escrever_barras_mt5(_cenario(), tmp_path / "WIN_M5.csv")
    rol = tmp_path / "rolagens.yaml"
    rol.write_text("WIN:\n  simbolo: WIN$N\n  regra: teste\n  datas: [2024-05-09]\n")
    monkeypatch.setitem(orb.PERIODOS, "desenvolvimento", ("2024-01-01", "2025-12-31"))
    monkeypatch.setenv("ROBOB3_COMMIT", "b" * 40)
    pasta = tmp_path / "manifestos"
    args = ["backtest-pivo", str(arq), "--grade", "--aleatorio", "20", "--rolagens", str(rol)]
    assert main([*args, "--manifesto", str(pasta)]) == 0
    out = capsys.readouterr().out
    assert "alvo,tol,operacoes" in out and "\n1,0.1,1,157.50," in out

    (arquivo,) = pasta.glob("win-pivo-v1_desenvolvimento_conservadora_*.json")
    m = json.loads(arquivo.read_text())
    assert m["estrategia"] == "win-pivo-v1" and len(m["linhas"]) == 6
    assert m["linhas"][4]["parametros"] == {"alvo": 1.0, "tol": 0.10}
    assert m["linhas"][4]["dias_sem_operacao"]["rolagem"] == 1  # 09/05 vira dia de troca

    # fora da amostra exige confirmação explícita
    assert main(["backtest-pivo", str(arq), "--periodo", "fora-da-amostra"]) == 2
