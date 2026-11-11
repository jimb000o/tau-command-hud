"""Unit test of the cruise ships' automatic announcements and reports (no network): the texts written from the
timetable and the last call (MS Dry Run of 4 November 2026: 122 accepted, 8 timeouts logged as refusals by the old
rule, left after 34 minutes), the announcement window, one post per call (also after a crash or a hand-posted one),
the hand-written file only on its own date, one report per visit to the owner's chat, nothing while ships are off.

Run: python test_cruise_crier.py
"""
import json
import os
import re
import sys
import tempfile

TMP = tempfile.mkdtemp()
ART = os.path.join(TMP, "art")
os.makedirs(ART)
from PIL import Image  # noqa: E402
Image.new("RGB", (1600, 900), (40, 120, 160)).save(os.path.join(ART, "isle.jpg"))
json.dump({"scenes": {"island": "isle.jpg"}}, open(os.path.join(ART, "index.json"), "w"))
SHIPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "rabbit", "art", "ships")
os.environ.update(BLOG_ART=ART, BLOG_SHIPS=SHIPS, PUBLIC_DIR=TMP, BLOG_STATE=os.path.join(TMP, "blog.json"), NEWS_AI_KEY="",
                  CHAT_AI_KEY="", TELEGRAM_BOT_TOKEN="", X_API_KEY="", CRUISE_CRIER="true", CRUISE_ANNOUNCE_MINUTES="150")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blog  # noqa: E402
import cruise_crier as cc  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T0 = 1793804400   # Wednesday 4 November 2026, 16:00 German time
V = "2026-11-04-dryrun"
log = [{"t": T0, "visit": V, "ship": "dryrun", "kind": "landed", "verdict": "calm", "plan": 247, "trial": ["book"]}]
for i in range(122):
    log.append({"t": T0 + 10 + i * 16, "visit": V, "kind": "pay", "ok": True, "verdict": "calm", "height": 5500 + i, "ms": 900})
for i in range(8):
    log.append({"t": T0 + 700 + i * 160, "visit": V, "kind": "pay", "ok": False, "err": None, "verdict": "calm"})
log.append({"t": T0 + 2041, "visit": V, "kind": "left", "verdict": "refused", "note": "the node refused 5 of the last 20 passenger transactions"})
summary = {"id": V, "ship": "dryrun", "name": "MS Dry Run", "t0": T0, "landed": True, "end": T0 + 2041,
           "sent": {"pay": 122}, "refused": {"pay": 8}, "skipped": 117, "half": 0, "passengers": 40}
log.append({"t": T0 + 5400, "visit": V, "kind": "visit over", "summary": summary})
NEXT_DRY = T0 + 7 * 86400                    # Wednesday 11 November, 16:00
QUEEN = 1794056400                           # Saturday 7 November, 14:00 German time
check(blog.clock(QUEEN) == "14:00" and blog.local(QUEEN).weekday() == 5, "Saturday 7 November 14:00 German time")

# ---------- the texts ----------
f = blog.facts_of(log, [])
tg, card, x = cc.last_lines(f)
check("accepted 122" in tg and "refused none" in tg and "8 got no answer from our node in time" in tg, "last call: 122 accepted, none refused, 8 timeouts")
check("left after 34 minutes" in tg and "no longer" in tg, "left after 34 minutes, the old brake named as ours")
check(card == "- Last call: 122 accepted, none refused", "card point")
t = cc.texts("dryrun", NEXT_DRY, f)
check(t["date"] == "2026-11-11" and t["card"][0] == "MS Dry Run · today 16:00 German time", "card title with the day's time")
check("from 15:30" in t["telegram"].lower() and "https://node.tauhud.com/cruise/log" in t["telegram"] and "made up" in t["telegram"], "Telegram: horizon time, logbook, honest note")
check("http" not in t["x"] and blog.re.search(r"\.com\b", t["x"]) is None, "X: no link")
import alerts  # noqa: E402
check(alerts.x_len(t["x"]) <= 280 and "made up" in t["x"] and "Wed 11 Nov" in t["x"], "X: within 280, honest, dated (X refuses a repeated text)")
for ship, t0, last in (("dryrun", NEXT_DRY, f), ("queen", QUEEN, None), ("queen", QUEEN + 7 * 86400, f)):
    tt = cc.texts(ship, t0, last)
    words = tt["telegram"] + tt["x"] + " ".join(tt["card"])
    check(not blog.HYPE.search(words) and not blog.BLAME.search(words), f"{ship}: no hype or blame words")
    check(alerts.x_len(tt["x"]) <= 280 and "#TauNet" in tt["x"], f"{ship}: X {alerts.x_len(tt['x'])} of 280 with the tag")
    nums = set(re.findall(r"\d+", re.sub(r"https?://\S+", "", words)))
    allowed = {"12", "90", "40", "120", "122", "8", "34", "11", "4", "7", "14", "13", "15", "16", "30", "00", "2026"}
    check(nums <= allowed, f"{ship}: every number is the timetable's or the logbook's ({sorted(nums - allowed)})")
q = cc.texts("queen", QUEEN, None)
check("first call" in q["telegram"] and q["card"][-2] == "- Every transaction logged with the node's answer, open to all", "first call: said so, no numbers")
check(cc.last_call("dryrun", "2026-11-11-dryrun", ["2026-11-07-queen", V], lambda v: log if v == V else [], []) is not None
      and cc.last_call("dryrun", V, [V], lambda v: log, []) is None, "last call: the same ship's visit before this one")
picture = cc.picture(t, os.path.join(TMP, "p.jpg"))
check(Image.open(picture).size == (1600, 900), "the picture is made (1600x900)")

# ---------- the window ----------
cruise = {"next": {"ship": "queen", "name": "Queen Mempool", "t0": QUEEN}}
check(cc.due_call(cruise, QUEEN - 151 * 60) is None, "not before 11:30")
check(cc.due_call(cruise, QUEEN - 150 * 60) == ("queen", QUEEN), "due at 11:30")
check(cc.due_call(cruise, QUEEN - 29 * 60) is None, "not once she is on the horizon")
check(cc.due_call({"enabled": False}, QUEEN - 60 * 60) is None, "ships switched off: no next call, nothing announced")

# ---------- one post per call ----------
posted, told = [], []
cc.post = lambda tx, pic: posted.append(tx) or ["telegram: posted", "x: posted"]
cc.tell = lambda text: told.append(text) or (True, "")
hand = {"date": "2026-11-07", "telegram": "hand", "x": "hand x", "card": ["a", "b"], "ship": "liner"}
cc.hand_written = lambda ship, t0: {**hand, "written": "by hand"} if blog.local(t0).date().isoformat() == hand["date"] else None
blog.get = lambda path: cruise if path == "/cruise" else ({"incidents": []} if "incidents" in path else {"entries": log, "visits": [V]})
st = cc.state()
check(cc.announce(QUEEN - 2 * 3600, cruise, st) == "2026-11-07-queen" and posted[-1]["telegram"] == "hand", "Saturday 7.11: the hand-written texts go out")
check(cc.announce(QUEEN - 3600, cruise, cc.state()) is None and len(posted) == 1, "and only once")
nxt = {"next": {"ship": "queen", "name": "Queen Mempool", "t0": QUEEN + 7 * 86400}}
cc.announce(QUEEN + 7 * 86400 - 2 * 3600, nxt, cc.state())
check(len(posted) == 2 and posted[-1]["written"] == "auto" and posted[-1]["date"] == "2026-11-14", "a week later: written anew, by itself")
st = cc.state()
st["announced"].pop("2026-11-14-queen")
st["announced"]["2026-11-14-queen"] = {"result": "posting"}
cc.save(st)
check(cc.announce(QUEEN + 7 * 86400 - 3600, nxt, cc.state()) is None, "a crash while posting: never a second post")

# up post … send by hand marks the day
cc.dt = __import__("datetime")
old = cc.dt.datetime


class Fixed(old):
    @classmethod
    def now(cls, tz=None):
        return old.fromtimestamp(NEXT_DRY - 4 * 3600, tz)


cc.dt.datetime = Fixed
cc.main(["mark", "cruise-dry-run"])
cc.dt.datetime = old
dcall = {"next": {"ship": "dryrun", "name": "MS Dry Run", "t0": NEXT_DRY}}
check(cc.announce(NEXT_DRY - 2 * 3600, dcall, cc.state()) is None and len(posted) == 2, "posted by hand that day: not posted again")

# ---------- one report per visit ----------
check(cc.report(T0 + 5400 + 600, cc.state()) == V and len(told) == 1, "the visit over: reported once")
check("MS Dry Run" in told[0] and "122 transactions accepted" in told[0] and "up.sh cruise 2026-11-04-dryrun" in told[0], "report: numbers and the full command")
check(os.path.exists(os.path.join(cc.REPORTS, V + ".json")), "report kept in /state/cruise-reports")
check(cc.report(T0 + 5400 + 1200, cc.state()) is None and len(told) == 1, "not twice")
st = cc.state(); st["reported"] = {}; cc.save(st)
check(cc.report(T0 + 5 * 86400, cc.state()) is None and not told[1:], "first run days later: an old visit is not told")
cc.tell_draft("2026-11-04-dryrun-learnings", "https://tauhud.com/blog/?draft=x")
cc.tell_draft("2026-11-04-dryrun-learnings", "https://tauhud.com/blog/?draft=x")
check(len(told) == 2 and 'up.sh blog publish 2026-11-04-dryrun-learnings"' in told[1], "draft told once with the publish line")
check(any("announced by itself" in s for s in cc.status_lines(QUEEN - 5 * 3600)), "up block names the next announcement")

# ---------- the pirates (Black Sequence, Tuesday 18:00): Telegram only, the chain's refusals, findings never posted ----------
TUE = 1794330000   # Tuesday 10 November 2026, 18:00 German time
check(blog.local(TUE).weekday() == 1 and blog.clock(TUE) == "18:00", "Tuesday 10 November 18:00 German time")
PV = "2026-11-10-pirates"
plog = [{"t": TUE, "visit": PV, "ship": "pirates", "kind": "landed", "verdict": "calm", "plan": 80, "trial": []}]
for i in range(40):
    plog.append({"t": TUE + 30 + i * 60, "visit": PV, "kind": "pay", "ok": True, "verdict": "calm", "height": 900 + i, "ms": 700})
codes = {"overspend": "INSUFFICIENT_FUNDS", "replay": "INVALID_SEQUENCE", "expired": "TX_EXPIRED", "forged": "INVALID_SIGNATURE"}
for i, (k, c) in enumerate(list(codes.items()) * 5):
    plog.append({"t": TUE + 900 + i * 150, "visit": PV, "kind": "trick", "trick": k, "what": k, "ok": False, "right": True, "code": c})
ps = {"id": PV, "ship": "pirates", "name": "Black Sequence", "t0": TUE, "landed": True, "end": TUE + 5400, "sent": {"pay": 40}, "refused": {},
      "skipped": 0, "half": 0, "passengers": 20, "per_min": 12,
      "changed": [{"what": "overspend tries a visit", "from": 6, "to": 4, "because": "the chain refused it with the right answer on 3 visits in a row"}]}
plog.append({"t": TUE + 5400, "visit": PV, "kind": "visit over", "summary": ps})
pf = blog.facts_of(plog, [])
check(pf["pirate tricks"]["tried"] == 20 and pf["pirate tricks"]["refused with the expected answer"] == 20 and pf["refused in all"] == 0,
      "facts: 20 tricks, all refused with the expected answer, and they are no refusals of the ship's payments")
check(pf["the ship changed for its next call"][0]["to"] == 4, "facts: what the ship changed for its next call, and why")
tg, card, _ = cc.last_lines(pf)
check("refused 20 of her pirates' 20 tricks" in tg and "Since then she changed overspend tries a visit from 6 to 4, because" in tg,
      "the next announcement: the tricks refused, and the learning line")
pt = cc.texts("pirates", TUE + 7 * 86400, pf)
check(pt["x"] == "" and pt["on_x"] is False and "🏴" in pt["telegram"] and "made up" in pt["telegram"], "the pirates are announced on Telegram only, honestly")
check(not blog.HYPE.search(pt["telegram"] + " ".join(pt["card"])) and not blog.BLAME.search(pt["telegram"]), "pirates: no hype or blame words")
# they come unannounced: never hours before, only once she is in sight (relay "now", approach), until shortly after she anchors
check(cc.due_call({"next": {"ship": "pirates", "t0": TUE}}, TUE - 150 * 60) is None, "pirates: no announcement at 15:30, even if a relay names them next")
sight = {"now": {"ship": "pirates", "t0": TUE, "phase": "approach"}, "next": {"ship": "dryrun", "t0": TUE + 22 * 3600}}
check(cc.due_call(sight, TUE - 25 * 60) == ("pirates", TUE), "pirates: posted once she is in sight")
check(cc.due_call({**sight, "now": {**sight["now"], "phase": "landing"}}, TUE + 5 * 60) == ("pirates", TUE), "or while she anchors")
check(cc.due_call({**sight, "now": {**sight["now"], "phase": "ashore"}}, TUE + 40 * 60) is None, "not later in the evening")
check("Nobody announced her" in pt["telegram"] and "in sight" in pt["telegram"], "the post says she came unannounced")
check(Image.open(cc.picture(pt, os.path.join(TMP, "pp.jpg"))).size == (1600, 900), "the pirate picture is made (MS Dry Run's painting darkened, a black flag)")
check(any("20 pirate tricks, 20 refused" in n for n in blog.numbers_of(pf)) and any("changed overspend" in n for n in blog.numbers_of(pf)),
      "the blog's post lists the tricks and the change")
# a finding: told privately once, with a ready issue for IDNI and the release line; no draft while it is held
thr = {"t": TUE + 2000, "visit": PV, "i": 33, "kind": "trick", "trick": "overspend", "what": "pays more than the wallet holds", "ok": True,
       "through": True, "hash": "ab" * 32, "expect": ["INSUFFICIENT_FUNDS"], "height": 950, "tx": {"sender_pubkey": "cd" * 48}}
HELD = {"entries": [thr], "released": []}
blog.get = lambda path: HELD if path == "/cruise/held" else cruise
n_told = len(told)
check(cc.held(TUE + 2100, cc.state()) == 1 and len(told) == n_told + 1, "a trick that got through: one private message to the owner")
msg = told[-1]
check("github.com/IDNI/tau-testnet/issues/new?" in msg and "cruise release 2026-11-10-pirates" in msg and "security/advisories/new" in msg
      and "Nothing about it is public" in msg, "with a ready IDNI issue, the private advisory link and the release command")
check(cc.held(TUE + 2200, cc.state()) == 0 and len(told) == n_told + 1, "told once")
HELD["released"] = [PV]
st = cc.state(); st["held_told"] = {}; cc.save(st)
check(cc.held(TUE + 2300, cc.state()) == 0, "released: not told again")
bst = blog.state(); bst["failed_at"] = 0; blog.write_json(blog.STATE, bst)
heldlog = plog + [{"t": TUE + 2000, "visit": PV, "kind": "trick", "held": True, "ok": None}]
calls = []
blog.AI_KEY = "x"
blog.write_draft = lambda vid, now=None: calls.append(vid) or "d"
blog.get = lambda path: {"visits": [PV]} if path == "/cruise/log?n=1" else {"entries": heldlog} if "visit=" in path else {"posts": []}
blog.site_ids = lambda: set()
blog.tick(TUE + 5400 + 4 * 3600)
check(calls == [], "no blog draft while a finding is held back")
heldlog = plog
blog.tick(TUE + 5400 + 4 * 3600)
check(calls == [PV], "once released, the blog writes the visit")

# ---------- fares booked ahead of the call, in escrow ----------
esc = {"escrow": [{"arrival": NEXT_DRY, "called_off": None, "count": {"in escrow": 4, "refund sent": 1}}]}
check(cc.booked_ahead(esc, NEXT_DRY) == 4 and cc.booked_ahead(esc, QUEEN) == 0 and cc.booked_ahead(None, NEXT_DRY) == 0, "bookings ahead: counted for this call only")
check(cc.booked_ahead({"escrow": [{**esc["escrow"][0], "called_off": {"why": "stalled"}}]}, NEXT_DRY) == 0, "none when the call was called off")
ta = cc.texts("dryrun", NEXT_DRY, f, 4)
check("4 passengers paid their fare days ahead" in ta["telegram"] and "at 16:00 the chain hands it to the ship by itself" in ta["telegram"], "Telegram names the fares in escrow")
check(ta["x"] == t["x"] and "days ahead" not in t["telegram"], "X unchanged, and no line without bookings")
check(not blog.HYPE.search(ta["telegram"]) and not blog.BLAME.search(ta["telegram"]), "no hype or blame words in it")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
