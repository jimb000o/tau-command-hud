#!/usr/bin/env bash
# Start the read-only node. Before that, make sure the chain data on the volume
# belongs to the genesis this image ships: when the network's genesis.json
# changes (it did on 2026-10-27, IDNI/tau-testnet#78), every block in the old
# database is on another chain and the node would sit on it forever. Wipe the
# chain data then, keep the libp2p identity so the node keeps its peer ID.
set -euo pipefail

mkdir -p data
cp networks/tau-testnet-v2/genesis.json data/genesis.json
want="$(python -c 'import json; print(json.load(open("data/genesis.json"))["block_0"]["hash"])')"
have="$(cat /data/genesis.hash 2>/dev/null || true)"

if [[ -f /data/node.db && "$have" != "$want" ]]; then
  echo "[start] chain data belongs to genesis '${have:-unknown}', image ships '$want': wiping /data (identity kept)"
  find /data -mindepth 1 ! -name identity.key -exec rm -rf {} +
fi
# The node leaves this marker (patches/chain-reset.py) when the bootnode runs a
# chain we do not have below our stored height, i.e. the testnet was restarted
# on the same genesis. Wipe and resync.
if [[ -f /data/chain-reset ]]; then
  echo "[start] chain reset requested: $(cat /data/chain-reset)"
  echo "[start] wiping /data (identity kept)"
  find /data -mindepth 1 ! -name identity.key -exec rm -rf {} +
fi
echo "$want" > /data/genesis.hash
echo "[start] genesis $want"
exec python server.py
