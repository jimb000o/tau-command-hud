#!/usr/bin/env python3
"""Keep docker's build cache from filling the server's disk, without ever touching the tau-lang stage.

Every `up` that rebuilds a service leaves layers behind in BuildKit's cache: 15.7 GB of it on 14.11.2026, with
1.4 GB of the disk left. A plain `docker builder prune` would also take the tau-lang stage of the node image (the
compiled engine, its tau-store and ccache), and building that again takes hours on this server and once froze it.
BuildKit's own garbage collection drops the least recently used entries first, and the tau-lang stage is used only
when the node image is built, so a cache that keeps growing puts it first in line there too.

So once a day (any `up` starts it in the background, `up cache now` at once) this drops cache entries that no build
used for PRUNE_MIN_DAYS days (3), oldest first, until the whole cache is below BUILDCACHE_KEEP_GB (6), and never an
entry of the tau-lang stage. Nothing happens while the cache is below that size. Entries in use are left to docker.

Commands: daily (at most once a day) | now | status | plan (what `now` would drop, drops nothing)
State and log: /var/lib/tau-buildcache (BUILDCACHE_DIR)
"""
from __future__ import annotations

import calendar
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time

DIR = os.environ.get("BUILDCACHE_DIR", "/var/lib/tau-buildcache")
STAMP = os.path.join(DIR, "last.json")
LOG = os.path.join(DIR, "log.txt")
INFRA = os.environ.get("BUILDCACHE_INFRA", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# the tau-lang stage of infra/node/Dockerfile: its steps, its compile run and that run's two cache mounts, and the
# node image's copies of it (a new IDNI commit reuses all of these; only the node sources above them change)
PROTECT = re.compile(r"tau-builder|dev build release|tau-store|tau-ccache|/app/tau-lang", re.I)
DAY = 86400


def sh(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def now() -> float:
    return time.time()


def read_env() -> dict:
    env = {}
    try:
        with open(os.path.join(INFRA, ".env")) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def setting(cfg: dict, key: str, default: float) -> float:
    try:
        return float(os.environ.get(key) or cfg.get(key) or default)
    except ValueError:
        return default


def size_bytes(text: str) -> int:
    """docker's sizes: 0B, 4.452kB, 68.16MB, 1.54GB (powers of 1000)."""
    m = re.match(r"^\s*([\d.]+)\s*([kKMGTP]?)i?B\s*$", text or "")
    if not m:
        return 0
    return int(float(m.group(1)) * 1000 ** " KMGTP".index(m.group(2).upper() or " "))


def age_seconds(text: str) -> float | None:
    """docker's 'Last used' wording (go-units HumanDuration + ' ago') in seconds; None when it says nothing."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t.startswith("less than a second") or t.startswith("now"):
        return 0.0
    if t.startswith("about a minute"):
        return 60.0
    if t.startswith("about an hour") or t.startswith("an hour"):
        return 3600.0
    m = re.match(r"^(\d+)\s+(second|minute|hour|day|week|month|year)s?\b", t)
    if not m:
        return None
    unit = {"second": 1, "minute": 60, "hour": 3600, "day": DAY, "week": 7 * DAY, "month": 30 * DAY,
            "year": 365 * DAY}[m.group(2)]
    return float(m.group(1)) * unit


def created_age(text: str) -> float | None:
    """'Created at: 2026-11-13 09:04:11.52 +0000 UTC' in seconds before now."""
    m = re.match(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)", (text or "").strip())
    if not m:
        return None
    try:
        t = calendar.timegm(time.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return None
    return max(0.0, now() - t)


def records(text: str) -> list[dict]:
    """`docker buildx du --verbose`: blocks of `Key: value` lines split by blank lines, one per cache entry (it has an
    ID); the summary block at the end (Shared, Private, Reclaimable, Total) has none and is skipped."""
    out = []
    for block in re.split(r"\n\s*\n", text or ""):
        rec = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                rec.setdefault(key.strip().lower(), value.strip())
        if not rec.get("id"):
            continue
        rec["bytes"] = size_bytes(rec.get("size", ""))
        rec["protected"] = bool(PROTECT.search(rec.get("description", "")))
        used = age_seconds(rec.get("last used", ""))
        rec["unused_s"] = used if used is not None else created_age(rec.get("created at", ""))
        out.append(rec)
    return out


def listing() -> list[dict] | None:
    rc, out = sh(["docker", "buildx", "du", "--verbose"], timeout=300)
    return records(out) if rc == 0 else None


def plan(recs: list[dict], keep_bytes: float, min_age_s: float) -> list[dict]:
    """Entries to drop, oldest first, until the cache is below keep_bytes; never protected, in-use or young ones."""
    total = sum(r["bytes"] for r in recs)
    if total <= keep_bytes:
        return []
    pool = [r for r in recs
            if not r["protected"]
            and (r.get("reclaimable") or "true").lower() == "true"
            and r["unused_s"] is not None and r["unused_s"] >= min_age_s]
    pool.sort(key=lambda r: -r["unused_s"])
    out = []
    for r in pool:
        if total <= keep_bytes:
            break
        out.append(r)
        total -= r["bytes"]
    return out


def gb(n: float) -> str:
    return f"{n / 1e9:.1f} GB"


def disk_free() -> float:
    try:
        return shutil.disk_usage("/var/lib/docker" if os.path.isdir("/var/lib/docker") else "/").free
    except OSError:
        return 0.0


def log(line: str) -> None:
    os.makedirs(DIR, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%SZ ", time.gmtime()) + line + "\n")


def run(force: bool = False) -> str:
    cfg = read_env()
    os.makedirs(DIR, exist_ok=True)
    try:
        last = json.load(open(STAMP))
    except (OSError, ValueError):
        last = {}
    if not force and now() - float(last.get("t") or 0) < DAY:
        return "build cache: looked at today already"
    with open(os.path.join(DIR, "lock"), "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return "build cache: a clean-up is under way"
        recs = listing()
        if recs is None:
            return "build cache: docker buildx du did not answer, nothing dropped"
        keep = setting(cfg, "BUILDCACHE_KEEP_GB", 6) * 1e9
        min_age = setting(cfg, "BUILDCACHE_MIN_DAYS", 3) * DAY
        before, free_before = sum(r["bytes"] for r in recs), disk_free()
        todo, dropped = plan(recs, keep, min_age), 0
        for r in todo:
            rc, out = sh(["docker", "buildx", "prune", "--force", "--all", "--filter", f"id={r['id']}"], timeout=300)
            if rc == 0:
                dropped += 1
            else:
                log(f"could not drop {r['id']}: {out.strip()[-160:]}")
        freed = max(0.0, disk_free() - free_before)
        kept = sum(r["bytes"] for r in recs if r["protected"])
        line = (f"build cache: {gb(before)}, dropped {dropped} of {len(recs)} entries unused for "
                f"{setting(cfg, 'BUILDCACHE_MIN_DAYS', 3):g}+ days, {gb(freed)} freed; tau-lang stage kept ({gb(kept)})"
                if todo else f"build cache: {gb(before)}, below {gb(keep)} or nothing old enough, nothing dropped"
                             f"; tau-lang stage kept ({gb(kept)})")
        json.dump({"t": now(), "line": line, "dropped": dropped, "freed": freed}, open(STAMP, "w"))
        log(line)
        return line


def status() -> list[str]:
    try:
        last = json.load(open(STAMP))
    except (OSError, ValueError):
        last = {}
    recs = listing()
    lines = []
    if recs is None:
        lines.append("cache:   docker buildx du did not answer")
    else:
        prot = [r for r in recs if r["protected"]]
        lines.append(f"cache:   {gb(sum(r['bytes'] for r in recs))} in {len(recs)} entries, tau-lang stage "
                     f"{gb(sum(r['bytes'] for r in prot))} in {len(prot)} (never dropped), disk free {gb(disk_free())}")
        if not prot:
            lines.append("         ! no tau-lang stage in the cache: the next node build compiles tau-lang (hours)")
    if last.get("line"):
        lines.append("         last clean-up " + time.strftime("%d.%m. %H:%M UTC", time.gmtime(last["t"])) + ": "
                     + last["line"].replace("build cache: ", ""))
    return lines


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd in ("daily", "now"):
        print(run(force=cmd == "now"))
        return 0
    if cmd == "plan":
        recs = listing() or []
        cfg = read_env()
        for r in plan(recs, setting(cfg, "BUILDCACHE_KEEP_GB", 6) * 1e9, setting(cfg, "BUILDCACHE_MIN_DAYS", 3) * DAY):
            print(f"{r['id'][:12]}  {r.get('size', ''):>9}  {r.get('last used', '')}  {r.get('description', '')[:80]}")
        return 0
    if cmd == "status":
        print("\n".join(status()))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
