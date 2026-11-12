/* Rule words: a wallet rule from plain words, for tauhud.com/builder/. "At most 5,000 per payment, above 1,000 the
   Guardian co-signs, nothing before Friday" becomes the four blocks the wallet builds (wallet/index.html buildRule),
   the same Tau text the wallet signs, the test payments that show where the rule decides, and what the rule answers
   for any one payment. No AI and no network: fixed patterns, so the same words always give the same rule, and every
   part that is not understood or not possible on the testnet is said, never guessed.

   What a personal rule can read on Tau Testnet Alpha (IDNI/tau-testnet consensus/admission.py _screen_clause_domains):
   only the one payment being checked, at [t]: amount i1, recipient i4, block time i5, co-signature slots i18 to i25.
   No earlier step, so no total per day; no balance (i2). The wallet's blocks: only to (up to 5 addresses), at most
   N per payment, nothing before a date, above N one co-signer signs. Tested by tests/rulewords.mjs. */
(function (root) {
  "use strict";
  const MAX_AMOUNT = 2 ** 24 - 1, MAX_ONLY = 5;
  const hex6 = n => Math.max(0, Math.min(MAX_AMOUNT, Math.floor(n))).toString(16).padStart(6, "0");
  const isAddr = s => /^[0-9a-f]{96}$/.test(s);
  /* the wallet's own text, character for character (wallet/index.html), so its reader and the rules wall know it */
  const ALLOW = "(o5[t]:bv[24] = { #x000001 }:bv[24])", BLOCK = "(o5[t]:bv[24] = { #x000000 }:bv[24])";
  const FREEZE = "always ( (o5[t]:bv[24] = { #x000000 }:bv[24]) ).";
  const above = n => `i1[t]:bv[24] > { #x${hex6(n)} }:bv[24]`;
  const unsigned = (slot, who) => `!(i${slot}[t]:bv[384] = { #x${who} }:bv[384])`;
  function coSignCond(limit, approvers) { return `(${above(limit)} && ${approvers.map((a, i) => unsigned(18 + i, a)).join(" && ")})`; }
  const parts = r => {
    const c = [];
    if (r.only && r.only.length) c.push(["only", "(" + r.only.map(a => `!(i4[t]:bv[384] = { #x${a} }:bv[384])`).join(" && ") + ")"]);
    if (r.cap != null) c.push(["cap", `(i1[t]:bv[24] >= { #x${hex6(r.cap + 1)} }:bv[24])`]);
    if (r.from != null) c.push(["from", `(i5[t]:bv[64] < {${Math.floor(r.from)}}:bv[64])`]);
    if (r.co) c.push(["co", coSignCond(r.co.limit, r.co.who)]);
    return c;
  };
  function build(r) {
    if (!r) return null;
    if (r.freeze) return FREEZE;
    const c = parts(r).map(x => x[1]);
    return c.length ? `always ( ${c.join(" || ")} ? ${BLOCK} : ${ALLOW} ).` : null;
  }
  /* what the rule answers for one payment {amount, to, ts, signed: [addresses]}: the blocks that stop it */
  function judge(r, p) {
    const why = [];
    if (!r) return why;
    if (r.freeze) return ["freeze"];
    if (r.only && r.only.length && !r.only.includes(p.to)) why.push("only");
    if (r.cap != null && p.amount > r.cap) why.push("cap");
    if (r.from != null && p.ts < r.from) why.push("from");
    if (r.co && p.amount > r.co.limit && !r.co.who.some(w => (p.signed || []).includes(w))) why.push("co");
    return why;
  }
  const without = (r, k) => { const x = { ...r, only: [...(r.only || [])], co: r.co ? { ...r.co } : null }; if (k === "only") x.only = []; else x[k] = null; return x; };

  /* ---------------- words ---------------- */
  const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
  const midnight = d => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
  /* 1,000 · 1.000 · 1 000 · 1k · 2.5k · 1m */
  function num(s) {
    const m = /^(\d{1,3}(?:[,.' ]\d{3})+|\d+(?:\.\d+)?)\s*(k|m|thousand|million)?$/i.exec(String(s).trim());
    if (!m) return null;
    let n = /[,' ]|\.\d{3}$/.test(m[1]) && !/^\d+\.\d{1,2}$/.test(m[1]) ? Number(m[1].replace(/[,.' ]/g, "")) : Number(m[1]);
    const u = (m[2] || "").toLowerCase();
    if (u === "k" || u === "thousand") n *= 1000;
    if (u === "m" || u === "million") n *= 1e6;
    return isFinite(n) ? Math.round(n) : null;
  }
  const NUM = String.raw`(\d{1,3}(?:[,.' ]\d{3})+|\d+(?:\.\d+)?)\s*(k|m|thousand|million)?\b`;
  const numAt = (text, before) => { const m = new RegExp(before + String.raw`\s*` + NUM, "i").exec(text); return m ? num(m[1] + (m[2] || "")) : null; };
  /* a day: 2026-12-01 · 1.12.2026 · 1 dec (2026) · december 1(st)(, 2026) · friday · tomorrow · next week/month · in 90 days */
  function day(text, now) {
    const t = text.toLowerCase(), today = midnight(now);
    let m;
    if ((m = /\b(\d{4})-(\d{1,2})-(\d{1,2})\b/.exec(t))) return midnight(new Date(+m[1], +m[2] - 1, +m[3]));
    if ((m = /\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b/.exec(t))) return midnight(new Date(+m[3], +m[2] - 1, +m[1]));
    const mon = String.raw`(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?`;
    const fix = (d, mo, y) => { let x = new Date(y ? +y : today.getFullYear(), mo, d); if (!y && x < today) x = new Date(today.getFullYear() + 1, mo, d); return midnight(x); };
    if ((m = new RegExp(String.raw`\b(\d{1,2})(?:st|nd|rd|th)?\.?\s+(?:of\s+)?${mon}(?:\s+(\d{4}))?`).exec(t))) return fix(+m[1], MONTHS.indexOf(m[2]), m[3]);
    if ((m = new RegExp(String.raw`\b${mon}\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?`).exec(t))) return fix(+m[2], MONTHS.indexOf(m[1]), m[3]);
    if ((m = /\b(sun|mon|tue|wed|thu|fri|sat)(?:day|s|sday|nesday|r|rs|rsday|urday)?\b/.exec(t))) {
      const want = DAYS.findIndex(d => d.startsWith(m[1]));
      const add = (want - today.getDay() + 7) % 7 || 7;   // the coming one; today's weekday means a week from today
      const x = new Date(today); x.setDate(x.getDate() + add); return x;
    }
    if (/\btomorrow\b/.test(t)) { const x = new Date(today); x.setDate(x.getDate() + 1); return x; }
    if (/\bnext\s+week\b/.test(t)) { const x = new Date(today); x.setDate(x.getDate() + ((8 - x.getDay()) % 7 || 7)); return x; }
    if (/\bnext\s+month\b/.test(t)) return new Date(today.getFullYear(), today.getMonth() + 1, 1);
    if (/\bnext\s+year\b/.test(t)) return new Date(today.getFullYear() + 1, 0, 1);
    if ((m = /\b(?:in|for|of)\s+(?:the\s+next\s+)?(\d+|a|an|one|two|three|six)\s+(day|week|month|year)s?\b/.exec(t))) {
      const n = { a: 1, an: 1, one: 1, two: 2, three: 3, six: 6 }[m[1]] || +m[1], x = new Date(today);
      if (m[2] === "day") x.setDate(x.getDate() + n);
      if (m[2] === "week") x.setDate(x.getDate() + 7 * n);
      if (m[2] === "month") x.setMonth(x.getMonth() + n);
      if (m[2] === "year") x.setFullYear(x.getFullYear() + n);
      return x;
    }
    return null;
  }
  const ADDR = /\b(?:0x)?([0-9a-f]{96})\b/gi;
  const SHORT_ADDR = /\b[0-9a-f]{20,95}\b|\b[0-9a-f]{97,}\b/i;
  /* names from the wallet's address book in a clause, longest first so "Mia Lee" beats "Mia" */
  function names(clause, book) {
    const found = []; let lower = clause.toLowerCase();
    for (const c of [...book].sort((a, b) => b.name.length - a.name.length)) {
      const n = c.name.toLowerCase().trim();
      if (!n || found.some(f => f.addr === c.addr)) continue;
      const re = new RegExp(String.raw`(^|[^\p{L}\p{N}])` + n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + String.raw`($|[^\p{L}\p{N}])`, "u");
      if (re.test(lower)) { found.push(c); lower = lower.replace(re, "$1 $2"); }   // a name found is taken out, so "Mia Lee" is not also "Mia"
    }
    return found;
  }
  const addrs = clause => [...new Set([...clause.matchAll(ADDR)].map(m => m[1].toLowerCase()))];

  /* clauses: split at line ends, ; and sentence ends, then at ", and" / " and " / "," before a new instruction */
  const STARTS = String.raw`(?:only|just|at\s+most|max|maximum|no\s+more|not\s+more|never|nothing|no\s+payments?|lock|locked|freeze|above|over|more\s+than|anything|everything|payments?|limit|cap|up\s+to|from|after|before|until|till|not\s+before|co-?sign|cosign|the\s+guardian|guardian|require|need|needs|keep|block|allow|only\s+on|on\s+weekdays|between)\b`;
  function clauses(text) {
    return String(text || "").replace(/\r/g, "")
      .replace(/(\d)\.(?=\d)/g, "$1\u0001")   // the dot inside 1.000 or 2.5k is not a sentence end
      .split(/\n|;|\./).map(x => x.replace(/\u0001/g, "."))
      .flatMap(s => s.split(new RegExp(String.raw`,\s*(?:and\s+|but\s+)?(?=${STARTS})|\s+(?:and|but|plus)\s+(?=${STARTS})`, "i")))
      .map(s => s.replace(/^[\s,–—-]*(?:and|but|also|plus|then)?\s*/i, "").replace(/[\s,]+$/, "").trim())
      .filter(s => s && /[\p{L}\p{N}]/u.test(s));
  }

  /* one clause → one item. kind: only | cap | from | co | freeze (understood), or no (said why, nothing built) */
  function readClause(c, ctx) {
    const t = c.toLowerCase(), item = { src: c };
    const period = /\b(?:per|a|each|every|in\s+(?:a|one))\s+(day|week|month|hour|year)\b|\b(daily|weekly|monthly|hourly|in\s+total|altogether|combined|summed?)\b/.exec(t);
    const co = /\b(co-?sign\w*|countersign\w*|second\s+signature|two\s+signatures|2fa|authenticator|approv\w*|guardian|sign(?:s|ed)?\s+(?:it|too|as\s+well|off))\b/.test(t);
    const dayWords = /\b(before|until|till|not\s+until|unlock\w*|lock\w*|from|after|starting|since)\b/.test(t) && day(t, ctx.now);
    if (/\b(week\s*days?|weekends?|working\s+days|office\s+hours|business\s+hours|at\s+night|by\s+day|o'?clock|\d{1,2}\s*(?:am|pm)|\d{1,2}:\d{2})\b/.test(t) || /\bbetween\s+\d{1,2}\s+and\s+\d{1,2}\b(?!\s*(?:k|000|,))/.test(t))
      return { ...item, kind: "no", code: "clock", why: "Hours and weekdays need arithmetic on the block time. The wallet's blocks have no such block yet; a date is possible." };
    if (/\b(balance|keep\s+at\s+least|minimum|leave\s+at\s+least|never\s+below|savings\s+of)\b/.test(t))
      return { ...item, kind: "no", code: "balance", why: "The testnet does not let a personal rule read the balance (i2), so no rule can keep a minimum." };
    if (/\b(never|not|no\s+payments?)\s+(?:send\s+|pay\s+)?to\b|\bblock(?:list)?\s+(?:payments\s+to\s+)?(?:0x)?[0-9a-f]{6,}|\bblacklist|\bban\b/.test(t))
      return { ...item, kind: "no", code: "blocklist", why: "The wallet has no block for a list of forbidden addresses: a thief makes a new address in a second. “Only to …” keeps out every address you did not name." };
    if (/\b(freeze|frozen|lock\s+(?:it|everything|the\s+account|my\s+account)\b(?!.*\b(?:until|till|for|before)\b)|block\s+(?:everything|all)|nothing\s+(?:leaves|goes\s+out|may\s+leave)\s*$|no\s+payments\s+at\s+all)\b/.test(t) && !dayWords)
      return { ...item, kind: "freeze" };
    if (co) {
      if (period) return { ...item, kind: "no", code: "period", why: "A rule sees one payment at a time, so it cannot add up a " + (period[1] || "day") + ". Say the limit for one payment, for example “above 1,000 the Guardian co-signs”." };
      const lim = numAt(t, String.raw`(?:above|over|more\s+than|beyond|exceeding|from|>=?|starting\s+at)`) ?? numAt(t, String.raw`(?:^|\s)`);
      if (lim == null) return { ...item, kind: "no", code: "co-amount", why: "Say from which amount on a co-signature is needed, for example “above 1,000 the Guardian co-signs”." };
      if (lim < 1 || lim > MAX_AMOUNT) return { ...item, kind: "no", code: "range", why: "Amounts run from 1 to 16,777,215 test AGRS." };
      let who = addrs(c).map(a => ({ addr: a, name: null }));
      for (const n of names(c, ctx.book || [])) if (!who.some(w => w.addr === n.addr)) who.push({ addr: n.addr, name: n.name });
      let guardian = false;
      if (!who.length || /\bguardian|authenticator|2fa\b/.test(t)) {
        if (ctx.guardian && !who.some(w => w.addr === ctx.guardian)) { who.unshift({ addr: ctx.guardian, name: "Guardian" }); guardian = true; }
        else if (!ctx.guardian && !who.length) return { ...item, kind: "no", code: "co-who", why: SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : "Name the co-signer: an address, a name from your wallet's address book, or the Guardian." };
      }
      const more = who.length > 1;
      return { ...item, kind: "co", limit: lim, who: who.slice(0, 1), guardian: guardian && who.length >= 1 && who[0].addr === ctx.guardian,
        note: more ? "The wallet takes one co-signer per rule; the first one named is used." : null };
    }
    if (/\b(only|just|exclusively|whitelist|allow\s*list)\b/.test(t) && !/\bonly\s+(?:after|from|before|until|above|below|up\s+to|\d)/.test(t)) {
      let who = addrs(c).map(a => ({ addr: a, name: null }));
      if (/\b(my\s+(?:address\s+)?book|my\s+contacts|my\s+people|my\s+friends|people\s+i\s+know|known\s+addresses)\b/.test(t)) who.push(...(ctx.book || []).map(b => ({ addr: b.addr, name: b.name })));
      for (const n of names(c, ctx.book || [])) who.push({ addr: n.addr, name: n.name });
      who = who.filter((w, i) => isAddr(w.addr) && who.findIndex(x => x.addr === w.addr) === i && w.addr !== ctx.me);
      if (!who.length) return { ...item, kind: "no", code: "only-who", why: SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : (ctx.book || []).length ? "Name who may be paid: an address, or a name from your wallet's address book." : "Name who may be paid by address, or put them in your wallet's address book first and use their names." };
      return { ...item, kind: "only", who: who.slice(0, MAX_ONLY), note: who.length > MAX_ONLY ? "The wallet takes up to 5 names; the first 5 are used." : null };
    }
    if (dayWords && !/\b(above|over|max|at\s+most|limit|up\s+to)\s+\d/.test(t)) {
      const d = dayWords;
      const ts = Math.floor(d.getTime() / 1000);
      if (/\b(after|until|till)\b/.test(t) && /\b(only\s+)?(?:allowed|possible|payments?\s+(?:are\s+)?(?:fine|ok))\s+until\b|\bstop\w*\s+(?:on|at|after)\b|\bno\s+more\s+after\b/.test(t))
        return { ...item, kind: "no", code: "end", why: "An end date (payments only until a day) is not one of the wallet's blocks; “nothing before a date” is." };
      return { ...item, kind: "from", from: ts, past: d.getTime() <= ctx.now.getTime() };
    }
    if (period) return { ...item, kind: "no", code: "period", why: "A rule sees one payment at a time (the testnet lets a personal rule read only [t]), so it cannot add up a " + (period[1] || "day") + ". Use a limit per payment instead, for example “at most 500 per payment”." };
    const capM = numAt(t, String.raw`(?:at\s+most|max(?:imum)?|no\s+more\s+than|not\s+more\s+than|never\s+more\s+than|up\s+to|limit(?:ed)?\s+(?:of\s+|to\s+|at\s+)?|cap(?:ped)?\s+(?:of\s+|at\s+)?|<=|≤)`);
    const capLt = numAt(t, String.raw`(?:less\s+than|under|below|<)`);
    const capOver = numAt(t, String.raw`(?:nothing|no\s+payments?|block\w*|stop|refuse)\s+(?:above|over|more\s+than|beyond|bigger\s+than|larger\s+than)`) ?? (/\b(block|stop|refuse|nothing|no\s+payments?)\b/.test(t) ? numAt(t, String.raw`(?:above|over|more\s+than)`) : null);
    const cap = capM ?? (capLt != null ? capLt - 1 : null) ?? capOver ?? (/\bmax\b/.test(t) ? numAt(t, String.raw`(?:^|\s)`) : null);
    if (cap != null) {
      if (cap < 1 || cap >= MAX_AMOUNT) return { ...item, kind: "no", code: "range", why: "A limit per payment runs from 1 to 16,777,214 test AGRS." };
      return { ...item, kind: "cap", cap };
    }
    if (/\b(before|until|till|after|from|lock)\b/.test(t)) return { ...item, kind: "no", code: "day", why: "Which day? Write it like 2026-12-01, 1 Dec, Friday, tomorrow or in 90 days." };
    return { ...item, kind: "no", code: "unknown", why: "Not understood. The wallet's rule has four blocks: only to some addresses, at most an amount per payment, nothing before a day, and a co-signature above an amount." };
  }

  /* the whole text → the wallet's rule {freeze, only, cap, from, co} and the items it came from */
  function parse(text, ctx) {
    ctx = { now: new Date(), book: [], guardian: null, me: null, ...(ctx || {}) };
    const items = clauses(text).slice(0, 12).map(c => readClause(c, ctx));
    const r = { freeze: false, only: [], cap: null, from: null, co: null };
    const seen = {};
    for (const it of items) {
      if (it.kind === "no") continue;
      if (seen[it.kind] && it.kind !== "only") { it.dup = true; }   // the last one said wins, and the earlier one says so
      if (seen[it.kind] && it.kind !== "only") seen[it.kind].replaced = true;
      seen[it.kind] = it;
      if (it.kind === "freeze") r.freeze = true;
      if (it.kind === "only") for (const w of it.who) if (!r.only.includes(w.addr) && r.only.length < MAX_ONLY) r.only.push(w.addr);
      if (it.kind === "cap") r.cap = it.cap;
      if (it.kind === "from") r.from = it.from;
      if (it.kind === "co") r.co = { limit: it.limit, who: it.who.map(w => w.addr), names: it.who.map(w => w.name), need: "any" };
    }
    const any = r.freeze || r.only.length || r.cap != null || r.from != null || r.co;
    return { rule: any ? r : null, items, text: any ? build(r) : null };
  }

  /* test payments that show each block at work: one that passes every block, then one change at a time.
     time: seconds, day-rounded so the same rule gives the same tests all day (the checker caches by rule and tests) */
  function tests(r, ctx) {
    if (!r) return [];
    ctx = { now: new Date(), stranger: "5e".repeat(48), ...(ctx || {}) };
    const noon = Math.floor(ctx.now.getTime() / 86400000) * 86400 + 43200;
    const later = r.from != null ? Math.max(noon, r.from + 43200) : noon;
    const okTo = r.only && r.only.length ? r.only[0] : ctx.stranger;
    const small = Math.max(1, Math.min(r.cap != null ? r.cap : 100, r.co ? r.co.limit : 100, 100));
    const base = { amount: small, to: okTo, ts: later, signed: [] };
    const out = [{ ...base, says: "an ordinary payment" }];
    if (r.cap != null) {
      out.push({ ...base, amount: r.cap, says: "exactly your limit", signed: r.co && r.cap > r.co.limit ? [r.co.who[0]] : [] });
      if (r.cap + 1 <= MAX_AMOUNT) out.push({ ...base, amount: r.cap + 1, says: "one above your limit", signed: r.co && r.cap + 1 > r.co.limit ? [r.co.who[0]] : [] });
    }
    if (r.co) {
      const a = Math.min(MAX_AMOUNT, r.co.limit + 1);
      out.push({ ...base, amount: a, says: "above the line, not co-signed" });
      out.push({ ...base, amount: a, signed: [r.co.who[0]], says: "above the line, co-signed" });
    }
    if (r.only && r.only.length) out.push({ ...base, to: ctx.stranger, says: "to a stranger" });
    if (r.from != null) out.push({ ...base, ts: Math.min(noon, r.from - 43200), says: "before your day" });
    return (r.freeze ? [{ ...base, says: "any payment" }] : out).slice(0, 8).map(p => ({ ...p, stop: judge(r, p) }));
  }
  /* a block that never changes an answer: with and without it, every case the exact reading lists ends the same */
  function idle(r, cases) {
    if (!r || r.freeze) return [];
    return parts(r).map(x => x[0]).filter(k => cases.every(p => !judge(r, p).length === !judge(without(r, k), p).length));
  }

  /* a Tau text that is one of the wallet's rules, read back into its blocks (as wallet/index.html readRule does); null for
     any other rule. Proven by writing it again: the blocks must give the same text. */
  function fromTau(text) {
    const flat = x => String(x || "").replace(/\s+/g, "");
    if (flat(text) === flat(FREEZE)) return { freeze: true, only: [], cap: null, from: null, co: null };
    const r = { freeze: false, only: [], cap: null, from: null, co: null };
    r.only = [...new Set([...String(text).matchAll(/i4\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})/gi)].map(m => m[1].toLowerCase()))];
    const cap = /i1\[t\]:bv\[24\]\s*>=\s*\{\s*#x([0-9a-f]+)/i.exec(text);
    if (cap) r.cap = parseInt(cap[1], 16) - 1;
    const from = /i5\[t\]:bv\[64\]\s*<\s*\{\s*(\d+)\s*\}/i.exec(text);
    if (from) r.from = Number(from[1]);
    const lim = /i1\[t\]:bv\[24\]\s*>\s*\{\s*#x([0-9a-f]+)/i.exec(text);
    const slot = /i18\[t\]:bv\[384\]\s*=\s*\{\s*#x([0-9a-f]{96})/i.exec(text);
    if (lim && slot) r.co = { limit: parseInt(lim[1], 16), who: [slot[1].toLowerCase()], names: [null], need: "any" };
    const again = build(r);
    return again && flat(again) === flat(text) ? r : null;
  }

  const api = { parse, build, fromTau, judge, tests, idle, clauses, day, num, MAX_AMOUNT, MAX_ONLY };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RuleWords = api;
})(typeof window !== "undefined" ? window : globalThis);
