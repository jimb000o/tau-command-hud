"""Testnet load (GET /load): how hard the testnet is working, minute by minute, for tauhud.com/load/.

The relay already sees everything this needs. From the blocks (read at request time): transactions sealed per
minute and the gaps between blocks. From the mempool poll (relay.py track_mempool, every few seconds): how many
transactions really wait, and for every transaction a block holds, how long it waited (first seen listed -> first
poll that finds it in a block, so accurate to one poll). Ghosts, transactions already sealed but still listed by the
node (IDNI #81), are neither waiting nor still waiting for a block. From the relay's own sending: transactions visitors' browsers sent through
tauhud (sendtx), White Rabbit Key's island bot sent (island.py), and sends tauhud or the node refused.

Kept per UTC minute for WINDOW minutes, plus the records since tracking began; both survive a relay restart in
LOAD_PATH. Nothing about who sent a transaction is stored, only counts.
"""
from __future__ import annotations

import json
import os
import time

VERSION = 2               # 2: waiting and the wait for a block leave out ghosts (sealed, still listed)
WINDOW = 360              # minutes kept and shown: six hours
SAVE_SECONDS = 60
STRAIN_WAIT = 60          # seconds: a transaction waiting longer than this for its block is a sign of strain
STRAIN_GAP = 90           # seconds between two blocks while transactions wait: strain


def _minute(t: float) -> int:
    return int(t // 60)


class Load:
    def __init__(self, path: str | None = None, clock=time.time):
        self.path = path or os.environ.get("LOAD_PATH", "/data/load.json")
        self.clock = clock
        self.mins: dict[int, dict] = {}   # minute -> {"pool": most waiting, "sent", "bot", "cruise", "refused", "wait": [sum, n, max]}
        self.top = {"pool": 0, "per_min": 0, "per_block": 0, "wait": 0, "since": round(clock())}
        self.saved_at = 0.0
        self._cache = (0.0, None)
        self.load()

    # ---------- what the relay tells it ----------
    def _m(self, now: float) -> dict:
        m = _minute(now)
        row = self.mins.get(m)
        if row is None:
            row = self.mins[m] = {"pool": 0, "sent": 0, "bot": 0, "cruise": 0, "refused": 0, "wait": [0, 0, 0]}
            for k in [k for k in self.mins if k <= m - WINDOW]:
                del self.mins[k]
        return row

    def pool(self, n: int, now: float | None = None):
        now = self.clock() if now is None else now
        row = self._m(now)
        row["pool"] = max(row["pool"], int(n))
        self.top["pool"] = max(self.top["pool"], int(n))
        self.maybe_save(now)

    def sealed_after(self, seconds: float, now: float | None = None):
        """A transaction left the mempool into a block after waiting this long."""
        now = self.clock() if now is None else now
        s = max(0, round(seconds))
        w = self._m(now)["wait"]
        w[0] += s
        w[1] += 1
        w[2] = max(w[2], s)
        self.top["wait"] = max(self.top["wait"], s)

    def sent(self, by: str = "sent", now: float | None = None):
        """by: "sent" (a visitor's browser through tauhud), "bot" (the island bot), "cruise" (a cruise ship's simulated
        passengers) or "refused"."""
        now = self.clock() if now is None else now
        row = self._m(now)
        k = by if by in ("sent", "bot", "cruise", "refused") else "sent"
        row[k] = row.get(k, 0) + 1

    # ---------- GET /load ----------
    def snapshot(self, blocks: list, waiting: int = 0, now: float | None = None) -> dict:
        """blocks: [(timestamp, txs), ...] of the current chain, oldest first."""
        now = self.clock() if now is None else now
        at, cached = self._cache
        if cached is not None and now - at < 5:
            return cached
        end = _minute(now)
        start = end - WINDOW + 1
        sealed = [0] * WINDOW
        nblocks = [0] * WINDOW
        gaps = [0] * WINDOW
        prev = None
        for ts, n in blocks:
            if not ts:
                continue
            i = _minute(ts) - start
            if prev is not None and 0 <= i < WINDOW:
                gaps[i] = max(gaps[i], ts - prev)
            prev = ts
            if 0 <= i < WINDOW:
                sealed[i] += n
                nblocks[i] += 1
            self.top["per_block"] = max(self.top["per_block"], n)
        for s in sealed:
            self.top["per_min"] = max(self.top["per_min"], s)
        rows = [self.mins.get(start + i) for i in range(WINDOW)]
        col = lambda k: [(r or {}).get(k, 0) for r in rows]   # noqa: E731
        waits = [(r or {}).get("wait", [0, 0, 0]) for r in rows]
        last = [ts for ts, _ in blocks if ts][-1:] or [None]
        hour = slice(WINDOW - 60, WINDOW)
        w_sum = sum(w[0] for w in waits[hour])
        w_n = sum(w[1] for w in waits[hour])
        out = {
            "generated_at": round(now), "start": start * 60, "minutes": WINDOW,
            "sealed": sealed, "blocks": nblocks, "gap": gaps,
            "pool": col("pool"), "sent": col("sent"), "bot": col("bot"), "cruise": col("cruise"), "refused": col("refused"),
            "wait_avg": [round(w[0] / w[1]) if w[1] else None for w in waits], "wait_max": [w[2] if w[1] else None for w in waits],
            "now": {
                "waiting": int(waiting),
                "last_block_age": round(now - last[0]) if last[0] else None,
                "sealed_hour": sum(sealed[hour]), "blocks_hour": sum(nblocks[hour]),
                "sent_hour": sum(col("sent")[hour]), "bot_hour": sum(col("bot")[hour]), "cruise_hour": sum(col("cruise")[hour]),
                "refused_hour": sum(col("refused")[hour]),
                "wait_hour": round(w_sum / w_n) if w_n else None,
                "busiest_minute_hour": max(sealed[hour]) if sealed else 0,
            },
            "records": dict(self.top),
            "thresholds": {"wait": STRAIN_WAIT, "gap": STRAIN_GAP},
        }
        out["state"] = self.verdict(out, now)
        self._cache = (now, out)
        return out

    @staticmethod
    def verdict(s: dict, now: float) -> str:
        """calm / busy / strained / stalled, from the last ten minutes."""
        n = s["now"]
        recent = slice(-10, None)
        if n["waiting"] and n["last_block_age"] is not None and n["last_block_age"] > 600:
            return "stalled"
        waits = [w for w in s["wait_max"][recent] if w is not None]
        if (waits and max(waits) > STRAIN_WAIT) or max(s["gap"][recent] or [0]) > STRAIN_GAP and n["waiting"] \
                or sum(s["refused"][recent]) > 5:
            return "strained"
        if sum(s["sealed"][recent]) >= 100:
            return "busy"
        return "calm"

    # ---------- kept across restarts ----------
    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.mins = {int(k): v for k, v in (d.get("mins") or {}).items()}
            self.top.update(d.get("top") or {})
            if d.get("v") != VERSION:   # the first version counted ghosts (sealed, still listed) as waiting: drop those numbers
                for row in self.mins.values():
                    row["pool"], row["wait"] = 0, [0, 0, 0]
                self.top["pool"] = self.top["wait"] = 0
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def maybe_save(self, now: float):
        if now - self.saved_at < SAVE_SECONDS:
            return
        self.saved_at = now
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"v": VERSION, "mins": self.mins, "top": self.top}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError:
            pass
