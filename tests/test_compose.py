import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).parents[1]
COMPOSE = yaml.safe_load((RAIZ / "docker-compose.yml").read_text())


def test_healthcheck_do_mt5_procura_a_porta_do_rpyc():
    # /proc/net/tcp lista as portas em hexadecimal: 18812 = 0x497C (0x4974 seria 18804)
    mt5 = COMPOSE["services"]["mt5"]
    porta = int(mt5["expose"][0])
    teste = " ".join(mt5["healthcheck"]["test"])
    (hexa,) = re.findall(r"':([0-9A-Fa-f]{4}) ", teste)
    assert int(hexa, 16) == porta == int(COMPOSE["services"]["coletor"]["environment"]["MT5_PORT"])


def test_mt5_tem_hostname_fixo():
    # sem isso, cada recriação do container apaga a conta salva no terminal
    assert COMPOSE["services"]["mt5"]["hostname"] == "mt5"


def test_mt5_usa_a_imagem_com_wine_novo():
    mt5 = COMPOSE["services"]["mt5"]
    assert mt5["build"] == "infra/mt5"
    arquivo = RAIZ / "infra/mt5/Dockerfile"
    if not arquivo.exists():  # imagem do lab só tem o compose
        pytest.skip("infra/mt5/Dockerfile fora da imagem")
    dockerfile = arquivo.read_text()
    assert "lprett/mt5linux@sha256:" in dockerfile  # base fixada por digest, nunca :latest
