#!/usr/bin/env bash
# Retrato da VPS para registrar no Notion. Somente leitura.
set -uo pipefail

secao() { printf '\n## %s\n' "$*"; }

echo "# Diagnóstico VPS — $(date '+%F %T %Z')"

secao "Sistema"
. /etc/os-release && echo "$PRETTY_NAME | kernel $(uname -r)"
echo "uptime: $(uptime -p)"

secao "CPU"
nproc --all | sed 's/^/vCPUs: /'
grep -m1 'model name' /proc/cpuinfo
if grep -qE 'vmx|svm' /proc/cpuinfo; then
  echo "Virtualização aninhada: flags vmx/svm PRESENTES (VM Windows talvez possível — testar)"
else
  echo "Virtualização aninhada: flags vmx/svm AUSENTES (VM Windows na VPS inviável)"
fi

secao "Memória e disco"
free -h
swapon --show
df -h / | tail -1

secao "Hora"
timedatectl | grep -E 'Time zone|synchronized|NTP'

secao "Rede"
echo "IP público: $(curl -s --max-time 5 https://ifconfig.me || echo '?')"
for host in github.com api.anthropic.com; do
  t=$(curl -s -o /dev/null -w '%{time_connect}' --max-time 5 "https://$host" || echo '?')
  echo "conexão TCP $host: ${t}s"
done

secao "Portas escutando (fora de 127.0.0.1 = exposto)"
ss -tlnH | awk '{print $4}' | sort -u

secao "Firewall"
sudo -n ufw status 2>/dev/null || echo "(rode com sudo para ver o ufw)"

secao "Docker"
if command -v docker >/dev/null; then
  docker --version
  docker compose version
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
  echo
  echo "Memória por container:"
  docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
  echo
  echo "Portas publicadas em todas as interfaces (abertas à internet, passam por fora do ufw):"
  docker ps --format '{{.Names}}: {{.Ports}}' | grep -E '0\.0\.0\.0:|\[::\]:|:::' || echo "nenhuma"
else
  echo "Docker não instalado"
fi

secao "Repositório"
if [[ -d $HOME/robo-b3/.git ]]; then
  git -C "$HOME/robo-b3" log -1 --format='%h %s (%cr)'
  git -C "$HOME/robo-b3" status --short | head
fi
