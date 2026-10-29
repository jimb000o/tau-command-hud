"""Unit test of the findings (no network): the first run is silent, one post per incident and one on recovery, the
bootnode outage of 29 Oct 2026 gives exactly two posts (and no health alarm on top), a cooldown and a busy stretch
hold posts back and the stretch comes as one summary, and findings on X stay under their own daily cap.

Run: python test_findings.py   (needs websockets==15.0.1)
"""
import asyncio
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(STATE_PATH=os.path.join(TMP, "alerts.json"), PUBLIC_DIR=TMP, TELEGRAM_BOT_TOKEN="", HEALTH_CONFIRM_SECONDS="600")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alerts  # noqa: E402
import findings  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = 1_800_000_000 - 1_800_000_000 % 86400 + 8 * 3600  # 08:00 UTC


def health(age=10, sealed=0, waiting=0, pace=120, sync="in sync", node="yes"):
    return {"expected_block_seconds": 30, "factors": [
        {"key": "node", "value": node}, {"key": "last_block", "value": age}, {"key": "sync", "value": sync},
        {"key": "pace", "value": pace}, {"key": "mempool", "value": {"waiting": waiting, "sealed": sealed}}]}


def peers(n=3, boot=True):
    return {"bootnode": "boot", "counts": {"connected": n}, "peers": [{"id": "boot", "label": "IDNI bootnode", "connected": boot}]}


def snap(h=None, p=None, reorgs=()):
    return {"health": h or health(), "peers": p or peers(), "status": {"reorgs": list(reorgs)}, "blocks": {1: {"header": {"timestamp": T}}}}


# 1. the bootnode outage of 29 Oct 2026: one "lost" post at 12:11, one "back" post at 15:22, the stall not posted twice
posts = alerts.findings_case_bootnode()
check([p["what"] for p in posts] == ["peers start", "peers end"], f"outage: two posts {[p['what'] for p in posts]}")
check("12:11" in findings.hm(posts[0]["at"]) and "15:22" in findings.hm(posts[1]["at"]), "outage: posted at 12:11 and 15:22")
check("does not prove the testnet itself stopped" in posts[0]["tg"] and posts[0]["x"], "outage start: careful wording, on X")
check("3 h 19 min" in posts[1]["tg"] and "kept making blocks the whole time" in posts[1]["tg"] and posts[1]["x"],
      "outage end: how long, the network kept going, on X")
check(all("bounty" not in p["tg"].lower() for p in posts), "no bounty wording")

# 2. first run silent: a ghost incident already going on is not posted, nor its end
st = findings.fresh_state()
check(findings.observe(st, snap(health(sealed=9, waiting=20)), T) == [], "first run: nothing posted")
for i in range(1, 40):
    out = findings.observe(st, snap(health(sealed=0)), T + 60 * i)
    check(out == [], f"end of an incident from before the first run is quiet ({i})") if out else None
check(not st["inc"], "the old incident is closed")

# 3. a new ghost incident: posted after 15 minutes, once, Telegram only, with IDNI #81; no recovery post
st = findings.fresh_state()
findings.observe(st, snap(), T)
got = []
for i in range(1, 60):
    got += findings.observe(st, snap(health(sealed=7, waiting=12)), T + 60 * i)
check([g["what"] for g in got] == ["ghost start"] and got[0]["x"] is None and "IDNI #81" in got[0]["tg"], f"ghost once {got}")
for i in range(60, 120):
    got += findings.observe(st, snap(health(sealed=0)), T + 60 * i)
check(len(got) == 1, "ghost: no recovery post")
for i in range(120, 160):  # again within its 24 h cooldown: held, not posted
    got += findings.observe(st, snap(health(sealed=7, waiting=12)), T + 60 * i)
check(len(got) == 1 and st["held"] and st["held"][0]["key"] == "ghost", "ghost again within the cooldown is held")

# 4. a stall while connected: posted at 20 minutes without a block, recovery says the testnet itself paused
st = findings.fresh_state()
findings.observe(st, snap(), T)
got = []
for i in range(1, 40):
    got += findings.observe(st, snap(health(age=60 * i)), T + 60 * i)
check([g["what"] for g in got] == ["stall start"] and got[0]["x"], f"stall at 20 min, on X {[g['what'] for g in got]}")
end = findings.observe(st, {**snap(health(age=5)), "blocks": {1: {"header": {"timestamp": T}}, 2: {"header": {"timestamp": T + 40 * 60}}}},
                       T + 40 * 60 + 5)
check(end and end[0]["what"] == "stall end" and "the testnet made no block for 40 minutes" in end[0]["tg"], f"stall end {end and end[0]['tg']}")

# 5. reorgs: older ones are history, a new deep one is one post, a depth-1 one none
st = findings.fresh_state()
findings.observe(st, snap(reorgs=[{"at": T - 100, "height": 5, "depth": 4}]), T)
got = findings.observe(st, snap(reorgs=[{"at": T - 100, "height": 5, "depth": 4}, {"at": T + 30, "height": 9, "depth": 1}]), T + 60)
check(got == [], "reorg of depth 1 is not news")
got = findings.observe(st, snap(reorgs=[{"at": T + 100, "height": 12, "depth": 3}]), T + 120)
check(len(got) == 1 and "3 blocks from #12" in got[0]["tg"] and got[0]["x"], "a reorg of 3 blocks is posted")
check(findings.observe(st, snap(reorgs=[{"at": T + 100, "height": 12, "depth": 3}]), T + 180) == [], "and only once")

# 6. a busy stretch: from the 4th start in 6 hours on, everything is collected; one summary when calm
st = findings.fresh_state()
findings.observe(st, snap(), T)
got, t = [], T
for k in range(8):  # a new 3-block reorg every 20 minutes
    t += 1200
    got += findings.observe(st, snap(reorgs=[{"at": t - 1, "height": 100 + k, "depth": 3}]), t)
check([g["what"] for g in got] == ["reorg start"] and st["storm"], f"cooldown, then busy stretch {[g['what'] for g in got]}")
quiet = []
for i in range(1, 200):
    quiet += findings.observe(st, snap(reorgs=[]), t + 60 * i)
check(len(quiet) == 1 and quiet[0]["what"] == "summary" and "7× blocks replaced" in quiet[0]["tg"] and quiet[0]["x"],
      f"one summary after 2 calm hours {[q['what'] for q in quiet]} {quiet and quiet[0]['tg']}")
check(st["storm"] is None and not st["held"], "the stretch is over")

# 7. our node falling behind: IDNI #78; not while our node has no peers
st = findings.fresh_state()
findings.observe(st, snap(), T)
got = []
for i in range(1, 20):
    got += findings.observe(st, snap(health(sync="42 blocks behind")), T + 60 * i)
check([g["what"] for g in got] == ["behind start"] and "IDNI #78" in got[0]["tg"] and not got[0]["x"], "behind: #78, Telegram only")
check(findings.conditions(snap(health(sync="42 blocks behind"), peers(0, False)), T, {}).get("behind") is None,
      "behind is not judged without peers")
check(findings.conditions(snap(health(node="no")), T, {}) is None, "nothing judged while our node does not answer")


# 8. the watcher: Telegram first, X copy under the findings cap, health alarm skipped while a finding covers it
class Fake(alerts.Outlet):
    def __init__(self, name):
        self.name, self.sent = name, []

    def enabled(self):
        return True

    def send_text(self, text, *a):
        self.sent.append(text)
        return True, None, ""


tg, x = Fake("telegram"), Fake("x")
w = alerts.Watcher([tg, x])
w.save_state = lambda: None
case = alerts.findings_case_bootnode()


async def main():
    st = w.state.setdefault("findings", findings.fresh_state())
    st["outbox"] = [{**m, "tries": 0} for m in case] + [{**case[0], "what": f"extra {i}", "tries": 0} for i in range(3)]
    for m in st["outbox"]:
        m["at"] = T
    st["checked"] = T + 10  # no detector run in this step
    await w.maybe_findings(T + 20)
    check(len(tg.sent) == 5 and len(x.sent) == findings.X_DAILY, f"telegram {len(tg.sent)}, x {len(x.sent)} (cap {findings.X_DAILY})")
    st["inc"]["peers"] = {"since": T, "start": T, "posted": True, "facts": {}}
    hs = w.state.setdefault("health", {"posted": "up", "checked": 0})
    w.health_now = lambda: {"score": 20, "state": "down", "label": "Down", "factors": []}
    await w.maybe_health(T + 100)
    await w.maybe_health(T + 800)
    check(hs["posted"] == "down" and hs.get("covered") and len(tg.sent) == 5, "health down not posted while the finding covers it")
    st["inc"].clear()
    w.health_now = lambda: {"score": 95, "state": "healthy", "label": "Healthy", "factors": []}
    await w.maybe_health(T + 900)
    await w.maybe_health(T + 1600)
    check(hs["posted"] == "up" and not hs.get("covered") and len(tg.sent) == 5, "nor its recovery")


asyncio.run(main())
print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)
