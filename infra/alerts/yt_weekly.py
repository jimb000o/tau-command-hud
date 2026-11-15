"""The week's one question (yt.py): what the relay and the site counted in the last seven days goes to the writer, who
picks the strongest finding, puts it as ONE question and writes the brief for it (yt_brief.py), or says there is none
this week. No strong question, no video.

What the writer may use is only what stands in the week's facts (week()): every number in the brief's own facts is
looked up there again (grounded()), and the brief's words are checked against the brief's facts (yt_brief.check).
The views it may show are the film service's (yt_scenes.json); it writes no selector and no page of its own.

The same writer makes a short (kind "short"): one moment, 20 to 45 seconds, one to three scenes.

Run: python yt_weekly.py facts     the week's facts as the writer gets them
     python yt_weekly.py brief     the brief it would write now (costs one answer; nothing is filmed)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request

import ai_meter
import yt_brief

log = logging.getLogger("yt.weekly")
RELAY = os.environ.get("RELAY_HTTP", "http://relay:8080").rstrip("/")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
AI_KEY = os.environ.get("NEWS_AI_KEY", "").strip()
AI_MODEL = os.environ.get("YT_AI_MODEL", "").strip() or os.environ.get("NEWS_AI_MODEL", "claude-sonnet-5-5")
WEEK = 7 * 86400

_opener = urllib.request.urlopen

SYSTEM = """You write the brief for one short video of the YouTube channel "Tau HUD". The channel shows the Tau Net testnet (Tau Testnet Alpha) at work, with real pictures of tauhud.com.

You get the facts of the last seven days as JSON, the views that can be filmed, and what earlier videos taught us. Pick the ONE strongest finding of the week and turn it into one question a curious viewer would ask. If nothing in the facts is worth a video, answer {"none": "<why, one sentence>"} and nothing else.

Rules that are checked by a program after you:
- One question. A title of at most 70 signs that promises exactly what the video shows. A preview picture of at most 4 words, and one number only if it stands in the facts.
- The first scene is the hook: at most 38 spoken words, and it already begins to answer the title.
- The picture leads. Words say only what the viewer cannot see: why it matters, what it means. Never read the screen aloud. Short words, short sentences, written for the ear. Say "transactions", never "txs".
- Exactly one scene is marked "moment": true, and it must be a view where the chain or a rule refuses something. The video builds towards it.
- For kind "weekly": one scene after the moment is marked "bonus": true (one more thing worth staying for). End with a line that makes the viewer want the next video; do not say goodbye.
- Every number you write must stand in "facts" of your brief, and every number in "facts" must stand in the week's facts you were given. Copy numbers exactly. If you are not sure of a number, leave it out.
- The network is "Tau Net"; its test network is "the Tau Net testnet" or "Tau Testnet Alpha". "Tau" alone is the language. Never "the Tau testnet".
- Views marked sim show OUR OWN test ships and bots. Their words must say "our test ships" or "our load test". They are never users, passengers are never people.
- Never name a wallet address or a player. Never talk about prices, gains or the future value of anything. No promises about mainnet.
- When something went wrong on our side, say so plainly. Never put blame on IDNI (the team that builds Tau Net). We are a community project, not affiliated with IDNI.
- One scene may have "voice": "rico": a dry, funny aside of at most 16 words by Rico, a radio host. All other scenes use "voice": "main".
- English only.

Answer with the brief as one JSON object and nothing else:
{"id": "<kind>-<yyyy>-<mm>-<dd>-<two-or-three-words>", "kind": "...", "audience": "...", "question": "...?", "title": "...",
 "thumb": {"words": "...", "number": "", "agorzilla": "grown"},
 "scenes": [{"scene": "<id of a view>", "say": "...", "caption": "<at most 6 words on screen>", "voice": "main", "moment": false, "bonus": false}],
 "description": "<the answer in two sentences>", "facts": {"<name>": "<fact with its number, copied from the week's facts>"},
 "sources": ["https://tauhud.com/..."], "tags": ["..."]}"""


def _get(url: str, timeout: int = 30):
    with _opener(urllib.request.Request(url, headers={"User-Agent": "tauhud-yt/1 (+https://tauhud.com)"}), timeout=timeout) as r:
        return json.loads(r.read())


def _try(name: str, fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001  one source down must not stop the week
        log.info("week: no %s (%s)", name, e)
        return None


def _trim(v, depth: int = 0):
    """Small enough for the writer: long lists cut to their first twelve, long texts to 400 signs, no addresses."""
    if isinstance(v, dict):
        return {k: _trim(x, depth + 1) for k, x in list(v.items())[:40] if depth < 5}
    if isinstance(v, list):
        return [_trim(x, depth + 1) for x in v[:12]] if depth < 5 else []
    if isinstance(v, str):
        return yt_brief.ADDRESS.sub("(a wallet)", v)[:400]
    return v


def week(now: float | None = None) -> dict:
    """What the last seven days hold, from our own public data. Each part is left out when its source is down."""
    now = time.time() if now is None else now
    since = now - WEEK
    out: dict = {"days": [time.strftime("%Y-%m-%d", time.gmtime(since)), time.strftime("%Y-%m-%d", time.gmtime(now))]}
    for name, path in (("status", "/status"), ("chain_history", "/history"), ("health", "/health-score"), ("active_wallets", "/wallets/active"),
                       ("who_sent_transactions", "/api/v1/sources"), ("rules_wall", "/rulewall"), ("showcase_wallets", "/showcase"),
                       ("load_tests", "/load")):
        v = _try(name, lambda p=path: _get(RELAY + p))
        if v is not None:
            out[name] = _trim(v)
    visits = _try("cruise", lambda: _get(RELAY + "/cruise/log?n=1")) or {}
    ships = []
    for vid in (visits.get("visits") or [])[:6]:
        vid = vid.get("id") if isinstance(vid, dict) else vid
        if not vid or str(vid)[:10] < out["days"][0]:
            continue
        rows = (_try("visit", lambda v=vid: _get(RELAY + f"/cruise/log?visit={v}&n=2000")) or {}).get("entries") or []
        kinds: dict = {}
        for r in rows:
            k = str(r.get("kind") or r.get("what") or "entry")
            kinds[k] = kinds.get(k, 0) + 1
        ships.append({"visit": vid, "our_own_test_ship": True, "logbook_entries": len(rows), "by_kind": kinds})
    if ships:
        out["our_test_ships"] = ships
    posts = _try("blog", lambda: _get(SITE + "/assets/blog/posts.json")) or []
    posts = posts.get("posts") if isinstance(posts, dict) else posts
    out["our_blog"] = [_trim({k: p.get(k) for k in ("id", "date", "title", "summary", "lede") if p.get(k)})
                       for p in (posts or []) if str(p.get("date") or p.get("id") or "")[:10] >= out["days"][0]][:6]
    ups = _try("updates", lambda: _get(SITE + "/assets/updates.json")) or []
    out["site_changes"] = [_trim({"on": e.get("on"), "text": (e.get("major") or {}).get("title") or e.get("text") or e.get("en")})
                           for e in ups if isinstance(e, dict) and str(e.get("on") or "")[:10] >= out["days"][0]][:12]
    return out


def grounded(brief: dict, facts: dict) -> list[str]:
    """Numbers in the brief's facts that the week's facts do not hold."""
    known = yt_brief.numbers(json.dumps(facts, ensure_ascii=False))
    return sorted(n for n in yt_brief.numbers(json.dumps(brief.get("facts") or {}, ensure_ascii=False)) if n not in known and len(n) > 1)


def _ask(messages: list[dict]) -> str:
    body = {"model": AI_MODEL, "max_tokens": 6000, "system": SYSTEM, "messages": messages}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with _opener(req, timeout=300) as r:
            j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"the writer's API answered {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    ai_meter.meter("yt", AI_MODEL, j.get("usage"))
    if j.get("stop_reason") == "refusal":
        raise RuntimeError("the writer declined")
    return "".join(b.get("text", "") for b in j.get("content") or [] if b.get("type") == "text")


def _json(text: str) -> dict:
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON in the writer's answer")
    return json.loads(text[a:b + 1])


def write(kind: str = "weekly", facts: dict | None = None, learned: list[str] | None = None, done: list[str] | None = None,
          now: float | None = None) -> tuple[dict | None, str]:
    """(the brief, "") or (None, why there is none). At most two tries: the checker's findings go back once."""
    if not AI_KEY:
        return None, "no writer (NEWS_AI_KEY in infra/.env)"
    facts = week(now) if facts is None else facts
    cat = yt_brief.scenes()
    views = {k: {"shows": v["what"], **({"sim": True} if v.get("sim") else {}), **({"moment": True} if v.get("moment") else {})} for k, v in cat.items()}
    ask = (f"kind: {kind}" + (" (20 to 45 seconds, one to three scenes, all of it one moment; the date in the id)" if kind == "short" else
                              " (4 to 6 minutes, 8 to 14 scenes)") +
           f"\ntoday: {time.strftime('%Y-%m-%d', time.gmtime(time.time() if now is None else now))}"
           "\n\nViews that can be filmed:\n" + json.dumps(views, ensure_ascii=False, indent=1) +
           "\n\nWhat earlier videos taught us:\n" + ("\n".join("- " + s for s in learned) if learned else "- nothing yet") +
           "\n\nQuestions already answered (do not repeat):\n" + ("\n".join("- " + s for s in (done or [])[-30:]) or "- none") +
           "\n\nThe week's facts:\n" + json.dumps(facts, ensure_ascii=False, indent=1))
    messages = [{"role": "user", "content": ask}]
    why = ""
    for _ in range(2):
        text = _ask(messages)
        try:
            brief = _json(text)
        except ValueError as e:
            why = str(e)
            messages += [{"role": "assistant", "content": text[:4000]}, {"role": "user", "content": "That was not one JSON object. Answer with the brief as JSON only."}]
            continue
        if brief.get("none"):
            return None, "no strong question this week: " + str(brief["none"])[:300]
        brief["kind"] = kind
        wrong = yt_brief.check(brief, cat)
        loose = grounded(brief, facts)
        if loose:
            wrong.append(f"numbers in your facts that the week's facts do not hold: {', '.join(loose)}")
        if not wrong:
            return brief, ""
        why = "; ".join(wrong)
        messages += [{"role": "assistant", "content": text[:8000]},
                     {"role": "user", "content": "The checker found:\n" + "\n".join("- " + w for w in wrong) + "\nWrite the whole brief again as JSON, with these mended."}]
    return None, "the brief did not pass the checker twice: " + why[:600]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.argv[1:2] == ["facts"]:
        print(json.dumps(week(), ensure_ascii=False, indent=1))
    else:
        b, w = write(sys.argv[2] if len(sys.argv) > 2 else "weekly")
        print(json.dumps(b, ensure_ascii=False, indent=1) if b else w)
