#!/bin/sh
# One short command for the server after any merge: pull, rebuild whatever changed, recreate caddy once,
# then show that the node and the relay answer. Safe to rerun; containers whose code did not change keep running.
# First time:  cd /opt/tau-command-hud && git pull && sh infra/up.sh
# After that:  up
set -e
cd "$(dirname "$(readlink -f "$0")")"
ln -sf "$(pwd)/up.sh" /usr/local/bin/up 2>/dev/null && chmod +x up.sh 2>/dev/null || true
if [ "$1" != "--pulled" ]; then
  git -C .. pull --ff-only
  exec sh "$(pwd)/up.sh" --pulled
fi
cp sites/agorzilla.caddy /opt/sites/ 2>/dev/null || true
docker compose up -d --build
docker compose up -d --force-recreate caddy
echo "waiting 20 s…"
sleep 20
curl -s https://node.tauhud.com/status | head -c 200; echo
curl -s https://node.tauhud.com/isle | head -c 200; echo
echo "done. next time just type: up"
