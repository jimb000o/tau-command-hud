"""Rule changes proposed by visitors of the simulation (GET /sim/propose).

Simulation mode on tauhud.com runs a made-up chain in every visitor's browser (assets/sim.js), the same for everyone
because it is a function of the clock. A visitor can write a rule change in the Playground and put it to the simulation:
this route checks it and registers it as a ballot in the shared vote store (simvotes.py, item "visitor:<id>"), with the
proposal itself in the item's meta. Every browser reads GET /sim/votes, so every browser inserts the same proposal at the
same block, everyone may vote on it for six minutes, and if more visitors said yes than no the simulated validators
vote it in and it takes effect for everyone ten minutes after it was proposed, the path a rule change takes on Tau.

Nothing here touches the real testnet. No free text reaches other visitors: the kinds and values are fixed, a rule text
may hold only Tau tokens, and the proposer is named by the word-list identity of the vote store.
"""
from __future__ import annotations

import os
import re
import secrets
import time
from urllib.parse import parse_qs

DAY = 86400
PACE = 8                     # seconds per simulated block (assets/sim.js PACE)
LEAD = 4                     # the proposal enters the chain four blocks (about 30 s) after it was sent
VOTE_BLOCKS = 45             # visitors vote for six minutes
ACTIVATE_BLOCKS = 75         # in force ten minutes after it was proposed, like the day's programme
OPEN_MAX = int(os.environ.get("SIM_PROPOSALS_OPEN_MAX", 3))       # at most this many visitor proposals open at once
PER_VOTER_DAY = int(os.environ.get("SIM_PROPOSALS_PER_VOTER", 3))
PER_IP_DAY = int(os.environ.get("SIM_PROPOSALS_PER_IP", 6))
DAY_MAX = int(os.environ.get("SIM_PROPOSALS_PER_DAY", 60))
VOTER = re.compile(r"^[0-9a-f]{32}$")
INDEX = re.compile(r"^\d{1,3}$")
KEY12 = re.compile(r"^[0-9a-f]{12}$")
RULE_MAX = 300
# a rule text may hold Tau tokens only: no comments, no words, so nothing but a rule can reach other visitors
RULE_TOKEN = re.compile(r"\s+|always\b|sbf\b|bv\b|t\b|[io]\d{1,2}\b|#x[0-9a-fA-F]{1,16}\b|#b[01]{1,64}\b|\d{1,20}\b"
                        r"|<->|->|&&|\|\||!=|<=|>=|<<|>>|[=<>!&|^+\-*/%'(){}\[\]:?.]")
KINDS = ("fee", "add", "remove", "quorum", "mode", "rule")


def rule_ok(text: str) -> str | None:
    """None if `text` is a network rule a visitor may propose, else the reason in plain words."""
    if not text or len(text) > RULE_MAX:
        return f"a rule of 1 to {RULE_MAX} characters"
    pos = 0
    while pos < len(text):
        m = RULE_TOKEN.match(text, pos)
        if not m or m.end() == pos:
            return "only Tau rule tokens: streams like o9[t], values like { #x00000c }:bv[24], operators and brackets"
        pos = m.end()
    body = " ".join(text.split())
    if not re.match(r"^always\s*\(.*\)\s*\.$", body) or body.count("always") != 1:
        return "one unit: always ( … ). with the final dot"
    depth = 0
    for c in body:
        depth += c in "([{"
        depth -= c in ")]}"
        if depth < 0:
            break
    if depth:
        return "brackets do not match"
    outs = re.findall(r"\bo(\d+)\[([^\]]*)\]", body)
    if not outs:
        return "sets no output stream, so it would change nothing"
    if any(step != "t" for _, step in outs):
        return "only the current step [t]"
    if any(n == "5" for n, _ in outs):
        return "o5 is each account's own transfer rule, not a network rule"
    return None


def head_at(t: float) -> int:
    """The simulated chain's height at time t, give or take one block (assets/sim.js seals block n at day start + 8 n ± 1 s)."""
    return int((t - (t // DAY) * DAY) // PACE)


class SimProps:
    def __init__(self, votes):
        self.votes = votes                                  # simvotes.SimVotes: the shared ballot store
        self.day = -1
        self.by_voter: dict[str, int] = {}
        self.by_ip: dict[str, int] = {}
        self.count = 0

    def _roll(self, now: float):
        day = int(now // DAY)
        if day != self.day:
            self.day, self.by_voter, self.by_ip, self.count = day, {}, {}, 0

    def open_items(self, now: float) -> list[dict]:
        out = []
        for item_id, item in self.votes.items.items():
            meta = item.get("meta") or {}
            if item_id.startswith("visitor:") and meta.get("activate_ts", 0) > now:
                out.append(item)
        return out

    def propose(self, q: dict[str, str], ip: str, now: float | None = None) -> dict:
        """Check a proposal and register its ballot. Returns {"ok": True, "item": …} or {"ok": False, "error": code, "why": words}."""
        now = time.time() if now is None else now
        self._roll(now)
        bad = lambda code, why: {"ok": False, "error": code, "why": why}
        voter, kind = q.get("voter", ""), q.get("kind", "")
        if not VOTER.match(voter) or kind not in KINDS:
            return bad("bad", "voter token or kind missing")
        ident = [q.get(k, "") for k in ("a", "b", "c")]
        if not all(INDEX.match(x) for x in ident):
            return bad("bad", "identity missing")
        value: object
        raw = q.get("value", "")
        if kind == "fee":
            if not re.fullmatch(r"\d{1,4}", raw) or not 1 <= int(raw) <= 1000:
                return bad("bad", "a base fee from 1 to 1000 AGRS")
            value = int(raw)
        elif kind == "add":
            value = None                                    # the chain admits its next free validator key
        elif kind == "remove":
            if not KEY12.match(raw):
                return bad("bad", "the first 12 hex digits of a validator key")
            value = raw
        elif kind == "quorum":
            if raw not in ("majority", "supermajority"):
                return bad("bad", "majority or supermajority")
            value = raw
        elif kind == "mode":
            if raw not in ("stake", "validator_set"):
                return bad("bad", "stake or validator_set")
            value = raw
        else:
            why = rule_ok(raw)
            if why:
                return bad("bad", why)
            value = " ".join(raw.split())
        if self.count >= DAY_MAX:
            return bad("full", "the simulation takes no more visitor proposals today; it starts over at 00:00 UTC")
        if self.by_voter.get(voter, 0) >= PER_VOTER_DAY or self.by_ip.get(ip, 0) >= PER_IP_DAY:
            return bad("rate", f"{PER_VOTER_DAY} proposals a day per visitor; the count starts over at 00:00 UTC")
        if len(self.open_items(now)) >= OPEN_MAX:
            return bad("busy", f"{OPEN_MAX} visitor proposals are already open; one closes within ten minutes")
        h = head_at(now)
        proposed_at = h + LEAD
        close_at, activate_at = proposed_at + VOTE_BLOCKS, proposed_at + ACTIVATE_BLOCKS
        d0 = (now // DAY) * DAY
        if d0 + activate_at * PACE > d0 + DAY - 120:
            return bad("late", "too close to midnight UTC, when the simulated chain starts over")
        pid = secrets.token_hex(6)
        meta = {"kind": kind, "value": value, "by": [int(x) for x in ident], "proposed_at": proposed_at, "close_at": close_at,
                "activate_at": activate_at, "activate_ts": d0 + activate_at * PACE, "proposer": voter[:8]}
        item_id = f"visitor:{pid}"
        if not self.votes.register(item_id, d0 + proposed_at * PACE, d0 + close_at * PACE, meta):
            return bad("full", "the simulation takes no more ballots today; it starts over at 00:00 UTC")
        self.count += 1
        self.by_voter[voter] = self.by_voter.get(voter, 0) + 1
        self.by_ip[ip] = self.by_ip.get(ip, 0) + 1
        return {"ok": True, "id": item_id, "meta": meta}

    def route(self, path: str, query: str, ip: str) -> dict | None:
        """The JSON answer for GET /sim/propose, or None for any other path."""
        if path != "/sim/propose":
            return None
        q = {k: v[0] for k, v in parse_qs(query, keep_blank_values=True).items() if v}
        return self.propose(q, ip)
