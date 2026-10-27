"""Configuração de risco (config/risk.yaml).

Os limites daqui são rígidos: nem a estratégia nem a IA podem alterá-los em tempo de execução.
"""

from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from robob3.signals import Acao


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LimiteAtivo(_Estrito):
    max_contratos: int = Field(ge=0, le=5)


class Horario(_Estrito):
    inicio_entradas: time
    fim_entradas: time
    zeragem: time

    @model_validator(mode="after")
    def _ordem(self) -> Horario:
        if not self.inicio_entradas < self.fim_entradas < self.zeragem:
            raise ValueError("esperado inicio_entradas < fim_entradas < zeragem")
        return self


class SinaisIA(_Estrito):
    acoes_permitidas: list[Acao]
    confianca_minima: float = Field(ge=0, le=1)
    max_sinais_hora: int = Field(ge=0)

    @model_validator(mode="after")
    def _somente_reduz_risco(self) -> SinaisIA:
        proibidas = {Acao.AMPLIAR, Acao.REARMAR} & set(self.acoes_permitidas)
        if proibidas:
            nomes = sorted(a.value for a in proibidas)
            raise ValueError(f"v1: IA não pode {nomes} — remover de acoes_permitidas")
        return self


class ConfigRisco(_Estrito):
    # Único modo existente nesta fase. Operação real exige decisão explícita e revisão do código.
    modo: Literal["demo"]
    limites: dict[Literal["WIN", "WDO"], LimiteAtivo]
    perda_maxima_diaria_brl: float = Field(gt=0)
    horario: Horario
    sinais_ia: SinaisIA


def carregar_config(caminho: str | Path = "config/risk.yaml") -> ConfigRisco:
    with Path(caminho).open(encoding="utf-8") as f:
        return ConfigRisco.model_validate(yaml.safe_load(f))
