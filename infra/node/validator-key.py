#!/opt/venv/bin/python
"""Create (once) and show the Tau HUD validator key.

Run on the server:  docker compose exec tau-node tau-validator-key

The private key is written to /data/validator.key (mode 0600, inside the
tau_data volume, kept when start.sh wipes chain data) and is never printed.
Only the public key is shown: it is what IDNI adds to the validator set, and
it is safe to paste anywhere. Running it again just shows the existing key.
"""
import os
import secrets
import sys

KEY = "/data/validator.key"
PUB = "/data/validator.pub"

if os.path.exists(KEY):
    if not os.path.exists(PUB):
        sys.exit(f"{KEY} exists but {PUB} is missing; not touching the key.")
    print("Existing validator key.")
else:
    # Same derivation as `tau-testnet keys new` (tau_testnet_cli/keys.py), done
    # with py_ecc directly: importing the node's modules would open its database.
    from py_ecc.bls import G2Basic
    sk = G2Basic.KeyGen(secrets.token_bytes(32))
    sk = sk if isinstance(sk, int) else int.from_bytes(bytes(sk), "big")
    fd = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(sk.to_bytes(32, "big").hex() + "\n")
    with open(PUB, "w") as f:
        f.write(G2Basic.SkToPk(sk).hex() + "\n")
    print("New validator key created. Private key stays in /data/validator.key on this server.")

print("Public key (send this to IDNI):")
print(open(PUB).read().strip())
