#!/usr/bin/env python3
"""The pirate copy: the pirates attack the chain itself, on a private copy of the Tau testnet on this server.

The live testnet carries No Memo, Agorzilla, the showcase wallets and everyone else's work, so attacks that may split
or stall a chain run here first: two nodes from the image our live node runs (same IDNI commit), on a docker network
with no way out (`--internal`), with their own network id and their own genesis (IDNI's scripts/gen_genesis.py, same
options as tau-testnet-v2: approval slots, base fee 10, faucet 100,000; our own validator key, the pirates' accounts
funded in genesis). Node A seals the blocks, node B follows and checks every one of them.

The attacks themselves are not in this public repository: what they try stays private until IDNI knows what they
found. They live on the server (PIRATE_COPY_ATTACKS, default /opt/tau-bench/piratecopy/attacks.py) as one Python file
that names the accounts (ACCOUNTS), the voyage's plan (PLAN: stages run inside node A, and node restarts in between),
runs a stage when piped into node A (`python -` with STAGE=<name>), and judges a voyage (judge(res) -> findings, held).

One voyage (`run`, from the systemd timer `up` installs, Tuesday evening after the pirates' call, or `up copy now`):
  1. holds back while a cruise ship is in port or due, while the node's auto-follow runs (it shares that lock), when
     the server lacks the free memory for two nodes (PIRATE_COPY_MIN_FREE_MB) and when there is no attack file
  2. makes the copy chain and starts A and B
  3. follows the plan: each stage runs inside A (it signs with IDNI's own wallet in the node image), both nodes are
     compared after it; a restart restarts that node with its chain kept and compares A's blocks before and after;
     at the end node B starts again from nothing and must replay the whole copy chain to A's head
  4. lets the attack file judge what it saw, keeps the result in /var/lib/tau-pirate-copy (last.json, runs/) and
     always removes both nodes, their data, the network and the copy's keys
  5. tells the owner privately on Telegram (the watchtower's chat): what the chain withstood, what broke. Nothing about
     it is public and nothing goes to IDNI from here.

Off: PIRATE_COPY=0 in infra/.env, or `up copy off`. When: PIRATE_COPY_WHEN (systemd OnCalendar, default Tuesday 19:15
UTC = 20:15 German winter time, after the pirates' call).
Commands: run | install | status | last | log | now | on | off
"""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
INFRA = os.environ.get("PIRATE_COPY_INFRA", os.path.dirname(HERE))
DIR = os.environ.get("PIRATE_COPY_DIR", "/var/lib/tau-pirate-copy")
RUN = os.path.join(DIR, "run")            # genesis + keys of the voyage under way, mounted read-only into the nodes
LOG = os.path.join(DIR, "log.txt")
LAST = os.path.join(DIR, "last.json")
FOLLOW_LOCK = os.environ.get("PIRATE_COPY_FOLLOW_LOCK", "/var/lib/tau-idni-follow/lock")
SYSTEMD = os.environ.get("PIRATE_COPY_SYSTEMD", "/etc/systemd/system")
RELAY = os.environ.get("PIRATE_COPY_RELAY", "https://node.tauhud.com")
UNIT = "tau-pirate-copy"
NET, SUBNET = "tau-copy", "172.31.250.0/24"
A, B = "tau-copy-a", "tau-copy-b"
IP = {A: "172.31.250.10", B: "172.31.250.11"}
NODE = {"A": A, "B": B}
NETWORK_ID = "tau-pirate-copy"
ATTACKS_DEFAULT = "/opt/tau-bench/piratecopy/attacks.py"
TRIAL = "tau-follow-trial"     # the auto-follow's trial node: never both at once on a 4 GB server


def attacks_path(cfg: dict | None = None) -> str:
    return (cfg or {}).get("PIRATE_COPY_ATTACKS") or os.environ.get("PIRATE_COPY_ATTACKS") or ATTACKS_DEFAULT


def load_attacks(path: str):
    """The private attack file as a module (it runs nothing when imported); None when it is missing or broken."""
    try:
        spec = importlib.util.spec_from_file_location("pirate_attacks", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 - a broken file holds the voyage back, it never crashes the timer
        log(f"attack file {path} not usable: {type(e).__name__}: {str(e)[:120]}")
        return None
    if not all(hasattr(mod, k) for k in ("ACCOUNTS", "PLAN", "judge")):
        log(f"attack file {path} lacks ACCOUNTS, PLAN or judge")
        return None
    return mod


# ---------------- small things the tests replace ----------------

def sh(cmd: list[str], timeout: float = 600, input: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=INFRA, input=input, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {round(timeout / 60)} min"
    except OSError as e:
        return 127, str(e)


def get(url: str, timeout: float = 20) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tauhud-pirate-copy"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - an unreachable relay is a reason to wait, never a crash
        return None


def now() -> float:
    return time.time()


def sleep(s: float):
    time.sleep(s)


def mem_free_mb() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def disk_free_gb() -> float:
    for p in ("/var/lib/docker", "/"):
        if os.path.isdir(p):
            return shutil.disk_usage(p).free / 1e9
    return 999.0


# ---------------- files ----------------

def env_path() -> str:
    return os.path.join(INFRA, ".env")


def read_env() -> dict:
    out = {}
    try:
        with open(env_path()) as f:
            for line in f:
                m = re.match(r"\s*([A-Z0-9_]+)=(.*)$", line.rstrip("\n"))
                if m:
                    out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def set_env(key: str, value: str):
    try:
        with open(env_path()) as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    for i, line in enumerate(lines):
        if line.startswith(key + "="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    with open(env_path(), "w") as f:
        f.write("\n".join(lines) + "\n")


def enabled(cfg: dict) -> bool:
    return str(cfg.get("PIRATE_COPY", "1")).strip().lower() not in ("0", "false", "off", "no")


def log(text: str):
    os.makedirs(DIR, exist_ok=True)
    line = f"{datetime.fromtimestamp(now(), timezone.utc):%Y-%m-%d %H:%M:%SZ} {text}"
    print(line, flush=True)
    try:
        with open(LOG) as f:
            old = f.read().splitlines()[-600:]
    except OSError:
        old = []
    with open(LOG, "w") as f:
        f.write("\n".join(old + [line]) + "\n")


def write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def read_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ---------------- talking to the owner ----------------

def tell(text: str) -> bool:
    code = ("import sys, tickerwatch; ok, why = tickerwatch.tell(sys.stdin.read()); "
            "print('sent' if ok else 'not sent: ' + why)")
    rc, out = sh(["docker", "compose", "exec", "-T", "alerts", "python", "-c", code], input=text, timeout=60)
    sent = rc == 0 and out.strip().endswith("sent") and "not sent" not in out
    log(f"note to the owner {'sent' if sent else 'NOT sent (' + out.strip()[-120:] + ')'}")
    return sent


# ---------------- the copy chain ----------------

GENESIS = r'''
import json, subprocess, sys
from tau_testnet_cli import keys as K
names, network_id = sys.argv[1].split(","), sys.argv[2]
val = K.generate_keypair()
acc = {n: K.generate_keypair() for n in names}
keys = {"validator": {"priv": val["private_key_hex"], "pub": val["public_key_hex"]},
        "accounts": {n: {"priv": k["private_key_hex"], "pub": k["public_key_hex"]} for n, k in acc.items()}}
args = [sys.executable, "scripts/gen_genesis.py", "--validator-privkey", val["private_key_hex"], "--approval-slots",
        "--base-fee", "10", "--faucet-amount", "100000", "--network-id", network_id, "--out", "/work/genesis.json"]
for k in acc.values():
    args += ["--account", k["public_key_hex"] + ":1000000"]
r = subprocess.run(args, capture_output=True, text=True)
if r.returncode:
    print(json.dumps({"ok": False, "error": (r.stdout + r.stderr)[-400:]}))
    sys.exit(1)
json.dump(keys, open("/work/keys.json", "w"), indent=1)
open("/data/test_miner.key", "w").write(val["private_key_hex"])
open("/data/test_miner.pub", "w").write(val["public_key_hex"])
g = json.load(open("/work/genesis.json"))
print(json.dumps({"ok": True, "validator": val["public_key_hex"], "block_0": g["block_0"]["hash"],
                  "network_id": g.get("network_id"), "accounts": len(acc)}))
'''

# the newest blocks of node A and node B as A sees them over the copy network: {"a": {height: hash}, "b": ..., heads}
PROBE = r'''
import json, socket, sys
def ask(host, cmd):
    try:
        s = socket.create_connection((host, 65432), timeout=20)
        s.sendall(cmd.encode() + b"\r\n")
        buf = b""
        while not buf.endswith(b"\n"):
            c = s.recv(65536)
            if not c:
                break
            buf += c
        s.close()
        return json.loads(buf)
    except Exception:
        return {}
out = {}
for name, host in (("a", "127.0.0.1"), ("b", sys.argv[1])):
    g = (ask(host, "getgovernance").get("data") or {})
    hashes = {}
    for b in (ask(host, "getblocks 40").get("data") or {}).get("blocks") or []:
        try:
            hashes[str(int((b.get("header") or {}).get("block_number")))] = b.get("block_hash")
        except (TypeError, ValueError):
            pass
    out[name] = {"head": g.get("head_number"), "hash": g.get("head_hash"), "hashes": hashes}
print(json.dumps(out))
'''


def node_image() -> str | None:
    """The image our live node runs, so the copy has the same IDNI commit and our patches."""
    rc, cid = sh(["docker", "compose", "ps", "-q", "tau-node"], timeout=60)
    cid = cid.strip().splitlines()[-1] if rc == 0 and cid.strip() else ""
    if not cid:
        return None
    rc, img = sh(["docker", "inspect", "-f", "{{.Config.Image}}", cid], timeout=60)
    img = img.strip()
    return img if rc == 0 and img else None


def cleanup():
    for c in (A, B):
        sh(["docker", "rm", "-f", c], timeout=120)
        sh(["docker", "volume", "rm", "-f", c], timeout=120)
    sh(["docker", "network", "rm", NET], timeout=60)
    shutil.rmtree(RUN, ignore_errors=True)


def make_chain(image: str, accounts: list[str]) -> dict:
    """The copy's genesis and keys (in RUN), the validator key in A's volume, the closed network."""
    shutil.rmtree(RUN, ignore_errors=True)
    os.makedirs(RUN, mode=0o700)
    rc, out = sh(["docker", "network", "create", "--internal", "--subnet", SUBNET, NET], timeout=60)
    if rc != 0:
        return {"ok": False, "error": f"no copy network: {out.strip()[-160:]}"}
    rc, out = sh(["docker", "run", "--rm", "-i", "--network", "none", "-v", f"{RUN}:/work", "-v", f"{A}:/data",
                  "--entrypoint", "python", image, "-", ",".join(accounts), NETWORK_ID],
                 input=GENESIS, timeout=600)
    try:
        d = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        d = {"ok": False, "error": out.strip()[-300:]}
    if rc != 0 and d.get("ok"):
        d = {"ok": False, "error": out.strip()[-300:]}
    return d


def start_node(image: str, name: str, cfg: dict, validator: str, bootstrap: list | None = None) -> tuple[bool, str]:
    sh(["docker", "rm", "-f", name], timeout=120)
    env = {
        "TAU_NETWORK_ID": NETWORK_ID,
        "TAU_NETWORK_LISTEN": "/ip4/0.0.0.0/tcp/4001",
        "TAU_ANNOUNCE_ADDRS": f"/ip4/{IP[name]}/tcp/4001",
        "TAU_BOOTSTRAP_PEERS": json.dumps(bootstrap or []),
        "TAU_MINING_ENABLED": "true" if name == A else "false",
        "TAU_MINER_PUBKEYS": validator,
        "TAU_GOVERNANCE_OPEN_ADMISSION": "true",
        "TAU_LOG_LEVEL": "INFO",
    }
    args = ["docker", "run", "-d", "--name", name, "--network", NET, "--ip", IP[name],
            "--memory", cfg.get("PIRATE_COPY_MEMORY") or "900m", "--cpus", cfg.get("PIRATE_COPY_CPUS") or "0.8",
            "-v", f"{name}:/data", "-v", f"{RUN}:/copy:ro", "--label", "tauhud=pirate-copy"]
    for k, v in sorted(env.items()):
        args += ["-e", f"{k}={v}"]
    script = "mkdir -p data && cp /copy/genesis.json data/genesis.json && exec python server.py"
    rc, out = sh(args + [image, "sh", "-c", script], timeout=120)
    return rc == 0, out.strip()[-200:]


def answers(name: str, minutes: float = 6) -> bool:
    """Node `name` answers on its RPC port (from inside itself) within `minutes`."""
    end = now() + minutes * 60
    # the answer begins {"status":"ok",...}: its first bytes are enough, the rest may be long
    probe = ("import socket;s=socket.create_connection(('127.0.0.1',65432),timeout=10);"
             "s.sendall(b'getgovernance\\r\\n');print('ok' if b'\"status\":\"ok\"' in s.recv(4096) else 'no')")
    while now() < end:
        rc, out = sh(["docker", "exec", name, "python", "-c", probe], timeout=60)
        if rc == 0 and out.strip().endswith("ok"):
            return True
        sleep(10)
    return False


def peer_id(name: str) -> str | None:
    rc, out = sh(["docker", "logs", name], timeout=60)
    m = re.findall(r"Network identity ready peer_id=(\w+)", out or "")
    return m[-1] if m else None


def probe() -> dict:
    rc, out = sh(["docker", "exec", "-i", A, "python", "-", IP[B]], input=PROBE, timeout=120)
    try:
        return json.loads(out.strip().splitlines()[-1]) if rc == 0 else {}
    except (ValueError, IndexError):
        return {}


def compare(p: dict) -> dict:
    """The two nodes after a stage: heads, and the first height both hold with different blocks."""
    a, b = p.get("a") or {}, p.get("b") or {}
    ha, hb = a.get("hashes") or {}, b.get("hashes") or {}
    differ = sorted(int(n) for n in set(ha) & set(hb) if ha[n] != hb[n])
    return {"a": a.get("head"), "b": b.get("head"), "same_head": a.get("hash") is not None and a.get("hash") == b.get("hash"),
            "first_different": differ[0] if differ else None}


def settle_b(minutes: float = 3) -> dict:
    """Gives node B up to `minutes` to reach A's head; the comparison as it stands then."""
    end, c = now() + minutes * 60, {}
    while now() < end:
        c = compare(probe())
        if c.get("same_head") or c.get("first_different") is not None:
            return c
        sleep(15)
    return c


def stage(code: str, name: str, env: dict | None = None) -> dict:
    """One stage of the attack file inside node A; its last JSON line, or why there is none."""
    args = ["docker", "exec", "-i", "-e", f"STAGE={name}", "-e", f"COPY_B={IP[B]}"]
    for k, v in (env or {}).items():
        args += ["-e", f"{k}={v}"]
    rc, out = sh(args + [A, "python", "-"], input=code, timeout=40 * 60)
    lines = (out or "").strip().splitlines()
    for line in lines[-8:]:
        if not line.startswith("{"):
            log(f"  {name}: {line[:220]}")
    try:
        return json.loads(lines[-1])
    except (ValueError, IndexError):
        return {"stage": name, "ok": False, "error": (out or "").strip()[-300:]}


def node_facts(name: str) -> dict:
    rc, out = sh(["docker", "inspect", "-f", "{{.State.Running}} {{.State.OOMKilled}} {{.RestartCount}}", name], timeout=60)
    parts = out.split() if rc == 0 else []
    _, logs = sh(["docker", "logs", "--tail", "4000", name], timeout=120)
    marks = {
        "rejected_in_block": len(re.findall(r"TX REJECTED during apply", logs or "")),
        "state_mismatch": len(re.findall(r"state.?hash|PreparedCommitMismatch|does not match", logs or "", re.I)),
        "tracebacks": len(re.findall(r"Traceback \(most recent call last\)", logs or "")),
        "worker_lost": len(re.findall(r"WorkerLost|worker (?:died|lost)", logs or "", re.I)),
    }
    tail = [ln for ln in (logs or "").splitlines() if re.search(r"ERROR|mismatch|reject|Traceback|WorkerLost", ln, re.I)][-12:]
    return {"running": parts[:1] == ["true"], "oom_killed": parts[1:2] == ["true"], "marks": marks,
            "log_lines": [ln[:240] for ln in tail]}


class MemWatch(threading.Thread):
    """The highest memory each copy node used during the voyage (docker stats every 20 s)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop, self.peak = False, {}

    def run(self):
        while not self.stop:
            rc, out = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}", A, B], timeout=60)
            for line in (out or "").splitlines() if rc == 0 else []:
                m = re.match(r"(\S+)\s+([\d.]+)(KiB|MiB|GiB)", line)
                if m:
                    mb = float(m.group(2)) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[m.group(3)]
                    self.peak[m.group(1)] = max(self.peak.get(m.group(1), 0), round(mb))
            for _ in range(20):
                if self.stop:
                    break
                sleep(1)


def note(res: dict) -> str:
    f, h = res.get("findings") or [], res.get("held") or []
    head = (f"Pirate copy {res.get('id')} (private copy chain, image {res.get('image')}): "
            f"{len(f)} finding{'s' if len(f) != 1 else ''}, the chain withstood {len(h)}.")
    lines = [head]
    if f:
        lines.append("")
        lines += [f"{i}. [{x['severity']}] {x['text']}" for i, x in enumerate(f, 1)]
    if h:
        lines.append("")
        lines.append("Withstood: " + "; ".join(h)[:1500])
    lines.append("")
    lines.append("Nothing of this is public and nothing went to IDNI. All details:")
    lines.append('ssh root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh copy last"')
    return "\n".join(lines)


# ---------------- one voyage ----------------

def cruise_reason(ahead_min: int = 45) -> str | None:
    raw = get(RELAY + "/cruise")
    try:
        c = json.loads(raw) if raw else {}
    except ValueError:
        c = {}
    v, n = c.get("now") or {}, c.get("next") or {}
    if v:
        return f"{v.get('name') or 'a ship'} is in port"
    if n.get("t0") and n["t0"] - now() < ahead_min * 60:
        return f"{n.get('name') or 'a ship'} is due"
    return None


def hold_reason(cfg: dict) -> str | None:
    if not enabled(cfg):
        return "switched off (PIRATE_COPY=0 in .env)"
    why = cruise_reason()
    if why:
        return why
    rc, out = sh(["docker", "ps", "-q", "-f", f"name=^{TRIAL}$"], timeout=60)
    if rc == 0 and out.strip():
        return "the node's auto-follow has a trial node running"
    need = int(cfg.get("PIRATE_COPY_MIN_FREE_MB") or 2000)
    free = mem_free_mb()
    if free < need:
        return f"only {free} MB of memory free, two copy nodes need {need}"
    if disk_free_gb() < 3:
        return f"only {disk_free_gb():.1f} GB of disk free"
    return None


def voyage(cfg: dict, mod, code: str) -> dict:
    t0 = now()
    rid = datetime.fromtimestamp(t0, timezone.utc).strftime("%Y-%m-%d-%H%M")
    res = {"id": rid, "started": round(t0), "compare": [], "stages": [], "restarts": [],
           "memory_cap": cfg.get("PIRATE_COPY_MEMORY") or "900m"}
    image = node_image()
    res["image"] = image
    if not image:
        res["error"] = "our live node is not running, so there is no image to copy"
        return res
    cleanup()
    watch = MemWatch()
    try:
        g = make_chain(image, list(mod.ACCOUNTS))
        res["genesis"] = {k: g.get(k) for k in ("ok", "block_0", "network_id", "accounts", "error")}
        if not g.get("ok"):
            res["error"] = f"no copy genesis: {g.get('error')}"
            return res
        ok, why = start_node(image, A, cfg, g["validator"])
        if not ok or not answers(A):
            res["error"] = f"node A did not come up: {why or node_facts(A)['log_lines'][-3:]}"
            return res
        pid = peer_id(A)
        if not pid:
            res["error"] = "node A has no peer id in its log"
            return res
        boot = [{"peer_id": pid, "addrs": [f"/ip4/{IP[A]}/tcp/4001"]}]
        ok, why = start_node(image, B, cfg, g["validator"], boot)
        if not ok or not answers(B):
            res["error"] = f"node B did not come up: {why or node_facts(B)['log_lines'][-3:]}"
            return res
        watch.start()
        log(f"copy chain {g.get('block_0', '')[:8]} up: A {IP[A]} seals, B {IP[B]} follows ({pid[:12]}…)")
        for step in mod.PLAN:
            if step[0] == "restart":
                node = NODE[step[1]]
                log(f"node {step[1]} restarts (keeps its chain)")
                before = (probe().get("a") or {}) if node == A else {}
                sh(["docker", "restart", node], timeout=300)
                back = answers(node)
                again = (probe().get("a") or {}) if node == A and back else {}
                h0, h1 = before.get("hashes") or {}, again.get("hashes") or {}
                res["restarts"].append({"node": step[1], "back": back, "head_before": before.get("head"),
                                        "head_after": again.get("head"),
                                        "changed": sorted(int(k) for k in set(h0) & set(h1) if h0[k] != h1[k])[:5]})
                if not back:
                    res["error"] = f"node {step[1]} did not come back after its restart"
                    break
                continue
            name, env = step[1], dict(step[2]) if len(step) > 2 else {}
            label = env.get("LABEL") or name
            out = stage(code, name, {k: str(v) for k, v in env.items()})
            res["stages"].append({"stage": name, "env": env, **out})
            c = settle_b()
            c["after"] = f"{name} {env.get('ROUND', '')}".strip()
            res["compare"].append(c)
            log(f"{c['after']} ({label}): {json.dumps(out.get('result') or out.get('error'))[:200]} | A {c.get('a')} "
                f"B {c.get('b')}{' SAME' if c.get('same_head') else ''}"
                f"{' DIFFER at ' + str(c['first_different']) if c.get('first_different') is not None else ''}")
        st = stage(code, "state")
        res["attacks"] = st if "stage" not in st else {}
        res["nodes"] = {A: node_facts(A), B: node_facts(B)}
        if not res.get("error"):
            log("node B starts again from nothing and replays the copy chain")
            sh(["docker", "rm", "-f", B], timeout=120)
            sh(["docker", "volume", "rm", "-f", B], timeout=120)
            ok, _ = start_node(image, B, cfg, g["validator"], boot)
            if ok and answers(B):
                res["resync"] = settle_b(minutes=float(cfg.get("PIRATE_COPY_RESYNC_MINUTES") or 12))
            else:
                res["resync"] = {"a": None, "b": None, "same_head": False, "first_different": None, "error": "B did not start"}
            res["nodes"][B + " (fresh)"] = node_facts(B)
    finally:
        watch.stop = True
        res["memory_peak_mb"] = watch.peak
        res["minutes"] = round((now() - t0) / 60, 1)
        cleanup()
    return res


def run_pass() -> str:
    cfg = read_env()
    why = hold_reason(cfg)
    path = attacks_path(cfg)
    mod = None if why else load_attacks(path)
    if not why and mod is None:
        why = f"no usable attack file at {path} (it is kept off the public repo, see the README)"
    if why:
        log(f"no voyage: {why}")
        return why
    with open(path) as f:
        code = f.read()
    os.makedirs(os.path.dirname(FOLLOW_LOCK) or "/", exist_ok=True)
    with open(FOLLOW_LOCK, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log("no voyage: the node's auto-follow is running")
            return "auto-follow running"
        log("voyage starts")
        res = voyage(cfg, mod, code)
    if res.get("error"):
        res["findings"], res["held"] = [], []
        log(f"voyage stopped: {res['error']}")
    else:
        try:
            res["findings"], res["held"] = mod.judge(res)
        except Exception as e:  # noqa: BLE001 - the result is kept anyway; the owner hears the judge broke
            res["findings"], res["held"] = [{"kind": "judge", "severity": "medium", "attack": "-",
                                             "text": f"the attack file could not judge this voyage ({type(e).__name__}: {e})"}], []
        log(f"voyage over after {res.get('minutes')} min: {len(res['findings'])} findings, withstood {len(res['held'])}")
    write_json(os.path.join(DIR, "runs", res["id"] + ".json"), res)
    write_json(LAST, res)
    if res.get("error"):
        tell(f"Pirate copy {res['id']}: the voyage stopped early ({res['error']}). Nothing public happened.\n"
             'Log: ssh root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh copy log"')
    else:
        tell(note(res))
    return "done"


# ---------------- the timer, the up lines ----------------

def install() -> str:
    cfg = read_env()
    if not shutil.which("systemctl"):
        return "pirate copy: no systemd on this machine, nothing scheduled"
    svc, tmr = os.path.join(SYSTEMD, UNIT + ".service"), os.path.join(SYSTEMD, UNIT + ".timer")
    if not enabled(cfg):
        sh(["systemctl", "disable", "--now", UNIT + ".timer"])
        return "pirate copy: off (PIRATE_COPY=0), timer stopped"
    when = cfg.get("PIRATE_COPY_WHEN") or "Tue *-*-* 19:15:00 UTC"
    unit = (f"[Unit]\nDescription=The pirates attack a private copy of the Tau testnet ({os.path.abspath(__file__)})\n"
            "After=docker.service network-online.target\n\n[Service]\nType=oneshot\n"
            f"WorkingDirectory={INFRA}\nExecStart=/usr/bin/env python3 {os.path.abspath(__file__)} run\nTimeoutStartSec=3h\n")
    timer = (f"[Unit]\nDescription=The pirate copy, once a week\n\n[Timer]\nOnCalendar={when}\n"
             "Persistent=false\n\n[Install]\nWantedBy=timers.target\n")
    changed = False
    for path, text in ((svc, unit), (tmr, timer)):
        try:
            with open(path) as f:
                same = f.read() == text
        except OSError:
            same = False
        if not same:
            with open(path, "w") as f:
                f.write(text)
            changed = True
    if changed:
        sh(["systemctl", "daemon-reload"])
    rc, out = sh(["systemctl", "enable", "--now", UNIT + ".timer"])
    return f"pirate copy: on, sails {when}" if rc == 0 else f"pirate copy: timer NOT started ({out.strip()[-120:]})"


def status_lines() -> list[str]:
    cfg = read_env()
    last = read_json(LAST)
    rc, out = sh(["systemctl", "is-active", UNIT + ".service"], timeout=30)
    busy = out.strip() in ("active", "activating")
    lines = [f"copy:    the pirate copy is {'ON' if enabled(cfg) else 'off'}, sails {cfg.get('PIRATE_COPY_WHEN') or 'Tue *-*-* 19:15:00 UTC'}"
             + (" (a voyage is under way now)" if busy else "")]
    if not last:
        lines.append("         no voyage yet (up copy now starts one)")
        return lines
    when = datetime.fromtimestamp(last.get("started") or 0, timezone.utc).strftime("%d.%m. %H:%M UTC")
    if last.get("error"):
        lines.append(f"         last voyage {when}: stopped early, {last['error']}")
        return lines
    f = last.get("findings") or []
    lines.append(f"         last voyage {when}, {last.get('minutes')} min: {len(f)} finding{'s' if len(f) != 1 else ''}, "
                 f"withstood {len(last.get('held') or [])}")
    lines += [f"         {i}. [{x['severity']}] {x['text'][:160]}" for i, x in enumerate(f, 1)]
    return lines


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "status":
        print("\n".join(status_lines()))
        return 0
    if cmd == "last":
        last = read_json(LAST)
        print(note(last) if last and not last.get("error") else json.dumps(last, indent=1)[:4000])
        return 0
    if cmd == "log":
        try:
            with open(LOG) as f:
                print("\n".join(f.read().splitlines()[-40:]))
        except OSError:
            print("no pirate copy log yet")
        return 0
    if cmd == "install":
        print(install())
        return 0
    if cmd in ("on", "off"):
        set_env("PIRATE_COPY", "1" if cmd == "on" else "0")
        print(install())
        return 0
    if cmd == "now":
        install()
        cfg = read_env()
        why = hold_reason(cfg) or (None if os.path.isfile(attacks_path(cfg)) else
                                   f"no attack file at {attacks_path(cfg)} (README: Pirate copy)")
        if why:   # said here, not only in the log: the voyage would stop at once in the background
            print(f"pirate copy: no voyage now, {why}")
            return 0
        rc, out = sh(["systemctl", "start", "--no-block", UNIT + ".service"])
        print("pirate copy: a voyage started in the background, about an hour (up copy shows how it went)"
              if rc == 0 else out.strip())
        return rc
    if cmd == "run":
        os.makedirs(DIR, exist_ok=True)
        with open(os.path.join(DIR, "lock"), "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                print("a voyage is under way")
                return 0
            try:
                print(run_pass())
            except Exception as e:  # noqa: BLE001 - logged; the copy is removed by voyage()'s finally
                log(f"voyage crashed: {type(e).__name__}: {e}")
                cleanup()
                return 1
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
