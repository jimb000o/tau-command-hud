#!/usr/bin/env python3
"""Rico's voice for Radio Coco in White Rabbit Key (rabbit/rico.js).

Speaks every fixed line Rico can say once with an ElevenLabs voice and keeps the clips where Caddy serves them,
https://node.tauhud.com/rico/<first 16 hex of sha1(English text)>.mp3, with index.json listing what is there.
The game plays a line aloud only when all its clips are listed; otherwise it shows the text as before.
Clips are made once: running it again only makes the lines that are new (or all of them for a new voice).

The key is read from ELEVENLABS_API_KEY in infra/.env (never in the repository). Plain Python 3, no packages.

  python3 infra/rico/make.py voices                 the voices in the account
  python3 infra/rico/make.py samples [name ...]     one sample per voice -> https://node.tauhud.com/rico/samples/
  python3 infra/rico/make.py make --voice <name>    every clip with that voice (prints the characters first)
  python3 infra/rico/make.py lines                  the lines and how many characters they are, no key needed
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RICO_JS = os.path.join(REPO, "rabbit", "rico.js")
OUT = "/opt/sites/rico"
API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.38, "similarity_boost": 0.8, "style": 0.5, "use_speaker_boost": True}
SAMPLE = ("This is Rico on Radio Coco, ninety-seven point three! Chain weather. A light breeze, a few txs in the "
          "last blocks. Forecast: clear skies, unless somebody sends something.")


def lines(src=None):
    """Every English text Rico can speak, read from rico.js the same way its all() builds it."""
    src = src if src is not None else open(RICO_JS, encoding="utf-8").read()
    names = re.findall(r'"([^"]+)"', re.search(r"const NAMES = \[([^\]]*)\]", src).group(1))
    days = int(re.search(r"const DAYS = (\d+);", src).group(1))
    body = re.search(r"const L = \{(.*?)\n  \};", src, re.S).group(1)
    out = []
    for key, text in re.findall(r'^\s*(\w+): "((?:[^"\\]|\\.)*)",', body, re.M):
        text = json.loads('"' + text + '"')
        if key == "topLaws":
            out += [text.replace("{x}", x) for x in names]
        elif key == "pact":
            out += [text.replace("{x}", x).replace("{y}", y) for x in names for y in names if x != y]
        elif key == "day":
            out += [text.replace("{n}", str(n)).replace("{m}", str(days)) for n in range(1, days + 1)]
        else:
            out.append(text)
    return out


def key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    env = os.path.join(REPO, "infra", ".env")
    if not k and os.path.exists(env):
        for row in open(env, encoding="utf-8"):
            if row.startswith("ELEVENLABS_API_KEY="):
                k = row.split("=", 1)[1].strip().strip("'\"")
    if not k:
        sys.exit("No ELEVENLABS_API_KEY in infra/.env. Add it with:\n"
                 "  echo 'ELEVENLABS_API_KEY=YOUR_KEY' >> /opt/tau-command-hud/infra/.env")
    return k


def call(path, body=None, accept="application/json"):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json", "Accept": accept})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ElevenLabs said {e.code}: {msg}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(3)
                continue
            sys.exit(f"ElevenLabs could not be reached: {e}")


def voices():
    return json.loads(call("/voices"))["voices"]


def find_voice(name):
    vs = voices()
    for v in vs:
        if name in (v["voice_id"], v["name"]) or v["name"].lower().startswith(name.lower()):
            return v
    sys.exit(f"No voice called {name!r}. The account has: " + ", ".join(v["name"] for v in vs))


def speak(voice_id, text):
    return call(f"/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}, accept="audio/mpeg")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "voice"


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def cmd_voices(a):
    for v in voices():
        labels = ", ".join(f"{k}: {x}" for k, x in (v.get("labels") or {}).items())
        print(f"{v['name']:<28} {v['voice_id']}  {labels}")


def cmd_samples(a):
    vs = [find_voice(n) for n in a.names] if a.names else voices()[:a.max]
    print(f"{len(vs)} samples, {len(SAMPLE) * len(vs)} characters.")
    rows = []
    for v in vs:
        f = slug(v["name"]) + ".mp3"
        write(os.path.join(a.out, "samples", f), speak(v["voice_id"], SAMPLE))
        rows.append(f'<li><b>{html.escape(v["name"])}</b><br><audio controls preload="none" src="{f}"></audio></li>')
        print("  made", v["name"])
    page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>Rico: voices</title>"
            "<style>body{font:16px system-ui;background:#111;color:#eee;max-width:640px;margin:2em auto;padding:0 16px}"
            "li{margin:1.2em 0;list-style:none}audio{width:100%}</style><h1>Rico on Radio Coco: pick a voice</h1>"
            f"<p>{html.escape(SAMPLE)}</p><ul>{''.join(rows)}</ul>")
    write(os.path.join(a.out, "samples", "index.html"), page.encode())
    print("Listen: https://node.tauhud.com/rico/samples/")


def cmd_lines(a):
    ls = lines()
    for t in ls:
        print(key(t), t)
    print(f"{len(ls)} lines, {sum(map(len, ls))} characters.")


def cmd_make(a):
    v = find_voice(a.voice)
    idx_path = os.path.join(a.out, "index.json")
    try:
        idx = json.load(open(idx_path))
    except (OSError, ValueError):
        idx = {}
    if idx.get("voice") != v["voice_id"]:
        idx = {"voice": v["voice_id"], "name": v["name"], "model": MODEL, "clips": []}
    ls = lines()
    todo = [t for t in ls if key(t) not in idx["clips"] or not os.path.exists(os.path.join(a.out, key(t) + ".mp3"))]
    print(f"Voice {v['name']}: {len(todo)} of {len(ls)} lines to make, {sum(map(len, todo))} characters.")
    for i, t in enumerate(todo, 1):
        write(os.path.join(a.out, key(t) + ".mp3"), speak(v["voice_id"], t))
        if key(t) not in idx["clips"]:
            idx["clips"].append(key(t))
        write(idx_path, json.dumps(idx, indent=1).encode())   # after each clip, so a stop halfway keeps what is made
        print(f"  {i}/{len(todo)} {t[:70]}")
    idx["clips"] = [k for k in idx["clips"] if os.path.exists(os.path.join(a.out, k + ".mp3"))]
    write(idx_path, json.dumps(idx, indent=1).encode())
    print(f"Done: {len(idx['clips'])} clips with {v['name']}. Rico now talks on https://tauhud.com/rabbit/")


def main():
    p = argparse.ArgumentParser(description="Rico's voice for Radio Coco")
    p.add_argument("--out", default=OUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("voices")
    s = sub.add_parser("samples")
    s.add_argument("names", nargs="*")
    s.add_argument("--max", type=int, default=12)
    sub.add_parser("lines")
    m = sub.add_parser("make")
    m.add_argument("--voice", required=True)
    a = p.parse_args()
    {"voices": cmd_voices, "samples": cmd_samples, "lines": cmd_lines, "make": cmd_make}[a.cmd](a)


if __name__ == "__main__":
    main()
