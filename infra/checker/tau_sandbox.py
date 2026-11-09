"""Tau Language sandbox for tauhud.com/learn: one formula in, one answer out.

checker.py serves it at POST /tau. Each question runs tau_worker.py in a new
process of its own session, so nothing a visitor typed survives the answer, and
the whole process group is killed at the deadline. The container adds the rest
(docker-compose.yml): read-only, no network, capped memory, CPU and processes.

Request  {"op": "sat"|"unsat"|"valid"|"realizable"|"why"|"run", "spec": "<tau>",
          "steps": [{"i1": "5"}, ...]}            steps only for run, at most 8
Answer   {"ok": true, "op", "verdict": true|false, "core": [...] (why),
          "outputs": [{"t", "in": {...}, "out": {...}}] (run), "ms", "engine"}
      or {"ok": false, "error": "...", ...}
"""
from __future__ import annotations

import json
import os
import re
import resource
import signal
import subprocess
import sys
import time

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tau_worker.py")
TESTNET_DIR = os.environ.get("TAU_TESTNET_DIR", "/app/tau-testnet")
OPS = ("sat", "unsat", "valid", "realizable", "why", "run")
MAX_SPEC = 2048
MAX_STEPS = 8
BUDGET = float(os.environ.get("TAU_BUDGET", "5"))       # seconds of wall time per question
# Optional address-space cap of one worker in MB (0 = off). The container's memory cap
# (docker-compose.yml) is the real guard: the engine's libraries reserve a lot of
# virtual memory they never touch, so a tight address-space cap breaks it.
MEMORY = int(os.environ.get("TAU_MEMORY_MB", "0"))

# No file or console streams, no stream declarations (":= in ..."), and not the
# natural-language algebra, which can call out. Everything else is plain logic.
REFUSED = re.compile(r"\b(ifile|ofile|file|console|nlang|include|load)\b|:=\s*(in|out)\b", re.I)
STREAM_NAME = re.compile(r"^(i\w{0,15}|this)$")
VALUE = re.compile(r"^[\w#{}:\[\]'. +-]{1,120}$")


class BadRequest(ValueError):
    pass


def parse(data) -> dict:
    if not isinstance(data, dict):
        raise BadRequest("send a JSON object")
    op = str(data.get("op", "")).strip().lower()
    spec = data.get("spec")
    if op not in OPS:
        raise BadRequest("op must be one of " + ", ".join(OPS))
    if not isinstance(spec, str) or not spec.strip():
        raise BadRequest("spec must be a non-empty string")
    spec = spec.strip()
    if len(spec.encode("utf-8")) > MAX_SPEC:
        raise BadRequest(f"spec is over {MAX_SPEC} bytes")
    if REFUSED.search(spec):
        raise BadRequest("files, the console, stream declarations and nlang are switched off here; use streams such as i1[t] and o1[t]")
    steps = []
    if op == "run":
        raw = data.get("steps")
        if raw is None:
            raw = [{}, {}, {}]
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_STEPS:
            raise BadRequest(f"steps must be a list of 1 to {MAX_STEPS} steps")
        for step in raw:
            if not isinstance(step, dict) or len(step) > 8:
                raise BadRequest("each step is an object of at most 8 inputs, such as {\"i1\": \"5\"}")
            clean = {}
            for name, value in step.items():
                value = str(value).strip()
                if not STREAM_NAME.match(str(name)) or not VALUE.match(value):
                    raise BadRequest(f"input {name!r} = {value!r} is not allowed")
                clean[str(name)] = value
            steps.append(clean)
    return {"op": op, "spec": spec, "steps": steps}


def _limits():
    """In the child, before the worker starts: its own memory, CPU time and file size caps."""
    caps = [(resource.RLIMIT_CPU, int(BUDGET) + 2), (resource.RLIMIT_FSIZE, 4 * 1024 * 1024), (resource.RLIMIT_CORE, 0)]
    if MEMORY > 0:
        caps.append((resource.RLIMIT_AS, MEMORY * 1024 * 1024))
    for res, value in caps:
        try:
            resource.setrlimit(res, (value, value))
        except (ValueError, OSError):
            pass


def ask(req: dict, budget: float = BUDGET) -> dict:
    """Run one parsed request in a fresh worker. Always returns a dict with "ok" and "ms"."""
    started = time.monotonic()
    proc = subprocess.Popen([sys.executable, "-I", WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, cwd=TESTNET_DIR, start_new_session=True,
                            preexec_fn=_limits)
    try:
        out, _ = proc.communicate(json.dumps(req).encode(), timeout=budget)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        return {"ok": False, "timeout": True, "ms": int((time.monotonic() - started) * 1000),
                "error": f"Tau needed more than {budget:g} seconds, so the question was stopped. Try a smaller formula."}
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    ms = int((time.monotonic() - started) * 1000)
    try:
        result = json.loads(out.decode("utf-8", "replace") or "null")
    except ValueError:
        result = None
    if not isinstance(result, dict):
        why = "ran out of memory" if proc.returncode in (-9, -11, 137, 139) else f"stopped (code {proc.returncode})"
        return {"ok": False, "ms": ms, "error": f"the Tau engine {why} on this formula"}
    result["ms"] = ms
    return result
