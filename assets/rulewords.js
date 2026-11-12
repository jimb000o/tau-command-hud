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
  /* 1,000 · 1.000 · 1 000 · 1k · 2.5k · 1m. Part of a coin (1.5 or 1,5) comes back as it is, so the reader can say
     "whole numbers only" and never rounds a limit on its own. */
  function amount(s) {
    const m = /^(\d{1,3}(?:[,.' ]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|m|thousand|million)?$/i.exec(String(s).trim());
    if (!m) return null;
    let n = /^\d{1,3}(?:[,.' ]\d{3})+$/.test(m[1]) ? Number(m[1].replace(/[,.' ]/g, "")) : Number(m[1].replace(",", "."));
    const u = (m[2] || "").toLowerCase();
    if (u === "k" || u === "thousand") n *= 1000;
    if (u === "m" || u === "million") n *= 1e6;
    return isFinite(n) ? Math.round(n * 1e6) / 1e6 : null;
  }
  function num(s) { const n = amount(s); return n == null ? null : Math.round(n); }
  const NUM = String.raw`(\d{1,3}(?:[,.' ]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|m|thousand|million)?\b`;
  const numAt = (text, before) => { const m = new RegExp(before + String.raw`\s*` + NUM, "i").exec(text); return m ? amount(m[1] + (m[2] || "")) : null; };
  /* a day: 2026-12-01 · 1.12.2026 · 1 dec (2026) · december 1(st)(, 2026) · friday · tomorrow · next week/month ·
     in 90 days · until 2028 (its first day) · end of 2027, end of the year, end of the month (the day after) */
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
    if (/\bnext\s+month\b|\bend\s+of\s+(?:the|this)\s+month\b/.test(t)) return new Date(today.getFullYear(), today.getMonth() + 1, 1);
    if (/\bnext\s+year\b|\bend\s+of\s+(?:the|this)\s+year\b/.test(t)) return new Date(today.getFullYear() + 1, 0, 1);
    if ((m = /\b(?:in|for|of)\s+(?:the\s+next\s+)?(\d+|a|an|one|two|three|six)\s+(day|week|month|year)s?\b/.exec(t))) {
      const n = { a: 1, an: 1, one: 1, two: 2, three: 3, six: 6 }[m[1]] || +m[1], x = new Date(today);
      if (m[2] === "day") x.setDate(x.getDate() + n);
      if (m[2] === "week") x.setDate(x.getDate() + 7 * n);
      if (m[2] === "month") x.setMonth(x.getMonth() + n);
      if (m[2] === "year") x.setFullYear(x.getFullYear() + n);
      return x;
    }
    if ((m = /\b(?:end\s+of|after)\s+(?:the\s+year\s+)?(20\d{2})\b(?![-./]\d)/.exec(t))) return new Date(+m[1] + 1, 0, 1);
    if ((m = /\b(?:until|till|before|from|since|starting|by|in)\s+(?:the\s+(?:year|start\s+of)\s+)?(20\d{2})\b(?![-./]\d)/.exec(t))) return new Date(+m[1], 0, 1);
    return null;
  }
  const ADDR = /\b(?:0x)?([0-9a-f]{96})\b/gi;
  const SHORT_ADDR = /\b[0-9a-f]{20,95}\b|\b[0-9a-f]{97,}\b/i;
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const nameRe = n => new RegExp(String.raw`(^|[^\p{L}\p{N}])` + esc(n) + String.raw`($|[^\p{L}\p{N}])`, "u");
  /* names from the wallet's address book in a clause, longest first so "Mia Lee" beats "Mia" */
  function names(clause, book) {
    const found = []; let lower = clause.toLowerCase();
    for (const c of [...book].sort((a, b) => b.name.length - a.name.length)) {
      const n = c.name.toLowerCase().trim();
      if (!n || found.some(f => f.addr === c.addr)) continue;
      const re = nameRe(n);
      if (re.test(lower)) { found.push(c); lower = lower.replace(re, "$1 $2"); }   // a name found is taken out, so "Mia Lee" is not also "Mia"
    }
    return found;
  }
  const addrs = clause => [...new Set([...clause.matchAll(ADDR)].map(m => m[1].toLowerCase()))];

  /* ---- the words a part may use. A word outside them was not read, and the part says so (never dropped in silence):
     "at most 100 to Mia" is a limit for everybody, and "to Mia" is shown as not used. ---- */
  const set = s => new Set(s.trim().split(/\s+/));
  const COMMON = set(`a an the i i'd i'm me my mine myself we our us you your it its this that these those there here is are be been being was were am
    will would shall should can could may might must do does did done doing don't dont doesn't doesnt cannot can't cant won't wont not no never none nothing nobody
    anything everything any all every each one single whole to of in on at by for with as than then and or but also plus so if when once while into onto
    please want wants wanted like let lets make makes set sets put puts have has had having need needs needed require requires required get gets
    out up off per more most less least much many over above below under beyond exceeding exceeds exceed bigger larger greater smaller higher lower equal
    max maximum limit limited limits cap capped caps ceiling amount amounts value size big large small tiny
    payment payments pay pays paid paying send sends sent sending spend spends spent spending transfer transfers transferred transaction transactions tx txs outgoing
    money funds coins coin tokens token agrs test wallet account savings rule rules leave leaves leaving go goes going move moves moved
    allow allowed allows block blocked blocks blocking stop stops stopped refuse refused refuses reject rejected deny denied forbid forbidden halt pause paused suspend
    lock locked locks unlock unlocked unlocks freeze frozen hold held keep kept ever always whatsoever k m thousand million time
    someone somebody anyone anybody everyone everybody else other others who whom whoever address addresses only just
    before until till after since starting start starts from unless except`);
  const DAYW = set(`sunday monday tuesday wednesday thursday friday saturday sun mon tue tues wed thu thur thurs fri sat
    january february march april june july august september october november december jan feb mar apr may jun jul aug sep sept oct nov dec
    today tomorrow tonight next coming now later day days week weeks month months year years date end st nd rd th`);
  const SIGNW = set(`signature signatures second two another extra both guardian authenticator 2fa code app too well signer`);
  const BOOKW = set(`exclusively whitelist allowlist list book contacts people friends known know stranger strangers unknown new`);
  const SIGN_RE = /^(?:co-?sign|countersign|approv|confirm|sign)/;
  const DET = set(`my our his her their the a an`), PREP = set(`to from by for with until till before after on in at except than over above under below per`);
  /* the words of one clause that no pattern read, as they were written: [“to Mia”, “before Friday”] */
  function unread(c, ctx, kinds, bare) {
    const has = k => kinds.includes(k);
    const blank = (s, re) => s.replace(re, x => " ".repeat(x.length));
    let s = blank(c.toLowerCase().replace(/[’`]/g, "'"), ADDR);
    s = blank(s, /\bfrom\s+now(?:\s+on)?\b|'s\b/g);
    if (has("only") || has("co")) for (const b of [...(ctx.book || [])].sort((a, b) => b.name.length - a.name.length)) {
      const n = b.name.toLowerCase().trim(); if (!n) continue;
      s = s.replace(new RegExp(nameRe(n).source, "gu"), (x, a, z) => a + " ".repeat(x.length - a.length - z.length) + z);
    }
    const numbers = has("cap") || has("co") || has("from"), toks = [];
    for (const m of s.matchAll(/[\p{L}][\p{L}\p{N}'-]*|\d[\d.,']*/gu)) {
      const w = m[0].replace(/[-']+$/, "");
      const ok = /^\d/.test(w) ? numbers : COMMON.has(w) || (has("from") && DAYW.has(w)) || (has("co") && (SIGNW.has(w) || SIGN_RE.test(w))) || (has("only") && BOOKW.has(w));
      toks.push({ at: m.index, end: m.index + m[0].length, ok, w });
    }
    const out = [];
    for (let i = 0; i < toks.length; i++) {
      if (toks[i].ok) continue;
      let a = i, z = i;
      while (z + 1 < toks.length && !toks[z + 1].ok) z++;
      if (a > 0 && DET.has(toks[a - 1].w)) a--;                 // “my brother”
      if (!bare && a > 0 && PREP.has(toks[a - 1].w)) a--;       // “to Mia”, “before Friday”
      out.push(c.slice(toks[a].at, toks[z].end));
      i = z;
    }
    return out;
  }

  /* clauses: split at line ends, ; and sentence ends, then at ", and" / " and " / "," before a new instruction */
  const STARTS = String.raw`(?:only|just|at\s+most|max|maximum|no\s+more|not\s+more|never|nothing|no\s+payments?|lock|locked|freeze|above|over|more\s+than|anything|everything|payments?|limit|cap|up\s+to|from|after|before|until|till|not\s+before|co-?sign|cosign|the\s+guardian|guardian|require|need|needs|keep|block|allow|only\s+on|on\s+weekdays|between|stop|don'?t|do\s+not)\b`;
  const CO_RE = /\b(co-?sign\w*|countersign\w*|second\s+signature|two\s+signatures|signatures?|2fa|authenticator|approv\w*|confirm(?:s|ed|ation)?|guardian|sign(?:s|ed)?\s+(?:it|too|as\s+well|off)|(?:unless|until|if|when|once)\b.*\bsigns?|signs?\s*$)\b/;
  function clauses(text) {
    const cs = String(text || "").replace(/\r/g, "").replace(/[’`]/g, "'")
      .replace(/(\d)\.(?=\d)/g, "$1\u0001")   // the dot inside 1.000 or 2.5k is not a sentence end
      .split(/\n|;|\./).map(x => x.replace(/\u0001/g, "."))
      .flatMap(s => s.split(new RegExp(String.raw`,\s*(?:and\s+then\s+|and\s+|but\s+|then\s+)?(?=${STARTS})|\s+(?:and\s+then|and|but|plus|then)\s+(?=${STARTS})`, "i")))
      .map(s => s.replace(/^[\s,–—-]*(?:and|but|also|plus|then)?\s*/i, "").replace(/[\s,]+$/, "").trim())
      .filter(s => s && /[\p{L}\p{N}]/u.test(s));
    /* "above 1,000, the Guardian co-signs": the amount and who signs belong to one part */
    const lead = new RegExp(String.raw`^(?:for\s+)?(?:(?:all\s+|any\s+)?(?:payments?|amounts?|anything|everything)\s+)?(?:above|over|more\s+than|beyond|from)\s+` + NUM + String.raw`(?:\s+test)?(?:\s+agrs)?$`, "i");
    for (let i = 0; i + 1 < cs.length; i++) if (lead.test(cs[i]) && CO_RE.test(cs[i + 1].toLowerCase()) && !/\d/.test(cs[i + 1].replace(ADDR, ""))) cs.splice(i, 2, cs[i] + " " + cs[i + 1]);
    return cs;
  }

  const OVER = String.raw`(?:above|over|more\s+than|beyond|exceeding|bigger\s+than|larger\s+than|greater\s+than|higher\s+than|>)`;
  const HALT = String.raw`(?:block|stop|refuse|halt|pause|reject|deny|forbid|freeze|suspend|lock)\w*`;
  const EXCEPT_SRC = String.raw`(?:except(?:\s+for)?|unless|apart\s+from|aside\s+from|other\s+than|besides|excluding|save\s+for|but\s+not|with\s+the\s+exception\s+of)`;
  const EXCEPT = new RegExp(String.raw`\b${EXCEPT_SRC}\b`);
  const NOBODY = String.raw`(?:nothing|nobody|no\s+one|none|no\s+(?:payments?|transfers?|money)|never|don'?t|do\s+not|${HALT})`;
  const FROZEN = new RegExp(String.raw`\b(?:freeze|frozen|(?:lock|pause|halt|suspend|block|stop)\s+(?:it|everything|(?:the|my|this)\s+(?:account|wallet))|${HALT}\s+(?:(?:all|every|any|my|outgoing)\s+)*(?:everything|all|payments?|transfers?|transactions?|spending|sending|paying))\b|\bnothing\s+(?:leaves|goes\s+out|gets\s+out|may\s+leave|can\s+leave|may\s+go\s+out)\s*$|\bno\s+(?:more\s+)?(?:payments|transfers|transactions|spending)(?:\s+at\s+all)?\s*$`);
  const whole = n => Number.isInteger(n);
  const WHOLE = "Amounts on the testnet are whole numbers of test AGRS. Write the amount without a part after the point, for example 1 or 2.";
  const said = list => list.map(x => "“" + x + "”").join(", ");

  /* one clause → one item, or two when it names who may be paid and a limit. kind: only | cap | from | co | freeze
     (understood), or no (said why, nothing built). unused: words of an understood part that are not in the rule. */
  function readClause(c, ctx) {
    const t = c.toLowerCase(), item = { src: c }, book = ctx.book || [];
    const no = (code, why) => ({ ...item, kind: "no", code, why });
    const done = (kinds, ...items) => { const u = unread(c, ctx, kinds); if (u.length) items[0].unused = said(u); return items.length > 1 ? items : items[0]; };
    const period = /\b(?:per|a|each|every|in\s+(?:a|one))\s+(day|week|month|hour|year)\b|\b(daily|weekly|monthly|hourly|in\s+total|altogether|combined|summed?)\b/.exec(t);
    const co = CO_RE.test(t);
    const dayWords = /\b(before|until|till|not\s+until|unlock\w*|lock\w*|from|after|starting|since|by|end\s+of)\b/.test(t) && day(t, ctx.now);
    const people = () => { let who = addrs(c).map(a => ({ addr: a, name: null })); for (const n of names(c, book)) who.push({ addr: n.addr, name: n.name }); return who.filter((w, i) => isAddr(w.addr) && who.findIndex(x => x.addr === w.addr) === i); };
    const capOf = () => {
      const capM = numAt(t, String.raw`(?:at\s+most|max(?:imum)?(?:\s+of)?|no\s+more\s+than|not\s+more\s+than|never\s+more\s+than|up\s+to|limit(?:ed)?\s+(?:of\s+|to\s+|at\s+|is\s+)?|cap(?:ped)?\s+(?:of\s+|at\s+|is\s+)?|(?:only|just)\s+(?=\d)|<=|≤)`);
      const capLt = numAt(t, String.raw`(?:less\s+than|under|below|<)`);
      const capOver = numAt(t, String.raw`(?:nothing|no\s+payments?|block\w*|stop|refuse)\s+${OVER}`) ?? (new RegExp(String.raw`\b(?:${NOBODY}|not|cannot|can'?t|won'?t|may\s+not|must\s+not)\b`).test(t) ? numAt(t, OVER) : null);
      return capM ?? (capLt != null ? (whole(capLt) ? capLt - 1 : capLt) : null) ?? capOver ?? (/\bmax\b/.test(t) ? numAt(t, String.raw`(?:^|\s)`) : null);
    };
    if (/\b(week\s*days?|weekends?|working\s+days|office\s+hours|business\s+hours|at\s+night|by\s+day|o'?clock|\d{1,2}\s*(?:am|pm)|\d{1,2}:\d{2})\b/.test(t) || /\bbetween\s+\d{1,2}\s+and\s+\d{1,2}\b(?!\s*(?:k|000|,))/.test(t))
      return no("clock", "Hours and weekdays need arithmetic on the block time. The wallet's blocks have no such block yet; a date is possible.");
    if (/\b(balance|keep\s+at\s+least|minimum|leave\s+at\s+least|never\s+below|savings\s+of)\b/.test(t))
      return no("balance", "The testnet does not let a personal rule read the balance (i2), so no rule can keep a minimum.");
    /* "block payments to strangers" is the wallet's list said the other way round */
    const strangers = new RegExp(String.raw`\b${NOBODY}\b.*\b(?:strangers?|unknown|people\s+i\s+don'?t\s+know|anyone\s+i\s+don'?t\s+know|new\s+addresses)\b`).test(t);
    /* "block everything except Mia", "nothing to anyone but Mia": also the list */
    const butTo = !co && new RegExp(String.raw`\b${NOBODY}\b.*\b(?:${EXCEPT_SRC}|but)\b`).test(t) && !/\d/.test(t.replace(ADDR, ""));
    const unlessSigns = co && /\b(?:unless|except\s+(?:if|when))\b.*\b(?:co-?sign|sign|approv|confirm)\w*/.test(t);
    if (EXCEPT.test(t) && !unlessSigns && !butTo)
      return no("except", "The wallet's four blocks have no exception: a limit, a list or a day counts for every payment. Say it without the exception, or write the rule in Tau by hand; the Playground has an example with an exception (Limit, Bob exempt).");
    if (!strangers && !butTo && (/\b(never|not|no\s+payments?)\s+(?:send\s+|pay\s+)?to\b|\bblock(?:list)?\s+(?:payments\s+to\s+)?(?:0x)?[0-9a-f]{6,}|\bblacklist|\bban\b/.test(t) || (new RegExp(String.raw`\b${HALT}\b.*\bto\b`).test(t) && !co && !/\d/.test(t.replace(ADDR, "")) && (people().length || unread(c, ctx, ["freeze"]).length))))
      return no("blocklist", "The wallet has no block for a list of forbidden addresses: a thief makes a new address in a second. “Only to …” keeps out every address you did not name.");
    if (FROZEN.test(t) && !dayWords && !co && !strangers && !butTo && !/\d/.test(t.replace(ADDR, "")) && !people().length)
      return done(["freeze"], { ...item, kind: "freeze" });
    if (co) {
      if (period) return no("period", "A rule sees one payment at a time, so it cannot add up a " + (period[1] || "day") + ". Say the limit for one payment, for example “above 1,000 the Guardian co-signs”.");
      const lim = numAt(t, String.raw`(?:above|over|more\s+than|beyond|exceeding|from|>=?|starting\s+at)`) ?? numAt(t, String.raw`(?:^|\s)`);
      if (lim == null) return no("co-amount", "Say from which amount on a co-signature is needed, for example “above 1,000 the Guardian co-signs”.");
      if (!whole(lim)) return no("whole", WHOLE);
      if (lim < 1 || lim > MAX_AMOUNT) return no("range", "Amounts run from 1 to 16,777,215 test AGRS.");
      const who = people(), named = /\bguardian|authenticator|2fa\b/.test(t), strange = unread(c, ctx, ["co"], true);
      let guardian = false;
      if (!who.length && !named && strange.length)   // "unless my brother signs": somebody is named, and this page does not know their address
        return no("co-who", SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : said(strange) + " is not in your wallet's address book. Write the co-signer's address, add the name to the address book first, or say “the Guardian”.");
      if (!who.length || named) {
        if (ctx.guardian && !who.some(w => w.addr === ctx.guardian)) { who.unshift({ addr: ctx.guardian, name: "Guardian" }); guardian = true; }
        else if (!ctx.guardian && !who.length) return no("co-who", SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : "Name the co-signer: an address, a name from your wallet's address book, or the Guardian.");
      }
      const more = who.length > 1;
      return done(["co"], { ...item, kind: "co", limit: lim, who: who.slice(0, 1), guardian: guardian && who.length >= 1 && who[0].addr === ctx.guardian,
        note: more ? "The wallet takes one co-signer per rule; the first one named is used." : null });
    }
    if (strangers || butTo || (/\b(only|just|exclusively|whitelist|allow\s*list)\b/.test(t) && !/\b(?:only|just)\s+(?:after|from|before|until|above|below|up\s+to|at\s+most|max|\d)/.test(t))) {
      let who = people();
      if (strangers || /\b(my\s+(?:address\s+)?book|my\s+contacts|my\s+people|my\s+friends|people\s+i\s+know|known\s+addresses)\b/.test(t)) who.push(...book.map(b => ({ addr: b.addr, name: b.name })));
      who = who.filter((w, i) => isAddr(w.addr) && who.findIndex(x => x.addr === w.addr) === i && w.addr !== ctx.me);
      const cap = capOf(), kinds = cap != null ? ["only", "cap"] : ["only"];
      if (!who.length) {
        const strange = strangers ? [] : unread(c, ctx, kinds, true);
        return no("only-who", SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut."
          : strange.length ? said(strange) + " is not in your wallet's address book. Write the address here, or add the name to the address book first."
          : book.length ? "Name who may be paid: an address, or a name from your wallet's address book." : "Name who may be paid by address, or put them in your wallet's address book first and use their names.");
      }
      const only = { ...item, kind: "only", who: who.slice(0, MAX_ONLY), note: who.length > MAX_ONLY ? "The wallet takes up to 5 names; the first 5 are used." : null };
      if (cap == null) return done(kinds, only);
      if (!whole(cap)) return no("whole", WHOLE);
      if (cap < 1 || cap >= MAX_AMOUNT) return no("range", "A limit per payment runs from 1 to 16,777,214 test AGRS.");
      return done(kinds, only, { ...item, kind: "cap", cap });
    }
    if (dayWords && !/\b(above|over|max|at\s+most|limit|up\s+to)\s+\d/.test(t)) {
      const d = dayWords;
      const ts = Math.floor(d.getTime() / 1000);
      if (/\b(after|until|till)\b/.test(t) && /\b(only\s+)?(?:allowed|possible|payments?\s+(?:are\s+)?(?:fine|ok))\s+until\b|\bstop\w*\s+(?:on|at|after)\b|\bno\s+more\s+after\b/.test(t))
        return no("end", "An end date (payments only until a day) is not one of the wallet's blocks; “nothing before a date” is.");
      return done(["from"], { ...item, kind: "from", from: ts, past: d.getTime() <= ctx.now.getTime() });
    }
    if (period) return no("period", "A rule sees one payment at a time (the testnet lets a personal rule read only [t]), so it cannot add up a " + (period[1] || "day") + ". Use a limit per payment instead, for example “at most 500 per payment”.");
    const cap = capOf();
    if (cap != null) {
      if (!whole(cap)) return no("whole", WHOLE);
      if (cap < 1 || cap >= MAX_AMOUNT) return no("range", "A limit per payment runs from 1 to 16,777,214 test AGRS.");
      return done(["cap"], { ...item, kind: "cap", cap });
    }
    if (/\b(before|until|till|after|from|lock)\b/.test(t)) return no("day", "Which day? Write it like 2026-12-01, 1 Dec, Friday, tomorrow or in 90 days.");
    const bare = numAt(t, String.raw`^(?:(?:for\s+)?(?:all\s+|any\s+)?(?:payments?|amounts?|anything|everything)\s+)?` + OVER);
    if (bare != null) return no("above-what", "Above that amount, then what? Write “nothing above 1,000” for a limit, or “above 1,000 the Guardian co-signs” for a second signature.");
    return no("unknown", "Not understood. The wallet's rule has four blocks: only to some addresses, at most an amount per payment, nothing before a day, and a co-signature above an amount.");
  }

  /* the whole text → the wallet's rule {freeze, only, cap, from, co} and the items it came from */
  function parse(text, ctx) {
    ctx = { now: new Date(), book: [], guardian: null, me: null, ...(ctx || {}) };
    const items = clauses(text).slice(0, 12).flatMap(c => readClause(c, ctx));
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
