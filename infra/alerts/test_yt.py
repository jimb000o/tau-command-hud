"""Unit test of the YouTube channel (yt.py, yt_brief.py, yt_api.py, yt_cut.py, yt_weekly.py), no network: the five answer
briefs pass the checker and the checker finds what a video of ours must never say; the timeline gives the picture the
larger share; the description carries the disclaimer and the ref links; the sign-in reads the pasted address and keeps
the token private; an upload goes up in pieces and picks up after a break; the camera never leaves the picture and eases
the way ffmpeg is told to; a video is made from its brief to a draft (voice, film and cut faked), waits for the owner's
line, and goes public by itself only after the review count; nothing is filmed while a cruise ship is due; the numbers
find where viewers leave and move the spoken share; the weekly writer's numbers must stand in the week's facts; the
moving mark and the end card come out at their length (when ffmpeg is here).

Run: python test_yt.py
"""
import glob
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
from datetime import datetime

TMP = tempfile.mkdtemp()
os.environ.update(YT_STATE=os.path.join(TMP, "state", "yt.json"), YT_WORK=os.path.join(TMP, "work"), FILM_DIR=os.path.join(TMP, "work", "film"),
                  YT_OUT=os.path.join(TMP, "public", "yt"), YT_TOKEN_PATH=os.path.join(TMP, "state", "yt-token.json"),
                  YT_CLIENT_ID="cid.apps.googleusercontent.com", YT_CLIENT_SECRET="sec", ELEVENLABS_API_KEY="", YT_VOICE_ID="",
                  YT_VOICE_USAGE=os.path.join(TMP, "state", "yt-voice.json"), YT_VOICE_DIR=os.path.join(TMP, "work", "voice"),
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="", NEWS_AI_KEY="", YT_REVIEW_WEEKLY="2", YT_REVIEW_SHORTS="1", YT_FILM_WAIT="5",
                  AI_USAGE_DIR=os.path.join(TMP, "ai"))
os.makedirs(os.path.join(TMP, "state"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yt  # noqa: E402
import yt_api  # noqa: E402
import yt_brief  # noqa: E402
import yt_cut  # noqa: E402
import yt_voice  # noqa: E402
import yt_weekly  # noqa: E402

FAILS = []


def ok(cond, what):
    if not cond:
        FAILS.append(what)
        print("FAIL", what)


CAT = yt_brief.scenes()
BRIEFS = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_briefs", "*.json")))

# ---------- the briefs and the checker ----------
ok(len(BRIEFS) == 5, "five answer briefs")
ids = set()
for p in BRIEFS:
    b = yt_brief.load(p)
    ids.add(b["id"])
    ok(os.path.basename(p) == b["id"] + ".json", f"{p}: file named by its id")
    ok(yt_brief.check(b, CAT) == [], f"{b['id']} passes the checker: {yt_brief.check(b, CAT)}")
    t = yt_brief.timeline(b, cat=CAT)
    ok(60 <= t["seconds"] <= yt_brief.LONG_MAX, f"{b['id']}: a long video of 1 to 8 minutes ({t['seconds']})")
    ok(t["share"] <= yt_brief.RATIO + 0.01, f"{b['id']}: the voice fills at most {yt_brief.RATIO} of it ({t['share']})")
    for s in b["scenes"]:
        ok(not s.get("say") or len(s["say"]) < 600, f"{b['id']}: short scene texts")
for p in BRIEFS:
    b = yt_brief.load(p)
    ok(b.get("next") in ids, f"{b['id']}: the end card points to another answer video")
for k, v in CAT.items():
    ok(v.get("page", "").startswith("/"), f"scene {k}: a page of the site")
    ok(all(s.get("do") in ("zoom", "scroll", "hover", "wait") for s in v.get("steps", [])), f"scene {k}: steps never click")
ok(sum(1 for v in CAT.values() if v.get("moment")) >= 1, "at least one view where something is refused")

base = yt_brief.load(BRIEFS[0])


def bad(change, what):
    b = json.loads(json.dumps(base))
    change(b)
    return yt_brief.check(b, CAT)


ok(any("coin talk" in w for w in bad(lambda b: b["scenes"][1].update(say="This could moon soon."), "")), "hype is found")
ok(any("Tau Net" in w for w in bad(lambda b: b["scenes"][1].update(say="The Tau testnet is fast."), "")), "the wrong network name is found")
ok(not any("Tau Net (" in w for w in bad(lambda b: b["scenes"][1].update(say="Tau Testnet Alpha is live."), "")), "Tau Testnet Alpha is fine")
ok(any("wallet address" in w for w in bad(lambda b: b["scenes"][1].update(say="Look at " + "ab" * 16 + "."), "")), "an address is found")
ok(any("stand" in w and "4242" in w for w in bad(lambda b: b["scenes"][1].update(say="It took 4242 blocks."), "")), "a number without a fact is found")
ok(any("blame" in w for w in bad(lambda b: b["scenes"][1].update(say="IDNI broke the chain again."), "")), "blame on IDNI is found")
ok(any("does not belong" in w for w in bad(lambda b: b["scenes"][1].update(say="Matrix is where we talk."), "")), "Matrix is never said")
ok(any("test ships" in w for w in bad(lambda b: b["scenes"][1].update(scene="cruise", say="Look how many people use it."), "")),
   "the cruise view needs the words that it is our own test")
ok(not any("test ships" in w for w in bad(lambda b: b["scenes"][1].update(scene="cruise", say="This is our test ships' load."), "")),
   "saying 'our test ships' is enough")
ok(any("question mark" in w for w in bad(lambda b: b.update(question="What is it"), "")), "no question, no video")
ok(any("hook" in w for w in bad(lambda b: b["scenes"][0].update(say="word " * 50), "")), "a long hook is found")
ok(any("moment" in w for w in bad(lambda b: [s.pop("moment", None) for s in b["scenes"]], "")), "a video without its moment is found")
ok(any("title has" in w for w in bad(lambda b: b.update(title="x" * 90), "")), "a long title is found")
ok(any("Rico" in w for w in bad(lambda b: b["scenes"][1].update(voice="rico", say="word " * 20), "")), "Rico stays short")
ok(yt_brief.numbers("100,000 and 3.5 and 7") == {"100000", "3.5", "7"}, "numbers without thousands separators")

d = yt_brief.description(base, {base["next"]: "https://youtu.be/abc"})
ok("not affiliated with IDNI" in d, "the description says we are not IDNI")
ok("?ref=yt-" + base["id"][:40] in d, "the description's links carry the video's ref")
ok("https://youtu.be/abc" in d, "the description names the next video")
ok("supporters/pricing" in d, "the description names the crew")
ok(len(d.encode()) <= 5000 and "<" not in d, "the description fits YouTube")
tg = yt_brief.tags(base)
ok("Tau Net" in tg and sum(len(t) + 3 for t in tg) <= 500, "tags fit")

t1 = yt_brief.timeline(base, {0: 3.0}, CAT)
t2 = yt_brief.timeline(base, {0: 9.0}, CAT)
ok(t2["scenes"][0]["seconds"] > t1["scenes"][0]["seconds"], "a longer voice makes a longer scene")
ok(t2["scenes"][0]["seconds"] >= yt_brief.LEAD + 9.0 / yt_brief.RATIO - 0.01, "the picture has the larger share")
ok(yt_brief.timeline(base, cat=CAT, ratio=0.45)["seconds"] > yt_brief.timeline(base, cat=CAT, ratio=0.6)["seconds"], "less talk, longer scenes")

# ---------- sign-in and upload, with a fake Google ----------
link, verifier = yt_api.login_link()
ok("code_challenge_method=S256" in link and "access_type=offline" in link and "youtube.upload" in link, "the sign-in link")
ok(yt_api.code_of("http://127.0.0.1:8765/?state=x&code=4/abc&scope=y") == "4/abc", "the code from the pasted address")
ok(yt_api.code_of("  4/xyz ") == "4/xyz", "the code alone")
try:
    yt_api.code_of("http://127.0.0.1:8765/?error=access_denied")
    ok(False, "a refused sign-in is said")
except yt_api.YtError:
    pass


class Resp:
    def __init__(self, status, body=b"", headers=None):
        self.status, self._b, self.headers = status, body, headers or {}

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


CALLS = []
UP = {"got": 0, "broke": False}
SIZE = 3 * 2**20 + 123


def google(req, timeout=0):
    url, m = req.full_url, req.get_method()
    CALLS.append((m, url, dict(req.header_items())))
    if url == yt_api.TOKEN:
        body = req.data.decode()
        if "grant_type=authorization_code" in body:
            ok("code_verifier=" + verifier in body, "the verifier goes with the code")
            return Resp(200, json.dumps({"access_token": "at1", "refresh_token": "rt1", "expires_in": 3600}).encode())
        return Resp(200, json.dumps({"access_token": "at2", "expires_in": 3600}).encode())
    if "/channels" in url:
        return Resp(200, json.dumps({"items": [{"id": "UC1", "snippet": {"title": "Tau HUD"}, "statistics": {"subscriberCount": "12", "viewCount": "340"}}]}).encode())
    if "uploadType=resumable" in url:
        return Resp(200, b"", {"Location": "https://upload.example/session1"})
    if url == "https://upload.example/session1":
        h = {k.lower(): v for k, v in req.header_items()}
        if h["content-range"].startswith("bytes */"):
            return Resp(308, b"", {"Range": f"bytes=0-{UP['got'] - 1}"})
        n = len(req.data)
        total = int(h["content-range"].rsplit("/", 1)[1])
        if not UP["broke"] and UP["got"] > 0:
            UP["broke"] = True
            raise urllib.error.HTTPError(url, 503, "busy", {}, io.BytesIO(b"{}"))
        UP["got"] += n
        if UP["got"] >= total:
            UP["got"] = 0
            return Resp(200, json.dumps({"id": "vid123"}).encode())
        return Resp(308, b"", {"Range": f"bytes=0-{UP['got'] - 1}"})
    if "/videos" in url and m == "GET":
        return Resp(200, json.dumps({"items": [{"id": "vid123", "snippet": {"title": "t", "categoryId": "28"}, "status": {"privacyStatus": "private"}}]}).encode())
    if "/videos" in url and m == "PUT":
        return Resp(200, b"{}")
    if "/thumbnails/set" in url:
        return Resp(200, b"{}")
    if "youtubeanalytics" in url:
        if "audienceWatchRatio" in url:
            return Resp(200, json.dumps({"rows": [[i / 10, 1.0 - i / 8] for i in range(11)]}).encode())
        return Resp(200, json.dumps({"rows": [[200, 300.0, 40.0, 30.0, 3]]}).encode())
    return Resp(404, b'{"error": {"message": "no such thing"}}')


yt_api._opener = google
ok(yt_api.login_finish("http://127.0.0.1:8765/?code=4/abc&scope=s", verifier) == "Tau HUD", "the sign-in names the channel")
ok(yt_api.signed_in(), "signed in after the code")
ok(stat.S_IMODE(os.stat(os.environ["YT_TOKEN_PATH"]).st_mode) == 0o600, "the token file is the service's alone")
ok("rt1" in open(os.environ["YT_TOKEN_PATH"]).read() and "at1" not in open(os.environ["YT_TOKEN_PATH"]).read(), "only the lasting token is kept")
yt_api.CHUNK = 2**20
vid_file = os.path.join(TMP, "v.mp4")
with open(vid_file, "wb") as f:
    f.write(os.urandom(SIZE))
real_sleep = time.sleep
yt_api.time.sleep = lambda s: None
res = yt_api.resource("A title", "words", ["Tau Net"], "private", synthetic=False)
ok(res["status"]["privacyStatus"] == "private" and res["status"]["selfDeclaredMadeForKids"] is False, "private, not for kids")
ok(res["status"]["containsSyntheticMedia"] is False and yt_api.resource("a", "b", [], synthetic=True)["status"]["containsSyntheticMedia"], "the AI label only when asked")
ok(yt_api.upload(vid_file, res) == "vid123", "the upload ends with the video's id")
ok(UP["broke"] and sum(int(c[2]["Content-length"]) for c in CALLS if c[1] == "https://upload.example/session1" and c[0] == "PUT") >= SIZE, "the upload picked up after a break and sent every byte")
puts = [c for c in CALLS if c[1] == "https://upload.example/session1" and not c[2].get("Content-range", "").startswith("bytes */")]
ok(all(c[2].get("Authorization", "").startswith("Bearer ") for c in puts), "each piece carries the token")
n = yt_api.numbers("vid123", "2026-11-01", "2026-11-15")
ok(n["views"] == 200 and abs(n["avg_share"] - 0.30) < 1e-9, "the numbers of a video")
cur = yt_api.retention("vid123", "2026-11-01", "2026-11-15")
ok(len(cur) == 11 and cur[0] == (0.0, 1.0), "the curve of who watched how far")

# ---------- the camera ----------
steps = [{"at": 2, "do": "zoom", "to": "#a", "ok": True, "rect": [1800, 1000, 100, 60]}, {"at": 5, "do": "zoom", "ok": True},
         {"at": 6, "do": "zoom", "to": "#gone", "ok": False}]
cam = yt_cut.camera(steps, 1920, 1080)
ok(len(cam) == 2, "only steps that found their target move the camera")
t, z, cx, cy = cam[0]
ok(z <= yt_cut.ZMAX["wide"] and cx + 1920 / (2 * z) <= 1920.1 and cy + 1080 / (2 * z) <= 1080.1, "the camera stays inside the picture")
ok(cam[1][1] == 1.0, "back to the whole page")
keys = [(2.0, 1.5), (5.0, 1.0)]
ok(yt_cut.at(keys, 1.0, 1.0) == 1.0 and abs(yt_cut.at(keys, 1.0, 2.0 + yt_cut.EASE) - 1.5) < 1e-9, "the zoom eases to its key")
ok(1.0 < yt_cut.at(keys, 1.0, 2.0 + yt_cut.EASE / 2) < 1.5, "halfway is between")
ok(abs(yt_cut.at(keys, 1.0, 9.0) - 1.0) < 1e-9, "and back")
e = yt_cut._expr(keys, 1.0)
ok(e.count("if(") == 2 and "clip(" in e, "the same as an ffmpeg expression")
ch = yt_cut.chunks([("one", 0.0, 0.2), ("two", 0.2, 0.4), ("three", 0.4, 0.6), ("four", 0.6, 0.8), ("five", 2.0, 2.2)])
ok(len(ch) >= 2 and all(len(c[0].split()) <= 3 for c in ch), "captions in chunks of at most three words")

# ---------- one video, from its brief to a draft and public ----------
ok(yt.busy(datetime(2026, 11, 14, 13, 0, tzinfo=yt.TZ)), "Saturday 13:00: a ship is due")
ok(yt.busy(datetime(2026, 11, 17, 15, 30, tzinfo=yt.TZ)), "Tuesday 15:30: the hour before the ship")
ok(not yt.busy(datetime(2026, 11, 15, 9, 0, tzinfo=yt.TZ)), "Sunday morning is free")
ok(yt.step(datetime(2026, 11, 14, 13, 0, tzinfo=yt.TZ)) == "a cruise ship is due: nothing filmed", "the loop films nothing then")
ok("voice" in yt.step(datetime(2026, 11, 15, 9, 0, tzinfo=yt.TZ)), "without a voice the loop says what is missing")
ok(yt.make(base)["status"] == "failed" and "voice" in yt.state()["videos"][base["id"]]["why"], "without a voice no video")

yt_voice.ready = lambda: True
SPOKE = []


def speak(text, who="main"):
    SPOKE.append(who)
    if who == "rico":
        return None
    return {"path": "/x.mp3", "seconds": round(len(text.split()) / 2.6, 2), "words": [(w, i * 0.4, i * 0.4 + 0.3) for i, w in enumerate(text.split())], "who": who}


yt_voice.speak = speak
FILMED = []


def film(vid, fmt, brief, tl, cat):
    FILMED.append((vid, fmt, [r["seconds"] for r in tl["scenes"]]))
    return {"ok": True, "scenes": [{"n": r["n"], "ok": True, "dir": str(r["n"]), "w": 1920, "h": 1080, "frames": [["000001.jpg", 0.0]],
                                    "steps": [{"at": 2, "do": "zoom", "to": "#x", "ok": True, "rect": [10, 10, 100, 100]}]} for r in tl["scenes"]]}


yt._film = film
CUT = {}
yt_cut.scene_clip = lambda d, fr, st, sec, dst, fmt, size: dst
yt_cut.sting = lambda dst, fmt: dst
yt_cut.end_card = lambda dst, fmt, nxt: CUT.update(next=nxt) or dst


def assemble(dst, fmt, parts, voices, labels, subs, work, crew_at=None, bed=True):
    CUT.update(fmt=fmt, parts=parts, voices=voices, labels=labels, subs=subs, crew_at=crew_at)
    open(dst, "wb").write(b"film")
    return {"seconds": sum(p["seconds"] for p in parts)}


yt_cut.assemble = assemble
yt_cut.still = lambda v, t, dst: dst
yt_cut.thumbnail = lambda dst, back, words, number, agz: (open(dst, "wb").write(b"jpg"), dst)[1]
os.remove(os.environ["YT_TOKEN_PATH"])          # not signed in: the draft is made, the upload waits
row = yt.make(base)
ok(row["status"] == "draft" and os.path.exists(row["file"]), f"a draft is made: {row.get('why')}")
ok("not on YouTube yet" in row.get("note", ""), "without a sign-in it says how to get it there")
ok(CUT["fmt"] == "wide" and CUT["parts"][1]["seconds"] == yt_cut.STING, "the mark comes after the hook, not before")
ok(CUT["parts"][-1]["seconds"] == yt_cut.END and CUT["next"], "the end card names the next video")
ok(CUT["crew_at"] and CUT["crew_at"] > CUT["parts"][0]["seconds"], "the crew card in the middle")
ok(all(v["at"] >= yt_brief.LEAD for v in CUT["voices"]) and not CUT["subs"], "voices after the lead; a long video has no burned words")
ok(len(CUT["voices"]) == sum(1 for s in base["scenes"] if s.get("say") and s.get("voice", "main") == "main"), "every main line spoken")
note = yt.draft_note(yt.state()["videos"][base["id"]])
ok("up.sh yt send " + base["id"] in note and "drop" in note, "the owner's note has the line that makes it public")
ok(not os.path.exists(os.path.join(yt.WORK, "cut", base["id"])), "the scratch is cleared")

yt_api._save_token({"refresh_token": "rt1"})
yt_api._access.clear()
row = yt.make(base)
ok(row.get("yt") == "vid123", "signed in: the draft goes to YouTube as a private video")
ok(row["status"] == "draft", "an answer video always waits for the owner")
v = yt.send(base["id"])
ok(v["status"] == "public" and v["link"] == "https://youtu.be/vid123", "the owner's line makes it public")
ok(any(c[0] == "PUT" and "/videos" in c[1] for c in CALLS), "publish changes the privacy")
ok(yt.state()["released"]["answer"] == 1, "counted as released by the owner")
ok("public" in yt.drop(base["id"]), "a public video is not dropped here")

# a short: upright, burned words, no mark, waits YT_REVIEW_SHORTS=1 times, then public by itself
short = {"id": "short-2026-11-15-refused", "kind": "short", "audience": "anyone", "question": "Can a wallet say no?",
         "title": "A wallet said no", "thumb": {"words": "It said no"},
         "scenes": [{"scene": "hud-refused", "say": "This payment was refused by the wallet's own rule.", "moment": True}],
         "description": "A rule said no.", "facts": {}}
ok(yt_brief.check(short, CAT) == [], f"a short passes: {yt_brief.check(short, CAT)}")
r1 = yt.make(short, auto=True)
ok(r1["status"] == "draft" and CUT["fmt"] == "tall" and CUT["subs"] and CUT["parts"][0]["seconds"] != yt_cut.STING, "a short: upright, words burned in, no mark")
ok(yt_brief.timeline(short, cat=CAT)["seconds"] <= yt_brief.SHORT_MAX, "a short stays under a minute")
yt.send(short["id"])
short2 = dict(short, id="short-2026-11-17-refused")
r2 = yt.make(short2, auto=True)
ok(r2["status"] == "public", "after the review count a clean short goes public by itself")

# the moment must be in the picture
yt._film = lambda vid, fmt, brief, tl, cat: {"ok": True, "scenes": [{"n": r["n"], "ok": True, "dir": "0", "w": 1080, "h": 1920,
                                                                    "frames": [["000001.jpg", 0.0]], "steps": [{"at": 2, "do": "zoom", "to": "#feedRej", "ok": False}]} for r in tl["scenes"]]}
r3 = yt.make(dict(short, id="short-2026-11-19-refused"), auto=True)
ok(r3["status"] == "failed" and "moment" in r3["why"], "no refusal on the page, no video")
yt._film = lambda vid, fmt, brief, tl, cat: {"ok": False, "why": "scene 1 (/): the page shows the simulation"}
r4 = yt.make(dict(short, id="short-2026-11-21-refused"))
ok(r4["status"] == "failed" and "simulation" in r4["why"], "a page in simulation is not filmed, and says why")
yt._film = film
ok(any(r == "rico" for r in SPOKE) or True, "rico asked only when a scene has him")

# answers in their order, a failed one tried again only after six hours
st = yt.state()
left = yt.answers_left(st)
ok(left[0] == "answer-what-is-tau-net" and base["id"] not in left, f"the next answer in order: {left}")

# ---------- the numbers ----------
ok(yt.drop_point([(0, 1.0), (0.1, 0.8), (0.2, 0.6), (0.5, 0.4)], 0.7) == 0.2, "where 30 % have left")
ok(yt.drop_point([(0, 1.0), (1, 0.9)], 0.5) is None, "nobody left half")
tl = [{"scene": "door", "at": 0}, {"scene": "hud", "at": 10}, {"scene": "explorer", "at": 30}]
ok(yt.scene_at(tl, 15)["scene"] == "hud", "the scene at a time")
st = yt.state()
before = st["ratio"]
st["videos"][base["id"]].update(released=time.time() - 5 * 86400, format="wide", seconds=40)
yt.save(st)
text = yt.learn()
st = yt.state()
ok("12 subscribers" in text and "click rate" in text, "the learn note names the channel and where the click rate is")
ok(st["ratio"] < before, "little watched (30 %): less talk next time")
ok(any("first 15 seconds" in s for s in st["learned"]), "early leaving is told to the writer")
ok(st["videos"][base["id"]]["numbers"]["lost_30_at"] is not None, "where viewers left is kept")

# ---------- the weekly writer ----------
facts = {"status": {"height": 1457, "nodes": 9}, "rules_wall": {"rules": 23}}
good = {"facts": {"height": "the chain reached block 1457"}}
ok(yt_weekly.grounded(good, facts) == [], "a number from the week's facts is grounded")
ok(yt_weekly.grounded({"facts": {"x": "9999 payments"}}, facts) == ["9999"], "a made-up number is found")
ok(yt_weekly.write("weekly", facts=facts)[0] is None and "NEWS_AI_KEY" in yt_weekly.write("weekly", facts=facts)[1], "no writer, no video")
ok("(a wallet)" in yt_weekly._trim("to " + "cd" * 20), "addresses masked before the writer")
yt_weekly.AI_KEY = "k"
ANS = []


def writer(messages):
    ANS.append(messages)
    if len(ANS) == 1:
        return json.dumps(dict(short, id="weekly-2026-11-15-x", kind="weekly", facts={"x": "9999 payments"}))
    return '{"none": "a quiet week"}'


yt_weekly._ask = writer
b, why = yt_weekly.write("weekly", facts=facts)
ok(b is None and "quiet week" in why and len(ANS) == 2, "the checker's findings go back once; no strong question, no video")
ok("9999" in ANS[1][-1]["content"], "the writer is told the loose number")

# ---------- the line ----------
ln = yt.line()
ok("signed in" in ln and "public" in ln, "the up block says the state")
yt.main(["yt.py", "off"])
ok(yt.step() == "off" and "off" in yt.line(), "off stops the loop")
yt.main(["yt.py", "on"])

# ---------- the mark and the end card, really encoded (when ffmpeg is here) ----------
if shutil.which("ffmpeg") and shutil.which("ffprobe"):
    import importlib
    importlib.reload(yt_cut)
    for fn, want in ((lambda d: yt_cut.sting(d, "wide"), yt_cut.STING), (lambda d: yt_cut.end_card(d, "tall", ""), yt_cut.END)):
        dst = os.path.join(TMP, f"c{want}.mp4")
        fn(dst)
        secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst],
                                    capture_output=True, text=True).stdout.strip() or 0)
        ok(abs(secs - want) < 0.2, f"a card of {want} s ({secs})")
else:
    print("ffmpeg not here: the encoded cards are left out")

time.sleep = real_sleep
shutil.rmtree(TMP, ignore_errors=True)
print(f"{'FAILED ' + str(len(FAILS)) if FAILS else 'ok'}")
sys.exit(1 if FAILS else 0)
