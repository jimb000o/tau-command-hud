"""The crew's ship log: one members-only post a week in the Tau HUD crew (Fourthwall memberships), written by itself.

Every Monday, after the weekly recap is drawn, alerts.py hands this module the week's numbers. compose() turns them,
the site's update log of the same seven days and the running costs into one post; Fourthwall posts it for paying
members only. Nothing in it is written by hand and nothing in it is secret: it gathers in one place what the
testnet and the site did that week, what the site cost, and how many are in the crew.

Fourthwall Open API (docs.fourthwall.com, read 13 November 2026): Basic auth with the shop's API user
(FOURTHWALL_API_USER / FOURTHWALL_API_PASS in infra/.env), base https://api.fourthwall.com,
GET /open-api/v1.1/memberships/tiers, GET /open-api/v1.1/memberships/posts?state=All,
POST /open-api/v1.1/memberships/posts/texts {attributes: {core: {title, description, liveAt}}, access: {type}, notifications: {enabled}}.
The docs do not say which format the description takes; the shop's editor writes HTML, so the post is plain HTML
paragraphs and links, and `up crewlog` shows a stored post's description so this can be checked.
"""
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = os.environ.get("FOURTHWALL_API_URL", "https://api.fourthwall.com/open-api/v1.1")
USER = os.environ.get("FOURTHWALL_API_USER", "")
PASS = os.environ.get("FOURTHWALL_API_PASS", "")
ON = os.environ.get("CREWLOG_ENABLED", "false").lower() in ("1", "true", "yes")
UPDATES_URL = os.environ.get("CREWLOG_UPDATES_URL", "https://tauhud.com/assets/updates.json")
COSTS_URL = os.environ.get("CREWLOG_COSTS_URL", "https://tauhud.com/assets/costs.json")
WEEK = 7 * 86400
MAX_UPDATES = 8
SKIP_TAGS = {"Crew", "Donations"}   # the site's own money pages: members already know them, the log shows what else changed
UA = "tauhud-crewlog/1"


def enabled() -> bool:
    """Credentials are there (posting weekly also needs CREWLOG_ENABLED)."""
    return bool(USER and PASS)


def _req(method: str, path: str, body: dict | None = None, timeout: int = 30):
    data = json.dumps(body).encode() if body is not None else None
    auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    r = urllib.request.Request(API + path, data=data, method=method,
                               headers={"Authorization": "Basic " + auth, "Accept": "application/json", "User-Agent": UA,
                                        **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _get_json(url: str):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def tiers() -> list[dict]:
    """The crew's tiers: [{id, name, members}] (two response shapes are documented; both are read)."""
    d = _req("GET", "/memberships/tiers")
    rows = d.get("tiers", []) if isinstance(d, dict) else (d or [])
    return [{"id": t.get("id"), "name": t.get("name", ""), "status": t.get("status", ""),
             "members": (t.get("statistics") or {}).get("membersCount"), "description": t.get("description", ""),
             "monthly": {c: (v or {}).get("amount") for c, v in (((t.get("variants") or {}).get("monthly") or {}).get("amounts") or {}).items()}}
            for t in rows if isinstance(t, dict)]


def posts(limit: int = 3) -> list[dict]:
    d = _req("GET", "/memberships/posts?state=All")
    return ((d or {}).get("posts", []) if isinstance(d, dict) else [])[:limit]


def error_text(exc: Exception) -> str:
    """An API error with what Fourthwall said about it (the body of a 4xx names the field), never the credentials."""
    body = ""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            body = ""
    return f"{exc}" + (f" · {body}" if body else "")


def members(ts: list[dict]) -> int | None:
    n = [t["members"] for t in ts if isinstance(t.get("members"), int)]
    return sum(n) if n else None


# ---------------- the words ----------------
def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()


def week_updates(updates: list | None, start: float, end: float, site: str) -> list[tuple[str, str]]:
    """The update log's entries of the seven days (by their date), newest first: [(text, link)]."""
    a = datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%d")
    b = datetime.fromtimestamp(end - 1, timezone.utc).strftime("%Y-%m-%d")
    out = []
    for e in reversed(updates or []):
        if not isinstance(e, dict) or not (a <= str(e.get("on", "")) <= b) or e.get("tag") in SKIP_TAGS:
            continue
        text = _plain(e.get("html", ""))
        if not text:
            continue
        link = str(e.get("link") or "")
        link = link if link.startswith("https://") else (site + link if link.startswith("/") else site + "/")
        out.append((text if len(text) <= 240 else text[:237].rsplit(" ", 1)[0] + "…", link))
    return out


def month_costs(costs: dict | None) -> list[str]:
    """The monthly bills, summed per currency, as written in costs.json (no exchange rate, nothing estimated)."""
    sums = {}
    for i in (costs or {}).get("items", []):
        if isinstance(i, dict) and isinstance(i.get("amount"), (int, float)):
            sums[i.get("cur", "")] = sums.get(i.get("cur", ""), 0) + i["amount"]
    sign = {"EUR": "€", "USD": "$"}
    return [f"{sign.get(c, c + ' ')}{v:,.2f}" for c, v in sorted(sums.items())]


def compose(r: dict, lines: list[str], period: str, updates: list | None, costs: dict | None, crew: int | None,
            site: str = "https://tauhud.com", paper: dict | None = None) -> tuple[str, str]:
    """(title, description HTML) of the week's ship log."""
    q = html.escape
    p = []
    p.append(f"<p>The week of {q(period)} on Tau Testnet Alpha and on Tau HUD, in one place. "
             f"Written by the server from the chain and the site's own log, nothing by hand.</p>")
    p.append("<p><strong>The testnet this week</strong><br>" + "<br>".join("• " + q(x) for x in lines) + "</p>")
    if paper and (paper.get("banner") or {}).get("en"):
        p.append(f"<p><strong>The Daily Consensus No. {q(str(paper.get('no', '')))}</strong><br>"
                 f"“{q(paper['banner']['en'])}” · <a href=\"{site}/gazette/\">read it</a></p>")
    ups = week_updates(updates, r["start"], r["end"], site)
    if ups:
        more = len(ups) - MAX_UPDATES
        p.append("<p><strong>New on Tau HUD</strong><br>" + "<br>".join(f"• {q(t)} <a href=\"{q(l)}\">open</a>" for t, l in ups[:MAX_UPDATES])
                 + (f"<br>• and {more} smaller changes: <a href=\"{site}/#updates\">the full log</a>" if more > 0 else "") + "</p>")
    else:
        p.append("<p><strong>New on Tau HUD</strong><br>No changes to the site this week.</p>")
    bills = month_costs(costs)
    if bills:
        p.append("<p><strong>What it costs</strong><br>The monthly bills are " + " + ".join(bills)
                 + f" (server, tools, domains). Every bill and every donation: <a href=\"{site}/donate/\">tauhud.com/donate</a></p>")
    if isinstance(crew, int) and crew > 0:
        p.append(f"<p>{'You are' if crew == 1 else 'You are one of'} {'the first member' if crew == 1 else str(crew) + ' in the crew'}. Thank you for keeping the lights on.</p>")
    else:
        p.append("<p>Thank you for keeping the lights on.</p>")
    p.append("<p>Tau HUD is a community project, not affiliated with IDNI.</p>")
    return f"Ship log · {period}", "".join(p)


def body(title: str, description: str, live_at: float) -> dict:
    return {"attributes": {"core": {"title": title, "description": description,
                                    "liveAt": datetime.fromtimestamp(live_at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}},
            "access": {"type": "MembersOnly"}, "notifications": {"enabled": True}}


def post(title: str, description: str, live_at: float) -> int | None:
    """Create the members-only post; its id, or None."""
    d = _req("POST", "/memberships/posts/texts", body(title, description, live_at))
    return (d or {}).get("postId")


def gather(r: dict, lines: list[str], period: str, site: str, paper: dict | None = None) -> tuple[str, str, int | None]:
    """Everything compose() needs, read now; the tiers only when the API user is set."""
    crew = None
    if enabled():
        try:
            crew = members(tiers())
        except (urllib.error.URLError, OSError, ValueError):
            crew = None
    t, d = compose(r, lines, period, _get_json(UPDATES_URL), _get_json(COSTS_URL), crew, site, paper)
    return t, d, crew
