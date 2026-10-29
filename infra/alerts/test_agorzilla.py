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
        self.assertTrue(xs[0].endswith("#Agorzilla #TauNet"))
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


if __name__ == "__main__":
    unittest.main()
