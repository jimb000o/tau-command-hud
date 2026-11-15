"""The wallets that walk on White Rabbit Key (tauhud.com/rabbit/, rabbit/walkers.js): every wallet that sent a real
transaction in the last day appears there as a small islander, and a click shows what the chain says about it.

Read from the public blocks only, nothing from the browser: for every sender key this keeps a few counts (first and
last transaction, how many, on which days, at which hours of the German day, how many different wallets it paid, test
AGRS moved) and what it did with our apps (Agorzilla's bowl and ballot boxes, Déjà's bowl, White Rabbit Key's council,
tills and ballot boxes, hearts) and with its own rules (the newest personal o5 rule it deployed in the chain the relay
holds, read for its parts: co-signer, only to, at most, not before a date, balance, freeze). Kept across testnet
restarts in WALKERS_PATH, like the hearts: the browser wallets keep their keys. Reading the same blocks twice changes
nothing: each wallet remembers the place of the last transaction it counted (block time, height, place in the block).

Never walkers: our own server's wallets (the island bot and its purses, cruise passengers, No Memo's purse, the hack
of the week, the showcase wallets; relay.py hands them over as `ours`). IDNI's genesis accounts walk, marked as such.
Wallets are keys, not people: nothing here knows who holds one.

The look (rabbit/walkers.js LOOK): without a choice, a wallet's islander is drawn from its key, always the same. A
wallet chooses its own by paying the hearts box (hearts.py BOX, no key behind it; no new address while IDNI #108 caps
the node's new addresses) LOOK + code, code 0..LOOKS-1 (figure, hair or hat, shirt colour); the newest such payment
counts. The hearts read only amounts below 1200, so the two never mix.

What it means (traits): a few plain readings of the counts, each with the number it rests on, for instance a night
owl (most of its transactions between 22:00 and 05:00 German time), Agorzilla's friend (fed the bowl), writes its own
rules, a guardian co-signs its payments. walkers.js says them in words and gives the islander the matching thing to
carry. Only readings, never a judgement of a person.

GET /walkers                the wallets active in the last WINDOW seconds, newest first: at most SHOW of everyone
                            else's and SHOW_IDNI of IDNI's, with look, traits and where on the island they like to be;
                            total / idni: how many are active in all
GET /walkers/<address>      one wallet's card: the counts, its rule's parts and whether a rule is in force for it now,
                            White Rabbit Key (isle.py) and No Memo (nomemo.py) when the relay hands them over, traits
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import time

from hearts import BOX, decode
from txsources import AGORZILLA, BOWL, BOXES, DEJA, GENESIS, RABBIT_BOXES, RABBIT_COUNCIL, RABBIT_TILLS

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:   # no time zone data: UTC+1 is near enough for "at night"
    BERLIN = dt.timezone(dt.timedelta(hours=1))

log = logging.getLogger("relay.walkers")

WINDOW = 86400
SHOW, SHOW_IDNI = 60, 6
LOOK, LOOKS = 1200, 384          # amount LOOK + code to BOX chooses a look; code = figure * 64 + hair * 8 + shirt
RECENT = 60                      # timestamps of the newest transactions kept per wallet (for "in the last day")
PEERS = 64                       # different wallets paid, counted up to this
SAVE_SECONDS = 60
HEX = re.compile(r"^[0-9a-f]{96}$")
RULE_MAX = 4000
NIGHT, MORNING = set(range(22, 24)) | set(range(0, 5)), set(range(5, 9))


def berlin_hour(ts: int) -> int:
    return dt.datetime.fromtimestamp(ts, BERLIN).hour


def rule_parts(text: str) -> list[str]:
    """What a personal rule is made of, read from its text (the wallet's blocks, assets/rulewords.js): co (a co-signer
    must sign: i18..i25), only (only to these addresses: i4), cap (at most per payment: i1), from (not before a time:
    i5), balance (reads the balance: i2), freeze (blocks everything)."""
    t = re.sub(r"\s+", "", text or "")
    if not t:
        return []
    out = []
    if re.search(r"i(1[89]|2[0-5])\[t\]", t):
        out.append("co")
    if "i4[t]" in t:
        out.append("only")
    if "i1[t]" in t:
        out.append("cap")
    if "i5[t]" in t:
        out.append("from")
    if "i2[t]" in t:
        out.append("balance")
    if not out and "o5[t]:bv[24]={#x000000}:bv[24]" in t and "?" not in t:
        out.append("freeze")
    return out


def blank() -> dict:
    return {"f": 0, "l": 0, "w": [0, 0, 0], "n": 0, "d": [], "h": [0] * 24, "p": [], "m": 0, "q": [],
            "meal": 0, "vote": 0, "ask": 0, "deja": 0, "line": 0, "ballot": 0, "heart": 0,
            "rules": 0, "rt": "", "look": None}


class Walkers:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("WALKERS_PATH", "/data/walkers.json")
        self.w: dict[str, dict] = {}
        self.dirty = False
        self.saved_at = 0.0
        try:
            with open(self.path) as f:
                st = json.load(f)
            for k, v in (st.get("w") or {}).items():
                if HEX.match(str(k)) and isinstance(v, dict):
                    r = blank()
                    r.update({x: v[x] for x in r if x in v})
                    self.w[str(k)] = r
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("cannot read %s: %r; starting a new walker record", self.path, exc)

    # ---------- reading the blocks ----------
    def add_blocks(self, blocks: list[dict], ours: set | frozenset = frozenset()) -> bool:
        changed = False
        for b in blocks:
            hd = b.get("header") or {}
            try:
                ts = int(hd.get("timestamp"))
                height = int(hd.get("block_number") or 0)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue
            day = ts // 86400
            for i, tx in enumerate(b.get("transactions") or []):
                if not isinstance(tx, dict):
                    continue
                s = str(tx.get("sender_pubkey") or "").lower()
                if not HEX.match(s) or s in ours:
                    continue
                r = self.w.get(s)
                if r is None:
                    r = self.w[s] = blank()
                if [ts, height, i] <= r["w"]:
                    continue   # counted already (a relay restart reads the kept blocks again)
                r["w"] = [ts, height, i]
                changed = True
                r["f"] = r["f"] or ts
                r["l"] = max(r["l"], ts)
                r["n"] += 1
                if day not in r["d"]:
                    r["d"] = (r["d"] + [day])[-400:]
                r["h"][berlin_hour(ts)] += 1
                r["q"] = (r["q"] + [ts])[-RECENT:]
                self._read(r, s, tx)
        if changed:
            self.dirty = True
        return changed

    def _read(self, r: dict, s: str, tx: dict):
        kind = tx.get("tx_type") or "user_tx"
        ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
        text = ops.get("0") if kind == "user_tx" else tx.get("rule_text") if kind == "rule_offer_accept" else None
        if isinstance(text, str) and "o5" in text and len(text) <= RULE_MAX:
            r["rules"] += 1
            r["rt"] = text.strip()
        fed = box = ask = deja = rabbit_line = ballot = False
        for op in ops.get("1") or []:
            if not (isinstance(op, (list, tuple)) and len(op) >= 3) or str(op[0]).lower() != s:
                continue
            to = str(op[1]).lower()
            try:
                amount = int(op[2])
            except (TypeError, ValueError):
                continue
            if amount < 1 or not HEX.match(to) or to == s:
                continue
            r["m"] += amount
            if to[:16] not in r["p"] and len(r["p"]) < PEERS:
                r["p"].append(to[:16])
            if to == BOWL:
                fed = True
            elif to in BOXES:
                box = True
            elif to == DEJA:
                deja = True
            elif to in AGORZILLA:
                ask = True
            elif to == RABBIT_COUNCIL or to in RABBIT_TILLS:
                rabbit_line = True
            elif to in RABBIT_BOXES:
                ballot = True
            elif to == BOX:
                if LOOK <= amount < LOOK + LOOKS:
                    r["look"] = amount - LOOK
                elif (d := decode(amount)) is not None and d[1]:
                    r["heart"] += 1
        r["meal"] += fed
        r["vote"] += fed and box
        r["ask"] += fed and ask
        r["deja"] += deja
        r["line"] += rabbit_line
        r["ballot"] += ballot

    # ---------- what it means ----------
    def traits(self, pk: str, r: dict, now: float, rabbit: dict | None = None, nomemo: dict | None = None) -> list[list]:
        """[[trait id, the number it rests on], ...], strongest first."""
        out: list[list] = []
        add = lambda k, n: out.append([k, int(n)])
        parts = rule_parts(r.get("rt", ""))
        n, hours = r["n"], r["h"]
        night, morning = sum(hours[h] for h in NIGHT), sum(hours[h] for h in MORNING)
        n24 = sum(1 for t in r["q"] if t >= now - WINDOW)
        rb = rabbit or {}
        chapters = len((nomemo or {}).get("claims") or {})
        apps = sum(1 for x in (r["meal"] + r["ask"], r["deja"], r["line"] + r["ballot"] + (rb.get("played") or 0), r["heart"], chapters) if x)
        if pk in GENESIS:
            add("idni", 0)
        if rb.get("won"):
            add("winner", rb["won"])
        if "co" in parts:
            add("guardian", 1)
        if chapters:
            add("hacker", chapters)
        if r["rules"]:
            add("lawmaker", r["rules"])
        if "from" in parts:
            add("vault", 1)
        if "only" in parts:
            add("picky", 1)
        if "cap" in parts:
            add("capped", 1)
        if "freeze" in parts:
            add("frozen", 1)
        if r["meal"]:
            add("feeder", r["meal"])
        if r["deja"]:
            add("catfriend", r["deja"])
        if r["line"] >= 3 or rb.get("played"):
            add("politician", max(r["line"], rb.get("moves") or 0))
        if r["vote"] + r["ballot"] >= 2:
            add("voter", r["vote"] + r["ballot"])
        if r["heart"] >= 2:
            add("hearts", r["heart"])
        if n >= 6 and night * 2 >= n:
            add("nightowl", round(100 * night / n))
        elif n >= 6 and morning * 2 >= n:
            add("earlybird", round(100 * morning / n))
        if apps >= 3:
            add("allrounder", apps)
        if len(r["p"]) >= 8:
            add("connector", len(r["p"]))
        if r["m"] >= 100000:
            add("bigspender", r["m"])
        if n24 >= 50:
            add("busy", n24)
        if len(r["d"]) >= 5:
            add("regular", len(r["d"]))
        age = (now - r["f"]) / 86400 if r["f"] else 0
        if age >= 14:
            add("veteran", int(age))
        elif r["f"] >= now - WINDOW:
            add("newcomer", 0)
        if not out:
            add("quiet", n)
        return out

    @staticmethod
    def home(traits: list[list]) -> str:
        for k, _ in traits:
            p = {"idni": "hall", "winner": "hall", "politician": "hall", "guardian": "book", "lawmaker": "book", "vault": "book",
                 "picky": "book", "capped": "book", "frozen": "book", "hacker": "radio", "feeder": "market", "catfriend": "cafe",
                 "nightowl": "bar", "newcomer": "pier", "connector": "market"}.get(k)
            if p:
                return p
        return ""

    def active(self, now: float | None = None, ours: set | frozenset = frozenset(), extra=None) -> dict:
        """GET /walkers. extra(pk) -> (rabbit, nomemo) for the traits that need them."""
        now = time.time() if now is None else now
        rows = [(pk, r) for pk, r in self.w.items() if r["l"] >= now - WINDOW and pk not in ours]
        rows.sort(key=lambda x: -x[1]["l"])
        idni = [x for x in rows if x[0] in GENESIS]
        rest = [x for x in rows if x[0] not in GENESIS]
        out = []
        for pk, r in rest[:SHOW] + idni[:SHOW_IDNI]:
            rb, nm = extra(pk) if extra else (None, None)
            tr = self.traits(pk, r, now, rb, nm)
            out.append({"a": pk, "look": r["look"], "idni": pk in GENESIS, "last": r["l"],
                        "n24": sum(1 for t in r["q"] if t >= now - WINDOW), "traits": [k for k, _ in tr[:4]], "home": self.home(tr)})
        return {"window": WINDOW, "total": len(rest), "idni": len(idni), "walkers": out, "look": {"box": BOX, "base": LOOK, "count": LOOKS},
                "generated_at": round(now)}

    def card(self, pk: str, now: float | None = None, rabbit: dict | None = None, nomemo: dict | None = None,
             in_force: bool | None = None) -> dict | None:
        now = time.time() if now is None else now
        r = self.w.get(pk)
        if r is None:
            return None
        hours = r["h"]
        return {"a": pk, "idni": pk in GENESIS, "look": r["look"], "first": r["f"], "last": r["l"], "txs": r["n"], "days": len(r["d"]),
                "n24": sum(1 for t in r["q"] if t >= now - WINDOW), "moved": r["m"], "peers": len(r["p"]), "peers_max": PEERS,
                "hours": hours, "meals": r["meal"], "votes": r["vote"], "asks": r["ask"], "deja": r["deja"],
                "rabbit": {"lines": r["line"], "ballots": r["ballot"], **({k: rabbit.get(k) for k in ("played", "won", "moves", "fav")} if rabbit else {})},
                "nomemo": {"chapters": len((nomemo or {}).get("claims") or {}), "nth": (nomemo or {}).get("nth")} if nomemo else None,
                "hearts": r["heart"], "rule": {"deploys": r["rules"], "parts": rule_parts(r["rt"]), "in_force": in_force},
                "traits": self.traits(pk, r, now, rabbit, nomemo)}

    def save(self, now: float | None = None, force: bool = False):
        now = time.time() if now is None else now
        if not self.dirty or (not force and now - self.saved_at < SAVE_SECONDS):
            return
        self.saved_at = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"w": self.w}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)
