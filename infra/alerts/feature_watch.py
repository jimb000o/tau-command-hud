"""A new feature on the Tau Net testnet gets its post the same day, by itself (Kilian, 16 November 2026: "whenever
there's a major feature update to the testnet, Tau HUD should write a post on that day, automatically, without me
saying anything"; over the weekend before, upgrades went by without a word).

What counts, found without a language model (free):
  - testnet: a change on IDNI's tau-testnet main whose title IDNI marks as a feature ("feat: …", "feat(policy): …",
    or a merged pull request with such a title) and that touches more than tests and docs
  - Tau Language in the testnet: tau-testnet's build moves to a newer tau-lang and IDNI's tau-lang changelog lists
    things "Added" between the two (IDNI's own words)
  - a Tau Language release: a new version tag on tau-lang (v0.8.0, …) with its changelog section

What happens:
  1. FEATURE_SETTLE_MINUTES after the newest such change (follow-up commits join the same post) the blog writer
     (news_article.py, the model of the blog) writes an article: what changed, what it gives you, where it stops, what
     is still open, in en/zh/ja, from the change itself and IDNI's docs. A number the input does not hold or a hype or
     blame word: it is asked once more, naming them.
  2. A clean article goes on the blog at once, with its one post on Telegram and X (link on X, #TauNet, the Tau tag
     where it is about Tau), between FEATURE_OPEN_HOUR and FEATURE_CLOSE_HOUR German time and after the usual room
     between posts (POST_GAP_MINUTES); later in the evening it goes out the next morning. At most FEATURE_MAX_PER_DAY.
  3. Without the model (no key, this month's Anthropic spend at FEATURE_AI_MONTH_MAX, the API refusing for
     FEATURE_FALLBACK_HOURS, or still not clean) a testnet feature still gets a short plain post on Telegram and X made
     from IDNI's own title, with the link to the change; the owner hears why. A Tau Language item then only goes to the
     owner.
  The owner always gets a private note with the address and how to take it back (up blog unpublish <id>).
  The daily IDNI post (idni_digest.py) leaves these changes out, so nothing is told twice.

  python feature_watch.py            what was found and what happened to it, and what would count now
On the server: up features
"""
from __future__ import annotations

import contextlib
import html
import io
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone

import devpulse as dp

log = logging.getLogger("feature_watch")

ON = os.environ.get("FEATURE_POSTS", "true").lower() in ("1", "true", "yes")
# changes from before this are never posted here (the daily IDNI post had them); 16 Nov 2026 takes in the rule-change guard
START = int(datetime.fromisoformat(os.environ.get("FEATURE_START", "2026-11-16T00:00:00+00:00")).timestamp())
SETTLE = float(os.environ.get("FEATURE_SETTLE_MINUTES", 45)) * 60
OPEN_HOUR = int(os.environ.get("FEATURE_OPEN_HOUR", 8))      # German time
CLOSE_HOUR = int(os.environ.get("FEATURE_CLOSE_HOUR", 22))
MAX_PER_DAY = int(os.environ.get("FEATURE_MAX_PER_DAY", 2))
AI_MONTH_MAX = float(os.environ.get("FEATURE_AI_MONTH_MAX", 8))   # US dollars, every writer this month together (ai_meter)
FALLBACK = float(os.environ.get("FEATURE_FALLBACK_HOURS", 2)) * 3600
RETRY = 30 * 60
SCAN_DAYS = 7          # commits pushed late (written earlier) are still found this long
KEEP_DAYS = 60
LANG = "IDNI/tau-lang"
SITE = os.environ.get("SITE_URL", "https://tauhud.com").rstrip("/")
FEAT = re.compile(r"^(?:merge:\s*)?feat(?:\([^)]*\))?!?:\s*(.+)", re.I)
TAG = re.compile(r"^v\d+\.\d+(?:\.\d+)?$")
FOOT = "<i>Made by IDNI. Tau HUD is a community project, not run by IDNI.</i>"


def path_of(repo: str) -> str:
    return os.path.join(dp.CLONES, repo.replace("/", "__") + ".git")


def state_file() -> str:
    return os.environ.get("FEATURE_STATE") or os.path.join(dp.CLONES, "features.json")


def load() -> dict:
    try:
        with open(state_file(), encoding="utf-8") as f:
            j = json.load(f)
    except (OSError, ValueError):
        j = {}
    if not isinstance(j, dict):
        j = {}
    j.setdefault("items", [])
    return j


def save(st: dict) -> None:
    os.makedirs(os.path.dirname(state_file()) or ".", exist_ok=True)
    dp.write_atomic(state_file(), json.dumps(st, ensure_ascii=False))


# ---------- what counts ----------
def title_of(subject: str) -> str | None:
    """IDNI's feature title in plain form ("feat(policy): judge transfers …" -> "Judge transfers …"), None if not one."""
    m = FEAT.match(subject.strip())
    if not m:
        return None
    t = re.sub(r"\s*\(#\d+\)\s*$", "", m.group(1)).strip().rstrip(".")
    return t[0].upper() + t[1:] if len(t) >= 4 else None


def is_feature(path: str, c: dict) -> bool:
    if not title_of(c.get("subject") or ""):
        return False
    names = dp.changed_files(path, c["sha"])
    return not (names and all(dp.QUIET_FILE.search(f) for f in names))


def covered() -> set:
    """Every testnet change this watcher has taken (the daily IDNI post leaves them out)."""
    return {s for it in load()["items"] if it.get("kind") == "testnet" for s in it.get("shas") or []}


def skip_in_digest(path: str, c: dict) -> bool:
    """For idni_digest.gather: a feature this watcher posts (or will post) is not in the daily post too."""
    return ON and c.get("ts", 0) >= START and (c["sha"] in covered() or is_feature(path, c))


def changelog(path: str, ref: str) -> str:
    try:
        return dp.git(path, "show", f"{ref}:CHANGELOG.md")
    except subprocess.CalledProcessError:
        return ""


def added(text: str, raw: bool = False) -> list[str]:
    """The "- " lines under every "### Added" of a changelog, without their source links (those change on their own);
    raw: as written, with them."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            on = line.strip().lower() == "### added"
            continue
        if on and line.startswith("- "):
            out.append(line[2:].strip() if raw else re.sub(r"\s*\(PRs:.*\)\s*$", "", line[2:]).strip())
    return out


GH = re.compile(r"\[([^\]]*)\]\((https://github\.com/IDNI/(?:tau-testnet|tau-lang)/(?:commit|pull|issues)/[0-9a-f]{7,40}|"
                r"https://github\.com/IDNI/(?:tau-testnet|tau-lang)/(?:pull|issues)/\d+)\)")


def changelog_links(lines: list[str], cap: int = 40) -> list[dict]:
    """The commits, pull requests and issues a changelog's own lines link, each with the line it belongs to."""
    out, seen = [], set()
    for line in lines:
        what = re.sub(r"\s*\(PRs:.*$", "", line.lstrip("- ")).strip()
        what = re.sub(r"`", "", what)[:110]
        for m in GH.finditer(line):
            if m.group(2) not in seen:
                seen.add(m.group(2))
                out.append({"url": m.group(2), "what": what})
    return out[:cap]


def section(text: str, tag: str) -> str:
    """A release's part of the changelog: from its "## [tag]" heading to the next "## " heading."""
    m = re.search(r"^## \[" + re.escape(tag) + r"\].*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def scan(st: dict, now: int) -> None:
    """New testnet features, a newer Tau Language in the testnet's build, new Tau Language releases: into the state."""
    import idni_digest
    tn = path_of(dp.TESTNET)
    if not os.path.isdir(tn):
        return
    branch = dp.default_branch(tn)
    known = {s for it in st["items"] for s in it.get("shas") or []}
    found = []
    for c in idni_digest.first_parent(tn, branch, max(START, now - SCAN_DAYS * 86400), now + 60):
        if c["sha"] not in known and c["ts"] >= START and is_feature(tn, c):
            found.append(c)
    if found:
        open_ = next((it for it in st["items"] if it.get("kind") == "testnet" and it.get("status") == "pending"), None)
        if open_ is None:
            open_ = {"id": f"testnet-{found[0]['sha'][:7]}", "kind": "testnet", "status": "pending", "shas": [], "titles": [],
                     "first": now}
            st["items"].append(open_)
        for c in found:
            open_["shas"].append(c["sha"])
            open_["titles"].append(title_of(c["subject"]))
        open_["last"] = now
    lp = path_of(LANG)
    if not os.path.isdir(lp):
        return
    pin = dp.lang_pin(tn, branch)
    old = st.get("lang_pin")
    if pin and old and pin != old:
        before = set(added(changelog(lp, old)))
        now_raw = added(changelog(lp, pin), raw=True)
        pairs = [(b, r) for b, r in zip(added(changelog(lp, pin)), now_raw) if b not in before]
        if pairs:
            st["items"].append({"id": f"lang-{pin[:8]}", "kind": "lang", "status": "pending", "shas": [pin], "from": old,
                                "titles": [b for b, _ in pairs][:40], "raw": [r for _, r in pairs][:40], "first": now, "last": now})
    if pin:
        st["lang_pin"] = pin
    tags = sorted(t for t in dp.git(lp, "tag", "-l").split() if TAG.match(t))
    if "lang_tags" not in st:
        st["lang_tags"] = tags          # the first look: releases from before are no news
    for t in tags:
        if t not in st["lang_tags"]:
            st["lang_tags"].append(t)
            text = section(changelog(lp, t), t) or section(changelog(lp, dp.default_branch(lp)), t)
            st["items"].append({"id": f"release-{t}", "kind": "release", "status": "pending", "tag": t, "shas": [],
                                "titles": [t], "changelog": text[:30000], "first": now, "last": now})


# ---------- when ----------
def local(t: float) -> datetime:
    import blog
    return blog.local(t)


def next_open(t: float) -> float:
    """t itself when it is inside the posting hours (German time), else the next opening."""
    d = local(t)
    if OPEN_HOUR <= d.hour < CLOSE_HOUR:
        return t
    day = d if d.hour < OPEN_HOUR else d + timedelta(days=1)
    return day.replace(hour=OPEN_HOUR, minute=0, second=0, microsecond=0).timestamp()


def went_out_on(st: dict, t: float) -> int:
    day = local(t).strftime("%Y-%m-%d")
    return sum(1 for it in st["items"] if it.get("at") and local(it["at"]).strftime("%Y-%m-%d") == day)


def slot(st: dict, now: float) -> float:
    """When the next feature post may go out: posting hours, the room between posts, at most MAX_PER_DAY a day."""
    import blog
    t = next_open(now + blog.gap_left(now))
    for _ in range(7):
        if went_out_on(st, t) < MAX_PER_DAY:
            return t
        t = next_open(local(t).replace(hour=CLOSE_HOUR, minute=0, second=0).timestamp() + 1)
    return t


# ---------- the article ----------
def facts(it: dict) -> dict:
    import news_article
    if it["kind"] == "testnet":
        tn = path_of(dp.TESTNET)
        return {"what this is": "New features IDNI merged into the Tau Net testnet's code (tau-testnet main), each with "
                                "IDNI's own title, the diff and IDNI's documentation changed with it.",
                "changes": [news_article.change_text(tn, s) for s in it["shas"][:news_article.CHANGES]],
                "links": links(it)}
    built = it["kind"] == "lang"
    return {"links": links(it), "what this is": ("The Tau Net testnet's build now uses a newer Tau Language (IDNI/tau-lang). These are the "
                             "lines IDNI's own Tau Language changelog lists as Added between the old and the new version "
                             "the testnet uses; they are what someone writing Tau rules on the testnet can now use.")
            if built else
            (f"IDNI released Tau Language {it['tag']} (IDNI/tau-lang). This is IDNI's own changelog of the release. "
             "Whether the Tau Net testnet uses this version yet is not said here, so do not say it does."),
            "changelog": ("\n".join("- " + b for b in it["titles"]) if built else it.get("changelog", ""))[:30000]}


def links(it: dict) -> list[dict]:
    """The exact changes an item tells of, {"url", "what"}: the article links them in its text and lists them."""
    import news_article
    if it["kind"] == "testnet":
        return news_article.commit_links(path_of(dp.TESTNET), it["shas"], dp.TESTNET)
    head = [{"url": sources(it)[0], "what": "Tau Language changes in the testnet's build" if it["kind"] == "lang"
             else f"Tau Language {it['tag']} release"},
            {"url": f"https://github.com/{LANG}/blob/main/CHANGELOG.md", "what": "IDNI's Tau Language changelog"}]
    lines = it.get("raw") or (it.get("changelog") or "").splitlines()
    return head + changelog_links([x for x in lines if x.lstrip().startswith("- ") or it.get("raw")])


def sources(it: dict) -> list[str]:
    if it["kind"] == "testnet":
        return [f"https://github.com/{dp.TESTNET}/commit/{s}" for s in it["shas"][:8]]
    if it["kind"] == "lang":
        return [f"https://github.com/{LANG}/compare/{it['from']}...{it['shas'][0]}"]
    return [f"https://github.com/{LANG}/releases/tag/{it['tag']}"]


def budget_left(now: float) -> bool:
    import ai_meter
    t = ai_meter.totals(ai_meter.month(now)) or {}
    return float(t.get("usd") or 0) < AI_MONTH_MAX


def write(it: dict, now: float, ask_=None, review_=None) -> tuple[str, dict]:
    """The article as an unlisted draft; (its id, its check)."""
    import blog
    import news_article
    on = local(now).strftime("%Y-%m-%d")
    base = f"{on}-" + {"testnet": "testnet-feature", "lang": "tau-language", "release": "tau-language-release"}[it["kind"]]
    aid, n = base, 2
    st = blog.state()
    taken = set(st.get("drafts") or {}) | {p["id"] for p in blog.posts()["posts"]}
    while aid in taken:
        aid, n = f"{base}-{n}", n + 1
    ln = links(it)
    d = {"id": it["id"], "feature": True, "end": int(now), "shas": it["shas"], "links": ln,
         "sources": [{"href": x["url"], "label": x["what"]} for x in ln[:12]]}
    f = facts(it)
    did = news_article.write_draft(d, path_of(dp.TESTNET), now, ask_, facts=f, aid=aid, retry=True)
    a = blog.read_json(os.path.join(blog.PUBLIC, "drafts", blog.state()["drafts"][did] + ".json"), {})
    # the second read against our house rules (editor.py), as for every draft: its notes go back to the writer once,
    # since nobody reads this one before it goes up (on 16 Nov the daily post's article of the same change had six)
    notes = (review_ or editor_review)(a)
    if notes:
        said = "; ".join(f'"{x["quote"]}": {x["fix"]}' if x.get("quote") else x["fix"] for x in notes)
        base = ask_ or news_article.ask
        again = lambda fx, note="": base(fx, "; ".join(x for x in (note, "an editor's notes against our rules: " + said) if x))  # noqa: E731
        did = news_article.write_draft(d, path_of(dp.TESTNET), now, again, facts=f, aid=aid, retry=True)
        a = blog.read_json(os.path.join(blog.PUBLIC, "drafts", blog.state()["drafts"][did] + ".json"), {})
        a["editor_read"] = notes   # what the second read found in the first answer, kept for the owner
        blog.write_json(os.path.join(blog.PUBLIC, "drafts", blog.state()["drafts"][did] + ".json"), a)
    return did, a.get("check") or {}


def editor_review(a: dict) -> list[dict]:
    try:
        import editor
        return editor.review(a)
    except Exception as e:  # noqa: BLE001 - no second read beats no article
        log.warning("editor: %s", e)
        return []


def publish(did: str, at: float, now: float) -> str:
    """On the blog with its one post now, or at `at` (blog.py's timed publish); what happened, in one line."""
    import blog
    if at > now + 60:
        st = blog.state()
        st.setdefault("publish_at", {})[did] = round(at)
        blog.write_json(blog.STATE, st)
        return f"goes up by itself at {local(at):%H:%M} German time ({local(at):%a %d.%m.})"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = blog.publish_cli(did, False, False, now=now)
    said = " ".join(out.getvalue().split())
    if rc != 0:
        raise RuntimeError(said)
    return "published now: " + said


# ---------- without the model ----------
def node_line(it: dict) -> str:
    pin = dp.pins().get(dp.TESTNET)
    tn = path_of(dp.TESTNET)
    if pin and all(dp.is_ancestor(tn, s, pin) for s in it["shas"]):
        return "Our node already runs it."
    return ""


def plain_text(it: dict) -> tuple[str, list[str]]:
    """The short post from IDNI's own title: Telegram (with the link to the change) and the X lines (no link)."""
    e = html.escape
    titles = it["titles"][:3]
    link = sources(it)[0] if len(it["shas"]) == 1 else f"https://github.com/{dp.TESTNET}/commits/main"
    tg = ["🛠 <b>New on the Tau Net testnet</b>", *(f"<b>{e(t)}</b>" for t in titles),
          " ".join(x for x in ("IDNI added this to the testnet's code.", node_line(it)) if x),
          f'<a href="{e(link)}">IDNI\'s change</a> · <a href="{SITE}/devpulse/">Build pulse on Tau HUD</a>', FOOT]
    x = [f"🛠 New on the Tau Net testnet: {titles[0]}", *titles[1:], "IDNI added this to the testnet's code."]
    return "\n\n".join(tg), x


def plain_post(it: dict) -> str:
    import alerts
    import idni_digest
    tg, lines = plain_text(it)
    said = []
    for out, text in ((alerts.Telegram(), tg), (alerts.X(), alerts.x_post(lines, foot=idni_digest.X_FOOT, keep=1))):
        if not out.enabled():
            said.append(f"{out.name}: not set up")
            continue
        ok, _, err = out.send_text(text, None)
        said.append(f"{out.name}: {'posted' if ok else 'not posted: ' + err}")
    return "; ".join(said)


def tell(text: str) -> None:
    try:
        import tickerwatch
        tickerwatch.tell(text)
    except Exception as e:  # noqa: BLE001
        log.warning("owner not told: %s", e)


NAMES = {"testnet": "New testnet feature", "lang": "Newer Tau Language in the testnet", "release": "Tau Language release"}


# ---------- each round of the blog loop ----------
def step(now: float | None = None, ask_=None, post_=None, review_=None) -> list[str]:
    """Called by blog.py's loop: finds, writes, publishes. Returns what it did (for the log and the tests)."""
    import blog
    if not ON:
        return []
    now = now or time.time()
    st = load()
    try:
        scan(st, int(now))
    except Exception as e:  # noqa: BLE001 - the clones may be fetching right now
        log.warning("feature scan: %s", e)
    did_ = []
    for it in st["items"]:
        if it.get("status") != "pending" or now - it.get("last", now) < SETTLE:
            continue
        if now - it.get("failed_at", 0) < RETRY:
            continue
        if next_open(now) > now:
            continue
        name = NAMES[it["kind"]] + ": " + "; ".join(it["titles"][:3])
        late = now - it["last"] >= SETTLE + FALLBACK
        why = ("no NEWS_AI_KEY" if not blog.AI_KEY else
               f"this month's Anthropic spend reached FEATURE_AI_MONTH_MAX=${AI_MONTH_MAX:g}" if not budget_left(now) else
               f"the writer failed for {FALLBACK / 3600:g} h ({it.get('error', '')[:200]})" if late and it.get("error") else "")
        if not why:
            try:
                did, chk = write(it, now, ask_, review_)
            except Exception as e:  # noqa: BLE001 - tried again after RETRY, then the plain post
                it["failed_at"], it["error"] = now, str(e)[:400]
                log.warning("feature %s: %s", it["id"], e)
                continue
            it["did"] = did
            url = blog.draft_url(blog.state(), did)
            if chk.get("unknown_numbers") or chk.get("hype"):
                why = f"its check still marks numbers {chk.get('unknown_numbers')} or words {chk.get('hype')}"
                tell(f"{name}\n\nThe article waits for you: {url}\nPublish after a read: up blog publish {did} --force")
            else:
                at = slot(st, now)
                try:
                    said = publish(did, at, now)
                except Exception as e:  # noqa: BLE001
                    it["failed_at"], it["error"] = now, str(e)[:400]
                    continue
                it.update(status="published", at=at)
                did_.append(did)
                tell(f"{name}\n\nThe article {said}.\n{SITE}/blog/?p={did}\n"
                     f"Take it back: up blog unpublish {did}" + ("" if at <= now + 60 else f" (before: up blog publish {did} --at=off)"))
                continue
        # without the article: a testnet feature still gets its short post, the rest goes to the owner only
        if it["kind"] == "testnet":
            if blog.gap_left(now) > 0 or went_out_on(st, now) >= MAX_PER_DAY:
                continue   # the next round; the plain post keeps to the room between posts and the day's number
            said = (post_ or plain_post)(it)
            it.update(status="plain", at=now, why=why)
            did_.append(it["id"])
            tell(f"{name}\n\nPosted the short version without an article ({said}), because {why}.")
        else:
            it.update(status="told", at=now, why=why)
            tell(f"{name}\n\nNo article ({why}). Nothing was posted.")
    st["items"] = [x for x in st["items"] if x.get("status") == "pending" or now - (x.get("at") or x.get("last") or now) < KEEP_DAYS * 86400]
    save(st)
    return did_


def status_lines(now: float | None = None) -> list[str]:
    now = now or time.time()
    st = load()
    out = [f"features: {'on' if ON else 'off (FEATURE_POSTS=false)'}; posts {OPEN_HOUR}:00–{CLOSE_HOUR}:00 German time, "
           f"{SETTLE / 60:g} min after the newest change, at most {MAX_PER_DAY} a day; the model while this month's "
           f"Anthropic spend is under ${AI_MONTH_MAX:g} ({'yes' if budget_left(now) else 'NO: plain posts only'})"]
    for it in st["items"][-8:]:
        when = local(it.get("at") or it.get("last") or now).strftime("%a %d.%m. %H:%M")
        out.append(f"  {it['id']}: {it['status']} {when}" + (f" · {it['did']}" if it.get("did") else "")
                   + (f" · {it['why']}" if it.get("why") else "") + (f" · error: {it['error'][:120]}" if it.get("error") and it["status"] == "pending" else ""))
        out.append("    " + "; ".join(it["titles"][:3])[:200])
    if not st["items"]:
        out.append("  nothing found since " + datetime.fromtimestamp(START, timezone.utc).strftime("%d.%m.%Y"))
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for line in status_lines():
        print(line)
