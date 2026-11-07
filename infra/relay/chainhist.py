"""Chain history across testnet restarts (tauhud.com/stats/, range "All chains"; tauhud.com/meta/ net view).

The relay holds only the current chain, and a testnet restart wipes it. This module writes down, per chain (one chain
per block 1: a restart on the same genesis seals a new block 1), what its blocks held per UTC hour and per UTC day, so
long-term charts keep growing across restarts instead of starting at zero each time. A chain ends when a block 1 with
another hash shows up; what was written for it stays as it was.

Reading the same blocks twice (relay restart, full refetch, reorg) changes nothing: a slot the relay still holds every
block of is counted again and replaced; a slot whose blocks were trimmed away keeps what was counted while they were
there. Chains that ended before this module existed come from the relay's restart log: how far they got, not what
their blocks held ("kept": "tip").

Each chain also keeps, frozen when it ends, the per-day counts the relay's /api/v1/sources gave for it (txsources.py
by_day), so those day series add up across restarts too (merge_sources).

GET /history
  fields     the counts in every slot row, in order (FIELDS)
  chains     [{n, start, end, first, tip, kept, current, senders, types, blocks, txs, transfers, volume}] oldest first;
             start / end = time of block 1 / of the newest block; tip = its height; kept = "full" (counted from block 1),
             "partial" (counted from block `first`) or "tip" (only the restart log remembers it)
  days       [[YYYY-MM-DD, chain n, *FIELDS]]  every recorded UTC day, one row per chain that had blocks that day
  hours      [[hour start, chain n, *FIELDS]]  the same per UTC hour, the last HOUR_DAYS days
  totals     {chains, blocks, txs, transfers, volume, counted_since}: blocks over every known chain (their tips);
             transactions only over the chains counted here, from counted_since on
"""
from __future__ import annotations

import calendar
import json
import logging
import os
import time

log = logging.getLogger("relay.chainhist")

# blocks; transactions; of them transfers / rule work / governance (as tauhud.com/stats/ colours them); transfer
# operations; test AGRS they moved; seconds between consecutive blocks summed, how many such gaps, the longest gap
FIELDS = ("blocks", "txs", "transfer", "rule", "gov", "transfers", "volume", "gap_sum", "gap_n", "gap_max")
HOUR_DAYS = 90
OBSERVE_SECONDS = 60
SOURCE_KEYS = ("days", "ours", "hours", "agorzilla", "starts", "rabbit")


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def height(b: dict) -> int:
    return _int((b.get("header") or {}).get("block_number")) or 0


def stamp(b: dict) -> int:
    return _int((b.get("header") or {}).get("timestamp")) or 0


def kind(t: dict) -> str:
    ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
    ty = str(t.get("tx_type") or "user_tx")
    if ty == "user_tx" and ops.get("0"):
        ty = "rule_deploy"
    return ty[:40]


def kind_group(ty: str) -> int:
    """Index in FIELDS of the colour group a transaction type counts under."""
    return 4 if ty.startswith("consensus_") else 3 if ty.startswith("rule_") else 2


def deep_add(a, b):
    """a + b for the nested count structures of txsources.by_day: numbers add, lists add element by element, dicts
    add key by key; anything else keeps a."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + b
    if isinstance(a, list) and isinstance(b, list):
        n = max(len(a), len(b))
        return [deep_add(a[i] if i < len(a) else 0, b[i] if i < len(b) else 0) for i in range(n)]
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_add(out[k], v) if k in out else v
        return out
    if a is None or a == 0:
        return b
    return a


def split_auto(src: dict) -> dict:
    """An earlier chain's frozen day counts, from before the relay kept the cruise ships and the island bot apart from
    White Rabbit Key's players (txsources AUTO): their transactions move out of "rabbit" into "cruise" and "bot" where the
    island's own counts know them (cruise, paid). The rivals' moves stay: a bot transaction can carry several, so the
    number of its transactions is not known."""
    days, isle = src.get("days"), src.get("rabbit") or {}
    if not isinstance(days, dict):
        return src
    out = dict(src)
    out["days"] = {}
    for day, row in days.items():
        if not isinstance(row, dict) or "cruise" in row or not isinstance(row.get("rabbit"), list):
            out["days"][day] = row
            continue
        row, r, z = dict(row), list(row["rabbit"]) + [0] * (5 - len(row["rabbit"])), isle.get(day) or {}
        c, ca, p, pa = (int(z.get(k) or 0) for k in ("cruise", "cruise_agrs", "paid", "paid_agrs"))
        r[0], r[4] = max(0, r[0] - c - p), max(0, r[4] - ca - pa)
        row["rabbit"], row["cruise"], row["bot"] = r, [c, 0, 0, 0, ca], [p, 0, 0, 0, pa]
        out["days"][day] = row
    return out


class ChainHistory:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("CHAINHIST_PATH", "/data/chainhist.json")
        self.chains: list[dict] = []
        self.observed_at = 0.0
        self.dirty = False
        try:
            with open(self.path) as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("chains"), list):
                self.chains = [c for c in data["chains"] if isinstance(c, dict) and c.get("id")]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting a new chain history", self.path, exc)

    # ---------- what is known ----------
    def find(self, cid: str) -> dict | None:
        return next((c for c in self.chains if c["id"] == cid), None)

    @property
    def current_id(self) -> str | None:
        cur = next((c for c in reversed(self.chains) if c.get("current")), None)
        return cur["id"] if cur else None

    def _renumber(self):
        self.chains.sort(key=lambda c: c.get("start") or 0)
        for i, c in enumerate(self.chains):
            c["n"] = i + 1

    def seed(self, restarts: list[dict]):
        """Chains that ended before this module counted them, from the relay's restart log (relay.py state)."""
        added = 0
        for r in restarts or []:
            old = (r or {}).get("old") or {}
            cid = old.get("block1_hash")
            if not cid or self.find(cid):
                continue
            self.chains.append({"id": cid, "start": old.get("block1_ts"), "end": old.get("tip_ts"),
                                "tip": old.get("tip"), "first": None, "kept": "tip", "days": {}, "hours": {}})
            added += 1
        if added:
            self._renumber()
            self.dirty = True
            self.save()

    # ---------- counting ----------
    def due(self, now: float | None = None) -> bool:
        return (time.time() if now is None else now) - self.observed_at >= OBSERVE_SECONDS

    def observe(self, blocks: list[dict], now: float | None = None, force: bool = False,
                sources: dict | None = None) -> bool:
        """Count the blocks the relay holds (oldest first) into their chain. `sources`: the chain's txsources.by_day
        output, kept with it (the relay passes it right before it drops a chain's blocks). True when a new chain began."""
        now = time.time() if now is None else now
        if not force and not self.due(now):
            return False
        self.observed_at = now
        blocks = sorted((b for b in blocks if height(b) >= 1 and stamp(b) > 0), key=height)
        b1 = next((b for b in blocks if height(b) == 1), None)
        if not b1 or not b1.get("block_hash"):
            return False   # without block 1 the chain cannot be told apart from the next one
        cid = str(b1["block_hash"])
        chain = self.find(cid)
        new = chain is None
        if new:
            chain = {"id": cid, "first": None, "days": {}, "hours": {}}
            self.chains.append(chain)
        for c in self.chains:
            c["current"] = c is chain
        # the run of consecutive heights that ends at the tip: every slot from its first block on is complete
        h0 = height(blocks[-1])
        held = {height(b) for b in blocks}
        while h0 - 1 in held:
            h0 -= 1
        cover = None if h0 <= 1 else stamp(next(b for b in blocks if height(b) == h0))
        days: dict[str, list] = {}
        hours: dict[str, list] = {}
        types: dict[str, int] = {}
        senders = set()
        prev = None
        for b in blocks:
            ts, h = stamp(b), height(b)
            day, hour = time.strftime("%Y-%m-%d", time.gmtime(ts)), str(ts - ts % 3600)
            rows = (days.setdefault(day, [0] * len(FIELDS)), hours.setdefault(hour, [0] * len(FIELDS)))
            add = [0] * len(FIELDS)
            add[0] = 1
            for t in b.get("transactions") or []:
                if not isinstance(t, dict):
                    continue
                ty = kind(t)
                types[ty] = types.get(ty, 0) + 1
                add[1] += 1
                add[kind_group(ty)] += 1
                s = t.get("sender_pubkey") or t.get("sender")
                if s:
                    senders.add(str(s))
                ops = t.get("operations") if isinstance(t.get("operations"), dict) else {}
                for x in ops.get("1") or []:
                    if isinstance(x, (list, tuple)) and len(x) >= 3:
                        add[5] += 1
                        add[6] += _int(x[2]) or 0
            if prev is not None and height(prev) == h - 1 and ts >= stamp(prev):
                gap = ts - stamp(prev)
                add[7], add[8], add[9] = gap, 1, gap
            for r in rows:
                for i in range(9):
                    r[i] += add[i]
                r[9] = max(r[9], add[9])
            prev = b
        for key, fresh, start in (("days", days, lambda k: _day_start(k)), ("hours", hours, lambda k: int(k))):
            kept = chain.setdefault(key, {})
            for k in [k for k in kept if (cover is None or start(k) >= cover) and k not in fresh]:
                del kept[k]   # a reorg moved its blocks elsewhere
            for k, v in fresh.items():
                old = kept.get(k)
                if cover is None or start(k) >= cover or old is None:
                    kept[k] = v
                else:   # some of this slot's blocks were trimmed: keep the larger count of each field
                    kept[k] = [max(a, b) for a, b in zip(old, v)]
        cut = now - HOUR_DAYS * 86400
        chain["hours"] = {k: v for k, v in chain["hours"].items() if int(k) >= cut - 3600}
        lowest = height(blocks[0])
        chain["first"] = lowest if chain.get("first") is None else min(chain["first"], lowest)
        chain["kept"] = "full" if chain["first"] <= 1 else "partial"
        chain["start"], chain["end"], chain["tip"] = stamp(b1), stamp(blocks[-1]), height(blocks[-1])
        chain["types"] = types if cover is None else {k: max(types.get(k, 0), (chain.get("types") or {}).get(k, 0))
                                                     for k in {*types, *(chain.get("types") or {})}}
        chain["senders"] = max(len(senders), chain.get("senders") or 0)
        if sources is not None:
            chain["sources"] = {k: sources.get(k) or {} for k in SOURCE_KEYS}
            chain["sources"]["since"] = sources.get("since")
        if new:
            self._renumber()
            log.info("chain history: chain %s began (block 1 %s…)", chain["n"], cid[:12])
        self.dirty = True
        self.save()
        return new

    # ---------- output ----------
    def history(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        chains, days, hours = [], [], []
        tot = {"chains": len(self.chains), "blocks": 0, "txs": 0, "transfers": 0, "volume": 0, "counted_since": None}
        for c in self.chains:
            sums = [0] * len(FIELDS)
            for v in (c.get("days") or {}).values():
                for i in range(len(FIELDS)):
                    sums[i] += v[i] if i < len(v) else 0
            row = {"n": c.get("n"), "start": c.get("start"), "end": c.get("end"), "first": c.get("first"),
                   "tip": c.get("tip"), "kept": c.get("kept"), "current": bool(c.get("current")),
                   "senders": c.get("senders"), "types": c.get("types") or {}}
            if c.get("kept") != "tip":
                row.update(blocks=sums[0], txs=sums[1], transfers=sums[5], volume=sums[6])
                tot["txs"] += sums[1]
                tot["transfers"] += sums[5]
                tot["volume"] += sums[6]
                if tot["counted_since"] is None and c.get("start"):
                    tot["counted_since"] = c["start"]
            tot["blocks"] += c.get("tip") or 0
            chains.append(row)
            days += [[d, c.get("n"), *v] for d, v in (c.get("days") or {}).items()]
            hours += [[int(h), c.get("n"), *v] for h, v in (c.get("hours") or {}).items()]
        days.sort(key=lambda r: (r[0], r[1]))
        hours.sort(key=lambda r: (r[0], r[1]))
        return {"generated_at": round(now), "fields": list(FIELDS), "hour_days": HOUR_DAYS,
                "chains": chains, "days": days, "hours": hours, "totals": tot}

    def merge_sources(self, current: dict) -> dict:
        """txsources.by_day of the current chain, with every earlier chain's frozen day counts added in. On a day a
        restart split, wallet counts of both chains are added, so a wallet active on both sides counts twice."""
        cur = self.current_id
        out = dict(current)
        n = 0
        for c in self.chains:
            src = c.get("sources")
            if not src or c["id"] == cur:
                continue
            src = split_auto(src)
            n += 1
            for k in SOURCE_KEYS:
                out[k] = deep_add(src.get(k) or {}, out.get(k) or {})
            if src.get("since") and (out.get("since") is None or src["since"] < out["since"]):
                out["since"] = src["since"]
        if n:
            for k in SOURCE_KEYS:
                out[k] = dict(sorted((out.get(k) or {}).items()))
            out["hours"] = {d: out["hours"][d] for d in sorted(out["hours"])[-31:]}
        out["chains"] = n + 1   # how many chains these day counts span, the current one included
        return out

    def save(self, force: bool = False):
        if not self.dirty and not force:
            return
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"chains": self.chains}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; chain history lives in memory only", self.path, exc)
                self._warned = True


def _day_start(day: str) -> int:
    return calendar.timegm(time.strptime(day, "%Y-%m-%d"))
