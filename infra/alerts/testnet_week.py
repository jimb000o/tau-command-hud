"""The Tau Net testnet this week, as a blog post (Kilian, 15 November 2026: the weekly report for IDNI becomes a weekly
post on tauhud.com/blog/ instead of an issue on IDNI/tau-testnet).

Every Sunday from 18:00 German time (IDNI_REPORT_WEEKDAY / IDNI_REPORT_HOUR) the blog loop writes the week as an
unlisted DRAFT and tells the owner's private Telegram chat (tickerwatch.tell, never the channel): where to read it and
the one line that publishes it. It never goes on the blog by itself (the draft carries "by_hand", so blog.auto_publish
leaves it), and nothing is filed on GitHub.

Every number is counted here from our own public data (idni_report.gather / facts: /uptime, /health-score, /stats,
/cruise/log, our node's log; plus /history for the blocks of every chain of the week and /api/v1/sources for where the
transactions came from). The English text is written by this script, not by a language model; with NEWS_AI_KEY a
model only translates it to Chinese and Japanese, and a translation with a number the English text does not hold is
dropped (the page then shows English).

Wording: a chain restart is said as seen, with its cause unknown; when it came during or within an hour after one of
our ships' visits, the post says so and that we have not ruled out our own traffic. Our own trouble stands under "On
our side". Simulated passengers and our other automated senders are never counted as users. No blame, no hype.

The address stays the same for a week: tauhud.com/blog/?p=testnet-week-<year>-w<week> (2026-w46 for 9 to 15 November).

  python testnet_week.py               this week so far, as the post would read (nothing written, nothing sent)
  python testnet_week.py last          the same for last week
  python testnet_week.py draft [last]  write the draft now (anew, same address) and tell the owner on Telegram
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import idni_report as ir  # noqa: E402  (the week's bounds and its numbers, counted from our public data)

log = logging.getLogger("testnet-week")

ON = os.environ.get("TESTNET_WEEK", "true").lower() in ("1", "true", "yes")
UP = 'ssh root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh {}"'
NEAR = 3600            # a restart this long after a ship's last logbook line still counts as "around a visit"
RETRY = 3600
PREFIX = "testnet-week-"
X_URL = re.compile(r"^https://(x|twitter)\.com/\w{1,15}/status/\d+$")   # only a post's own address, as the blog page links it

# where the transactions came from (relay/txsources.py): people's wallets on our apps and elsewhere, and our own
# server's automated senders, which are never users
PEOPLE = (("agorzilla", "Agorzilla"), ("tauhud", "Tau HUD"), ("rabbit", "White Rabbit Key"), ("nomemo", "players in No Memo"),
          ("idni", "the accounts the testnet started with (set up by IDNI)"), ("other", "other wallets"))
OURS = (("cruise", "our cruise ships' simulated passengers"), ("nmsrv", "No Memo's own wallets"),
        ("hack", "the hack of the week's test wallets"), ("bot", "the island bot"))


def pid(wid: str) -> str:
    return PREFIX + wid


def n(x) -> str:
    return f"{int(x):,}"


def s(k: int, one: str, many: str | None = None) -> str:
    return f"{n(k)} {one if k == 1 else (many or one + 's')}"


# ---------- reading ----------
def gather(t0: float, t1: float) -> dict:
    raw = ir.gather(t0, t1)
    try:   # the week's feature posts on X (xfeatures.py, HUD #785); without it the post just has no "On X" section
        import xfeatures
        y, wk, _ = blog.local(t0).isocalendar()
        raw["x"] = list(xfeatures.week_lines(xfeatures.load(), y, wk) or [])
    except Exception as e:  # noqa: BLE001
        raw["x"] = []
        log.info("x posts not read: %s", e)
    for key, path in (("history", "/history"), ("sources", "/api/v1/sources"), ("cruise", "/cruise")):
        try:
            raw[key] = blog.get(path)
        except Exception as e:  # noqa: BLE001 - the post does without it and says less
            raw["missing"].append(path)
            log.warning("%s not read: %s", path, e)
    return raw


# ---------- counting ----------
def week_facts(raw: dict, t0: float, t1: float) -> dict:
    f = ir.facts(raw, t0, t1)
    f["posts"] = [p for p in f.get("posts") or [] if "?p=" + PREFIX not in p["url"]]
    h = raw.get("history") or {}
    fields = h.get("fields") or []
    if "blocks" in fields and "txs" in fields:
        ib, it = fields.index("blocks") + 2, fields.index("txs") + 2
        rows = [r for r in h.get("hours") or [] if len(r) > max(ib, it) and t0 <= (r[0] or 0) < t1]
        if rows:
            f["week"] = {"blocks": sum(r[ib] or 0 for r in rows), "txs": sum(r[it] or 0 for r in rows),
                         "chains": len({r[1] for r in rows})}
    days = (raw.get("sources") or {}).get("days") or {}
    d0, d1 = blog.local(t0).date().isoformat(), blog.local(t1 - 1).date().isoformat()
    by: dict = {}
    for d, groups in days.items():
        if d0 <= d <= d1 and isinstance(groups, dict):
            for g, v in groups.items():
                if isinstance(v, list) and v:
                    by[g] = by.get(g, 0) + (v[0] or 0)
    if by:
        f["sources"] = {"people": [(label, by[g]) for g, label in PEOPLE if by.get(g)],
                        "ours": [(label, by[g]) for g, label in OURS if by.get(g)],
                        "days": (d0, d1)}
    win = []
    for vid, entries in (raw.get("visits") or {}).items():
        ts = [e.get("t") for e in entries or [] if e.get("t")]
        if ts:
            ship = next((v["ship"] for v in f.get("visits") or [] if v["id"] == vid), vid)
            win.append((min(ts), max(ts), ship))
    for r in f.get("restarts") or []:
        at = r.get("old_tip_ts") or r.get("detected_at") or 0
        r["near"] = next((sh for a, b, sh in win if a - 600 <= at <= b + NEAR), None)
    f["x posts"] = [p for p in raw.get("x") or [] if isinstance(p, dict) and p.get("headline") and X_URL.match(str(p.get("url") or ""))]
    cr = raw.get("cruise")
    f["ships paused"] = isinstance(cr, dict) and cr.get("enabled") is False
    return f


# ---------- writing ----------
def span(f: dict) -> str:
    a, b = blog.local(f["from"]), blog.local(f["to"] - 1)
    return f"{a.day}–{b.day} {b.strftime('%b %Y')}" if a.month == b.month else f"{a.day} {a.strftime('%b')} – {b.day} {b.strftime('%b %Y')}"


def chain_counts(f: dict) -> tuple[int, int, int] | None:
    """(blocks, transactions, chains) of the week: over every chain from /history, else the current chain's only."""
    if f.get("week"):
        w = f["week"]
        return w["blocks"], w["txs"], w["chains"]
    if f.get("blocks"):
        return f["blocks"]["count"], f["blocks"]["txs"], 1
    return None


def restart_at(r: dict) -> float:
    return r.get("old_tip_ts") or r.get("detected_at") or 0


def text(f: dict) -> dict:
    """The post in English: title, dek, why, body (Markdown), card, hero numbers and the announcement's numbers."""
    rs, st, vs = f.get("restarts") or [], f.get("stalls") or [], f.get("visits") or []
    near = [r for r in rs if r.get("near")]
    cc = chain_counts(f)
    src = f.get("sources") or {}
    people = sum(k for _, k in src.get("people") or [])
    ours = sum(k for _, k in src.get("ours") or [])
    a, b = blog.local(f["from"]), blog.local(f["to"])

    title = f"The Tau Net testnet this week, {span(f)}"
    head = []
    if cc:
        head.append(f"{n(cc[0])} blocks, {n(cc[1])} transactions")
    head.append(s(len(rs), "chain restart"))
    dek = f"What our community node saw on Tau Testnet Alpha: {', '.join(head)}. Counted from our public logs."

    why = []
    if rs:
        why.append(f"A restart starts the testnet over: balances, rules and history begin again. It happened {s(len(rs), 'time')} this week.")
    else:
        why.append("No chain restart this week: what people set up on the testnet stayed.")
    if src.get("people"):
        why.append(f"{n(people)} transactions came from wallets on our apps and elsewhere; our own automated test traffic is counted apart.")
    else:
        why.append("One node's view of a public testnet, counted the same way every week, so weeks can be compared.")
    if rs:
        why.append("We do not know what caused the restarts" + (", and we have not ruled out our own test traffic." if near else "."))
    else:
        why.append("One node's view: corrections are welcome.")

    L = [f"Every Sunday we write down what our node saw on Tau Testnet Alpha in the week, counted from our public logs by "
         f"a script. This week: Monday {a.day} {a.strftime('%B')} to Sunday {b.day} {b.strftime('%B')}, {b.strftime('%H:%M')} "
         "German time. It is a testnet: its coins have no value, and it can start over.", ""]

    L.append("## The chain")
    if cc:
        L.append(f"- {n(cc[0])} blocks with {n(cc[1])} transactions" + (f", across {cc[2]} chains (a restart begins a new one)" if cc[2] > 1 else "")
                 + (f"; typically {f['block seconds']} seconds between blocks" if f.get("block seconds") else ""))
    mins = round(f["stall_seconds"] / 60)
    if st:
        L.append(f"- {s(len(st), 'pause')} of more than {mins} minutes without a block; the chain came back after each")
    else:
        L.append(f"- No pause of more than {mins} minutes without a block")
    L.append(f"- {s(len(f.get('reorgs') or []), 'reorg')} seen")
    if f.get("score"):
        sc = f["score"]
        L.append(f"- Our health score (our node's view of the testnet, 0 to 100): average {sc['average']}, lowest {sc['lowest']}")
    L.append("")

    if rs:
        L.append("## Chain restarts")
        L.append(f"The testnet started over {s(len(rs), 'time')} this week: a new block 1, and the old chain's balances, rules and "
                 "history gone with it.")
        L.append("")
        for r in rs:
            line = f"- {ir.utc(restart_at(r))}" + (f": the old chain ended at block {r['old_tip']}" if r.get("old_tip") else "")
            if r.get("near"):
                line += f", during or shortly after the visit of our cruise ship {r['near']}"
            L.append(line)
        L.append("")
        say = "We saw these restarts; we do not know what caused them."
        if near:
            say += (f" {'All' if len(near) == len(rs) else n(len(near)) + ' of them'} came while one of our cruise ships was "
                    "sending test traffic or within an hour after, so we have not ruled out that our own traffic plays a part.")
        if f.get("ships paused"):
            say += " Our cruise ships are paused for now."
        L += [say, ""]

    if src.get("people") or src.get("ours"):
        L.append("## Where the transactions came from")
        L.append("Counted per day (UTC), Monday to Sunday. Wallets, not people: one person can hold many.")
        L.append("")
        for label, k in src.get("people") or []:
            L.append(f"- {label}: {n(k)}")
        if src.get("ours"):
            L.append("")
            L.append(f"Our own server sent {n(ours)} more. They are real transactions, but not users:")
            L.append("")
            for label, k in src["ours"]:
                L.append(f"- {label}: {n(k)}")
        L.append("")

    if vs:
        L.append("## Our cruise ships")
        L.append("Simulated passengers, every stop a real transaction, paced so they never crowd the testnet.")
        L.append("")
        for v in vs:
            if not v["landed"]:
                L.append(f"- {v['day']}, {v['ship']}: did not land" + (f" ({v['why not']})" if v["why not"] else ""))
                continue
            line = f"- {v['day']}, {v['ship']}: {n(v['accepted'])} accepted, {n(v['refused'])} refused"
            if v["timeouts"]:
                line += f", {n(v['timeouts'])} sends our own node did not answer in time"
            if not v["over"]:
                line += " (still under way)"
            L.append(line + f" ([logbook]({blog.NODE}/cruise/log?visit={v['id']}))")
        L.append("")

    L.append("## On our side")
    ours_l = []
    if f.get("in sync") is not None:
        ours_l.append(f"- Our node was in sync {f['in sync'] * 100:.1f}% of the week and answered {f['node answering'] * 100:.1f}% "
                      f"of {n(f['checks'])} checks (one a minute).")
    if f.get("down node"):
        x = f["down node"]
        ours_l.append(f"- Our node did not answer {s(x['count'], 'time')}, {ir.mins(x['seconds'])} in all.")
    if f.get("down sync"):
        x = f["down sync"]
        ours_l.append(f"- Our node fell more than 2 blocks behind {s(x['count'], 'time')}, {ir.mins(x['seconds'])} in all.")
    if f.get("down relay"):
        x = f["down relay"]
        ours_l.append(f"- Our relay, which serves tauhud.com, was down {s(x['count'], 'time')}, {ir.mins(x['seconds'])} in all.")
    to = sum(v["timeouts"] for v in vs)
    if to:
        ours_l.append(f"- {s(to, 'send')} of our ships got no answer from our own node within 20 seconds: timeouts on our side, not refusals.")
    lg = f.get("log")
    if lg is not None:
        ours_l.append(f"- Our node's log held {s(lg['lines'], 'warning')} about syncing or peers, in {s(len(lg['groups']), 'kind')}."
                      if lg["lines"] else "- No warning about syncing or peers in our node's log.")
    L += ours_l or ["- Nothing to report on our side this week."]
    L.append("")

    if f.get("posts"):
        L.append("## Written up this week")
        L += [f"- [{p['title']}]({p['url']})" for p in f["posts"][:5]]
        L.append("")

    if f.get("x posts"):
        L.append("## On X this week")
        for p in f["x posts"][:8]:
            who = "@" + str(p.get("handle") or "").lstrip("@") if p.get("handle") else str(p.get("account") or "X")
            head = " ".join(str(p["headline"]).replace("[", "(").replace("]", ")").split())[:140]
            L.append(f"- {who}: [{head}]({p['url']})")
        L.append("")

    L.append(f"Tau HUD is a community project, not affiliated with IDNI. One node's view; if you saw something else, "
             "tell us and we correct it.")

    nums = []
    if cc:
        nums.append(f"{n(cc[0])} blocks, {n(cc[1])} transactions" + (f" across {cc[2]} chains" if cc[2] > 1 else ""))
    nums.append(f"{s(len(rs), 'chain restart')}" + (", cause unknown" if rs else "") + f", {s(len(st), 'long pause')}")
    if src.get("people"):
        nums.append(f"{n(people)} transactions from wallets on our apps and elsewhere, {n(ours)} from our own test traffic")
    if f.get("in sync") is not None:
        nums.append(f"our node in sync {f['in sync'] * 100:.1f}% of the week")

    stats = []
    if cc:
        stats.append([n(cc[0]), "blocks this week"])
    stats.append([str(len(rs)), "chain restarts, cause unknown" if rs else "chain restarts"])
    if src.get("people"):
        stats.append([n(people), "transactions, our test traffic not counted"])
    if f.get("in sync") is not None:
        stats.append([f"{f['in sync'] * 100:.1f}%", "our node in sync"])

    card = [blog.card_title(title), "What one community node saw, counted from its logs", "## Why it matters"]
    card += ["- " + c for c in (
        f"{s(len(rs), 'chain restart')}, cause unknown" if rs else "No chain restart this week",
        f"{n(people)} transactions from wallets" if src.get("people") else "Counted the same way every week",
        "Our own test traffic counted apart")]
    card.append("Tau HUD blog · community project, not affiliated with IDNI")
    return {"title": title, "dek": dek, "why": why, "body": "\n".join(L).rstrip(), "card": card, "stats": stats, "numbers": nums,
            "x": f"{', '.join(head)}. One community node's view of Tau Testnet Alpha, counted from its logs."}


# ---------- Chinese and Japanese ----------
TRANSLATE = """You translate a blog post of Tau HUD (tauhud.com), a community project not affiliated with IDNI, from \
English into Simplified Chinese (zh) and Japanese (ja). Keep the meaning exactly; add nothing, leave nothing out. Keep \
every number exactly as it is written, and write no number the English does not hold (write dates the English way, \
for example "9–15 Nov 2026", not with month numbers). Keep Markdown as it is ("## " headings, "- " lists, links with \
their addresses). Keep in Latin letters: Tau Net, Tau Testnet Alpha, Tau HUD, IDNI, Agorzilla, White Rabbit Key, No \
Memo, UTC, and the ships' names. Plain words, no exclamation marks.

Answer with JSON only: {"zh":{"title":"","dek":"","why":["","",""],"body":""},"ja":{...the same...}}"""


def nums(t: str) -> set[str]:
    return {x.replace(",", "") for x in blog.NUM.findall(t)}


def translate(en: dict) -> dict:
    """{"zh": {...}, "ja": {...}} for the languages whose translation came back whole and holds no number the English
    does not; {} without a key or when the model fails (the page then shows English)."""
    if not blog.AI_KEY:
        return {}
    src = {"title": en["title"], "dek": en["dek"], "why": en["why"], "body": en["body"]}
    body = {"model": blog.AI_MODEL, "max_tokens": blog.ROOM, "system": TRANSLATE,
            "messages": [{"role": "user", "content": json.dumps(src, ensure_ascii=False, indent=1)}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": blog.AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            j = json.load(r)
        import ai_meter
        ai_meter.meter("blog", blog.AI_MODEL, j.get("usage"))
        out = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", out, re.S)
        got = json.loads(m.group(0)) if m else {}
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning("translation: %s", e)
        return {}
    allowed = nums(json.dumps(src, ensure_ascii=False))
    ok = {}
    for lang in ("zh", "ja"):
        t = got.get(lang) if isinstance(got, dict) else None
        if not (isinstance(t, dict) and all(isinstance(t.get(k), str) and t[k].strip() for k in ("title", "dek", "body"))
                and isinstance(t.get("why"), list) and len(t["why"]) == len(en["why"])):
            log.warning("translation %s: not whole, left out", lang)
            continue
        extra = nums(json.dumps(t, ensure_ascii=False)) - allowed
        if extra:
            log.warning("translation %s: numbers the English does not hold %s, left out", lang, sorted(extra))
            continue
        ok[lang] = t
    return ok


# ---------- the draft ----------
def article(f: dict, wid: str, now: float, tr: dict | None = None) -> dict:
    en = text(f)
    tr = tr or {}
    pick = lambda k: {"en": en[k], **{lang: tr[lang][k] for lang in tr}}
    why = [{"en": w, **{lang: tr[lang]["why"][i] for lang in tr}} for i, w in enumerate(en["why"])]
    full = " ".join([en["title"], en["dek"], en["body"], *en["why"]])
    on = blog.local(f["to"] - 1).strftime("%Y-%m-%d")
    day = blog.local(f["to"] - 1)
    return {"id": pid(wid), "on": on, "kind": "week", "week": wid, "t0": int(now), "by_hand": True,
            "kicker": f"Testnet week · {day.day} {day.strftime('%B %Y')}",
            "title": pick("title"), "dek": pick("dek"), "why": why, "body": pick("body"), "x": en["x"][:240],
            "card": en["card"], "stats": en["stats"], "numbers": en["numbers"],
            "sources": [f"{blog.NODE}/uptime", f"{blog.NODE}/health-score", f"{blog.NODE}/history",
                        f"{blog.NODE}/api/v1/sources", f"{blog.NODE}/cruise/log"],
            "check": {"unknown_numbers": [], "hype": sorted({m.group(0) for m in blog.HYPE.finditer(full)}
                                                            | {m.group(0) for m in blog.BLAME.finditer(full)})},
            "written": int(now), "model": "script" + (f", translated by {blog.AI_MODEL}" if tr else "")}


def write_draft(f: dict, wid: str, now: float | None = None, tr: dict | None = None) -> str:
    """The week's draft, unlisted under /blog/drafts/ like every other; written anew (same id, same address) on a rerun."""
    now = now or time.time()
    a = article(f, wid, now, translate(text(f)) if tr is None else tr)
    try:
        if blog.make_hero(a, a["stats"]):
            a["image"] = f"{blog.NODE}/blog/img/{a['id']}-hero.jpg"
    except Exception as e:  # noqa: BLE001 - a post without its picture beats no post
        log.warning("week hero: %s", e)
    st = blog.state()
    name = st["drafts"].get(a["id"]) or f"{a['id']}-{secrets.token_hex(4)}"
    st["drafts"][a["id"]] = name
    st.setdefault("drafted_at", {})[a["id"]] = round(now)
    st.setdefault("pics", {})[a["id"]] = blog.pics_version(a)
    a["status"] = "draft"
    a = blog.with_notes(a)
    blog.write_json(os.path.join(blog.PUBLIC, "drafts", name + ".json"), a)
    blog.write_json(blog.STATE, st)
    return a["id"]


def tell_text(a: dict, url: str) -> str:
    return "\n".join([f"Weekly testnet post ready as a draft: {a['title']['en']}"] + ["• " + x for x in a.get("numbers") or []] + [
        "", f"Read it: {url}", "", "Publish it (blog + one post on Telegram and X):", UP.format(f"blog publish {a['id']}"),
        "", "Not good? Leave it: it never goes up by itself. Write it anew: " + UP.format("week draft"),
        "", f"Its address once published: {blog.SITE}/blog/?p={a['id']}"])


def build(now: float, last: bool = False) -> tuple[dict, str]:
    t0, t1, wid = ir.week_of(now, last)
    return week_facts(gather(t0, t1), t0, t1), wid


def draft_and_tell(now: float, last: bool = False) -> tuple[str, bool, str]:
    f, wid = build(now, last)
    did = write_draft(f, wid, now)
    st = blog.state()
    url = blog.draft_url(st, did)
    a = blog.read_json(os.path.join(blog.PUBLIC, "drafts", st["drafts"][did] + ".json"), {})
    import tickerwatch
    ok, err = tickerwatch.tell(tell_text(a, url)[:4000])
    st = blog.state()
    st.setdefault("week_drafted", {})[wid] = {"at": round(now), "ok": True, "id": did,
                                             "told": "sent to you on Telegram" if ok else f"not sent ({err})"}
    blog.write_json(blog.STATE, st)
    return did, ok, url


def step(now: float | None = None) -> str | None:
    """One round of the blog loop: the week's draft, once, from Sunday 18:00 German time."""
    if not ON:
        return None
    now = now or time.time()
    d = blog.local(now)
    if d.weekday() != ir.WEEKDAY or d.hour < ir.HOUR:
        return None
    wid = ir.week_of(now)[2]
    st = blog.state()
    s_ = (st.get("week_drafted") or {}).get(wid) or {}
    if s_.get("ok") or now - (st.get("week_failed_at") or 0) < RETRY:
        return None
    try:
        did, ok, url = draft_and_tell(now)
    except Exception as e:  # noqa: BLE001 - tried again in an hour
        log.warning("week draft %s: %s", wid, e)
        st = blog.state()
        st["week_failed_at"] = now
        blog.write_json(blog.STATE, st)
        return None
    log.info("week draft %s written: %s (%s)", did, url, "told" if ok else "not told")
    return did


def status_lines(now: float | None = None) -> list[str]:
    if not ON:
        return ["week:    weekly testnet post off (TESTNET_WEEK=false)"]
    import datetime as dt
    now = now or time.time()
    d = blog.local(now)
    nxt = (d + dt.timedelta(days=(ir.WEEKDAY - d.weekday()) % 7)).replace(hour=ir.HOUR, minute=0, second=0, microsecond=0)
    done = blog.state().get("week_drafted") or {}
    if (done.get(ir.week_of(now)[2]) or {}).get("ok") or nxt.timestamp() < now - 3600:
        nxt += dt.timedelta(days=7)
    out = [f"week:    weekly testnet post as a draft for you {nxt.strftime('%a %d.%m. %H:%M')} (up week shows it now; never published by itself)"]
    if done:
        wid = max(done)
        out.append(f"         last {wid}: {done[wid].get('id')}, {done[wid].get('told')}")
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if any(x not in ("draft", "last") for x in argv):
        print(__doc__)
        return 2
    now = time.time()
    last = "last" in argv
    if "draft" in argv:
        print("writing the week's draft (with NEWS_AI_KEY a model translates it, up to a few minutes); nothing is published", flush=True)
        did, ok, url = draft_and_tell(now, last)
        print(f"draft {did}: {url}")
        print("told on your Telegram" if ok else "NOT told on Telegram (up owner?)")
        print("publish: " + UP.format(f"blog publish {did}"))
        return 0
    f, wid = build(now, last)
    e = text(f)
    print(f"--- {pid(wid)} (address once published: {blog.SITE}/blog/?p={pid(wid)})")
    print(f"# {e['title']}\n{e['dek']}\n")
    print("Why it matters:\n" + "\n".join("- " + w for w in e["why"]) + "\n")
    print(e["body"])
    print("---\nnothing written, nothing sent; up week draft  writes the draft and tells you on Telegram")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
