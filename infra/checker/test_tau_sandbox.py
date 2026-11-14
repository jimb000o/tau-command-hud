"""Unit test of tau_sandbox.py's process side (no engine, no network):
1. Spot's ltlsynt is found in the tau-lang dependency store, in the layout the build uses and in others, and put on PATH;
2. a process the worker leaves in a process group of its own (as the engine does with ltlsynt) is killed with the
   worker's session.
The real engine answers every lesson in `up tau` (tau_selftest.py), which also says where ltlsynt was found.

Run: python test_tau_sandbox.py
"""
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
EMPTY = tempfile.mkdtemp()
os.environ["TAU_STORE"] = EMPTY            # the import looks in this store, not in /root/.tau
os.environ["PATH"] = EMPTY + os.pathsep + "/usr/bin:/bin"
import tau_sandbox  # noqa: E402

failed = 0


def check(cond, label):
    global failed
    print(("ok   " if cond else "FAIL ") + label)
    failed += not cond


def tool(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


# 1. finding ltlsynt
check(tau_sandbox.SPOT_BIN == "" and os.environ["PATH"] == EMPTY + os.pathsep + "/usr/bin:/bin", "an empty store: nothing found, PATH untouched")
check(tau_sandbox.find_spot_bin(EMPTY) == "", "an empty store: \"\"")

store = tempfile.mkdtemp()
bin_dir = os.path.join(store, "store", "spot", "4f2a" * 16, "prefix", "bin")
tool(os.path.join(bin_dir, "ltlsynt"))
os.makedirs(os.path.join(store, "store", "boost", "77", "prefix", "include", "boost", "bin"), exist_ok=True)
check(tau_sandbox.find_spot_bin(store) == bin_dir, "the build's layout: <store>/store/spot/<id>/prefix/bin")

other = tempfile.mkdtemp()
deep = os.path.join(other, "packages", "linux-arm64", "spot-2.16", "bin")
tool(os.path.join(deep, "ltlsynt"))
check(tau_sandbox.find_spot_bin(other) == deep, "another layout: found by the walk")

hidden = tempfile.mkdtemp()
tool(os.path.join(hidden, "store", "cvc5", "1", "include", "bin", "ltlsynt"))
tool(os.path.join(hidden, "a", "b", "c", "d", "e", "f", "g", "bin", "ltlsynt"))
check(tau_sandbox.find_spot_bin(hidden) == "", "header trees and anything deeper than six folders are not searched")

plain = tempfile.mkdtemp()
with open(os.path.join(plain, "ltlsynt"), "w") as f:
    f.write("not a program")
os.makedirs(os.path.join(plain, "bin"))
os.rename(os.path.join(plain, "ltlsynt"), os.path.join(plain, "bin", "ltlsynt"))
check(tau_sandbox.find_spot_bin(plain) == "", "a file that cannot run is not ltlsynt")

on_path = tempfile.mkdtemp()
tool(os.path.join(on_path, "ltlsynt"))
saved = os.environ["PATH"]
os.environ["PATH"] = on_path + os.pathsep + saved
check(tau_sandbox.find_spot_bin(store) == on_path, "an ltlsynt already on PATH wins over the store")
os.environ["PATH"] = saved

# the import puts the store's ltlsynt first on PATH, and a worker started afterwards sees it
code = ("import os, sys; sys.path.insert(0, %r); os.environ['TAU_STORE'] = %r; import tau_sandbox, shutil; "
        "print(tau_sandbox.SPOT_BIN); print(shutil.which('ltlsynt') or '')") % (HERE, store)
out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=dict(os.environ)).stdout.split("\n")
check(out[0] == bin_dir and out[1] == os.path.join(bin_dir, "ltlsynt"), "import: the store's ltlsynt is first on PATH")

# 2. a stray in its own process group dies with the worker's session
worker = subprocess.Popen(
    [sys.executable, "-c",
     "import os, subprocess, sys, time\n"
     "p = subprocess.Popen(['sleep', '60'], preexec_fn=os.setpgrp)\n"
     "print(p.pid, flush=True)\n"
     "time.sleep(60)\n"],
    stdout=subprocess.PIPE, text=True, start_new_session=True)
stray = int(worker.stdout.readline())


def alive(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


check(alive(stray) and os.getpgid(stray) != worker.pid and os.getsid(stray) == worker.pid,
      "the stray runs in a group of its own, in the worker's session")
os.killpg(worker.pid, signal.SIGKILL)
worker.wait()
time.sleep(0.2)
check(alive(stray), "killing the worker's group misses it (what happened to ltlsynt before)")
n = tau_sandbox.kill_session(worker.pid)
end = time.monotonic() + 3
while alive(stray) and time.monotonic() < end:
    time.sleep(0.05)
check(n == 1 and not alive(stray), "kill_session ends it")
check(tau_sandbox.kill_session(worker.pid) == 0, "nothing left in the session afterwards")

print("all tau_sandbox tests passed" if not failed else f"{failed} tau_sandbox checks failed")
sys.exit(1 if failed else 0)
