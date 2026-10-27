#!/usr/bin/env bash
# Deploy key somente leitura para a VPS puxar o repositório e clone em ~/robo-b3.
#   bash 02-github.sh DONO/robo-b3
set -euo pipefail

REPO="${1:?uso: $0 DONO/REPO}"
DESTINO="${DESTINO:-$HOME/robo-b3}"
CHAVE="$HOME/.ssh/robo-b3_deploy"
ALIAS="github-robo-b3"

mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"

if [[ ! -f $CHAVE ]]; then
  ssh-keygen -t ed25519 -N "" -C "deploy@$(hostname)" -f "$CHAVE"
fi

if ! grep -q "Host $ALIAS" "$HOME/.ssh/config" 2>/dev/null; then
  cat >> "$HOME/.ssh/config" <<EOF

Host $ALIAS
    HostName github.com
    User git
    IdentityFile $CHAVE
    IdentitiesOnly yes
EOF
  chmod 600 "$HOME/.ssh/config"
fi

ssh-keyscan -t ed25519 github.com 2>/dev/null >> "$HOME/.ssh/known_hosts"
sort -u -o "$HOME/.ssh/known_hosts" "$HOME/.ssh/known_hosts"

echo
echo "Cole esta chave em: https://github.com/$REPO/settings/keys  (Add deploy key, SEM write access)"
echo "------------------------------------------------------------------"
cat "$CHAVE.pub"
echo "------------------------------------------------------------------"
read -r -p "Depois de adicionar, pressione Enter para testar... "

# ssh -T no GitHub sempre sai com código 1, mesmo autenticado
saida=$(ssh -T "git@$ALIAS" 2>&1 || true)
grep -q "successfully authenticated" <<<"$saida" \
  || { echo "Falha na autenticação. Confira a deploy key."; echo "$saida"; exit 1; }

if [[ -d $DESTINO/.git ]]; then
  echo "Repositório já existe em $DESTINO."
else
  git clone "git@$ALIAS:$REPO.git" "$DESTINO"
fi

cd "$DESTINO"
# push via ForwardAgent (chave pessoal) quando editar pela VPS
git remote set-url --push origin "git@github.com:$REPO.git"
git config pull.ff only

[[ -f .env ]] || { cp .env.example .env; chmod 600 .env; }
[[ -f config/risk.yaml ]] || cp config/risk.example.yaml config/risk.yaml
mkdir -p data/raw data/processed logs

echo "OK: $DESTINO. Edite .env e config/risk.yaml conforme necessário."
