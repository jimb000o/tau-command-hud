"""Tau HUD's YouTube channel, made by the server: real pictures of tauhud.com in Live mode, the owner's own (cloned)
voice, one question per video.

  brief     every video starts from a brief (yt_brief.py) and is read by the checker before anything is filmed
  voice     ElevenLabs speaks each scene's words (yt_voice.py); the scene is then made longer than its words
  film      the film service pictures each scene on the live site (agorzilla-shots/film.mjs, the shared /work volume);
            a page that shows the simulation or an offline header is not filmed, and there is no video
  cut       yt_cut.py: camera, voice, captions, the moving pulse mark, the end card, the preview picture
  draft     the film in /public/yt/drafts/ and on YouTube as a PRIVATE video; the owner is told privately with the
            line that releases it (up yt send <id>). The first YT_REVIEW_WEEKLY weekly videos and YT_REVIEW_SHORTS
            shorts wait for that line; after them a video that passed every check goes public by itself.
            The five answer videos (yt_briefs/) always wait.
  learn     on the 1st and 15th: views, minutes, the share watched and where viewers left, per video; scenes that
            lose viewers are told to the writer, and the share of a scene that may be spoken moves with what is watched

What runs by itself (python yt.py loop), never while a cruise ship is due (the node shares this machine):
  answers   one of the five answer videos every YT_ANSWER_HOURS until all are drafts
  weekly    Sunday YT_WEEKLY_HOUR (Europe/Berlin): the week's one question (yt_weekly.py); no strong question, no video
  shorts    YT_SHORT_DAYS (default Tuesday, Thursday): one moment, 20 to 45 s, upright; at most YT_SHORTS_WEEK a week

Commands (infra/up.sh yt ...):
  python yt.py line                 the state in a few lines (the `up yt` block)
  python yt.py login                the one-time YouTube sign-in (asks for the pasted address)
  python yt.py check <brief.json>   what the checker says, and the timeline
  python yt.py make <id|brief.json> that video now, as a draft          python yt.py weekly | short   the same, written now
  python yt.py send <id>            the draft made public               python yt.py drop <id>   a draft thrown away
  python yt.py list                 every video                         python yt.py learn       the numbers now
  python yt.py on | off             the service's own work started / stopped (drafts stay)

Not possible through YouTube's API (read on its pages 15 November 2026): the preview picture's click rate and pinning
a comment. `learn` names the three numbers it has; the click rate stands in YouTube Studio.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import yt_api
import yt_brief
import yt_cut
import yt_voice

log = logging.getLogger("yt")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("YT_STATE", "/state/yt.json")
WORK = os.environ.get("YT_WORK", "/work")
FILM = os.environ.get("FILM_DIR", os.path.join(WORK, "film"))
OUT = os.environ.get("YT_OUT", "/public/yt")
BRIEFS = os.environ.get("YT_BRIEFS", os.path.join(HERE, "yt_briefs"))
ART = os.environ.get("YT_AGORZILLA", os.path.join(HERE, "yt_art"))
NODE = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/")
ON = os.environ.get("YT", "true").lower() in ("1", "true", "yes")
REVIEW = {"weekly": int(os.environ.get("YT_REVIEW_WEEKLY", "4") or 0), "short": int(os.environ.get("YT_REVIEW_SHORTS", "3") or 0), "answer": 10**6}
ANSWER_HOURS = float(os.environ.get("YT_ANSWER_HOURS", "6") or 6)
WEEKLY_DAY = int(os.environ.get("YT_WEEKLY_WEEKDAY", "6") or 6)       # Monday = 0; 6 = Sunday
WEEKLY_HOUR = int(os.environ.get("YT_WEEKLY_HOUR", "9") or 9)
SHORT_DAYS = {int(d) for d in os.environ.get("YT_SHORT_DAYS", "1,3").split(",") if d.strip()}
SHORT_HOUR = int(os.environ.get("YT_SHORT_HOUR", "10") or 10)
SHORTS_WEEK = int(os.environ.get("YT_SHORTS_WEEK", "3") or 0)
CROSS = {c.strip() for c in os.environ.get("YT_CROSSPOST", "telegram").split(",") if c.strip()}
FILM_WAIT = int(os.environ.get("YT_FILM_WAIT", "2400"))
TZ = ZoneInfo("Europe/Berlin")
# German time: the cruise ships' hours, when the node needs the machine (Tuesday 16-20, Wednesday 14-18, Saturday 12-17)
BUSY = {1: (16, 20), 2: (14, 18), 5: (12, 17)}
UP = 'ssh root@node.tauhud.com "cd /opt/tau-command-hud && sh infra/up.sh yt {}"'


# ---------- state ----------
def state() -> dict:
    try:
        with open(STATE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    st.setdefault("videos", {})
    st.setdefault("released", {})
    st.setdefault("ratio", yt_brief.RATIO)
    st.setdefault("learned", [])
    return st


def save(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
    with open(STATE + ".part", "w") as f:
        json.dump(st, f, indent=1)
    os.replace(STATE + ".part", STATE)


def mark(vid: str, **kw) -> dict:
    st = state()
    v = st["videos"].setdefault(vid, {"id": vid})
    v.update(kw)
    save(st)
    return v


def tell(text: str) -> tuple[bool, str]:
    try:
        import tickerwatch
        return tickerwatch.tell(text[:4000])
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def busy(now: datetime | None = None) -> bool:
    now = now or datetime.now(TZ)
    span = BUSY.get(now.weekday())
    return bool(span and span[0] - 1 <= now.hour < span[1])


def off() -> bool:
    return not ON or bool(state().get("off"))


def ready() -> str:
    """"" when a video can be made; else what is missing, in the owner's words."""
    if not yt_voice.ready():
        return "no voice yet (YT_VOICE_ID and ELEVENLABS_API_KEY in infra/.env)"
    return ""


# ---------- one video ----------
def _film(vid: str, fmt: str, brief: dict, tl: dict, cat: dict) -> dict:
    os.makedirs(FILM, exist_ok=True)
    job = {"id": vid, "format": fmt, "level": brief.get("level", "new"), "scenes": []}
    for row, s in zip(tl["scenes"], brief["scenes"]):
        c = cat[s["scene"]]
        job["scenes"].append({"n": row["n"], "page": c["page"], "seconds": row["seconds"], "door": bool(c.get("door")), "steps": c.get("steps") or []})
    done = os.path.join(FILM, vid + ".done.json")
    for p in (done, os.path.join(FILM, vid + ".job.json")):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(os.path.join(FILM, vid), ignore_errors=True)
    tmp = os.path.join(FILM, "." + vid + ".job.json")
    with open(tmp, "w") as f:
        json.dump(job, f)
    os.replace(tmp, os.path.join(FILM, vid + ".job.json"))
    t0 = time.time()
    while time.time() - t0 < FILM_WAIT:
        if os.path.exists(done):
            with open(done) as f:
                return json.load(f)
        time.sleep(5)
    return {"ok": False, "why": f"the film service did not answer in {FILM_WAIT // 60} minutes (docker compose ps film)"}


def _agorzilla(name: str) -> str | None:
    for p in (os.path.join(ART, f"agorzilla-{name}.webp"), os.path.join(ART, "agorzilla-grown.webp")):
        if os.path.exists(p):
            return p
    return None


def make(brief: dict, auto: bool = False) -> dict:
    """The whole way from a brief to a private draft. Returns the video's state row; row["status"] is "draft",
    "public" (auto, past the review count) or "failed" with row["why"]."""
    vid, kind = brief.get("id", ""), brief.get("kind")
    cat = yt_brief.scenes()
    wrong = yt_brief.check(brief, cat)
    if wrong:
        return mark(vid or "no-id", kind=kind, status="failed", why="the checker: " + "; ".join(wrong), at=round(time.time()))
    miss = ready()
    if miss:
        return mark(vid, kind=kind, status="failed", why=miss, at=round(time.time()))
    fmt = "tall" if kind == "short" else "wide"
    st = state()
    mark(vid, kind=kind, status="making", title=brief["title"], question=brief["question"], at=round(time.time()), why="")
    work = os.path.join(WORK, "cut", vid)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    try:
        spoken, clips = {}, {}
        for i, s in enumerate(brief["scenes"]):
            if not (s.get("say") or "").strip():
                continue
            v = yt_voice.speak(s["say"], s.get("voice", "main"))
            if v is None:                      # Rico has no voice here: his line is left out, the scene stays
                continue
            spoken[i], clips[i] = v["seconds"], v
        tl = yt_brief.timeline(brief, spoken, cat, ratio=st["ratio"])
        film = _film(vid, fmt, brief, tl, cat)
        if not film.get("ok"):
            raise RuntimeError("not filmed: " + str(film.get("why") or "no reason given"))
        parts, voices, labels, subs, t = [], [], [], [], 0.0
        missing = []
        for row, s, fs in zip(tl["scenes"], brief["scenes"], film["scenes"]):
            clip = yt_cut.scene_clip(os.path.join(FILM, vid, fs["dir"]), fs["frames"], fs["steps"], row["seconds"],
                                     os.path.join(work, f"s{row['n']}.mp4"), fmt, (fs["w"], fs["h"]))
            missing += [f"scene {row['n'] + 1} ({s['scene']}): {x.get('to')} was not on the page" for x in fs["steps"] if not x.get("ok")]
            row["at"] = round(t, 2)
            if row["n"] in clips:
                c = clips[row["n"]]
                voices.append({"path": c["path"], "at": t + yt_brief.LEAD})
                if fmt == "tall":
                    subs += yt_cut.chunks([(w, a + t + yt_brief.LEAD, b + t + yt_brief.LEAD) for w, a, b in c["words"]])
            if s.get("caption"):
                labels.append((s["caption"], t + 0.4, t + min(row["seconds"] - 0.3, 6.0)))
            parts.append({"path": clip, "seconds": row["seconds"]})
            t += row["seconds"]
            if row["n"] == 0 and fmt == "wide":          # the hook first, then the mark: never an intro before the promise
                parts.append({"path": yt_cut.sting(os.path.join(work, "sting.mp4"), fmt), "seconds": yt_cut.STING})
                t += yt_cut.STING
        if any(s.get("moment") for s, fs in zip(brief["scenes"], film["scenes"]) if not any(x.get("ok") and x.get("rect") for x in fs["steps"])):
            raise RuntimeError("the moment was not in the picture (nothing refused on the page while filming); tried again at the next turn")
        nxt = brief.get("next") or ""
        nxt_title = (st["videos"].get(nxt) or {}).get("title") or ""
        if not nxt_title and nxt:
            try:
                nxt_title = yt_brief.load(os.path.join(BRIEFS, nxt + ".json"))["title"]
            except (OSError, ValueError, KeyError):
                nxt_title = ""
        parts.append({"path": yt_cut.end_card(os.path.join(work, "end.mp4"), fmt, nxt_title if fmt == "wide" else ""), "seconds": yt_cut.END})
        crew_at = None
        if fmt == "wide":
            mids = [r["at"] for r in tl["scenes"] if r["at"] >= t * 0.45]
            crew_at = (mids[0] if mids else t * 0.5) + 1.0
        os.makedirs(os.path.join(OUT, "drafts"), exist_ok=True)
        dst = os.path.join(OUT, "drafts", vid + ".mp4")
        info = yt_cut.assemble(dst + ".part.mp4", fmt, parts, voices, labels, subs, work, crew_at=crew_at)
        os.replace(dst + ".part.mp4", dst)
        thumb = None
        if fmt == "wide":
            m = next((r for r, s in zip(tl["scenes"], brief["scenes"]) if s.get("moment")), tl["scenes"][0])
            back = yt_cut.still(dst, m["at"] + min(m["seconds"] - 0.5, 6.0), os.path.join(work, "back.jpg"))
            th = brief.get("thumb") or {}
            thumb = yt_cut.thumbnail(os.path.join(OUT, "drafts", vid + ".jpg"), back, th.get("words", ""), th.get("number", ""),
                                     _agorzilla(th.get("agorzilla") or "grown"))
        row = mark(vid, status="draft", file=dst, seconds=info["seconds"], share=tl["share"], format=fmt, thumb=thumb, notes=missing,
                   timeline=[{"n": r["n"], "scene": r["scene"], "at": r["at"], "seconds": r["seconds"]} for r in tl["scenes"]],
                   brief=brief, made=round(time.time()), url=f"{NODE}/yt/drafts/{vid}.mp4")
    except Exception as e:  # noqa: BLE001  one video failing must never stop the service
        log.warning("%s failed: %s", vid, e)
        return mark(vid, status="failed", why=str(e)[:500], at=round(time.time()))
    finally:
        yt_cut.clean(work)
        shutil.rmtree(os.path.join(FILM, vid), ignore_errors=True)
    row = _upload(vid)
    if auto and row.get("status") == "draft" and row.get("yt") and state()["released"].get(kind, 0) >= REVIEW.get(kind, 10**6) and not row.get("notes"):
        return send(vid)
    return row


def _upload(vid: str) -> dict:
    v = state()["videos"][vid]
    if not yt_api.signed_in():
        return mark(vid, note="not on YouTube yet: sign in once (up yt login), then up yt make " + vid)
    b = v["brief"]
    urls = {k: "https://youtu.be/" + x["yt"] for k, x in state()["videos"].items() if x.get("yt") and x.get("status") == "public"}
    try:
        res = yt_api.resource(b["title"], yt_brief.description(b, urls), yt_brief.tags(b), "private", synthetic=not yt_voice.OWN)
        yid = yt_api.upload(v["file"], res)
        v = mark(vid, yt=yid, note="")
        if v.get("thumb"):
            try:
                yt_api.set_thumbnail(yid, v["thumb"])
            except yt_api.YtError as e:
                v = mark(vid, note=f"{e} (a channel must be phone-verified for its own preview pictures: youtube.com/verify)")
    except yt_api.YtError as e:
        return mark(vid, note=f"not on YouTube: {e}")
    return v


def draft_note(v: dict) -> str:
    kind = v.get("kind")
    left = max(0, REVIEW.get(kind, 0) - state()["released"].get(kind, 0)) if kind != "answer" else None
    lines = [f"YouTube draft ({kind}, {v.get('seconds', 0):.0f} s, {v.get('share', 0) * 100:.0f} % spoken): {v.get('title')}",
             "Look at it: " + (f"https://youtu.be/{v['yt']} (private, only you see it)" if v.get("yt") else str(v.get("url")))]
    if v.get("note"):
        lines.append("Note: " + v["note"])
    for n in (v.get("notes") or [])[:4]:
        lines.append("Camera: " + n)
    lines += ["Make it public:", UP.format("send " + v["id"]), "Not good? " + UP.format("drop " + v["id"])]
    if left is not None:
        lines.append(f"{left} more {kind} video{'s' if left != 1 else ''} wait for your line, then this kind goes public by itself." if left
                     else "From the next one on, this kind goes public by itself.")
    return "\n".join(lines)


def send(vid: str) -> dict:
    st = state()
    v = st["videos"].get(vid)
    if not v or v.get("status") not in ("draft", "public"):
        raise SystemExit(f"no draft called {vid} (python yt.py list)")
    if v.get("status") == "public":
        return v
    if not v.get("yt"):
        v = _upload(vid)
        if not v.get("yt"):
            raise SystemExit(v.get("note") or "not on YouTube")
    yt_api.publish(v["yt"])
    st = state()
    st["released"][v["kind"]] = st["released"].get(v["kind"], 0) + 1
    st["videos"][vid].update(status="public", released=round(time.time()), link="https://youtu.be/" + v["yt"])
    save(st)
    v = st["videos"][vid]
    if v.get("format") == "tall" and "telegram" in CROSS:
        try:
            import alerts
            import post_video as pv
            if alerts.Telegram().enabled():
                pv.telegram_video(v["file"], f"<b>{alerts.html.escape(v['title'])}</b>\n\n{alerts.html.escape(v['brief'].get('description', ''))}", 1080, 1920)
                mark(vid, telegram=True)
        except Exception as e:  # noqa: BLE001
            log.warning("telegram: %s", e)
    return state()["videos"][vid]


def drop(vid: str) -> str:
    st = state()
    v = st["videos"].get(vid)
    if not v:
        return f"no video called {vid}"
    if v.get("status") == "public":
        return f"{vid} is public; take it down in YouTube Studio"
    for p in (v.get("file"), v.get("thumb")):
        if p and os.path.exists(p):
            os.remove(p)
    v.update(status="dropped", why="dropped by the owner")
    save(st)
    return f"{vid} dropped here" + (f"; the private video https://youtu.be/{v['yt']} stays in YouTube Studio until you delete it there" if v.get("yt") else "")


# ---------- what runs by itself ----------
def answers_left(st: dict) -> list[str]:
    out = []
    for p in sorted(glob.glob(os.path.join(BRIEFS, "*.json"))):
        vid = os.path.basename(p)[:-5]
        v = st["videos"].get(vid) or {}
        if v.get("status") in ("draft", "public", "dropped"):
            continue
        if v.get("status") == "failed" and time.time() - v.get("at", 0) < 6 * 3600:
            continue
        out.append(vid)
    order = ["answer-what-is-tau-net", "answer-watch-the-chain", "answer-first-payment", "answer-personal-rule", "answer-run-a-node"]
    return sorted(out, key=lambda v: order.index(v) if v in order else 99)


def _week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def written(kind: str) -> dict | None:
    import yt_weekly
    st = state()
    done = [v.get("question", "") for v in st["videos"].values() if v.get("question")]
    brief, why = yt_weekly.write(kind, learned=st.get("learned"), done=done)
    if not brief:
        log.info("%s: %s", kind, why)
        mark(f"{kind}-{time.strftime('%Y-%m-%d')}-none", kind=kind, status="none", why=why, at=round(time.time()))
        return None
    return brief


def step(now: datetime | None = None) -> str:
    """One turn of the loop; returns what it did, for the log."""
    now = now or datetime.now(TZ)
    if off():
        return "off"
    if busy(now):
        return "a cruise ship is due: nothing filmed"
    if ready():
        return ready()
    st = state()
    day, wk = now.strftime("%Y-%m-%d"), _week_key(now)
    if now.day in (1, 15) and now.hour >= 8 and st.get("learned_on") != day and yt_api.signed_in():
        st["learned_on"] = day
        save(st)
        text = learn()
        tell(text)
        return "learned"
    if now.weekday() == WEEKLY_DAY and now.hour >= WEEKLY_HOUR and st.get("weekly") != wk:
        st["weekly"] = wk
        save(st)
        b = written("weekly")
        if not b:
            tell("YouTube: no weekly video this week. " + (state()["videos"].get(f"weekly-{time.strftime('%Y-%m-%d')}-none") or {}).get("why", ""))
            return "weekly: none"
        return _made(make(b, auto=True))
    shorts = [v for v in st["videos"].values() if v.get("kind") == "short" and v.get("week") == wk]
    if now.weekday() in SHORT_DAYS and now.hour >= SHORT_HOUR and st.get("short") != day and len(shorts) < SHORTS_WEEK:
        st["short"] = day
        save(st)
        b = written("short")
        if not b:
            return "short: none"
        row = make(b, auto=True)
        mark(row["id"], week=wk)
        return _made(row)
    left = answers_left(st)
    if left and time.time() - st.get("answer_at", 0) >= ANSWER_HOURS * 3600:
        st["answer_at"] = round(time.time())
        save(st)
        return _made(make(yt_brief.load(os.path.join(BRIEFS, left[0] + ".json"))))
    return "nothing due"


def _made(row: dict) -> str:
    if row.get("status") == "draft":
        tell(draft_note(row))
    elif row.get("status") == "public":
        tell(f"YouTube: public by itself: {row.get('title')}\n{row.get('link')}")
    elif row.get("status") == "failed":
        tell(f"YouTube: no video {row.get('id')}: {row.get('why')}")
    return f"{row.get('id')}: {row.get('status')} {row.get('why') or ''}".strip()


# ---------- the numbers ----------
def drop_point(curve: list[tuple[float, float]], share: float) -> float | None:
    """How far into the video (0..1) the audience first falls to `share` of those who started."""
    if not curve:
        return None
    top = max(curve[0][1], 1e-9)
    for x, y in curve:
        if y / top <= share:
            return x
    return None


def scene_at(timeline: list[dict], seconds: float) -> dict | None:
    last = None
    for r in timeline or []:
        if r["at"] <= seconds:
            last = r
    return last


def learn(now: float | None = None) -> str:
    """Reads each public video's numbers, notes where viewers left, and moves two things the next videos use: what
    the writer is told (scenes that lost viewers, what held them) and the share of a scene that may be spoken."""
    now = time.time() if now is None else now
    st = state()
    until = time.strftime("%Y-%m-%d", time.gmtime(now))
    rows, lost = [], {}
    for v in st["videos"].values():
        if v.get("status") != "public" or not v.get("yt"):
            continue
        since = time.strftime("%Y-%m-%d", time.gmtime(v.get("released", now) - 86400))
        try:
            n = yt_api.numbers(v["yt"], since, until)
            curve = yt_api.retention(v["yt"], since, until) if n["views"] >= 30 else []
        except yt_api.YtError as e:
            return f"YouTube numbers: {e}"
        p30, p50 = drop_point(curve, 0.7), drop_point(curve, 0.5)
        v["numbers"] = dict(n, lost_30_at=p30, lost_50_at=p50, read=until)
        rows.append(v)
        for p in (p30, p50):
            if p is not None:
                s = scene_at(v.get("timeline"), p * v.get("seconds", 0))
                if s:
                    lost[s["scene"]] = lost.get(s["scene"], 0) + 1
    try:
        ch = yt_api.channel()
    except yt_api.YtError as e:
        return f"YouTube numbers: {e}"
    longs = [v for v in rows if v.get("format") == "wide" and v["numbers"]["views"] >= 30]
    learned = []
    if longs:
        avg = sum(v["numbers"]["avg_share"] for v in longs) / len(longs)
        early = [v for v in longs if v["numbers"]["lost_30_at"] is not None and v["numbers"]["lost_30_at"] * v["seconds"] < 15]
        if len(early) * 2 > len(longs):
            learned.append("Most viewers who leave do so in the first 15 seconds: make the first scene shorter and start answering the title at once.")
        worst = sorted(lost.items(), key=lambda kv: -kv[1])[:2]
        for sc, k in worst:
            if k >= 2:
                learned.append(f"Viewers left during the view '{sc}' in {k} videos: keep it short or bring it later.")
        best = max(longs, key=lambda v: v["numbers"]["avg_share"])
        learned.append(f"Best held so far ({best['numbers']['avg_share'] * 100:.0f} % watched): \"{best.get('question')}\".")
        # the voice's share of a scene: less talk when little is watched, back towards the start value when much is
        st["ratio"] = round(min(0.6, max(0.45, st["ratio"] + (0.02 if avg >= 0.5 else -0.03 if avg < 0.35 else 0.0))), 2)
    st["learned"], st["channel"] = learned, dict(ch, read=until)
    save(st)
    out = [f"YouTube, {until}: {ch['subscribers']} subscribers, {ch['views']} views, {len(rows)} public videos."]
    for v in sorted(rows, key=lambda v: -v["numbers"]["views"])[:5]:
        n = v["numbers"]
        out.append(f"  {n['views']} views, {n['avg_share'] * 100:.0f} % watched, +{n['subscribers']} subscribers: {v.get('title')}")
    out += ["Learned: " + s for s in learned] or ["Too few views yet to learn from (30 per video)."]
    out.append("The preview pictures' click rate is not in YouTube's API: see it in YouTube Studio, Analytics, Reach.")
    return "\n".join(out)


# ---------- the `up` block ----------
def line() -> str:
    st = state()
    if off():
        return "youtube: off (up yt on)"
    vids = [v for v in st["videos"].values() if v.get("status") in ("draft", "public", "failed", "making")]
    out = ["youtube: " + ("no YouTube client yet (YT_CLIENT_ID in infra/.env; the guide: infra/alerts/YOUTUBE.md)" if not yt_api.configured() else
                         "signed in" if yt_api.signed_in() else "not signed in yet (up yt login)") +
           "; voice: " + ("ready" + ("" if yt_voice.OWN else ", not the owner's own: videos carry YouTube's AI label") if yt_voice.ready() else
                          "none yet (YT_VOICE_ID in infra/.env)") +
           f"; {yt_voice.used()} of {yt_voice.MONTH_CAP} signs spoken this month"]
    n = {k: sum(1 for v in vids if v.get("status") == k) for k in ("draft", "public", "failed")}
    out.append(f"  {n['public']} public, {n['draft']} drafts, {n['failed']} failed; answers still to make: {len(answers_left(st))}; "
               f"released by you: weekly {st['released'].get('weekly', 0)} of {REVIEW['weekly']}, shorts {st['released'].get('short', 0)} of {REVIEW['short']}")
    for v in sorted(vids, key=lambda v: -(v.get("made") or v.get("at") or 0))[:6]:
        s = f"  {v.get('status'):7} {v['id']}"
        if v.get("status") == "draft":
            s += "  " + (f"https://youtu.be/{v['yt']}" if v.get("yt") else str(v.get("url"))) + f"  ->  up yt send {v['id']}"
        elif v.get("status") == "public":
            s += "  " + str(v.get("link"))
        elif v.get("why"):
            s += "  (" + v["why"][:160] + ")"
        out.append(s)
    ch = st.get("channel")
    if ch:
        out.append(f"  channel on {ch.get('read')}: {ch.get('subscribers')} subscribers, {ch.get('views')} views")
    return "\n".join(out)


def login() -> int:
    if not yt_api.configured():
        print("No YouTube client yet: put YT_CLIENT_ID and YT_CLIENT_SECRET into infra/.env (the guide: infra/alerts/YOUTUBE.md), then up yt login again.")
        return 1
    link, verifier = yt_api.login_link()
    print("1. Open this link in your browser and choose the channel Tau HUD:\n\n" + link + "\n")
    print("2. Google warns that the app is not verified: Advanced, then Go to ... (it is your own app). Allow everything it asks.")
    print("3. The browser then shows an error page (\"127.0.0.1 refused to connect\"). That is right. Copy the whole address\n   from the address line and paste it here, then Enter:\n")
    try:
        pasted = input("> ")
    except EOFError:
        print("Nothing to read: run it with a terminal (ssh -t ...).")
        return 1
    try:
        name = yt_api.login_finish(pasted, verifier)
    except yt_api.YtError as e:
        print(f"\nNot signed in: {e}")
        return 1
    print(f"\nSigned in. The channel: {name}")
    return 0


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[1] if len(argv) > 1 else "line"
    arg = argv[2] if len(argv) > 2 else ""
    if cmd == "line":
        print(line())
    elif cmd == "login":
        return login()
    elif cmd == "check":
        b = yt_brief.load(arg)
        wrong = yt_brief.check(b)
        print("\n".join("  - " + w for w in wrong) if wrong else json.dumps(yt_brief.timeline(b), indent=1))
        return 1 if wrong else 0
    elif cmd in ("make", "weekly", "short"):
        if busy() and "--now" not in argv:
            print("A cruise ship is due: filming waits (add --now to do it anyway).")
            return 1
        if cmd == "make":
            path = arg if os.path.exists(arg) else os.path.join(BRIEFS, arg + ".json")
            if not os.path.exists(path):
                v = state()["videos"].get(arg) or {}
                if not v.get("brief"):
                    print(f"no brief called {arg}")
                    return 1
                b = v["brief"]
            else:
                b = yt_brief.load(path)
        else:
            b = written(cmd)
            if not b:
                print("no video: " + str((state()["videos"].get(f"{cmd}-{time.strftime('%Y-%m-%d')}-none") or {}).get("why")))
                return 1
        row = make(b)
        print(draft_note(row) if row.get("status") == "draft" else f"{row.get('id')}: {row.get('status')}: {row.get('why')}")
        return 0 if row.get("status") == "draft" else 1
    elif cmd == "send":
        v = send(arg)
        print(f"public: {v.get('link')}")
    elif cmd == "drop":
        print(drop(arg))
    elif cmd == "list":
        for v in sorted(state()["videos"].values(), key=lambda v: v.get("made") or v.get("at") or 0):
            print(f"{v.get('status', '?'):8} {v.get('kind', '?'):7} {v['id']}  {v.get('link') or v.get('url') or v.get('why') or ''}")
    elif cmd == "learn":
        print(learn())
    elif cmd in ("on", "off"):
        st = state()
        st["off"] = cmd == "off"
        save(st)
        print(line())
    elif cmd == "loop":
        log.info("youtube service: %s", line().replace("\n", " | "))
        while True:
            try:
                did = step()
                if did not in ("nothing due", "off"):
                    log.info(did)
            except Exception:  # noqa: BLE001
                log.exception("a turn failed")
            time.sleep(300)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
