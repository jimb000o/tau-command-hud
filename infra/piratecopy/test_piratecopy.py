"""Unit test of the pirate copy's harness (no network, no docker): when a voyage holds back, the timer, the note to the
owner, and one whole voyage against a fake docker that plays the two copy nodes, with a stand-in attack file (the real
one is kept off this repository).

Run: python test_piratecopy.py
"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
INFRA = os.path.join(TMP, "infra")
os.makedirs(INFRA)
STUB = os.path.join(TMP, "attacks.py")
os.environ.update(PIRATE_COPY_DIR=os.path.join(TMP, "state"), PIRATE_COPY_INFRA=INFRA, PIRATE_COPY_SYSTEMD=TMP,
                  PIRATE_COPY_FOLLOW_LOCK=os.path.join(TMP, "follow", "lock"), PIRATE_COPY_ATTACKS=STUB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import piratecopy as p  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


# a stand-in attack file: two stages, a restart of each node between them, and a judge that finds one thing
with open(STUB, "w") as f:
    f.write('''
ACCOUNTS = ["one", "two", "sink"]
PLAN = [("stage", "first", {"ROUND": 1, "LABEL": "warm"}), ("restart", "B"), ("restart", "A"),
        ("stage", "second", {"ROUND": 2, "LABEL": "after restarts"})]
def judge(res):
    stages = [s["stage"] for s in res["stages"]]
    return ([{"kind": "demo", "severity": "high", "attack": "second", "text": "second stage saw something"}],
            [f"stages run: {', '.join(stages)}", f"restarts: {len(res['restarts'])}"])
''')

# ---------------- the attack file ----------------
mod = p.load_attacks(STUB)
check(mod is not None and mod.ACCOUNTS == ["one", "two", "sink"], "the attack file is read from PIRATE_COPY_ATTACKS")
check(p.load_attacks(os.path.join(TMP, "missing.py")) is None, "a missing attack file gives None, no crash")
broken = os.path.join(TMP, "broken.py")
with open(broken, "w") as f:
    f.write("ACCOUNTS = []\n")
check(p.load_attacks(broken) is None, "an attack file without PLAN and judge is not used")

# ---------------- the note ----------------
res = {"id": "2026-11-17-1915", "image": "tau-testnet-standalone:5ad1bb7",
       "findings": [{"kind": "split", "severity": "high", "attack": "x", "text": "nodes disagree at block 9"}],
       "held": ["steady: 8 payments, both nodes agree"]}
text = p.note(res)
check(text.startswith("Pirate copy 2026-11-17-1915") and "1. [high] nodes disagree at block 9" in text, "the owner's note: headline, numbered findings")
check("nothing went to IDNI" in text and text.rstrip().endswith('sh infra/up.sh copy last"'), "nothing public, and the full up line last")

# ---------------- holding back ----------------
p.get = lambda url, timeout=20: json.dumps({"now": {"name": "Black Sequence"}})
check(p.hold_reason({}) == "Black Sequence is in port", "no voyage while a ship is in port")
p.get = lambda url, timeout=20: json.dumps({"now": None, "next": {"name": "Queen", "t0": p.now() + 600}})
check(p.hold_reason({}) == "Queen is due", "no voyage when a ship is due")
p.get = lambda url, timeout=20: json.dumps({"now": None, "next": {}})
p.sh = lambda cmd, timeout=600, input=None: (0, "abc123\n") if cmd[:2] == ["docker", "ps"] else (0, "")
check("auto-follow" in (p.hold_reason({}) or ""), "no voyage while the auto-follow's trial node runs")
p.sh = lambda cmd, timeout=600, input=None: (0, "")
p.mem_free_mb = lambda: 1500
check("1500 MB" in (p.hold_reason({}) or ""), "no voyage without the memory for two nodes")
p.mem_free_mb = lambda: 2600
p.disk_free_gb = lambda: 20.0
check(p.hold_reason({}) is None and p.hold_reason({"PIRATE_COPY": "0"}).startswith("switched off"), "clear way; off means off")
os.environ["PIRATE_COPY_ATTACKS"] = os.path.join(TMP, "missing.py")
check("no usable attack file" in p.run_pass(), "no voyage without the private attack file")
os.environ["PIRATE_COPY_ATTACKS"] = STUB

# ---------------- the timer ----------------
p.shutil.which = lambda name: "/bin/systemctl"
ran = []
p.sh = lambda cmd, timeout=600, input=None: (ran.append(cmd), (0, ""))[1]
out = p.install()
with open(os.path.join(TMP, "tau-pirate-copy.timer")) as fh:
    tm = fh.read()
check("OnCalendar=Tue *-*-* 19:15:00 UTC" in tm and out.startswith("pirate copy: on"), "the timer sails Tuesday 19:15 UTC")
with open(os.path.join(INFRA, ".env"), "w") as fh:
    fh.write("PIRATE_COPY=0\n")
check("off" in p.install() and ["systemctl", "disable", "--now", "tau-pirate-copy.timer"] in ran, "PIRATE_COPY=0 stops the timer")
os.remove(os.path.join(INFRA, ".env"))

# ---------------- one whole voyage against a fake docker ----------------
STAGES, TOLD, REMOVED, RESTARTED, STARTED = [], [], [], [], []
HEAD = {"n": 8}


def fake_sh(cmd, timeout=600, input=None):
    if cmd[:3] == ["docker", "compose", "ps"]:
        return 0, "cid1\n"
    if cmd[:2] == ["docker", "inspect"] and "{{.Config.Image}}" in cmd:
        return 0, "tau-testnet-standalone:5ad1bb7\n"
    if cmd[:2] == ["docker", "inspect"]:
        return 0, "true false 0\n"
    if cmd[:3] == ["docker", "network", "create"]:
        check("--internal" in cmd, "the copy network has no way out")
        return 0, "netid\n"
    if cmd[:2] == ["docker", "run"] and "--rm" in cmd:
        check(cmd[cmd.index("--network") + 1] == "none", "the genesis is made without any network")
        check(cmd[-2] == "one,two,sink" and cmd[-1] == p.NETWORK_ID, "the genesis gets the attack file's accounts and the copy's network id")
        return 0, json.dumps({"ok": True, "validator": "ab" * 48, "block_0": "c0ffee" * 10, "network_id": p.NETWORK_ID, "accounts": 3})
    if cmd[:2] == ["docker", "run"]:
        name = cmd[cmd.index("--name") + 1]
        STARTED.append(name)
        envs = dict(cmd[i + 1].split("=", 1) for i, x in enumerate(cmd) if x == "-e")
        check(envs["TAU_NETWORK_ID"] == "tau-pirate-copy" and "34.251.82.246" not in json.dumps(envs),
              f"{name}: own network id, never IDNI's bootnode")
        check(envs["TAU_MINING_ENABLED"] == ("true" if name == p.A else "false") and "-p" not in cmd, f"{name}: only A seals, no published ports")
        if name == p.B:
            check(json.loads(envs["TAU_BOOTSTRAP_PEERS"])[0]["peer_id"] == "12D3KooWCopyA", "B dials A by its peer id")
        return 0, "cid\n"
    if cmd[:2] == ["docker", "restart"]:
        RESTARTED.append(cmd[2])
        return 0, ""
    if cmd[:2] == ["docker", "exec"] and "-c" in cmd:
        return 0, "ok\n"
    if cmd[:2] == ["docker", "exec"] and cmd[-2:] == ["python", "-"]:
        env = dict(cmd[i + 1].split("=", 1) for i, x in enumerate(cmd) if x == "-e")
        STAGES.append((env["STAGE"], env.get("ROUND"), env.get("LABEL")))
        check(input and "judge" in input, f"stage {env['STAGE']}: the attack file itself is piped into node A")
        if env["STAGE"] == "state":
            return 0, json.dumps({"attacks": {"one": {"pays": []}}})
        return 0, "12:00:00 a line\n" + json.dumps({"stage": env["STAGE"], "ok": True, "result": {"round": env.get("ROUND")}})
    if cmd[:2] == ["docker", "exec"]:   # the probe of both nodes
        hashes = {str(n): f"h{n}" for n in range(1, HEAD["n"] + 1)}
        return 0, json.dumps({"a": {"head": HEAD["n"], "hash": f"h{HEAD['n']}", "hashes": hashes},
                              "b": {"head": HEAD["n"], "hash": f"h{HEAD['n']}", "hashes": hashes}})
    if cmd[:2] == ["docker", "logs"]:
        return 0, "INFO Network identity ready peer_id=12D3KooWCopyA source=persistent\n"
    if cmd[:3] == ["docker", "compose", "exec"]:
        TOLD.append(input)
        return 0, "sent\n"
    if cmd[:3] in (["docker", "rm", "-f"], ["docker", "volume", "rm"], ["docker", "network", "rm"]):
        REMOVED.append(tuple(cmd))
        return 0, ""
    return 0, ""


p.sh, p.sleep = fake_sh, (lambda s: None)
p.get = lambda url, timeout=20: json.dumps({"now": None, "next": {}})
check(p.run_pass() == "done", "a whole voyage runs through")
last = p.read_json(p.LAST)
check([s[0] for s in STAGES] == ["first", "second", "state"], "the plan's stages, then the state")
check([s[2] for s in STAGES[:2]] == ["warm", "after restarts"], "each stage gets its plan entry's settings")
check(RESTARTED == [p.B, p.A] and [r["node"] for r in last["restarts"]] == ["B", "A"] and last["restarts"][1]["changed"] == [],
      "B, then A restarted with their chains, A's blocks compared before and after")
check(STARTED.count(p.B) == 2 and last.get("resync", {}).get("same_head") is True, "B starts again from nothing and replays")
check(last["findings"][0]["kind"] == "demo" and "restarts: 2" in last["held"], "the attack file judges the voyage")
check(len(TOLD) == 1 and TOLD[0].startswith("Pirate copy") and "1 finding," in TOLD[0], "the owner hears once, privately")
check(("docker", "network", "rm", p.NET) in REMOVED and ("docker", "volume", "rm", "-f", p.A) in REMOVED,
      "the copy is removed afterwards: nodes, data, network")
check(not os.path.exists(p.RUN), "the copy's keys are gone after the voyage")
check(os.path.exists(os.path.join(p.DIR, "runs", last["id"] + ".json")), "the voyage is kept under runs/")
lines = p.status_lines()
check(lines[0].startswith("copy:    the pirate copy is ON") and "1 finding," in lines[1], "up copy shows the last voyage")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
