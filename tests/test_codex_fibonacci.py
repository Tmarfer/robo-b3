import pandas as pd
import pytest

from robob3.backtest.codex_fibonacci import Ziguezague, cluster, fibogap, preparar_entrada, saida


def test_pivo_so_e_conhecido_depois_da_reversao():
    zig = Ziguezague(300)
    times = pd.date_range("2025-01-02 09:00", periods=4, freq="15min")
    assert zig.atualizar(times[0], 1000) is None
    assert zig.atualizar(times[1], 1100) is None
    assert zig.atualizar(times[2], 1295) is None
    p = zig.atualizar(times[3], 1300)
    assert p["tipo"] == "fundo" and p["preco"] == 1000
    assert p["extremo_em"] == times[0] and p["confirmado_em"] == times[3]


def test_cluster_usa_quatro_pivos_confirmados_e_inverte_na_baixa():
    ts = pd.Timestamp("2025-01-02 10:00")
    p = [
        {"tipo": t, "preco": v, "confirmado_em": ts}
        for t, v in [("fundo", 1000), ("topo", 2000), ("fundo", 1400), ("topo", 1800)]
    ]
    c = cluster(p)
    assert c is not None and c["lado"] == 1
    assert c["superior"] - c["inferior"] <= 100
    espelho = [
        {
            "tipo": "topo" if x["tipo"] == "fundo" else "fundo",
            "preco": 3000 - x["preco"],
            "confirmado_em": ts,
        }
        for x in p
    ]
    c2 = cluster(espelho)
    assert c2["lado"] == -1 and c2["centro"] == pytest.approx(3000 - c["centro"])


def test_fibogap_aguarda_primeira_hora_e_barra_de_confirmacao():
    idx = pd.date_range("2025-01-02 09:00", periods=6, freq="15min")
    d = pd.DataFrame(
        {
            "open": [1050, 1060, 1070, 1080, 950, 950],
            "high": [1100, 1150, 1200, 1180, 1000, 1000],
            "low": [1000, 1030, 1040, 1020, 890, 900],
            "close": [1060, 1100, 1150, 1100, 920, 980],
        },
        index=idx,
    )
    prev = next(pd.DataFrame({"high": [1000], "low": [900]}).itertuples())
    assert list(fibogap(d.iloc[:5], prev)) == []
    s = list(fibogap(d, prev))
    assert len(s) == 1 and s[0]["lado"] == 1
    assert s[0]["sinal_em"] == idx[5]
    assert s[0]["stop"] == 885 and s[0]["alvo"] == pytest.approx(1129.2)


def test_entrada_na_abertura_depois_do_sinal_e_descarta_alvo_inviavel():
    idx = pd.to_datetime(["2025-01-02 10:30", "2025-01-02 10:35", "2025-01-02 17:00"])
    d = pd.DataFrame(
        {
            "open": [1000, 1000, 1000],
            "high": [1010, 1600, 1000],
            "low": [990, 690, 1000],
            "close": [1000, 1000, 1000],
        },
        index=idx,
    )
    setup = {
        "sinal_em": pd.Timestamp("2025-01-02 10:15"),
        "lado": 1,
        "stop": 700,
        "alvo": 1500,
        "nivel": 1000,
    }
    e = preparar_entrada(setup, d)
    assert e["entrada_em"] == "2025-01-02 10:30:00"
    invalido = dict(setup, alvo=1000)
    assert preparar_entrada(invalido, d) is None
    op = saida(d, e, "padrao")
    assert op["ambigua"] and op["motivo"] == "stop" and op["saida"] == 695


def test_salto_abertura_alem_stop_nao_usa_preco_do_stop():
    idx = pd.to_datetime(["2025-01-02 10:30", "2025-01-02 10:35", "2025-01-02 17:00"])
    d = pd.DataFrame(
        {
            "open": [1000, 650, 1000],
            "high": [1010, 660, 1000],
            "low": [990, 640, 1000],
            "close": [1000, 650, 1000],
        },
        index=idx,
    )
    setup = {
        "sinal_em": pd.Timestamp("2025-01-02 10:15"),
        "lado": 1,
        "stop": 700,
        "alvo": 1500,
        "nivel": 1000,
    }
    e = preparar_entrada(setup, d)
    assert saida(d, e, "padrao")["saida"] == 645
