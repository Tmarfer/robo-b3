#!/usr/bin/env bash
# Preparação inicial da VPS (Ubuntu 22.04/24.04). Rodar como root. Pode ser repetido.
#   NOVO_USUARIO=robo TZ_LOCAL=America/Sao_Paulo SWAP_GB=2 bash 00-bootstrap.sh
set -euo pipefail

NOVO_USUARIO="${NOVO_USUARIO:-robo}"
TZ_LOCAL="${TZ_LOCAL:-America/Sao_Paulo}"
SWAP_GB="${SWAP_GB:-2}"

log() { printf '\n==> %s\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "Rode como root."; exit 1; }
. /etc/os-release
[[ ${ID:-} == ubuntu ]] || echo "Aviso: testado apenas em Ubuntu (detectado: ${ID:-?})."

log "Pacotes"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y upgrade
apt-get -y install ca-certificates curl git ufw fail2ban unattended-upgrades \
  htop jq make rsync netcat-openbsd

log "Fuso horário e NTP"
timedatectl set-timezone "$TZ_LOCAL"
timedatectl set-ntp true || echo "Aviso: NTP não pôde ser ativado pelo timedatectl."

log "Usuário $NOVO_USUARIO"
if ! id "$NOVO_USUARIO" &>/dev/null; then
  adduser --disabled-password --gecos "" "$NOVO_USUARIO"
  usermod -aG sudo "$NOVO_USUARIO"
  echo "Defina a senha que $NOVO_USUARIO usará no sudo:"
  passwd "$NOVO_USUARIO"
fi

HOME_U="/home/$NOVO_USUARIO"
install -d -m 700 -o "$NOVO_USUARIO" -g "$NOVO_USUARIO" "$HOME_U/.ssh"
touch "$HOME_U/.ssh/authorized_keys"
if [[ -s /root/.ssh/authorized_keys ]]; then
  cat /root/.ssh/authorized_keys "$HOME_U/.ssh/authorized_keys" | sort -u > "$HOME_U/.ssh/ak.tmp"
  mv "$HOME_U/.ssh/ak.tmp" "$HOME_U/.ssh/authorized_keys"
fi
chown "$NOVO_USUARIO:$NOVO_USUARIO" "$HOME_U/.ssh/authorized_keys"
chmod 600 "$HOME_U/.ssh/authorized_keys"

log "SSH"
if [[ -s $HOME_U/.ssh/authorized_keys ]]; then
  # Nome 00-* de propósito: no sshd vale o PRIMEIRO valor lido, e o Ubuntu traz 50-cloud-init.conf
  # com PasswordAuthentication yes.
  cat > /etc/ssh/sshd_config.d/00-robo-b3.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
  sshd -t
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
  echo "Login por senha desativado; somente chave."
else
  echo "ATENÇÃO: nenhuma chave em authorized_keys — login por senha MANTIDO."
  echo "Adicione sua chave (hPanel > Chaves SSH) e rode este script de novo."
fi

log "Firewall (ufw): somente SSH"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

log "fail2ban e atualizações de segurança automáticas (sem reboot automático)"
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

log "Swap"
if [[ -z $(swapon --show --noheadings) ]]; then
  fallocate -l "${SWAP_GB}G" /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl -w vm.swappiness=10
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-robo-b3.conf
else
  echo "Swap já existe:"; swapon --show
fi

log "Pronto"
cat <<EOF
Próximos passos:
  1. NÃO feche esta sessão. Em outro terminal teste:  ssh $NOVO_USUARIO@<IP>  (ou o alias robo-b3)
  2. Se funcionar, siga docs/vps-setup.md a partir do passo 3 (Antigravity) e 4 (Docker).
  3. Se houver atualização de kernel pendente, reinicie fora do pregão: sudo reboot
EOF
