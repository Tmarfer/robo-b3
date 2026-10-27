#!/usr/bin/env bash
# Atualiza o código na VPS a partir do GitHub, reconstrói o lab e roda os testes.
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
  echo "Há alterações locais não commitadas. Faça commit/push ou descarte antes do deploy."
  git status --short
  exit 1
fi

dia=$(date +%u); hora=$(date +%H%M)
if (( dia <= 5 && 10#$hora >= 845 && 10#$hora <= 1830 )) && docker compose ps --services --status running | grep -qx mt5; then
  read -r -p "Pregão em andamento e MT5 rodando. Continuar mesmo assim? [s/N] " r
  [[ $r == s ]] || exit 1
fi

antes=$(git rev-parse --short HEAD)
git pull --ff-only
depois=$(git rev-parse --short HEAD)

if [[ $antes == "$depois" ]]; then
  echo "Já atualizado ($depois)."
else
  echo "Atualizado: $antes -> $depois"
  git log --oneline "$antes..$depois"
fi

docker compose build lab
docker compose run --rm --entrypoint pytest lab -q
