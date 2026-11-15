"""A second read of every blog draft against our own rules, before the owner looks at it (Kilian, 15 November 2026:
"reason against our knowledge base again when you have drafted them").

A language model (NEWS_AI_KEY) reads the English draft with the rules below, the editorial rules Tau HUD has settled on
over the weeks, and answers with at most six concrete notes: the sentence and what to change. It never changes the
draft and never stops it; the notes go with the owner's Telegram message and into the draft (`editor`), so the read
before publishing starts where it matters. Without a key, or when the model fails, there are no notes and nothing else
changes.

  python editor.py <draft id>   the notes for one waiting draft
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402

log = logging.getLogger("editor")

RULES = """Tau HUD's rules for its blog (tauhud.com/blog/), a community project not affiliated with IDNI:
1. Meaning first. A post says what the numbers mean for people who use or follow the Tau Net testnet, then backs it with \
numbers. A post that only lists numbers fails this rule. Readers should want to read it, without clickbait or trolling.
2. Naming: the network is Tau Net; its test network is Tau Testnet Alpha or "the Tau Net testnet". Tau alone is the \
language rules are written in (and the Tau engine checks them), never the network.
3. Never blame, mock or lecture IDNI or the testnet. Credit what held up. Own what went wrong on our side plainly.
4. Chain restarts: as seen, cause unknown unless IDNI said it. When one came during or right after one of our cruise \
ships' visits, the post must not rule out our own test traffic.
5. Users: only transactions by users of our apps (Agorzilla, Tau HUD, White Rabbit Key, players in No Memo) and other \
wallets are people's. Simulated cruise passengers, the island bot, No Memo's own wallets, the hack-of-the-week wallets \
and IDNI's genesis accounts (IDNI's own testing) are never users. No Memo's players are real people. Wallets, not people.
6. Every number must be grounded in the post's own data; no invented causes, plans or effects.
7. No hype or marketing words, no price or coin talk, no exclamation marks, no emoji, no names of people.
8. Plain words for non-developers; no code, file or field names. Labels and captions read as natural English, never \
clipped or inverted ("transactions, our test traffic not counted" is wrong; "transactions by users of our apps" is right).
9. Short paragraphs with air; a "why it matters" that says why at a glance.
10. Our apps named in the text are linked to their pages. It is a testnet: coins have no value, it can start over."""

ASK = RULES + """

Read the draft below as an editor. Name what breaks a rule or reads weak, most important first, at most six notes. \
Each note: the exact words from the draft (short), the rule number, and the better wording or the fix. If nothing \
needs a change, answer with no notes. Answer with JSON only: {"notes": [{"quote": "", "rule": 1, "fix": ""}]}"""


def text_of(a: dict) -> str:
    en = lambda v: (v or {}).get("en", "") if isinstance(v, dict) else str(v or "")  # noqa: E731
    why = "\n".join("- " + en(w) for w in a.get("why") or [])
    tiles = "\n".join(f"- {t[0]} {t[1]}" for t in a.get("stats") or [] if len(t) > 1)
    caps = "\n".join("- " + en(f.get("caption")) for f in a.get("figures") or [])
    return (f"TITLE: {en(a.get('title'))}\nDEK: {en(a.get('dek'))}\nWHY IT MATTERS:\n{why}\n"
            + (f"PICTURE TILES:\n{tiles}\n" if tiles else "") + (f"CHART CAPTIONS:\n{caps}\n" if caps else "")
            + f"X POST: {a.get('x') or ''}\nBODY:\n{en(a.get('body'))}")


def review(a: dict, post=None) -> list[dict]:
    """[{quote, rule, fix}] for the draft `a`; [] without a key or when the model fails."""
    if not blog.AI_KEY and post is None:
        return []
    body = {"model": blog.AI_MODEL, "max_tokens": 4000, "system": ASK,
            "messages": [{"role": "user", "content": text_of(a)[:30000]}]}
    try:
        if post:
            j = post(body)
        else:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
                "x-api-key": blog.AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                j = json.load(r)
            import ai_meter
            ai_meter.meter("blog", blog.AI_MODEL, j.get("usage"))
        out = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", out, re.S)
        notes = (json.loads(m.group(0)) if m else {}).get("notes") or []
    except Exception as e:  # noqa: BLE001 - no notes beats no draft
        log.warning("editor: %s", e)
        return []
    keep = []
    for x in notes[:6]:
        if isinstance(x, dict) and str(x.get("fix") or "").strip():
            keep.append({"quote": " ".join(str(x.get("quote") or "").split())[:160], "rule": x.get("rule"),
                         "fix": " ".join(str(x["fix"]).split())[:300]})
    return keep


def lines(a: dict) -> list[str]:
    """The notes for the owner's message: a short block, or one line saying the read found nothing."""
    notes = a.get("editor")
    if notes is None:
        return []
    if not notes:
        return ["", "Second read against our rules: nothing to change."]
    out = ["", f"Second read against our rules, {len(notes)} note{'s' if len(notes) != 1 else ''}:"]
    for x in notes:
        out.append(f"• \"{x['quote']}\" (rule {x['rule']}): {x['fix']}" if x["quote"] else f"• (rule {x['rule']}): {x['fix']}")
    return out


def main(argv: list[str]) -> int:
    st = blog.state()
    if not argv or argv[0] not in st["drafts"]:
        print(__doc__)
        return 2
    a = blog.read_json(os.path.join(blog.PUBLIC, "drafts", st["drafts"][argv[0]] + ".json"), {})
    a["editor"] = review(a)
    print("\n".join(lines(a)) or "no key: no second read")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
