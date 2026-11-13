"""Big IDNI news as a blog article (Kilian, 13 November 2026: "such big news is worth a blog post that goes deeper:
what is the value for the user"). When the daily IDNI post (idni_digest.py) marks its window as worth an article (a
new capability every user can try, or a change to what users or node runners can do), the blog service writes a
draft that explains it: what changed, what it gives the user, where it stops, what is still open.

Like the ships' articles it waits as an unlisted draft (up blog drafts); the owner gets its address privately, and it
goes on the blog by hand (up blog publish <id>) or by itself after BLOG_AUTO_PUBLISH_HOURS when its check is clean.

Facts: the daily post's own text and, for each change of its window, the commit message, the files, the code diff and
the docs diff from our clone of IDNI's repository (/state/devpulse, written by devpulse.py). Every number in the
English text must appear in them, and blame and hype words are marked: either keeps the draft from going out by itself.

Run by blog.py's loop (one draft a round); python news_article.py <digest id> writes one by hand.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger("news_article")

REPO = "IDNI/tau-testnet"
START = int(datetime(2026, 11, 14, tzinfo=timezone.utc).timestamp())   # the personal rules of 12 November have a hand-written article
FRESH = 3 * 86400        # a window older than this gets no article any more
CHANGES = 8              # changes read per article at most

SYSTEM = """You write a news article for the blog of Tau HUD (tauhud.com), a community project not affiliated with \
IDNI, the team that builds Tau Net. Tau Net is the network; its test network is Tau Testnet Alpha (the Tau Net \
testnet). Tau Language is the language its rules are written in, and the Tau engine checks them. Never call the \
network just "Tau".

You get IDNI's changes of one window that our daily post already summed up (its text is included), each with its \
commit message, files, code diff and the changes to IDNI's own documentation. Write the article that goes deeper than \
the post, for curious people who are not developers: what changed, what it gives someone who uses the Tau Net testnet, \
where it stops, and what is still open.

Rules:
- Use ONLY what the input shows. Never invent numbers, causes, motives, plans, dates or effects. Every number you \
write must appear in the input. When the input does not say why IDNI did something, do not guess.
- Explain the value for the user in concrete terms (what they can do now that they could not before, what it protects \
against), but stay honest: where IDNI's documentation names a limit, say it plainly in "Where it stops".
- Credit IDNI plainly. Never blame, mock or lecture IDNI, Tau Net or the testnet. Never say IDNI did it because of \
Tau HUD or anyone else unless the input says so.
- Plain words. No code names, file names, function names, stream names or commit hashes in the text; explain an idea \
instead of naming its variable.
- No hype or marketing words (huge, exciting, revolutionary, game-changing, finally, breakthrough), no price talk, no \
coin talk, no exclamation marks, no emoji, no names of people.
- It is a testnet: say once that its coins have no value and that it can start over.
- Length: 400 to 700 English words in body.
- title: at most 60 characters, a real headline with subject and verb. dek: one sentence, at most 160 characters, \
that adds to the title.
- why: three lines, each at most 160 characters: for the user, for Tau Net, and one honest limit.
- body: Markdown with "## " section headings, short paragraphs and "- " lists. Sections in this order: "What \
changed", "What it gives you", "Where it stops", "What is still open". No title in body, no tables, no links.
- Numbers of 1,000 and more with commas (100,000).
- zh: Simplified Chinese, ja: Japanese, same meaning and the same numbers; keep Tau Net, Tau, IDNI and AGRS in Latin \
letters.
- x: one post for X, at most 200 characters, no link, no hashtags.
- card: the text on the article's picture, English only: "line", at most 60 characters, in other words than the \
title; "why", three points of at most 52 characters each.

Answer with JSON only, no other text:
{"title":{"en":"","zh":"","ja":""},"dek":{"en":"","zh":"","ja":""},"why":[{"en":"","zh":"","ja":""}],\
"body":{"en":"","zh":"","ja":""},"x":"","card":{"line":"","why":["","",""]}}"""


def _git(path: str, *a: str) -> str:
    return subprocess.run(["git", "-C", path, *a], check=True, capture_output=True, text=True, timeout=300).stdout


def change_text(path: str, sha: str) -> str:
    """One change as the writer reads it: message, files, code diff and docs diff (each cut)."""
    import devpulse as dp
    out = dp.commit_context(REPO, path, sha, limit=8000)
    try:
        parents = _git(path, "log", "-1", "--format=%P", sha).split()
        if parents:
            docs = _git(path, "diff", "--no-renames", "-U2", parents[0], sha, "--", "docs", "*.md")
            if docs.strip():
                out += "\nIDNI's documentation, changed by it (may be cut):\n" + docs[:8000]
    except subprocess.CalledProcessError:
        pass
    return out


def facts_of(d: dict, path: str) -> dict:
    return {"the daily post": {"title": d.get("title"), "points": d.get("points"), "why": d.get("why")},
            "changes": [change_text(path, s) for s in (d.get("shas") or [])[:CHANGES]]}


def ask(facts: dict) -> dict:
    import ai_meter
    import blog
    prompt = "IDNI's changes and our daily post about them (JSON):\n\n" + json.dumps(facts, ensure_ascii=False, indent=1)[:150000]
    body = {"model": blog.AI_MODEL, "max_tokens": blog.ROOM_MAX, "system": SYSTEM, "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": blog.ARTICLE_SHAPE}}}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": blog.AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"the API answered {e.code}: {e.read().decode('utf-8', 'replace')[:400]}") from None
    ai_meter.meter("blog", blog.AI_MODEL, j.get("usage"))
    if j.get("stop_reason") in ("refusal", "max_tokens"):
        raise RuntimeError(f"no article: {j.get('stop_reason')}")
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


def article(d: dict, facts: dict, out: dict, now: float) -> dict:
    import blog
    title, dek, body = blog.three(out.get("title"), 90), blog.three(out.get("dek"), 220), blog.three(out.get("body"), 9000)
    why = [w for w in (blog.three(x, 200) for x in (out.get("why") or [])[:3]) if w]
    if not (title and dek and body and why):
        raise ValueError("the answer misses a title, dek, why or body in one of the languages")
    en = " ".join([title["en"], dek["en"], body["en"], *[w["en"] for w in why], str(out.get("x") or "")])
    on = blog.local(d.get("end") or now).strftime("%Y-%m-%d")
    plain = lambda t: re.sub(r"(?<=\d),(?=\d{3}(?![\d,]))", "", t)   # 100,000 in the text is 100000 in the code
    check = {"unknown_numbers": blog.unknown_numbers(plain(en), json.loads(plain(json.dumps(facts, ensure_ascii=False)))),
             "hype": sorted({m.group(0) for m in blog.HYPE.finditer(en)} | {m.group(0) for m in blog.BLAME.finditer(en)})}
    return {"id": f"{on}-idni-news", "on": on, "kind": "news", "digest": d.get("id"), "t0": int(d.get("end") or now),
            "title": title, "dek": dek, "why": why, "body": body, "x": " ".join(str(out.get("x") or "").split())[:240],
            "sources": [f"https://github.com/{REPO}/commit/{s}" for s in (d.get("shas") or [])[:CHANGES]],
            "check": check, "card": blog.card_of(out.get("card"), title["en"]), "written": int(now), "model": blog.AI_MODEL}


def write_draft(d: dict, path: str, now: float | None = None, ask_=None) -> str:
    """The draft for one digest window, unlisted under /blog/drafts/ like a ship's article; returns its id."""
    import blog
    now = now or time.time()
    facts = facts_of(d, path)
    a = article(d, facts, (ask_ or ask)(facts), now)
    try:
        a = blog.pictures(a)
    except Exception as e:  # noqa: BLE001 - an article without its picture beats no article
        log.warning("news article picture: %s", e)
    st = blog.state()
    name = st["drafts"].get(a["id"]) or f"{a['id']}-{secrets.token_hex(4)}"
    st["drafts"][a["id"]] = name
    st.setdefault("drafted_at", {})[a["id"]] = round(now)
    st.setdefault("news_drafted", {})[d["id"]] = a["id"]
    a["status"] = "draft"
    blog.write_json(os.path.join(blog.PUBLIC, "drafts", name + ".json"), a)
    blog.write_json(blog.STATE, st)
    return a["id"]


def due(items: list[dict], drafted: dict, now: float) -> list[dict]:
    return [d for d in items if d.get("article") and d.get("status") in ("ready", "check") and d.get("shas")
            and (d.get("end") or 0) >= START and now - (d.get("end") or 0) <= FRESH and d["id"] not in drafted]


def tick(now: float | None = None, ask_=None) -> str | None:
    """One draft a round, for the newest window the daily post marked as worth an article."""
    import blog
    import devpulse as dp
    import idni_digest
    now = now or time.time()
    st = blog.state()
    if not blog.AI_KEY or now - st.get("news_failed_at", 0) < blog.RETRY_AFTER:
        return None
    todo = due(idni_digest.load().get("items") or [], st.get("news_drafted") or {}, now)
    if not todo:
        return None
    d = todo[-1]
    path = os.path.join(dp.CLONES, REPO.replace("/", "__") + ".git")
    try:
        did = write_draft(d, path, now, ask_)
    except Exception as e:  # noqa: BLE001 - tried again after RETRY_AFTER; nothing half-written is kept
        log.warning("news article for %s: %s", d.get("id"), e)
        st = blog.state()
        st["news_failed_at"] = now
        blog.write_json(blog.STATE, st)
        return None
    url = blog.draft_url(blog.state(), did)
    log.info("news draft %s written: %s", did, url)
    try:
        import cruise_crier
        cruise_crier.tell_draft(did, url)
    except Exception as e:  # noqa: BLE001
        log.warning("news draft %s not told: %s", did, e)
    return did


if __name__ == "__main__":
    import sys
    import idni_digest
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    want = sys.argv[1] if len(sys.argv) > 1 else None
    items = [d for d in idni_digest.load().get("items") or [] if d.get("shas") and (want is None or d["id"] == want)]
    if not items:
        print("no window with changes" + (f" named {want}" if want else ""))
        sys.exit(1)
    import devpulse as dp
    print("draft", write_draft(items[-1], os.path.join(dp.CLONES, REPO.replace("/", "__") + ".git")))
