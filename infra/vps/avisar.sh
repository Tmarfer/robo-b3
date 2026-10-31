#!/usr/bin/env bash
# Manda um aviso no Telegram (se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID estiverem no .env) e
# registra em logs/avisos.log. Uso: infra/vps/avisar.sh "texto"
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p logs
texto="Robô B3 (VPS): $1"
echo "$(date -Is) $texto" >> logs/avisos.log
valor() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2-; }
token=$(valor TELEGRAM_BOT_TOKEN); chat=$(valor TELEGRAM_CHAT_ID)
[ -n "$token" ] && [ -n "$chat" ] || exit 0
curl -fsS -m 20 "https://api.telegram.org/bot${token}/sendMessage" \
  --data-urlencode "chat_id=${chat}" --data-urlencode "text=${texto}" >/dev/null \
  || echo "$(date -Is) falha ao enviar o aviso" >> logs/avisos.log
