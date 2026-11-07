"""Chain history across testnet restarts (chainhist.py). Run: python test_chainhist.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from chainhist import FIELDS, ChainHistory, deep_add  # noqa: E402

FAILED = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        FAILED.append(what)


T0 = 1_762_000_000 - 1_762_000_000 % 86400   # a UTC midnight


def block(n, chain="a", gap=600, txs=1, base=T0):
    t = [{"tx_type": "user_tx", "sender_pubkey": "s%d" % (n % 3), "operations": {"1": [["x", "y", "7"]]}}] * txs
    if n == 5:
        t = t + [{"tx_type": "consensus_rule_vote", "sender_pubkey": "g"}]
    return {"block_hash": f"{chain}{n:08d}", "header": {"block_number": n, "timestamp": base + gap * n}, "transactions": t}


path = os.path.join(tempfile.mkdtemp(), "chainhist.json")
h = ChainHistory(path)
h.seed([{"old": {"block1_hash": "old1", "block1_ts": T0 - 5 * 86400, "tip": 900, "tip_ts": T0 - 4 * 86400}}])
chain_a = [{"block_hash": "g", "header": {"block_number": 0, "timestamp": 0}}] + [block(n) for n in range(1, 301)]   # 50 h
check(h.observe(chain_a, now=T0 + 300 * 600, force=True), "first chain counted")
out = h.history(now=T0 + 300 * 600)
a = out["chains"][1]
check([c["kept"] for c in out["chains"]] == ["tip", "full"] and a["blocks"] == 300 and a["txs"] == 301 and a["volume"] == 2100,
      f"seeded chain from the log, counted chain in full {[(c['kept'], c.get('blocks')) for c in out['chains']]}")
d0 = next(r for r in out["days"] if r[1] == 2)
check(d0[2] == 143 and d0[2 + FIELDS.index("gap_n")] == 142 and d0[2 + FIELDS.index("gap_sum")] == 142 * 600,
      f"day rows count blocks and the gaps between them {d0[:4]}")
check(len([r for r in out["hours"] if r[1] == 2]) == 51, "hour rows")

# reading the same blocks again changes nothing
h.observe(chain_a, now=T0 + 300 * 600 + 61)
check(h.history()["chains"][1]["txs"] == 301, "observing twice does not double count")

# the relay trims the oldest blocks (block 1 stays): the trimmed days keep their counts
trimmed = [b for b in chain_a if b["header"]["block_number"] in (0, 1) or b["header"]["block_number"] > 200]
h.observe(trimmed + [block(301)], now=T0 + 302 * 600, force=True)
a = h.history()["chains"][1]
check(a["blocks"] == 301 and a["txs"] == 302 and a["tip"] == 301, f"trimmed blocks stay counted {a['blocks']}, {a['txs']}")

# a restart: a new block 1; the old chain is frozen with its source counts
h.observe(trimmed + [block(301)], force=True, sources={"days": {"2025-11-01": {"other": [5, 1, 1, 0, 9]}}, "since": T0})
check(h.observe([block(n, chain="b", gap=60, base=T0 + 86400 * 3) for n in range(1, 11)], now=T0 + 400 * 600, force=True), "a new block 1 starts a new chain")
out = h.history()
check([c["n"] for c in out["chains"]] == [1, 2, 3] and out["chains"][2]["current"] and not out["chains"][1]["current"]
      and out["chains"][1]["blocks"] == 301, "earlier chain kept as it was")
check(out["totals"]["blocks"] == 900 + 301 + 10 and out["totals"]["txs"] == 302 + 11, f"totals over all chains {out['totals']}")
merged = h.merge_sources({"days": {"2025-11-01": {"other": [1, 1, 0, 1, 1]}, "2025-11-02": {"other": [2, 1, 1, 0, 3]}},
                          "since": T0 + 10, "hours": {}, "totals": {}})
check(merged["days"]["2025-11-01"]["other"] == [6, 2, 1, 1, 10] and merged["days"]["2025-11-02"]["other"] == [2, 1, 1, 0, 3]
      and merged["since"] == T0 and merged["chains"] == 2, f"sources add up across chains {merged['days']}")

# kept on disk
h2 = ChainHistory(path)
check(h2.history()["totals"] == out["totals"] and h2.current_id == "b00000001", "history survives a relay restart")

check(deep_add({"a": [1, 2], "b": {"c": 1}, "s": "x"}, {"a": [1, 1, 1], "b": {"c": 2, "d": 3}, "s": "y"})
      == {"a": [2, 3, 1], "b": {"c": 3, "d": 3}, "s": "x"}, "deep_add")

from chainhist import split_auto  # noqa: E402
old = {"days": {"2026-11-04": {"rabbit": [10, 2, 1, 1, 100], "idni": [5, 1, 0, 1, 5]},
                "2026-11-05": {"rabbit": [3, 1, 0, 1, 3], "cruise": [0, 0, 0, 0, 0], "bot": [0, 0, 0, 0, 0]}},
       "rabbit": {"2026-11-04": {"cruise": 6, "cruise_agrs": 60, "paid": 1, "paid_agrs": 20}}}
sa = split_auto(old)["days"]
check(sa["2026-11-04"]["rabbit"] == [3, 2, 1, 1, 20] and sa["2026-11-04"]["cruise"] == [6, 0, 0, 0, 60] and sa["2026-11-04"]["bot"] == [1, 0, 0, 0, 20]
      and sa["2026-11-05"] == old["days"]["2026-11-05"] and old["days"]["2026-11-04"]["rabbit"][0] == 10,
      "an earlier chain's cruise passengers and wages move out of the players' count; newer days and the frozen copy stay")

print("FAILED: %s" % FAILED if FAILED else "all passed")
sys.exit(1 if FAILED else 0)
