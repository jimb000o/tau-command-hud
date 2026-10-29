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


def post_x(msg: str, state: dict, now: float | None = None) -> bool:
    """One try on Agorzilla's X account, within the daily cap; with the picture when there is one."""
    if not X_OUT.enabled():
        return False
    day = time.strftime("%Y-%m-%d", time.gmtime(now if now is not None else time.time()))
    if state.get("x_day") != day:
        state["x_day"], state["x_n"] = day, 0
    if state["x_n"] >= X_DAILY_CAP:
        log.info("x: daily cap reached, left out")
        return False
    png = card()
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


def post(msg: str) -> bool:
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


def step(latest: dict, state: dict, send=post, send_x=post_x) -> list[str]:
    """Post the evenings newer than the last one posted; returns the texts sent. Updates state in place.
    Telegram decides (a failed send is tried again next pass); the X copy follows once, never late."""
    rounds = sorted(latest.get("rounds") or [], key=lambda r: r["n"])
    if not rounds:
        return []
    if "last" not in state:            # first pass: remember, do not post history
        state["last"] = rounds[-1]["n"]
        return []
    sent = []
    for r in rounds:
        if r["n"] <= state["last"]:
            continue
        msg = text(r, latest)
        if TOKEN or send is not post:
            if not send(msg):
                break                  # try again next pass
        state["last"] = r["n"]
        sent.append(msg)
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
