"""What a testnet restart brought: when Tau Testnet Alpha starts over from block 0, the restart post (alerts.py) says
what is new on the new chain, not only that it restarted (13 November 2026: the restart that gave every account its
own personal rule went out as "balances, rules and history begin again", which told nobody anything).

devpulse.py calls step() on every pass and wakes for a new restart within a minute (it naps in one-minute steps and
asks the relay's /uptime): the first pass after a restart fetches IDNI's code, lets the news line write its headlines,
and then sends the language model once:
  - every headline our news line wrote for IDNI's changes since the chain before started (with its tip), and
  - how the starting state differs: the genesis files of tau-testnet main at the previous restart and now.
The answer counts only when it passes the checks of the daily IDNI post (no number the input does not hold, no blame
or hype wording); otherwise the restart post stays the short one. alerts.py holds a restart post back for
RESTART_BRIEF_WAIT_MINUTES at most while it waits for this, then posts it either way.

  /state/devpulse/restart.json   {"at", "written", "status": ready|plain|failed, "title", "points", "why", "x_text"}
  python devpulse.py --restart     what the post for the newest restart would say now (one model call, nothing posted)
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone

log = logging.getLogger("restart_brief")

STATE = os.environ.get("RESTART_BRIEF_PATH", "/state/devpulse/restart.json")
WAIT = float(os.environ.get("RESTART_BRIEF_WAIT_MINUTES", 45)) * 60   # alerts.py: how long a restart post waits for it
MATCH = 6 * 3600          # a brief belongs to a restart seen within this time of it
FALLBACK_DAYS = 14        # without a known previous restart, the changes of this many days


def load() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            j = json.load(f)
        return j if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


def save(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)


def when(r: dict) -> int:
    return int(r.get("new_block1_ts") or r.get("at") or r.get("detected_at") or 0)


def newest(restarts: list[dict]) -> tuple[dict | None, int | None]:
    """The newest restart the relay knows, and when the one before it began (None when it does not know one)."""
    rs = sorted((r for r in restarts or [] if when(r)), key=when)
    if not rs:
        return None, None
    return rs[-1], (when(rs[-2]) if len(rs) > 1 else None)


# ---------- what the model reads ----------
def _git(path: str, *a: str) -> str:
    return subprocess.run(["git", "-C", path, *a], check=True, capture_output=True, text=True, timeout=300).stdout


def _short(v, cap: int = 160) -> str:
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= cap else s[:cap] + "…"


def genesis_lines(path: str, branch: str, before: int) -> list[str]:
    """How the starting state on tau-testnet main differs now from main at `before` (the previous restart): block 0,
    the accounts, the consensus settings and the rule texts, as short plain lines."""
    try:
        old = _git(path, "rev-list", "-1", "--first-parent", f"--before=@{before}", branch).strip()
        names = [n for n in _git(path, "ls-tree", "-r", "--name-only", branch, "networks").split() if n.endswith("genesis.json")]
    except subprocess.CalledProcessError:
        return []
    out = []
    for n in names:
        try:
            b = json.loads(_git(path, "show", f"{branch}:{n}"))
        except (subprocess.CalledProcessError, ValueError):
            continue
        try:
            a = json.loads(_git(path, "show", f"{old}:{n}")) if old else None
        except (subprocess.CalledProcessError, ValueError):
            a = None
        if a == b:
            continue
        if a is None:
            out.append(f"{n}: new file (no starting state for this network before)")
            continue
        lines = [f"{n} (starting state before -> now):"]
        for k in sorted(set(a) | set(b)):
            va, vb = a.get(k), b.get(k)
            if va == vb or k == "block_0":
                continue
            if k == "accounts_state" and isinstance(va, dict) and isinstance(vb, dict):
                lines.append(f"- accounts at the start: {len(va)} -> {len(vb)}; "
                             f"coins at the start: {sum(x for x in va.values() if isinstance(x, (int, float)))} -> "
                             f"{sum(x for x in vb.values() if isinstance(x, (int, float)))}")
            elif isinstance(va, dict) and isinstance(vb, dict):
                for s in sorted(set(va) | set(vb)):
                    if va.get(s) != vb.get(s):
                        lines.append(f"- {k}.{s}: {_short(va.get(s)) if s in va else '(not set)'} -> {_short(vb.get(s)) if s in vb else '(removed)'}")
            elif isinstance(va, str) and isinstance(vb, str) and ("\n" in va or "\n" in vb):
                diff = "\n".join(difflib.unified_diff(va.splitlines(), vb.splitlines(), lineterm="", n=1))
                lines.append(f"- {k} changed:\n{diff[:2500]}")
            else:
                lines.append(f"- {k}: {_short(va)} -> {_short(vb)}")
        out += lines
    return out


def heads_of(news: dict, start: int, end: int) -> list[dict]:
    """The news line's headlines for IDNI's changes written between two times, oldest first."""
    return sorted((i for i in news.get("items") or [] if start <= (i.get("ts") or 0) <= end), key=lambda i: i["ts"])


SYSTEM = """You write the post that tells the Telegram channel and the X account of Tau HUD (tauhud.com), an unofficial \
community dashboard for Tau Testnet Alpha made by people not affiliated with IDNI (the team that builds Tau), that the \
Tau Net testnet has started over from block 0. Readers are the Tau community and the IDNI team: curious people, node runners, \
testers; many never read code.

You get the headlines our news line wrote for IDNI's changes to the testnet's code since the chain before this one \
started (each written from the change's own diff, with a one-line tip), and how the starting state (the genesis) of \
the testnet differs from the one before. A restart on Tau Testnet Alpha means the chain starts again from block 0: \
balances, rules and history begin again from the starting state.

Write ONE post that says what the new chain brings: the few changes that matter most to someone using the testnet or \
running a node, and why it matters. Rules:
- Only facts the input shows. Never guess why IDNI restarted, dates, releases or effects the input does not show. \
Never say the restart was needed for a change unless the input says so; say what is new on the new chain.
- Lead with what people can do or will notice now (a new capability, a changed limit, new accounts or coins at the \
start); fixes and internal work at most in one point.
- Say what works now, not that anyone gained power. Write "again", "no longer" or "now" only when the input says how it \
was before.
- Credit IDNI plainly ("IDNI restarted the testnet with ..."). Never blame or criticise anyone.
- Plain words. No code names, file names, stream names, flags, commit hashes or version numbers; no names of people.
- Names: the network is Tau Net and its test network is the Tau Net testnet (Tau Testnet Alpha); never call the \
network just "Tau". Tau Language is the language rules are written in, and the Tau engine checks them.
- No hype or marketing words (huge, major, game-changing, finally, exciting, breakthrough), no price talk, no \
exclamation marks, no emoji.
- post: false when the input shows nothing new that someone using the testnet would notice (then the short restart \
note goes out instead).

Fields (English only):
- title: at most 90 characters, starting with "The Tau Net testnet restarted" and naming the biggest change, e.g. \
"The Tau Net testnet restarted with a personal rule for every account".
- points: two to four short points, each at most 160 characters, most important first.
- why: one sentence, at most 200 characters: why this matters.
- x_text: one or two sentences, at most 200 characters, for X: the gist, no link, no hashtag.
- reason: a few words why (not published).

Answer with JSON only, no other text:
{"post":true,"title":"","points":[""],"why":"","x_text":"","reason":""}"""


def prompt_of(heads: list[dict], gen: list[str], at: int, prev: int | None) -> str:
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"The testnet started over at {day(at)}." + (f" The chain before started at {day(prev)}." if prev else "")]
    if heads:
        parts.append("Our news line's headlines for IDNI's changes since then, oldest first:\n" + "\n".join(
            f"- {(h.get('headline') or {}).get('en', '')} ({(h.get('tip') or {}).get('en', '')})" for h in heads))
    else:
        parts.append("Our news line has no headlines for IDNI's changes since then.")
    parts.append("How the starting state differs:\n" + ("\n".join(gen) if gen else "(no difference found, or not readable)"))
    return "\n\n".join(parts)[:60000]


def ask(prompt: str) -> dict:
    import ai_meter
    import devpulse as dp
    import urllib.request
    body = json.dumps({"model": dp.NEWS_AI_MODEL, "max_tokens": 1200, "system": SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": dp.NEWS_AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.load(r)
    ai_meter.meter("restart", dp.NEWS_AI_MODEL, j.get("usage"))
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


def write(heads: list[dict], gen: list[str], at: int, prev: int | None, now: int, ask_=None) -> dict:
    """One brief: ready (the post says it), plain (the model saw nothing new; the short post goes out), check (numbers
    or wording the checks hold back: the short post goes out, the text stays here for a look)."""
    import idni_digest as idg
    d = {"at": at, "prev": prev, "written": now, "heads": len(heads), "gen": len(gen)}
    if not heads and not gen:
        return {**d, "status": "plain", "reason": "nothing to read"}
    prompt = prompt_of(heads, gen, at, prev)
    out = (ask_ or ask)(prompt)
    pts = [p for p in (idg.line(x, 200) for x in (out.get("points") or [])[:4]) if p]
    d.update(title=idg.line(out.get("title"), 100), points=pts, why=idg.line(out.get("why"), 240),
             x_text=idg.line(out.get("x_text"), 240), reason=idg.line(out.get("reason"), 300))
    if not out.get("post"):
        return {**d, "status": "plain"}
    if not (d["title"] and pts and d["why"] and d["x_text"]) or not d["title"].startswith("The Tau Net testnet restarted"):
        return {**d, "status": "plain", "reason": "the answer misses a field: " + (d.get("reason") or "")}
    d["check"] = idg.check_text([d["title"], *pts, d["why"], d["x_text"]], prompt)
    d["status"] = "check" if d["check"]["unknown_numbers"] or d["check"]["wording"] else "ready"
    return d


def step(restarts: list[dict], tn_path: str | None, branch: str, news: dict, now: int, ask_=None) -> dict | None:
    """Called by devpulse after the news line: writes the brief of the newest restart once. Returns its state."""
    import devpulse as dp
    r, prev = newest(restarts)
    st = load()
    if not r or not tn_path:
        return st or None
    at = when(r)
    if st.get("at") == at and st.get("status") in ("ready", "plain", "check"):
        return st
    if now - at > MATCH:   # an old restart (first start, or found late): nothing to post about any more
        return st or None
    if not dp.NEWS_AI_KEY:
        return st or None
    if st.get("at") == at and now - st.get("failed_at", 0) < 600:
        return st
    start = prev if prev else at - FALLBACK_DAYS * 86400
    try:
        d = write(heads_of(news, start, now), genesis_lines(tn_path, branch, start), at, prev, now, ask_)
    except Exception as e:  # noqa: BLE001 - the restart post goes out short after its wait; tried again in 10 minutes
        log.warning("restart brief: %s", e)
        d = {"at": at, "status": "failed", "failed_at": now, "error": str(e)[:200]}
    save(d)
    log.info("restart brief for %s: %s %s", at, d["status"], d.get("title") or "")
    return d


# ---------- alerts.py ----------
def for_restart(seen: float, st: dict | None = None) -> dict | None:
    """The finished brief for a restart alerts.py saw at `seen`, or None while there is none (yet)."""
    st = load() if st is None else st
    if st.get("status") not in ("ready", "plain", "check") or abs((st.get("at") or 0) - seen) > MATCH:
        return None
    return st


def apply(item: dict, b: dict) -> dict:
    """The restart post's fields with the brief in: its title, what is new, why it matters; the old chain's end and what
    it means for a test wallet stay as the facts."""
    if b.get("status") != "ready":
        return {}
    return {"headline": b["title"], "what": list(b["points"]), "what_title": "New on the new chain", "why": b["why"],
            "why_title": "Why it matters", "x_line": b["x_text"],
            "body": " ".join([b["why"], *b["points"], *(item.get("facts") or [])])}


def cli(restarts: list[dict], tn_path: str, branch: str, news: dict, now: int) -> int:
    r, prev = newest(restarts)
    if not r:
        print("no restart known to the relay")
        return 1
    at = when(r)
    start = prev if prev else at - FALLBACK_DAYS * 86400
    heads, gen = heads_of(news, start, now), genesis_lines(tn_path, branch, start)
    print(f"newest restart {datetime.fromtimestamp(at, timezone.utc):%a %d.%m. %H:%M UTC}: {len(heads)} headlines, "
          f"{len(gen)} lines on the starting state")
    d = write(heads, gen, at, prev, now)
    print(f"  {d['status']}" + (f" ({d.get('reason')})" if d.get("reason") else ""))
    if d.get("title"):
        print(f"\n🔄 {d['title']}\n" + "\n".join("• " + p for p in d["points"]) + f"\n\nWhy it matters: {d['why']}\n\nX: {d['x_text']}")
    if d.get("check") and (d["check"]["unknown_numbers"] or d["check"]["wording"]):
        print(f"\nheld back by the check: {d['check']}")
    print("\n(a preview: nothing was saved or posted)")
    return 0
