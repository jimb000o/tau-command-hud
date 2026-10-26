"""Patch tau-testnet to say, at INFO/WARNING, what sync and ingest decide.

Upstream logs a successful handshake but not the peer's head, logs the header
batch but not which blocks it covers, and drops the reason a block was
rejected ('invalid') or stored as an orphan entirely. A node parked at some
height cannot be told from a network whose tip really is that height, nor
from one block that keeps failing verification. This adds:

- one line per handshake: peer head vs local head, syncing or not;
- the block-number range of every header batch and the first missing numbers;
- "No headers received" at INFO with the peer's tip;
- per sync batch: counts of added/known/orphan/invalid, plus a WARNING with
  block number, hash and reason for every rejected block (capped per batch).

Usage: python3 -I sync-diagnostics.py <tau-testnet checkout>
Apply AFTER sync-paginate.py.
"""
import pathlib
import sys

service = pathlib.Path(sys.argv[1]) / "network" / "service.py"
src = service.read_text()


def replace_once(old: str, new: str, what: str) -> None:
    global src
    assert src.count(old) == 1, f"service.py: {what} anchor not found exactly once"
    src = src.replace(old, new, 1)


replace_once(
    "                        if need_sync:\n                            locator = self._build_block_locator()\n",
    '                        logger.info("Peer %s head #%s %s, local head #%s: %s", peer_id,\n'
    '                                    remote_head_number, str(remote_head)[:16], local_head_number,\n'
    '                                    "syncing" if need_sync else "nothing to sync")\n'
    "                        if need_sync:\n                            locator = self._build_block_locator()\n",
    "handshake need_sync",
)

replace_once(
    '        if not headers:\n            logger.debug("No headers received from %s during sync", peer_id)\n',
    '        if not headers:\n            logger.info("No headers received from %s during sync (peer tip #%s)", peer_id, resp.get("tip_number"))\n',
    "no headers",
)

replace_once(
    '        logger.info(\n'
    '            "Header sync from %s: headers=%d missing=%d stop=%s",\n'
    '            peer_id,\n'
    '            len(headers),\n'
    '            len(missing_hashes),\n'
    '            stop,\n'
    '        )\n',
    '        _nums = [h.get("block_number") for h in headers if isinstance(h, dict)]\n'
    '        _missing_nums = [h.get("block_number") for h in headers\n'
    '                         if isinstance(h, dict) and str(h.get("block_hash")) in set(missing_hashes)]\n'
    '        logger.info(\n'
    '            "Header sync from %s: headers=%d (#%s..#%s) missing=%d (first %s) peer tip #%s stop=%s",\n'
    '            peer_id,\n'
    '            len(headers),\n'
    '            _nums[0] if _nums else None,\n'
    '            _nums[-1] if _nums else None,\n'
    '            len(missing_hashes),\n'
    '            _missing_nums[:5],\n'
    '            resp.get("tip_number"),\n'
    '            str(stop)[:16] if stop else None,\n'
    '        )\n',
    "header sync log",
)

replace_once(
    "            ingested = 0\n"
    "            for b in sorted_blocks:\n"
    "                try:\n"
    "                    blk = Block.from_dict(b)\n"
    "                    res = chain_state.ingest_block(blk)\n"
    "                    if res.status in ('added', 'orphan', 'known'):\n"
    "                        ingested += 1\n"
    "                except Exception as e:\n"
    "                    logger.debug(\"Ingest error for block: %s\", e)\n"
    "                    continue\n",
    "            ingested = 0\n"
    "            counts: Dict[str, int] = {}\n"
    "            complaints = 0\n"
    "            for b in sorted_blocks:\n"
    "                num = (b.get('header') or {}).get('block_number')\n"
    "                try:\n"
    "                    blk = Block.from_dict(b)\n"
    "                    res = chain_state.ingest_block(blk)\n"
    "                    counts[res.status] = counts.get(res.status, 0) + 1\n"
    "                    if res.status in ('added', 'orphan', 'known'):\n"
    "                        ingested += 1\n"
    "                    elif complaints < 5:\n"
    "                        complaints += 1\n"
    "                        logger.warning(\"Block #%s %s rejected during sync from %s: %s; header=%s proof=%s\",\n"
    "                                       num, str(blk.block_hash)[:16], peer_id, res.message,\n"
    "                                       b.get('header'), bool(b.get('consensus_proof')))\n"
    "                except Exception as e:\n"
    "                    counts['error'] = counts.get('error', 0) + 1\n"
    "                    if complaints < 5:\n"
    "                        complaints += 1\n"
    "                        logger.warning(\"Block #%s failed to ingest during sync from %s: %s\", num, peer_id, e, exc_info=True)\n"
    "                    continue\n"
    "            if sorted_blocks:\n"
    "                nums = [(b.get('header') or {}).get('block_number') for b in sorted_blocks]\n"
    "                logger.info(\"Sync batch from %s: %d block bodies (#%s..#%s): %s\", peer_id, len(sorted_blocks),\n"
    "                            nums[0], nums[-1], \", \".join(f\"{k}={v}\" for k, v in sorted(counts.items())) or \"none\")\n",
    "ingest loop",
)

service.write_text(src)
print("patched: handshake heads, header ranges, empty replies and per-block ingest verdicts logged")
