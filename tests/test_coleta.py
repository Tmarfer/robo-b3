import json
from datetime import date, datetime

import pandas as pd
import pytest

from robob3.coleta import exportar, gravar_m1, status
from robob3.coleta.gravador import dias_gravados, pasta_simbolo
from robob3.data import ler_barras_mt5


class FonteFalsa:
    """Imita o servidor: M1 das 09:00 às 18:29 em dias úteis, até `agora`, limitado às últimas
    `limite` barras (como o teto de 100 mil do servidor real, que corta o 1º dia)."""

    def __init__(self, agora: str, limite: int = 2000, erro_em: str | None = None):
        self.agora, self.limite, self.erro_em = pd.Timestamp(agora), limite, erro_em
        self.pedidos = []

    def info(self):
        return {"servidor": "Falso-DEMO", "conta_demo": True, "build": 1}

    def _todas(self, simbolo):
        idx = pd.DatetimeIndex([])
        for d in pd.bdate_range("2026-01-01", self.agora.normalize()):
            idx = idx.append(
                pd.date_range(d + pd.Timedelta("9h"), d + pd.Timedelta("18h29min"), freq="1min")
            )
        idx = idx[idx <= self.agora][-self.limite :]
        base = 5000.0 if simbolo.startswith("WDO") else 120000.0
        p = pd.Series(base, index=idx) + pd.Series(range(len(idx)), index=idx) % 50
        return pd.DataFrame(
            {
                "open": p,
                "high": p + 5,
                "low": p - 5,
                "close": p,
                "tick_volume": 10,
                "real_volume": 20,
                "spread": 0,
            }
        )

    def barras(self, simbolo, minutos, inicio, fim):
        self.pedidos.append((simbolo, inicio, fim))
        if simbolo == self.erro_em:
            raise RuntimeError("símbolo indisponível")
        df = self._todas(simbolo)
        return df[(df.index >= inicio) & (df.index <= fim)]


def test_backfill_descarta_dia_cortado_e_grava_ate_ontem(tmp_path):
    # 2.000 barras até 30/10 10:00 (hoje, incompleto): 61 barras de hoje + 3 dias cheios (1.710)
    # + 229 barras do dia 26/10, que vem cortado
    fonte = FonteFalsa("2026-10-30 10:00")
    reg = gravar_m1(fonte, ["WIN$N"], tmp_path, hoje=date(2026, 10, 30))
    r = reg["simbolos"]["WIN$N"]
    assert r["descartado_corte"] == "2026-10-26"
    assert [d["data"] for d in r["dias"]] == ["2026-10-27", "2026-10-28", "2026-10-29"]
    assert all(d["barras"] == 570 and d["primeira"] == "09:00" for d in r["dias"])
    assert dias_gravados(tmp_path, "WIN$N")[-1] == date(2026, 10, 29)  # hoje não entra
    assert (pasta_simbolo(tmp_path, "WIN$N") / "2026-10-27.parquet").exists()


def test_execucao_seguinte_so_acrescenta_e_nao_sobrescreve(tmp_path):
    gravar_m1(FonteFalsa("2026-10-30 10:00"), ["WIN$N"], tmp_path, hoje=date(2026, 10, 30))
    arq = pasta_simbolo(tmp_path, "WIN$N") / "2026-10-29.parquet"
    antes = arq.stat().st_mtime_ns

    fonte = FonteFalsa("2026-11-02 10:00", limite=5000)
    reg = gravar_m1(fonte, ["WIN$N"], tmp_path, hoje=date(2026, 11, 2))
    r = reg["simbolos"]["WIN$N"]
    assert [d["data"] for d in r["dias"]] == ["2026-10-30"]
    assert r["descartado_corte"] is None  # não é backfill
    assert fonte.pedidos[0][1] == datetime(2026, 10, 30)  # pede a partir do dia seguinte ao último
    assert arq.stat().st_mtime_ns == antes

    linhas = (tmp_path / "registro.jsonl").read_text().splitlines()
    assert len(linhas) == 2 and json.loads(linhas[1])["fonte"]["servidor"] == "Falso-DEMO"


def test_nada_a_fazer_no_mesmo_dia(tmp_path):
    gravar_m1(FonteFalsa("2026-10-30 10:00"), ["WIN$N"], tmp_path, hoje=date(2026, 10, 30))
    reg = gravar_m1(FonteFalsa("2026-10-30 12:00"), ["WIN$N"], tmp_path, hoje=date(2026, 10, 30))
    assert reg["simbolos"]["WIN$N"]["dias_novos"] == 0


def test_erro_em_um_simbolo_nao_impede_o_outro(tmp_path):
    fonte = FonteFalsa("2026-10-30 10:00", erro_em="WDO$N")
    reg = gravar_m1(fonte, ["WIN$N", "WDO$N"], tmp_path, hoje=date(2026, 10, 30))
    assert reg["simbolos"]["WDO$N"]["erro"] == "RuntimeError: símbolo indisponível"
    assert reg["simbolos"]["WIN$N"]["dias_novos"] == 3


def test_status_e_exportar(tmp_path):
    gravar_m1(FonteFalsa("2026-10-30 10:00"), ["WIN$N"], tmp_path, hoje=date(2026, 10, 30))
    st = status(tmp_path, ["WIN$N", "WDO$N"], hoje=date(2026, 11, 3))
    assert st["WIN$N"] == {
        "dias": 3,
        "primeiro": "2026-10-27",
        "ultimo": "2026-10-29",
        "dias_uteis_sem_gravar": 2,
    }  # 30/10 e 02/11
    assert st["WDO$N"] == {"dias": 0}
    saida = tmp_path / "WIN.csv"
    assert exportar(tmp_path, "WIN$N", saida) == 3 * 570
    assert len(ler_barras_mt5(saida)) == 1710


class ConexaoFalsa:
    """Imita rpyc.classic.connect(): responde ao código que a ponte manda executar no MT5."""

    def __init__(self, logado=None):
        self._config, self.executado, self.avaliado = {}, [], []
        self.namespace, self.logado, self.logins = {}, logado, []

    def execute(self, codigo):
        self.executado.append(codigo)
        if codigo == "del _robob3_conta":
            del self.namespace["_robob3_conta"]

    def eval(self, codigo):
        self.avaliado.append(codigo)
        if codigo == "mt5.initialize()" or codigo.startswith("mt5.symbol_select"):
            return True
        if codigo == "(lambda a: None if a is None else a.login)(mt5.account_info())":
            return self.logado
        if codigo.startswith("mt5.login("):
            self.logins.append(self.namespace["_robob3_conta"])
            self.logado = self.namespace["_robob3_conta"][0]
            return True
        if codigo.startswith("mt5.account_info"):
            return {"server": "ClearInvestimentos-DEMO", "company": "Clear", "trade_mode": 0}
        if codigo.startswith("mt5.terminal_info"):
            return {"build": 5000, "maxbars": 100000, "trade_allowed": False}
        if "copy_rates_range" in codigo:
            t = 1793264400  # 2026-10-29 09:00 (horário do servidor codificado como UTC)
            return [(t, 1.0, 2.0, 0.5, 1.5, 10, 0, 20), (t + 60, 1.5, 2.5, 1.0, 2.0, 11, 0, 21)]
        if codigo == "mt5.shutdown()":
            return None
        raise AssertionError(codigo)

    def close(self):
        pass


def test_ponte_rpyc(monkeypatch):
    pytest.importorskip("rpyc")
    import rpyc

    from robob3.coleta import PonteMT5

    conn = ConexaoFalsa()
    monkeypatch.setattr(rpyc.classic, "connect", lambda host, port: conn)
    with PonteMT5("mt5", 18812) as ponte:
        info = ponte.info()
        df = ponte.barras("WIN$N", 1, datetime(2026, 10, 29, 9), datetime(2026, 10, 29, 18, 30))
    assert info == {
        "servidor": "ClearInvestimentos-DEMO",
        "corretora": "Clear",
        "conta_demo": True,
        "build": 5000,
        "max_barras": 100000,
        "negociacao_algoritmica": False,
    }
    assert list(df.index.strftime("%Y-%m-%d %H:%M")) == ["2026-10-29 09:00", "2026-10-29 09:01"]
    assert df["real_volume"].tolist() == [20, 21]
    # o pedido vai em segundos (horário do servidor como UTC) e volta como lista simples
    pedido = next(c for c in conn.avaliado if "copy_rates_range" in c)
    assert "'WIN$N', mt5.TIMEFRAME_M1, 1793264400, 1793298600" in pedido and ".tolist()" in pedido
    assert conn.avaliado[-1] == "mt5.shutdown()"


def test_ponte_loga_a_conta_sem_expor_a_senha(monkeypatch):
    pytest.importorskip("rpyc")
    import rpyc

    from robob3.coleta import PonteMT5

    conn = ConexaoFalsa(logado=None)  # terminal reiniciou deslogado
    monkeypatch.setattr(rpyc.classic, "connect", lambda host, port: conn)
    with PonteMT5("mt5", 18812, conta=(1195572676, "s3nh@-demo", "ClearInvestimentos-DEMO")):
        pass
    assert conn.logins == [(1195572676, "s3nh@-demo", "ClearInvestimentos-DEMO")]
    assert "_robob3_conta" not in conn.namespace  # apagada depois do login
    assert not any("s3nh@-demo" in c for c in conn.avaliado + conn.executado)

    conn = ConexaoFalsa(logado=1195572676)  # já está na conta: não reloga
    monkeypatch.setattr(rpyc.classic, "connect", lambda host, port: conn)
    with PonteMT5("mt5", 18812, conta=(1195572676, "s3nh@-demo", "ClearInvestimentos-DEMO")):
        pass
    assert conn.logins == []


def test_conta_mt5_do_ambiente(monkeypatch):
    from robob3.cli import _conta_mt5

    for k in ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER"):
        monkeypatch.delenv(k, raising=False)
    assert _conta_mt5() is None
    monkeypatch.setenv("MT5_LOGIN", "1195572676")
    monkeypatch.setenv("MT5_SERVER", "ClearInvestimentos-DEMO")
    assert _conta_mt5() is None  # sem senha, não tenta logar
    monkeypatch.setenv("MT5_PASSWORD", "x")
    assert _conta_mt5() == (1195572676, "x", "ClearInvestimentos-DEMO")


def test_cli_gravar_m1_recusa_conta_que_nao_e_demo(tmp_path, monkeypatch, capsys):
    from robob3 import cli

    class PonteReal(FonteFalsa):
        def __init__(self, host, port, conta=None):
            super().__init__("2026-10-30 10:00")

        def info(self):
            return super().info() | {"conta_demo": False}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(cli, "PonteMT5", PonteReal)
    assert cli.main(["gravar-m1", "--destino", str(tmp_path), "--hoje", "2026-10-30"]) == 2
    assert "não é demo" in capsys.readouterr().out
    assert not (tmp_path / "registro.jsonl").exists()


def test_cli_gravar_m1(tmp_path, monkeypatch, capsys):
    from robob3 import cli

    class PonteFalsa(FonteFalsa):
        def __init__(self, host, port, conta=None):
            super().__init__("2026-10-30 10:00")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(cli, "PonteMT5", PonteFalsa)
    args = ["gravar-m1", "--destino", str(tmp_path), "--hoje", "2026-10-30"]
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "WIN$N: 3 dias novos, 1710 barras (2026-10-27 a 2026-10-29)" in out
    assert "1º dia descartado (corte): 2026-10-26" in out
