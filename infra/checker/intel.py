"""Intel contracts for No Memo (tauhud.com/nomemo/): a wallet guarded by a personal rule the player has not seen.

The rule is dealt here, from a small family, out of the player's seed and a server secret, so it is never in the page:
  cap A        a transfer passes up to A              floor A      from A up
  band A B     from A to B                            hole A B     everything but A to B
  none         nothing passes: the clause that only says when to block (where a rule says nothing, the engine answers 0)
  above A      the clause that only says when to pass: above A it passes, at A and below it says nothing, so blocked
The amounts are round hundreds up to 20,000. Each probe is one transfer the real Tau engine on this server judges
with that rule (checker.py runs tau_sandbox.py, the engine /learn uses). The player names the behaviour, not the text:
"above 4,000" is named floor 4,100. The text is shown once the rule is named, given up, or the one-shot edge is sent.

POST /tau/intel  {"case": "<contract>", "seed": "<16 to 64 hex>", and one of}
  "probe": <amount>                       one transfer, judged by the engine     → {"ok", "pass", "round", "ms"}
  "final": <amount>                       the edge in one shot: it passes and one more does not
                                                                                 → {"ok", "pass", "edge", "round", "rule"}
  "name": {"kind", "a", "b"}              the player's guess, compared by behaviour → {"ok", "right", "round", "rule"?}
  "reveal": true                          giving up                              → {"ok", "rule", "round"}
  "lead": true                            one number from the rule, for the contracts that give one (LEADS):
                                          its first amount, "a"                  → {"ok", "lead", "round"}
With "rule" come "says" (what it lets through, in words) and "dealt" ({kind, a, b}, for the page's own words).
"round" changes when the server's secret does (INTEL_SECRET in .env; unset, a new one at each start of the checker,
and every rule is dealt anew): the page then starts the contract's probes over.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

MAX = (1 << 24) - 1          # an amount is 24 bits wide
TOP = 20000                  # the rules' amounts: round hundreds up to this
SECRET = (os.environ.get("INTEL_SECRET") or secrets.token_hex(32)).encode()
CASES = {                    # the rules each contract deals
    "i-cap": ("cap", "floor"),
    "i-edge": ("cap",),
    "i-band": ("band", "hole"),
    "i-blind": ("cap", "floor", "band", "hole", "none", "above"),
}
NAMES = ("cap", "floor", "band", "hole", "none")   # what a player may name
LEADS = ("i-band", "i-blind")   # contracts where the crew's lookout read one number in the rule: a window or a hole is
                                # found in a few probes around it, not by sweeping 20,000 amounts
SEED = re.compile(r"^[0-9a-f]{16,64}$")


class BadRequest(ValueError):
    pass


def _r(case: str, seed: str, what: str) -> int:
    return int.from_bytes(hmac.new(SECRET, f"{what}:{case}:{seed}".encode(), hashlib.sha256).digest(), "big")


def round_of(case: str, seed: str) -> str:
    return format(_r(case, seed, "round"), "x")[:8]


def deal(case: str, seed: str) -> dict:
    """The rule this seed gets for this contract: {kind, a, b}."""
    r = _r(case, seed, "rule")
    kinds = CASES[case]
    kind = kinds[r % len(kinds)]
    r //= len(kinds)
    if kind in ("band", "hole"):
        a = 100 * (1 + r % 150)                 # 100 to 15,000
        b = a + 100 * (5 + (r // 150) % 46)     # 500 to 5,000 wide, at most 20,000
        return {"kind": kind, "a": a, "b": b}
    return {"kind": kind, "a": 100 * (1 + r % (TOP // 100)), "b": None}


def passing(rule: dict) -> list:
    """The amounts a rule lets through, as sorted stretches (lo, hi)."""
    k, a, b = rule["kind"], rule.get("a"), rule.get("b")
    raw = {"cap": lambda: [(0, a)], "floor": lambda: [(a, MAX)], "band": lambda: [(a, b)],
           "hole": lambda: [(0, a - 1), (b + 1, MAX)], "none": lambda: [], "above": lambda: [(a + 1, MAX)]}[k]()
    out = []
    for lo, hi in sorted((max(0, lo), min(MAX, hi)) for lo, hi in raw):
        if lo > hi:
            continue
        if out and lo <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def passes(rule: dict, amount: int) -> bool:
    return any(lo <= amount <= hi for lo, hi in passing(rule))


def text(rule: dict) -> str:
    """The rule in Tau, as a personal rule of the testnet (o5: 1 passes, 0 blocks)."""
    k, a, b = rule["kind"], rule.get("a"), rule.get("b")
    i1, v = "i1[t]:bv[24]", (lambda n: f"{{ {n} }}:bv[24]")
    one, zero = "(o5[t]:bv[24] = { #x000001 }:bv[24])", "(o5[t]:bv[24] = { #x000000 }:bv[24])"
    cond = {"cap": f"({i1} <= {v(a)})", "floor": f"({i1} >= {v(a)})",
            "band": f"(({i1} >= {v(a)}) && ({i1} <= {v(b)}))", "hole": f"(({i1} < {v(a)}) || ({i1} > {v(b)}))"}
    if k in cond:
        return f"always ( {cond[k]} ? {one} : {zero} )."
    return f"always ( ({i1} > {v(a)}) -> {zero if k == 'none' else one} )."


def words(rule: dict) -> str:
    """What the rule lets through, in plain words."""
    s = passing(rule)
    if not s:
        return "nothing passes"
    if s == [(0, MAX)]:
        return "everything passes"
    part = lambda lo, hi: f"up to {hi:,}" if lo == 0 else f"{lo:,} or more" if hi == MAX else f"{lo:,} to {hi:,}"  # noqa: E731
    return "passes " + " and ".join(part(lo, hi) for lo, hi in s)


def _amount(v) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, str)) or not re.fullmatch(r"\d{1,8}", str(v).strip()):
        raise BadRequest("an amount is a whole number from 0 to 16,777,215")
    n = int(str(v).strip())
    if n > MAX:
        raise BadRequest("an amount is a whole number from 0 to 16,777,215")
    return n


def parse(data) -> dict:
    if not isinstance(data, dict):
        raise BadRequest("send a JSON object")
    case, seed = str(data.get("case", "")), str(data.get("seed", "")).lower()
    if case not in CASES:
        raise BadRequest("case must be one of " + ", ".join(CASES))
    if not SEED.match(seed):
        raise BadRequest("seed must be 16 to 64 hex characters")
    req = {"case": case, "seed": seed}
    if "probe" in data:
        req["probe"] = _amount(data["probe"])
    elif "final" in data:
        req["final"] = _amount(data["final"])
        if req["final"] >= MAX:
            raise BadRequest("the edge needs one more above it")
    elif "name" in data:
        g = data["name"] if isinstance(data["name"], dict) else {}
        kind = str(g.get("kind", "")).lower()
        if kind not in NAMES:
            raise BadRequest("name one of " + ", ".join(NAMES))
        a = _amount(g.get("a")) if kind != "none" else None
        b = _amount(g.get("b")) if kind in ("band", "hole") else None
        if b is not None and b < a:
            raise BadRequest("the second number is the top: it cannot be below the first")
        req["name"] = {"kind": kind, "a": a, "b": b}
    elif data.get("reveal") is True:
        req["reveal"] = True
    elif data.get("lead") is True:
        req["lead"] = True
    else:
        raise BadRequest("send one of probe, final, name, reveal or lead")
    return req


def steps_of(req: dict) -> list | None:
    """The engine run a request needs (as tau_sandbox steps), or None when it needs none."""
    if "probe" in req:
        return [{"i1": str(req["probe"])}]
    if "final" in req:
        return [{"i1": str(req["final"])}, {"i1": str(req["final"] + 1)}]
    return None


def o5_of(row: dict):
    try:
        return int(str((row.get("out") or {}).get("o5")).strip(), 0)
    except (TypeError, ValueError):
        return None


def answer(req: dict, run=None) -> dict:
    """The reply to one parsed request. run(spec, steps) is the engine: tau_sandbox.ask for a run question."""
    rule = deal(req["case"], req["seed"])
    out = {"ok": True, "round": round_of(req["case"], req["seed"])}
    shown = {"rule": text(rule), "says": words(rule), "dealt": rule}   # once named, given up or shot: the rule, its words, its numbers
    if "name" in req:
        right = passing(req["name"]) == passing(rule)
        return {**out, "right": right, **(shown if right else {})}
    if "reveal" in req:
        return {**out, **shown}
    if "lead" in req:
        return {**out, "lead": rule["a"] if req["case"] in LEADS else None}
    res = run(text(rule), steps_of(req))
    if not res or not res.get("ok"):
        return {"ok": False, "error": (res or {}).get("error") or "the engine gave no answer", "timeout": bool((res or {}).get("timeout")),
                "round": out["round"]}
    vals = [o5_of(row) for row in res.get("outputs") or []]
    if len(vals) != len(steps_of(req)) or any(v is None for v in vals):
        return {"ok": False, "error": "the engine's answer had no o5", "round": out["round"]}
    out["ms"] = res.get("ms")
    if "probe" in req:
        return {**out, "pass": vals[0] != 0, "agrees": (vals[0] != 0) == passes(rule, req["probe"])}
    p, q = vals[0] != 0, vals[1] != 0
    return {**out, "pass": p, "edge": p and not q, **shown,
            "agrees": p == passes(rule, req["final"]) and q == passes(rule, req["final"] + 1)}
