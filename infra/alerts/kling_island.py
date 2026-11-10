"""The island painting, alive, and a trailer when it is new (kling.py; the blog service calls step() every 10 minutes).

  living island  For the painting the game shows (index.json "scenes" "island"), one 10 s clip in which only what moves
                 by nature moves: ripples and glints on the sea, smoke from the chimneys, palm fronds in a breeze, lamps.
                 Its last frame is the painting again, so it loops without a seam. From the clip a motion mask is
                 measured (where any frame differs from the first one), softened and kept beside it:
                 tauhud.com/rabbit/ draws the clip only there, over the sharp painting, so roofs, people and outlines
                 stay the painting's own pixels. A clip in which too much moves (over MAX_MOVING of the picture: the
                 painter moved houses) is not shown; the owner gets the draft to look at.
                 Files: /public/kling/island.json {of, video, mask, moving}, island-<k>.mp4, island-<k>-mask.png
                 (Caddy serves /kling/*); `up kling off island` takes it off again until the next painting.
  trailer        A painting the game did not show before (also one kept in the last three days, when this first runs):
                 a 10 s slow flight over it, then the island picture with its card fades in; to Telegram and X. Its first
                 KLING_REVIEW clips are drafts (kling.py), as for every public use.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kling  # noqa: E402

log = logging.getLogger("kling-island")

ART = os.environ.get("BLOG_ART", "/art")
MAX_MOVING = 0.5       # more than half the picture moving is not "a little life", it is a painter's mistake
FRESH = 3 * 86400      # a painting kept this recently gets its trailer when this runs for the first time
GAME = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/") + "/rabbit/"
FOOT = "White Rabbit Key · community project, not affiliated with IDNI"

LOOP_PROMPT = (
    "A hand-painted tropical island seen from above, as a living painting. The camera is completely still: no zoom, "
    "no pan. Only gentle natural motion: soft ripples and small glints of light move across the sea, thin smoke drifts "
    "slowly up from the chimneys, palm fronds stir faintly in a light breeze, warm lamps and torches flicker softly. "
    "Buildings, roofs, paths, boats, people and the coastline stay exactly as painted, sharp and still. Calm, minimal, "
    "premium; the painted brushwork and colours are kept.")
TRAILER_PROMPT = (
    "A slow, calm cinematic flight over a hand-painted tropical island: the camera glides gently forward and a little "
    "down towards the island, smooth and steady. The sea ripples and glints, smoke drifts from chimneys, palm fronds "
    "sway in a breeze, flags move. The painting, its buildings and its colours stay as painted; no new objects.")


def painting() -> tuple[str, str] | None:
    """(file name in the art folder, its path) of the island the game shows, or None."""
    try:
        sc = json.load(open(os.path.join(ART, "index.json"))).get("scenes", {})
    except (OSError, ValueError):
        return None
    f = sc.get("island")
    p = os.path.join(ART, f) if f else ""
    return (f, p) if f and os.path.exists(p) else None


def key_of(f: str) -> str:
    return os.path.splitext(os.path.basename(f))[0]


def plain(f: str) -> str:
    """The painting a clean copy was made of (paint.py isle: the same island with a few spots changed, e.g. the people
    taken out of the square, island-36-abc-clean-1234abcd.webp): the same island, not a new one."""
    return re.sub(r"-clean-[0-9a-f]{8}(?=\.[A-Za-z0-9]+$)", "", f or "")


def world(path: str):
    """The game's 1600x900 world window of the painting, as scene.js and the posts draw it."""
    from PIL import Image
    import cruise_pic
    return cruise_pic.island_view(Image.open(path).convert("RGB"), 0, 0, 1)


# ---------- the motion mask ----------
def mask(video: str, out_png: str, w: int = 400, h: int = 225) -> float:
    """Where the clip moves: per pixel the largest difference to its first frame (every 3rd frame, 160x90 grey),
    a little noise left out, grown and softened; saved as a grey PNG (white = moving). Returns the moving share."""
    from PIL import Image, ImageChops, ImageFilter
    sw, sh = 160, 90
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", f"scale={sw}:{sh},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (sw * sh)
    if n < 2:
        raise RuntimeError("clip has no frames")
    first = Image.frombytes("L", (sw, sh), raw[:sw * sh])
    acc = Image.new("L", (sw, sh))
    for i in range(1, n, 3):
        fr = Image.frombytes("L", (sw, sh), raw[i * sw * sh:(i + 1) * sw * sh])
        acc = ImageChops.lighter(acc, ImageChops.difference(first, fr))
    m = acc.point(lambda v: 0 if v < 9 else min(255, (v - 9) * 14)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.5))
    moving = sum(1 for v in m.getdata() if v > 127) / (sw * sh)
    m.resize((w, h), Image.BICUBIC).save(out_png + ".part.png")
    os.replace(out_png + ".part.png", out_png)
    return moving


# ---------- the living island ----------
def live(f: str) -> str | None:
    try:
        return json.load(open(os.path.join(kling.OUT, "island.json"))).get("of")
    except (OSError, ValueError):
        return None


def living(f: str, path: str, now: float, tell) -> str | None:
    if not kling.enabled("island") or live(f) in (f, plain(f)):   # a clean copy keeps the clip of its painting
        return None
    st = kling.state()
    off = st["off"].get("island")
    if off is True or off in (f, plain(f)):
        return None
    k = "island-" + key_of(plain(f))   # one clip per island: a clean copy of a painting that has one gets none
    if st["jobs"].get(k, {}).get("done_island"):
        return None
    j = kling.ask(k, "island", lambda: world(path), LOOP_PROMPT, duration="10", mode="pro", tail=True, now=now)
    if j.get("status") != "succeed":
        return None
    os.makedirs(kling.OUT, exist_ok=True)
    vid, msk = f"{k}.mp4", f"{k}-mask.png"
    src = j["file"]
    if not j.get("tail"):
        src = kling.loop(src, os.path.join(kling.RAW, k + "-loop.mp4"), float(j.get("seconds") or 10))
    kling.web(src, os.path.join(kling.OUT, vid), crf=21)
    moving = mask(os.path.join(kling.OUT, vid), os.path.join(kling.OUT, msk))
    if moving > MAX_MOVING:
        url = kling.draft(k, os.path.join(kling.OUT, vid))
        kling.mark(k, done_island="too much moves", moving=round(moving, 3))
        tell(f"Living island for {f}: NOT shown, {moving:.0%} of the picture moves in Kling's clip (houses moved?). "
             f"The still painting stays. The clip: {url}")
        return k
    info = {"of": f, "video": vid, "mask": msk, "moving": round(moving, 3), "made": round(now), "w": 1600, "h": 900}
    with open(os.path.join(kling.OUT, "island.json.part"), "w") as fh:
        json.dump(info, fh)
    os.replace(os.path.join(kling.OUT, "island.json.part"), os.path.join(kling.OUT, "island.json"))
    kling.mark(k, done_island="live", moving=round(moving, 3))
    tell(f"The island is alive on {GAME} ({f}: sea, smoke and lights move on {moving:.0%} of the picture, the rest is the "
         f"sharp painting). The clip alone: {kling.PUBLIC}/{vid}\nNot good? Off again (the still painting shows):\n"
         'ssh root@node.tauhud.com "sh /opt/tau-command-hud/infra/up.sh kling off island"')
    log.info("living island %s: live, %.0f%% moving", f, moving * 100)
    return k


# ---------- the trailer ----------
def texts() -> dict:
    import alerts
    tg = "\n\n".join([
        "🏝 <b>White Rabbit Key has a new island</b>",
        "A new painting of the island game on Tau Testnet Alpha: a small island election with four candidates, laws, pacts, "
        "radio rumours and a Book in the lighthouse that nobody can edit. Your laws and your vote can go to Tau Testnet "
        "Alpha as real test transactions.",
        "<b>Why it matters</b>\nA game gives people a reason to come back to the testnet, and every vote sent from it is "
        "one more real transaction the chain has to carry.",
        html.escape(f"Play in your browser, sound on: {GAME}", quote=False),
        FOOT,
    ])
    x = alerts.x_post(["🏝 White Rabbit Key has a new island.",
                       "A small island election game: your laws and your vote can go to Tau Testnet Alpha as real test transactions."],
                      foot="", keep=1)
    return {"telegram": tg[:1024], "x": x, "size": (1600, 900)}


def trailer(f: str, path: str, now: float, tell) -> str | None:
    if not kling.enabled("trailer"):
        return None
    st = kling.state()
    seen = st.get("seen_island")
    if seen == f:
        return None
    if seen and plain(seen) == plain(f):   # the same island, only cleaned (paint.py isle): not a new island, no trailer
        st["seen_island"] = f; kling.save(st)
        return None
    if seen is None and now - os.path.getmtime(path) > FRESH:   # first run: the painting has been live for a while
        st["seen_island"] = f; kling.save(st)
        return None
    k = "trailer-" + key_of(f)
    j = kling.ask(k, "trailer", lambda: world(path), TRAILER_PROMPT, duration="10", mode="pro", now=now)
    if j.get("status") == "failed" or j.get("status") == "off":
        st = kling.state(); st["seen_island"] = f; kling.save(st)
        return None
    if j.get("status") != "succeed":
        return None
    import island_pic
    card = os.path.join(kling.RAW, k + "-card.jpg")
    island_pic.make(ART, card, ["A new island on White Rabbit Key", "Laws, pacts and votes as real test transactions",
                                "on Tau Testnet Alpha", "Play in your browser: tauhud.com/rabbit"])
    out = kling.then_card(j["file"], card, os.path.join(kling.RAW, k + "-post.mp4"), float(j.get("seconds") or 10))
    post = texts()
    st = kling.state(); st["seen_island"] = f; kling.save(st)
    if j.get("draft"):
        url = kling.draft(k, out, post)
        tell(kling.draft_note(k, "trailer", url, f"trailer of the new island {f}; nothing was posted"))
        return k
    said = kling.post_video(out, post)
    kling.mark(k, sent="; ".join(said), video=out)
    tell(f"New island trailer posted by itself ({f}):\n" + "\n".join(said))
    return k


def step(now: float | None = None, tell=None) -> None:
    if not kling.enabled():
        return
    now = time.time() if now is None else now
    tell = tell or (lambda text: kling.tell(text))
    p = painting()
    if not p:
        return
    for fn in (living, trailer):
        try:
            fn(p[0], p[1], now, tell)
        except Exception as e:  # noqa: BLE001 - tried again in 10 minutes
            log.warning("%s: %s", fn.__name__, e)
