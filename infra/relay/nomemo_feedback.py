"""What players tell the crew: `feedback <text>` in the No Memo terminal (nomemo/game.js) lands here.

GET /nomemo/feedback?t=<text>&w=<wallet>&d=<contracts settled>&c=<chapters claimed>&l=<lang>
  t  the player's words, MIN_LEN to MAX_LEN characters (control characters dropped)
  w  the player's test wallet address, if the game has one (public anyway: it is on the chain)
  d, c, l  how far the player is and the page's language, so a remark can be read in its place in the game
Answers {"ok": true} or {"error": <code>} with code short, long, wait, today, full, off.

Each entry is one JSON line appended to NOMEMO_FEEDBACK_PATH (default /data/nomemo-feedback.jsonl): time (UTC),
text, wallet, d, c, l. Nothing else: no IP address, no browser, no name. The visitor's address is kept in memory
only for the limits (one remark every GAP seconds, PER_DAY a day) and forgotten at 00:00 UTC.
Nothing is shown anywhere; the owner reads it with `up nomemo feedback` (infra/up.sh), which prints the entries not
read yet. NOMEMO_FEEDBACK=0 in infra/.env stops taking new ones.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from urllib.parse import parse_qs

MIN_LEN = 3
MAX_LEN = 600
GAP = 30                 # seconds between two remarks from one visitor
PER_DAY = 10             # remarks a day from one visitor
ALL_DAY = 500            # remarks a day from everyone
MAX_BYTES = 5_000_000    # the file stops growing here until it is cleared

CTRL = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮⁦-⁩]")


class Feedback:
    def __init__(self, path: str | None = None, clock=time.time, enabled: bool | None = None):
        data = os.environ.get("CRUISE_DATA", "/data")
        self.path = path or os.environ.get("NOMEMO_FEEDBACK_PATH", os.path.join(data, "nomemo-feedback.jsonl"))
        self.enabled = (os.environ.get("NOMEMO_FEEDBACK", "1") != "0") if enabled is None else enabled
        self.clock = clock
        self.day = ""
        self.count = 0
        self.seen: dict[str, list[float]] = {}   # visitor address -> times today, memory only

    def _tick(self, now: float):
        day = dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y-%m-%d")
        if day != self.day:
            self.day, self.count, self.seen = day, 0, {}

    def add(self, ip: str, text: str, wallet: str = "", done: str = "", chapters: str = "", lang: str = "") -> dict:
        if not self.enabled:
            return {"error": "off"}
        text = re.sub(r"\s+", " ", CTRL.sub(" ", text or "")).strip()
        if len(text) < MIN_LEN:
            return {"error": "short"}
        if len(text) > MAX_LEN:
            return {"error": "long"}
        now = self.clock()
        self._tick(now)
        mine = self.seen.get(ip, [])
        if mine and now - mine[-1] < GAP:
            return {"error": "wait", "wait": int(GAP - (now - mine[-1])) + 1}
        if len(mine) >= PER_DAY or self.count >= ALL_DAY:
            return {"error": "today"}
        try:
            if os.path.exists(self.path) and os.path.getsize(self.path) >= MAX_BYTES:
                return {"error": "full"}
        except OSError:
            pass
        wallet = (wallet or "").lower()
        entry = {"at": dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "text": text,
                 "wallet": wallet if len(wallet) == 96 and all(ch in "0123456789abcdef" for ch in wallet) else None,
                 "d": int(done) if done.isdigit() and int(done) <= 99 else None,
                 "c": int(chapters) if chapters.isdigit() and int(chapters) <= 9 else None,
                 "l": lang if lang in ("en", "zh", "ja") else None}
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            return {"error": "full"}
        self.seen[ip] = mine + [now]
        self.count += 1
        return {"ok": True}

    def route(self, path: str, query: str, ip: str) -> dict | None:
        if path != "/nomemo/feedback":
            return None
        q = {k: v[0] for k, v in parse_qs(query).items()}
        return self.add(ip, q.get("t", ""), q.get("w", ""), q.get("d", ""), q.get("c", ""), q.get("l", ""))
