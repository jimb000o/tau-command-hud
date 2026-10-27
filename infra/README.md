# Tau HUD live backend

Lets tauhud.com show the real Tau testnet instead of the simulation:

```
browser ──wss──▶ Caddy (TLS) ──▶ relay ──ws──▶ tau-node ──p2p──▶ testnet
          node.tauhud.com         read-only    65433, internal   4001
```

- **tau-node**: an unmodified [IDNI/tau-testnet](https://github.com/IDNI/tau-testnet) read node
  (pinned commit, mining off), built by `node/Dockerfile`, which is upstream's
  `Dockerfile.standalone` minus a dependency-prefetch step that fails at the pinned tau-lang commit. It joins `tau-testnet-v2` through the
  public bootnode. Its RPC (65432) and WebSocket (65433) ports are never published.
- **relay** (`relay/relay.py`): holds one connection to the node, polls it on a fixed
  schedule that stays under the node's own rate limits, and serves every visitor from that
  cache. New blocks, mempool and governance changes are pushed to visitors as they happen.
- **Caddy**: HTTPS with automatic Let's Encrypt certificates.

## Server

Hetzner Cloud CAX11 (2 vCPU Ampere ARM, 4 GB RAM, 40 GB, Ubuntu 24.04), CX23 (x86) or
anything similar. Both arm64 and x86_64 work: the base images are multi-arch and tau-lang
ships native linux-arm64 dependency recipes, everything else compiles from source.
4 GB RAM plus swap is needed for the one-time tau-lang compile; the running node needs far less.

```bash
# on the server, as root
curl -fsSL https://raw.githubusercontent.com/jimb000o/tau-command-hud/main/infra/setup.sh | bash
```

Then add a DNS A record `node.tauhud.com → <server IP>`. Check with
`curl https://node.tauhud.com/status`.

Update later: `cd /opt/tau-command-hud && git pull && cd infra && docker compose up -d --build`.

Open ports: 22, 80, 443 and 4001 (P2P). Docker-published ports bypass ufw, so only
publish what is meant to be public.

## Protocol for the page

Same text protocol as the node's own WebSocket, so the HUD's live mode works as is.
Connect to `wss://node.tauhud.com`, send a command as text, get the node's JSON envelope
`{"status":"ok","command":…,"data":…}` back.

| Command | Answered from | Notes |
|---|---|---|
| `hello version=1` | relay | `ok version=1 env=testnet node=tau-hud-relay` |
| `getblocks [n]` | cache, last 50 blocks | ascending; `n` capped at 50 |
| `getmempool` | cache, refreshed every 3 s | |
| `getgovernance` | cache, refreshed every 15 s | |
| `gettaustate` | cache, refreshed every 30 s | `{"rules_state": "…"}` |
| `presence` | relay | `{"online": n}`: pages connected right now |
| `getbalance <addr>`, `getsequence <addr>`, `getaccountstate <addr>`, `getruleoffers <addr> [in\|out\|all]`, `gettxstatus <hash>` | node, cached 10 s | hex arguments only; global cap 2/s |

Anything else (`sendtx`, `createblock`, `getallaccounts`, `history`, …) gets
`{"status":"error","error":{"code":"FORBIDDEN"}}` and never reaches the node.

Pushed without asking:
- `getblocks` envelopes with only the new blocks and `"pushed": true`,
- full `getmempool` and `getgovernance` envelopes whenever they change,
- `presence` envelopes `{"online": n, "pushed": true}` right after connecting, whenever a page
  joins or leaves, and every 30 s as a heartbeat. It is a connection count only; the relay
  does not identify or log who is behind a connection.

Clients should de-duplicate blocks by `block_hash` (the HUD already does).

Limits: 20 messages burst then 2/s per connection, 8 connections per IP, 500 in total,
512-byte messages. Browser origins allowed: tauhud.com, www.tauhud.com,
jimb000o.github.io and localhost (`ALLOWED_ORIGINS` in `.env`).

`GET /status` returns `{"upstream_connected", "height", "canonical_height", "tip_height", "live_default", "open_governance_admission", "total_blocks", "online", "age_seconds", …}`. `tip_height` is the highest network tip the node heard from peers (null until known). `height` counts every block the node stores (orphans included); `canonical_height` is the node's real head, and `live_default` is true only while the node follows a real chain, so the page may use it to decide its default view. `open_governance_admission` mirrors the node's `TAU_GOVERNANCE_OPEN_ADMISSION` setting (true: any account's vote counts, false: only active validators).
with CORS `*`; `GET /health` is the same but answers 503 while the node is unreachable.

## Tests

```bash
pip install websockets==15.0.1
python relay/test_relay.py
```

Runs the relay against a mock node that enforces the real node's rate limits: read
commands, refusal of write commands, pushes, origin check, per-IP and per-client limits,
`/health`, and that the polling never trips the node's limiter.
