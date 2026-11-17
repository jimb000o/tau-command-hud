"""What our X posts did (17 Nov 2026): once a day the numbers of every post of the last days on @TauHUDcom and @Agorzilla
are read from the X API and kept, so the posting plan can be measured instead of guessed (no Premium, no analytics export).

Price (docs.x.com/x-api/getting-started/pricing, read 17 Nov 2026): reading the posts of the app's own account is an
"owned read", $0.001 a post. A day reads the posts of the last XSTATS_DAYS (7) days: about 35 posts, about $1 a month for
both accounts. The first run reads 30 days back once (X keeps the private numbers 30 days). The account's id is asked
once and kept (a user read, $0.01).

Numbers kept per post: impressions, likes, reposts, replies, quotes, bookmarks (public), and where X gives them for the
account's own posts: link clicks, profile clicks, video views (non_public_metrics). If X refuses the private numbers the
public ones are read, and the report says so.

State: /state/xstats.json {"users": {acc: id}, "posts": {id: {...latest...}}, "runs": [...], "reads": n}.

  python xstats.py run [--days N]     read now (the xfeatures service does it by itself once a day, XSTATS_HOUR UTC)
  python xstats.py [report] [--days N]  what worked in the last N (30) days: best posts, link vs no link, film vs
                                      picture vs text, hour and weekday, and what the reading cost
  python xstats.py csv                every post kept, one line each, for the knowledge base
"""
import base64
import csv
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("xstats")

STATE_DIR = os.path.dirname(os.environ.get("STATE_PATH", "/state/alerts.json")) or "/state"
PATH = os.environ.get("XSTATS_PATH", os.path.join(STATE_DIR, "xstats.json"))
DAYS = int(os.environ.get("XSTATS_DAYS", 7))
FIRST_DAYS = 30
HOUR = int(os.environ.get("XSTATS_HOUR", 4))          # UTC: 05:00 German time, nothing posts then
OWNED_READ = 0.001                                    # $ per post read on the own account
USER_READ = 0.010
API = "https://api.x.com/2"
BERLIN = ZoneInfo("Europe/Berlin")
ACCOUNTS = {"hud": "", "agorzilla": "AGORZILLA_"}
HANDLES = {"hud": "TauHUDcom", "agorzilla": "Agorzilla"}
FIELDS_ALL = "created_at,public_metrics,non_public_metrics,attachments,entities"
FIELDS_PUBLIC = "created_at,public_metrics,attachments,entities"
EXPANSIONS = {"expansions": "attachments.media_keys", "media.fields": "type"}


def keys(acc: str) -> dict:
    p = ACCOUNTS[acc]
    return {k: os.environ.get(p + k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}


def _pct(s: str) -> str:
    return urllib.parse.quote(str(s), safe="-._~")


def auth(k: dict, method: str, url: str, query: dict) -> str:
    """OAuth 1.0a user context; for a GET the query is part of what is signed."""
    oauth = {"oauth_consumer_key": k["X_API_KEY"], "oauth_nonce": secrets.token_hex(16),
             "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
             "oauth_token": k["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
    params = "&".join(f"{_pct(a)}={_pct(b)}" for a, b in sorted({**oauth, **query}.items()))
    base = "&".join([method, _pct(url), _pct(params)])
    key = f"{_pct(k['X_API_SECRET'])}&{_pct(k['X_ACCESS_SECRET'])}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_pct(a)}="{_pct(b)}"' for a, b in sorted(oauth.items()))


def get(k: dict, path: str, query: dict) -> dict:
    url = API + path
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(query),
                                 headers={"Authorization": auth(k, "GET", url, query), "User-Agent": "tauhud-xstats"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detail = json.load(e)
        except ValueError:
            detail = {}
        raise RuntimeError(f"HTTP {e.code}: {detail.get('detail') or detail.get('title') or ''}") from None


def load() -> dict:
    try:
        with open(PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    for k, v in (("users", {}), ("posts", {}), ("runs", []), ("reads", 0), ("cost", 0.0)):
        d.setdefault(k, v)
    return d


def save(d: dict) -> None:
    os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, PATH)


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def row(acc: str, t: dict, media: dict, now: float) -> dict:
    """One post as kept: when, what kind, and its numbers."""
    pm, npm = t.get("public_metrics") or {}, t.get("non_public_metrics") or {}
    kinds = {media.get(m) for m in (t.get("attachments") or {}).get("media_keys") or []}
    urls = [u.get("expanded_url") or u.get("url") or "" for u in (t.get("entities") or {}).get("urls") or []]
    links = [u for u in urls if "/photo/" not in u and "/video/" not in u and not u.startswith("https://x.com/")
             and not u.startswith("https://twitter.com/")]
    at = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).timestamp()
    return {"id": t["id"], "account": acc, "at": at, "text": t.get("text", ""),
            "media": "video" if kinds & {"video", "animated_gif"} else "photo" if "photo" in kinds else "none",
            "link": links[0] if links else "",
            "impressions": pm.get("impression_count", npm.get("impression_count", 0)),
            "likes": pm.get("like_count", 0), "reposts": pm.get("retweet_count", 0), "replies": pm.get("reply_count", 0),
            "quotes": pm.get("quote_count", 0), "bookmarks": pm.get("bookmark_count", 0),
            "link_clicks": npm.get("url_link_clicks"), "profile_clicks": npm.get("user_profile_clicks"),
            "video_views": npm.get("video_view_count") if "video_view_count" in npm else None,
            "read": now}


def read_account(acc: str, d: dict, now: float, days: int, fetch=get) -> tuple[int, str]:
    """The account's posts of the last `days` days, kept in d. Returns (posts read, note)."""
    k = keys(acc)
    if not all(k.values()):
        return 0, "no keys"
    uid = d["users"].get(acc)
    if not uid:
        uid = (fetch(k, "/users/me", {}).get("data") or {}).get("id")
        if not uid:
            return 0, "no user id"
        d["users"][acc] = uid
        d["cost"] += USER_READ
    note, private = "", True
    token, n = None, 0
    while True:
        q = {"max_results": "100", "start_time": iso(now - days * 86400), "exclude": "retweets",
             "tweet.fields": FIELDS_ALL if private else FIELDS_PUBLIC, **EXPANSIONS}
        if token:
            q["pagination_token"] = token
        try:
            r = fetch(k, f"/users/{uid}/tweets", q)
        except RuntimeError as e:
            if private and n == 0 and ("HTTP 400" in str(e) or "HTTP 403" in str(e)):
                private, note = False, f"private numbers refused ({e}), public ones only"
                continue
            raise
        media = {m["media_key"]: m.get("type") for m in (r.get("includes") or {}).get("media") or []}
        for t in r.get("data") or []:
            d["posts"][t["id"]] = row(acc, t, media, now)
            n += 1
        token = (r.get("meta") or {}).get("next_token")
        if not token:
            break
    d["reads"] += n
    d["cost"] += n * OWNED_READ
    return n, note


def run(now: float | None = None, days: int | None = None, fetch=get) -> list[str]:
    now = now or time.time()
    d = load()
    out = []
    for acc in ACCOUNTS:
        n_days = days or (DAYS if d["users"].get(acc) else FIRST_DAYS)
        try:
            n, note = read_account(acc, d, now, n_days, fetch)
            out.append(f"@{HANDLES[acc]}: {n} posts of the last {n_days} days read" + (f" ({note})" if note else ""))
        except Exception as e:  # noqa: BLE001
            out.append(f"@{HANDLES[acc]}: not read ({e})")
    d["runs"] = (d["runs"] + [{"at": now, "lines": out}])[-60:]
    save(d)
    return out


def due(d: dict, now: float) -> bool:
    """Once a day, from XSTATS_HOUR UTC on."""
    last = max((r["at"] for r in d.get("runs") or []), default=0)
    t = datetime.fromtimestamp(now, timezone.utc)
    return t.hour >= HOUR and datetime.fromtimestamp(last, timezone.utc).date() < t.date()


def maybe_run(now: float) -> list[str]:
    if os.environ.get("XSTATS", "1").strip() == "0" or not due(load(), now):
        return []
    return run(now)


# ---------------- what worked ----------------

def rate(p: dict) -> float:
    """Clicks to us (link + profile) per 1,000 impressions: the step toward a visit."""
    clicks = (p.get("link_clicks") or 0) + (p.get("profile_clicks") or 0)
    return 1000 * clicks / p["impressions"] if p.get("impressions") else 0.0


def group(posts: list[dict], key) -> list[str]:
    g: dict = {}
    for p in posts:
        g.setdefault(key(p), []).append(p)
    lines = []
    for k, ps in sorted(g.items(), key=lambda kv: str(kv[0])):
        imp = sum(p["impressions"] for p in ps)
        clicks = sum((p.get("link_clicks") or 0) + (p.get("profile_clicks") or 0) for p in ps)
        eng = sum(p["likes"] + p["reposts"] + p["replies"] + p["quotes"] + p["bookmarks"] for p in ps)
        lines.append(f"  {str(k):<10} {len(ps):>3} posts · {imp // len(ps):>6} views/post · "
                     f"{clicks / len(ps):>5.1f} clicks/post · {1000 * clicks / imp if imp else 0:>5.1f} per 1k · "
                     f"{eng / len(ps):>4.1f} reactions/post")
    return lines


def report(now: float | None = None, days: int = 30) -> str:
    now = now or time.time()
    d = load()
    posts = [p for p in d["posts"].values() if p["at"] >= now - days * 86400 and now - p["at"] >= 86400]
    out = [f"X numbers, posts of the last {days} days older than a day: {len(posts)} "
           f"(read {d['reads']} posts so far, ${d['cost']:.2f} in all)"]
    if d["runs"]:
        last = d["runs"][-1]
        out.append(f"last read {datetime.fromtimestamp(last['at'], BERLIN):%d.%m %H:%M}: " + "; ".join(last["lines"]))
    if not posts:
        return "\n".join(out + ["nothing to compare yet"])
    private = any(p.get("link_clicks") is not None for p in posts)
    if not private:
        out.append("(no link/profile clicks: X gave only the public numbers)")
    for acc in ACCOUNTS:
        ps = [p for p in posts if p["account"] == acc]
        if not ps:
            continue
        out.append(f"\n@{HANDLES[acc]}")
        out.append(" by clicks toward us" if private else " by views")
        best = sorted(ps, key=lambda p: ((p.get("link_clicks") or 0) + (p.get("profile_clicks") or 0), p["impressions"]),
                      reverse=True)[:5]
        for p in best:
            head = p["text"].split("\n")[0][:70]
            out.append(f"  {datetime.fromtimestamp(p['at'], BERLIN):%d.%m %H:%M} {p['impressions']:>6} views "
                       f"{p.get('link_clicks') or 0:>3} link {p.get('profile_clicks') or 0:>3} profile · {head}")
        out.append(" link in the post"); out += group(ps, lambda p: "link" if p["link"] else "no link")
        out.append(" media"); out += group(ps, lambda p: p["media"])
        out.append(" German hour"); out += group(ps, lambda p: f"{datetime.fromtimestamp(p['at'], BERLIN):%H}:00")
        out.append(" weekday"); out += group(ps, lambda p: f"{datetime.fromtimestamp(p['at'], BERLIN).weekday()}"
                                             f"-{datetime.fromtimestamp(p['at'], BERLIN):%a}")
    out.append("\nfew posts per group mean little; read it as a hint until a group has 10+")
    return "\n".join(out)


COLS = ["id", "account", "at", "media", "link", "impressions", "likes", "reposts", "replies", "quotes", "bookmarks",
        "link_clicks", "profile_clicks", "video_views", "text"]


def write_csv(f=sys.stdout) -> None:
    w = csv.writer(f)
    w.writerow(COLS)
    for p in sorted(load()["posts"].values(), key=lambda p: p["at"]):
        w.writerow([iso(p["at"]) if c == "at" else ("" if p.get(c) is None else p.get(c)) for c in COLS])


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "report"
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else None
    if cmd == "run":
        print("\n".join(run(days=days)))
        print(report(days=30))
    elif cmd == "csv":
        write_csv()
    else:
        print(report(days=days or 30))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
