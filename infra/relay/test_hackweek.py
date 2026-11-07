"""Unit test of the hack of the week (hackweek.py), no network: the weekly slot, one ship at a time, the lookalike pair,
a whole address poisoning run against a fake node with an escrow book (held), a late take-back (missed), and a chain
that takes a take-back from the wrong wallet (finding, masked in public).

Run: python test_hackweek.py
"""
import asyncio
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cruise  # noqa: E402
import hackweek  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


THU = cruise.berlin_t(dt.date(2026, 11, 12), 11)
check(hackweek.week_slot(THU - 3 * 86400) == THU and hackweek.week_slot(THU + 3 * 86400) == THU, "this week's run: Thursday 12 November, 11:00 German time")
check(hackweek.next_slot(THU + 3600) == THU + 7 * 86400, "once it has started, the next one is a week later")
check(hackweek.ship_near(THU) is None, "no cruise ship near Thursday 11:00")
check(hackweek.ship_near(cruise.berlin_t(dt.date(2026, 11, 11), 15)) == "MS Dry Run", "Wednesday 15:00 would meet MS Dry Run")
check(hackweek.short("8a91f2" + "0" * 86 + "c03e") == "8a91f2…c03e", "an address shortened the way the pages show it")

# the lookalike pair: a short tag so the test is quick; the real one is 6 + 4 characters
pair = hackweek.grind(limit=20000, tag=lambda h: int(h[:3] + h[-1:], 16))
from py_ecc.bls import G2Basic  # noqa: E402
a, b = (G2Basic.SkToPk(x).hex() for x in pair)
check(a != b and a[:3] == b[:3] and a[-1:] == b[-1:], "the search finds two different keys whose addresses start and end alike")

KEYS = {}
for n, sk in (("victim", 11), ("twin", 12), ("friend", pair[0]), ("poisoner", pair[1])):
    KEYS[n] = {"sk": sk.to_bytes(32, "big").hex(), "pk": G2Basic.SkToPk(sk).hex()}

# ---------- a fake node with an escrow book ----------
T = [float(THU)]
MODE = {"impostor_ok": False, "retract_late": False, "down": 0}
PARKS, BY_HASH, SEQ, BAL, BLOCK, TXS = {}, {}, {}, {}, [100], {}


def sweep():
    for p in PARKS.values():
        if p["status"] == "open" and T[0] >= p["release_at_time"]:
            p.update(status="released", resolved_at_height=BLOCK[0])
            BAL[p["recipient_pubkey"]] = BAL.get(p["recipient_pubkey"], 0) + p["amount"]


async def ask(cmd: str):
    sweep()
    BLOCK[0] += 1
    name, _, rest = cmd.partition(" ")
    if name == "getsequence":
        return {"status": "ok", "data": {"sequence_number": SEQ.get(rest, 0), "tip_height": BLOCK[0]}}
    if name == "getretractables":
        pk = rest.split()[0]
        return {"status": "ok", "data": {"retractables": [p for p in PARKS.values() if p["sender_pubkey"] == pk and p["status"] == "open"]}}
    if name == "getretractable":
        p = PARKS.get(rest)
        return {"status": "ok", "data": {"retractable_id": rest, "status": p["status"], "resolved_at_height": p.get("resolved_at_height")}} if p else {"status": "error"}
    if name == "gettxstatus":
        return {"status": "ok", "data": TXS.get(rest, {"status": "unknown"})}
    if name == "sendtx":
        if MODE["down"]:
            MODE["down"] -= 1
            return None
        tx = json.loads(rest)
        h = hashlib.sha256(rest.encode()).hexdigest()
        snd = tx["sender_pubkey"]
        if tx["tx_type"] == "retract_transfer":
            p = PARKS.get(tx["retractable_id"])
            if not p or p["status"] != "open":
                return {"status": "error", "error": {"code": "UNKNOWN_RETRACTABLE"}}
            if p["sender_pubkey"] != snd and not MODE["impostor_ok"]:
                return {"status": "error", "error": {"code": "NOT_RETRACTABLE_SENDER", "message": "Only the sender may retract."}}
            SEQ[snd] = SEQ.get(snd, 0) + 1
            TXS[h] = {"status": "confirmed", "block_number": BLOCK[0]}
            if not MODE["retract_late"]:
                p.update(status="retracted", resolved_at_height=BLOCK[0])
            return {"status": "ok", "data": {"tx_hash": h}}
        SEQ[snd] = SEQ.get(snd, 0) + 1
        TXS[h] = {"status": "confirmed", "block_number": BLOCK[0]}
        if tx["tx_type"] == "retractable_transfer":
            rid = hashlib.sha256(("id" + rest).encode()).hexdigest()
            PARKS[rid] = {"retractable_id": rid, "sender_pubkey": snd, "recipient_pubkey": tx["recipient_pubkey"],
                          "amount": tx["amount"], "release_at_time": tx["release_at_time"], "status": "open"}
            TXS[h]["retractable"] = {"id": rid, "status": "open"}
        else:
            for _, to, amt in tx["operations"]["1"]:
                BAL[to] = BAL.get(to, 0) + int(amt)
        return {"status": "ok", "data": {"tx_hash": h}}
    return None


def run_week(H, until: float, step: float = 5.0):
    sent = 0
    while T[0] < until:
        sent += asyncio.run(H.step(ask, lambda: {}))
        T[0] += step
    return sent


d = tempfile.mkdtemp()
VERDICT = ["calm"]


def fresh(n: str):
    PARKS.clear(); BY_HASH.clear(); BAL.clear(); TXS.clear()
    return hackweek.HackWeek(keys_path=os.path.join(d, n + ".keys"), state_path=os.path.join(d, n + ".json"), clock=lambda: T[0],
                             enabled=True, verdict=lambda: VERDICT[0], keys=KEYS)


H = fresh("a")
check(set(H.who) == {k["pk"] for k in KEYS.values()}, "the four wallets are known as simulated")
T[0] = THU - 60
check(run_week(H, THU - 10) == 0 and not H.runs, "nothing before Thursday 11:00")
T[0] = THU
sent = run_week(H, THU + hackweek.WINDOW + 30 * 60)
r = H.runs[-1]
check(r["id"] == "2026-11-12-poisoning" and r["status"] == "done", "the run of 12 November ran to its end")
check(r["result"] == "held", f"with the take-back window the payment came back: {r.get('result')} ({r.get('why')})")
check(sent == 8, f"eight transactions in all (2 habit, 2 dust, 2 slips, the impostor's try, the take-back): {sent}")
check(r["steps"]["impostor"].get("ok") is False and r["steps"]["impostor"].get("right"), "the chain refused the poisoner's take-back with NOT_RETRACTABLE_SENDER")
check(r["steps"]["peek"].get("status") == "open", "before the take-back the payment was still in escrow")
check(r["outcome"]["twin"] == "confirmed" and r["outcome"]["victim"]["status"] == "retracted", "the twin's 50 reached the poisoner, the victim's came back")
check(BAL.get(KEYS["poisoner"]["pk"]) == hackweek.SLIP, "the poisoner holds only the twin's 50")
check(r["steps"]["catch"]["t"] - r["steps"]["slip"]["t"] <= hackweek.WINDOW - hackweek.RETRACT_MARGIN, "the take-back went out with margin before the release")
ts = sorted(s["t"] for s in r["steps"].values() if s.get("t") and s.get("tx"))
check(all(b - a >= hackweek.GAP for a, b in zip(ts, ts[1:])), "never two sends closer than GAP seconds")
check(json.load(open(os.path.join(d, "a.json")))["runs"][-1]["result"] == "held", "kept in the state file")
pub = H.route("/hack")
check(pub["runs"][0]["result"] == "held" and pub["wallets"]["friend"]["short"][:3] == pub["wallets"]["poisoner"]["short"][:3], "GET /hack shows the run and the lookalike pair")
check(run_week(H, T[0] + 3600) == 0, "a run happens once a week")

# a ship near the slot: skipped
saved = hackweek.SLOT
hackweek.SLOT = (2, 15)
WED = cruise.berlin_t(dt.date(2026, 11, 11), 15)
H2 = fresh("b")
T[0] = WED
run_week(H2, WED + 60)
check(H2.runs[-1]["result"] == "skipped" and "MS Dry Run" in H2.runs[-1]["why"], "never near a cruise ship's call: one ship at a time")
hackweek.SLOT = saved

# the testnet not calm: waits, then skips
VERDICT[0] = "strained"
H3 = fresh("c")
T[0] = THU
check(run_week(H3, THU + hackweek.START_WAIT + 60) == 0 and H3.runs[-1]["result"] == "skipped", "a strained testnet: no start, next week again")
VERDICT[0] = "calm"

# the take-back lost the race: missed, told honestly, no finding
MODE["retract_late"] = True
H4 = fresh("d")
T[0] = THU
run_week(H4, THU + hackweek.WINDOW + 30 * 60)
r = H4.runs[-1]
check(r["result"] == "missed" and not r.get("findings"), f"take-back not applied, release without an earlier take-back block: missed ({r.get('result')})")
MODE["retract_late"] = False

# a chain that lets the poisoner take back the victim's payment: finding, held back from the public
MODE["impostor_ok"] = True
H5 = fresh("e")
T[0] = THU
run_week(H5, THU + hackweek.WINDOW + 30 * 60)
r = H5.runs[-1]
check(r["result"] == "finding" and r["findings"][0]["step"] == "impostor", "a take-back from the wrong wallet accepted: a finding")
pub = H5.route("/hack")["runs"][0]
check(pub.get("held") and "steps" not in pub and "findings" not in pub, "the public sees only 'held back'")
check(H5.route("/hack/held", internal=False).get("error") and H5.route("/hack/held", internal=True)["runs"][0]["findings"], "/hack/held only from inside the server")
json.dump([r["id"]], open(os.path.join(d, "hack-released.json"), "w"))
check(H5.route("/hack")["runs"][0].get("findings"), "up hack release shows it")
MODE["impostor_ok"] = False

# our node does not answer the first sends: tried again, still held
MODE["down"] = 2
H6 = fresh("f")
T[0] = THU
run_week(H6, THU + hackweek.WINDOW + 30 * 60)
check(H6.runs[-1]["result"] == "held", f"two unanswered sends are tried again: {H6.runs[-1]['result']}")

print("\n" + ("all ok" if not failed else f"{failed} FAILED"))
sys.exit(1 if failed else 0)
