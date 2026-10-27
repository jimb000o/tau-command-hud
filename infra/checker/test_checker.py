"""Checker tests against the real engine.

Run where tau-testnet and its built native module are importable, e.g. inside the
node image:
  docker compose run --rm checker python /checker/test_checker.py
or locally with TAU_TESTNET_DIR pointing at a tau-testnet checkout whose sibling
tau-lang/ has the nanobind module built.
"""
import os
import sys

os.environ.setdefault("TAU_ENV", "test")
os.environ.setdefault("TAU_SHRINK_ENABLED", "false")
os.environ.setdefault("TAU_DB_PATH", "/tmp/checker-test.db")
os.environ.setdefault("TAU_DATA_DIR", "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker  # noqa: E402

YOU, BOB, CAROL = "db" * 48, "8a" * 48, "42" * 48
T = 1793500000
LIMIT = ("always ( (i1[t]:bv[24] > { 1000 }:bv[24]) ? (o5[t]:bv[24] = { #x000000 }:bv[24])"
         " : (o5[t]:bv[24] = { #x000001 }:bv[24]) ).")
ONLY_BOB = (f"always ( (i4[t]:bv[384] = {{ #x{BOB} }}:bv[384]) ? (o5[t]:bv[24] = {{ #x000001 }}:bv[24])"
            " : (o5[t]:bv[24] = { #x000000 }:bv[24]) ).")
failures = 0


def check(name, cond, info=""):
    global failures
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {info}"))
    failures += 0 if cond else 1


def tx(amount, frm, to):
    return {"amount": amount, "from": frm, "to": to, "time": T}


r = checker.check(LIMIT, YOU, [tx(500, YOU, BOB), tx(5000, YOU, CAROL), tx(5000, BOB, CAROL)])
check("limit accepted", r["accepted"] is True, r)
check("limit verdicts", [t["o5"] for t in r.get("tests", [])] == [1, 0, 1], r.get("tests"))

r = checker.check(ONLY_BOB, YOU, [tx(9, YOU, BOB), tx(9, YOU, CAROL)])
check("recipient rule verdicts", [t["o5"] for t in r.get("tests", [])] == [1, 0], r.get("tests"))

r = checker.check(LIMIT.replace("i1[t]", "i2[t]"), YOU, [])
check("balance read refused before the engine", r["accepted"] is False and r["stage"] == "streams", r)

r = checker.check(LIMIT.replace("i1[t]", "i1[t-1]"), YOU, [])
check("lookback refused", r["accepted"] is False and "[t] only" in r["reason"], r)

r = checker.check("always ( (o5[t]:bv[24] = { #x000000 }:bv[24]) && (o5[t]:bv[24] = { #x000001 }:bv[24]) ).", YOU, [])
check("contradiction refused by the engine", r["accepted"] is False and r["stage"] == "engine", r)

r = checker.check(LIMIT.replace("i1[t]:bv[24] >", "i4[t]:bv[16] >").replace("{ 1000 }:bv[24]", "{ 1000 }:bv[16]"), YOU, [])
check("width clash refused by the engine", r["accepted"] is False and "i4" in r.get("reason", ""), r)

sys.exit(1 if failures else 0)
