"""Unit test of intel.py (no engine, no network): No Memo's intel contracts, a hidden rule the player probes.
1. the rules each contract deals: the same for the same seed, round hundreds, the kinds the contract promises;
2. each rule's text in Tau means what the contract says it lets through: read case by case with rulefacts.py (the
   reader checked against 53 answers of the real engine, tests/rulefacts-cases.json), at its edges;
3. requests: what is refused before anything runs;
4. answers with a stand-in for the engine: a probe, the one-shot edge, naming by behaviour, giving up, a new round,
   and an engine that fails or answers otherwise.
The real engine answers the same rules in `up tau` (tau_selftest.py).

Run: python test_intel.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["INTEL_SECRET"] = "test-secret"
import intel  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


SEEDS = [format(n * 7919 + 1, "016x") for n in range(400)]

# 1. the deal
for case, kinds in intel.CASES.items():
    rules = [intel.deal(case, s) for s in SEEDS]
    check(all(r == intel.deal(case, s) for r, s in zip(rules, SEEDS)), f"{case}: the same seed gets the same rule")
    check({r["kind"] for r in rules} == set(kinds), f"{case}: deals {', '.join(kinds)} and nothing else")
    check(all(r["a"] % 100 == 0 and 100 <= r["a"] <= intel.TOP for r in rules), f"{case}: amounts are round hundreds from 100 to {intel.TOP:,}")
    two = [r for r in rules if r["kind"] in ("band", "hole")]
    check(all(r["b"] % 100 == 0 and 500 <= r["b"] - r["a"] <= 5000 and r["b"] <= intel.TOP for r in two), f"{case}: a window or hole is 500 to 5,000 wide")
check(len({tuple(intel.deal("i-blind", s).values()) for s in SEEDS}) > 300, "different seeds get different rules")
check(intel.round_of("i-cap", SEEDS[0]) == intel.round_of("i-cap", SEEDS[0]) != intel.round_of("i-cap", SEEDS[1]), "a round id per contract and seed")

# 2. the text means what the contract says
try:
    sys.path.insert(0, os.path.join(HERE, "..", "alerts"))
    import rulefacts as RF
except ImportError:
    RF = None
SAMPLES = [{"kind": "cap", "a": 4100, "b": None}, {"kind": "floor", "a": 4100, "b": None}, {"kind": "band", "a": 3000, "b": 3500},
           {"kind": "hole", "a": 3000, "b": 3500}, {"kind": "none", "a": 4100, "b": None}, {"kind": "above", "a": 4100, "b": None},
           {"kind": "cap", "a": 20000, "b": None}, {"kind": "hole", "a": 100, "b": 600}]
if RF:
    for rule in SAMPLES:
        edges = {0, 1, rule["a"] - 1, rule["a"], rule["a"] + 1, intel.MAX - 1, intel.MAX} | (
            {rule["b"] - 1, rule["b"], rule["b"] + 1} if rule["b"] else set())
        got = {a: RF.answer(intel.text(rule), {"i1": a})["outcome"] == "pass" for a in sorted(edges)}
        want = {a: intel.passes(rule, a) for a in sorted(edges)}
        check(got == want, f"{rule['kind']} {rule['a']} {rule['b'] or ''}: the Tau text lets through what the contract says ({intel.words(rule)})")
        r = RF.read(intel.text(rule))
        if r["ok"]:
            for cell in r["cells"]:
                a = cell["v"]["i1"] if "i1" in cell["v"] else 0
                if RF.OUTCOME[cell["d"]] != ("pass" if intel.passes(rule, a) else "block"):
                    check(False, f"{rule['kind']}: the X-ray reads {cell['d']} at {a}")
    check(RF.read(intel.text({"kind": "none", "a": 4100, "b": None}))["cells"][0]["d"] == "open",
          "a rule that only says when to block leaves the rest open, so the engine answers 0 there")
else:
    print("skip the reading: infra/alerts/rulefacts.py is not here")
check(intel.words({"kind": "cap", "a": 4100}) == "passes up to 4,100" and intel.words({"kind": "hole", "a": 3000, "b": 3500}) == "passes up to 2,999 and 3,501 or more"
      and intel.words({"kind": "none", "a": 9}) == "nothing passes" and intel.words({"kind": "above", "a": 4100}) == "passes 4,101 or more",
      "the rule in plain words")

# 3. requests
S = SEEDS[0]
for bad, why in (({"case": "x", "seed": S, "probe": 1}, "an unknown contract"), ({"case": "i-cap", "seed": "zz", "probe": 1}, "a seed that is no hex"),
                 ({"case": "i-cap", "seed": S, "probe": -1}, "a negative amount"), ({"case": "i-cap", "seed": S, "probe": 1 << 24}, "an amount wider than 24 bits"),
                 ({"case": "i-cap", "seed": S, "probe": "1e3"}, "an amount that is no whole number"), ({"case": "i-cap", "seed": S, "probe": True}, "true for an amount"),
                 ({"case": "i-cap", "seed": S, "final": intel.MAX}, "an edge with no amount above it"),
                 ({"case": "i-cap", "seed": S, "name": {"kind": "bad", "a": 1}}, "a kind of rule there is not"),
                 ({"case": "i-cap", "seed": S, "name": {"kind": "band", "a": 500, "b": 400}}, "a window whose top is below its bottom"),
                 ({"case": "i-cap", "seed": S, "name": {"kind": "cap"}}, "a cap with no amount"),
                 ({"case": "i-cap", "seed": S}, "no move at all"), ([1], "no object")):
    try:
        intel.parse(bad)
        check(False, f"refused: {why}")
    except intel.BadRequest:
        check(True, f"refused: {why}")
check(intel.parse({"case": "i-cap", "seed": S.upper(), "probe": " 250 "}) == {"case": "i-cap", "seed": S, "probe": 250}, "a seed in capitals and an amount as text are fine")
check(intel.steps_of(intel.parse({"case": "i-edge", "seed": S, "final": 400})) == [{"i1": "400"}, {"i1": "401"}], "the edge runs two steps: it and one more")
check(intel.steps_of(intel.parse({"case": "i-cap", "seed": S, "reveal": True})) is None, "naming and giving up need no engine")


# 4. answers, with a stand-in engine that answers as the contract reads the rule
def engine(rule, lie=False):
    def run(spec, steps):
        assert spec == intel.text(rule)
        return {"ok": True, "ms": 12, "outputs": [{"t": i, "out": {"o5": "1" if intel.passes(rule, int(st["i1"])) != lie else "0"}} for i, st in enumerate(steps)]}
    return run


seed = next(s for s in SEEDS if intel.deal("i-edge", s)["kind"] == "cap")
rule = intel.deal("i-edge", seed)
a = rule["a"]
p = intel.answer(intel.parse({"case": "i-edge", "seed": seed, "probe": a}), engine(rule))
check(p["ok"] and p["pass"] is True and p["agrees"] and p["round"] == intel.round_of("i-edge", seed) and "rule" not in p, "a probe at the cap passes; the rule stays hidden")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "probe": a + 1}), engine(rule))["pass"] is False, "one more is blocked")
f = intel.answer(intel.parse({"case": "i-edge", "seed": seed, "final": a}), engine(rule))
check(f["edge"] is True and f["rule"] == intel.text(rule) and f["says"] == intel.words(rule) and f["dealt"] == rule, "the edge in one shot: right, and the rule is shown")
f = intel.answer(intel.parse({"case": "i-edge", "seed": seed, "final": a - 100}), engine(rule))
check(f["edge"] is False and f["pass"] is True and f["rule"], "a shot below the edge misses, and the rule is shown all the same")
n = intel.answer(intel.parse({"case": "i-edge", "seed": seed, "name": {"kind": "cap", "a": a + 1}}))
check(n["right"] is False and "rule" not in n and "dealt" not in n, "a wrong name: not right, nothing shown")
n = intel.answer(intel.parse({"case": "i-edge", "seed": seed, "name": {"kind": "cap", "a": a}}))
check(n["right"] is True and n["rule"] == intel.text(rule), "the right name: the rule is shown")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "reveal": True}))["rule"] == intel.text(rule), "giving up shows it")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "lead": True})) == {"ok": True, "round": intel.round_of("i-edge", seed), "lead": None},
      "no lead for a cap: it is found by halving")
check(all(intel.answer(intel.parse({"case": c, "seed": s, "lead": True}))["lead"] == intel.deal(c, s)["a"] for c in ("i-band", "i-blind") for s in SEEDS[:40]),
      "a window, a hole or the blind guard: the lookout read one number of its rule, its first amount")
bs = next(s for s in SEEDS if intel.deal("i-blind", s)["kind"] == "above")
ab = intel.deal("i-blind", bs)
check(intel.answer(intel.parse({"case": "i-blind", "seed": bs, "name": {"kind": "floor", "a": ab["a"] + 1}}))["right"] is True,
      "a rule that only says when to pass is named by what it does: above 4,100 is floor 4,101")
ns = next(s for s in SEEDS if intel.deal("i-blind", s)["kind"] == "none")
check(intel.answer(intel.parse({"case": "i-blind", "seed": ns, "name": {"kind": "none"}}))["right"] is True
      and intel.answer(intel.parse({"case": "i-blind", "seed": ns, "name": {"kind": "cap", "a": 0}}))["right"] is False,
      "a rule that lets nothing through is named none (cap 0 still lets 0 through)")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "probe": a}), engine(rule, lie=True))["agrees"] is False,
      "an engine that answers otherwise than the contract reads it: noticed")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "probe": a}), lambda s, st: {"ok": False, "timeout": True, "error": "slow"})
      == {"ok": False, "error": "slow", "timeout": True, "round": intel.round_of("i-edge", seed)}, "an engine that runs out of time: an error, no answer")
check(intel.answer(intel.parse({"case": "i-edge", "seed": seed, "probe": a}), lambda s, st: {"ok": True, "outputs": [{"out": {}}]})["ok"] is False,
      "an engine answer without o5: an error")
old = intel.round_of("i-edge", seed)
intel.SECRET = b"another secret"
check(intel.round_of("i-edge", seed) != old, "a new secret on the server: a new round, and the page starts the contract's probes over")

print("all intel tests passed" if not failed else f"{failed} intel checks failed")
sys.exit(1 if failed else 0)
