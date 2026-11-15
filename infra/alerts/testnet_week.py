"""The Tau Net testnet this week, as a blog post (Kilian, 15 November 2026: the weekly report for IDNI becomes a weekly
post on tauhud.com/blog/ instead of an issue on IDNI/tau-testnet).

Every Sunday from 18:00 German time (IDNI_REPORT_WEEKDAY / IDNI_REPORT_HOUR) the blog loop writes the week as an
unlisted DRAFT and tells the owner's private Telegram chat (tickerwatch.tell, never the channel): where to read it and
the one line that publishes it. It never goes on the blog by itself (the draft carries "by_hand", so blog.auto_publish
leaves it), and nothing is filed on GitHub.

Every number is counted here from our own public data (idni_report.gather / facts: /uptime, /health-score, /stats,
/cruise/log, our node's log; plus /history for the blocks of every chain of the week and /api/v1/sources for where the
transactions came from), with what they come to worked out here (shares, the week before, blocks against the
testnet's own pace, the longest stretch without a restart). With NEWS_AI_KEY a language model writes the post from
those facts in three languages, meaning first (Kilian, 15 November: "extract the meaning of the numbers, not just
report them"); every number it writes is checked against the facts and a stranger is marked in the draft. Without a
key, or when that fails, the script's own text goes out (its zh/ja translated, a translation with a number the English
does not hold dropped). Three charts (blocks per day, where transactions came from, the week before) and a second read
against our rules (editor.py) go with every draft; the editor's notes come with the Telegram message.

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

# where the transactions came from (relay/txsources.py), grouped as tauhud.com/meta/ shows them: users of our apps;
# IDNI's genesis accounts (IDNI tests with them, not users); other wallets; our own server's automated senders (never users)
APPS = (("agorzilla", "Agorzilla", "https://agorzilla.com/"), ("tauhud", "Tau HUD", "/"), ("rabbit", "White Rabbit Key", "/rabbit/"),
        ("nomemo", "No Memo", "/nomemo/"))
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
        f["sources"] = {"apps": [(label, by[g], href) for g, label, href in APPS if by.get(g)],
                        "idni": by.get("idni") or 0, "other": by.get("other") or 0,
                        "ours": [(label, by[g]) for g, label in OURS if by.get(g)], "days": (d0, d1)}
    f["before"] = week_before(raw, t0)
    f["per day"] = per_day(raw, t0, t1)
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


def sums_of(h: dict, a: float, b: float) -> dict | None:
    fields = h.get("fields") or []
    if "blocks" not in fields or "txs" not in fields:
        return None
    ib, it = fields.index("blocks") + 2, fields.index("txs") + 2
    rows = [r for r in h.get("hours") or [] if len(r) > max(ib, it) and a <= (r[0] or 0) < b]
    if not rows:
        return None
    return {"blocks": sum(r[ib] or 0 for r in rows), "txs": sum(r[it] or 0 for r in rows), "hours": len(rows)}


def apps_of(raw: dict, a: float, b: float) -> int | None:
    days = (raw.get("sources") or {}).get("days") or {}
    d0, d1 = blog.local(a).date().isoformat(), blog.local(b - 1).date().isoformat()
    got = [g for d, g in days.items() if d0 <= d <= d1 and isinstance(g, dict)]
    if not got:
        return None
    return sum((g.get(k) or [0])[0] or 0 for g in got for k, _, _ in APPS)


def week_before(raw: dict, t0: float) -> dict | None:
    """The same headline numbers for the 7 days before (from /history and /api/v1/sources), for the comparison."""
    h = raw.get("history") or {}
    p0 = t0 - 7 * 86400
    w = sums_of(h, p0, t0)
    if not w:
        return None
    starts = [c.get("start") for c in h.get("chains") or [] if c.get("start") and p0 <= c["start"] < t0 and (c.get("n") or 0) > 1]
    w["restarts"] = len(starts)
    w["app txs"] = apps_of(raw, p0, t0)
    return w


def per_day(raw: dict, t0: float, t1: float) -> list[list]:
    """[[day label, blocks, restarts that day]] Monday to the post's day, German time."""
    h = raw.get("history") or {}
    fields = h.get("fields") or []
    if "blocks" not in fields:
        return []
    ib = fields.index("blocks") + 2
    out: dict = {}
    t = t0
    while t < t1:
        d = blog.local(t)
        out.setdefault(d.date().isoformat(), [d.strftime("%a"), 0, 0])
        t += 86400
    for r in h.get("hours") or []:
        if len(r) > ib and t0 <= (r[0] or 0) < t1:
            k = blog.local(r[0]).date().isoformat()
            if k in out:
                out[k][1] += r[ib] or 0
    for r in (raw.get("uptime") or {}).get("restarts") or []:
        at = r.get("old_tip_ts") or r.get("detected_at") or 0
        if t0 <= at < t1:
            k = blog.local(at).date().isoformat()
            if k in out:
                out[k][2] += 1
    return [out[k] for k in sorted(out)]


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
    people = sum(k for _, k, _ in src.get("apps") or [])
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
        why.append("No chain restart this week: balances and rules set on the testnet stayed.")
    if src.get("apps"):
        why.append(f"Users of our apps sent {n(people)} transactions; IDNI's own testing and our automated test traffic are counted apart.")
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

    if src:
        L += source_lines(src)
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
    if src.get("apps"):
        nums.append(f"{n(people)} transactions by users of our apps, {n(ours)} from our own test traffic")
    if f.get("in sync") is not None:
        nums.append(f"our node in sync {f['in sync'] * 100:.1f}% of the week")

    stats = []
    if cc:
        stats.append([n(cc[0]), "blocks this week"])
    stats.append([str(len(rs)), "chain restarts, cause unknown" if rs else "chain restarts"])
    if src.get("apps"):
        stats.append([n(people), "transactions by users of our apps"])
    if f.get("in sync") is not None:
        stats.append([f"{f['in sync'] * 100:.1f}%", "our node in sync"])

    card = [blog.card_title(title), "What one community node saw, counted from its logs", "## Why it matters"]
    card += ["- " + c for c in (
        f"{s(len(rs), 'chain restart')}, cause unknown" if rs else "No chain restart this week",
        f"{n(people)} transactions by users of our apps" if src.get("apps") else "Counted the same way every week",
        "Our own test traffic counted apart")]
    card.append("Tau HUD blog · community project, not affiliated with IDNI")
    return {"title": title, "dek": dek, "why": why, "body": "\n".join(L).rstrip(), "card": card, "stats": stats, "numbers": nums,
            "x": f"{', '.join(head)}. One community node's view of Tau Testnet Alpha, counted from its logs."}


def source_lines(src: dict) -> list[str]:
    """Where the transactions came from, as tauhud.com/meta/ groups them, our apps linked."""
    L = ["## Where the transactions came from", "Counted per day (UTC), Monday to Sunday. Wallets, not people: one person can hold many.", ""]
    for label, k, href in src.get("apps") or []:
        L.append(f"- Users of [{label}]({href}): {n(k)}" if label != "No Memo" else f"- Players in [No Memo]({href}): {n(k)}")
    if src.get("other"):
        L.append(f"- Other wallets, scripts and tools: {n(src['other'])}")
    if src.get("idni"):
        L.append(f"- IDNI's genesis accounts, which IDNI uses for testing (not counted as users): {n(src['idni'])}")
    L.append("")
    return L


# ---------- what the numbers mean, for the writer ----------
def pct(a: float, b: float) -> str:
    return f"{round(100 * a / b)}%" if b else "n/a"


def change(now_, before) -> str | None:
    if before in (None, 0) or now_ is None:
        return None
    d = now_ - before
    return f"{'+' if d >= 0 else ''}{n(d)} ({'+' if d >= 0 else ''}{round(100 * d / before)}%)"


def model_facts(f: dict) -> dict:
    """The week as plain-named facts plus what they come to (shares, changes, gaps), every number counted here, so the
    writer explains meaning without inventing any."""
    rs, vs = f.get("restarts") or [], f.get("visits") or []
    cc = chain_counts(f)
    src = f.get("sources") or {}
    apps = sum(k for _, k, _ in src.get("apps") or [])
    ours = sum(k for _, k in src.get("ours") or [])
    allsrc = apps + (src.get("idni") or 0) + (src.get("other") or 0) + ours
    a, b = blog.local(f["from"]), blog.local(f["to"])
    hours = round((f["to"] - f["from"]) / 3600)
    x: dict = {"week": f"Monday {a.day} {a.strftime('%B')} to Sunday {b.day} {b.strftime('%B %Y')}, {b.strftime('%H:%M')} German time",
               "hours counted": hours}
    if cc:
        x["blocks"], x["transactions"], x["chains the week ran on"] = cc
    if f.get("block seconds"):
        x["seconds between blocks the testnet aims for"] = f["block seconds"]
    x["pauses of more than 10 minutes without a block"] = len(f.get("stalls") or [])
    x["reorgs"] = len(f.get("reorgs") or [])
    x["chain restarts"] = [{"when": ir.utc(restart_at(r)), "the old chain ended at block": r.get("old_tip"),
                            "during or within an hour after our cruise ship": r.get("near")} for r in rs]
    x["what a restart means for someone using the testnet"] = (
        "a new block 1: balances, personal wallet rules and the history of the old chain are gone, every wallet starts again "
        "at zero, and the faucet pays 100,000 test AGRS again to a wallet with zero balance")
    x["cause of the restarts"] = "unknown to us; IDNI runs the testnet and has not said" if rs else None
    x["our cruise ships paused"] = bool(f.get("ships paused"))
    if src:
        x["transactions by users of our apps"] = {label: k for label, k, _ in src.get("apps") or []}
        x["transactions by users of our apps, in all"] = apps
        x["transactions by IDNI's genesis accounts (IDNI tests with them; not users)"] = src.get("idni") or 0
        x["transactions by other wallets, scripts and tools"] = src.get("other") or 0
        x["transactions our own server sent (simulated or automated; never users)"] = {label: k for label, k in src.get("ours") or []}
    if f.get("in sync") is not None:
        x["our node in sync, share of the week"] = f"{f['in sync'] * 100:.1f}%"
    for k, lab in (("down node", "times our node did not answer"), ("down sync", "times our node fell more than 2 blocks behind"),
                   ("down relay", "times our relay was down")):
        if f.get(k):
            x[lab] = {"count": f[k]["count"], "minutes in all": round(f[k]["seconds"] / 60)}
    if vs:
        x["cruise ship visits"] = [{"day": v["day"], "ship": v["ship"], "accepted": v["accepted"], "refused": v["refused"],
                                    "sends our own node did not answer in time": v["timeouts"]} for v in vs]
    if f.get("log") is not None:
        x["warnings about syncing or peers in our node's log"] = f["log"]["lines"]
    if f.get("per day"):
        x["blocks per day"] = {d: k for d, k, _ in f["per day"]}
    m: dict = {}
    if cc and f.get("block seconds"):
        possible = round(hours * 3600 / f["block seconds"])
        m["blocks the testnet's own pace would give in these hours"] = possible
        m["share of those blocks that were made"] = pct(cc[0], possible)
    if rs:
        cuts = sorted([f["from"]] + [restart_at(r) for r in rs] + [f["to"]])
        m["longest stretch without a restart, hours"] = round(max(b_ - a_ for a_, b_ in zip(cuts, cuts[1:])) / 3600)
        m["restarts during or within an hour after one of our ship visits"] = sum(1 for r in rs if r.get("near"))
    if allsrc:
        m["share of all counted transactions by users of our apps"] = pct(apps, allsrc)
        m["share by IDNI's genesis accounts"] = pct(src.get("idni") or 0, allsrc)
        m["share sent by our own server"] = pct(ours, allsrc)
    bf = f.get("before") or {}
    if bf:
        m["the week before"] = {"blocks": bf["blocks"], "transactions": bf["txs"], "chain restarts": bf["restarts"],
                                "transactions by users of our apps": bf.get("app txs")}
        ch = {"blocks": change(cc[0] if cc else None, bf["blocks"]), "transactions": change(cc[1] if cc else None, bf["txs"]),
              "transactions by users of our apps": change(apps if src else None, bf.get("app txs")),
              "chain restarts": f"{len(rs)} after {bf['restarts']}"}
        m["change against the week before"] = {k: v for k, v in ch.items() if v}
    x["what the numbers mean"] = m
    return {k: v for k, v in x.items() if v is not None}


WEEK_SYSTEM = """You write the weekly testnet post of Tau HUD (tauhud.com), a community project not affiliated with IDNI, \
the team that builds Tau Net. Tau Net is the network; Tau Testnet Alpha is its test network ("the Tau Net testnet"). \
Tau alone is the language rules are written in; never call the network just "Tau".

You get the week's facts, counted from our community node's public logs, with "what the numbers mean" worked out. Write \
the post people look forward to every Sunday: the week's story and what it means for someone who uses or follows the \
testnet, so a reader feels they would miss something without it. Grounded, never clickbait, never trolling.

Rules:
- Use ONLY these facts. Every number you write must appear in them (shares and changes are in "what the numbers \
mean"). Never invent causes, motives, plans or effects. When the facts do not say why, say plainly that we do not know.
- Lead with meaning, not with a list: open with the one thing that defined the week and what it meant for people on the \
testnet (for example what a restart did to their balances and rules), then back it with the numbers. Compare with the \
week before where the facts have it, and say what changed and what that suggests, without overclaiming.
- Chain restarts: say them as seen, cause unknown. Where one came during or within an hour after one of our cruise \
ships, say so and that we have not ruled out our own test traffic. Never blame, mock or lecture IDNI or the testnet; \
credit what held up.
- Users: only "transactions by users of our apps" are users (Agorzilla, Tau HUD, White Rabbit Key, players in No Memo). \
IDNI's genesis accounts are IDNI's own testing, not users; our cruise ships' passengers are simulated; the island bot and \
our other automated wallets are ours. Never count any of those as users. Wallets, not people.
- "Our node" and "our relay" are Tau HUD's own. Own what went wrong on our side, plainly.
- Plain words for curious readers who are not developers. No code, file or field names. No hype or marketing words, no \
price or coin talk, no exclamation marks, no emoji, no names of people. Every sentence and label must read as natural \
English (no clipped or inverted phrases).
- It is a testnet: say once that its coins have no value and that it can start over.
- Length: 350 to 550 English words in body.
- title: at most 60 characters, a real headline with subject and verb about the week's main story (not "this week" \
alone). dek: one sentence, at most 160 characters, that adds to the title.
- why: three lines, each at most 160 characters: for people using the testnet, for the Tau community and IDNI, and one \
honest limit.
- body: Markdown with "## " headings, short paragraphs with air, few "- " lists. Sections in this order: "What the \
week meant", "The chain", "Who used it", "Compared with the week before" (only with the week before in the facts), \
"On our side", "What we do not know yet". No title in body, no tables. Links only these, each at most once, where you \
name them: [Agorzilla](https://agorzilla.com/), [White Rabbit Key](/rabbit/), [No Memo](/nomemo/), [Tau HUD](/), \
[the stats page](/stats/), [where transactions come from](/meta/), [our node's status](/status/).
- zh: Simplified Chinese, ja: Japanese, the same meaning and numbers; keep Tau Net, Tau Testnet Alpha, Tau HUD, IDNI, \
AGRS, Agorzilla, White Rabbit Key, No Memo and ship names in Latin letters.
- x: one post for X, at most 200 characters, no link, no hashtags: why the week matters, then the main number.
- card: the text on the picture, English only: "line" at most 60 characters in other words than the title; "why" three \
points of at most 52 characters each.

Answer with JSON only:
{"title":{"en":"","zh":"","ja":""},"dek":{"en":"","zh":"","ja":""},"why":[{"en":"","zh":"","ja":""}],\
"body":{"en":"","zh":"","ja":""},"x":"","card":{"line":"","why":["","",""]}}"""


def ask(facts: dict) -> dict:
    """The model's article from the week's facts (three languages), shaped like the ships' articles."""
    import ai_meter
    body = {"model": blog.AI_MODEL, "max_tokens": blog.ROOM_MAX, "system": WEEK_SYSTEM,
            "messages": [{"role": "user", "content": "The week's facts (JSON):\n\n" + json.dumps(facts, ensure_ascii=False, indent=1)}],
            "output_config": {"format": {"type": "json_schema", "schema": blog.ARTICLE_SHAPE}}}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": blog.AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        j = json.load(r)
    ai_meter.meter("blog", blog.AI_MODEL, j.get("usage"))
    if j.get("stop_reason") in ("refusal", "max_tokens"):
        raise RuntimeError(f"no article: {j.get('stop_reason')}")
    out = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise ValueError("no JSON in the answer")
    return json.loads(m.group(0))


LINK_HEADS = {"posts": {"en": "## Written up this week", "zh": "## 本周文章", "ja": "## 今週の記事"},
              "x": {"en": "## On X this week", "zh": "## 本周在 X 上", "ja": "## 今週の X"},
              "end": {"en": "Tau HUD is a community project, not affiliated with IDNI. One node's view; if you saw something else, tell us and we correct it.",
                      "zh": "Tau HUD 是社区项目，与 IDNI 无关。这是一个节点的视角；如果你看到的不同，请告诉我们，我们会更正。",
                      "ja": "Tau HUD はコミュニティのプロジェクトで、IDNI とは関係ありません。一つのノードからの見方です。違うものを見た方は教えてください。訂正します。"}}


def link_tail(f: dict, lang: str) -> str:
    """The week's own articles and X posts as link lists, and the closing line: the same in every language."""
    L = []
    if f.get("posts"):
        L += ["", LINK_HEADS["posts"][lang]] + [f"- [{p['title']}]({p['url']})" for p in f["posts"][:5]]
    if f.get("x posts"):
        L += ["", LINK_HEADS["x"][lang]]
        for p in f["x posts"][:8]:
            who = "@" + str(p.get("handle") or "").lstrip("@") if p.get("handle") else str(p.get("account") or "X")
            head = " ".join(str(p["headline"]).replace("[", "(").replace("]", ")").split())[:140]
            L.append(f"- {who}: [{head}]({p['url']})")
    return "\n".join(L + ["", LINK_HEADS["end"][lang]])


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
def article(f: dict, wid: str, now: float, tr: dict | None = None, out: dict | None = None) -> dict:
    """The draft: the model's article from the counted facts when there is one (`out`), else the script's text (with
    `tr`, its Chinese and Japanese). The hero numbers, the post's numbers and the link lists are the script's either way."""
    en = text(f)
    on = blog.local(f["to"] - 1).strftime("%Y-%m-%d")
    day = blog.local(f["to"] - 1)
    base = {"id": pid(wid), "on": on, "kind": "week", "week": wid, "t0": int(now), "by_hand": True,
            "kicker": f"Testnet week · {day.day} {day.strftime('%B %Y')}", "stats": en["stats"], "numbers": en["numbers"],
            "sources": [f"{blog.NODE}/uptime", f"{blog.NODE}/health-score", f"{blog.NODE}/history",
                        f"{blog.NODE}/api/v1/sources", f"{blog.NODE}/cruise/log"], "written": int(now)}
    if out:
        title, dek, body = blog.three(out.get("title"), 90), blog.three(out.get("dek"), 220), blog.three(out.get("body"), 9000)
        why = [w for w in (blog.three(x, 200) for x in (out.get("why") or [])[:3]) if w]
        if not (title and dek and body and why):
            raise ValueError("the answer misses a title, dek, why or body in one of the languages")
        text_en = " ".join([title["en"], dek["en"], body["en"], *[w["en"] for w in why], str(out.get("x") or "")])
        plain = lambda t: re.sub(r"(?<=\d),(?=\d{3}(?![\d,]))", "", t)   # 9,720 in the text is 9720 in the facts
        facts = model_facts(f)
        known = json.loads(plain(json.dumps(facts, ensure_ascii=False)))
        body = {k: v.rstrip() + "\n" + link_tail(f, k) for k, v in body.items()}
        return {**base, "title": title, "dek": dek, "why": why, "body": body,
                "x": " ".join(str(out.get("x") or "").split())[:240] or en["x"][:240],
                "card": blog.card_of(out.get("card"), title["en"]), "facts_week": facts,
                "check": {"unknown_numbers": blog.unknown_numbers(plain(text_en), known),
                          "hype": sorted({m.group(0) for m in blog.HYPE.finditer(text_en)} | {m.group(0) for m in blog.BLAME.finditer(text_en)})},
                "model": blog.AI_MODEL}
    tr = tr or {}
    pick = lambda k: {"en": en[k], **{lang: tr[lang][k] for lang in tr}}
    why = [{"en": w, **{lang: tr[lang]["why"][i] for lang in tr}} for i, w in enumerate(en["why"])]
    full = " ".join([en["title"], en["dek"], en["body"], *en["why"]])
    return {**base, "title": pick("title"), "dek": pick("dek"), "why": why, "body": pick("body"), "x": en["x"][:240], "card": en["card"],
            "check": {"unknown_numbers": [], "hype": sorted({m.group(0) for m in blog.HYPE.finditer(full)}
                                                            | {m.group(0) for m in blog.BLAME.finditer(full)})},
            "model": "script" + (f", translated by {blog.AI_MODEL}" if tr else "")}


# ---------- charts ----------
CAPTIONS = {
    "days": {"en": "Blocks per day, German time; a day with a chain restart is grey and marked.", "zh": "每天的区块数（德国时间）；有链重启的日子为灰色并有标注。",
             "ja": "1日あたりのブロック数（ドイツ時間）。チェーンの再起動があった日は灰色で印付き。"},
    "sources": {"en": "Where the week's transactions came from.", "zh": "本周交易的来源。", "ja": "今週のトランザクションの出どころ。"},
    "before": {"en": "This week against the week before.", "zh": "本周与上周对比。", "ja": "今週と先週の比較。"}}


def figures(f: dict, a: dict) -> list[dict]:
    """Up to three charts from the counted numbers, each linked to the live page it comes from; placed after the
    sections they belong to (by heading position in the English body)."""
    import blog_pics as bp
    os.makedirs(blog.IMG, exist_ok=True)
    base = os.path.join(blog.IMG, a["id"])
    heads = [ln[3:].strip().lower() for ln in str(a["body"]["en"]).split("\n") if ln.startswith("## ")]
    def after(*words):
        for i, h in enumerate(heads):
            if any(w in h for w in words):
                return i + 1
        return 99
    figs = []
    pd = f.get("per day") or []
    if len(pd) > 1 and any(k for _, k, _ in pd):
        im = bp.bars([k for _, k, _ in pd], [d + ("\nrestart" if r else "") for d, _, r in pd],
                     "Blocks per day", f"{s(len(f.get('restarts') or []), 'chain restart')} this week, cause unknown"
                     if f.get("restarts") else "No chain restart this week", accent=[i for i, (_, _, r) in enumerate(pd) if not r])
        im.save(base + "-days.png")
        figs.append({"src": f"{blog.NODE}/blog/img/{a['id']}-days.png", "caption": CAPTIONS["days"], "after": after("chain"), "link": "/stats/"})
    src = f.get("sources") or {}
    apps = sum(k for _, k, _ in src.get("apps") or [])
    ours = sum(k for _, k in src.get("ours") or [])
    parts = [("users of our apps", apps, bp.OK), ("other wallets", src.get("other") or 0, (190, 196, 204)),
             ("IDNI's testing", src.get("idni") or 0, (120, 120, 128)), ("our test traffic", ours, bp.AMBER)]
    parts = [p for p in parts if p[1]]
    if parts:
        bp.split(parts, "Where the transactions came from", "wallets, not people; IDNI's testing and our own traffic are not users").save(base + "-sources.png")
        figs.append({"src": f"{blog.NODE}/blog/img/{a['id']}-sources.png", "caption": CAPTIONS["sources"], "after": after("who used", "came from"), "link": "/meta/"})
    bf = f.get("before") or {}
    cc = chain_counts(f)
    if bf and cc:
        rows = [("blocks", bf["blocks"], cc[0]), ("transactions", bf["txs"], cc[1]), ("chain restarts", bf["restarts"], len(f.get("restarts") or []))]
        if bf.get("app txs") is not None and src:
            rows.append(("by users of our apps", bf["app txs"], apps))
        bp.pairs([r for r in rows if r[1] or r[2]], "This week against the week before", "grey: the week before, green: this week").save(base + "-before.png")
        figs.append({"src": f"{blog.NODE}/blog/img/{a['id']}-before.png", "caption": CAPTIONS["before"], "after": after("week before"), "link": "/stats/"})
    return figs


def write_draft(f: dict, wid: str, now: float | None = None, tr: dict | None = None, ask_=None) -> str:
    """The week's draft, unlisted under /blog/drafts/ like every other; written anew (same id, same address) on a rerun.
    With NEWS_AI_KEY the model writes it from the counted facts (every number checked); without, or when that fails,
    the script's own text."""
    now = now or time.time()
    a = None
    if (ask_ or blog.AI_KEY) and tr is None:
        try:
            a = article(f, wid, now, out=(ask_ or ask)(model_facts(f)))
        except Exception as e:  # noqa: BLE001 - the script's text instead
            log.warning("week article by the model: %s; the script's text instead", e)
    if a is None:
        a = article(f, wid, now, translate(text(f)) if tr is None else tr)
    try:
        if blog.make_hero(a, a["stats"]):
            a["image"] = f"{blog.NODE}/blog/img/{a['id']}-hero.jpg"
    except Exception as e:  # noqa: BLE001 - a post without its picture beats no post
        log.warning("week hero: %s", e)
    try:
        a["figures"] = figures(f, a)
    except Exception as e:  # noqa: BLE001
        log.warning("week charts: %s", e)
    try:
        import editor
        a["editor"] = editor.review(a)
    except Exception as e:  # noqa: BLE001
        log.warning("week editor: %s", e)
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
    import editor
    return "\n".join([f"Weekly testnet post ready as a draft: {a['title']['en']}"] + ["• " + x for x in a.get("numbers") or []]
                     + editor.lines(a) + [
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
        print("writing the week's draft (with NEWS_AI_KEY the model writes it from the counted facts, then a second read; a few minutes); nothing is published", flush=True)
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
