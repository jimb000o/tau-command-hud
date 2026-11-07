"""The pirates' clip: after each Tuesday call of Black Sequence (relay/cruise.py, ship "pirates"), a clip of about 22
seconds made from that visit's logbook, every trick the pirates tried and what the chain answered, posted once to
Telegram and X by the blog service (cruise_crier.step calls step() here).

  intro     the ship at anchor off the island (the live painting and the painted ship, as cruise_pic.py draws them)
  8 x 2 s   one pirate of the crew sheet (rabbit/art/ships/crew-pirate.*, k01..k08, each holding the prop of its trick),
            the trick in words, then the chain's answer: REFUSED, the node's code, "4 of 4 tries"
  outro     all tries refused, why it matters, the logbook, "not affiliated with IDNI"

Honest by construction:
  - every number comes from the visit's logbook (/cruise/log?visit=...): a try is a trick the node answered and refused;
    a trick the node did not answer in time, or one the ship skipped, is no try and is not shown as refused
  - a trick that got through (a finding, held back for the owner) means NO clip for that visit at all, not one without
    it: "the chain refused everything" would then be untrue. The owner is told privately that the clip waits
  - a refusal with another answer than the expected one is still a refusal, and the clip shows the answer it got

Frames are drawn with Pillow and piped to ffmpeg (in the alerts image since 7 November 2026), 1280x720, 25 fps, H.264,
no sound. The post goes out with post_video.py's helpers; X only while today's X posts (the alerts service's count in
/state/alerts.json) leave room, the text without a link.

  python trick_clip.py preview [visit] [out.mp4]   the clip of that visit (default: the newest pirate visit; a made-up
                                                   SAMPLE, marked as such on every frame, when there is none yet);
                                                   posts nothing
  python trick_clip.py send <visit>                render and post that visit's clip now (once; up clip send)
"""
from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import sys
import time
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

log = logging.getLogger("trick-clip")

ON = os.environ.get("TRICK_CLIP", "true").lower() in ("1", "true", "yes")
W, H, FPS = 1280, 720, 25
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SHIP = "pirates"
FRESH = 12 * 3600       # a visit that ended longer ago gets no clip by itself (the first run after a deploy)
X_LEAVE = 1             # X posts of the day left for the real chain's news

# the order of the crew sheet (k01..k08, the Codex prompt of 7 November 2026) and each trick's name on screen
ORDER = ["overspend", "replay", "expired", "stale", "forged", "impostor", "freeride", "giant"]
NAMES = {"overspend": "Overspend", "replay": "Replay", "expired": "Expired", "stale": "Stale", "forged": "Forged",
         "impostor": "Impostor", "freeride": "Free ride", "giant": "Giant"}
# relay/cruise.py TRICKS, the words the logbook writes as "what"; used only when an entry has none
WHAT = {"overspend": "pays more than the wallet holds", "replay": "sends a payment the chain already took a second time",
        "expired": "sends a payment whose time ran out", "forged": "signs a payment with another pirate's key",
        "impostor": "pays from another pirate's wallet with their own signature", "freeride": "allows no fee at all for a payment",
        "stale": "sends a payment whose block height deadline has passed",
        "giant": "pays more than a transfer can carry (2^24 test AGRS)"}

# monochrome, green the only accent (the site's design rules)
INK, SOFT, DIM = (242, 242, 242), (205, 214, 222), (140, 150, 160)
GREEN = (120, 220, 140)
PANEL = (8, 12, 24)
CARD_H = 340


# ---------- the facts ----------
def tally(entries: list[dict]) -> dict:
    """What the clip may say about one visit: per trick the tries the node answered and refused, the codes it gave.
    "held" is True when any trick got through or is held back: then there is no clip."""
    rows = sorted(entries, key=lambda e: e.get("t") or 0)
    over = next((e for e in rows if e.get("kind") == "visit over"), None)
    tr = [e for e in rows if e.get("kind") in ("trick", "held")]
    held = any(e.get("held") or e.get("through") or e.get("ok") is True for e in tr) or any(
        isinstance(c, dict) and (c.get("held") or c.get("through")) for c in (((over or {}).get("summary") or {}).get("tricks") or {}).values())
    per = {}
    for k in ORDER:
        mine = [e for e in tr if e.get("trick") == k and e.get("ok") is False]
        codes = Counter(e.get("code") or "no code" for e in mine)
        what = next((e.get("what") for e in tr if e.get("trick") == k and e.get("what")), None) or WHAT[k]
        per[k] = {"refused": len(mine), "right": sum(1 for e in mine if e.get("right")), "codes": dict(codes.most_common()),
                  "expect": next((e.get("expect") for e in tr if e.get("trick") == k and e.get("expect")), []), "what": what}
    n = sum(p["refused"] for p in per.values())
    return {"visit": (rows[0].get("visit") if rows else None), "t": (over or {}).get("t") or (rows[-1].get("t") if rows else None),
            "over": over is not None, "held": held, "tricks": per, "refused": n,
            "right": sum(p["right"] for p in per.values()), "kinds": sum(1 for p in per.values() if p["refused"])}


def sample() -> dict:
    """A made-up visit for the preview before the first sailing: every frame then says SAMPLE."""
    rows = [{"t": 1794330000, "visit": "sample-pirates", "kind": "landed"}]
    for i, k in enumerate(ORDER):
        code = {"overspend": "INSUFFICIENT_FUNDS", "replay": "INVALID_SEQUENCE", "expired": "TX_EXPIRED", "stale": "TX_EXPIRED",
                "forged": "INVALID_SIGNATURE", "impostor": "TX_INVALID", "freeride": "FEE_LIMIT_TOO_LOW", "giant": "TX_INVALID"}[k]
        for j in range(4):
            rows.append({"t": 1794330100 + i * 4 + j, "visit": "sample-pirates", "kind": "trick", "trick": k, "what": WHAT[k],
                         "ok": False, "right": True, "code": code, "expect": [code]})
    rows.append({"t": 1794335400, "visit": "sample-pirates", "kind": "visit over"})
    f = tally(rows)
    f["sample"] = True
    return f


# ---------- drawing ----------
def font(size: int, weight: int = 700, mono: bool = False):
    from PIL import ImageFont
    p = os.path.join(FONTS, "JetBrainsMono.ttf" if mono else "Sora.ttf")
    f = ImageFont.truetype(p, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:  # noqa: BLE001 - a static font
        pass
    return f


def backdrop(art: str, ships: str) -> Image.Image:
    """The pirate ship at anchor off the live island painting, with its crew aboard (cruise_pic.py, no card), 1600x900;
    the sea alone when there is no painting (a test)."""
    import tempfile
    import cruise_pic
    tmp = tempfile.mkdtemp()
    try:
        t = os.path.join(tmp, "t.json")
        json.dump({"ship": "pirate", "ship_scale": 1.6}, open(t, "w"))
        out = os.path.join(tmp, "bg.jpg")
        with open(os.devnull, "w") as quiet:
            old, sys.stdout = sys.stdout, quiet
            try:
                cruise_pic.main(art, ships, t, out)
            finally:
                sys.stdout = old
        return Image.open(out).convert("RGB")
    except (SystemExit, OSError, KeyError, ValueError) as e:
        log.warning("no island painting for the clip (%s): the sea alone", e)
        im = Image.new("RGB", (1600, 900), (24, 64, 86))
        d = ImageDraw.Draw(im)
        for y in range(900):
            d.line([(0, y), (1600, y)], fill=(int(18 + 20 * y / 900), int(48 + 40 * y / 900), int(70 + 40 * y / 900)))
        return im
    finally:
        for n in os.listdir(tmp):
            os.remove(os.path.join(tmp, n))
        os.rmdir(tmp)


def crew(ships: str, scale: int = 3) -> dict:
    """Each trick's pirate, both frames, from the crew sheet, `scale` times its cell (painted sprites, soft upscale)."""
    cm = json.load(open(os.path.join(ships, "crew-pirate.json")))
    sheet = Image.open(os.path.join(ships, cm["src"])).convert("RGBA")
    cw, ch = cm["cell"]
    by = {f["id"]: f for f in cm["figures"]}
    out = {}
    for i, k in enumerate(ORDER):
        f = by.get(f"k{i + 1:02d}")
        if not f:
            continue
        pics = []
        for c in (f["a"], f["b"]):
            cell = sheet.crop(((c % cm["cols"]) * cw, (c // cm["cols"]) * ch, (c % cm["cols"] + 1) * cw, (c // cm["cols"] + 1) * ch))
            pics.append(cell.convert("RGBa").resize((cw * scale, ch * scale), Image.LANCZOS).convert("RGBA"))
        out[k] = pics
    return out


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def panel(size, radius=22, alpha=222) -> Image.Image:
    p = Image.new("RGBA", size)
    ImageDraw.Draw(p).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=PANEL + (alpha,))
    return p


def with_alpha(im: Image.Image, a: float) -> Image.Image:
    if a >= 1:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def wrap(d, text: str, f, width: int) -> list[str]:
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) <= width or not line:
            line = t
        else:
            out.append(line)
            line = w
    return out + ([line] if line else [])


class Motion:
    """Kling's clip of the backdrop (kling.py), frame by frame as the clip is drawn, over and over: the sea moves under
    the cards. One frame in memory at a time (ffmpeg decodes it, looped), so the blog service's memory is enough."""

    def __init__(self, path: str):
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", path, "-vf",
                                   "scale=1600:900:flags=lanczos,fps=25", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE)
        self.n = 1600 * 900 * 3

    def next(self) -> Image.Image | None:
        b = self.p.stdout.read(self.n)
        return Image.frombytes("RGB", (1600, 900), b) if len(b) == self.n else None

    def close(self) -> None:
        try:
            self.p.kill()
            self.p.wait(5)
        except Exception:  # noqa: BLE001
            pass


class Clip:
    INTRO, EACH, OUTRO = 2.6, 2.0, 4.0

    def __init__(self, f: dict, art: str, ships: str, when: str, motion: str | None = None):
        self.f, self.when = f, when
        self.bg = backdrop(art, ships)
        self.motion = Motion(motion) if motion else None
        self.crew = crew(ships)
        self.shown = [k for k in ORDER if f["tricks"][k]["refused"]]   # tricks with no try this visit are left out
        self.length = self.INTRO + self.EACH * len(self.shown) + self.OUTRO
        self.fonts = {"tag": font(20, 600), "big": font(54), "mid": font(30, 500), "small": font(22, 500), "name": font(48),
                      "stamp": font(44, 800), "code": font(24, 500, mono=True), "huge": font(96, 800), "foot": font(18, 500),
                      "dot": font(13, 600)}
        self.cards = {k: self.trick_card(i, k) for i, k in enumerate(self.shown)}

    # the island, slowly closer (a 6% push-in over the whole clip, centred on the ship)
    def background(self, t: float) -> Image.Image:
        z = 1 + 0.06 * t / self.length
        w, h = 1600 / z, 900 / z
        cx, cy = 1600 * 0.62, 900 * 0.62
        x0, y0 = min(max(cx - w / 2, 0), 1600 - w), min(max(cy - h / 2, 0), 900 - h)
        if self.motion:   # the living sea: the next frame of Kling's clip (the still backdrop if it ends early)
            fr = self.motion.next()
            if fr is not None:
                return fr.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h)).convert("RGBA")
            self.motion.close(); self.motion = None
        return self.bg.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h)).convert("RGBA")

    def shade(self, im: Image.Image, a: float) -> Image.Image:
        return Image.alpha_composite(im, Image.new("RGBA", (W, H), (4, 8, 16, int(a))))

    def trick_card(self, i: int, k: str) -> Image.Image:
        """The static part of one trick's card: number, name, what the pirate does (the pirate and the stamp move)."""
        p = panel((860, CARD_H))
        d = ImageDraw.Draw(p)
        fo = self.fonts
        d.text((250, 34), f"TRICK {i + 1} OF {len(self.shown)}", font=fo["tag"], fill=DIM)
        d.text((250, 66), NAMES[k], font=fo["name"], fill=INK)
        y = 132
        for line in wrap(d, "The pirate " + self.f["tricks"][k]["what"] + ".", fo["small"], 570)[:3]:
            d.text((250, y), line, font=fo["small"], fill=SOFT)
            y += 30
        return p

    def stamp(self, k: str) -> Image.Image:
        tk = self.f["tricks"][k]
        fo = self.fonts
        im = Image.new("RGBA", (580, 112))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, 252, 62], radius=10, outline=GREEN + (255,), width=4)
        d.text((126, 31), "REFUSED", font=fo["stamp"], fill=GREEN, anchor="mm")
        n = tk["refused"]
        d.text((272, 8), f"{n} of {n} {'try' if n == 1 else 'tries'}", font=fo["mid"], fill=INK)
        codes = list(tk["codes"])
        line = codes[0] if len(codes) == 1 else ", ".join(codes[:2])
        if tk["right"] < n and tk["expect"]:   # refused, but with another answer than the expected one: shown as it was
            line += f"  (expected {' or '.join(tk['expect'])})"
        d.text((2, 78), line, font=fo["code"], fill=SOFT if tk["right"] == n else DIM)
        return im

    def dots(self, upto: int) -> Image.Image:
        """The row of tricks at the bottom: each one green once the chain refused it on screen."""
        n = len(self.shown)
        gap = 140
        im = Image.new("RGBA", (gap * n, 46))
        d = ImageDraw.Draw(im)
        for i, k in enumerate(self.shown):
            cx = i * gap + gap // 2
            done = i < upto
            d.ellipse([cx - 9, 2, cx + 9, 20], fill=(GREEN + (255,)) if done else None, outline=(GREEN if done else DIM) + (255,), width=2)
            d.text((cx, 34), NAMES[k].upper(), font=self.fonts["dot"], fill=(GREEN if done else DIM) + (255,), anchor="mm")
        return im

    def marks(self, im: Image.Image) -> Image.Image:
        if self.f.get("sample"):
            d = ImageDraw.Draw(im)
            d.text((W - 30, 26), "SAMPLE · made-up numbers, not a real visit", font=self.fonts["tag"], fill=(255, 255, 255, 230), anchor="ra")
        return im

    def frame(self, t: float) -> Image.Image:
        fo = self.fonts
        im = self.background(t)
        n = len(self.shown)
        if t < self.INTRO:
            a = ease(t / 0.6)
            im = self.shade(im, 70 * a)
            p = panel((1040, 250))
            d = ImageDraw.Draw(p)
            d.text((40, 32), f"BLACK SEQUENCE · {self.when.upper()}", font=fo["tag"], fill=GREEN)
            d.text((40, 66), f"{n} pirate trick{'s' if n != 1 else ''} the chain must refuse", font=fo["name"], fill=INK)
            d.text((40, 150), "Made-up pirates, real signed transactions", font=fo["mid"], fill=SOFT)
            d.text((40, 190), "on Tau Testnet Alpha.", font=fo["mid"], fill=SOFT)
            im.alpha_composite(with_alpha(p, a), (60, int(H - 310 + 30 * (1 - a))))
            return self.marks(im)
        u = t - self.INTRO
        i = int(u // self.EACH)
        if i < n:
            k, s = self.shown[i], u - i * self.EACH
            im = self.shade(im, 90)
            a = ease(s / 0.35)
            card = self.cards[k].copy()
            pics = self.crew.get(k)
            if pics:   # the pirate, waving his trick: the two painted frames in turn
                fig = pics[int(s / 0.3) % 2]
                fy = CARD_H - fig.height - 20
                card.alpha_composite(fig, (125 - fig.width // 2, max(0, fy)))
            if s >= 0.75:
                sa = ease((s - 0.75) / 0.2)
                st = self.stamp(k)
                sc = 1.12 - 0.12 * sa
                st = st.resize((int(st.width * sc), int(st.height * sc)), Image.BICUBIC)
                card.alpha_composite(with_alpha(st, sa), (250, CARD_H - 22 - st.height))
            x = int((W - card.width) / 2 + 60 * (1 - a))
            im.alpha_composite(with_alpha(card, a), (x, 120))
            row = self.dots(i + (1 if s >= 0.75 else 0))
            band = panel((row.width + 40, row.height + 28), radius=16)
            im.alpha_composite(band, ((W - band.width) // 2, H - 106))
            im.alpha_composite(row, ((W - row.width) // 2, H - 92))
            return self.marks(im)
        s = u - n * self.EACH
        a = ease(s / 0.5)
        im = self.shade(im, 110 * a)
        im.alpha_composite(with_alpha(panel((1100, 640), radius=26, alpha=228), a), ((W - 1100) // 2, 40))
        f = self.f
        d = ImageDraw.Draw(im)
        col = lambda c, k=1.0: c + (int(255 * a * k),)
        d.text((W // 2, 140), f"{f['refused']} of {f['refused']}", font=fo["huge"], fill=col(GREEN), anchor="mm")
        d.text((W // 2, 228), "pirate tricks refused by the chain", font=fo["big"], fill=col(INK), anchor="mm")
        right = ("every one with the answer it should give" if f["right"] == f["refused"]
                 else f"{f['right']} with the answer it should give, {f['refused'] - f['right']} with another")
        d.text((W // 2, 292), right, font=fo["mid"], fill=col(SOFT), anchor="mm")
        if s > 0.8:
            b = ease((s - 0.8) / 0.5)
            col2 = lambda c: c + (int(255 * b),)
            d.text((W // 2, 400), "WHY IT MATTERS", font=fo["tag"], fill=col2(GREEN), anchor="mm")
            d.text((W // 2, 440), "These are the checks that keep every wallet's coins safe,", font=fo["mid"], fill=col2(INK), anchor="mm")
            d.text((W // 2, 480), "tested in public on Tau Testnet Alpha, every Tuesday.", font=fo["mid"], fill=col2(INK), anchor="mm")
            d.text((W // 2, 570), "Every try in the open logbook: tauhud.com/cruise", font=fo["small"], fill=col2(SOFT), anchor="mm")
            d.text((W // 2, 640), "White Rabbit Key · community project, not affiliated with IDNI", font=fo["foot"], fill=col2(DIM), anchor="mm")
        return self.marks(im)

    def render(self, out: str) -> str:
        """Every frame through ffmpeg: H.264, yuv420p, faststart (X and Telegram both play it), no sound, 2 threads."""
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-threads", "2",
               "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for j in range(int(self.length * FPS)):
                p.stdin.write(self.frame(j / FPS).convert("RGB").tobytes())
            p.stdin.close()
        except BrokenPipeError:
            pass
        finally:
            if self.motion:
                self.motion.close()
        if p.wait() != 0:
            raise RuntimeError(f"ffmpeg ended with {p.returncode}")
        return out


# ---------- the texts ----------
def short_day(t: float) -> str:
    import blog
    d = blog.local(t)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def texts(f: dict) -> dict:
    """Telegram (HTML caption, with the logbook link) and X (no link), every number from tally()."""
    import alerts
    import html
    LOGBOOK = os.environ.get("NODE_URL", "https://node.tauhud.com").rstrip("/") + "/cruise/log"
    n, kinds, right = f["refused"], f["kinds"], f["right"]
    names = [NAMES[k].lower() for k in ORDER if f["tricks"][k]["refused"]]
    day = short_day(f["t"])
    answer = ("every one with the answer it should give" if right == n else f"{right} with the answer it should give, "
              f"{n - right} with another (shown in the clip)")
    tg = "\n\n".join([
        f"🏴 <b>Black Sequence, {html.escape(day)}: {n} pirate tricks, {n} refused</b>",
        html.escape(f"Our made-up pirates tried {kinds} kinds of trick on Tau Testnet Alpha ({', '.join(names)}). "
                    f"The chain refused all {n} tries, {answer}.", quote=False),
        "<b>Why it matters</b>\nThese are the checks that keep every wallet's coins safe: no paying more than you have, no "
        "payment twice, no payment with someone else's key. Here they are tested in public, every Tuesday.",
        html.escape("Honest note: the pirates are made up, their transactions are real and signed, never more than 12 a "
                    f"minute. Every try in the logbook: {LOGBOOK}?visit={f['visit']}", quote=False),
        "White Rabbit Key · community project, not affiliated with IDNI",
    ])
    x = alerts.x_post([f"🏴 Black Sequence, {day}: made-up pirates tried {kinds} kinds of trick on Tau Testnet Alpha. "
                       f"The chain refused all {n} tries.",
                       "Why it matters: these checks keep every wallet's coins safe. Tested in public, every Tuesday."],
                      foot="", keep=1)
    return {"telegram": tg[:1024], "x": x}


# ---------- once per visit, by itself ----------
def x_room() -> bool:
    """Today's X posts (the alerts service counts them in /state/alerts.json) leave room, and one more for the chain."""
    import datetime as dt
    try:
        st = json.load(open(os.environ.get("STATE_PATH", "/state/alerts.json"))).get("x") or {}
    except (OSError, ValueError):
        st = {}
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    cap = int(os.environ.get("X_DAILY_CAP", 8))
    today = st.get("today", 0) if st.get("day") == day else 0
    return today < cap - X_LEAVE and st.get("pause_until", 0) <= time.time()


def post(path: str, t: dict) -> list[str]:
    import alerts
    import post_video
    said = []
    if alerts.Telegram().enabled():
        try:
            post_video.telegram_video(path, t["telegram"]); said.append("telegram: posted")
        except Exception as e:  # noqa: BLE001
            said.append(f"telegram: {e}")
    else:
        said.append("telegram: not set up")
    if not alerts.X().enabled():
        said.append("x: not set up")
    elif not x_room():
        said.append("x: left out (today's X posts are at the cap)")
    else:
        try:
            said.append("x: https://x.com/TauHUDcom/status/" + post_video.x_video(path, t["x"]))
        except Exception as e:  # noqa: BLE001
            said.append(f"x: {e}")
    return said


def make(f: dict, out: str, motion: str | None = None) -> str:
    import blog
    return Clip(f, blog.ART, blog.SHIPS, short_day(f["t"]), motion).render(out)


# ---------- Kling: the living sea under the clip (kling.py) ----------
PROMPT = ("A hand-painted tropical island with a dark-sailed pirate ship at anchor, as a living painting. The camera is "
          "completely still. Thin sea mist drifts slowly across the water, the ship rocks gently, its black sails and "
          "flag move in the wind, lantern light flickers on deck, the sea ripples and glints. The island, the ship's "
          "shape and every colour stay exactly as painted. Quiet, a little ominous, premium.")


def kling_ask(vid: str, now: float | None = None) -> dict:
    """Asked for once the pirates are in sight (cruise_crier.kling_prepare); the clip after their call uses it."""
    import blog
    import kling
    return kling.ask("pirate-" + vid, "pirate", lambda: backdrop(blog.ART, blog.SHIPS), PROMPT, duration="10", tail=True, now=now)


def motion_of(vid: str | None) -> tuple[str | None, dict | None]:
    """(a seamless looping clip of the living sea, its job) for that visit, or (None, None)."""
    try:
        import kling
        if not vid or not kling.enabled("pirate"):
            return None, None
        j = kling.ready("pirate-" + vid)
        if not j:
            return None, None
        if j.get("tail"):
            return j["file"], j
        dst = j["file"].replace(".mp4", "-loop.mp4")
        return (dst if os.path.exists(dst) else kling.loop(j["file"], dst, float(j.get("seconds") or 10))), j
    except Exception as e:  # noqa: BLE001 - the still sea
        log.warning("pirate clip %s: no living sea (%s)", vid, e)
        return None, None


def step(now: float, st: dict, save, tell) -> str | None:
    """The newest pirate visit that ended within FRESH and has no clip yet: rendered and posted once. A visit with a
    finding held back gets no clip; the owner hears that once."""
    import blog
    if not ON:
        return None
    clips = st.setdefault("clipped", {})
    for vid in (blog.get("/cruise/log?n=1").get("visits") or [])[:3]:
        if not vid.endswith("-" + SHIP) or vid in clips:
            continue
        f = tally(blog.get(f"/cruise/log?visit={vid}&n=2000").get("entries") or [])
        if not f["over"]:
            continue
        if not f["t"] or now - f["t"] > FRESH:
            clips[vid] = {"at": round(now), "result": "too old, no clip"}
            save(st)
            continue
        try:   # what the public logbook masks, the server sees (/cruise/held answers only from inside)
            f["held"] = f["held"] or any(e.get("visit") == vid for e in blog.get("/cruise/held").get("entries") or [])
        except Exception:  # noqa: BLE001 - unsure: no clip
            f["held"] = True
        if f["held"]:
            clips[vid] = {"at": round(now), "result": "no clip: a trick got through or is held back"}
            save(st)
            tell(f"Pirate clip for {vid}: NOT made and not posted, because a trick got through or is held back. "
                 "A clip saying 'all refused' would not be true. Nothing to do.")
            return vid
        if not f["refused"]:
            clips[vid] = {"at": round(now), "result": "no clip: no trick was answered and refused"}
            save(st)
            return vid
        out = f"/tmp/trick-clip-{vid}.mp4"
        sea, job = motion_of(vid)
        if sea and job.get("draft"):   # one of the first living-sea clips: the still one posts, this one waits for a look
            import kling
            make(f, out)   # a failure here is tried again in 10 minutes
            try:
                k = "pirate-" + vid
                url = kling.draft(k, make(f, f"/tmp/trick-clip-{vid}-kling.mp4", sea), {**texts(f), "size": (1280, 720)})
                tell(kling.draft_note(k, "pirate", url, "the pirates' clip on a living sea"))
            except Exception as e:  # noqa: BLE001
                log.warning("pirate clip draft: %s", e)
        else:
            make(f, out, sea)   # a failure here is tried again in 10 minutes
        t = texts(f)
        clips[vid] = {"at": round(now), "result": "posting"}
        save(st)   # before posting: a crash while posting never posts twice
        said = post(out, t)
        clips[vid] = {"at": round(now), "result": said}
        save(st)
        log.info("pirate clip %s: %s", vid, "; ".join(said))
        tell(f"Pirate clip for {vid} posted by itself ({f['refused']} of {f['refused']} tricks refused):\n" + "\n".join(said))
        return vid
    return None


def main(argv: list[str]) -> int:
    import blog
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cmd = argv[0] if argv else ""
    if cmd == "preview":
        vid = argv[1] if len(argv) > 1 and not argv[1].endswith(".mp4") else None
        out = next((a for a in argv[1:] if a.endswith(".mp4")), "/tmp/trick-clip.mp4")
        f = None
        try:
            if not vid:
                vid = next((v for v in blog.get("/cruise/log?n=1").get("visits") or [] if v.endswith("-" + SHIP)), None)
            if vid:
                f = tally(blog.get(f"/cruise/log?visit={vid}&n=2000").get("entries") or [])
        except Exception as e:  # noqa: BLE001
            print(f"logbook not read ({e}): a sample instead")
        if not f or not f["refused"]:
            print("no pirate visit with refused tricks yet: a SAMPLE with made-up numbers (marked on every frame)")
            f = sample()
        elif f["held"]:
            print(f"{vid}: a trick got through or is held back, so this clip would never be posted (preview only)")
        t0 = time.time()
        sea, _ = motion_of(vid)
        if sea:
            print("with Kling's living sea (kling.py)")
        make(f, out, sea)
        t = texts(f)
        print(f"clip {out}: {os.path.getsize(out) / 2**20:.1f} MB, {Clip.INTRO + Clip.EACH * f['kinds'] + Clip.OUTRO:.1f} s, "
              f"made in {time.time() - t0:.0f} s")
        import alerts
        print(f"--- telegram\n{t['telegram']}\n--- x ({alerts.x_len(t['x'])} of 280)\n{t['x']}\n---")
        return 0
    if cmd == "send" and len(argv) > 1:
        import cruise_crier
        st = cruise_crier.state()
        vid = argv[1]
        if vid in st.get("clipped", {}) and "--again" not in argv:
            print(f"{vid}: already done ({st['clipped'][vid].get('result')}); --again posts it a second time")
            return 1
        f = tally(blog.get(f"/cruise/log?visit={vid}&n=2000").get("entries") or [])
        f["held"] = f["held"] or any(e.get("visit") == vid for e in blog.get("/cruise/held").get("entries") or [])
        if f["held"] or not f["refused"]:
            print(f"{vid}: no clip (" + ("a trick got through or is held back" if f["held"] else "no refused trick") + ")")
            return 1
        out = make(f, f"/tmp/trick-clip-{vid}.mp4")
        said = post(out, texts(f))
        st.setdefault("clipped", {})[vid] = {"at": round(time.time()), "result": said, "by": "hand"}
        cruise_crier.save(st)
        print("\n".join(said))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
