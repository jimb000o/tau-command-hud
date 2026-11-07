"""Unit test of the node's auto-follow of IDNI main (no network, no docker): German time and the ship windows, which
commit `up` builds, and one pass through every way it can go (up to date, ship window, tau-lang moved, a patch that no
longer applies, a trial node that disagrees, a clean switch, a switch that rolls back), with the owner told once.

Run: python test_idni_follow.py
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

TMP = tempfile.mkdtemp()
INFRA = os.path.join(TMP, "infra")
os.makedirs(os.path.join(INFRA, "node"))
os.environ.update(IDNI_FOLLOW_DIR=os.path.join(TMP, "state"), IDNI_FOLLOW_INFRA=INFRA, IDNI_FOLLOW_SYSTEMD=TMP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idni_follow as f  # noqa: E402

failed = 0
OLD, NEW, LANG = "a" * 40, "b" * 40, "c3ea334cd1e6612930ea9f404933211858f0009f"


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def utc(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


# ---------------- German time, ship windows ----------------
check(f"{f.german(utc('2026-11-07 19:00')):%H:%M}" == "20:00", "November: German time is UTC+1")
check(f"{f.german(utc('2026-07-01 19:00')):%H:%M}" == "21:00", "July: German time is UTC+2")
check(f"{f.german(utc('2026-03-29 00:59')):%H}" == "01" and f"{f.german(utc('2026-03-29 01:00')):%H}" == "03", "summer time starts last Sunday of March")
SPEC = f.QUIET_DEFAULT
check("Tue 16-20" in (f.quiet_reason(utc("2026-11-10 16:30"), 0, SPEC) or ""), "Tue 17:30 German time is the pirate window")
check("starts soon" in (f.quiet_reason(utc("2026-11-10 14:00"), 90, SPEC) or ""), "Tue 15:00: the window starts within 90 min")
check(f.quiet_reason(utc("2026-11-09 11:00"), 90, SPEC) is None, "Monday noon is clear")
check(f.quiet_reason(utc("2026-11-07 19:00"), 90, SPEC) is None, "Saturday 20:00 (after the Queen) is clear")
check("Thu 10-12" in (f.quiet_reason(utc("2026-11-12 10:00"), 0, SPEC) or ""), "Thursday 11:00, the hack of the week, is held")
check(f.windows("sat 12-17, nonsense, mon 1-2") == [(5, 12, 17), (0, 1, 2)], "windows parse and skip junk")

# ---------------- block comparison ----------------
check(f.compare({10: "x", 11: "y"}, {10: "x", 11: "y", 12: "z"}) == (2, None), "same blocks agree")
check(f.compare({1: "q", 2: "r", 10: "x"}, {1: "p", 2: "r", 10: "x"})[1] == 1, "an old block with another hash is a disagreement")
check(f.compare({10: "x", 11: "fork"}, {10: "x", 11: "y"})[1] is None, "a different block at the tip is not (yet) one")


# ---------------- a fake server ----------------
def write(path, text):
    with open(path, "w") as fh:
        fh.write(text)


class Server:
    def __init__(self, head=NEW, idni_lang=LANG, build_ok=True, build_out="", trial_hashes=None, after_switch_ok=True,
                 cruise=None, image=False):
        self.head, self.idni_lang, self.build_ok, self.build_out = head, idni_lang, build_ok, build_out
        self.trial_hashes = trial_hashes if trial_hashes is not None else {str(n): f"h{n}" for n in range(91, 101)}
        self.after_switch_ok, self.cruise, self.image = after_switch_ok, cruise or {}, image
        self.calls, self.notes, self.t = [], [], utc("2026-11-09 11:00")   # a quiet Monday noon

    def sh(self, cmd, env=None, timeout=600, input=None):
        self.calls.append((cmd, env))
        j = " ".join(cmd)
        if cmd[:2] == ["git", "ls-remote"]:
            return 0, f"{self.head}\trefs/heads/main\n"
        if "tickerwatch.tell" in j:
            self.notes.append(input)
            return 0, "sent\n"
        if "compose build" in j:
            return (0, "done") if self.build_ok else (1, self.build_out)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return (0, "[]") if self.image else (1, "no such image")
        if "config --format json" in j:
            return 0, json.dumps({"services": {"tau-node": {"environment": {"TAU_NETWORK_ID": "tau-testnet-v2",
                                  "TAU_ANNOUNCE_ADDRS": "/ip4/1.2.3.4/tcp/4001", "TAU_MINING_ENABLED": "true"}}}})
        if cmd[:2] == ["docker", "run"] and "-d" in cmd:
            self.trial_env = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-e"]
            return 0, "cid"
        if cmd[:2] == ["docker", "inspect"] and "Running" in j:
            return 0, "true\n"
        if "ps -a -q tau-node" in j:
            return 0, "nodecid\n"
        if cmd[:2] == ["docker", "inspect"] and "Mounts" in j:
            return 0, "infra_tau_data\n"
        if cmd[:3] == ["docker", "exec", "-i"]:   # the trial node
            return 0, json.dumps({"ok": True, "hashes": self.trial_hashes})
        if "exec -T tau-node" in j:               # our node
            running = f.read_env().get("TAU_TESTNET_REF")
            if running == NEW and not self.after_switch_ok:
                return 1, "connection refused"
            return 0, json.dumps({"ok": True, "hashes": {str(n): f"h{n}" for n in range(91, 101)}})
        return 0, ""

    def get(self, url, timeout=20):
        if url.endswith("/Dockerfile.standalone"):
            return f"ARG TAU_LANG_REF={self.idni_lang}\n"
        if url.endswith("/cruise"):
            return json.dumps(self.cruise)
        if url.endswith("/status"):
            return json.dumps({"height": 100, "tip_height": 100})
        if "/compare/" in url:
            return json.dumps({"commits": [{"sha": NEW, "commit": {"message": "fix: something\n\nbody"}}]})
        return None

    def install(self):
        f.sh, f.get, f.now, f.free_gb = self.sh, self.get, lambda: self.t, lambda: 30.0

        def sleep(s):
            self.t += s
        f.sleep = sleep
        return self


def reset(env_ref=OLD, state=None):
    write(os.path.join(INFRA, ".env"), f"RELAY_DOMAIN=node.tauhud.com\nTAU_TESTNET_REF={env_ref}\nTAU_BUILD_JOBS=1\n")
    write(os.path.join(INFRA, ".env.example"), f"TAU_TESTNET_REF={OLD}\n")
    write(os.path.join(INFRA, "node", "Dockerfile"), f"ARG TAU_TESTNET_REF={OLD}\nARG TAU_LANG_REF={LANG}\n")
    os.makedirs(f.DIR, exist_ok=True)
    if os.path.exists(f.STATE):
        os.remove(f.STATE)
    if state:
        f.save(state)


def ref():
    import io
    from contextlib import redirect_stdout
    out = io.StringIO()
    with redirect_stdout(out):
        f.main(["x", "ref"])
    return out.getvalue().strip()


# ---------------- which commit up builds ----------------
reset()
check(ref() == OLD, "no state yet: up builds the repo pin")
reset(state={"live": {"sha": NEW, "base": OLD}})
check(ref() == NEW, "followed from this pin: up keeps the followed commit")
reset(state={"live": {"sha": NEW, "base": "d" * 40}})
check(ref() == OLD, "a repin merged since wins over the followed commit")

# ---------------- passes ----------------
reset(env_ref=NEW)
s = Server().install()
check(f.run_pass() == "up to date", "node already on IDNI main: nothing to do")
check(not any("build" in " ".join(c) for c, _ in s.calls), "... and nothing is built")

reset()
s = Server().install()
s.t = utc("2026-11-10 15:30")   # Tue 16:30 German time
check(f.run_pass() == "quiet", "pirate window: held back")
check("Tue 16-20" in f.load()["held"]["reason"] and not s.notes, "... with the reason kept, nobody told")

reset()
s = Server(cruise={"now": {"name": "Queen", "phase": "here"}}).install()
check(f.run_pass() == "quiet" and "Queen is in port" in f.load()["held"]["reason"], "a ship in port holds it back")

reset()
s = Server(idni_lang="1" * 40).install()
check(f.run_pass() == "tau-lang", "IDNI moved to another tau-lang: held for a repin by hand")
check(len(s.notes) == 1 and "tau-lang" in s.notes[0], "... the owner is told")
check(f.run_pass() == "failed before" and len(s.notes) == 1, "... once, not again on the next check")

reset()
s = Server(build_ok=False, build_out='ERROR: failed to solve: process "/bin/sh -c python3 -I /patches/peer-book.py /src" did not complete successfully').install()
check(f.run_pass() == "build", "a patch that no longer applies stops the build")
check("peer-book" in f.load()["failed"]["reason"] and "peer-book" in s.notes[0], "... and the note names the patch")
check(f.read_env()["TAU_TESTNET_REF"] == OLD, "... the node stays on its commit")

reset()
s = Server(trial_hashes={str(n): ("bad" if n == 92 else f"h{n}") for n in range(91, 101)}).install()
check(f.run_pass() == "trial", "a trial node with other blocks fails the trial")
check("disagrees" in f.load()["failed"]["reason"] and "block 92" in s.notes[0], "... at the block named")
check(not any(e and e.get("TAU_TESTNET_REF") == NEW for c, e in s.calls if "up" in c), "... no switch tried")

reset()
s = Server(trial_hashes={str(n): f"h{n}" for n in range(1, 11)}).install()
check(f.run_pass() == "trial" and "reached block 10" in f.load()["failed"]["reason"], "a trial node that never catches up fails in time")

reset()
s = Server().install()
check(f.run_pass() == "switched", "clean pass: built, tested, switched")
st = f.load()
check(f.read_env()["TAU_TESTNET_REF"] == NEW, "... .env now names the new commit")
check(st["live"]["sha"] == NEW and st["live"]["base"] == OLD and st["last_switch"]["ok"], "... state remembers what it follows")
check("TAU_MINING_ENABLED=false" in s.trial_env and not any(e.startswith("TAU_ANNOUNCE_ADDRS") for e in s.trial_env),
      "... the trial node is never a validator and never announces our address")
check(any("tau-follow-snapshot" in " ".join(c) for c, _ in s.calls), "... the chain data was copied before the switch")
check(len(s.notes) == 1 and "now runs" in s.notes[0] and "fix: something" in s.notes[0], "... owner told, with IDNI's commits")
check(ref() == NEW, "... and the next up keeps building it")
lines = f.status_lines(s.t)
check("followed from IDNI main" in lines[0] and "fine" in lines[1], "up shows it: " + " | ".join(l.strip() for l in lines))

reset()
s = Server(after_switch_ok=False).install()
check(f.run_pass() == "rolled back", "new node does not answer: rolled back")
check(f.read_env()["TAU_TESTNET_REF"] == OLD, "... .env names the old commit again")
st = f.load()
check(st["failed"]["sha"] == NEW and st["last_switch"]["ok"] is False and st["last_switch"]["rolled_back"], "... state says so")
check(len(s.notes) == 1 and "rolled back" in s.notes[0], "... owner told")
check("FAILED, rolled back" in " ".join(f.status_lines(s.t)), "... and up shows it")

reset()
s = Server(image=True).install()
s.t = utc("2026-11-10 15:00")
f.save({"tested": {"sha": NEW, "at": s.t - 600}})
check(f.run_pass() == "quiet", "tested commit waits through a ship window")
s.t = utc("2026-11-10 20:00")
check(f.run_pass() == "switched" and not any("compose build" in " ".join(c) for c, _ in s.calls), "... and switches after it without building again")

reset()
write(os.path.join(INFRA, ".env"), f"TAU_TESTNET_REF={OLD}\nIDNI_FOLLOW=0\n")
s = Server().install()
check(f.run_pass() == "off" and not s.notes, "IDNI_FOLLOW=0: nothing happens")
check("OFF" in f.status_lines(s.t)[0], "... and up says it is off")
f.set_env("IDNI_FOLLOW", "1")
check(f.read_env()["IDNI_FOLLOW"] == "1" and f.read_env()["TAU_TESTNET_REF"] == OLD, "up follow on rewrites only that line")

print("all ok" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
