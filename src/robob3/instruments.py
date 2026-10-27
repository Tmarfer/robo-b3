"""Especificações dos minicontratos (B3). Conferir periodicamente no site da B3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrumento:
    codigo: str
    tick: float  # variação mínima de preço, em pontos
    valor_ponto_brl: float  # R$ por ponto por contrato

    @property
    def valor_tick_brl(self) -> float:
        return self.tick * self.valor_ponto_brl

    def resultado_brl(self, pontos: float, contratos: int = 1) -> float:
        """Resultado bruto (antes de custos) de `pontos` a favor (+) ou contra (-)."""
        return pontos * self.valor_ponto_brl * contratos


WIN = Instrumento("WIN", tick=5.0, valor_ponto_brl=0.20)
WDO = Instrumento("WDO", tick=0.5, valor_ponto_brl=10.0)

INSTRUMENTOS = {i.codigo: i for i in (WIN, WDO)}
