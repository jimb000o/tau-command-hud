"""Patch tau-testnet so a sync keeps going past one batch of 2000 blocks.

network/service.py's _sync_and_ingest_from_peer asks a peer for at most 2000
headers and ingests those blocks once. Nothing asks for the next page: a fresh
node stops at block #1999 and then only advances by one 2000-batch per gossip
announce it happens to receive. Wrap the method so it repeats from a new
locator until a batch ingests nothing (caught up) or a cap is hit.

Usage: python3 -I sync-paginate.py <tau-testnet checkout>
"""
import pathlib
import sys

service = pathlib.Path(sys.argv[1]) / "network" / "service.py"
src = service.read_text()

old_def = "    async def _sync_and_ingest_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000) -> int:\n"
assert src.count(old_def) == 1, "service.py: _sync_and_ingest_from_peer signature not found"
assert "_sync_one_batch_from_peer" not in src, "service.py: already patched"

wrapper = '''    async def _sync_and_ingest_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000, max_batches: int = 500) -> int:
        """Sync in batches of `limit` until a batch ingests nothing.

        The peer answers one get_headers with at most `limit` headers; a chain
        further ahead than that needs the next request from a fresh locator.
        """
        total = 0
        for _ in range(max_batches):
            ingested = await self._sync_one_batch_from_peer(peer_id, locator, stop=stop, limit=limit)
            total += ingested
            if ingested <= 0:
                break
            locator = self._build_block_locator()
        if total:
            logger.info("Sync from %s complete: %d blocks ingested", peer_id, total)
        return total

    async def _sync_one_batch_from_peer(self, peer_id: Any, locator: List[str], stop: Optional[str] = None, limit: int = 2000) -> int:
'''
service.write_text(src.replace(old_def, wrapper, 1))
print("patched: _sync_and_ingest_from_peer now paginates")
