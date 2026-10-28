"""Patch tau-testnet so the node tells which peers it knows.

The node talks to peers (connections, handshakes, header syncs, block
announces) and hears of more in the `dht_peers` list a peer sends with its
handshake, but RPC clients cannot see any of it. This keeps a small in-memory
peer book in network/service.py and reports it as `peers` in the
getgovernance payload, with the node's own peer ID as `peer_id` (known once a
peer connected; the kit's heartbeat reports it so tauhud.com can name the node):

    [{"id", "first_seen", "last_direct", "last_heard", "head", "connected"}]

`last_direct` is the last time this node exchanged something with the peer
itself, `last_heard` the last time another peer listed it. No addresses: the
list is public through the relay, and a peer ID says nothing about where a
node runs. At most 500 entries; the one heard of longest ago goes first.

Usage: python3 -I peer-book.py <tau-testnet checkout>
Apply AFTER network-tip.py (it anchors on its lines).
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
    "def best_known_tip() -> Dict[str, Any]:\n    return dict(_network_tip)\n",
    "def best_known_tip() -> Dict[str, Any]:\n    return dict(_network_tip)\n"
    "\n"
    "\n"
    "# Peers this node has met or heard of. Read by commands/getgovernance.py as `peers`.\n"
    "_peer_book: Dict[str, Dict[str, Any]] = {}\n"
    "_PEER_BOOK_MAX = 500\n"
    "_peer_self: Dict[str, Any] = {\"id\": None}  # our own ID, which peers list back to us\n"
    "\n"
    "\n"
    "def note_peer(peer_id: Any, head: Any = None, heard: bool = False, connected: Any = None) -> None:\n"
    "    try:\n"
    "        key = str(peer_id or \"\")\n"
    "    except Exception:\n"
    "        return\n"
    "    if not key or len(key) > 128 or key == _peer_self[\"id\"]:\n"
    "        return\n"
    "    now = time.time()\n"
    "    entry = _peer_book.get(key)\n"
    "    if entry is None:\n"
    "        if len(_peer_book) >= _PEER_BOOK_MAX:\n"
    "            stale = min(_peer_book, key=lambda k: max(_peer_book[k][\"last_direct\"] or 0,\n"
    "                                                    _peer_book[k][\"last_heard\"] or 0))\n"
    "            del _peer_book[stale]\n"
    "        entry = _peer_book[key] = {\"first_seen\": now, \"last_direct\": None, \"last_heard\": None,\n"
    "                                   \"head\": None, \"connected\": False}\n"
    "    if heard:\n"
    "        entry[\"last_heard\"] = now\n"
    "    else:\n"
    "        entry[\"last_direct\"] = now\n"
    "    if connected is not None:\n"
    "        entry[\"connected\"] = bool(connected)\n"
    "    try:\n"
    "        if head is not None:\n"
    "            entry[\"head\"] = int(head)\n"
    "    except (TypeError, ValueError):\n"
    "        pass\n"
    "\n"
    "\n"
    "def known_peers() -> List[Dict[str, Any]]:\n"
    "    return [dict(entry, id=key) for key, entry in list(_peer_book.items()) if key != _peer_self[\"id\"]]\n",
    "service.py peer book",
)
replace_once(
    "        logger.info(\"Peer connected: %s\", peer_id)\n",
    "        logger.info(\"Peer connected: %s\", peer_id)\n"
    "        try:\n"
    "            _peer_self[\"id\"] = str(self.get_id())\n"
    "        except Exception:\n"
    "            pass\n"
    "        note_peer(peer_id, connected=True)\n",
    "service.py connected",
)
replace_once(
    "            self._connected_peer_ids.discard(str(peer_id))\n",
    "            self._connected_peer_ids.discard(str(peer_id))\n"
    "            note_peer(peer_id, connected=False)\n",
    "service.py disconnected",
)
replace_once(
    "                                note_network_tip(remote_n)\n",
    "                                note_network_tip(remote_n)\n"
    "                                note_peer(peer_id, head=remote_n)\n",
    "service.py outbound handshake",
)
replace_once(
    "                    remote_pubkey = payload.get(\"peer_pubkey\", \"\")\n",
    "                    note_peer(getattr(getattr(stream, \"muxed_conn\", None), \"peer_id\", None),\n"
    "                              head=payload.get(\"head_number\"))\n"
    "                    remote_pubkey = payload.get(\"peer_pubkey\", \"\")\n",
    "service.py inbound handshake",
)
replace_once(
    "                        if not pid_str or len(pid_str) > 128:\n                            continue\n",
    "                        if not pid_str or len(pid_str) > 128:\n                            continue\n"
    "                        note_peer(pid_str, heard=True)\n",
    "service.py handshake dht_peers",
)
replace_once(
    "            note_network_tip(resp.get(\"tip_number\"))\n",
    "            note_network_tip(resp.get(\"tip_number\"))\n"
    "            note_peer(peer_id, head=resp.get(\"tip_number\"))\n",
    "service.py header sync",
)
replace_once(
    "        note_network_tip(payload.get(\"tip_number\"))\n",
    "        note_network_tip(payload.get(\"tip_number\"))\n"
    "        note_peer(peer_id, head=payload.get(\"tip_number\"))\n",
    "service.py gossip",
)
service.write_text(src)

gov = root / "commands" / "getgovernance.py"
gsrc = gov.read_text()
old = "    return api_response.success_response(\"getgovernance\", payload)\n"
assert gsrc.count(old) == 1, "getgovernance.py return anchor not found exactly once"
new = (
    "    try:\n"
    "        from network import service as _net_service\n"
    "        payload[\"peers\"] = _net_service.known_peers()\n"
    "        payload[\"peer_id\"] = _net_service._peer_self[\"id\"]\n"
    "    except Exception:\n"
    "        payload[\"peers\"] = payload[\"peer_id\"] = None\n"
) + old
gov.write_text(gsrc.replace(old, new, 1))
print("patched: peer book kept in network/service.py and reported by getgovernance")
