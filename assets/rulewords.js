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
    if ((m = /\b(?:in|for|of|within|during)\s+(?:the\s+next\s+)?(\d+|a|an|one|two|three|six)\s+(day|week|month|year)s?\b/.exec(t))) {
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
    money funds coins coin tokens token agrs test test-agrs wallet account savings rule rules leave leaves leaving go goes going move moves moved
    allow allowed allows block blocked blocks blocking stop stops stopped refuse refused refuses reject rejected deny denied forbid forbidden halt pause paused suspend
    lock locked locks unlock unlocked unlocks freeze frozen hold held keep kept ever always whatsoever k m thousand million time
    someone somebody anyone anybody everyone everybody else other others who whom whoever address addresses only just
    before until till after since starting start starts from unless except apart aside besides excluding exception save within during without`);
  const DAYW = set(`sunday monday tuesday wednesday thursday friday saturday sun mon tue tues wed thu thur thurs fri sat
    january february march april june july august september october november december jan feb mar apr may jun jul aug sep sept oct nov dec
    today tomorrow tonight next coming now later day days week weeks month months year years date end st nd rd th two three six`);
  const SIGNW = set(`signature signatures second two another extra both guardian authenticator 2fa code app too well signer`);
  const BOOKW = set(`exclusively whitelist allowlist list book contacts people friends known know stranger strangers unknown new`);
  const SIGN_RE = /^(?:co-?sign|countersign|approv|confirm|sign)/;
  const DET = set(`my our his her their the a an`), PREP = set(`to from by for with until till before after on in at except than over above under below per`);
  /* the words of one clause that no pattern read, as they were written: [“to Mia”, “before Friday”] */
  function unread(c, ctx, kinds, bare, tr) {
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
      if (!tr && a > 0 && DET.has(toks[a - 1].w)) a--;                 // “my brother”
      if (!tr && !bare && a > 0 && PREP.has(toks[a - 1].w)) a--;       // “to Mia”, “before Friday”
      out.push(c.slice(toks[a].at, toks[z].end));
      i = z;
    }
    return out;
  }

  /* clauses: split at line ends, ; and sentence ends, then at ", and" / " and " / "," before a new instruction */
  const STARTS = String.raw`(?:only|just|at\s+most|max|maximum|no\s+more|not\s+more|never|nothing|no\s+payments?|lock|locked|freeze|above|over|more\s+than|anything|everything|payments?|limit|cap|up\s+to|from|after|before|until|till|not\s+before|co-?sign|cosign|the\s+guardian|guardian|require|need|needs|keep|block|allow|only\s+on|on\s+weekdays|between|stop|don'?t|do\s+not|nobody|no\s+one|under|below|less\s+than|per\s+(?:payment|transfer|transaction)\s+(?=\S))\b`;
  const CO_RE = /\b((?:only|just)\s+with\b|co-?sign\w*|countersign\w*|second\s+signature|two\s+signatures|signatures?|2fa|authenticator|approv\w*|confirm(?:s|ed|ation)?|guardian|sign(?:s|ed)?\s+(?:it|too|as\s+well|off)|(?:unless|until|if|when|once)\b.*\bsigns?|signs?\s*$)\b/;
  function clauses(text, tr) {
    const tidy = s => s.replace(/^[\s,–—-]*(?:(?:and|but|also|plus|then|please)\b)?[\s,]*/i, "").replace(/[\s,]+$/, "").trim();
    const plain = s => s.replace(MARKS, "").trim();
    const cs = String(text || "").replace(/\r/g, "").replace(/[’`]/g, "'")
      .replace(/(\d)\.(?=\d)/g, "$1\u0001")   // the dot inside 1.000 or 2.5k is not a sentence end
      .replace(/\b(max|min)\.(?=\s*\d)/gi, "$1")   // nor the one of "max. 500"
      .split(/\n|;|\./).map(x => x.replace(/\u0001/g, "."))
      .flatMap(s => s.split(new RegExp(String.raw`(?<!^\s*${EXCEPT_SRC}\b(?:(?!\b${NOBODY}\b)[^,])*),\s*(?:and\s+then\s+|and\s+|but\s+|then\s+)?(?=${STARTS})|\s+(?:and\s+then|and|but|plus|then)\s+(?=${STARTS})`, "i")))   // not after "Except Mia,": the exception belongs to what follows, as long as nothing was stopped yet
      .map(s => { const marks = s.match(MARKS), body = tidy(marks ? s.replace(MARKS, " ") : s); return marks && body ? body + marks.join("") : body; })   // a mark says where the words of another language end
      .filter(s => s && /[\p{L}\p{N}]/u.test(s));
    /* "above 1,000, the Guardian co-signs": the amount and who signs belong to one part */
    const lead = new RegExp(String.raw`^(?:for\s+)?(?:(?:all\s+|any\s+)?(?:payments?|amounts?|anything|everything)\s+)?(?:above|over|more\s+than|beyond|from)\s+` + NUM + String.raw`(?:\s+test)?(?:\s+agrs)?$`, "i");
    /* read from another language the amount may stand in another order: "above 1000 payments" */
    const leads = a => lead.test(a) || (!!tr && new RegExp(String.raw`\b(?:${OVER}|from)\s+` + NUM, "i").test(a) && (a.replace(ADDR, "").match(/\d[\d.,']*/g) || []).length === 1
      && !CO_RE.test(a.toLowerCase()) && !new RegExp(String.raw`\b(?:${NOBODY}|at\s+most|only|before|until|after|not|less)\b`, "i").test(a));
    for (let i = 0; i + 1 < cs.length; i++) { const a = plain(cs[i]), b = plain(cs[i + 1]); if (leads(a) && CO_RE.test(b.toLowerCase()) && !/\d/.test(b.replace(ADDR, ""))) cs.splice(i, 2, cs[i] + " " + cs[i + 1]); }
    /* "only to Mia, block everyone else": the second half says the first again, it is no freeze */
    for (let i = 0; i + 1 < cs.length; i++) { const a = plain(cs[i]), b = plain(cs[i + 1]); if (/\bonly\b/i.test(a) && !CO_RE.test(a.toLowerCase()) && ELSE.test(b) && !/\bonly\b/i.test(b) && !/\d/.test(b.replace(ADDR, ""))) cs.splice(i, 2, cs[i] + " " + cs[i + 1]); }
    return cs;
  }

  const OVER = String.raw`(?:above|over|more\s+than|beyond|exceeding|bigger\s+than|larger\s+than|greater\s+than|higher\s+than|>)`;
  const HALT = String.raw`(?:block|stop|refuse|halt|pause|reject|deny|forbid|freeze|suspend|lock)\w*`;
  const EXCEPT_SRC = String.raw`(?:except(?:\s+for)?|unless|apart\s+from|aside\s+from|other\s+than|besides|excluding|save\s+for|but\s+not|with\s+the\s+exception\s+of)`;
  const EXCEPT = new RegExp(String.raw`\b${EXCEPT_SRC}\b`);
  const NOBODY = String.raw`(?:nothing|nobody|no\s+one|none|no\s+(?:payments?|transfers?|money)|never|don'?t|do\s+not|${HALT})`;
  const FROZEN = new RegExp(String.raw`\b(?:freeze|frozen|(?:lock|pause|halt|suspend|block|stop)\s+(?:it|everything|(?:the|my|this)\s+(?:account|wallet))|${HALT}\s+(?:(?:all|every|any|my|outgoing)\s+)*(?:everything|all|payments?|transfers?|transactions?|spending|sending|paying))\b|\bnothing\s+(?:leaves|goes\s+out|gets\s+out|may\s+leave|can\s+leave|may\s+go\s+out)\s*$|\bno\s+(?:more\s+)?(?:payments|transfers|transactions|spending)(?:\s+at\s+all)?\s*$`);
  const DAYISH = String.raw`(?:\d|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|sun|mon|tue|wed|thu|fri|sat)[a-z]*\b|tomorrow|next\s|end\s|start\s|year\s)`;   // how a day begins
  const ELSE = new RegExp(String.raw`^(?=.*\b${NOBODY}\b).*\b(?:else|others?|the\s+rest)\b`, "i");
  const whole = n => Number.isInteger(n);
  const WHOLE = "Amounts on the testnet are whole numbers of test AGRS. Write the amount without a part after the point, for example 1 or 2.";
  const said = list => list.map(x => "“" + x + "”").join(", ");

  /* one clause → one item, or two when it names who may be paid and a limit. kind: only | cap | from | co | freeze
     (understood), or no (said why, nothing built). unused: words of an understood part that are not in the rule. */
  function readClause(c, ctx, part) {
    const tr = !!(part && part.tr), t = c.toLowerCase(), item = { src: part ? part.src : c }, book = ctx.book || [];   // tr: read from German, Chinese or Japanese
    const mine = list => (tr ? list.map(u => own(u, part)).filter((v, i, a) => v && a.indexOf(v) === i) : list);
    const left = (kinds, bare) => mine(unread(c, ctx, kinds, bare, tr));
    const no = (code, why) => ({ ...item, kind: "no", code, why });
    const done = (kinds, ...items) => { const u = left(kinds); if (u.length) items[0].unused = said(u); return items.length > 1 ? items : items[0]; };
    const halts = new RegExp(String.raw`\b${HALT}\b`).test(t), nobody = new RegExp(String.raw`\b${NOBODY}\b`).test(t), digitless = !/\d/.test(t.replace(ADDR, ""));
    const period = /\b(?:per|a|each|every|in\s+(?:a|one))\s+(day|week|month|hour|year)\b|\b(daily|weekly|monthly|hourly|in\s+total|altogether|combined|summed?)\b/.exec(t);
    const co = CO_RE.test(t);
    const dayWords = (tr || /\b(before|until|till|not\s+until|unlock\w*|lock\w*|from|after|starting|since|by|end\s+of|(?:in|for|within|during)\s+(?:the\s+next\s+)?(?:\d+|a|an|one|two|three|six)\s+(?:day|week|month|year)s?)\b/.test(t)) && day(t, ctx.now);
    const people = () => { let who = addrs(c).map(a => ({ addr: a, name: null })); for (const n of names(c, book)) who.push({ addr: n.addr, name: n.name }); return who.filter((w, i) => isAddr(w.addr) && who.findIndex(x => x.addr === w.addr) === i); };
    const capOf = () => {
      const capM = numAt(t, String.raw`(?:at\s+most|max(?:imum)?(?:\s+of)?|no\s+more\s+than|not\s+more\s+than|never\s+more\s+than|up\s+to|limit(?:ed)?\s+(?:of\s+|to\s+|at\s+|is\s+)?|cap(?:ped)?\s+(?:of\s+|at\s+|is\s+)?|(?:only|just)\s+(?=\d)|<=|≤)`);
      const capLt = numAt(t, String.raw`(?:less\s+than|under|below|<)`);
      const capOver = numAt(t, String.raw`(?:nothing|no\s+payments?|block\w*|stop|refuse)\s+${OVER}`) ?? (new RegExp(String.raw`\b(?:${NOBODY}|not|cannot|can'?t|won'?t|may\s+not|must\s+not)\b`).test(t) ? numAt(t, OVER) : null);
      return capM ?? (capLt != null ? (whole(capLt) ? capLt - 1 : capLt) : null) ?? capOver ?? (/\bmax\b/.test(t) || (tr && /\b(?:at\s+most|limit)\b/.test(t)) ? numAt(t, String.raw`(?:^|\s)`) : null);
    };
    if (/\b(?:don'?t|do\s+not|never|not|doesn'?t|no\s+need\s+to)\s+(?:ever\s+|have\s+to\s+)?(?:freeze|lock|block|stop|pause|halt|suspend|refuse|reject|deny|forbid)\w*\b/.test(t))
      return no("allow", "This says what should not be stopped. A wallet rule only stops payments: whatever no part of it stops goes through anyway.");
    if (/\b(week\s*days?|weekends?|working\s+days|office\s+hours|business\s+hours|at\s+night|by\s+day|o'?clock|\d{1,2}\s*(?:am|pm)|\d{1,2}:\d{2})\b/.test(t) || /\bbetween\s+\d{1,2}\s+and\s+\d{1,2}\b(?!\s*(?:k|000|,))/.test(t))
      return no("clock", "Hours and weekdays need arithmetic on the block time. The wallet's blocks have no such block yet; a date is possible.");
    if (/\b(balance|keep\s+at\s+least|minimum|leave\s+at\s+least|never\s+below|savings\s+of)\b/.test(t))
      return no("balance", "The testnet does not let a personal rule read the balance (i2), so no rule can keep a minimum.");
    /* "block payments to strangers" is the wallet's list said the other way round */
    const strangers = new RegExp(String.raw`\b${NOBODY}\b.*\b(?:strangers?|unknown|people\s+i\s+don'?t\s+know|anyone\s+i\s+don'?t\s+know|new\s+addresses)\b`).test(t) || (tr && nobody && /\bstrangers\b/.test(t));
    /* "block everything except Mia", "nothing to anyone but Mia": also the list */
    const butTo = !co && (new RegExp(String.raw`\b${NOBODY}\b.*\bbut\b`).test(t) || (new RegExp(String.raw`\b${NOBODY}\b`).test(t) && EXCEPT.test(t))) && !/\d/.test(t.replace(ADDR, ""));
    const unlessSigns = co && /\b(?:unless|except\s+(?:if|when))\b.*\b(?:co-?sign|sign|approv|confirm)\w*/.test(t);
    if (EXCEPT.test(t) && !unlessSigns && !butTo)
      return no("except", "The wallet's four blocks have no exception: a limit, a list or a day counts for every payment. Say it without the exception, or write the rule in Tau by hand; the Playground has an example with an exception (Limit, Bob exempt).");
    if (!strangers && !butTo && (/\b(never|not|no\s+payments?)\s+(?:send\s+|pay\s+)?to\b|\bblock(?:list)?\s+(?:payments\s+to\s+)?(?:0x)?[0-9a-f]{6,}|\bblacklist|\bban\b/.test(t) || ((tr ? halts && /\bto\b/.test(t) && !/\bonly\b/.test(t) : new RegExp(String.raw`\b${HALT}\b.*\bto\b`).test(t)) && !co && digitless && (people().length || left(["freeze"]).length))))
      return no("blocklist", "The wallet has no block for a list of forbidden addresses: a thief makes a new address in a second. “Only to …” keeps out every address you did not name.");
    /* everything stops. Read from another language the words may stand in another order, so there every word must be one the freeze knows */
    const frozen = FROZEN.test(t) || (tr && halts && /\b(?:all|everything|anything|payments?|transfers?|wallet|account|money)\b/.test(t) && !/\bto\b/.test(t) && !left(["freeze"], true).length);
    if (frozen && !/\b(?:else|others?|the\s+rest|before|until|till|after|since)\b/.test(t) && !dayWords && !co && !strangers && !butTo && digitless && !people().length)
      return done(["freeze"], { ...item, kind: "freeze" });
    if (co) {
      if (period) return no("period", "A rule sees one payment at a time, so it cannot add up a " + (period[1] || "day") + ". Say the limit for one payment, for example “above 1,000 the Guardian co-signs”.");
      const lim = numAt(t, String.raw`(?:above|over|more\s+than|beyond|exceeding|from|>=?|starting\s+at)`) ?? numAt(t, String.raw`(?:^|\s)`);
      if (lim == null) return no("co-amount", "Say from which amount on a co-signature is needed, for example “above 1,000 the Guardian co-signs”.");
      if (!whole(lim)) return no("whole", WHOLE);
      if (lim < 1 || lim > MAX_AMOUNT) return no("range", "Amounts run from 1 to 16,777,215 test AGRS.");
      const who = people(), named = /\bguardian|authenticator|2fa\b/.test(t), strange = left(["co"], true);
      let guardian = false;
      if (!who.length && !named && strange.length)   // "unless my brother signs": somebody is named, and this page does not know their address
        return no("co-who", SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : said(strange) + " is not in your wallet's address book. Write the co-signer's address, add the name to the address book first, or say “the Guardian”.");
      if (!who.length || named) {
        if (ctx.guardian && !who.some(w => w.addr === ctx.guardian)) { who.unshift({ addr: ctx.guardian, name: "Guardian" }); guardian = true; }
        else if (!ctx.guardian && !who.length) return no("co-who", SHORT_ADDR.test(t) ? "An address has 96 hex characters; this one is cut." : "Name the co-signer: an address, a name from your wallet's address book, or the Guardian.");
      }
      const more = who.length > 1;
      return done(["co"], { ...item, kind: "co", limit: lim, who: who.slice(0, 1), guardian: guardian && who.length >= 1 && who[0].addr === ctx.guardian, named,
        note: more ? "The wallet takes one co-signer per rule; the first one named is used." : null });
    }
    if (strangers || butTo || (/\b(only|just|exclusively|whitelist|allow\s*list)\b/.test(t) && !/\b(?:only|just)\s+(?:after|from|before|until|above|below|up\s+to|at\s+most|max|\d)/.test(t))) {
      let who = people();
      if (strangers || /\b(my\s+(?:address\s+)?book|my\s+contacts|my\s+people|my\s+friends|people\s+i\s+know|known\s+addresses)\b/.test(t)) who.push(...book.map(b => ({ addr: b.addr, name: b.name })));
      who = who.filter((w, i) => isAddr(w.addr) && who.findIndex(x => x.addr === w.addr) === i && w.addr !== ctx.me);
      const cap = capOf(), kinds = cap != null ? ["only", "cap"] : ["only"];
      if (!who.length) {
        const strange = strangers ? [] : left(kinds, true);
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
      /* which side of the day is closed: "nothing before Friday" and "from Friday" open the wallet on that day; "nothing after
         Friday" and "payments until Friday" close it on that day, and the wallet has no block for that */
      const shut = new RegExp(String.raw`\b(?:nothing|no|none|nobody|never|not|don'?t|cannot|can'?t|won'?t|hold|held|keep|kept|${HALT})\b`).test(t);
      const says = /\b(?:only|just|allow\w*|possible|fine|ok|okay|payments?|pay|send|spend|transfers?|may|can)\b/.test(t);
      const after = new RegExp(String.raw`\b(?:after|from|since|starting(?:\s+(?:on|from))?|as\s+of|beyond|past)\s+(?:the\s+|on\s+)?${DAYISH}`).test(t);
      const before = new RegExp(String.raw`\b(?:before|until|till|by|up\s+to)\s+(?:the\s+|on\s+)?${DAYISH}`).test(t);
      if ((after && before) || (after && shut) || (before && !shut && says) || /\bstop\w*\s+(?:on|at|after)\b|\bno\s+more\s+after\b/.test(t))
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

  /* ---------------- German, Chinese and Japanese ----------------
     A sentence in one of these languages is put into the English words above, phrase by phrase, and then read by the
     same reader: one reader, so the four blocks and every "no, because" are the same in every language. Names from the
     address book and addresses are set aside first, so no phrase can match inside them. A word no phrase covers stays as
     it was written, and the part says it was not used. Tested sentence by sentence in tests/rulewords.mjs. */
  const NAME0 = 0xE000, MARK0 = 0xF000;                 // private-use characters: a name set aside, the end of a stretch of the original
  const MARKS = /[\uF000-\uF8FF]/g, HELD = /[\uE000-\uEFFF]/g, MARKED = /[\uF000-\uF8FF]/, CJK = /[\u3040-\u30ff\u4e00-\u9fff]/;
  const LN = String.raw`[\p{L}\p{N}]`;
  /* Latin words need their own word edges: \b does not know ü */
  const w = (src, to) => [new RegExp(`(?<!${LN})(?:${src})(?!${LN})`, "giu"), to];
  const x = (src, to, flags) => [new RegExp(src, flags || "gu"), to];
  const AMT = String.raw`(?<![\d-])(?<!\d[.,])(\d[\d,.]*\d|\d)(?:\s*(?:[Tt]est[\s-]*)?(?:AGRS|agrs))?`;   // an amount, with or without its unit
  const DE_MON = String.raw`(?:januar|j(?:ä|ae)nner|februar|m(?:ä|ae)rz|april|mai|juni|juli|august|september|oktober|november|dezember|jan|feb|m(?:ä|ae)r|mrz|apr|jun|jul|aug|sep|sept|okt|nov|dez)`;
  const EN_MON = String.raw`(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)`;
  /* which language: kana → Japanese, Han without kana → Chinese, words only German has → German, else the reader as it is */
  const DE_SURE = new RegExp(`(?<!${LN})(?:h(?:ö|oe)chstens|maximal|nur|nichts|niemals|nicht|kein(?:e[nrms]?)?|zahlung(?:en)?|(?:ü|ue)berweisung(?:en)?|weniger|(?:ü|ue)ber|sperr\\w*|gesperrt|einfrier\\w*|friere|eingefroren|blockier\\w*|mitzeichn\\w*|gegenzeichn\\w*|zeichnet|unterschr\\w*|best(?:ä|ae)tig\\w*|au(?:ß|ss)er|jede[nrms]?|d(?:ü|ue)rfen|m(?:ü|ue)ssen|adressbuch|kontakte[n]?|freunde[n]?|n(?:ä|ae)chste[nrms]?|wochen?|monat(?:e[n]?)?|jahr(?:e[n]?)?|tage[n]?|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|januar|februar|m(?:ä|ae)rz|juni|juli|oktober|dezember|t(?:ä|ae)glich|w(?:ö|oe)chentlich|monatlich|insgesamt|betrag|guthaben|kontostand|fremde[n]?|unbekannte[n]?|braucht|brauchen|ben(?:ö|oe)tigt|mein(?:e[nmrs]?)?|darf|erst|ohne|wenn|oder|und|f(?:ü|ue)r|morgen|geht|raus|mindestens|wenigstens|behalten|senden|sende|schick(?:en|e|t)|(?:ü|ue)berweis\\w*|bezahl\\w*|zahlen|erlaub\\w*|niemand(?:em|en)?|alles|heute|sofort|bitte|konto|geld|empf(?:ä|ae)nger[n]?|adressen|gr(?:ö|oe)(?:ß|ss)er|h(?:ö|oe)her|kleiner|zweite[rn]?|signatur(?:en)?|w(?:ä|ae)chter|obergrenze|h(?:ö|oe)chstbetrag|erlaubt|stoppe|limit\\s+von)(?!${LN})`, "iu");
  const DE_MAYBE = new RegExp(`(?<!${LN})(?:bis|vor|nach|ab|unter|alle[ns]?|ich|muss|an|am|mit|pro|je|nie|zu|von|im|der|die|das|den|dem)(?!${LN})`, "iu");
  const EN_SURE = /\b(?:the|to|only|most|before|until|nothing|payments?|above|never|after|from|block|and|per|than|more|no|not|of|is|are|my)\b/i;
  const langOf = s => (/[\u3040-\u30ff]/.test(s) ? "ja" : /[\u4e00-\u9fff]/.test(s) ? "zh" : DE_SURE.test(s) || (DE_MAYBE.test(s) && !EN_SURE.test(s)) ? "de" : null);

  const DE_UNIT = { tag: "day", woche: "week", monat: "month", jahr: "year" }, DE_N = { ein: "one", eine: "one", einem: "one", einen: "one", einer: "one", zwei: "two", drei: "three", sechs: "six" };
  const DE_PAY = String.raw`(?:zahlung(?:en)?|(?:ü|ue)berweisung(?:en)?|transaktion(?:en)?|transfers?)`, DE_HALT = String.raw`(?:sperren|blockieren|stoppen|anhalten|einfrieren|verbieten|ablehnen)`;
  const DE = [
    /* days and dates */
    x(String.raw`(?<![\d.])(\d{1,2})\.\s*(?=${DE_MON}(?![\p{L}]))`, (m, d) => ` ${d} `, "giu"),
    x(String.raw`(?<![\d.])(\d{1,2})\.\s?(\d{1,2})\.(?!\d)|(?<![\d.])(\d{1,2})\.\s?(\d{1,2})(?=[\uF000-\uF8FF]\.(?!\d))`, (m, d, mo, d2, mo2) => (MONTHS[(mo || mo2) - 1] ? ` ${+(d || d2)} ${MONTHS[(mo || mo2) - 1]} ` : m)),
    w("januar|j(?:ä|ae)nner", "january"), w("februar", "february"), w("m(?:ä|ae)rz|mrz\\.?|m(?:ä|ae)r\\.?", "march"), w("mai", "may"), w("juni", "june"), w("juli", "july"), w("oktober|okt\\.?", "october"), w("dezember|dez\\.?", "december"),
    w("montags?", "monday"), w("dienstags?", "tuesday"), w("mittwochs?", "wednesday"), w("donnerstags?", "thursday"), w("freitags?", "friday"), w("samstags?|sonnabends?", "saturday"), w("sonntags?", "sunday"),
    w("(?:ü|ue)bermorgen", "in 2 days"), w("morgen", "tomorrow"),
    w("(?:n(?:ä|ae)chste[nrs]?|kommende[nr]?)\\s+woche", "next week"), w("(?:n(?:ä|ae)chste[nrs]?|kommende[nr]?)\\s+monat", "next month"), w("(?:n(?:ä|ae)chste[nrs]?|kommende[nrs]?)\\s+jahr", "next year"),
    w("ende\\s+des\\s+monats|monatsende", "end of the month"), w("ende\\s+des\\s+jahres|jahresende", "end of the year"), w("ende\\s+(20\\d{2})", (m, y) => ` end of ${y} `),
    w("ab\\s+jetzt|ab\\s+sofort|von\\s+(?:jetzt|nun)\\s+an", "from now on"),
    w("pro\\s+tag|am\\s+tag|je\\s+tag|jeden\\s+tag|t(?:ä|ae)glich", "per day"), w("pro\\s+woche|jede\\s+woche|w(?:ö|oe)chentlich", "per week"), w("pro\\s+monat|im\\s+monat|jeden\\s+monat|monatlich", "per month"),
    w("pro\\s+stunde|st(?:ü|ue)ndlich", "per hour"), w("pro\\s+jahr|im\\s+jahr|j(?:ä|ae)hrlich", "per year"), w("insgesamt|zusammengerechnet|in\\s+summe", "in total"),
    w("(\\d+|eine[mnr]?|ein|zwei|drei|sechs)\\s+(tag|woche|monat|jahr)(?:e|en|n)?", (m, n, u) => ` ${DE_N[n.toLowerCase()] || n} ${DE_UNIT[u.toLowerCase()]}s `),
    w("n(?:ä|ae)chste[nrs]?|kommende[nrs]?", "next"),
    w("werktags|wochentags|an\\s+werktagen|unter\\s+der\\s+woche", "weekdays"), w("(?:am\\s+)?wochenenden?", "weekends"), w("nachts|in\\s+der\\s+nacht", "at night"), w("tags(?:ü|ue)ber", "by day"),
    w("(\\d{1,2})\\s*uhr", (m, h) => ` ${h} o'clock `), w("gesch(?:ä|ae)ftszeiten|b(?:ü|ue)rozeiten", "office hours"),
    w("tsd\\.?|tausend", "thousand"), w("mio\\.?|million(?:en)?", "million"),
    /* a comma that ends nothing: "ich möchte, dass …", "Zahlungen, die über 1000 liegen, sperren" */
    x(String.raw`,\s*(?:dass|damit)(?!${LN})`, " ", "giu"), x(String.raw`,\s*(?:die|welche)\s+(?=(?:ü|ue)ber|unter|mehr|weniger|gr(?:ö|oe)(?:ß|ss)er|h(?:ö|oe)her|kleiner)`, " ", "giu"), x(String.raw`(?<!${LN})(?:liegen|sind|betragen)[\s\uF000-\uF8FF]*,`, " ", "giu"),
    w("m(?:ö|oe)chte|will|w(?:ü|ue)nsche(?:\\s+mir)?", "want"), w("ohne", "without"),
    /* what should not be stopped */
    w(`nicht\\s+(?:mehr\\s+)?${DE_HALT}|nicht\\s+gesperrt|nicht\\s+eingefroren`, "not block"),
    /* a second signature */
    w("zeichnet\\s+(.{1,60}?)\\s+(?:mit|gegen)", (m, a) => ` ${a} co-signs `), w("unterschreibt\\s+(.{1,60}?)\\s+mit", (m, a) => ` ${a} co-signs `),
    w("zweite[rn]?\\s+(?:unterschrift|signatur)|zweitunterschrift", "second signature"), w("zwei\\s+unterschriften", "two signatures"),
    w("(?:mit|gegen)(?:zu)?zeichne[nt]|mit\\s*unterschreib(?:t|en)|mitsignier(?:t|en)|gegenzeichn\\w+|mitzeichn\\w+|unterschreib(?:t|en)|unterzeichne[nt]|signier(?:t|en)", "co-signs"),
    w("unterschrift(?:en)?|signatur(?:en)?", "signature"),
    w("best(?:ä|ae)tig(?:t|en|ung)|zustimm(?:t|en|ung)|stimmt\\s+zu|genehmig(?:t|en|ung)|freigeben|freigabe|gibt\\s+frei", "confirms"), w("w(?:ä|ae)chter", "guardian"),
    /* everything stops */
    w(`(?:alle|s(?:ä|ae)mtliche|jede|jegliche)\\s+(?:ausgehenden?\\s+)?${DE_PAY}\\s+${DE_HALT}`, "block all payments"),
    w(`(?:sperre|blockiere|stoppe|verbiete)\\s+(?:alle|s(?:ä|ae)mtliche|jede)\\s+(?:ausgehenden?\\s+)?${DE_PAY}`, "block all payments"),
    w("alles\\s+(?:sperren|blockieren|stoppen|anhalten|einfrieren)|(?:sperre|blockiere|stoppe|friere)\\s+alles(?:\\s+ein)?", "block everything"),
    w("(?:(?:das|mein|dieses)\\s+)?(?:wallet|konto)\\s+(?:sperren|einfrieren|blockieren)|(?:sperre|friere|blockiere)\\s+(?:das|mein|dieses)\\s+(?:wallet|konto)(?:\\s+ein)?", "freeze the wallet"),
    w("nichts\\s+(?:(?:geht|darf|kann|soll)\\s+)?(?:mehr\\s+)?(?:raus|hinaus|rausgehen|ausgehen)|nichts\\s+rauslassen", "nothing leaves"),
    w("gesperrt", "locked"), w("eingefroren|einfrieren|friere", "freeze"),
    w("sperr(?:en|e|t)|blockier(?:en|e|t)|stopp(?:en|e|t)|anhalten|verbiete[nt]?|verboten|ablehnen|verweigern", "block"),
    /* who may be paid */
    w("(?:nur|ausschlie(?:ß|ss)lich|einzig)(?:\\s+noch)?\\s+(?:an|zu|f(?:ü|ue)r)", "only to"),
    w("(?:mein(?:em|e|en)?\\s+)?adressbuch|(?:mein(?:e|en)?\\s+)?kontakte[n]?|(?:mein(?:e|en)?\\s+)?freunde[n]?|leute[n]?,?\\s+die\\s+ich\\s+kenne|bekannte[n]?\\s+adressen", "my address book"),
    w("fremde[n]?|unbekannte[n]?(?:\\s+adressen)?|leute[n]?,?\\s+die\\s+ich\\s+nicht\\s+kenne|neue[n]?\\s+adressen", "strangers"),
    w("nur|ausschlie(?:ß|ss)lich|lediglich", "only"),
    /* an amount; "erst ab 2028" is "not before 2028", so it is read before "ab" alone */
    w("nicht\\s+vor(?:\\s+dem)?|erst\\s+(?:ab|nach|am)(?:\\s+dem)?|fr(?:ü|ue)hestens(?:\\s+(?:ab|am))?(?:\\s+dem)?|erst", "not before"),
    w("h(?:ö|oe)chstens|maximal|max\\.?|nicht\\s+mehr\\s+als|nie(?:mals)?\\s+mehr\\s+als|bis\\s+zu|obergrenze(?:\\s+von)?|h(?:ö|oe)chstbetrag(?:\\s+von)?|limit(?:\\s+von)?", "at most"),
    x(String.raw`(?<!${LN})(bis|ab)\s+(?=(?:\d{4}-\d|\d{1,2}\.\d{1,2}\.|\d{1,2}\s+${EN_MON}(?![a-z])|20\d{2}(?![\d.,])(?!\s*(?:test|agrs|pro|je|per))))`, (m, a) => (/^b/i.test(a) ? " until " : " from "), "giu"),
    x(String.raw`(?<!${LN})bis\s+(?=\d)`, "at most", "giu"), x(String.raw`(?<!${LN})ab\s+(?=\d)`, "above", "giu"),
    w("weniger\\s+als|unterhalb\\s+von|kleiner\\s+als|unter", "less than"),
    w("mehr\\s+als|oberhalb\\s+von|gr(?:ö|oe)(?:ß|ss)er\\s+als|h(?:ö|oe)her\\s+als|(?:ü|ue)ber", "above"),
    w("(?:pro|je)\\s+(?:zahlung|(?:ü|ue)berweisung|transaktion|transfer|sendung)", "per payment"),
    w("begrenz\\w*|beschr(?:ä|ae)nk\\w*|limitier\\w*", "limit"),
    /* a day */
    w("vor(?:\\s+dem)?", "before"), w("bis(?:\\s+zum|\\s+zur)?", "until"), w("nach(?:\\s+dem)?", "after"), w("ab(?:\\s+dem)?|seit(?:\\s+dem)?|vom", "from"), w("am", "on"),
    /* exceptions and the rest */
    w("au(?:ß|ss)er(?:\\s+an)?|ausgenommen|mit\\s+ausnahme\\s+von", "except"), w("es\\s+sei\\s+denn|sofern\\s+nicht|wenn\\s+nicht|solange\\s+nicht", "unless"),
    w(`kein(?:e|en|er)?\\s+(?:einzige\\s+)?${DE_PAY}`, "no payments"), w("kein\\s+geld", "no money"),
    w("nichts", "nothing"), w("niemand(?:em|en)?|keinem|keiner", "nobody"), w("niemals|nie", "never"), w("nicht", "not"), w("kein(?:e[nrms]?)?", "no"),
    w("guthaben|kontostand|saldo|mindestguthaben|behalten|(?:ü|ue)brig\\w*|verbleiben", "balance"), w("mindestens|wenigstens", "at least"),
    w("zahlungen|(?:ü|ue)berweisungen|transaktionen|sendungen", "payments"), w("zahlung|(?:ü|ue)berweisung|transaktion|sendung", "payment"),
    w("betr(?:ä|ae)ge|betrag|summe", "amount"), w("geld", "money"), w("konto|geldb(?:ö|oe)rse|brieftasche", "wallet"), w("adressen", "addresses"), w("adresse", "address"), w("empf(?:ä|ae)nger[n]?|leute[n]?|personen", "people"),
    w("senden|sende[tn]?|schick(?:en|e|t)|(?:ü|ue)berweis(?:en|e|t)|gesendet|geschickt|(?:ü|ue)berwiesen", "send"), w("zahl(?:en|e|t)|bezahl(?:en|e|t)|gezahlt|auszahlen", "pay"),
    w("rausgehen|rausgeht|ausgehen|gehen|geht|verl(?:ä|ae)sst|verlassen", "leaves"), w("lass(?:e|en|t)?", "let"),
    w("erlaub(?:en|e|t)|zulassen|gestatten|m(?:ö|oe)glich", "allowed"), w("brauch(?:t|en)|ben(?:ö|oe)tig(?:t|en)|erforder(?:t|n|lich)|n(?:ö|oe)tig|verlang(?:t|en)", "needs"),
    w("muss|m(?:ü|ue)ssen|soll(?:en|te)?", "must"), w("darf|d(?:ü|ue)rfen|kann|k(?:ö|oe)nnen", "can"), w("ist|sind|wird|werden|sein|bleib(?:t|en)|liegen|liegt", "is"),
    w("und|sowie", "and"), w("oder", "or"), w("aber|jedoch", "but"), w("dann|danach", "then"), w("auch|zus(?:ä|ae)tzlich", "also"),
    w("ich|mir|mich", "i"), w("mein(?:e[nmrs]?)?", "my"), w("der|die|das|den|dem|des", "the"), w("eine[nmrs]?|ein", "a"), w("diese[nmrs]?", "these"),
    w("alles", "everything"), w("alle[nrs]?|s(?:ä|ae)mtliche|jede[nrms]?", "all"), w("jemand(?:en|em)?|irgendwen|irgendjemand(?:en)?", "anyone"), w("andere[nrs]?|sonst", "else"),
    w("raus|hinaus|heraus", "out"), w("mehr", "more"), w("bitte", "please"), w("f(?:ü|ue)r", "for"), w("mit", "with"), w("von", "of"), w("an|zu|auf", "to"), w("im|ins", "in"), w("pro|je", "per"),
    w("wenn|falls|sobald|noch|mal|einfach|eben|halt|doch|es|man|dass|damit|gilt|gelten|sofort|jetzt|nun|gleich|immer|stets|jeweils|grunds(?:ä|ae)tzlich|generell|folgende[nrs]?|danke", ""),
  ];

  /* 五百 → 500, 一万 → 10000, 1万5千 → 15000, 十二月 → 12月: a numeral that carries 十, 百, 千 or 万, or stands before a
     counter of time; 一个 and 第二 stay words */
  const HAN_D = { "〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
  function hanNum(s) {
    let total = 0, part = 0, d = 0, seen = false;
    for (const ch of s) {
      if (ch in HAN_D) { d = HAN_D[ch]; seen = true; }
      else if (ch === "十") { part += (seen ? d : 1) * 10; d = 0; seen = false; }
      else if (ch === "百") { part += (seen ? d : 1) * 100; d = 0; seen = false; }
      else if (ch === "千") { part += (seen ? d : 1) * 1000; d = 0; seen = false; }
      else if (ch === "万" || ch === "萬") { total += (part + (seen ? d : 0) || 1) * 10000; part = 0; d = 0; seen = false; }
    }
    return total + part + (seen ? d : 0);
  }
  function cjkNumbers(s) {
    const HN = "〇零一二两兩三四五六七八九十百千万萬";
    s = s.replace(/[０-９]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0)).replace(/．/g, ".");
    s = s.replace(new RegExp(`(?<![周週期拜第])[${HN}]+(?=\\s*(?:月|日|号|號|年|天|周|週|个月|個月|か月|ヶ月|カ月|星期))`, "g"), m => String(hanNum(m)));
    s = s.replace(new RegExp(`(?<![周週期拜第])[${HN}]{2,}`, "g"), m => (/[十百千万萬]/.test(m) ? String(hanNum(m)) : m));
    s = s.replace(/(\d+(?:\.\d+)?)\s*[万萬](?:\s*(\d)\s*千)?/g, (m, a, b) => String(Math.round(Number(a) * 10000 + (b ? Number(b) * 1000 : 0))));
    return s.replace(/(\d+(?:\.\d+)?)\s*千/g, (m, a) => String(Math.round(Number(a) * 1000))).replace(/(\d+)\s*百(?!分)/g, (m, a) => String(Number(a) * 100));
  }
  const p2 = n => String(n).padStart(2, "0");
  const HAN_DAY = { "一": "monday", "二": "tuesday", "三": "wednesday", "四": "thursday", "五": "friday", "六": "saturday", "日": "sunday", "天": "sunday",
    "月": "monday", "火": "tuesday", "水": "wednesday", "木": "thursday", "金": "friday", "土": "saturday" };
  const SINCE = "之后|之後|以后|以後|后|後", WITHIN = "之内|之內|以内|以內|内|內";
  /* dates, the same way in Chinese and Japanese */
  const HAN_DATE = [
    x(String.raw`(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号號]?`, (m, y, mo, d) => ` ${y}-${p2(mo)}-${p2(d)} `),
    x(String.raw`(\d{1,2})\s*月\s*(\d{1,2})\s*[日号號]`, (m, mo, d) => (MONTHS[mo - 1] ? ` ${+d} ${MONTHS[mo - 1]} ` : m)),
    x(String.raw`(20\d{2})\s*年\s*(?:年底|年末|底|末)`, (m, y) => ` end of ${y} `),
    x(String.raw`(?:到|直到|至)\s*(20\d{2})\s*年(?:为止|為止)?|(20\d{2})\s*年\s*(?:之前|以前|前|まで(?:は)?|より前)`, (m, a, b) => ` until ${a || b} `),
    x(String.raw`(?:从|從|自)?\s*(20\d{2})\s*年\s*(?:${SINCE}|起|开始|開始|以降|から)`, (m, y) => ` from ${y} `),
    x(String.raw`(?:周|週|星期|礼拜|禮拜)([一二三四五六日天])|([月火水木金土日])曜日?`, (m, a, b) => ` ${HAN_DAY[a || b]} `),
    x("后天|後天|明後日|あさって", "in 2 days"), x("明天|明日|あした", "tomorrow"),
    x("下周|下週|下星期|下个星期|下個星期|下礼拜|来週", "next week"), x("下个月|下個月|下月|来月", "next month"), x("明年|来年", "next year"),
    x("(?:本|这个|這個|今)?月(?:底|末)", "end of the month"), x("(?:今|本)?年(?:底|末)", "end of the year"),
  ];
  /* a stretch of time, counted from today */
  const HAN_SPAN = [
    x(String.raw`(\d+)\s*(?:天|日)(?:${SINCE}|${WITHIN}|間|间)`, (m, n) => ` locked for ${n} days `),
    x(String.raw`(\d+)\s*(?:个星期|個星期|星期|週間|周)(?:${SINCE}|${WITHIN})?`, (m, n) => ` locked for ${n} weeks `),
    x(String.raw`(\d+)\s*(?:个月|個月|か月|ヶ月|カ月|ケ月|箇月)(?:${SINCE}|${WITHIN}|間)?`, (m, n) => ` locked for ${n} months `),
    x(String.raw`(?<![\d-])(\d{1,2})\s*年(?:${SINCE}|${WITHIN}|間)`, (m, n) => ` locked for ${n} years `),
    x(String.raw`(\d+)\s*天|(\d+)\s*日(?![本曜])`, (m, a, b) => ` in ${a || b} days `),
  ];
  const ZH = [
    ...HAN_DATE,
    /* what the testnet cannot do, so the reader can say why */
    x("每天|每日|1天(?![后後之以])内?|单日|單日|日限额?", "per day"), x("每周|每週|每星期|每个星期|1周(?![后後之以])内?", "per week"), x("每个?月|每個月|1个月(?![后後之以])内?", "per month"), x("每小时|每小時", "per hour"), x("总共|總共|合计|合計|累计|累計|总计|一共", "in total"),
    x("余额|餘額|至少保留|至少留|保留至少|留下至少|最低余额", "balance"), x("工作日|平日", "weekdays"), x("周末|週末", "weekends"), x("晚上|夜间|夜間|夜里", "at night"), x("白天", "by day"),
    x(String.raw`(\d{1,2})\s*点钟?`, (m, h) => ` ${h} o'clock `),
    /* a day after which nothing leaves: an end date */
    x(`(?:${SINCE})(?:就|便|则|都)?(?:不能|不许|不准|禁止|停止|不再|不可|不行)(?:再)?(?:付款|支付|转账|汇款)?`, "no more after"),
    ...HAN_SPAN,
    /* one payment */
    x("每一?笔|每一?筆|每次|单笔|單筆|单次|一笔|1笔", "per payment"),
    /* an amount */
    x("不能超过|不能超過|不得超过|不得超過|不可超过|不要超过|不超过|不超過|不多于|不高于|最多|至多|最高|最大|上限(?:为|為|是)?|限额(?:为|是)?|限額(?:為|是)?|限制(?:为|在)", "at most"),
    x(AMT + String.raw`\s*(?:以内|以內|之内|之內|以下|为限|封顶)`, (m, n) => ` at most ${n} `),
    x(AMT + String.raw`\s*(?:以上|起)`, (m, n) => ` above ${n} `),
    x("低于|低於|少于|少於|小于|小於|不到|不足", "less than"), x("超过|超過|高于|高於|大于|大於|多于|多於|超出", "above"),
    /* a second signature */
    x("共同签名|共同簽名|共同签署|共同簽署|联署|聯署|联合签名|会签|會簽|副署|共签|一起签名|一同签名|也要签名|也签名", "co-signs"),
    x("第二个签名|第二個簽名|第二签名|二次签名|双重签名|雙重簽名|两个签名|兩個簽名|双签|第二人签名", "second signature"),
    x("签名|簽名|签字|簽字|签署|簽署", "signature"), x("二次确认|确认|確認|批准|审批|核准|同意", "confirms"), x("守护者|守護者", "guardian"),
    /* what should not be stopped */
    x("(?:不要|不用|无需|無需|不必|别|別|不)(?:冻结|凍結|锁定|鎖定|锁住|停止|阻止|拦截|拒绝)", "not block"),
    /* everything stops */
    x("(?:冻结|凍結|锁定|鎖定|锁住|鎖住|锁|鎖)(?:到|至|直到)", "locked until"),
    x("(?:冻结|凍結|锁定|鎖定|锁住|鎖住)(?:我的|这个|這個|该)?(?:钱包|錢包|账户|賬戶|帳戶|账号)|冻结|凍結", "freeze the wallet"),
    x("(?:停止|禁止|阻止|暂停|暫停|拒绝|拒絕|锁定|鎖定)(?:所有|全部|一切|任何)?的?(?:付款|支付|转账|轉賬|交易|汇款|支出)", "block all payments"),
    x("(?:所有|全部|一切|任何)的?(?:付款|支付|转账|轉賬|交易|汇款|支出)(?:都|一律|全部)?(?:不能|不许|不准|禁止|停止|不行|不可以?|拒绝)(?:进行|通过|发出|出去)?", "block all payments"),
    x("什么都不能(?:付|转|发|出)|什麼都不能(?:付|轉|發|出)|一分钱?都不能?(?:出|付|转)|不允许任何(?:付款|转账|支付)|什么都不(?:付|出)", "block all payments"),
    x("锁定|鎖定|锁住|鎖住", "lock"),
    /* who may be paid */
    x("(?:我的)?(?:地址簿|通讯录|通訊錄|联系人|聯絡人|联络人)(?:里的人?|裡的人?|中的人?|上的人)?|我认识的人|我認識的人|我的朋友|朋友们?", "my address book"),
    x("陌生人|不认识的人|不認識的人|未知地址|新地址|生人", "strangers"),
    x("不要(?:付款?|转账?|发送?|汇款?)?给|不能(?:付款?|转账?|发送?)?给|禁止(?:付款?|转账?|发送?)?给|别给|別給|拉黑|黑名单|黑名單", "never to"),
    x("只(?:能|可以|允许|允許|准)?(?:付款?|支付|转账?|轉賬?|发送?|發送?|汇款?|打钱)?(?:给|給|向|对)|仅(?:限|能|可)?(?:付款?|转|发)?(?:给|給|向|限)?|僅(?:限|能|可)?(?:給|向|限)?", "only to"),
    x("只", "only"), x("和|与|與|以及|及|跟|还有|還有", "and"), x("或者?", "or"),
    /* a day */
    x("之前|以前|前(?=[\\s,;，不禁别別锁鎖冻凍都可能才\\uF000-\\uF8FF]|$)", "before"), x("直到|为止|為止", "until"), x("之后|之後|以后|以後|过后", "after"), x("从|從|自(?!己)|开始|開始|起(?=[\\s,;，才可能\\uF000-\\uF8FF]|$)", "from"),
    /* the rest */
    x("除非", "unless"), x("除了|以外|之外|但不包括|不包括|例外", "except"), x("其他人?|其它人?|别人|別人|其余的?人?|任何人|所有人", "anyone else"), x("谁也?|誰也?", "anyone"),
    x("不能|不许|不許|不准|不可以?|禁止|不得|不允许|不允許|停止|阻止|拒绝|拒絕|拦截|不行|不要|不付|不转|别|別", "block"),
    x("需要|必须|必須|须|須|得要|要有", "needs"),
    x("收款|收钱|收錢", "paid"), x("付款|支付|转账|轉賬|轉帳|转帐|汇款|匯款|交易|支出|打款|转出|发送|發送", "payments"), x("所有|全部|一切|任何", "all"), x("钱包|錢包|账户|賬戶|帳戶|账号|户头", "wallet"),
    x("金额|金額|数额|數額|额度|額度", "amount"), x("资金|資金|代币|代幣", "money"), x("付给|付給|转给|轉給|发给|發給|汇给|给|給|向", "to"),
    x("才能|才可以|才允许|方可|允许|允許|可以|能够|能夠", "can"),
    x("如果|假如|要是|[请請麻烦帮幫我想希望把将將让讓使的了吗嗎呢吧啊呀都就才也还還再则則即被由地得着著是为為有在里裡中上内內个個这這那此该該它其而且并並时時话話钱錢币幣测測试試要能可转轉付发發到至对對元块塊枚若款]", ""),
  ];
  const JA_NOT = "ない|ません|なかった";
  const JA = [
    ...HAN_DATE,
    x("1日あたり|1日に(?:つき)?|毎日|日ごと|1日の(?:上限|合計)?", "per day"), x("毎週|週に|1週間に", "per week"), x("毎月|月に|1[かヶカ]月に", "per month"), x("毎時|1時間に", "per hour"), x("合計で?|累計で?|トータルで?", "in total"),
    x("残高|残しておく|残す", "balance"), x("平日", "weekdays"), x("週末", "weekends"), x("夜間|夜は|夜に", "at night"), x("昼間", "by day"), x("営業時間", "office hours"),
    x(String.raw`(\d{1,2})\s*時(?!間)`, (m, h) => ` ${h} o'clock `),
    /* a day after which nothing leaves: an end date */
    x("(?:以降|以後|の後|より後|後)(?:に)?(?:は)?(?:送らない|送金しない|払わない|支払わない|支払いしない|禁止|停止|ブロック|できない)", "no more after"),
    ...HAN_SPAN,
    x("(?:1|一)回(?:の(?:支払い?|送金))?(?:あたり|につき|ごとに|に)?|毎回|(?:支払い?|送金|取引)(?:ごとに|1回につき|一回につき)|1件(?:あたり|につき)?", "per payment"),
    /* an amount */
    x(AMT + String.raw`\s*(?:を超える|を超えた(?:ら|場合(?:は)?)?|を越える|超(?!え)|より多い|より大きい|以上)`, (m, n) => ` above ${n} `),
    x(AMT + String.raw`\s*(?:まで|以内|以下|を上限)`, (m, n) => ` at most ${n} `),
    x(AMT + String.raw`\s*(?:未満|より少ない|より小さい)`, (m, n) => ` less than ${n} `),
    x("最大|最高|上限は?|マックス", "at most"),
    /* a second signature */
    x("共同署名|連署|副署|共同で署名|一緒に署名|も署名", "co-signs"),
    x("(?:二|2)人目の署名|第二の署名|(?:二|2)つ目の署名|二重署名|(?:二|2)つの署名", "second signature"),
    x("署名|サイン", "signature"), x("承認|確認|同意", "confirms"), x("ガーディアン", "guardian"),
    x("必要|必須|なければならない|しなければならない|要ります|要る", "needs"),
    /* what should not be stopped */
    x(`(?:凍結|ロック|停止|ブロック|禁止)(?:は|を)?(?:し|され)?(?:${JA_NOT})|止め(?:${JA_NOT})`, "not block"),
    /* everything stops */
    x("(?:ウォレット|財布|口座|アカウント)を?(?:凍結|ロック|停止)(?:する|して(?:ください)?)?|凍結(?:する|して(?:ください)?)?", "freeze the wallet"),
    x("(?:すべて|全て|全部)(?:の(?:支払い?|送金|取引|出金))?を?(?:止める|停止(?:する)?|ブロック(?:する)?|禁止(?:する)?|拒否(?:する)?)|(?:支払い?|送金)を?(?:すべて|全て|全部)(?:止める|停止|ブロック|禁止)(?:する)?", "block all payments"),
    x("何も(?:送らない|払わない|送金しない|出さない)|一切(?:送金しない|送らない|支払わない|払わない|出金しない)", "block all payments"),
    x("ロック(?:する|して(?:ください)?)?", "lock"),
    /* who may be paid */
    x("アドレス帳(?:の人)?|連絡先(?:の人)?|知っている人|知ってる人|友達|友だち|友人", "my address book"),
    x("知らない人|知らないアドレス|未知のアドレス|新しいアドレス|見知らぬ(?:人|アドレス)", "strangers"),
    x("ブラックリスト", "blacklist"),
    x("(以降|以後|から|より後|まで)(?:のみ|だけ)", (m, a) => a),   // "only from that day on" is a day, not a list
    x("(?:に|へ)?しか(?:送らない|送金しない|払わない|支払わない|送れない)?", "only to"),
    x("(?:に|へ)?(?:だけ|のみ)(?:に|へ)?", "only to"),
    x("(?:に|へ)は?(?:送らない|送金しない|払わない|支払わない|送れない)", "never to"),
    x(String.raw`(?<=[\uE000-\uEFFF])\s*(?:と|や|および|及び)\s*(?=[\uE000-\uEFFF])`, "and"),
    /* a day */
    x("までは?|迄", "until"), x("より前|以前|の前に?|前に", "before"), x("以降|以後|より後|の後", "after"), x("から", "from"),
    /* the rest */
    x("でない限り|しない限り|ない限り", "unless"), x("以外|を?除いて|を?除き|を?除く", "except"),
    x("送らない|送金しない|送れない|送金できない|払わない|支払わない|支払えない|支払いできない|できない|禁止(?:する)?|ブロック(?:する)?|停止(?:する)?|止める|拒否(?:する)?|許可しない", "block"),
    x("支払い?|送金|出金|振込|振り込み|取引|トランザクション|送信", "payments"), x("すべて|全て|全部|あらゆる", "all"), x("ウォレット|財布|口座|アカウント", "wallet"),
    x("金額|額", "amount"), x("お金|資金|コイン|トークン", "money"), x("テスト", "test"),
    x(JA_NOT, "not"),
    x("もし|場合|[\\u3040-\\u309f]+|[私僕円枚]", ""),   // what is left in hiragana is grammar
  ];
  const TABLES = { de: [DE], zh: [ZH, JA], ja: [JA, ZH] };   // Japanese without kana looks like Chinese, so each gets the other's phrases too
  const DAYEXPR = String.raw`(?:\d{4}-\d{2}-\d{2}|\d{1,2} (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|tomorrow|next (?:week|month|year)|end of the (?:month|year)|end of 20\d{2}|(?:mon|tues|wednes|thurs|fri|satur|sun)day|in \d+ days)`;
  /* one text → its English reading; pairs keeps what each English phrase was written as */
  function toEnglish(text, lang, pairs) {
    let s = lang === "de" ? text : cjkNumbers(text.replace(/[。．]/g, ".").replace(/；/g, ";").replace(/[，、]/g, ",").replace(/：/g, ":"));
    for (const table of TABLES[lang]) for (const [re, to] of table)
      s = s.replace(re, (...a) => {
        const m = a[0], out = typeof to === "function" ? to(...a) : to ? " " + to + " " : " ", marks = m.match(MARKS);
        if (out.trim() && out !== m) pairs.push([out.trim().toLowerCase(), m.replace(MARKS, "").trim()]);
        return marks && !MARKED.test(out) ? out + marks.join("") : out;
      });
    /* Chinese and Japanese say "1 Dec before": the reader wants the word in front of the day */
    if (lang !== "de") s = s.replace(new RegExp(`(${DAYEXPR})\\s+(before|until|after|from)(?![a-z])`, "g"), "$2 $1");
    return s.replace(/[ \t]+/g, " ");
  }
  const CUT = { de: /[.;,\n]|\s+(?:und|aber|sowie|dann|danach|plus|and|but|then)\s+/giu,
    zh: /[.。;；,，、\n]|并且|並且|而且|同时|同時|然后|然後|但是|不过|不過|和|与|與|以及|还有|還有/gu,
    ja: /[.。;；,，、\n]|そして|かつ|また|しかし|ただし|および|及び/gu };
  const HARD = /^(?:并且|並且|而且|同时|同時|然后|然後|但是|不过|不過|そして|かつ|また|しかし|ただし)$/;
  const PUNCT = /^[.。;；,，、\n]$/, EXC = /除了?|以外|之外|除[いきく]/, NEG = /不|别|別|禁止|停止|拒绝|拒絕|ない|ません|ブロック|止め/, lettered = s => /[\p{L}\p{N}\uE000-\uEFFF]/u.test(s);
  /* the parts of a text with what each one was written as: [{ c: the English the reader gets, src: the words as written }] */
  function pieces(text, ctx) {
    text = String(text || "").replace(/\r/g, "").replace(/[\uE000-\uF8FF]/g, "");
    /* names and addresses aside, each as it was written */
    const kept = [], keep = m => { kept.push(m); return String.fromCharCode(NAME0 + kept.length - 1); };
    let masked = text.replace(ADDR, keep);
    const han = CJK.test(masked);
    for (const b of [...(ctx.book || [])].sort((a, b) => b.name.length - a.name.length)) {
      const n = b.name.trim(); if (!n || kept.length > 3000) continue;
      const edge = !han ? LN : CJK.test(n) ? null : "[A-Za-z0-9]";   // no spaces around a name in Chinese or Japanese
      masked = masked.replace(new RegExp(edge ? `(?<!${edge})${esc(n)}(?!${edge})` : esc(n), "giu"), keep);
    }
    const lang = langOf(masked);
    if (!lang) return clauses(text).map(c => ({ c, src: c }));
    const raw = s => s.replace(HELD, ch => kept[ch.charCodeAt(0) - NAME0]), spaced = s => s.replace(HELD, ch => " " + kept[ch.charCodeAt(0) - NAME0] + " ");
    /* the places where the original may be cut: every one gets a mark, so each part of the reading knows its own words */
    const cuts = [...masked.matchAll(CUT[lang])].filter(m => {
      const i = m.index, d = m[0], prev = masked[i - 1] || "", rest = masked.slice(i + d.length);
      if ((d === "." || d === ",") && /\d/.test(prev) && /^\d/.test(rest)) return false;                                   // 1.000 · 1,5 · 1.12.2026
      if (d === "." && /\d/.test(prev) && new RegExp(`^\\s*${DE_MON}(?![\\p{L}])`, "iu").test(rest)) return false;        // 1. Dezember
      if (d === "." && /(?<![\p{L}])(?:max|min|ca|nr|tsd|mio|bzw|inkl|jan|feb|mrz|apr|jun|jul|aug|sep|sept|okt|nov|dez)$/iu.test(masked.slice(0, i))) return false;   // max. 500 · 1. Dez. 2026
      if (d === "." && /(?<![\d.])\d{1,2}\.\s?\d{1,2}$/.test(masked.slice(0, i)) && /^\s*[a-zäöü]/.test(rest)) return false;   // am 1.12. nichts
      return true;
    });
    const segs = []; let marked = "", last = 0;
    cuts.forEach((m, k) => {
      const seg = masked.slice(last, m.index), next = masked.slice(m.index + m[0].length, k + 1 < cuts.length ? cuts[k + 1].index : masked.length);
      let d = m[0];
      if (lang !== "de") {   // a comma in Chinese or Japanese ends a part, unless it stands between two names or after an exception that stopped nothing yet
        if (HARD.test(d)) d = ";";
        else if (/^[,，、]$/.test(d)) {
          let j = k - 1; while (j >= 0 && !PUNCT.test(cuts[j][0]) && !HARD.test(cuts[j][0])) j--;
          const since = masked.slice(j >= 0 ? cuts[j].index + cuts[j][0].length : 0, m.index);   // back to the last comma or sentence end
          d = /[\uE000-\uEFFF]\s*$/.test(seg) && /^\s*[\uE000-\uEFFF]/.test(next) ? "," : EXC.test(since) && !NEG.test(since) ? " " : ";";
        }
      }
      if (lettered(seg)) { segs.push([last, m.index]); marked += seg + String.fromCharCode(MARK0 + segs.length - 1) + d; }
      else marked += seg + d;
      last = m.index + m[0].length;
    });
    if (lettered(masked.slice(last))) segs.push([last, masked.length]);
    marked += masked.slice(last);
    const pairs = [], cs = clauses(spaced(toEnglish(marked, lang, pairs)), true), out = [], wrote = pairs.map(([en, o]) => [en, raw(o)]);
    let from = 0;
    cs.forEach((c, i) => {
      const ms = [...c.matchAll(MARKS)].map(m => m[0].charCodeAt(0) - MARK0);
      const a = Math.min(from, segs.length - 1), z = Math.max(a, i === cs.length - 1 ? segs.length - 1 : ms.length ? Math.max(...ms) : a);
      const src = segs.length ? raw(masked.slice(segs[a][0], segs[z][1])).replace(/\s+/g, " ").trim() : "";
      out.push({ c: c.replace(MARKS, " ").replace(/\s+/g, " ").trim(), src: src || raw(c.replace(MARKS, "")).trim(), tr: true, pairs: wrote });
      if (ms.length) from = z + 1;
    });
    return out;
  }
  /* a word of the English reading, as the writer wrote it: “Freitag”, not “friday” */
  function own(u, part) {
    const src = part.src, low = src.toLowerCase(), one = v => {
      const lv = v.toLowerCase();
      if (low.includes(lv)) return v;
      const hit = part.pairs.find(([en, o]) => o && low.includes(o.toLowerCase()) && new RegExp(`(?<!${LN})${esc(lv)}(?!${LN})`, "u").test(en));
      if (hit) return hit[1];
      const near = CJK.test(v) ? new RegExp([...v].map(esc).join(".{0,4}?"), "u").exec(src) : null;   // a word that lost its small words
      return near ? near[0] : v;
    };
    const all = one(u);
    return all !== u || low.includes(u.toLowerCase()) ? all : u.split(/\s+/).map(one).filter((v, i, a) => a.indexOf(v) === i).join(" ");
  }

  /* the whole text → the wallet's rule {freeze, only, cap, from, co} and the items it came from */
  function parse(text, ctx) {
    ctx = { now: new Date(), book: [], guardian: null, me: null, ...(ctx || {}) };
    const items = pieces(text, ctx).slice(0, 12).flatMap(p => readClause(p.c, ctx, p));
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

  const api = { parse, build, fromTau, judge, tests, idle, clauses, pieces, langOf, day, num, MAX_AMOUNT, MAX_ONLY };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RuleWords = api;
})(typeof window !== "undefined" ? window : globalThis);
