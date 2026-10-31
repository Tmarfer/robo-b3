#!/usr/bin/env bash
# Confere se o MT5 está logado na conta demo (título da janela) e avisa se não estiver.
# Cron do usuário robo, antes do gravador:  0 8 * * 1-6 /home/robo/robo-b3/infra/vps/mt5-login-check.sh
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p logs
login=$(grep -E '^MT5_LOGIN=' .env 2>/dev/null | tail -1 | cut -d= -f2-)
titulos=$(docker exec -e DISPLAY=:0 mt5 sh -c \
  'for w in $(xdotool search --onlyvisible --name "."); do xdotool getwindowname "$w"; done' 2>&1)
if [ -n "$login" ] && printf '%s\n' "$titulos" | grep -q "^${login} - "; then
  echo "$(date -Is) logado" >> logs/mt5-login.log
  exit 0
fi
echo "$(date -Is) DESLOGADO | janelas: $(printf '%s' "$titulos" | tr '\n' '|')" >> logs/mt5-login.log
infra/vps/avisar.sh "MT5 sem a conta demo logada ($(date '+%d/%m %H:%M')). Logar pela tela (noVNC)."
exit 1
