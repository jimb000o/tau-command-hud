"""Patch tau-testnet so a node that cannot reach its bootnode for a while restarts itself.

2026-11-14: IDNI restarted the testnet on a new chain a few minutes after
block #1569. Our node kept running, and from then on every handshake with the
bootnode failed ("handshake failed when upgrading to secure connection"), once
a minute, for two hours. bootstrap-redial kept dialing, chain-reset never got a
handshake to compare heads with, so the node sat on the dead chain. A plain
container restart fixed it at once: the same bootnode (same peer id) accepted
the handshake, chain-reset saw the new chain and the node synced 117 blocks.

This adds a loop: when none of the configured bootstrap peers has been
connected for TAU_BOOTNODE_LOST_RESTART seconds (default 600; <= 0 disables)
the node logs why and exits; the container's restart policy starts it again.
Each restart is noted in TAU_BOOTNODE_RESTART_LOG (default
/data/bootnode-restarts); with n restarts in the last two hours the next one
waits 2**n times longer (10, 20, 40, 80 min, at most 160), so a bootnode that
is really down for hours costs a few restarts, not a restart loop. Nothing
changes while a bootstrap peer is connected.

Usage: python3 -I bootnode-watchdog.py <tau-testnet checkout>
Apply AFTER bootstrap-redial.py (it anchors on that patch's start line).
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
service = root / "network" / "service.py"
src = service.read_text()


def replace_once(old: str, new: str, what: str) -> None:
    global src
    assert src.count(old) == 1, f"{what} anchor not found exactly once"
    src = src.replace(old, new, 1)


replace_once(
    "            self._nursery.start_soon(self._bootstrap_redial_loop)\n",
    "            self._nursery.start_soon(self._bootstrap_redial_loop)\n"
    "            self._nursery.start_soon(self._bootnode_watchdog_loop)\n",
    "start loops",
)
replace_once(
    "    async def _bootstrap_redial_loop(self) -> None:\n",
    "    async def _bootnode_watchdog_loop(self) -> None:\n"
    "        \"\"\"Exit (the container restarts) when no configured bootstrap peer has\n"
    "        been connected for TAU_BOOTNODE_LOST_RESTART seconds (default 600;\n"
    "        <= 0 disables). Backs off with recent restarts (bootnode-watchdog.py).\"\"\"\n"
    "        import os\n"
    "        import time\n"
    "\n"
    "        try:\n"
    "            limit = float(os.environ.get(\"TAU_BOOTNODE_LOST_RESTART\", \"600\"))\n"
    "        except ValueError:\n"
    "            limit = 600.0\n"
    "        if limit <= 0:\n"
    "            return\n"
    "        log_path = os.environ.get(\"TAU_BOOTNODE_RESTART_LOG\", \"/data/bootnode-restarts\")\n"
    "        boot_ids = set()\n"
    "        for cfg in (self._config.bootstrap_peers or []):\n"
    "            pid = cfg.get(\"peer_id\") if isinstance(cfg, dict) else getattr(cfg, \"peer_id\", None)\n"
    "            if pid and str(pid) != str(self.get_id()):\n"
    "                boot_ids.add(str(pid))\n"
    "        if not boot_ids:\n"
    "            return\n"
    "        now = time.time()\n"
    "        try:\n"
    "            with open(log_path) as f:\n"
    "                recent = [float(x) for x in f.read().split() if x.strip()]\n"
    "        except (OSError, ValueError):\n"
    "            recent = []\n"
    "        recent = [t for t in recent if now - t < 7200]\n"
    "        wait = limit * (2 ** min(len(recent), 4))\n"
    "        lost_since = time.monotonic()  # counts from start: a node that never reaches the bootnode restarts too\n"
    "        while not self._runner_stop.is_set():\n"
    "            await trio.sleep(30)\n"
    "            try:\n"
    "                connected = {str(p) for p in self.get_connected_peers()}\n"
    "            except Exception:\n"
    "                continue\n"
    "            if connected & boot_ids:\n"
    "                lost_since = None\n"
    "                continue\n"
    "            if lost_since is None:\n"
    "                lost_since = time.monotonic()\n"
    "                continue\n"
    "            lost = time.monotonic() - lost_since\n"
    "            if lost < wait:\n"
    "                continue\n"
    "            logger.error(\"BOOTNODE WATCHDOG: no bootstrap peer connected for %d min \"\n"
    "                         \"(%d other peer(s), %d restart(s) in the last 2 h); restarting the node\",\n"
    "                         lost // 60, len(connected), len(recent))\n"
    "            try:\n"
    "                with open(log_path, \"w\") as f:\n"
    "                    f.write(\"\\n\".join(str(t) for t in recent + [time.time()]) + \"\\n\")\n"
    "            except OSError:\n"
    "                logger.error(\"could not write %s\", log_path, exc_info=True)\n"
    "            os._exit(4)\n"
    "\n"
    "    async def _bootstrap_redial_loop(self) -> None:\n",
    "watchdog loop",
)
service.write_text(src)
print("bootnode-watchdog: patched", service)
