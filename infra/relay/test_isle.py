"""Unit test of White Rabbit Key's shared island day (isle.py), no network.

Run: python test_isle.py
"""
import json
import os
import random
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import isle  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


T = [1_793_491_200.0 + 36000]  # 2026-11-01 10:00 UTC
clock = lambda: T[0]  # noqa: E731
path = os.path.join(tempfile.mkdtemp(), "isle.json")
I = isle.Isle(path=path, clock=clock)

# ---------- nobody plays: the islanders keep the island going ----------
s = I.snapshot()
check(s["day"] == "2026-11-01" and s["players"]["campaigns"] == 0 and s["recent"] == [], "a new day starts empty")
evs = []
for _ in range(20):
    T[0] += isle.HOUSE_EVERY
    e = I.house()
    if e:
        evs.append(e)
check(len(evs) == 20 and all(e["h"] == 1 for e in evs), "with nobody playing, the islanders make a move every HOUSE_EVERY seconds, marked as theirs")
check(I.snapshot()["islanders"]["moves"] == 20 and I.snapshot()["players"]["moves"] == 0, "the islanders' moves are counted apart from the players'")
check(len({e["k"] for e in evs}) >= 3 and len({e["c"] for e in evs}) >= 3, "they do different things, all four candidates take part")
check(all(e["k"] in isle.KINDS and e["c"] in isle.CANDS and e["at"] in isle.PLACES for e in evs), "only moves the game knows")
check(I.house() is None, "not twice in one HOUSE_EVERY")
inforce = I.islanders["inforce"]
check(not any(a in isle.LAWS[b][1] for a in inforce for b in inforce), "the islanders' laws in force never contradict each other")

# the same moment gives the same move, so a restart picks up the same day
J = isle.Isle(path="", clock=clock)
K = isle.Isle(path="", clock=clock)
check(J.house() == K.house(), "the islanders' move comes from the clock: the same on a restarted relay")

# ---------- players ----------
ok, d = I.move("1.2.3.4", "game0001", "hana", "law", "boat", "hall")
check(ok and d["counted"], "a player's law is counted")
ok, d = I.move("1.2.3.4", "game0001", "hana", "talk", "school", "market")
s = I.snapshot()
check(s["players"]["campaigns"] == 1 and s["players"]["moves"] == 2 and s["players"]["as"] == {"hana": 1} and s["players"]["laws"] == {"boat": 1},
      "one campaign, two moves, played as Hana, one law passed")
check(s["recent"][0]["h"] == 0 and s["recent"][0]["k"] == "talk", "the newest move first, marked as a player's")
check(I.move("1.2.3.4", "game0001", "rico", "law", "boat", "hall")[0] is False, "only the four candidates")
check(I.move("1.2.3.4", "game0001", "hana", "steal", "boat", "hall")[0] is False, "only the game's kinds of move")
check(I.move("1.2.3.4", "game0001", "hana", "law", "<script>", "hall")[0] is False, "no free text")
check(I.move("1.2.3.4", "g", "hana", "law", "boat", "hall")[0] is False, "a campaign id of 6 to 16 letters and digits")
ok, d = I.end("1.2.3.4", "game0001", "hana", "hana")
check(ok and d["counted"] and I.snapshot()["players"]["wins"] == {"hana": 1} and I.snapshot()["players"]["finished"] == 1, "the election result counts")
ok, d = I.end("1.2.3.4", "game0001", "hana", "tobias")
check(not d["counted"] and d["why"] == "once", "a campaign's result counts once")

# limits per address
for i in range(isle.IP_BURST + 5):
    ok, d = I.move("6.6.6.6", "gameflood", "baako", "talk", "roads", "market")
check(not d["counted"] and d["why"] == "busy", "one address cannot flood the island")
L = isle.Isle(path="", clock=clock, house=False)
for i in range(isle.GAMES_PER_IP):
    T[0] += 10
    L.move("7.7.7.7", f"game{i:04d}", "baako", "talk", "roads", "market")
T[0] += 10
ok, d = L.move("7.7.7.7", "gamextra1", "baako", "talk", "roads", "market")
check(not d["counted"] and d["why"] == "enough" and L.players["campaigns"] == isle.GAMES_PER_IP, "at most GAMES_PER_IP campaigns per address per day")

# when people play, the islanders step back
B = isle.Isle(path="", clock=clock)
T[0] += isle.HOUSE_EVERY
for i in range(isle.FLOOR):
    B.move(f"9.0.0.{i}", f"game{i:04d}", "marisol", "talk", "fish", "market")
check(B.house() is None, "enough players: the islanders make no moves of their own")
T[0] += isle.FLOOR_WINDOW + 1
check(B.house() is not None, "the players gone quiet: the islanders take over again")

# ---------- a restart keeps the day, a new day starts empty ----------
I.dirty = True
I.save()
R = isle.Isle(path=path, clock=clock)
check(R.players["campaigns"] == I.players["campaigns"] and R.islanders["moves"] == I.islanders["moves"] and len(R.recent) == len(I.recent),
      "a restarted relay keeps the day's numbers")
check(R.recent[0] == I.recent[0], "and the newest move stays first")
T[0] += 86400
check(R.snapshot()["players"]["campaigns"] == 0 and R.snapshot()["day"] == "2026-11-02", "the count starts again each UTC day")
check(I.route("/isle")["day"] == "2026-11-02" and I.route("/island") is None, "GET /isle")

# ---------- at scale: thousands of players, the same small message ----------
S = isle.Isle(path="", clock=clock)
rnd = random.Random(1)
start = time.perf_counter()
for p in range(5000):
    who = rnd.choice(sorted(isle.CANDS))
    for m in range(15):
        k = rnd.choice(isle.KINDS)
        S.move(f"10.{p // 250}.{p % 250}.{m % 3}", f"g{p:07d}", who, k, rnd.choice(sorted(isle.LAWS)), rnd.choice(isle.PLACES))
    S.end(f"10.{p // 250}.{p % 250}.9", f"g{p:07d}", who, rnd.choice(sorted(isle.CANDS)))
took = time.perf_counter() - start
snap = S.snapshot()
size = len(json.dumps(snap, separators=(",", ":")))
check(snap["players"]["campaigns"] == 5000 and snap["players"]["finished"] == 5000 and snap["players"]["moves"] == 75000, "5,000 campaigns, 75,000 moves counted")
check(size < 3000, f"the pushed summary stays small at 5,000 players ({size} bytes)")
check(took < 5, f"counting 80,000 messages takes {took:.2f} s")
check(S.house() is None, "with thousands playing, the islanders stay out of the way")

B = isle.Isle(path=os.path.join(tempfile.mkdtemp(), "isle.json"), clock=lambda: T[0]) if "tempfile" in dir() else None
if B is not None:
    B.move("1.1.1.1", "gamebuild", "hana", "gift", "roof", "school"); B.move("1.1.1.1", "gamebuild", "hana", "gift", "roof", "school"); B.move("1.1.1.1", "gamebuild", "hana", "gift", "lamp", "book")
    check(B.snapshot()["built"] == {"roof": 2, "lamp": 1}, "what the players buy for the island is counted")
    check(B.move("1.1.1.1", "gamebuild", "hana", "gift", "-", "bar")[1]["counted"] and B.snapshot()["built"] == {"roof": 2, "lamp": 1}, "a treat is a gift too, but builds nothing")
    B.save(); B2 = isle.Isle(path=B.path, clock=lambda: T[0] + 200000)
    check(B2.snapshot()["built"] == {"roof": 2, "lamp": 1} and B2.snapshot()["players"]["moves"] == 0, "the island keeps what was built past midnight")

# ---------- the week: a governor and the laws of the week, Monday to Sunday on the island's clock ----------
T[0] = 1_793_491_200.0 + 36000   # Sunday 2026-11-01 10:00 UTC, the last day of week 44
W = isle.Isle(path=os.path.join(tempfile.mkdtemp(), "isle.json"), clock=clock, house=False)
check(W.snapshot()["week"]["id"] == "2026-W44" and W.snapshot()["week"]["from"] == "2026-10-26" and W.snapshot()["last"] is None, "a week runs Monday to Sunday; no governor before a week is over")
W.end("2.2.2.2", "gameweek01", "hana", "hana", "boat,copy")
W.end("2.2.2.2", "gameweek02", "baako", "hana", "boat,copy,night")
W.end("2.2.2.2", "gameweek03", "tobias", "tobias", "night,boat,quiet")
check(W.end("2.2.2.2", "gameweek04", "tobias", "tobias", "x;y")[0] is False, "the laws at the end: only ids, commas")
w = W.snapshot()["week"]
check(w["finished"] == 3 and w["wins"] == {"hana": 2, "tobias": 1} and w["laws"] == {"boat": 3, "copy": 2, "night": 2, "quiet": 1}, "the week counts finished campaigns, wins and the laws in force at the end")
T[0] = 1_793_491_200.0 + 86400 - 1800   # 23:30 UTC Sunday = 00:30 Monday in Berlin: week 45 begins while the UTC day goes on
s = W.snapshot()
check(s["week"]["id"] == "2026-W45" and s["week"]["finished"] == 0 and s["day"] == "2026-11-01", "at Monday 00:00 on the island's clock a new week starts, before the UTC day ends")
check(s["last"]["governor"] == "hana" and s["last"]["laws"] == ["boat", "copy", "night"] and s["last"]["finished"] == 3, "last week decides: Hana governs, the three laws most often in force, none contradicting a stronger one (quiet lost to night)")
check(W.islanders["inforce"] == ["boat", "copy", "night"], "the islanders start the week with the island's laws")
W.dirty = True; W.save()
W2 = isle.Isle(path=W.path, clock=clock)
check(W2.snapshot()["last"]["governor"] == "hana" and W2.snapshot()["week"]["id"] == "2026-W45", "a restart keeps the governor and the running week")
T[0] += 7 * 86400
check(W2.snapshot()["week"]["id"] == "2026-W46" and W2.snapshot()["last"]["governor"] == "hana", "a week nobody finished changes nothing: the governor stays")
check(isle.verdict(isle.week_of(T[0])) is None, "no verdict without a finished campaign")
# the island's clock without the system's zone files
real = isle.berlin
for t in (1_774_745_000.0, 1_793_491_200.0 + 82800, 1_761_440_000.0):   # a day in March 2026 after the change, Sunday 23:00 UTC, late October before the change
    import datetime as dt
    try:
        from zoneinfo import ZoneInfo
        want = dt.datetime.fromtimestamp(t, ZoneInfo("Europe/Berlin")).date()
    except Exception:
        want = None
    import builtins
    imp = builtins.__import__
    builtins.__import__ = lambda n, *a, **k: (_ for _ in ()).throw(ImportError(n)) if n == "zoneinfo" else imp(n, *a, **k)
    try:
        got = isle.berlin(t)
    finally:
        builtins.__import__ = imp
    check(want is None or got == want, f"the island's day without zone files: {got} for {t}")

# ---------- the players' board: test wallets, counted only once they signed from that address ----------
T[0] = 1_793_491_200.0 + 36000 + 14 * 86400   # a Sunday two weeks on, 10:00 UTC
B = isle.Isle(path=os.path.join(tempfile.mkdtemp(), "isle.json"), clock=clock, house=False)
wa, wb, wc = "a" * 92 + "0001", "b" * 92 + "0002", "c" * 92 + "0003"
ok, d = B.move("9.9.9.1", "boardg01", "hana", "law", "boat", "hall", wa)
check(ok and d["counted"] and d["listed"] is False and B.snapshot()["board"]["busy"] == [], "a wallet that never signed from here is not on the board, the move still counts for the island")
B.saw("9.9.9.1", wa)
ok, d = B.move("9.9.9.1", "boardg01", "hana", "talk", "school", "market", wa)
s = B.snapshot()["board"]
check(d["listed"] is True and s["busy"][0]["moves"] == 2 and s["busy"][0]["laws"] == 1 and s["busy"][0]["as"] == "hana", "once it signed, the campaign's earlier moves join it on the board")
check(s["busy"][0]["id"] == "aaaaaa…0001" and "a" * 20 not in json.dumps(s), "the board shows the short form only")
check(B.move("9.9.9.2", "boardg02", "tobias", "talk", "music", "market", wa)[1]["listed"] is False, "someone else's wallet from another address does not count")
B.saw("9.9.9.1", wb)
check(B.move("9.9.9.1", "boardg01", "hana", "talk", "school", "market", wb)[1]["listed"] is False, "a campaign stays with the first wallet it was seen with")
check(B.move("9.9.9.1", "boardg01", "hana", "talk", "school", "market", "x" * 96)[0] is False, "a wallet is 96 hex characters or -")
B.saw("9.9.9.3", wc)
for i in range(5):
    B.move("9.9.9.3", "boardg03", "baako", "talk", "roads", "market", wc)
ok, d = B.end("9.9.9.3", "boardg03", "baako", "marisol", "boat", wc, "3", "-")
ok, d = B.end("9.9.9.1", "boardg01", "hana", "hana", "boat,lunch", wa, "7", "reform")
s = B.snapshot()["board"]
check([r["id"][:6] for r in s["best"]] == ["aaaaaa", "cccccc"] and s["best"][0]["won"] == 1 and s["best"][0]["votes"] == 7 and s["best"][0]["goal"] == "reform",
      "best results: an election won first, then votes")
check([r["id"][:6] for r in s["busy"]] == ["cccccc", "aaaaaa"] and s["busy"][0]["moves"] == 5, "most active: most moves first")
check(s["ever"][0]["won"] == 1 and s["ever"][0]["played"] == 1 and s["ever"][0]["goals"] == 1 and s["everWallets"] == 2, "all time: elections won, campaigns, ambitions")
B.saw("9.9.9.1", wa)
B.end("9.9.9.1", "boardg09", "hana", "tobias", "-", wa, "2", "-")
check(B.snapshot()["board"]["best"][0]["votes"] == 7 and B.board["all"][wa]["played"] == 1, "the week keeps a wallet's first finished campaign; a replay neither improves nor counts twice")
check(B.end("9.9.9.1", "boardg10", "hana", "hana", "-", wa, "11", "-")[0] is False and B.end("9.9.9.1", "boardg10", "hana", "hana", "-", wa, "5", "boss")[0] is False, "votes 0-10, a known ambition or -")
st = B.standing(wc)["board"]
check(st["me"]["best"] == 2 and st["me"]["busy"] == 1 and st["me"]["ever"] == 2 and st["me"]["id"] == "cccccc…0003", "a wallet can ask where it stands")
check(B.standing("-")["board"]["me"] is None and B.route("/isle/board")["board"]["best"][0]["n"] == 1, "GET /isle/board, without a wallet")
T[0] += isle.SEEN_FOR + 60
check(B.move("9.9.9.3", "boardg03", "baako", "talk", "roads", "market", wc)[1]["listed"] is False, "a signature from here counts SEEN_FOR seconds, then the wallet must sign again")
B.dirty = True; B.save()
B2 = isle.Isle(path=B.path, clock=clock, house=False)
check(B2.snapshot()["board"]["best"][0]["votes"] == 7, "a restart keeps the board")
T[0] += 86400   # Monday: the governor's count, a new week on the board
s = B2.snapshot()["board"]
check(s["best"] == [] and s["busy"] == [] and s["prev"]["best"][0]["id"][:6] == "aaaaaa" and s["ever"][0]["won"] == 1, "a new week starts an empty board; last week's best and all time stay")
B2.saw("9.9.9.1", wa)
B2.end("9.9.9.1", "boardg11", "hana", "hana", "-", wa, "6", "-")
check(B2.board["all"][wa]["won"] == 2 and B2.snapshot()["board"]["best"][0]["votes"] == 6, "a new week, a new campaign counts")

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)
