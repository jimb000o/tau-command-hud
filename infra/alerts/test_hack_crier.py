"""Unit test of the hack of the week's posts (hack_crier.py), no network: the texts of a held and a missed replay
(X without a link and within 280, Telegram caption within 1024, what the window does not protect always in), the
picture, one post per run, a finding only to the owner with a ready IDNI issue, skipped runs only told privately.

Run: python test_hack_crier.py
"""
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="", CHAT_AI_KEY="",
                  TELEGRAM_BOT_TOKEN="", X_API_KEY="", HACK_CRIER="true")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relay"))
import blog  # noqa: E402
import hack_crier as hc  # noqa: E402
import hackweek  # noqa: E402  (the relay's catalogue: the texts come from it)

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T0 = 1794477600   # Thursday 12 November 2026, 11:00 German time
F = "8a91f2" + "1" * 86 + "c03e"
P = "8a91f2" + "2" * 86 + "c03e"
SNAP = {"enabled": True, "ready": True, "window_minutes": 30,
        "hacks": {k: {x: v[x] for x in ("name", "news", "how", "rule", "rule_what", "not")} for k, v in hackweek.HACKS.items()},
        "wallets": {"friend": {"address": F, "short": hackweek.short(F)}, "poisoner": {"address": P, "short": hackweek.short(P)}},
        "next": {"t0": T0 + 7 * 86400, "hack": "poisoning", "ship_near": None}}
HELD = {"id": "2026-11-12-poisoning", "hack": "poisoning", "t0": T0, "status": "done", "result": "held", "settled": T0 + 2400,
        "why": "the payment came back to the victim", "outcome": {"twin": "confirmed", "victim": {"status": "retracted"}},
        "steps": {"slip": {"t": T0 + 300, "ok": True}, "catch": {"t": T0 + 900, "ok": True},
                  "impostor": {"ok": False, "right": True, "code": "NOT_RETRACTABLE_SENDER"}}}

t = hc.texts(HELD, SNAP)
check("8a91f2…c03e" in t["telegram"] and "came back after 10 minutes" in t["telegram"], "Telegram: the lookalike and the take-back after 10 minutes")
check("NOT protect" in t["telegram"] and "only helps if you notice" in t["telegram"], "Telegram: what the window does not protect")
check("only the sender" in t["telegram"], "Telegram: the poisoner's own take-back was refused")
check(len(t["telegram"]) <= 1024, f"Telegram caption within 1024 ({len(t['telegram'])})")
check("http" not in t["x"] and "tauhud" not in t["x"].lower() and len(t["x"]) <= 280, f"X: no link, within 280 ({len(t['x'])})")
check("Without: gone" in t["x"] and "notice in time" in t["x"], "X: why it matters and its limit")
check(not any(w in (t["telegram"] + t["x"]).lower() for w in ("idni's fault", "testnet failed", "moon", "100x")), "no blame, no hype")
pic = hc.picture(t["card"], os.environ.get("HACK_PIC", os.path.join(TMP, "hack.jpg")))
from PIL import Image  # noqa: E402
check(Image.open(pic).size == (1600, 900), "the picture: 1600 x 900")

MISSED = {**HELD, "result": "missed", "id": "2026-11-19-poisoning", "why": "the take-back was not in a block before the release"}
m = hc.texts(MISSED, SNAP)
check("too late" in m["x"] and "on our timing" in m["telegram"], "missed: told plainly, as our timing")

# the loop: one post per run, a finding only privately, skipped only privately
POSTS, TELLS = [], []
hc.post = lambda tt, p: POSTS.append(tt) or ["telegram: posted", "x: posted"]
hc.tell = lambda text: TELLS.append(text) or (True, "")
FIND = {"id": "2026-11-26-poisoning", "hack": "poisoning", "t0": T0 + 14 * 86400, "status": "done", "result": "finding",
        "findings": [{"t": T0 + 14 * 86400 + 780, "what": "the chain took a take-back from a wallet that did not send the payment",
                      "step": "impostor", "tx": {"tx_type": "retract_transfer"}, "answer": {"status": "ok"}}]}
SKIP = {"id": "2026-12-03-poisoning", "hack": "poisoning", "t0": T0 + 21 * 86400, "status": "done", "result": "skipped",
        "why": "the testnet was not calm enough to start; next week again"}
NOW = [T0 + 2500]
ROUTES = {"/hack": {**SNAP, "runs": [HELD]}, "/hack/held": {"runs": [], "released": []}}
blog.get = lambda path: ROUTES[path]
hc.step(NOW[0])
hc.step(NOW[0] + 600)
check(len(POSTS) == 1 and len(TELLS) == 1, "a held replay is posted once, and the owner told once")
ROUTES["/hack"] = {**SNAP, "runs": [{k: FIND[k] for k in ("id", "hack", "t0", "status")} | {"result": "held back", "held": True}, HELD]}
ROUTES["/hack/held"] = {"runs": [FIND], "released": []}
NOW[0] = FIND["t0"] + 2500
hc.step(NOW[0])
hc.step(NOW[0] + 600)
check(len(POSTS) == 1, "a finding is never posted")
check(len(TELLS) == 2 and "github.com/IDNI/tau-testnet/issues/new?" in TELLS[-1] and "hack release 2026-11-26-poisoning" in TELLS[-1],
      "the owner gets the finding once, with a ready issue and the release line")
ROUTES["/hack"] = {**SNAP, "runs": [SKIP]}
NOW[0] = SKIP["t0"] + 1500
hc.step(NOW[0])
check(len(POSTS) == 1 and len(TELLS) == 3 and "nothing posted" in TELLS[-1], "a skipped run: no post, one private line")
blog.get = lambda path: {**SNAP, "runs": [HELD]}
check(any("next replay" in x for x in hc.status_lines()), "the up block names the next replay")

print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)
