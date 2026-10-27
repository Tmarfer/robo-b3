"""Ponte de sinais IA -> execução: formato do sinal e validador.

A IA nunca envia ordens; emite sinais que o script valida. Na v1 só são aceitas ações que
reduzem risco (DESARMAR, REDUZIR) — ver `acoes_permitidas` em config/risk.yaml.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError


class Acao(StrEnum):
    DESARMAR = "DESARMAR"
    REDUZIR = "REDUZIR"
    AJUSTAR_META = "AJUSTAR_META"
    AMPLIAR = "AMPLIAR"
    REARMAR = "REARMAR"


class Sinal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    ts: AwareDatetime
    ativo: Literal["WIN", "WDO", "AMBOS"]
    acao: Acao
    intensidade: float = Field(ge=0, le=1)
    nova_meta_pts: float | None = None
    validade_s: int = Field(gt=0, le=3600)
    confianca: float = Field(ge=0, le=1)  # autodeclarada pelo modelo; não é probabilidade calibrada
    motivo: str = Field(min_length=1, max_length=500)
    fonte: str = Field(min_length=1)


@dataclass(frozen=True)
class Decisao:
    aceito: bool
    motivo: str
    sinal: Sinal | None = None


class ValidadorSinais:
    """Valida sinais em ordem: schema, ação permitida, idempotência, validade, confiança, taxa."""

    TOLERANCIA_FUTURO = timedelta(seconds=5)

    def __init__(
        self,
        acoes_permitidas: set[Acao],
        confianca_minima: float,
        max_sinais_hora: int,
    ) -> None:
        self.acoes_permitidas = set(acoes_permitidas)
        self.confianca_minima = confianca_minima
        self.max_sinais_hora = max_sinais_hora
        self._vistos: set[UUID] = set()
        self._aceitos: deque[datetime] = deque()

    def validar(self, payload: str | bytes | dict, agora: datetime) -> Decisao:
        try:
            dados = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
            sinal = Sinal.model_validate(dados)
        except (ValidationError, json.JSONDecodeError, TypeError) as e:
            return Decisao(False, f"schema inválido: {e}")

        if sinal.id in self._vistos:
            return Decisao(False, "id repetido", sinal)
        self._vistos.add(sinal.id)

        if sinal.acao not in self.acoes_permitidas:
            return Decisao(False, f"ação {sinal.acao.value} não permitida", sinal)
        if sinal.ts > agora + self.TOLERANCIA_FUTURO:
            return Decisao(False, "timestamp no futuro", sinal)
        if agora > sinal.ts + timedelta(seconds=sinal.validade_s):
            return Decisao(False, "sinal expirado", sinal)
        if sinal.confianca < self.confianca_minima:
            return Decisao(False, f"confiança {sinal.confianca} abaixo do mínimo", sinal)

        uma_hora_atras = agora - timedelta(hours=1)
        while self._aceitos and self._aceitos[0] <= uma_hora_atras:
            self._aceitos.popleft()
        if len(self._aceitos) >= self.max_sinais_hora:
            return Decisao(False, "limite de sinais por hora atingido", sinal)

        self._aceitos.append(agora)
        return Decisao(True, "aceito", sinal)
