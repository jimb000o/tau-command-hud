"""Hearts on tauhud.com (assets/hearts.js): a visitor marks a part of a page they love with ♥, and the mark is a real
test transaction from the test wallet in their browser to one box that has no key behind it (BOX).

A transaction has no memo, so its amount says which part and which way: LIKE + id gives the part a heart, UNLIKE + id
takes it back (ids 1..MAX_ID, the list is in assets/hearts.js). For each wallet and part only the newest such
transaction counts (block time, then its place in the block), so a wallet holds at most one heart per part however
often it clicks; reading the same blocks again changes nothing. Kept across testnet restarts in HEARTS_PATH: the
browser wallets keep their keys, so their hearts stay.

GET /hearts
  box      the address the hearts go to
  parts    {id: wallets whose newest mark on that part is a heart}
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
LIKE, UNLIKE, MAX_ID = 100, 200, 99
SAVE_SECONDS = 60


def decode(amount) -> tuple[int, bool] | None:
    """(part id, heart on?) for an amount sent to the box, None for any other amount."""
    try:
        a = int(amount)
    except (TypeError, ValueError):
        return None
    if LIKE < a <= LIKE + MAX_ID:
        return a - LIKE, True
    if UNLIKE < a <= UNLIKE + MAX_ID:
        return a - UNLIKE, False
    return None


class Hearts:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("HEARTS_PATH", "/data/hearts.json")
        self.marks: dict[str, list] = {}   # "<sender>:<id>" -> [block time, place in the block, 1 heart / 0 taken back]
        self.count = 0                      # marks read (each transaction once per block it is in)
        self.dirty = False
        self.saved_at = 0.0
        try:
            with open(self.path) as f:
                st = json.load(f)
            self.marks = {str(k): [int(v[0]), int(v[1]), 1 if v[2] else 0] for k, v in (st.get("marks") or {}).items()
                          if isinstance(v, list) and len(v) == 3}
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
                    d = decode(op[2])
                    if d is None:
                        continue
                    key = f"{str(op[0]).lower()}:{d[0]}"
                    new, old = [ts, i, 1 if d[1] else 0], self.marks.get(key)
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
        wallets = set()
        for key, (_, _, on) in self.marks.items():
            if not on:
                continue
            sender, pid = key.rsplit(":", 1)
            parts[pid] = parts.get(pid, 0) + 1
            wallets.add(sender)
        return {"box": BOX, "parts": dict(sorted(parts.items(), key=lambda kv: int(kv[0]))), "wallets": len(wallets),
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
