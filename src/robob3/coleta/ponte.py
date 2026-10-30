"""Ponte Python <-> MT5 rodando no container `mt5` (imagem lprett/mt5linux), via RPyC clássico.

Não usa o cliente `mt5linux` 1.x, que tenta criar containers sozinho: conecta direto no servidor
RPyC da imagem (porta 18812, só na rede interna `trading`) e executa o pacote `MetaTrader5` lá.
Os resultados voltam como listas/dicionários simples (`.tolist()`, `._asdict()`), sem trafegar
objetos numpy entre versões diferentes de Python.

Somente leitura: este módulo não envia ordens.
"""

from __future__ import annotations

import calendar
from datetime import datetime

import pandas as pd

from robob3.data.mt5_csv import rates_para_df

CAMPOS_RATES = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
TIMEFRAMES = {1: "TIMEFRAME_M1", 5: "TIMEFRAME_M5", 15: "TIMEFRAME_M15"}


def _epoch(dt: datetime) -> int:
    """Horário do servidor (sem fuso) -> segundos, como o MT5 espera e devolve."""
    return calendar.timegm(dt.timetuple())


class PonteMT5:
    def __init__(self, host: str = "mt5", port: int = 18812, timeout: int = 120):
        self.host, self.port, self.timeout = host, port, timeout
        self._conn = None

    def conectar(self) -> PonteMT5:
        import rpyc  # dependência opcional: pip install ".[ponte]"

        self._conn = rpyc.classic.connect(self.host, self.port)
        self._conn._config["sync_request_timeout"] = self.timeout
        self._conn.execute("import sys; sys.path.append('C:\\\\mt5libs')")
        self._conn.execute("import MetaTrader5 as mt5")
        if not self._eval("mt5.initialize()"):
            raise ConnectionError(f"MT5 não inicializou: {self._eval('mt5.last_error()')}")
        return self

    def fechar(self) -> None:
        if self._conn is not None:
            try:
                self._eval("mt5.shutdown()")
            finally:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> PonteMT5:
        return self.conectar()

    def __exit__(self, *exc) -> None:
        self.fechar()

    def _eval(self, codigo: str):
        import rpyc

        return rpyc.classic.obtain(self._conn.eval(codigo))

    def info(self) -> dict:
        conta = self._eval("mt5.account_info()._asdict()")
        terminal = self._eval("mt5.terminal_info()._asdict()")
        return {
            "servidor": conta.get("server"),
            "corretora": conta.get("company"),
            "conta_demo": conta.get("trade_mode") == 0,  # ACCOUNT_TRADE_MODE_DEMO
            "build": terminal.get("build"),
            "max_barras": terminal.get("maxbars"),
            "negociacao_algoritmica": terminal.get("trade_allowed"),
        }

    def barras(self, simbolo: str, minutos: int, inicio: datetime, fim: datetime) -> pd.DataFrame:
        """Barras de `inicio` a `fim` (horário do servidor, inclusive)."""
        if not self._eval(f"mt5.symbol_select({simbolo!r}, True)"):
            raise ValueError(f"símbolo {simbolo!r} indisponível: {self._eval('mt5.last_error()')}")
        tf = f"mt5.{TIMEFRAMES[minutos]}"
        codigo = (
            f"(lambda r: None if r is None else r.tolist())"
            f"(mt5.copy_rates_range({simbolo!r}, {tf}, {_epoch(inicio)}, {_epoch(fim)}))"
        )
        linhas = self._eval(codigo)
        if linhas is None:
            raise RuntimeError(f"copy_rates_range falhou: {self._eval('mt5.last_error()')}")
        if not linhas:
            return pd.DataFrame(columns=CAMPOS_RATES[1:], index=pd.DatetimeIndex([], name="time"))
        return rates_para_df(pd.DataFrame(linhas, columns=CAMPOS_RATES))
