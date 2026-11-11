"""Rule facts: what a Tau rule answers, for every possible case. The same reading as assets/rulefacts.js (the
Playground's X-ray and the meaning of a rule change on /proposals/ and /history/), in Python for two services:
alerts (what a rule change decides differently, in its Telegram post) and relay (the pirates' fee edge).

infra/alerts/rulefacts.py and infra/relay/rulefacts.py are one file in two places, because each service's image
copies only its own folder; test_rulefacts.py in each folder fails when they differ. tests/meaning-cases.json holds
the lines this file and assets/rulefacts.js must both write, tests/rulefacts-cases.json the answers of the real Tau
engine both must give.

How the engine turns a rule into an answer, as measured with tau-lang: when 0 is among the answers a rule allows,
the engine answers 0 (an answer the rule leaves open reads as 0); when it allows only answers other than 0, it
answers one of those; when it allows none, the rule contradicts itself there. The reading cuts each input at the
values the rule compares it with; one value per piece stands for the whole piece, so trying every combination of
pieces covers every possible case. It is exact inside that scope and says when a rule is outside it (Outside.code:
"text", "temporal", "computes", "outputs", "big"). No dependencies.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone


class Outside(Exception):
    """The rule is outside what this reading covers; code says why."""

    def __init__(self, msg: str, code: str = "text"):
        super().__init__(msg)
        self.code = code


def _out(msg: str, code: str = "text"):
    raise Outside(msg, code)


# ---------------- text ----------------
def strip_comments(text) -> str:
    """A # starts a comment unless #b or #x follows (a literal); so does //."""
    lines = []
    for line in re.split(r"\r?\n", "" if text is None else str(text)):
        s, i = "", 0
        while i < len(line):
            ch = line[i]
            if ch == "#":
                if line[i + 1:i + 2].lower() in ("b", "x"):
                    s += ch
                    i += 1
                    continue
                break
            if ch == "/" and line[i + 1:i + 2] == "/":
                break
            s += ch
            i += 1
        lines.append(s)
    return "\n".join(lines)


_TOKEN = re.compile(
    r"\s+|(\{\s*(?:#x[0-9a-fA-F]+|#b[01]+|\d+)\s*\})|(\b[io]\d+\s*\[[^\]]*\])"
    r"|(:\s*(?:bv\s*\[\s*\d+\s*\]|bv\b|sbf\b|tau\b|bool\b))|(\(\s*bv\s*\[\s*\d+\s*\]\s*\))"
    r"|(<->|->|<-|&&|\|\||\^\^|!<=|!>=|!<|!>|!=|<=|>=|<<|>>|!&|!\^|!\||[?:()!=<>'&^|%*/+\-.,])"
    r"|(\b\d+\b)|(\b[A-Za-z_]\w*\b)|([\s\S])", re.ASCII)
_KINDS = (None, "const", "stream", "type", "cast", "op", "num", "name", "bad")


def _tokenize(text: str) -> list:
    toks = []
    for m in _TOKEN.finditer(text):
        k = next((i for i in range(1, len(_KINDS)) if m.group(i) is not None), 0)
        if not k:
            continue  # white space
        if _KINDS[k] == "bad":
            _out(f"the character “{m.group(0)}”")
        toks.append((_KINDS[k], m.group(0)))
    return toks


# ---------------- tree (precedences of the tau-lang README) ----------------
_CMP = {"=", "!=", "<", "<=", ">", ">=", "!<", "!<=", "!>", "!>="}
_LEVELS = (("<<", ">>"), ("-", "+"), ("%", "*", "/"), ("!|",), ("!^",), ("!&",), ("|",), ("^",), ("&",))


def _node(kind: str, **o) -> dict:
    n = {"kind": kind, "kids": []}
    n.update(o)
    return n


def _parse_tokens(toks: list) -> dict:
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else ("end", "")

    def eat(val=None, kind=None):
        t = peek()
        if (val is not None and t[1] != val) or (kind is not None and t[0] != kind):
            _out(f"“{val or kind}” expected, found “{t[1] or 'the end'}”")
        pos[0] += 1
        return t

    def wff():
        c = imp()
        if peek()[1] == "?":
            eat("?")
            a = wff()
            eat(":")
            b = wff()
            return _node("ite", kids=[c, a, b])
        return c

    def imp():
        left = limp()
        if peek()[1] == "->":
            eat("->")
            return _node("imp", kids=[left, imp()])
        return left

    def limp():
        left = iff()
        while peek()[1] == "<-":
            eat("<-")
            right = iff()
            left = _node("imp", kids=[right, left])
        return left

    def binary(sub, sym, kind):
        def f():
            left = sub()
            while peek()[1] == sym:
                eat(sym)
                left = _node(kind, kids=[left, sub()])
            return left
        return f

    def lnot():
        if peek()[0] == "op" and peek()[1] == "!":
            eat("!")
            return _node("not", kids=[lnot()])
        return atom()

    land = binary(lnot, "&&", "and")
    lxor = binary(land, "^^", "xor")
    lor = binary(lxor, "||", "or")
    iff = binary(lor, "<->", "iff")

    def atom():
        t = peek()
        if t[0] == "name" and t[1] in ("T", "F"):
            eat()
            return _node("bool", value=t[1] == "T")
        if t[0] == "name" and t[1] in ("ex", "all", "always", "sometimes", "G"):
            _out(f"“{t[1]}” inside the rule", "temporal")
        save = pos[0]
        try:  # a comparison of two values …
            left = term()
            op = peek()
            if op[0] == "op" and op[1] in _CMP:
                eat()
                right = term()
                if peek()[1] in _CMP:
                    _out("two comparisons in a row")
                return _node("cmp", op=op[1], kids=[left, right])
            _out("a value without a comparison")
        except Outside:
            pos[0] = save
            if peek()[1] != "(":
                raise
        eat("(")  # … or a formula in parentheses
        inner = wff()
        eat(")")
        return inner

    def term(level=0):
        if level == len(_LEVELS):
            return postfix()
        left = term(level + 1)
        while peek()[0] == "op" and peek()[1] in _LEVELS[level]:
            op = eat()[1]
            left = _node("binop", op=op, kids=[left, term(level + 1)])
        return left

    def postfix():
        n = prefix()
        while peek()[1] == "'":
            eat("'")
            n = _node("unop", op="'", kids=[n])
        return n

    def prefix():
        t = peek()
        if t[0] == "cast":
            eat()
            return _node("cast", width=int(re.search(r"\d+", t[1]).group(0)), kids=[postfix()])
        return typed(primary())

    def typed(n):
        if peek()[0] == "type":
            ty = re.sub(r"\s+", "", eat()[1])[1:]
            m = re.fullmatch(r"bv\[(\d+)\]", ty)
            if m:
                n["width"] = int(m.group(1))
            elif ty == "bv":
                n["width"] = 16  # a bare `bv` is 16 bits wide
            else:
                n["other"] = ty
        return n

    def primary():
        k, v = peek()
        if k == "stream":
            eat()
            name = re.search(r"[io]\d+", v).group(0)
            at = re.sub(r"\s+", "", re.search(r"\[(.*)\]", v).group(1))
            if at != "t":
                _out(f"{name} is read at step [{at}], not [t]", "temporal")
            return _node("stream", name=name)
        if k == "const":
            eat()
            b = re.sub(r"[{}\s]", "", v)
            value = int(b[2:], 16) if b.startswith("#x") else int(b[2:], 2) if b.startswith("#b") else int(b)
            return _node("const", value=value)
        if k == "num":
            eat()
            if v not in ("0", "1"):
                _out(f"the bare number {v}")
            return _node("num", value=int(v))  # 0 and 1 are the bottom and the top of the type
        if v == "(":
            eat("(")
            inner = term()
            eat(")")
            return _node("paren", kids=[inner])
        if k == "name" and v in ("min", "max"):
            eat()
            eat("(")
            a = term()
            eat(",")
            b = term()
            eat(")")
            return _node("binop", op=v, kids=[a, b])
        _out(f"the name “{v}”" if k == "name" else f"“{v or 'the end'}” where a value belongs")

    tree = wff()
    if peek()[0] != "end":
        _out(f"text after the rule: “{peek()[1]}”")
    return tree


def parse(text) -> dict:
    body = strip_comments(text).strip()
    m = re.match(r"always\b", body)
    if not m:
        _out("a rule starts with “always”")
    toks = _tokenize(body[m.end():])
    while toks and toks[-1][1] == ".":
        toks.pop()
    if not toks:
        _out("the rule is empty")
    return _parse_tokens(toks)


# ---------------- widths ----------------
DEFAULT_WIDTH = {"i1": 24, "i2": 24, "i3": 384, "i4": 384, "i5": 64, "i12": 384, "o5": 24, "o8": 24, "o9": 24}


def _walk(n: dict):
    yield n
    for k in n["kids"]:
        yield from _walk(k)


def _infer(n: dict, w: dict):
    kind = n["kind"]
    if kind == "stream":
        return w.get(n["name"])
    if kind in ("const", "num", "cast"):
        return n.get("width")
    if kind in ("paren", "unop"):
        return _infer(n["kids"][0], w)
    if kind == "binop":
        a, b = _infer(n["kids"][0], w), _infer(n["kids"][1], w)
        if a is not None and b is not None and a != b:
            _out(f"the two sides of {n['op']} have widths {a} and {b}")
        return a if a is not None else b
    return None


def _widths(tree: dict) -> dict:
    w: dict = {}
    for n in _walk(tree):
        if n["kind"] == "stream":
            if n.get("other"):
                _out(f"{n['name']} is typed {n['other']}, not as a bit-vector")
            if n.get("width") is not None:
                if w.get(n["name"]) is not None and w[n["name"]] != n["width"]:
                    _out(f"{n['name']} is typed with two widths ({w[n['name']]} and {n['width']})")
                w[n["name"]] = n["width"]
    changed = True
    while changed:  # a stream left untyped takes the width of the other side of its comparison
        changed = False
        for n in _walk(tree):
            if n["kind"] != "cmp":
                continue
            a, b = _infer(n["kids"][0], w), _infer(n["kids"][1], w)
            if a is not None and b is not None and a != b:
                _out(f"a comparison of widths {a} and {b}")
            x = a if a is not None else b
            if x is None:
                continue
            for side in n["kids"]:
                for s in _walk(side):
                    if s["kind"] == "cast":
                        break
                    if s["kind"] == "stream" and w.get(s["name"]) is None:
                        w[s["name"]] = x
                        changed = True
    for n in _walk(tree):
        if n["kind"] == "stream" and w.get(n["name"]) is None:
            if n["name"] not in DEFAULT_WIDTH:
                _out(f"{n['name']} has no width anywhere in the rule")
            w[n["name"]] = DEFAULT_WIDTH[n["name"]]
    return w


# ---------------- evaluation ----------------
def _mask(w: int) -> int:
    return (1 << w) - 1


def _op(op: str, m: int, bw: int):
    return {
        "&": lambda a, b: a & b, "|": lambda a, b: a | b, "^": lambda a, b: a ^ b,
        "!&": lambda a, b: ~(a & b) & m, "!|": lambda a, b: ~(a | b) & m, "!^": lambda a, b: ~(a ^ b) & m,
        "+": lambda a, b: (a + b) & m, "-": lambda a, b: (a - b) & m, "*": lambda a, b: (a * b) & m,
        "/": lambda a, b: m if b == 0 else a // b,  # x / 0 = all ones, as the engine answers
        "%": lambda a, b: a if b == 0 else a % b,  # x % 0 = x
        "<<": lambda a, b: 0 if b >= bw else (a << b) & m, ">>": lambda a, b: 0 if b >= bw else a >> b,
        "min": lambda a, b: a if a <= b else b, "max": lambda a, b: a if a >= b else b,
    }[op]


def _term(n: dict, w: dict, want=None):
    """(function env → value, width)"""
    kind = n["kind"]
    if kind == "paren":
        return _term(n["kids"][0], w, want)
    if kind == "stream":
        name = n["name"]
        return (lambda env: env[name]), w[name]
    if kind == "const":
        width = n.get("width") if n.get("width") is not None else want
        if width is None:
            _out("a value without a width")
        if n["value"] > _mask(width):
            _out(f"{n['value']} does not fit {width} bits")
        v = n["value"]
        return (lambda env: v), width
    if kind == "num":
        width = n.get("width") if n.get("width") is not None else want
        if width is None:
            _out(f"a bare {n['value']} without a width")
        v = 0 if n["value"] == 0 else _mask(width)
        return (lambda env: v), width
    if kind == "cast":
        f, aw = _term(n["kids"][0], w)
        width = n["width"]
        m = _mask(width)
        return (f, aw) if width == aw else ((lambda env: f(env) & m), width)
    if kind == "unop":
        f, aw = _term(n["kids"][0], w, want)
        m = _mask(aw)
        return (lambda env: ~f(env) & m), aw
    if kind == "binop":
        width = _infer(n["kids"][0], w)
        if width is None:
            width = _infer(n["kids"][1], w)
        if width is None:
            width = want
        fa, wa = _term(n["kids"][0], w, width)
        fb, wb = _term(n["kids"][1], w, width)
        if wa != wb:
            _out(f"the two sides of {n['op']} have different widths")
        op = _op(n["op"], _mask(wa), wa)
        return (lambda env: op(fa(env), fb(env))), wa
    _out(f"the part “{kind}”")


_REL = {"=": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def _formula(n: dict, w: dict):
    kind = n["kind"]
    if kind == "bool":
        v = n["value"]
        return lambda env: v
    if kind == "cmp":
        width = _infer(n["kids"][0], w)
        if width is None:
            width = _infer(n["kids"][1], w)
        if width is None:
            _out("a comparison with no width on either side")
        fa, wa = _term(n["kids"][0], w, width)
        fb, wb = _term(n["kids"][1], w, width)
        if wa != wb:
            _out("a comparison of two widths")
        op = n["op"]
        neg = op[0] == "!" and op != "!="
        rel = _REL[op[1:] if neg else op]
        if neg:
            return lambda env: not rel(fa(env), fb(env))
        return lambda env: rel(fa(env), fb(env))
    if kind == "not":
        a = _formula(n["kids"][0], w)
        return lambda env: not a(env)
    if kind in ("and", "or", "xor", "iff", "imp"):
        a, b = _formula(n["kids"][0], w), _formula(n["kids"][1], w)
        return {"and": lambda env: a(env) and b(env), "or": lambda env: a(env) or b(env),
                "xor": lambda env: a(env) != b(env), "iff": lambda env: a(env) == b(env),
                "imp": lambda env: (not a(env)) or b(env)}[kind]
    if kind == "ite":
        c, a, b = (_formula(k, w) for k in n["kids"])
        return lambda env: a(env) if c(env) else b(env)
    _out(f"the part “{kind}”")


def _num(s: str) -> int:
    return int(s[1:])


def compile_rule(text, out_name: str | None = None) -> dict:
    """One rule, compiled: its streams, their widths and f(env) → True/False."""
    tree = parse(text) if isinstance(text, str) else text
    w = _widths(tree)
    f = _formula(tree, w)
    names = list(dict.fromkeys(n["name"] for n in _walk(tree) if n["kind"] == "stream"))
    outs = sorted((x for x in names if x[0] == "o"), key=_num)
    ins = sorted((x for x in names if x[0] == "i"), key=_num)
    o = out_name or "o5"
    return {"tree": tree, "w": w, "f": f, "ins": ins, "outs": outs, "out": o, "writes": o in outs,
            "others": [x for x in outs if x != o]}


def _only(rule: dict) -> dict:
    if rule["others"]:
        _out(f"it also writes {', '.join(rule['others'])}", "outputs")
    return rule


def _side_of(n: dict):
    """How a side of a comparison relates to the inputs: a bare stream, a fixed value, or a computation with one."""
    k = n
    while k["kind"] == "paren":
        k = k["kids"][0]
    if k["kind"] == "stream":
        return ("var", k["name"])
    for s in _walk(n):
        if s["kind"] == "stream":
            return ("expr", s["name"])
    return ("fixed", None)


def _pieces(values: list, width: int) -> list:
    """The pieces of 0..max cut at the given values: each value alone, and the stretches between them, as (lo, hi)."""
    top = _mask(width)
    pts = sorted({v for v in values if 0 <= v <= top})
    r, lo = [], 0
    for p in pts:
        if p > lo:
            r.append((lo, p - 1))
        r.append((p, p))
        lo = p + 1
    if lo <= top:
        r.append((lo, top))
    return r


def _cut(rules: list, want_out: str) -> dict:
    """The classes of streams compared with each other, the values each class is compared with, and stand-in values
    per piece (as many as the class has members, so any order among them can be built)."""
    parent: dict = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    widths, fixed = {}, {}
    for r in rules:
        for n in _walk(r["tree"]):
            if n["kind"] == "stream":
                name = n["name"]
                parent.setdefault(name, name)
                if name in widths and widths[name] != r["w"][name]:
                    _out(f"{name} has two widths")
                widths[name] = r["w"][name]
    for r in rules:
        for n in _walk(r["tree"]):
            if n["kind"] != "cmp":
                continue
            a, b = _side_of(n["kids"][0]), _side_of(n["kids"][1])
            e = a if a[0] == "expr" else b if b[0] == "expr" else None
            if e:
                _out(f"it computes with {e[1]}", "computes")
            wd = _infer(n["kids"][0], r["w"])
            if wd is None:
                wd = _infer(n["kids"][1], r["w"])
            if a[0] == "var" and b[0] == "var":
                x, y = find(a[1]), find(b[1])
                if x != y:
                    parent[x] = y
            elif a[0] == "var" and b[0] == "fixed":
                fixed.setdefault(a[1], []).append(_term(n["kids"][1], r["w"], wd)[0]({}))
            elif b[0] == "var" and a[0] == "fixed":
                fixed.setdefault(b[1], []).append(_term(n["kids"][0], r["w"], wd)[0]({}))
    classes: dict = {}
    for s in list(parent):
        classes.setdefault(find(s), []).append(s)
    stand, cuts, class_of = {}, {}, {}
    for members in classes.values():
        ps = _pieces([v for m in members for v in fixed.get(m, [])], widths[members[0]])
        k = max(len(members), 2 if want_out in members else 1)
        reps = []
        for lo, hi in ps:
            j = 0
            while j < k and lo + j <= hi:
                reps.append(lo + j)
                j += 1
        for m in members:
            stand[m], cuts[m], class_of[m] = reps, ps, sorted(members)
    return {"W": widths, "stand": stand, "cuts": cuts, "class_of": class_of}


def _decide(allowed: list) -> str:
    if not allowed:
        return "none"
    zero, other = any(v == 0 for v in allowed), any(v != 0 for v in allowed)
    return ("open" if other else "block") if zero else "pass"


OUTCOME = {"pass": "pass", "block": "block", "open": "block", "none": "fail"}  # what the engine does: open reads as 0
LIMIT = 40000


def piece_of(ps: list, v: int) -> int:
    for i, (lo, hi) in enumerate(ps):
        if lo <= v <= hi:
            return i
    return -1


def _enumerate(rules: list, o: str):
    """Every kind of case the rules can tell apart, with each rule's allowed answers."""
    c = _cut(rules, o)
    ins = sorted({x for r in rules for x in r["ins"]}, key=_num)
    size = 1
    for x in ins:
        size *= len(c["stand"][x])
    if size > LIMIT:
        _out(f"it tells {size} kinds of transfer apart", "big")
    out_reps = c["stand"].get(o) or [0, 1]
    cells, env = [], {}

    def rec(j):
        if j == len(ins):
            per = []
            for r in rules:
                allowed = []
                for y in out_reps:
                    env[o] = y
                    if r["f"](env):
                        allowed.append(y)
                env.pop(o, None)
                per.append({"allowed": allowed, "d": _decide(allowed) if r["writes"] else "silent"})
            cells.append({"v": {x: env[x] for x in ins}, "per": per})
            return
        for y in c["stand"][ins[j]]:
            env[ins[j]] = y
            rec(j + 1)
        env.pop(ins[j], None)

    rec(0)
    return c, ins, cells


def _read_inputs(ins: list, cells: list, key) -> list:
    """Inputs whose value changes the key: two cases equal in everything else, keyed differently."""
    read = []
    for x in ins:
        seen, hit = {}, False
        for cell in cells:
            k = ",".join(str(cell["v"][y]) for y in ins if y != x)
            d = key(cell)
            if k not in seen:
                seen[k] = d
            elif seen[k] != d:
                hit = True
                break
        if hit:
            read.append(x)
    return read


def _shared(c: dict, ins: list) -> list:
    return [x for x in ins if len([y for y in c["class_of"][x] if y[0] == "i"]) > 1]


def _inputs(c: dict, ins: list) -> list:
    sh = _shared(c, ins)
    return [{"name": x, "width": c["W"][x], "pieces": c["cuts"][x], "shared": x in sh} for x in ins]


def read(text, out: str = "o5") -> dict:
    """The reading of one rule: every kind of case with the answer the rule gives it (d: pass, block, open, none)."""
    try:
        rule = compile_rule(text, out)
        if not rule["writes"]:
            return {"ok": False, "code": "noout", "why": f"the rule sets no {out}"}
        _only(rule)
        c, ins, cells = _enumerate([rule], out)
    except Outside as e:
        return {"ok": False, "code": e.code, "why": str(e)}
    for cell in cells:
        cell["allowed"], cell["d"] = cell["per"][0]["allowed"], cell["per"][0]["d"]
        del cell["per"]
    for cell in cells:
        cell["value"] = value_of(cell["allowed"], c["cuts"][out])
    by_value = (STREAMS.get(out) or {}).get("kind") == "value"   # a fee: the inputs that change its amount
    return {"ok": True, "out": out, "inputs": _inputs(c, ins), "cells": cells,
            "read": _read_inputs(ins, cells, (lambda cell: str(cell["value"])) if by_value else (lambda cell: cell["d"])),
            "follows": [y for y in c["class_of"].get(out, []) if y[0] == "i"]}


def _to_int(v) -> int:
    s = str(v).strip()
    if s[:2].lower() == "#x":
        return int(s[2:], 16)
    if s[:2].lower() == "#b":
        return int(s[2:], 2)
    return int(s, 0) if s[:2].lower() in ("0x", "0b", "0o") else int(s or 0)


def answer(text, inputs: dict | None = None, out: str = "o5") -> dict:
    """The answers a rule allows for one concrete case, and the value the engine gives: exact for any rule whose
    outputs stand bare in its comparisons (inputs may be computed with); other outputs only need some value.
    Inputs nobody feeds read 0. {d, outcome, allowed, value}"""
    rule = compile_rule(text, out)
    inputs = inputs or {}
    env = {x: _to_int(inputs[x] if inputs.get(x) is not None else 0) & _mask(rule["w"][x]) for x in rule["ins"]}
    vals: dict = {y: [] for y in rule["outs"]}

    def outs_in(side):
        return [k["name"] for k in _walk(side) if k["kind"] == "stream" and k["name"][0] == "o"]

    for n in _walk(rule["tree"]):
        if n["kind"] != "cmp":
            continue
        a, b = _side_of(n["kids"][0]), _side_of(n["kids"][1])
        oa, ob = outs_in(n["kids"][0]), outs_in(n["kids"][1])
        if (oa and a[0] != "var") or (ob and b[0] != "var") or (oa and ob):
            _out(f"it computes with {(oa + ob)[0]}", "computes")
        wd = _infer(n["kids"][0], rule["w"])
        if wd is None:
            wd = _infer(n["kids"][1], rule["w"])
        if oa:
            vals[a[1]].append(_term(n["kids"][1], rule["w"], wd)[0](env))
        if ob:
            vals[b[1]].append(_term(n["kids"][0], rule["w"], wd)[0](env))
    cuts_of = {y: _pieces(vals[y], rule["w"][y]) for y in rule["outs"]}
    reps = {y: [lo + j for lo, hi in cuts_of[y] for j in range(2) if lo + j <= hi] for y in rule["outs"]}
    others = rule["others"]

    def holds(j=0):  # some value for every other output makes the rule true
        if j == len(others):
            return rule["f"](env)
        for v in reps[others[j]]:
            env[others[j]] = v
            if holds(j + 1):
                return True
        return False

    allowed = []
    if rule["writes"]:
        for v in reps[out]:
            env[out] = v
            if holds():
                allowed.append(v)
    d = _decide(allowed) if rule["writes"] else "silent"
    value = None  # 0 when 0 is allowed (an open answer reads as 0), else the one value allowed
    if any(v == 0 for v in allowed):
        value = 0
    elif len(allowed) == 1:
        lo, hi = cuts_of[out][piece_of(cuts_of[out], allowed[0])]
        if lo == hi:
            value = allowed[0]
    return {"d": d, "outcome": "pass" if d == "silent" else OUTCOME[d], "allowed": allowed, "value": value}


def value_of(allowed: list, cuts: list):
    """The value an output takes in one case: the one value the rule allows, "open" when it allows more than one
    (for o5 to o7 the engine then answers 0; for a fee nobody measured it), "none" when it allows none."""
    if not allowed:
        return "none"
    if len(allowed) == 1:
        lo, hi = cuts[piece_of(cuts, allowed[0])]
        if lo == hi:
            return allowed[0]
    return "open"


def cell_at(reading: dict, inputs: dict | None):
    """The case of a reading that one concrete case falls in (inputs by name, missing ones read 0); None when the
    reading has inputs compared with each other (then a piece does not say which case it is)."""
    if not reading or not reading.get("ok") or any(x["shared"] for x in reading["inputs"]):
        return None
    inputs = inputs or {}
    at = {x["name"]: _to_int(inputs[x["name"]] if inputs.get(x["name"]) is not None else 0) & _mask(x["width"])
          for x in reading["inputs"]}
    for cell in reading["cells"]:
        if all(piece_of(x["pieces"], cell["v"][x["name"]]) == piece_of(x["pieces"], at[x["name"]]) for x in reading["inputs"]):
            return cell
    return None


def value_at(reading: dict, inputs: dict | None):
    """The value of the read output in one concrete case (a number, "open" or "none"), or None."""
    if not reading or reading.get("follows"):
        return None
    cell = cell_at(reading, inputs)
    return cell["value"] if cell else None


def value_edges(reading: dict, x_name: str) -> list:
    """Where one step in input x_name changes the value (all else equal): [{below, above, was, now, rest}]."""
    if not reading or not reading.get("ok") or reading.get("follows"):
        return []
    x = next((i for i in reading["inputs"] if i["name"] == x_name), None)
    if not x or x["shared"]:
        return []
    others = [y for y in reading["inputs"] if y is not x]
    rows: dict = {}
    for cell in reading["cells"]:
        rows.setdefault(",".join(str(cell["v"][y["name"]]) for y in others), []).append(cell)
    res, seen = [], set()
    for row in rows.values():
        row.sort(key=lambda cell: cell["v"][x_name])
        for a, b in zip(row, row[1:]):
            pa, pb = x["pieces"][piece_of(x["pieces"], a["v"][x_name])], x["pieces"][piece_of(x["pieces"], b["v"][x_name])]
            if str(a["value"]) == str(b["value"]) or pa[1] + 1 != pb[0]:
                continue
            k = (pa[1], str(a["value"]), str(b["value"]))
            if k in seen:
                continue
            seen.add(k)
            res.append({"below": pa[1], "above": pb[0], "was": a["value"], "now": b["value"],
                        "rest": {y["name"]: a["v"][y["name"]] for y in others}})
    return res


# ================ two rules side by side: where their answers differ ================
def diff(before, after, out: str = "o5") -> dict:
    try:
        a, b = _only(compile_rule(before, out)), _only(compile_rule(after, out))
        c, ins, cells = _enumerate([a, b], out)
    except Outside as e:
        return {"ok": False, "code": e.code, "why": str(e)}
    for cell in cells:
        cell["was"], cell["now"] = cell["per"][0]["d"], cell["per"][1]["d"]
        del cell["per"]

    def say(d):
        return "pass" if d == "silent" else OUTCOME[d]  # a rule that sets nothing lets a case through

    changed = [cell for cell in cells if say(cell["was"]) != say(cell["now"])]
    return {"ok": True, "out": out, "inputs": _inputs(c, ins), "cells": cells, "changed": changed, "same": not changed}


def value_diff(before, after, out: str) -> dict:
    """diff() for an output whose answer is an amount: the cases where the value changes."""
    try:
        a, b = _only(compile_rule(before, out)), _only(compile_rule(after, out))
        c, ins, cells = _enumerate([a, b], out)
    except Outside as e:
        return {"ok": False, "code": e.code, "why": str(e)}
    follows = [y for y in c["class_of"].get(out, []) if y[0] == "i"]
    if follows:
        return {"ok": False, "code": "computes", "why": f"{out} follows {', '.join(follows)}"}
    cuts = c["cuts"][out]
    for cell in cells:
        cell["was"] = value_of(cell["per"][0]["allowed"], cuts) if a["writes"] else "open"
        cell["now"] = value_of(cell["per"][1]["allowed"], cuts) if b["writes"] else "open"
        del cell["per"]
    changed = [cell for cell in cells if str(cell["was"]) != str(cell["now"])]
    return {"ok": True, "out": out, "inputs": _inputs(c, ins), "cells": cells, "changed": changed, "same": not changed}


# ================ a change to the network's rules: what it decides differently ================
STREAMS = {
    "o5": {"kind": "yesno", "topic": "Personal rule", "every": "every transfer", "yes": "Newly passing", "no": "Newly blocked"},
    "o6": {"kind": "yesno", "topic": "Which blocks count as valid", "every": "every block", "yes": "Newly accepted", "no": "Newly rejected"},
    "o7": {"kind": "yesno", "topic": "Who may make blocks", "every": "every proposer", "yes": "Newly allowed to make blocks",
           "no": "Newly barred from making blocks"},
    "o8": {"kind": "value", "topic": "Custom fee", "every": "every transfer"},
    "o9": {"kind": "value", "topic": "Base fee per transaction", "every": "every transfer"},
}


def _norm(s) -> str:
    return re.sub(r"\s+", "", str(s))


def _body_of(text) -> str:
    t = strip_comments(text)
    m = re.search(r"\balways\s*\(", t)
    if not m:
        return re.sub(r"\.\s*$", "", t.strip())
    depth, start = 0, m.end() - 1
    for i in range(start, len(t)):
        if t[i] == "(":
            depth += 1
        elif t[i] == ")":
            depth -= 1
            if depth == 0:
                return t[start + 1:i]
    return t[start + 1:]


def _split_and(b: str) -> list:
    parts, depth, cur, i = [], 0, "", 0
    while i < len(b):
        ch = b[i]
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if depth == 0 and b.startswith("&&", i):
            parts.append(cur)
            cur, i = "", i + 2
            continue
        cur += ch
        i += 1
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def clauses_of(text) -> dict:
    """Output stream → the part of the rule that defines it (as assets/rulediff.js and explain.py split it)."""
    res = {}
    for part in _split_and(_body_of(text)):
        for s in dict.fromkeys(re.findall(r"\bo\d+(?=\[t\])", part)):
            res[s] = part
    return res


def _where_of(r: dict, sub: list) -> dict:
    """The cases of one kind of change: every case, one box of input ranges ("all"), a few boxes ("any"; two boxes
    that differ in one input only become one), or "some" when inputs compared with each other decide it."""
    mem = {id(cell) for cell in sub}
    names = [x["name"] for x in r["inputs"]]
    read_ = _read_inputs(names, r["cells"], lambda cell: id(cell) in mem)
    if not read_:
        return {"every": True}
    xs = [x for x in r["inputs"] if x["name"] in read_]
    if any(x["shared"] for x in xs):
        return {"some": True, "inputs": [x["name"] for x in xs]}

    def at(x, cell):
        return piece_of(x["pieces"], cell["v"][x["name"]])

    boxes = [[[int(i)] for i in k.split(",")] for k in dict.fromkeys(",".join(str(at(x, cell)) for x in xs) for cell in sub)]
    again = True
    while again:
        again = False
        for j in range(len(xs)):
            by: dict = {}
            for b in boxes:
                k = ",".join("" if i == j else ".".join(map(str, g)) for i, g in enumerate(b))
                if k not in by:
                    by[k] = b
                    continue
                m = by[k]
                m[j] = sorted(set(m[j]) | set(b[j]))
                again = True
            boxes = list(by.values())

    def as_conds(b):
        return [{"input": xs[j]["name"], "width": xs[j]["width"], "pieces": xs[j]["pieces"], "group": g} for j, g in enumerate(b)]

    if len(boxes) == 1:
        return {"all": as_conds(boxes[0])}
    return {"any": [as_conds(b) for b in boxes[:4]], "more": max(0, len(boxes) - 4)}


def meaning(spec: dict, revisions: list) -> dict:
    """For each output the revisions redefine: does it decide differently from the rules in force (spec: output →
    the part that defines it), and where. {ok, same, streams: [{stream, kind, ok, code?, same, changes}]}"""
    nxt: dict = {}
    for r in revisions or []:
        nxt.update(clauses_of(r))
    streams = []
    for s in sorted(nxt, key=_num):
        was, now, info = (spec or {}).get(s), nxt[s], STREAMS.get(s)
        if was is not None and _norm(was) == _norm(now):
            continue
        kind = info["kind"] if info else "other"
        if was is None or not info:
            streams.append({"stream": s, "kind": kind, "ok": False, "code": "new" if was is None else "other"})
            continue
        before, after = f"always ( {was} ).", f"always ( {now} )."
        r = diff(before, after, s) if kind == "yesno" else value_diff(before, after, s)
        if not r["ok"]:
            streams.append({"stream": s, "kind": kind, "ok": False, "code": r["code"], "why": r["why"]})
            continue

        def say(v, kind=kind):
            return ("pass" if v == "silent" else OUTCOME[v]) if kind == "yesno" else str(v)

        by: dict = {}
        for cell in r["changed"]:
            was_, now_ = say(cell["was"]), say(cell["now"])
            # a yes/no output gets one line per head: "No answer fits any more", whatever it answered before
            k = (was_ + ">" + now_ if kind != "yesno" else "fail" if now_ == "fail" else "again" if was_ == "fail" else now_)
            g = by.setdefault(k, {"was": was_, "now": now_, "cells": []})
            if g["was"] != was_:
                g["was"] = None
            if g["now"] != now_:
                g["now"] = None
            g["cells"].append(cell)
        changes = [{"was": g["was"], "now": g["now"], "where": _where_of(r, g["cells"])} for g in by.values()]
        streams.append({"stream": s, "kind": kind, "ok": True, "same": r["same"], "changes": changes})
    return {"ok": all(x["ok"] for x in streams), "same": all(x["ok"] and x["same"] for x in streams), "streams": streams}


# ================ words ================
LABEL = {
    "i1": "amount", "i2": "balance", "i3": "sender", "i4": "receiver", "i5": "block time", "i12": "sender",
    "i6": "block height", "i7": "block time", "i8": "proposer", "i9": "previous block", "i10": "signature check", "i11": "claims",
    "i13": "proposer key", "i14": "proposer balance", "i15": "eligibility mode",
}


def label(x: str) -> str:
    return LABEL.get(x, x)


def is_time(x: str) -> bool:
    return x in ("i5", "i7")


def is_addr(x: str, width: int) -> bool:
    return not is_time(x) and width == 384


def fmt_num(v) -> str:
    return f"{int(v):,}"


def fmt_time(v) -> str:
    s = int(v)
    if not 0 <= s <= 253402300799:  # up to the year 9999
        return fmt_num(v)
    d = datetime.fromtimestamp(s, tz=timezone.utc)
    day, hms = f"{d.year:04d}-{d.month:02d}-{d.day:02d}", f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"
    if hms == "00:00:00":
        return day
    return f"{day} {hms[:5] if hms[6:] == '00' else hms} UTC"


def hex_of(v, width: int) -> str:
    return format(int(v), "x").rjust(-(-width // 4), "0")


def fmt_addr(v, width: int, names: dict | None = None) -> str:
    h = hex_of(v, width)
    if names and names.get(h):
        return names[h]
    return h[:6] + "…" + h[-4:] if len(h) > 12 else "#x" + h


def stretches(ps: list, group: list) -> list:
    """Adjacent pieces of a group joined into stretches."""
    res = []
    for i in sorted(group, key=lambda i: ps[i][0]):
        if res and res[-1][1] + 1 == ps[i][0]:
            res[-1] = (res[-1][0], ps[i][1])
        else:
            res.append(ps[i])
    return res


def stretch_words(x: str, width: int, s: tuple, names: dict | None = None, whole: bool = False) -> str:
    """One stretch of one input in words, without the input's name: "up to 1,000", "before 2027-01-01"."""
    top = _mask(width)
    lo, hi = s
    if is_addr(x, width):
        if lo == hi:
            return fmt_addr(lo, width, names)
        return "anyone" if whole else "anyone else"
    if is_time(x):
        if lo == 0 and hi == top:
            return "any time"
        if lo == hi:
            return f"at exactly {fmt_time(lo)}"
        if lo == 0:
            return f"before {fmt_time(hi + 1)}"
        if hi == top:
            return f"on or after {fmt_time(lo)}"
        return f"from {fmt_time(lo)} to before {fmt_time(hi + 1)}"
    if lo == 0 and hi == top:
        return "any value"
    if lo == hi:
        return f"exactly {fmt_num(lo)}"
    if lo == 0:
        return f"up to {fmt_num(hi)}"
    if hi == top:
        return f"{fmt_num(lo)} or more"
    return f"{fmt_num(lo)} to {fmt_num(hi)}"


def _cond_parts(c: dict, names: dict | None = None):
    """One condition in words, as parts: ["block height", "exactly 0"], ["proposer", "other than a1fe40…7d2b"],
    ["signature check failed"]; None = any value."""
    x, width, ps, g = c["input"], c["width"], c["pieces"], c["group"]
    in_g = set(g)
    if x == "i10":  # the host's signature check: 1 when it verified the block's signature, else 0
        zero, other = any(ps[i][0] == 0 for i in g), any(ps[i][1] > 0 for i in g)
        return None if zero and other else ["signature check failed" if zero else "signature check passed"]
    if is_addr(x, width):
        def point(i):
            return ps[i][0] == ps[i][1]
        if all(i in in_g for i in range(len(ps)) if not point(i)):
            nots = [fmt_addr(ps[i][0], width, names) for i in range(len(ps)) if point(i) and i not in in_g]
            return [label(x), "other than " + ", ".join(nots)] if nots else None
        if all(point(i) for i in g):
            return [label(x), ", ".join(fmt_addr(ps[i][0], width, names) for i in g)]
    ss = stretches(ps, g)
    if len(ss) == 1 and ss[0][0] == 0 and ss[0][1] == _mask(width):
        return None
    res = [label(x)]
    for i, s in enumerate(ss):
        if i:
            res.append("or")
        res.append(stretch_words(x, width, s, names, False))
    return res


def meaning_lines(m: dict, names: dict | None = None) -> list:
    """meaning() in English, one line per change: {stream, topic, head, items, more}; see line_text()."""
    lines = []
    for s in m["streams"]:
        if not s["ok"]:
            continue
        info = STREAMS[s["stream"]]

        def fmt_v(v):
            return "left open" if v == "open" else "no answer" if v == "none" else f"{fmt_num(int(v))} AGRS"

        for ch in s["changes"]:
            if s["kind"] == "yesno":
                head = ("No answer fits any more" if ch["now"] == "fail" else "An answer fits again" if ch["was"] == "fail"
                        else info["yes"] if ch["now"] == "pass" else info["no"])
            else:
                head = f"{fmt_v(ch['was'])} → {fmt_v(ch['now'])}"
            w = ch["where"]

            def conds(lst):
                return [p for p in (_cond_parts(c, names) for c in lst) if p]

            if w.get("every"):
                items = [[[info["every"]]]]
            elif w.get("some"):
                ls = list(dict.fromkeys(label(x) for x in w["inputs"]))
                items = [[["some cases, depending on"] + [p for i, t in enumerate(ls) for p in (["and", t] if i else [t])]]]
            elif w.get("all"):
                items = [conds(w["all"])]
            else:
                items = [conds(lst) for lst in w["any"]]
            items = [it if it else [[info["every"]]] for it in items]
            lines.append({"stream": s["stream"], "topic": info["topic"], "head": head, "items": items, "more": w.get("more", 0)})
    return lines


def line_text(line: dict) -> str:
    """A line as plain text: "Newly rejected: block height exactly 0 and signature check passed"."""
    items = "; ".join(" and ".join(" ".join(c) for c in it) for it in line["items"])
    return f"{line['head']}: {items}" + (f"; and {line['more']} more" if line["more"] else "")
