"""python -m unittest test_simpredict  (no network, no node)"""
import calendar
import os
import tempfile
import unittest

from simpredict import SimPredict, bucket_of, score, slot_open

DAY0 = float(calendar.timegm((2026, 10, 28, 0, 0, 0)))
TOK = "ab" * 16


class Clock:
    def __init__(self, t): self.t = t
    def __call__(self): return self.t


class Votes:
    def __init__(self): self.items = {}
    def snapshot(self, voter=None): return {"day": "2026-10-28", "items": self.items}


class SimPredictTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "p.json")
        self.clock, self.votes = Clock(DAY0 + 600), Votes()     # 00:10 UTC: round 0 (00:20) is open
        self.p = SimPredict(self.path, self.votes, self.clock, names=lambda a, b: f"N{a}-{b}")

    def put(self, token=TOK, item="slot:0", come="1", n="2", ip="1.1.1.1", a=1, b=2, c=3):
        return self.p.route("/sim/predict", f"item={item}&voter={token}&a={a}&b={b}&c={c}&come={come}&n={n}", ip)

    def test_slot_times(self):
        self.assertEqual(slot_open(DAY0, 0), DAY0 + 20 * 60)
        self.assertEqual(slot_open(DAY0, 23), DAY0 + 23 * 3600 + 20 * 60)

    def test_buckets_and_score(self):
        self.assertEqual([bucket_of(n) for n in (0, 1, 2, 3, 5, 6, 10, 11, 20, 21, 500)], [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertEqual(score({"come": True, "n": 2}, True, 4), 5)
        self.assertEqual(score({"come": True, "n": 1}, True, 4), 3)
        self.assertEqual(score({"come": False, "n": 0}, True, 4), 0)

    def test_guess_scored_after_ballot(self):
        code, body = self.put()
        self.assertEqual(code, 200)
        self.assertEqual(body["open"], "slot:0")
        self.assertEqual(body["me"]["points"], 0)
        # a changed mind before the close replaces the guess
        self.assertEqual(self.p.route("/sim/predict", f"item=slot%3A0&voter={TOK}&a=1&b=2&c=3&come=1&n=3", "1.1.1.1")[0], 200)   # as URLSearchParams sends it
        self.clock.t = DAY0 + 20 * 60 + 1                     # ballot open: guesses closed
        code, body = self.put(n="2")
        self.assertEqual(code, 409)
        self.votes.items["slot:0"] = {"yes": 5, "no": 2, "opens": DAY0 + 1200, "closes": DAY0 + 1620, "outcome": "yes"}
        self.clock.t = DAY0 + 1700
        code, body = self.p.route("/sim/predictions", f"voter={TOK}", "1.1.1.1")
        self.assertEqual(code, 200)
        r = [x for x in body["rounds"] if x["item"] == "slot:0"][0]
        self.assertEqual(r["result"]["voters"], 7)
        self.assertEqual(r["mine"]["points"], 2 + 3)            # 7 voters is bucket 3, the changed guess
        self.assertEqual(body["board"][0]["name"], "N1-2")
        self.assertNotIn(TOK, str(body))                        # tokens never leave the relay

    def test_no_and_none(self):
        self.put(come="0", n="0")
        self.put(token="cd" * 16, come="1", n="0", a=4)
        self.votes.items["slot:0"] = {"yes": 0, "no": 0, "closes": DAY0 + 1620, "outcome": "none"}   # nobody voted: the rule comes
        self.clock.t = DAY0 + 1700
        body = self.p.summary()
        self.assertEqual([r["points"] for r in body["board"]], [5, 3])

    def test_limits(self):
        self.assertEqual(self.put(item="slot:1")[0], 409)        # only the next round
        self.assertEqual(self.put(token="xyz")[0], 400)
        self.assertEqual(self.put(n="9")[0], 400)
        for i in range(10):
            self.assertEqual(self.put(token=f"{i:032x}", ip="2.2.2.2")[0], 200)
            self.clock.t += 2
        self.assertEqual(self.put(token="f" * 32, ip="2.2.2.2")[0], 429)

    def test_day_rolls_and_keeps_yesterday(self):
        self.put()
        self.votes.items["slot:0"] = {"yes": 1, "no": 0, "closes": DAY0 + 1620, "outcome": "yes"}
        self.clock.t = DAY0 + 1700
        self.p.summary()
        self.clock.t = DAY0 + 86400 + 60
        body = self.p.summary()
        self.assertEqual(body["day"], "2026-10-29")
        self.assertEqual(body["board"], [])
        code, y = self.p.route("/sim/predictions", "day=2026-10-28", "1.1.1.1")
        self.assertEqual((code, y["board"][0]["points"]), (200, 3))   # yes right, 1 voter is the bucket next to 3-5
        again = SimPredict(self.path, self.votes, self.clock)   # survives a restart
        self.assertEqual(again.state["yesterday"]["day"], "2026-10-28")

    def test_with_the_real_ballot(self):
        from simvotes import SimVotes
        votes = SimVotes(os.path.join(self.dir, "v.json"), clock=self.clock)
        p = SimPredict(os.path.join(self.dir, "p2.json"), votes, self.clock)
        p.route("/sim/predict", f"item=slot:0&voter={TOK}&a=1&b=2&c=3&come=0&n=1", "1.1.1.1")
        self.clock.t = DAY0 + 1200 + 5                           # 00:20:05, the ballot is open
        for i, yes in enumerate((0, 0, 1)):
            votes.vote("slot:0", f"{i:032x}", bool(yes), 1, 1, 1, f"9.9.9.{i}")
        self.clock.t = DAY0 + 1200 + 421                         # closed: two no, one yes
        body = p.summary(TOK)
        r = [x for x in body["rounds"] if x["item"] == "slot:0"][0]
        self.assertEqual((r["result"]["come"], r["result"]["voters"], r["mine"]["points"]), (False, 3, 2 + 1))
        self.assertEqual(body["open"], "slot:1")

    def test_other_paths_pass(self):
        self.assertIsNone(self.p.route("/status", "", "1.1.1.1"))


if __name__ == "__main__":
    unittest.main()
