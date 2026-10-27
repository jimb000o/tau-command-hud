"""Patch tau-testnet so the node proposes blocks only while its key is in the
active validator set, even with open governance admission.

Upstream (miner/service.py `_should_mine`) skips the validator-set check when
TAU_GOVERNANCE_OPEN_ADMISSION=true, which tau-testnet-v2 needs (see
docker-compose.yml). In PoA mode Tau's o7 is the constant 1, so a node with
mining on and a key that is not (or no longer) a validator would build its own
blocks, which peers reject: our node would leave the public chain and the HUD
would show a private fork. With this patch it simply stays a read node until
governance has added the key. Node-local policy only: it decides which blocks
we propose, never whether a block is valid.

Usage: python3 -I validator-gate.py <tau-testnet checkout>
"""
import pathlib
import sys

path = pathlib.Path(sys.argv[1]) / "miner" / "service.py"
src = path.read_text()
old = (
    "        if active and not tau_bound \\\n"
    "                and not getattr(config.settings.authority, \"open_governance_admission\", False) \\\n"
    "                and (config.MINER_PUBKEY or \"\").lower() not in active:\n"
    "            return False\n"
)
new = (
    "        if not tau_bound and (config.MINER_PUBKEY or \"\").lower() not in active:\n"
    "            if not getattr(self, \"_gate_logged\", False):\n"
    "                logger.warning(\"validator gate: key %s… is not in the active validator set; not proposing\",\n"
    "                               (config.MINER_PUBKEY or \"\")[:12])\n"
    "                self._gate_logged = True\n"
    "            return False\n"
    "        self._gate_logged = False\n"
)
assert src.count(old) == 1, "miner/service.py: validator-set gate anchor not found exactly once"
src = src.replace(old, new, 1)
assert "\nlogger = " in src or "\nlogger=" in src, "miner/service.py: no module logger"
path.write_text(src)
print("validator-gate: applied")
