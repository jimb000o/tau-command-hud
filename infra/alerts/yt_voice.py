"""The voice of the videos (yt.py): ElevenLabs speaks each scene's words and says when each sign is spoken, so the
subtitles of a short can follow the voice word by word.

  YT_VOICE_ID       the narrator: the owner's own voice, cloned once at elevenlabs.io (Voices, Instant Voice Clone)
  YT_VOICE_OWN      true = that voice is the owner's own; YouTube asks no "altered or synthetic" label for a creator's
                    own cloned voice (support.google.com/youtube/answer/14328491, read 15 November 2026). false = a
                    voice that is nobody's: the video is uploaded with the label, to be safe
  YT_VOICE_RICO     Rico's voice id (the radio host of White Rabbit Key), for a short line thrown in; none = left out
  YT_VOICE_MONTH    signs a month this service may have spoken (default 60000; ElevenLabs counts about one credit
                    a sign with this model); past it no new video is voiced until the next month

A clip is kept by the hash of voice + words: the same words are never paid twice. Without ELEVENLABS_API_KEY or
YT_VOICE_ID nothing is spoken and yt.py makes no video (a video without its voice is not what was planned).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
VOICE = os.environ.get("YT_VOICE_ID", "").strip()
RICO = os.environ.get("YT_VOICE_RICO", "").strip()
OWN = os.environ.get("YT_VOICE_OWN", "true").lower() in ("1", "true", "yes")
MODEL = os.environ.get("YT_VOICE_MODEL", "eleven_multilingual_v2")
MONTH_CAP = int(os.environ.get("YT_VOICE_MONTH", "60000") or 0)
DIR = os.environ.get("YT_VOICE_DIR", "/work/voice")
USAGE = os.environ.get("YT_VOICE_USAGE", "/state/yt-voice.json")
API = "https://api.elevenlabs.io/v1"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True}

_opener = urllib.request.urlopen


class VoiceError(RuntimeError):
    pass


def ready() -> bool:
    return bool(KEY and VOICE)


def voice_id(who: str) -> str:
    return RICO if who == "rico" else VOICE


def month(now: float | None = None) -> str:
    return time.strftime("%Y-%m", time.gmtime(time.time() if now is None else now))


def used(now: float | None = None) -> int:
    try:
        with open(USAGE) as f:
            return int(json.load(f).get(month(now), 0))
    except (OSError, ValueError):
        return 0


def _count(n: int) -> None:
    try:
        with open(USAGE) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d[month()] = int(d.get(month(), 0)) + n
    os.makedirs(os.path.dirname(USAGE) or ".", exist_ok=True)
    with open(USAGE + ".part", "w") as f:
        json.dump(d, f)
    os.replace(USAGE + ".part", USAGE)


def spoken_form(text: str) -> str:
    """What is said aloud: "transactions", never "txs"; the test coin by its letters."""
    out = text
    for a, b in ((" txs", " transactions"), (" tx ", " transaction "), ("AGRS", "A G R S"), ("tauhud.com", "tau hud dot com"),
                 ("HUD", "hud")):
        out = out.replace(a, b)
    return out


def words_of(alignment: dict, offset: float = 0.0) -> list[tuple[str, float, float]]:
    """(word, start, end) from ElevenLabs' signs and their times."""
    ch = alignment.get("characters") or []
    st = alignment.get("character_start_times_seconds") or []
    en = alignment.get("character_end_times_seconds") or []
    out, cur, a, b = [], "", 0.0, 0.0
    for c, s, e in zip(ch, st, en):
        if c.isspace():
            if cur:
                out.append((cur, a + offset, b + offset))
            cur = ""
            continue
        if not cur:
            a = float(s)
        cur += c
        b = float(e)
    if cur:
        out.append((cur, a + offset, b + offset))
    return out


def seconds_of(path: str) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        raise VoiceError(f"ffprobe could not read {path}: {p.stderr[-200:]}") from None


def speak(text: str, who: str = "main") -> dict | None:
    """{"path": mp3, "seconds": length, "words": [(word, start, end)]} for these words in this voice; None when the
    voice (Rico's) is not set up. Raises VoiceError when the month's signs are used up or ElevenLabs says no."""
    vid = voice_id(who)
    if not vid:
        if who == "rico":
            return None
        raise VoiceError("no narrator yet (YT_VOICE_ID in infra/.env)")
    if not KEY:
        raise VoiceError("no ELEVENLABS_API_KEY")
    text = text.strip()
    h = hashlib.sha256(f"{vid}|{MODEL}|{text}".encode()).hexdigest()[:20]
    mp3, meta = os.path.join(DIR, h + ".mp3"), os.path.join(DIR, h + ".json")
    if os.path.exists(mp3) and os.path.exists(meta):
        with open(meta) as f:
            return dict(json.load(f), path=mp3)
    if MONTH_CAP and used() + len(text) > MONTH_CAP:
        raise VoiceError(f"this month's {MONTH_CAP} signs of voice are used up (YT_VOICE_MONTH in infra/.env)")
    body = {"text": spoken_form(text), "model_id": MODEL, "voice_settings": SETTINGS}
    req = urllib.request.Request(f"{API}/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json"}, method="POST")
    try:
        with _opener(req, timeout=180) as r:
            j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise VoiceError(f"ElevenLabs answered {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    os.makedirs(DIR, exist_ok=True)
    with open(mp3 + ".part", "wb") as f:
        f.write(base64.b64decode(j["audio_base64"]))
    os.replace(mp3 + ".part", mp3)
    _count(len(text))
    out = {"seconds": round(seconds_of(mp3), 3), "words": words_of(j.get("alignment") or {}), "signs": len(text), "who": who}
    with open(meta, "w") as f:
        json.dump(out, f)
    return dict(out, path=mp3)
