"""Patch tau-testnet so the node notices when the bootnode runs a different
chain below our height and asks start.sh to wipe the chain data.

On a PoA testnet with a single bootnode the operators restart the chain
now and then (2026-10-27: twice). The restarted chain keeps the genesis
but every later block differs, and a node that stored blocks of the old
run sees the bootnode's head below its own height and concludes "nothing
to sync" forever. When the configured bootnode's head is lower than our
stored height and we do not have the block it names, this patch writes
/data/chain-reset and exits; start.sh wipes the chain data (identity kept)
and the container restarts onto the live chain.

Usage: python3 -I chain-reset.py <tau-testnet checkout>
Apply AFTER network-tip.py (it anchors on the note_network_tip line).
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
service = root / "network" / "service.py"
src = service.read_text()


def replace_once(old: str, new: str, what: str) -> None:
    global src
    assert src.count(old) == 1, f"service.py: {what} anchor not found exactly once"
    src = src.replace(old, new, 1)


replace_once(
    "def best_known_tip() -> Dict[str, Any]:\n    return dict(_network_tip)\n",
    "def best_known_tip() -> Dict[str, Any]:\n    return dict(_network_tip)\n"
    "\n"
    "\n"
    "CHAIN_RESET_MARKER = os.environ.get(\"TAU_CHAIN_RESET_MARKER\", \"/data/chain-reset\")\n"
    "\n"
    "\n"
    "def highest_stored_block() -> int:\n"
    "    \"\"\"Highest block number in the blocks table (orphans included), unlike the\n"
    "    canonical head which stays at the last verified block.\"\"\"\n"
    "    import db\n"
    "    try:\n"
    "        with db._db_lock:\n"
    "            cur = db._db_conn.cursor()\n"
    "            cur.execute(\"SELECT MAX(block_number) FROM blocks\")\n"
    "            row = cur.fetchone()\n"
    "        return int(row[0] or 0) if row else 0\n"
    "    except Exception:\n"
    "        return max(int(db.get_block_count() or 0) - 1, 0)\n"
    "\n"
    "\n"
    "def request_chain_reset(reason: str) -> None:\n"
    "    \"\"\"Leave a marker for start.sh and exit; the container restarts, start.sh\n"
    "    wipes the chain data and the node resyncs from the bootnode.\"\"\"\n"
    "    logger.error(\"CHAIN RESET: %s; wiping chain data on restart\", reason)\n"
    "    try:\n"
    "        with open(CHAIN_RESET_MARKER, \"w\") as f:\n"
    "            f.write(reason + \"\\n\")\n"
    "    except Exception:\n"
    "        logger.error(\"could not write %s\", CHAIN_RESET_MARKER, exc_info=True)\n"
    "        return\n"
    "    os._exit(3)\n",
    "helper",
)
replace_once(
    "                        logger.info(\"Peer %s head #%s %s, local head #%s: %s\", peer_id,\n"
    "                                    remote_head_number, str(remote_head)[:16], local_head_number,\n"
    "                                    \"syncing\" if need_sync else \"nothing to sync\")\n",
    "                        logger.info(\"Peer %s head #%s %s, local head #%s: %s\", peer_id,\n"
    "                                    remote_head_number, str(remote_head)[:16], local_head_number,\n"
    "                                    \"syncing\" if need_sync else \"nothing to sync\")\n"
    "                        # The configured bootnode is the network: when its head is below our\n"
    "                        # highest stored block (orphans included) on a block we never saw, the\n"
    "                        # chain was restarted and everything we stored above genesis is dead.\n"
    "                        try:\n"
    "                            stored_height = highest_stored_block()\n"
    "                            if (remote_head_number is not None\n"
    "                                    and self._is_bootstrap_peer(peer_id)\n"
    "                                    and local_has_blocks and remote_has_blocks\n"
    "                                    and remote_n < stored_height\n"
    "                                    and db.get_block_by_hash(remote_h) is None):\n"
    "                                request_chain_reset(\n"
    "                                    f\"bootnode {peer_id} head #{remote_n} {remote_h[:16]} is below our \"\n"
    "                                    f\"stored height #{stored_height} and unknown to us\")\n"
    "                        except Exception:\n"
    "                            logger.debug(\"chain reset check failed\", exc_info=True)\n",
    "head comparison",
)
replace_once(
    "    def _self_advertised_addrs(self) -> List[str]:\n",
    "    def _is_bootstrap_peer(self, peer_id: Any) -> bool:\n"
    "        try:\n"
    "            for cfg in (self._config.bootstrap_peers or []):\n"
    "                pid = cfg.get(\"peer_id\") if isinstance(cfg, dict) else getattr(cfg, \"peer_id\", None)\n"
    "                if pid and str(pid) == str(peer_id):\n"
    "                    return True\n"
    "        except Exception:\n"
    "            pass\n"
    "        return False\n"
    "\n"
    "    def _self_advertised_addrs(self) -> List[str]:\n",
    "bootstrap helper",
)
replace_once("import functools\nimport logging\n", "import functools\nimport logging\nimport os\n", "os import")
service.write_text(src)
print("chain-reset patch applied")
