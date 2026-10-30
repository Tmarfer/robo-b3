#!/usr/bin/env bash
# Roda o Codex sem supervisão com uma tarefa escrita (arquivo .md) e guarda o relatório em logs/.
#   infra/vps/codex-agendado.sh infra/vps/tarefas/2026-10-31-login-mt5.md
# Agendar uma única vez no cron do usuário robo (ex.: 31/10 às 08:30):
#   30 8 31 10 * /home/robo/robo-b3/infra/vps/codex-agendado.sh infra/vps/tarefas/2026-10-31-login-mt5.md
# Ao terminar, a própria linha da tarefa sai do crontab (não roda de novo no ano seguinte).
set -uo pipefail

cd "$(dirname "$0")/../.."
tarefa="$1"
nome=$(basename "$tarefa" .md)
mkdir -p logs
# o cron não carrega o PATH do usuário: incluir onde o npm costuma instalar o codex
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

exec 9>logs/.codex.lock
flock -n 9 || { echo "$(date -Is) codex já em execução, saindo" >> "logs/codex-$nome.log"; exit 0; }
# espera o gravador das 08:15 terminar, se ainda estiver rodando
flock -w 1800 logs/.gravador.lock true

{
  echo "=== $(date -Is) codex exec: $tarefa"
  codex exec --dangerously-bypass-approvals-and-sandbox -C "$PWD" \
    --output-last-message "logs/codex-$nome.md" "$(cat "$tarefa")"
  codigo=$?
  echo "=== $(date -Is) fim (código $codigo); relatório: logs/codex-$nome.md"
} >> "logs/codex-$nome.log" 2>&1

crontab -l 2>/dev/null | grep -vF "$tarefa" | crontab -
exit "${codigo:-1}"
