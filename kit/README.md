# Tau node operator kit

Run your own node on the Tau testnet (`tau-testnet-v2`) with one command. It is the same
node that powers [tauhud.com](https://tauhud.com): IDNI's
[tau-testnet](https://github.com/IDNI/tau-testnet) at a pinned commit, plus a few small
patches that make it sync reliably today (see [What is patched](#what-is-patched)).

Every extra node that follows the chain makes the testnet easier to check: anyone can see
whether independent nodes agree on the same blocks. If you like, your node shows up on
[tauhud.com/stats](https://tauhud.com/stats) under **community nodes**, with a mark that
says whether it is on the same chain as tauhud.com's node.

## What you need

- A server with **Ubuntu 24.04** (Debian 12/13 works too), **x86_64 or ARM64**.
- **2 CPU, 4 GB RAM, 40 GB disk.** Example: Hetzner Cloud CAX11 (ARM) or CX23 (x86), about
  €6 a month. The installer adds an 8 GB swap file: the one-time compile needs it.
- **Time for the first build: about 1.5 hours** on such a server (tau-lang and its solvers
  compile from source). Later updates take minutes.
- Port **4001/tcp** reachable from the internet (the installer opens it in `ufw`; also allow
  it in your cloud provider's firewall if it has one).
- Root access over SSH.

## Install

On the server, as root. `tmux` first, so the build keeps running if your SSH drops:

```bash
tmux
curl -fsSL https://raw.githubusercontent.com/jimb000o/tau-command-hud/main/kit/install.sh | NODE_NAME=my-node bash
```

Pick your own `NODE_NAME` (1 to 24 letters, digits, `.`, `_`, `-`). Leave `NODE_NAME=` out
and the node reports nowhere. (Reattach to `tmux` after a dropped SSH with `tmux attach`.)

The installer:

1. checks the server (CPU, RAM, disk),
2. installs Docker from Docker's own repository and turns on automatic security updates,
3. adds 8 GB swap (below 12 GB RAM) and caps Docker's build cache at 12 GB,
4. opens SSH and 4001/tcp in `ufw` (and 80/443 if you use `PUBLIC_DOMAIN`),
5. puts the kit in `/opt/tau-node-kit`, writes `/opt/tau-node-kit/kit/.env`,
6. builds and starts the node.

Options, all optional, given the same way as `NODE_NAME`:

| Variable | What it does |
|---|---|
| `NODE_NAME=my-node` | List the node on tauhud.com/stats. |
| `PUBLIC_DOMAIN=tau.example.org` | Also run a public read-only relay at `wss://tau.example.org` with HTTPS (see [Public relay](#public-relay)). |
| `TAU_BUILD_JOBS=2` | Parallel compile jobs. Default 1 below 8 GB RAM, 2 from 8 GB. More jobs on 4 GB freezes the server. |
| `FORCE=1` | Install although the server looks too small. |

## Is it working?

```bash
cd /opt/tau-node-kit/kit
docker compose logs -f heartbeat
```

One line a minute:

```
2026-10-27 18:02:11 height 214 · network tip 214 · in sync · reported as my-node (same chain as tauhud.com)
```

- `catching up, n behind`: still downloading blocks. Normal for the first minutes.
- `no peer seen yet`: the node has not reached the bootnode yet. Check that 4001/tcp is open.
- `node not reachable yet`: the node is still building or starting.
- `DIFFERENT chain from tauhud.com`: your node follows other blocks than tauhud.com's. Rerun
  the install command (it picks up the current pinned commit), and if it stays, open an
  issue (link below).

The node's own log: `docker compose logs -f tau-node`.

## Update

Run the install command again. It pulls the latest kit, keeps your settings, chain data
and keys, and rebuilds only what changed. When the testnet restarts or its genesis changes,
the node notices, wipes the old chain (keeping its identity and keys) and syncs again by
itself.

## Settings

Edit `/opt/tau-node-kit/kit/.env`, then `docker compose up -d` in that directory.

- Stop reporting: `NODE_NAME=` (empty).
- Rename: change `NODE_NAME`.
- Stop everything: `docker compose down` (chain data stays in Docker volumes;
  `docker compose down -v` deletes it too, and with it your validator key).

## What is reported

Only if `NODE_NAME` is set, once a minute, to `wss://node.tauhud.com`: the name, your
node's canonical height and head block hash, the highest network tip it has heard of, the
kit version and the tau-testnet commit. No IP address is shown or stored on disk, no keys,
no peer IDs. A random secret in the `heartbeat_data` volume proves that later reports come
from the same node; tauhud.com shows only a short hash of it. A node that stops reporting
disappears from the list after 15 minutes.

## Public relay

With `PUBLIC_DOMAIN=tau.example.org`, the kit also starts the same relay and HTTPS proxy
that serve tauhud.com: a read-only WebSocket at `wss://tau.example.org` that speaks the
node's text protocol from a cache (`getblocks`, `getgovernance`, `getmempool`, …; every
write command is refused). Point a DNS A record `tau.example.org` at the server; Caddy gets
the certificate by itself. Check with `curl https://tau.example.org/status`. The protocol is
described in [`infra/README.md`](../infra/README.md#protocol-for-the-page).

## Validator

tau-testnet-v2 is proof of authority: only keys in the on-chain validator set propose
blocks, and a key joins only when the current validators vote it in (today that is IDNI's
single validator). The kit can hold a validator key and stays a read node until the key is
actually in the set.

1. Make the key (once; running it again only shows the public key):
   `cd /opt/tau-node-kit/kit && docker compose exec tau-node tau-validator-key`.
   The private key stays in the `tau_data` volume (`/data/validator.key`, mode 0600) and is
   never printed.
2. Ask IDNI to add the printed public key, in an issue on
   [IDNI/tau-testnet](https://github.com/IDNI/tau-testnet/issues).
3. Once the key is in the validator set: `TAU_VALIDATOR=true` in `.env`, then
   `docker compose up -d tau-node`.

The `validator-gate` patch keeps the node from proposing while its key is not in the active
set, so turning this on early cannot fork your node onto a chain of its own.

## What is patched

The node is built by [`infra/node/Dockerfile`](../infra/node/Dockerfile) from IDNI's
tau-testnet at the commit in [`infra/.env.example`](../infra/.env.example). The patches in
[`infra/node/patches/`](../infra/node/patches) fix problems found while running
tauhud.com's node:

| Patch | Why |
|---|---|
| `read-until-eof` | Sync read one 64 KiB frame of each reply, so any bigger header or block batch failed to parse. |
| `sync-paginate` | Sync fetched one batch of 2,000 headers and stopped; it now pages until caught up. |
| `sync-diagnostics` | Logs peer heads, header ranges and why a block was rejected, so a stuck sync says why. |
| `network-tip` | Reports the highest tip heard from peers, for "catching up n / tip". |
| `peer-addrs` | The bootnode announces `/ip4/0.0.0.0/tcp/4001`; dialing that made the node dial itself after a restart. |
| `chain-reset` | The testnet gets restarted on the same genesis without notice (twice on 2026-10-27); the node detects that, wipes and resyncs. |
| `validator-gate` | Never propose while the key is not in the active validator set. |

Two settings must match the network and are set for you: the genesis from
`networks/tau-testnet-v2/genesis.json`, and `TAU_GOVERNANCE_OPEN_ADMISSION=true` (votes
from non-validators count; with `false` a node stops verifying at the first such vote).

## Troubleshooting

- **Build seems stuck** at a compile step for many minutes: normal, one file can take
  10+ minutes on 2 CPU. If the server stops answering SSH, it ran out of memory: reboot it
  from your provider's console and run the install command again (it continues from cache).
- **Disk full**: `docker buildx prune -af --filter type=regular`, then run the install
  command again. Keep at least 40 GB of disk.
- **`no peer seen yet` for more than a few minutes**: 4001/tcp is blocked somewhere, or
  the bootnode `34.251.82.246:4001` is down.

Questions or problems: [open an issue](https://github.com/jimb000o/tau-command-hud/issues/new?title=%5BNode%20kit%5D%20).
