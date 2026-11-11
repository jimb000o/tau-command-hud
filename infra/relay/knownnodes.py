"""Nodes we know by name: a peer ID that tauhud.com shows under its operator's name.

A known node is listed in KNOWN below with its peer ID, its name, the name its
heartbeat sends (report names allow no spaces) and the public addresses it
reports from. Three things are checked apart, and each only from real data:

- Reachable: tauhud.com opens a TCP connection to its P2P port every few
  minutes (`probe`, nothing is sent), and our node's peer book says whether it
  talked to that peer ID or heard of it from another peer.
- Reporting: its heartbeat (kit/heartbeat.py) reported within the community
  TTL. A report that names the known peer ID or the known name counts only from
  one of the node's own addresses; from anywhere else the relay refuses it, so
  nobody else can take the name.
- In sync: only a heartbeat report can say so, because only it carries a block
  hash: same hash at its height as ours and at most `lag` blocks below our
  head. The peer book's head is a height without a hash, so it can say
  "catching up" or "at our height", never "synced".

Nothing about the node is guessed: with no check yet, the state is "unknown".
"""
from __future__ import annotations

import asyncio
import time

KNOWN: dict[str, dict] = {
    "12D3KooWEafLrs7GSJjuBbrRtGXeCzMZcJZowHvpCcFXLyetuzTc": {
        "name": "Age of Chains",
        "report_name": "Age-of-Chains",
        "ips": ("2.29.161.201",),
        "p2p": ("2.29.161.201", 4001),
        "network": "tau-testnet-v2",
    },
}

PROBE_SECONDS = 300      # one TCP connect per known node every 5 minutes
PROBE_TIMEOUT = 5.0
PROBE_FRESH = 3 * PROBE_SECONDS   # a probe result older than this says nothing any more


def _fold(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def peer_of_name(name: str) -> str | None:
    """The known peer whose name (or report name) this is, spaces, dashes and case aside."""
    f = _fold(name)
    for pid, k in KNOWN.items():
        if f in (_fold(k["name"]), _fold(k["report_name"])):
            return pid
    return None


def check_report(name: str, peer: str | None, ip: str) -> tuple[str | None, str | None]:
    """(known peer ID or None, refusal or None) for a heartbeat report.

    A report that names a known node, by peer ID or by name, is that node's only
    from one of its addresses. A report naming one known node's peer ID and
    another's name is refused too."""
    by_name = peer_of_name(name)
    by_peer = peer if peer in KNOWN else None
    pid = by_peer or by_name
    if pid is None:
        return None, None
    if by_name and by_peer and by_name != by_peer:
        return None, "That name belongs to another node."
    if ip not in KNOWN[pid]["ips"]:
        return None, "That name is reserved."
    return pid, None


class Probe:
    """TCP connects to each known node's P2P port: is it reachable from the internet?"""

    def __init__(self):
        self.results: dict[str, dict] = {pid: {"ok": None, "at": None, "last_ok": None, "error": None} for pid in KNOWN}

    async def check(self, pid: str):
        host, port = KNOWN[pid]["p2p"]
        r = self.results[pid]
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), PROBE_TIMEOUT)
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
            r.update(ok=True, at=time.time(), error=None)
            r["last_ok"] = r["at"]
        except (OSError, asyncio.TimeoutError) as exc:
            r.update(ok=False, at=time.time(), error="timeout" if isinstance(exc, asyncio.TimeoutError) else exc.__class__.__name__)

    async def run(self):
        while True:
            await asyncio.gather(*(self.check(pid) for pid in KNOWN))
            await asyncio.sleep(PROBE_SECONDS)


def state(pid: str, peer_row: dict | None, report: dict | None, board_row: dict | None, probe: dict | None,
          agrees: str | None, ours: int | None, now: float, *, online_seconds: float, lag: int) -> dict:
    """Reachability and sync of one known node, each from its own evidence.

    peer_row: our node's peer-book row for its peer ID; report: its live
    community report (None once silent); board_row: its leaderboard row (the
    last report, even an old one); probe: the TCP probe result; agrees: how its
    reported head compares with our chain; ours: our canonical height."""
    k = KNOWN[pid]
    p2p_last = max((peer_row or {}).get("last_direct") or 0, 0) or None
    heard = (peer_row or {}).get("last_heard") or None
    p2p = {"talked": p2p_last, "heard": heard, "connected": bool((peer_row or {}).get("connected")),
           "online": bool(p2p_last and now - p2p_last < online_seconds)}
    pr = probe or {}
    port = {"open": pr.get("ok") if pr.get("at") and now - pr["at"] < PROBE_FRESH else None,
            "checked": round(pr["at"]) if pr.get("at") else None,
            "last_open": round(pr["last_ok"]) if pr.get("last_ok") else None,
            "error": pr.get("error"), "port": k["p2p"][1]}
    rep = {"live": report is not None, "last": round(board_row["last_seen"]) if board_row else None}

    if port["open"] or p2p["online"] or rep["live"]:
        reach = "online"
    elif port["open"] is False or p2p_last or heard or rep["last"]:
        reach = "offline"
    else:
        reach = "unknown"

    sync = {"state": "unknown", "height": None, "ours": ours, "behind": None, "source": None}
    if report is not None:
        h = int(report["height"])
        sync.update(height=h, source="report")
        if ours is not None:
            sync["behind"] = max(0, ours - h)
        if agrees == "different":
            sync["state"] = "other_chain"
        elif agrees == "ahead":
            sync["state"] = "ahead"
        elif agrees == "same" and ours is not None and ours - h <= lag:
            sync["state"] = "synced"
        elif ours is not None and ours - h > lag:
            sync["state"] = "catching_up"
    elif peer_row and peer_row.get("head") is not None and p2p["online"]:
        h = int(peer_row["head"])
        sync.update(height=h, source="p2p")
        if ours is not None:
            sync["behind"] = max(0, ours - h)
            sync["state"] = "catching_up" if ours - h > lag else "at_height"

    seen = [x for x in ((peer_row or {}).get("first_seen"), (board_row or {}).get("first_seen"), pr.get("last_ok")) if x]
    return {"peer": pid, "name": k["name"], "report_name": k["report_name"], "network": k["network"],
            "reach": reach, "port": port, "p2p": p2p, "report": rep, "sync": sync,
            "first_seen": round(min(seen)) if seen else None}
