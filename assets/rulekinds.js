/* Rule kinds: what a personal rule checks, read from its Tau text, for tauhud.com/rules/numbers/. The same reading as
   the relay's infra/relay/ruledays.py kinds(); tests/rulekinds-cases.json holds the answers both must give
   (tests/rulekinds.mjs, infra/relay/test_ruledays.py). Uses the playground's parser (assets/rulefacts.js), so nothing is guessed:

   cap      a most per payment: the amount (i1) against a fixed number, outside a co-signer condition
   only     only to certain recipients: reads the recipient (i4)
   time     a time lock: reads the block time (i5)
   cosign   a second signature: reads a co-signer slot (i18 to i25)
   reserve  keeps a reserve: reads the balance at the block before (i2)
   freeze   nothing leaves: the wallet's freeze, old or new text
   other    reads something else (custom inputs from i26, the fee i3), or none of the above */
(function (root) {
  "use strict";
  const KINDS = ["cap", "only", "time", "cosign", "reserve", "freeze", "other"];
  const COSIGN = new Set(Array.from({ length: 8 }, (_, i) => "i" + (18 + i)));
  const KNOWN = new Set(["i1", "i2", "i4", "i5", ...COSIGN]);
  const RF = () => root.RuleFacts || (typeof require === "function" ? require("./rulefacts.js") : null);
  function streams(n) {
    const out = new Set(), todo = [n];
    while (todo.length) { const k = todo.pop(); if (k.kind === "stream") out.add(k.name); todo.push(...(k.kids || [])); }
    return out;
  }
  function* cmps(n, up) {
    if (n.kind === "cmp") { if ([...streams(n)].some(s => s[0] === "i")) yield [n, up]; return; }
    for (const k of n.kids || []) yield* cmps(k, up.concat([n]));
  }
  function kinds(text) {
    let tree;
    try { tree = RF().parse(text); } catch (e) { return { kinds: ["other"], size: 0 }; }
    const list = [...cmps(tree, [])];
    const reads = new Set();
    for (const [c] of list) for (const s of streams(c)) if (s[0] === "i") reads.add(s);
    if (!reads.size) return { kinds: [streams(tree).has("o5") ? "freeze" : "other"], size: 0 };
    if (list.length === 1 && reads.size === 1 && reads.has("i1")) {
      const c = list[0][0], [a, b] = c.kids;
      if (c.op === ">" && a.kind === "stream" && b.kind === "const" && Number(b.value) === 0) return { kinds: ["freeze"], size: 1 };
    }
    const found = new Set();
    for (const [c, up] of list) {
      const s = new Set([...streams(c)].filter(x => x[0] === "i"));
      if ([...s].some(x => COSIGN.has(x))) found.add("cosign");
      if (s.has("i2")) found.add("reserve");
      if (s.has("i4")) found.add("only");
      if (s.has("i5")) found.add("time");
      if (s.size === 1 && s.has("i1") && !up.some(p => p.kind === "and" && [...streams(p)].some(x => COSIGN.has(x)))) found.add("cap");
      if ([...s].some(x => !KNOWN.has(x))) found.add("other");
    }
    const k = KINDS.filter(x => found.has(x));
    return { kinds: k.length ? k : ["other"], size: list.length };
  }
  const api = { KINDS, kinds };
  if (typeof module === "object" && module.exports) module.exports = api; else root.RuleKinds = api;
})(typeof window !== "undefined" ? window : globalThis);
