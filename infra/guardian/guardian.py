"""Guardian: a second factor for a Tau Testnet Alpha account, hosted for tauhud.com/guardian/.

The account's own rule (an o5 policy, tau-testnet docs/approvals.md) says "a payment above N needs the Guardian's
co-signature". A payment above N then parks on the chain as an approval_request. Its owner types the 6-digit code from
an authenticator app (Google Authenticator, Authy, 1Password …) on tauhud.com/guardian/; this service checks the code
and, only then, co-signs with its own key (a feeless transfer_vote). Below N nothing changes.

What it can do and what it cannot:
- It can only say yes to a payment the account itself asked for, and only to one that names the Guardian. It can never
  send, move or hold anything: it has no account key of anyone and no funds (votes are feeless).
- If it is down, payments above the limit wait and run out (expire_at_height); nothing below the limit is touched.
- Whoever holds the account key can still replace or remove the rule (the protocol allows it today). This guards against
  a mistaken or tricked payment, not against a stolen key. The page says so.
- The code never goes on chain: six digits on chain can be brute-forced in their validity window.

Built on IDNI's reference approver bot in tau-testnet (scripts/approval_bot_totp.py and approval_bot_common.py): its
RFC 6238 code check, enrolment store, rate limiter, one-time use per (account, time step), node client and signer are
used as they are, from the node image this service runs in (docker-compose.yml, same image as the node). What is added
here: an HTTPS door for the page instead of the loopback port, enrolment that proves the account (a BLS signature from
the account's own key), confirmation of the first code before an enrolment counts, and a per-account lock after wrong
codes.

    python guardian.py serve      the service (docker-compose.yml `guardian`)
    python guardian.py status     what `up guardian` prints: the Guardian's address, accounts, last approvals

HTTP (Caddy: node.tauhud.com/guardian/*), JSON in and out:
    GET  /guardian/info                      {pubkey, slot, enabled, accounts, max_accounts, issuer}
    GET  /guardian/account?pk=<96 hex>        {enrolled, since, approvals}
    POST /guardian/enroll   {account, at, signature[, code]}   -> {secret, uri}   (code: the current one, to move phones)
    POST /guardian/confirm  {account, code}                    -> {enrolled: true}
    POST /guardian/approve  {request_id, code}                 -> {approved: true, tx_hash}
    POST /guardian/remove   {account, at, signature, code}     -> {removed: true}
The signature is BLS over sha256 of the text "tauhud guardian <enroll|remove> <account> <at>", made by the account's key
in the visitor's browser (wallet/vendor/tau-bls.min.js, the same signing the wallet uses for transactions).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

TAU_TESTNET_DIR = os.environ.get("TAU_TESTNET_DIR", "/app/tau-testnet")
for p in (TAU_TESTNET_DIR, os.path.join(TAU_TESTNET_DIR, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import approval_bot_common as idni_common  # noqa: E402  (IDNI/tau-testnet scripts/)
import approval_bot_totp as idni_totp  # noqa: E402

log = logging.getLogger("guardian")

ENABLED = os.environ.get("GUARDIAN_ENABLED", "1") not in ("0", "false", "no", "")
DATA = os.environ.get("GUARDIAN_DATA", "/data")
NODE_HOST = os.environ.get("NODE_HOST", "tau-node")
NODE_PORT = int(os.environ.get("NODE_PORT", "65432"))
PORT = int(os.environ.get("GUARDIAN_PORT", "8075"))
MAX_ACCOUNTS = int(os.environ.get("GUARDIAN_MAX_ACCOUNTS", "50"))   # a testnet prototype: a short list of accounts
POLL = float(os.environ.get("GUARDIAN_POLL_SECONDS", "15"))
ISSUER = "Tau HUD Guardian"
SLOT = 18   # the first approval slot (i18); the page writes the rule with the Guardian there
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://tauhud.com,https://www.tauhud.com,https://jimb000o.github.io").split(",") if o.strip()]
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") == "1"

SIGNED_AGE = 600            # an enrol or remove signature is good for 10 minutes
PENDING_TTL = 15 * 60       # a QR code shown but not confirmed yet
WRONG_MAX, WRONG_WINDOW = 5, 15 * 60   # five wrong codes for one account: that account waits 15 minutes
BODY_MAX = 4096
REASON = "code from the account's authenticator app"

PK = re.compile(r"^[0-9a-f]{96}$")
SIG = re.compile(r"^[0-9a-f]{192}$")
RID = re.compile(r"^[0-9a-f]{64}$")
CODE = re.compile(r"^\d{6}$")


class Refused(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def proof_text(action: str, account: str, at: int) -> bytes:
    return f"tauhud guardian {action} {account} {at}".encode()


def verify_proof(action: str, account: str, at, signature: str, now: float) -> None:
    """The account's own key signed this request a moment ago (BLS over sha256, as the node checks transactions)."""
    if not isinstance(at, int) or abs(now - at) > SIGNED_AGE:
        raise Refused(400, "The signature is too old; reload the page and try again.")
    if not isinstance(signature, str) or not SIG.match(signature):
        raise Refused(400, "signature must be 192 hex characters.")
    from py_ecc.bls import G2Basic
    try:
        ok = G2Basic.Verify(bytes.fromhex(account), hashlib.sha256(proof_text(action, account, at)).digest(),
                            bytes.fromhex(signature))
    except Exception:
        ok = False
    if not ok:
        raise Refused(403, "This was not signed by that account's key.")


class GuardianBot(idni_totp.TotpBot):
    """IDNI's TOTP bot, asked by the page instead of a loopback port.

    vote() is the one part written here, because IDNI's own builds the transaction with tau_testnet_cli.tx, which pulls
    in the whole node (database, engine). It builds the same fields as tau_testnet_cli.tx.build_transfer_vote_tx and
    signs them with IDNI's Signer (the node's own preimage, consensus/tx_signing.py)."""

    name = "guardian"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vote_lock = threading.Lock()
        self.last_vote: dict = {}

    def vote(self, request_id: str, approve: bool, reason: str = ""):
        with self.vote_lock:
            seq = self.client.data(f"getsequence {self.signer.pubkey}")
            tip = seq.get("tip_height")
            if not isinstance(tip, int) or isinstance(tip, bool):
                raise idni_common.RpcError("node did not report tip_height")
            payload = {
                "tx_type": "transfer_vote",
                "sender_pubkey": self.signer.pubkey,
                "sequence_number": int(seq["sequence_number"]),
                "expiration_time": int(time.time()) + 3600,
                "expire_at_height": tip + idni_common.VOTE_EXPIRY_BLOCKS,
                "fee_limit": "0",
                "request_id": request_id.lower(),
                "approve": bool(approve),
            }
            if reason:
                payload["reason"] = reason[:256]
            self.signer.sign(payload)
            res = self.client.rpc("sendtx '" + json.dumps(payload, separators=(",", ":")) + "'")
            self.last_vote = res
            if res.get("status") != "ok" or (res.get("data") or {}).get("ok") is False:
                log.error("vote on %s refused: %s", request_id[:16], json.dumps(res.get("error") or res)[:300])
            else:
                log.info("co-signed %s", request_id[:16])
            return res


class Guardian:
    def __init__(self, data_dir: str = DATA, client=None, clock=time.time):
        self.dir = data_dir
        self.clock = clock
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self.store = idni_totp.EnrollmentStore(os.path.join(self.dir, "enroll"))
        self.store.check_permissions()
        self.meta_path = os.path.join(self.dir, "guardian.json")
        self.meta = self._load_meta()
        signer = idni_common.Signer(self._key())
        self.bot = GuardianBot(client or idni_common.NodeClient(NODE_HOST, NODE_PORT, timeout=30.0), signer,
                               store=self.store, poll_seconds=POLL)
        self.pubkey = signer.pubkey
        self.pending: dict[str, tuple[str, float]] = {}   # account -> (secret shown as QR, when)
        self.wrong: dict[str, list[float]] = {}           # account -> times of wrong codes
        self.ip_codes = idni_totp._RateLimiter(burst=6, refill_per_sec=0.2)
        self.ip_enrol = idni_totp._RateLimiter(burst=4, refill_per_sec=1 / 60)
        self.lock = threading.Lock()

    # ---------- files ----------
    def _key(self) -> str:
        path = os.path.join(self.dir, "guardian.key")
        if not os.path.exists(path):
            import secrets
            from py_ecc.bls import G2Basic
            sk = G2Basic.KeyGen(secrets.token_bytes(32))
            sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(sk.to_bytes(32, "big").hex())
        return idni_common.load_privkey(SimpleNamespace(privkey_file=path, privkey=None))   # refuses a loose mode

    def _load_meta(self) -> dict:
        try:
            with open(self.meta_path) as f:
                m = json.load(f)
        except (OSError, ValueError):
            m = {}
        m.setdefault("accounts", {})
        m.setdefault("approvals", [])
        m.setdefault("wrong_codes", 0)
        return m

    def _save_meta(self):
        tmp = self.meta_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.meta, f, indent=1, sort_keys=True)
        os.replace(tmp, self.meta_path)

    # ---------- what the page reads ----------
    def info(self) -> dict:
        return {"pubkey": self.pubkey, "slot": SLOT, "enabled": ENABLED, "accounts": len(self.store.load()),
                "max_accounts": MAX_ACCOUNTS, "issuer": ISSUER}

    def account(self, pk: str) -> dict:
        pk = (pk or "").lower()
        if not PK.match(pk):
            raise Refused(400, "pk must be 96 hex characters.")
        a = self.meta["accounts"].get(pk) or {}
        return {"enrolled": bool(self.store.secret_for(pk)), "since": a.get("since"), "approvals": a.get("approvals", 0)}

    # ---------- enrolment ----------
    def _locked(self, account: str, now: float) -> bool:
        times = [t for t in self.wrong.get(account, []) if now - t < WRONG_WINDOW]
        self.wrong[account] = times
        return len(times) >= WRONG_MAX

    def _wrong(self, account: str, now: float):
        self.wrong.setdefault(account, []).append(now)
        self.meta["wrong_codes"] = self.meta.get("wrong_codes", 0) + 1

    def _check_current_code(self, account: str, code, now: float) -> None:
        """The code of the authenticator already connected; one use per time step, as IDNI's bot keeps it."""
        if self._locked(account, now):
            raise Refused(429, "Too many wrong codes for this account; wait 15 minutes.")
        secret = self.store.secret_for(account)
        step = idni_totp.verify_totp(secret, str(code or ""), now=int(now)) if secret else None
        if step is None:
            self._wrong(account, now)
            raise Refused(403, "That code is not right. Use the newest one in the app.")
        with self.bot._lock:
            if (account, step) in self.bot._used_steps:
                raise Refused(403, "That code was used already; wait for the next one.")
            self.bot._used_steps.add((account, step))

    def enroll(self, body: dict, ip: str) -> dict:
        if not ENABLED:
            raise Refused(503, "The Guardian is switched off on our server.")
        if not self.ip_enrol.allow(ip):
            raise Refused(429, "Too many tries from here; wait a minute.")
        account = str(body.get("account", "")).lower()
        if not PK.match(account):
            raise Refused(400, "account must be 96 hex characters.")
        now = self.clock()
        verify_proof("enroll", account, body.get("at"), body.get("signature"), now)
        with self.lock:
            enrolled = self.store.load()
            if account in enrolled:
                self._check_current_code(account, body.get("code"), now)   # a new phone: only with the old one's code
            elif len(enrolled) >= MAX_ACCOUNTS:
                raise Refused(409, f"The Guardian takes {MAX_ACCOUNTS} accounts on the testnet, and all are taken.")
            self.pending = {k: v for k, v in self.pending.items() if now - v[1] < PENDING_TTL}
            secret = idni_totp.new_secret()
            self.pending[account] = (secret, now)
        return {"secret": secret, "uri": idni_totp.otpauth_uri(secret, "tauhud:" + account[:8] + "…" + account[-4:], issuer=ISSUER)}

    def confirm(self, body: dict, ip: str) -> dict:
        if not self.ip_codes.allow(ip):
            raise Refused(429, "Too many codes from here; wait a minute.")
        account = str(body.get("account", "")).lower()
        code = str(body.get("code", ""))
        now = self.clock()
        with self.lock:
            p = self.pending.get(account)
            if not p or now - p[1] >= PENDING_TTL:
                raise Refused(404, "No QR code waits for this account; show a new one.")
            if self._locked(account, now):
                raise Refused(429, "Too many wrong codes for this account; wait 15 minutes.")
            step = idni_totp.verify_totp(p[0], code, now=int(now)) if CODE.match(code) else None
            if step is None:
                self._wrong(account, now)
                raise Refused(403, "That code is not right. Use the newest one in the app.")
            data = self.store.load()
            data[account] = p[0]
            self.store.save(data)   # IDNI's store: 0600 file in a 0700 folder
            with self.bot._lock:
                self.bot._used_steps.add((account, step))
            del self.pending[account]
            a = self.meta["accounts"].setdefault(account, {"approvals": 0})
            a["since"] = int(now)
            self._save_meta()
        log.info("enrolled %s", account[:12])
        return {"enrolled": True}

    def remove(self, body: dict, ip: str) -> dict:
        if not self.ip_codes.allow(ip):
            raise Refused(429, "Too many codes from here; wait a minute.")
        account = str(body.get("account", "")).lower()
        if not PK.match(account):
            raise Refused(400, "account must be 96 hex characters.")
        now = self.clock()
        verify_proof("remove", account, body.get("at"), body.get("signature"), now)
        with self.lock:
            if not self.store.secret_for(account):
                raise Refused(404, "This account has no Guardian.")
            self._check_current_code(account, body.get("code"), now)
            data = self.store.load()
            data.pop(account, None)
            self.store.save(data)
            self.meta["accounts"].pop(account, None)
            self._save_meta()
        log.info("removed %s", account[:12])
        return {"removed": True}

    # ---------- the co-signature ----------
    def approve(self, body: dict, ip: str) -> dict:
        if not ENABLED:
            raise Refused(503, "The Guardian is switched off on our server.")
        if not self.ip_codes.allow(ip):
            raise Refused(429, "Too many codes from here; wait a minute.")
        request_id = str(body.get("request_id", "")).lower()
        code = str(body.get("code", ""))
        if not RID.match(request_id):
            raise Refused(400, "request_id must be 64 hex characters.")
        if not CODE.match(code):
            raise Refused(400, "The code has 6 digits.")
        try:
            inbox = self.bot.inbox()
        except Exception as exc:
            log.warning("inbox unavailable: %r", exc)
            raise Refused(503, "Our node does not answer right now; your payment waits. Try again in a minute.")
        req = next((r for r in inbox if str(r.get("request_id", "")).lower() == request_id), None)
        if req is None:
            raise Refused(404, "No payment with this id waits for the Guardian (it may be paid, expired or not in a block yet).")
        slot, state = self.bot.my_slot(req)
        if slot is None or state != "awaiting":
            raise Refused(409, "The Guardian has answered this payment already.")
        sender = str(req.get("sender_pubkey", "")).lower()
        now = self.clock()
        with self.lock:
            if self._locked(sender, now):
                raise Refused(429, "Too many wrong codes for this account; wait 15 minutes.")
        self.bot.decide(req)                     # IDNI's bot: the request is now one it waits on
        ok, detail = self.bot.submit_code(request_id, code)   # IDNI's check: enrolled, right code, not used before
        if not ok:
            with self.lock:
                if detail == "invalid code":
                    self._wrong(sender, now)
                self._save_meta()
            words = {"invalid code": "That code is not right. Use the newest one in the app.",
                     "code already used": "That code was used already; wait for the next one."}
            raise Refused(403, words.get(detail) or ("This account has no Guardian yet." if "not enrolled" in detail else detail))
        self.bot._acted.add(request_id)   # so the poll does not sign it a second time meanwhile
        try:
            res = self.bot.vote(request_id, True, REASON)
        except Exception as exc:
            log.warning("vote failed: %r", exc)
            self.bot._acted.discard(request_id)   # the poll signs it on its next round
            raise Refused(503, "Code accepted, but our node did not take the signature yet; it is sent again within a minute.")
        if res.get("status") != "ok" or (res.get("data") or {}).get("ok") is False:
            self.bot._acted.discard(request_id)
            raise Refused(502, "Code accepted, but the node refused the signature: "
                          + str((res.get("error") or {}).get("message") or "no reason given")[:160])
        with self.lock:
            a = self.meta["accounts"].setdefault(sender, {"approvals": 0})
            a["approvals"] = a.get("approvals", 0) + 1
            self.meta["approvals"] = (self.meta["approvals"] + [{"t": int(now), "request": request_id, "amount": req.get("amount"),
                                                                 "account": sender[:12]}])[-50:]
            self._save_meta()
        return {"approved": True, "tx_hash": (res.get("data") or {}).get("tx_hash"), "amount": req.get("amount")}

    def loop(self):
        """IDNI's poll: a code accepted while the node was busy is signed on the next round."""
        while True:
            try:
                if ENABLED:
                    self.bot.tick()
            except Exception:
                log.exception("poll failed")
            time.sleep(POLL)


# ---------- HTTP ----------
def make_handler(g: Guardian):
    class Handler(BaseHTTPRequestHandler):
        server_version = "guardian"

        def log_message(self, *a):   # no access log: no visitor addresses in the container log (tauhud.com/legal/)
            pass

        def _ip(self) -> str:
            if TRUST_PROXY and self.headers.get("X-Forwarded-For"):
                return self.headers["X-Forwarded-For"].split(",")[0].strip()
            return self.client_address[0]

        def _send(self, status: int, data: dict):
            body = json.dumps(data, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            origin = self.headers.get("Origin")
            if origin and (origin in ALLOWED_ORIGINS or re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin)):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            origin = self.headers.get("Origin")
            if origin in ALLOWED_ORIGINS or re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin or ""):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            u = urlsplit(self.path)
            try:
                if u.path == "/guardian/health":
                    return self._send(200, {"ok": True})
                if u.path == "/guardian/info":
                    return self._send(200, g.info())
                if u.path == "/guardian/account":
                    return self._send(200, g.account((parse_qs(u.query).get("pk") or [""])[0]))
                self._send(404, {"error": "not here"})
            except Refused as r:
                self._send(r.status, {"error": r.message})

        def do_POST(self):
            u = urlsplit(self.path)
            route = {"/guardian/enroll": g.enroll, "/guardian/confirm": g.confirm,
                     "/guardian/approve": g.approve, "/guardian/remove": g.remove}.get(u.path)
            if not route:
                return self._send(404, {"error": "not here"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > BODY_MAX:
                    raise Refused(413, "Too large.")
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    raise Refused(400, "Send JSON.")
                if not isinstance(body, dict):
                    raise Refused(400, "Send a JSON object.")
                self._send(200, route(body, self._ip()))
            except Refused as r:
                self._send(r.status, {"error": r.message})
            except Exception:
                log.exception("request failed")
                self._send(500, {"error": "Something went wrong on our server."})

    return Handler


def status(g: Guardian) -> int:
    """For `up guardian`: plain lines for the chat block."""
    info = g.info()
    print(f"guardian: {'on' if ENABLED else 'switched off (GUARDIAN_ENABLED=0 in .env)'}, address {g.pubkey[:12]}…{g.pubkey[-4:]}, "
          f"{info['accounts']} of {MAX_ACCOUNTS} accounts connected, {g.meta.get('wrong_codes', 0)} wrong codes so far")
    try:
        seq = g.bot.client.data(f"getsequence {g.pubkey}")
        print(f"          node answers: {seq.get('sequence_number')} co-signatures sent, chain at block {seq.get('tip_height')}")
        waiting = g.bot.inbox()
        print(f"          payments waiting for a code now: {len(waiting)}")
    except Exception as exc:
        print(f"          node does not answer ({exc!r})")
    for a in g.meta.get("approvals", [])[-3:]:
        when = time.strftime("%d.%m. %H:%M UTC", time.gmtime(a["t"]))
        print(f"          co-signed {when}: {a.get('amount')} test AGRS from {a.get('account')}…")
    print("          page: https://tauhud.com/guardian/")
    return 0


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    g = Guardian()
    if argv[:1] == ["status"]:
        return status(g)
    log.info("guardian %s on :%d, %s, node %s:%d", g.pubkey[:16], PORT, "on" if ENABLED else "OFF", NODE_HOST, NODE_PORT)
    threading.Thread(target=g.loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), make_handler(g)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
