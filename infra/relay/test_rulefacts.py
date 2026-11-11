"""Unit test of rulefacts.py (no network), the same reading of Tau rules as assets/rulefacts.js on the pages:
1. infra/alerts and infra/relay hold the same file (each service's image copies only its own folder);
2. every answer of the real Tau engine in tests/rulefacts-cases.json: the value for one case, and the X-ray's verdict;
3. tests/meaning-cases.json: what a change to the network's rules decides differently, line for line as the pages;
4. the reading of a fee: its value per case and where it steps with the amount (the pirates' fee edge, relay/cruise.py).

Run: python test_rulefacts.py   (here and in infra/relay, the same file)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import rulefacts as RF  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    if not cond:
        print("FAIL " + label)
    failed += not cond


def tests_file(name):
    """A file of tests/, or None inside a service image (only the service's own folder is there)."""
    p = os.path.join(ROOT, "tests", name)
    return json.load(open(p)) if os.path.exists(p) else None


# 1. one file in two places
twins = [os.path.join(ROOT, "infra", d, f) for d in ("alerts", "relay") for f in ("rulefacts.py", "test_rulefacts.py")]
if all(os.path.exists(p) for p in twins):
    for f in ("rulefacts.py", "test_rulefacts.py"):
        a, b = (open(os.path.join(ROOT, "infra", d, f), "rb").read() for d in ("alerts", "relay"))
        check(a == b, f"infra/alerts/{f} and infra/relay/{f} are the same file")
else:
    print("skip the twin check: not run from the repository")

# 2. the engine's own answers
fx = tests_file("rulefacts-cases.json")
engine = 0
if fx:
    for c in fx["cases"]:
        reading = RF.read(c["rule"]) if c["watch"] == "o5" else None
        if reading and not reading["ok"] and reading["code"] == "outputs":
            reading = None   # also sets o1: answered per case only
        for p in c["probes"]:
            engine += 1
            try:
                got = RF.answer(c["rule"], p["in"], c["watch"])
            except RF.Outside as e:
                check(False, f"{c['id']} / {p['name']}: {e}")
                continue
            check(got["value"] is not None and got["value"] == int(p["engine"]),
                  f"{c['id']} / {p['name']}: engine {p['engine']}, reader {got['value']} (allowed {got['allowed']})")
            if reading:
                check(reading["ok"], f"{c['id']}: the X-ray cannot read it ({reading.get('why')})")
                cell = RF.cell_at(reading, p["in"]) if reading["ok"] else None
                want = "block" if int(p["engine"]) == 0 else "pass"
                check(cell is not None and RF.OUTCOME[cell["d"]] == want, f"{c['id']} / {p['name']}: X-ray says {cell and cell['d']}, engine {p['engine']}")
        if c["watch"] == "o8":   # a fee read for every case: the value where the rule sets one, open where it leaves it (engine: 0)
            r = RF.read(c["rule"], "o8")
            check(r["ok"], f"{c['id']}: the fee is read ({r.get('why')})")
            for p in c["probes"] if r["ok"] else []:
                v = RF.value_at(r, p["in"])
                check(v == int(p["engine"]) or (v == "open" and int(p["engine"]) == 0), f"{c['id']} / {p['name']}: value {v}, engine {p['engine']}")
    check(engine >= 50, f"{engine} engine answers read")
else:
    print("skip the engine answers: tests/rulefacts-cases.json is not here")

# 3. what a change decides differently
mc = tests_file("meaning-cases.json")
if mc:
    for c in mc["cases"]:
        spec = RF.clauses_of(mc["spec"])
        for r in c.get("before") or []:
            spec.update(RF.clauses_of(r))
        m = RF.meaning(spec, c["revisions"])
        lines = [f"{line['topic']} · {RF.line_text(line)}" for line in RF.meaning_lines(m)]
        streams = " ".join(f"{s['stream']}:" + (("same" if s["same"] else "changed") if s["ok"] else s["code"]) for s in m["streams"])
        check((m["ok"], m["same"], streams) == (c["ok"], c["same"], c["streams"]), f"meaning {c['id']}: {m['ok']} {m['same']} {streams!r}, page {c['streams']!r}")
        check(lines == c["lines"], f"meaning {c['id']}: {lines} != {c['lines']}")
    check(len(mc["cases"]) >= 20, f"{len(mc['cases'])} rule changes read as the pages read them")
else:
    print("skip the meaning cases: tests/meaning-cases.json is not here")

# 4. a fee: its value per case and its steps
step = "always ( (i1[t]:bv[24] > { 1000 }:bv[24]) ? o9[t]:bv[24] = { 20 }:bv[24] : o9[t]:bv[24] = { 10 }:bv[24] )."
r = RF.read(step, "o9")
check(r["ok"] and r["read"] == ["i1"] and not r["follows"], "a fee that steps with the amount: read, by the amount")
check([RF.value_at(r, {"i1": a}) for a in (0, 1000, 1001, "#x0f4240")] == [10, 10, 20, 20], "the fee for 0, 1,000, 1,001 and 1,000,000")
e = RF.value_edges(r, "i1")
check(len(e) == 1 and (e[0]["below"], e[0]["above"], e[0]["was"], e[0]["now"]) == (1000, 1001, 10, 20), f"one step: 1,000 costs 10, 1,001 costs 20 ({e})")
flat = RF.read("always ( o9[t]:bv[24] = { #x00000a }:bv[24] ).", "o9")
check(flat["ok"] and RF.value_at(flat, {}) == 10 and RF.value_edges(flat, "i1") == [], "the genesis fee: 10 for every transfer, no step")
check(RF.read("always ( o9[t]:bv[24] = i1[t]:bv[24] / { 100 }:bv[24] ).", "o9")["code"] == "computes", "a fee computed from the amount is not read")
check(RF.answer("always ( o9[t]:bv[24] = i1[t]:bv[24] / { 100 }:bv[24] ).", {"i1": 2550}, "o9")["value"] == 25, "but answered for one transfer: 1% of 2,550 is 25")
check(RF.value_at(RF.read("always ( o9[t]:bv[24] > { 5 }:bv[24] ).", "o9"), {}) == "open", "a fee the rule leaves open is no number")
same = RF.read("always ( (i3[t]:bv[384] = i4[t]:bv[384]) ? o9[t]:bv[24] = { 0 }:bv[24] : o9[t]:bv[24] = { 10 }:bv[24] ).", "o9")
check(same["ok"] and RF.cell_at(same, {}) is None, "inputs compared with each other: no case by pieces")

print(f"{'all rulefacts tests passed' if not failed else f'{failed} rulefacts checks failed'} ({engine} engine answers)")
sys.exit(1 if failed else 0)
