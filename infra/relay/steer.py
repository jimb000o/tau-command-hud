"""Your own islander on White Rabbit Key (tauhud.com/rabbit/, rabbit/walkers.js): the wallet in a browser can walk its
walker where its visitor clicks, and every page on the island sees it walk there, the same way.

The relay only passes on where to: the clicking page sends the point its walker starts from and the point it goes to
(world units of the island painting), and the relay pushes that to every page on the island (the "isle join" sockets),
with how long ago it was asked. Every page then works out the same way along the island's paths (rabbit/paths.js, the
same graph and the same rules everywhere, no randomness), so all of them show the walker in the same place.

Only the wallet itself can steer its walker: a page says hello once a day with a BLS signature of
`tauhud.com walker <wallet> <day>` made by the wallet's key in the browser (BLS over sha256, as the node checks a
transaction), or it needs no hello at all when that wallet signed a transaction through this relay from the same
address lately (isle.py `signed`, the rule the players' board uses). A checked hello is remembered for the socket and,
for the day, for the signature, so a page pays for one check a day; checks run one at a time in a thread, a few per
address a minute.

Kept in memory only, never on disk: for each wallet its last walk for HOLD seconds (so a page opened a moment later
shows it where it stands), then forgotten. A walk is a point on a made-up island, nothing about a person.

WebSocket commands (replies and pushes have command "walker"):
  walker hello <wallet> <day> <signature>              this socket may steer <wallet> (day = UTC YYYY-MM-DD)
  walker go <wallet> <fx> <fy> <tx> <ty> [place]      walk from (fx, fy) to (tx, ty); place: the place it opens there
GET /walkers carries the walks of the last HOLD seconds as "go" (walkers.py, relay.py).
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time

WALLET = re.compile(r"^[0-9a-f]{96}$")
SIG = re.compile(r"^[0-9a-f]{192}$")
PLACE = re.compile(r"^[a-z]{2,12}$")
HOLD = 30 * 60            # a walk is shown this long after it was asked (then the walker wanders again)
EVERY = 1.0               # seconds between two walks of one wallet
CHECKS_PER_MIN = 6        # signature checks one address may ask for a minute
KEEP = 2000               # wallets remembered at most
BOX = (-300.0, 0.0, 1900.0, 900.0)   # the world (x0, y0, x1, y1): a point outside is refused


def message(wallet: str, day: str) -> bytes:
    return f"tauhud.com walker {wallet} {day}".encode()


def verify(wallet: str, day: str, sig: str) -> bool:
    try:
        from py_ecc.bls import G2Basic
        return bool(G2Basic.Verify(bytes.fromhex(wallet), hashlib.sha256(message(wallet, day)).digest(), bytes.fromhex(sig)))
    except Exception:
        return False


def utc_day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


class Steer:
    def __init__(self, clock=time.time, check=verify):
        self.clock, self.check = clock, check
        self.walks: dict[str, dict] = {}          # wallet -> {f, t, p, at}
        self.ok: dict[object, set] = {}           # socket -> wallets it may steer
        self.good: dict[tuple, float] = {}        # (wallet, day, sig) -> when checked
        self.asked: dict[str, list] = {}          # address -> times of checks asked
        self.last: dict[str, float] = {}          # wallet -> last walk
        self.lock = asyncio.Lock()

    def forget(self, ws):
        self.ok.pop(ws, None)

    async def hello(self, ws, ip: str, wallet: str, day: str, sig: str) -> tuple[bool, dict | str]:
        wallet, sig = wallet.lower(), sig.lower()
        if not WALLET.match(wallet) or not SIG.match(sig):
            return False, "Usage: walker hello <wallet> <day> <signature>"
        now = self.clock()
        if day not in (utc_day(now), utc_day(now - 3600), utc_day(now + 3600)):
            return False, "the day is not today (UTC)"
        key = (wallet, day, sig)
        if key not in self.good:
            ts = [t for t in self.asked.get(ip, []) if now - t < 60]
            if len(ts) >= CHECKS_PER_MIN:
                return False, "too many checks from your address; wait a minute"
            ts.append(now)
            self.asked[ip] = ts
            if len(self.asked) > 20000:
                self.asked.clear()
            async with self.lock:   # one check at a time: a pairing in pure Python takes about a second
                ok = await asyncio.to_thread(self.check, wallet, day, sig)
            if not ok:
                return False, "the signature is not this wallet's"
            if len(self.good) > 20000:
                self.good.clear()
            self.good[key] = now
        self.ok.setdefault(ws, set()).add(wallet)
        return True, {"wallet": wallet, "ok": True}

    def go(self, ws, ip: str, args: list[str], signed=None) -> tuple[bool, dict | str]:
        if len(args) not in (5, 6):
            return False, "Usage: walker go <wallet> <fx> <fy> <tx> <ty> [place]"
        wallet = args[0].lower()
        if not WALLET.match(wallet):
            return False, "not a wallet"
        now = self.clock()
        if wallet not in self.ok.get(ws, set()) and not (signed and signed(ip, wallet, now)):
            return False, "say hello first: walker hello <wallet> <day> <signature>"
        try:
            fx, fy, tx, ty = (round(float(a), 1) for a in args[1:5])
        except ValueError:
            return False, "the points are numbers"
        x0, y0, x1, y1 = BOX
        if not all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in ((fx, fy), (tx, ty))):
            return False, "a point off the island"
        place = args[5].lower() if len(args) == 6 else "-"
        if place != "-" and not PLACE.match(place):
            return False, "not a place"
        if now - self.last.get(wallet, 0) < EVERY:
            return False, "one walk a second"
        self.last[wallet] = now
        if len(self.walks) >= KEEP:
            self.prune(now)
            if len(self.walks) >= KEEP:
                for k in sorted(self.walks, key=lambda k: self.walks[k]["at"])[:len(self.walks) - KEEP + 1]:
                    del self.walks[k]
        self.walks[wallet] = {"f": [fx, fy], "t": [tx, ty], "p": place, "at": now}
        if len(self.last) > 20000:
            self.last.clear()
        return True, self.one(wallet, now)

    def one(self, wallet: str, now: float) -> dict:
        w = self.walks[wallet]
        return {"a": wallet, "f": w["f"], "t": w["t"], "p": w["p"], "age": int((now - w["at"]) * 1000)}

    def prune(self, now: float):
        for k in [k for k, w in self.walks.items() if now - w["at"] > HOLD]:
            del self.walks[k]

    def recent(self, wallets=None) -> list[dict]:
        """The walks of the last HOLD seconds (for GET /walkers), only of the wallets given if any."""
        now = self.clock()
        self.prune(now)
        return [self.one(k, now) for k in self.walks if wallets is None or k in wallets]
