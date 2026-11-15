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

The islander, part by part (rabbit/islander.js, the same lists): seventeen parts (build, skin, hair or hat, hair colour,
clothes, clothes colour, trousers, walk, face shape, eyes, brows, nose, mouth, beard, marks, glasses and jewellery, an
earned piece). Each part comes from the wallet's key until the wallet chooses: PART + part * STRIDE + choice to the
hearts box, one payment per part, any number of them in one transaction; the newest per part counts. An older look
payment sets skin, hair, hair colour and shirt colour. The earned piece is shown only while the wallet has the trait
it stands for (EARN). The first wallet whose chosen parts make a face (FACE) records it: `faces` keeps the first one in
block order, so anyone can check it against the blocks. Wallets that never chose wear their key's face, unrecorded.

The chain's own state for the island: the newest block read (time, height) and the last restart seen (a block newer
than the newest one read but more than five blocks lower), so the islanders can sit down while the chain pauses.
A payment the node refused because the wallet's own rule said no (relay.py held_by_rule) is noted per wallet (`held`).

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
PART, STRIDE = 1600, 32          # amount PART + part * STRIDE + choice to BOX chooses one part of the islander
NS = (5, 10, 16, 10, 8, 16, 8, 5, 6, 10, 8, 8, 8, 8, 8, 10, 10)   # choices per part (rabbit/islander.js SLOTS)
FACE = (1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15)
EARN = (None, "lawmaker", "hacker", "feeder", "veteran", "guardian", "winner", "voter", "hearts", "catfriend")
OLD_SKIN = (1, 2, 4, 5, 7, 9)
HELD_SHOW = 3600                 # a refusal by the wallet's own rule shows on the island for an hour
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
            "rules": 0, "rt": "", "look": None, "pt": [None] * len(NS), "held": 0}


def key_part(pk: str, i: int) -> int:
    """Part i of a wallet that did not choose it: from byte i of its key (rabbit/islander.js parts())."""
    if i == 16:
        return 0
    b = int(pk[2 * i:2 * i + 2], 16)
    if i >= 13:
        return 0 if b < 180 else 1 + b % (NS[i] - 1)
    return b % NS[i]


def parts_of(pk: str, chosen: list) -> list[int]:
    return [c if isinstance(c, int) and 0 <= c < NS[i] else key_part(pk, i) for i, c in enumerate((list(chosen or []) + [None] * len(NS))[:len(NS)])]


def face_sig(p: list[int]) -> str:
    return "-".join(str(p[i]) for i in FACE)


def look_parts(code: int) -> dict[int, int]:
    """An older look code as parts: skin, hair or hat, hair colour, shirt colour."""
    return {1: OLD_SKIN[code // 64], 2: code // 8 % 8, 3: (code * 7 + 3) % 6, 5: code % 8}


class Walkers:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("WALKERS_PATH", "/data/walkers.json")
        self.w: dict[str, dict] = {}
        self.since = 0          # when this record began: a wallet first seen in its first day may be much older
        self.faces: dict[str, list] = {}   # face -> [first wallet that chose it, block time, height, place in the block]
        self.tip = [0, 0]                   # the newest block read: time, height
        self.restart = 0                    # block time of the first block after the last restart seen
        self.dirty = False
        self.saved_at = 0.0
        try:
            with open(self.path) as f:
                st = json.load(f)
            self.since = int(st.get("since") or 0)
            self.faces = {str(k): list(v) for k, v in (st.get("faces") or {}).items() if isinstance(v, list) and len(v) >= 2}
            self.tip = [int(x) for x in (st.get("tip") or [0, 0])][:2]
            self.restart = int(st.get("restart") or 0)
            for k, v in (st.get("w") or {}).items():
                if HEX.match(str(k)) and isinstance(v, dict):
                    r = blank()
                    r.update({x: v[x] for x in r if x in v})
                    r["pt"] = (list(r["pt"] or []) + [None] * len(NS))[:len(NS)]
                    self.w[str(k)] = r
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("cannot read %s: %r; starting a new walker record", self.path, exc)

    # ---------- reading the blocks ----------
    def add_blocks(self, blocks: list[dict], ours: set | frozenset = frozenset()) -> bool:
        changed = False
        if not self.since:
            self.since = int(time.time())
            self.dirty = True
        for b in blocks:
            hd = b.get("header") or {}
            try:
                ts = int(hd.get("timestamp"))
                height = int(hd.get("block_number") or 0)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue
            if ts > self.tip[0]:
                if height < self.tip[1] - 5:
                    self.restart = ts   # newer, but far lower: the chain started over
                self.tip = [ts, height]
                changed = True
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
        chose = False
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
                    for i, c in look_parts(amount - LOOK).items():
                        r["pt"][i] = c
                    chose = True
                elif PART <= amount < PART + len(NS) * STRIDE:
                    i, c = divmod(amount - PART, STRIDE)
                    if c < NS[i]:
                        r["pt"][i] = c
                        chose = True
                elif (d := decode(amount)) is not None and d[1]:
                    r["heart"] += 1
        r["meal"] += fed
        r["vote"] += fed and box
        r["ask"] += fed and ask
        r["deja"] += deja
        r["line"] += rabbit_line
        r["ballot"] += ballot
        if chose:
            sig = face_sig(parts_of(s, r["pt"]))
            if sig not in self.faces or r["w"] < self.faces[sig][1:4]:
                self.faces[sig] = [s, *r["w"]]

    def held(self, pk: str, ts: float | None = None):
        """The node refused one of this wallet's payments because its own rule said no."""
        r = self.w.get(str(pk).lower())
        if r is not None:
            r["held"] = int(ts or time.time())
            self.dirty = True

    def parts(self, pk: str, r: dict, traits: list[list]) -> list[int]:
        """The islander as shown: chosen parts, the key's for the rest; the earned piece only with its trait."""
        p = parts_of(pk, r["pt"])
        need = EARN[p[16]] if p[16] < len(EARN) else None
        if need and need not in {k for k, _ in traits}:
            p[16] = 0
        return p

    def face(self, sig: str) -> dict:
        """GET /walkers/face/<face>: the first wallet that chose this face, if any."""
        f = self.faces.get(sig)
        return {"face": sig, "first": f[0] if f else None, "at": f[1] if f else None}

    def first_wearer(self, pk: str, r: dict) -> bool:
        if not any(c is not None for c in r["pt"]):
            return False
        f = self.faces.get(face_sig(parts_of(pk, r["pt"])))
        return bool(f and f[0] == pk)

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
        elif r["f"] >= now - WINDOW and r["f"] >= self.since + WINDOW:
            add("newcomer", 0)   # only once the record is a day old: before that, "first seen" is only "first read here"
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
            row = {"a": pk, "look": r["look"], "idni": pk in GENESIS, "last": r["l"],
                   "n24": sum(1 for t in r["q"] if t >= now - WINDOW), "traits": [k for k, _ in tr[:4]], "home": self.home(tr),
                   "pt": self.parts(pk, r, tr)}
            if self.first_wearer(pk, r):
                row["first"] = True
            if r.get("held", 0) >= now - HELD_SHOW:
                row["held"] = r["held"]
            out.append(row)
        return {"window": WINDOW, "total": len(rest), "idni": len(idni), "walkers": out,
                "look": {"box": BOX, "base": LOOK, "count": LOOKS, "part": PART, "stride": STRIDE, "n": list(NS)},
                "chain": {"tip": self.tip[0], "height": self.tip[1], "restart": self.restart}, "generated_at": round(now)}

    def card(self, pk: str, now: float | None = None, rabbit: dict | None = None, nomemo: dict | None = None,
             in_force: bool | None = None) -> dict | None:
        now = time.time() if now is None else now
        r = self.w.get(pk)
        if r is None:
            return None
        hours = r["h"]
        tr = self.traits(pk, r, now, rabbit, nomemo)
        have = {k for k, _ in tr}
        return {"a": pk, "idni": pk in GENESIS, "look": r["look"], "first": r["f"], "last": r["l"], "txs": r["n"], "days": len(r["d"]),
                "n24": sum(1 for t in r["q"] if t >= now - WINDOW), "moved": r["m"], "peers": len(r["p"]), "peers_max": PEERS,
                "hours": hours, "meals": r["meal"], "votes": r["vote"], "asks": r["ask"], "deja": r["deja"],
                "rabbit": {"lines": r["line"], "ballots": r["ballot"], **({k: rabbit.get(k) for k in ("played", "won", "moves", "fav")} if rabbit else {})},
                "nomemo": {"chapters": len((nomemo or {}).get("claims") or {}), "nth": (nomemo or {}).get("nth")} if nomemo else None,
                "hearts": r["heart"], "rule": {"deploys": r["rules"], "parts": rule_parts(r["rt"]), "in_force": in_force},
                "traits": tr, "pt": self.parts(pk, r, tr), "chosen": r["pt"],
                "earned": [i for i, k in enumerate(EARN) if k and k in have],
                "face": {**self.face(face_sig(parts_of(pk, r["pt"]))), "mine": self.first_wearer(pk, r)}}

    def save(self, now: float | None = None, force: bool = False):
        now = time.time() if now is None else now
        if not self.dirty or (not force and now - self.saved_at < SAVE_SECONDS):
            return
        self.saved_at = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"w": self.w, "since": self.since, "faces": self.faces, "tip": self.tip, "restart": self.restart}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)
