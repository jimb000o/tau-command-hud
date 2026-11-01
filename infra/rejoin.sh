#!/bin/sh
# Rejoin the testnet after IDNI restarts the chain: wipe the node's chain data
# (start.sh keeps identity.key and the validator key), recreate the node and the
# services that read it, then show the status. Run on the server from anywhere:
#   sh /opt/tau-command-hud/infra/rejoin.sh
set -e
cd "$(dirname "$0")"
docker compose stop tau-node
docker compose run --rm --no-deps --entrypoint sh tau-node -c 'touch /data/chain-reset'
docker compose up -d --force-recreate tau-node relay alerts
docker compose up -d --force-recreate caddy
echo "waiting 90 s for the node to resync…"
sleep 90
curl -s https://node.tauhud.com/status | head -c 300; echo
