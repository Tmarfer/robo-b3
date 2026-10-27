import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from robob3.config import ConfigRisco, carregar_config
from robob3.instruments import WDO, WIN
from robob3.signals import Acao, ValidadorSinais

BRT = timezone(timedelta(hours=-3))
AGORA = datetime(2026, 10, 26, 14, 32, 10, tzinfo=BRT)
EXEMPLO = Path(__file__).parents[1] / "config" / "risk.example.yaml"


def sinal(**over):
    base = {
        "id": str(uuid.uuid4()),
        "ts": "2026-10-26T14:32:05-03:00",
        "ativo": "WIN",
        "acao": "DESARMAR",
        "intensidade": 1.0,
        "nova_meta_pts": None,
        "validade_s": 300,
        "confianca": 0.82,
        "motivo": "Copom surpreende com alta de 50 bps",
        "fonte": "https://exemplo/noticia",
    }
    return base | over


@pytest.fixture
def validador():
    return ValidadorSinais({Acao.DESARMAR, Acao.REDUZIR}, confianca_minima=0.7, max_sinais_hora=2)


def test_aceita_sinal_valido(validador):
    d = validador.validar(sinal(), AGORA)
    assert d.aceito, d.motivo


@pytest.mark.parametrize(
    "over, motivo",
    [
        ({"acao": "AMPLIAR"}, "não permitida"),
        ({"acao": "REARMAR"}, "não permitida"),
        ({"confianca": 0.5}, "abaixo do mínimo"),
        ({"ts": "2026-10-26T14:00:00-03:00"}, "expirado"),
        ({"ts": "2026-10-26T14:40:00-03:00"}, "futuro"),
        ({"ts": "2026-10-26T14:32:05"}, "schema"),  # sem fuso
        ({"extra": 1}, "schema"),
        ({"intensidade": 2}, "schema"),
    ],
)
def test_rejeicoes(validador, over, motivo):
    d = validador.validar(sinal(**over), AGORA)
    assert not d.aceito and motivo in d.motivo


def test_idempotencia_e_json(validador):
    import json

    s = json.dumps(sinal())
    assert validador.validar(s, AGORA).aceito
    assert validador.validar(s, AGORA).motivo == "id repetido"
    assert "schema" in validador.validar("{nao json", AGORA).motivo


def test_rate_limit_janela_de_uma_hora(validador):
    assert validador.validar(sinal(), AGORA).aceito
    assert validador.validar(sinal(), AGORA).aceito
    assert "limite" in validador.validar(sinal(), AGORA).motivo
    depois = AGORA + timedelta(hours=1, seconds=1)
    assert validador.validar(sinal(ts=depois.isoformat()), depois).aceito


def test_config_exemplo_valida():
    cfg = carregar_config(EXEMPLO)
    assert cfg.modo == "demo"
    assert set(cfg.sinais_ia.acoes_permitidas) == {Acao.DESARMAR, Acao.REDUZIR}


def _cfg(**over):
    dados = yaml.safe_load(EXEMPLO.read_text(encoding="utf-8"))
    for chave, valor in over.items():
        alvo = dados
        *caminho, ultima = chave.split(".")
        for parte in caminho:
            alvo = alvo[parte]
        alvo[ultima] = valor
    return dados


@pytest.mark.parametrize(
    "over",
    [
        {"modo": "real"},
        {"sinais_ia.acoes_permitidas": ["DESARMAR", "AMPLIAR"]},
        {"horario.zeragem": "16:00"},
        {"limites.WIN.max_contratos": 50},
    ],
)
def test_config_recusa_valores_perigosos(over):
    with pytest.raises(ValidationError):
        ConfigRisco.model_validate(_cfg(**over))


def test_instrumentos():
    assert WIN.resultado_brl(-100) == pytest.approx(-20.0)
    assert WDO.resultado_brl(5) == pytest.approx(50.0)
    assert WIN.valor_tick_brl == pytest.approx(1.0)
    assert WDO.valor_tick_brl == pytest.approx(5.0)
