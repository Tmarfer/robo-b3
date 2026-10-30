"""Manifesto de uma rodada de backtest: tudo o que é preciso para refazê-la e conferi-la.

Cada execução de `robob3 backtest-orb` grava um JSON em `data/backtests/` (versionado no GitHub):

    data/backtests/{estrategia}_{trecho}_{ambiguidade}_{AAAAMMDD-HHMMSS}.json

Uma linha por combinação de parâmetros, nunca só a "melhor": a escolha é feita pela regra da
especificação, escrita antes do teste. As linhas do DB Backtests no Notion saem deste arquivo.

O commit vem de `ROBOB3_COMMIT` (o container não tem .git; `infra/vps/lab.sh` preenche) ou, fora
do container, do próprio git. `ROBOB3_ALTERADO=1` marca código com mudanças não commitadas.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

VERSAO_MANIFESTO = 1


def commit_atual() -> dict:
    """Hash completo do commit e se havia código alterado fora dele."""
    commit, alterado = (
        os.environ.get("ROBOB3_COMMIT", "").strip(),
        os.environ.get("ROBOB3_ALTERADO", "").strip(),
    )
    if not commit:
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            sujo = subprocess.run(
                ["git", "status", "--porcelain", "--", "src", "config", "pyproject.toml"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            alterado = "1" if sujo else "0"
        except (OSError, subprocess.CalledProcessError):
            commit = ""
    return {
        "commit": commit or None,
        "codigo_alterado": {"1": True, "0": False}.get(alterado),  # None = não se sabe
    }


def montar_manifesto(
    *,
    estrategia: str,
    ativo: str,
    timeframe: str,
    trecho: str,
    periodo: tuple[str, str],
    dados: dict,
    custos: dict,
    ambiguidade: str,
    linhas: list[dict],
    comando: list[str],
    aleatorio: dict | None = None,
) -> dict:
    return {
        "versao_manifesto": VERSAO_MANIFESTO,
        "gerado_em_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "estrategia": estrategia,
        "ativo": ativo,
        "timeframe": timeframe,
        "trecho": trecho,  # desenvolvimento | fora-da-amostra | walk-forward
        "periodo": {"inicio": periodo[0], "fim": periodo[1]},
        "codigo": commit_atual(),
        "dados": dados,  # arquivo, sha256, barras, primeira e última barra
        "custos": custos,  # custo por lado, derrapagem, valor do ponto, sensibilidade
        "ambiguidade": ambiguidade,
        "entrada_aleatoria": aleatorio,  # sorteios e semente; percentil fica em cada linha
        "comando": comando,
        "linhas": linhas,
    }


def gravar_manifesto(manifesto: dict, pasta: str | Path) -> Path:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    nome = f"{manifesto['estrategia']}_{manifesto['trecho']}_{manifesto['ambiguidade']}_{carimbo}"
    destino = pasta / f"{nome}.json"
    destino.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return destino
