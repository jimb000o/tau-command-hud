"""One Tau Language question from tauhud.com/learn, answered in a throwaway process.

tau_sandbox.py starts this file once per question with the request as JSON on
stdin and reads one JSON answer from the original stdout. The engine prints its
own diagnostics straight to file descriptors 1 and 2, so both are pointed at a
temporary file while it works; that text comes back as "log" when there is any.

Ops, all from the tau-lang Python binding (the same module the node uses):
  sat / unsat / valid / realizable   the verdict, T or F
  why                                unsat_core: the smallest set of parts that already contradict
  run                                get_interpreter + step: feed inputs step by step, read the outputs
"""
import json
import os
import re
import sys
import tempfile

TESTNET_DIR = os.environ.get("TAU_TESTNET_DIR", "/app/tau-testnet")
sys.path.insert(0, TESTNET_DIR)

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
VERDICT_OPS = ("sat", "unsat", "valid", "realizable")


def clean(text) -> str:
    return ANSI.sub("", str(text or "")).strip()


def errors_of(report) -> str:
    try:
        lines = [clean(e) for e in report.errors]
    except Exception:
        lines = []
    text = "; ".join(l for l in lines if l)
    if not text:
        text = clean(getattr(report, "text", "") or "")
    return re.sub(r"^\(Error\)\s*", "", text)[:600]


def short_value(raw: str) -> str:
    """{ 5 }:bv[8] -> 5, { #x000001 }:bv[24] -> 1, T/F and other values as printed."""
    s = clean(raw)
    m = re.fullmatch(r"\{\s*(.*?)\s*\}\s*(:\s*\w+(\[\d+\])?)?", s)
    if m:
        s = m.group(1)
    else:
        s = re.sub(r":\s*bv\[\d+\]$", "", s).strip()
    try:
        if s.lower().startswith("#x"):
            return str(int(s[2:], 16))
        if s.lower().startswith("#b"):
            return str(int(s[2:], 2))
    except ValueError:
        pass
    return s


def answer(tau, req):
    op, spec = req["op"], req["spec"]
    if op in VERDICT_OPS:
        res = getattr(tau, op)(spec)
        value = res.value if res else None
        if value is None:
            return {"ok": False, "error": errors_of(res.report) or "Tau gave no verdict for this formula", "unknown": True}
        return {"ok": True, "verdict": bool(value)}

    if op == "why":
        res = tau.unsat_core(spec, True)
        value = res.value if res else None
        if value is None:
            return {"ok": False, "error": errors_of(res.report) or "Tau found no answer for this formula"}
        core = [clean(part) for part in value]
        return {"ok": True, "verdict": not core, "core": core}

    # run
    res = tau.get_interpreter(spec)
    interp = res.value if res else None
    if interp is None:
        return {"ok": False, "error": errors_of(res.report) or "Tau could not run this spec (it may be unsatisfiable)"}
    rows = []
    for step_no, given in enumerate(req["steps"]):
        outputs = None
        asked = {}
        for _ in range(20):   # a step may ask for its inputs in more than one round, as tau_native does
            need = tau.get_inputs_for_step(interp)
            wanted = need.value if need else None
            if wanted is None:
                return {"ok": False, "error": errors_of(need.report) or "the engine asked for no inputs", "outputs": rows}
            assignments = {}
            for stream in wanted:
                value = str(given.get(stream.name, "0"))
                assignments[stream] = value
                asked[stream.name] = value
            before = interp.time_point
            stepped = tau.step(interp, assignments)
            outputs = stepped.value if stepped else None
            if outputs is not None:
                break
            report = stepped.report
            if getattr(report, "awaiting_input", False) and interp.time_point == before:
                continue
            return {"ok": False, "error": errors_of(report) or f"step {step_no} stopped without outputs", "outputs": rows}
        else:
            return {"ok": False, "error": f"step {step_no} kept asking for inputs", "outputs": rows}
        row = {"t": step_no, "in": asked, "out": {}}
        for stream, value in outputs.items():
            row["out"][stream.name] = short_value(value)
        rows.append(row)
    return {"ok": True, "verdict": True, "outputs": rows}


def main():
    req = json.loads(sys.stdin.read())
    reply = os.fdopen(os.dup(1), "w")
    capture = tempfile.TemporaryFile()
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(capture.fileno(), 1)
    os.dup2(capture.fileno(), 2)
    try:
        import tau_native
        tau = tau_native.load_tau_module()
        try:
            tau.set_colors(False)
        except Exception:
            pass
        result = answer(tau, req)
    except Exception as exc:  # the engine's own error text is the useful part
        result = {"ok": False, "error": clean(exc)[:600] or exc.__class__.__name__}
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    capture.seek(0)
    log = clean(capture.read().decode("utf-8", "replace"))
    if log:
        result["log"] = log[-1500:]
    reply.write(json.dumps(result))
    reply.flush()


if __name__ == "__main__":
    main()
