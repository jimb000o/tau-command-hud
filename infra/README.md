# Tau HUD live backend

Lets tauhud.com show the real Tau testnet instead of the simulation:

```
browser ──wss──▶ Caddy (TLS) ──▶ relay ──ws──▶ tau-node ──p2p──▶ testnet
          node.tauhud.com   reads + signed tx  65433, internal   4001
```

- **tau-node**: an [IDNI/tau-testnet](https://github.com/IDNI/tau-testnet) read node
  (pinned commit, small patches in `node/patches/`, mining off unless the validator seat is on), built by `node/Dockerfile`, which is upstream's
  `Dockerfile.standalone` minus a dependency-prefetch step that fails at the pinned tau-lang commit. It joins `tau-testnet-v2` through the
  public bootnode. Its RPC (65432) and WebSocket (65433) ports are never published.
- **relay** (`relay/relay.py`): holds one connection to the node, polls it on a fixed
  schedule that stays under the node's own rate limits, and serves every visitor from that
  cache. New blocks, mempool and governance changes are pushed to visitors as they happen.
- **No Memo's crew purse** (`relay/nomemo.py`, inside the relay): the drop the terminal game pays and its lookalike, both keys made once in the relay's data volume (never in the repository). Pays each chapter's share (500 test AGRS) back to the wallet whose claim (a payment of 101, 102 or 103 to the drop) the chain sealed, the crew's mark once, and, as the Tracer, dust from the lookalike after the first chapter; in the island bot's free slots, one send every 20 s at most, 300 payouts a day. `GET /nomemo` (the drop, the players' board), `GET /nomemo/wallet/<address>`; `up nomemo` prints the state; `NOMEMO_ENABLED=0`, `NOMEMO_TRACER=0`.
- **Caddy**: HTTPS with automatic Let's Encrypt certificates; also serves the tracker's `proposals.json` and `feed.xml`.
- **alerts** (`alerts/alerts.py`): proposal tracker; Telegram/X posts and an Atom feed when rules are proposed, agreed or take effect, plus a weekly recap image.
- **donations** (`alerts/donations.py`): watches the donation address on Ethereum (AGRS and ETH only, public Blockscout API), keeps `/donations.json` for the About section and posts one thank-you per new donation to the channel.
- **devpulse** (`alerts/devpulse.py`): keeps blob-less git clones of IDNI's public tau-testnet and tau-lang repositories and writes `/devpulse.json` every 30 minutes for tauhud.com/devpulse/ (newest commits, weekly rhythm, code areas, tags, how far upstream is ahead of the commits in `node/Dockerfile`). Open issue and pull request counts come from the public GitHub search API, a few requests an hour, no token.
- **bot** (`alerts/bot.py`): the same Telegram bot answers questions in private chats and groups: height, proposals, a transaction, an address, a block, node status (see "Question bot").
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

Update later: `up` (infra/up.sh: pull, rebuild what changed, recreate Caddy, speak new voice lines, and print one block
with the node, the island's week, the last two days of posts and the voices to paste into the chat). `up island` also paints
a new island with every room to match (infra/island.sh auto).

Open ports: 22, 80, 443 and 4001 (P2P). Docker-published ports bypass ufw, so only
publish what is meant to be public.

## Protocol for the page

Same text protocol as the node's own WebSocket, so the HUD's live mode works as is.
Connect to `wss://node.tauhud.com`, send a command as text, get the node's JSON envelope
`{"status":"ok","command":…,"data":…}` back.

| Command | Answered from | Notes |
|---|---|---|
| `hello version=1` | relay | `ok version=1 env=testnet node=tau-hud-relay`; a `viewer=<token>` field from older pages is accepted and ignored |
| `getblocks [n]` | cache, last 50 blocks | ascending; `n` capped at 50 |
| `getblockrange <from> <count>` | cache, whole current chain | blocks with `from <= block_number < from+count`, ascending; `count` 1..100; `{"blocks", "from", "total", "head"}` |
| `getmempool` | cache, refreshed every 3 s | |
| `getgovernance` | cache, refreshed every 15 s | |
| `gettaustate` | cache, refreshed every 30 s | `{"rules_state": "…"}` |
| `presence` | relay | `{"online": n}`: pages connected right now |
| `getbalance <addr>`, `getsequence <addr>`, `getaccountstate <addr>`, `getruleoffers <addr> [in\|out\|all]`, `getapprovalrequests <addr> [in\|out\|all]`, `getretractables <addr> [in\|out\|all]`, `getruleoffer <offer id>`, `getruleconflict <offer id>`, `gettxstatus <hash>` | node, cached 10 s | hex arguments only; global cap 2/s |
| `sendtx <json>`, `checktx <json>` | node, never cached | the wallet's write door (tauhud.com/wallet/): a transaction the visitor's browser already signed, as one JSON object of at most 8 KB with `tx_type` in `user_tx`, `consensus_rule_vote`, `rule_offer`, `rule_offer_accept`, `rule_offer_reject`, `approval_request`, `transfer_vote`, `retractable_transfer`, `retract_transfer`, a 96-hex `sender_pubkey` and a 192-hex `signature`; `checktx` is the node's dry run (nothing is sent); both share 12/min per address (burst 6) and 60/min for everyone; content is never logged |
| `leasetx <json>` | node `checktx` once, then kept | the wallet's pre-signed neutral clause for a fair turn on a personal-rule place (see `/lease` below); only that exact shape, same buckets as `sendtx` |

| `report key=<32 hex> name=<name> height=<n> head=<64 hex> [tip=<n>\|none] [kit=<v>] [ref=<commit>]` | relay | community node heartbeat from `kit/heartbeat.py`, see below |

Anything else (`createblock`, a `consensus_rule_update` proposal, `getallaccounts`, `history`, …) gets
`{"status":"error","error":{"code":"FORBIDDEN"}}` and never reaches the node.

Pushed without asking:
- `getblocks` envelopes with only the new blocks and `"pushed": true`,
- full `getmempool` and `getgovernance` envelopes whenever they change,
- `presence` envelopes `{"online": n, "pushed": true}` right after connecting, whenever a page
  joins or leaves, and every 30 s as a heartbeat. `online` counts people, not sockets: one
  browser's tabs, pages and reconnects count once. The relay tells browsers apart the way the
  visit count does (`visits.py`): the day's random salt hashed with the address and the user
  agent, in memory only, nothing stored in the browser and nothing logged;
  `/status` reports `online` (people) and `clients` (sockets).

Clients should de-duplicate blocks by `block_hash` (the HUD already does).

Limits: 20 messages burst then 2/s per connection for commands that reach the node or write; over that
the reply is `{"status":"error","command":<the command>,"error":{"code":"RATE_LIMITED","request":<the line>}}`.
Reads answered from the relay's memory (`getblocks`, `getblockrange`, the cached commands, `presence`)
have their own budget of 40 then 10/s per connection and are never refused: over it the connection
waits for the next token, so a page loading the chain in 100-block pages always gets every answer.
96 connections per IP (`MAX_PER_IP` in `.env`; every open page holds two to four sockets: header, page, presence, chat), 500 in total,
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

**Bootstrapping from node.tauhud.com.** Our node listens on 4001/tcp, holds the whole verified
chain and announces `/ip4/2.31.101.42/tcp/4001` (`TAU_ANNOUNCE_ADDRS`), so any tau-testnet
node can use it as a bootstrap peer next to, or instead of, the IDNI bootnode. Its peer ID is
`12D3KooWRgGw5yDHBmYEpaCZtNVPYD7xQ3yhh5urM9w7jNtNqpmY` (printed at start, `docker compose logs tau-node | grep -o
'peer_id=[A-Za-z0-9]*'`; it stays the same across restarts, `/data/identity.key`). On the other node:

```
TAU_BOOTSTRAP_PEERS='[{"peer_id":"12D3KooWRgGw5yDHBmYEpaCZtNVPYD7xQ3yhh5urM9w7jNtNqpmY","addrs":["/ip4/2.31.101.42/tcp/4001"]},
                      {"peer_id":"12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC","addrs":["/ip4/34.251.82.246/tcp/4001"]}]'
```

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

`GET /sim/votes` and `GET /sim/vote?item=&voter=&yes=1|0&a=&b=&c=` (CORS `*`, no-store,
`relay/simvotes.py`) count the visitors' votes on the simulation's hourly rule change: open
hh:20 to hh:27, one vote per browser token, at most three tokens per address per item, a
name and colour that are indices into fixed lists (no free text). The simulated validators
in `assets/sim.js` follow the majority. Kept in `/data/simvotes.json`, cleared at 00:00 UTC.

`GET /rules` (CORS `*`, cached 60 s) says who holds the testnet's personal-rule places:
`{"places": 2, "taken": 1, "holders": ["<address>"], "checked_at": …}`. The node caps o5
rules at 2 accounts chain-wide and has no command that lists them, so every 5 minutes the
relay takes the candidates from its kept blocks (senders of an o5 rule, acceptors of an
offer) and asks the node `getruleoffers` for each, one at a time. The wallet shows it as
"x of 2 rule places taken".

Fair turns on those places (`slotlease.py`). **The relay is not read-only here: it holds signed
transactions and submits them on a timer.** Right after a visitor's wallet sends a rule, it signs
the neutral clause (which frees the place) for the account's next sequence number and leaves it
with the socket command `leasetx <json>`; the relay accepts only that exact transaction shape and
checks it once with `checktx`. A turn lasts 24 h while nobody waits and 30 min while somebody is
in line (`GET /lease/wait?pk=…`, three accounts per address, kept 3 h). After each rule poll the
relay runs `checktx` again for a turn that is over and then `sendtx`, one at a time; a removal whose
sequence number was used meanwhile is marked stale and never retried. The log names the holder
and the transaction hash, never the payload. `GET /lease[?pk=…]` shows holders, their turns, the
line and your place in it. Kept in `/data/slotlease.json`. Switch off without a rebuild:
`SLOTLEASE_ENABLED=0` in `.env`, then `docker compose up -d relay`.

`GET /peers` (CORS `*`, cached 30 s) is the network as our node sees it: every peer it
talked to or heard of from another peer (a handshake's peer list) in the last 30 days,
from the node's patched `getgovernance.peers` (`node/patches/peer-book.py`; the relay
strips the list before it pushes governance to visitors). Peer IDs only, never addresses.
`{"peers": [{"id", "label", "community", "first_seen", "last_direct", "last_heard", "last_seen", "head", "connected"}],
"counts": {"connected", "met_30m", "met_24h", "seen_24h", "seen_30d"}, "bootnode", "since"}`; `label` is
"IDNI bootnode" for IDNI's bootnode, `community` names a kit node that reported this peer ID
(kit 3 sends `peer=` with its report). Kept in `/data/peers.json`.
`steady` is true once our node has known a peer for `PEER_STEADY_SECONDS` (10 min; the bootnode
always), `online` while a steady peer was seen in the last `PEER_ONLINE_SECONDS` (30 min), and
`counts.online` counts those: pages count only online peers, so a node someone starts for a few
minutes never shows up and a peer does not drop out between two polls.

The alerts service posts one Telegram message per genuinely new node (`maybe_newnodes`): a kit
node or a peer that stayed `NEWNODE_HOLD_SECONDS` (30 min), first seen within the last day, never
the same node twice, at most `NEWNODE_DAILY_CAP` (3) posts a day; nodes already known when it first
runs are not posted. `NEWNODE_ALERTS=false` turns it off.

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
| `availability` live and in sync, 24 h | 10 | 99 % of the checks | 80 % |
| `stability` restarts, reorgs, stalls, 24 h | 15 | none | restart −10, stall −4, reorg −3 |
| `mempool` waiting transactions | 10 | none already in a block, oldest real one up to 10 min | all listed ones already in a block (IDNI #81), or a real one waiting 60 min |

The typical block time (`expected_block_seconds`) is the median gap of the last 100
blocks, stalls left out (60 s until there are enough). `state` is `healthy` from 80
(`HEALTH_OK_AT`), `degraded` from 50 (`HEALTH_DEGRADED_AT`), else `down`; no answer from
the node or no block for 30 minutes is `down` whatever the score. `hours` is
`[hour, average, lowest]` for the last 31 days. `known_issues` lists testnet bugs that cost
points right now (`id`, `url`, `title`, `count`, `points`); today only IDNI #81: the node keeps
transactions that are already in a block listed as waiting, and each costs its share of the
mempool factor. `/status` carries `health`
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

No Memo's intel contracts use the same container: `POST https://node.tauhud.com/tau/intel` with
`{"case", "seed"}` and one of `probe`, `final`, `name`, `reveal` or `lead` (`checker/intel.py`). The hidden rule is
dealt from the seed and `INTEL_SECRET` in `.env` (`up tau` makes it once), and the page sees its text only once the
player names it, shoots at the edge or gives up. A probe runs the rule in the Tau engine the Learn page uses and counts
against the same 40 questions per 5 minutes per address. `up tau` runs six sample rules at their edges and prints
`intel: 6 of 6 hidden rules answer as No Memo's contracts read them`.

## Node follows IDNI main

`follow/idni_follow.py` keeps the node on the newest IDNI tau-testnet main by itself. Every `up` installs a systemd timer
(`tau-idni-follow.timer`, minute 05 and 35 of every hour); nothing else schedules it. One check:

1. Asks GitHub for IDNI/tau-testnet main. Same commit as the node runs: done.
2. Waits while a ship window is on or starts within 90 minutes (`IDNI_FOLLOW_QUIET`, German time, default
   `sat 12-17,tue 16-20,wed 14-18,thu 10-12`) and while a ship is in port or due within 2 hours (relay `/cruise`).
3. Leaves a commit whose IDNI `Dockerfile.standalone` moved to another tau-lang for a repin by hand (a tau-lang rebuild
   takes hours on a CAX11).
4. Builds the node image of the new commit next to the running one; our node patches must still apply, otherwise the
   build stops and the note names the patch.
5. Starts a trial node from that image with an empty chain on the live testnet (no published ports, 1 CPU, 1.5 GB): it
   must sync from genesis to the live tip within `IDNI_FOLLOW_TRIAL_MINUTES` (45) and hold the same blocks as our node.
6. Switches: stops the node, copies its chain data to the volume `tau-follow-snapshot`, sets `TAU_TESTNET_REF` in `.env`,
   `docker compose up -d --no-build`, then the node must answer and be within 3 blocks of the network tip, twice,
   3 minutes apart.
7. If not: the old image and the copied chain data go back, and the commit is not tried again (the next IDNI commit is).

**A new chain.** When the new commit ships another genesis (`networks/tau-testnet-v2/genesis.json`, block 0 hash; first
time IDNI/tau-testnet#93, 12.11.2026), there is nothing to compare it with until IDNI restarts the testnet on it:
- While our node still gets new blocks (its head moved in the last 45 minutes), the check only waits and builds nothing.
  The owner hears once that a new chain is coming.
- When our node has had no new block for 45 minutes, the image is built (and kept) and a trial node must join the new
  chain from the bootnode and reach its tip (past block 0 and at the tip it hears, or its head block is under
  10 minutes old, twice in a row). A trial node that stays on block 0 means the testnet does not run that genesis yet:
  the check waits and tries again after `IDNI_FOLLOW_GENESIS_RETRY_MINUTES` (120). It is never marked failed.
- The switch is the same as above; `infra/node/start.sh` wipes the old chain's data because the genesis differs, and
  relay, alerts and caddy start fresh as `rejoin.sh` does. The node must be past block 0 and in sync.
- Heights here are canonical heads (`getgovernance`), not `getblocks`, which also lists stored blocks that never joined
  the chain (a node on its genesis read "block 1999" there on 12.11.2026).

The owner's private Telegram chat (`up owner`) hears about every switch and once about every commit held back.
`up` shows it under `idni:` as `auto-follow:`. State and log: `/var/lib/tau-idni-follow/`.

The followed commit outlives `up`: `up` builds it as long as `.env.example`'s pin is the one it followed from. A repin
merged here wins.

Turn it off: `up follow off` (or `IDNI_FOLLOW=0` in `.env` and `up`). The node stays on the commit it runs. On again:
`up follow on`. One check now: `up follow now`. Back to the repo pin by hand: `up follow off`, then
`rm /var/lib/tau-idni-follow/state.json` and `up`.

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
- What a change decides differently is read for every case, not sampled (`alerts/rulefacts.py`,
  the same reading as `assets/rulefacts.js` on /proposals/ and /history/): one line per change
  such as "Newly rejected: block height exactly 0 and signature check passed", or "decides
  exactly as before" for the same rules written another way. The Telegram posts carry these
  lines. `relay/rulefacts.py` is the same file (each image copies only its own folder), and
  `test_rulefacts.py` in both folders checks it against the real engine's answers in
  `tests/rulefacts-cases.json` and the pages' lines in `tests/meaning-cases.json`.
- Telegram and X: each event as a post, when the keys are in `.env`. Without keys that
  channel is off; the feed and the page work regardless.
- While one yes vote is enough (one validator), a "proposed" post waits
  `PROPOSED_HOLD_SECONDS` (default 600). If the proposal is agreed meanwhile, one combined
  post "New rule change, agreed right away" goes out instead of two. With more validators
  each step is posted on its own again.

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

**X** (optional, @TauHUDcom): X bills every post since 2026 (credits bought in the
console at console.x.com: $0.015 a post, $0.20 for one with a link). An app there with
user authentication set to "Read and write" (set it before you generate the access token;
a token made earlier stays read-only and posting fails with 403), then the app's API key
and secret and the account's access token and secret as `X_API_KEY`, `X_API_SECRET`,
`X_ACCESS_TOKEN`, `X_ACCESS_SECRET` in `.env` (OAuth 1.0a user context), and
`X_PROFILE_URL=https://x.com/TauHUDcom` for the page's follow link. Then
`docker compose up -d --build alerts donations`.
- What goes to X, each in its own short text: rule changes on the real chain (not practice
  votes), new nodes, "Testnet today", new pages and features (one line each when several go
  together), the smaller site changes, the simulation's switches only with `SIM_POSTS=true` (off since 5 November 2026; `X_SIM=false` keeps them off X),
  the Monday recap picture with the headline of the week's paper, donation thank-yous. Not on
  X: health alarms, visitor proposals, and a major with `"x": false` (announced on X by hand, with its link).
- Site news goes out at fixed times, `SITE_SLOTS` (UTC, default 8,12,16 = 09:00, 13:00, 17:00 German
  winter time): one new page or feature gets its own post, several waiting go together in one post.
  A slot unused 4 hours after its time is over, so nothing posts at night. The smaller changes go out
  once a week, `SITE_DIGEST_WEEKDAY` (4 = Friday) at `SITE_DIGEST_HOUR` (16 UTC = 17:00 German winter
  time), at most `SITE_DIGEST_LINES` (5) by name with the pages' changes before the bot's, the rest counted,
  Telegram only unless `SITE_DIGEST_X=true` (since 6 November 2026; before, up to three digests a day).
- A round-up is a major with `"lines"` ({label, text, link, x} per change: Telegram gets a line and a link
  each, X the short `x` lines that fit) and `"covers"` (the major ids it replaces; they and the digest so far are
  not posted on their own). A major's `"image"` also shows large above its Telegram text.
- Layout: the headline first, the text, then one line saying where it comes from, with
  `#TauNet $AGRS` (always both, once, never more tags). A picture goes along where one fits (`X_PICTURES`): a rule change's card and the
  live overview from the share service, a new page's screenshot (`"image": "/assets/shots/<id>.png"` in its
  `major`, required by CI for every new major), else its own preview picture, else the site's; the post stays
  $0.015, and without a picture the text goes alone.
- No links in X posts (`X_LINKS=true` adds them), except the blog's one post per article, which carries the
  share page's link ($0.20 instead of $0.015; its card shows the picture; `X_BLOG_LINK=false` leaves it out); `X_DAILY_CAP` (8) and `X_MONTHLY_CAP` (240, about
  $3.60) posts at most, the rest stays on Telegram. The simulation and the smaller changes leave the
  day's last `X_RESERVE` (2) posts for the real chain. An X failure never holds up Telegram; it is
  logged and that X post is left out.
- "Testnet today" (`TESTNET_TODAY_HOUR`, 19 UTC) goes out every evening since 2 November 2026, a quiet day included:
  with blocks and no transactions it says so (Telegram only); without a block in 24 hours it says since when the
  chain stands still, and that one goes to X too. A restart and a stall of 20 minutes get their own posts anyway.
  Since 6 November 2026 it leads with who sent: the wallets active that UTC day by kind, from the relay's
  `/wallets/active` (IDNI's genesis accounts, our island bot, the cruise ships' simulated passengers by ship name
  from `/cruise/log`, White Rabbit Key players, Agorzilla's feeders, wallets that sent from a Tau HUD page, others),
  against the mean of the seven days before ("3.5× the usual 22"), the wallets seen for the first time, and one
  "Why it matters" line drawn from those facts (a spike, strangers, newcomers, a quiet day, a rule change). X gets
  it only on a day worth telling: a rule event, no block, 1.5× the usual wallets or more, or three or more newcomers.
- `docker compose run --rm --no-deps alerts python alerts.py --check` asks each channel, without posting, whether the
  service may post there: Telegram's token and the bot's standing in the channel (it must be an administrator with
  Post messages), Tau HUD's X keys and Agorzilla's (`GET /2/users/me`). The service runs the same check when it
  starts, `up` prints it after every deploy, and the answers, the last good send and the last error of each channel
  are in `posting.json` next to `proposals.json`. A channel that is on and takes no post from the alerts service for
  `SILENCE_HOURS` (26) gets a warning in the log and in `posting.json`, so a quiet channel is noticed before someone
  asks. The last good send and the last error are kept in the state file, so a restart does not forget them, and
  `--check` adds when the alerts service last posted to each of its channels. Before 4 November 2026 they lived only
  in memory, and the first check after `up` counted from the service's very first start ("SILENT for 28 hours"
  although both channels had posted shortly before).
- An X copy never waits for Telegram: when the Telegram send fails (a token gone bad, the bot no longer admin in the
  channel) or the channel is off, the X copy goes out alone, once, and the Telegram post follows when the channel is
  back, without a second X post. The same holds for Agorzilla's evenings (`agorzilla.py`). Before 2 November 2026
  one failing Telegram send held every X post back, and both accounts went quiet together.
- A closer look at one page a day lives in `assets/deepdives.json` (in order, each id once, ever; add new pages at
  the end): Telegram at `DEEPDIVE_HOUR` (13 UTC = 14:00 German winter time) with the page's picture and a button,
  every `DEEPDIVE_X_EVERY`-th (2nd) one also on X as a spare post, on the days `DEEPDIVE_DAYS` (0,2,4 = Monday,
  Wednesday, Friday since 6 November 2026; before, every day). `--deepdives-preview` prints the ones still to
  come; `DEEPDIVES=false` stops them. The file is read from the site, so a new entry needs no server step.
- The Key Crier (White Rabbit Key): the relay's `/isle` summary is read every `ISLAND_POLL_SECONDS` (600) and the
  last reading of a UTC day is that day; at `ISLAND_HOUR` (7 UTC = 08:00 German winter time) Telegram gets the day
  before (campaigns, elections and who won, the players' moves by kind, the law of the day, the islanders' own
  moves), only for a day a real player moved (since 6 November 2026; a day nobody played gets no report, the
  islanders' own politics are not news), with the standing explanation of the campaign cycle on Monday only, with
  the governor's count; its length is read from `rabbit/game.js` (`ISLAND_DAYS`, 5, when unreachable). X gets it
  only for a day with a story (an election won or a law passed by real players, since 7 November 2026; a day of moves
  alone stays on Telegram), told as that story with the live island painting, at most every `ISLAND_X_EVERY_DAYS` (1)
  days, as a spare post; the Monday governor's count always.
  `--island-preview` prints today's so far; `ISLAND_CRIER=false` stops it.
- Nothing is posted late in a burst after a restart: the Monday recap is skipped once it is `RECAP_LATE_HOURS` (3)
  late, Agorzilla's evenings older than `AGORZILLA_LATE_HOURS` (6) are noted and not posted (on 2 November 2026 the
  service came back after two days and posted the recap, the day and three evenings in one minute).
- Posts planned ahead live in `assets/posts-plan.json` (the month's calendar: a spotlight on a page on Wednesdays,
  the rule challenge's last days on Fridays, dated events): each is sent once at its `at` time (UTC) on Telegram and
  X, or within 3 hours after it, never later. `--plan-preview` prints the ones still to come; `POSTS_PLAN=false` stops them.
- `docker compose run --rm alerts python alerts.py --x-preview` prints what X would get now,
  with X's own character count; `--x-test` posts one test post on X only.

**Agorzilla on X**: `alerts/agorzilla.py` also posts each evening's result and every new
growth stage on Agorzilla's own X account, with the creature on a dark 16:9 card, no links,
at most `AGORZILLA_X_DAILY_CAP` (8) a day. Keys: an app made at console.x.com while signed
in as that account, as `AGORZILLA_X_API_KEY`, `AGORZILLA_X_API_SECRET`,
`AGORZILLA_X_ACCESS_TOKEN`, `AGORZILLA_X_ACCESS_SECRET` in `.env`; then
`docker compose up -d --build agorzilla` and
`docker compose run --rm agorzilla python agorzilla.py --x-test` (one test post on X only).

**Agorzilla's archive and summary**: service `agorzilla-latest` runs the agorilla repo's
`tools/archive.cjs --live` every 10 minutes from the site checkout in `/opt/sites/agorilla`
and writes `archive.json`, `archive.js` and `latest.json` to `/opt/sites/agorilla-live/chain/`.
`sites/agorzilla.caddy` (copied to `/opt/sites/`) serves those first and the checkout's copies
otherwise, so neither the page nor the evening post waits for GitHub's schedule, and a testnet
restart between two skipped GitHub runs loses no meals. The repo's own Action still commits the
public copy. A checkout from before `--live` makes only `latest.json` (`--latest`); each run is
cut off after 5 minutes. Log: `docker compose logs --tail 20 agorzilla-latest`.

**Agorzilla's evening pictures**: service `agorzilla-shots` (`agorzilla-shots/shots.mjs`, a
headless Chromium) opens `agorzilla.com/?shot=<evening>` after each evening and photographs the
creature just before and just after it into the volume `agorzilla_shots`
(`evening-<n>-before.jpg`, `-after.jpg`, `evenings.json`). The evening post sets the two side by
side on one card for Telegram and X (it waits up to 25 minutes for them, then posts the text
alone); agorzilla.com serves them under `/evenings/`. Picture one evening again by hand:
`docker compose run --rm agorzilla-shots node shots.mjs --once <n>` (n counts from 0).

**Donation thank-yous**: `alerts/donations.py` (service `donations`, same image) reads
incoming AGRS (contract `0x7388…bdda` only, so look-alike tokens are ignored) and ETH
transfers to the donation address every 5 minutes, above a small minimum
(`DONATION_MIN_AGRS`, `DONATION_MIN_ETH`). Each new donation gets one post, the sender
named only by a shortened address; a donation is remembered and never posted twice, and on
the first run only donations younger than 3 days are thanked. Transfers from your own
wallets: list them in `.env` as `DONATION_IGNORE_FROM=0x…,0x…`. With `ETHERSCAN_API_KEY`
in `.env` it reads Etherscan instead of Blockscout.
- `docker compose run --rm donations python donations.py --preview` lists what it finds and
  the post the newest donation would get, and posts nothing.

**Weekly recap**: every Monday 09:00 German time, 08:00 UTC in winter and 07:00 UTC in summer (`RECAP_WEEKDAY`, `RECAP_HOUR`, `RECAP_TZ`) `alerts/recap.py`
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

**The weekly newspaper**: in the same Monday slot, right after the recap image,
`alerts/gazette.py` writes that week's edition of The Daily Consensus (the site's
`gazette/` page) in English and Chinese: a headline chosen from the week (a rule change in
force, agreed, a fresh chain, new proposals, new nodes, or a steady week), the lead story,
the week in figures, the rule changes still waiting, and the visitors' week in the
simulation. For that last part the watcher notes `/sim/votes` and `/sim/predictions` every
ten minutes, because the relay starts them over at midnight UTC. Files:
`https://node.tauhud.com/recap/gazette/latest.json`, `/recap/gazette/<date>.json` and
`/recap/gazette/editions.json` (newest first; `number`, `headline`, `deck` and their `_zh`
twins are what the HUD's notice of the paper reads). The page sets the latest edition as
its front page; `gazette/?edition=<date>` opens an older one. The first edition is written
as soon as the service starts and none exists yet. The words stay careful: read from the
chain, plans are IDNI's, testnet AGRS have no value, nothing is offered.

- `docker compose run --rm alerts python alerts.py --gazette-now` writes an edition of
  the last 7 days now (it keeps the number if one is already out today).
- `docker compose run --rm alerts python alerts.py --gazette-reprint` prints the latest
  edition again with the current wording: same number, date and week.

**Health alerts**: once a minute the watcher reads `/health-score` and posts to Telegram
when the testnet goes down (score under 50, the relay says `down`, or the relay does not
answer) and when it recovers (score 70 or more), each only after the new state held for
10 minutes (`HEALTH_DOWN_BELOW`, `HEALTH_UP_AT`, `HEALTH_CONFIRM_SECONDS`). The post names
the factors that lose the most points. The state on the first run is not posted.
`HEALTH_ALERTS=false` turns it off.

**Firsts** (`alerts/firsts.py`): the first time the real chain carries a returnable
payment, a payment taken back, a personal rule that reads the block time, a co-signer
rule, a payment waiting for its co-signer or a co-signer's approval, the bot posts it once
on Telegram and X (firsts that land within 10 minutes of each other share one post; the
first run is silent). The kinds go into `proposals.json` as `firsts`, and the HUD's
"Money with terms" card switches to "seen on the testnet" with a link to the first one.
`FIRSTS=false` turns it off.

To show them ourselves, `node/tools/money_demo.py` sends them between three test wallets
of our own (about 25 minutes, keys kept in the node volume at `/data/money-demo.json`):
`cd /opt/tau-command-hud/infra && docker compose exec -T tau-node python - < node/tools/money_demo.py`.
Steps 3 to 5 need one of the testnet's two personal-rule places; the script frees it again
at the end.

**Findings** (`alerts/findings.py`): once a minute the watcher also looks for unusual
things on the real chain and posts each incident once when it starts and once when it
is over: our node without the IDNI bootnode or any peer (10 min), no new block while
connected (20 min), ghost transactions (IDNI #81, no recovery post),
a reorg of 2+ blocks, blocks at under half the usual pace for an hour, a spike of
dropped transactions, our node 30+ blocks behind (IDNI #78). After a peer outage the
recovery post says, from the caught-up blocks' timestamps, whether the testnet kept
going or really paused. Every start post says in one line why it matters to someone using the
testnet. The same detector stays quiet for a while after an incident: two days for ghosts,
dropped transactions and repeated votes (since 6 November 2026), hours for the outages.
From the 4th start in 6 hours on (`FINDINGS_STORM_AT`, `FINDINGS_STORM_HOURS`) nothing
is posted one by one; the list goes out once, after 2 calm hours or at 21:00 UTC.
On X: peer outages without any peer, stalls, reorgs and busy-stretch summaries, at most
`FINDINGS_X_DAILY_CAP` (3) a day. While a posted finding covers an outage, the health
alarm above stays quiet. `FINDINGS=false` turns it off.

- `docker compose run --rm alerts python alerts.py --findings-preview` prints what the
  detectors see now, the replay of the 29 Oct bootnode outage and one of each post.

Logs: `docker compose logs -f alerts`.

## Question bot

The bot that posts to `@tauHUDcom` also answers anyone who writes to it (`alerts/bot.py`,
service `bot`, same image as alerts, same `TELEGRAM_BOT_TOKEN`; nothing else to set up):

| Ask | Answer | Source |
|---|---|---|
| `/height`, "height?" | block height, age of the last block, block pace | relay `/uptime`, `proposals.json` |
| `/proposals`, "last proposal?" | coming up (votes, deadline), agreed, in force, in the alerts' plain words | `proposals.json` |
| `/tx <hash>`, "is my tx in? <hash>", a 64-hex hash | in a block / waiting / expired / refused / not known | relay `gettxstatus` |
| `/address <address>`, a 96-hex address | confirmed balance, amounts waiting for a block | relay `getaccountstate` |
| `/block <n>`, "block 12?" | when it was made, what it holds | relay `getblockrange` |
| `/status`, "is it running?" | node online, in sync, availability over 24 h, restarts in 7 days | relay `/uptime` |

Every answer links to the matching tauhud.com page. It long-polls Telegram (`getUpdates`),
so no webhook and no open port. In groups it answers only commands (and `/cmd@ourbot`
only, when several bots are there); it never posts into the alerts channel. Each person
gets 5 questions in a row and one more every 8 s (`BOT_USER_BURST`,
`BOT_USER_REFILL_SECONDS`); past that it says so once and stays quiet. Questions sent
while the bot was down for more than 2 minutes are skipped. Telegram's command menu is
set on start.

In the channel: a channel has no member messages, so link a discussion group to it
(channel settings → Discussion) and add the bot to that group as a member. People then
ask with commands under any post or in the group; the channel's own posts copied into
the group are ignored. Privacy mode can stay on (it lets commands and mentions through).

- `docker compose run --rm bot python bot.py --ask "/proposals"` prints one answer and sends nothing.
- `docker compose logs bot | grep answering` shows the bot's username.

Making it visible in the channel:
- Every alert and recap post carries three buttons (Ask the bot, Height, Status) that open
  the bot in a private chat with that question asked (`t.me/<bot>?start=height`).
  `TELEGRAM_BOT_USERNAME` (default `tauhud_alerts_bot`, empty = no buttons).
- `docker compose run --rm bot python bot.py --post-howto` posts an "Ask the bot" message
  with the commands and the buttons to the channel and pins it (the bot needs the "Pin
  messages" admin right; otherwise pin it by hand).
- A command a channel admin posts in the channel itself (`/height`) is answered there and
  the command post is removed. Only admins can post in a channel, so this is for showing.
- Channel Direct Messages (channel settings → Direct Messages): messages people send to the
  channel arrive at the bot when it is a channel admin and are answered in that
  conversation, like a private chat.

Logs: `docker compose logs -f bot`.

### Personal alerts

In a private chat the bot also follows things for one person (`alerts/follow.py`), opt-in only:

| Command | What it does |
|---|---|
| `/follow <address>` | a message when the account sends or receives test AGRS, its own rule lands in a block, it gets or makes a rule offer or co-sign request, it votes, and on every vote on a rule change it proposed |
| `/follow <rule change id>` (or its first 16 characters) | a message on every vote and when it is agreed, takes effect or is dropped; then it stops by itself |
| `/unfollow <address or id>`, `/unfollow all` | drops one, or everything |
| `/following` | the list |
| `/stop` | forgets the chat completely |

tauhud.com links straight to it: "Telegram alerts" on an account page, in the wallet and on a proposal
open `t.me/<bot>?start=<code>`, the code being the address (48 bytes) in base64url, or `p` + the rule change id
(32 bytes) in base64url, so the person only presses Start.

Stored in `/state/follows.json` (volume `alerts_state`): per chat its Telegram chat id, what it follows and since
when, nothing else; plus the last block looked at and each rule change's status and vote count. `/stop`, blocking the
bot, or 60 days with nothing followed deletes a chat. Every `FOLLOW_EVERY` (20) s the bot reads the new blocks from
the relay and `proposals.json`; one message per chat per round, at most `FOLLOW_HOURLY` (20) an hour per chat, then
one "pausing" note. Limits: `FOLLOW_MAX_ADDRESSES` 10 and `FOLLOW_MAX_PROPOSALS` 20 per chat, `FOLLOW_MAX_CHATS`
5000. After a chain restart, or more than `FOLLOW_BACKLOG` (300) blocks missed, it starts at the tip without old news.
`docker compose exec bot python -c "import follow; print(len(follow.Store().chats))"` shows how many chats follow something.

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

## Public API and badges

For other sites; documented with copy-paste snippets on https://tauhud.com/developers/.
All CORS `*`, read-only, no key.

| Path | What |
|---|---|
| `/api/v1/summary` | one object: status (`synced`, `catching_up`, `offline`), height, tip, last block time, pace, spec revision, base fee, validators, proposal counts (`waiting`, `agreed`, `in_force`, `dropped`), mempool, viewers, community nodes, `health` (when `/status` carries one). Cached `API_CACHE_SECONDS` (10 s). |
| `/api/v1/badge/{height,status,proposals,validators,health}.svg` | live badges in the site's colours, cached 60 s |

Within v1 fields are only added, never renamed or removed. `/api` redirects to the docs.
The embeddable widget is a static page on tauhud.com (`/embed/?panel=…`) that polls the summary.

## Visitor numbers

`relay/visits.py`: cookie-free counts for the site owner, so it shows which pages people open and stay on.
Every page's header (`assets/nav.js`) sends `GET /v?p=<page>&r=<referrer>&s=<tag>&l=<lang>&m=<sim|live>&w=<width>`
when it opens and `GET /v?p=<page>&e=1` after 30 s visible. The relay keeps only daily totals in `/data/visits.json`:
views, visitors and "stayed 30 s" per page, referring site (host name only), `?ref=`/`utm_source` tag, previous
Tau HUD page, language, sim or live, screen class, hour of day.

- No cookies and nothing stored in the browser (only `?nostats=1`, on request, leaves a browser out).
- A visitor is a hash of address + user agent with a random salt that lives in memory and changes at 00:00 UTC;
  addresses and user agents are never written down. Do Not Track, Global Privacy Control and bots are not counted.
- Report: `https://node.tauhud.com/visits?key=<key>` (`/visits.json?key=` for the raw counts). The key is
  `VISITS_KEY` from `.env`, or made once and kept in `/data/visits.key`:
  `docker compose exec relay cat /data/visits.key`

## Rico's voice (White Rabbit Key)

Rico, the DJ on Radio Coco in /rabbit/, speaks his lines aloud when the server has his clips. Every line he can say
is fixed in `rabbit/rico.js` (numbers and block heights are only shown, never spoken), about 50 lines and under
4,000 characters, so the clips are made once with ElevenLabs and kept in `/opt/sites/rico`, which Caddy serves at
`https://node.tauhud.com/rico/`. A line without its clip stays text, as before.

```
echo 'ELEVENLABS_API_KEY=YOUR_KEY' >> /opt/tau-command-hud/infra/.env
cd /opt/tau-command-hud && python3 infra/rico/make.py samples          # then listen at https://node.tauhud.com/rico/samples/
cd /opt/tau-command-hud && python3 infra/rico/make.py make --voice NAME
```

`design` draws three new voices from a description (Caribbean radio host by default) and `keep N` keeps one as "Rico" and makes every clip; both need a key with Voice Generation: Access and Voices: Write. `voices` lists the account's voices (a Voice Library voice must first be added to My Voices), `lines` shows the
lines and their characters without a key. After new lines in rico.js, run `make` again: it only makes the new ones;
a different `--voice` makes them all again.

## Tests

```bash
pip install websockets==15.0.1
python relay/test_relay.py
python relay/test_uptime.py
python relay/test_health.py
python relay/test_api.py
python relay/test_simvotes.py
python relay/test_visits.py
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
python alerts/test_bot.py       # -v prints the answers
```

Runs the question bot against a mock relay and a mock Telegram: every question type,
plain questions in private chats, groups only with commands meant for this bot, nothing
into the alerts channel, old questions skipped, and the per-person limit.

```bash
pip install websockets==15.0.1 pillow==11.3.0
python share/test_share.py      # OUT=/tmp/cards also writes the cards to look at
```

Runs the share service against a mock relay: the chain is read in pages, every card is
a 1200×630 PNG, the link pages carry the tags and send on to tauhud.com, bad paths are
refused, and a chain restart is reloaded.

Runs the checker against the real engine: verdicts for sample transfers, refusals by
the text screens and by the engine.
