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

    def test_failed_send_retries_later(self):
        s = {"last": -1}
        A.step(LATEST, s, send=lambda m: False, send_x=lambda m, st: True)
        self.assertEqual(s["last"], -1)


    def test_evening_waits_for_its_picture_then_goes_alone(self):
        r0 = dict(LATEST["rounds"][0], t=1000)
        latest = dict(LATEST, rounds=[r0])
        s, out = {"last": -1}, []
        A.step(latest, s, send=lambda m, png=None: out.append(m) or True, send_x=lambda m, st, png=None: True, now=1000 + 60, picture=lambda r: None)
        self.assertEqual((out, s["last"]), ([], -1))   # still waiting for the photographs
        A.step(latest, s, send=lambda m, png=None: out.append(m) or True, send_x=lambda m, st, png=None: True, now=1000 + A.SHOTS_WAIT + 1, picture=lambda r: None)
        self.assertEqual((len(out), s["last"]), (1, 0))   # too late: the text alone

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


if __name__ == "__main__":
    unittest.main()
