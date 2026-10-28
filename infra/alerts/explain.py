"""What a rule change does, in plain words.

A consensus_rule_update carries Tau rule text (and optionally a settings
patch). The node folds the text into the running spec pointwise: each output
stream the text defines gets the new definition, every other stream keeps
its old one. So the honest answer to "what does this change?" is a per-stream
comparison of the proposal with the rules in force, described in terms of what
each consensus stream decides (tau_defs.py at the pinned tau-testnet commit):

  o6  is a block valid?            i10 signature verified by the host
  o7  may this validator propose?  i8  proposer identity, i6 height, i7 time
  o9  base fee per transaction     i14 proposer stake, i15 eligibility mode
"""
from __future__ import annotations

import re

GENESIS_RULES = (
    "always (\n    o6[t]:bv[16] = i10[t]:bv[16] &&\n    o7[t]:bv[16] = { 1 }:bv[16]\n &&\n"
    "    o9[t]:bv[24] = { #x00000a }:bv[24]\n)\n"
)

INPUTS = {
    "i6": "block height", "i7": "block time", "i8": "which validator proposes", "i9": "the previous block",
    "i10": "the signature check", "i11": "endorsed claims", "i13": "the proposer's key", "i14": "the proposer's balance",
    "i15": "the eligibility mode",
}
STREAM_TOPIC = {"o6": "Which blocks count as valid", "o7": "Who may make blocks", "o9": "Base fee per transaction"}


def short(h: str) -> str:
    h = str(h or "")
    return h[:6] + "…" + h[-4:] if len(h) > 14 else h


def strip_comments(text: str) -> str:
    """Drop comment lines (a line starting with # that is not a #x/#b literal)."""
    return "\n".join("" if re.match(r"\s*#(?![xb][0-9a-fA-F])", line) else line for line in text.splitlines())


def label_of(text: str) -> str | None:
    """The proposer's own heading from the comment block, if it wrote one
    (the wallet templates start with e.g. "# WHITELIST PROPOSER")."""
    for line in text.splitlines():
        m = re.match(r"\s*#\s*(.+?)\s*$", line)
        if not m:
            if line.strip():
                break
            continue
        t = m.group(1)
        if re.fullmatch(r"[-=#*_ ]+", t) or re.match(r"[io]\d+\s*:", t) or t.lower().startswith(("replace ", "restricts", "this ")):
            continue
        if 3 <= len(t) <= 60:
            return t.capitalize() if t.isupper() else t
    return None


def _body(text: str) -> str:
    """The inside of the outermost always ( ... )."""
    t = strip_comments(text)
    m = re.search(r"\balways\s*\(", t)
    if not m:
        return t.strip().rstrip(".")
    depth, start = 0, m.end() - 1
    for i in range(start, len(t)):
        if t[i] == "(":
            depth += 1
        elif t[i] == ")":
            depth -= 1
            if depth == 0:
                return t[start + 1:i]
    return t[start + 1:]


def _split_and(body: str) -> list[str]:
    parts, depth, cur, i = [], 0, "", 0
    while i < len(body):
        c = body[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        if depth == 0 and body.startswith("&&", i):
            parts.append(cur)
            cur, i = "", i + 2
            continue
        cur += c
        i += 1
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def clauses(text: str) -> dict[str, str]:
    """output stream -> the conjunct that defines it."""
    out: dict[str, str] = {}
    for c in _split_and(_body(text)):
        for s in sorted(set(re.findall(r"\b(o\d+)\[t\]", c))):
            out[s] = c
    return out


def apply(spec: dict[str, str], revisions: list[str]) -> dict[str, str]:
    new = dict(spec)
    for r in revisions:
        new.update(clauses(r))
    return new


def _const(expr: str) -> int | None:
    m = re.fullmatch(r"\(?\s*\{\s*(#x[0-9a-fA-F]+|#b[01]+|\d+)\s*\}(?::bv\[\d+\])?\s*\)?", expr.strip())
    if not m:
        return None
    v = m.group(1)
    return int(v[2:], 16) if v.startswith("#x") else int(v[2:], 2) if v.startswith("#b") else int(v)


def _assign(clause: str, stream: str) -> str | None:
    """Right-hand side when the clause is just `oN[t] = X`."""
    m = re.fullmatch(rf"\(?\s*{stream}\[t\](?::bv\[\d+\])?\s*=\s*(.+?)\s*\)?", clause.strip(), re.S)
    return m.group(1) if m and "?" not in m.group(1) else None


def _inputs(clause: str) -> list[str]:
    return [INPUTS.get(i, i) for i in dict.fromkeys(re.findall(r"\b(i\d+)\[t\]", clause))]


def _names(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def describe_stream(stream: str, clause: str, old: str | None) -> dict:
    """{topic, text, title, why, severity} for one changed stream."""
    rhs = _assign(clause, stream)
    val = _const(rhs) if rhs is not None else None
    ins = _inputs(clause)
    topic = STREAM_TOPIC.get(stream, f"Output {stream}")
    if stream == "o9":
        if val is not None:
            old_v = _const(_assign(old, "o9") or "") if old else None
            if old_v is not None and old_v != val:
                return {"topic": topic, "text": f"{old_v:,} → {val:,} AGRS", "title": f"Base fee {old_v:,} → {val:,} AGRS",
                        "why": f"Every transaction would cost {val:,} AGRS instead of {old_v:,}."}
            return {"topic": topic, "text": f"{val:,} AGRS", "title": f"Base fee {val:,} AGRS",
                    "why": f"Every transaction would cost {val:,} AGRS."}
        return {"topic": topic, "text": f"computed from {_names(ins)}" if ins else "a new formula",
                "title": "New fee formula", "why": "Transaction fees would follow a formula instead of a fixed amount."}
    if stream == "o7":
        if val == 1:
            return {"topic": topic, "text": "every validator", "title": "Every validator may make blocks",
                    "why": "All validators take part in making blocks."}
        if val == 0:
            return {"topic": topic, "text": "nobody", "title": "Stop all block making", "severity": "halt",
                    "why": "If it takes effect, nobody may make blocks and the chain stops."}
        m = re.search(r"i8\[t\][^=]*=\s*\{\s*#x([0-9a-fA-F]{16,})\s*\}", clause)
        if m and "?" in clause and len(re.findall(r"i8\[t\]", clause)) == 1:
            return {"topic": topic, "text": f"only validator {short(m.group(1).lower())}", "title": "Only one validator may make blocks",
                    "why": "Block making would rest with a single validator. Others could no longer add blocks."}
        return {"topic": topic, "text": f"depends on {_names(ins)}" if ins else "a new condition",
                "title": "New rule for who makes blocks", "why": "Changes which validators may add blocks to the chain."}
    if stream == "o6":
        if rhs is not None and re.fullmatch(r"\(?\s*i10\[t\](?::bv\[\d+\])?\s*\)?", rhs.strip()):
            return {"topic": topic, "text": "blocks with a verified signature", "title": "Blocks need a valid signature",
                    "why": "Only blocks signed by their validator are accepted (the default)."}
        if val == 1:
            return {"topic": topic, "text": "every block, signed or not", "title": "Accept blocks without signature check", "severity": "unsafe",
                    "why": "Blocks would be accepted even without a valid signature."}
        if val == 0:
            return {"topic": topic, "text": "no block", "title": "Reject all blocks", "severity": "halt",
                    "why": "If it takes effect, every new block is rejected and the chain stops."}
        return {"topic": topic, "text": f"depends on {_names(ins)}" if ins else "a new condition",
                "title": "New rule for valid blocks", "why": "Changes which blocks the network accepts."}
    return {"topic": topic, "text": f"depends on {_names(ins)}" if ins else (f"set to {val:,}" if val is not None else "new definition"),
            "title": f"New definition of {stream}", "why": "Changes a part of the consensus rules every node runs."}


PATCH_WHY = {
    "validator_additions": "More parties would make blocks and vote on rule changes.",
    "validator_removals": "Fewer parties would make blocks and vote on rule changes.",
    "vote_quorum": "Changes how many votes a rule change needs.",
    "max_rule_txs_per_block": "Changes how many rule transactions fit in one block.",
    "fee_beneficiary": "Changes who receives the transaction fees.",
    "eligibility_mode": "Switches the consensus mechanism: who may make blocks. Tau does this by agreement, without a fork or a software upgrade.",
    "approval_slots_active": "Lets accounts require co-signatures on large transfers.",
}
QUORUM_TXT = {"supermajority": "two thirds", "majority": "more than half"}
# eligibility_mode values -> the consensus mechanism in plain words (same names as the pages)
MODE_TXT = {"validator_set": "proof of authority (fixed validator list)", "tau_validator_set": "validator list in Tau",
            "stake": "proof of stake"}


def explain(revisions: list[str], patch: dict | None, spec: dict[str, str]) -> dict:
    """Everything the posts and the tracker page say about one proposal.

    spec: the rules in force when it was proposed (stream -> clause).
    Returns {title, label, changes: [{topic, text, why}], unchanged: [streams], why, severity}.
    """
    new = {}
    for r in revisions:
        new.update(clauses(r))
    changes, unchanged = [], []
    for s in sorted(new, key=lambda x: int(x[1:])):
        if _norm(new[s]) == _norm(spec.get(s, "")):
            unchanged.append(s)
            continue
        changes.append({"stream": s, **describe_stream(s, new[s], spec.get(s))})
    patch = patch or {}
    for a in patch.get("validator_additions") or []:
        changes.append({"topic": "Validators", "text": f"add {short(str(a).lower())}", "title": f"Admit validator {short(str(a).lower())}",
                        "why": PATCH_WHY["validator_additions"]})
    for a in patch.get("validator_removals") or []:
        changes.append({"topic": "Validators", "text": f"remove {short(str(a).lower())}", "title": f"Remove validator {short(str(a).lower())}",
                        "why": PATCH_WHY["validator_removals"]})
    for k in ("vote_quorum", "max_rule_txs_per_block", "fee_beneficiary", "eligibility_mode", "approval_slots_active"):
        if k in patch:
            v = patch[k]
            text = {"vote_quorum": f"votes needed: {QUORUM_TXT.get(v, v)}", "max_rule_txs_per_block": f"{v} rule transactions per block",
                    "fee_beneficiary": f"fees go to {short(v)}" if v else "fees go to each block's maker",
                    "eligibility_mode": f"consensus switches to {MODE_TXT.get(v or 'validator_set', v)}",
                    "approval_slots_active": "co-signed transfers on" if v else "co-signed transfers off"}[k]
            changes.append({"topic": "Settings", "text": text, "title": text[0].upper() + text[1:], "why": PATCH_WHY[k]})
    label = next((label_of(r) for r in revisions if label_of(r)), None)
    if label and label.lower().startswith("tau-driven consensus"):
        label = None
    if not changes:
        why = ("Nothing would change: the text equals the rules already in force. "
               "Often a test of the voting itself.") if revisions else "It carries no rule text and no settings."
        return {"title": "Same rules as now (no real change)", "label": label, "changes": [], "unchanged": unchanged,
                "why": why, "severity": "none"}
    sev = next((c.get("severity") for c in changes if c.get("severity") == "halt"), None) or \
        next((c.get("severity") for c in changes if c.get("severity")), None)
    title = " + ".join(dict.fromkeys(c["title"] for c in changes[:2])) + (f" + {len(changes) - 2} more" if len(changes) > 2 else "")
    halt = next((c for c in changes if c.get("severity") == "halt"), None)
    why = halt["why"] if halt else " ".join(dict.fromkeys(c["why"] for c in changes[:2]))
    return {"title": title, "label": label, "changes": [{k: c[k] for k in ("topic", "text", "why")} for c in changes],
            "unchanged": unchanged, "why": why, "severity": sev or "normal"}


# ---------------- rule text diff (same as assets/rulediff.js on the pages) ----------------
def _lines(spec: dict[str, str]) -> list[tuple[str, str]]:
    """The spec as readable text, as (shown, compared) pairs. The && between two
    clauses is shown but not compared, so adding a clause does not mark the one before it."""
    seen, cs = set(), []
    for s in sorted(spec, key=lambda x: int(x[1:])):
        if spec[s] not in seen:
            seen.add(spec[s])
            cs.append(spec[s])
    out = [("always (", "always (")]
    for i, c in enumerate(cs):
        ls = [ln.rstrip() for ln in c.split("\n") if ln.strip()]
        ind = min((len(ln) - len(ln.lstrip()) for ln in ls[1:]), default=0)
        for j, ln in enumerate(ls):
            t = ("        " + ln[ind:]) if j else ("    " + ln.strip())
            out.append((t + (" &&" if j == len(ls) - 1 and i < len(cs) - 1 else ""), t.strip()))
    out.append((")", ")"))
    return out


def diff(revisions: list[str], spec: dict[str, str]) -> dict:
    """{lines: [[op, text]], added, removed, streams} comparing the rules in force
    with the rules after this proposal. Whitespace-only changes do not count."""
    import difflib
    new, streams = dict(spec), []
    for s, c in apply({}, revisions).items():
        if s in spec and _norm(spec[s]) == _norm(c):
            continue
        new[s] = c
        streams.append(s)
    a, b = _lines(spec), _lines(new)
    sm = difflib.SequenceMatcher(None, [k for _, k in a], [k for _, k in b], autojunk=False)
    rows: list[list[str]] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            rows += [[" ", t] for t, _ in b[j1:j2]]
        else:
            rows += [["-", t] for t, _ in a[i1:i2]] + [["+", t] for t, _ in b[j1:j2]]
    added = sum(1 for r in rows if r[0] == "+")
    removed = sum(1 for r in rows if r[0] == "-")
    return {"lines": rows, "added": added, "removed": removed, "streams": sorted(streams, key=lambda x: int(x[1:]))}


def diff_summary(d: dict) -> str:
    if not d["added"] and not d["removed"]:
        return "no difference"
    pl = lambda n: f"{n} line{'' if n == 1 else 's'}"  # noqa: E731
    return ", ".join(x for x in (f"+{pl(d['added'])}" if d["added"] else "", f"−{pl(d['removed'])}" if d["removed"] else "") if x)
