"""Development pulse of the Tau software, for tauhud.com/devpulse/.

Keeps a bare, blob-less clone of each public IDNI repository below (git only,
no GitHub API needed for the history) and writes /public/devpulse.json, served
by Caddy at https://node.tauhud.com/devpulse.json:

  - the newest commits with the code areas they touched
  - commits per week for a year, per day for 90 days
  - which code areas moved in the last 4 and 12 weeks
  - tags, and how far each repo's main is ahead of the commit our node runs
  - chain restarts our relay saw, so the page can lay commits beside them
  - news: what landed on tau-testnet main in the last two weeks as news headlines (en, zh, ja) for the news line on
    tauhud.com: a language model reads each new merge once (message, branch commits, diff) and writes what it means,
    groups what belongs together and skips housekeeping; each item says whether our node runs it yet
  - sync: whether our node keeps up with IDNI: how far tau-testnet main is ahead of our pin, whether IDNI's own
    build still uses our tau-lang commit, and whether each of our node patches still applies to the newest main
    (checked once per new upstream commit on a shallow checkout; `up` prints it)
  - open issues and pull requests, from the public GitHub search API (no token;
    a few requests an hour, far below its limit; left out when it refuses)

Only public data and neutral numbers: no ranking of people, author names are
counted (how many people committed) but not published.

  python devpulse.py                 run, refresh every DEVPULSE_SECONDS (default 30 min)
  python devpulse.py --once OUT      one pass into OUT (used for the page's built-in snapshot)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger("tau-devpulse")

REPOS = [r.strip() for r in os.environ.get("DEVPULSE_REPOS", "IDNI/tau-testnet,IDNI/tau-lang").split(",") if r.strip()]
CLONES = os.environ.get("DEVPULSE_CLONES", "/state/devpulse")
PUBLIC_PATH = os.path.join(os.environ.get("PUBLIC_DIR", "/public"), "devpulse.json")
EVERY = float(os.environ.get("DEVPULSE_SECONDS", 1800))
API_EVERY = float(os.environ.get("DEVPULSE_API_SECONDS", 3600))
RELAY_HTTP = os.environ.get("RELAY_HTTP", "").rstrip("/")
PINS_FILE = os.environ.get("DEVPULSE_PINS_FILE", "/pins/Dockerfile")   # infra/node/Dockerfile: the commits our node is built from
RECENT = 30          # newest commits listed per repo
WEEKS = 52
DAYS = 90
UA = {"User-Agent": "tauhud-devpulse/1 (+https://tauhud.com)", "Accept": "application/vnd.github+json"}
# areas below these folders are counted one level deeper (src/boolean_algebras rather than src)
DEEP = {"src", "tests", "bindings", "scripts", "networks"}
NEWS_DAYS = int(os.environ.get("DEVPULSE_NEWS_DAYS", 14))
NEWS_MAX = 20
PATCHES_DIR = os.environ.get("DEVPULSE_PATCHES", "/pins/patches")   # infra/node/patches, applied in the Dockerfile's order
REMOTE = os.environ.get("DEVPULSE_REMOTE", "https://github.com/{repo}.git")
# commit kinds that never make news: housekeeping around the code, not the code the testnet runs
QUIET_KINDS = {"docs", "doc", "test", "tests", "ci", "chore", "style"}
QUIET_FILE = re.compile(r"(^|/)(docs?|tests?)/|^\.github/|\.md$|^LICENSE|^NOTICE")


def git(repo_dir: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo_dir, *args], check=True, capture_output=True, text=True, timeout=600).stdout


def sync(repo: str) -> str:
    """Clone once (history and file names only, no file contents), then fetch."""
    path = os.path.join(CLONES, repo.replace("/", "__") + ".git")
    if not os.path.isdir(path):
        os.makedirs(CLONES, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--bare", "--filter=blob:none", REMOTE.format(repo=repo), path],
                       check=True, capture_output=True, text=True, timeout=900)
    else:
        git(path, "fetch", "--quiet", "--prune", "--tags", "origin", "+refs/heads/*:refs/heads/*")
    return path


def area(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "root files"
    if parts[0] in DEEP and len(parts) > 2:
        return parts[0] + "/" + parts[1]
    return parts[0]


def default_branch(path: str) -> str:
    try:
        return git(path, "symbolic-ref", "--short", "HEAD").strip()
    except subprocess.CalledProcessError:
        return "main"


def read_log(path: str, branch: str, since: int) -> list[dict]:
    """Commits on the default branch since a time, newest first: sha, time, subject, author (kept local), areas."""
    out = git(path, "log", branch, f"--since=@{since}", "--no-renames", "--name-only",
              "--format=%x1e%H%x1f%ct%x1f%ae%x1f%s")
    commits = []
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        head, _, files = chunk.partition("\n")
        sha, ct, author, subject = (head.split("\x1f") + ["", "", "", ""])[:4]
        names = [f for f in files.split("\n") if f.strip()]
        areas = Counter(area(f) for f in names)
        commits.append({"sha": sha, "ts": int(ct), "author": author.lower(), "title": subject.strip(),
                        "areas": [a for a, _ in areas.most_common()]})
    return commits


def monday(ts: int) -> int:
    d = datetime.fromtimestamp(ts, timezone.utc).date()
    d -= timedelta(days=d.weekday())
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def day0(ts: int) -> int:
    return ts - ts % 86400


def pins() -> dict:
    """The tau-testnet and tau-lang commits our node is built from."""
    found = {}
    try:
        with open(PINS_FILE, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*ARG\s+(TAU_TESTNET_REF|TAU_LANG_REF)=([0-9a-f]{7,40})", line)
                if m:
                    found[m.group(1)] = m.group(2)
    except OSError:
        pass
    env = os.environ.get("TAU_TESTNET_REF", "").strip()
    if re.fullmatch(r"[0-9a-f]{7,40}", env):
        found["TAU_TESTNET_REF"] = env
    return {"IDNI/tau-testnet": found.get("TAU_TESTNET_REF"), "IDNI/tau-lang": found.get("TAU_LANG_REF")}


def repo_pulse(repo: str, path: str, now: int, pin: str | None) -> dict:
    branch = default_branch(path)
    week_start = monday(now) - (WEEKS - 1) * 7 * 86400
    year = read_log(path, branch, week_start)
    weeks = [0] * WEEKS
    days = [0] * DAYS
    first_day = day0(now) - (DAYS - 1) * 86400
    for c in year:
        w = (monday(c["ts"]) - week_start) // (7 * 86400)
        if 0 <= w < WEEKS:
            weeks[w] += 1
        d = (day0(c["ts"]) - first_day) // 86400
        if 0 <= d < DAYS:
            days[d] += 1
    c4 = Counter()
    c12 = Counter()
    last = {}
    for c in year:
        for a in c["areas"]:
            last[a] = max(last.get(a, 0), c["ts"])
            if c["ts"] >= now - 28 * 86400:
                c4[a] += 1
            if c["ts"] >= now - 84 * 86400:
                c12[a] += 1
    areas = sorted(({"path": a, "c4": c4[a], "c12": n, "last": last[a]} for a, n in c12.items()),
                   key=lambda r: (-r["c12"], r["path"]))[:24]
    head_line = git(path, "log", "-1", branch, "--format=%H%x1f%ct%x1f%s").strip().split("\x1f")
    head = {"sha": head_line[0], "ts": int(head_line[1]), "title": head_line[2]}
    tags = []
    for line in git(path, "for-each-ref", "--sort=-creatordate", "--count=12", "refs/tags",
                    "--format=%(refname:short)%1f%(creatordate:unix)%1f%(objectname)").splitlines():
        name, ts, sha = (line.split("\x1f") + ["", "", ""])[:3]
        if name:
            tags.append({"name": name, "ts": int(ts or 0), "sha": sha})
    runs = None
    if pin:
        try:
            full = git(path, "rev-parse", "--verify", "--quiet", pin + "^{commit}").strip()
            ts, title = git(path, "log", "-1", full, "--format=%ct%x1f%s").strip().split("\x1f", 1)
            ahead = int(git(path, "rev-list", "--count", f"{full}..{branch}").strip())
            runs = {"sha": full, "ts": int(ts), "title": title, "ahead": ahead}
        except (subprocess.CalledProcessError, ValueError):
            runs = {"sha": pin, "ts": None, "title": "", "ahead": None}
    recent = [{k: c[k] for k in ("sha", "ts", "title", "areas")} for c in year[:RECENT]]
    for c in recent:
        c["areas"] = c["areas"][:3]
    return {
        "repo": repo, "url": f"https://github.com/{repo}", "branch": branch, "head": head, "runs": runs,
        "weeks": weeks, "week0": week_start, "days": days, "day0": first_day,
        "commits_4w": sum(1 for c in year if c["ts"] >= now - 28 * 86400),
        "commits_12w": sum(1 for c in year if c["ts"] >= now - 84 * 86400),
        "commits_52w": len(year),
        "people_12w": len({c["author"] for c in year if c["ts"] >= now - 84 * 86400}),
        "active_weeks_12": sum(1 for n in weeks[-12:] if n),
        "areas": areas, "tags": tags, "recent": recent,
    }


def search_count(q: str) -> int | None:
    url = "https://api.github.com/search/issues?per_page=1&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return int(json.load(r)["total_count"])
    except Exception as e:  # noqa: BLE001 - rate limit or network: leave the number out
        log.info("GitHub search %s: %s", q, e)
        return None


def tracker(repo: str, now: int) -> dict:
    since = datetime.fromtimestamp(now - 30 * 86400, timezone.utc).strftime("%Y-%m-%d")
    out = {
        "issues_open": search_count(f"repo:{repo} is:issue is:open"),
        "prs_open": search_count(f"repo:{repo} is:pr is:open"),
        "closed_30d": search_count(f"repo:{repo} is:closed closed:>={since}"),
        "opened_30d": search_count(f"repo:{repo} created:>={since}"),
        "at": now,
    }
    return out if any(v is not None for k, v in out.items() if k != "at") else {}


def restarts() -> list[dict]:
    if not RELAY_HTTP:
        return []
    try:
        with urllib.request.urlopen(RELAY_HTTP + "/uptime", timeout=20) as r:
            j = json.load(r)
        return [{"at": x.get("new_block1_ts") or x.get("detected_at"), "old_tip": x.get("old_tip")} for x in j.get("restarts", [])]
    except Exception as e:  # noqa: BLE001
        log.info("relay /uptime: %s", e)
        return []


# ---------- news and sync: what landed on tau-testnet main, and whether our node keeps up ----------
TESTNET = "IDNI/tau-testnet"


def headline(subject: str) -> dict | None:
    """A commit title as one plain news line: 'merge: fix(#78) header sync into main' -> fix, 'Header sync', [78].
    None for housekeeping (docs, tests, CI, merging main into a branch)."""
    t = re.sub(r"^merge:\s*", "", subject.strip(), flags=re.I)
    if re.match(r"(merge (branch|remote)|main into\b|revert \"merge)", t, re.I):
        return None
    m = re.match(r"([A-Za-z]+)(?:\(([^)]*)\)!?:?|!?:)\s*(.+)", t)   # "fix(net): …", "feat: …", IDNI's "fix(#78) …"
    kind, scope, rest = (m.group(1).lower(), m.group(2) or "", m.group(3)) if m else ("", "", t)
    if kind in QUIET_KINDS:
        return None
    issues = sorted({int(x) for x in re.findall(r"#(\d+)", scope + " " + rest)})
    rest = re.sub(r"\s*\(#\d+\)\s*$", "", rest)            # a squash merge's "(#93)"
    rest = re.sub(r"\s+into (main|master)$", "", rest).strip().rstrip(".")
    if len(rest) < 4:
        return None
    fix = kind == "fix" or bool(re.match(r"fix(es|ed)?\b", rest, re.I))
    if not m and fix:   # "Fix crash on start": the line already says "fixed"
        rest = re.sub(r"^fix(es|ed)?:?\s+", "", rest, flags=re.I) or rest
    if len(rest) > 90:
        rest = rest[:88].rsplit(" ", 1)[0] + "…"
    return {"kind": "fix" if fix else "change", "text": rest[0].upper() + rest[1:], "issues": issues}


def is_ancestor(path: str, sha: str, of: str) -> bool:
    return subprocess.run(["git", "-C", path, "merge-base", "--is-ancestor", sha, of], capture_output=True).returncode == 0


def changed_files(path: str, sha: str) -> list[str]:
    """Files a commit changed against its first parent (trees only, no file contents needed)."""
    try:
        return [f for f in git(path, "diff", "--name-only", "--no-renames", sha + "^1", sha).splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        return []


def candidates(repo: str, path: str, branch: str, now: int, pin: str | None) -> list[dict]:
    """The commits that may make news: each merge (or direct commit) on main in the last NEWS_DAYS days, newest
    first, housekeeping left out. Their titles are never published as they are; headlines() writes the news."""
    out = git(path, "log", "--first-parent", branch, f"--since=@{now - NEWS_DAYS * 86400}",
              "--format=%H%x1f%ct%x1f%s%x1f%b%x1e")
    items = []
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        sha, ct, subject, body = (chunk.strip("\n").split("\x1f") + ["", "", "", ""])[:4]
        if re.match(r"merge pull request #\d+", subject, re.I):   # GitHub's own merge title: the PR title is the next line
            subject = next((x for x in body.splitlines() if x.strip()), subject)
        h = headline(subject)
        if not h:
            continue
        files = changed_files(path, sha)
        if files and all(QUIET_FILE.search(f) for f in files):
            continue
        items.append({"sha": sha, "ts": int(ct), **h, "url": f"https://github.com/{repo}/commit/{sha}",
                      "runs": bool(pin) and is_ancestor(path, sha, pin)})
        if len(items) >= NEWS_MAX:
            break
    return items


# ---------- headlines: what the new commits mean, written once per commit by a language model ----------
NEWS_AI_KEY = (os.environ.get("NEWS_AI_KEY") or os.environ.get("CHAT_AI_KEY") or "").strip()
NEWS_AI_MODEL = os.environ.get("NEWS_AI_MODEL", "").strip() or "claude-sonnet-5-5"
HEADLINES = os.environ.get("DEVPULSE_HEADLINES", "") or os.path.join(CLONES, "headlines.json")
RETRY_AFTER = 2 * 3600
NEWS_VERSION = 2   # raise when the instructions change: every kept headline is written anew once
NEWS_SYSTEM = """You write the news line of Tau HUD (tauhud.com), an unofficial community dashboard for Tau Testnet Alpha, \
made by people not affiliated with IDNI. Its readers are curious people, not developers: they follow the testnet, \
send test transactions or play games on it, and many have never read its code. You get the commits IDNI just merged \
into the testnet's code: their messages, the commits of merged branches, the files changed, part of the diff, and \
titles of issues they name.

Your job is to find the point of each change and say it the way a good newspaper would: what is different now, and \
why it matters for the testnet, its safety, its users or the people running nodes. Rules:
- Only facts the input shows. Never guess motives, dates, releases, numbers or effects the input does not show. The \
point of a change is often written in its message ("a proposer could ...", "so that ...", "before, ..."): use it.
- Plain words only. Never use code names, file names, function names, stream names (like i2, o5, i13), receipt \
reasons, exit codes, package names, flags or version numbers. Say "rule checks", "signatures", "nodes", "blocks", \
"a block maker", "syncing", "new nodes joining", "the node restarts itself".
- No hype or marketing words (huge, major, game-changing, finally, exciting, revolutionary), no price talk, no \
exclamation marks, no emoji, no commit hashes, no names of people.
- headline: at most 70 characters, a real news headline with subject and verb, present tense, sentence case. It says \
what happened in the world, not what the code does internally. Do not start with "IDNI" (the line adds it).
  Bad: "Block apply refuses rule offers that fail clause checks". Good: "Block makers can no longer slip unchecked rules into blocks".
  Bad: "Node exits with code 1 when its network thread dies". Good: "A node that loses its network now stops instead of running blind".
- tip: one or two short sentences, at most 140 characters: the background or the practical effect, also in plain words.
- Several commits that serve one purpose (for example the same kind of check added in three places) become ONE item \
whose headline names that purpose. Prefer fewer, clearer items.
- Skip changes nobody using the testnet or running a node would notice: refactors, internal tooling, tests, docs, \
CI, build scripts, dependency bumps without a visible effect.
- zh: Simplified Chinese, ja: Japanese, same meaning, natural news wording; keep Tau, tau-testnet, IDNI, AGRS in Latin letters.
- kind: "fix" when it repairs something that was broken or closes a hole, else "change".

Answer with JSON only, no other text:
{"items":[{"commits":["<first 7 letters of each commit>"],"kind":"fix","headline":{"en":"","zh":"","ja":""},\
"tip":{"en":"","zh":"","ja":""}}],"skip":["<first 7 letters>"]}"""


def issue_title(repo: str, n: int) -> str:
    try:
        url = f"https://api.github.com/repos/{repo}/issues/{n}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return str(json.load(r).get("title") or "")
    except Exception:  # noqa: BLE001 - rate limit or network: the commit speaks for itself
        return ""


def commit_context(repo: str, path: str, sha: str, limit: int = 12000) -> str:
    """What a model needs to understand one commit on main: message, the commits of a merged branch, files, diff."""
    msg = git(path, "log", "-1", "--format=%B", sha).strip()
    parents = git(path, "log", "-1", "--format=%P", sha).split()
    parts = [f"### commit {sha[:7]} ({datetime.fromtimestamp(int(git(path, 'log', '-1', '--format=%ct', sha)), timezone.utc):%Y-%m-%d})", msg]
    if len(parents) > 1:
        branch = git(path, "log", "--no-merges", "--format=- %s%n%b", f"{parents[0]}..{parents[1]}", "-40").strip()
        parts += ["Commits of the merged branch:", branch[:4000]]
    issues = sorted({int(x) for x in re.findall(r"#(\d+)", msg)})[:3]
    for n in issues:
        t = issue_title(repo, n)
        if t:
            parts.append(f"Issue #{n}: {t}")
    if parents:
        try:
            parts += ["Files changed:", git(path, "diff", "--stat=120", "--no-renames", parents[0], sha).strip()[:3000]]
            diff = git(path, "diff", "--no-renames", "-U2", parents[0], sha, "--", ".",
                       ":(exclude)tests", ":(exclude)docs", ":(exclude)*.md")
            parts += ["Diff (code only, may be cut):", diff[:limit]]
        except subprocess.CalledProcessError as e:
            parts.append(f"(diff not available: {e})")
    return "\n".join(parts)


def ask_ai(prompt: str) -> dict:
    body = json.dumps({"model": NEWS_AI_MODEL, "max_tokens": 4000, "system": NEWS_SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": NEWS_AI_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.load(r)
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the answer: " + text[:200])
    return json.loads(m.group(0))


def _lines(d, cap: int) -> dict | None:
    """{"en", "zh", "ja"}, each a short single line; None when one is missing."""
    if not isinstance(d, dict):
        return None
    out = {}
    for k in ("en", "zh", "ja"):
        v = " ".join(str(d.get(k) or "").split())
        if not v or len(v) > cap:
            return None
        out[k] = v
    return out


def load_headlines() -> dict:
    try:
        with open(HEADLINES, encoding="utf-8") as f:
            j = json.load(f)
        if j.get("version") != NEWS_VERSION:   # new instructions: write everything in the window anew
            return {"seen": {}, "items": [], "failed_at": 0, "version": NEWS_VERSION}
        return {"seen": dict(j.get("seen") or {}), "items": list(j.get("items") or []), "failed_at": j.get("failed_at") or 0,
                "version": NEWS_VERSION}
    except (OSError, ValueError):
        return {"seen": {}, "items": [], "failed_at": 0, "version": NEWS_VERSION}


_ai_state = {"status": "off"}


def headlines(repo: str, path: str, cands: list[dict], now: int, pin: str | None) -> list[dict]:
    """News items for the line: new candidate commits go to the model once (grouped, skipped or written up); the
    answers are kept in HEADLINES, so a commit is never written twice. Without a key nothing is published: a raw
    commit title is not news."""
    st = load_headlines()
    new = [c for c in cands if c["sha"] not in st["seen"]]
    if not NEWS_AI_KEY:
        _ai_state["status"] = "no key (NEWS_AI_KEY or CHAT_AI_KEY in infra/.env)"
    elif new and now - st["failed_at"] >= RETRY_AFTER:
        try:
            prompt = (f"New commits on {repo} main (the code Tau Testnet Alpha runs), oldest first:\n\n" +
                      "\n\n".join(commit_context(repo, path, c["sha"]) for c in reversed(new)))
            out = ask_ai(prompt[:150000])
            by7 = {c["sha"][:7]: c for c in new}
            for it in out.get("items") or []:
                shas = [by7[x[:7]]["sha"] for x in (it.get("commits") or []) if str(x)[:7] in by7]
                head, tip = _lines(it.get("headline"), 90), _lines(it.get("tip"), 200)
                if not shas or not head or not tip:
                    continue
                st["items"].append({"id": shas[0], "shas": shas, "ts": max(by7[x[:7]]["ts"] for x in shas),
                                    "kind": "fix" if it.get("kind") == "fix" else "change", "headline": head, "tip": tip,
                                    "url": f"https://github.com/{repo}/commit/{max(shas, key=lambda x: by7[x[:7]]['ts'])}"})
            for c in new:   # written up, skipped or passed over: decided once
                st["seen"][c["sha"]] = c["ts"]
            st["failed_at"] = 0
            _ai_state["status"] = "on"
        except Exception as e:  # noqa: BLE001 - try again in two hours, nothing half-written is kept
            log.warning("headlines: %s", e)
            st["failed_at"] = now
            _ai_state["status"] = f"failed: {str(e)[:160]}"
    else:
        _ai_state["status"] = "on" if not st["failed_at"] else "waiting to retry after a failed try"
    keep = now - NEWS_DAYS * 86400
    st["items"] = [i for i in st["items"] if i["ts"] >= keep]
    st["seen"] = {k: v for k, v in st["seen"].items() if v >= now - 60 * 86400}
    os.makedirs(os.path.dirname(HEADLINES) or ".", exist_ok=True)
    write_atomic(HEADLINES, json.dumps(st))
    items = sorted(st["items"], key=lambda i: -i["ts"])
    for i in items:
        i["runs"] = bool(pin) and all(is_ancestor(path, x, pin) for x in i["shas"])
    return items


def lang_pin(path: str, branch: str) -> str | None:
    """The tau-lang commit IDNI's own standalone image is built from, on tau-testnet main."""
    try:
        m = re.search(r"ARG\s+TAU_LANG_REF=([0-9a-f]{7,40})", git(path, "show", f"{branch}:Dockerfile.standalone"))
        return m.group(1) if m else None
    except subprocess.CalledProcessError:
        return None


def patch_order() -> list[str]:
    try:
        with open(PINS_FILE, encoding="utf-8") as f:
            return re.findall(r"python3 -I /patches/([\w.-]+\.py) /src", f.read())
    except OSError:
        return []


_patched: dict = {}


def check_patches(repo: str, branch: str, head: str) -> dict | None:
    """Apply our node patches, in the Dockerfile's order, to a fresh shallow checkout of upstream main, once per
    new upstream commit (or changed patch). A patch fails when the source no longer matches what it expects; the
    ones after it are not tried, since they build on it."""
    order = patch_order()
    if not order or not os.path.isdir(PATCHES_DIR):
        return None
    stamp = head
    for name in order:
        try:
            stamp += ":%d" % os.stat(os.path.join(PATCHES_DIR, name)).st_mtime_ns
        except OSError:
            stamp += ":missing"
    if _patched.get("stamp") == stamp:
        return _patched["result"]
    os.makedirs(CLONES, exist_ok=True)
    results, checked = [], head
    with tempfile.TemporaryDirectory(dir=CLONES, prefix="patch-") as tmp:
        src = os.path.join(tmp, "src")
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch, REMOTE.format(repo=repo), src],
                       check=True, capture_output=True, text=True, timeout=900)
        checked = git(src, "rev-parse", "HEAD").strip()
        failed = False
        for name in order:
            if failed:
                results.append({"name": name, "ok": None, "error": "not tried after the failure above"})
                continue
            p = subprocess.run([sys.executable, "-I", os.path.join(PATCHES_DIR, name), src],
                               capture_output=True, text=True, timeout=300)
            err = next((x.strip() for x in reversed(p.stderr.splitlines()) if x.strip()), "") if p.returncode else ""
            results.append({"name": name, "ok": p.returncode == 0, "error": err[:240]})
            failed = p.returncode != 0
    result = {"sha": checked, "ok": all(r["ok"] for r in results), "results": results}
    _patched.update(stamp=stamp, result=result)
    return result


def sync_state(repo: str, path: str, branch: str, pins_: dict) -> dict:
    pin = pins_.get(TESTNET)
    head = git(path, "rev-parse", branch).strip()
    out = {"pin": pin, "head": head, "ahead": None, "behind": []}
    try:
        full = git(path, "rev-parse", "--verify", "--quiet", pin + "^{commit}").strip() if pin else ""
    except subprocess.CalledProcessError:
        full = ""
    if full:
        out["pin"] = full
        out["ahead"] = int(git(path, "rev-list", "--count", f"{full}..{branch}").strip())
        for line in git(path, "log", "--first-parent", f"{full}..{branch}", "-8", "--format=%H%x1f%ct%x1f%s").splitlines():
            sha, ct, subject = (line.split("\x1f") + ["", "", ""])[:3]
            h = headline(subject)
            out["behind"].append({"sha": sha, "ts": int(ct or 0), "text": h["text"] if h else subject})
    ours, idni = pins_.get("IDNI/tau-lang"), lang_pin(path, branch)
    lang = {"ours": ours, "idni": idni,
            "same": bool(ours and idni) and (ours.startswith(idni) or idni.startswith(ours))}
    try:
        patches = check_patches(repo, branch, head)
    except Exception as e:  # noqa: BLE001 - a failed checkout is reported, never fatal
        log.warning("patch check: %s", e)
        patches = None
    ok = out["ahead"] == 0 and lang["same"] and (patches is None or patches["ok"])
    return {"testnet": out, "tau_lang": lang, "patches": patches, "ok": ok}


def build(now: int | None = None, trackers: dict | None = None) -> dict:
    now = int(now or time.time())
    pin = pins()
    repos, paths = [], {}
    for repo in REPOS:
        try:
            paths[repo] = sync(repo)
            repos.append(repo_pulse(repo, paths[repo], now, pin.get(repo)))
        except Exception as e:  # noqa: BLE001 - one repo failing must not hide the other
            log.warning("%s: %s", repo, e)
    for r in repos:
        r["tracker"] = (trackers or {}).get(r["repo"], {})
    data = {"v": 1, "generated_at": now, "source": "git", "repos": repos, "restarts": restarts()}
    tn = next((r for r in repos if r["repo"] == TESTNET), None)
    if tn:
        try:
            full = (tn.get("runs") or {}).get("sha")
            pin_full = full if full and len(full) == 40 else None
            cands = candidates(TESTNET, paths[TESTNET], tn["branch"], now, pin_full)
            data["news"] = headlines(TESTNET, paths[TESTNET], cands, now, pin_full)
            data["news_ai"] = _ai_state["status"]
            data["sync"] = sync_state(TESTNET, paths[TESTNET], tn["branch"], pin)
        except Exception as e:  # noqa: BLE001
            log.warning("news/sync: %s", e)
    return data


def write_atomic(path: str, text: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if len(sys.argv) == 3 and sys.argv[1] == "--once":
        now = int(time.time())
        data = build(now, {r: tracker(r, now) for r in REPOS})
        write_atomic(sys.argv[2], json.dumps(data, separators=(",", ":")))
        print(f"wrote {sys.argv[2]}: {', '.join(r['repo'] for r in data['repos'])}")
        return
    trackers, api_at = {}, 0.0
    while True:
        started = time.time()
        try:
            if started - api_at >= API_EVERY:
                fresh = {r: tracker(r, int(started)) for r in REPOS}
                trackers.update({r: v for r, v in fresh.items() if v})
                api_at = started
            data = build(int(started), trackers)
            if data["repos"]:
                write_atomic(PUBLIC_PATH, json.dumps(data, separators=(",", ":")))
                sy = data.get("sync") or {}
                log.info("devpulse.json: %s; sync %s", ", ".join(f"{r['repo']} {r['head']['sha'][:7]}" for r in data["repos"]),
                         "ok" if sy.get("ok") else json.dumps(sy)[:300])
        except Exception as e:  # noqa: BLE001
            log.warning("pass failed: %s", e)
        time.sleep(max(60.0, EVERY - (time.time() - started)))


if __name__ == "__main__":
    main()
