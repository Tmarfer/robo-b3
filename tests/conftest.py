from pathlib import Path

import pytest

CABECALHO = "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>"


def linha(data: str, hora: str, o, h, low, c, tv=10, v=20, s=0) -> str:
    return f"{data}\t{hora}\t{o}\t{h}\t{low}\t{c}\t{tv}\t{v}\t{s}"


@pytest.fixture
def csv_mt5(tmp_path: Path):
    """Escreve um CSV no formato do MT5 (UTF-16, tabulação) e devolve o caminho."""

    def _escrever(linhas: list[str], encoding: str = "utf-16") -> Path:
        p = tmp_path / "barras.csv"
        p.write_text("\n".join([CABECALHO, *linhas]) + "\n", encoding=encoding)
        return p

    return _escrever
