"""Personal rules in numbers, across chain restarts (tauhud.com/rules/numbers/).

Since IDNI main 5ad1bb7 every account may hold its own personal rule (an o5 clause). The relay already asks the node,
every few minutes, which accounts hold one (relay.py poll_rules, GET /rules). This module sorts the rules in force by
what they check and writes one line per UTC day, so the page can show how rules grow over time. A testnet restart wipes
the chain and every rule with it; what is written per day stays.

What a rule checks is read from its Tau text (kinds below), never guessed: the reader is the same parser the playground
uses (rulefacts.py), and assets/rulekinds.js does the same in the browser; tests/rulekinds-cases.json holds the answers
both must give.

  cap      a most per payment: compares the amount (i1) with a fixed number, outside a co-signer condition
  only     only to certain recipients: reads the recipient (i4)
  time     a time lock: reads the block time (i5)
  cosign   a second signature: reads a co-signer slot (i18 to i25)
  reserve  keeps a reserve: reads the balance at the block before (i2)
  freeze   nothing leaves: blocks every payment (the wallet's freeze, old or new text)
  other    reads something else (custom inputs from i26, the fee i3), or none of the above

A rule can be several kinds at once (four-eyes with a reserve is cosign + reserve). Who holds it:

  people   every account that is not ours and not IDNI's
  ours     our own server's wallets: the showcase wallets, the island bot and its purses, cruise passengers, No Memo's
           and the hack of the week's (relay.simulated() + walletdays bots)
  idni     one of the accounts the testnet started with (txsources.GENESIS)

The day file keeps counts only, plus each holder's rule text from the last check (public in the blocks anyway), so that
"new" and "gone" can be told apart from "unchanged".
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

import rulefacts

log = logging.getLogger("relay.ruledays")

KINDS = ("cap", "only", "time", "cosign", "reserve", "freeze", "other")
WHO = ("people", "ours", "idni")
# where a rule came from (relay.rule_origin): the app its rule transaction (own rule or accepted offer) was sent through,
# else "uses" (sent elsewhere or before the kept blocks, by a wallet that uses our apps), "elsewhere" (sent elsewhere by a
# wallet we know no app of), "unknown" (older than the kept blocks, wallet unknown to our apps). Counts only, never keys.
FROM = ("tauhud", "rabbit", "nomemo", "agorzilla", "deja", "uses", "elsewhere", "unknown")
KEEP_DAYS = 400
COSIGN = {f"i{n}" for n in range(18, 26)}
KNOWN = {"i1", "i2", "i4", "i5"} | COSIGN


def day_of(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def flat(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def _streams(n: dict) -> set:
    out, todo = set(), [n]
    while todo:
        k = todo.pop()
        if k.get("kind") == "stream":
            out.add(k["name"])
        todo.extend(k.get("kids") or [])
    return out


def _cmps(n: dict, up: list):
    """Every comparison on an input, with the chain of nodes above it."""
    if n.get("kind") == "cmp":
        if any(s[0] == "i" for s in _streams(n)):
            yield n, up
        return
    for k in n.get("kids") or []:
        yield from _cmps(k, up + [n])


def kinds(text: str) -> dict:
    """{"kinds": [...], "size": comparisons on inputs} for one rule text. A text the reader cannot parse is "other"."""
    text = str(text or "").strip()
    if not re.match(r"always\b", text):   # the node answers a clause body without its "always ( … )." (getruleoffers)
        text = f"always ( {text} )."
    try:
        tree = rulefacts.parse(text)
    except Exception:
        return {"kinds": ["other"], "size": 0}
    cmps = list(_cmps(tree, []))
    reads = set().union(*(_streams(c) for c, _ in cmps)) if cmps else set()
    reads = {s for s in reads if s[0] == "i"}
    if not reads:   # the old freeze: o5 = 0 for every payment, reads nothing
        return {"kinds": ["freeze" if "o5" in _streams(tree) else "other"], "size": 0}
    if len(cmps) == 1 and reads == {"i1"}:
        c = cmps[0][0]
        a, b = c["kids"]
        if c.get("op") == ">" and a.get("kind") == "stream" and b.get("kind") == "const" and int(b.get("value") or 0) == 0:
            return {"kinds": ["freeze"], "size": 1}   # the wallet's freeze: any amount above 0 is blocked
    found = set()
    for c, up in cmps:
        s = {x for x in _streams(c) if x[0] == "i"}
        if s & COSIGN:
            found.add("cosign")
        if "i2" in s:
            found.add("reserve")
        if "i4" in s:
            found.add("only")
        if "i5" in s:
            found.add("time")
        if s == {"i1"}:
            # an amount threshold inside an "and" that also asks for a co-signer is the co-signer's limit, not a most
            inside = any(p.get("kind") == "and" and _streams(p) & COSIGN for p in up)
            if not inside:
                found.add("cap")
        if s - KNOWN:
            found.add("other")
    return {"kinds": [k for k in KINDS if k in found] or ["other"], "size": len(cmps)}


class RuleDays:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("RULEDAYS_PATH", "/data/ruledays.json")
        self.days: dict[str, dict] = {}
        self.last: dict[str, str] = {}     # holder -> flat rule text at the last check
        self.dirty = False
        try:
            with open(self.path) as f:
                st = json.load(f)
            self.days = {str(d): v for d, v in (st.get("days") or {}).items() if isinstance(v, dict)}
            self.last = {str(k): str(v) for k, v in (st.get("last") or {}).items()}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.warning("cannot read %s: %r; starting a new rule record", self.path, exc)

    def _day(self, now: float) -> dict:
        d = self.days.setdefault(day_of(now), {})
        for k in ("new", "gone", "held"):
            d.setdefault(k, {w: 0 for w in WHO})
        return d

    def held(self, w: str, now: float | None = None):
        """A payment our node refused because the sender's own rule said no (the wallet door's sendtx answer, or a
        showcase wallet's daily forbidden try). Only what passed our node: refusals at other nodes never reach us."""
        self._day(time.time() if now is None else now)["held"][w if w in WHO else "people"] += 1
        self.dirty = True

    def record(self, bodies: dict, checked, who, now: float | None = None, balances: dict | None = None, origin=None) -> dict:
        """One check of the node: bodies = {holder: rule text} in force now, checked = every account asked (an account
        not asked this time keeps its last state), who(pk) -> people/ours/idni, origin(pk) -> one of FROM. Writes today's
        numbers; returns them."""
        now = time.time() if now is None else now
        d = self._day(now)
        for pk, body in bodies.items():
            if self.last.get(pk) != flat(body):
                d["new"][who(pk)] += 1
                if origin is not None:
                    nf = d.setdefault("new_from", {w: {c: 0 for c in FROM} for w in WHO})
                    c = origin(pk)
                    nf[who(pk)][c if c in FROM else "unknown"] += 1
                self.last[pk] = flat(body)
        for pk in [p for p in checked if p in self.last and p not in bodies]:
            d["gone"][who(pk)] += 1
            del self.last[pk]
        d.update(self.snapshot(bodies, who, balances, origin))
        d["at"] = round(now)
        self.dirty = True
        return d

    @staticmethod
    def snapshot(bodies: dict, who, balances: dict | None = None, origin=None) -> dict:
        """Rules in force by kind and holder; with balances ({holder: test AGRS}), the AGRS those wallets hold; with
        origin(pk), where each rule in force came from (FROM)."""
        kinds_by = {w: {k: 0 for k in KINDS} for w in WHO}
        frm = {w: {c: 0 for c in FROM} for w in WHO}
        holders = {w: 0 for w in WHO}
        agrs = {w: 0 for w in WHO}
        for pk, body in bodies.items():
            w = who(pk)
            holders[w] += 1
            agrs[w] += int((balances or {}).get(pk) or 0)
            for k in kinds(body)["kinds"]:
                kinds_by[w][k] += 1
            if origin is not None:
                c = origin(pk)
                frm[w][c if c in FROM else "unknown"] += 1
        out = {"holders": holders, "kinds": kinds_by}
        if origin is not None:
            out["from"] = frm
        if balances is not None:
            out["agrs"] = agrs
        return out

    def restart(self, now: float | None = None):
        """The testnet started over: every rule is gone with the old chain. Not counted as "gone" (nobody removed one);
        the day is marked, and every rule set again on the new chain counts as new."""
        self.last = {}
        self._day(time.time() if now is None else now)["restart"] = True
        self.dirty = True

    def save(self, now: float | None = None):
        if not self.dirty:
            return
        cut = day_of((time.time() if now is None else now) - KEEP_DAYS * 86400)
        for d in [d for d in self.days if d < cut]:
            del self.days[d]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"days": dict(sorted(self.days.items())), "last": self.last}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
            self.dirty = False
        except OSError as exc:
            log.warning("cannot write %s: %r", self.path, exc)

    def history(self) -> dict:
        return {"since": min(self.days) if self.days else None, "days": dict(sorted(self.days.items()))}


def offers(blocks: list[dict], height: int | None, offer_id, who, app=None) -> dict:
    """Rule offers in the kept blocks: made, accepted, rejected, expired, still open; per who made them.
    offer_id(offerer, recipient, text, expire) -> id or None (showcase.offer_id; None without blake3).
    app(tx, tx hash) -> which of our apps sent it, or None: then "apps" counts the offers made through each app, and
    "apps_accepted" the accepts sent through each (counts only)."""
    made: dict[str, tuple] = {}
    acc, rej = set(), set()
    out = {w: {"made": 0, "accepted": 0, "rejected": 0, "expired": 0, "open": 0} for w in WHO}
    if app is not None:
        for o in out.values():
            o["apps"], o["apps_accepted"] = {}, {}
    ids_ok = True
    for b in blocks:
        hs = b.get("tx_ids") or []
        for i, t in enumerate(b.get("transactions") or []):
            if not isinstance(t, dict):
                continue
            kind = t.get("tx_type")
            sender = str(t.get("sender_pubkey") or "").lower()
            if app is not None and kind in ("rule_offer", "rule_offer_accept"):
                a = app(t, str(hs[i] if i < len(hs) else t.get("tx_hash") or "").lower())
                if a:
                    d = out[who(sender)]["apps" if kind == "rule_offer" else "apps_accepted"]
                    d[a] = d.get(a, 0) + 1
            if kind == "rule_offer":
                to = str(t.get("recipient_pubkey") or "").lower()
                try:
                    exp = int(t.get("expire_at_height") or 0)
                    oid = offer_id(sender, to, str(t.get("rule_text") or ""), exp)
                except (TypeError, ValueError):
                    oid, exp = None, 0
                if oid is None:
                    ids_ok = False
                    oid = f"?{len(made)}"
                made[oid] = (who(sender), exp)
            elif kind == "rule_offer_accept":
                acc.add(str(t.get("offer_id") or "").lower())
            elif kind == "rule_offer_reject":
                rej.add(str(t.get("offer_id") or "").lower())
    for oid, (w, exp) in made.items():
        o = out[w]
        o["made"] += 1
        if oid in acc:
            o["accepted"] += 1
        elif oid in rej:
            o["rejected"] += 1
        elif not ids_ok:
            continue
        elif height is not None and exp and exp < height:
            o["expired"] += 1
        else:
            o["open"] += 1
    return {"by": out, "matched": ids_ok}
