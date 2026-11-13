"""Road to mainnet links (tauhud.com/roadmap/): the IDNI issues and pull requests the page names, their state on GitHub,
and one private note to the owner when one of them changes.

The page's words never change by themselves (nothing on it is guessed), so when IDNI merges, closes or reopens
something an item links, the item's text may need a hand edit. Run by devpulse.py once an hour:

  - reads roadmap/index.html (mounted read-only at ROADMAP_PAGE) and collects, per item, its refs and every link to
    an IDNI/tau-testnet issue or pull request
  - asks GitHub for their state with a few list calls (IDNI's issues and pull requests, newest first), not one call
    per number; the result goes into devpulse.json as refs.states, so the page shows a chip on each link
    (merged, closed, open) without every visitor's browser asking GitHub
  - compares with the last pass (/state/devpulse/roadmap-links.json) and tells the owner privately, never the channel:
    "item X links #N, which IDNI merged: its text may need a look". The first pass only remembers. Between 22:00 and
    08:00 German time the note waits for the morning (as tickerwatch.py does).

  python roadmap_watch.py status   the links and their stored state
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

log = logging.getLogger("roadmap_watch")

REPO = "IDNI/tau-testnet"
PAGE = os.environ.get("ROADMAP_PAGE", "/roadmap/index.html")
STATE = os.environ.get("ROADMAP_WATCH_PATH", "/state/devpulse/roadmap-links.json")
SITE = "https://tauhud.com/roadmap/"
UA = {"User-Agent": "tauhud-devpulse/1 (+https://tauhud.com)", "Accept": "application/vnd.github+json"}
PAGES = 6            # 100 issues and pull requests a page, newest first: IDNI has about 110 in all (12.11.2026)
QUIET = (22, 8)      # German time: no private message from 22:00 to 08:00
BERLIN = ZoneInfo("Europe/Berlin")
WORD = {"merged": "merged", "closed": "closed", "not_planned": "closed as not planned", "open": "open"}


# ---------------- the page ----------------

def items(text: str) -> list[dict]:
    """The page's ITEMS, as far as this needs them: id, title, refs and the IDNI issues and pull requests it links."""
    out = []
    a = text.find("const ITEMS = [")
    if a >= 0:
        b = text.find("\n];", a)
        text = text[a:b if b > a else len(text)]
    starts = [m.start() for m in re.finditer(r'\{\s*id:\s*"', text)]
    for i, a in enumerate(starts):
        chunk = text[a:starts[i + 1] if i + 1 < len(starts) else len(text)]
        m = re.match(r'\{\s*id:\s*"([\w-]+)"', chunk)
        if not m:
            continue
        t = re.search(r'title:\s*"((?:[^"\\]|\\.)*)"', chunk)
        r = re.search(r"refs:\s*\[([\d,\s]*)\]", chunk)
        refs = [int(x) for x in re.findall(r"\d+", r.group(1))] if r else []
        links = sorted({int(n) for n in re.findall(r"\$\{IDNI\}/(?:issues|pull)/(\d+)\b", chunk)})
        out.append({"id": m.group(1), "title": t.group(1) if t else m.group(1), "refs": refs, "links": links})
    return out


def wanted(its: list[dict]) -> dict[int, list[dict]]:
    """Each IDNI number the page names, with the items that name it."""
    w: dict[int, list[dict]] = {}
    for it in its:
        for n in sorted(set(it["refs"]) | set(it["links"])):
            w.setdefault(n, []).append({"id": it["id"], "title": it["title"]})
    return w


# ---------------- GitHub ----------------

def _get(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def state_of(j: dict) -> dict:
    pr = isinstance(j.get("pull_request"), dict)
    if pr and j["pull_request"].get("merged_at"):
        s = "merged"
    elif j.get("state") == "closed":
        s = "not_planned" if j.get("state_reason") == "not_planned" else "closed"
    else:
        s = "open"
    return {"state": s, "pr": pr}


def fetch(nums: set[int], get=_get) -> dict[int, dict]:
    """State of each number, from IDNI's issue list (pull requests included), newest first, until all are found."""
    found: dict[int, dict] = {}
    for page in range(1, PAGES + 1):
        rows = get(f"https://api.github.com/repos/{REPO}/issues?state=all&sort=created&direction=desc&per_page=100&page={page}")
        if not rows:
            break
        for j in rows:
            n = j.get("number")
            if n in nums:
                found[n] = state_of(j)
        if nums <= set(found) or min((j.get("number") or 0) for j in rows) <= min(nums):
            break
    return found


# ---------------- the owner ----------------

def quiet(now: float) -> bool:
    h = dt.datetime.fromtimestamp(now, BERLIN).hour
    return h >= QUIET[0] or h < QUIET[1]


def _tell(text: str) -> tuple[bool, str]:
    import tickerwatch
    return tickerwatch.tell(text)


def note(changes: list[dict]) -> str:
    lines = ["Road to mainnet: IDNI changed something the page links. The page's words do not change by themselves, "
             "so these items may need a look:"]
    for c in changes:
        kind = "pull request" if c.get("pr") else "issue"
        now_ = "open again" if c["to"] == "open" else WORD.get(c["to"], c["to"])
        for it in c["items"]:
            lines.append(f"- {it['title']}: IDNI {kind} #{c['n']} is now {now_} (was {WORD.get(c['from'], c['from'])}). "
                         f"{SITE}#{it['id']}")
    return "\n".join(lines)


def load() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(st: dict):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE)


def step(now: float, get=_get, tell=_tell) -> dict | None:
    """One pass: {n: {state, pr}} for devpulse.json refs.states, or None when the page or GitHub cannot be read."""
    try:
        with open(PAGE, encoding="utf-8") as f:
            w = wanted(items(f.read()))
    except OSError as e:
        log.info("roadmap page: %s", e)
        return None
    if not w:
        return None
    try:   # our own reports on the Findings page too: fixwatch.py learns from their state when IDNI solves one
        import fixwatch
        for n in fixwatch.numbers():
            w.setdefault(n, [])
    except Exception as e:  # noqa: BLE001
        log.info("findings numbers: %s", e)
    try:
        got = fetch(set(w), get)
    except Exception as e:  # noqa: BLE001 - rate limit or network: the last states stay, nothing is told
        log.info("roadmap links from GitHub: %s", e)
        return None
    st = load()
    old = st.get("states") or {}
    pending = st.get("pending") or []
    first = not old
    for n, s in sorted(got.items()):
        was = (old.get(str(n)) or {}).get("state")
        if not first and was and was != s["state"]:
            known = next((p["from"] for p in pending if p["n"] == n), was)   # what the owner last heard of it
            pending = [p for p in pending if p["n"] != n] + [{"n": n, "from": known, "to": s["state"], "pr": s["pr"], "items": w[n], "at": now}]
    pending = [p for p in pending if p["from"] != (got.get(p["n"]) or {}).get("state")   # changed back: nothing to say
               and p["items"]]   # a number only Findings names: fixwatch.py tells that one
    if pending and not quiet(now):
        ok, why = tell(note(pending))
        log.info("roadmap note to the owner %s", "sent" if ok else f"NOT sent ({why})")
        if ok:
            pending = []
    st.update(states={str(n): got[n] for n in sorted(got)}, pending=pending, at=now)
    save(st)
    return st["states"]


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "status":
        st = load()
        print(f"roadmap links: {len(st.get('states') or {})} checked" + (f", {len(st['pending'])} note(s) waiting for the morning" if st.get("pending") else ""))
        for n, s in sorted((st.get("states") or {}).items(), key=lambda x: int(x[0])):
            print(f"  #{n} {s['state']}{' (pull request)' if s.get('pr') else ''}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
