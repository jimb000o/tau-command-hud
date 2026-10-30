"""How many nodes were on the network, hour by hour (tauhud.com/meta/, the Nodes view).

The relay's peer book (relay.py, /peers) only keeps each peer's first and last sighting, so it cannot say how many
nodes were there at a given hour. From the moment this module runs, every peer poll adds the peers our node had contact
with to the current UTC hour and day; a finished hour or day keeps only its counts. A peer counts once it is steady
(known for PEER_STEADY seconds, like "online" on /peers), so test nodes that come and go for a minute stay out. Our own
node counts too: the history is written by it.

The hours before recording began are estimated from the peer book: a peer counts for every hour between its first and
last sighting. That overcounts a peer that was away in between, so those hours are marked as estimated. Nothing exists
before our node first ran (the peer book's "since"): the testnet keeps no record of its nodes.

GET /nodes/history
  days        {"YYYY-MM-DD": [most at once, different nodes that day, community nodes that day, estimated 0|1]}
  hours       {"YYYY-MM-DD": [24 counts]} nodes per UTC hour, the last HOUR_DAYS days
  recorded    first hour counted as it happened (unix seconds); earlier hours are estimated
  since       when our node's peer book began
Peer IDs are never written to the history; only counts, plus the current hour's and day's IDs to count them once.
"""
from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger("relay.nodehist")

HOUR, DAY = 3600, 86400
HOUR_DAYS = 31
KEEP_DAYS = 400
SAVE_SECONDS = 300


def day_of(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


class NodeHistory:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("NODEHIST_PATH", "/data/nodehist.json")
        self.saved_at = 0.0
        st = None
        try:
            with open(self.path) as f:
                st = json.load(f)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new node history", self.path, exc)
        if not isinstance(st, dict) or not isinstance(st.get("hours"), dict):
            st = {"recorded": None, "hours": {}, "days": {}, "hour": None, "hour_ids": [], "day": None, "day_ids": [], "day_comm": []}
        for k, v in (("days", {}), ("hour_ids", []), ("day_ids", []), ("day_comm", [])):
            st.setdefault(k, v)
        self.st = st

    def _save(self, now: float):
        self.saved_at = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.st, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; the node history lives in memory only", self.path, exc)
                self._warned = True

    def note(self, active: list[str], community: set, now: float | None = None):
        """active = steady peers our node had contact with just now; community = the ones that are community nodes."""
        now = now if now is not None else time.time()
        st = self.st
        h, d = int(now // HOUR * HOUR), day_of(now)
        if st["recorded"] is None:
            st["recorded"] = h
        if st["hour"] != h:
            if st["hour"] is not None:
                self._close_hour()
            st["hour"], st["hour_ids"] = h, []
        if st["day"] != d:
            if st["day"] is not None:
                self._close_day()
            st["day"], st["day_ids"], st["day_comm"] = d, [], []
        changed = False
        for pid in active:
            if pid not in st["hour_ids"]:
                st["hour_ids"].append(pid)
                changed = True
            if pid not in st["day_ids"]:
                st["day_ids"].append(pid)
                changed = True
            if pid in community and pid not in st["day_comm"]:
                st["day_comm"].append(pid)
        if changed or now - self.saved_at >= SAVE_SECONDS:
            self._save(now)

    def _close_hour(self):
        st = self.st
        st["hours"][str(st["hour"])] = len(st["hour_ids"]) + 1   # + our own node
        cutoff = st["hour"] - KEEP_DAYS * DAY
        for k in [k for k in st["hours"] if int(k) < cutoff]:
            del st["hours"][k]

    def _close_day(self):
        st = self.st
        st["days"][st["day"]] = [len(st["day_ids"]) + 1, len(st["day_comm"])]
        for k in sorted(st["days"])[:-KEEP_DAYS]:
            del st["days"][k]

    def history(self, book: dict, community: set, steady, now: float | None = None) -> dict:
        """book = the relay's peer book {"since", "peers"}; steady(pid, row) -> bool."""
        now = now if now is not None else time.time()
        st = self.st
        cur = int(now // HOUR * HOUR)
        rec = st["recorded"] if st["recorded"] is not None else cur
        hours = {int(k): v for k, v in st["hours"].items()}
        if st["hour"] is not None:
            hours[st["hour"]] = len(st["hour_ids"]) + 1
        # before recording began: a peer counts for every hour between its first and last sighting
        since = int(book.get("since") or rec)
        spans = []
        for pid, r in (book.get("peers") or {}).items():
            last = max(r.get("last_direct") or 0, r.get("last_heard") or 0)
            if last and steady(pid, r):
                spans.append((r["first_seen"], last, pid in community))
        est_days: dict[str, list] = {}
        for t in range(since // HOUR * HOUR, rec, HOUR):
            hours[t] = 1 + sum(1 for a, b, _ in spans if a < t + HOUR and b >= t)
        for t in range(since // DAY * DAY, rec // DAY * DAY + (DAY if rec % DAY else 0), DAY):
            d = day_of(t)
            if d in st["days"] or d == st["day"]:
                continue
            inside = [c for a, b, c in spans if a < t + DAY and b >= t]
            est_days[d] = [1 + len(inside), sum(inside)]
        days: dict[str, list] = {}
        for t, n in hours.items():
            d = day_of(t)
            row = days.setdefault(d, [0, 0, 0, 0])
            row[0] = max(row[0], n)
            if t < rec:
                row[3] = 1
        for d, v in st["days"].items():
            days.setdefault(d, [0, 0, 0, 0])[1:3] = v
        if st["day"] is not None:
            days.setdefault(st["day"], [0, 0, 0, 0])[1:3] = [len(st["day_ids"]) + 1, len(st["day_comm"])]
        for d, v in est_days.items():
            row = days.setdefault(d, [0, 0, 0, 1])
            if row[1] == 0:
                row[1:3] = v
            row[3] = 1
        for row in days.values():
            row[1] = max(row[1], row[0])   # a day's different nodes are at least the most at once
        recent = day_of(cur - (HOUR_DAYS - 1) * DAY)
        by_hour: dict[str, list] = {}
        for t, n in hours.items():
            d = day_of(t)
            if d >= recent:
                by_hour.setdefault(d, [0] * 24)[t % DAY // HOUR] = n
        return {"days": dict(sorted(days.items())), "hours": dict(sorted(by_hour.items())), "recorded": rec,
                "since": since, "generated_at": round(now)}
