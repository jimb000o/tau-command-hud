"""Unit test of the cruise ships (cruise.py), no network: timetable, passengers' days, pace, brakes, logbook.

Run: python test_cruise.py
"""
import asyncio
import datetime as dt
import hashlib
import json
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cruise  # noqa: E402
import island  # noqa: E402
from load import Load  # noqa: E402
from py_ecc.bls import G2Basic  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# ---------- the timetable: Wednesday 16:00 and Saturday 14:00 in Germany, winter and summer ----------
WED = cruise.berlin_t(dt.date(2026, 11, 4), 16)
check(WED == 1793804400, "MS Dry Run: Wednesday 4 November 2026, 16:00 in Germany = 15:00 UTC")
check(cruise.berlin_t(dt.date(2026, 7, 1), 16) == 1782914400, "in summer 16:00 in Germany is 14:00 UTC")
calls = cruise.calls_near(WED - 86400)
check([k for t, k in calls][:3] == ["dryrun", "queen", "dryrun"] and calls[1][0] - WED == 3 * 86400 - 7200,
      "the next calls: Wednesday, then Saturday 14:00, then Wednesday again")
check(cruise.visit_id(WED, "dryrun") == "2026-11-04-dryrun", "a visit is named by its day and ship")

# ---------- a passenger's day ----------
P1 = cruise.plan("dryrun", WED, {"book"}, {"book"})
P2 = cruise.plan("dryrun", WED, {"book"}, {"book"})
check(P1 == P2, "the same visit plans the same day, so a restart carries on where it was")
end = WED + (cruise.VISIT_MIN - cruise.BOARDING) * 60
check(all(WED <= a["t"] < end for a in P1), "every stop lies between landing and boarding")
landings = [a for a in P1 if a["kind"] == "pay" and a["to"] == "pier"]
check(len(landings) == 40 and len({a["p"] for a in landings}) == 40, "each of the 40 passengers pays the landing fee at the pier")
first = {}
for a in P1:
    first.setdefault(a["p"], a)
check(all(f["kind"] == "pay" and f["to"] == "pier" for f in first.values()), "a passenger's first transaction is the landing (a new wallet is funded by the faucet on it)")
places = {a["to"] for a in P1 if isinstance(a["to"], str)}
check(not places & cruise.CLOSED and places <= set(island.PLACES), "no group goes to Ama's or Tano's places, the council or an embassy's political till")
books = [a for a in P1 if a["kind"] == "book"]
cancels = [a for a in P1 if a["kind"] == "cancel"]
check(0 < len(books) <= cruise.TRIAL_MAX, f"a first visit with bookings sends at most {cruise.TRIAL_MAX} ({len(books)})")
check(len(cancels) >= 1, "and withdraws at least one of them, so both halves are tried")
check(all(c["t"] <= c["rel"] - cruise.RETRACT_MARGIN for c in cancels), "a withdrawal goes out well before the booking's time")
check(all(b["rel"] <= end - 5 * 60 and b["rel"] - b["t"] >= 25 * 60 for b in books), "a booking's time is at least 25 minutes ahead and inside the visit")
check(not any(a["kind"] == "bill" for a in P1), "MS Dry Run sends no group bills")
full = cruise.plan("dryrun", WED, set(), {"book"})
check(len([a for a in full if a["kind"] == "book"]) > cruise.TRIAL_MAX, "once bookings are tried, more passengers book")
SAT = calls[1][0]
Q = cruise.plan("queen", SAT, {"bill"}, {"bill", "book"})
bills = [a for a in Q if a["kind"] == "bill"]
check(0 < len(bills) <= cruise.TRIAL_MAX and all(len(b["to"]) == 3 and b["amount"] == sum(x for _, x in b["to"]) for b in bills),
      "Queen Mempool's first group bills: at most five, each one transaction paying the bar, the radio and the Coconut Works")
check(len([a for a in Q if a["kind"] == "pay" and a["to"] == "pier"]) == 120 and len(Q) <= cruise.VISIT_MAX, "120 passengers, at most VISIT_MAX stops")
rate = len(Q) / (cruise.VISIT_MIN - cruise.BOARDING)
check(rate < cruise.RATE, f"the plan fits the pace: {rate:.1f} a minute on average, at most {cruise.RATE}")
at = cruise.where(Q, SAT + 40 * 60, SAT + 80 * 60)
check(sum(at.values()) == 120 and "pier" not in at or at.get("pier", 0) < 120, "forty minutes in, the passengers are spread over the places")
check(cruise.where(Q, SAT + 81 * 60, SAT + 80 * 60) == {}, "at boarding everyone is back on the ship")

# ---------- signed as the node reads it (tau-testnet consensus/tx_signing.py, checked against it) ----------
d = tempfile.mkdtemp()
paths = dict(keys_path=os.path.join(d, "k"), log_path=os.path.join(d, "log.jsonl"), state_path=os.path.join(d, "st.json"),
             incidents_path=os.path.join(d, "inc.json"))
T = [WED - 40 * 60.0]
clock = lambda: T[0]  # noqa: E731
STATE = ["calm"]
spent = []
C = cruise.Cruise(**paths, clock=clock, enabled=True, verdict=lambda: STATE[0], chain=lambda: {"height": 4242, "waiting": 3},
                  spend=lambda: spent.append(1), background=False)
check(C.ready and len(C.pk) == 160 and len(set(C.pk.values())) == 160, "160 passenger wallets are made on first start")
check(stat.S_IMODE(os.stat(paths["keys_path"]).st_mode) == 0o600, "their keys are readable by the relay only")
check(not set(C.pk.values()) & set(island.PLACES.values()), "no passenger wallet is a place's till")
again = cruise.Cruise(**{**paths, "log_path": os.path.join(d, "l2"), "state_path": os.path.join(d, "s2")}, clock=clock, enabled=True, background=False)
check(again.pk == C.pk, "the same wallets after a restart")
park = C.build("dryrun", {"i": 0, "p": 3, "kind": "book", "to": "dive", "amount": 24, "rel": WED + 3600}, 2, 900, 10)
pre = cruise.signing_bytes(park)
check(json.loads(pre) == {"sender_pubkey": C.pk["dryrun-3"], "sequence_number": 2, "expiration_time": int(T[0]) + 600, "expire_at_height": 1900,
                          "fee_limit": "50", "tx_type": "retractable_transfer", "recipient_pubkey": island.PLACES["dive"], "amount": 24,
                          "release_at_height": None, "release_at_time": WED + 3600},
      "a booking: both release fields signed, the unused one as null, an integer amount")
check(G2Basic.Verify(bytes.fromhex(park["sender_pubkey"]), hashlib.sha256(pre).digest(), bytes.fromhex(park["signature"])), "its BLS signature verifies")
late = C.build("dryrun", {"i": 0, "p": 3, "kind": "book", "to": "dive", "amount": 24, "rel": int(T[0]) + 300}, 2, 900, 10)
check(late["expiration_time"] < late["release_at_time"], "a booking expires before its time (the node refuses DEADLINE_AFTER_RELEASE)")
ret = C.build("dryrun", {"i": 1, "p": 3, "kind": "cancel", "to": "dive", "amount": 24, "rel": WED + 3600}, 3, 900, 10, "ab" * 32)
check(ret["fee_limit"] == "0" and ret["retractable_id"] == "ab" * 32 and "amount" not in ret and json.loads(cruise.signing_bytes(ret))["retractable_id"] == "ab" * 32,
      "a withdrawal: feeless, names the booking, signs its id")
bill = C.build("queen", {"i": 2, "p": 7, "kind": "bill", "to": [["bar", 15], ["radio", 25], ["works", 12]], "amount": 52}, 0, 900, 10)
check(bill["operations"]["1"] == [[C.pk["queen-7"], island.PLACES["bar"], "15"], [C.pk["queen-7"], island.PLACES["radio"], "25"],
                                  [C.pk["queen-7"], island.PLACES["works"], "12"]] and bill["fee_limit"] == "150",
      "a group bill: three payments in one transaction, fee room for each")
try:
    cruise.signing_bytes({"tx_type": "consensus_rule_vote", "sender_pubkey": "", "sequence_number": 0, "expiration_time": 0, "fee_limit": "0"})
    check(False, "a passenger never signs a vote")
except ValueError:
    check(True, "a passenger never signs a vote, a rule or a co-signed payment")

# ---------- a visit, sent through a fake node ----------
sent, retracts = [], []
OPEN: dict = {}


async def ask(cmd: str):
    name, _, rest = cmd.partition(" ")
    if name == "getsequence":
        return {"status": "ok", "data": {"sequence_number": sum(1 for t in sent if t["sender_pubkey"] == rest), "tip_height": 5000}}
    if name == "getretractables":
        pk = rest.split()[0]
        return {"status": "ok", "data": {"retractables": OPEN.get(pk, [])}}
    if name == "sendtx":
        tx = json.loads(rest)
        sent.append(tx)
        if tx["tx_type"] == "retractable_transfer":
            OPEN.setdefault(tx["sender_pubkey"], []).append({"retractable_id": hashlib.sha256(rest.encode()).hexdigest(), "recipient_pubkey": tx["recipient_pubkey"],
                                                             "amount": tx["amount"], "release_at_time": tx["release_at_time"], "status": "open"})
        if tx["tx_type"] == "retract_transfer":
            retracts.append(tx)
        return {"status": "ok", "data": {"ok": True, "tx_hash": hashlib.sha256(rest.encode()).hexdigest()}}
    return None


gov = lambda: {"consensus_rules": "o9[t]:bv[24] = { #x0a }"}  # noqa: E731


def run(until: float, step: float = 1.0, ship=None):
    n = 0
    while T[0] < until:
        if asyncio.run((ship or C).step(ask, gov)):
            n += 1
        T[0] += step
    return n


check(C.brief(T[0]).get("now") is None and C.brief(T[0])["next"]["ship"] == "dryrun", "forty minutes before: no ship yet, the next one is named")
T[0] = WED - 20 * 60
b = C.brief(T[0])
check(b["now"]["phase"] == "approach" and b["now"]["name"] == "MS Dry Run" and b["simulated"] is True, "twenty minutes before: MS Dry Run is seen coming, marked simulated")
check(b["now"]["kinds"] == ["pay", "book"] and b["now"]["why"] == "", "and what its passengers will do: pay, and book (its first trial)")
OFF = cruise.Cruise(**{**paths, "state_path": os.path.join(d, "s0"), "log_path": os.path.join(d, "l0"), "incidents_path": os.path.join(d, "i0")},
                    clock=clock, enabled=False, verdict=lambda: "calm", background=False)
check(not OFF.brief(T[0]).get("now") and not OFF.brief(T[0]).get("next") and OFF.brief(T[0])["enabled"] is False,
      "switched off (CRUISE_ENABLED=0): no ship and none announced")
run(WED)
check(not sent, "nothing is sent before the ship lands")
STATE[0] = "calm"
n = run(WED + 10 * 60)
v = C.cur
check(v["landed"] and v["trial"] == ["book"] and n == len(sent) > 0, f"at four it lands on a calm testnet and tries bookings ({n} sent in the first ten minutes)")
per_min: dict = {}
for e in C.logbook:
    if e.get("kind") in cruise.KINDS:
        per_min[e["t"] // 60] = per_min.get(e["t"] // 60, 0) + 1
check(max(per_min.values()) <= cruise.RATE, f"never more than {cruise.RATE} a minute ({max(per_min.values())})")
check(all(t["tx_type"] in ("user_tx", "retractable_transfer", "retract_transfer") for t in sent), "only transfers, bookings and withdrawals")
check(len(spent) == len(sent), "every transaction is taken from the island's day budget")

STATE[0] = "strained"
before = len(sent)
run(WED + 15 * 60)
check(0 < len(sent) - before <= cruise.RATE // 2 * 5 + 1, f"strained: half the pace ({len(sent) - before} in five minutes)")
STATE[0] = "calm"
run(WED + 70 * 60)
check(any(t["tx_type"] == "retractable_transfer" for t in sent) and retracts, "bookings went out, and a withdrawal for one of them")
check(all(r["retractable_id"] in {e["retractable_id"] for es in OPEN.values() for e in es} for r in retracts), "a withdrawal names a booking the node lists")
snap = C.route("/cruise")
check(snap["now"]["ashore"] > 0 and snap["now"]["sent"]["pay"] > 0 and len(snap["wallets"]["dryrun"]) == 40 and snap["places"]["pier"] == island.PLACES["pier"],
      "GET /cruise: passengers ashore, what they sent, their wallets and the tills")
lg = C.route("/cruise/log", "n=5")
check(len(lg["entries"]) == 5 and lg["entries"][0]["t"] >= lg["entries"][-1]["t"] and all("hash" in e for e in lg["entries"] if e.get("kind") in cruise.KINDS),
      "GET /cruise/log: the newest entries first, each with its hash")
rare = [e for e in C.logbook if e.get("kind") in ("book", "cancel")]
check(rare and all("tx" in e and "sk" not in json.dumps(e) for e in rare) and all(e.get("verdict") for e in rare),
      "the logbook keeps the signed booking and withdrawal, the load verdict, and never a key")
check(C.route("/cruise/log", "visit=../../etc")["entries"] == [], "the visit filter takes only visit ids")

# ---------- a restart during the visit carries on, sends nothing twice ----------
done_before = set(C.cur["done"])
C2 = cruise.Cruise(**paths, clock=clock, enabled=True, verdict=lambda: STATE[0], spend=lambda: None, background=False)
C2.advance(T[0])
check(C2.cur and C2.cur["done"] == done_before and C2.cur["landed"], "after a restart the visit goes on with what was already sent")
C = C2

# ---------- the end of the visit ----------
run(WED + 91 * 60, 2.0)
check(C.cur is None and C.visits[-1]["id"] == "2026-11-04-dryrun" and C.tried["book"] == "2026-11-04-dryrun",
      "after ninety minutes the visit is over, and bookings count as tried")
lastsend = max(e["t"] for e in C.logbook if e.get("kind") in cruise.KINDS)
check(lastsend < WED + (cruise.VISIT_MIN - cruise.BOARDING) * 60 + cruise.MISS, "nothing goes out after boarding")
for es in OPEN.values():   # one booking the chain never released
    es[:] = es[:1]
    es[0]["release_at_time"] = WED + 30 * 60
    break
run(WED + 96 * 60, 2.0)
inc = C.route("/cruise/incidents")["incidents"]
check(inc and inc[0]["kind"] == "not released" and inc[0]["bookings"], "a booking still in escrow after its time is reported")
check(C.tried["book"] is None, "and bookings go back on trial")

# ---------- no landing on a strained testnet; a stall sends the ship away ----------
T[0] = SAT - 5 * 60
STATE[0] = "strained"
run(SAT + cruise.LAND_WAIT + 30, 5.0)
check(C.cur and not C.cur["landed"] and C.cur["note"].startswith("no landing") and not [e for e in C.logbook if e.get("visit") == C.cur["id"] and e.get("kind") in cruise.KINDS],
      "on a strained testnet the ship waits ten minutes, then sails on without landing")
check(C.brief(T[0])["now"]["why"] == "no landing", "and the pages say it did not land")
C3 = cruise.Cruise(**{**paths, "state_path": os.path.join(d, "s3"), "log_path": os.path.join(d, "l3"), "incidents_path": os.path.join(d, "i3")}, clock=clock,
                   enabled=True, verdict=lambda: STATE[0], chain=lambda: {"height": 777, "waiting": 40, "oldest_waiting": {"hash": "f" * 64}}, background=False)
C3.tried = {"book": "x", "bill": None}
T[0] = SAT
STATE[0] = "busy"
run(SAT + 20 * 60, ship=C3)
check(C3.cur["landed"] and C3.cur["trial"] == ["bill"] and "book" in C3.cur["allowed"], "Queen Mempool lands on a busy testnet, tries group bills, books freely")
STATE[0] = "stalled"
run(SAT + 21 * 60, ship=C3)
check(C3.cur["left"] and C3.cur["note"].startswith("left early") and C3.brief(T[0])["now"]["why"] == "stalled", "a stall: the ship leaves at once")
rep = C3.route("/cruise/incidents")["incidents"][0]
check(rep["kind"] == "stalled" and rep["chain"]["height"] == 777 and rep["chain"]["oldest_waiting"]["hash"] == "f" * 64 and rep["tail"],
      "and writes an incident: the newest block, the transaction waiting longest, the last entries before it")
n = len(C3.logbook)
run(SAT + 30 * 60, ship=C3)
check(len([e for e in list(C3.logbook)[n:] if e.get("kind") in cruise.KINDS]) == 0, "after leaving, no passenger sends anything")
T[0] = SAT + 95 * 60
asyncio.run(C3.step(ask, gov))
check(C3.tried["bill"] is None, "a visit that ended in a stall does not count its new kind as tried")

# ---------- the node refuses again and again (a changed or restarted testnet): the ship leaves ----------
C4 = cruise.Cruise(**{**paths, "state_path": os.path.join(d, "s4"), "log_path": os.path.join(d, "l4"), "incidents_path": os.path.join(d, "i4")}, clock=clock,
                   enabled=True, verdict=lambda: "calm", background=False)
NEXT = calls_after = cruise.calls_near(SAT + 86400)[0]
T[0] = NEXT[0]


async def refuse(cmd: str):
    if cmd.startswith("getsequence"):
        return {"status": "ok", "data": {"sequence_number": 0, "tip_height": 10}}
    return {"status": "error", "error": {"code": "INSUFFICIENT_FUNDS", "message": "no balance"}}


for _ in range(600):
    asyncio.run(C4.step(refuse, gov))
    T[0] += 1
check(C4.cur["left"] and "refused 5" in C4.cur["note"], "five refusals among the last sends: the ship leaves")
r4 = C4.route("/cruise/incidents")["incidents"][0]
check(r4["kind"] == "refused" and any("INSUFFICIENT_FUNDS" in (e.get("err") or "") for e in r4["tail"]), "and the incident shows the node's answers")
check(len([e for e in C4.logbook if e.get("kind") in cruise.KINDS]) == cruise.REFUSE_STOP, "not one transaction more than that")
b4 = C4.brief(T[0])["now"]
check(b4["phase"] == "gone" and b4["why"] == "refused", "the pages are told it was the refusals, not a stall")

# ---------- the testnet load page counts the passengers apart ----------
L = Load(path=os.path.join(d, "load.json"), clock=lambda: 1_793_804_400.0)
L.sent("cruise")
L.sent("cruise")
L.sent("bot")
s = L.snapshot([])
check(s["cruise"][-1] == 2 and s["now"]["cruise_hour"] == 2 and s["bot"][-1] == 1, "load.py: the passengers' transactions have their own line")

# ---------- the island bot gives its free slots to the ship ----------
I = island.Island(path=os.path.join(d, "island.keys"), daily=20, enabled=True)
calls = []


async def idle(a, g):
    calls.append(1)
    return True


I.idle = idle


async def spin():
    try:
        await asyncio.wait_for(I.run(ask, gov), 3.2)
    except asyncio.TimeoutError:
        pass


asyncio.run(spin())
check(1 <= len(calls) <= 2, f"with no moves waiting, the island bot asks the ship, one slot every {island.SPACING} s ({len(calls)})")

print()
print("all good" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)
