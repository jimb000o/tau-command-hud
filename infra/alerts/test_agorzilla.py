import json
import os
import tempfile
import unittest

import agorzilla as A

LATEST = {"stage_name": "Little one", "lived": 2,
          "open": {"n": 2, "category": "Aura", "options": ["Gold", "Pearl", "Ice"]},
          "rounds": [{"n": 0, "category": "Pendant light", "options": ["White", "Rose", "Blue"], "tally": [4, 9, 2], "winner": "Rose", "tie": False, "feeders": 7},
                     {"n": 1, "category": "Sky", "options": ["Dusk", "Dawn", "Storm"], "tally": [0, 0, 0], "winner": None, "tie": False, "feeders": 1}]}


class Evening(unittest.TestCase):
    def test_first_pass_posts_nothing(self):
        s = {}
        self.assertEqual(A.step(LATEST, s, send=lambda m: True, send_x=lambda m, st: True), [])
        self.assertEqual(s["last"], 1)

    def test_posts_each_new_evening_once(self):
        s, out = {"last": -1}, []
        A.step(LATEST, s, send=lambda m: out.append(m) or True, send_x=lambda m, st: True)
        A.step(LATEST, s, send=lambda m: out.append(m) or True, send_x=lambda m, st: True)
        self.assertEqual(len(out), 2)
        self.assertIn("Pendant light became <b>Rose</b> (White 4 / Rose 9 / Blue 2)", out[0])
        self.assertIn("2 days lived; 7 wallets fed it that day", out[0])
        self.assertIn("Tonight's choice: Aura (Gold, Pearl, Ice)", out[0])
        self.assertIn("no value", out[0])
        self.assertIn("nothing changed", out[1])
        self.assertNotIn("no value", out[1])

    def test_x_copy_once_without_link(self):
        s, xs = {"last": -1}, []
        A.step(LATEST, s, send=lambda m: True, send_x=lambda m, st: xs.append(m) or True)
        A.step(LATEST, s, send=lambda m: True, send_x=lambda m, st: xs.append(m) or True)
        self.assertEqual(len(xs), 2)
        self.assertTrue(xs[0].startswith("🦍 Evening 1: Pendant light became Rose\n\nWhite 4 · Rose 9 · Blue 2"))
        self.assertTrue(xs[0].endswith("#TauNet $AGRS"))
        self.assertNotIn("http", xs[0] + xs[1])
        self.assertNotIn("agorzilla.com", xs[0] + xs[1])
        self.assertNotIn("<b>", xs[0])

    def test_x_daily_cap(self):
        A.X_OUT.keys, A.X_PICTURE = {"k": "v"}, ""
        A.X_OUT.send_text = lambda m, media=None: (True, None, "")
        s = {}
        self.assertEqual(sum(A.post_x("m", s, now=0) for _ in range(A.X_DAILY_CAP + 2)), A.X_DAILY_CAP)
        self.assertTrue(A.post_x("m", s, now=86400))

    def test_growth_only_on_change(self):
        s, xs = {}, []
        send = lambda m, st: xs.append(m) or True  # noqa: E731
        self.assertIsNone(A.grow({"stage": 1, "stage_name": "Little one", "lived": 2}, s, send))
        self.assertIsNone(A.grow({"stage": 1, "stage_name": "Little one", "lived": 3}, s, send))
        m = A.grow({"stage": 2, "stage_name": "Young", "lived": 3}, s, send)
        self.assertTrue(m.startswith("🦍 Agorzilla grew into Young after 3 days lived\n\nIt was Little one until now."))
        self.assertEqual(len(xs), 1)

    def test_first_evening_ever_is_posted(self):
        s, out = {}, []
        A.step(dict(LATEST, rounds=[]), s, send=lambda m, png=None: True, send_x=lambda m, st, png=None: True, picture=lambda r: None)
        A.step(dict(LATEST, rounds=LATEST["rounds"][:1]), s, send=lambda m, png=None: out.append(m) or True,
               send_x=lambda m, st, png=None: True, now=LATEST["rounds"][0].get("t", 0) + 7200, picture=lambda r: None)
        self.assertEqual(len(out), 1)

    def test_failed_send_retries_later(self):
        s = {"last": -1}
        A.step(LATEST, s, send=lambda m: False, send_x=lambda m, st: True)
        self.assertEqual(s["last"], -1)

    def test_x_does_not_wait_for_a_failing_telegram(self):
        s, xs, tg = {"last": -1}, [], []
        A.step(LATEST, s, send=lambda m: False, send_x=lambda m, st: xs.append(m) or True)
        self.assertEqual((s["last"], len(xs)), (-1, 1))          # Telegram failed, the X copy of the first evening went out
        A.step(LATEST, s, send=lambda m: False, send_x=lambda m, st: xs.append(m) or True)
        self.assertEqual(len(xs), 1)                              # not again while Telegram keeps failing
        A.step(LATEST, s, send=lambda m: tg.append(m) or True, send_x=lambda m, st: xs.append(m) or True)
        self.assertEqual((s["last"], len(tg), len(xs)), (LATEST["rounds"][-1]["n"], len(LATEST["rounds"]), len(LATEST["rounds"])))


    def test_evening_waits_for_its_picture_then_goes_alone(self):
        r0 = dict(LATEST["rounds"][0], t=1000)
        latest = dict(LATEST, rounds=[r0])
        s, out = {"last": -1}, []
        A.step(latest, s, send=lambda m, png=None: out.append(m) or True, send_x=lambda m, st, png=None: True, now=1000 + 60, picture=lambda r: None)
        self.assertEqual((out, s["last"]), ([], -1))   # still waiting for the photographs
        A.step(latest, s, send=lambda m, png=None: out.append(m) or True, send_x=lambda m, st, png=None: True, now=1000 + A.SHOTS_WAIT + 1, picture=lambda r: None)
        self.assertEqual((len(out), s["last"]), (1, 0))   # too late: the text alone

    def test_picture_that_fails_twice_goes_as_text(self):
        latest = dict(LATEST, rounds=[dict(LATEST["rounds"][0], t=1000)])
        s, tries = {"last": -1}, []
        send = lambda m, png=None: tries.append(png) or png is None   # Telegram refuses the photo
        for _ in range(3):
            A.step(latest, s, send=send, send_x=lambda m, st, png=None: True, now=1100, picture=lambda r: b"PNG")
        self.assertEqual((tries, s["last"]), ([b"PNG", b"PNG", None], 0))

    def test_picture_goes_to_telegram_and_x(self):
        latest = dict(LATEST, rounds=[dict(LATEST["rounds"][0], t=1000)])
        s, tg, xs = {"last": -1}, [], []
        A.step(latest, s, send=lambda m, png=None: tg.append(png) or True, send_x=lambda m, st, png=None: xs.append(png) or True, now=1100, picture=lambda r: b"PNG")
        self.assertEqual((tg, xs), ([b"PNG"], [b"PNG"]))

    def test_evening_card_from_the_photographs(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            for side, colour in (("before", "#335533"), ("after", "#553355")):
                Image.new("RGB", (900, 1100), colour).save(os.path.join(d, f"evening-0-{side}.jpg"))
            with open(os.path.join(d, "evenings.json"), "w") as f:
                json.dump([{"n": 0, "before_value": "Gold", "before_color": "#ffd36b", "after_value": "Rose", "after_color": "#fda4af"}], f)
            A.SHOTS, keep = d, A.SHOTS
            try:
                png = A.evening_card(LATEST["rounds"][0])
                self.assertIsNone(A.evening_card(LATEST["rounds"][1]))   # nothing changed: no picture
            finally:
                A.SHOTS = keep
        self.assertTrue(png.startswith(b"\x89PNG"))
        import io
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1600, 900))


# rules v4 on agorzilla.com: a rule evening asks one rule of the game (kind "rule"), from Wednesday 4 November 18:00 UTC
T6 = 1793901600   # Thursday 5 November 2026, 18:00 UTC: the first rule evening closes
GAME = {"repeat": {"question": "May a decided question come back?", "value": "Never again", "says": "A decided question never comes back."},
        "lived": {"question": "How many wallets make a day lived?", "value": "3 wallets", "says": "A day counts as lived when at least 3 wallets feed it."},
        "every": {"question": "How often is there a rule evening?", "value": "Every 7th evening", "says": "Every 7th evening is a rule evening."}}
LOOK5 = {"n": 5, "t": T6 - 86400, "kind": "look", "category": "Temperament", "options": ["Dreamer", "Calm", "Playful"], "tally": [1, 2, 0],
         "winner": "Calm", "tie": False, "feeders": 3}
ASK = {"kind": "rule", "rule": "repeat", "question": "May a decided question come back?", "category": "Decided questions",
       "options": ["Never again", "After 7 evenings", "Any time"]}
RULE6 = dict(ASK, n=6, t=T6, says="A decided question can come back after 7 evenings.", tally=[1, 3, 0], winner="After 7 evenings", tie=False, feeders=4)
WED = {"rules": 4, "stage_name": "Young", "lived": 5, "game_rules": GAME, "open": dict(ASK, n=6, closes_at=T6), "rounds": [LOOK5]}
THU = {"rules": 4, "stage_name": "Young", "lived": 6, "rounds": [LOOK5, RULE6],
       "game_rules": dict(GAME, repeat=dict(GAME["repeat"], value="After 7 evenings", says=RULE6["says"])),
       "open": {"n": 7, "kind": "look", "category": "Fur", "options": ["Moss", "Honey", "Silver"], "closes_at": T6 + 86400}}


def run(latest, s, now, tg=None, xs=None, picture=lambda r: None, ok=True):
    tg, xs = (tg if tg is not None else []), (xs if xs is not None else [])
    A.step(latest, s, send=lambda m, png=None: tg.append(m) or ok, send_x=lambda m, st, png=None: xs.append(m) or True, now=now, picture=picture)
    return tg, xs


class RuleEvenings(unittest.TestCase):
    def test_wednesday_says_tonight_is_a_rule_evening(self):
        tg, xs = run(WED, {"last": 4}, T6 - 86400 + A.SHOTS_WAIT + 60)
        self.assertIn("Temperament became <b>Calm</b>", tg[0])
        self.assertIn("Tonight is a rule evening, a vote on the rules of the game: May a decided question come back? "
                      "(Never again, After 7 evenings, Any time). agorzilla.com", tg[0])
        self.assertNotIn("Tonight's choice", tg[0])
        self.assertTrue(xs[0].startswith("🦍 Evening 6: Temperament became Calm"))
        self.assertIn("Tonight is a rule evening, a vote on the rules of the game: May a decided question come back?", xs[0])   # on X before the growth line
        self.assertLessEqual(__import__("alerts").x_len(xs[0]), 280)

    def test_a_changed_rule(self):
        s = {"last": 4}
        run(WED, s, T6 - 86400 + A.SHOTS_WAIT + 60)                       # Wednesday: the rules as they stand are remembered
        self.assertEqual(s["rules_known"]["repeat"], "Never again")
        tg, xs = run(THU, s, T6 + 60)                       # Thursday, a minute after the evening: no wait for photographs
        self.assertEqual(len(tg), 1)
        self.assertTrue(tg[0].startswith("🦍 Agorzilla, evening 7 was a rule evening: May a decided question come back?\n"
                                         "The feeders changed it to <b>After 7 evenings</b> (Never again 1 / After 7 evenings 3 / Any time 0). "
                                         "From now on: A decided question can come back after 7 evenings.\n"), tg[0])
        self.assertIn("Tonight's choice: Fur (Moss, Honey, Silver)", tg[0])
        self.assertTrue(xs[0].startswith("🦍 Evening 7, a rule evening: May a decided question come back?\n\n"
                                         "The feeders changed it to After 7 evenings (3 of 4 votes). "
                                         "From now on: A decided question can come back after 7 evenings."), xs[0])
        self.assertTrue(xs[0].endswith("#TauNet $AGRS"))
        self.assertLessEqual(__import__("alerts").x_len(xs[0]), 280)
        self.assertEqual(s["rules_known"]["repeat"], "After 7 evenings")

    def test_a_kept_rule(self):
        s = {"last": 4}
        run(WED, s, T6 - 86400 + A.SHOTS_WAIT + 60)
        kept = dict(RULE6, tally=[3, 1, 0], winner="Never again", says="A decided question never comes back.")
        tg, xs = run(dict(THU, rounds=[LOOK5, kept], game_rules=GAME), s, T6 + 60)
        self.assertIn("The feeders kept <b>Never again</b> (Never again 3 / After 7 evenings 1 / Any time 0). "
                      "The rule stays: A decided question never comes back.", tg[0])
        self.assertIn("The feeders kept Never again (3 of 4 votes). The rule stays: A decided question never comes back.", xs[0])

    def test_nobody_voted(self):
        s = {"last": 4}
        run(WED, s, T6 - 86400 + A.SHOTS_WAIT + 60)
        none = dict(RULE6, tally=[0, 0, 0], winner=None, says=None, feeders=1)
        tg, xs = run(dict(THU, rounds=[LOOK5, none], game_rules=GAME), s, T6 + 60, picture=A.evening_card)
        self.assertIn("evening 7 was a rule evening: May a decided question come back?\nNobody voted, so the rule stays: "
                      "A decided question never comes back.", tg[0])
        self.assertNotIn("no value", tg[0])
        self.assertIsNone(A.rule_card(none))
        self.assertEqual(s["rules_known"]["repeat"], "Never again")

    def test_telegram_retry_still_says_changed(self):
        s = {"last": 4}
        run(WED, s, T6 - 86400 + A.SHOTS_WAIT + 60)
        tg, xs = run(THU, s, T6 + 60, ok=False)                 # Telegram refuses, the X copy goes
        self.assertIn("changed it to After 7 evenings", xs[0])
        self.assertEqual(s["rules_known"]["repeat"], "Never again")
        tg, xs = run(THU, s, T6 + 700)                          # Telegram back: still a change, X not again
        self.assertIn("The feeders changed it to <b>After 7 evenings</b>", tg[0])
        self.assertEqual(xs, [])

    def test_unknown_rule_before_says_chose(self):
        tg, xs = run(THU, {}, T6 + 60)                          # a fresh start right after the evening: no rule known before it
        self.assertEqual(len(tg), 1)
        self.assertIn("The feeders chose <b>After 7 evenings</b>", tg[0])

    def test_rule_card(self):
        from PIL import Image
        import io
        png = A.evening_card(RULE6)                             # a rule evening's card is its ballot, no photographs needed
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1600, 900))
        tg = []
        A.step(THU, {"last": 5}, send=lambda m, png=None: tg.append(png) or True, send_x=lambda m, st, png=None: True, now=T6 + 60)
        self.assertTrue(tg and tg[0] and tg[0].startswith(b"\x89PNG"))

    def test_old_latest_without_kind_is_a_look(self):
        self.assertFalse(A.is_rule(LATEST["rounds"][0]))
        self.assertIn("Tonight's choice: Aura (Gold, Pearl, Ice)", A.text(LATEST["rounds"][0], LATEST))


if __name__ == "__main__":
    unittest.main()
