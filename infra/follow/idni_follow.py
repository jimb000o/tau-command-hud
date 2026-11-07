#!/usr/bin/env python3
"""Keep our node on the newest IDNI tau-testnet main, with a safety net. Runs on the server itself (host python3,
docker), every 30 minutes from a systemd timer that `up` installs (tau-idni-follow.timer); nothing else schedules it.

One pass (`run`):
  1. asks GitHub for IDNI/tau-testnet main; nothing to do when the node already runs it
  2. waits outside the ship windows (IDNI_FOLLOW_QUIET, German time) and while a ship is in port or due (relay /cruise)
  3. leaves a commit alone whose IDNI build moved to another tau-lang (a tau-lang rebuild takes hours on this server and
     once froze it): that one needs a repin by hand, and the owner is told once
  4. builds the node image of the new commit next to the running one (our node patches must still apply, else the build
     stops and says which one), the running node is not touched
  5. starts a trial node from that image with an empty chain, on the live testnet, no ports published: it must sync from
     genesis to the live tip and agree with our running node block for block (IDNI_FOLLOW_TRIAL_MINUTES)
  6. switches: stops the node, keeps a copy of its chain data, starts the new image on the same data, and checks that it
     answers and is in sync with the network tip twice, 3 minutes apart
  7. any failure in 6 puts the old image and the copied chain data back
The owner's private Telegram chat (`up owner`, the watchtower's chat) hears about every switch and every commit held
back for good (once per commit). A commit that failed is not tried again; the next IDNI commit is.

Off: IDNI_FOLLOW=0 in infra/.env, or `up follow off` (the node stays on the commit it runs).
Commands: run | ref | status | install | now | on | off | log
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
INFRA = os.environ.get("IDNI_FOLLOW_INFRA", os.path.dirname(HERE))
DIR = os.environ.get("IDNI_FOLLOW_DIR", "/var/lib/tau-idni-follow")
STATE = os.path.join(DIR, "state.json")
LOG = os.path.join(DIR, "log.txt")
UPSTREAM = "https://github.com/IDNI/tau-testnet"
RAW = "https://raw.githubusercontent.com/IDNI/tau-testnet"
API = "https://api.github.com/repos/IDNI/tau-testnet"
RELAY = os.environ.get("IDNI_FOLLOW_RELAY", "https://node.tauhud.com")
IMAGE = "tau-testnet-standalone"
TRIAL = "tau-follow-trial"
SNAPSHOT = "tau-follow-snapshot"
UNIT = "tau-idni-follow"
SYSTEMD = os.environ.get("IDNI_FOLLOW_SYSTEMD", "/etc/systemd/system")
# the ship windows of the deploy rules (a node restart is not allowed then), plus the hack of the week (Thu 11:00)
QUIET_DEFAULT = "sat 12-17,tue 16-20,wed 14-18,thu 10-12"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MIN_FREE_GB = 8
LAG_OK = 3   # blocks behind the network tip that still count as in sync (relay /status)

# the probe: run inside a node container, asks the node's own RPC for its newest blocks
PROBE = r'''
import json, socket
s = socket.create_connection(("127.0.0.1", 65432), timeout=20)
s.sendall(b"getblocks 10\r\n")
buf = b""
while not buf.endswith(b"\n"):
    c = s.recv(65536)
    if not c:
        break
    buf += c
m = json.loads(buf)
d = m.get("data") or {}
out = {}
for b in d.get("blocks") or []:
    try:
        out[str(int((b.get("header") or {}).get("block_number")))] = b.get("block_hash")
    except (TypeError, ValueError):
        pass
print(json.dumps({"ok": m.get("status") == "ok", "hashes": out}))
'''


# ---------------- small things the tests replace ----------------

def sh(cmd: list[str], env: dict | None = None, timeout: float = 600, input: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=INFRA, env={**os.environ, **(env or {})}, input=input, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {round(timeout / 60)} min"
    except OSError as e:
        return 127, str(e)


def get(url: str, timeout: float = 20) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tauhud-node-follow"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - an unreachable source is a reason to wait, never a crash
        return None


def now() -> float:
    return time.time()


def sleep(s: float):
    time.sleep(s)


def free_gb() -> float:
    for p in ("/var/lib/docker", "/"):
        if os.path.isdir(p):
            return shutil.disk_usage(p).free / 1e9
    return 999.0


# ---------------- files ----------------

def env_path() -> str:
    return os.path.join(INFRA, ".env")


def read_env(path: str | None = None) -> dict:
    out = {}
    try:
        with open(path or env_path()) as f:
            for line in f:
                m = re.match(r"\s*([A-Z0-9_]+)=(.*)$", line.rstrip("\n"))
                if m:
                    out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def set_env(key: str, value: str, path: str | None = None):
    path = path or env_path()
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    for i, line in enumerate(lines):
        if line.startswith(key + "="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    tmp = path + ".follow"
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def repo_pin() -> str:
    return read_env(os.path.join(INFRA, ".env.example")).get("TAU_TESTNET_REF", "")


def our_tau_lang() -> str:
    try:
        with open(os.path.join(INFRA, "node", "Dockerfile")) as f:
            m = re.search(r"ARG\s+TAU_LANG_REF=([0-9a-f]{7,40})", f.read())
        return m.group(1) if m else ""
    except OSError:
        return ""


def load() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(st: dict):
    os.makedirs(DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE)


def log(text: str):
    os.makedirs(DIR, exist_ok=True)
    line = f"{datetime.fromtimestamp(now(), timezone.utc):%Y-%m-%d %H:%M:%SZ} {text}"
    print(line, flush=True)
    try:
        with open(LOG) as f:
            old = f.read().splitlines()[-400:]
    except OSError:
        old = []
    with open(LOG, "w") as f:
        f.write("\n".join(old + [line]) + "\n")


def short(sha: str | None) -> str:
    return (sha or "?")[:7]


# ---------------- German time and the ship windows ----------------

def _last_sunday(year: int, month: int) -> datetime:
    d = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(days=1) if month < 12 else datetime(year, 12, 31, tzinfo=timezone.utc)
    return d - timedelta(days=(d.weekday() - 6) % 7)


def german(t: float) -> datetime:
    """German local time without depending on the host's tz database (CEST from the last Sunday of March 01:00 UTC
    to the last Sunday of October 01:00 UTC)."""
    u = datetime.fromtimestamp(t, timezone.utc)
    start = _last_sunday(u.year, 3).replace(hour=1)
    end = _last_sunday(u.year, 10).replace(hour=1)
    return (u + timedelta(hours=2 if start <= u < end else 1)).replace(tzinfo=None)


def windows(spec: str) -> list[tuple[int, int, int]]:
    out = []
    for part in (spec or "").split(","):
        m = re.match(r"\s*([a-z]{3})\w*\s+(\d{1,2})\s*-\s*(\d{1,2})\s*$", part.lower())
        if m and m.group(1) in DAYS:
            out.append((DAYS.index(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def quiet_reason(t: float, ahead_min: int, spec: str) -> str | None:
    """A ship window now or starting within ahead_min minutes, as text; None when the way is clear."""
    ws = windows(spec)
    for step in range(0, ahead_min + 1, 5):
        g = german(t + step * 60)
        for day, a, b in ws:
            if g.weekday() == day and a <= g.hour < b:
                return f"ship window {DAYS[day].capitalize()} {a}-{b} German time" + ("" if step == 0 else " starts soon")
    return None


def cruise_reason(t: float, ahead_min: int) -> str | None:
    raw = get(RELAY + "/cruise")
    try:
        c = json.loads(raw) if raw else {}
    except ValueError:
        c = {}
    v, n = c.get("now") or {}, c.get("next") or {}
    if v:
        return f"{v.get('name') or 'a ship'} is in port"
    if n.get("t0") and n["t0"] - t < ahead_min * 60:
        return f"{n.get('name') or 'a ship'} is due"
    return None


# ---------------- talking to the owner ----------------

def tell(text: str) -> bool:
    code = ("import sys, tickerwatch; ok, why = tickerwatch.tell(sys.stdin.read()); "
            "print('sent' if ok else 'not sent: ' + why)")
    rc, out = sh(["docker", "compose", "exec", "-T", "alerts", "python", "-c", code], input=text, timeout=60)
    sent = rc == 0 and out.strip().endswith("sent") and "not sent" not in out
    log(f"note to the owner {'sent' if sent else 'NOT sent (' + out.strip()[-120:] + ')'}")
    return sent


def commits_between(a: str, b: str) -> list[str]:
    raw = get(f"{API}/compare/{a}...{b}")
    try:
        cs = json.loads(raw).get("commits") or [] if raw else []
    except (ValueError, AttributeError):
        cs = []
    return [f"{c['sha'][:7]} {(c.get('commit') or {}).get('message', '').splitlines()[0][:90]}" for c in cs if c.get("sha")][-6:]


# ---------------- the node ----------------

def remote_head() -> str | None:
    rc, out = sh(["git", "ls-remote", UPSTREAM, "refs/heads/main"], timeout=60)
    m = re.match(r"([0-9a-f]{40})\s", out or "")
    return m.group(1) if rc == 0 and m else None


def idni_tau_lang(sha: str) -> str | None:
    raw = get(f"{RAW}/{sha}/Dockerfile.standalone")
    m = re.search(r"ARG\s+TAU_LANG_REF=([0-9a-f]{7,40})", raw or "")
    return m.group(1) if m else None


def probe(container: str | None = None) -> dict | None:
    """The newest blocks a node holds, {height: hash}; container None = our running node."""
    cmd = (["docker", "exec", "-i", container, "python", "-"] if container
           else ["docker", "compose", "exec", "-T", "tau-node", "python", "-"])
    rc, out = sh(cmd, input=PROBE, timeout=60)
    try:
        d = json.loads(out.strip().splitlines()[-1]) if rc == 0 else None
    except (ValueError, IndexError):
        return None
    if not d or not d.get("ok"):
        return None
    return {int(k): v for k, v in (d.get("hashes") or {}).items()}


def synced() -> tuple[bool, str]:
    """Our running node answers and the relay sees it within LAG_OK blocks of the network tip."""
    blocks = probe()
    if not blocks:
        return False, "the node does not answer"
    raw = get(RELAY + "/status")
    try:
        s = json.loads(raw) if raw else {}
    except ValueError:
        s = {}
    h, tip = s.get("height"), s.get("tip_height")
    if isinstance(h, int) and isinstance(tip, int) and tip - h > LAG_OK:
        return False, f"block {h}, network tip {tip}"
    return True, f"block {max(blocks)}" + (f", network tip {tip}" if isinstance(tip, int) else "")


def build(sha: str, cfg: dict) -> tuple[bool, str]:
    log(f"building the node image of {short(sha)}")
    rc, out = sh(["docker", "compose", "build", "tau-node"],
                 env={"TAU_TESTNET_REF": sha, "TAU_BUILD_JOBS": cfg.get("TAU_BUILD_JOBS", "1")}, timeout=4 * 3600)
    with open(os.path.join(DIR, "build.log"), "w") as f:
        f.write(out)
    if rc == 0:
        return True, "built"
    m = re.search(r"/patches/([\w-]+)\.py", "\n".join(l for l in out.splitlines() if "did not complete" in l or "ERROR" in l))
    if m:
        return False, f"our node patch {m.group(1)} no longer applies to {short(sha)} (it needs reworking by hand)"
    err = [l.strip() for l in out.splitlines() if "ERROR" in l or "error" in l.lower()]
    return False, f"the build failed: {(err[-1] if err else out.strip()[-160:])[:160]}"


def node_env() -> dict:
    """The tau-node service's environment as compose has it, for the trial node; never a validator, never our address."""
    rc, out = sh(["docker", "compose", "config", "--format", "json"], timeout=60)
    try:
        env = dict((json.loads(out)["services"]["tau-node"].get("environment") or {})) if rc == 0 else {}
    except (ValueError, KeyError, TypeError):
        env = {}
    env = {k: str(v) for k, v in env.items() if v is not None}
    env.pop("TAU_ANNOUNCE_ADDRS", None)
    env["TAU_MINING_ENABLED"] = "false"
    return env


def compare(trial: dict, live: dict) -> tuple[int, int | None]:
    """(heights both hold with the same hash, a height where they differ below the tip zone or None)."""
    same, bad = 0, None
    low = min(max(trial), max(live)) - LAG_OK
    for n in set(trial) & set(live):
        if trial[n] == live[n]:
            same += 1
        elif n <= low:
            bad = n
    return same, bad


def trial(sha: str, cfg: dict) -> tuple[bool, str]:
    minutes = int(cfg.get("IDNI_FOLLOW_TRIAL_MINUTES") or 45)
    log(f"trial node of {short(sha)}: syncing from genesis on the live testnet (up to {minutes} min)")
    sh(["docker", "rm", "-f", TRIAL])
    sh(["docker", "volume", "rm", "-f", TRIAL])
    args = ["docker", "run", "-d", "--name", TRIAL, "--memory", cfg.get("IDNI_FOLLOW_TRIAL_MEMORY") or "1500m",
            "--cpus", "1", "-v", f"{TRIAL}:/data"]
    for k, v in sorted(node_env().items()):
        args += ["-e", f"{k}={v}"]
    rc, out = sh(args + [f"{IMAGE}:{sha}", "/usr/local/bin/tau-node-start"], timeout=120)
    if rc != 0:
        return False, f"the trial node did not start: {out.strip()[-120:]}"
    ok, why, best = False, "", None
    try:
        deadline = now() + minutes * 60
        while now() < deadline:
            sleep(30)
            rc, state = sh(["docker", "inspect", "-f", "{{.State.Running}}", TRIAL])
            if state.strip() != "true":
                _, tail = sh(["docker", "logs", "--tail", "3", TRIAL])
                why = f"the trial node stopped: {tail.strip().splitlines()[-1][:140] if tail.strip() else 'no log'}"
                break
            t, live = probe(TRIAL), probe()
            if not t or not live:
                continue
            best = max(t)
            same, bad = compare(t, live)
            if bad is not None:
                why = f"the trial node disagrees with our node at block {bad}"
                break
            if same and max(t) >= max(live) - 2:
                ok, why = True, f"synced to block {max(t)} in {round((now() - (deadline - minutes * 60)) / 60)} min, same blocks as our node"
                break
        else:
            why = f"the trial node reached block {best if best is not None else 'none'} in {minutes} min, not the live tip"
    finally:
        _, tail = sh(["docker", "logs", "--tail", "60", TRIAL])
        with open(os.path.join(DIR, "trial.log"), "w") as f:
            f.write(tail)
        sh(["docker", "rm", "-f", TRIAL])
        sh(["docker", "volume", "rm", "-f", TRIAL])
    log(f"trial: {why}")
    return ok, why


def data_volume() -> str | None:
    rc, cid = sh(["docker", "compose", "ps", "-a", "-q", "tau-node"])
    cid = cid.strip().splitlines()[0] if rc == 0 and cid.strip() else ""
    if not cid:
        return None
    rc, out = sh(["docker", "inspect", "-f", '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}', cid])
    return out.strip() or None if rc == 0 else None


def copy_volume(src: str, dst: str, image: str) -> bool:
    sh(["docker", "volume", "create", dst])
    rc, out = sh(["docker", "run", "--rm", "-v", f"{src}:/from:ro", "-v", f"{dst}:/to", "--entrypoint", "sh", image, "-c",
                  "find /to -mindepth 1 -delete && cp -a /from/. /to/"], timeout=1800)
    if rc != 0:
        log(f"copying {src} -> {dst} failed: {out.strip()[-160:]}")
    return rc == 0


def wait_synced(minutes: int) -> tuple[bool, str]:
    end, why = now() + minutes * 60, "not checked"
    while now() < end:
        sleep(20)
        ok, why = synced()
        if ok:
            return True, why
    return False, why


def switch(old: str, new: str, st: dict) -> bool:
    vol = data_volume()
    if not vol:
        hold(st, "could not find the node's chain data volume")
        return False
    log(f"switching the node {short(old)} -> {short(new)}")
    sh(["docker", "compose", "stop", "tau-node"], timeout=180)
    if not copy_volume(vol, SNAPSHOT, f"{IMAGE}:{old}"):
        sh(["docker", "compose", "up", "-d", "--no-build", "tau-node"], timeout=300)
        hold(st, "could not keep a copy of the chain data, so it did not switch")
        tell(f"Node auto-follow: {short(new)} was tested fine but NOT switched: copying the chain data failed. "
             f"The node runs {short(old)} as before.")
        return False
    set_env("TAU_TESTNET_REF", new)
    rc, out = sh(["docker", "compose", "up", "-d", "--no-build"], timeout=600)
    ok, why = (rc == 0, out.strip()[-160:])
    if ok:
        ok, why = wait_synced(15)
    if ok:
        sleep(180)
        ok, why = synced()
    if ok:
        st["live"] = {"sha": new, "since": now(), "base": repo_pin(), "prev": old}
        st["last_switch"] = {"from": old, "to": new, "at": now(), "ok": True}
        st.pop("held", None), st.pop("failed", None), st.pop("tested", None)
        save(st)
        log(f"switched to {short(new)}: {why}")
        news = commits_between(old, new)
        tell(f"Node auto-follow: our node now runs IDNI tau-testnet main {short(new)} (was {short(old)}). "
             f"Trial sync and the switch went fine, {why}.\n" + "\n".join(news))
        sh(["docker", "rmi", f"{IMAGE}:{old}"])   # several GB; the chain data copy stays for a hand rollback
        return True
    log(f"the new node failed ({why}); putting {short(old)} back")
    sh(["docker", "compose", "stop", "tau-node"], timeout=180)
    restored = copy_volume(SNAPSHOT, vol, f"{IMAGE}:{old}")
    set_env("TAU_TESTNET_REF", old)
    sh(["docker", "compose", "up", "-d", "--no-build"], timeout=600)
    back, bwhy = wait_synced(15)
    st["last_switch"] = {"from": old, "to": new, "at": now(), "ok": False, "why": why, "rolled_back": back}
    fail(st, new, f"switched, but the new node failed ({why}); rolled back to {short(old)}"
         + ("" if back else f", and the old node is NOT in sync yet ({bwhy})") + ("" if restored else " (chain data not restored)"),
         urgent=not back)
    return False


# ---------------- one pass ----------------

def hold(st: dict, reason: str):
    st["held"] = {"reason": reason, "at": now()}
    save(st)
    log(f"held back: {reason}")


def fail(st: dict, sha: str, reason: str, urgent: bool = False):
    first = (st.get("failed") or {}).get("sha") != sha
    st["failed"] = {"sha": sha, "reason": reason, "at": now()}
    hold(st, f"{short(sha)}: {reason}")
    if first or urgent:
        tell(("URGENT " if urgent else "") + f"Node auto-follow held back IDNI main {short(sha)}: {reason}. "
             "Our node keeps running the commit it ran. The next IDNI commit is tried again by itself.")


def enabled(cfg: dict) -> bool:
    return str(cfg.get("IDNI_FOLLOW", "1")).strip().lower() not in ("0", "false", "off", "no")


def run_pass() -> str:
    cfg = read_env()
    st = load()
    st["last_check"] = now()
    save(st)
    if not enabled(cfg):
        hold(st, "switched off (IDNI_FOLLOW=0 in .env)")
        return "off"
    head = remote_head()
    if not head:
        hold(st, "GitHub did not answer")
        return "no head"
    st["head"] = head
    running = cfg.get("TAU_TESTNET_REF", "")
    if head == running:
        st.pop("held", None)
        save(st)
        return "up to date"
    f = st.get("failed") or {}
    if f.get("sha") == head:
        hold(st, f"{short(head)}: {f.get('reason')}")
        return "failed before"
    spec = cfg.get("IDNI_FOLLOW_QUIET") or QUIET_DEFAULT
    t = now()
    q = quiet_reason(t, 90, spec) or cruise_reason(t, 120)
    if q:
        hold(st, q)
        return "quiet"
    lang, ours = idni_tau_lang(head), our_tau_lang()
    if lang is None:
        hold(st, "could not read IDNI's Dockerfile.standalone")
        return "no dockerfile"
    if ours and not (lang.startswith(ours) or ours.startswith(lang)):
        fail(st, head, f"IDNI's build moved to tau-lang {short(lang)} (ours {short(ours)}); a tau-lang rebuild takes "
                       "hours on this server, so this one needs a repin by hand")
        return "tau-lang"
    tested = st.get("tested") or {}
    have_image = sh(["docker", "image", "inspect", f"{IMAGE}:{head}"])[0] == 0   # a full up removes other images
    if not (tested.get("sha") == head and now() - tested.get("at", 0) < 24 * 3600 and have_image):
        if free_gb() < MIN_FREE_GB:
            hold(st, f"only {free_gb():.1f} GB free on disk, a node build needs about {MIN_FREE_GB}")
            return "disk"
        ok, why = build(head, cfg)
        if not ok:
            fail(st, head, why)
            sh(["docker", "rmi", f"{IMAGE}:{head}"])
            return "build"
        ok, why = trial(head, cfg)
        if not ok:
            fail(st, head, why)
            sh(["docker", "rmi", f"{IMAGE}:{head}"])
            return "trial"
        st["tested"] = {"sha": head, "at": now(), "why": why}
        save(st)
    t = now()
    q = quiet_reason(t, 30, spec) or cruise_reason(t, 60)
    if q:
        hold(st, f"{q}; {short(head)} is built and tested and switches at the next quiet check")
        return "quiet after test"
    if read_env().get("TAU_TESTNET_REF", "") != running:
        hold(st, "an up changed the node meanwhile; the next check starts over")
        return "changed"
    return "switched" if switch(running, head, st) else "rolled back"


# ---------------- what `up` shows ----------------

def status_lines(t: float | None = None) -> list[str]:
    t = now() if t is None else t
    cfg, st, pin = read_env(), load(), repo_pin()
    at = lambda x: f"{german(x):%a %d.%m. %H:%M}" if x else "never"
    running = cfg.get("TAU_TESTNET_REF", "")
    source = "followed from IDNI main" if (st.get("live") or {}).get("sha") == running and running != pin else "the repo pin"
    timer = "every 30 min" if os.path.exists(os.path.join(SYSTEMD, UNIT + ".timer")) else "NOT scheduled (no systemd timer yet; the next up installs it)"
    head = st.get("head")
    lines = [f"         auto-follow: {'on, ' + timer if enabled(cfg) else 'OFF (IDNI_FOLLOW=0; up follow on)'}; node on {short(running)} ({source}), "
             f"IDNI main {short(head) if head else 'not checked yet'}, last check {at(st.get('last_check'))} German time"]
    ls = st.get("last_switch")
    if ls:
        lines.append(f"         last switch {at(ls.get('at'))}: {short(ls.get('from'))} -> {short(ls.get('to'))} "
                     + ("fine" if ls.get("ok") else f"FAILED, rolled back ({ls.get('why')})"))
    h = st.get("held")
    if h and running != head:
        lines.append(f"         held back: {h.get('reason')} (up follow shows the log)")
    return lines


# ---------------- systemd ----------------

def install() -> str:
    cfg = read_env()
    if not shutil.which("systemctl"):
        return "auto-follow: no systemd on this machine, nothing scheduled"
    svc, tmr = os.path.join(SYSTEMD, UNIT + ".service"), os.path.join(SYSTEMD, UNIT + ".timer")
    if not enabled(cfg):
        sh(["systemctl", "disable", "--now", UNIT + ".timer"])
        return "auto-follow: off (IDNI_FOLLOW=0), timer stopped"
    unit = (f"[Unit]\nDescription=Keep the Tau node on the newest IDNI tau-testnet main ({os.path.abspath(__file__)})\n"
            "After=docker.service network-online.target\n\n[Service]\nType=oneshot\n"
            f"WorkingDirectory={INFRA}\nExecStart=/usr/bin/env python3 {os.path.abspath(__file__)} run\nTimeoutStartSec=6h\n")
    timer = (f"[Unit]\nDescription=Check IDNI tau-testnet main every 30 minutes\n\n[Timer]\nOnCalendar=*-*-* *:05,35:00\n"
             "RandomizedDelaySec=120\nPersistent=false\n\n[Install]\nWantedBy=timers.target\n")
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
    return "auto-follow: on, checks IDNI main every 30 min" if rc == 0 else f"auto-follow: timer NOT started ({out.strip()[-120:]})"


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "ref":   # what `up` builds: the followed commit while the repo pin is the one it followed from
        st, pin = load(), repo_pin()
        live = st.get("live") or {}
        print(live["sha"] if live.get("sha") and live.get("base") == pin else pin)
        return 0
    if cmd == "status":
        print("\n".join(status_lines()))
        return 0
    if cmd == "log":
        try:
            with open(LOG) as f:
                print("\n".join(f.read().splitlines()[-15:]))
        except OSError:
            print("no auto-follow log yet")
        return 0
    if cmd == "install":
        print(install())
        return 0
    if cmd in ("on", "off"):
        set_env("IDNI_FOLLOW", "1" if cmd == "on" else "0")
        print(install())
        return 0
    if cmd == "now":
        rc, out = sh(["systemctl", "start", "--no-block", UNIT + ".service"])
        print("auto-follow: one check started in the background (up follow shows how it went)" if rc == 0 else out.strip())
        return rc
    if cmd == "run":
        os.makedirs(DIR, exist_ok=True)
        with open(os.path.join(DIR, "lock"), "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                print("another check is running")
                return 0
            try:
                print(run_pass())
            except Exception as e:  # noqa: BLE001 - logged, the timer tries again in 30 minutes
                log(f"pass crashed: {type(e).__name__}: {e}")
                return 1
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
