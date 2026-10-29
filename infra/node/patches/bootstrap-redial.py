"""Patch tau-testnet so a node that lost every peer dials its bootstrap peers again.

Upstream dials each configured bootstrap peer five times at start and never
again. When the bootnode stops accepting connections for a while (2026-10-29:
its py-libp2p connection handling overflowed for three hours) every node that
loses it sits at 0 peers forever, with a stale head, until someone restarts it.
This adds a loop that checks every TAU_BOOTSTRAP_REDIAL_INTERVAL seconds
(default 60; <= 0 disables) and, while the node has no connected peer, runs the
normal bootstrap dial (with its own retries) for every configured bootstrap
peer. Nothing changes while at least one peer is connected.

Usage: python3 -I bootstrap-redial.py <tau-testnet checkout>
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
    "            self._nursery.start_soon(self._head_reannounce_loop)\n",
    "            self._nursery.start_soon(self._head_reannounce_loop)\n"
    "            self._nursery.start_soon(self._bootstrap_redial_loop)\n",
    "start loops",
)
replace_once(
    "    async def _head_reannounce_loop(self) -> None:\n",
    "    async def _bootstrap_redial_loop(self) -> None:\n"
    "        \"\"\"While this node has no connected peer, dial the configured bootstrap\n"
    "        peers again every TAU_BOOTSTRAP_REDIAL_INTERVAL seconds (default 60;\n"
    "        <= 0 disables). Upstream dials them at start only, so a bootnode that\n"
    "        is away for a while leaves every node peerless until a restart.\"\"\"\n"
    "        import os\n"
    "\n"
    "        try:\n"
    "            interval = float(os.environ.get(\"TAU_BOOTSTRAP_REDIAL_INTERVAL\", \"60\"))\n"
    "        except ValueError:\n"
    "            interval = 60.0\n"
    "        if interval <= 0:\n"
    "            return\n"
    "        while not self._runner_stop.is_set():\n"
    "            await trio.sleep(interval)\n"
    "            try:\n"
    "                if self.get_connected_peers():\n"
    "                    continue\n"
    "                bootstraps = list(self._config.bootstrap_peers or []) + list(getattr(self._config, \"dht_bootstrap_peers\", []) or [])\n"
    "                if not bootstraps:\n"
    "                    continue\n"
    "                logger.info(\"No connected peer; dialing %d bootstrap peer(s) again\", len(bootstraps))\n"
    "                for peer_cfg in bootstraps:\n"
    "                    await self._connect_to_bootstrap_peer(peer_cfg)\n"
    "            except Exception:\n"
    "                logger.debug(\"Bootstrap re-dial failed\", exc_info=True)\n"
    "\n"
    "    async def _head_reannounce_loop(self) -> None:\n",
    "redial loop",
)
service.write_text(src)
print("bootstrap-redial: patched", service)
