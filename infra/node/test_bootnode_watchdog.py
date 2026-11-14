"""Tests for patches/bootnode-watchdog.py: the patches apply in Dockerfile order to
IDNI's tau-testnet at our pin, and the watchdog loop restarts only when no
bootstrap peer is connected, backs off with recent restarts, and stays quiet
while the bootnode is there.

Needs TAU_TESTNET_DIR (a checkout of IDNI/tau-testnet at TAU_TESTNET_REF, as CI
provides); skipped without it. No network, no trio: the loop runs with a stand-in.
"""
import ast
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time

HERE = pathlib.Path(__file__).resolve().parent
BOOT = "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC"


def patch_order() -> list[str]:
    text = (HERE / "Dockerfile").read_text()
    return re.findall(r"RUN python3 -I /patches/([\w-]+\.py) /src", text)


def patched_source(src_dir: str) -> str:
    work = tempfile.mkdtemp()
    dst = os.path.join(work, "src")
    shutil.copytree(src_dir, dst, ignore=shutil.ignore_patterns(".git"))
    order = patch_order()
    assert order[-1] == "bootnode-watchdog.py", order
    assert order.index("bootstrap-redial.py") < order.index("bootnode-watchdog.py")
    for p in order:
        subprocess.run([sys.executable, "-I", str(HERE / "patches" / p), dst], check=True, capture_output=True)
    text = (pathlib.Path(dst) / "network" / "service.py").read_text()
    shutil.rmtree(work)
    compile(text, "service.py", "exec")
    return text


def watchdog_function(text: str):
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_bootnode_watchdog_loop":
            body = textwrap.dedent(ast.get_source_segment(text, node))
            break
    else:
        raise AssertionError("watchdog loop missing")
    assert "self._nursery.start_soon(self._bootnode_watchdog_loop)" in text

    class Trio:
        @staticmethod
        async def sleep(_s):
            return None

    class Log:
        lines = []

        def error(self, msg, *a, **k):
            self.lines.append(msg % a)

    ns = {"trio": Trio, "logger": Log()}
    exec(body, ns)
    return ns["_bootnode_watchdog_loop"], ns["logger"]


class Exited(Exception):
    pass


class Stop:
    def __init__(self, after):
        self.n, self.after = 0, after

    def is_set(self):
        self.n += 1
        return self.n > self.after


class Cfg:
    def __init__(self, peers):
        self.bootstrap_peers = peers


class Node:
    def __init__(self, connected, checks=50, peers=None):
        self._config = Cfg(peers if peers is not None else [{"peer_id": BOOT, "addrs": []}])
        self._runner_stop = Stop(checks)
        self.connected = connected  # list of lists, one per check (last repeats)
        self.i = 0

    def get_id(self):
        return "12D3KooWOurOwnNode"

    def get_connected_peers(self):
        c = self.connected[min(self.i, len(self.connected) - 1)]
        self.i += 1
        return c


def run(fn, node, env):
    old_exit, old_env = os._exit, dict(os.environ)
    os.environ.update(env)

    def fake_exit(code):
        raise Exited(code)

    os._exit = fake_exit
    try:
        coro = fn(node)
        try:
            while True:
                coro.send(None)
        except StopIteration:
            return None
        except Exited as e:
            return e.args[0]
    finally:
        os._exit = old_exit
        os.environ.clear()
        os.environ.update(old_env)


def main() -> None:
    src = os.environ.get("TAU_TESTNET_DIR")
    if not src or not os.path.isdir(os.path.join(src, "network")):
        print("skipped: TAU_TESTNET_DIR not set")
        return
    fn, log = watchdog_function(patched_source(src))
    tmp = tempfile.mkdtemp()
    restarts = os.path.join(tmp, "restarts")
    env = {"TAU_BOOTNODE_LOST_RESTART": "1e-9", "TAU_BOOTNODE_RESTART_LOG": restarts}

    # bootnode connected the whole time: never restarts
    assert run(fn, Node([[BOOT]]), env) is None
    assert not os.path.exists(restarts)

    # other peers but never the bootnode: restarts (today's case had no working peer at all)
    assert run(fn, Node([["12D3KooWSomeCommunityNode"]]), env) == 4
    with open(restarts) as f:
        assert len(f.read().split()) == 1
    assert "no bootstrap peer connected" in log.lines[-1]

    # bootnode back before the limit: the clock starts over, no restart
    os.remove(restarts)
    slow = dict(env, TAU_BOOTNODE_LOST_RESTART="3600")
    assert run(fn, Node([[], [BOOT], [], [BOOT]]), slow) is None

    # backoff: 4 restarts in the last 2 h → waits 16 × limit; old entries are dropped
    now = time.time()
    with open(restarts, "w") as f:
        f.write("\n".join(str(now - s) for s in (60, 600, 1200, 3000, 9000)) + "\n")
    code = run(fn, Node([[]]), env)
    assert code == 4
    with open(restarts) as f:
        kept = f.read().split()
    assert len(kept) == 5, kept  # 4 recent + this one; the 9000 s old one dropped
    assert "4 restart(s)" in log.lines[-1]

    # with a real limit, 16 × 600 s is not reached in a quick run
    with open(restarts, "w") as f:
        f.write("\n".join(str(now - s) for s in (60, 600, 1200, 3000)) + "\n")
    assert run(fn, Node([[]], checks=5), dict(env, TAU_BOOTNODE_LOST_RESTART="600")) is None

    # switched off, or no bootstrap peer configured: the loop returns at once
    assert run(fn, Node([[]]), dict(env, TAU_BOOTNODE_LOST_RESTART="0")) is None
    assert run(fn, Node([[]], peers=[]), env) is None

    shutil.rmtree(tmp)
    print("bootnode watchdog: all ok")


if __name__ == "__main__":
    main()
