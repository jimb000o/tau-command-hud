"""Rule Playground checker: runs a visitor's Tau rule through the testnet's own checks.

tauhud.com/playground posts a personal transfer rule (an o5 clause) and a few
sample transfers. This service answers what the Tau Testnet Alpha would do with
them, using tau-testnet's own code from the node image rather than a copy:

  1. consensus.rule_offers.normalize_offer_rule_text   shape screen
  2. consensus.admission._screen_clause_domains        stream / time / width screens
  3. the engine, the way the node of the running commit asks it:
     - since IDNI main 5ad1bb7 (per-account clauses): tau_policy.PolicyEvaluator, the
       policy worker admission and apply use. The body is built on its own
       (`always ( body ).`, refused when it does not build or reads no input), then
       each sample transfer OF THE SENDER is stepped and o5 read. A transfer by
       anyone else is not judged by this clause at all.
     - before that: consensus.rule_offers.compose_stream_rule (the guarded composite
       the node stored) in tau_speculation.SpeculationSession: build the baseline,
       revise with the composite, then step each sample transfer and read o5.

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
    MAX_OFFER_RULE_BYTES, RuleOfferShapeError, normalize_offer_rule_text,
)
import tau_native  # noqa: E402
import tau_speculation  # noqa: E402
try:   # gone in IDNI main 5ad1bb7: every account's o5 rule is its own clause, judged on its own
    from consensus.rule_offers import compose_stream_rule  # noqa: E402
except ImportError:
    compose_stream_rule = None
PER_ACCOUNT = compose_stream_rule is None
if PER_ACCOUNT:
    import tau_policy  # noqa: E402
    from consensus.sender_policy import clause_inputs  # noqa: E402
# The balance a test transfer's sender has (i2, which a per-account clause may read): a fresh testnet account's faucet
# balance unless the test gives one.
TEST_BALANCE = 100_000

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intel  # noqa: E402  No Memo's intel contracts: a hidden rule judged by the same engine (POST /tau/intel)
import tau_sandbox  # noqa: E402  the Tau Language sandbox for tauhud.com/learn (POST /tau)

logging.basicConfig(level=logging.INFO, format="%(asctime)s checker %(levelname)s %(message)s")
log = logging.getLogger("checker")

PORT = int(os.environ.get("PORT", "8090"))
ALLOWED_ORIGINS = [o.strip() for o in (os.environ.get("ALLOWED_ORIGINS")
    or "https://tauhud.com,https://www.tauhud.com,https://jimb000o.github.io").split(",") if o.strip()]
# Commit ids shortened to 7 characters for display.
ENGINE_LABEL = re.sub(r"\b([0-9a-f]{7})[0-9a-f]{33}\b", r"\1", os.environ.get("ENGINE_LABEL", ""))
MAX_BODY = 16 * 1024
MAX_TESTS = 8
BUDGET = float(os.environ.get("CHECK_BUDGET", "30"))  # seconds of engine time per request
QUEUE_WAIT = 30.0                  # seconds a request may wait for the engine
MAX_WAITING = 4                    # requests allowed to wait at once
# per client address; only real engine runs count (cached answers and text refusals are free)
RATE_WINDOW, RATE_MAX = 300.0, int(os.environ.get("RATE_MAX", "24"))
TAU_RATE_MAX = int(os.environ.get("TAU_RATE_MAX", "40"))  # /tau questions per address per window
MAX_BV24 = (1 << 24) - 1
MAX_TIME = (1 << 64) - 1
HEX96 = re.compile(r"^[0-9a-f]{96}$")
# The co-signature slots i18..i25 (tau_defs.APPROVAL_SLOT_BASE/COUNT). The node feeds every slot on each step once a rule
# reads them: 0 for no signature, else the approver's key (consensus/engine.py); a test does the same, so a co-signature
# rule is stepped as the chain steps it.
SLOT_BASE, SLOT_COUNT = 18, 8
SIGNED_OK = False   # set by _prove_signed once this engine has answered a co-signature rule as expected
READS_SLOTS = re.compile(r"\bi(1[89]|2[0-5])\s*\[")

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


def _rate_wait(addr: str, limit: int = RATE_MAX) -> int:
    """Seconds until this address may start another engine run (0 = now)."""
    now = time.monotonic()
    with _hits_lock:
        q = _hits.get(addr)
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if not q or len(q) < limit:
            return 0
        return max(1, int(q[0] + RATE_WINDOW - now + 0.999))


def _rate_charge(addr: str) -> None:
    with _hits_lock:
        _hits.setdefault(addr, collections.deque()).append(time.monotonic())
        if len(_hits) > 5000:  # forget idle addresses
            for k in [k for k, v in _hits.items() if not v]:
                del _hits[k]


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
    """The engine's own words for a refusal: its first error line, else its report.

    sendtx._revision_refusal reads the same two places in the other order; the
    diagnostic line is the more specific one ("Incompatible type information in
    i4 ..." rather than "type inference produced no tree"), so it goes first here.
    """
    for key in ("diagnostics", "deferred_diagnostics"):
        for line in str(receipt.get(key) or "").splitlines():
            if "rror" in line:
                text = tau_native.strip_ansi(line).strip()
                return re.sub(r"^\(Error\)\s*", "", text)[:400]
    errors = (receipt.get("report") or {}).get("errors") or []
    if errors:
        return tau_native.strip_ansi(str(errors[0])).strip()[:400]
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
        # co-signatures for this transfer (tauhud.com/builder/): signed[k] is the approver in slot i(18+k), "" for none
        signed = t.get("signed") or []
        if not isinstance(signed, list) or len(signed) > SLOT_COUNT:
            raise ValueError(f"signed must be a list of at most {SLOT_COUNT} addresses")
        signed = [str(x or "").lower() for x in signed]
        if not all(x == "" or HEX96.match(x) for x in signed):
            raise ValueError("signed holds 96 lowercase hex digits or empty strings")
        row = {"amount": amount, "time": time_, "from": frm, "to": to}
        if t.get("balance") is not None:
            balance = int(t["balance"])
            if not 0 <= balance <= MAX_BV24:
                raise ValueError("test balance out of range")
            row["balance"] = balance
        if any(signed):
            row["signed"] = signed
        clean.append(row)
    return rule, sender, clean


def check(rule: str, sender: str, tests: list, engine_ok: bool = True) -> dict:
    """The verdict for one rule, in the node's order. Cheap screens before any engine work.
    With engine_ok False, a rule that would need a fresh engine run returns {"limited": True}."""
    if len(rule.encode("utf-8")) > MAX_OFFER_RULE_BYTES:
        return {"accepted": False, "stage": "size", "reason": f"over the {MAX_OFFER_RULE_BYTES} byte limit"}
    try:
        body, stream = normalize_offer_rule_text(rule)
    except RuleOfferShapeError as exc:
        return {"accepted": False, "stage": "shape", "reason": str(exc)}
    domain_error = admission._screen_clause_domains(body)
    if domain_error:
        return {"accepted": False, "stage": "streams", "reason": domain_error}
    # what the node keeps: the clause on its own, or (before 5ad1bb7) the composite behind the sender guard
    composite = tau_policy.clause_spec(body) if PER_ACCOUNT else compose_stream_rule(stream, {sender: body})

    key = hashlib.sha256(json.dumps([composite, sender if PER_ACCOUNT else "", tests], sort_keys=True).encode()).hexdigest()
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return dict(_cache[key], cached=True)
    if not engine_ok:
        return {"limited": True}

    started = time.monotonic()
    deadline = started + BUDGET
    left = lambda: max(0.5, deadline - time.monotonic())  # noqa: E731
    result = {"composite": composite, "engine": ENGINE_LABEL}
    if PER_ACCOUNT:
        return _check_clause(body, sender, tests, result, started, left, key)
    session = tau_speculation.SpeculationSession(cwd=TESTNET_DIR)
    try:
        session.init(SEED_SPEC, timeout=left())
        for i, rule in enumerate(BUILTIN_RULES):
            if session.revise(rule, candidate_id=f"builtin-{i}", timeout=left()).get("outcome") not in tau_speculation.ACCEPTED:
                raise tau_speculation.SpeculationError(f"builtin rule {i} did not replay")
        receipt = session.revise(tau_native.TauInterface.preprocess_spec_text(composite),
                                 candidate_id="playground", timeout=left())
        outcome = receipt.get("outcome")
        result["outcome"] = outcome
        # Every outcome but acceptance refuses, as sendtx._revision_refusal does.
        if outcome == "REJECTED_NOT_ROUTED":
            result.update(accepted=False, stage="engine", reason=_first_error(receipt)
                          or "the rule contradicts itself or the network's rules, so Tau found no way to apply it")
        elif outcome not in tau_speculation.ACCEPTED:
            result.update(accepted=False, stage="engine",
                          reason=_first_error(receipt) or f"the Tau engine refused the rule ({outcome})")
        else:
            result["accepted"] = True
            runs = []
            slots = bool(READS_SLOTS.search(composite))
            for t in tests:
                inputs = {"i1": str(t["amount"]), "i3": "#x" + t["from"], "i4": "#x" + t["to"],
                          "i5": str(t["time"]), "i12": "#x" + t["from"]}
                if slots:
                    signed = t.get("signed") or []
                    for k in range(SLOT_COUNT):
                        who = signed[k] if k < len(signed) else ""
                        inputs[f"i{SLOT_BASE + k}"] = "#x" + who if who else "0"
                resp = session.step(inputs, timeout=left())
                outs = resp.get("outputs") if resp.get("ok") else None
                runs.append({"ok": outs is not None,
                             "o5": _o5_value(outs.get("o5")) if outs else None,
                             "o1": _o5_value(outs.get("o1")) if outs else None})
            result["tests"] = runs
        session.close()
    except tau_speculation.WorkerTimeout:
        # Deterministic for this text, like the node's ADMISSION_TIMEOUT: too heavy.
        session.kill()
        result.update(accepted=False, stage="engine", timeout=True,
                      reason=f"the engine needed more than {BUDGET:g} seconds, so the check was stopped")
    except (tau_speculation.SpeculationError, tau_speculation.WorkerLost) as exc:
        session.kill()
        log.warning("engine unavailable: %s", exc)
        return {"accepted": None, "stage": "engine", "unavailable": True,
                "reason": "the engine stopped unexpectedly"}
    result["ms"] = int((time.monotonic() - started) * 1000)
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > 256:
            _cache.popitem(last=False)
    return result


def _check_clause(body: str, sender: str, tests: list, result: dict, started: float, left, key: str) -> dict:
    """The engine part for per-account clauses (IDNI main 5ad1bb7 on), as consensus/sender_policy.py asks it: does the
    clause build and step once on its own, then o5 for each of the sender's own test transfers. A clause the engine
    cannot step on a transfer's inputs blocks it, as on the node."""
    evaluator = tau_policy.PolicyEvaluator(pool="checker", cwd=TESTNET_DIR)
    try:
        built = evaluator.validate(body, timeout=left())
        if not built.ok:
            reason = _first_error({"diagnostics": built.error}) or built.error.strip()[:400]
            result.update(accepted=False, stage="engine",
                          reason=reason or "the rule does not build on the Tau engine, so the node would refuse it")
        else:
            result["accepted"] = True
            runs = []
            slots = bool(READS_SLOTS.search(body))
            for t in tests:
                if t["from"] != sender:   # someone else's transfer: this clause is never asked
                    runs.append({"ok": True, "o5": 1, "o1": None, "other": True})
                    continue
                inputs = {"i1": str(t["amount"]), "i2": str(t.get("balance", TEST_BALANCE)), "i3": "#x" + t["from"],
                          "i4": "#x" + t["to"], "i5": str(t["time"])}
                if slots:
                    signed = t.get("signed") or []
                    for k in range(SLOT_COUNT):
                        who = signed[k] if k < len(signed) else ""
                        inputs[f"i{SLOT_BASE + k}"] = "#x" + who if who else "0"
                try:
                    v = evaluator.verdict(body, clause_inputs(inputs), timeout=left())
                    runs.append({"ok": True, "o5": tau_policy.parse_o5(v.o5) if v.o5 is not None else 1, "o1": None})
                except (tau_policy.PolicyBuildError, tau_policy.PolicyStepError):
                    runs.append({"ok": True, "o5": 0, "o1": None, "refused_step": True})   # the node blocks it
            result["tests"] = runs
        evaluator.close()
    except tau_speculation.WorkerTimeout:
        _drop(evaluator)
        result.update(accepted=False, stage="engine", timeout=True,
                      reason=f"the engine needed more than {BUDGET:g} seconds, so the check was stopped")
    except (tau_speculation.SpeculationError, tau_speculation.WorkerLost) as exc:
        _drop(evaluator)
        log.warning("engine unavailable: %s", exc)
        return {"accepted": None, "stage": "engine", "unavailable": True, "reason": "the engine stopped unexpectedly"}
    result["ms"] = int((time.monotonic() - started) * 1000)
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > 256:
            _cache.popitem(last=False)
    return result


def _drop(evaluator) -> None:
    """Throw a stuck or lost policy worker away without waiting on it."""
    w = getattr(evaluator, "_worker", None)
    evaluator._worker = None
    evaluator._closed = True
    if w is not None:
        try:
            w.kill()
        except Exception:
            pass


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

    def _json(self, status, payload, headers=None):
        blob = json.dumps(payload).encode()
        self.send_response(status)
        self._cors()
        for k, v in (headers or {}).items():
            self.send_header(k, v)
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
            # signed: test transfers may carry co-signatures, proven on this engine at start (_prove_signed)
            return self._json(200, {"ok": True, "engine": ENGINE_LABEL, "signed": SIGNED_OK})
        if self.path.rstrip("/") == "/tau/health":
            return self._json(200, {"ok": True, "engine": ENGINE_LABEL, "budget_s": tau_sandbox.BUDGET,
                                    "max_spec": tau_sandbox.MAX_SPEC, "max_steps": tau_sandbox.MAX_STEPS, "intel": list(intel.CASES)})
        self._json(404, {"error": "not found"})

    def _engine_slot(self) -> bool:
        """Wait for the one engine slot the Playground and /tau share; False when it stays busy."""
        global _waiting
        with _waiting_lock:
            if _waiting >= MAX_WAITING:
                return False
            _waiting += 1
        try:
            return _engine.acquire(timeout=QUEUE_WAIT)
        finally:
            with _waiting_lock:
                _waiting -= 1

    def _tau(self):
        """POST /tau: one Tau Language question from tauhud.com/learn (tau_sandbox.py)."""
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS and "*" not in ALLOWED_ORIGINS:
            return self._json(403, {"ok": False, "error": "origin not allowed"})
        size = int(self.headers.get("Content-Length") or 0)
        if size <= 0 or size > MAX_BODY:
            return self._json(413, {"ok": False, "error": f"body must be 1 to {MAX_BODY} bytes"})
        try:
            req = tau_sandbox.parse(json.loads(self.rfile.read(size)))
        except (ValueError, tau_sandbox.BadRequest) as exc:
            return self._json(400, {"ok": False, "error": str(exc)})
        key = "tau:" + hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()
        with _cache_lock:
            if key in _cache:
                _cache.move_to_end(key)
                return self._json(200, dict(_cache[key], cached=True))
        client = "tau:" + self._client()
        wait = _rate_wait(client, TAU_RATE_MAX)
        if wait:
            return self._json(429, {"ok": False, "error": "too many questions from this address, wait a little",
                                    "retry_after": wait}, {"Retry-After": str(wait)})
        if not self._engine_slot():
            return self._json(503, {"ok": False, "error": "the engine is busy, try again in a few seconds"})
        try:
            result = tau_sandbox.ask(req)
        except Exception:
            log.exception("tau failed")
            result = {"ok": False, "error": "internal error"}
        finally:
            _engine.release()
        _rate_charge(client)
        result.update(op=req["op"], engine=ENGINE_LABEL)
        # a timeout or a crash is as deterministic as a verdict for the same text, so it is cached too
        if "ms" in result:
            with _cache_lock:
                _cache[key] = result
                while len(_cache) > 256:
                    _cache.popitem(last=False)
        log.info("tau: %s ok=%s %sms", req["op"], result.get("ok"), result.get("ms", "-"))
        self._json(200, result)

    def _intel(self):
        """POST /tau/intel: one move in a No Memo intel contract (intel.py). A probe or the one-shot edge runs the hidden
        rule in the real engine, as /tau runs a question, and counts against the same per-address limit; naming the rule
        or giving up needs no engine run but counts too, so the rule cannot be guessed by brute force."""
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS and "*" not in ALLOWED_ORIGINS:
            return self._json(403, {"ok": False, "error": "origin not allowed"})
        size = int(self.headers.get("Content-Length") or 0)
        if size <= 0 or size > MAX_BODY:
            return self._json(413, {"ok": False, "error": f"body must be 1 to {MAX_BODY} bytes"})
        try:
            req = intel.parse(json.loads(self.rfile.read(size)))
        except (ValueError, intel.BadRequest) as exc:
            return self._json(400, {"ok": False, "error": str(exc)})
        client = "tau:" + self._client()
        steps = intel.steps_of(req)
        run = None
        if steps is not None:
            spec = intel.text(intel.deal(req["case"], req["seed"]))
            key = "intel:" + hashlib.sha256(json.dumps({"spec": spec, "steps": steps}, sort_keys=True).encode()).hexdigest()
            with _cache_lock:
                run = _cache.get(key)
                if run is not None:
                    _cache.move_to_end(key)
        if run is None:
            wait = _rate_wait(client, TAU_RATE_MAX)
            if wait:
                return self._json(429, {"ok": False, "error": "too many questions from this address, wait a little",
                                        "retry_after": wait}, {"Retry-After": str(wait)})
            _rate_charge(client)
        if steps is not None and run is None:
            if not self._engine_slot():
                return self._json(503, {"ok": False, "error": "the engine is busy, try again in a few seconds"})
            try:
                run = tau_sandbox.ask({"op": "run", "spec": spec, "steps": steps})
            except Exception:
                log.exception("intel failed")
                run = {"ok": False, "error": "internal error"}
            finally:
                _engine.release()
            if run.get("ok"):
                with _cache_lock:
                    _cache[key] = run
                    while len(_cache) > 256:
                        _cache.popitem(last=False)
        result = intel.answer(req, lambda _spec, _steps: run)
        if result.pop("agrees", True) is False:   # the engine is the judge; a contract that reads it otherwise must be fixed
            log.warning("intel: the engine and the contract's reading differ (%s, %s)", req["case"], intel.deal(req["case"], req["seed"])["kind"])
        result["engine"] = ENGINE_LABEL
        log.info("intel: %s %s ok=%s %sms", req["case"], next((k for k in ("probe", "final", "name", "reveal", "lead") if k in req), "-"),
                 result.get("ok"), result.get("ms", "-"))
        self._json(200 if result.get("ok") else 503, result)

    def do_POST(self):
        global _waiting
        if self.path.rstrip("/") == "/tau":
            return self._tau()
        if self.path.rstrip("/") == "/tau/intel":
            return self._intel()
        if self.path.rstrip("/") != "/check":
            return self._json(404, {"error": "not found"})
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS and "*" not in ALLOWED_ORIGINS:
            return self._json(403, {"error": "origin not allowed"})
        size = int(self.headers.get("Content-Length") or 0)
        if size <= 0 or size > MAX_BODY:
            return self._json(413, {"error": f"body must be 1 to {MAX_BODY} bytes"})
        client = self._client()
        try:
            rule, sender, tests = _validate_request(json.loads(self.rfile.read(size)))
        except Exception as exc:
            return self._json(400, {"error": f"bad request: {exc}"})

        wait = _rate_wait(client)
        if wait:
            # over the limit: screens and cached answers still come back, only a fresh engine run waits
            result = check(rule, sender, tests, engine_ok=False)
            if result.get("limited"):
                return self._json(429, {"error": "too many engine runs from this address", "retry_after": wait},
                                  {"Retry-After": str(wait)})
            return self._json(200 if result.get("accepted") is not None else 503, result)

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
        if "ms" in result and not result.get("cached"):
            _rate_charge(client)
        # the visitor's address is used for the rate limit in memory only and is not logged
        log.info("check: %s %s %sms", result.get("stage", "-"), result.get("accepted"), result.get("ms", "-"))
        self._json(200 if result.get("accepted") is not None else 503, result)

    def log_message(self, *args):  # requests are logged once, in do_POST
        pass


def _prove_signed() -> None:
    """Once at start: step a co-signature rule with and without its signature on this engine. Only when all four
    answers are the expected ones does /check/health say "signed": true, and only then does tauhud.com/builder/
    send co-signed test payments; until then it shows them as not checked."""
    global SIGNED_OK
    you, bob, carol, now = "db" * 48, "8a" * 48, "42" * 48, int(time.time())
    rule = (f"always ( (i1[t]:bv[24] > {{ #x0003e8 }}:bv[24] && !(i18[t]:bv[384] = {{ #x{carol} }}:bv[384]))"
            " ? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) ).")
    tx = lambda amount, signed: {"amount": amount, "time": now, "from": you, "to": bob, "signed": signed}  # noqa: E731
    try:
        with _engine:
            got = check(rule, you, [tx(500, []), tx(5000, []), tx(5000, [carol]), tx(5000, [bob])])
        answers = [t.get("o5") for t in got.get("tests") or []]
        SIGNED_OK = got.get("accepted") is True and answers == [1, 0, 1, 0]
        log.info("co-signed test payments: %s (answers %s%s)", "on" if SIGNED_OK else "off", answers,
                 "" if got.get("accepted") else f", rule refused: {got.get('reason')}")
    except Exception:
        log.exception("co-signed test payments: off, the self-check failed")


if __name__ == "__main__":
    threading.Thread(target=_prove_signed, daemon=True).start()
    log.info("%s, listening on :%d", "per-account clauses (policy worker)" if PER_ACCOUNT
             else f"baseline: genesis + {len(BUILTIN_RULES)} builtin rules", PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
