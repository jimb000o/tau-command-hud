# "Enforced against the key holder", shown on the real testnet: a fresh test account writes itself a personal rule
# (nothing above 1,000 AGRS leaves), then the same key signs a payment of 5,000 and the node refuses it, while a payment
# of 500 goes through. Everything is signed by IDNI's own command-line wallet, not by tauhud.com: the refusal comes from
# the node, which checks every payment against the sender's rule whatever program signed it.
#
# Run inside the tau-node container (it has the tau-testnet CLI); it takes about 5 minutes:
#   cd /opt/tau-command-hud/infra && docker compose exec -T tau-node python - < node/tools/keyholder_demo.py
#
# Two fresh keys per run (the faucet funds a new account on its first transaction; test AGRS only). The keys and the
# result are kept in /data/keyholder-demo.json (the node's volume). At the end the rule is removed with the neutral
# clause. The last lines are one JSON object: copy them into the chat.
import json
import os
import re
import subprocess
import sys
import tempfile
import time

OUT = os.environ.get("DEMO_OUT", "/data/keyholder-demo.json")
FEE = os.environ.get("DEMO_FEE", "100")
LIMIT = 1000
RULE = ("always ( (i1[t]:bv[24] > { #x%06x }:bv[24]) "
        "? (o5[t]:bv[24] = { #x000000 }:bv[24]) : (o5[t]:bv[24] = { #x000001 }:bv[24]) )." % LIMIT)
NEUTRAL = "always ( (o5[t]:bv[24] = { #x000001 }:bv[24]) )."
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cli(*args):
    r = subprocess.run([sys.executable, "-m", "tau_testnet_cli", *args, "--json"], capture_output=True, text=True, timeout=180)
    return r.returncode, r.stdout, r.stderr


def data(out):
    try:
        j = json.loads(out)
    except ValueError:
        return {}
    return j.get("data", j) if isinstance(j, dict) else {}


def find(obj, key):
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


def num(pk, cmd, *keys):
    _, out, _ = cli(cmd, pk)
    for k in keys:
        v = find(data(out), k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    m = re.search(r"\d+", out)
    return int(m.group()) if m else None


def seq(pk):
    return num(pk, "sequence", "sequence_number", "sequence")


def balance(pk):
    return num(pk, "balance", "balance")


def landed(pk, before, minutes=6):
    end = time.time() + minutes * 60
    while time.time() < end:
        s = seq(pk)
        if s is not None and s > before:
            return True
        time.sleep(6)
    say(f"  ! gave up after {minutes} min waiting for the transaction to land")
    return False


def head():
    _, out, _ = cli("blocks", "--limit", "1")
    v = find(data(out), "block_number")
    if v is None:
        v = find(data(out), "height")
    return v


def newkey():
    _, out, _ = cli("keys", "new")
    d = data(out)
    priv, pub = find(d, "private_key_hex"), find(d, "public_key_hex")
    if not (priv and pub):
        sys.exit("cannot make a key: " + out[:300])
    return {"priv": str(priv), "pub": str(pub).lower().removeprefix("0x")}


def pay(k, to, amount):
    code, out, err = cli("tx", "send", "--privkey", k["priv"], "--to", to, "--amount", str(amount), "--fee", FEE)
    text = (out + "\n" + err).strip()
    resp = find(data(out), "response") or data(out)
    refused = bool(code) or (isinstance(resp, dict) and resp.get("ok") is False)
    msg = (find(resp, "message") if isinstance(resp, dict) else None) or text
    h = find(resp, "tx_hash") if isinstance(resp, dict) else None
    if not h:
        m = HEX64.search(text)
        h = m.group() if m else None
    return refused, str(msg)[:600], h


def set_rule(k, text):
    with tempfile.NamedTemporaryFile("w", suffix=".tau", delete=False) as f:
        f.write(text)
    before = seq(k["pub"]) or 0
    code, out, err = cli("tx", "send", "--privkey", k["priv"], "--rule-file", f.name, "--fee", FEE)
    os.unlink(f.name)
    if code:
        say("  ! the node refused the rule: " + (out + err).strip()[-300:])
        return False
    return landed(k["pub"], before)


def main():
    res = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "limit": LIMIT, "rule": RULE, "signer": "IDNI tau-testnet CLI"}
    a, b = newkey(), newkey()
    res["account"], res["receiver"] = a["pub"], b["pub"]
    say(f"account {a['pub'][:12]}…  receiver {b['pub'][:12]}…  (fresh test keys)")

    say("1/4 a first payment of 10 AGRS (the faucet funds the new account)")
    s0 = seq(a["pub"])
    refused, msg, h = pay(a, b["pub"], 10)
    if refused or not landed(a["pub"], s0 if s0 is not None else -1):
        say("  ! the first payment did not land: " + msg)
        return finish(res, False)
    res["first"] = {"tx": h, "block": head()}
    say(f"  landed, balance now {balance(a['pub'])}")

    say(f"2/4 the account writes itself a rule: nothing above {LIMIT:,} AGRS leaves")
    if not set_rule(a, RULE):
        return finish(res, False)
    res["rule_block"] = head()
    say(f"  rule in force (about block {res['rule_block']})")

    say("3/4 the same key signs a payment of 5,000 AGRS")
    bal0 = balance(a["pub"])
    refused, msg, h = pay(a, b["pub"], 5000)
    res["big"] = {"amount": 5000, "refused": refused, "node_said": msg, "balance_before": bal0}
    say("  " + ("REFUSED by the node: " if refused else "went through (unexpected!): ") + msg[:300])
    time.sleep(20)
    res["big"]["balance_after"] = balance(a["pub"])

    say("4/4 and a payment of 500 AGRS, inside the rule")
    before = seq(a["pub"]) or 0
    refused2, msg2, h2 = pay(a, b["pub"], 500)
    ok2 = not refused2 and landed(a["pub"], before)
    res["small"] = {"amount": 500, "landed": ok2, "tx": h2, "block": head() if ok2 else None, "node_said": None if ok2 else msg2}
    say("  " + ("went through" if ok2 else "did not go through: " + msg2[:300]))

    say("cleanup: the neutral clause removes the rule")
    res["removed"] = set_rule(a, NEUTRAL)
    finish(res, refused and ok2 and "own policy" in msg)


def finish(res, proven):
    res["proven"] = bool(proven)
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with open(OUT, "w") as f:
            json.dump(res, f, indent=1)
    except OSError:
        pass
    say("PROVEN" if proven else "NOT PROVEN, see the lines marked ! or 'unexpected'")
    print("---- copy everything below into the chat ----")
    print(json.dumps(res, separators=(",", ":")))


main()
