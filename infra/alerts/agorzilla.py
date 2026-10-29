"""Agorzilla's evening, posted to the Telegram channel.

Agorzilla (https://agorzilla.com) is a separate experiment on Tau Testnet
Alpha: people feed one shared creature with test AGRS, and every evening at
18:00 UTC the option most wallets picked is adopted. Its archive job writes
chain/latest.json every half hour; this job reads it and posts each newly
closed evening once, to Telegram only (never to X).

The first pass only remembers the newest evening, so a fresh start never
posts old evenings.

  python agorzilla.py          poll every AGORZILLA_SECONDS (default 10 min)
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

log = logging.getLogger("tau-agorzilla")

URL = os.environ.get("AGORZILLA_LATEST", "https://agorzilla.com/chain/latest.json")
STATE = os.environ.get("AGORZILLA_STATE", "/state/agorzilla.json")
EVERY = float(os.environ.get("AGORZILLA_SECONDS", 600))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "@tauHUDcom").strip()
ENABLED = os.environ.get("AGORZILLA_POSTS", "1") != "0"


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


def step(latest: dict, state: dict, send=post) -> list[str]:
    """Post the evenings newer than the last one posted; returns the texts sent. Updates state in place."""
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
        if not send(msg):
            break                      # try again next pass
        state["last"] = r["n"]
        sent.append(msg)
    return sent


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if not (ENABLED and TOKEN):
        log.info("off (AGORZILLA_POSTS=0 or no TELEGRAM_BOT_TOKEN)")
        while True:
            time.sleep(3600)
    while True:
        try:
            state = load()
            for msg in step(fetch(), state):
                log.info("posted: %s", msg.splitlines()[0])
            save(state)
        except Exception as e:  # noqa: BLE001
            log.warning("pass failed: %s", e)
        time.sleep(EVERY)


if __name__ == "__main__":
    main()
