"""Unit test of the Kling clips (kling.py, kling_island.py), no network: Kling's token is a valid HS256 JWT; without a key
nothing is asked; a clip is asked once and picked up later; the first KLING_REVIEW clips of a public use are drafts,
the island loop never; the month's cap holds over every service's file; a model without a last frame is asked again
without one; a failed clip is never asked again; the motion mask finds where a clip moves and only there; the living
island is published for the painting that shows and refused when too much moves; a trailer comes once per new painting;
the loop and the card helpers make clips of the right length (when ffmpeg is here).

Run: python test_kling.py
"""
import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
ART = os.path.join(TMP, "art")
os.makedirs(ART)
from PIL import Image, ImageDraw  # noqa: E402
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "island-36-abc.jpg"))
json.dump({"scenes": {"island": "island-36-abc.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
os.environ.update(KLING_API_KEY="", KLING_ACCESS_KEY="", KLING_SECRET_KEY="", KLING_STATE_DIR=os.path.join(TMP, "state"),
                  KLING_OUT=os.path.join(TMP, "public", "kling"), KLING_MONTH_CAP="5", KLING_REVIEW="2", BLOG_ART=ART,
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="", NEWS_AI_KEY="", PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kling  # noqa: E402
import kling_island  # noqa: E402

failed = 0


def check(name, ok, detail=""):
    global failed
    print(("ok   " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))
    failed += 0 if ok else 1


FF = shutil.which("ffmpeg") is not None

# ---------- the token ----------
tok = kling.jwt("AK123", "SK456", now=1_800_000_000)
h, b, s = tok.split(".")
pad = lambda x: x + "=" * (-len(x) % 4)  # noqa: E731
body = json.loads(base64.urlsafe_b64decode(pad(b)))
sig = base64.urlsafe_b64encode(hmac.new(b"SK456", f"{h}.{b}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
check("jwt: HS256 signed with the secret", s == sig)
check("jwt: iss = access key, 30 min, from 5 s ago", body == {"iss": "AK123", "exp": 1_800_001_800, "nbf": 1_799_999_995}, body)

# ---------- no key: nothing ----------
check("no key: off", kling.ask("x", "ship", b"", "p")["status"] == "off")
check("no key: the up line says so", "no key yet" in kling.line())

# ---------- a key, and a fake Kling ----------
kling.API_KEY = "test-key"
calls = []
TASKS = {}


def fake_call(method, path, body=None):
    calls.append((method, path, body))
    if method == "POST":
        if body.get("image_tail") and FAKE["no_tail"]:
            raise RuntimeError("kling /v1/videos/image2video: code 1201 image_tail not supported")
        tid = f"t{len(TASKS) + 1}"
        TASKS[tid] = {"task_status": "submitted"}
        return {"task_id": tid, "task_status": "submitted"}
    return TASKS[path.rsplit("/", 1)[1]]


FAKE = {"no_tail": False}
kling._call = fake_call
CLIP = os.path.join(TMP, "clip.mp4")


def make_clip(path, moving_box=True, seconds=2, all_moves=False):
    """A test clip: the painting's blue, a white box sliding in the lower left (or everything flickering)."""
    if not FF:
        open(path, "wb").write(b"not a video")
        return path
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "320x180", "-r", "25",
                          "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(seconds * 25):
        im = Image.new("RGB", (320, 180), (40, 120, 160) if not all_moves else ((i * 37) % 255, (i * 91) % 255, 160))
        if moving_box:
            ImageDraw.Draw(im).rectangle([20 + i, 130, 50 + i, 160], fill=(255, 255, 255))
        p.stdin.write(im.tobytes())
    p.stdin.close()
    p.wait()
    return path


def fake_fetch(url, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(FAKE.get("src", CLIP), dst)
    return dst


kling.fetch = fake_fetch
make_clip(CLIP)


def finish(tid, seconds="5"):
    TASKS[tid] = {"task_status": "succeed", "task_result": {"videos": [{"url": "https://cdn.example/x.mp4", "duration": seconds}]}}


img = Image.new("RGB", (1600, 900), (10, 20, 30))
check("a key: the test clip is on (it is no use of KLING_USES)", kling.enabled("test") and not kling.enabled("nope"))
j = kling.ask("ship-a", "ship", img, "calm sea", tail=True)
check("asked: submitted with the last frame", j["status"] == "submitted" and j["tail"] and calls[-1][2].get("image_tail"), j)
check("asked: the picture as base64 JPEG, no data: prefix", base64.b64decode(calls[-1][2]["image"])[:2] == b"\xff\xd8")
check("first public clip is a draft", j["draft"] is True)
n = len(calls)
j = kling.ask("ship-a", "ship", img, "calm sea")
check("asked again: only looked at, not a new clip", j["status"] == "submitted" and calls[n][0] == "GET" and len(calls) == n + 1)
finish("t1")
j = kling.ready("ship-a")
check("done: fetched, ready", j and os.path.exists(j["file"]) and j["seconds"] == 5.0, j)
check("done: fetched once, then not looked up again", kling.poll("ship-a")["status"] == "succeed" and calls[-1][0] == "GET")
j2 = kling.ask("ship-b", "ship", img, "calm sea")
j3 = kling.ask("ship-c", "ship", img, "calm sea")
check("second is a draft, third posts by itself", j2["draft"] and not j3["draft"], (j2, j3))
j4 = kling.ask("island-x", "island", img, "loop")
check("the living island is never a draft (not a post)", not j4["draft"])

# a failed clip is not asked again
TASKS["t2"] = {"task_status": "failed", "task_status_msg": "risk control"}
check("failed: so marked", kling.poll("ship-b")["status"] == "failed")
n = len(calls)
check("failed: never asked again", kling.ask("ship-b", "ship", img, "x")["status"] == "failed" and len(calls) == n)

# no last frame with this model: asked once more without it
FAKE["no_tail"] = True
j = kling.ask("pirate-a", "pirate", img, "mist", tail=True)
check("no last frame: asked without it", j["status"] == "submitted" and j["tail"] is False and "image_tail" not in calls[-1][2], j)
FAKE["no_tail"] = False

# the month's cap, over every service's file
other = os.path.join(os.environ["KLING_STATE_DIR"], "kling-agorzilla.json")
json.dump({"jobs": {"agorzilla-1": {"kind": "agorzilla", "task": "z", "at": round(time.time()), "status": "succeed"}}}, open(other, "w"))
check("cap: counts every service", kling.this_month() == 6, kling.this_month())
j = kling.ask("ship-d", "ship", img, "x")
check("cap: no more clips this month", j["status"] == "capped", j)
check("up line: the month and the cap", "6 of 5 clips this month" in kling.line(), kling.line())
os.remove(other)
kling.CAP = 50

# ---------- the motion mask ----------
if FF:
    mp = os.path.join(TMP, "m.png")
    moving = kling_island.mask(CLIP, mp)
    m = Image.open(mp).convert("L").resize((160, 90))
    check("mask: a small share moves", 0.0 < moving < 0.2, moving)
    check("mask: white where the box slid", m.getpixel((40, 72)) > 200, m.getpixel((40, 72)))
    check("mask: black on the still sea", m.getpixel((130, 20)) < 10, m.getpixel((130, 20)))
    loud = make_clip(os.path.join(TMP, "loud.mp4"), all_moves=True)
    check("mask: everything flickering = nearly all moves", kling_island.mask(loud, mp) > 0.9)
else:
    print("skip mask (no ffmpeg)")

# ---------- the living island ----------
told = []
st = kling.state()
st["jobs"] = {}
kling.save(st)
kling_island.step(tell=told.append)
k = "island-island-36-abc"
check("island: asked for the painting that shows, 10 s pro with the last frame",
      kling.state()["jobs"].get(k, {}).get("mode") == "pro" and calls[-2][2]["duration"] == "10" if len(calls) > 1 else False)
check("trailer: the new painting gets one too (kept just now)", "trailer-island-36-abc" in kling.state()["jobs"])
check("island: nothing public yet", not os.path.exists(os.path.join(kling.OUT, "island.json")))
if FF:
    tid_island = kling.state()["jobs"][k]["task"]
    finish(tid_island, "2")
    kling_island.step(tell=told.append)
    info = json.load(open(os.path.join(kling.OUT, "island.json")))
    check("island: published for its painting", info["of"] == "island-36-abc.jpg" and os.path.exists(os.path.join(kling.OUT, info["video"]))
          and os.path.exists(os.path.join(kling.OUT, info["mask"])), info)
    check("island: the owner told, with the off line", any("up.sh kling off island" in t for t in told), told)
    n = len(told)
    kling_island.step(tell=told.append)
    check("island: once only", len(told) == n)
    # off again
    kling.main(["off", "island"])
    check("off: island.json gone", not os.path.exists(os.path.join(kling.OUT, "island.json")))
    kling_island.step(tell=told.append)
    check("off: not made again for the same painting", not os.path.exists(os.path.join(kling.OUT, "island.json")))
    # a new painting where everything moves: refused
    Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "island-37-def.jpg"))
    json.dump({"scenes": {"island": "island-37-def.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
    kling_island.step(tell=told.append)
    FAKE["src"] = os.path.join(TMP, "loud.mp4")
    finish(kling.state()["jobs"]["island-island-37-def"]["task"], "2")
    kling_island.step(tell=told.append)
    check("island: too much moving is not shown", not os.path.exists(os.path.join(kling.OUT, "island.json")) and any("NOT shown" in t for t in told), told[-1:])
    FAKE.pop("src")
    # the trailer of island 36 is a draft (the first of its kind), with its post kept for up kling send
    finish(kling.state()["jobs"]["trailer-island-36-abc"]["task"], "2")
    json.dump({"scenes": {"island": "island-36-abc.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
    st = kling.state(); st["seen_island"] = None; st.pop("seen_island"); kling.save(st)
    kling_island.step(tell=told.append)
    tj = kling.state()["jobs"]["trailer-island-36-abc"]
    check("trailer: a draft with its texts and the send line", tj.get("video", "").endswith("/drafts/trailer-island-36-abc.mp4")
          and tj["post"].get("x") and "http" not in tj["post"]["x"] and any("up.sh kling send trailer-island-36-abc" in t for t in told), tj)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tj["video"]],
                               capture_output=True, text=True).stdout or 0)
    check("trailer: the clip, then the card held", 5.5 < dur < 7.5, dur)
    # loop helper
    lp = kling.loop(CLIP, os.path.join(TMP, "loop.mp4"), 2.0, fade=0.5)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", lp], capture_output=True, text=True).stdout)
    check("loop: fade seconds shorter", 1.3 < d < 1.7, d)
else:
    print("skip island publishing (no ffmpeg)")

# an old painting when this first runs: no trailer
st = kling.state(); st.pop("seen_island", None); st["jobs"] = {}; kling.save(st)
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "island-30-old.jpg"))
os.utime(os.path.join(ART, "island-30-old.jpg"), (time.time() - 10 * 86400,) * 2)
json.dump({"scenes": {"island": "island-30-old.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
kling_island.step(tell=told.append)
check("trailer: none for a painting live for days already", "trailer-island-30-old" not in kling.state()["jobs"]
      and kling.state().get("seen_island") == "island-30-old.jpg")

# ---------- the cruise announcement falls back to the photo ----------
import cruise_crier  # noqa: E402
check("ship clip: none without a finished clip", cruise_crier.ship_clip("2026-11-11-dryrun", {}, "/nope.jpg") is None)

shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("all passed" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)
