"""The brief every YouTube video starts from, and the checker that reads it before anything is filmed.

A video answers ONE question. Its brief says for whom, the question, the title and the preview picture (written before
the film, so the first seconds can keep the title's promise), then the scenes in order: each names a view the film
service knows (yt_scenes.json) and the words spoken over it. The picture leads: a scene runs longer than its words
(RATIO), so the voice only adds what cannot be seen.

  {"id": "answer-what-is-tau-net", "kind": "answer" | "weekly" | "short",
   "audience": "...", "question": "What is the Tau Net testnet?", "title": "...",
   "thumb": {"words": "IS IT LIVE?", "number": "", "agorzilla": "grown"},
   "scenes": [{"scene": "hud", "say": "...", "caption": "...", "voice": "main" | "rico", "seconds": 10,
               "moment": true, "bonus": true}, ...],
   "facts": {"faucet": "a new wallet gets 100,000 test AGRS once"},     every number spoken must stand here
   "sources": ["https://tauhud.com/facts/"], "next": "answer-watch-the-chain", "tags": ["Tau Net", ...]}

check(brief) returns what is wrong, in plain words; an empty list means the brief may be filmed. It holds the site's
own content rules where a machine can hold them:
  - one question, a title that fits, a first scene short enough to be a hook, one scene where a rule or the chain says no
  - the network is "Tau Net" (or "Tau Testnet Alpha"), never "the Tau testnet"; no talk of prices or gains
  - a scene of our own test ships or bots says so in its words: simulated load is never shown as users
  - no wallet address or player name spoken or written on screen
  - every number in the words stands in the brief's facts (which the maker counted from the logbook or facts.json)
  - nothing blames IDNI; the description says "not affiliated with IDNI"

Run: python yt_brief.py <brief.json>   (prints what is wrong, exit 1; or the timeline)
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCENES_PATH = os.environ.get("YT_SCENES", os.path.join(HERE, "yt_scenes.json"))
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
WPM = 150.0            # spoken words a minute, for the plan before the voice exists
LEAD = 0.8             # seconds of picture before the voice begins in a scene
RATIO = 0.6            # at most this share of a scene is spoken (a starting value of ours; yt.py learn moves it)
HOOK_WORDS = 38        # the first scene's words: about 15 seconds
TITLE_MAX = 70         # YouTube takes 100; longer than this is cut off in the lists
KINDS = ("answer", "weekly", "short")
SHORT_MAX = 58.0       # seconds; a short stays under a minute
LONG_MAX = 8 * 60.0
MEMBERS = "https://tau-hud-shop.fourthwall.com/supporters/pricing"
SHOP = "https://tau-hud-shop.fourthwall.com"

HYPE = re.compile(r"\b(moon(ing)?|100x|10x|lambo|pump(ing)?|price target|to the moon|get rich|profit|invest(ment|ing)?|"
                  r"buy (now|agrs|\$agrs)|financial advice|guaranteed|bullish|bearish)\b", re.I)
NEVER = re.compile(r"\b(matrix|uplink|bug bounty|proof[- ]of[- ]work)\b", re.I)
WRONG_NAME = re.compile(r"\b(the )?tau (test ?net|network|chain|blockchain)\b(?! alpha)", re.I)
BLAME = re.compile(r"\b(fault|blame[sd]?|broke|botched|screwed|incompetent|careless|sloppy)\b", re.I)
ADDRESS = re.compile(r"\b[0-9a-f]{24,}\b", re.I)
SAYS_SIM = re.compile(r"\b(our (own )?(test )?(ship|ships|bot|bots|load test)|load test|test ship|simulated|test load|we (send|sent))", re.I)
NUM = re.compile(r"\d[\d,.]*\d|\d")


def scenes() -> dict:
    with open(SCENES_PATH, encoding="utf-8") as f:
        return json.load(f)["scenes"]


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def words(text: str) -> int:
    return len(re.findall(r"[\w$'’%-]+", text or ""))


def speech_seconds(text: str) -> float:
    return words(text) * 60.0 / WPM


def numbers(text: str) -> set[str]:
    """Every number in a text, without thousands separators ("100,000" and "100000" are one number)."""
    out = set()
    for m in NUM.findall(text or ""):
        n = m.replace(",", "").rstrip(".")
        if n:
            out.add(n)
    return out


def _texts(brief: dict) -> list[tuple[str, str]]:
    """(where, text) of everything a viewer hears or reads."""
    out = [("title", brief.get("title", "")), ("question", brief.get("question", ""))]
    th = brief.get("thumb") or {}
    out += [("preview picture", f"{th.get('words', '')} {th.get('number', '')}")]
    for i, s in enumerate(brief.get("scenes") or [], 1):
        out += [(f"scene {i} words", s.get("say", "")), (f"scene {i} caption", s.get("caption", ""))]
    out.append(("description", brief.get("description", "")))
    return out


def check(brief: dict, cat: dict | None = None) -> list[str]:
    cat = scenes() if cat is None else cat
    bad: list[str] = []
    kind = brief.get("kind")
    if kind not in KINDS:
        bad.append(f"kind must be one of {', '.join(KINDS)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}", brief.get("id", "")):
        bad.append("id: small letters, digits and dashes")
    q = (brief.get("question") or "").strip()
    if not q.endswith("?") or q.count("?") != 1:
        bad.append("one question, ending in a question mark (no question, no video)")
    if not (brief.get("audience") or "").strip():
        bad.append("audience: say for whom this video is")
    title = (brief.get("title") or "").strip()
    if not title:
        bad.append("title missing: the title is written before the film")
    elif len(title) > TITLE_MAX:
        bad.append(f"title has {len(title)} signs, at most {TITLE_MAX}")
    if "<" in title or ">" in title:
        bad.append("title: YouTube takes no < or >")
    th = brief.get("thumb") or {}
    if not (th.get("words") or "").strip():
        bad.append("preview picture: its few words are missing")
    elif words(th["words"]) > 4:
        bad.append("preview picture: at most 4 words")
    sc = brief.get("scenes") or []
    if len(sc) < (1 if kind == "short" else 3):
        bad.append("too few scenes")
    for i, s in enumerate(sc, 1):
        c = cat.get(s.get("scene"))
        if not c:
            bad.append(f"scene {i}: the film service knows no view called {s.get('scene')!r}")
            continue
        say = s.get("say") or ""
        if c.get("sim") and say and not SAYS_SIM.search(say):
            bad.append(f"scene {i} shows our own test ships or bots and its words do not say so (say \"our test ships\" or \"load test\")")
        if s.get("moment") and not c.get("moment"):
            bad.append(f"scene {i} is marked as the moment, but {s['scene']} shows nothing being refused")
        if s.get("voice", "main") not in ("main", "rico"):
            bad.append(f"scene {i}: voice is main or rico")
        if s.get("voice") == "rico" and words(say) > 16:
            bad.append(f"scene {i}: Rico only throws in a short line (at most 16 words)")
    if sc and words(sc[0].get("say", "")) > HOOK_WORDS:
        bad.append(f"the first scene speaks {words(sc[0]['say'])} words; the hook is at most {HOOK_WORDS} (about 15 seconds)")
    if sc and not (sc[0].get("say") or "").strip():
        bad.append("the first scene needs its words: they keep the title's promise")
    if kind in ("answer", "weekly") and not any(s.get("moment") for s in sc):
        bad.append("no scene is marked as the moment (a rule or the chain says no, in view)")
    if kind == "weekly" and not any(s.get("bonus") for s in sc):
        bad.append("a weekly video has one bonus scene after its high point")
    facts = json.dumps(brief.get("facts") or {}, ensure_ascii=False)
    known = numbers(facts)
    for where, text in _texts(brief):
        if not text:
            continue
        if where != "description":
            missing = sorted(n for n in numbers(text) if n not in known)
            if missing:
                bad.append(f"{where}: {', '.join(missing)} stand{'s' if len(missing) == 1 else ''} in no fact of this brief")
        m = HYPE.search(text)
        if m:
            bad.append(f"{where}: \"{m.group(0)}\" reads as coin talk")
        m = NEVER.search(text)
        if m:
            bad.append(f"{where}: \"{m.group(0)}\" does not belong in a video of ours")
        m = WRONG_NAME.search(text)
        if m:
            bad.append(f"{where}: \"{m.group(0)}\": the network is Tau Net (its test network: the Tau Net testnet, Tau Testnet Alpha)")
        if ADDRESS.search(text):
            bad.append(f"{where}: a wallet address; no wallet or player is named without being asked")
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if "IDNI" in sentence and BLAME.search(sentence):
                bad.append(f"{where}: a sentence puts blame on IDNI")
    if brief.get("next") and not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}", brief["next"]):
        bad.append("next: the id of the video the end points to")
    t = timeline(brief, cat=cat)
    if t and kind == "short" and t["seconds"] > SHORT_MAX:
        bad.append(f"a short of {t['seconds']:.0f} s; at most {SHORT_MAX:.0f}")
    if t and kind != "short" and t["seconds"] > LONG_MAX:
        bad.append(f"{t['seconds'] / 60:.1f} minutes; at most {LONG_MAX / 60:.0f}")
    return bad


def timeline(brief: dict, spoken: dict[int, float] | None = None, cat: dict | None = None, ratio: float | None = None) -> dict | None:
    """When each scene starts and how long it runs. spoken: scene number (from 0) to the real length of its voice
    clip in seconds; without it the length is guessed from the words. A scene is never shorter than its view needs
    (min), than the brief asks (seconds), or than LEAD + words / ratio: the picture always has the larger share."""
    cat = scenes() if cat is None else cat
    ratio = RATIO if ratio is None else ratio
    rows, t, talk = [], 0.0, 0.0
    for i, s in enumerate(brief.get("scenes") or []):
        c = cat.get(s.get("scene"))
        if not c:
            return None
        say = (spoken or {}).get(i, speech_seconds(s.get("say", "")))
        dur = max(float(c.get("min") or 6), float(s.get("seconds") or 0), LEAD + say / ratio if say else 0)
        if brief.get("kind") == "short":      # a short is all moment: its words may fill more of it
            dur = max(float(s.get("seconds") or 0), min(dur, LEAD + say + 1.2) if say else float(c.get("min") or 6))
        rows.append({"n": i, "scene": s["scene"], "start": round(t, 2), "seconds": round(dur, 2), "voice_at": round(t + LEAD, 2),
                     "say": round(say, 2)})
        t += dur
        talk += say
    return {"scenes": rows, "seconds": round(t, 2), "spoken": round(talk, 2), "share": round(talk / t, 3) if t else 0.0}


def description(brief: dict, urls: dict[str, str] | None = None) -> str:
    """What stands under the video: the answer in a line, the pages shown, how to help, and that we are not IDNI.
    urls: id of another video to its address, for the "next" line."""
    lines = [(brief.get("description") or brief.get("question") or "").strip(), ""]
    cat = scenes()
    seen = []
    for s in brief.get("scenes") or []:
        p = (cat.get(s.get("scene")) or {}).get("page")
        if p and p not in seen:
            seen.append(p)
    ref = "ref=yt-" + brief.get("id", "video")[:40]
    lines.append("See it live:")
    lines += [f"{SITE}{p}?{ref}" for p in seen[:6]]
    nxt = (urls or {}).get(brief.get("next") or "")
    if nxt:
        lines += ["", f"Next: {nxt}"]
    lines += ["", f"Tau HUD is free and has no ads of its own. The crew that carries its costs: {MEMBERS}",
              f"Shop: {SHOP}", f"Talk with us on Telegram: {SITE}/telegram/?{ref}"]
    if brief.get("sources"):
        lines += ["", "Sources:"] + [str(u) for u in brief["sources"][:8]]
    lines += ["", "Everything shown is the Tau Net testnet (Tau Testnet Alpha): test coins without value, nothing here is "
              "financial advice. Load from our own test ships and bots is named as such.",
              "Tau HUD is a community project, not affiliated with IDNI."]
    text = "\n".join(lines).replace("<", "(").replace(">", ")")
    while len(text.encode()) > 4900:
        text = text[:-200]
    return text


def tags(brief: dict) -> list[str]:
    base = ["Tau Net", "Tau Testnet Alpha", "Tau language", "Tau HUD", "AGRS", "Agoras", "testnet", "blockchain rules"]
    out, total = [], 0
    for t in list(brief.get("tags") or []) + base:
        t = str(t).strip()
        if t and t.lower() not in [o.lower() for o in out] and total + len(t) + 3 <= 480:
            out.append(t)
            total += len(t) + 3
    return out


if __name__ == "__main__":
    b = load(sys.argv[1])
    wrong = check(b)
    for w in wrong:
        print("  -", w)
    if wrong:
        sys.exit(1)
    tl = timeline(b)
    print(f"{b['id']}: {tl['seconds']:.0f} s, {tl['share'] * 100:.0f} % spoken")
    for r in tl["scenes"]:
        print(f"  {r['start']:6.1f}  {r['seconds']:5.1f} s  {r['scene']}")
