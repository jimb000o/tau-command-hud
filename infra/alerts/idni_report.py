"""The weekly report for IDNI: what our community node saw on Tau Testnet Alpha in one week, as ONE GitHub issue the
owner files on IDNI/tau-testnet by hand (instead of many single issues).

Every number comes from our own public data, counted here, never written by a language model:
  /uptime         our node answering, in sync, outages, chain restarts, reorgs, pauses without a block
  /health-score   the health score per hour (our node's view of the testnet)
  /stats          the blocks of the current chain (count, transactions)
  /cruise/log     the cruise ships' visits (accepted, refused with the node's answer, our node's timeouts, answer times)
  /public/devpulse.json  which tau-testnet commit our node runs, how far main is ahead, do our patches apply
  blog posts      articles published that week (our own write-ups, mistakes included)

Wording: our own trouble (our node not answering, behind, our relay down, our timeouts) stands under "On our side",
in our words; what the testnet did right is credited; nothing blames IDNI or the testnet; no hype; no names.

Once a week (REPORT_WEEKDAY/REPORT_HOUR, Sunday 18:00 German time) the blog loop writes the week's report as an
unlisted page, node.tauhud.com/idni-report/<week>-<code>.html: the text, a button that opens the pre-filled issue on
GitHub (title and text in the link, editable before it is sent) and a copy button; and tells the owner's private
Telegram chat (tickerwatch.tell, `up owner` sets it), never the channel. Nothing is ever filed by itself.

  python idni_report.py              this week so far: the text, the page and the pre-filled link (sends nothing)
  python idni_report.py last         the same for last week (Monday to Monday)
  python idni_report.py send [last]  the same, and the page link to the owner's Telegram now
"""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import os
import re
import secrets
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402  (relay access, the logbook's facts, local time, json files)
import node_logs  # noqa: E402  (our node's own log: sync and peering failures, kept by the nodelog service)

log = logging.getLogger("idni-report")

ON = os.environ.get("IDNI_REPORT", "true").lower() in ("1", "true", "yes")
WEEKDAY = int(os.environ.get("IDNI_REPORT_WEEKDAY", "6"))   # 0 Monday … 6 Sunday, German time
HOUR = int(os.environ.get("IDNI_REPORT_HOUR", "18"))
STATE = os.path.join(os.path.dirname(blog.STATE), "idni-report.json")
OUT = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "idni-report")
REPO = "IDNI/tau-testnet"
NEW_ISSUE = f"https://github.com/{REPO}/issues/new"
URL_MAX = 8000          # GitHub refuses longer new-issue links; the report gets shorter until it fits
RETRY = 3600
UP = 'ssh root@node.tauhud.com "sh /opt/tau-command-hud/infra/up.sh {}"'
NOT_AFFILIATED = "Tau HUD is a community project, not affiliated with IDNI."
PATCHES = "https://github.com/jimb000o/tau-command-hud/tree/main/infra/node/patches"
DAY = 86400


# ---------- the week ----------
def week_of(now: float, last: bool = False) -> tuple[float, float, str]:
    """(start, end, id): Monday 00:00 German time of this week up to now, or last week's Monday to Monday."""
    d = blog.local(now)
    monday = (d - dt.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if last:
        start, end = monday - dt.timedelta(days=7), monday.timestamp()
    else:
        start, end = monday, now
    y, w, _ = start.isocalendar()
    return start.timestamp(), end, f"{y}-w{w:02d}"


def dshort(t: float) -> str:
    d = blog.local(t)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def utc(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%a %d %b %H:%M UTC")


def mins(sec: float) -> str:
    m = round(sec / 60)
    return f"{m // 60} h {m % 60} min" if m >= 90 else f"{m} min"


def n(x: int) -> str:
    return f"{x:,}"


# ---------- reading ----------
def gather(t0: float, t1: float) -> dict:
    """Everything the report is counted from; a source that does not answer is left out (and the report says so)."""
    raw: dict = {"missing": []}
    for key, path in (("uptime", "/uptime"), ("health", "/health-score"), ("stats", "/stats"), ("incidents", "/cruise/incidents")):
        try:
            raw[key] = blog.get(path)
        except Exception as e:  # noqa: BLE001
            raw["missing"].append(path)
            log.warning("%s not read: %s", path, e)
    raw["visits"] = {}
    try:
        for vid in blog.get("/cruise/log?n=1").get("visits") or []:
            if in_week(vid, t0, t1):
                raw["visits"][vid] = blog.get(f"/cruise/log?visit={vid}&n=2000").get("entries") or []
    except Exception as e:  # noqa: BLE001
        raw["missing"].append("/cruise/log")
        log.warning("/cruise/log not read: %s", e)
    raw["pulse"] = blog.read_json(os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "devpulse.json"), None)
    posts = list(blog.posts().get("posts") or [])
    try:
        with blog.urllib.request.urlopen(blog.SITE + "/assets/blog/posts.json", timeout=20) as r:
            posts += json.load(r).get("posts") or []
    except Exception:  # noqa: BLE001 - the server's list is enough
        pass
    raw["posts"] = posts
    raw["node_log"] = node_logs.from_state(t0, t1)
    return raw


def in_week(vid: str, t0: float, t1: float) -> bool:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", vid or "")
    if not m:
        return False
    day0 = blog.local(t0).date().isoformat()
    day1 = blog.local(t1 - 1).date().isoformat()
    return day0 <= m.group(1) <= day1


# ---------- counting ----------
def overlap(a: float, b: float | None, t0: float, t1: float) -> float:
    b = t1 if b is None else b
    return max(0.0, min(b, t1) - max(a, t0))


def facts(raw: dict, t0: float, t1: float) -> dict:
    f: dict = {"from": t0, "to": t1, "missing": list(raw.get("missing") or [])}
    up = raw.get("uptime") or {}
    hours = [h for h in up.get("hours") or [] if t0 <= h[0] < t1]
    samples = sum(h[1] for h in hours)
    if samples:
        f["checks"] = samples
        f["node answering"] = sum(h[2] for h in hours) / samples
        f["in sync"] = sum(h[3] for h in hours) / samples
    inc = [i for i in up.get("incidents") or [] if overlap(i.get("start") or 0, i.get("end"), t0, t1) > 0]
    for kind in ("node", "sync", "relay"):
        mine = [i for i in inc if i.get("kind") == kind]
        if mine:
            f["down " + kind] = {"count": len(mine), "seconds": sum(overlap(i["start"], i.get("end"), t0, t1) for i in mine),
                       "longest": max(overlap(i["start"], i.get("end"), t0, t1) for i in mine),
                       "max_lag": max((i.get("max_lag") or 0) for i in mine)}
    f["restarts"] = [r for r in up.get("restarts") or [] if t0 <= (r.get("detected_at") or 0) < t1]
    f["reorgs"] = [r for r in up.get("reorgs") or [] if t0 <= (r.get("at") or 0) < t1]
    f["stalls"] = [s for s in up.get("stalls") or [] if t0 <= (s.get("end") or 0) and (s.get("start") or 0) < t1]
    f["stall_seconds"] = up.get("stall_seconds") or 600
    he = raw.get("health") or {}
    sc = [(h[0], h[1], h[2]) for h in he.get("hours") or [] if t0 <= h[0] < t1]
    if sc:
        f["score"] = {"average": round(sum(x[1] for x in sc) / len(sc)), "lowest": min(x[2] for x in sc),
                      "lowest at": min(sc, key=lambda x: x[2])[0], "hours": len(sc)}
    if he.get("expected_block_seconds"):
        f["block seconds"] = he["expected_block_seconds"]
    for k in he.get("known_issues") or []:
        if k.get("id") == "IDNI #81" and k.get("count"):
            f["ghosts"] = {"count": k["count"], "url": k.get("url")}
    st = raw.get("stats") or {}
    rows = [b for b in st.get("blocks") or [] if len(b) > 2 and b[1] and t0 <= b[1] < t1]
    if rows:
        f["blocks"] = {"count": len(rows), "first": rows[0][0], "last": rows[-1][0], "txs": sum(b[2] for b in rows)}
    drop = [d for d in st.get("dropped") or [] if t0 <= (d.get("left") or 0) < t1]
    if drop:
        f["dropped"] = len(drop)
    f["visits"] = []
    for vid, entries in sorted((raw.get("visits") or {}).items()):
        if not entries:
            continue
        v = blog.facts_of(entries, (raw.get("incidents") or {}).get("incidents") or [])
        old = v.get("refusals logged without any answer from the node (a timeout, counted as refusal by the old rule)") or 0
        f["visits"].append({
            "id": vid, "ship": v.get("ship") or vid, "day": dshort(min(e.get("t") or t1 for e in entries)),
            "landed": v.get("landed") is not False, "why not": v.get("why not landed"),
            "accepted": v.get("accepted in all") or 0, "refused": max(0, (v.get("refused in all") or 0) - old),
            "timeouts": old + (v.get("sends our node did not answer in time (not refusals)") or 0),
            "reached later": v.get("of those, reached the chain after all") or 0,
            "answers": v.get("refusal answers") or {}, "time": v.get("our node's answer time to a send, seconds"),
            "left": v.get("left early"), "incidents": len(v.get("incidents") or []),
            "heights": v.get("block heights"), "over": any(e.get("kind") == "visit over" for e in entries)})
    p = raw.get("pulse") or {}
    y = p.get("sync") or {}
    if y:
        t, pa = y.get("testnet") or {}, y.get("patches") or {}
        f["node"] = {"pin": (t.get("pin") or "")[:7], "head": (t.get("head") or "")[:7], "ahead": t.get("ahead"),
                     "patches": len(pa.get("results") or []) or None,
                     "patches ok": pa.get("ok") if pa else None, "patches on": (pa.get("sha") or "")[:7]}
    f["log"] = raw.get("node_log")
    f["posts"] = []
    seen = set()
    for a in raw.get("posts") or []:
        on = a.get("on") or ""
        if a.get("id") in seen or not on:
            continue
        try:
            at = dt.datetime.strptime(on[:10], "%Y-%m-%d").replace(tzinfo=blog.TZ or dt.timezone.utc).timestamp()
        except ValueError:
            continue
        if t0 - DAY < at < t1:
            seen.add(a.get("id"))
            f["posts"].append({"title": (a.get("title") or {}).get("en") or a.get("id"), "url": f"{blog.SITE}/blog/?p={a['id']}"})
    return f


# ---------- writing ----------
def title(f: dict) -> str:
    a, b = blog.local(f["from"]), blog.local(f["to"] - 1)
    span = f"{a.day}–{b.day} {b.strftime('%b %Y')}" if a.month == b.month else f"{a.day} {a.strftime('%b')} – {b.day} {b.strftime('%b %Y')}"
    return f"Weekly report from a community node, {span}"


def body(f: dict, short: int = 0) -> str:
    """The issue text in Markdown. `short` 1..3 leaves out detail until the pre-filled link fits."""
    L = []
    a, b = blog.local(f["from"]), blog.local(f["to"])
    L += [f"{NOT_AFFILIATED} We run one read-only node on Tau Testnet Alpha and send paced, openly simulated test "
          "traffic from our apps. This is what our node saw from "
          f"{dshort(f['from'])} {a.strftime('%H:%M')} to {dshort(f['to'])} {b.strftime('%H:%M')} (German time), "
          "counted from our public logs. Nothing here needs an answer; it is one data point a week, and corrections are welcome.", ""]

    L.append("### The chain, as our node saw it")
    bl = f.get("blocks")
    if bl:
        L.append(f"- {n(bl['count'])} blocks (#{bl['first']} to #{bl['last']}) with {n(bl['txs'])} transactions"
                 + (f"; typically {f['block seconds']} s between blocks" if f.get("block seconds") else ""))
    st = f.get("stalls") or []
    if st:
        L.append(f"- {len(st)} pause{'s' if len(st) != 1 else ''} of more than {round(f['stall_seconds'] / 60)} minutes without a block"
                 + ("" if short >= 2 else ": " + ", ".join(f"after #{s['after']} ({utc(s['start'])}, {mins(s['end'] - s['start'])})" for s in st[:6])
                    + (" …" if len(st) > 6 else "")))
    else:
        L.append(f"- No pause of more than {round(f['stall_seconds'] / 60)} minutes without a block")
    rs = f.get("restarts") or []
    L.append(f"- Chain restarts seen (a new block 1): {len(rs)}" + (" (" + ", ".join(utc(r['detected_at']) + (f", old tip #{r['old_tip']}" if r.get("old_tip") else "")
                                                                                   for r in rs) + ")" if rs else ""))
    L.append(f"- Reorgs seen: {len(f.get('reorgs') or [])}")
    if f.get("dropped"):
        L.append(f"- Transactions that left our node's mempool and were in no block 30 s later: {f['dropped']}")
    if f.get("ghosts"):
        L.append(f"- Transactions already in a block but still listed as waiting at the time of this report: {f['ghosts']['count']} (#81)")
    if f.get("score"):
        s = f["score"]
        L.append(f"- Our health score (our node's view of the testnet, 0 to 100): average {s['average']}, lowest {s['lowest']} ({utc(s['lowest at'])} hour)")
    L.append("")

    vs = f.get("visits") or []
    acc = sum(v["accepted"] for v in vs)
    ref = sum(v["refused"] for v in vs)
    L.append("### What held up")
    if bl and not st and not rs:
        L.append("- The chain kept producing blocks all week without a long pause or a restart.")
    elif bl:
        L.append(f"- The chain produced {n(bl['count'])} blocks this week" + (" and came back after each pause." if st else "."))
    if acc:
        L.append(f"- The node accepted {n(acc)} of our test transactions" + (f" and refused {ref}." if ref else " and refused none."))
    if not f.get("reorgs"):
        L.append("- No reorg seen.")
    L.append("")

    L.append("### On our side")
    ours = []
    if f.get("down node"):
        x = f["down node"]
        ours.append(f"- Our node did not answer our relay {x['count']} time{'s' if x['count'] != 1 else ''}, {mins(x['seconds'])} in all (longest {mins(x['longest'])}).")
    if f.get("down sync"):
        x = f["down sync"]
        ours.append(f"- Our node was more than 2 blocks behind the network {x['count']} time{'s' if x['count'] != 1 else ''}, {mins(x['seconds'])} in all"
                    + (f", at most {x['max_lag']} blocks as our relay counted it" if x["max_lag"] else "") + ".")
    if f.get("down relay"):
        x = f["down relay"]
        ours.append(f"- Our relay itself was down {x['count']} time{'s' if x['count'] != 1 else ''}, {mins(x['seconds'])} in all.")
    to = sum(v["timeouts"] for v in vs)
    if to:
        later = sum(v["reached later"] for v in vs)
        ours.append(f"- {to} of our ships' sends got no answer from our own node within 20 s. These are timeouts on our side, not refusals"
                    + (f"; {later} of them reached the chain all the same." if later else "."))
    if f.get("in sync") is not None:
        ours.append(f"- Over the week our node answered {f['node answering'] * 100:.1f}% and was in sync {f['in sync'] * 100:.1f}% of {n(f['checks'])} checks (one a minute).")
    L += ours or ["- Nothing to report on our side this week."]
    L.append("")
    L += node_logs.section(f.get("log"), short)   # IDNI asked for sync and peering failures with their logs (Q&A, Nov 2026)

    if vs:
        L.append("### Test traffic from our cruise ships")
        L.append("Simulated passengers, every stop a real transaction, at most 12 a minute, slower when the node is slow.")
        for v in vs if short < 3 else vs[:4]:
            if not v["landed"]:
                L.append(f"- {v['day']}, {v['ship']}: did not land" + (f" ({v['why not']})" if v["why not"] else ""))
                continue
            t = v.get("time")
            line = f"- {v['day']}, {v['ship']}: {n(v['accepted'])} accepted, {v['refused']} refused, {v['timeouts']} timeouts on our side"
            if t:
                line += f"; our node's answer time median {t['median']} s, slowest {t['slowest']} s"
            if isinstance(v.get("left"), dict) and v["left"].get("minutes in port") is not None:
                line += f"; the ship left after {v['left']['minutes in port']} of 90 minutes"
            if not v["over"]:
                line += " (still under way)"
            L.append(line + f" ([logbook]({blog.NODE}/cruise/log?visit={v['id']}))")
            if short < 1:
                for err, k in list(v["answers"].items())[:3]:
                    L.append(f"  - refused {k}x: `{err[:110]}`")
        L.append("")

    nd = f.get("node")
    if nd:
        L.append("### Our node")
        line = f"- tau-testnet {nd['pin']}" + (f" plus {nd['patches']} small patches ([what they do]({PATCHES}))" if nd.get("patches") else "")
        if nd.get("ahead"):
            line += f"; main is {nd['ahead']} commits ahead ({nd['head']})"
            if nd.get("patches ok") is True:
                line += ", and all our patches apply to it"
            elif nd.get("patches ok") is False:
                line += ", and one of our patches needs rework before we can move to it"
        elif nd.get("ahead") == 0:
            line += ", the newest main"
        L += [line, ""]

    if f.get("posts"):
        L.append("### Written up this week")
        L += [f"- [{p['title']}]({p['url']})" for p in f["posts"][:5]]
        L.append("")

    L.append(f"Sources: {blog.NODE}/uptime · {blog.NODE}/health-score · {blog.NODE}/stats · {blog.NODE}/cruise/log · {blog.SITE}/status/"
             + (f" (not read this time: {', '.join(f['missing'])})" if f.get("missing") else ""))
    L.append("")
    L.append(f"_{NOT_AFFILIATED}_")
    return "\n".join(L)


def issue_url(t: str, b: str) -> str:
    return NEW_ISSUE + "?" + urllib.parse.urlencode({"title": t, "body": b}, quote_via=urllib.parse.quote)


def fitted(f: dict) -> tuple[str, str, str]:
    """(title, body, link) with the shortest leaving-out that still fits the link."""
    t = title(f)
    for short in range(4):
        b = body(f, short)
        u = issue_url(t, b)
        if len(u) <= URL_MAX:
            return t, b, u
    return t, b, issue_url(t, b[: 2500] + "\n\n(cut to fit the link; the whole text is on our page)")


# ---------- the page ----------
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Weekly report for IDNI</title>
<style>body{{margin:0;background:#050807;color:#d8e6df;font:15px/1.5 system-ui,sans-serif}}main{{max-width:46rem;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:20px;margin:0 0 4px}}p{{margin:6px 0 14px;color:#9fb3aa}}.b{{display:inline-block;margin:0 8px 10px 0;padding:12px 16px;min-height:44px;box-sizing:border-box;
border:1px solid #3cff8f;border-radius:6px;background:#0b1a12;color:#3cff8f;font:inherit;text-decoration:none;cursor:pointer}}
pre{{white-space:pre-wrap;word-break:break-word;background:#0a0f0d;border:1px solid #1d2a24;border-radius:6px;padding:14px;font:13px/1.5 ui-monospace,monospace}}</style></head>
<body><main><h1>{title}</h1><p>Not filed yet. The button opens a new issue on {repo} with this text filled in; read it, change what you like, then press Create.</p>
<a class="b" href="{url}" target="_blank" rel="noopener">Open the pre-filled issue on GitHub</a><button class="b" id="c">Copy the text</button>
<pre id="t">{body}</pre></main><script>document.getElementById("c").onclick=function(){{navigator.clipboard.writeText(document.getElementById("t").textContent).then(function(){{document.getElementById("c").textContent="Copied"}})}}</script></body></html>
"""


def state() -> dict:
    st = blog.read_json(STATE, {})
    st.setdefault("codes", {})
    st.setdefault("sent", {})
    return st


def write(f: dict, wid: str, st: dict) -> dict:
    t, b, u = fitted(f)
    code = st["codes"].setdefault(wid, secrets.token_hex(4))
    os.makedirs(OUT, exist_ok=True)
    name = f"{wid}-{code}.html"
    tmp = os.path.join(OUT, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(PAGE.format(title=html.escape(t), repo=REPO, url=html.escape(u), body=html.escape(b)))
    os.replace(tmp, os.path.join(OUT, name))
    blog.write_json(STATE, st)
    return {"title": t, "body": b, "url": u, "page": f"{blog.NODE}/idni-report/{name}"}


def summary(f: dict) -> list[str]:
    out = []
    if f.get("blocks"):
        out.append(f"{n(f['blocks']['count'])} blocks, {n(f['blocks']['txs'])} transactions, {len(f.get('stalls') or [])} long pauses, {len(f.get('restarts') or [])} restarts")
    vs = f.get("visits") or []
    if vs:
        out.append(f"{len(vs)} ship visits: {n(sum(v['accepted'] for v in vs))} accepted, {sum(v['refused'] for v in vs)} refused, {sum(v['timeouts'] for v in vs)} timeouts on our side")
    if f.get("in sync") is not None:
        out.append(f"our node in sync {f['in sync'] * 100:.1f}% of the week")
    if f.get("log") is not None:
        lg = f["log"]
        out.append(f"node log: {lg['lines']} sync or peering warnings in {len(lg['groups'])} kinds" if lg["lines"] else "node log: no sync or peering warning")
    return out


def tell_text(r: dict, f: dict, wid: str) -> str:
    return "\n".join([f"Weekly report for IDNI ready ({wid}): {r['title']}"] + ["• " + s for s in summary(f)] + [
        "", "Read it and file it with one click (opens a pre-filled issue on IDNI/tau-testnet, you can edit before sending):",
        r["page"], "", "Again any time: " + UP.format("report")])


def build(now: float, last: bool = False) -> tuple[dict, dict, str]:
    t0, t1, wid = week_of(now, last)
    f = facts(gather(t0, t1), t0, t1)
    return write(f, wid, state()), f, wid


def step(now: float | None = None) -> str | None:
    """One round of the blog loop: the week's report to the owner, once, from REPORT_WEEKDAY REPORT_HOUR on."""
    if not ON:
        return None
    now = now or time.time()
    d = blog.local(now)
    if d.weekday() != WEEKDAY or d.hour < HOUR:
        return None
    wid = week_of(now)[2]
    st = state()
    s = st["sent"].get(wid) or {}
    if s.get("ok") or now - (s.get("at") or 0) < RETRY:
        return None
    r, f, wid = build(now)
    import tickerwatch
    ok, err = tickerwatch.tell(tell_text(r, f, wid)[:4000])
    st = state()
    st["sent"][wid] = {"at": round(now), "ok": ok, "told": "sent to you on Telegram" if ok else f"not sent ({err})", "page": r["page"]}
    blog.write_json(STATE, st)
    log.info("idni report %s: %s", wid, st["sent"][wid]["told"])
    return wid


def status_lines(now: float | None = None) -> list[str]:
    """For the `up` block: when the next report comes and what became of the last."""
    if not ON:
        return ["report:  weekly IDNI report off (IDNI_REPORT=false)"]
    now = now or time.time()
    d = blog.local(now)
    nxt = (d + dt.timedelta(days=(WEEKDAY - d.weekday()) % 7)).replace(hour=HOUR, minute=0, second=0, microsecond=0)
    st = state()
    if st["sent"].get(week_of(now)[2], {}).get("ok") or nxt.timestamp() < now - 3600:
        nxt += dt.timedelta(days=7)
    out = [f"report:  weekly IDNI report to your Telegram {nxt.strftime('%a %d.%m. %H:%M')} (up report shows it now)"]
    if st["sent"]:
        wid = max(st["sent"])
        out.append(f"         last {wid}: {st['sent'][wid].get('told')} {st['sent'][wid].get('page') or ''}".rstrip())
    return out


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    args = [a for a in argv if a in ("send", "last")]
    if argv and len(args) != len(argv):
        print(__doc__)
        return 2
    now = time.time()
    r, f, wid = build(now, "last" in args)
    print(f"--- title\n{r['title']}\n--- text\n{r['body']}\n---")
    print(f"page (text, copy button and the pre-filled issue): {r['page']}")
    print(f"pre-filled issue on {REPO} ({len(r['url'])} characters, opens GitHub's form, nothing is filed until you press Create):")
    print(r["url"])
    if "send" in args:
        import tickerwatch
        ok, err = tickerwatch.tell(tell_text(r, f, wid)[:4000])
        print("report:  sent to your Telegram" if ok else f"report:  NOT sent: {err}")
        if ok:
            st = state()
            st["sent"][wid] = {"at": round(now), "ok": True, "told": "sent to you on Telegram (by hand)", "page": r["page"]}
            blog.write_json(STATE, st)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
