"""Our node's sync and peering failures, read from its own log, for the weekly report to IDNI (idni_report.py).

IDNI asked in its Q&A of November 2026 (youtube.com/watch?v=_4DnQImw4tQ, 13:37) for exactly this help: run a node and
report sync and peering failures with their logs. The report already counts what our node saw from the outside
(answering, in sync, restarts, reorgs); this adds what the node itself wrote down.

Where the log comes from: Docker keeps each container's output as JSON lines under /var/lib/docker/containers/<id>/
(<id>-json.log, rotated to .1 and .2 by the compose file's logging options), readable by root only. The small
`nodelog` service (docker-compose.yml) runs this file as root with that folder mounted read-only at NODE_LOG_DIR and
no network; the container whose config.v2.json names the tau-node service is ours. Once an hour it keeps the WARNING
and ERROR lines from the node's networking and sync code of the last KEEP_DAYS days, masked (IP addresses other than
IDNI's bootnode and our own become x.x.x.x, peer ids are shortened), with up to TRACE_LINES lines of each traceback,
in NODE_LOG_STATE. The weekly report (blog service, not root) reads only that file: it groups the lines by their
message with the changing parts (peer ids, numbers, addresses) taken out, counts them and shows one example each.

  python node_logs.py loop        the nodelog service: the file anew every hour
  python node_logs.py [days]      the groups of the last days (default 7), read from the node's log directly
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
import sys
import time

LOG_DIR = os.environ.get("NODE_LOG_DIR", "/dockerlogs")
SERVICE = os.environ.get("NODE_LOG_SERVICE", "tau-node")
TRACE_LINES = 12
GROUPS = 6
STATE = os.environ.get("NODE_LOG_STATE", "/state/node-log.json")
KEEP_DAYS = 9
EVERY = 3600
MAX_LINES = 3000
KEEP_IPS = {"34.251.82.246", "2.31.101.42"}   # IDNI's bootnode (public in the README) and our own node (public on /nodes/)
# the node's own format (tau-testnet config.py): "2026-11-10 12:00:00 WARNING [network.host] message"
LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:,\d+)? (WARNING|ERROR|CRITICAL) \[([\w.]+)\] (.*)$")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
WATCH = re.compile(r"^(network|sync|p2p|libp2p|gossip|dht|peer)|\.(host|sync|discovery|gossip|dht_manager|bootstrap)$", re.I)
# "connect" alone is not enough: the node's WebSocket server logs browsers and our relay hanging up as "WS connection
# task crashed" (tau.server); those are clients, not peers, and stay out (first week's report, 10.11.2026)
WORDS = re.compile(r"sync|peer|dial|handshake|reconnect|bootstrap|gossip|header|block bodies|ingest|genesis", re.I)
IP = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
PEER = re.compile(r"\b(12D3Koo[1-9A-HJ-NP-Za-km-z]{30,}|Qm[1-9A-HJ-NP-Za-km-z]{40,})\b")
HEX = re.compile(r"\b[0-9a-f]{16,}\b", re.I)
NUM = re.compile(r"\b\d+(?:\.\d+)?\b")


def find_logs(root: str = LOG_DIR, service: str = SERVICE) -> list[str]:
    """The log files (newest last) of the container running `service`, or [] when there is none or no access."""
    for cfg in glob.glob(os.path.join(root, "*", "config.v2.json")):
        try:
            with open(cfg, encoding="utf-8") as f:
                c = json.load(f)
        except (OSError, ValueError):
            continue
        labels = (c.get("Config") or {}).get("Labels") or {}
        name = str(c.get("Name") or "")
        if labels.get("com.docker.compose.service") == service or re.search(rf"[-_/]{re.escape(service)}[-_]\d+$", name):
            d = os.path.dirname(cfg)
            files = glob.glob(os.path.join(d, "*-json.log*"))
            # oldest first: .2, .1, then the live file
            return sorted(files, key=lambda p: -int(p.rsplit(".", 1)[1]) if p.rsplit(".", 1)[1].isdigit() else 0)
    return []


def mask(text: str) -> str:
    text = IP.sub(lambda m: m.group(1) if m.group(1) in KEEP_IPS else "x.x.x.x", text)
    return PEER.sub(lambda m: m.group(1)[:12] + "…", text)


def shape(msg: str) -> str:
    """The message with what changes from line to line taken out, so that one kind of failure is one group."""
    s = PEER.sub("<peer>", msg)
    s = re.sub(r"\b(12D3Koo|Qm)\w*…", "<peer>", s)
    s = IP.sub("<ip>", s)
    s = HEX.sub("<hex>", s)
    return NUM.sub("<n>", s)[:160]


def read(files: list[str], t0: float, t1: float) -> list[dict]:
    """The watched WARNING/ERROR lines between t0 and t1 with the traceback lines that follow each."""
    out: list[dict] = []
    cur = None
    for path in files:
        try:
            f = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            for raw in f:
                try:
                    text = json.loads(raw).get("log", "")
                except ValueError:
                    continue
                for line in text.rstrip("\n").split("\n"):
                    if STAMP.match(line):   # every log line, any level, ends the traceback of the one before
                        cur = None
                        m = LINE.match(line)
                        if not m:
                            continue
                        when, level, name, msg = m.groups()
                        if not (WATCH.search(name) or WORDS.search(msg)):
                            continue
                        try:
                            # the node logs in the container's local time, which is UTC in the image
                            t = dt.datetime.strptime(when, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp()
                        except ValueError:
                            continue
                        if t0 <= t < t1:
                            cur = {"t": t, "level": level, "name": name, "msg": mask(msg), "trace": []}
                            out.append(cur)
                    elif cur is not None and line.strip() and len(cur["trace"]) < TRACE_LINES:
                        cur["trace"].append(mask(line.rstrip())[:240])
    return out


def groups(entries: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    for e in entries:
        k = f"{e['level']} [{e['name']}] {shape(e['msg'])}"
        g = by.setdefault(k, {"key": k, "level": e["level"], "name": e["name"], "count": 0, "first": e["t"], "last": e["t"], "example": e})
        g["count"] += 1
        g["first"], g["last"] = min(g["first"], e["t"]), max(g["last"], e["t"])
        if not g["example"]["trace"] and e["trace"]:
            g["example"] = e   # an example that shows where it failed beats one that does not
    return sorted(by.values(), key=lambda g: (-g["count"], g["first"]))


def summary(t0: float, t1: float, root: str = LOG_DIR) -> dict | None:
    """{"lines": n, "groups": [...]} straight from the node's log, or None when it cannot be read here."""
    files = find_logs(root)
    if not files:
        return None
    entries = read(files, t0, t1)
    return {"lines": len(entries), "groups": groups(entries)}


def keep(now: float | None = None, root: str = LOG_DIR, path: str = STATE) -> int:
    """The nodelog service's round: the last KEEP_DAYS days of watched lines into the state file (masked already)."""
    now = time.time() if now is None else now
    files = find_logs(root)
    entries = read(files, now - KEEP_DAYS * 86400, now + 60) if files else []
    data = {"at": round(now), "found": bool(files), "entries": entries[-MAX_LINES:]}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    return len(entries)


def from_state(t0: float, t1: float, path: str = STATE) -> dict | None:
    """What the weekly report shows: the kept lines of its week, grouped; None when the nodelog service has not
    written its file (not running, or it cannot find the node's log), so the report leaves the section out."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not data.get("found") or time.time() - (data.get("at") or 0) > 3 * 86400:
        return None
    entries = [e for e in data.get("entries") or [] if t0 <= (e.get("t") or 0) < t1]
    return {"lines": len(entries), "groups": groups(entries)}


def utc(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%a %d %b %H:%M UTC")


def section(s: dict | None, short: int = 0) -> list[str]:
    """The report's Markdown lines; `short` 1..3 leaves out examples, then groups, until the issue link fits."""
    if s is None:
        return []
    L = ["### Sync and peering, from our node's own log"]
    if not s["groups"]:
        return L + ["- No warning or error about syncing or peers in our node's log this week.", ""]
    gs = s["groups"][: (GROUPS if short < 3 else 3)]
    L.append(f"{s['lines']} warning or error lines about syncing and peers, in {len(s['groups'])} kinds"
             + (f" (the {len(gs)} most frequent here)" if len(s["groups"]) > len(gs) else "")
             + ". Addresses of other nodes are masked.")
    for g in gs:
        e = g["example"]
        span = utc(g["first"]) if g["count"] == 1 else f"{utc(g['first'])} to {utc(g['last'])}"
        L.append(f"- {g['count']}x `{g['level']} [{g['name']}] {mask(e['msg'])[:200]}` ({span})")
        if short < 1 and e["trace"]:
            L += ["", "  ```"] + ["  " + mask(x)[:200] for x in e["trace"]] + ["  ```"]
        elif short < 2 and e["trace"]:
            L.append(f"  - last line of its traceback: `{mask(e['trace'][-1])[:200]}`")
    L.append("")
    return L


def main(argv: list[str]) -> int:
    if argv[:1] == ["loop"]:
        import logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s nodelog %(message)s")
        while True:
            try:
                logging.info("kept %d lines", keep())
            except Exception as e:  # noqa: BLE001 - try again next hour
                logging.warning("not kept: %s", e)
            time.sleep(EVERY)
    days = float(argv[0]) if argv and re.match(r"^\d+(\.\d+)?$", argv[0]) else 7
    t1 = time.time()
    s = summary(t1 - days * 86400, t1)
    if s is None:
        print(f"node log: not readable here (no container '{SERVICE}' under {LOG_DIR})")
        return 1
    print("\n".join(section(s)) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
