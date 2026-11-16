"""Unit test of new testnet features posted the same day (no network): what counts as a feature, the wait for
follow-up commits, the article on the blog at once within the posting hours, the plain post without the model, a newer
Tau Language in the testnet's build, and the daily IDNI post leaving these changes out.

Run: python test_feature_watch.py   (needs git)
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

TMP = tempfile.mkdtemp()
SRC = os.path.join(TMP, "clones", "IDNI__tau-testnet.git")     # a working repo where the bare clone would be
LSRC = os.path.join(TMP, "clones", "IDNI__tau-lang.git")
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), DEVPULSE_CLONES=os.path.join(TMP, "clones"),
                  NEWS_AI_KEY="test", TELEGRAM_BOT_TOKEN="", X_API_KEY="", BLOG_ART=os.path.join(TMP, "no-art"),
                  STATE_PATH=os.path.join(TMP, "alerts.json"), AI_USAGE_DIR=os.path.join(TMP, "ai"),
                  FEATURE_START="2026-11-16T00:00:00+00:00", POST_GAP_MINUTES="0", TZ_NAME="Europe/Berlin",
                  DEVPULSE_PINS_FILE=os.path.join(TMP, "no-pins"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import feature_watch as fw  # noqa: E402
import idni_digest as idg  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def at(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def run(repo, *a, ts=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.org", GIT_COMMITTER_NAME="Dev",
               GIT_COMMITTER_EMAIL="dev@example.org")
    if ts:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"@{ts} +0000"
    return subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True, env=env).stdout.strip()


def commit(repo, files, msg, ts):
    for path, text in files.items():
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)
    run(repo, "add", "-A")
    run(repo, "commit", "-q", "-m", msg, ts=ts)
    return run(repo, "rev-parse", "HEAD")


GOOD = {"title": {"en": "A rule change can now wait for a co-signer", "zh": "z", "ja": "j"},
        "dek": {"en": "On the Tau Net testnet a guarded rule changes only with a second signature.", "zh": "z", "ja": "j"},
        "why": [{"en": "For you: a stolen key alone cannot swap your rule.", "zh": "z", "ja": "j"},
                {"en": "For Tau Net: rules that guard themselves.", "zh": "z", "ja": "j"},
                {"en": "Limit: without the co-signer a change waits 1,000 blocks.", "zh": "z", "ja": "j"}],
        "body": {"en": "## What changed\nA guard.\n## What it gives you\nA co-signer.\n## Where it stops\nAfter 1,000 blocks.\n## What is still open\nMore.", "zh": "z", "ja": "j"},
        "x": "A rule change on the Tau Net testnet can now wait for a co-signer.", "card": {"line": "Guarded rules", "why": ["a", "b", "c"]}}
asked = []


def fake(answers):
    def f(facts, note=""):
        asked.append((facts, note))
        return json.loads(json.dumps(answers[min(len(asked), len(answers)) - 1]))
    return f


# --- the testnet repository ---
os.makedirs(SRC)
run(SRC, "init", "-q", "-b", "main")
commit(SRC, {"policy/guard.py": "GUARD = None\n", "Dockerfile.standalone": "ARG TAU_LANG_REF=aaaaaaa\n"}, "start", at("2026-11-12T08:00:00Z"))
old_feat = commit(SRC, {"policy/x.py": "X = 1\n"}, "feat(policy): judge transfers against the sender's own clause", at("2026-11-12T09:00:00Z"))

check(fw.title_of("feat: co-signed policy changes through a rule-change guard (#120)") == "Co-signed policy changes through a rule-change guard"
      and fw.title_of("feat(policy)!: judge transfers") == "Judge transfers" and fw.title_of("fix: header sync") is None
      and fw.title_of("Feature flags for tests") is None, "a feature is what IDNI titles feat:, in plain form")

T0 = at("2026-11-16T08:44:00Z")   # 09:44 German time
docs = commit(SRC, {"docs/guard.md": "Guard.\n"}, "feat(docs): explain the guard", T0 - 600)
fix = commit(SRC, {"policy/y.py": "Y = 1\n"}, "fix: a typo", T0 - 300)
feat = commit(SRC, {"policy/guard.py": "GUARD = 1000\n", "docs/guard.md": "Without the co-signer a change waits 1000 blocks.\n"},
              "feat: co-signed policy changes through a rule-change guard", T0)

asked.clear()
check(fw.step(T0 + 60, fake([GOOD])) == [] and not asked, "found, but it waits for follow-up commits first")
st = fw.load()
check([it["shas"] for it in st["items"]] == [[feat]] and st["items"][0]["titles"] == ["Co-signed policy changes through a rule-change guard"],
      "only the feature: not a fix, not docs alone, not one from before FEATURE_START")

g = idg.gather({"IDNI/tau-testnet": SRC}, {"IDNI/tau-testnet": "main"}, at("2026-11-16T00:00:00Z"), T0 + 3600, None, {})
check(feat not in [c["sha"] for c in g["changes"] + g["pending"] + g["house"]] and fix in [c["sha"] for c in g["pending"] + g["house"]],
      "the daily IDNI post leaves the feature out (its own post), keeps the rest")

out = fw.step(T0 + 50 * 60, fake([GOOD]))
bst = blog.state()
check(len(out) == 1 and out[0] == "2026-11-16-testnet-feature" and len(asked) == 1, "after the wait: one article, one model call")
posts = blog.posts()["posts"]
check(posts and posts[0]["id"] == out[0] and posts[0]["kind"] == "news" and out[0] in bst.get("announced", []),
      "on the blog at once with its one post (09:34 German time)")
check("judge transfers" not in json.dumps(asked[0][0]) and "rule-change guard" in json.dumps(asked[0][0])
      and posts[0]["sources"] == [{"href": f"https://github.com/IDNI/tau-testnet/commit/{feat}",
                                   "label": "feat: co-signed policy changes through a rule-change guard"}], "written from the feature's own change")
url = f"https://github.com/IDNI/tau-testnet/commit/{feat}"
check(f"]({url})" in posts[0]["body"]["en"] and "## The changes on GitHub" in posts[0]["body"]["en"]
      and f"]({url})" in posts[0]["body"]["zh"] and "GitHub 上的改动" in posts[0]["body"]["zh"],
      "the writer linked nothing: the exact change is listed at the end, in every language")
check(fw.load()["items"][0]["status"] == "published" and fw.step(T0 + 3 * 3600, fake([GOOD])) == [], "once")

# --- a second feature late in the evening: the next morning; hype twice: the plain post ---
T1 = at("2026-11-16T21:30:00Z")   # 22:30 German time
f2 = commit(SRC, {"policy/z.py": "Z = 1\n"}, "feat(policy): offers can expire", T1)
asked.clear()
check(fw.step(T1 + 3600, fake([GOOD])) == [] and not asked, "after 22:00 German time nothing goes out")
BAD = dict(GOOD, body=dict(GOOD["body"], en=GOOD["body"]["en"] + "\nIt is 40 times faster, finally."))
posted = []
out = fw.step(at("2026-11-17T07:05:00Z"), fake([BAD, BAD]), post_=lambda it: posted.append(it) or "telegram: posted")
check(len(asked) == 2 and "40" in asked[1][1] and "finally" in asked[1][1], "a marked answer: asked once more, naming what to leave out")
it = fw.load()["items"][-1]
check(posted and it["status"] == "plain" and "check" in it["why"], "still marked: the short plain post instead, the owner hears why")
tg, x = fw.plain_text(it)
check("Offers can expire" in tg and "Tau Net testnet" in tg and "github.com/IDNI/tau-testnet/commit/" + f2 in tg
      and x[0] == "🛠 New on the Tau Net testnet: Offers can expire", "the plain post: IDNI's own title, the link on Telegram only")

# --- without the model ---
f3 = commit(SRC, {"policy/w.py": "W = 1\n"}, "feat: rules can name a friend", at("2026-11-17T09:00:00Z"))
key, blog.AI_KEY = blog.AI_KEY, ""
posted.clear()
asked.clear()
fw.step(at("2026-11-17T09:10:00Z"), fake([GOOD]), post_=lambda it: posted.append(it) or "ok")
fw.step(at("2026-11-17T10:00:00Z"), fake([GOOD]), post_=lambda it: posted.append(it) or "ok")
check(posted and not asked and fw.load()["items"][-1]["why"] == "no NEWS_AI_KEY", "no key: the plain post, no model call")
blog.AI_KEY = key

# --- a newer Tau Language in the testnet's build ---
os.makedirs(LSRC)
run(LSRC, "init", "-q", "-b", "main")
l1 = commit(LSRC, {"CHANGELOG.md": "# Changelog\n## [v0.8.0](x)\n### Added\n- Old thing. (PRs: none / Commits: none)\n### Fixed\n- A fix.\n"}, "one", at("2026-11-10T09:00:00Z"))
l2 = commit(LSRC, {"CHANGELOG.md": "# Changelog\n## [v0.8.0](x)\n### Added\n- Old thing. (PRs: none / Commits: [a](b))\n- Sets of programs as terms. (PRs: [#7](https://github.com/IDNI/tau-lang/pull/7))\n### Fixed\n- A fix.\n- Another fix.\n"}, "two", at("2026-11-15T09:00:00Z"))
check(fw.added(open(os.path.join(LSRC, "CHANGELOG.md")).read()) == ["Old thing.", "Sets of programs as terms."], "the Added lines, without their links")
commit(SRC, {"Dockerfile.standalone": f"ARG TAU_LANG_REF={l1}\n"}, "build: pin tau-lang", at("2026-11-17T11:00:00Z"))
st = fw.load()
fw.scan(st, at("2026-11-17T11:05:00Z"))
check(st.get("lang_pin") == l1 and not any(i["kind"] == "lang" for i in st["items"]) and "lang_tags" in st, "the first look only notes the pin")
commit(SRC, {"Dockerfile.standalone": f"ARG TAU_LANG_REF={l2}\n"}, "build: bump tau-lang", at("2026-11-18T09:00:00Z"))
fw.scan(st, at("2026-11-18T09:05:00Z"))
lang = [i for i in st["items"] if i["kind"] == "lang"]
check(len(lang) == 1 and lang[0]["titles"] == ["Sets of programs as terms."], "the build moved: what IDNI's changelog added in between")
ln = fw.links(lang[0])
check(ln[0]["url"] == f"https://github.com/IDNI/tau-lang/compare/{l1}...{l2}" and any(x["url"].endswith("/pull/7") for x in ln),
      "a Tau Language item links the compare view, the changelog and the pull requests its lines name")
run(LSRC, "tag", "v0.8.0")
fw.scan(st, at("2026-11-18T09:10:00Z"))
rel = [i for i in st["items"] if i["kind"] == "release"]
check(len(rel) == 1 and "Sets of programs" in rel[0]["changelog"] and "Another fix" in rel[0]["changelog"], "a new release tag: its changelog section")
fw.save(st)
check("Sets of programs" in "\n".join(fw.status_lines(at("2026-11-18T09:10:00Z"))), "status lines read")

print("FAILED" if failed else "all ok")
sys.exit(1 if failed else 0)
