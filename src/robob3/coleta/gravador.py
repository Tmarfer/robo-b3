"""Gravador de M1: guarda o histórico que a janela do servidor vai descartando.

O servidor demo da Clear só entrega as últimas 100 mil barras de M1 (~8,5 meses). Rodando uma vez
por dia, este gravador acumula o M1 em disco, um arquivo Parquet por dia e por símbolo:

    {destino}/m1/{SIMBOLO}/{AAAA-MM-DD}.parquet       ex.: data/gravador/m1/WIN-N/2026-10-29.parquet
    {destino}/registro.jsonl                           uma linha por execução

Regras:
- grava só dias **completos** (até ontem, pelo relógio do servidor informado em `hoje`);
- **nunca sobrescreve** um dia já gravado (como data/raw);
- na primeira execução de um símbolo, descarta o 1º dia recebido: ele vem cortado pelo limite de
  barras do servidor.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd

from robob3.data.mt5_csv import escrever_barras_mt5


class Fonte(Protocol):
    def info(self) -> dict: ...

    def barras(
        self, simbolo: str, minutos: int, inicio: datetime, fim: datetime
    ) -> pd.DataFrame: ...


@dataclass
class DiaGravado:
    data: str
    barras: int
    primeira: str
    ultima: str
    sha256: str


@dataclass
class ResultadoSimbolo:
    simbolo: str
    novos: list[DiaGravado] = field(default_factory=list)
    descartado_corte: str | None = None  # 1º dia do backfill, cortado pelo limite do servidor
    erro: str | None = None


def pasta_simbolo(destino: Path, simbolo: str) -> Path:
    return Path(destino) / "m1" / re.sub(r"[^A-Za-z0-9]+", "-", simbolo).strip("-")


def dias_gravados(destino: Path, simbolo: str) -> list[date]:
    pasta = pasta_simbolo(destino, simbolo)
    return sorted(date.fromisoformat(p.stem) for p in pasta.glob("*.parquet"))


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _meses(inicio: date, fim: date):
    """Janelas de até um mês, para não pedir tudo de uma vez ao servidor."""
    a = inicio
    while a <= fim:
        b = min((pd.Timestamp(a) + pd.offsets.MonthEnd(0)).date(), fim)
        yield a, b
        a = b + timedelta(days=1)


def gravar_simbolo(
    fonte: Fonte, simbolo: str, destino: Path, hoje: date, backfill_dias: int = 400
) -> ResultadoSimbolo:
    res = ResultadoSimbolo(simbolo)
    existentes = dias_gravados(destino, simbolo)
    backfill = not existentes
    inicio = hoje - timedelta(days=backfill_dias) if backfill else existentes[-1] + timedelta(1)
    fim = hoje - timedelta(days=1)
    if inicio > fim:
        return res

    partes = []
    for a, b in _meses(inicio, fim):
        df = fonte.barras(
            simbolo,
            1,
            datetime.combine(a, datetime.min.time()),
            datetime.combine(b, datetime.max.time().replace(microsecond=0)),
        )
        if len(df):
            partes.append(df)
    if not partes:
        return res
    barras = pd.concat(partes).sort_index()
    barras = barras[~barras.index.duplicated(keep="first")]

    pasta = pasta_simbolo(destino, simbolo)
    pasta.mkdir(parents=True, exist_ok=True)
    ja = set(existentes)
    dias = sorted(barras.groupby(barras.index.normalize()), key=lambda x: x[0])
    for i, (dia, df_dia) in enumerate(dias):
        d = dia.date()
        if backfill and i == 0:
            res.descartado_corte = d.isoformat()
            continue
        if d in ja or d > fim:
            continue
        arquivo = pasta / f"{d.isoformat()}.parquet"
        df_dia.to_parquet(arquivo)
        res.novos.append(
            DiaGravado(
                data=d.isoformat(),
                barras=len(df_dia),
                primeira=df_dia.index[0].strftime("%H:%M"),
                ultima=df_dia.index[-1].strftime("%H:%M"),
                sha256=_sha256(arquivo),
            )
        )
    return res


def gravar_m1(
    fonte: Fonte,
    simbolos: list[str],
    destino: str | Path,
    hoje: date,
    backfill_dias: int = 400,
) -> dict:
    """Grava os símbolos e acrescenta o resumo da execução em `registro.jsonl`."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    registro = {
        "executado_em_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "hoje_servidor": hoje.isoformat(),
        "fonte": fonte.info(),
        "simbolos": {},
    }
    for simbolo in simbolos:
        try:
            r = gravar_simbolo(fonte, simbolo, destino, hoje, backfill_dias)
        except Exception as e:  # um símbolo com erro não impede os outros
            r = ResultadoSimbolo(simbolo, erro=f"{type(e).__name__}: {e}")
        registro["simbolos"][simbolo] = {
            "dias_novos": len(r.novos),
            "barras_novas": sum(d.barras for d in r.novos),
            "primeiro_novo": r.novos[0].data if r.novos else None,
            "ultimo_novo": r.novos[-1].data if r.novos else None,
            "descartado_corte": r.descartado_corte,
            "erro": r.erro,
            "dias": [asdict(d) for d in r.novos],
        }
    with (destino / "registro.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def status(destino: str | Path, simbolos: list[str], hoje: date) -> dict:
    """Resumo do que está gravado e há quantos dias úteis não grava."""
    out = {}
    for s in simbolos:
        dias = dias_gravados(Path(destino), s)
        if not dias:
            out[s] = {"dias": 0}
            continue
        uteis_sem = len(pd.bdate_range(dias[-1] + timedelta(1), hoje - timedelta(1)))
        out[s] = {
            "dias": len(dias),
            "primeiro": dias[0].isoformat(),
            "ultimo": dias[-1].isoformat(),
            "dias_uteis_sem_gravar": uteis_sem,
        }
    return out


def exportar(destino: str | Path, simbolo: str, saida: str | Path) -> int:
    """Junta os dias gravados num CSV no formato do export do MT5."""
    pasta = pasta_simbolo(Path(destino), simbolo)
    arquivos = sorted(pasta.glob("*.parquet"))
    if not arquivos:
        raise FileNotFoundError(f"nada gravado para {simbolo} em {pasta}")
    df = pd.concat(pd.read_parquet(a) for a in arquivos).sort_index()
    escrever_barras_mt5(df, saida)
    return len(df)
