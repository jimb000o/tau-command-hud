#!/usr/bin/env bash
# Tau node operator kit: one command from a fresh Ubuntu/Debian server to a
# synced tau-testnet-v2 node (the same patched node that runs tauhud.com).
#
#   curl -fsSL https://raw.githubusercontent.com/jimb000o/tau-command-hud/main/kit/install.sh | sudo NODE_NAME=my-node bash
#
# Options, as environment variables (all optional):
#   NODE_NAME=my-node        list the node on tauhud.com/stats ("community nodes")
#   PUBLIC_DOMAIN=tau.example.org   also serve a public read-only relay over HTTPS
#   TAU_BUILD_JOBS=2         parallel compile jobs (default: 1 below 8 GB RAM)
#   FORCE=1                  install although the server looks too small
# Re-running it is safe: it updates the kit and keeps the chain data and keys.
# Host preparation mirrors ../infra/setup.sh (tauhud.com's own server).
set -euo pipefail

REPO="${REPO:-https://github.com/jimb000o/tau-command-hud.git}"
BRANCH="${BRANCH:-main}"
DIR="${KIT_DIR:-/opt/tau-node-kit}"

say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nError: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "please run as root (sudo)."
[[ -d /opt/tau-command-hud/infra ]] && die "this server runs tauhud.com's own stack (/opt/tau-command-hud); use infra/setup.sh there."
. /etc/os-release
[[ "$ID" == ubuntu || "$ID" == debian ]] || die "Ubuntu or Debian needed, found $ID."
case "$(uname -m)" in x86_64|aarch64) ;; *) die "x86_64 or arm64 needed, found $(uname -m)." ;; esac
if [[ -n "${NODE_NAME:-}" && ! "$NODE_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,23}$ ]]; then
  die "NODE_NAME: 1-24 of A-Z a-z 0-9 . _ - , starting with a letter or digit."
fi

# Only with a name (the same opt-in as the node's reports): tell tauhud.com how far this setup gets, so the Nodes view
# on tauhud.com/meta/ can show where setups stop. Sent: a random install id made on this server, the step and the
# seconds since the script began. No address is kept. Without NODE_NAME nothing is sent.
T0=$(date +%s); STEP=start; IID=
if [[ -n "${NODE_NAME:-}" ]]; then
  mkdir -p /var/lib/tau-node-kit
  [[ -s /var/lib/tau-node-kit/install-id ]] || od -An -N8 -tx1 /dev/urandom | tr -d ' \n' > /var/lib/tau-node-kit/install-id
  IID=$(cat /var/lib/tau-node-kit/install-id)
fi
ping_step() {  # step [failed at]
  [[ -n "$IID" ]] && command -v curl >/dev/null || return 0
  curl -fsS -m 5 -o /dev/null "https://node.tauhud.com/setup?i=$IID&s=$1&t=$(( $(date +%s) - T0 ))${2:+&at=$2}" 2>/dev/null || true
}
step() { STEP=$1; ping_step "$1"; }
trap 'rc=$?; [[ $rc -eq 0 ]] || ping_step fail "$STEP"' EXIT
step start

say "Checking the server"
ram_gb=$(awk '/MemTotal/ {printf "%d", $2/1024/1024 + 0.5}' /proc/meminfo)
cpus=$(nproc)
disk_gb=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
echo "    ${cpus} CPU, ${ram_gb} GB RAM, ${disk_gb} GB free disk"
if [[ $ram_gb -lt 4 || $cpus -lt 2 || ( $disk_gb -lt 30 && ! -d $DIR ) ]]; then
  [[ "${FORCE:-}" == 1 ]] || die "needs 2 CPU, 4 GB RAM and 30 GB free disk (40 GB disk). FORCE=1 to try anyway."
fi
export DEBIAN_FRONTEND=noninteractive

say "System packages and automatic security updates"
apt-get update -q
apt-get install -yq ca-certificates curl git ufw unattended-upgrades
step packages

if ! command -v docker >/dev/null; then
  say "Docker (official repository)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
step docker

# Keep the tau-lang build layers in the BuildKit cache (otherwise an unrelated
# change rebuilds tau-lang for ~90 minutes), but cap the cache so it cannot
# fill a 40 GB disk. Only written if the server has no Docker daemon config.
if [[ ! -s /etc/docker/daemon.json ]]; then
  mkdir -p /etc/docker
  echo '{"builder": {"gc": {"enabled": true, "defaultKeepStorage": "12GB"}}}' > /etc/docker/daemon.json
  systemctl restart docker
fi

# The one-time tau-lang compile needs more than 3 GB for a single file: below
# 12 GB RAM, make sure there is 8 GB of swap.
if [[ $ram_gb -lt 12 ]]; then
  swap_gb=$(awk '/SwapTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
  if [[ $swap_gb -lt 7 ]]; then
    say "8 GB swap file"
    swapoff /swapfile 2>/dev/null || true
    rm -f /swapfile
    fallocate -l 8G /swapfile && chmod 600 /swapfile && mkswap -q /swapfile && swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
fi

say "Firewall: SSH and Tau P2P${PUBLIC_DOMAIN:+, HTTP(S) for $PUBLIC_DOMAIN}"
ufw allow OpenSSH >/dev/null
ufw allow 4001/tcp >/dev/null
if [[ -n "${PUBLIC_DOMAIN:-}" ]]; then ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; fi
ufw --force enable >/dev/null

say "Kit in $DIR"
if [[ -d $DIR/.git ]]; then
  git -C "$DIR" fetch -q --depth 1 origin "$BRANCH" && git -C "$DIR" reset -q --hard FETCH_HEAD
else
  git clone -q --depth 1 --branch "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR/kit"
[[ -f .env ]] || cp .env.example .env
setenv() {  # key value: set or replace one line in .env
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
# The node follows the tau-testnet commit tauhud.com runs, not an old .env.
setenv TAU_TESTNET_REF "$(grep '^TAU_TESTNET_REF=' ../infra/.env.example | cut -d= -f2)"
if [[ -n "${NODE_NAME:-}" ]]; then setenv NODE_NAME "$NODE_NAME"; fi
if [[ -n "${PUBLIC_DOMAIN:-}" ]]; then setenv PUBLIC_DOMAIN "$PUBLIC_DOMAIN"; setenv COMPOSE_PROFILES public; fi
if [[ -n "${TAU_BUILD_JOBS:-}" ]]; then setenv TAU_BUILD_JOBS "$TAU_BUILD_JOBS"
elif [[ $ram_gb -ge 8 ]] && grep -q '^TAU_BUILD_JOBS=1$' .env; then setenv TAU_BUILD_JOBS 2; fi

step kit
say "Building and starting (the first build compiles tau-lang: about 1.5 hours on 2 CPU / 4 GB)"
step build
docker compose up -d --build
step up
docker image prune -f >/dev/null   # each rebuild leaves the previous image behind

name=$(grep '^NODE_NAME=' .env | cut -d= -f2)
domain=$(grep '^PUBLIC_DOMAIN=' .env | cut -d= -f2)
IP=$(curl -fsS4 --max-time 5 https://ifconfig.me 2>/dev/null || echo "<server IP>")
cat <<MSG

Done. The node now syncs tau-testnet-v2 in the background.
  Status:  cd $DIR/kit && docker compose logs -f heartbeat
           (one line a minute: height, network tip, in sync or catching up)
  Node:    cd $DIR/kit && docker compose logs -f tau-node
  Update:  run the same install command again
MSG
if [[ -n "$name" ]]; then
  echo "  Listed:  as \"$name\" on https://tauhud.com/stats (community nodes). Turn off: NODE_NAME= in $DIR/kit/.env, then docker compose up -d"
else
  echo "  Listed:  not reporting. To appear on https://tauhud.com/stats: NODE_NAME=<name> in $DIR/kit/.env, then docker compose up -d"
fi
if [[ -n "$domain" ]]; then
  echo "  Relay:   DNS A record $domain -> $IP, then wss://$domain (check: curl https://$domain/status)"
fi
