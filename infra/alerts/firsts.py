"""Firsts: the first time the real Tau testnet carries a kind of transaction nobody had used there before.

The testnet supports payments with terms (tau-testnet 539d1e2: retractable transfers, co-signed approvals, personal rules
that read the block time), but until someone uses them they are only promises in the docs. The first block that carries
one is news: one post on Telegram and X, and the HUD's "Money with terms" tile lights up with a link to that transaction.

alerts.py hands scan() the blocks it holds after each sync. Each kind is posted once per chain. Firsts that land close
together (someone trying several in a row) wait until QUIET seconds pass without another, or at most HOLD seconds, and go
out as one post. The first run is silent: what the chain already holds then is history, not news. A first whose block is
older than alerts.py's POST_MAX_AGE (a long outage) is recorded and shown on the HUD, never posted late.
"""
from __future__ import annotations

import html
import os
import re

SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
FIRSTS_ON = os.environ.get("FIRSTS", "true").lower() in ("1", "true", "yes")
QUIET = float(os.environ.get("FIRSTS_QUIET_SECONDS", 600))
HOLD = float(os.environ.get("FIRSTS_HOLD_SECONDS", 2700))

SLOT = re.compile(r"\bi(1[89]|2[0-5])\s*\[")   # the approval slots a co-signer's vote fills (docs/approvals.md)
CLOCK = re.compile(r"\bi5\s*\[")                # the block time, as consensus feeds it to a personal rule
POLICY = re.compile(r"\bo5\s*\[")               # the sender's own payment policy
NEUTRAL = "always((o5[t]:bv[24]={#x000001}:bv[24]))."


def rule_of(t: dict) -> str:
    ops = t.get("operations")
    r = ops.get("0") if isinstance(ops, dict) else None
    return r if isinstance(r, str) else ""


def own_rule(t: dict) -> str:
    """The text of a personal o5 rule this transaction sets, or "" (removing one with the neutral clause sets none)."""
    if (t.get("tx_type") or "user_tx") != "user_tx":
        return ""
    r = rule_of(t)
    return r if POLICY.search(r) and re.sub(r"\s+", "", r) != NEUTRAL else ""


# In the order they are told. `name` heads a single first; `line` is its sentence in a post.
KINDS = [
    ("returnable", lambda t: t.get("tx_type") == "retractable_transfer",
     "a returnable payment",
     "A returnable payment: the money waits in escrow, and its sender can still take it back until the release point."),
    ("taken_back", lambda t: t.get("tx_type") == "retract_transfer",
     "a payment taken back",
     "A payment taken back: its sender pulled a returnable payment back before it was released."),
    ("time_lock", lambda t: bool(CLOCK.search(own_rule(t))),
     "a rule that follows the clock",
     "A rule that follows the clock: an account set its own payment rule that depends on the time of the block."),
    ("cosign_rule", lambda t: bool(SLOT.search(own_rule(t))),
     "a co-signer rule",
     "A co-signer rule: an account set its own rule that some of its payments need a named co-signer."),
    ("cosign_request", lambda t: t.get("tx_type") == "approval_request",
     "a payment waiting for its co-signer",
     "A payment waiting for its co-signer: it goes through only once the co-signer approves."),
    ("cosign_vote", lambda t: t.get("tx_type") == "transfer_vote" and str(t.get("approve", True)).lower() != "false",
     "a co-signer's approval",
     "A co-signer approved a payment that waited for them."),
]
NAMES = {k: n for k, _, n, _ in KINDS}
LINES = {k: line for k, _, _, line in KINDS}


def fresh_state() -> dict:
    return {"chain": "", "seen": {}, "pending": [], "primed": False}


def ts_of(b: dict) -> int | None:
    try:
        return int((b or {}).get("header", {}).get("timestamp")) or None
    except (TypeError, ValueError):
        return None


def scan(st: dict, blocks: dict[int, dict], chain: str) -> list[dict]:
    """Record every kind's earliest transaction in `blocks`; returns the firsts that are new since the last scan.
    A new chain starts the record over. Kinds already seen keep their first transaction even when the blocks held
    later begin above it."""
    if st.get("chain") != chain:
        st["chain"], st["seen"], st["pending"] = chain, {}, []
    new = []
    left = [k for k, *_ in KINDS if k not in st["seen"]]
    for h in sorted(blocks):
        if not left:
            break
        b = blocks[h]
        ids = b.get("tx_ids") or []
        for i, t in enumerate(b.get("transactions") or []):
            if not isinstance(t, dict):
                continue
            for k, test, *_ in KINDS:
                if k in left and test(t):
                    f = {"key": k, "h": h, "ts": ts_of(b), "tx": ids[i] if i < len(ids) else None}
                    st["seen"][k] = f
                    left.remove(k)
                    new.append(f)
    return new


def take(st: dict, now: float, max_age: float) -> list[dict]:
    """The pending firsts that are due to be posted together (oldest first), removed from pending; [] while waiting.
    Firsts from blocks older than `max_age` are dropped from pending without a post."""
    pend = [f for f in st["pending"] if now - (f.get("ts") or now) <= max_age]
    st["pending"] = pend
    if not pend:
        return []
    newest = max(f["found"] for f in pend)
    oldest = min(f["found"] for f in pend)
    if now - newest < QUIET and now - oldest < HOLD:
        return []
    st["pending"] = []
    return sorted(pend, key=lambda f: [k for k, *_ in KINDS].index(f["key"]))


def headline(fs: list[dict]) -> str:
    if len(fs) == 1:
        n = NAMES[fs[0]["key"]]
        return "First on the testnet: " + n
    return "Firsts on the testnet: money with terms"


def telegram_text(fs: list[dict], real_line: str) -> str:
    e = html.escape
    out = [real_line, f"🆕 <b>{e(headline(fs))}</b>",
           "Tau Testnet Alpha carried these for the first time:" if len(fs) > 1 else "Tau Testnet Alpha carried this for the first time:", ""]
    for f in fs:
        where = (f'<a href="{e(SITE)}/explorer/?tx={e(f["tx"])}">block #{f["h"]:,}</a>' if f.get("tx")
                 else f'<a href="{e(SITE)}/explorer/?b={f["h"]}">block #{f["h"]:,}</a>')
        out.append(f"• {e(LINES[f['key']])} In {where}.")
    out += ["", "Until now these were only described in the testnet's code. Now they have happened on the chain.",
            "", f'<a href="{e(SITE)}/">Watch it on Tau HUD</a>']
    return "\n".join(out)


def x_lines(fs: list[dict]) -> list[str]:
    """For alerts.x_post: one first is told in full; several are listed by name, so all of them fit."""
    if len(fs) == 1:
        return ["🆕 " + headline(fs), f"{LINES[fs[0]['key']]} Block #{fs[0]['h']:,}."]
    return ["🆕 " + headline(fs)] + ["• " + NAMES[f["key"]] for f in fs]


def public(st: dict) -> dict:
    """What the HUD reads (proposals.json "firsts"): kind -> {h, ts, tx}."""
    return {k: {"h": f["h"], "ts": f.get("ts"), "tx": f.get("tx")} for k, f in st.get("seen", {}).items()}
