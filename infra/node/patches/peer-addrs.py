"""Patch tau-testnet so learned peer addresses cannot point the node at itself.

Peers advertise `host.get_addrs()`, which for a node bound to 0.0.0.0 is
`/ip4/0.0.0.0/tcp/4001`; gossip and the persisted peerstore keep such
addresses forever. libp2p 0.8 dials only one TCP address per peer, so once
`/ip4/0.0.0.0/tcp/4001` sorts before the real bootnode address the node
dials 0.0.0.0:4001 = its own listener, the noise handshake meets its own
peer id and every bootstrap dial fails with "handshake failed when
upgrading to secure connection" (seen 2026-10-27 after a docker restart).

Fix: drop unspecified, loopback, link-local and private addresses wherever
a peer address is learned (gossip, persisted peerstore, connection
callback), and let a configured bootstrap peer be dialed with exactly its
configured addresses.

Usage: python3 -I peer-addrs.py <tau-testnet checkout>
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])


def patch(path: pathlib.Path, pairs) -> None:
    src = path.read_text()
    for old, new, what in pairs:
        assert src.count(old) == 1, f"{path.name}: {what} anchor not found exactly once"
        src = src.replace(old, new, 1)
    path.write_text(src)


patch(root / "network" / "libp2p_compat.py", [
    (
        "from libp2p.peer.peerstore import PERMANENT_ADDR_TTL\n",
        "from libp2p.peer.peerstore import PERMANENT_ADDR_TTL\n"
        "import ipaddress\n",
        "import",
    ),
    (
        "def seed_peerstore(\n",
        "def is_dialable_addr(addr: multiaddr.Multiaddr) -> bool:\n"
        "    \"\"\"False for addresses no other host can be reached at: unspecified\n"
        "    (0.0.0.0, ::), loopback, link-local and private ranges. Peers advertise\n"
        "    their bind address, which is 0.0.0.0 for most nodes, and dialing it\n"
        "    reaches our own listener.\"\"\"\n"
        "    try:\n"
        "        for proto in (\"ip4\", \"ip6\"):\n"
        "            try:\n"
        "                value = addr.value_for_protocol(proto)\n"
        "            except Exception:\n"
        "                continue\n"
        "            if value is None:\n"
        "                continue\n"
        "            ip = ipaddress.ip_address(value)\n"
        "            return not (ip.is_unspecified or ip.is_loopback or ip.is_link_local\n"
        "                        or ip.is_private or ip.is_multicast or ip.is_reserved)\n"
        "    except Exception:\n"
        "        return True\n"
        "    return True\n"
        "\n"
        "\n"
        "def dialable_addrs(addrs: Iterable[multiaddr.Multiaddr]) -> List[multiaddr.Multiaddr]:\n"
        "    return [a for a in addrs if is_dialable_addr(a)]\n"
        "\n"
        "\n"
        "def seed_peerstore(\n",
        "helper",
    ),
    (
        "        parsed = [a if isinstance(a, multiaddr.Multiaddr) else multiaddr.Multiaddr(a)\n"
        "                  for a in addrs]\n"
        "        host.get_peerstore().add_addrs(pid, parsed, ttl)\n",
        "        parsed = dialable_addrs(a if isinstance(a, multiaddr.Multiaddr) else multiaddr.Multiaddr(a)\n"
        "                                for a in addrs)\n"
        "        host.get_peerstore().add_addrs(pid, parsed, ttl)\n",
        "seed_peerstore strict",
    ),
    (
        "    if not parsed:\n        return parsed\n    try:\n        host.get_peerstore().add_addrs(pid, parsed, ttl)\n",
        "    parsed = dialable_addrs(parsed)\n    if not parsed:\n        return parsed\n    try:\n        host.get_peerstore().add_addrs(pid, parsed, ttl)\n",
        "seed_peerstore lenient",
    ),
    (
        "            peerstore.add_addrs(\n                ID.from_base58(pid),\n                [multiaddr.Multiaddr(a) for a in addrs],\n                PERMANENT_ADDR_TTL,\n            )\n",
        "            parsed = dialable_addrs(multiaddr.Multiaddr(a) for a in addrs)\n"
        "            if not parsed:\n                continue\n"
        "            peerstore.add_addrs(ID.from_base58(pid), parsed, PERMANENT_ADDR_TTL)\n",
        "seed_peerstore_persisted",
    ),
])

patch(root / "network" / "service.py", [
    (
        "                self.host.get_peerstore().add_addrs(peer_id, [ma], 60)\n",
        "                from .libp2p_compat import is_dialable_addr\n"
        "                if is_dialable_addr(ma):\n"
        "                    self.host.get_peerstore().add_addrs(peer_id, [ma], 60)\n",
        "connection callback",
    ),
    (
        "            try:\n                self.host.get_peerstore().add_addrs(pid, maddrs, 86400)\n            except Exception:\n                pass\n",
        "            # A configured bootstrap peer is dialed at its configured addresses only:\n"
        "            # libp2p tries one TCP address per peer, and a learned 0.0.0.0 or\n"
        "            # private address would be our own listener.\n"
        "            try:\n"
        "                self.host.get_peerstore().clear_addrs(pid)\n"
        "            except Exception:\n"
        "                pass\n"
        "            try:\n                self.host.get_peerstore().add_addrs(pid, maddrs, 86400)\n            except Exception:\n                pass\n",
        "bootstrap dial",
    ),
])
print("peer-addrs patch applied")
