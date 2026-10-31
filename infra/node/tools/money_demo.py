# Money with terms, shown on the real testnet: a returnable payment taken back, one released, a co-signed payment and a
# time lock, sent between three test wallets of our own. Every step is an ordinary transaction through our node, so the
# chain records it and the alerts bot (alerts/firsts.py) posts the firsts to Telegram and X by itself.
#
# Run inside the tau-node container (it has the tau-testnet CLI), in tmux, it takes about 25 minutes:
#   cd /opt/tau-command-hud/infra && docker compose exec -T tau-node python - < node/tools/money_demo.py
#
# The three keys are made once and kept in /data/money-demo.json (the node's volume); they hold test AGRS only, which
# the testnet's faucet gives every new account. Run it again and it reuses them. Steps 3 to 5 need one of the testnet's
# two personal-rule places (MAX_TIER_AUTHORS = 2); when both are taken they are skipped and step 1 and 2 still run.
# At the end the rule is removed with the neutral clause, so the place is free again.
import json
import os
import re
import subprocess
import sys
import tempfile
import time

KEYS = os.environ.get("DEMO_KEYS", "/data/money-demo.json")
LOCK_MIN = int(os.environ.get("DEMO_LOCK_MINUTES", 10))
FEE = os.environ.get("DEMO_FEE", "100")
NEUTRAL = "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cli(*args, ok_fail=False):
    """One CLI call; returns (exit code, stdout, stderr)."""
    r = subprocess.run([sys.executable, "-m", "tau_testnet_cli", *args, "--json"], capture_output=True, text=True, timeout=120)
    if r.returncode and not ok_fail:
        say("  ! " + " ".join(args[:2]) + f" exit {r.returncode}: " + (r.stderr or r.stdout).strip()[:600])
    return r.returncode, r.stdout, r.stderr


def data(out):
    try:
        j = json.loads(out)
    except ValueError:
        return {}
    return j.get("data", j) if isinstance(j, dict) else {}


def find(obj, key):
    """The first value under `key` anywhere in obj."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            r = find(v, key)
            if r is not None:
                return r
    return None


def wait(what, check, minutes=10, every=8):
    end = time.time() + minutes * 60
    while time.time() < end:
        r = check()
        if r:
            return r
        time.sleep(every)
    say(f"  ! gave up waiting for {what} after {minutes} min")
    return None


def keys():
    if os.path.exists(KEYS):
        return json.load(open(KEYS))
    k = {}
    for name in ("sender", "receiver", "cosigner"):
        _, out, _ = cli("keys", "new")
        d = data(out)
        priv, pub = find(d, "private_key_hex"), find(d, "public_key_hex")
        if not (priv and pub):
            sys.exit("cannot make a key: " + out[:300])
        k[name] = {"priv": str(priv), "pub": str(pub).lower().removeprefix("0x")}
    with open(KEYS, "w") as f:
        json.dump(k, f)
    os.chmod(KEYS, 0o600)
    return k


def seq(pk):
    _, out, _ = cli("sequence", pk, ok_fail=True)
    v = find(data(out), "sequence_number")
    if v is None:
        v = find(data(out), "sequence")
    try:
        return int(v)
    except (TypeError, ValueError):
        m = re.search(r"\d+", out)
        return int(m.group()) if m else None


def landed(pk, before):
    return wait("the transaction to land in a block", lambda: (s := seq(pk)) is not None and s > before)


def retractable(rid):
    _, out, _ = cli("retractable", "show", rid, ok_fail=True)
    return find(data(out), "status")


def request(rid):
    _, out, _ = cli("approval", "show", rid, ok_fail=True)
    return find(data(out), "status")


def send_retractable(k, amount, after):
    code, out, err = cli("retractable", "send", "--privkey", k["sender"]["priv"], "--to", k["receiver"]["pub"],
                         "--amount", str(amount), "--release-after", str(after), "--fee", FEE)
    m = re.search(r"retractable id:\s*([0-9a-f]{64})", err + out)
    return m.group(1) if not code and m else None


def ask_cosigned(k, amount):
    s = seq(k["sender"]["pub"])
    code, out, err = cli("approval", "request", "--privkey", k["sender"]["priv"], "--to", k["receiver"]["pub"],
                         "--amount", str(amount), "--approver", "18=" + k["cosigner"]["pub"], "--fee", FEE)
    if code:
        return None
    rid = find(data(out), "request_id")
    if not rid:
        sub = find(data(out), "submitted") or {}
        _, o2, _ = cli("approval", "request-id", "--from-pubkey", k["sender"]["pub"], "--to", k["receiver"]["pub"],
                       "--amount", str(amount), "--sequence", str(sub.get("sequence_number", s)),
                       "--expire-at-height", str(sub.get("expire_at_height", 0)), "--approver", "18=" + k["cosigner"]["pub"])
        m = HEX64.search(o2)
        rid = m.group() if m else None
    return rid


def main():
    k = keys()
    A, B, C = (k[n]["pub"] for n in ("sender", "receiver", "cosigner"))
    say(f"sender {A[:12]}…  receiver {B[:12]}…  co-signer {C[:12]}…  (keys in {KEYS})")
    done = []

    say("1/5 a returnable payment, then taken back")
    rid = send_retractable(k, 25, 1800)
    if rid and wait("the payment in escrow", lambda: retractable(rid) == "open"):
        say(f"  25 AGRS in escrow, returnable for 30 min: {rid}")
        cli("retractable", "retract", "--privkey", k["sender"]["priv"], rid)
        if wait("the take-back", lambda: retractable(rid) == "retracted"):
            say("  taken back before its release point: the money is home again")
            done.append("returnable payment taken back")

    say("2/5 a returnable payment that is released by itself")
    rid = send_retractable(k, 10, 150)
    if rid and wait("the payment in escrow", lambda: retractable(rid) == "open"):
        say(f"  10 AGRS in escrow until about {time.strftime('%H:%M', time.localtime(time.time() + 150))}: {rid}")
        if wait("the release", lambda: retractable(rid) == "released", minutes=12):
            say("  released at its release point, with no further transaction")
            done.append("returnable payment released")

    lock = int(time.time()) + 120 + LOCK_MIN * 60
    rule = ("always ( ( (i1[t]:bv[24] > { #x0003e8 }:bv[24] && i5[t]:bv[64] < { %d }:bv[64]) "
            "|| (i1[t]:bv[24] > { #x000064 }:bv[24] && !(i18[t]:bv[384] = { #x%s }:bv[384])) ) "
            "? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )." % (lock, C))
    say(f"3/5 the sender's own rule: above 100 AGRS the co-signer must sign; above 1,000 nothing leaves before "
        f"{time.strftime('%H:%M', time.localtime(lock))}")
    with tempfile.NamedTemporaryFile("w", suffix=".tau", delete=False) as f:
        f.write(rule)
    before = seq(A)
    code, out, err = cli("tx", "send", "--privkey", k["sender"]["priv"], "--rule-file", f.name, "--fee", FEE)
    if code:
        if "CLAUSE_REGISTRY_FULL" in out + err:
            say("  both personal-rule places on the testnet are taken; steps 3 to 5 skipped")
        return finish(done)
    if not landed(A, before):
        return finish(done)
    say("  rule in force")
    code, out, err = cli("tx", "send", "--privkey", k["sender"]["priv"], "--to", B, "--amount", "500", "--fee", FEE, ok_fail=True)
    say("  a plain payment of 500 AGRS: " + ("REFUSED by the sender's own rule, as it should be" if code else "went through (unexpected!)"))

    say("4/5 a co-signed payment of 500 AGRS")
    rid = ask_cosigned(k, 500)
    if rid and wait("the request on chain", lambda: request(rid) == "open"):
        say(f"  waiting for its co-signer: {rid}")
        cli("approval", "approve", "--privkey", k["cosigner"]["priv"], rid)
        if wait("the payment to go through", lambda: request(rid) in ("executed", "failed")) and request(rid) == "executed":
            say("  co-signed, so it went through")
            done.append("co-signed payment")

    say("5/5 the time lock: 2,000 AGRS before and after the lock time, both co-signed")
    rid = ask_cosigned(k, 2000)
    if rid and wait("the request on chain", lambda: request(rid) == "open"):
        cli("approval", "approve", "--privkey", k["cosigner"]["priv"], rid)
        st = wait("the verdict", lambda: (s := request(rid)) in ("executed", "failed") and s)
        say(f"  before the lock time: {st}" + (" (the lock held, even with the co-signature)" if st == "failed" else ""))
    left = lock - time.time() + 20
    if left > 0:
        say(f"  waiting {round(left / 60)} min for the lock time")
        time.sleep(left)
    rid = ask_cosigned(k, 2000)
    if rid and wait("the request on chain", lambda: request(rid) == "open"):
        cli("approval", "approve", "--privkey", k["cosigner"]["priv"], rid)
        st = wait("the verdict", lambda: (s := request(rid)) in ("executed", "failed") and s)
        say(f"  after the lock time: {st}")
        if st == "executed":
            done.append("time lock")

    say("cleanup: the neutral clause frees the personal-rule place")
    before = seq(A)
    with open(f.name, "w") as g:
        g.write(NEUTRAL)
    if not cli("tx", "send", "--privkey", k["sender"]["priv"], "--rule-file", f.name, "--fee", FEE)[0] and landed(A, before):
        say("  place freed")
    finish(done)


def finish(done):
    say("DONE: " + (", ".join(done) if done else "nothing completed, see the lines marked !"))
    say("The bot posts the firsts on Telegram and X about 10 minutes after the last one; the HUD tile lights up by itself.")


main()
