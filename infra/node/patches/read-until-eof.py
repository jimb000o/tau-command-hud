"""Patch tau-testnet so P2P sync reads a whole reply, not one yamux frame.

network/service.py fetches headers and block bodies with a single
`await stream.read(N)`. py-libp2p's yamux `read(n)` returns whatever is
buffered when data first arrives, i.e. one frame of ~64 KiB, so any reply
larger than that (2000 headers, 128 blocks) is cut off and json.loads fails
with "Unterminated string starting at ... column 65523". The serving side
writes the reply and closes the stream, so the fix is to read until EOF.

Usage: python3 -I read-until-eof.py <tau-testnet checkout>
Exits non-zero if the source no longer looks like the pinned commit.
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
compat = root / "network" / "libp2p_compat.py"
service = root / "network" / "service.py"

HELPER = '''

async def read_stream_to_eof(stream, limit: int, *, chunk_timeout: float = 30.0) -> bytes:
    """Read until the peer closes the stream, at most `limit` bytes.

    yamux `read(n)` returns one frame (~64 KiB) as soon as it is buffered, so
    a reply larger than that needs the loop. Stops at EOF or reset, at
    `limit`, or when no chunk arrives within `chunk_timeout` seconds.
    """
    buf = bytearray()
    while len(buf) < limit:
        chunk = None
        with trio.move_on_after(chunk_timeout) as scope:
            try:
                chunk = await stream.read(limit - len(buf))
            except Exception:  # MuxedStreamEOF / MuxedStreamReset: the peer is done
                chunk = None
        if scope.cancelled_caught or not chunk:
            break
        buf += chunk
    return bytes(buf)
'''

src = compat.read_text()
anchor = "\n\nasync def close_stream_safely(stream) -> None:"
assert src.count(anchor) == 1, "libp2p_compat.py: anchor not found"
assert "read_stream_to_eof" not in src, "libp2p_compat.py: already patched"
compat.write_text(src.replace(anchor, HELPER + anchor, 1))

src = service.read_text()
# the import line names every shim upstream installs (539d1e2: one, e88814b: two), so find it by its start
import re
imports = re.findall(r"^from \.libp2p_compat import [^\n]*apply_quic_cleanup_shim[^\n]*$", src, re.M)
assert len(imports) == 1, "service.py: import anchor not found"
old_import = imports[0]
src = src.replace(old_import, old_import + "\nfrom .libp2p_compat import read_stream_to_eof  # noqa: E402", 1)
for n in ("2 * 1024 * 1024", "20 * 1024 * 1024"):
    old = f"resp_raw = await stream.read({n})"
    assert src.count(old) == 1, f"service.py: expected exactly one '{old}'"
    src = src.replace(old, f"resp_raw = await read_stream_to_eof(stream, {n})", 1)
service.write_text(src)
print("patched: read_stream_to_eof in libp2p_compat.py; 2 sync reads in service.py")
