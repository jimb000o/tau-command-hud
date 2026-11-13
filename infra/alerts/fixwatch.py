"""Reported by us, solved by IDNI: tauhud.com/findings/ and /roadmap/ follow IDNI's code by themselves, and the
channel hears it once when IDNI solves something we reported (Kilian, 13 November 2026: "I should not have to start a
conversation each time").

devpulse.py runs step() after each pass:
  - our reports come from the Findings page itself (findings/index.html, mounted read-only at FINDINGS_PAGE): number,
    kind (bug, request, or our own pull request), what we found, why it matters, and how far IDNI got by hand
    (idni: "partly" / "done", fixedOn)
  - each change on IDNI's tau-testnet main that our news line wrote a headline for goes to the language model once,
    with every report IDNI has not solved yet: does the change solve one (done), part of one (partly), or none? An
    answer counts only when it quotes the change's message or diff word for word and the quote is really there, and
    its sentence passes the daily IDNI post's checks (no number the change does not hold, no blame or hype wording)
  - IDNI closing one of our issues as completed, or merging one of our pull requests, counts too (GitHub's state, read
    once an hour by roadmap_watch.py)
  - the result goes into devpulse.json as refs.fixed, {n: {level, by, sha, ts, at, line{en,zh,ja}, evidence}}; both
    pages show it beside what is written by hand (the hand-written level wins when it says more)
  - the owner hears of each one privately (not between 22:00 and 08:00 German time) and can take it back:
    up idni fixed no <n>
  - the post "Reported by us, solved by IDNI": everything solved (done, not partly) since the last such post, in ONE
    post, once the newest of them is GROUP_MINUTES old, between 08:00 and 22:00 German time, at most one a UTC day.
    In draft mode (the start) the owner gets the text privately and sends it with up idni fixed send; after
    up idni fixed auto the next ones go out by themselves (alerts.py posts an approved one within a minute).

  python devpulse.py --fixed [status | send | no <n> | auto | draft]      (on the server: up idni fixed …)
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger("fixwatch")

PAGE = os.environ.get("FINDINGS_PAGE", "/findings/index.html")
STATE = os.environ.get("FIXWATCH_PATH", "/state/devpulse/fixes.json")
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
REPO = "IDNI/tau-testnet"
GROUP = float(os.environ.get("FIXWATCH_GROUP_MINUTES", 120)) * 60   # wait this long after the newest one for more
PER_PASS = 6            # changes read per pass at most; the rest the next pass
FIRST_DAYS = 3          # the first pass reads the news line's changes of this many days
RECENT_DAYS = 7         # a report marked done by hand with a fixedOn this recent is still worth its post
DRAFT_DAYS = 2          # a draft the owner leaves this long is not sent, and its reports are not drafted again
QUIET = (22, 8)
BERLIN = ZoneInfo("Europe/Berlin")
RANK = {"partly": 1, "done": 2}


# ---------------- our reports, from the Findings page ----------------
def reports(text: str) -> list[dict]:
    """FINDINGS from findings/index.html: n, kind, title, brief, found, impact, idni, idniBrief, fixedOn."""
    a = text.find("const FINDINGS = [")
    if a < 0:
        return []
    b = text.find("\n];", a)
    text = text[a:b if b > a else len(text)]
    starts = [m.start() for m in re.finditer(r"\{\s*n:\s*\d+", text)]
    out = []
    for i, s in enumerate(starts):
        chunk = text[s:starts[i + 1] if i + 1 < len(starts) else len(text)]
        r = {"n": int(re.match(r"\{\s*n:\s*(\d+)", chunk).group(1))}
        for k, v in re.findall(r'\b(kind|title|brief|found|impact|idni|idniBrief|fixedOn):\s*"((?:[^"\\]|\\.)*)"', chunk):
            r.setdefault(k, v.replace('\\"', '"'))
        out.append(r)
    return out


def read_reports() -> list[dict]:
    try:
        with open(PAGE, encoding="utf-8") as f:
            return reports(f.read())
    except OSError as e:
        log.info("findings page: %s", e)
        return []


def numbers() -> set[int]:
    """Every report's number, for the hourly GitHub states (roadmap_watch.py)."""
    return {r["n"] for r in read_reports()}


# ---------------- state ----------------
def load() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            j = json.load(f)
        return j if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


def save(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE)


def quiet(now: float) -> bool:
    h = datetime.fromtimestamp(now, BERLIN).hour
    return h >= QUIET[0] or h < QUIET[1]


def level_of(r: dict, fixed: dict) -> int:
    """How far IDNI got with a report: by hand on the page, or as read here, whichever says more."""
    auto = fixed.get(str(r["n"])) or {}
    return max(RANK.get(r.get("idni") or "", 0), RANK.get(auto.get("level") or "", 0))


def still_open(reps: list[dict], fixed: dict, states: dict, no: dict) -> list[dict]:
    """The reports a change could still solve: our issues (bugs and requests) IDNI has not solved yet, open on GitHub."""
    out = []
    for r in reps:
        s = (states.get(str(r["n"])) or states.get(r["n"]) or {}).get("state")
        if r.get("kind") == "fix" or level_of(r, fixed) >= RANK["done"] or (s and s != "open"):
            continue
        out.append(r)
    return out


# ---------------- the language model ----------------
SYSTEM = """You check whether one change IDNI made to the code of Tau Net's testnet (Tau Testnet Alpha) solves any of \
the reports Tau HUD filed with IDNI. Tau HUD is a community project not affiliated with IDNI.

You get the change (its message, the commits of a merged branch, the files and part of the diff, and the headline our \
news line wrote for it) and the reports that are still open: what we found and why it matters.

For each report the change solves, completely or in part, give one verdict. Rules:
- done: after this change the problem we reported no longer happens, or what we asked for is now there (also when IDNI \
went further than we asked). partly: one clear part of it is solved and another part is not.
- Only what the change itself shows. A change in the same area is not a fix. A test, a doc line or a comment alone is \
not a fix. When in doubt, no verdict.
- evidence: a quote of 15 to 200 characters copied exactly, character for character, from the change's message or \
diff above, that shows it. No quote, no verdict.
- line: one sentence of at most 200 characters in plain words: what IDNI's change does about our report, present \
tense, starting with "IDNI's change" or "Since this change". Never say IDNI did it because of our report. No blame, no \
hype, no exclamation marks, no code names, stream names or commit hashes. Call the network Tau Net.
- zh and ja: the same sentence in Simplified Chinese and in Japanese.

Answer with JSON only, no other text, an empty list when the change solves none of them:
{"verdicts":[{"n":0,"level":"done","evidence":"","line":"","zh":"","ja":""}]}"""


def prompt_of(item: dict, context: str, opens: list[dict]) -> str:
    reps = "\n\n".join(f"Report #{r['n']}{' (a request, not a bug)' if r.get('kind') == 'request' else ''}: {r.get('title', '')}\n"
                       f"What we found: {r.get('found', '')}\nWhy it matters: {r.get('impact', '')}"
                       + ("\nIDNI so far: partly solved" if level_of(r, {}) == RANK["partly"] else "") for r in opens)
    head = (item.get("headline") or {}).get("en", "")
    return f"The change:\n{context}\n\nOur news line's headline for it: {head}\n\nThe open reports:\n\n{reps}"


def ask(prompt: str) -> dict:
    import ai_meter
    import devpulse as dp
    import urllib.request
    body = json.dumps({"model": dp.NEWS_AI_MODEL, "max_tokens": 1500, "system": SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": dp.NEWS_AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.load(r)
    ai_meter.meter("fixwatch", dp.NEWS_AI_MODEL, j.get("usage"))
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


def flat(s: str) -> str:
    return " ".join(str(s or "").split())


def verdicts(out: dict, context: str, prompt: str, opens: list[dict]) -> list[dict]:
    """The model's verdicts that hold up: a report still open, a known level, a quote that is in the change, and a
    sentence the checks let through."""
    import idni_digest as idg
    ok, nums, body = [], {r["n"] for r in opens}, flat(context)
    for v in out.get("verdicts") or []:
        try:
            n = int(v.get("n"))
        except (TypeError, ValueError):
            continue
        ev, line = flat(v.get("evidence")), idg.line(v.get("line"), 220)
        if n not in nums or v.get("level") not in RANK or not (15 <= len(ev) <= 300) or ev not in body or not line:
            log.info("fixwatch: verdict on #%s left out (level %s, quote found %s)", v.get("n"), v.get("level"), ev in body)
            continue
        chk = idg.check_text([line], prompt)
        if chk["unknown_numbers"] or chk["wording"]:
            log.info("fixwatch: verdict on #%s left out by the check %s", n, chk)
            continue
        ok.append({"n": n, "level": v["level"], "evidence": ev, "line": {"en": line, "zh": idg.line(v.get("zh"), 300) or line,
                                                                          "ja": idg.line(v.get("ja"), 300) or line}})
    return ok


# ---------------- one pass ----------------
def _tell(text: str) -> tuple[bool, str]:
    import tickerwatch
    return tickerwatch.tell(text)


def _context(path: str, sha: str) -> str:
    import devpulse as dp
    ctx = dp.commit_context(REPO, path, sha, limit=8000)
    try:   # the docs too: a change that explains itself in the docs says so there
        parents = dp.git(path, "log", "-1", "--format=%P", sha).split()
        if parents:
            docs = dp.git(path, "diff", "--no-renames", "-U1", parents[0], sha, "--", "docs", "*.md")
            if docs.strip():
                ctx += "\nDocs diff (may be cut):\n" + docs[:4000]
    except Exception:  # noqa: BLE001
        pass
    return ctx


def note_of(n: int, e: dict, r: dict | None) -> str:
    what = {"code": f"IDNI's change {e.get('sha', '')[:7]}", "closed": "IDNI closed the issue as completed",
            "merged": "IDNI merged our pull request", "page": "marked by hand on the page"}.get(e.get("by"), e.get("by"))
    lines = [f"Findings: #{n} {'solved' if e['level'] == 'done' else 'partly solved'} by IDNI ({what}).",
             (r or {}).get("brief", ""), f"Our server read: {e['line']['en']}" if e.get("line") else ""]
    if e.get("evidence"):
        lines.append(f"Quote from the change: “{e['evidence']}”")
    lines += [f"{SITE}/findings/ and {SITE}/roadmap/ show it now. Wrong? up idni fixed no {n}"]
    return "\n".join(x for x in lines if x)


def step(news: list[dict], states: dict | None, path: str | None, now: float, ask_=None, tell=_tell,
         reps: list[dict] | None = None) -> dict:
    """One pass; returns refs.fixed for devpulse.json."""
    import devpulse as dp
    reps = read_reports() if reps is None else reps
    st = load()
    first = "judged" not in st
    st.setdefault("judged", {})
    st.setdefault("fixed", {})
    st.setdefault("no", {})
    st.setdefault("notes", [])
    st.setdefault("posted", [])
    st.setdefault("mode", "draft")
    fixed, no, states = st["fixed"], st["no"], {str(k): v for k, v in (states or {}).items()}
    by_n = {r["n"]: r for r in reps}
    new: list[int] = []

    def put(n: int, e: dict):
        old = fixed.get(str(n))
        if str(n) in no and e.get("sha") in no[str(n)]:
            return
        if old and RANK.get(old.get("level"), 0) >= RANK[e["level"]]:
            return
        fixed[str(n)] = {**e, "at": now}
        new.append(n)

    # GitHub: an issue of ours closed as completed, a pull request of ours merged (not on the first pass: history)
    was = st.get("states") or {}
    for r in reps:
        s, w = (states.get(str(r["n"])) or {}).get("state"), (was.get(str(r["n"])) or {}).get("state")
        if was and w == "open" and s in ("closed", "merged"):
            put(r["n"], {"level": "done", "by": "merged" if s == "merged" else "closed", "ts": now})
    if states:
        st["states"] = {k: {"state": v.get("state")} for k, v in states.items()}

    # the code: each new headline of the news line, read once against the reports still open
    todo = [i for i in sorted(news or [], key=lambda i: i.get("ts") or 0)
            if i.get("id") and i["id"] not in st["judged"] and (not first or (i.get("ts") or 0) >= now - FIRST_DAYS * 86400)]
    if first:
        for i in news or []:
            if i.get("id") and (i.get("ts") or 0) < now - FIRST_DAYS * 86400:
                st["judged"][i["id"]] = now
    if todo and path and dp.NEWS_AI_KEY and now - st.get("failed_at", 0) >= 1800:
        for i in todo[:PER_PASS]:
            opens = still_open(reps, fixed, states, no)
            if not opens:
                st["judged"][i["id"]] = now
                continue
            sha = (i.get("shas") or [i["id"]])[-1]
            try:
                ctx = _context(path, sha)
                prompt = prompt_of(i, ctx, opens)
                for v in verdicts((ask_ or ask)(prompt), ctx, prompt, opens):
                    put(v["n"], {"level": v["level"], "by": "code", "sha": sha, "ts": i.get("ts"), "line": v["line"],
                                 "evidence": v["evidence"], "url": f"https://github.com/{REPO}/commit/{sha}"})
                st["judged"][i["id"]] = now
            except Exception as e:  # noqa: BLE001 - the change is read again in half an hour
                log.warning("fixwatch: %s", e)
                st["failed_at"] = now
                break

    # marked done by hand on the page, recently: worth the post too (it has no note: the page already says it)
    for r in reps:
        if r.get("idni") == "done" and r.get("fixedOn") and str(r["n"]) not in fixed:
            try:
                ts = datetime.fromisoformat(r["fixedOn"]).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
            if ts >= now - RECENT_DAYS * 86400:
                fixed[str(r["n"])] = {"level": "done", "by": "page", "ts": ts, "at": now,
                                      "line": {"en": _cap(r.get("idniBrief", ""))}}

    st["notes"] += [{"n": n, "text": note_of(n, fixed[str(n)], by_n.get(n))} for n in new]
    if st["notes"] and not quiet(now):
        ok, why = tell("\n\n".join(x["text"] for x in st["notes"]))
        log.info("fixwatch note to the owner %s", "sent" if ok else f"NOT sent ({why})")
        if ok:
            st["notes"] = []
    plan_post(st, by_n, now, tell, ask_)
    st["judged"] = {k: v for k, v in st["judged"].items() if v >= now - 60 * 86400}
    save(st)
    return public(st)


def _cap(s: str) -> str:
    s = s.strip()
    return s[:1].upper() + s[1:] if s else s


def public(st: dict) -> dict:
    """What the pages read (devpulse.json refs.fixed): never what the owner took back."""
    return {n: {k: e.get(k) for k in ("level", "by", "sha", "ts", "line", "evidence", "url") if e.get(k) is not None}
            for n, e in (st.get("fixed") or {}).items() if e.get("by") != "page"}


# ---------------- the post ----------------
POST_SYSTEM = """You write one short post for the Telegram channel and the X account of Tau HUD (tauhud.com), a \
community project not affiliated with IDNI, the team that builds Tau Net. Tau HUD reports problems and requests to \
IDNI; IDNI has now solved some of them. You get each one: what we reported and what IDNI's change does about it.

Rules:
- Only facts the input shows. Never say IDNI did it because of our report, or because of us; say we reported it and \
that it is solved now.
- Thank IDNI plainly, once. No blame, no hype or marketing words, no exclamation marks, no emoji, no price talk.
- Plain words; no code names, stream names or commit hashes; numbers of 1,000 and more with commas (100,000). The network is Tau Net, its test network the Tau Net \
testnet; Tau Language is the language its rules are written in.

Fields (English only):
- title: at most 70 characters, what is solved now.
- items: for each report in the input, in its order, one sentence of at most 180 characters: what works now that did \
not before.
- x_text: at most 200 characters for X, no link, no hashtag.

Answer with JSON only: {"title":"","items":[""],"x_text":""}"""


def post_input(ns: list[int], fixed: dict, by_n: dict) -> str:
    out = []
    for n in ns:
        r, e = by_n.get(n) or {}, fixed.get(str(n)) or {}
        out.append(f"#{n} ({'our request' if r.get('kind') == 'request' else 'our pull request' if r.get('kind') == 'fix' else 'our bug report'}): "
                   f"{r.get('found') or r.get('brief', '')}\nWhat IDNI did: "
                   + ((e.get("line") or {}).get("en") or {"closed": "IDNI closed the issue as completed.",
                                                           "merged": "IDNI merged our pull request."}.get(e.get("by"), "")))
    return "\n\n".join(out)


def write_post(ns: list[int], fixed: dict, by_n: dict, ask_=None) -> dict:
    """The post's text: the model's when it passes the checks, else plain lines from the reports themselves."""
    import idni_digest as idg
    prompt = post_input(ns, fixed, by_n)
    plain = {"title": "Reported by us, solved by IDNI",
             "items": [_cap(((fixed.get(str(n)) or {}).get("line") or {}).get("en") or (by_n.get(n) or {}).get("brief", "")) for n in ns],
             "x_text": ""}
    try:
        out = (ask_ or post_ask)(prompt)
        items = [idg.line(x, 200) for x in (out.get("items") or [])]
        d = {"title": idg.line(out.get("title"), 80), "items": items, "x_text": idg.line(out.get("x_text"), 220)}
        chk = idg.check_text([d["title"], *items, d["x_text"]], prompt)
        if len(items) == len(ns) and all(items) and d["title"] and d["x_text"] and not chk["unknown_numbers"] and not chk["wording"]:
            return {**d, "by": "model"}
        log.info("fixwatch post: the model's text left out (%s)", chk)
    except Exception as e:  # noqa: BLE001
        log.warning("fixwatch post: %s", e)
    return {**plain, "by": "plain"}


def post_ask(prompt: str) -> dict:
    import ai_meter
    import devpulse as dp
    import urllib.request
    body = json.dumps({"model": dp.NEWS_AI_MODEL, "max_tokens": 800, "system": POST_SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": dp.NEWS_AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        j = json.load(r)
    ai_meter.meter("fixwatch", dp.NEWS_AI_MODEL, j.get("usage"))
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer")
    return json.loads(m.group(0))


def tg_text(p: dict) -> str:
    e = html.escape
    rows = [f"• <b>#{n}</b> {e(t)}" for n, t in zip(p["ns"], p["items"])]
    return "\n\n".join([f"🎉 <b>{e(p['title'])}</b>", "\n".join(rows),
                        f'Thank you, IDNI. Every report we filed and where it stands: <a href="{SITE}/findings/">Findings on Tau HUD</a>',
                        "<i>Tau HUD is a community project, not affiliated with IDNI.</i>"])


X_FOOT = "🛠 Tau HUD build watch, not affiliated with IDNI"


def x_lines(p: dict) -> list[str]:
    return [f"🎉 {p['title']}", p.get("x_text") or p["items"][0]]


def plan_post(st: dict, by_n: dict, now: float, tell=_tell, ask_=None) -> None:
    """Gather what is solved (done) and not yet in a post; once the newest is GROUP old, outside the night and with no
    such post today, write it: as a draft for the owner, or approved for alerts.py in auto mode."""
    p = st.get("post")
    if p and p.get("status") in ("draft", "approved"):
        posted = (_alerts_state().get("posted") or {})
        if p["id"] in posted:
            st["posted"] = sorted(set(st["posted"]) | set(p["ns"]))
            st["post"] = {**p, "status": "posted", "posted_at": posted[p["id"]]}
        elif p["status"] == "draft" and now - p["built"] > DRAFT_DAYS * 86400:   # left as it was: never sent, not drafted again
            st["posted"] = sorted(set(st["posted"]) | set(p["ns"]))
            st["post"] = {**p, "status": "left"}
        return
    fixed = st.get("fixed") or {}
    ns = sorted(int(n) for n, e in fixed.items()
                if e.get("level") == "done" and int(n) not in st.get("posted", []) and int(n) in by_n)
    if not ns:
        return
    newest = max(fixed[str(n)].get("at") or 0 for n in ns)
    day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    if now - newest < GROUP or quiet(now) or (st.get("post") or {}).get("day") == day:
        return
    d = write_post(ns, fixed, by_n, ask_)
    p = {"id": f"fixed-{int(now)}", "ns": ns, "built": now, "day": day, **d,
         "status": "approved" if st.get("mode") == "auto" else "draft"}
    st["post"] = p
    if p["status"] == "draft":
        tell("Draft of the post “Reported by us, solved by IDNI” (Telegram, then X without a link). Nothing is sent yet.\n\n"
             + re.sub(r"<[^>]+>", "", tg_text(p)) + "\n\nX: " + " · ".join(x_lines(p))
             + "\n\nSend it: up idni fixed send · leave it: nothing to do · from now on without asking: up idni fixed auto")


def _alerts_state() -> dict:
    try:
        with open(os.environ.get("STATE_PATH", "/state/alerts.json"), encoding="utf-8") as f:
            j = json.load(f)
        return (j.get("fixed") or {}) if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


# ---------------- the owner's commands ----------------
def cli(argv: list[str]) -> int:
    st = load()
    what = argv[0] if argv else "status"
    if what in ("auto", "draft"):
        st["mode"] = what
        save(st)
        print("from now on the post goes out by itself" if what == "auto" else "from now on you get each post as a draft first")
        return 0
    if what == "no" and len(argv) > 1 and argv[1].lstrip("#").isdigit():
        n = argv[1].lstrip("#")
        e = (st.get("fixed") or {}).pop(n, None)
        if not e:
            print(f"#{n} is not marked as solved here")
            return 1
        st.setdefault("no", {}).setdefault(n, []).append(e.get("sha"))
        p = st.get("post") or {}
        if p.get("status") in ("draft", "approved") and int(n) in p.get("ns", []):
            st["post"] = {**p, "status": "dropped"}
        save(st)
        print(f"taken back: #{n} is no longer shown as solved, and that change is not read for it again")
        return 0
    if what == "send":
        p = st.get("post") or {}
        if p.get("status") != "draft":
            print("no draft waiting" + (f" (the last one is {p.get('status')})" if p else ""))
            return 1
        st["post"] = {**p, "status": "approved"}
        save(st)
        print("approved: the alerts service posts it within a minute (Telegram, then X)")
        return 0
    print(f"mode: {st.get('mode', 'draft')} (up idni fixed auto / draft)")
    for n, e in sorted((st.get("fixed") or {}).items(), key=lambda x: int(x[0])):
        day = datetime.fromtimestamp(e.get("at") or 0, timezone.utc).strftime("%d.%m.")
        print(f"  #{n} {e['level']} ({e.get('by')}{' ' + e['sha'][:7] if e.get('sha') else ''}, noticed {day}): "
              f"{(e.get('line') or {}).get('en', '')}")
    p = st.get("post")
    if p:
        print(f"\npost {p['id']}: {p['status']}\n" + re.sub(r"<[^>]+>", "", tg_text(p)))
    print(f"\n{len(st.get('judged') or {})} IDNI changes read so far")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(cli(sys.argv[1:]))
