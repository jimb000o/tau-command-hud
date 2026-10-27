# Tau HUD live backend

Lets tauhud.com show the real Tau testnet instead of the simulation:

```
browser ──wss──▶ Caddy (TLS) ──▶ relay ──ws──▶ tau-node ──p2p──▶ testnet
          node.tauhud.com         read-only    65433, internal   4001
```

- **tau-node**: an [IDNI/tau-testnet](https://github.com/IDNI/tau-testnet) read node
  (pinned commit, small patches in `node/patches/`, mining off unless the validator seat is on), built by `node/Dockerfile`, which is upstream's
  `Dockerfile.standalone` minus a dependency-prefetch step that fails at the pinned tau-lang commit. It joins `tau-testnet-v2` through the
  public bootnode. Its RPC (65432) and WebSocket (65433) ports are never published.
- **relay** (`relay/relay.py`): holds one connection to the node, polls it on a fixed
  schedule that stays under the node's own rate limits, and serves every visitor from that
  cache. New blocks, mempool and governance changes are pushed to visitors as they happen.
- **Caddy**: HTTPS with automatic Let's Encrypt certificates; also serves the tracker's `proposals.json` and `feed.xml`.
- **alerts** (`alerts/alerts.py`): proposal tracker; Telegram/X posts and an Atom feed when rules are proposed, agreed or take effect, plus a weekly recap image.
- **share** (`share/share.py`): share previews, the picture X, Telegram and WhatsApp show under a link (see "Share previews").

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
| `hello version=1 [viewer=<16–64 hex>]` | relay | `ok version=1 env=testnet node=tau-hud-relay`; `viewer` is a random token the browser keeps in localStorage so one person's tabs, pages and reconnects count once in `online` |
| `getblocks [n]` | cache, last 50 blocks | ascending; `n` capped at 50 |
| `getblockrange <from> <count>` | cache, whole current chain | blocks with `from <= block_number < from+count`, ascending; `count` 1..100; `{"blocks", "from", "total", "head"}` |
| `getmempool` | cache, refreshed every 3 s | |
| `getgovernance` | cache, refreshed every 15 s | |
| `gettaustate` | cache, refreshed every 30 s | `{"rules_state": "…"}` |
| `presence` | relay | `{"online": n}`: pages connected right now |
| `getbalance <addr>`, `getsequence <addr>`, `getaccountstate <addr>`, `getruleoffers <addr> [in\|out\|all]`, `gettxstatus <hash>` | node, cached 10 s | hex arguments only; global cap 2/s |

| `report key=<32 hex> name=<name> height=<n> head=<64 hex> [tip=<n>\|none] [kit=<v>] [ref=<commit>]` | relay | community node heartbeat from `kit/heartbeat.py`, see below |

Anything else (`sendtx`, `createblock`, `getallaccounts`, `history`, …) gets
`{"status":"error","error":{"code":"FORBIDDEN"}}` and never reaches the node.

Pushed without asking:
- `getblocks` envelopes with only the new blocks and `"pushed": true`,
- full `getmempool` and `getgovernance` envelopes whenever they change,
- `presence` envelopes `{"online": n, "pushed": true}` right after connecting, whenever a page
  joins or leaves, and every 30 s as a heartbeat. `online` counts people: sockets that sent
  the same `viewer` token count once, sockets without one count individually. The token is
  random, chosen by the browser, held in memory only while connected and never logged;
  `/status` reports `online` (people) and `clients` (sockets).

Clients should de-duplicate blocks by `block_hash` (the HUD already does).

Limits: 20 messages burst then 2/s per connection, 8 connections per IP, 500 in total,
512-byte messages. Browser origins allowed: tauhud.com, www.tauhud.com,
jimb000o.github.io and localhost (`ALLOWED_ORIGINS` in `.env`).

`GET /status` returns `{"upstream_connected", "height", "canonical_height", "tip_height", "live_default", "open_governance_admission", "total_blocks", "online", "age_seconds", …}`. `tip_height` is the highest network tip the node heard from peers (null until known). `height` counts every block the node stores (orphans included; when the node wipes a dead chain after a testnet restart the relay drops its cache and the next pushed `getblocks` carries `"reset": true`); `canonical_height` is the node's real head, and `live_default` is true only while the node follows a real chain, so the page may use it to decide its default view. `open_governance_admission` mirrors the node's `TAU_GOVERNANCE_OPEN_ADMISSION` setting (true: any account's vote counts, false: only active validators). `restarts` (newest 10: `{"detected_at", "old_tip"}`) and `reorgs` (newest 10: `{"at", "height", "depth"}`, recorded when the node replaces a block at a height the relay already held) are the relay's fork radar; the full lists are on `/stats`.
with CORS `*`; `GET /health` is the same but answers 503 while the node is unreachable.

`GET /stats` (CORS `*`, cached 5 s; used by tauhud.com/stats) returns the history of the
current chain: `blocks` is one row per block,
`[height, timestamp, txs, transfers, volume, proposer, {tx_type: count}, [sender]]`, where
`proposer` and `sender` index into `proposers` and `accounts`. `restarts` lists every chain
restart the relay noticed (`{"detected_at", "old": {"block1_ts", "tip", "tip_ts", …},
"new_block1_ts"}`), also ones that happened while the relay was down: the last chain seen is
kept in `/data/events.json` (volume `relay_data`) and compared by its block 1 hash. `dropped`
lists transactions that left the node's mempool without reaching a block within 30 s
(`dropped_total` counts all). `tracking_since` is when that log began; `governance` counts
pending, scheduled, activated and expired rule changes.

To serve these, the relay holds every block of the current chain (up to `CHAIN_BLOCKS`,
default 20,000) and keeps a copy in `/data/chain.jsonl`, so the history survives relay
restarts. The node's WebSocket hands out at most its newest ~900 KB of blocks (a bare
`getblocks` means 50 there, bigger replies fail with `PAYLOAD_TOO_LARGE`), so at startup,
after a restart or a gap the relay asks for `getblocks <chain length>` and halves the request
until the reply fits; older blocks come from the file. Every other poll fetches the newest 20.
Blocks in the file that contradict the node below its tip belong to an earlier chain and are
dropped (and logged as a restart).

## Community nodes

Nodes run with the operator kit ([`kit/`](../kit/README.md)) can report their head once a
minute with `report` (opt-in: only when the operator sets `NODE_NAME`). `key` is a random
secret the reporter keeps; the relay shows only the first 12 hex of its SHA-256 as `id`, so
nobody can overwrite another node's row. Names are 1-24 of `A-Z a-z 0-9 . _ -` and may not
contain "tauhud"; render them as text. Limits: one report per 20 s per node, 3 nodes per
address, 200 in total; a node silent for 15 minutes is dropped. The reporter's address is
kept in memory for the per-address cap only; nothing is written to disk.

`GET /community` (CORS `*`, no-store) returns
`{"reference": {"name": "tauhud.com", "height", "head", "tip", "upstream_connected"}, "nodes": [...], "ttl_seconds", "generated_at"}`
with one row per node, highest first:
`{"id", "name", "height", "tip", "head", "kit", "ref", "first_seen", "last_seen", "age_seconds", "agrees"}`.
`agrees` compares the reported head with this relay's block at that height: `same`,
`different` (another chain or a fork), `ahead` (higher than this relay has) or `unknown`.
`/status` counts them as `community_nodes`.

The leaderboard on tauhud.com/nodes reads `GET /community/board` (CORS `*`, built at most every `STATS_CACHE_SECONDS`):
every node that reported in the last 30 days, also after it went silent, kept in
`/data/community.json` (volume `relay_data`) across relay restarts. One row per node:
`{"id", "name", "first_seen", "last_seen", "online", "days", "uptime", "height", "kit", "ref", "agrees"}`,
online nodes first, then the longest running. `uptime` is the share of minutes since
`first_seen` in which the node reported (null for its first ten minutes); `agrees` is null
while offline. `first_seen` in `/community` comes from the same record, so a node keeps its
start date through a silence.

`GET /community/badge/<id>.svg` is an embeddable badge ("Tau HUD node | running 12 d · 98 % up", green
while the node reports, grey when offline, "unknown node" for an id it never saw), cached
5 minutes. The kit's heartbeat log prints the Markdown snippet for it once per start.

`GET /uptime` (CORS `*`, cached 5 s; used by tauhud.com/status) is the availability
history for the status page. Once a minute the relay samples whether the node is
connected and answering (`node_ok`) and whether its verified head is within
`SYNC_LAG_BLOCKS` (2) of the network tip (`synced`), and folds the samples into hourly
buckets `[hour, samples, node_ok, synced]` for 31 days. A bucket with fewer than 60
samples means the relay itself was down for the rest of that hour. `incidents` lists
outages `{"kind": "relay" | "node" | "sync", "start", "end", "max_lag"}` (`end` null while
it lasts); `restarts`, `reorgs` and `stalls` (gaps of more than 10 min between two blocks
of the current chain: the network made no block) cover the same 31 days, and `status` is
`/status`. Stored in `/data/uptime.json` (volume `relay_data`), so it survives restarts;
the time between the relay's last sample and its next start counts as a relay outage.
Since the health score, each bucket also carries `score_sum`, `score_min` and
`score_samples` (older hours have only the first four fields).

`GET /health-score` (CORS `*`, cached 5 s; tauhud.com/status, the alerts and `/status`
use it) is one number for "does the testnet run?": 0 to 100 from seven factors whose
weights add up to 100. `factors` lists each with `weight`, `points`, `value` and a `note`:

| factor | weight | full points | no points |
|---|---|---|---|
| `node` node answering | 20 | answers | no answer |
| `sync` in sync with the network | 15 | within 2 blocks of the tip | 30 behind |
| `last_block` time since the last block | 20 | up to 3 typical block times | 30 min |
| `pace` blocks in the last hour | 10 | 75 % of the expected count | none |
| `availability` live and in sync, 24 h | 15 | 99 % of the checks | 80 % |
| `stability` restarts, reorgs, stalls, 24 h | 15 | none | restart −10, stall −4, reorg −3 |
| `mempool` oldest waiting transaction | 5 | up to 10 min | 60 min (IDNI #81 shows here) |

The typical block time (`expected_block_seconds`) is the median gap of the last 100
blocks, stalls left out (60 s until there are enough). `state` is `healthy` from 80
(`HEALTH_OK_AT`), `degraded` from 50 (`HEALTH_DEGRADED_AT`), else `down`; no answer from
the node or no block for 30 minutes is `down` whatever the score. `hours` is
`[hour, average, lowest]` for the last 31 days. `/status` carries `health`
(`score`, `state`, `label`).

## Rule Playground checker

`checker/checker.py` answers tauhud.com/playground: `POST https://node.tauhud.com/check`
with `{"rule": "...", "sender": "<96 hex>", "tests": [{"amount", "from", "to", "time"}, …]}`.
It runs the rule through tau-testnet's own code from the node image, in the node's order:
`normalize_offer_rule_text` (shape), `_screen_clause_domains` (streams, `[t]` only, widths),
`compose_stream_rule` (the sender-guarded composite), then a fresh `SpeculationSession`
worker that builds genesis plus the shipped rules, offers the composite on `i0` and steps
each sample transfer, reading `o5` (1 allow, 0 block). The answer is
`{"accepted", "stage", "reason", "composite", "tests": [{"o5"}], "ms", "engine"}`.

It never talks to the node or the chain. One worker at a time, 30 s of engine time per
request, 8 sample transfers, 16 KB bodies, 8 checks per 5 minutes per address, a cache for
repeated texts. The container uses the node's image (nothing extra to compile), has no
outbound network, a read-only filesystem, no capabilities, 512 MB, 1 CPU and 64 processes.
`GET /check/health` answers `{"ok": true}`.

## Validator seat

tau-testnet-v2 is proof of authority: only keys in the on-chain validator set propose
blocks, and a key joins only when an existing validator proposes
`consensus_rule_update` with `host_contract_patch.validator_additions` and the set
votes it in (today one validator, IDNI's). Steps:

1. Make the key on the server (once; running it again only shows the public key):
   `cd /opt/tau-command-hud/infra && docker compose exec tau-node tau-validator-key`.
   The private key goes to `/data/validator.key` in the `tau_data` volume (mode 0600,
   kept when the node wipes chain data) and is never printed or committed. Back it up
   off-server only if you want to keep the seat across a lost volume.
2. Ask IDNI to add the printed public key.
3. Once the key shows up in the validator set (HUD, or `getgovernance`):
   `echo TAU_VALIDATOR=true >> .env && docker compose up -d tau-node`.
   The log says `[start] validator mode, key …`.

Safety: the `validator-gate` patch keeps the node from proposing while its key is not in
the active set, also under open admission where upstream skips that check, so turning
the seat on early or after a removal cannot fork the HUD onto a private chain. Without
the key file the node logs a warning and stays a read node. The relay is unchanged: it
still refuses every write command, and the node's RPC stays internal, so the seat signs
only blocks the node builds itself. Turn it off with `TAU_VALIDATOR=false` and the same
`up -d`.

## Proposal tracker and alerts

`alerts/alerts.py` turns governance into news. It reads the chain from the relay over the
same read-only WebSocket protocol as the pages (`getblockrange`, `getgovernance`), replays
it block by block like history/ does (`consensus/governance.py` at the pinned commit: update
ids are BLAKE3 over the node's serialization), and emits one event each when a rule change
is **proposed**, **agreed** (quorum reached), **active** (its activation block arrived) or
**dropped** (deadline passed with too few votes), plus **restart** when block 1 changes.

- `https://node.tauhud.com/proposals.json`: every proposal with its votes and status, the
  rules in force and the last 100 events. Read by tauhud.com/proposals/.
- `https://node.tauhud.com/feed.xml`: Atom feed of the same events.
- Each proposal is explained in plain words (`alerts/explain.py`): its rule text is compared
  stream by stream with the rules in force (o6 valid blocks, o7 who makes blocks, o9 base
  fee) plus its settings patch, giving "what changes", "why it matters" and a title such as
  "Base fee 10 → 20 AGRS" or "Same rules as now (no real change)". The tracker page and
  the recap use the same words. `python alerts.py --preview` prints how the newest rule
  changes on the chain would be posted, without posting.
- Telegram and X: each event as a post, when the keys are in `.env`. Without keys that
  channel is off; the feed and the page work regardless.

What it finds on its very first run is history and is never posted, and neither is an
event whose block is older than 3 hours (`POST_MAX_AGE_SECONDS`), so a fresh volume or a
long outage does not flood the channel. A channel switched on later starts from that
moment. State (seen events, what went where) lives in the `alerts_state` volume, so
nothing is posted twice across restarts. Failed posts are retried up to 8 times with
back-off; the token is never logged.

**Telegram** (channel `@tauHUDcom`):
1. In Telegram, open @BotFather, send `/newbot`, pick a name and a username ending in
   `bot`. It answers with a token.
2. Channel → Administrators → Add admin → the bot, with "Post messages".
3. On the server: `cd /opt/tau-command-hud/infra && nano .env`, add
   `TELEGRAM_BOT_TOKEN=<token>` (and `TELEGRAM_CHAT_ID=@tauHUDcom` if the channel has
   another name), save, then `docker compose up -d alerts`.
4. Test: `docker compose run --rm alerts python alerts.py --test` posts one message.

**X** (optional): an app at developer.x.com with "Read and write" user authentication,
then its API key and secret and the account's access token and secret (generated after
switching to Read and write) as `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
`X_ACCESS_SECRET` in `.env`, and `X_PROFILE_URL=https://x.com/<handle>` for the page's
follow link. Same `up -d alerts` and `--test`.

**Weekly recap**: every Monday 09:00 UTC (`RECAP_WEEKDAY`, `RECAP_HOUR`) `alerts/recap.py`
draws the past 7 days as one 1200×675 image in the HUD look: blocks and block time,
transactions and active accounts, blocks per day, rule changes (proposed, agreed, in force,
dropped), chain restarts, community nodes (new ones this week) and the most active accounts.
Data: the relay's `/stats` and `/community` plus the tracker's own events. It goes to
Telegram (and X once its keys are set) as a photo with a short caption, and stays at
`https://node.tauhud.com/recap/latest.png`, `/recap/<date>.png` and `/recap/index.json`
(newest first, with the caption lines) for the HUD to link. The first run only notes the
next slot; a slot missed by more than a day is drawn but not posted. Fonts (Sora,
JetBrains Mono, SIL OFL) live in `alerts/fonts/`.

- `docker compose run --rm alerts python alerts.py --recap-preview` draws the last 7 days
  to `/recap/latest.png` and posts nothing.
- `docker compose run --rm alerts python alerts.py --recap-now` draws it and posts it.

**Health alerts**: once a minute the watcher reads `/health-score` and posts to Telegram
when the testnet goes down (score under 50, the relay says `down`, or the relay does not
answer) and when it recovers (score 70 or more), each only after the new state held for
10 minutes (`HEALTH_DOWN_BELOW`, `HEALTH_UP_AT`, `HEALTH_CONFIRM_SECONDS`). The post names
the factors that lose the most points. The state on the first run is not posted.
`HEALTH_ALERTS=false` turns it off.

Logs: `docker compose logs -f alerts`.

## Share previews

tauhud.com is static, so every page has one og:image and the crawlers of X and
Telegram never run the page's JavaScript. The share service draws a 1200×630
card per thing, live from the chain, in the look of the weekly recap:

| Path | Card |
|---|---|
| `/og/hud.png` | live overview: height, sync, rule changes in force, coming up, validators |
| `/og/block/<n>.png` | one block: its transactions, who sealed it, when |
| `/og/proposal/<id or first 8+ hex>.png` | one rule change: what changes, why, votes, countdown or result |
| `/og/address/<96 hex>.png` | one account: balance, transactions, latest activity |

`/s/`, `/s/block/<n>`, `/s/proposal/<id>` and `/s/address/<hex>` are tiny pages
with the og:/twitter: tags for that card; a person who opens one is sent on to
the real page on tauhud.com. These are the links to share: the Explorer and the
proposal tracker have a "Copy share link" button, and the HUD's own og:image is
`/og/hud.png`. If the chain cannot be read, every card falls back to the logo card.
Cards are cached for a minute (older blocks for an hour); X and Telegram keep their
own copy of a preview once fetched.

Logs: `docker compose logs -f share`.

## Tests

```bash
pip install websockets==15.0.1
python relay/test_relay.py
python relay/test_uptime.py
python relay/test_health.py
```

Runs the relay against a mock node that enforces the real node's rate limits: read
commands, refusal of write commands, pushes, origin check, per-IP and per-client limits,
`/health`, and that the polling never trips the node's limiter.

```bash
docker compose run --rm checker python /checker/test_checker.py
```

```bash
pip install websockets==15.0.1 blake3==1.0.5 pillow==11.3.0
python alerts/test_alerts.py
python alerts/test_health_alerts.py
```

Runs the alerts watcher against a mock relay: history on the first run is not posted, new
proposals, agreement, activation and a dropped change are posted once each per channel
(also after a failed post and a watcher restart), the feed and proposals.json are right,
a chain restart is reported, and the weekly recap is drawn and posted once.

```bash
pip install websockets==15.0.1 pillow==11.3.0
python share/test_share.py      # OUT=/tmp/cards also writes the cards to look at
```

Runs the share service against a mock relay: the chain is read in pages, every card is
a 1200×630 PNG, the link pages carry the tags and send on to tauhud.com, bad paths are
refused, and a chain restart is reloaded.

Runs the checker against the real engine: verdicts for sample transfers, refusals by
the text screens and by the engine.
