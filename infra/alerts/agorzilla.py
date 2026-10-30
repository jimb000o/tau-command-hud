"""Agorzilla's evening, posted to the Telegram channel.

Agorzilla (https://agorzilla.com) is a separate experiment on Tau Testnet
Alpha: people feed one shared creature with test AGRS, and every evening at
18:00 UTC the option most wallets picked is adopted. Its archive job writes
chain/latest.json every half hour; this job reads it and posts each newly
closed evening once to the Telegram channel and, with its own keys
(AGORZILLA_X_API_KEY, _API_SECRET, _ACCESS_TOKEN, _ACCESS_SECRET in .env),
on Agorzilla's own X account: a short text without links (a link makes an X
post 13 times dearer) with the creature on a dark card, at most
AGORZILLA_X_DAILY_CAP posts a day. X never holds Telegram up: one try each.
X also gets a post when the creature reaches a new growth stage.

When an evening changed something, both posts carry a before/after picture:
the agorzilla-shots service (agorzilla-shots/shots.mjs) photographs the real
page just before and just after the evening into AGORZILLA_SHOTS; this job
sets the two side by side on one card. It waits for them up to
AGORZILLA_SHOTS_WAIT seconds after the evening (default 25 min), then posts
without them.

The first pass only remembers the newest evening, so a fresh start never
posts old evenings.

  python agorzilla.py          poll every AGORZILLA_SECONDS (default 10 min)
  python agorzilla.py --x-test  one test post on Agorzilla's X account only
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request

from alerts import X, fetch_picture, x_post

log = logging.getLogger("tau-agorzilla")

URL = os.environ.get("AGORZILLA_LATEST", "https://agorzilla.com/chain/latest.json")
STATE = os.environ.get("AGORZILLA_STATE", "/state/agorzilla.json")
EVERY = float(os.environ.get("AGORZILLA_SECONDS", 600))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDcom").strip()
ENABLED = os.environ.get("AGORZILLA_POSTS", "1") != "0"
X_OUT = X({k: os.environ.get("AGORZILLA_" + k, "").strip() for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")})
# the creature: its base picture (portrait WebP, transparent), set once on a dark 16:9 card for X
X_PICTURE = os.environ.get("AGORZILLA_X_PICTURE", "https://agorzilla.com/assets/agorilla.webp").strip()
X_DAILY_CAP = int(os.environ.get("AGORZILLA_X_DAILY_CAP", 8))
X_FOOT = "🦍 A shared creature on Tau Testnet Alpha · test AGRS, no value"
X_TAG = "#TauNet $AGRS"   # every Agorzilla post on X carries these two, once, at the end
SHOTS = os.environ.get("AGORZILLA_SHOTS", "/shots").strip()
SHOTS_WAIT = float(os.environ.get("AGORZILLA_SHOTS_WAIT", 1500))
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def text(r: dict, latest: dict) -> str:
    """Two or three short lines: what changed, how it grows, what is open tonight."""
    votes = sum(r.get("tally") or [])
    if r.get("winner"):
        tally = " / ".join(f"{o} {t}" for o, t in zip(r["options"], r["tally"]))
        head = f"🦍 Agorzilla, evening {r['n'] + 1}: {esc(r['category'])} became <b>{esc(r['winner'])}</b>"
        head += f" ({esc(tally)}{', a tie settled by the state hash' if r.get('tie') else ''})."
    else:
        head = f"🦍 Agorzilla, evening {r['n'] + 1}: nobody picked a {esc(r['category'].lower())}, so nothing changed."
    lines = [head]
    grow = f"It is {esc(latest.get('stage_name', ''))}"
    if latest.get("lived") is not None:
        grow += f", {plural(latest['lived'], 'day', 'days')} lived"
    if r.get("feeders") is not None:
        grow += f"; {plural(r['feeders'], 'wallet', 'wallets')} fed it that day"
    lines.append(grow + ".")
    o = latest.get("open")
    if o:
        lines.append(f"Tonight's choice: {esc(o['category'])} ({esc(', '.join(o['options']))}). agorzilla.com")
    if votes:
        lines.append("Test AGRS only, no value; wallets, not people.")
    return "\n".join(lines)


def x_text(r: dict, latest: dict) -> str:
    """The evening on X: what changed first, then how it grows and tonight's choice; no link, no HTML."""
    if r.get("winner"):
        head = f"🦍 Evening {r['n'] + 1}: {r['category']} became {r['winner']}"
        body = " · ".join(f"{o} {t}" for o, t in zip(r["options"], r["tally"])) + (", a tie settled by the state hash" if r.get("tie") else "")
    else:
        head, body = f"🦍 Evening {r['n'] + 1}: nobody picked a {r['category'].lower()}, so nothing changed", ""
    grow = f"It is {latest.get('stage_name', '')}"
    if latest.get("lived") is not None:
        grow += f", {plural(latest['lived'], 'day', 'days')} lived"
    if r.get("feeders") is not None:
        grow += f"; {plural(r['feeders'], 'wallet', 'wallets')} fed it that day"
    o = latest.get("open")
    tonight = f"Tonight's choice: {o['category']} ({', '.join(o['options'])})." if o else ""
    return x_post([head, body, grow + ".", tonight], foot=X_FOOT, tag=X_TAG)


def post_x(msg: str, state: dict, now: float | None = None, png: bytes | None = None) -> bool:
    """One try on Agorzilla's X account, within the daily cap; with the evening's picture, else the creature's card."""
    if not X_OUT.enabled():
        return False
    day = time.strftime("%Y-%m-%d", time.gmtime(now if now is not None else time.time()))
    if state.get("x_day") != day:
        state["x_day"], state["x_n"] = day, 0
    if state["x_n"] >= X_DAILY_CAP:
        log.info("x: daily cap reached, left out")
        return False
    png = png or card()
    media = X_OUT.upload(png, "agorzilla.png")[0] if png else None
    ok, _, err = X_OUT.send_text(msg, media)
    if ok:
        state["x_n"] += 1
    else:
        log.warning("x post failed (%s), left out", err)
    return ok


_card: list = []


def card() -> bytes | None:
    """The creature centred on Agorzilla's dark green, 1600×900 PNG; made once, None when the picture cannot be had."""
    if _card:
        return _card[0]
    if not X_PICTURE:
        return None
    try:
        import io

        from PIL import Image
        req = urllib.request.Request(X_PICTURE, headers={"User-Agent": "tauhud-agorzilla/1 (+https://tauhud.com)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            im = Image.open(io.BytesIO(r.read(10 * 2**20))).convert("RGBA")
        im.thumbnail((1400, 820))
        bg = Image.new("RGBA", (1600, 900), "#06120d")
        bg.alpha_composite(im, ((1600 - im.width) // 2, (900 - im.height) // 2))
        out = io.BytesIO()
        bg.convert("RGB").save(out, "PNG", optimize=True)
    except Exception as e:  # noqa: BLE001 - no picture, the text goes alone
        log.info("x: no picture (%s)", e)
        return None
    _card.append(out.getvalue())
    return _card[0]


def shots_of(r: dict) -> tuple[str, str] | None:
    """The paths of the evening's two photographs, when both are there."""
    if not SHOTS:
        return None
    b, a = (os.path.join(SHOTS, f"evening-{r['n']}-{side}.jpg") for side in ("before", "after"))
    return (b, a) if os.path.exists(b) and os.path.exists(a) else None


def shot_info(r: dict) -> dict:
    """What the agorzilla-shots service saw: the part's value (and colour) before and after the evening."""
    try:
        with open(os.path.join(SHOTS, "evenings.json"), encoding="utf-8") as f:
            return next((x for x in json.load(f) if x.get("n") == r["n"]), {})
    except (OSError, ValueError):
        return {}


def evening_card(r: dict) -> bytes | None:
    """Before and after side by side on Agorzilla's dark green, 1600×900 PNG: what changed in the title, the part's
    value under each photograph, the count in the foot. None when the evening changed nothing or its photographs are not there."""
    if not r.get("winner"):
        return None
    paths = shots_of(r)
    if not paths:
        return None
    try:
        import io

        from PIL import Image, ImageDraw, ImageFont, ImageOps
        W, H, bg, cream, muted, green = 1600, 900, "#06120d", "#f3e2b8", "#9fb8aa", "#6ee7a0"
        im = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(im)
        font = lambda size: ImageFont.truetype(os.path.join(FONTS, "Sora.ttf"), size)  # noqa: E731
        info = shot_info(r)
        d.text((W // 2, 60), f"Evening {r['n'] + 1} · {r['category']} became {r['winner']}", font=font(46), fill=cream, anchor="mm")
        box_w, box_h, top, gap = 660, 680, 112, 100
        for k, (path, side) in enumerate(zip(paths, ("before", "after"))):
            x = (W - 2 * box_w - gap) // 2 + k * (box_w + gap)
            pic = ImageOps.fit(Image.open(path).convert("RGB"), (box_w, box_h), centering=(.5, .45))
            mask = Image.new("L", (box_w, box_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, box_w - 1, box_h - 1), 26, fill=255)
            im.paste(pic, (x, top), mask)
            d.rounded_rectangle((x, top, x + box_w - 1, top + box_h - 1), 26, outline=green if k else "#2a4a3b", width=3)
            d.text((x + 28, top + 26), side.upper(), font=font(24), fill=green if k else muted)
            value = info.get(side + "_value") or (r["winner"] if k else None)
            if value:   # a chip at the foot of the photograph: the part's value then, with its colour when it has one
                f, colour = font(28), info.get(side + "_color")
                tw = d.textlength(value, font=f) + (34 if colour else 0)
                cx, cy = x + box_w // 2, top + box_h - 46
                d.rounded_rectangle((cx - tw / 2 - 22, cy - 26, cx + tw / 2 + 22, cy + 26), 26, fill="#0b1f17", outline=green if k else "#2a4a3b", width=2)
                tx = cx - tw / 2
                if colour:
                    d.ellipse((tx, cy - 11, tx + 22, cy + 11), fill=colour)
                    tx += 34
                d.text((tx, cy), value, font=f, fill=cream, anchor="lm")
        ax, ay = W // 2, top + box_h // 2   # an arrow from before to after
        d.line((ax - 30, ay, ax + 22, ay), fill=cream, width=6)
        d.polygon([(ax + 34, ay), (ax + 12, ay - 18), (ax + 12, ay + 18)], fill=cream)
        tally = " · ".join(f"{o} {t}" for o, t in zip(r["options"], r["tally"]))
        foot = f"{tally} wallets{', a tie settled by the state hash' if r.get('tie') else ''} · test AGRS, no value · agorzilla.com"
        d.text((W // 2, H - 50), foot, font=font(24), fill=muted, anchor="mm")
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception as e:  # noqa: BLE001 - no picture, the text goes alone
        log.info("evening card: not made (%s)", e)
        return None


def growth_x(old: str, latest: dict) -> str:
    lived = latest.get("lived")
    head = f"🦍 Agorzilla grew into {latest.get('stage_name', '')}" + (f" after {plural(lived, 'day', 'days')} lived" if lived is not None else "")
    return x_post([head, f"It was {old} until now. The wallets that feed it every day decide how it looks."], foot=X_FOOT, tag=X_TAG)


def grow(latest: dict, state: dict, send_x=None) -> str | None:
    """An X post when the growth stage changed since the last read; the first read only records it."""
    stage, name = latest.get("stage"), latest.get("stage_name")
    if stage is None:
        return None
    last = state.get("stage")
    state["stage"], prev = stage, state.get("stage_name")
    state["stage_name"] = name
    if last is None or last == stage:
        return None
    msg = growth_x(prev or "smaller", latest)
    (send_x or post_x)(msg, state)
    return msg


def fetch() -> dict:
    req = urllib.request.Request(URL, headers={"User-Agent": "tauhud-agorzilla/1 (+https://tauhud.com)", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def post(msg: str, png: bytes | None = None) -> bool:
    """The evening on the channel; with its picture as a photo with the text under it."""
    if png:
        from alerts import multipart
        body, ctype = multipart({"chat_id": CHAT, "caption": msg, "parse_mode": "HTML"}, {"photo": ("agorzilla-evening.png", png, "image/png")})
        req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", body, {"Content-Type": ctype})
    else:
        body = json.dumps({"chat_id": CHAT, "text": msg, "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return bool(json.load(r).get("ok"))
    except Exception as e:  # noqa: BLE001
        log.warning("sendMessage failed: %s", e)
        return False


def load() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(s: dict):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def step(latest: dict, state: dict, send=post, send_x=post_x, now: float | None = None, picture=evening_card) -> list[str]:
    """Post the evenings newer than the last one posted; returns the texts sent. Updates state in place.
    Telegram decides (a failed send is tried again next pass); the X copy follows once, never late.
    An evening that changed something waits up to SHOTS_WAIT for its before/after picture."""
    now = time.time() if now is None else now
    rounds = sorted(latest.get("rounds") or [], key=lambda r: r["n"])
    if not rounds:
        state.setdefault("last", -1)   # no evening yet: the first one ever is news, not history
        return []
    if "last" not in state:            # first pass: remember, do not post history; the last 6 h are still news
        old = [r["n"] for r in rounds if not r.get("t") or now - r["t"] > 6 * 3600]
        state["last"] = old[-1] if old else rounds[0]["n"] - 1
    sent = []
    for r in rounds:
        if r["n"] <= state["last"]:
            continue
        png = picture(r)
        if not png and r.get("winner") and r.get("t") and now - r["t"] < SHOTS_WAIT:
            break                      # its photographs are being made; next pass
        msg = text(r, latest)
        if TOKEN or send is not post:
            if not (send(msg, png) if png else send(msg)):
                break                  # try again next pass
        state["last"] = r["n"]
        sent.append(msg)
        if png:
            send_x(x_text(r, latest), state, png=png)
        else:
            send_x(x_text(r, latest), state)
    return sent


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if "--x-test" in sys.argv:
        if not X_OUT.enabled():
            print("x: off (AGORZILLA_X_API_KEY, _API_SECRET, _ACCESS_TOKEN and _ACCESS_SECRET are not all set in .env)")
            sys.exit(1)
        ok, _, err = X_OUT.send_text(x_post(["🦍 Agorzilla is connected to X",
                                             "Every evening this account posts what the wallets picked for the creature and how it grows."],
                                            foot=X_FOOT, tag=X_TAG))
        print("x: sent, look at the profile" if ok else "x: FAILED " + err)
        sys.exit(0 if ok else 1)
    if "--repost" in sys.argv:          # post evening N again on the running service's next pass (it reads the state each pass)
        n = int(sys.argv[sys.argv.index("--repost") + 1])
        state = load()
        state["last"] = n - 1
        save(state)
        print(f"evening {n + 1} goes out on the next pass (within {EVERY} s)")
        sys.exit(0)
    if not (ENABLED and (TOKEN or X_OUT.enabled())):
        log.info("off (AGORZILLA_POSTS=0, or neither TELEGRAM_BOT_TOKEN nor the AGORZILLA_X keys)")
        while True:
            time.sleep(3600)
    while True:
        try:
            state = load()
            latest = fetch()
            for msg in step(latest, state):
                log.info("posted: %s", msg.splitlines()[0])
            if grow(latest, state):
                log.info("growth: %s", latest.get("stage_name"))
            save(state)
        except Exception as e:  # noqa: BLE001
            log.warning("pass failed: %s", e)
        time.sleep(EVERY)


if __name__ == "__main__":
    main()
