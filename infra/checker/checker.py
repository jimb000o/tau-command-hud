"""Rule Playground checker: runs a visitor's Tau rule through the testnet's own checks.

tauhud.com/playground posts a personal transfer rule (an o5 clause) and a few
sample transfers. This service answers what the Tau Testnet Alpha would do with
them, using tau-testnet's own code from the node image rather than a copy:

  1. consensus.rule_offers.normalize_offer_rule_text   shape screen
  2. consensus.admission._screen_clause_domains        stream / time / width screens
  3. consensus.rule_offers.compose_stream_rule         the guarded composite the node stores
  4. tau_speculation.SpeculationSession                the isolated, killable engine worker
                                                       admission itself uses: build the
                                                       baseline, revise with the composite,
                                                       then step each sample transfer and
                                                       read o5.

Nothing here touches the chain or the node. Every request gets a fresh worker
process that is thrown away afterwards. Limits: one engine run at a time, a short
queue, a per-address rate limit, a body cap, a test cap and per-step deadlines;
the container itself is capped in memory, CPU and process count (docker-compose.yml).
"""
from __future__ import annotations

import collections
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TESTNET_DIR = os.environ.get("TAU_TESTNET_DIR", "/app/tau-testnet")
sys.path.insert(0, TESTNET_DIR)

from consensus import admission  # noqa: E402
from consensus.rule_offers import (  # noqa: E402
    MAX_OFFER_RULE_BYTES, RuleOfferShapeError, compose_stream_rule, normalize_offer_rule_text,
)
import tau_native  # noqa: E402
import tau_speculation  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s checker %(levelname)s %(message)s")
log = logging.getLogger("checker")

PORT = int(os.environ.get("PORT", "8090"))
ALLOWED_ORIGINS = [o.strip() for o in (os.environ.get("ALLOWED_ORIGINS")
    or "https://tauhud.com,https://www.tauhud.com,https://jimb000o.github.io").split(",") if o.strip()]
ENGINE_LABEL = os.environ.get("ENGINE_LABEL", "")
MAX_BODY = 16 * 1024
MAX_TESTS = 8
STEP_TIMEOUT = float(os.environ.get("STEP_TIMEOUT", "20"))
QUEUE_WAIT = 30.0                  # seconds a request may wait for the engine
MAX_WAITING = 4                    # requests allowed to wait at once
RATE_WINDOW, RATE_MAX = 300.0, 12  # per client address
MAX_BV24 = (1 << 24) - 1
MAX_TIME = (1 << 64) - 1
HEX96 = re.compile(r"^[0-9a-f]{96}$")

# The application spec a fresh node starts from, built the way the node builds it
# (tau_native.compile_revisions_isolated): genesis.tau seeds the interpreter, and
# the shipped transfer-validation rules are replayed through i0 on top. A personal
# rule is then offered on i0 against exactly this, as admission does.
def _baseline():
    with open(os.path.join(TESTNET_DIR, "genesis.tau"), encoding="utf-8") as fh:
        seed = tau_native.TauInterface.preprocess_spec_text(fh.read())
    rules = []
    rules_dir = os.path.join(TESTNET_DIR, "rules")
    for name in sorted(os.listdir(rules_dir)):
        if name.endswith(".tau") and not name.startswith("_"):
            with open(os.path.join(rules_dir, name), encoding="utf-8") as fh:
                text = tau_native.TauInterface.preprocess_spec_text(fh.read())
            if text:
                rules.append(text)
    return seed, rules


SEED_SPEC, BUILTIN_RULES = _baseline()

_engine = threading.Semaphore(1)
_waiting = 0
_waiting_lock = threading.Lock()
_hits: dict[str, collections.deque] = {}
_hits_lock = threading.Lock()
_cache: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
_cache_lock = threading.Lock()


def _rate_ok(addr: str) -> bool:
    now = time.monotonic()
    with _hits_lock:
        q = _hits.setdefault(addr, collections.deque())
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_MAX:
            return False
        q.append(now)
        if len(_hits) > 5000:  # forget idle addresses
            for k in [k for k, v in _hits.items() if not v]:
                del _hits[k]
        return True


def _o5_value(text):
    """o5 as an int from the engine's printed value, or None if absent or unreadable."""
    if text is None:
        return None
    s = str(text).strip().strip("{}").strip()
    s = s.split(":")[0].strip()
    try:
        if s.lower().startswith("#x"):
            return int(s[2:], 16)
        if s.lower().startswith("#b"):
            return int(s[2:], 2)
        return int(s, 10)
    except ValueError:
        return None


def _first_error(receipt) -> str:
    for key in ("diagnostics", "deferred_diagnostics"):
        for line in tau_native.strip_ansi(receipt.get(key) or "").splitlines():
            if "Error" in line:
                return line.strip()[:400]
    return ""


def _validate_request(data):
    rule = data.get("rule")
    sender = str(data.get("sender", "")).lower()
    tests = data.get("tests") or []
    if not isinstance(rule, str) or not rule.strip():
        raise ValueError("rule must be a non-empty string")
    if not HEX96.match(sender):
        raise ValueError("sender must be 96 lowercase hex digits")
    if not isinstance(tests, list) or len(tests) > MAX_TESTS:
        raise ValueError(f"tests must be a list of at most {MAX_TESTS}")
    clean = []
    for t in tests:
        amount, time_, frm, to = int(t["amount"]), int(t["time"]), str(t["from"]).lower(), str(t["to"]).lower()
        if not (0 <= amount <= MAX_BV24 and 0 <= time_ <= MAX_TIME and HEX96.match(frm) and HEX96.match(to)):
            raise ValueError("test transfer out of range")
        clean.append({"amount": amount, "time": time_, "from": frm, "to": to})
    return rule, sender, clean


def check(rule: str, sender: str, tests: list) -> dict:
    """The verdict for one rule, in the node's order. Cheap screens before any engine work."""
    if len(rule.encode("utf-8")) > MAX_OFFER_RULE_BYTES:
        return {"accepted": False, "stage": "size", "reason": f"over the {MAX_OFFER_RULE_BYTES} byte limit"}
    try:
        body, stream = normalize_offer_rule_text(rule)
    except RuleOfferShapeError as exc:
        return {"accepted": False, "stage": "shape", "reason": str(exc)}
    domain_error = admission._screen_clause_domains(body)
    if domain_error:
        return {"accepted": False, "stage": "streams", "reason": domain_error}
    composite = compose_stream_rule(stream, {sender: body})

    key = hashlib.sha256(json.dumps([composite, tests], sort_keys=True).encode()).hexdigest()
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return dict(_cache[key], cached=True)

    started = time.monotonic()
    result = {"composite": composite, "engine": ENGINE_LABEL}
    session = tau_speculation.SpeculationSession(cwd=TESTNET_DIR, timeout=STEP_TIMEOUT)
    try:
        session.init(SEED_SPEC)
        for i, rule in enumerate(BUILTIN_RULES):
            if session.revise(rule, candidate_id=f"builtin-{i}").get("outcome") not in tau_speculation.ACCEPTED:
                raise tau_speculation.SpeculationError(f"builtin rule {i} did not replay")
        receipt = session.revise(tau_native.TauInterface.preprocess_spec_text(composite), candidate_id="playground")
        outcome = receipt.get("outcome")
        result["outcome"] = outcome
        if outcome == "REJECTED_RULE":
            result.update(accepted=False, stage="engine",
                          reason=_first_error(receipt) or "the Tau engine refused the rule")
        elif outcome == "REJECTED_NOT_ROUTED":
            result.update(accepted=False, stage="engine",
                          reason="the rule contradicts itself or the network's rules, so Tau found no way to apply it")
        elif outcome not in tau_speculation.ACCEPTED:
            result.update(accepted=False, stage="engine", reason=f"the engine gave no verdict ({outcome})")
        else:
            result["accepted"] = True
            runs = []
            for t in tests:
                resp = session.step({
                    "i1": str(t["amount"]), "i3": "#x" + t["from"], "i4": "#x" + t["to"],
                    "i5": str(t["time"]), "i12": "#x" + t["from"],
                })
                outs = resp.get("outputs") if resp.get("ok") else None
                runs.append({"ok": outs is not None,
                             "o5": _o5_value(outs.get("o5")) if outs else None,
                             "o1": _o5_value(outs.get("o1")) if outs else None})
            result["tests"] = runs
        session.close()
    except (tau_speculation.SpeculationError, tau_speculation.WorkerLost) as exc:
        session.kill()
        log.warning("engine unavailable: %s", exc)
        return {"accepted": None, "stage": "engine", "unavailable": True,
                "reason": "the engine could not finish in time"}
    result["ms"] = int((time.monotonic() - started) * 1000)
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > 256:
            _cache.popitem(last=False)
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "tauhud-checker"
    sys_version = ""

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")

    def _json(self, status, payload):
        blob = json.dumps(payload).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def _client(self):
        # Caddy sets X-Forwarded-For; the checker is reachable only through Caddy.
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("/check/health", "/health"):
            return self._json(200, {"ok": True, "engine": ENGINE_LABEL})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        global _waiting
        if self.path.rstrip("/") != "/check":
            return self._json(404, {"error": "not found"})
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS and "*" not in ALLOWED_ORIGINS:
            return self._json(403, {"error": "origin not allowed"})
        size = int(self.headers.get("Content-Length") or 0)
        if size <= 0 or size > MAX_BODY:
            return self._json(413, {"error": f"body must be 1 to {MAX_BODY} bytes"})
        if not _rate_ok(self._client()):
            return self._json(429, {"error": "too many checks, try again in a few minutes"})
        try:
            rule, sender, tests = _validate_request(json.loads(self.rfile.read(size)))
        except Exception as exc:
            return self._json(400, {"error": f"bad request: {exc}"})

        with _waiting_lock:
            if _waiting >= MAX_WAITING:
                return self._json(503, {"error": "the checker is busy, try again shortly"})
            _waiting += 1
        try:
            if not _engine.acquire(timeout=QUEUE_WAIT):
                return self._json(503, {"error": "the checker is busy, try again shortly"})
        finally:
            with _waiting_lock:
                _waiting -= 1
        try:
            result = check(rule, sender, tests)
        except Exception:
            log.exception("check failed")
            result = {"accepted": None, "stage": "engine", "unavailable": True, "reason": "internal error"}
        finally:
            _engine.release()
        log.info("check from %s: %s %s %sms", self._client(), result.get("stage", "-"),
                 result.get("accepted"), result.get("ms", "-"))
        self._json(200 if result.get("accepted") is not None else 503, result)

    def log_message(self, *args):  # requests are logged once, in do_POST
        pass


if __name__ == "__main__":
    log.info("baseline: genesis + %d builtin rules, listening on :%d", len(BUILTIN_RULES), PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
