"""What we sent right before each testnet restart, read in the relay container (read only, sends nothing).

  up restarts            on the server (infra/up.sh): the report, ready to paste for IDNI
  docker compose cp restart-report.py relay:/tmp/rr.py && docker compose exec -T relay python /tmp/rr.py [days]

IDNI asked (15.11.2026) for a repeating pattern like "when I send X, it restarts". For every restart the relay noted
in the last `days` days (default 14) this prints, in English:
  - when the old chain's last block came and when the new block 1 came;
  - the cruise ships' sends in the WINDOW minutes before that last block: how many, which kinds, how many from a
    wallet's first transaction on the chain (sequence 0, a balance-0 wallet), the node's answers and answer times;
    the sends between the last block and the new block 1;
  - the last LAST sends one by one (time, kind, amount, sequence, answer, hash);
  - when the relay kept the old chain's last blocks (from 16.11.2026 on, relay CHAIN_END_DIR): the blocks' pace and
    contents, and which of our accepted sends never made it into a block (waiting when the chain ended).
Then every ship call of the same days next to each other: what its first WINDOW minutes sent and whether the testnet
restarted during the call, so a pattern (or none) shows. Facts only, no guess about the cause.
"""
import collections
import glob
import json
import os
import statistics
import sys
import time

DATA = os.environ.get("CRUISE_DATA", "/data")
EVENTS = os.environ.get("EVENTS_PATH", os.path.join(DATA, "events.json"))
LOG = os.environ.get("CRUISE_LOG_PATH", os.path.join(DATA, "cruise-log.jsonl"))
ENDS = os.environ.get("CHAIN_END_DIR", os.path.join(DATA, "chain-ends"))
WINDOW = 15 * 60
LAST = 10
TX_KINDS = ("pay", "bill", "book", "cancel", "trick")


def hm(t):
    return time.strftime("%H:%M:%S", time.gmtime(t)) + "Z" if t else "?"


def day(t):
    return time.strftime("%Y-%m-%d", time.gmtime(t)) if t else "?"


def load_log():
    rows = []
    try:
        with open(LOG) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict) and e.get("t"):
                    rows.append(e)
    except OSError as exc:
        print(f"(no cruise logbook: {exc})")
    return sorted(rows, key=lambda e: e["t"])


def sends(rows, t0, t1):
    return [e for e in rows if e.get("kind") in TX_KINDS and t0 <= e["t"] <= t1 and ("ok" in e or e.get("note"))]


def answer(e):
    if e.get("ok") is True:
        return "accepted"
    if e.get("ok") is False:
        return "refused"
    return "no answer" if "no answer" in str(e.get("note") or "") else "not sent"


def summary(ss):
    """One line on a list of sends."""
    if not ss:
        return "no sends"
    kinds = collections.Counter(e["kind"] for e in ss)
    ans = collections.Counter(answer(e) for e in ss)
    first = sum(1 for e in ss if e.get("seq") == 0 and answer(e) != "not sent")
    ms = [e["ms"] for e in ss if isinstance(e.get("ms"), int)]
    out = f"{len(ss)} sends ({', '.join(f'{k} {n}' for k, n in kinds.most_common())}); " \
          f"{', '.join(f'{n} {a}' for a, n in ans.most_common())}; {first} from a wallet's first transaction (sequence 0)"
    if ms:
        out += f"; node answered in median {statistics.median(ms):.0f} ms, max {max(ms) / 1000:.1f} s"
    span = (ss[-1]["t"] - ss[0]["t"]) / 60
    if span > 0:
        out += f"; {len(ss) / span:.1f} per minute"
    return out


def chain_end(tip, tip_ts):
    for p in sorted(glob.glob(os.path.join(ENDS, "*.json"))):
        try:
            d = json.load(open(p))
        except (OSError, ValueError):
            continue
        bs = d.get("blocks") or []
        if bs and int((bs[-1].get("header") or {}).get("block_number", -1)) == tip:
            return bs
    return None


def tx_hashes(b):
    ids = b.get("tx_ids") or []
    out = []
    for i, tx in enumerate(b.get("transactions") or []):
        h = ids[i] if i < len(ids) else (tx.get("tx_hash") if isinstance(tx, dict) else None)
        if h:
            out.append(str(h).lower())
    return out


def tx_kind(tx):
    ops = tx.get("operations") if isinstance(tx, dict) and isinstance(tx.get("operations"), dict) else {}
    return "+".join(sorted(ops)) or "none"


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 14
    since = time.time() - days * 86400
    try:
        restarts = json.load(open(EVENTS)).get("restarts") or []
    except (OSError, ValueError) as exc:
        restarts = []
        print(f"(no restart log: {exc})")
    restarts = [r for r in restarts if (r.get("detected_at") or 0) >= since]
    rows = load_log()
    print(f"Testnet restarts seen by our node (Tau HUD) in the last {days} days: {len(restarts)}. Times in UTC.")
    print(f"Our test traffic = the cruise ships: simulated passengers, small plain transfers (pay), multi-payee transfers "
          f"(bill), retractable transfers (book) and their retractions (cancel).")
    ends = []
    for n, r in enumerate(restarts, 1):
        old = r.get("old") or {}
        tip, tip_ts, b1 = old.get("tip"), old.get("tip_ts"), r.get("new_block1_ts")
        ends.append(tip_ts or r.get("detected_at"))
        print()
        print(f"Restart {n}: old chain's last block #{tip} at {day(tip_ts)} {hm(tip_ts)}; new block 1 at {hm(b1)}"
              + (f" ({(b1 - tip_ts) / 60:.1f} min later)" if b1 and tip_ts else "")
              + f"; noticed by our relay at {hm(r.get('detected_at'))}")
        if not tip_ts:
            print("  (the old chain's last block time is unknown)")
            continue
        before = sends(rows, tip_ts - WINDOW, tip_ts)
        after = sends(rows, tip_ts + 1, b1 or tip_ts + 600)
        visits = sorted({e.get("visit") for e in before + after if e.get("visit")})
        print(f"  ship call: {', '.join(visits) or 'none'}")
        if visits:
            first = min(e["t"] for e in rows if e.get("visit") in visits and e.get("kind") in TX_KINDS)
            print(f"  first send of that call {hm(first)}, {(tip_ts - first) / 60:.1f} min before the last block")
        print(f"  {WINDOW // 60} min before the last block: {summary(before)}")
        print(f"  between the last block and the new block 1: {summary(after)}")
        if before:
            print(f"  last {min(LAST, len(before))} sends before the last block:")
            for e in before[-LAST:]:
                print(f"    {hm(e['t'])} {e['kind']:6} {e.get('amount', '')!s:>7} seq {e.get('seq', '?')!s:>3} "
                      f"height {e.get('height', '?')} {answer(e):9} {e.get('ms', '')!s:>5} ms {str(e.get('hash') or '')[:16]}")
        bs = chain_end(tip, tip_ts)
        if bs:
            ts = [int((b.get("header") or {}).get("timestamp") or 0) for b in bs]
            gaps = [b - a for a, b in zip(ts, ts[1:]) if a and b]
            ours = {str(e.get("hash")).lower(): e for e in before if e.get("hash") and e.get("ok") is True}
            inblocks = set()
            print(f"  the old chain's last {len(bs)} blocks (kept by our relay):"
                  + (f" block gap median {statistics.median(gaps):.0f} s, max {max(gaps)} s" if gaps else ""))
            for b in bs[-LAST:]:
                hs = tx_hashes(b)
                inblocks.update(hs)
                kinds = collections.Counter(tx_kind(tx) for tx in b.get("transactions") or [])
                h = b.get("header") or {}
                print(f"    #{h.get('block_number')} {hm(int(h.get('timestamp') or 0))} {len(hs)} txs "
                      f"(ops {', '.join(f'{k}×{v}' for k, v in kinds.items()) or '-'}), {sum(1 for x in hs if x in ours)} ours")
            for b in bs[:-LAST]:
                inblocks.update(tx_hashes(b))
            waiting = [e for h, e in ours.items() if h not in inblocks]
            print(f"  our accepted sends not in any block when the chain ended: {len(waiting)}"
                  + (f" (oldest {hm(waiting[0]['t'])})" if waiting else ""))
        else:
            print("  the old chain's blocks were not kept (our relay keeps them from 16.11.2026 on)")
    # every call, side by side
    print()
    print(f"Every ship call in these days, its first {WINDOW // 60} minutes:")
    calls = collections.OrderedDict()
    for e in rows:
        if e.get("visit") and e.get("kind") in TX_KINDS and e["t"] >= since:
            calls.setdefault(e["visit"], []).append(e)
    for vid, es in calls.items():
        t0, t1 = es[0]["t"], es[-1]["t"]
        hit = [x for x in ends if x and t0 - 60 <= x <= t1 + 600]
        first = [e for e in es if e["t"] <= t0 + WINDOW]
        print(f"  {vid}: from {day(t0)} {hm(t0)}, {(t1 - t0) / 60:.0f} min, "
              + (f"RESTART {(hit[0] - t0) / 60:.1f} min after the first send" if hit else "no restart"))
        print(f"    {summary(first)}")


if __name__ == "__main__":
    main()
