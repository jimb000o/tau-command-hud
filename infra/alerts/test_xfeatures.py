import json
import os
import tempfile
import unittest
from datetime import datetime

os.environ.setdefault("STATE_PATH", os.path.join(tempfile.mkdtemp(), "alerts.json"))
import xfeatures as X  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
T = lambda s: datetime.fromisoformat(s).timestamp()   # noqa: E731  (German time in the tests: +01:00 in November)

GOOD = {"id": "rabbit-walkers", "account": "hud", "from": "2026-11-16T11:00:00Z",
        "text": "Every wallet walks on the island now.\n\nClick one to read it from the chain.\n\n#TauNet $AGRS",
        "film": {"url": "https://tauhud.com/rabbit/", "steps": [["wait", 1000]]}}


class Plan(unittest.TestCase):
    def test_the_repositorys_plan_keeps_the_rules(self):
        updates = json.load(open(os.path.join(ROOT, "assets", "updates.json")))
        plan = json.load(open(os.path.join(ROOT, "assets", "x-features.json")))
        got = X.specs(updates, plan)
        self.assertTrue(got)
        for p in got:
            self.assertEqual(p["problems"], [], p.get("id"))

    def test_updates_entry_without_from_starts_on_its_day(self):
        p = X.specs([{"on": "2026-11-16", "x": {k: v for k, v in GOOD.items() if k != "from"}}], None)[0]
        self.assertEqual(p["at"], T("2026-11-16T08:00:00+00:00"))

    def test_slop_links_tags_and_length_are_refused(self):
        def probs(**kw):
            return X.problems({**GOOD, **kw})
        self.assertEqual(probs(), [])
        self.assertTrue(any("hype" in w for w in probs(text="Excited to announce 🚀\n\nnew\n\n#TauNet $AGRS")))
        self.assertTrue(any("links" in w for w in probs(text="New\n\nhttps://tauhud.com\n\n#TauNet $AGRS")))
        self.assertTrue(any("ends with" in w for w in probs(text="New\n\nsee it")))
        self.assertTrue(any("$AGRS" in w for w in probs(account="agorzilla", text="New\n\nsee\n\n#TauNet $AGRS")))
        self.assertTrue(any("280" in w for w in probs(text="x" * 300 + "\n\n#TauNet $AGRS")))
        self.assertTrue(any("blank line" in w for w in probs(text="One line only #TauNet $AGRS")))
        self.assertTrue(any("film" in w for w in probs(film=None)))
        for claim in ("You cannot lose your test AGRS", "Risk-free", "A guaranteed result", "Completely safe", "Keys that cannot be stolen"):
            self.assertTrue(any("promise" in w for w in probs(text=claim + "\n\nmore\n\n#TauNet $AGRS")), claim)
        self.assertTrue(any("twice" in w for w in X.specs(None, {"posts": [GOOD, GOOD]})[1]["problems"]))


class Loop(unittest.TestCase):
    def run_step(self, now, d, cut=lambda pid: ("/f/" + pid + ".mp4", ""), told=None):
        told = [] if told is None else told
        filmed = []
        X.step(now, X.specs(None, {"posts": [GOOD]}), d, film=lambda p: filmed.append(p["id"]),
               cutter=cut, teller=lambda msg, v: told.append((msg, v)) or (True, ""))
        return filmed, told

    def test_draft_film_offer_never_post(self):
        d = {"drafts": {}, "sent": []}
        self.assertEqual(self.run_step(T("2026-11-16T10:00:00+00:00"), d), ([], []))   # not yet
        filmed, told = self.run_step(T("2026-11-16T11:05:00+00:00"), d)
        self.assertEqual(filmed, ["rabbit-walkers"])
        self.assertEqual(d["drafts"]["rabbit-walkers"]["state"], "offered")
        self.assertIn("up.sh x send rabbit-walkers", told[0][0])
        self.assertIn("nothing posted", told[0][0])
        self.assertEqual(told[0][1], "/f/rabbit-walkers.mp4")
        self.assertEqual(d["sent"], [])
        filmed, told = self.run_step(T("2026-11-16T12:00:00+00:00"), d)   # offered once
        self.assertEqual((filmed, told), ([], []))

    def test_no_message_at_night_and_old_drafts_expire(self):
        d = {"drafts": {}, "sent": []}
        _, told = self.run_step(T("2026-11-16T22:30:00+00:00"), d)   # 23:30 German time
        self.assertEqual(told, [])
        self.assertEqual(d["drafts"]["rabbit-walkers"]["state"], "filmed")
        self.run_step(T("2026-11-19T12:00:00+00:00"), d)
        self.assertEqual(d["drafts"]["rabbit-walkers"]["state"], "expired")

    def test_a_failed_film_still_offers_the_words(self):
        d = {"drafts": {}, "sent": []}
        _, told = self.run_step(T("2026-11-16T11:05:00+00:00"), d, cut=lambda pid: (None, "not fit to film: header"))
        self.assertIn("no film: not fit to film", told[0][0])
        self.assertIsNone(told[0][1])


class Room(unittest.TestCase):
    NONE = {"hud": {}, "agorzilla": {}}

    def test_caps_per_account(self):
        now = T("2026-11-18T12:00:00+01:00")   # a Wednesday, before the ship hours
        d = {"sent": [{"account": "hud", "at": now - 3600}]}
        self.assertTrue(any("today" in w for w in X.room("hud", d, now, hand=True, other=self.NONE)))
        d = {"sent": [{"account": "hud", "at": now - k * 86400} for k in (1, 2, 3)]}
        self.assertTrue(any("7 days" in w for w in X.room("hud", d, now, hand=True, other=self.NONE)))
        self.assertEqual(X.room("agorzilla", d, now, hand=True, other=self.NONE), [])
        d = {"sent": [{"account": "agorzilla", "at": now - k * 86400} for k in (1, 2)]}
        self.assertTrue(X.room("agorzilla", d, now, hand=True, other=self.NONE))

    def test_other_services_counts(self):
        now = T("2026-11-18T12:00:00+01:00")
        full = {"hud": {"day": "2026-11-18", "today": 5}, "agorzilla": {"x_day": "2026-11-18", "x_n": 2}}
        self.assertTrue(X.room("hud", {"sent": []}, now, hand=True, other=full))
        self.assertTrue(X.room("agorzilla", {"sent": []}, now, hand=True, other=full))

    def test_ship_hours_unless_by_hand_now(self):
        sat = T("2026-11-21T14:30:00+01:00")
        X.CRUISE_ON = True
        self.assertTrue(any("cruise" in w for w in X.room("agorzilla", {"sent": []}, sat, other=self.NONE)))
        self.assertEqual(X.room("agorzilla", {"sent": []}, sat, hand=True, other=self.NONE), [])
        X.CRUISE_ON = False
        self.assertEqual(X.room("agorzilla", {"sent": []}, sat, other=self.NONE), [])
        X.CRUISE_ON = True


class Week(unittest.TestCase):
    def test_week_lines_for_the_sunday_post(self):
        d = {"sent": [{"account": "hud", "at": T("2026-11-16T12:00:00+01:00"), "url": "https://x.com/TauHUDcom/status/1",
                       "text": "Every wallet walks.\n\nmore\n\n#TauNet $AGRS"},
                      {"account": "agorzilla", "at": T("2026-11-24T20:00:00+01:00"), "url": "u", "text": "Next week"}]}
        got = X.week_lines(d, 2026, 47)
        self.assertEqual([g["headline"] for g in got], ["Every wallet walks."])
        self.assertEqual(got[0]["handle"], "TauHUDcom")


if __name__ == "__main__":
    unittest.main()
