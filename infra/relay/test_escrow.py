"""Unit test of the bookings ahead of a call (cruise.py escrow), no network: plan, booking, withdrawal, call-off refunds,
release at arrival, the logbook's "paid out" / "refunded".

Run: python test_escrow.py
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
import island  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


WED = cruise.berlin_t(dt.date(2026, 11, 11), 16)
check(WED == 1794409200, "MS Dry Run: Wednesday 11 November 2026, 16:00 in Germany")
B = cruise.escrow_plan("dryrun", WED, WED - 4 * 86400)
check(B == cruise.escrow_plan("dryrun", WED, WED - 4 * 86400), "the same call plans the same bookings")
check(len(B) == 5 and len({b["p"] for b in B}) == 5 and all(b["amount"] == 10 for b in B), "five passengers book the fare, 10 test AGRS each")
check(all(WED - cruise.ESCROW_AHEAD <= b["at"] < WED - cruise.ESCROW_CLOSE for b in B), "booked between three days and two hours before the arrival")
wd = [b for b in B if b.get("withdraw_at")]
check(len(wd) == 1 and wd[0]["at"] < wd[0]["withdraw_at"] < WED - cruise.CALL_OFF, "one of them withdraws again, before the call-off check")
check(cruise.escrow_plan("dryrun", WED, WED - 3600) == [], "too close to the arrival: no bookings ahead")
check(not cruise.SHIPS["queen"].get("escrow"), "Queen Mempool takes no bookings ahead")

# ---------- a fake node with an escrow book ----------
T = [0.0]
PARKS: dict = {}    # id -> entry
BY_HASH: dict = {}
SEQ: dict = {}
LOG: list = []
DOWN = [False]


def sweep():
    for p in PARKS.values():
        if p["status"] == "open" and T[0] >= p["release_at_time"]:
            p["status"] = "released"


async def ask(cmd: str):
    sweep()
    name, _, rest = cmd.partition(" ")
    LOG.append(name)
    if DOWN[0] and name == "sendtx":
        return None
    if name == "getsequence":
        return {"status": "ok", "data": {"sequence_number": SEQ.get(rest, 0), "tip_height": 5000}}
    if name == "getretractables":
        pk = rest.split()[0]
        return {"status": "ok", "data": {"retractables": [p for p in PARKS.values() if p["sender_pubkey"] == pk and p["status"] == "open"], "mempool": []}}
    if name == "gettxstatus":
        rid = BY_HASH.get(rest)
        return {"status": "ok", "data": {"status": "confirmed", "retractable": {"id": rid, "status": PARKS[rid]["status"]}} if rid else {"status": "unknown"}}
    if name == "getretractable":
        p = PARKS.get(rest)
        return {"status": "ok", "data": {"retractable_id": rest, "status": p["status"]}} if p else {"status": "error", "error": "RETRACTABLE_UNKNOWN"}
    if name == "sendtx":
        tx = json.loads(rest)
        h = hashlib.sha256(rest.encode()).hexdigest()
        SEQ[tx["sender_pubkey"]] = SEQ.get(tx["sender_pubkey"], 0) + 1
        if tx["tx_type"] == "retractable_transfer":
            if tx["expiration_time"] >= tx["release_at_time"]:
                return {"status": "error", "error": "DEADLINE_AFTER_RELEASE"}
            rid = hashlib.sha256(("id" + rest).encode()).hexdigest()
            PARKS[rid] = {"retractable_id": rid, "sender_pubkey": tx["sender_pubkey"], "recipient_pubkey": tx["recipient_pubkey"],
                          "amount": tx["amount"], "release_at_time": tx["release_at_time"], "status": "open"}
            BY_HASH[h] = rid
        elif tx["tx_type"] == "retract_transfer":
            p = PARKS.get(tx["retractable_id"])
            if not p or p["status"] != "open":
                return {"status": "error", "error": "UNKNOWN_RETRACTABLE"}
            if tx["fee_limit"] != "0":
                return {"status": "error", "error": "a retract is feeless"}
            p["status"] = "retracted"
        else:
            return {"status": "error", "error": "not expected here: " + tx["tx_type"]}
        return {"status": "ok", "data": {"ok": True, "tx_hash": h}}
    return None


gov = lambda: {"consensus_rules": "o9[t]:bv[24] = { #x0a }"}  # noqa: E731
STATE = ["calm"]
d = tempfile.mkdtemp()
keys = os.path.join(d, "cruise.keys")


def ship(tag, enabled=True):
    return cruise.Cruise(keys_path=keys, log_path=os.path.join(d, tag + ".log"), state_path=os.path.join(d, tag + ".state"),
                         incidents_path=os.path.join(d, tag + ".inc"), clock=lambda: T[0], enabled=enabled,
                         verdict=lambda: STATE[0], background=False)


def run(C, until, step=20.0):
    n = 0
    while T[0] < until:
        if asyncio.run(C.step(ask, gov)):
            n += 1
        T[0] += step
    return n


def lines(C, kind):
    return [e for e in C.logbook if e.get("kind") == kind]


# ---------- a call that goes ahead: four paid out, one refunded ----------
T[0] = WED - 4 * 86400
C = ship("a")
check(C.till.get("dryrun") and C.till["dryrun"] not in C.pk.values() and C.till["dryrun"] not in island.PLACES.values()
      and C.who[C.till["dryrun"]] == "dryrun", "the ship has a till of its own, tagged as simulated")
run(C, WED - cruise.ESCROW_AHEAD + 60, 600)
vid = cruise.visit_id(WED, "dryrun")
check(vid in C.escrow and len(C.escrow[vid]["bookings"]) == 5, "three days before the arrival the bookings open")
run(C, WED - cruise.ESCROW_CLOSE, 60)
parks = [p for p in PARKS.values()]
check(len(parks) == 5 and all(p["recipient_pubkey"] == C.till["dryrun"] and p["release_at_time"] == WED and p["amount"] == 10 for p in parks),
      "five bookings in escrow for the ship's till, released at the arrival")
check(sum(1 for p in parks if p["status"] == "retracted") == 1, "and one passenger took theirs back")
check(len(lines(C, "book ahead")) == 5 and len(lines(C, "refund")) == 1 and all("tx" in e and e["ok"] for e in lines(C, "book ahead")),
      "the logbook has every booking and the withdrawal, signed")
C2 = ship("a")   # a restart in between keeps the bookings
check(C2.escrow[vid]["bookings"] == C.escrow[vid]["bookings"], "a restart keeps the bookings and their state")
C = C2
run(C, WED - 30 * 60, 120)
check(not C.escrow[vid].get("off"), "a calm testnet: the call goes ahead")
T[0] = WED + cruise.UNRELEASED + 5
asyncio.run(C.step(ask, gov))
res = C.escrow[vid].get("result") or {}
check(res == {"paid out": 4, "refunded": 1}, f"after the arrival: 4 paid out to the till, 1 refunded ({res})")
st = lines(C, "escrow")
check(sorted(e["status"] for e in st if e.get("p") is not None) == ["paid out"] * 4 + ["refunded"], "the logbook shows each booking as paid out or refunded")
view = C.route("/cruise")["escrow"][0]
check(view["visit"] == vid and view["settled"] and view["count"] == {"paid out": 4, "refunded": 1} and view["till"] == C.till["dryrun"],
      "GET /cruise: the bookings of the call and how each ended")
check("escrow" in C.route("/cruise/log", "n=5"), "GET /cruise/log carries them too")

# ---------- the kill switch: the server refunds every booking before the arrival ----------
WED2 = WED + 7 * 86400
PARKS.clear()
BY_HASH.clear()
T[0] = WED2 - 2 * 86400
run(C, WED2 - 1 * 86400, 300)
vid2 = cruise.visit_id(WED2, "dryrun")
held = sum(1 for b in C.escrow[vid2]["bookings"] if b["status"] == "in escrow")
check(held >= 3, f"bookings for the next call are in escrow ({held})")
OFF = ship("a", enabled=False)   # CRUISE_ENABLED=0 and a restart
check(OFF.ready and not OFF.enabled, "switched off with bookings open: the wallets are still loaded, to refund them")
run(OFF, WED2 - cruise.ESCROW_CLOSE, 60)
e2 = OFF.escrow[vid2]
check(e2["off"] and e2["off"]["why"] == "the ships are switched off" and lines(OFF, "called off"), "the call is called off, and the logbook says why")
check(all(p["status"] == "retracted" for p in PARKS.values()), "every booking is taken back")
check(all(b["status"] in ("refund sent", "not booked") for b in e2["bookings"]), "planned bookings no longer go out")
check(OFF.brief(T[0]).get("next") is None, "switched off: no ship announced")
T[0] = WED2 + cruise.UNRELEASED + 5
asyncio.run(OFF.step(ask, gov))
check(set((e2.get("result") or {})) <= {"refunded", "not booked"} and e2["result"].get("refunded") == held, f"after the arrival: all refunded ({e2.get('result')})")

# ---------- a stalled testnet before the arrival calls it off; a refund too late is paid out ----------
WED3 = WED2 + 7 * 86400
PARKS.clear()
BY_HASH.clear()
C = ship("c")
T[0] = WED3 - 3 * 86400
run(C, WED3 - cruise.ESCROW_CLOSE, 300)
vid3 = cruise.visit_id(WED3, "dryrun")
n3 = sum(1 for p in PARKS.values() if p["status"] == "open")
STATE[0] = "stalled"
DOWN[0] = True   # and the node does not answer one refund in time
run(C, WED3 - cruise.CALL_OFF + 10, 30)
check(C.escrow[vid3]["off"] and "stalled" in C.escrow[vid3]["off"]["why"], "a stall 20 minutes before the arrival calls the call off")
run(C, WED3 - cruise.RETRACT_MARGIN + 30, 5)
check(all(b.get("late") or "refund" in (b.get("note") or "") for b in C.escrow[vid3]["bookings"] if b["status"] != "refunded" and not b.get("withdraw_at")),
      "a refund the node does not take in time is given up at RETRACT_MARGIN, with a note")
check(not any(e.get("kind") == "refund" and e["t"] >= WED3 - cruise.RETRACT_MARGIN for e in C.logbook), "nothing is sent after that margin")
DOWN[0] = False
STATE[0] = "calm"
run(C, WED3 + 5 * 60, 10)
check(C.cur and C.cur["left"] and C.cur["note"].startswith("no landing: called off") and not C.cur["landed"], "the ship does not land")
check(C.brief(T[0])["now"]["why"] == "no landing", "and the pages say so")
T[0] = WED3 + cruise.UNRELEASED + 5
asyncio.run(C.step(ask, gov))
r3 = C.escrow[vid3].get("result") or {}
check(r3.get("paid out", 0) + r3.get("refunded", 0) == 5 and r3.get("paid out", 0) == n3,
      f"each booking ends paid out or refunded as the chain has it: the unanswered refunds were too late ({r3})")

# ---------- privacy: no key in the logbook or the state ----------
blob = open(os.path.join(d, "a.log")).read() + open(os.path.join(d, "a.state")).read()
sks = json.load(open(keys))
check(not any(v["sk"] in blob for v in sks.values()), "no key in the logbook or the state file")

print()
print("all good" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)
