"""Unit test of what happens by itself after a testnet restart (restartwatch.py, restart_report.brief), no network:
the note waits for the rules, goes once, carries a fact-only reply for IDNI with the timeline link; the ships pause at
the third restart during a call and sail again on resume; the report is served as text; a call under way ends.

Run: python test_restartwatch.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
os.environ["CRUISE_DATA"] = tmp
os.environ["RESTART_SHIP_PAUSE_AFTER"] = "3"
import restart_report  # noqa: E402
import restartwatch  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


DAY = 86400
T = 1763300000   # 16.11.2026 ~13:33Z


def rows_for(calls):
    """A cruise logbook: each call sends one pay a minute from t0 for 30 minutes."""
    out = []
    for vid, t0 in calls:
        for i in range(30):
            out.append({"t": t0 + i * 60, "visit": vid, "kind": "pay", "amount": 5, "seq": i, "ok": True, "ms": 40,
                        "hash": f"{vid}-{i:02d}"})
    return out


def restart(tip_ts, tip=100):
    return {"detected_at": tip_ts + 90, "old": {"tip": tip, "tip_ts": tip_ts}, "new_block1_ts": tip_ts + 40}


calls = [("2026-11-14-queen", T - 2 * DAY), ("2026-11-15-queen", T - DAY), ("2026-11-15-dryrun", T - DAY + 4 * 3600),
         ("2026-11-16-queen", T)]
rows = rows_for(calls)
restarts = [restart(T - 2 * DAY + 600), restart(T - DAY + 480), restart(T + 1500, tip=1234)]

# --- the reply for IDNI: facts only
b = restart_report.brief(restarts, rows, now=T + 1700, link="https://node.tauhud.com/restarts/report.txt")
check(b["tip"] == 1234 and b["calls"] == ["2026-11-16-queen"], "brief names the newest restart and its call")
check("Hi Andrei" in b["reply"] and "#1234" in b["reply"] and "Queen Mempool" in b["reply"], "reply: block, ship")
check("25 min into one of our test runs" in b["reply"], "reply: minutes into the run")
check("3 restarts in the last 7 days, 3 of them during one of our runs (14, 15 and 16 Nov). 1 of our other runs" in b["reply"],
      "reply: the pattern, counted, with the days")
check("• We sent 16 transactions (16 pay)" in b["reply"] and "• 16 accepted" in b["reply"], "reply: what we sent and the answers")
check("• Median answer time: 40 ms" in b["reply"], "reply: answer time in ms below a second")
check("restarts/report.txt" in b["reply"], "reply carries the timeline link")
for word in ("fault", "bug", "broke", "crash", "Uplink", "Matrix"):
    check(word not in b["reply"], f"reply never says '{word}'")
check(restart_report.brief([], rows) is None, "no restart, no brief")

# --- the ships pause at the third restart during a call
class Ship:
    def __init__(self):
        self.enabled, self.cur, self.left = True, {"id": "2026-11-16-queen"}, None

    def leave(self, now, why, state):
        self.cur["left"] = now
        self.left = (why, state)


w = restartwatch.RestartWatch(os.path.join(tmp, "rw.json"), clock=lambda: T + 1600, rows_fn=lambda: rows)
ship = Ship()
check(not w.on_restart(restarts[:2], ship, now=T - DAY + 600), "two restarts during calls: ships keep sailing")
check(ship.enabled, "ships still on after two")
check(w.on_restart(restarts, ship, now=T + 1600), "third restart during a call: ships pause")
check(not ship.enabled and ship.left is not None, "the ship in port left, ships off")
check(not w.on_restart(restarts, ship, now=T + 1601), "already paused: nothing more")
ship2 = Ship()
restartwatch.RestartWatch(os.path.join(tmp, "rw.json"), rows_fn=lambda: rows).apply_pause(ship2)
check(not ship2.enabled, "the pause survives a relay restart")
r = w.resume(ship, now=T + 3600)
check(ship.enabled and r["was_paused"], "up ships on: ships sail again")
check(not w.on_restart(restarts, ship, now=T + 3700), "after resume the old restarts no longer count")

# --- the owner's note waits for the rules, then goes once
w2 = restartwatch.RestartWatch(os.path.join(tmp, "rw2.json"), rows_fn=lambda: rows)
at = restarts[-1]["detected_at"]
rules_missing = {"Schaufenster-Wallets": {"piggy": True, "foureyes": False, "feeding": True}}
rules_ok = {"Schaufenster-Wallets": {"piggy": True, "foureyes": True, "feeding": True}, "No-Memo-Vaults": {"till": True}}
check(w2.tick(restarts, rules_ok, 5, now=at + 60) is None, "no note in the first minutes")
check(w2.tick(restarts, rules_missing, 5, now=at + 15 * 60) is None, "a rule still missing: note waits")
check(w2.tick(restarts, rules_ok, None, now=at + 15 * 60) is None, "no block on the new chain yet: note waits")
n = w2.tick(restarts, rules_ok, 9, now=at + 15 * 60)
check(n is not None and "3/3" in n["text"] and "1/1" in n["text"], "rules back: note says what set itself")
check("<pre>Hi Andrei" in n["text"] and "nichts wurde an IDNI geschickt" in n["text"], "note: copy block, nothing sent")
check(w2.tick(restarts, rules_ok, 9, now=at + 16 * 60) is None, "one note per restart")
w3 = restartwatch.RestartWatch(os.path.join(tmp, "rw3.json"), rows_fn=lambda: rows)
n3 = w3.tick(restarts, rules_missing, 9, now=at + 41 * 60)
check(n3 and "foureyes" in n3["text"] and "Noch nicht" in n3["text"], "after 40 min the note goes with what is missing")
w4 = restartwatch.RestartWatch(os.path.join(tmp, "rw4.json"), rows_fn=lambda: rows)
check(w4.tick(restarts, rules_ok, 9, now=at + 2 * DAY) is None, "a restart from two days ago gets no note")

# --- routes
code, ctype, body = w2.route("/restarts/report.txt", internal=False)
check(code == 200 and ctype.startswith("text/plain") and b"Tau HUD" in body, "report.txt served as text to anyone")
check(w2.route("/restarts/notes", internal=False)[0] == 404, "notes only from inside the server")
got = json.loads(w2.route("/restarts/notes", internal=True)[2])
check(len(got["notes"]) == 1, "notes listed inside")
check(w2.route("/restarts/other", internal=True) is None, "other paths left alone")

# --- a call under way ends with the restart (cruise.chain_restarted)
import cruise  # noqa: E402
c = cruise.Cruise.__new__(cruise.Cruise)
c.cur = {"id": "2026-11-16-queen", "ship": "queen", "left": None, "note": ""}
c.visits, wrote, left = [], [], []
c.write = wrote.append
c.leave = lambda now, why, state: left.append((why, state))
cruise.Cruise.chain_restarted(c, T + 1600, 1234, T + 1540)
check(wrote and wrote[0]["kind"] == "chain restarted", "logbook: chain restarted")
check(left and left[0][1] == "restarted" and "cut short" in left[0][0], "the ship in port ends its call")

# --- the island never tells a restart (or Tau HUD's own brake) as a stall
check(cruise.Cruise.why({"left": 1, "note": "left early: the testnet restarted during the call, so the call was cut short"}) == "restarted",
      "why: a restart is 'restarted', not 'stalled'")
check(cruise.Cruise.why({"left": 1, "note": "left early: Tau HUD called the ship back"}) == "recalled", "why: up ships leave")
check(cruise.Cruise.why({"left": 1, "note": "left early: no new block reached our node"}) == "stalled", "why: a stall stays a stall")

# --- Telegram HTML: every & escaped, the reply in a copy block
n["paused"] = {"restarts": 3}
txt = restartwatch.owner_text(n)
check("&& " not in txt and "&amp;&amp;" in txt, "the resume line's && is escaped for Telegram")

# --- a restart the relay found after being away: no unknown block numbers in the reply
b2 = restart_report.brief(restarts + [{"detected_at": T + 9000, "old": {"tip": None}}], rows, now=T + 9100)
check("#None" not in b2["reply"] and "noticed it at " in b2["reply"] and " UTC" in b2["reply"], "reply without the old chain's end says only what is known")

print("failed:", failed)
sys.exit(1 if failed else 0)
