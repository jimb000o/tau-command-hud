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
#
# Every step waits until its transaction is CONFIRMED in a block (gettxstatus), not merely accepted: the sequence number
# the node reports counts waiting transactions too, so it cannot tell "in force" from "queued".
#
# Look back at an earlier run instead (which of the account's transactions are in the last 120 blocks):
#   cd /opt/tau-command-hud/infra && docker compose exec -T -e INSPECT=<account> tau-node python - < node/tools/keyholder_demo.py
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


def status(h):
    _, out, _ = cli("rpc", "gettxstatus " + h)
    # `rpc --json` prints {"response": {"status": "ok", "data": {..., "status": "confirmed"}}}: the tx status is inside data
    d = find(data(out), "data")
    d = d if isinstance(d, dict) else {}
    return (d.get("status") or "unknown"), d


def confirm(h, minutes=6):
    """Wait until tx `h` is in a block; returns (status, block number or None, details)."""
    end = time.time() + minutes * 60
    st, d = "unknown", {}
    while time.time() < end:
        st, d = status(h)
        if st == "confirmed":
            return st, find(d, "block_number"), d
        if st in ("rejected", "evicted", "expired"):
            return st, None, d
        time.sleep(5)
    say(f"  ! still '{st}' after {minutes} min")
    return st, None, d


def send(args):
    code, out, err = cli("tx", "send", *args, "--fee", FEE)
    text = (out + "\n" + err).strip()
    d = data(out)
    resp = find(d, "response")
    resp = resp if isinstance(resp, dict) else d
    refused = bool(code) or resp.get("ok") is False or find(resp, "status") == "error"
    msg = find(resp, "message") or text
    h = find(resp, "tx_hash")
    if not h:
        m = HEX64.search(text)
        h = m.group() if m else None
    return refused, str(msg)[:600], h


def inspect(pk):
    _, out, _ = cli("rpc", "getblocks 120")
    blocks = find(data(out), "blocks") or []
    rows = []
    for b in blocks:
        n = find(b.get("header", b), "block_number")
        for i, tx in enumerate(b.get("transactions") or []):
            if not isinstance(tx, dict) or str(tx.get("sender_pubkey", "")).lower() != pk.lower():
                continue
            ops = tx.get("operations") or {}
            ids = b.get("tx_ids") or []
            rows.append({"block": n, "tx": ids[i] if i < len(ids) else None, "seq": tx.get("sequence_number"),
                         "type": tx.get("tx_type"), "rule": bool(ops.get("0")),
                         "transfers": [op[2] if isinstance(op, (list, tuple)) and len(op) > 2 else op for op in ops.get("1", [])]})
    print(json.dumps({"account": pk, "balance": balance(pk), "blocks_scanned": len(blocks), "in_blocks": rows}, separators=(",", ":")))


def newkey():
    _, out, _ = cli("keys", "new")
    d = data(out)
    priv, pub = find(d, "private_key_hex"), find(d, "public_key_hex")
    if not (priv and pub):
        sys.exit("cannot make a key: " + out[:300])
    return {"priv": str(priv), "pub": str(pub).lower().removeprefix("0x")}


def pay(k, to, amount):
    return send(["--privkey", k["priv"], "--to", to, "--amount", str(amount)])


def set_rule(k, text):
    with tempfile.NamedTemporaryFile("w", suffix=".tau", delete=False) as f:
        f.write(text)
    refused, msg, h = send(["--privkey", k["priv"], "--rule-file", f.name])
    os.unlink(f.name)
    if refused or not h:
        say("  ! the node refused the rule: " + msg[-300:])
        return None
    st, blk, _ = confirm(h)
    return blk if st == "confirmed" else None


def main():
    if os.environ.get("INSPECT"):
        return inspect(os.environ["INSPECT"].strip())
    res = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "limit": LIMIT, "rule": RULE, "signer": "IDNI tau-testnet CLI"}
    a, b = newkey(), newkey()
    res["account"], res["receiver"] = a["pub"], b["pub"]
    say(f"account {a['pub'][:12]}…  receiver {b['pub'][:12]}…  (fresh test keys)")

    say("1/4 a first payment of 10 AGRS (the faucet funds the new account)")
    refused, msg, h = pay(a, b["pub"], 10)
    st, blk, _ = confirm(h) if h and not refused else ("refused", None, {})
    if st != "confirmed":
        say(f"  ! the first payment is not in a block ({st}): " + msg)
        return finish(res, False)
    res["first"] = {"tx": h, "block": blk}
    say(f"  in block {blk}, balance now {balance(a['pub'])}")

    say(f"2/4 the account writes itself a rule: nothing above {LIMIT:,} AGRS leaves")
    blk = set_rule(a, RULE)
    if blk is None:
        return finish(res, False)
    res["rule_block"] = blk
    say(f"  rule in block {blk}, so in force from now on")

    say("3/4 the same key signs a payment of 5,000 AGRS")
    bal0 = balance(a["pub"])
    refused, msg, h = pay(a, b["pub"], 5000)
    big = {"amount": 5000, "tx": h, "balance_before": bal0, "node_said": msg}
    if refused:
        big["outcome"] = "refused at admission"
        say("  REFUSED by the node: " + msg[:300])
    else:
        say("  accepted into the queue (unexpected), watching what the block does with it")
        st, blk, d = confirm(h, minutes=3)
        big["outcome"], big["block"], big["status"] = ("in a block" if st == "confirmed" else st), blk, d
        say(f"  outcome: {big['outcome']}")
    big["balance_after"] = balance(a["pub"])
    res["big"] = big

    say("4/4 and a payment of 500 AGRS, inside the rule")
    refused2, msg2, h2 = pay(a, b["pub"], 500)
    st2, blk2, _ = confirm(h2) if h2 and not refused2 else ("refused", None, {})
    res["small"] = {"amount": 500, "tx": h2, "block": blk2, "status": st2, "node_said": None if st2 == "confirmed" else msg2}
    say(f"  {st2}" + (f" in block {blk2}" if blk2 else ": " + msg2[:300]))

    say("cleanup: the neutral clause removes the rule")
    res["removed_block"] = set_rule(a, NEUTRAL)
    finish(res, big.get("outcome") == "refused at admission" and "own policy" in big["node_said"] and st2 == "confirmed")


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
