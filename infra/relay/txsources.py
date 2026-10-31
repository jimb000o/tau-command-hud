"""Where the testnet's transactions come from: Agorzilla, Tau HUD, or somewhere else (tauhud.com/meta/).

Every transaction in the blocks the relay holds is put in one of four groups:

  agorzilla  it pays one of Agorzilla's addresses (the bowl, a ballot box or a question box). These addresses have no
             key (hash_to_curve, see the agorilla repo's tools/addresses.mjs), so only a meal or a vote sends there,
             wherever it was signed.
  tauhud     it was sent through this relay's wallet door from a Tau HUD page (wallet, playground, vote, …), or by the
             relay itself (the end of a turn on a rule place).
  idni       sent by one of the accounts the testnet started with (tau-testnet networks/tau-testnet-v2/genesis.json,
             accounts_state), which IDNI set up; on this testnet they make most of the traffic.
  other      everything else: other wallets, scripts and tools.

The relay remembers the hashes it sent, with the site the page came from and, for Tau HUD, the page that led the
visitor to the wallet (the wallet says it with "via <page>" before a send), in SENT_PATH: only hashes, a site name and a
page name; no address, no browser. Wallets are distinct sender keys, not people.

GET /api/v1/sources
  days       {"YYYY-MM-DD": {group: [txs, wallets, new wallets, returning wallets, test AGRS moved]}}; new = first
             seen in that group in the blocks the relay holds, returning = also seen there on an earlier day
  ours       {"YYYY-MM-DD": [...]} the same for Agorzilla and Tau HUD together (a wallet on both counts once)
  totals     {group or "ours": {"7": n, "30": n, "all": n}} distinct wallets over the last 7 / 30 days / all held
  hours      {"YYYY-MM-DD": [24 counts]} our two sites' transactions per UTC hour, the last 31 days with any
  agorzilla  {"YYYY-MM-DD": {"meals", "snacks", "votes", "asks", "agrs", "wallets", "new", "hours"}}
  starts     {"YYYY-MM-DD": {source: {kind: txs}}} where our two sites' transactions started: "agorzilla" (kinds meal,
             vote, wish, other), "deja" (Déjà the café cat, kind meal) and "tauhud:<page>" (the page that led to the
             wallet: start, rules, card, hud …; "" before the relay kept pages, "relay" for the end of a rule-place
             turn; kinds send, rule, vote, shared, other)
  rabbit     {"YYYY-MM-DD": {"moves", "rivals", "lines", "votes", "agrs", "wallets", "new", "cands", "by", "hours"}}
             White Rabbit Key (tauhud.com/rabbit/) on the testnet: every transaction that pays the island council or one
             of the four ballot boxes (rabbit/game.js ADDR). rivals = the rival candidates' moves, sent by the island bot
             from its campaign wallets (island.py, `bots`); lines = the visitors' own Book lines to the council; votes =
             visitors' ballots, cands = ballots per candidate, by = rival moves per candidate; wallets / new = visitor
             wallets that day and the ones playing on the chain for the first time; hours = moves per UTC hour
  since, sent_since   first block time held, first remembered send

The "agorzilla" part follows Agorzilla's own reading (agorilla assets/core.js): a meal pays the bowl at least 1 AGRS,
a snack is a meal by a wallet that already ate in the hour before, a vote is a meal that also pays a ballot box, an ask
one that pays a question box. agrs = test AGRS put in the bowl, wallets = feeding wallets that day, new = wallets
feeding for the first time in the blocks the relay holds, hours = meals per UTC hour.
"""
from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger("relay.txsources")

GROUPS = ("agorzilla", "tauhud", "idni", "other")
OURS = ("agorzilla", "tauhud")   # the two sites we run
SENT_MAX = 50000
# Agorzilla's addresses (agorilla repo assets/core.js: BOWL, BOXES, ASKS)
AGORZILLA = frozenset({
    "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108",
    "931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392",
    "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4",
    "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b",
    "ad628e861687c726aa780c4af1d4e10df4e16c169772686ada8ed81e430ec7bd70214bb732d9b7a75fb4d968136cec86",
    "940bad7f401e65b0ddfd2b891251cdb3f027dc96bbe4d64b5ea5547900338107186cc23d500c1888598ccc4343f6df2e",
    "b6bdcade83f317c5a3e0402466a4f6c93a1b9018a3dd61026143c8284741fad2deeffda9a7fd3db587e86f4f44de3418",
    "992d87e93030634c581fc3e6c574af0da06c70798d49f82135d8231147b79c071e277616d84fb6175dbeae2264377071",
    "b09ad0b1742efd5a4a4e7fa93a52b9f5954466ca2f694db9dfda4d593d9c15a73dfdd9055ad286e8f11f76b0f69395cf",
    "8dbae75034a8cdc776e462f004dd686c8d0a32dbedd400483a026a01db4ce1f78b9d6450d2c832d8116d47a315fd8973",   # Déjà's bowl
})
DEJA = "8dbae75034a8cdc776e462f004dd686c8d0a32dbedd400483a026a01db4ce1f78b9d6450d2c832d8116d47a315fd8973"   # agorilla assets/cat.js
VIA_MAX = 24


BOWL = "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108"
BOXES = frozenset({
    "931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392",
    "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4",
    "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b",
})
MEAL_COOLDOWN = 3600
# White Rabbit Key's addresses (rabbit/game.js ADDR): the island council and the four candidates' ballot boxes
RABBIT_COUNCIL = "96179f47d33ab65d9922c5652d7686f9e6be9d36ef4b9e9e04bdaac25b6e30d01928182c16da7aaa6dc954cccb88b62b"
# the island's places' tills (rabbit/game.js TILL): a move paid where it happened counts like one paid to the council
RABBIT_TILLS = {
    "89798ff443b446b8392097e50bb61f383f24ed60f45b4f592e6b9d5356056e90698e7114f17692bdd2539bce24d73ac2",
    "b6ef83b962c9e8be7345050bc34de31bc8996cfc3782947db4509f48750b53640b19d7211c591bc2e4e16d2b148bf945",
    "b3909c612e07036be9504e3be10eef3b1483e0c1c7be4d05950ccb373f06292f186709c7344e5aa7b83501ce7f1d48af",
    "a752d4269c95abd44c6ec855ce3513f6ce8b3a8c94f58621ee1596ceb728a69aa329a541a9f75a188fdfff92ad6c045d",
    "87208cfd4313f66ec1baa2021ff0fdd5667285be5396a4a83480efc18d80ba3c2e41504d2bcd2b01a8d37a6cab54cd05",
    "98e2aa832d79c1689b6b3190d45e0c2319838c0f58293e6a837d606548f2c1e797b20550e0c5230a7cebbc13f74e849f",
    "8ed60ef9cc93ec996d7eeac725539e720f86b701bdb7ac646434d177690e48869dbfdedc759c930dc88f1e3cd315c58b",
    "98e8a33fa10f0dca59bb6fe8c9d14fb2e9b6be5cbeb95d862fc4eb9ad2d5957617f8b998757f9947065cd76c05a82578",
    "899220e0128f24e1666fdaf53809c16854bc37cfcac3aa9a887e7e0205fff14de93c5b1272e1c5204ad4c1f1ee7c11de",
    "816cdcda9accef093332ca8356f87fb1a40aa612d999b55d8cc7229865508ad09bd1214ba6f4b16a6dc8b64d03fa852d",
    "81a080eed60d737f73623b80d3b1dcad85d37b5a5a4d5b0ba60c3c2379b995d470c8c2d3db2f92b803b7feb215091d16",
    "83546df43205836667fc104c6a56549b2b0c0cd5fd0bc188ad55e96ce656c8220991325fdd49ef8a5549bb7ca9d1cb3e",
    "8ffb79523db95c885e3267633767246dda76cc9378804b02328835ba45667d7012be8b79f32e497d1822d1df96726d3d",
    "96e0c6d33c1848fa6a2355ababc5f66a7a8121c81a05f923c3e60d645f0110fe28a81db5176f750adec25b26b8746bf9",
    "897178ec1333edd5d3cb27f5746976e6cb8fd0d07360a8dcdfccd1f0a90d15f5a2f8b24616acb5ebfa360b86bc025175",
    "82a45ff8fd1bbba834c5c9f89e8ebb712935f83aa2709cdda051deebec517483e73fc6eeb997ebbaf2dc582a2eea56dc",
    "a974149276f73fa2021068c89521bc68e8877cbfdb7d75b348951269bc3ab6c0677997f31bdbb1d28c95dc3aacacd34e",
    "9266b7dbca59d06c60517e815e32169aaba70056101d394c6ab851a99925f18e23da324cf0c73ab5fe27c951c8bb024e",
}
RABBIT_BOXES = {
    "b44a202e884682b8677daf5f2685b5775f3c9ea9443a89651013bc455bc66061f2cf8d092897893bad3311e598f2cb11": "marisol",
    "96bf03fb7c34b84f916d928cf82bd332cd9558ab3c55e9a717381fe5c8cc6d4ec1e694e39855a680ea8f29351d6a2aea": "tobias",
    "981bfa68b487e86991cbd70d3c1c8ed4b151715031580976f0942610958a16e29d71c15ea4accdb3750db225f35c3f50": "baako",
    "adf1b27a6cfe88b1c73f12ed38eaaef535f892ee2f2b695030427ecaef7d4e43deb89f7849f2f5550cc5eec711652174": "hana",
}


def moved(tx: dict) -> int:
    """Test AGRS the transaction sends (all transfers added up)."""
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    n = 0
    for op in ops.get("1") or []:
        if isinstance(op, (list, tuple)) and len(op) >= 3:
            try:
                n += max(0, int(op[2]))
            except (TypeError, ValueError):
                pass
    return n


def meal(tx: dict) -> tuple[int, bool, bool] | None:
    """(AGRS put in the bowl, voted, asked) for a transaction Agorzilla reads as a meal, else None."""
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    sender = str(tx.get("sender_pubkey") or "").lower()
    fed, box, ask = 0, False, False
    for op in ops.get("1") or []:
        if not isinstance(op, (list, tuple)) or len(op) < 3 or str(op[0]).lower() != sender:
            continue
        try:
            amount = int(op[2])
        except (TypeError, ValueError):
            continue
        if amount < 1:
            continue
        to = str(op[1]).lower()
        if to == BOWL:
            fed += amount
        elif to in BOXES:
            box = True
        elif to in AGORZILLA:
            ask = True
    return (fed, box, ask) if fed >= 1 else None


# the genesis accounts of tau-testnet-v2 (genesis.json accounts_state), set up by IDNI
GENESIS = frozenset({
    "f427fbf4cb8cc5ebcfc50add98ba574b94c03b1e32626e2e50cf60ba5e0a6d0c42d3ed702c2e0eeef7fae29bc4f3d2f9",
    "838d089401687e4ba5fe844f1241b2f6cf63cf73a7f8fb6aa0e45b3c6b85454f4e7ca19960b71d847655486495b64cb4",
    "93da919aed3b83e517190b8362528b35cbd51beb754289c5d99db12a306ac7f4980fbb96108a9cb812a46aede0c5f9ca",
    "8a39b9d9498535492290c52b44959b5a6e9177dc85ae6a1d97f54462f03c15a38052a85c7ace5cd81858e343a3b789d0",
    "b1337fcdf8d713a53518f0d6289c70bec2a09a7d6ec84548aac208988391cd66a9b627d03c07d922cd6ad15ebecf3ad7",
    "b3566dd294833030380d74b39fdb0bf214e9c64906b175f8822c3d4386602b1a9340231e553f9c299d6d8a82b9d441da",
    "af1d997703d7c0a86a5988762bb9ac2642890b5f0599f9821372684487d580a5f211ec160c038c073cda604c3c646487",
    "9689f5f8ffe6b73bb549e4058e54a3fc6a96ef2e784c415adeffd83d9488c9b435f075b59a778308f86226074f8b09b0",
    "916b92be0561ee21d042d033cabdf58d1c2f9ed110b2e173ab9cdd2a585442bec6232ffe0d97b779976a1dfd6a9d38fc",
    "b9e4b8fbe06a12f4702617f71ef031206426c4205ca0bc3436d2e0cb047fd18473ad125ceefc7ef18b851a19af2f370b",
    "8df32da800ad4b0657e333774889e6b08f768ab055ffb964d5935bbc8460aa8f91fa60a6a042f64ec144c7ec18ae02a3",
})


def rabbit(tx: dict, bots: dict) -> tuple[str, str] | None:
    """("rival" | "line" | "vote", candidate) for a White Rabbit Key transaction, else None."""
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    sender = str(tx.get("sender_pubkey") or "").lower()
    for op in ops.get("1") or []:
        if not isinstance(op, (list, tuple)) or len(op) < 2:
            continue
        to = str(op[1]).lower()
        if to == RABBIT_COUNCIL or to in RABBIT_TILLS:
            return ("rival", bots[sender]) if sender in bots else ("line", "")
        if to in RABBIT_BOXES:
            return "vote", RABBIT_BOXES[to]
    return None


def group(tx: dict, tx_hash: str, sent: dict) -> str:
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    for op in ops.get("1") or []:
        if isinstance(op, (list, tuple)) and len(op) >= 2 and str(op[1]).lower() in AGORZILLA:
            return "agorzilla"
    site = sent.get(tx_hash)
    if site is not None:
        return site.split("|")[0] or "tauhud"
    if str(tx.get("sender_pubkey") or "").lower() in GENESIS:
        return "idni"
    return "other"


def start(tx: dict, tx_hash: str, g: str, sent: dict) -> tuple[str, str]:
    """(source, kind) of one of our two sites' transactions, for "where they started"."""
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    if g == "agorzilla":
        if any(isinstance(op, (list, tuple)) and len(op) >= 2 and str(op[1]).lower() == DEJA for op in ops.get("1") or []):
            return "deja", "meal"
        m = meal(tx)
        return "agorzilla", ("vote" if m[1] else "wish" if m[2] else "meal") if m else "other"
    via = (sent.get(tx_hash) or "").partition("|")[2]
    t = str(tx.get("tx_type") or "")
    kind = ("rule" if ops.get("0") else "send" if ops.get("1") else "other") if t in ("user_tx", "") else \
        "vote" if t.startswith("consensus_rule") else "shared" if t.startswith("rule_offer") else "other"
    return "tauhud:" + via, kind


class TxSources:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("SENT_PATH", "/data/sent.json")
        self.sent: dict[str, str] = {}   # tx hash -> "" (Tau HUD) or the other site's name, oldest first
        self.since = time.time()
        self.bots: dict[str, str] = {}   # the island bot's campaign wallets: pubkey -> candidate (island.py)
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("sent"), dict):
                self.sent = {str(k): str(v) for k, v in st["sent"].items()}
                self.since = float(st.get("since") or self.since)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting afresh", self.path, exc)

    def note(self, tx_hash, site: str = "", via: str = ""):
        """A transaction the relay passed to the node and the node took; via = the Tau HUD page that led to the wallet."""
        if not isinstance(tx_hash, str) or not tx_hash or len(tx_hash) > 128:
            return
        self.sent[tx_hash.lower()] = site + ("|" + via[:VIA_MAX] if via else "")
        while len(self.sent) > SENT_MAX:
            del self.sent[next(iter(self.sent))]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"since": self.since, "sent": self.sent}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; sent hashes live in memory only", self.path, exc)
                self._warned = True

    def by_day(self, blocks: list[dict]) -> dict:
        """Counts per UTC day from the blocks (oldest first) the relay holds."""
        days: dict[str, dict] = {}
        ours: dict[str, list] = {}
        hours: dict[str, list] = {}
        agz: dict[str, dict] = {}
        starts: dict[str, dict] = {}
        isle: dict[str, dict] = {}
        played: set = set()                    # visitor wallets that made a White Rabbit Key move
        isle_last: dict[str, str] = {}         # visitor wallet -> last day it played
        bots = {k.lower(): v for k, v in self.bots.items()}
        seen_day: set = set()                  # (day, group, wallet)
        first_day: dict[tuple, str] = {}       # (group, wallet) -> first day seen
        ever: dict[str, dict] = {}             # group or "ours" -> wallet -> last day seen
        ate: dict[str, int] = {}               # wallet -> time of its last counted meal
        first = last = None
        for b in blocks:
            try:
                ts = int((b.get("header") or {}).get("timestamp"))
            except (TypeError, ValueError):
                continue
            if ts > 0:   # the genesis block carries time 0
                first = ts if first is None else min(first, ts)
                last = ts if last is None else max(last, ts)
            day = time.strftime("%Y-%m-%d", time.gmtime(ts))
            ids = b.get("tx_ids") or []
            for i, tx in enumerate(b.get("transactions") or []):
                if not isinstance(tx, dict):
                    continue
                h = str(ids[i] if i < len(ids) else tx.get("tx_hash") or "").lower()
                g = group(tx, h, self.sent)
                s = str(tx.get("sender_pubkey") or "").lower()
                amount = moved(tx)
                row = days.setdefault(day, {k: [0, 0, 0, 0, 0] for k in GROUPS})
                keys = [g] + (["ours"] if g in OURS else [])
                for k in keys:
                    r = row[k] if k != "ours" else ours.setdefault(day, [0, 0, 0, 0, 0])
                    r[0] += 1
                    r[4] += amount
                    if s and (day, k, s) not in seen_day:
                        seen_day.add((day, k, s))
                        r[1] += 1
                        if (k, s) not in first_day:
                            first_day[(k, s)] = day
                            r[2] += 1
                        else:
                            r[3] += 1   # acted on an earlier day too
                        ever.setdefault(k, {})[s] = day
                if g in OURS:
                    hours.setdefault(day, [0] * 24)[ts % 86400 // 3600] += 1
                    src, kind = start(tx, h, g, self.sent)
                    kinds = starts.setdefault(day, {}).setdefault(src, {})
                    kinds[kind] = kinds.get(kind, 0) + 1
                rb = rabbit(tx, bots)
                if rb:
                    r = isle.setdefault(day, {"moves": 0, "rivals": 0, "lines": 0, "votes": 0, "agrs": 0, "wallets": 0,
                                              "new": 0, "cands": {}, "by": {}, "hours": [0] * 24})
                    r["moves"] += 1
                    r["agrs"] += amount
                    r["hours"][ts % 86400 // 3600] += 1
                    if rb[0] == "rival":
                        r["rivals"] += 1
                        r["by"][rb[1]] = r["by"].get(rb[1], 0) + 1
                    else:
                        r["lines" if rb[0] == "line" else "votes"] += 1
                        if rb[0] == "vote":
                            r["cands"][rb[1]] = r["cands"].get(rb[1], 0) + 1
                        if s and (day, "rabbit", s) not in seen_day:
                            seen_day.add((day, "rabbit", s))
                            r["wallets"] += 1
                            if s not in played:
                                played.add(s)
                                r["new"] += 1
                        if s:
                            isle_last[s] = day
                m = meal(tx) if g == "agorzilla" else None
                if m:
                    a = agz.setdefault(day, {"meals": 0, "snacks": 0, "votes": 0, "asks": 0, "agrs": 0, "wallets": 0,
                                             "new": 0, "hours": [0] * 24})
                    a["meals"] += 1
                    a["agrs"] += m[0]
                    a["votes"] += m[1]
                    a["asks"] += m[2]
                    a["hours"][ts % 86400 // 3600] += 1
                    if s not in ate:
                        a["new"] += 1
                    elif ts - ate[s] < MEAL_COOLDOWN:
                        a["snacks"] += 1
                    if ts - ate.get(s, -MEAL_COOLDOWN) >= MEAL_COOLDOWN:
                        ate[s] = ts
                    if (day, "meal", s) not in seen_day:
                        seen_day.add((day, "meal", s))
                        a["wallets"] += 1
        # distinct wallets over the last 7 and 30 days and over everything held, per group and for our two sites
        totals = {}
        if last is not None:
            for k, wallets in ever.items():
                totals[k] = {}
                for n in (7, 30):
                    since = time.strftime("%Y-%m-%d", time.gmtime(last - (n - 1) * 86400))
                    totals[k][str(n)] = sum(1 for d in wallets.values() if d >= since)
                totals[k]["all"] = len(wallets)
            if isle_last:
                totals["rabbit"] = {str(n): sum(1 for d in isle_last.values()
                                               if d >= time.strftime("%Y-%m-%d", time.gmtime(last - (n - 1) * 86400)))
                                    for n in (7, 30)}
                totals["rabbit"]["all"] = len(isle_last)
        recent = sorted(hours)[-31:]
        return {"days": dict(sorted(days.items())), "ours": dict(sorted(ours.items())), "totals": totals,
                "hours": {d: hours[d] for d in recent}, "agorzilla": dict(sorted(agz.items())),
                "starts": dict(sorted(starts.items())), "rabbit": dict(sorted(isle.items())), "since": first, "sent_since": round(self.since)}
