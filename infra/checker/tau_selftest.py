"""Every lesson on tauhud.com/learn asked of this engine: `up tau` prints the result for the chat.

Each try and each task solution in learn/lessons.json (mounted at /learn/lessons.json)
goes through tau_sandbox exactly as a visitor's question does. A line says ok or
FAIL, what the engine answered and how long it took; a FAIL means the lesson text
promises something this engine does not do, so the lesson has to change.
"""
import json
import os
import resource
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tau_sandbox  # noqa: E402

LESSONS = os.environ.get("TAU_LESSONS", "/learn/lessons.json")


def matches(expect, got):
    if not got.get("ok"):
        return False
    if "verdict" in expect and bool(got.get("verdict")) != expect["verdict"]:
        return False
    for name, values in (expect.get("out") or {}).items():
        seen = [str((row.get("out") or {}).get(name)) for row in got.get("outputs") or []]
        if seen != list(values):
            return False
    return True


def shown(got):
    if not got.get("ok"):
        return "error: " + str(got.get("error"))[:240]
    if got.get("outputs") is not None:
        return "; ".join(f"t{r['t']} in {r.get('in')} out {r.get('out')}" for r in got["outputs"])
    text = "T" if got.get("verdict") else "F"
    if got.get("core"):
        text += " core " + " | ".join(got["core"])[:200]
    return text


def main():
    lessons = json.load(open(LESSONS, encoding="utf-8"))["lessons"]
    fails = total = 0
    for n, lesson in enumerate(lessons, 1):
        items = [(t["label"], t) for t in lesson["tries"]]
        task = lesson.get("task")
        if task:
            items.append(("solution", dict(task, spec=task["solution"])))
        for label, item in items:
            req = tau_sandbox.parse({"op": item["op"], "spec": item["spec"], "steps": item.get("steps")})
            got = tau_sandbox.ask(req)
            good = matches(item["expect"], got)
            total += 1
            fails += not good
            print(f"{'ok  ' if good else 'FAIL'} {n} {lesson['id']} · {label}: {item['op']} {item['spec'][:70]}")
            print(f"       → {shown(got)} ({got.get('ms')} ms)" + ("" if good else f"  expected {item['expect']}"))
            if not good and got.get("log"):
                print("       log: " + got["log"][-300:].replace("\n", " / "))
    # No Memo's `tau <line>` contract (nomemo/game.js) sends this shape: G(...) with inline types and {1} constants
    for label, item in [("No Memo contract", {"op": "run", "spec": "G(o1[t]:bv[8] = i1[t]:bv[8] + {1}:bv[8])",
                                               "steps": [{"i1": "5"}], "expect": {"out": {"o1": ["6"]}}}),
                        ("No Memo 1 % cut", {"op": "run", "spec": "G(o1[t]:bv[24] = i1[t]:bv[24] / {100}:bv[24])",
                                             "steps": [{"i1": "1000"}, {"i1": "250"}, {"i1": "99"}], "expect": {"out": {"o1": ["10", "2", "0"]}}})]:
        got = tau_sandbox.ask(tau_sandbox.parse(item))
        good = matches(item["expect"], got)
        total += 1
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'} nomemo · {label}: run {item['spec']}")
        print(f"       → {shown(got)} ({got.get('ms')} ms)")
    # the brief on tauhud.com/learn/brief/: each listed set of requirements, joined with &&, must get the verdict the page shows
    brief = json.load(open(LESSONS, encoding="utf-8")).get("brief") or {}
    lines = {r["id"]: r["tau"] for r in brief.get("reqs") or []}
    for check in brief.get("checks") or []:
        spec = " && ".join(lines[i] for i in check["on"])
        for op in ("sat", "why"):
            got = tau_sandbox.ask(tau_sandbox.parse({"op": op, "spec": spec}))
            good = matches(check["expect"], got)
            total += 1
            fails += not good
            print(f"{'ok  ' if good else 'FAIL'} brief · {' '.join(check['on'])}: {op} {spec[:70]}")
            print(f"       → {shown(got)} ({got.get('ms')} ms)" + ("" if good else f"  expected {check['expect']}"))
    # No Memo's intel contracts (intel.py): every kind of hidden rule, run by this engine at its edges, must let through
    # exactly what the contract says, or a player who reads the engine right is told otherwise
    import intel
    good_rules = 0
    for rule in ({"kind": "cap", "a": 4100, "b": None}, {"kind": "floor", "a": 4100, "b": None}, {"kind": "band", "a": 3000, "b": 3500},
                 {"kind": "hole", "a": 3000, "b": 3500}, {"kind": "none", "a": 4100, "b": None}, {"kind": "above", "a": 4100, "b": None}):
        amounts = sorted({0, rule["a"] - 1, rule["a"], rule["a"] + 1, intel.MAX} | ({rule["b"] - 1, rule["b"], rule["b"] + 1} if rule["b"] else set()))[:8]
        got = tau_sandbox.ask(tau_sandbox.parse({"op": "run", "spec": intel.text(rule), "steps": [{"i1": str(a)} for a in amounts]}))
        seen = [str((row.get("out") or {}).get("o5")) for row in got.get("outputs") or []] if got.get("ok") else []
        want = ["1" if intel.passes(rule, a) else "0" for a in amounts]
        good = [int(x) != 0 if x.isdigit() else None for x in seen] == [w == "1" for w in want]
        good_rules += good
        print(f"{'ok  ' if good else 'FAIL'} intel · {rule['kind']}: {intel.words(rule)}")
        print(f"       → o5 {' '.join(seen) or shown(got)} for {', '.join(map(str, amounts))} ({got.get('ms')} ms)" + ("" if good else f"  expected {' '.join(want)}"))
    for rule in ({"kind": "reserve", "a": None, "b": 40000}, {"kind": "rich", "a": 3000, "b": 40000}, {"kind": "safe", "a": 3000, "b": 40000}):
        pts = [(0, 39999), (0, 40000), (3000, 39999), (3001, 39999), (3001, 40000), (intel.MAX, intel.MAX)]
        got = tau_sandbox.ask(tau_sandbox.parse({"op": "run", "spec": intel.text(rule), "steps": [{"i1": str(x), "i2": str(y)} for x, y in pts]}))
        seen = [str((row.get("out") or {}).get("o5")) for row in got.get("outputs") or []] if got.get("ok") else []
        want = ["1" if intel.passes2(rule, x, y) else "0" for x, y in pts]
        good = [int(x) != 0 if x.isdigit() else None for x in seen] == [w == "1" for w in want]
        good_rules += good
        print(f"{'ok  ' if good else 'FAIL'} intel · {rule['kind']}: {intel.words(rule)}")
        print(f"       → o5 {' '.join(seen) or shown(got)} for {', '.join(f'{x}@{y}' for x, y in pts)} ({got.get('ms')} ms)" + ("" if good else f"  expected {' '.join(want)}"))
    print(f"intel:   {good_rules} of 9 hidden rules answer as No Memo's contracts read them")
    # a guard that must hold: a file stream is refused before the engine sees it
    try:
        tau_sandbox.parse({"op": "run", "spec": "o1[t] = i1[t] && x := ifile(\"/etc/passwd\")"})
        print("FAIL guard: a file stream was let through")
        fails += 1
    except tau_sandbox.BadRequest:
        print("ok   guard: file streams refused")
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024
    print(f"tau:     {total - fails} of {total} lesson answers as the page says, biggest worker {peak} MB, "
          f"limit {tau_sandbox.BUDGET:g} s per question")


if __name__ == "__main__":
    main()
