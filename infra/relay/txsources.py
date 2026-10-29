"""Where the testnet's transactions come from: Agorzilla, Tau HUD, or somewhere else (tauhud.com/meta/).

Every transaction in the blocks the relay holds is put in one of three groups:

  agorzilla  it pays one of Agorzilla's addresses (the bowl, a ballot box or a question box). These addresses have no
             key (hash_to_curve, see the agorilla repo's tools/addresses.mjs), so only a meal or a vote sends there,
             wherever it was signed.
  tauhud     it was sent through this relay's wallet door from a Tau HUD page (wallet, playground, vote, …), or by the
             relay itself (the end of a turn on a rule place).
  other      everything else: IDNI's tools, scripts, other wallets.

The relay remembers the hashes it sent, with the site the page came from, in SENT_PATH (only hashes and a site name;
no address, no browser). The counts per UTC day are [transactions, wallets] for each group: wallets are distinct
sender keys, not people.

GET /api/v1/sources   {"days": {"YYYY-MM-DD": {"agorzilla": [txs, wallets], "tauhud": [...], "other": [...]}},
                       "since": <first block time>, "sent_since": <first remembered send>}
"""
from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger("relay.txsources")

GROUPS = ("agorzilla", "tauhud", "other")
SENT_MAX = 50000
# Agorzilla's addresses (agorilla repo assets/core.js: BOWL, BOXES, ASKS)
AGORZILLA = frozenset({
    "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108",
    "931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392",
    "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4",
    "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b",
    "ad628e861687c726aa780c4af1d4e10df4e16c169772686ada8ed81e430ec7bd70214bb732d9b7a75fb4d968136cec86",
    "940bad7f401e65b0ddfd2b891251cdb3f027dc96bbe4d64b5ea5547900338107186cc23d500c1888598ccc4343f6df2e",
    "b6bdcade83f317c5a3e0402466a4f6c93a1b9018a3dd61026143c8284741fad2deeffda9a7fd3db587e86f4f44de3418",
    "992d87e93030634c581fc3e6c574af0da06c70798d49f82135d8231147b79c071e277616d84fb6175dbeae2264377071",
    "b09ad0b1742efd5a4a4e7fa93a52b9f5954466ca2f694db9dfda4d593d9c15a73dfdd9055ad286e8f11f76b0f69395cf",
})


def group(tx: dict, tx_hash: str, sent: dict) -> str:
    ops = tx.get("operations") if isinstance(tx.get("operations"), dict) else {}
    for op in ops.get("1") or []:
        if isinstance(op, (list, tuple)) and len(op) >= 2 and str(op[1]).lower() in AGORZILLA:
            return "agorzilla"
    site = sent.get(tx_hash)
    if site is not None:
        return site or "tauhud"
    return "other"


class TxSources:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("SENT_PATH", "/data/sent.json")
        self.sent: dict[str, str] = {}   # tx hash -> "" (Tau HUD) or the other site's name, oldest first
        self.since = time.time()
        try:
            with open(self.path) as f:
                st = json.load(f)
            if isinstance(st, dict) and isinstance(st.get("sent"), dict):
                self.sent = {str(k): str(v) for k, v in st["sent"].items()}
                self.since = float(st.get("since") or self.since)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s: %r; starting afresh", self.path, exc)

    def note(self, tx_hash, site: str = ""):
        """A transaction the relay passed to the node and the node took."""
        if not isinstance(tx_hash, str) or not tx_hash or len(tx_hash) > 128:
            return
        self.sent[tx_hash.lower()] = site
        while len(self.sent) > SENT_MAX:
            del self.sent[next(iter(self.sent))]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"since": self.since, "sent": self.sent}, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as exc:
            if not getattr(self, "_warned", False):
                log.warning("cannot write %s: %r; sent hashes live in memory only", self.path, exc)
                self._warned = True

    def by_day(self, blocks: list[dict]) -> dict:
        """Counts per UTC day from the blocks (oldest first) the relay holds."""
        days: dict[str, dict] = {}
        senders: dict[tuple[str, str], set] = {}
        first = None
        for b in blocks:
            try:
                ts = int((b.get("header") or {}).get("timestamp"))
            except (TypeError, ValueError):
                continue
            first = ts if first is None else min(first, ts)
            day = time.strftime("%Y-%m-%d", time.gmtime(ts))
            ids = b.get("tx_ids") or []
            for i, tx in enumerate(b.get("transactions") or []):
                if not isinstance(tx, dict):
                    continue
                h = str(ids[i] if i < len(ids) else tx.get("tx_hash") or "").lower()
                g = group(tx, h, self.sent)
                row = days.setdefault(day, {k: [0, 0] for k in GROUPS})
                row[g][0] += 1
                who = senders.setdefault((day, g), set())
                s = str(tx.get("sender_pubkey") or "")
                if s and s not in who:
                    who.add(s)
                    row[g][1] += 1
        return {"days": dict(sorted(days.items())), "since": first, "sent_since": round(self.since)}
