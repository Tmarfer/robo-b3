#!/usr/bin/env bash
# Instala Docker Engine + compose plugin pelo repositório oficial. Rodar como o usuário do projeto.
set -euo pipefail

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi

sudo usermod -aG docker "$USER"

# Rotação de logs dos containers (evita encher o disco)
if [[ ! -f /etc/docker/daemon.json ]]; then
  sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" }
}
EOF
  sudo systemctl restart docker
fi

docker --version || sudo docker --version
docker compose version || sudo docker compose version

echo
echo "Saia e entre de novo na sessão SSH para o grupo 'docker' valer; depois: docker run --rm hello-world"
