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
  echo "[start] chain data belongs to genesis '${have:-unknown}', image ships '$want': wiping /data (identity and validator key kept)"
  find /data -mindepth 1 ! -name identity.key ! -name 'validator.*' -exec rm -rf {} +
fi
# The node leaves this marker (patches/chain-reset.py) when the bootnode runs a
# chain we do not have below our stored height, i.e. the testnet was restarted
# on the same genesis. Wipe and resync.
if [[ -f /data/chain-reset ]]; then
  echo "[start] chain reset requested: $(cat /data/chain-reset)"
  echo "[start] wiping /data (identity and validator key kept)"
  find /data -mindepth 1 ! -name identity.key ! -name 'validator.*' -exec rm -rf {} +
fi
echo "$want" > /data/genesis.hash
echo "[start] genesis $want"

# Validator mode (TAU_VALIDATOR=true in .env, see infra/README.md): sign with the
# key made by tau-validator-key. Without that key the node stays a read node;
# a crash loop here would take the HUD down with it. Off by default, and the
# validator-gate patch keeps the node from proposing until governance has
# added the key to the active validator set.
if [[ "${TAU_MINING_ENABLED:-false}" =~ ^(true|1|yes)$ ]]; then
  if [[ -s /data/validator.key && -s /data/validator.pub ]]; then
    export TAU_MINER_PRIVKEY_PATH=/data/validator.key TAU_MINER_PUBKEY_PATH=/data/validator.pub
    # Upstream falls back to [our key] as the validator set where a block carries
    # none; pin that fallback to the genesis set so it matches every read node.
    TAU_MINER_PUBKEYS="$(python -c 'import json; print(",".join(json.load(open("data/genesis.json"))["consensus_meta"]["active_validators"]))')"
    export TAU_MINER_PUBKEYS
    echo "[start] validator mode, key $(head -c 12 /data/validator.pub)…"
  else
    echo "[start] TAU_VALIDATOR=true but no /data/validator.key (run tau-validator-key): staying a read node"
    export TAU_MINING_ENABLED=false
  fi
fi
exec python server.py
