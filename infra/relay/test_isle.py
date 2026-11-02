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

print("all ok" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)
