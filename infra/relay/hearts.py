"""Hearts on tauhud.com (assets/hearts.js): a visitor marks a part of a page they love with ♥, and the mark is a real
test transaction from the test wallet in their browser to one box that has no key behind it (BOX).

A transaction has no memo, so its amount says which part and which way: LIKE + id gives the part a heart, UNLIKE + id
takes it back (ids 1..MAX_ID, the list is in assets/hearts.js). LEVEL × the sender's level on tauhud.com is added on top
(1 Beginner, 2 Intermediate, 3 Expert; 0 none chosen, and every heart sent before 14 Nov 2026): 401 is a beginner's heart
for part 1. A heart counts for the level of its wallet's newest mark on that part. For each wallet and part only the newest such
transaction counts (block time, then its place in the block), so a wallet holds at most one heart per part however
often it clicks; reading the same blocks again changes nothing. Kept across testnet restarts in HEARTS_PATH: the
browser wallets keep their keys, so their hearts stay.

GET /hearts
  box      the address the hearts go to
  parts    {id: wallets whose newest mark on that part is a heart}
  levels   {"new"|"mid"|"pro"|"none": {id: wallets}}, the same hearts split by level
  wallets  wallets with at least one heart now
  marks    heart and take-back transactions counted so far
It counts wallets, not people: whoever makes several wallets can give several hearts.
"""
from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger("relay.hearts")

BOX = "a43259757c7e5a26dae5dde9ce22ecafe2d7570c93e71ccf65756691d57e7a512e7fdfbfc78e9ce3bfd608b71e286a0b"
LIKE, UNLIKE, MAX_ID, LEVEL = 100, 200, 99, 300
LEVELS = ("none", "new", "mid", "pro")
SAVE_SECONDS = 60


def decode_level(amount) -> tuple[int, bool, int] | None:
    """(part id, heart on?, level 0..3) for an amount sent to the box, None for any other amount."""
    try:
        v = int(amount)
    except (TypeError, ValueError):
        return None
    lv = v // LEVEL
    a = v - LEVEL * lv
    if not 0 <= lv < len(LEVELS):
        return None
    if LIKE < a <= LIKE + MAX_ID:
        return a - LIKE, True, lv
    if UNLIKE < a <= UNLIKE + MAX_ID:
        return a - UNLIKE, False, lv
    return None


def decode(amount) -> tuple[int, bool] | None:
    """(part id, heart on?) for an amount sent to the box, None for any other amount."""
    d = decode_level(amount)
    return None if d is None else (d[0], d[1])


class Hearts:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("HEARTS_PATH", "/data/hearts.json")
        self.marks: dict[str, list] = {}   # "<sender>:<id>" -> [block time, place in the block, 1 heart / 0 taken back, level 0..3]
        self.count = 0                      # marks read (each transaction once per block it is in)
        self.dirty = False
        self.saved_at = 0.0
        try:
            with open(self.path) as f:
                st = json.load(f)
            self.marks = {str(k): [int(v[0]), int(v[1]), 1 if v[2] else 0, int(v[3]) if len(v) > 3 and 0 <= int(v[3]) < len(LEVELS) else 0]
                          for k, v in (st.get("marks") or {}).items() if isinstance(v, list) and len(v) in (3, 4)}
            self.count = int(st.get("count") or 0)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("cannot read %s: %r; starting a new heart record", self.path, exc)

    def add_blocks(self, blocks: list[dict]) -> bool:
        """Read the hearts in these blocks. True when a wallet's heart on a part changed."""
        changed = False
        for b in blocks:
            try:
                ts = int((b.get("header") or {}).get("timestamp"))
            except (TypeError, ValueError, AttributeError):
                continue
            for i, tx in enumerate(b.get("transactions") or []):
                if not isinstance(tx, dict) or tx.get("tx_type", "user_tx") != "user_tx":
                    continue
                ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
                for op in ops.get("1") or []:
                    if not (isinstance(op, (list, tuple)) and len(op) >= 3) or str(op[1]).lower() != BOX:
                        continue
                    d = decode_level(op[2])
                    if d is None:
                        continue
                    key = f"{str(op[0]).lower()}:{d[0]}"
                    new, old = [ts, i, 1 if d[1] else 0, d[2]], self.marks.get(key)
                    if old is not None and (old[0], old[1]) > (ts, i):
                        continue   # an older mark read late: the newer one stands
                    if old == new:
                        continue   # the same block read again
                    self.marks[key] = new
                    self.count += 1
                    self.dirty = changed = True
        return changed

    def summary(self) -> dict:
        parts: dict[str, int] = {}
        levels: dict[str, dict[str, int]] = {name: {} for name in LEVELS}
        wallets = set()
        for key, m in self.marks.items():
            if not m[2]:
                continue
            sender, pid = key.rsplit(":", 1)
            parts[pid] = parts.get(pid, 0) + 1
            per = levels[LEVELS[m[3] if len(m) > 3 else 0]]
            per[pid] = per.get(pid, 0) + 1
            wallets.add(sender)
        order = lambda d: dict(sorted(d.items(), key=lambda kv: int(kv[0])))
        return {"box": BOX, "parts": order(parts), "levels": {k: order(v) for k, v in levels.items()}, "wallets": len(wallets),
                "marks": self.count}

    def save(self, now: float | None = None, force: bool = False):
        now = time.time() if now is None else now
        if not self.dirty or (not force and now - self.saved_at < SAVE_SECONDS):
            return
        self.saved_at = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"marks": self.marks, "count": self.count}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)
