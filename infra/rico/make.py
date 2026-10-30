#!/usr/bin/env python3
"""The islanders' voices in White Rabbit Key: Rico on Radio Coco and everyone you meet in the places (rabbit/rico.js).

Speaks every fixed line once, each in that islander's own ElevenLabs voice, and keeps the clips where Caddy serves
them, https://node.tauhud.com/rico/<first 16 hex of sha1("<who>|<English text>")>.mp3, with index.json listing what
is there. The game plays a line aloud only when all its clips are listed; otherwise it shows the text as before.
Clips are made once: running it again only makes the lines that are new (or all of someone's lines for a new voice).
The lines come from rabbit/voices.json (node tests/voices.mjs --write makes it from rico.js).

The key is read from ELEVENLABS_API_KEY in infra/.env (never in the repository). Plain Python 3, no packages.

  python3 infra/rico/make.py design all             three voices for each islander -> https://node.tauhud.com/rico/samples/
  python3 infra/rico/make.py design lola sam        three new ones for some islanders (again if none is right)
  python3 infra/rico/make.py keep rico=2 lola=1     keeps those designs as their voices and makes every clip with them
  python3 infra/rico/make.py library rico           twelve ready voices from the ElevenLabs Voice Library that fit Rico
  python3 infra/rico/make.py keep rico=L3           keeps library voice 3 (L) instead of a design
  python3 infra/rico/make.py make                   makes whatever clips are missing, for everyone with a voice
  python3 infra/rico/make.py make --again rico      makes Rico's clips anew
  python3 infra/rico/make.py make --voice rico=Name gives someone a voice already in the account, then makes the clips
  python3 infra/rico/make.py voices                 the voices in the account
  python3 infra/rico/make.py samples [name ...]     one sample per account voice -> https://node.tauhud.com/rico/samples/
  python3 infra/rico/make.py say                    the lines exactly as they are sent to be spoken
  python3 infra/rico/make.py lines                  the lines, who says them and how many characters, no key needed
design and keep need a key with Voice Generation: Access and Voices: Write.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
VOICES_JSON = os.path.join(REPO, "rabbit", "voices.json")
OUT = "/opt/sites/rico"
API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_v3"   # the most natural one, and it takes [tags] for how a line is said
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8}   # v3 takes 0 (creative), 0.5 (natural) or 1 (steady)
LOUD = {"stability": 0.0, "similarity_boost": 0.8}       # Rico on air: as lively as it gets
SAMPLE = ("This is Rico on Radio Coco, ninety-seven point three! Chain weather. A light breeze, a few txs in the "
          "last blocks. Forecast: clear skies, unless somebody sends something.")

# who they are, for Voice Design; a description is between 20 and 1000 characters
CAST = {
    "rico": ("Rico", "An energetic African-American man in his thirties, a radio DJ with a deep, warm, booming voice, fast "
                     "and punchy hype delivery, big grin you can hear, rhythmic and funky like a late-night soul and party radio "
                     "host, laughs between lines, never shouts, clear American English, very easy to understand."),
    "lola": ("Lola", "An energetic African-American Caribbean woman around thirty who runs a beach bar, bright warm voice full "
                     "of life, quick laugh, playful and teasing, light island lilt, clear and easy to understand."),
    "sam": ("Old Sam", "An old lighthouse keeper in his seventies, slow gravelly voice, calm and kind, a little dry humour, "
                       "speaks like someone who has read every page twice, gentle island accent, clear."),
    "marisol": ("Marisol", "A brisk, friendly Caribbean fisherwoman in her thirties, bright confident voice, straight talker, "
                           "warm and practical, light Spanish-island accent, clear and easy to understand."),
    "tobias": ("Tobias", "A pompous, theatrical harbour master in his sixties who loves a ceremony, booming self-important "
                         "voice, rolling words, comic grandeur, clear and easy to understand."),
    "baako": ("Baako", "A jovial coconut farmer in his forties, deep round friendly voice, easy laugh, West African and "
                       "Caribbean lilt, relaxed and generous, clear and easy to understand."),
    "hana": ("Hana", "A precise, calm schoolteacher in her thirties, clear crisp voice, patient and a little strict, "
                     "warm underneath, neutral accent, very easy to understand."),
    "frost": ("Ambassador Frost", "A cool, polished northern diplomat in his fifties, smooth measured voice, crisp consonants, "
                                  "politely menacing, every word weighed, clear."),
    "salado": ("Ambassador Salado", "A charming southern diplomat in his fifties, velvet voice, warm Latin accent, flattering "
                                    "and smooth, a hint of a smile that is not quite friendly, clear."),
}
DESIGN = CAST["rico"][1]
TALK = (" Talks naturally and casually, straight to the person in front of them, like a real conversation, "
        "never reading aloud or narrating.")

# how each one says their lines to you (v3 audio tags); Rico on air has his own
TAG = {"rico": "[friendly, leaning in]", "lola": "[warm, teasing]", "sam": "[slowly, kindly]", "marisol": "[friendly, direct]",
       "tobias": "[pompous]", "baako": "[warmly, with a chuckle]", "hana": "[calm, patient]", "frost": "[coolly]",
       "salado": "[smooth, charming]"}
ON_AIR = "[excited radio DJ]"   # the callouts that end in "!"
RADIO = "[radio DJ, playful]"     # his other lines on the radio strip
LAWS = {"A deep harbour for cruise ships": "a deep harbour for cruise ships", "A road round the island": "a road round the island"}
COINS = {"40": "Forty", "35": "Thirty-five"}
# the lines as they are said, to you, in a place: the same words as on screen, only loosened up for speaking
SAY = {
    "Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first.":
        "Okay, so, pick a law. The other three candidates vote on it, and two yeses make it law. Oh, and the Book checks it against the laws we already have, first.",
    "Sam keeps the minutes today. Pick a law; the other three candidates vote, two yes and it is law.":
        "I'm keeping the minutes today. Go on, pick a law. The other three candidates vote, and two yeses make it law.",
    "Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it.":
        "Honey, everyone passes through here. Talk about what people actually care about. And if you already passed a law for it? Counts double.",
    "Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time.":
        "Twenty-five coins and I'll play anything, baby. I don't check, I just spin. But, heh, the Book writes down who paid me. Every single time.",
    "A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house.":
        "So, a pact means you two vote for each other's laws. Break one, and the whole island knows by breakfast. Here, lemonade's on the house.",
    "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing.":
        "Every move on this island gets written in here, with the name of whoever made it. Nobody can tear out a page. Not even me. And reading? Costs you nothing.",
    "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page.":
        "Empty, for now. But every move on this island will be written in here, with the name of whoever made it. Nobody can tear out a page.",
    "Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks.":
        "Boats, gulls, and a black cat that sometimes walks past twice. Nothing to do out here but think. Tau Testnet Alpha's out there too, you know. The Book on this island works a lot like its blocks.",
    "Three moves a day, five days, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book.":
        "Three moves a day, five days, and then the island votes. Each of the ten islanders cares about two things. Laws and talk about those, that's what wins them over. Rumours? They work for a day. Until people read the Book.",
    "Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law.":
        "Two laws that can't both hold would leave the whole island not knowing what's allowed. So the Book won't take it. Repeal the old one first, or pick another law.",
    "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me.":
        "Done, it's out there. Half the island's talking already. The other half reads the Book tomorrow, and the Book says you paid me.",
    "Done. And this one’s true, so let them check. The Book backs you up.":
        "Done. And this one's true, so let 'em check. The Book's got your back.",
    "Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory.":
        "Fine. I vote for yours, you vote for mine. Lola's our witness, and the Book is our memory.",
    "After what you did? Buy yourself a lemonade.": "After what you did? Ha. Buy yourself a lemonade.",
    "Not today. Show me how you vote first.": "Not today. Show me how you vote first, then we'll talk.",
}


def said(who, text, model=MODEL):
    """What is sent to ElevenLabs for a line: loosened up for speaking, with how it is said in front (v3 only)."""
    m = re.match(r"We are counting on you for “(.+)”\. We would hate to remind the island in public\.$", text)
    n = re.match(r"(\d+) coins, today\. All we ask is that you propose “(.+)” before the election\. A small thing between friends\.$", text)
    if m:
        out = f"We're counting on you for {LAWS.get(m[1], m[1])}. We would hate to have to remind the island. In public."
    elif n:
        out = f"{COINS.get(n[1], n[1])} coins. Today. All we ask is that you propose {LAWS.get(n[2], n[2])} before the election. A small thing, between friends."
    else:
        out = SAY.get(text, text)
    if not model.startswith("eleven_v3"):
        return out
    air = who == "rico" and text not in SAY
    return f"{(ON_AIR if text.endswith('!') else RADIO) if air else TAG.get(who, '')} {out}".strip()


def lines(path=None):
    """Every line anyone can speak, as (who, English text), in the order rico.js all() builds them."""
    return [(r["who"], r["text"]) for r in json.load(open(path or VOICES_JSON, encoding="utf-8"))]


def sample(who):
    """A Voice Design preview text for someone: their own lines as they say them to you, 100 to 1000 characters."""
    if who == "rico":
        return SAMPLE + " " + SAY["Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time."]
    t = ""
    for w, x in lines():
        if w == who and len(t) < 160:
            t = (t + " " + said(w, x, "plain")).strip()
    while len(t) < 100:
        t = (t + " " + t).strip()
    return t[:1000]


def key(who, text):
    return hashlib.sha1(f"{who}|{text}".encode("utf-8")).hexdigest()[:16]


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


def call(path, body=None, accept="application/json", missing_ok=False, retry_400=False):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json", "Accept": accept})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if (missing_ok and e.code in (404, 405)) or (retry_400 and e.code in (400, 422)):
                return None
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


def speak(voice_id, text, settings=SETTINGS, model=MODEL):
    if not model.startswith("eleven_v3"):
        settings = dict(settings, stability=max(0.3, settings["stability"]), style=0.5, use_speaker_boost=True)
    return call(f"/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                {"text": text, "model_id": model, "voice_settings": settings}, accept="audio/mpeg")


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
    write(os.path.join(a.out, "samples", "index.html"), page(rows, "Rico on Radio Coco: pick a voice", SAMPLE))
    print("Listen: https://node.tauhud.com/rico/samples/")


def page(rows, title, text):
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>White Rabbit Key: voices</title>"
            "<style>body{font:16px system-ui;background:#111;color:#eee;max-width:640px;margin:2em auto;padding:0 16px}"
            "li{margin:1.2em 0;list-style:none}audio{width:100%}code{color:#7f7}h2{margin-top:2em}</style>"
            f"<h1>{html.escape(title)}</h1><p>{html.escape(text)}</p><ul>{''.join(rows)}</ul>").encode()


def load(path, empty):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return empty


def index(out):
    idx = load(os.path.join(out, "index.json"), {})
    if "voice" in idx:   # the first index, when only Rico spoke: his voice stays, his clips are named anew
        idx = {"voices": {"rico": {"id": idx["voice"], "name": idx.get("name", "Rico")}}, "clips": []}
    idx.setdefault("voices", {})
    idx.setdefault("clips", [])
    idx["model"] = MODEL
    return idx


def design_page(out, designs):
    rows = []
    for who in CAST:
        d = designs.get(who)
        if not d:
            continue
        rows.append(f"<h2>{html.escape(CAST[who][0])}</h2><p><small>{html.escape(d['text'])}</small></p>")
        for i in range(1, len(d["ids"]) + 1):
            rows.append(f"<li><b>{i}</b> &nbsp; <code>{who}={i}</code><br>"
                        f"<audio controls preload=none src='design-{who}-{i}.mp3'></audio></li>")
    keep = " ".join(f"{w}=1" for w in CAST if w in designs)
    write(os.path.join(out, "samples", "index.html"),
          page(rows, "White Rabbit Key: pick a voice for everyone",
               f"Then on the server: python3 infra/rico/make.py keep {keep}   (with the numbers you like)"))


def cmd_design(a):
    """Three voices for each islander named, drawn from their description (ElevenLabs Voice Design); nothing is kept yet."""
    names = [a.who] if isinstance(a.who, str) else list(a.who or ["all"])
    who = list(CAST) if "all" in names else names
    for w in who:
        if w not in CAST:
            sys.exit(f"No islander {w!r}. They are: {', '.join(CAST)}")
    path = os.path.join(a.out, "design.json")
    designs = load(path, {})
    if "ids" in designs:   # the first design.json, Rico's only
        designs = {"rico": {"description": designs.get("description", DESIGN), "text": SAMPLE, "ids": designs["ids"]}}
    for w in who:
        desc = a.description if a.description and len(who) == 1 else CAST[w][1]
        body = {"voice_description": (desc + TALK)[:1000], "text": sample(w)}
        r = call("/text-to-voice/design", dict(body, model_id="eleven_ttv_v3"), missing_ok=True, retry_400=True)
        if r is None:
            r = call("/text-to-voice/design", dict(body, model_id="eleven_multilingual_ttv_v2"), missing_ok=True)
        if r is None:
            r = call("/text-to-voice/create-previews", body)
        previews = json.loads(r)["previews"][:3]
        for i, p in enumerate(previews, 1):
            write(os.path.join(a.out, "samples", f"design-{w}-{i}.mp3"), base64.b64decode(p["audio_base_64"]))
        designs[w] = {"description": desc, "text": body["text"], "ids": [p["generated_voice_id"] for p in previews]}
        write(path, json.dumps(designs, indent=1).encode())
        print(f"  {CAST[w][0]}: {len(previews)} designs")
    design_page(a.out, designs)
    print("Listen: https://node.tauhud.com/rico/samples/")
    print("Keep the ones you like with: python3 infra/rico/make.py keep " + " ".join(f"{w}=1" for w in who))


# what to look for in the Voice Library, which holds voices their speakers shared for use
FIND = {"rico": {"gender": "male", "accent": "african-american", "search": "radio"},
        "lola": {"gender": "female", "search": "caribbean"}, "baako": {"gender": "male", "search": "african"},
        "sam": {"gender": "male", "age": "old"}, "tobias": {"gender": "male", "age": "old", "search": "narrator"},
        "marisol": {"gender": "female", "accent": "latin"}, "hana": {"gender": "female", "search": "calm"},
        "frost": {"gender": "male", "accent": "british"}, "salado": {"gender": "male", "accent": "latin"}}


def cmd_library(a):
    """Ready voices from the ElevenLabs Voice Library for one islander, with their previews on the samples page."""
    w = a.who
    if w not in CAST:
        sys.exit(f"No islander {w!r}. They are: {', '.join(CAST)}")
    q = dict(FIND.get(w, {}), **({"search": a.search} if a.search else {}))
    found = []
    for drop in ([], ["search"], ["search", "accent"]):   # widen the search when nothing fits
        params = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in q.items() if k not in drop)
        found = json.loads(call(f"/shared-voices?page_size=12&{params}")).get("voices", [])
        if found:
            break
    if not found:
        sys.exit("The Voice Library had nothing for that. Try: python3 infra/rico/make.py library " + w + " \"some words\"")
    path = os.path.join(a.out, "library.json")
    lib = load(path, {})
    lib[w] = [{"owner": v["public_owner_id"], "id": v["voice_id"], "name": v.get("name", "")} for v in found]
    write(path, json.dumps(lib, indent=1).encode())
    rows = []
    for i, v in enumerate(found, 1):
        about = " · ".join(x for x in (v.get("accent"), v.get("age"), v.get("descriptive"), v.get("use_case")) if x)
        rows.append(f"<li><b>L{i} {html.escape(v.get('name', ''))}</b> <small>{html.escape(about)}</small> &nbsp; "
                    f"<code>{w}=L{i}</code><br><small>{html.escape((v.get('description') or '')[:160])}</small><br>"
                    f"<audio controls preload=none src='{html.escape(v.get('preview_url') or '')}'></audio></li>")
    write(os.path.join(a.out, "samples", "library.html"),
          page(rows, f"{CAST[w][0]}: voices from the Voice Library", f"Keep one with: python3 infra/rico/make.py keep {w}=L1"))
    print(f"{len(found)} voices. Listen: https://node.tauhud.com/rico/samples/library.html")
    print(f"Keep one with: python3 infra/rico/make.py keep {w}=L1   (or L2, L3 ...)")


def cmd_keep(a):
    """Keep design N for each islander as their voice in the account, then make every clip with them."""
    designs = load(os.path.join(a.out, "design.json"), {})
    idx = index(a.out)
    for pick in a.picks:
        w, _, n = pick.partition("=")
        if n.upper().startswith("L"):   # a voice from the Voice Library: added to the account as it is
            try:
                v = load(os.path.join(a.out, "library.json"), {})[w][int(n[1:]) - 1]
            except (KeyError, ValueError, IndexError):
                sys.exit(f"No library voice {pick!r}. Run: python3 infra/rico/make.py library {w}")
            # used straight from the library by its id: nothing is created in the account, so the free plan works too
            vid, name = v["id"], v["name"]
            idx["voices"][w] = {"id": vid, "name": name}
            idx["clips"] = [k for k in idx["clips"] if k not in {key(w, t) for x, t in lines() if x == w}]
            write(os.path.join(a.out, "index.json"), json.dumps(idx, indent=1).encode())
            print(f"{CAST.get(w, (w,))[0]} speaks with {name} from the Voice Library ({vid}).")
            continue
        try:
            d = designs[w]
            gid = d["ids"][int(n) - 1]
        except (KeyError, ValueError, IndexError):
            sys.exit(f"No design {pick!r}. Run: python3 infra/rico/make.py design {w if w in CAST else 'all'}")
        name = CAST[w][0] if w in CAST else w
        body = {"voice_name": f"{name} (White Rabbit Key)", "voice_description": d["description"][:500], "generated_voice_id": gid}
        r = call("/text-to-voice", body, missing_ok=True)
        if r is None:
            r = call("/text-to-voice/create-voice-from-preview", body)
        vid = json.loads(r).get("voice_id")
        if not vid:
            sys.exit(f"ElevenLabs kept {name}'s voice but sent no id back: {r[:200]!r}")
        idx["voices"][w] = {"id": vid, "name": body["voice_name"]}
        idx["clips"] = [k for k in idx["clips"] if k not in {key(w, t) for x, t in lines() if x == w}]   # their lines anew
        write(os.path.join(a.out, "index.json"), json.dumps(idx, indent=1).encode())
        print(f"Kept {name} design {n} ({vid}).")
    a.voice = []
    cmd_make(a)


def cmd_lines(a):
    ls = lines()
    for w, t in ls:
        print(key(w, t), f"{w:<8}", t)
    by = {}
    for w, t in ls:
        by[w] = by.get(w, 0) + len(t)
    print(f"{len(ls)} lines, {sum(by.values())} characters: " + ", ".join(f"{w} {n}" for w, n in by.items()))


def cmd_say(a):
    for w, t in lines():
        print(f"{w:<8}", said(w, t))


def cmd_make(a):
    idx = index(a.out)
    for pick in a.voice or []:
        w, _, name = pick.partition("=")
        if not name:   # the old way, "make --voice Name": Rico's voice
            w, name = "rico", w
        v = find_voice(name)
        if idx["voices"].get(w, {}).get("id") != v["voice_id"]:
            idx["clips"] = [k for k in idx["clips"] if k not in {key(w, t) for x, t in lines() if x == w}]
        idx["voices"][w] = {"id": v["voice_id"], "name": v["name"]}
    idx_path = os.path.join(a.out, "index.json")
    ls = lines()
    for w in getattr(a, "again", None) or []:   # someone's clips made anew, e.g. after the way they speak changed
        idx["clips"] = [k for k in idx["clips"] if k not in {key(x, t) for x, t in ls if x == w}]
    have = lambda w, t: key(w, t) in idx["clips"] and os.path.exists(os.path.join(a.out, key(w, t) + ".mp3"))
    todo = [(w, t) for w, t in ls if w in idx["voices"] and not have(w, t)]
    silent = sorted({w for w, t in ls if w not in idx["voices"]})
    print(f"{len(todo)} of {len(ls)} lines to make, {sum(len(t) for w, t in todo)} characters."
          + (f" No voice yet for: {', '.join(silent)}." if silent else ""))
    for i, (w, t) in enumerate(todo, 1):
        k = key(w, t)
        model = getattr(a, "model", None) or MODEL
        loud = w == "rico" and t not in SAY and t.endswith("!")   # the callouts; his other radio lines stay natural
        write(os.path.join(a.out, k + ".mp3"), speak(idx["voices"][w]["id"], said(w, t, model), LOUD if loud else SETTINGS, model))
        if k not in idx["clips"]:
            idx["clips"].append(k)
        write(idx_path, json.dumps(idx, indent=1).encode())   # after each clip, so a stop halfway keeps what is made
        print(f"  {i}/{len(todo)} {w}: {t[:64]}")
    idx["clips"] = [k for k in idx["clips"] if os.path.exists(os.path.join(a.out, k + ".mp3"))]
    write(idx_path, json.dumps(idx, indent=1).encode())
    print(f"Done: {len(idx['clips'])} clips. The island talks on https://tauhud.com/rabbit/")


def main():
    p = argparse.ArgumentParser(description="The islanders' voices in White Rabbit Key")
    p.add_argument("--out", default=OUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("voices")
    s = sub.add_parser("samples")
    s.add_argument("names", nargs="*")
    s.add_argument("--max", type=int, default=12)
    sub.add_parser("lines")
    sub.add_parser("say")
    d = sub.add_parser("design")
    d.add_argument("who", nargs="*", default=["all"], help="all, or the islanders to design, e.g. lola sam")
    d.add_argument("--description", default=None, help="instead of the one in CAST (one islander only)")
    lb = sub.add_parser("library")
    lb.add_argument("who", nargs="?", default="rico")
    lb.add_argument("search", nargs="?", default=None)
    k = sub.add_parser("keep")
    k.add_argument("--model", default=MODEL, help="eleven_v3, or eleven_multilingual_v2 if v3 is not there")
    k.add_argument("picks", nargs="+", help="who=N (a design) or who=LN (a library voice), e.g. rico=L2 lola=1")
    m = sub.add_parser("make")
    m.add_argument("--model", default=MODEL, help="eleven_v3, or eleven_multilingual_v2 if v3 is not there")
    m.add_argument("--again", nargs="+", default=[], help="make these islanders' clips anew, e.g. --again rico")
    m.add_argument("--voice", action="append", help="who=voice name in the account (a bare name is Rico's)")
    a = p.parse_args()
    {"voices": cmd_voices, "samples": cmd_samples, "lines": cmd_lines, "make": cmd_make, "design": cmd_design, "keep": cmd_keep, "library": cmd_library, "say": cmd_say}[a.cmd](a)


if __name__ == "__main__":
    main()
