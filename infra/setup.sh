#!/usr/bin/env bash
# One-time setup of the Tau HUD live backend on a fresh Ubuntu 24.04 server.
# Run as root:
#   curl -fsSL https://raw.githubusercontent.com/jimb000o/tau-command-hud/main/infra/setup.sh | bash
# Re-running it is safe; it updates the checkout and restarts the stack.
set -euo pipefail

RELAY_DOMAIN="${RELAY_DOMAIN:-node.tauhud.com}"
REPO="${REPO:-https://github.com/jimb000o/tau-command-hud.git}"
DIR=/opt/tau-command-hud

[[ $EUID -eq 0 ]] || { echo "Please run as root."; exit 1; }
export DEBIAN_FRONTEND=noninteractive

echo "==> System packages and automatic security updates"
apt-get update -q
apt-get install -yq ca-certificates curl git ufw unattended-upgrades

if ! command -v docker >/dev/null; then
  echo "==> Docker (official repository)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

# 8 GB swap: a tau-lang translation unit can need more than 3 GB, and a 4 GB
# box with 4 GB swap still froze. A smaller /swapfile from an earlier run is
# grown in place.
SWAP_GB=8
swap_bytes=$(stat -c %s /swapfile 2>/dev/null || echo 0)
if [[ $swap_bytes -lt $((SWAP_GB * 1024 * 1024 * 1024)) ]]; then
  echo "==> ${SWAP_GB} GB swap"
  swapoff /swapfile 2>/dev/null || true
  rm -f /swapfile
  fallocate -l "${SWAP_GB}G" /swapfile && chmod 600 /swapfile && mkswap -q /swapfile && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
# Compile jobs: the build thrashes with 2 on 4 GB, whatever .env says.
export TAU_BUILD_JOBS="${TAU_BUILD_JOBS:-1}"

echo "==> Firewall: SSH, HTTP(S), Tau P2P"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw allow 4001/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> Checkout in $DIR"
if [[ -d $DIR/.git ]]; then git -C "$DIR" pull --ff-only; else git clone --depth 1 "$REPO" "$DIR"; fi
cd "$DIR/infra"
if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i "s/^RELAY_DOMAIN=.*/RELAY_DOMAIN=${RELAY_DOMAIN}/" .env
fi

echo "==> Building and starting (first build compiles tau-lang: 1-2 hours with ${TAU_BUILD_JOBS} job)"
docker compose up -d --build

IP=$(curl -fsS4 https://ifconfig.me || echo "<server IP>")
cat <<MSG

Done. The node now syncs the testnet in the background.
  1. DNS: A record  ${RELAY_DOMAIN%%.*}  ->  ${IP}  (Caddy fetches the TLS certificate by itself once it resolves)
  2. Check:  curl https://${RELAY_DOMAIN}/status
  3. Logs:   cd $DIR/infra && docker compose logs -f
MSG
