#!/usr/bin/env bash
# Roda um comando do laboratório com a imagem do commit atual e o hash gravado no manifesto.
#   infra/vps/lab.sh backtest-orb data/raw/WIN-N_M5_clear-mt5_20261030.csv --grade
# O container não tem .git: o hash vai por variável. A imagem é reconstruída antes (rápido com
# cache), para o código que roda ser o do commit registrado.
set -euo pipefail

cd "$(dirname "$0")/../.."
commit=$(git rev-parse HEAD)
if [ -n "$(git status --porcelain -- src config pyproject.toml)" ]; then
  alterado=1
  echo "AVISO: código alterado e não commitado; o manifesto vai marcar codigo_alterado=true" >&2
else
  alterado=0
fi

docker compose build -q lab
exec docker compose run --rm -e ROBOB3_COMMIT="$commit" -e ROBOB3_ALTERADO="$alterado" lab "$@"
