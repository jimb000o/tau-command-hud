"""Patch tau-testnet so the node tells how far behind the network it is.

The node learns the network's tip at every handshake (peer head_number), in
every header-sync reply (tip_number) and in every block announce, but keeps
none of it; RPC clients only see the local canonical head. This records the
highest peer tip seen in network/service.py and reports it as `network_tip`
{"number", "seen"} in the getgovernance payload (null until a peer was seen),
so a dashboard can show "catching up: n / tip" during the initial sync.

Usage: python3 -I network-tip.py <tau-testnet checkout>
Apply AFTER read-until-eof.py (it anchors on its import line).
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
    "import functools\nimport logging\n",
    "import functools\nimport logging\nimport time\n",
    "service.py time import",
)
replace_once(
    "from .libp2p_compat import read_stream_to_eof  # noqa: E402\n",
    "from .libp2p_compat import read_stream_to_eof  # noqa: E402\n"
    "\n"
    "# Highest peer tip this node has heard of (handshake head, header-sync reply,\n"
    "# block announce). Read by commands/getgovernance.py as `network_tip`.\n"
    "_network_tip: Dict[str, Any] = {\"number\": None, \"seen\": None}\n"
    "\n"
    "\n"
    "def note_network_tip(number: Any) -> None:\n"
    "    try:\n"
    "        n = int(number)\n"
    "    except (TypeError, ValueError):\n"
    "        return\n"
    "    if _network_tip[\"number\"] is None or n >= _network_tip[\"number\"]:\n"
    "        _network_tip[\"number\"] = n\n"
    "        _network_tip[\"seen\"] = time.time()\n"
    "\n"
    "\n"
    "def best_known_tip() -> Dict[str, Any]:\n"
    "    return dict(_network_tip)\n",
    "service.py import",
)
replace_once(
    "                                remote_n = int(remote_head_number)\n",
    "                                remote_n = int(remote_head_number)\n"
    "                                note_network_tip(remote_n)\n",
    "service.py handshake",
)
replace_once(
    "            headers = resp.get(\"headers\") or []\n        except Exception:\n            logger.warning(\"Failed to sync headers from %s\", peer_id, exc_info=True)\n",
    "            headers = resp.get(\"headers\") or []\n            note_network_tip(resp.get(\"tip_number\"))\n        except Exception:\n            logger.warning(\"Failed to sync headers from %s\", peer_id, exc_info=True)\n",
    "service.py header sync",
)
replace_once(
    "        headers = payload.get(\"headers\") or []\n        remote_tip = payload.get(\"tip_hash\") or payload.get(\"block_hash\")\n",
    "        headers = payload.get(\"headers\") or []\n        note_network_tip(payload.get(\"tip_number\"))\n"
    "        remote_tip = payload.get(\"tip_hash\") or payload.get(\"block_hash\")\n",
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
    "        payload[\"network_tip\"] = _net_service.best_known_tip()\n"
    "    except Exception:\n"
    "        payload[\"network_tip\"] = None\n"
) + old
gov.write_text(gsrc.replace(old, new, 1))
print("patched: network tip recorded in network/service.py and reported by getgovernance")
