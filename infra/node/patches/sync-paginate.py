"""Patch tau-testnet so header sync keeps paging until the node is caught up.

Upstream `_sync_and_ingest_from_peer` fetches ONE batch of at most 2000 headers
and returns, and nothing calls it again until the next gossip announce. A node
behind by more than 2000 blocks therefore stalls (e.g. at #1999).

The wrapper repeats the batch from a fresh locator while the canonical head
actually advances. Progress is measured on the head, not on the batch's
"ingested" count: that count includes blocks stored as orphans and blocks
already known, so a batch can report 2000 ingested while the chain stays put,
and looping on it would hammer the peer every few seconds forever.

Usage: python3 -I sync-paginate.py <tau-testnet checkout>
"""
import pathlib
import sys

service = pathlib.Path(sys.argv[1]) / "network" / "service.py"
src = service.read_text()

old = "    async def _sync_and_ingest_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000) -> int:\n"
assert src.count(old) == 1, "service.py: _sync_and_ingest_from_peer signature not found"

wrapper = '''    async def _sync_and_ingest_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000, max_batches: int = 500) -> int:
        """Page through header sync until the canonical head stops advancing."""
        import db

        def head_number() -> int:
            try:
                head = db.get_canonical_head()
                return int(((head or {}).get("header") or {}).get("block_number", 0))
            except Exception:
                return -1

        total = 0
        for _ in range(max_batches):
            before = head_number()
            ingested = await self._sync_one_batch_from_peer(peer_id, locator, stop=stop, limit=limit)
            total += ingested
            after = head_number()
            if ingested <= 0 or after <= before:
                break
            locator = self._build_block_locator()
        logger.info("Sync from %s complete: %d blocks ingested, canonical head #%s", peer_id, total, head_number())
        return total

    async def _sync_one_batch_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000) -> int:
'''
src = src.replace(old, wrapper, 1)
service.write_text(src)
print("patched: _sync_and_ingest_from_peer now pages until the canonical head stops advancing")
