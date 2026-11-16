"""Active wallets over time, across chain restarts (tauhud.com/stats/, "Active wallets").

A wallet is active on a day when it sent at least one transaction that a block sealed that day (UTC). It counts as
active over the last N days when it was active on any of them. The relay only holds the current chain, and a testnet
restart wipes it, so this module writes down, for every UTC day, which wallets were active then. A restart does not
touch what is written: the new chain's blocks only add wallets to their own days. Reading the same blocks twice (relay
restart, full refetch, reorg) changes nothing, because a day is a set.

Every wallet gets one tag, the first that fits in TAGS order, from everything it ever did:

  idni       one of the accounts the testnet started with (txsources.GENESIS), set up by IDNI
  bot        our own server wallets: the White Rabbit Key island bot's campaign wallets and the island's purses
  cruise     a simulated cruise passenger of White Rabbit Key (the relay fills `cruise` with their keys once ships run)
  rabbit     a visitor who played White Rabbit Key on the chain (paid the island council, a till or a ballot box)
  agorzilla  a wallet that fed Agorzilla or Deja (paid one of Agorzilla's addresses)
  tauhud     a wallet that sent through this relay's wallet door from a Tau HUD page
  other      everything else: other people's wallets, scripts and tools

A wallet that used several of our apps counts once, under the first. Wallets are keys, not people.

GET /wallets/active
  tags       the tag names, in the order of every count list below
  windows    [1, 7, 30, 90]
  days       {"YYYY-MM-DD": {"1": [n per tag], "7": [...], "30": [...], "90": [...]}} wallets active in the N days up to
             and including that day, every day from the first recorded one to today
  new        {"YYYY-MM-DD": [n per tag]} wallets active for the first time that day (since recording began)
  totals     [n per tag] different wallets ever recorded
  since      first recorded day: a window reaching back before it only counts what was recorded
  players    White Rabbit Key players over time (tauhud.com/stats/, "Players"): wallets tagged rabbit, each counted from
             the first day it paid the island council, a till or a ballot box (a campaign's first step since the pick is
             signed). {"since": day, "days": {"YYYY-MM-DD": [players so far, new that day]}}; empty days included

GET /wallets/tags
  tags       {pubkey: tag} for the wallets whose tag comes from the public blocks or from our own server wallets:
             idni, bot, cruise, rabbit, agorzilla (tauhud.com's chain core marks their transactions, assets/origins.js).
  via        {tx hash: page} the newest transactions sent from one of our games with a page of its own (txsources
             GAME_VIA: "nomemo"). A wallet's tag says what it did first; this says which game a transaction came from.
             "tauhud" stays out of tags: it comes from the relay's own note of what it sent.
  apps       {pubkey: {"b": app, "d": day, "u": [apps]}} which of our apps a visitor's wallet came from, so a page can say
             that a wallet started in Tau HUD. Only wallets that are not IDNI's and not our own server's.
             b = the app its first transaction we know of came from, d = that day (UTC). Written only when the wallet was
             new to a record that already ran on an earlier day, so a wallet from before the record began never gets one.
             u = every app it has sent through since (and, for wallets recorded before apps were kept, the app its tag names),
             the one it was active in on the most days first: u[0] is what the wallet mostly does with our apps.
             n = {app: days} the days it sent through each app, counted since 16 Nov 2026.
             Apps: tauhud (sent through this relay's wallet door from a tauhud.com page), nomemo (the same, from No Memo),
             rabbit (a White Rabbit Key move, line or ballot, or anything sent from its pages, such as a rule proposed to an islander), agorzilla (paid one of Agorzilla's addresses, or sent from
             agorzilla.com), deja (fed Déjà, Agorzilla's café cat). A wallet is a key, not a person.
Only counts leave the relay, and the apps above. The file keeps sender keys per day; they are public in the blocks anyway.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import time

from txsources import AGORZILLA, DEJA, GAME_VIA, GENESIS, group, rabbit

log = logging.getLogger("relay.walletdays")

TAGS = ("idni", "bot", "cruise", "rabbit", "agorzilla", "tauhud", "other")
RANK = {t: i for i, t in enumerate(TAGS)}
PUBLIC = ("idni", "bot", "cruise", "rabbit", "agorzilla")   # tags anyone could read off the blocks, or our own wallets
WINDOWS = (1, 7, 30, 90)
KEEP_DAYS = 400
SAVE_SECONDS = 60
APPS = ("tauhud", "nomemo", "rabbit", "agorzilla", "deja")   # our apps a visitor's wallet can come from (GET /wallets/tags "apps")
RABBIT_VIA = ("rabbit", "islander")   # wallet-door pages that are White Rabbit Key's (rabbit/game.js, offers.js, studio.js)
NOT_VISITOR = ("idni", "bot", "cruise")   # IDNI's genesis wallets and our own server's: never a visitor's app


def app_of(tx: dict, tx_hash: str, sent: dict) -> str | None:
    """Which of our apps this transaction came from, read from the transaction itself or from the relay's note of what
    it sent; None when nothing says so."""
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    to = {str(op[1]).lower() for op in ops.get("1") or [] if isinstance(op, (list, tuple)) and len(op) >= 2}
    if DEJA in to:
        return "deja"
    if to & AGORZILLA:
        return "agorzilla"
    if rabbit(tx, {}):
        return "rabbit"
    note = sent.get(tx_hash)
    if note is None:
        return None
    site, _, via = note.partition("|")
    if site:
        return site if site in APPS else None
    if via in GAME_VIA:
        return "nomemo"
    # White Rabbit Key's own pages: a move or ballot (game.js "via rabbit"), a rule proposed to an islander or the
    # islander studio (offers.js, studio.js "via islander")
    return "rabbit" if via.split("/")[0] in RABBIT_VIA else "tauhud"


def day_of(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def ordinal(day: str) -> int:
    return datetime.date.fromisoformat(day).toordinal()


class WalletDays:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("WALLETDAYS_PATH", "/data/walletdays.json")
        self.keys: list[str] = []          # sender keys, in the order first seen
        self.index: dict[str, int] = {}
        self.tag: list[str] = []           # tag per key
        self.days: dict[str, set[int]] = {}
        self.play: dict[int, str] = {}     # key -> first day it made a White Rabbit Key transaction
        self.born: dict[int, tuple[str, str]] = {}   # key -> (app, day) its first transaction we know of came from
        self.apps: dict[int, list[str]] = {}         # key -> our apps it sent through, first used first
        self.appdays: dict[int, dict[str, set[str]]] = {}   # key -> app -> days it sent through it
        self.bots: set[str] = set()        # filled by the relay: the island bot's and purses' keys
        self.cruise: set[str] = set()      # filled by the relay once cruise ships run: their passengers' keys
        self.dirty = False
        self.saved_at = 0.0
        try:
            with open(self.path) as f:
                st = json.load(f)
            keys, tags = st.get("keys") or [], st.get("tag") or []
            for k, t in zip(keys, tags):
                self.index[str(k)] = len(self.keys)
                self.keys.append(str(k))
                self.tag.append(t if t in RANK else "other")
            n = len(self.keys)
            self.days = {str(d): {int(i) for i in v if isinstance(i, int) and 0 <= i < n}
                         for d, v in (st.get("days") or {}).items()}
            self.play = {int(i): str(d) for i, d in (st.get("play") or {}).items() if str(i).isdigit() and int(i) < n}
            self.born = {int(i): (str(v[0]), str(v[1])) for i, v in (st.get("born") or {}).items()
                         if str(i).isdigit() and int(i) < n and isinstance(v, list) and len(v) == 2 and v[0] in APPS}
            self.apps = {int(i): [a for a in v if a in APPS] for i, v in (st.get("apps") or {}).items()
                         if str(i).isdigit() and int(i) < n and isinstance(v, list)}
            self.appdays = {int(i): {a: {str(d) for d in ds if isinstance(d, str)} for a, ds in v.items() if a in APPS and isinstance(ds, list)}
                            for i, v in (st.get("appdays") or {}).items() if str(i).isdigit() and int(i) < n and isinstance(v, dict)}
            if "apps" not in st:   # a record from before apps were kept: the app its tag names, nothing more
                self.apps = {i: [t] for i, t in enumerate(self.tag) if t in ("rabbit", "agorzilla", "tauhud")}
                self.dirty = bool(self.apps)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("cannot read %s: %r; starting a new wallet record", self.path, exc)

    def classify(self, tx: dict, tx_hash: str, sent: dict) -> str:
        s = str(tx.get("sender_pubkey") or "").lower()
        if s in GENESIS:
            return "idni"
        if s in self.bots:
            return "bot"
        if s in self.cruise:
            return "cruise"
        if rabbit(tx, {}):
            return "rabbit"
        g = group(tx, tx_hash, sent)
        g = "tauhud" if g == "nomemo" else g   # No Memo is a page of tauhud.com: its players count as Tau HUD's wallets
        return g if g in ("rabbit", "agorzilla", "tauhud") else "other"

    def add_blocks(self, blocks: list[dict], sent: dict | None = None) -> bool:
        """Write down the senders of these blocks on their days. True when something new was learnt."""
        sent = sent or {}
        changed = False
        for b in blocks:
            try:
                ts = int((b.get("header") or {}).get("timestamp"))
            except (TypeError, ValueError):
                continue
            if ts <= 0:   # the genesis block carries time 0
                continue
            day = day_of(ts)
            ids = b.get("tx_ids") or []
            for i, tx in enumerate(b.get("transactions") or []):
                if not isinstance(tx, dict):
                    continue
                s = str(tx.get("sender_pubkey") or "").lower()
                if not s:
                    continue
                h = str(ids[i] if i < len(ids) else tx.get("tx_hash") or "").lower()
                t = self.classify(tx, h, sent)
                app = None if t in NOT_VISITOR else app_of(tx, h, sent)
                k = self.index.get(s)
                if k is None:
                    k = self.index[s] = len(self.keys)
                    self.keys.append(s)
                    self.tag.append(t)
                    changed = True
                    if app and self.days and min(self.days) < day:   # new to a record that already ran before this day
                        self.born[k] = (app, day)
                elif RANK[t] < RANK[self.tag[k]]:
                    self.tag[k] = t
                    changed = True
                if app and app not in self.apps.get(k, ()):
                    self.apps.setdefault(k, []).append(app)
                    changed = True
                if app and day not in self.appdays.setdefault(k, {}).setdefault(app, set()):
                    self.appdays[k][app].add(day)
                    changed = True
                if rabbit(tx, {}) and (k not in self.play or day < self.play[k]):
                    self.play[k] = day
                    changed = True
                got = self.days.setdefault(day, set())
                if k not in got:
                    got.add(k)
                    changed = True
        if changed:
            self.dirty = True
        return changed

    def retag(self):
        """Bot and passenger keys can become known after their transactions were written down."""
        for s in self.bots | self.cruise:
            k = self.index.get(s)
            t = "bot" if s in self.bots else "cruise"
            if k is not None and RANK[t] < RANK[self.tag[k]]:
                self.tag[k] = t
                self.dirty = True

    def known(self) -> dict:
        """{pubkey: tag} for the public tags (PUBLIC), for GET /wallets/tags."""
        return {k: t for k, t in zip(self.keys, self.tag) if t in PUBLIC}

    def apps_of(self, pk: str) -> list[str]:
        """Our apps this visitor's wallet sent through (its first app included); [] for our own and IDNI's wallets."""
        k = self.index.get(str(pk or "").lower())
        if k is None or self.tag[k] in NOT_VISITOR:
            return []
        used = list(self.apps.get(k, []))
        if k in self.born and self.born[k][0] not in used:
            used.insert(0, self.born[k][0])
        return used

    def app_list(self) -> dict:
        """{pubkey: {"b": app, "d": day, "u": [apps], "n": {app: days}}} for visitors' wallets we know an app of, for
        GET /wallets/tags; u has the app it was active in on the most days first."""
        out = {}
        for k in sorted(set(self.born) | set(self.apps)):
            if self.tag[k] in NOT_VISITOR:
                continue
            e, used = {}, list(self.apps.get(k, []))
            if k in self.born:
                e["b"], e["d"] = self.born[k]
                if e["b"] not in used:
                    used.insert(0, e["b"])
            days = {a: len(ds) for a, ds in self.appdays.get(k, {}).items() if ds}
            used.sort(key=lambda a: -days.get(a, 0))   # stable: among equal days, the one used first
            if used:
                e["u"] = used
            if days:
                e["n"] = days
            if e:
                out[self.keys[k]] = e
        return out

    def save(self, now: float | None = None, force: bool = False):
        now = time.time() if now is None else now
        if not self.dirty or (not force and now - self.saved_at < SAVE_SECONDS):
            return
        cut = day_of(now - KEEP_DAYS * 86400)
        for d in [d for d in self.days if d < cut]:
            del self.days[d]
        self.saved_at = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"keys": self.keys, "tag": self.tag,
                           "days": {d: sorted(v) for d, v in sorted(self.days.items())},
                           "play": {str(k): d for k, d in self.play.items()},
                           "born": {str(k): list(v) for k, v in self.born.items()},
                           "apps": {str(k): v for k, v in self.apps.items()},
                           "appdays": {str(k): {a: sorted(ds) for a, ds in v.items()} for k, v in self.appdays.items()}}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)

    def history(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        if not self.days:
            return {"tags": list(TAGS), "windows": list(WINDOWS), "days": {}, "new": {}, "totals": [0] * len(TAGS), "since": None,
                    "players": {"since": None, "days": {}}}
        first, last = min(self.days), max(max(self.days), day_of(now))
        o0, o1 = ordinal(first), ordinal(last)
        n, nt = o1 - o0 + 1, len(TAGS)
        active: dict[int, list[int]] = {}      # key -> sorted day offsets
        for d, ks in self.days.items():
            off = ordinal(d) - o0
            for k in ks:
                active.setdefault(k, []).append(off)
        diff = {w: [[0] * nt for _ in range(n + 1)] for w in WINDOWS}
        new = [[0] * nt for _ in range(n)]
        totals = [0] * nt
        for k, offs in active.items():
            offs.sort()
            ti = RANK[self.tag[k]]
            totals[ti] += 1
            new[offs[0]][ti] += 1
            for w in WINDOWS:
                lo = hi = None             # merge the days each one covers into runs
                for o in offs:
                    if hi is not None and o <= hi + 1:
                        hi = o + w - 1
                        continue
                    if lo is not None:
                        diff[w][lo][ti] += 1
                        diff[w][min(hi + 1, n)][ti] -= 1
                    lo, hi = o, o + w - 1
                diff[w][lo][ti] += 1
                diff[w][min(hi + 1, n)][ti] -= 1
        days, run = {}, {w: [0] * nt for w in WINDOWS}
        for i in range(n):
            d = datetime.date.fromordinal(o0 + i).isoformat()
            row = {}
            for w in WINDOWS:
                run[w] = [a + b for a, b in zip(run[w], diff[w][i])]
                row[str(w)] = list(run[w])
            days[d] = row
        return {"tags": list(TAGS), "windows": list(WINDOWS), "days": days,
                "new": {datetime.date.fromordinal(o0 + i).isoformat(): new[i] for i in range(n) if any(new[i])},
                "totals": totals, "since": first, "players": self.players(active, o0, n)}

    def players(self, active: dict, o0: int, n: int) -> dict:
        """White Rabbit Key players so far, per day: rabbit-tagged wallets from their first move on the island. A wallet
        written down before first days were kept (older file) counts from its first active day; a player from before the
        first recorded day counts on that day, so the total never shrinks."""
        new = [0] * n
        for k, t in enumerate(self.tag):   # every player ever, also one whose days are past KEEP_DAYS
            if t != "rabbit":
                continue
            d = self.play.get(k)
            off = ordinal(d) - o0 if d else (active[k][0] if k in active else 0)
            new[min(max(off, 0), n - 1)] += 1
        firsts = [i for i in range(n) if new[i]]
        if not firsts:
            return {"since": None, "days": {}}
        days, run = {}, 0
        for i in range(firsts[0], n):
            run += new[i]
            days[datetime.date.fromordinal(o0 + i).isoformat()] = [run, new[i]]
        return {"since": datetime.date.fromordinal(o0 + firsts[0]).isoformat(), "days": days}
