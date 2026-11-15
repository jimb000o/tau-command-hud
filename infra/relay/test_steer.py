"""steer.py: who may walk which islander, what is passed on, what is forgotten. No network."""
import asyncio
import hashlib
import unittest

from steer import HOLD, Steer, message, utc_day, verify

A = "a" * 96
B = "b" * 96
SIG = "c" * 192


class Clock:
    def __init__(self):
        self.t = 1_763_250_000.0

    def __call__(self):
        return self.t


class SteerTest(unittest.TestCase):
    def setUp(self):
        self.c = Clock()
        self.checked = []
        self.s = Steer(clock=self.c, check=lambda w, d, sig: self.checked.append(w) or w == A)

    def hello(self, ws, w, sig=SIG, ip="1.1.1.1", day=None):
        return asyncio.run(self.s.hello(ws, ip, w, day or utc_day(self.c()), sig))

    def test_hello_then_go(self):
        ok, _ = self.hello("ws1", A)
        self.assertTrue(ok)
        ok, d = self.s.go("ws1", "1.1.1.1", [A, "500", "600", "700.25", "650", "cafe"])
        self.assertTrue(ok)
        self.assertEqual(d["a"], A)
        self.assertEqual(d["t"], [700.2, 650.0])
        self.assertEqual(d["p"], "cafe")
        self.assertEqual(d["age"], 0)

    def test_someone_elses_walker(self):
        self.hello("ws1", A)
        ok, why = self.s.go("ws1", "1.1.1.1", [B, "500", "600", "700", "650"])
        self.assertFalse(ok)
        self.assertIn("hello", why)
        ok, why = self.hello("ws1", B)
        self.assertFalse(ok)
        ok, _ = self.s.go("ws2", "1.1.1.1", [A, "500", "600", "700", "650"])   # another socket: no hello there
        self.assertFalse(ok)

    def test_signed_through_relay_needs_no_hello(self):
        ok, _ = self.s.go("ws1", "2.2.2.2", [B, "500", "600", "700", "650"], signed=lambda ip, w, now: ip == "2.2.2.2" and w == B)
        self.assertTrue(ok)

    def test_one_check_a_day(self):
        self.hello("ws1", A)
        self.hello("ws2", A)
        self.assertEqual(self.checked, [A])

    def test_checks_are_rate_limited(self):
        for i in range(6):
            self.hello("ws", B, sig=f"{i:0192x}")
        ok, why = self.hello("ws", B, sig="f" * 192)
        self.assertFalse(ok)
        self.assertIn("too many", why)
        self.c.t += 61
        ok, why = self.hello("ws", B, sig="f" * 192)
        self.assertIn("not this wallet", why)

    def test_wrong_day(self):
        ok, why = self.hello("ws", A, day="2020-01-01")
        self.assertFalse(ok)

    def test_bad_points_and_pace(self):
        self.hello("ws1", A)
        self.assertFalse(self.s.go("ws1", "x", [A, "500", "600", "9999", "650"])[0])
        self.assertFalse(self.s.go("ws1", "x", [A, "500", "600", "nan?", "650"])[0])
        self.assertFalse(self.s.go("ws1", "x", [A, "500", "600", "700", "650", "Café!"])[0])
        self.assertTrue(self.s.go("ws1", "x", [A, "500", "600", "700", "650"])[0])
        self.assertFalse(self.s.go("ws1", "x", [A, "700", "650", "800", "650"])[0])   # within a second
        self.c.t += 1.1
        self.assertTrue(self.s.go("ws1", "x", [A, "700", "650", "800", "650"])[0])

    def test_recent_and_forgotten(self):
        self.hello("ws1", A)
        self.s.go("ws1", "x", [A, "500", "600", "700", "650"])
        self.c.t += 12
        r = self.s.recent({A})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["age"], 12000)
        self.assertEqual(self.s.recent({B}), [])
        self.c.t += HOLD
        self.assertEqual(self.s.recent(), [])
        self.s.forget("ws1")
        self.c.t += 2
        self.assertFalse(self.s.go("ws1", "x", [A, "500", "600", "700", "650"])[0])

    def test_real_bls(self):
        try:
            from py_ecc.bls import G2Basic
        except ImportError:
            self.skipTest("py_ecc not installed")
        sk = 123456789
        pk = G2Basic.SkToPk(sk).hex()
        day = "2026-11-16"
        sig = G2Basic.Sign(sk, hashlib.sha256(message(pk, day)).digest()).hex()
        self.assertTrue(verify(pk, day, sig))
        self.assertFalse(verify(pk, "2026-11-17", sig))
        self.assertFalse(verify(B, day, sig))


if __name__ == "__main__":
    unittest.main()
