"""Road to mainnet, the weekly check (tauhud.com/roadmap/): once a week our server reads the page against what it
knows and sends the owner one private note, every week, also when all is well. Nothing on it is written by a model
and nothing is guessed; it only compares.

  - an item that says an issue "is still open" while every IDNI issue it rests on is closed or merged
  - an IDNI issue or pull request the page names that changed state since last week's check
  - an open IDNI issue filed by us (ROADMAP_OUR_LOGINS) that neither this page nor the Findings page names yet
  - a testnet restart this week whose date the page does not mention yet
  - what IDNI merged into main this week (the news line's headlines), to read next to the items
  - an open pull request of ours that changes this page ("Road to mainnet" in its title): the fix waiting for a merge

Items with a finding get flagged on the page ("our weekly check found something here that may be out of date"),
with the date of the check, until the page's text changes or the next check finds nothing. Run by devpulse.py
every pass; it acts once a week (Monday after 10:00 German time by default).

  python roadmap_review.py status   the last check
  python roadmap_review.py now      check now and send the note (also when it is not Monday)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

log = logging.getLogger("roadmap_review")

STATE = os.environ.get("ROADMAP_REVIEW_PATH", "/state/devpulse/roadmap-review.json")
WEEKDAY = int(os.environ.get("ROADMAP_REVIEW_WEEKDAY", 0))   # 0 = Monday
HOUR = int(os.environ.get("ROADMAP_REVIEW_HOUR", 10))        # German time; a fix pull request opened earlier that morning is named
OURS = [x.strip() for x in os.environ.get("ROADMAP_OUR_LOGINS", "jimb000o").split(",") if x.strip()]
OUR_REPO = os.environ.get("ROADMAP_OUR_REPO", "jimb000o/tau-command-hud")
BERLIN = ZoneInfo("Europe/Berlin")
SITE = "https://tauhud.com/roadmap/"
WEEK = 7 * 86400
STILL_OPEN = re.compile(r"\b(?:the|our) issue (?:#\d+ )?is still open\b", re.I)


def _get(url: str):
    import roadmap_watch as rw
    return rw._get(url)


def _tell(text: str) -> tuple[bool, str]:
    import tickerwatch
    return tickerwatch.tell(text)


# ---------------- the page ----------------

def texts(page: str) -> dict[str, str]:
    """Each item's own words (everything between its id and the next item), for the checks below."""
    out = {}
    a = page.find("const ITEMS = [")
    if a < 0:
        return out
    b = page.find("\n];", a)
    body = page[a:b if b > a else len(page)]
    starts = [m for m in re.finditer(r'\{\s*id:\s*"([\w-]+)"', body)]
    for i, m in enumerate(starts):
        out[m.group(1)] = body[m.start():starts[i + 1].start() if i + 1 < len(starts) else len(body)]
    return out


def day_words(ts: float) -> str:
    d = dt.datetime.fromtimestamp(ts, BERLIN)
    return f"{d.day} {d.strftime('%B')}"


def said(ts: float, page: str) -> bool:
    """The page names that day: "14 November", or "14 and 15 November"."""
    d = dt.datetime.fromtimestamp(ts, BERLIN)
    return bool(re.search(rf"\b{d.day}\b[\w ,]{{0,24}}?\b{d.strftime('%B')}\b", page))


# ---------------- the checks ----------------

def check(page: str, findings_nums: set[int], states: dict, last_states: dict, ours_open: list[dict],
          restarts: list[float], news: list[dict], prs: list[dict], now: float) -> dict:
    import roadmap_watch as rw
    its, words = rw.items(page), texts(page)
    named = set(findings_nums)
    for it in its:
        named |= set(it["refs"]) | set(it["links"])
    flags: dict[str, list[str]] = {}

    def flag(i, why):
        flags.setdefault(i, []).append(why)

    for it in its:
        st = [states.get(str(n), {}).get("state") for n in it["refs"]]
        if it["refs"] and all(s in ("closed", "merged") for s in st) and STILL_OPEN.search(words.get(it["id"], "")):
            flag(it["id"], "says an issue is still open, but IDNI closed " + ", ".join(f"#{n}" for n in it["refs"]))
        for n in sorted(set(it["refs"]) | set(it["links"])):
            was, now_ = (last_states.get(str(n)) or {}).get("state"), (states.get(str(n)) or {}).get("state")
            if was and now_ and was != now_:
                flag(it["id"], f"#{n} is now {rw.WORD.get(now_, now_)} (was {rw.WORD.get(was, was)})")
    missing = [i for i in ours_open if i["n"] not in named]
    week = [t for t in restarts if now - WEEK <= t <= now]
    unsaid = [t for t in week if not said(t, page)]
    if unsaid:
        flag("upgrades", "testnet restart on " + ", ".join(sorted({day_words(t) for t in unsaid})) + " is not on the page yet")
    merged = [n for n in news if now - WEEK <= (n.get("ts") or 0) <= now]
    return {"at": now, "page": hashlib.sha1(page.encode()).hexdigest()[:12], "flags": flags,
            "titles": {it["id"]: it["title"] for it in its}, "missing": missing,
            "restarts": sorted(week), "merged": [{"en": (n.get("headline") or {}).get("en", ""), "url": n.get("url", "")} for n in merged],
            "prs": prs}


def note(r: dict) -> str:
    when = dt.datetime.fromtimestamp(r["at"], BERLIN).strftime("%d.%m.")
    lines = [f"Road to mainnet, weekly check {when}"]
    if not r["flags"] and not r["missing"]:
        lines.append(f"All {len(r['titles'])} items still match what our server knows. Nothing to do.")
    for i, whys in r["flags"].items():
        lines.append(f"- {r['titles'].get(i, i)}: " + "; ".join(whys) + f". {SITE}#{i}")
    if r["missing"]:
        lines.append("Our open IDNI issues the page does not name yet:")
        lines += [f"- #{m['n']} {m['title']}" for m in r["missing"]]
    if r["merged"]:
        lines.append("IDNI merged into main this week (read next to the items):")
        lines += [f"- {m['en']}" for m in r["merged"][:6] if m["en"]]
    if r["prs"]:
        lines.append("A fix for the page is waiting, merge it: " + " ".join(p["url"] for p in r["prs"]))
    elif r["flags"] or r["missing"]:
        lines.append("A weekly review in the project opens a fix pull request for these; if none comes, paste this note into the project chat.")
    return "\n".join(lines)


# ---------------- GitHub ----------------

def ours_open(get=_get) -> list[dict]:
    out = []
    for who in OURS:
        for j in get(f"https://api.github.com/repos/IDNI/tau-testnet/issues?state=open&creator={who}&per_page=100") or []:
            if "pull_request" not in j:
                out.append({"n": j["number"], "title": " ".join(str(j.get("title") or "").split())[:140]})
    return sorted({m["n"]: m for m in out}.values(), key=lambda m: m["n"])


def fix_prs(get=_get) -> list[dict]:
    rows = get(f"https://api.github.com/repos/{OUR_REPO}/pulls?state=open&per_page=50") or []
    return [{"n": p["number"], "url": p["html_url"]} for p in rows if "road to mainnet" in str(p.get("title") or "").lower()]


# ---------------- state ----------------

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


def due(now: float, st: dict) -> bool:
    d = dt.datetime.fromtimestamp(now, BERLIN)
    if d.weekday() != WEEKDAY or d.hour < HOUR or d.hour >= 22:
        return False
    return now - (st.get("last") or {}).get("at", 0) >= 6 * 86400 and now - st.get("failed_at", 0) >= 7200


def public(st: dict, page: str | None) -> dict | None:
    """For devpulse.json refs.review: when the last check ran, and the items it flagged while the page is unchanged."""
    r = st.get("last")
    if not r:
        return None
    same = page is not None and hashlib.sha1(page.encode()).hexdigest()[:12] == r.get("page")
    return {"at": int(r["at"]), "flag": sorted(r["flags"]) if same else []}


def step(now: float, states: dict | None, news: list[dict], restarts: list[float], force: bool = False,
         get=_get, tell=_tell) -> dict | None:
    import roadmap_watch as rw
    st = load()
    try:
        with open(rw.PAGE, encoding="utf-8") as f:
            page = f.read()
    except OSError as e:
        log.info("roadmap page: %s", e)
        return None
    if states and (force or due(now, st)):
        try:
            import fixwatch
            fnums = fixwatch.numbers()
        except Exception:  # noqa: BLE001
            fnums = set()
        try:
            r = check(page, fnums, states, st.get("states") or {}, ours_open(get), restarts, news, fix_prs(get), now)
        except Exception as e:  # noqa: BLE001 - GitHub or network: try again in two hours
            log.warning("roadmap review: %s", e)
            st["failed_at"] = now
            save(st)
            return public(st, page)
        ok, why = tell(note(r))
        log.info("roadmap weekly note %s", "sent" if ok else f"NOT sent ({why})")
        st.update(last=r, states=states, sent=ok)
        save(st)
    return public(st, page)


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if len(argv) > 1 and argv[1] == "status":
        r = load().get("last")
        print(note(r) if r else "roadmap weekly check: not run yet")
        return 0
    if len(argv) > 1 and argv[1] == "now":
        import time
        import devpulse as dp
        import roadmap_watch as rw
        states = rw.load().get("states") or {}
        news = (dp.load_headlines().get("items") or [])
        out = step(time.time(), states, news, [float(r["at"]) for r in dp.restarts() if r.get("at")], force=True)
        print(note(load()["last"]) if load().get("last") else "no check (no states yet)")
        return 0 if out is not None else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
