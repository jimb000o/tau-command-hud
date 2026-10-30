"""How far people get when they set up a node with the kit (tauhud.com/meta/, the Nodes view).

Two kinds of trace, both counts without addresses:

  copied   the Nodes page sends GET /setup?s=copied when someone copies the install command (a count per UTC day)
  steps    kit/install.sh, only when NODE_NAME is set (the same opt-in as the node's reports), sends
           GET /setup?i=<random install id>&s=<step>&t=<seconds since it started> as it reaches each step:
           start, packages, docker, kit, build (the long tau-lang compile begins), up (the node runs);
           and s=fail&at=<step> when the script stops with an error. The install id is a random number made
           on that server, so a re-run counts once; nothing ties it to a person or an address.

What happens after "up" comes from the community board (relay.py): the node's first report, the first time its
head matched our chain near the tip, and whether it still reports. The board keeps those for 30 days.

GET /setup/stats -> {"days": {"YYYY-MM-DD": {"copied": n, "start": n, …}}, "installs": {"reached": {step: n},
                     "failed": {step: n}, "minutes": {step: median minutes from start}}, "since": first trace}
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

log = logging.getLogger("relay.setupfunnel")

STEPS = ("start", "packages", "docker", "kit", "build", "up")
INSTALL_ID = re.compile(r"^[0-9a-f]{16}$")
KEEP_DAYS = 400
INSTALLS_MAX = 5000
SAVE_SECONDS = 60
BURST, REFILL = 20.0, 0.2   # per address: 20 at once, then one every 5 s (the address itself is never kept)


def day_of(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


class SetupFunnel:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("SETUP_PATH", "/data/setup.json")
        self.saved_at = 0.0
        self.buckets: dict[str, list] = {}
        st = None
        try:
            with open(self.path) as f:
                st = json.load(f)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting afresh", self.path, exc)
        if not isinstance(st, dict) or not isinstance(st.get("days"), dict) or not isinstance(st.get("installs"), dict):
            st = {"since": None, "days": {}, "installs": {}}
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
                log.warning("cannot write %s: %r; setup traces live in memory only", self.path, exc)
                self._warned = True

    def _allow(self, ip: str, now: float) -> bool:
        if len(self.buckets) > 5000:
            self.buckets.clear()
        tokens, at = self.buckets.get(ip, (BURST, now))
        tokens = min(BURST, tokens + (now - at) * REFILL)
        if tokens < 1:
            self.buckets[ip] = [tokens, now]
            return False
        self.buckets[ip] = [tokens - 1, now]
        return True

    def note(self, query: dict, ip: str, now: float | None = None) -> bool:
        """One trace from GET /setup; False if it was not counted."""
        now = now if now is not None else time.time()
        s = str(query.get("s") or "")
        if not self._allow(ip, now):
            return False
        st = self.st
        d = st["days"].setdefault(day_of(now), {})
        if s == "copied":
            d["copied"] = d.get("copied", 0) + 1
        else:
            i = str(query.get("i") or "")
            if not INSTALL_ID.match(i) or (s not in STEPS and s != "fail"):
                return False
            try:
                t = max(0, min(10 ** 6, int(query.get("t") or 0)))
            except ValueError:
                t = 0
            row = st["installs"].get(i)
            if row is None:
                if len(st["installs"]) >= INSTALLS_MAX:
                    oldest = min(st["installs"], key=lambda k: st["installs"][k]["last"])
                    del st["installs"][oldest]
                row = st["installs"][i] = {"first": round(now), "last": round(now), "steps": {}, "failed": None}
            row["last"] = round(now)
            if s == "fail":
                at = str(query.get("at") or "")
                row["failed"] = at if at in STEPS else "start"
                d["fail"] = d.get("fail", 0) + 1
            elif s not in row["steps"]:
                row["steps"][s] = t
                row["failed"] = None   # a re-run that gets further is no longer stuck
                d[s] = d.get(s, 0) + 1
        if st["since"] is None:
            st["since"] = round(now)
        for k in sorted(st["days"])[:-KEEP_DAYS]:
            del st["days"][k]
        self._save(now)
        return True

    def stats(self) -> dict:
        inst = self.st["installs"].values()
        reached = {s: sum(1 for r in inst if s in r["steps"]) for s in STEPS}
        failed = {s: sum(1 for r in inst if r["failed"] == s) for s in STEPS}
        minutes = {}
        for s in STEPS:
            ts = sorted(r["steps"][s] for r in inst if s in r["steps"])
            if ts:
                minutes[s] = round(ts[len(ts) // 2] / 60)
        return {"days": dict(sorted(self.st["days"].items())), "installs": {"reached": reached, "failed": failed,
                "minutes": minutes, "total": len(self.st["installs"])}, "since": self.st["since"]}
