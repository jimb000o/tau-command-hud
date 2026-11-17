import json
import os
import tempfile
import unittest
from datetime import datetime

os.environ["XSTATS_PATH"] = os.path.join(tempfile.mkdtemp(), "xstats.json")
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    os.environ[k] = "k"
    os.environ.pop("AGORZILLA_" + k, None)
import xstats as S  # noqa: E402

T = lambda s: datetime.fromisoformat(s).timestamp()   # noqa: E731
NOW = T("2026-11-18T05:00:00+00:00")
TWEETS = {"data": [
    {"id": "1", "created_at": "2026-11-16T10:00:00Z", "text": "Wallets walk now.\n\nhttps://t.co/a",
     "public_metrics": {"impression_count": 1000, "like_count": 5, "retweet_count": 1, "reply_count": 0, "quote_count": 0,
                        "bookmark_count": 1},
     "non_public_metrics": {"impression_count": 1000, "url_link_clicks": 12, "user_profile_clicks": 3},
     "attachments": {"media_keys": ["m1"]}, "entities": {"urls": [{"expanded_url": "https://tauhud.com/rabbit/"}]}},
    {"id": "2", "created_at": "2026-11-15T19:00:00Z", "text": "Testnet today",
     "public_metrics": {"impression_count": 200, "like_count": 1, "retweet_count": 0, "reply_count": 0, "quote_count": 0,
                        "bookmark_count": 0},
     "non_public_metrics": {"url_link_clicks": 0, "user_profile_clicks": 1}}],
    "includes": {"media": [{"media_key": "m1", "type": "video"}]}, "meta": {}}


class Stats(unittest.TestCase):
    def setUp(self):
        if os.path.exists(S.PATH):
            os.remove(S.PATH)
        self.calls = []

    def fetch(self, k, path, q):
        self.calls.append((path, dict(q)))
        if path == "/users/me":
            return {"data": {"id": "42"}}
        if "non_public_metrics" in q["tweet.fields"] and getattr(self, "refuse", False):
            raise RuntimeError("HTTP 403: not allowed")
        return TWEETS

    def test_reads_keeps_and_costs(self):
        out = S.run(NOW, fetch=self.fetch)
        self.assertIn("@TauHUDcom: 2 posts of the last 30 days read", out[0])
        self.assertIn("no keys", out[1])
        d = S.load()
        self.assertEqual(d["users"]["hud"], "42")
        p = d["posts"]["1"]
        self.assertEqual((p["media"], p["link"], p["link_clicks"]), ("video", "https://tauhud.com/rabbit/", 12))
        self.assertAlmostEqual(d["cost"], 0.012)
        S.run(NOW + 86400, fetch=self.fetch)   # second day: 7 days back, no new user read
        self.assertEqual([c[0] for c in self.calls].count("/users/me"), 1)
        self.assertTrue(self.calls[-1][1]["start_time"].startswith("2026-11-12"))

    def test_private_numbers_refused_falls_back(self):
        self.refuse = True
        out = S.run(NOW, fetch=self.fetch)
        self.assertIn("public ones only", out[0])

    def test_report_and_once_a_day(self):
        S.run(NOW, fetch=self.fetch)
        r = S.report(NOW)
        self.assertIn("@TauHUDcom", r)
        self.assertIn("Wallets walk now.", r)
        self.assertFalse(S.due(S.load(), NOW + 3600))
        self.assertTrue(S.due(S.load(), NOW + 86400))
        self.assertFalse(S.due(S.load(), T("2026-11-19T02:00:00+00:00")))

    def test_signature_covers_query(self):
        k = {"X_API_KEY": "a", "X_API_SECRET": "b", "X_ACCESS_TOKEN": "c", "X_ACCESS_SECRET": "d"}
        h1 = S.auth(k, "GET", "https://api.x.com/2/users/1/tweets", {"max_results": "100"})
        self.assertIn("oauth_signature=", h1)


if __name__ == "__main__":
    unittest.main()
