#!/usr/bin/env bash
# Roda o gravador de M1 uma vez (dias completos até ontem). Para o cron do usuário robo:
#   15 8 * * 1-6  /home/robo/robo-b3/infra/vps/gravador-cron.sh
# Seg-sáb às 08:15: grava o pregão anterior antes da abertura. Sábado recupera a sexta.
set -uo pipefail

cd "$(dirname "$0")/../.."
mkdir -p logs
exec 9>logs/.gravador.lock
flock -n 9 || { echo "$(date -Is) já em execução, saindo" >> logs/gravador.log; exit 0; }

{
  echo "=== $(date -Is) gravar-m1"
  docker compose --profile mt5 run --rm coletor
  codigo=$?
  echo "=== $(date -Is) fim (código $codigo)"
} >> logs/gravador.log 2>&1

exit "$codigo"
