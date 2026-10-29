import unittest

import agorzilla as A

LATEST = {"stage_name": "Little one", "lived": 2,
          "open": {"n": 2, "category": "Aura", "options": ["Gold", "Pearl", "Ice"]},
          "rounds": [{"n": 0, "category": "Pendant light", "options": ["White", "Rose", "Blue"], "tally": [4, 9, 2], "winner": "Rose", "tie": False, "feeders": 7},
                     {"n": 1, "category": "Sky", "options": ["Dusk", "Dawn", "Storm"], "tally": [0, 0, 0], "winner": None, "tie": False, "feeders": 1}]}


class Evening(unittest.TestCase):
    def test_first_pass_posts_nothing(self):
        s = {}
        self.assertEqual(A.step(LATEST, s, send=lambda m: True), [])
        self.assertEqual(s["last"], 1)

    def test_posts_each_new_evening_once(self):
        s, out = {"last": -1}, []
        A.step(LATEST, s, send=lambda m: out.append(m) or True)
        A.step(LATEST, s, send=lambda m: out.append(m) or True)
        self.assertEqual(len(out), 2)
        self.assertIn("Pendant light became <b>Rose</b> (White 4 / Rose 9 / Blue 2)", out[0])
        self.assertIn("2 days lived; 7 wallets fed it that day", out[0])
        self.assertIn("Tonight's choice: Aura (Gold, Pearl, Ice)", out[0])
        self.assertIn("no value", out[0])
        self.assertIn("nothing changed", out[1])
        self.assertNotIn("no value", out[1])

    def test_failed_send_retries_later(self):
        s = {"last": -1}
        A.step(LATEST, s, send=lambda m: False)
        self.assertEqual(s["last"], -1)


if __name__ == "__main__":
    unittest.main()
