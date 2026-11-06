"""IDNI's progress of the day in one post: what IDNI merged into the testnet's code, read together.

The news line already gets one headline per change (devpulse.py). The channels got nothing of it until 6 November
2026: a day with real progress (a block-maker fix, a multi-validator fix, tests) went by without a word on Telegram
or X. Here every merge of one day is read together and written up as ONE post with the combined meaning:

  - once a day at IDNI_DIGEST_HOUR UTC (11:00 German winter time) devpulse closes a window: everything merged on
    tau-testnet main since the last window (the first one reaches back IDNI_DIGEST_FIRST_DAYS days, from midnight)
  - a window with nothing the news writer counted as news (only tests, CI, docs, merging main into a branch) is quiet:
    no model call, no post
  - otherwise a language model gets each change (message, merged branch commits, diff, the headline the news line
    already shows), the housekeeping of the same window by title only, and tau-lang's commits of the same window by
    title (with whether the testnet's build uses them yet), and writes a title, two to four points, "why it matters"
    and the X text, or says the day is not worth a post
  - every number the text uses must be in the input, and blame or hype words hold the post back (like the blog)
  - alerts.py posts it once within IDNI_DIGEST_LATE_HOURS of the window's end: Telegram (with the links) and, when the
    model marks it as notable beyond the community, X (never a link); at most one IDNI post a UTC day

  python devpulse.py --digest            what the next post would say now (one model call, posts nothing), and the last ones
  python devpulse.py --digest send       write it now for the window up to now; alerts posts it within a minute
                                         (--force: also when the check found numbers or wording to look at)
  python devpulse.py --digest hold       the next automatic post is not sent (its commits wait for the one after)
  python devpulse.py --digest release    take the hold back
On the server: up idni, up idni send, up idni hold, up idni release.
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

import devpulse as dp

HOUR = int(os.environ.get("IDNI_DIGEST_HOUR", 10))                 # UTC: 11:00 German winter time
FIRST_DAYS = int(os.environ.get("IDNI_DIGEST_FIRST_DAYS", 3))      # the first window reaches back this many days
LANG_ALONE = os.environ.get("IDNI_DIGEST_LANG_ALONE", "false").lower() in ("1", "true", "yes")   # tau-lang alone is a post
LATE = float(os.environ.get("IDNI_DIGEST_LATE_HOURS", 3)) * 3600   # a window not posted by then stays unposted
KEEP_DAYS = 21
VERSION = 1
LANG = "IDNI/tau-lang"
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
NUM = re.compile(r"\d+(?:[.,]\d+)?")
BLAME = re.compile(r"\b(IDNI|Tau|the testnet|the chain|the team|developers?)(['’]s)?\s+(is |was |were |had )?"
                   r"(at fault|to blame|fault|failed|broke|broken|unreliable|unstable|buggy|careless|let us down|sloppy)\b", re.I)
HYPE = re.compile(r"\b(huge|exciting|revolutionary|game[- ]chang\w*|moon|pump|finally|incredible|massive|breakthrough|"
                  r"mainnet (is )?(near|close|soon))\b|!", re.I)


def path_of(name: str) -> str:
    return os.path.join(dp.CLONES, name)


def files() -> tuple[str, str]:
    return (os.environ.get("IDNI_DIGEST_FILE") or path_of("digests.json"), path_of("digest-hold.json"))


def read(p: str, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def load() -> dict:
    j = read(files()[0], {})
    if not isinstance(j, dict) or j.get("version") != VERSION:
        return {"version": VERSION, "items": []}
    j.setdefault("items", [])
    return j


def save(st: dict) -> None:
    os.makedirs(os.path.dirname(files()[0]) or ".", exist_ok=True)
    dp.write_atomic(files()[0], json.dumps(st, ensure_ascii=False))


def held() -> dict:
    """{"until": ts}: no automatic post with a window ending before `until`."""
    j = read(files()[1], {})
    return j if isinstance(j, dict) else {}


def slot_at(now: float) -> int:
    """The latest IDNI_DIGEST_HOUR (UTC) at or before now."""
    t = dp.day0(int(now)) + HOUR * 3600
    return t if t <= now else t - 86400


def day_label(ts: list[int]) -> str:
    """'5 Nov', '4–5 Nov', '31 Oct – 2 Nov' (UTC days of the commits)."""
    if not ts:
        return ""
    a, b = (datetime.fromtimestamp(x, timezone.utc) for x in (min(ts), max(ts)))
    if a.date() == b.date():
        return f"{a.day} {a:%b}"
    if (a.month, a.year) == (b.month, b.year):
        return f"{a.day}–{b.day} {b:%b}"
    return f"{a.day} {a:%b} – {b.day} {b:%b}"


# ---------- what landed in a window ----------
def first_parent(path: str, branch: str, start: int, end: int) -> list[dict]:
    out = dp.git(path, "log", "--first-parent", branch, f"--since=@{start - 60}", f"--until=@{end + 60}",
                 "--format=%H%x1f%ct%x1f%s%x1f%b%x1e")
    items = []
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        sha, ct, subject, body = (chunk.strip("\n").split("\x1f") + ["", "", "", ""])[:4]
        if not (start <= int(ct) < end):
            continue
        if re.match(r"merge pull request #\d+", subject, re.I):
            subject = next((x for x in body.splitlines() if x.strip()), subject)
        items.append({"sha": sha, "ts": int(ct), "subject": subject.strip()})
    return list(reversed(items))   # oldest first


def is_candidate(path: str, c: dict) -> bool:
    """The same test the news line uses: not housekeeping by its title, and not only tests, docs or CI by its files."""
    if not dp.headline(c["subject"]):
        return False
    names = dp.changed_files(path, c["sha"])
    return not (names and all(dp.QUIET_FILE.search(f) for f in names))


def gather(paths: dict, branches: dict, start: int, end: int, pin: str | None, news: dict) -> dict:
    """The window's changes: `changes` the news writer counted as news (with its headline), `pending` not judged yet,
    `house` the rest by title, `lang` tau-lang's own changes by title."""
    tn = paths.get(dp.TESTNET)
    out = {"changes": [], "pending": [], "house": [], "lang": []}
    if not tn:
        return out
    by_sha = {s: it for it in news.get("items") or [] for s in it.get("shas") or []}
    seen = news.get("seen") or {}
    for c in first_parent(tn, branches.get(dp.TESTNET) or "main", start, end):
        if c["sha"] in by_sha:
            it = by_sha[c["sha"]]
            c.update(headline=it["headline"]["en"], tip=it["tip"]["en"], kind=it.get("kind"),
                     runs=bool(pin) and dp.is_ancestor(tn, c["sha"], pin))
            out["changes"].append(c)
        elif c["sha"] not in seen and is_candidate(tn, c):
            c["runs"] = bool(pin) and dp.is_ancestor(tn, c["sha"], pin)
            out["pending"].append(c)
        else:
            out["house"].append(c)
    lp = paths.get(LANG)
    if lp:
        used = dp.lang_pin(tn, branches.get(dp.TESTNET) or "main")
        for c in first_parent(lp, branches.get(LANG) or "main", start, end)[-30:]:
            if is_candidate(lp, c):
                c["in_build"] = bool(used) and dp.is_ancestor(lp, c["sha"], used)
                out["lang"].append(c)
    return out


SYSTEM = """You write one daily post for the Telegram channel and the X account of Tau HUD (tauhud.com), an unofficial \
community dashboard for Tau Testnet Alpha, made by people not affiliated with IDNI, the team that builds Tau. Readers \
are the Tau community and the IDNI team itself: curious people, node runners, testers; many never read code.

You get everything IDNI merged into the testnet's code in one window (usually one day): each change with its message, \
the commits of the merged branch, the files and part of the diff, and the one-line headline our news line already \
shows for it. Then the housekeeping of the same window (tests, CI, docs) by title only, and changes to the Tau \
language (tau-lang) in the same window by title.

Write ONE post with the combined meaning of the window, the way a good newspaper sums up a day: what is different now, \
what it adds up to, and why it matters for the testnet, its users or the people running nodes. Rules:
- Only facts the input shows. Never guess motives, causes, dates, releases, timelines or effects it does not show. \
Never link a change to a past outage, stall or incident unless the commit message itself says so. No promises about mainnet.
- Say what works now, not what someone may now do: never word a fix as if miners, validators or anyone gained power or permission ("lets miners change governance" is wrong; "the backup block maker can now make blocks that turn on a rule change" is right). Write "again", "no longer" or "now accepted" only when the input says it worked before or failed before. Never say what a change keeps or protects beyond what its message says.
- Credit IDNI's work plainly ("IDNI merged", "the testnet now ..."). Never blame or criticise anyone, never call \
anything broken or careless; a fix is progress, say what it makes work.
- Plain words. No code names, file names, function names, stream names, flags, package names, commit hashes or \
version numbers; no names of people. Issue or pull request numbers only if they help, at most one.
- No hype or marketing words (huge, major, game-changing, finally, exciting, breakthrough), no price talk, no \
exclamation marks, no emoji.
- Tests, CI and docs: mention them at most in passing in one point ("more of the test suite now runs in a fixed order"), \
never as the lead.
- tau-lang: mention a language change only when someone writing Tau rules would notice it, and say whether the testnet \
uses it yet exactly as the input says.
- post: false when nothing in the window would matter to someone using the testnet or running a node.
- x: true only when the window holds a change people beyond the community would care about (a fix to how blocks are \
made or checked, safety, a new capability, nodes joining or syncing); false for small or internal days.

Fields (English only):
- title: a news headline, at most 80 characters, subject and verb, present tense, sentence case, no date.
- points: two to four short points, each at most 160 characters, most important first; one point per purpose, \
several commits for one purpose make one point.
- why: one sentence, at most 200 characters: why this matters (the "why it matters" line).
- x_text: one or two sentences, at most 200 characters, for X: the gist, no link, no hashtag.
- reason: a few words why you chose post/x as you did (not published).

Answer with JSON only, no other text:
{"post":true,"x":true,"title":"","points":[""],"why":"","x_text":"","reason":""}"""


def prompt_of(g: dict, paths: dict, start: int, end: int) -> str:
    tn = paths[dp.TESTNET]
    a = datetime.fromtimestamp(start, timezone.utc)
    b = datetime.fromtimestamp(end, timezone.utc)
    parts = [f"Window: {a:%Y-%m-%d %H:%M} to {b:%Y-%m-%d %H:%M} UTC. Merged into {dp.TESTNET} main, oldest first:"]
    for c in g["changes"] + g["pending"]:
        parts.append(dp.commit_context(dp.TESTNET, tn, c["sha"], limit=6000))
        if c.get("headline"):
            parts.append(f"Our news line shows: {c['headline']} ({c['tip']})")
    if g["house"]:
        parts.append("Housekeeping merged in the same window (titles only):\n" + "\n".join("- " + c["subject"] for c in g["house"]))
    if g["lang"]:
        parts.append("Tau language (IDNI/tau-lang) changes in the same window (titles only; 'in the testnet's build' says "
                     "whether the testnet already uses it):\n" +
                     "\n".join(f"- {c['subject']} (in the testnet's build: {'yes' if c['in_build'] else 'not yet'})" for c in g["lang"]))
    return "\n\n".join(parts)[:120000]


def ask(prompt: str) -> dict:
    body = json.dumps({"model": dp.NEWS_AI_MODEL, "max_tokens": 1500, "system": SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    import urllib.request
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": dp.NEWS_AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.load(r)
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


def line(v, cap: int) -> str:
    s = " ".join(str(v or "").split())
    return s if 0 < len(s) <= cap else ""


def check_text(texts: list[str], prompt: str) -> dict:
    """Numbers the input does not hold, and blame or hype wording: either holds the post back for a look."""
    known = set(NUM.findall(prompt)) | {"1", "2", "3", "4"}
    joined = " ".join(texts)
    unknown = sorted({n for n in NUM.findall(joined) if n not in known})
    words = sorted({m.group(0) for m in HYPE.finditer(joined)} | {m.group(0) for m in BLAME.finditer(joined)})
    return {"unknown_numbers": unknown, "wording": words}


def write(g: dict, paths: dict, start: int, end: int, pin_ts: int | None, now: int, ask_=None) -> dict:
    """One window written up: status ready (post it), skip (the model saw nothing worth a post), quiet (nothing to
    read), check (numbers or wording to look at first)."""
    changes = g["changes"] + g["pending"]
    d = {"id": f"idni-{end}", "start": start, "end": end, "built": now, "shas": [c["sha"] for c in changes],
         "house": len(g["house"]), "lang": len(g["lang"]), "days": day_label([c["ts"] for c in changes]),
         "runs": "all" if changes and all(c.get("runs") for c in changes) else ("some" if any(c.get("runs") for c in changes) else "none"),
         "pin_ts": pin_ts, "url": f"https://github.com/{dp.TESTNET}/commits/main"}
    if not changes and not (LANG_ALONE and g["lang"]):
        return {**d, "status": "quiet"}
    prompt = prompt_of(g, paths, start, end)
    out = (ask_ or ask)(prompt)
    pts = [p for p in (line(x, 200) for x in (out.get("points") or [])[:4]) if p]
    d.update(title=line(out.get("title"), 100), points=pts, why=line(out.get("why"), 240),
             x_text=line(out.get("x_text"), 240), x=bool(out.get("x")), reason=line(out.get("reason"), 300),
             model=dp.NEWS_AI_MODEL)
    if not out.get("post"):
        return {**d, "status": "skip"}
    if not (d["title"] and pts and d["why"] and d["x_text"]):
        raise ValueError("the answer misses a title, points, why or x_text")
    d["check"] = check_text([d["title"], *pts, d["why"], d["x_text"]], prompt)
    d["status"] = "check" if d["check"]["unknown_numbers"] or d["check"]["wording"] else "ready"
    return d


def plan(st: dict, now: float) -> tuple[int | None, int, int]:
    """(the slot to close now or None, the next slot that can still go out, where the open window starts)."""
    slot = slot_at(now)
    if now - slot > LATE:   # this slot's post could no longer go out: the window stays open for the next one
        slot_next, slot = slot + 86400, None
    else:
        slot_next = slot
    last = st.get("last_end")
    if last is None:        # the first window reaches back FIRST_DAYS days from the midnight before its slot
        last = dp.day0(slot_next) - FIRST_DAYS * 86400
    return slot, slot_next, last


def step(paths: dict, branches: dict, pin: str | None, now: int) -> dict:
    """Called by devpulse on every pass, after the news writer: closes the window at the day's slot once."""
    st = load()
    slot, slot_next, last = plan(st, now)
    st["last_end"] = last
    status = {"next_at": slot_next if slot is None or last < slot else slot_next + 86400, "since": last,
              "state": "waiting for the slot"}
    if not dp.NEWS_AI_KEY:
        status["state"] = "no key"
    elif slot is None or last >= slot:
        pass
    elif held().get("until", 0) > slot:
        status.update(next_at=slot + 86400, state="held (up idni release): its commits wait for the next one")
    elif last < slot and last > slot - 12 * 3600 and st.get("manual_end") == last:
        status.update(next_at=slot + 86400, state="sent by hand within 12 h: the next slot takes it on")
    elif last < slot:
        news = dp.load_headlines()
        g = gather(paths, branches, last, slot, pin, news)
        if g["pending"] and now - slot < 2 * 3600:
            status["state"] = "waiting for the news writer"
        elif now - st.get("failed_at", 0) < 1800:
            status["state"] = "waiting to retry"
        else:
            try:
                pin_ts = int(dp.git(paths[dp.TESTNET], "log", "-1", "--format=%ct", pin)) if pin else None
                dr = st.pop("draft", None)   # the text `up idni` showed, when nothing new came in since
                if dr and dr.get("start") == last and dr.get("shas") == [c["sha"] for c in g["changes"] + g["pending"]]:
                    d = {**dr, "id": f"idni-{slot}", "end": slot, "built": now, "from_preview": True}
                else:
                    d = write(g, paths, last, slot, pin_ts, now)
                st["items"].append(d)
                st["last_end"], st["failed_at"] = slot, 0
                status.update(since=slot, next_at=slot + 86400, state=d["status"])
            except Exception as e:  # noqa: BLE001 - the window stays open; the next pass tries again
                dp.log.warning("IDNI digest: %s", e)
                st["failed_at"] = now
                status["state"] = f"failed: {str(e)[:160]}"
    st["items"] = [x for x in st["items"] if x.get("end", 0) >= now - KEEP_DAYS * 86400]
    save(st)
    last_item = st["items"][-1] if st["items"] else None
    if last_item:
        status["last"] = {k: last_item.get(k) for k in ("id", "end", "status", "title", "days", "x")}
    return status


# ---------- the posts ----------
def node_line(d: dict) -> str:
    if d.get("runs") == "all":
        return "Our node already runs all of it."
    when = datetime.fromtimestamp(d["pin_ts"], timezone.utc).strftime("%-d %b") if d.get("pin_ts") else ""
    if d.get("runs") == "some":
        return "Our node runs part of it" + (f"; its code is from {when}." if when else ".")
    return "Our node does not run it yet" + (f"; its code is from {when}." if when else ".")


def tg_text(d: dict) -> str:
    e = html.escape
    head = "🛠 <b>IDNI testnet progress" + (f" · {e(d['days'])}" if d.get("days") else "") + "</b>"
    parts = [head, f"<b>{e(d['title'])}</b>", "\n".join("• " + e(p) for p in d["points"]),
             f"<b>Why it matters</b>\n{e(d['why'])}", e(node_line(d)),
             f'<a href="{e(d["url"])}">IDNI\'s commits</a> · <a href="{SITE}/devpulse/">Build pulse on Tau HUD</a>',
             "<i>Merged by IDNI. Tau HUD is a community project, not affiliated with IDNI.</i>"]
    return "\n\n".join(parts)


X_FOOT = "🛠 Tau HUD build watch, not affiliated with IDNI"


def x_lines(d: dict) -> list[str]:
    return [f"🛠 IDNI testnet: {d['title']}", d["x_text"], "Why it matters: " + d["why"]]


# ---------- by hand ----------
def _alerts_state() -> dict:
    j = read(os.environ.get("STATE_PATH", "/state/alerts.json"), {})
    return (j.get("idni") or {}) if isinstance(j, dict) else {}


def _show(d: dict, x_post) -> None:
    print(f"  status: {d.get('status')}" + (f" ({d.get('reason')})" if d.get("reason") else ""))
    if d.get("check") and (d["check"]["unknown_numbers"] or d["check"]["wording"]):
        print(f"  check:  numbers not in IDNI's commits {d['check']['unknown_numbers']}, wording {d['check']['wording']}")
    if d.get("title"):
        print("  --- Telegram ---")
        print("  " + tg_text(d).replace("\n", "\n  "))
        print("  --- X " + ("(would go out on X too)" if d.get("x") else "(would stay off X: a small day, Telegram only)") + " ---")
        print("  " + x_post(x_lines(d), foot=X_FOOT, keep=2).replace("\n", "\n  "))


def cli(argv: list[str]) -> int:
    import alerts   # the X formatting and caps live there
    what = argv[0] if argv else "preview"
    st = load()
    when = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%a %d.%m. %H:%M UTC")
    if what == "hold":
        slot, slot_next, last = plan(st, time.time())
        until = (slot_next if slot is None or last < slot else slot_next + 86400) + 1
        dp.write_atomic(files()[1], json.dumps({"until": until}))
        print(f"held: the post of {when(until - 1)} is not sent; its commits wait for the next one (up idni release takes it back)")
        return 0
    if what == "release":
        dp.write_atomic(files()[1], json.dumps({}))
        print("released: the next IDNI post goes out as planned")
        return 0
    paths, branches = {}, {}
    for repo in dp.REPOS:
        paths[repo] = dp.sync(repo)
        branches[repo] = dp.default_branch(paths[repo])
    pin = dp.pins().get(dp.TESTNET)
    try:
        pin = dp.git(paths[dp.TESTNET], "rev-parse", "--verify", "--quiet", pin + "^{commit}").strip() if pin else None
    except subprocess.CalledProcessError:
        pin = None
    now = int(time.time())
    slot, slot_next, last = plan(st, now)
    next_at = slot_next if slot is None or last < slot else slot_next + 86400
    posted = _alerts_state().get("posted") or {}
    if what == "preview":
        for d in st["items"][-3:]:
            print(f"window up to {when(d['end'])}: {d.get('status')}" + (f", {d.get('title')}" if d.get("title") else "")
                  + (" — posted" if d["id"] in posted else ""))
        h = held().get("until", 0)
        if h > now:
            print(f"held until {when(h)} (up idni release)")
        print(f"\nthe next post at {when(next_at)}, covering since {when(last)}; "
              "if it went out now it would say:")
    if not dp.NEWS_AI_KEY:
        print("no key (NEWS_AI_KEY or CHAT_AI_KEY in infra/.env): no IDNI posts")
        return 1
    g = gather(paths, branches, last, now, pin, dp.load_headlines())
    pin_ts = int(dp.git(paths[dp.TESTNET], "log", "-1", "--format=%ct", pin)) if pin else None
    d = write(g, paths, last, now, pin_ts, now)
    print(f"  {len(d['shas'])} changes, {d['house']} housekeeping, {d['lang']} tau-lang")
    print("  (a preview: nothing was sent)")
    _show(d, alerts.x_post)
    if what == "preview" and d["status"] in ("ready", "check"):
        st["draft"] = d   # the post at the slot uses this very text, unless IDNI merges something new before then
        save(st)
        print("\nkept: the next post uses exactly this text unless IDNI merges something new first; "
              "up idni again writes a new one, up idni hold keeps it back")
    if what == "send":
        force = "--force" in argv
        if _alerts_state().get("day") == datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d"):
            print("not sent: an IDNI post already went out today (UTC); at most one a day")
            return 1
        if d["status"] == "check" and force:
            d["status"] = "ready"
        if d["status"] != "ready":
            print("not sent: " + {"quiet": "nothing to report", "skip": "the writer sees nothing worth a post",
                                  "check": "look at the check above (up idni send --force sends it anyway)"}.get(d["status"], d["status"]))
            return 1
        d["manual"] = True
        st["items"].append(d)
        st["last_end"] = st["manual_end"] = now
        save(st)
        print("written: alerts posts it within a minute (at most one IDNI post a UTC day; `docker compose logs alerts` says when)")
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
