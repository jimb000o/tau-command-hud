"""Feature posts on X, never without the owner (15 Nov 2026): a new feature of Tau HUD on @TauHUDcom, a new feature of
Agorzilla on @Agorzilla, each only when a reader can do or see something today that did not exist yesterday.

Where a post comes from: the thread that builds a feature writes it next to the feature, as an "x" field on its entry in
assets/updates.json, or (Agorzilla, whose changes live in another repository, or anything dated ahead) as an item of
assets/x-features.json {"posts": [...]}. Both read the same:

  {"id": "rabbit-walkers", "account": "hud" | "agorzilla", "from": "2026-11-16T11:00:00Z",
   "text": "the post, at most 280, link-free, #TauNet $AGRS on hud, #TauNet on agorzilla",
   "film": {"url": "https://tauhud.com/rabbit/", "seconds": 12, "settle": 3000, "steps": [...]}}

What happens by itself (the xfeatures service, every 5 minutes):
  1  from "from" on (an updates.json entry without it: its day, 08:00 UTC) the post is a draft; its film is asked of the
     films service (agorzilla-shots/film.mjs: the live page in Chromium, a drawn pointer, a slow zoom)
  2  the film is cut to an mp4 and sent with the text to the owner's private Telegram chat (up owner), never the channel;
     not between 22:00 and 08:00 German time
  3  a draft nobody sent is dropped 3 days after "from": news only while it is news

What only the owner does (up x …): send posts it, after the caps below; drop throws it away; text sets new words; film
films it again. Nothing in this file posts by itself.

Caps (15 Nov 2026 playbook): @TauHUDcom at most 1 a day and 3 in any 7 days, inside X_DAILY_CAP, 2 h after the last post
(POST_GAP_MINUTES); @Agorzilla at most 2 in any 7 days, not two on one day, inside AGORZILLA_X_DAILY_CAP; neither while
a cruise ship is due or in port (Tue 16-20, Wed 14-18, Sat 12-17 German time, only while CRUISE_ENABLED is not 0).
--now sets the room and the ship hours aside, never the caps.

  python xfeatures.py loop            the service
  python xfeatures.py [list]          every draft and what it waits for
  python xfeatures.py send <id> [--now]   python xfeatures.py drop <id>   python xfeatures.py film <id>
  python xfeatures.py text <id> <new text>          python xfeatures.py check   the plan's posts read against the rules
  python xfeatures.py week [2026-W47]               the week's feature posts, for the Sunday testnet post
"""
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("xfeatures")

SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
STATE_DIR = os.path.dirname(os.environ.get("STATE_PATH", "/state/alerts.json")) or "/state"
STATE_PATH = os.environ.get("XFEATURES_PATH", os.path.join(STATE_DIR, "xfeatures.json"))
FILMS = os.environ.get("FILMS_DIR", "/public/xfilms")
EVERY = float(os.environ.get("XFEATURES_MINUTES", 5)) * 60
EXPIRE = float(os.environ.get("XFEATURES_EXPIRE_DAYS", 3)) * 86400
FILM_WAIT = 2 * 3600            # a film not back after this is given up, and the owner told
BERLIN = ZoneInfo("Europe/Berlin")
QUIET = (22, 8)                 # no private message from 22:00 to 08:00 German time (as tickerwatch)
HANDLES = {"hud": "TauHUDcom", "agorzilla": "Agorzilla"}
CAPS = {"hud": {"day": 1, "week": 3}, "agorzilla": {"day": 1, "week": 2}}
SHIP_HOURS = {1: range(16, 20), 2: range(14, 18), 5: range(12, 17)}   # weekday (Mon 0) -> German hours a ship is due/in
CRUISE_ON = os.environ.get("CRUISE_ENABLED", "1").strip() != "0"
SERVER_LINE = 'ssh root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh x {}"'

# words that make a post read as made by a machine or as a sales pitch (15 Nov 2026 playbook)
SLOP = ["excited to announce", "thrilled", "game-changer", "game changer", "revolutionary", "unleash", "supercharge",
        "level up", "don't miss", "dive in", "delve", "seamless", "cutting-edge", "next-level", "to the moon", "🚀", "🔥",
        "💥", "🤯", "pump it", "buy now", "financial advice"]
# bold safety claims a regulator would read as a promise (Kilian, 15 Nov 2026: for every text of the project)
BOLD = ["cannot lose", "can't lose", "can not lose", "never lose", "risk-free", "risk free", "no risk", "zero risk",
        "guaranteed", "guarantee", "completely safe", "totally safe", "100% safe", "fully safe", "perfectly safe",
        "cannot be stolen", "can't be stolen", "can never be stolen", "unhackable", "impossible to hack", "always safe"]
TAGS = {"hud": ["#TauNet", "$AGRS"], "agorzilla": ["#TauNet"]}


# ---------------- reading the plan ----------------

def fetch_json(path: str):
    req = urllib.request.Request(SITE + path + f"?t={int(time.time())}",
                                 headers={"User-Agent": "tauhud-xfeatures/1 (+https://tauhud.com)", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ts(s) -> float | None:
    if not s:
        return None
    try:
        s = str(s)
        if len(s) == 10:
            s += "T08:00:00Z"
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def specs(updates: list | None, plan: dict | list | None) -> list[dict]:
    """Every planned feature post, from both files, each with its "from" as a number ("at"); a broken one is kept with
    its problems so `check` can name them, but never drafted."""
    out, seen = [], set()
    for e in updates if isinstance(updates, list) else []:
        x = e.get("x") if isinstance(e, dict) else None
        if isinstance(x, dict):
            out.append({**x, "from": x.get("from") or e.get("on")})
    items = plan.get("posts") if isinstance(plan, dict) else plan if isinstance(plan, list) else []
    out += [p for p in items or [] if isinstance(p, dict)]
    res = []
    for p in out:
        p = dict(p)
        p["at"] = ts(p.get("from"))
        p["problems"] = problems(p)
        if p.get("id") in seen:
            p["problems"].append("id used twice")
        seen.add(p.get("id"))
        res.append(p)
    return res


def x_len(text: str) -> int:
    """X counts a link as 23 and most emoji as 2; the plan's posts carry no links, so: characters, wide ones twice."""
    return sum(2 if ord(c) > 0x2FFF else 1 for c in text)


def problems(p: dict) -> list[str]:
    """What keeps a planned post from being a draft: the rules of the 15 Nov 2026 playbook that a machine can check."""
    out = []
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}", str(p.get("id") or "")):
        out.append("id: lowercase letters, digits and dashes")
    acc = p.get("account")
    if acc not in HANDLES:
        out.append('account: "hud" or "agorzilla"')
    text = p.get("text")
    if not isinstance(text, str) or not text.strip():
        return out + ["no text"]
    if x_len(text) > 280:
        out.append(f"text: {x_len(text)} of 280")
    low = text.lower()
    for w in SLOP:
        if w in low:
            out.append(f"text: {w.strip()!r} reads as hype")
    for w in BOLD:
        if w in low:
            out.append(f"text: {w!r} is a safety promise we cannot make")
    if re.search(r"https?://|\bwww\.", text):
        out.append("text: no links (the film carries the post; the profile has the site)")
    for t in TAGS.get(acc, []):
        if t not in text:
            out.append(f"text: ends with {' '.join(TAGS[acc])}")
            break
    if acc == "agorzilla" and "$AGRS" in text:
        out.append("text: no $AGRS on Agorzilla's account")
    if "\n\n" not in text.strip():
        out.append("text: a blank line after the first line")
    if text.count("#") > 2:
        out.append("text: at most two hashtags")
    f = p.get("film")
    if not isinstance(f, dict) or not str(f.get("url") or "").startswith("https://"):
        out.append("film: {url: https://…, steps: […]} (a real film of the live page)")
    elif not isinstance(f.get("steps"), list):
        out.append("film: steps must be a list")
    if ts(p.get("from")) is None:
        out.append("from: a date or time (UTC)")
    return out


# ---------------- state ----------------

def load() -> dict:
    try:
        with open(STATE_PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("drafts", {})
    d.setdefault("sent", [])
    return d


def save(d: dict) -> None:
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, STATE_PATH)


def quiet(now: float) -> bool:
    h = datetime.fromtimestamp(now, BERLIN).hour
    return h >= QUIET[0] or h < QUIET[1]


def ship_due(now: float) -> bool:
    d = datetime.fromtimestamp(now, BERLIN)
    return CRUISE_ON and d.hour in SHIP_HOURS.get(d.weekday(), ())


# ---------------- the caps ----------------

def read_file(p: str) -> dict:
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def room(acc: str, d: dict, now: float, hand: bool = False, other: dict | None = None) -> list[str]:
    """Why a feature post on this account may not go out now ([] = it may). `hand`: up x send --now, which sets the
    room after the last post and the ship hours aside, never the caps. `other`: the other services' counts (tests)."""
    why = []
    day = datetime.fromtimestamp(now, BERLIN).date()
    mine = [s for s in d.get("sent", []) if s.get("account") == acc]
    today = [s for s in mine if datetime.fromtimestamp(s["at"], BERLIN).date() == day]
    week = [s for s in mine if now - s["at"] < 7 * 86400]
    if len(today) >= CAPS[acc]["day"]:
        why.append(f"already {len(today)} feature post today on @{HANDLES[acc]}")
    if len(week) >= CAPS[acc]["week"]:
        nxt = min(s["at"] for s in week) + 7 * 86400
        why.append(f"{len(week)} feature posts in 7 days on @{HANDLES[acc]}; room again "
                   + datetime.fromtimestamp(nxt, BERLIN).strftime("%a %d %b %H:%M"))
    other = other if other is not None else {
        "hud": read_file(os.path.join(STATE_DIR, "alerts.json")).get("x") or {},
        "agorzilla": read_file(os.path.join(STATE_DIR, "agorzilla.json")),
    }
    utc_day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    if acc == "hud":
        x = other.get("hud") or {}
        cap = int(os.environ.get("X_DAILY_CAP", 5))
        if x.get("day") == utc_day and int(x.get("today") or 0) >= cap:
            why.append(f"@TauHUDcom already posted {x.get('today')} times today (X_DAILY_CAP {cap})")
        if not hand:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import alerts
                left = alerts.post_gap_left("x", now)
            except Exception:  # noqa: BLE001 - the room is a courtesy; a missing file is no reason to stop
                left = 0
            if left > 0:
                why.append(f"the last post on X is younger than 2 h; room in {round(left / 60)} min (--now sets it aside)")
    else:
        a = other.get("agorzilla") or {}
        cap = int(os.environ.get("AGORZILLA_X_DAILY_CAP", 2))
        if a.get("x_day") == utc_day and int(a.get("x_n") or 0) >= cap:
            why.append(f"@Agorzilla already posted {a.get('x_n')} times today (AGORZILLA_X_DAILY_CAP {cap})")
    if not hand and ship_due(now):
        why.append("a cruise ship is due or in port now (--now sets it aside)")
    return why


# ---------------- the films ----------------

def want_film(p: dict) -> None:
    os.makedirs(os.path.join(FILMS, "want"), exist_ok=True)
    for ext in (".webm", ".meta.json", ".mp4"):
        try:
            os.remove(os.path.join(FILMS, p["id"] + ext))
        except OSError:
            pass
    tmp = os.path.join(FILMS, "want", p["id"] + ".json.tmp")
    with open(tmp, "w") as f:
        json.dump({"id": p["id"], "film": p["film"]}, f)
    os.replace(tmp, tmp[:-4])


def cut(pid: str) -> tuple[str | None, str]:
    """The film back from film.mjs cut to an mp4 X takes (H.264, 30 fps, no sound): (path, "") or (None, why)."""
    meta = read_file(os.path.join(FILMS, pid + ".meta.json"))
    if not meta:
        return None, ""
    if not meta.get("ok"):
        return None, meta.get("why") or "film failed"
    src, out = os.path.join(FILMS, pid + ".webm"), os.path.join(FILMS, pid + ".mp4")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(meta.get("start") or 0), "-i", src, "-t", str(meta.get("seconds") or 10),
           "-vf", "fps=30,scale=1280:720:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-movflags", "+faststart", "-an", out]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out):
        return None, "ffmpeg: " + (r.stderr or "").strip()[-200:]
    return out, ""


def tell(text: str, video: str | None = None) -> tuple[bool, str]:
    """A private message to the owner (tickerwatch's chat), with the film when there is one; never the channel."""
    import tickerwatch as T
    chat = T.owner()
    if not T.TOKEN or not chat:
        return False, "no owner chat (up owner)"
    if not video:
        return T.tell(text)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import alerts
    body, ctype = alerts.multipart({"chat_id": chat, "caption": text[:1024], "supports_streaming": "true", "width": "1280", "height": "720"},
                                   {"video": (os.path.basename(video), open(video, "rb").read(), "video/mp4")})
    req = urllib.request.Request(f"https://api.telegram.org/bot{T.TOKEN}/sendVideo", data=body, headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.load(r)
        return bool(j.get("ok")), str(j.get("description") or "")
    except Exception as e:  # noqa: BLE001 - never log the URL: it holds the token
        return False, type(e).__name__


def offer_text(p: dict, text: str) -> str:
    return (f"Draft for @{HANDLES[p['account']]} ({p['id']}), nothing posted:\n\n{text}\n\n"
            f"Post it:\n{SERVER_LINE.format('send ' + p['id'])}\n\n"
            f"Drop it: up x drop {p['id']} · new words: up x text {p['id']} \"…\" · film again: up x film {p['id']}")


# ---------------- the loop ----------------

def step(now: float, plan: list[dict], d: dict, film=want_film, cutter=cut, teller=tell) -> list[str]:
    """One look: new drafts asked for a film, films cut and offered to the owner, old drafts dropped. Returns what it did."""
    did = []
    by = {p["id"]: p for p in plan if not p["problems"] and p.get("at") is not None}
    for pid, p in by.items():
        if pid in d["drafts"] or not (p["at"] <= now < p["at"] + EXPIRE):
            continue
        d["drafts"][pid] = {"state": "filming", "account": p["account"], "text": p["text"], "at": round(now), "from": p["at"]}
        film(p)
        did.append(f"{pid}: film asked")
    for pid, r in d["drafts"].items():
        p = by.get(pid)
        if r["state"] in ("filming", "filmed", "offered") and now > r.get("from", r["at"]) + EXPIRE:
            r["state"] = "expired"
            did.append(f"{pid}: expired")
            continue
        if r["state"] == "filming":
            path, why = cutter(pid)
            if path:
                r.update(state="filmed", film=path)
                did.append(f"{pid}: filmed")
            elif why or now - r["at"] > FILM_WAIT:
                r.update(state="filmed", film=None, film_why=why or "no film after 2 h")
                did.append(f"{pid}: no film ({r['film_why']})")
        if r["state"] == "filmed" and p and not quiet(now):
            text = r.get("text_new") or r["text"]
            msg = offer_text(p, text) + (f"\n\n(no film: {r['film_why']}; up x film {pid} tries again)" if r.get("film_why") else "")
            ok, err = teller(msg, r.get("film"))
            if ok:
                r.update(state="offered", offered=round(now))
                did.append(f"{pid}: offered to the owner")
            else:
                did.append(f"{pid}: not offered ({err})")
    return did


def loop() -> None:
    while True:
        try:
            updates, plan = None, None
            try:
                updates = fetch_json("/assets/updates.json")
            except Exception as e:  # noqa: BLE001
                log.warning("updates.json: %s", e)
            try:
                plan = fetch_json("/assets/x-features.json")
            except Exception as e:  # noqa: BLE001
                log.info("x-features.json: %s", e)
            d = load()
            for line in step(time.time(), specs(updates, plan), d):
                log.info(line)
            save(d)
        except Exception as e:  # noqa: BLE001 - the loop never dies
            log.exception("round failed: %s", e)
        time.sleep(EVERY)


# ---------------- by hand ----------------

def post(acc: str, text: str, video: str | None) -> str:
    """The post on the account; with the film when there is one. Returns the status id."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import alerts
    import post_video
    keys = None if acc == "hud" else {k: os.environ.get("AGORZILLA_" + k, "").strip()
                                      for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all((keys or alerts.X_KEYS).values()):
        raise RuntimeError(f"no X keys for @{HANDLES[acc]} in infra/.env")
    if video:
        return post_video.x_video(video, text, keys)
    out = alerts.X(keys) if keys else alerts.X()
    ok, _, err = out.send_text(text)
    if not ok:
        raise RuntimeError(err)
    return ""


def week_lines(d: dict, year: int, week: int) -> list[dict]:
    """The feature posts sent in that ISO week (German time), oldest first: for the Sunday testnet post (testnet_week),
    so the week's flow on X is kept on the blog."""
    out = []
    for s in sorted(d.get("sent", []), key=lambda s: s["at"]):
        y, w, _ = datetime.fromtimestamp(s["at"], BERLIN).isocalendar()
        if (y, w) == (year, week):
            out.append({"account": s["account"], "handle": HANDLES[s["account"]], "headline": s["text"].strip().split("\n")[0],
                        "url": s.get("url") or "", "at": s["at"]})
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    now = time.time()
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "loop":
        loop()
        return 0
    d = load()
    if cmd == "week":
        if len(argv) > 2:
            y, w = re.fullmatch(r"(\d{4})-W(\d{1,2})", argv[2]).groups()
        else:
            y, w, _ = datetime.fromtimestamp(now, BERLIN).isocalendar()
        for s in week_lines(d, int(y), int(w)):
            print(f"@{s['handle']}: {s['headline']}  {s['url']}")
        return 0
    if cmd == "check":
        bad = 0
        for p in specs(fetch_json("/assets/updates.json"), fetch_json("/assets/x-features.json")):
            print(f"{p.get('id')}: " + ("ok" if not p["problems"] else "; ".join(p["problems"])))
            bad += bool(p["problems"])
        return 1 if bad else 0
    if cmd == "list":
        if not d["drafts"]:
            print("feature posts: no drafts yet")
        for pid, r in sorted(d["drafts"].items(), key=lambda kv: kv[1]["at"]):
            line = f"{pid:24} @{HANDLES[r['account']]:10} {r['state']}"
            if r["state"] in ("filmed", "offered"):
                why = room(r["account"], d, now)
                line += "   " + ("can go now: up x send " + pid if not why else "waits: " + "; ".join(why))
            print(line)
        for s in d["sent"][-5:]:
            print(f"sent {datetime.fromtimestamp(s['at'], BERLIN):%d %b %H:%M} @{HANDLES[s['account']]}: {s['url']}")
        return 0
    pid = argv[2] if len(argv) > 2 else ""
    r = d["drafts"].get(pid)
    if not r:
        print(f"no draft {pid!r}; up x lists them")
        return 1
    if cmd == "drop":
        r["state"] = "dropped"
        save(d)
        print(f"{pid}: dropped, it will not be offered again")
        return 0
    if cmd == "film":
        plan = {p["id"]: p for p in specs(fetch_json("/assets/updates.json"), fetch_json("/assets/x-features.json"))}
        if pid not in plan:
            print(f"{pid} is no longer in the plan")
            return 1
        want_film(plan[pid])
        r.update(state="filming", at=round(now), film=None, film_why=None)
        save(d)
        print(f"{pid}: filmed again within a few minutes, then it comes to your Telegram")
        return 0
    if cmd == "text":
        new = " ".join(argv[3:]).replace("\\n", "\n")
        probs = problems({"id": pid, "account": r["account"], "text": new, "film": {"url": "https://x", "steps": []}, "from": "2026-01-01"})
        if probs:
            print("not taken: " + "; ".join(probs))
            return 1
        r["text_new"] = new
        save(d)
        print(f"{pid}: new words kept ({x_len(new)} of 280):\n{new}")
        return 0
    if cmd == "send":
        if r["state"] == "sent":
            print(f"{pid} was posted already: {r.get('url')}")
            return 1
        why = room(r["account"], d, now, hand="--now" in argv)
        if why:
            print("not posted: " + "; ".join(why))
            return 1
        text = r.get("text_new") or r["text"]
        try:
            sid = post(r["account"], text, r.get("film") if r.get("film") and os.path.exists(r["film"]) else None)
        except Exception as e:  # noqa: BLE001
            print(f"not posted: {e}")
            return 1
        url = f"https://x.com/{HANDLES[r['account']]}/status/{sid}" if sid else ""
        r.update(state="sent", sent=round(now), url=url)
        d["sent"].append({"id": pid, "account": r["account"], "at": round(now), "url": url, "text": text})
        save(d)
        print(f"posted: {url or 'on @' + HANDLES[r['account']]}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
