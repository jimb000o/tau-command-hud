/* Rule facts: what a Tau rule answers, for every possible transfer. Used by the X-ray, the case builder and
   "what would pass" on /playground/, and by meaning(): what a change to the network's rules decides differently
   (the box on /proposals/ and /history/). The same reading is in infra/alerts/rulefacts.py (the Telegram posts) and
   its twin infra/relay/rulefacts.py; tests/meaning-cases.json holds the lines both must write.

   A rule is one `always ( … ).` unit. It speaks about the inputs of one transfer (i1 amount, i3 sender,
   i4 receiver, i5 block time, …) and one answer (o5 for a personal rule). How the engine turns the rule into
   an answer, as measured with tau-lang (tests/rulefacts-cases.json holds the runs this file is tested against):
     0 among the answers the rule allows  → the engine answers 0: blocked. That includes an answer the rule
                                            leaves open (0 and others allowed): an open answer reads as 0.
     only answers other than 0            → passes.
     no answer at all                     → the rule contradicts itself there, and the transfer fails.

   read() is exact inside this scope and says so when a rule is outside it: inputs are compared with fixed values
   or with each other (= != < <= > >= and their ! forms), and fixed values may be computed ({ 999 }:bv[24] + { 1 }:bv[24]).
   Each input is cut at the values the rule compares it with. All values of one piece make every comparison in the
   rule come out the same, so one value per piece stands for the whole piece, and trying every combination of
   pieces covers every possible transfer. A rule that computes with an input (i1 + i1 > …) is answered for single
   transfers (answer()), not read as a whole. No dependencies; runs in the browser and in Node. */
(function (root) {
  "use strict";

  class Outside extends Error { constructor(msg, code) { super(msg); this.code = code || "text"; } }
  const out = (msg, code) => { throw new Outside(msg, code); };

  /* ---------------- text ---------------- */
  function stripComments(text) {
    return String(text == null ? "" : text).split(/\r?\n/).map(line => {
      let s = "";
      for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === "#") { const n = (line[i + 1] || "").toLowerCase(); if (n === "b" || n === "x") { s += ch; continue; } break; }
        if (ch === "/" && line[i + 1] === "/") break;
        s += ch;
      }
      return s;
    }).join("\n");
  }

  const TOKEN = /\s+|(\{\s*(?:#x[0-9a-fA-F]+|#b[01]+|\d+)\s*\})|(\b[io]\d+\s*\[[^\]]*\])|(:\s*(?:bv\s*\[\s*\d+\s*\]|bv\b|sbf\b|tau\b|bool\b))|(\(\s*bv\s*\[\s*\d+\s*\]\s*\))|(<->|->|<-|&&|\|\||\^\^|!<=|!>=|!<|!>|!=|<=|>=|<<|>>|!&|!\^|!\||[?:()!=<>'&^|%*\/+\-.,])|(\b\d+\b)|(\b[A-Za-z_]\w*\b)|([\s\S])/g;
  const KINDS = [null, "const", "stream", "type", "cast", "op", "num", "name", "bad"];
  function tokenize(text) {
    const toks = [];
    TOKEN.lastIndex = 0;
    let m;
    while ((m = TOKEN.exec(text))) {
      let k = 0;
      for (let i = 1; i < KINDS.length; i++) if (m[i] !== undefined) { k = i; break; }
      if (!k) continue;                       // white space
      if (KINDS[k] === "bad") out(`the character “${m[0]}”`);
      toks.push([KINDS[k], m[0]]);
    }
    return toks;
  }

  /* ---------------- tree (precedences of the tau-lang README) ---------------- */
  const CMP = new Set(["=", "!=", "<", "<=", ">", ">=", "!<", "!<=", "!>", "!>="]);
  const LEVELS = [["<<", ">>"], ["-", "+"], ["%", "*", "/"], ["!|"], ["!^"], ["!&"], ["|"], ["^"], ["&"]];
  const node = (kind, o) => Object.assign({ kind, kids: [] }, o);

  function parseTokens(toks) {
    let i = 0;
    const peek = () => toks[i] || ["end", ""];
    const eat = (val, kind) => {
      const t = peek();
      if ((val != null && t[1] !== val) || (kind != null && t[0] !== kind)) out(`“${val || kind}” expected, found “${t[1] || "the end"}”`);
      i++; return t;
    };
    function wff() { const c = imp(); if (peek()[1] === "?") { eat("?"); const a = wff(); eat(":"); const b = wff(); return node("ite", { kids: [c, a, b] }); } return c; }
    function imp() { const l = limp(); if (peek()[1] === "->") { eat("->"); return node("imp", { kids: [l, imp()] }); } return l; }
    function limp() { let l = iff(); while (peek()[1] === "<-") { eat("<-"); const r = iff(); l = node("imp", { kids: [r, l] }); } return l; }
    function iff() { let l = lor(); while (peek()[1] === "<->") { eat("<->"); l = node("iff", { kids: [l, lor()] }); } return l; }
    function lor() { let l = lxor(); while (peek()[1] === "||") { eat("||"); l = node("or", { kids: [l, lxor()] }); } return l; }
    function lxor() { let l = land(); while (peek()[1] === "^^") { eat("^^"); l = node("xor", { kids: [l, land()] }); } return l; }
    function land() { let l = lnot(); while (peek()[1] === "&&") { eat("&&"); l = node("and", { kids: [l, lnot()] }); } return l; }
    function lnot() { if (peek()[0] === "op" && peek()[1] === "!") { eat("!"); return node("not", { kids: [lnot()] }); } return atom(); }
    function atom() {
      const t = peek();
      if (t[0] === "name" && (t[1] === "T" || t[1] === "F")) { eat(); return node("bool", { value: t[1] === "T" }); }
      if (t[0] === "name" && ["ex", "all", "always", "sometimes", "G"].includes(t[1])) out(`“${t[1]}” inside the rule`, "temporal");
      const save = i;
      try {                                   // a comparison of two values …
        const l = term(), op = peek();
        if (op[0] === "op" && CMP.has(op[1])) {
          eat(); const r = term();
          if (CMP.has(peek()[1])) out("two comparisons in a row");
          return node("cmp", { op: op[1], kids: [l, r] });
        }
        out("a value without a comparison");
      } catch (e) {
        if (!(e instanceof Outside)) throw e;
        i = save;
        if (peek()[1] !== "(") throw e;
      }
      eat("("); const inner = wff(); eat(")");   // … or a formula in parentheses
      return inner;
    }
    function term(level = 0) {
      if (level === LEVELS.length) return postfix();
      let l = term(level + 1);
      while (peek()[0] === "op" && LEVELS[level].includes(peek()[1])) { const op = eat()[1]; l = node("binop", { op, kids: [l, term(level + 1)] }); }
      return l;
    }
    function postfix() { let n = prefix(); while (peek()[1] === "'") { eat("'"); n = node("unop", { op: "'", kids: [n] }); } return n; }
    function prefix() {
      const t = peek();
      if (t[0] === "cast") { eat(); return node("cast", { width: +/\d+/.exec(t[1])[0], kids: [postfix()] }); }
      return typed(primary());
    }
    function typed(n) {
      if (peek()[0] === "type") {
        const ty = eat()[1].replace(/\s+/g, "").slice(1), m = /^bv\[(\d+)\]$/.exec(ty);
        if (m) n.width = +m[1]; else if (ty === "bv") n.width = 16; else n.other = ty;   // a bare `bv` is 16 bits wide
      }
      return n;
    }
    function primary() {
      const [k, v] = peek();
      if (k === "stream") {
        eat();
        const name = /[io]\d+/.exec(v)[0], at = /\[(.*)\]/.exec(v)[1].replace(/\s+/g, "");
        if (at !== "t") out(`${name} is read at step [${at}], not [t]`, "temporal");
        return node("stream", { name });
      }
      if (k === "const") {
        eat();
        const b = v.replace(/[{}\s]/g, "");
        return node("const", { value: b.startsWith("#x") ? BigInt("0x" + b.slice(2)) : b.startsWith("#b") ? BigInt("0b" + b.slice(2)) : BigInt(b) });
      }
      if (k === "num") {
        eat();
        if (v !== "0" && v !== "1") out(`the bare number ${v}`);
        return node("num", { value: BigInt(v) });       // 0 and 1 are the bottom and the top of the type
      }
      if (v === "(") { eat("("); const inner = term(); eat(")"); return node("paren", { kids: [inner] }); }
      if (k === "name" && (v === "min" || v === "max")) { eat(); eat("("); const a = term(); eat(","); const b = term(); eat(")"); return node("binop", { op: v, kids: [a, b] }); }
      out(k === "name" ? `the name “${v}”` : `“${v || "the end"}” where a value belongs`);
    }
    const tree = wff();
    if (peek()[0] !== "end") out(`text after the rule: “${peek()[1]}”`);
    return tree;
  }

  function parse(text) {
    const body = stripComments(text).trim();
    const m = /^always\b/.exec(body);
    if (!m) out("a rule starts with “always”");
    const toks = tokenize(body.slice(m[0].length));
    while (toks.length && toks[toks.length - 1][1] === ".") toks.pop();
    if (!toks.length) out("the rule is empty");
    return parseTokens(toks);
  }

  /* ---------------- widths ---------------- */
  const DEFAULT_WIDTH = { i1: 24, i2: 24, i3: 384, i4: 384, i5: 64, i12: 384, o5: 24, o8: 24, o9: 24 };
  function* walk(n) { yield n; for (const k of n.kids) yield* walk(k); }
  function infer(n, w) {
    switch (n.kind) {
      case "stream": return w[n.name] == null ? null : w[n.name];
      case "const": case "num": case "cast": return n.width == null ? null : n.width;
      case "paren": case "unop": return infer(n.kids[0], w);
      case "binop": {
        const a = infer(n.kids[0], w), b = infer(n.kids[1], w);
        if (a != null && b != null && a !== b) out(`the two sides of ${n.op} have widths ${a} and ${b}`);
        return a != null ? a : b;
      }
    }
    return null;
  }
  function widths(tree) {
    const w = {};
    for (const n of walk(tree)) if (n.kind === "stream") {
      if (n.other) out(`${n.name} is typed ${n.other}, not as a bit-vector`);
      if (n.width != null) {
        if (w[n.name] != null && w[n.name] !== n.width) out(`${n.name} is typed with two widths (${w[n.name]} and ${n.width})`);
        w[n.name] = n.width;
      }
    }
    for (let changed = true; changed;) {     // a stream left untyped takes the width of the other side of its comparison
      changed = false;
      for (const n of walk(tree)) {
        if (n.kind !== "cmp") continue;
        const a = infer(n.kids[0], w), b = infer(n.kids[1], w);
        if (a != null && b != null && a !== b) out(`a comparison of widths ${a} and ${b}`);
        const x = a != null ? a : b;
        if (x == null) continue;
        for (const side of n.kids) for (const s of walk(side)) {
          if (s.kind === "cast") break;
          if (s.kind === "stream" && w[s.name] == null) { w[s.name] = x; changed = true; }
        }
      }
    }
    for (const n of walk(tree)) if (n.kind === "stream" && w[n.name] == null) {
      if (DEFAULT_WIDTH[n.name] == null) out(`${n.name} has no width anywhere in the rule`);
      w[n.name] = DEFAULT_WIDTH[n.name];
    }
    return w;
  }

  /* ---------------- evaluation ---------------- */
  const mask = w => (1n << BigInt(w)) - 1n;
  const OPS = {
    "&": () => (a, b) => a & b, "|": () => (a, b) => a | b, "^": () => (a, b) => a ^ b,
    "!&": m => (a, b) => ~(a & b) & m, "!|": m => (a, b) => ~(a | b) & m, "!^": m => (a, b) => ~(a ^ b) & m,
    "+": m => (a, b) => (a + b) & m, "-": m => (a, b) => (a - b) & m, "*": m => (a, b) => (a * b) & m,
    "/": m => (a, b) => b === 0n ? m : a / b,                       // x / 0 = all ones, as the engine answers
    "%": () => (a, b) => b === 0n ? a : a % b,                      // x % 0 = x
    "<<": (m, bw) => (a, b) => b >= bw ? 0n : (a << b) & m, ">>": (m, bw) => (a, b) => b >= bw ? 0n : a >> b,
    min: () => (a, b) => a <= b ? a : b, max: () => (a, b) => a >= b ? a : b,
  };
  function term(n, w, want) {
    switch (n.kind) {
      case "paren": return term(n.kids[0], w, want);
      case "stream": { const name = n.name; return { f: env => env[name], w: w[name] }; }
      case "const": {
        const W = n.width != null ? n.width : want;
        if (W == null) out("a value without a width");
        if (n.value > mask(W)) out(`${n.value} does not fit ${W} bits`);
        const v = n.value; return { f: () => v, w: W };
      }
      case "num": {
        const W = n.width != null ? n.width : want;
        if (W == null) out(`a bare ${n.value} without a width`);
        const v = n.value === 0n ? 0n : mask(W); return { f: () => v, w: W };
      }
      case "cast": {
        const a = term(n.kids[0], w), W = n.width, m = mask(W), f = a.f;
        return W === a.w ? a : { f: env => f(env) & m, w: W };
      }
      case "unop": { const a = term(n.kids[0], w, want), m = mask(a.w), f = a.f; return { f: env => ~f(env) & m, w: a.w }; }
      case "binop": {
        let W = infer(n.kids[0], w); if (W == null) W = infer(n.kids[1], w); if (W == null) W = want;
        const A = term(n.kids[0], w, W), B = term(n.kids[1], w, W);
        if (A.w !== B.w) out(`the two sides of ${n.op} have different widths`);
        const op = OPS[n.op](mask(A.w), BigInt(A.w)), fa = A.f, fb = B.f;
        return { f: env => op(fa(env), fb(env)), w: A.w };
      }
    }
    out(`the part “${n.kind}”`);
  }
  const REL = { "=": (a, b) => a === b, "!=": (a, b) => a !== b, "<": (a, b) => a < b, "<=": (a, b) => a <= b, ">": (a, b) => a > b, ">=": (a, b) => a >= b };
  function formula(n, w) {
    switch (n.kind) {
      case "bool": { const v = n.value; return () => v; }
      case "cmp": {
        let W = infer(n.kids[0], w); if (W == null) W = infer(n.kids[1], w);
        if (W == null) out("a comparison with no width on either side");
        const A = term(n.kids[0], w, W), B = term(n.kids[1], w, W);
        if (A.w !== B.w) out("a comparison of two widths");
        const fa = A.f, fb = B.f, neg = n.op[0] === "!" && n.op !== "!=", rel = REL[neg ? n.op.slice(1) : n.op];
        return neg ? env => !rel(fa(env), fb(env)) : env => rel(fa(env), fb(env));
      }
      case "not": { const a = formula(n.kids[0], w); return env => !a(env); }
      case "and": { const a = formula(n.kids[0], w), b = formula(n.kids[1], w); return env => a(env) && b(env); }
      case "or": { const a = formula(n.kids[0], w), b = formula(n.kids[1], w); return env => a(env) || b(env); }
      case "xor": { const a = formula(n.kids[0], w), b = formula(n.kids[1], w); return env => a(env) !== b(env); }
      case "iff": { const a = formula(n.kids[0], w), b = formula(n.kids[1], w); return env => a(env) === b(env); }
      case "imp": { const a = formula(n.kids[0], w), b = formula(n.kids[1], w); return env => !a(env) || b(env); }
      case "ite": { const c = formula(n.kids[0], w), a = formula(n.kids[1], w), b = formula(n.kids[2], w); return env => c(env) ? a(env) : b(env); }
    }
    out(`the part “${n.kind}”`);
  }

  /* one rule, compiled: its streams, their widths and a test env → true/false */
  function compile(text, outName) {
    const tree = typeof text === "string" ? parse(text) : text;
    const w = widths(tree), f = formula(tree, w);
    const names = [...new Set([...walk(tree)].filter(n => n.kind === "stream").map(n => n.name))];
    const byNum = (a, b) => +a.slice(1) - +b.slice(1);
    const outs = names.filter(n => n[0] === "o").sort(byNum), ins = names.filter(n => n[0] === "i").sort(byNum);
    const o = outName || "o5";
    return { tree, w, f, ins, outs, out: o, writes: outs.includes(o), others: outs.filter(n => n !== o) };
  }
  const only = rule => { if (rule.others.length) out(`it also writes ${rule.others.join(", ")}`, "outputs"); return rule; };

  /* how a side of a comparison relates to the inputs: a bare stream, a fixed value, or a computation with a stream */
  function sideOf(n) {
    let k = n; while (k.kind === "paren") k = k.kids[0];
    if (k.kind === "stream") return { kind: "var", name: k.name };
    for (const s of walk(n)) if (s.kind === "stream") return { kind: "expr", name: s.name };
    return { kind: "fixed" };
  }

  const cmpBig = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  /* the pieces of 0..max cut at the given values: each value alone, and the stretches between them */
  function pieces(values, W) {
    const M = mask(W), pts = [...new Set(values.filter(v => v >= 0n && v <= M).map(String))].map(BigInt).sort(cmpBig);
    const r = []; let lo = 0n;
    for (const p of pts) { if (p > lo) r.push({ lo, hi: p - 1n }); r.push({ lo: p, hi: p }); lo = p + 1n; }
    if (lo <= M) r.push({ lo, hi: M });
    return r;
  }

  /* the classes of streams compared with each other, the values each class is compared with, and one or more
     stand-in values per piece (as many as the class has members, so any order among them can be built) */
  function cut(rules, wantOut) {
    const parent = {}, find = x => { while (parent[x] !== x) x = parent[x] = parent[parent[x]]; return x; };
    const W = {}, fixed = {};
    for (const r of rules) for (const n of walk(r.tree)) if (n.kind === "stream") {
      if (parent[n.name] == null) parent[n.name] = n.name;
      if (W[n.name] != null && W[n.name] !== r.w[n.name]) out(`${n.name} has two widths`);
      W[n.name] = r.w[n.name];
    }
    for (const r of rules) for (const n of walk(r.tree)) {
      if (n.kind !== "cmp") continue;
      const [a, b] = n.kids.map(sideOf);
      const e = a.kind === "expr" ? a : b.kind === "expr" ? b : null;
      if (e) out(`it computes with ${e.name}`, "computes");
      let w = infer(n.kids[0], r.w); if (w == null) w = infer(n.kids[1], r.w);
      if (a.kind === "var" && b.kind === "var") { const x = find(a.name), y = find(b.name); if (x !== y) parent[x] = y; }
      else if (a.kind === "var" && b.kind === "fixed") (fixed[a.name] = fixed[a.name] || []).push(term(n.kids[1], r.w, w).f({}));
      else if (b.kind === "var" && a.kind === "fixed") (fixed[b.name] = fixed[b.name] || []).push(term(n.kids[0], r.w, w).f({}));
    }
    const classes = {};
    for (const s of Object.keys(parent)) (classes[find(s)] = classes[find(s)] || []).push(s);
    const stand = {}, cuts = {}, classOf = {};
    for (const members of Object.values(classes)) {
      const w = W[members[0]], vals = [].concat(...members.map(m => fixed[m] || []));
      const ps = pieces(vals, w);
      const k = Math.max(members.length, members.includes(wantOut) ? 2 : 1);
      const reps = [];
      for (const p of ps) for (let j = 0n; j < BigInt(k) && p.lo + j <= p.hi; j++) reps.push(p.lo + j);
      for (const m of members) { stand[m] = reps; cuts[m] = ps; classOf[m] = members.slice().sort(); }
    }
    return { W, stand, cuts, classOf };
  }

  const decide = allowed => {
    if (!allowed.length) return "none";
    const zero = allowed.some(v => v === 0n), other = allowed.some(v => v !== 0n);
    return zero ? (other ? "open" : "block") : "pass";
  };
  /* what the engine does with each kind of answer: open reads as 0 */
  const OUTCOME = { pass: "pass", block: "block", open: "block", none: "fail" };
  const pieceOf = (ps, v) => { for (let i = 0; i < ps.length; i++) if (v >= ps[i].lo && v <= ps[i].hi) return i; return -1; };
  const LIMIT = 40000;

  /* every kind of transfer the rules can tell apart, with each rule's answers */
  function enumerate(rules, o) {
    const c = cut(rules, o);
    const ins = [...new Set([].concat(...rules.map(r => r.ins)))].sort((a, b) => +a.slice(1) - +b.slice(1));
    let size = 1; for (const x of ins) size *= c.stand[x].length;
    if (size > LIMIT) out(`it tells ${size} kinds of transfer apart`, "big");
    const outReps = c.stand[o] || [0n, 1n];
    const cells = [], env = {};
    const rec = j => {
      if (j === ins.length) {
        const v = {}; for (const x of ins) v[x] = env[x];
        const per = rules.map(r => { const allowed = []; for (const y of outReps) { env[o] = y; if (r.f(env)) allowed.push(y); } delete env[o]; return { allowed, d: r.writes ? decide(allowed) : "silent" }; });
        cells.push({ v, per });
        return;
      }
      for (const y of c.stand[ins[j]]) { env[ins[j]] = y; rec(j + 1); }
      delete env[ins[j]];
    };
    rec(0);
    return { c, ins, cells };
  }

  /* inputs whose value changes the answer: two transfers equal in everything else, answered differently */
  function readInputs(ins, cells, key) {
    const read = [];
    for (const x of ins) {
      const seen = new Map();
      let hit = false;
      for (const cell of cells) {
        const k = ins.filter(y => y !== x).map(y => String(cell.v[y])).join(","), d = key(cell);
        if (!seen.has(k)) seen.set(k, d); else if (seen.get(k) !== d) { hit = true; break; }
      }
      if (hit) read.push(x);
    }
    return read;
  }

  /* group the pieces of a single input by how the rule treats them (same answer wherever everything else is the same) */
  function groupsOf(x, ins, cells, ps, key) {
    const sig = ps.map(() => []);
    const others = ins.filter(y => y !== x);
    const sorted = cells.slice().sort((a, b) => { for (const y of others) { const d = cmpBig(a.v[y], b.v[y]); if (d) return d; } return 0; });
    for (const cell of sorted) sig[pieceOf(ps, cell.v[x])].push(key(cell));
    const byKey = new Map();
    sig.forEach((s, i) => { const k = s.join("|"); if (!byKey.has(k)) byKey.set(k, []); byKey.get(k).push(i); });
    return [...byKey.values()];
  }

  /* ================ the reading of one rule ================ */
  function read(text, opts) {
    const o = (opts && opts.out) || "o5";
    let rule;
    try {
      rule = compile(text, o);
      if (!rule.writes) return { ok: false, code: "noout", why: `the rule sets no ${o}` };
      only(rule);
    } catch (e) { if (e instanceof Outside) return { ok: false, code: e.code, why: e.message }; throw e; }
    let en;
    try { en = enumerate([rule], o); } catch (e) { if (e instanceof Outside) return { ok: false, code: e.code, why: e.message }; throw e; }
    const { c, ins, cells } = en;
    for (const cell of cells) { cell.allowed = cell.per[0].allowed; cell.d = cell.per[0].d; delete cell.per; }
    const has = { pass: 0, block: 0, open: 0, none: 0 };
    for (const cell of cells) has[cell.d]++;
    const key = cell => cell.d;
    const read = readInputs(ins, cells, key);
    const shared = ins.filter(x => c.classOf[x].filter(y => y[0] === "i").length > 1);   // inputs compared with each other
    const inputs = ins.map(x => ({
      name: x, width: c.W[x], pieces: c.cuts[x], read: read.includes(x), shared: shared.includes(x),
      groups: shared.includes(x) ? c.cuts[x].map((_, i) => [i]) : groupsOf(x, ins, cells, c.cuts[x], key),
    }));
    const outcomes = new Set(cells.map(cell => OUTCOME[cell.d]));
    return {
      ok: true, out: o, inputs, cells, has, read, shared,
      kinds: cells.length,
      total: !has.none, decided: !has.open,
      all: outcomes.size === 1 ? [...outcomes][0] : null,      // "pass" / "block" / "fail" when every transfer ends the same way
    };
  }

  /* ---------------- one transfer ---------------- */
  const toBig = v => typeof v === "bigint" ? v : /^#x/i.test(String(v)) ? BigInt("0x" + String(v).slice(2)) : /^#b/i.test(String(v)) ? BigInt("0b" + String(v).slice(2)) : BigInt(String(v).trim() || 0);
  /* the answers a rule allows for one concrete transfer, and the value the engine gives. Exact for any rule whose
     outputs stand bare in its comparisons (inputs may be computed with); other outputs only need some value.
     Inputs nobody feeds read 0. */
  function answer(text, inputs, opts) {
    const o = (opts && opts.out) || "o5";
    const rule = compile(text, o);
    const env = {};
    for (const x of rule.ins) env[x] = toBig(inputs && inputs[x] != null ? inputs[x] : 0) & mask(rule.w[x]);
    const vals = {};
    for (const y of rule.outs) vals[y] = [];
    const outsIn = s => [...walk(s)].filter(k => k.kind === "stream" && k.name[0] === "o").map(k => k.name);
    for (const n of walk(rule.tree)) {
      if (n.kind !== "cmp") continue;
      const [a, b] = n.kids.map(sideOf), oa = outsIn(n.kids[0]), ob = outsIn(n.kids[1]);
      if ((oa.length && a.kind !== "var") || (ob.length && b.kind !== "var") || (oa.length && ob.length)) out(`it computes with ${oa.concat(ob)[0]}`, "computes");
      let w = infer(n.kids[0], rule.w); if (w == null) w = infer(n.kids[1], rule.w);
      if (oa.length) vals[a.name].push(term(n.kids[1], rule.w, w).f(env));
      if (ob.length) vals[b.name].push(term(n.kids[0], rule.w, w).f(env));
    }
    const cutsOf = {}, reps = {};
    for (const y of rule.outs) {
      cutsOf[y] = pieces(vals[y], rule.w[y]);
      reps[y] = [];
      for (const p of cutsOf[y]) for (let j = 0n; j < 2n && p.lo + j <= p.hi; j++) reps[y].push(p.lo + j);
    }
    const others = rule.others;
    const holds = () => {                       // some value for every other output makes the rule true
      const rec = j => {
        if (j === others.length) return rule.f(env);
        for (const v of reps[others[j]]) { env[others[j]] = v; if (rec(j + 1)) return true; }
        return false;
      };
      return rec(0);
    };
    const allowed = [];
    if (rule.writes) for (const v of reps[o]) { env[o] = v; if (holds()) allowed.push(v); }
    const d = rule.writes ? decide(allowed) : "silent";
    /* the value the engine gives: 0 when 0 is allowed (an open answer reads as 0), else the one value allowed */
    let value = null;
    if (allowed.some(v => v === 0n)) value = 0n;
    else if (allowed.length === 1) { const p = cutsOf[o][pieceOf(cutsOf[o], allowed[0])]; if (p.lo === p.hi) value = allowed[0]; }
    return { d, outcome: d === "silent" ? "pass" : OUTCOME[d], allowed, value };
  }

  /* ---------------- what would pass ---------------- */
  /* for a blocked transfer: each single input whose change lets it pass, with the passing pieces and the nearest value */
  function wouldPass(reading, inputs) {
    if (!reading || !reading.ok || reading.shared.length) return null;
    const at = {};
    for (const x of reading.inputs) at[x.name] = toBig(inputs && inputs[x.name] != null ? inputs[x.name] : 0) & mask(x.width);
    const cellAt = v => reading.cells.find(cell => reading.inputs.every(x => pieceOf(x.pieces, cell.v[x.name]) === pieceOf(x.pieces, v[x.name])));
    const here = cellAt(at), now = here ? OUTCOME[here.d] : null, d = here ? here.d : null;
    const ways = [];
    for (const x of reading.inputs) {
      if (!x.read) continue;
      const pass = [];
      x.pieces.forEach((p, i) => {
        const v = Object.assign({}, at, { [x.name]: p.lo });
        const cell = cellAt(v);
        if (cell && OUTCOME[cell.d] === "pass") pass.push(i);
      });
      if (!pass.length) continue;
      const cur = at[x.name];
      let best = null, dist = null;
      for (const i of pass) {
        const p = x.pieces[i], v = cur < p.lo ? p.lo : cur > p.hi ? p.hi : cur, d = v > cur ? v - cur : cur - v;
        if (dist === null || d < dist) { best = v; dist = d; }
      }
      ways.push({ input: x.name, pieces: pass, nearest: best });
    }
    return { now, d, ways };
  }

  /* ================ two rules side by side: where their answers differ ================ */
  function diff(before, after, opts) {
    const o = (opts && opts.out) || "o5";
    let a, b, en;
    try { a = only(compile(before, o)); b = only(compile(after, o)); en = enumerate([a, b], o); }
    catch (e) { if (e instanceof Outside) return { ok: false, code: e.code, why: e.message }; throw e; }
    const { c, ins, cells } = en;
    const silent = d => d === "silent" ? "pass" : OUTCOME[d];      // a rule that sets nothing lets a transfer through
    for (const cell of cells) { cell.was = cell.per[0].d; cell.now = cell.per[1].d; delete cell.per; }
    const key = cell => cell.was + ">" + cell.now;
    const changed = cells.filter(cell => silent(cell.was) !== silent(cell.now));
    const shared = ins.filter(x => c.classOf[x].filter(y => y[0] === "i").length > 1);
    const inputs = ins.map(x => ({
      name: x, width: c.W[x], pieces: c.cuts[x], shared: shared.includes(x),
      groups: shared.includes(x) ? c.cuts[x].map((_, i) => [i]) : groupsOf(x, ins, cells, c.cuts[x], key),
    }));
    return { ok: true, out: o, inputs, cells, changed, read: readInputs(ins, cells, key), same: !changed.length };
  }

  /* ================ edges: the last value on one side of a cut and the first on the other ================ */
  /* every place where one step in a single input turns a passing transfer into a blocked one (or back) */
  function edges(reading) {
    if (!reading || !reading.ok) return [];
    const res = [];
    for (const x of reading.inputs) {
      if (!x.read || x.shared) continue;
      const others = reading.inputs.filter(y => y !== x);
      const byRest = new Map();
      for (const cell of reading.cells) {
        const k = others.map(y => String(cell.v[y.name])).join(",");
        if (!byRest.has(k)) byRest.set(k, []);
        byRest.get(k).push(cell);
      }
      const seen = new Set();
      for (const row of byRest.values()) {
        row.sort((p, q) => cmpBig(p.v[x.name], q.v[x.name]));
        for (let i = 0; i + 1 < row.length; i++) {
          const A = row[i], B = row[i + 1], pa = x.pieces[pieceOf(x.pieces, A.v[x.name])], pb = x.pieces[pieceOf(x.pieces, B.v[x.name])];
          if (OUTCOME[A.d] === OUTCOME[B.d] || pa.hi + 1n !== pb.lo) continue;
          const k = `${pa.hi}|${A.d}|${B.d}`;
          if (seen.has(k)) continue;
          seen.add(k);
          const rest = {}; for (const y of others) rest[y.name] = A.v[y.name];
          res.push({ input: x.name, below: pa.hi, above: pb.lo, belowSays: A.d, aboveSays: B.d, rest });
        }
      }
    }
    return res;
  }

  /* ================ a change to the network's rules: what it decides differently ================ */
  /* The node folds a rule change into the rules in force output by output: each output the change defines gets its
     new definition, every other output keeps the old one. meaning() compares, for each output the change redefines,
     the old definition with the new one over every possible case and says where the answer differs. Outputs whose
     answer is yes or no (any value but 0 is yes, as the node reads o5, o6 and o7) and the fee outputs (an amount)
     are read; any other output is only named. Same cutting as read(), so it is exact where it answers. */
  const STREAMS = {
    o5: { kind: "yesno", topic: "Personal rule", every: "every transfer", yes: "Newly passing", no: "Newly blocked" },
    o6: { kind: "yesno", topic: "Which blocks count as valid", every: "every block", yes: "Newly accepted", no: "Newly rejected" },
    o7: { kind: "yesno", topic: "Who may make blocks", every: "every proposer", yes: "Newly allowed to make blocks", no: "Newly barred from making blocks" },
    o8: { kind: "value", topic: "Custom fee", every: "every transfer" },
    o9: { kind: "value", topic: "Base fee per transaction", every: "every transfer" },
  };
  const norm = s => String(s).replace(/\s+/g, "");
  function bodyOf(text) {
    const t = stripComments(text), m = /\balways\s*\(/.exec(t);
    if (!m) return t.trim().replace(/\.\s*$/, "");
    let depth = 0; const start = m.index + m[0].length - 1;
    for (let i = start; i < t.length; i++) {
      if (t[i] === "(") depth++;
      else if (t[i] === ")" && --depth === 0) return t.slice(start + 1, i);
    }
    return t.slice(start + 1);
  }
  function splitAnd(b) {
    const parts = []; let depth = 0, cur = "";
    for (let i = 0; i < b.length; i++) {
      const ch = b[i];
      if ("({[".includes(ch)) depth++; else if (")}]".includes(ch)) depth--;
      if (depth === 0 && b.startsWith("&&", i)) { parts.push(cur); cur = ""; i++; continue; }
      cur += ch;
    }
    parts.push(cur);
    return parts.map(p => p.trim()).filter(Boolean);
  }
  /* output stream → the part of the rule that defines it (as assets/rulediff.js and infra/alerts/explain.py split it) */
  function clausesOf(text) {
    const res = {};
    for (const part of splitAnd(bodyOf(text))) for (const s of new Set(part.match(/\bo\d+(?=\[t\])/g) || [])) res[s] = part;
    return res;
  }
  /* the value an output takes in one case: the one value the rule allows, "open" when it allows more than one
     (for o5 to o7 the engine then answers 0; for a fee nobody measured it), "none" when it allows none */
  function valueOf(allowed, cuts) {
    if (!allowed.length) return "none";
    if (allowed.length === 1) { const p = cuts[pieceOf(cuts, allowed[0])]; if (p.lo === p.hi) return allowed[0]; }
    return "open";
  }
  /* diff() for an output whose answer is an amount: the cases where the value changes */
  function valueDiff(before, after, o) {
    let a, b, en;
    try { a = only(compile(before, o)); b = only(compile(after, o)); en = enumerate([a, b], o); }
    catch (e) { if (e instanceof Outside) return { ok: false, code: e.code, why: e.message }; throw e; }
    const { c, ins, cells } = en;
    if ((c.classOf[o] || []).some(y => y[0] === "i")) return { ok: false, code: "computes", why: `${o} follows ${c.classOf[o].filter(y => y[0] === "i").join(", ")}` };
    const cuts = c.cuts[o];
    for (const cell of cells) {
      cell.was = a.writes ? valueOf(cell.per[0].allowed, cuts) : "open";
      cell.now = b.writes ? valueOf(cell.per[1].allowed, cuts) : "open";
      delete cell.per;
    }
    const key = cell => String(cell.was) + ">" + String(cell.now);
    const changed = cells.filter(cell => String(cell.was) !== String(cell.now));
    const shared = ins.filter(x => c.classOf[x].filter(y => y[0] === "i").length > 1);
    const inputs = ins.map(x => ({
      name: x, width: c.W[x], pieces: c.cuts[x], shared: shared.includes(x),
      groups: shared.includes(x) ? c.cuts[x].map((_, i) => [i]) : groupsOf(x, ins, cells, c.cuts[x], key),
    }));
    return { ok: true, out: o, inputs, cells, changed, read: readInputs(ins, cells, key), same: !changed.length };
  }
  /* the cases of one kind of change: every case, one box of input ranges ("all"), a few boxes ("any"; two boxes that
     differ in one input only become one), or "some" when inputs compared with each other decide it */
  function whereOf(r, sub) {
    const mem = new Set(sub), names = r.inputs.map(x => x.name);
    const read = readInputs(names, r.cells, cell => mem.has(cell));
    if (!read.length) return { every: true };
    const X = r.inputs.filter(x => read.includes(x.name));
    if (X.some(x => x.shared)) return { some: true, inputs: X.map(x => x.name) };
    const at = (x, cell) => pieceOf(x.pieces, cell.v[x.name]);
    let boxes = [...new Set(sub.map(cell => X.map(x => at(x, cell)).join(",")))].map(k => k.split(",").map(i => [+i]));
    for (let again = true; again;) {
      again = false;
      for (let j = 0; j < X.length; j++) {
        const by = new Map();
        for (const b of boxes) {
          const k = b.map((g, i) => i === j ? "" : g.join(".")).join(",");
          if (!by.has(k)) { by.set(k, b); continue; }
          const m = by.get(k);
          m[j] = [...new Set([...m[j], ...b[j]])].sort((p, q) => p - q);
          again = true;
        }
        boxes = [...by.values()];
      }
    }
    const asConds = b => b.map((group, j) => ({ input: X[j].name, width: X[j].width, pieces: X[j].pieces, group }));
    if (boxes.length === 1) return { all: asConds(boxes[0]) };
    return { any: boxes.slice(0, 4).map(asConds), more: Math.max(0, boxes.length - 4) };
  }
  function meaning(spec, revisions) {
    const next = {};
    for (const r of revisions || []) Object.assign(next, clausesOf(r));
    const streams = [];
    for (const s of Object.keys(next).sort((a, b) => +a.slice(1) - +b.slice(1))) {
      const was = spec ? spec[s] : null, now = next[s], info = STREAMS[s];
      if (was != null && norm(was) === norm(now)) continue;
      const kind = info ? info.kind : "other";
      if (was == null || !info) { streams.push({ stream: s, kind, ok: false, code: was == null ? "new" : "other" }); continue; }
      const before = `always ( ${was} ).`, after = `always ( ${now} ).`;
      const r = kind === "yesno" ? diff(before, after, { out: s }) : valueDiff(before, after, s);
      if (!r.ok) { streams.push({ stream: s, kind, ok: false, code: r.code, why: r.why }); continue; }
      const say = kind === "yesno" ? (d => d === "silent" ? "pass" : OUTCOME[d]) : (v => String(v));
      const by = new Map();
      for (const cell of r.changed) {
        const was = say(cell.was), now = say(cell.now);
        // a yes/no output gets one line per head: "No answer fits any more", whatever it answered before
        const k = kind !== "yesno" ? was + ">" + now : now === "fail" ? "fail" : was === "fail" ? "again" : now;
        if (!by.has(k)) by.set(k, { was, now, cells: [] });
        const g = by.get(k);
        if (g.was !== was) g.was = null;
        if (g.now !== now) g.now = null;
        g.cells.push(cell);
      }
      const changes = [...by.values()].map(g => ({ was: g.was, now: g.now, where: whereOf(r, g.cells) }));
      streams.push({ stream: s, kind, ok: true, same: r.same, changes });
    }
    return { ok: streams.every(x => x.ok), same: streams.every(x => x.ok && x.same), streams };
  }

  /* ================ words ================ */
  /* English phrases for the pages (each one a key of the page dictionaries, so it is translated whole) */
  const LABEL = {
    i1: "amount", i2: "balance", i3: "sender", i4: "receiver", i5: "block time", i12: "sender",
    i6: "block height", i7: "block time", i8: "proposer", i9: "previous block", i10: "signature check", i11: "claims",
    i13: "proposer key", i14: "proposer balance", i15: "eligibility mode",
  };
  const label = x => LABEL[x] || x;
  const isTime = x => x === "i5" || x === "i7";
  const isAddr = (x, W) => !isTime(x) && W === 384;
  const fmtNum = v => BigInt(v).toLocaleString("en-US");
  function fmtTime(v) {
    const s = Number(v);
    if (!(s >= 0 && s <= 253402300799)) return fmtNum(v);      // up to the year 9999
    const iso = new Date(s * 1000).toISOString();
    if (iso.slice(11, 19) === "00:00:00") return iso.slice(0, 10);
    return iso.slice(0, 10) + " " + (iso.slice(17, 19) === "00" ? iso.slice(11, 16) : iso.slice(11, 19)) + " UTC";
  }
  const hexOf = (v, W) => BigInt(v).toString(16).padStart(Math.ceil(W / 4), "0");
  function fmtAddr(v, W, names) {
    const h = hexOf(v, W);
    if (names && names[h]) return names[h];
    return h.length > 12 ? h.slice(0, 6) + "…" + h.slice(-4) : "#x" + h;
  }
  /* adjacent pieces of a group joined into stretches */
  function stretches(ps, group) {
    const sorted = group.slice().sort((a, b) => cmpBig(ps[a].lo, ps[b].lo)), res = [];
    for (const i of sorted) {
      const last = res[res.length - 1];
      if (last && last.hi + 1n === ps[i].lo) last.hi = ps[i].hi; else res.push({ lo: ps[i].lo, hi: ps[i].hi });
    }
    return res;
  }
  /* one stretch of one input in words, without the input's name: "up to 1,000", "Bob", "before 2027-01-01" */
  function stretchWords(x, W, s, names, whole) {
    const M = mask(W);
    if (isAddr(x, W)) {
      if (s.lo === s.hi) return fmtAddr(s.lo, W, names);
      return whole ? "anyone" : "anyone else";
    }
    if (isTime(x)) {
      if (s.lo === 0n && s.hi === M) return "any time";
      if (s.lo === s.hi) return `at exactly ${fmtTime(s.lo)}`;
      if (s.lo === 0n) return `before ${fmtTime(s.hi + 1n)}`;
      if (s.hi === M) return `on or after ${fmtTime(s.lo)}`;
      return `from ${fmtTime(s.lo)} to before ${fmtTime(s.hi + 1n)}`;
    }
    if (s.lo === 0n && s.hi === M) return "any value";
    if (s.lo === s.hi) return `exactly ${fmtNum(s.lo)}`;
    if (s.lo === 0n) return `up to ${fmtNum(s.hi)}`;
    if (s.hi === M) return `${fmtNum(s.lo)} or more`;
    return `${fmtNum(s.lo)} to ${fmtNum(s.hi)}`;
  }
  /* a group of pieces in words: a list of short phrases (an address group with stretches reads "anyone else") */
  function groupWords(inp, group, names) {
    const x = inp.name, W = inp.width;
    const ss = stretches(inp.pieces, group);
    if (isAddr(x, W)) {
      const pts = ss.filter(s => s.lo === s.hi).map(s => fmtAddr(s.lo, W, names));
      const rest = ss.some(s => s.lo !== s.hi);
      const all = group.length === inp.pieces.length;
      if (all) return ["anyone"];
      return rest ? (pts.length ? pts.concat(["anyone else"]) : ["anyone else"]) : pts;
    }
    return ss.map(s => stretchWords(x, W, s, names, group.length === inp.pieces.length));
  }
  const SAYS = { pass: "passes", block: "blocked", open: "no answer: blocked", none: "fails" };

  /* one condition of a meaning() change in words, as parts that are each a key of the page dictionaries:
     ["block height", "exactly 0"], ["proposer", "other than a1fe40…7d2b"], ["signature check failed"]; null = any */
  function condParts(c, names) {
    const x = c.input, W = c.width, ps = c.pieces, g = c.group, inG = new Set(g);
    if (x === "i10") {                      // the host's signature check: 1 when it verified the block's signature, else 0
      const zero = g.some(i => ps[i].lo === 0n), other = g.some(i => ps[i].hi > 0n);
      return zero && other ? null : [zero ? "signature check failed" : "signature check passed"];
    }
    if (isAddr(x, W)) {
      const point = i => ps[i].lo === ps[i].hi, all = ps.map((_, i) => i);
      if (all.filter(i => !point(i)).every(i => inG.has(i))) {
        const not = all.filter(i => point(i) && !inG.has(i)).map(i => fmtAddr(ps[i].lo, W, names));
        return not.length ? [label(x), `other than ${not.join(", ")}`] : null;
      }
      if (g.every(point)) return [label(x), g.map(i => fmtAddr(ps[i].lo, W, names)).join(", ")];
    }
    const ss = stretches(ps, g);
    if (ss.length === 1 && ss[0].lo === 0n && ss[0].hi === mask(W)) return null;
    const res = [label(x)];
    ss.forEach((s, i) => { if (i) res.push("or"); res.push(stretchWords(x, W, s, names, false)); });
    return res;
  }
  /* meaning() in English, one line per change: { stream, topic, head, items, more }. items: one entry per case box
     (one for "all", a few for "any"), each a list of conditions, each condition a list of parts (each part a key of
     the page dictionaries). Read as text by lineText(): "Newly rejected: block height exactly 0 and signature check passed" */
  function meaningLines(m, names) {
    const lines = [];
    for (const s of m.streams) {
      if (!s.ok) continue;
      const info = STREAMS[s.stream];
      const fmtV = v => v === "open" ? "left open" : v === "none" ? "no answer" : `${fmtNum(v)} AGRS`;
      for (const ch of s.changes) {
        const head = s.kind === "yesno"
          ? ch.now === "fail" ? "No answer fits any more" : ch.was === "fail" ? "An answer fits again" : ch.now === "pass" ? info.yes : info.no
          : `${fmtV(ch.was)} → ${fmtV(ch.now)}`;
        const w = ch.where, conds = list => list.map(c => condParts(c, names)).filter(Boolean);
        const some = () => [["some cases, depending on", ...[...new Set(w.inputs.map(label))].flatMap((t, i) => i ? ["and", t] : [t])]];
        let items = w.every ? [[[info.every]]] : w.some ? [some()] : w.all ? [conds(w.all)] : w.any.map(conds);
        items = items.map(it => it.length ? it : [[info.every]]);
        lines.push({ stream: s.stream, topic: info.topic, head, items, more: w.more || 0 });
      }
    }
    return lines;
  }
  const lineText = l => `${l.head}: ${l.items.map(it => it.map(c => c.join(" ")).join(" and ")).join("; ")}${l.more ? `; and ${l.more} more` : ""}`;

  const api = { Outside, stripComments, parse, read, answer, wouldPass, diff, edges, meaning, clausesOf, OUTCOME, SAYS, STREAMS,
    words: { label, fmtNum, fmtTime, fmtAddr, hexOf, stretchWords, groupWords, stretches, pieceOf, isAddr, isTime, meaningLines, lineText } };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RuleFacts = api;
})(typeof window !== "undefined" ? window : globalThis);
