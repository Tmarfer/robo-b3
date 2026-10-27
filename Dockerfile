# Imagem do laboratório Python (dados, backtest). Não contém MT5.
FROM python:3.12-slim

ENV TZ=America/Sao_Paulo \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[dev]"

COPY tests ./tests
COPY config ./config

RUN useradd --create-home --uid 1000 robo && mkdir -p data logs && chown -R robo /app
USER robo

ENTRYPOINT ["robob3"]
CMD ["--help"]
