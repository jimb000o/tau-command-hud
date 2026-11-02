#!/bin/sh
# Rebuild the relay with the code just pulled, then show that it answers. Run on the server after a git pull:
#   cd /opt/tau-command-hud && git pull && sh infra/relay.sh
set -e
cd "$(dirname "$0")"
docker compose up -d --build relay
docker compose up -d --force-recreate caddy
echo "waiting 20 s for the relay…"
sleep 20
curl -s https://node.tauhud.com/isle | head -c 400; echo
curl -s https://node.tauhud.com/island | head -c 200; echo
