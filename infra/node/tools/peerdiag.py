# Diagnose why the libp2p security handshake with the bootnode fails.
# Run inside the tau-node container:
#   cd /opt/tau-command-hud/infra && docker compose cp node/tools/peerdiag.py tau-node:/tmp/peerdiag.py \
#     && docker compose exec tau-node python /tmp/peerdiag.py
# The node only logs "handshake failed when upgrading to secure connection"; this tries the
# dial with several identity key kinds and prints the underlying cause for each (peer id
# mismatch with the actual id, closed connection, signature failure, ...).
import os
import sys

import trio
from multiaddr import Multiaddr
from libp2p import new_host
from libp2p.peer.id import ID
from libp2p.peer.peerinfo import PeerInfo

PEER = os.environ.get("DIAG_PEER", "12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC")
ADDR = os.environ.get("DIAG_ADDR", "/ip4/34.251.82.246/tcp/4001")


def tcp_check():
    import socket
    host, port = ADDR.split("/")[2], int(ADDR.split("/")[4])
    try:
        with socket.create_connection((host, port), timeout=5):
            print("TCP to bootnode: open")
    except OSError as e:
        print(f"TCP to bootnode: FAILED ({e})")


def key_variants():
    from libp2p.crypto.secp256k1 import create_new_key_pair as secp
    yield "secp256k1 (libp2p)", secp()
    try:
        from libp2p.crypto.ed25519 import create_new_key_pair as ed
        yield "ed25519 (libp2p)", ed()
    except Exception as e:  # pragma: no cover
        print(f"ed25519 (libp2p): unavailable ({e})")
    try:
        sys.path.insert(0, "/app/tau-testnet")
        from network.libp2p_compat import keypair_from_seed
        yield "ed25519 (tau-testnet compat, like the node)", keypair_from_seed(os.urandom(32))
    except Exception as e:
        print(f"ed25519 (tau compat): unavailable ({e})")
    try:
        from network.libp2p_compat import keypair_from_seed
        path = os.environ.get("TAU_IDENTITY_KEY_PATH", "/data/identity.key")
        with open(path, "rb") as f:
            seed = f.read()
        if len(seed) != 32:
            seed = bytes.fromhex(seed.decode().strip())
        yield "node's own identity.key", keypair_from_seed(seed)
    except Exception as e:
        print(f"node identity.key: unavailable ({e})")


def show(e, depth=0):
    while e is not None and depth < 8:
        print(f"{'  ' * depth}{type(e).__name__}: {e}")
        for sub in getattr(e, "exceptions", []):
            show(sub, depth + 1)
        e = e.__cause__ or e.__context__
        depth += 1


async def try_connect(label, key_pair, listen):
    host = new_host(key_pair=key_pair)
    addrs = [Multiaddr(listen)] if listen else []
    async with host.run(listen_addrs=addrs):
        print(f"--- {label}, our peer id {host.get_id()}, listen={listen or 'none'}")
        try:
            with trio.fail_after(20):
                await host.connect(PeerInfo(ID.from_base58(PEER), [Multiaddr(ADDR)]))
            print("    CONNECTED OK")
            await host.disconnect(ID.from_base58(PEER))
        except BaseException as e:
            show(e, 1)


async def main():
    tcp_check()
    for label, kp in key_variants():
        await try_connect(label, kp, None)
    # the node listens on 4001; a listener changes how libp2p dials, so try that too
    from libp2p.crypto.secp256k1 import create_new_key_pair as secp
    await try_connect("secp256k1 with listener", secp(), "/ip4/0.0.0.0/tcp/4002")


trio.run(main)
