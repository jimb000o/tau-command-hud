#!/usr/bin/env python3
"""No Memo: richer sounds and the ship's voice from ElevenLabs, kept where Caddy serves them (/opt/sites/rico/nomemo-sfx,
https://node.tauhud.com/rico/nomemo-sfx/). The game plays these instead of its drawn files (nomemo/sfx/) when they exist;
without them it keeps the drawn ones, so nothing here is needed for the game to sound.

    python3 infra/nomemo/sfx.py make            every sound in nomemo/sfx/list.json that has an "eleven" prompt
    python3 infra/nomemo/sfx.py make seal paid  only these (made again)
    python3 infra/nomemo/sfx.py voice           the ship's short fixed lines ("Contract sealed." ...), one voice
    python3 infra/nomemo/sfx.py voice --as Lily the same with another voice of the account
    python3 infra/nomemo/sfx.py drop seal       back to the drawn file for these (v-... drops a voice line)
    python3 infra/nomemo/sfx.py list            what is made, and the credits left

Listen and compare: https://node.tauhud.com/rico/nomemo-sfx/
The key is ELEVENLABS_API_KEY in infra/.env, shared with infra/rico/make.py. Plain Python 3, no packages, no restart.
"""
import argparse, html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "infra", "rico"))
import make as rico  # noqa: E402  (call, write, credits, find_voice, speak: the same key, retries and quota messages)

LIST = os.path.join(REPO, "nomemo", "sfx", "list.json")
OUT = os.path.join(rico.OUT, "nomemo-sfx")
DRAWN = "https://tauhud.com/nomemo/sfx/"
VOICE = "River"   # a ready voice of the account; the game puts it through a radio filter, so it sounds like the ship
HOW = "[flat, calm, precise, like a ship's computer]"


def listing():
    return json.load(open(LIST, encoding="utf-8"))


def index():
    return rico.load(os.path.join(OUT, "index.json"), {"sounds": [], "voice": []})


def save(idx):
    idx["sounds"] = sorted(set(idx["sounds"]))
    idx["voice"] = sorted(set(idx["voice"]))
    rico.write(os.path.join(OUT, "index.json"), json.dumps(idx, indent=1).encode())
    page(idx)


def page(idx):
    lj = listing()
    rows = []
    for s in lj["sounds"]:
        mine = s["name"] in idx["sounds"]
        rows.append(f"<li><b>{html.escape(s['name'])}</b> <small>{html.escape(s['what'])} · {html.escape(s['when'])}</small><br>"
                    f"drawn <audio controls preload=none src='{DRAWN}{s['name']}.mp3'></audio>"
                    + (f" &nbsp; ElevenLabs <audio controls preload=none src='{s['name']}.mp3'></audio>"
                       f" <code>python3 infra/nomemo/sfx.py drop {s['name']}</code>" if mine else "") + "</li>")
    for v in lj["voice"]:
        if v["name"] in idx["voice"]:
            rows.append(f"<li><b>{html.escape(v['name'])}</b> “{html.escape(v['text'])}” <small>{html.escape(v['when'])}</small><br>"
                        f"<audio controls preload=none src='{v['name']}.mp3'></audio></li>")
    rico.write(os.path.join(OUT, "index.html"),
               rico.page(rows, "No Memo: the sounds", "The game plays the ElevenLabs version where there is one. "
                         "To go back to the drawn one: python3 infra/nomemo/sfx.py drop NAME"))


def left():
    c = rico.credits()
    return f"{c[0]:,} credits left (renew {c[1]})" if c else "credits: the key may not read them"


def cmd_make(a):
    lj, idx = listing(), index()
    todo = [s for s in lj["sounds"] if s.get("eleven") and (not a.names or s["name"] in a.names)]
    if a.names:
        unknown = set(a.names) - {s["name"] for s in lj["sounds"] if s.get("eleven")}
        if unknown:
            sys.exit("No ElevenLabs prompt for: " + ", ".join(sorted(unknown)) + ". These have one: "
                     + " ".join(s["name"] for s in lj["sounds"] if s.get("eleven")))
    print(left())
    for s in todo:
        dst = os.path.join(OUT, s["name"] + ".mp3")
        if not a.names and os.path.exists(dst):
            print(f"  {s['name']}: made before (make {s['name']} makes it again)")
            continue
        loop = s["name"].startswith("amb-")
        body = {"text": s["eleven"], "duration_seconds": max(0.5, min(22.0, float(s.get("sec") or 2))), "prompt_influence": 0.5}
        r = rico.call("/sound-generation?output_format=mp3_44100_64",
                      dict(body, loop=loop, model_id="eleven_text_to_sound_v2"), accept="audio/mpeg", retry_400=True)
        if r is None:   # an older API without the loop switch or the model name
            r = rico.call("/sound-generation?output_format=mp3_44100_64", body, accept="audio/mpeg")
        rico.write(dst, r)
        idx["sounds"].append(s["name"])
        save(idx)
        print(f"  {s['name']}: {len(r) // 1024} KB")
    save(idx)
    print(left())
    print("Listen: https://node.tauhud.com/rico/nomemo-sfx/   (the game takes them within two minutes, after a reload)")


def cmd_voice(a):
    lj, idx = listing(), index()
    v = rico.find_voice(a.voice)
    print(left())
    for line in lj["voice"]:
        if a.names and line["name"] not in a.names:
            continue
        r = rico.speak(v["voice_id"], f"{HOW} {line['text']}")
        rico.write(os.path.join(OUT, line["name"] + ".mp3"), r)
        idx["voice"].append(line["name"])
        print(f"  {line['name']}: {line['text']}")
    idx["voice_name"] = v["name"]
    save(idx)
    print(left())
    print("Listen: https://node.tauhud.com/rico/nomemo-sfx/   (in the game: voice on)")


def cmd_drop(a):
    idx = index()
    for n in a.names:
        for k in ("sounds", "voice"):
            if n in idx[k]:
                idx[k].remove(n)
        p = os.path.join(OUT, n + ".mp3")
        if os.path.exists(p):
            os.remove(p)
        print(f"  {n}: back to the drawn one" if not n.startswith("v-") else f"  {n}: silent again")
    save(idx)


def cmd_list(a):
    idx = index()
    print("ElevenLabs sounds: " + (" ".join(idx["sounds"]) or "none yet"))
    print("ship's voice: " + (" ".join(idx["voice"]) or "none yet") + (f" ({idx['voice_name']})" if idx.get("voice_name") else ""))
    print(left())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("names", nargs="*")
    v = sub.add_parser("voice"); v.add_argument("names", nargs="*"); v.add_argument("--as", dest="voice", default=VOICE)
    d = sub.add_parser("drop"); d.add_argument("names", nargs="+")
    sub.add_parser("list")
    a = p.parse_args()
    {"make": cmd_make, "voice": cmd_voice, "drop": cmd_drop, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()
