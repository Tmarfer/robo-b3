import re
from pathlib import Path

import yaml

COMPOSE = yaml.safe_load((Path(__file__).parents[1] / "docker-compose.yml").read_text())


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
