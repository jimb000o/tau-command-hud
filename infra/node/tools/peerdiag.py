# Diagnose why the libp2p security handshake with the bootnode fails.
# Run inside the tau-node container:
#   cd /opt/tau-command-hud/infra && docker compose cp infra/node/tools/peerdiag.py tau-node:/tmp/peerdiag.py \
#     && docker compose exec tau-node python /tmp/peerdiag.py
# The node only logs "handshake failed when upgrading to secure connection"; this prints
# the underlying cause (peer id mismatch with the actual id, closed connection, ...).
import sys, traceback
import trio
from multiaddr import Multiaddr
from libp2p import new_host
from libp2p.crypto.secp256k1 import create_new_key_pair
from libp2p.peer.id import ID
from libp2p.peer.peerinfo import PeerInfo

PEER = "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC"
ADDR = "/ip4/34.251.82.246/tcp/4001"

def tcp_check():
    import socket
    try:
        with socket.create_connection(("34.251.82.246", 4001), timeout=5):
            print("TCP to bootnode: open")
    except OSError as e:
        print(f"TCP to bootnode: FAILED ({e})")


async def main():
    tcp_check()
    host = new_host(key_pair=create_new_key_pair())
    async with host.run(listen_addrs=[Multiaddr("/ip4/0.0.0.0/tcp/0")]):
        try:
            with trio.fail_after(20):
                await host.connect(PeerInfo(ID.from_base58(PEER), [Multiaddr(ADDR)]))
            print("CONNECTED OK; remote peer id matches")
        except BaseException as e:
            def show(e, depth=0):
                while e is not None and depth < 8:
                    print(f"{'  '*depth}{type(e).__name__}: {e}")
                    for sub in getattr(e, "exceptions", []):
                        show(sub, depth + 1)
                    e = e.__cause__ or e.__context__
                    depth += 1
            show(e)

trio.run(main)
