"""Unit test of the pirates' clip (trick_clip.py), no network: only refused tricks count as tries (a timeout or a skip
never does), a refusal with another answer is shown as it was, a trick that got through (or one held back) means no
clip at all and a private note, each visit gets one clip only, an old visit none, X only while the day has room, the
X text has no link, every frame draws (and the clip encodes when ffmpeg is here).

Run: python test_trick_clip.py
"""
import json
import os
import shutil
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
ART = os.path.join(TMP, "art")
os.makedirs(ART)
from PIL import Image  # noqa: E402
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "isle.jpg"))
json.dump({"scenes": {"island": "isle.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
SHIPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "art", "ships")
os.environ.update(BLOG_ART=ART, BLOG_SHIPS=SHIPS, PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="",
                  CHAT_AI_KEY="", TELEGRAM_BOT_TOKEN="", X_API_KEY="", STATE_PATH=os.path.join(TMP, "alerts.json"), X_DAILY_CAP="8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import trick_clip as tc  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


V = "2026-11-10-pirates"
T0 = 1794330000   # Tuesday 10 November 2026, 18:00 German time


def visit(extra=(), over=True):
    rows = [{"t": T0, "visit": V, "kind": "landed"}]
    for i, k in enumerate(tc.ORDER):
        code = {"overspend": "INSUFFICIENT_FUNDS", "replay": "INVALID_SEQUENCE", "expired": "TX_EXPIRED", "stale": "TX_EXPIRED",
                "forged": "INVALID_SIGNATURE", "impostor": "TX_INVALID", "freeride": "FEE_LIMIT_TOO_LOW", "giant": "TX_INVALID"}[k]
        for j in range(3):
            rows.append({"t": T0 + 100 + i * 10 + j, "visit": V, "kind": "trick", "trick": k, "what": tc.WHAT[k], "ok": False,
                         "right": True, "code": code, "expect": [code]})
    rows += list(extra)
    if over:
        rows.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": {}})
    return rows


# ---------- tally ----------
f = tc.tally(visit())
check(f["refused"] == 24 and f["right"] == 24 and f["kinds"] == 8 and not f["held"] and f["over"], "24 refused tries over 8 tricks")
f = tc.tally(visit([{"t": T0 + 900, "visit": V, "kind": "trick", "trick": "replay", "ok": None, "note": "nothing to replay yet"},
                    {"t": T0 + 901, "visit": V, "kind": "trick", "trick": "forged", "ok": None, "note": "no answer from the node to sendtx"}]))
check(f["refused"] == 24 and f["tricks"]["replay"]["refused"] == 3, "a skipped or unanswered trick is no try")
f = tc.tally(visit([{"t": T0 + 902, "visit": V, "kind": "trick", "trick": "giant", "ok": False, "right": False, "code": "TX_REJECTED",
                     "expect": ["TX_INVALID", "INVALID_PARAMS"]}]))
check(f["refused"] == 25 and f["right"] == 24 and f["tricks"]["giant"]["codes"].get("TX_REJECTED") == 1, "another answer: refused, shown as it was")
check(tc.tally(visit([{"t": T0 + 903, "visit": V, "kind": "trick", "trick": "stale", "ok": True, "through": True}]))["held"],
      "a trick that got through: held")
check(tc.tally(visit([{"t": T0 + 903, "visit": V, "kind": "held", "held": True, "ok": None}]))["held"], "a masked public entry: held")
check(not tc.tally(visit(over=False))["over"], "a visit still going is not over")
only = [r for r in visit() if r.get("trick") in (None, "overspend", "giant")]
check(tc.tally(only)["kinds"] == 2, "tricks without a try are left out of the clip")

# ---------- texts ----------
t = tc.texts(tc.tally(visit()))
check("http" not in t["x"] and len(t["x"]) <= 280, "X: no link, fits")
check("24 refused" in t["telegram"] and "not affiliated with IDNI" in t["telegram"] and f"visit={V}" in t["telegram"], "Telegram: numbers, foot, logbook")
check(len(t["telegram"]) <= 1024, "Telegram caption within 1024")
t = tc.texts(tc.tally(visit([{"t": T0 + 902, "visit": V, "kind": "trick", "trick": "giant", "ok": False, "right": False, "code": "TX_REJECTED"}])))
check("24 with the answer it should give, 1 with another" in t["telegram"], "another answer named in the text")

# ---------- frames and the clip ----------
c = tc.Clip(tc.tally(visit()), ART, SHIPS, "Tue 10 Nov")
check(len(c.crew) == 8 and all(len(p) == 2 for p in c.crew.values()), "each trick's pirate, both frames, from the crew sheet")
for s in (0.3, 2.0, 3.0, 3.8, 10.0, c.length - 0.5):
    im = c.frame(s)
    check(im.size == (tc.W, tc.H), f"frame at {s} s draws")
check(abs(c.length - (2.6 + 8 * 2.0 + 4.0)) < 0.01, "about 22 seconds")
if shutil.which("ffmpeg"):
    out = c.render(os.path.join(TMP, "clip.mp4"))
    check(os.path.getsize(out) > 100_000, "the clip encodes")
else:
    print("skip the clip's encoding: no ffmpeg here")

# ---------- once per visit, by itself ----------
LOG = {"visits": [V, "2026-11-07-queen"]}
held_entries = []
entries = visit()


def fake_get(path):
    if path.startswith("/cruise/log?n="):
        return LOG
    if path.startswith("/cruise/log?visit="):
        return {"entries": entries}
    if path == "/cruise/held":
        return {"entries": held_entries}
    raise AssertionError(path)


blog.get = fake_get
posted, told, made = [], [], []
tc.post = lambda path, t: posted.append(t) or ["telegram: posted", "x: posted"]
tc.make = lambda f, out: made.append(f) or out
st, saves = {}, []
save = lambda s: saves.append(json.dumps(s))
NOW = T0 + 5400 + 600
check(tc.step(NOW, st, save, told.append) == V and len(posted) == 1, "posted once after the visit")
check("posting" in saves[0] and st["clipped"][V]["result"][0] == "telegram: posted", "marked before posting, result kept")
check(tc.step(NOW + 600, st, save, told.append) is None and len(posted) == 1, "never a second time")
check(any("posted by itself" in x for x in told), "the owner hears it was posted")

st, posted, told = {}, [], []
held_entries.append({"visit": V, "i": 7})
check(tc.step(NOW, st, save, told.append) == V and not posted, "a held-back finding (only the server sees it): no clip")
check(told and "NOT made" in told[0], "the owner hears why there is no clip")
held_entries.clear()

st, posted = {}, []
check(tc.step(T0 + 5400 + 13 * 3600, st, save, told.append) is None and not posted and "too old" in st["clipped"][V]["result"], "an old visit: no clip")

st, posted = {}, []
entries = visit(over=False)
check(tc.step(NOW, st, save, told.append) is None and not posted and V not in st.get("clipped", {}), "a visit still going: wait")
entries = visit()

LOG = {"visits": ["2026-11-11-dryrun"]}
st, posted = {}, []
check(tc.step(NOW, st, save, told.append) is None and not posted, "other ships get no clip")

os.environ["TRICK_CLIP"] = "false"
import importlib  # noqa: E402
tc2 = importlib.reload(tc)
check(tc2.step(NOW, {}, save, told.append) is None, "TRICK_CLIP=false: nothing")
os.environ["TRICK_CLIP"] = "true"
tc = importlib.reload(tc)

# ---------- X room ----------
day = time.strftime("%Y-%m-%d", time.gmtime())
json.dump({"x": {"day": day, "today": 6}}, open(os.environ["STATE_PATH"], "w"))
check(tc.x_room(), "6 of 8 X posts today: room")
json.dump({"x": {"day": day, "today": 7}}, open(os.environ["STATE_PATH"], "w"))
check(not tc.x_room(), "7 of 8: the last one stays for the chain's news")
json.dump({"x": {"day": "2000-01-01", "today": 8}}, open(os.environ["STATE_PATH"], "w"))
check(tc.x_room(), "yesterday's count does not hold today back")
os.remove(os.environ["STATE_PATH"])
check(tc.x_room(), "no count yet: room")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)
