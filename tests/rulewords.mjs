/* Checks assets/rulewords.js, the plain words behind tauhud.com/builder/:
   1. sentences → the wallet's blocks (limit, list, day, co-signer, freeze), and what is not possible says so;
   2. every rule it writes is read by the exact reader (assets/rulefacts.js): one answer for every kind of payment,
      and the plain reading of the blocks (judge) gives that same answer for each kind;
   3. the test payments it makes get the answer it predicts from the exact reader too;
   4. a part that never decides is found, and a wallet rule read back from its Tau text gives the same text again.
   Run: node tests/rulewords.mjs */
import { createRequire } from "node:module";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const req = createRequire(import.meta.url);
const RW = req(join(ROOT, "assets", "rulewords.js")), RF = req(join(ROOT, "assets", "rulefacts.js"));
const fails = [];
let checked = 0;
const check = (ok, what) => { checked++; if (!ok) fails.push(what); };

const NOW = new Date(2026, 10, 12, 10, 0, 0);   // Thursday 12 Nov 2026, local time
const G = "cd".repeat(48), MIA = "ab".repeat(48), LEE = "12".repeat(48), X = "ef".repeat(48);
const ctx = { now: NOW, guardian: G, book: [{ name: "Mia", addr: MIA }, { name: "Mia Lee", addr: LEE }] };
const day = (y, m, d) => Math.floor(new Date(y, m - 1, d).getTime() / 1000);
const hex96 = v => BigInt(v).toString(16).padStart(96, "0");

/* ---- 1. words → blocks ---- */
const WORDS = [
  ["At most 5,000 per payment", { cap: 5000 }],
  ["max 500", { cap: 500 }],
  ["no more than 1.000 per transfer", { cap: 1000 }],
  ["up to 2k", { cap: 2000 }],
  ["under 50", { cap: 49 }],
  ["no payments over 2000", { cap: 2000 }],
  ["nothing above 300", { cap: 300 }],
  ["co-sign above 1,000", { co: [1000, G] }],
  ["Above 1k the Guardian co-signs", { co: [1000, G] }],
  ["above 1000 Mia must co-sign", { co: [1000, MIA] }],
  ["above 250 a second signature from " + X, { co: [250, X] }],
  ["nothing before Friday", { from: day(2026, 11, 13) }],
  ["nothing before Thursday", { from: day(2026, 11, 19) }],
  ["no money leaves before Fri", { from: day(2026, 11, 13) }],
  ["locked until 2026-12-24", { from: day(2026, 12, 24) }],
  ["nothing leaves before 1 Dec", { from: day(2026, 12, 1) }],
  ["not before January 5, 2027", { from: day(2027, 1, 5) }],
  ["lock for 90 days", { from: day(2027, 2, 10) }],
  ["nothing until tomorrow", { from: day(2026, 11, 13) }],
  ["only to Mia", { only: [MIA] }],
  ["only to Mia Lee", { only: [LEE] }],
  ["only to " + X, { only: [X] }],
  ["only to my address book", { only: [MIA, LEE] }],
  ["freeze", { freeze: true }],
  ["block everything", { freeze: true }],
  ["At most 5,000 per payment, above 1,000 the Guardian co-signs, nothing before Friday", { cap: 5000, co: [1000, G], from: day(2026, 11, 13) }],
  ["Only to Mia and at most 300 per payment; nothing before 2027-01-01", { only: [MIA], cap: 300, from: day(2027, 1, 1) }],
  ["max 100\nmax 200", { cap: 200 }],
  /* a word for "everything" followed by an amount is a limit, never a freeze */
  ["block everything over 1000", { cap: 1000 }],
  ["stop all payments above 2k", { cap: 2000 }],
  ["payments over 500 are blocked", { cap: 500 }],
  ["don't let me send more than 200", { cap: 200 }],
  ["only 100 per payment", { cap: 100 }],
  ["stop all payments", { freeze: true }],
  ["no payments", { freeze: true }],
  ["pause my wallet", { freeze: true }],
  ["block everything over 1000 unless Mia signs", { co: [1000, MIA] }],
  ["above 1000, the Guardian co-signs", { co: [1000, G] }],
  ["block everything except Mia", { only: [MIA] }],
  ["nothing to anyone but Mia", { only: [MIA] }],
  ["block payments to strangers", { only: [MIA, LEE] }],
  ["only to Mia at most 300 per payment", { only: [MIA], cap: 300 }],
  ["lock my savings until 2028", { from: day(2028, 1, 1) }],
  ["nothing before the end of 2027", { from: day(2028, 1, 1) }],
  ["nothing until next month, then at most 100", { cap: 100, from: day(2026, 12, 1) }],
];
for (const [text, want] of WORDS) {
  const p = RW.parse(text, ctx), r = p.rule || {};
  const got = { ...(r.cap != null ? { cap: r.cap } : {}), ...(r.co ? { co: [r.co.limit, r.co.who[0]] } : {}), ...(r.from != null ? { from: r.from } : {}), ...(r.only && r.only.length ? { only: r.only } : {}), ...(r.freeze ? { freeze: true } : {}) };
  check(JSON.stringify(got) === JSON.stringify({ ...(want.cap != null ? { cap: want.cap } : {}), ...(want.co ? { co: want.co } : {}), ...(want.from != null ? { from: want.from } : {}), ...(want.only ? { only: want.only } : {}), ...(want.freeze ? { freeze: true } : {}) }),
    `“${text}”: wanted ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
  check(p.items.every(i => i.kind !== "no"), `“${text}”: a part was not understood: ${p.items.filter(i => i.kind === "no").map(i => i.src).join(" | ")}`);
}
/* what is not possible, or not understood, builds nothing and says which */
const NO = [["max 100 a day", "period"], ["at most 500 per week", "period"], ["only on weekdays", "clock"], ["between 9 and 17 o'clock", "clock"], ["keep at least 1000", "balance"],
  ["never to " + X, "blocklist"], ["hello world", "unknown"], ["only to Bob", "only-who"], ["nothing before", "day"], ["co-sign everything", "co-amount"], ["max 99999999", "range"],
  /* part of a coin is never rounded; an exception, a forbidden payee and an unknown co-signer build nothing and say so */
  ["at most 1,5 per payment", "whole"], ["at most 1.5 per payment", "whole"], ["above 2.5 the Guardian co-signs", "whole"],
  ["send at most 100 to anyone except Mia", "except"], ["above 1000 the Guardian co-signs except for Mia", "except"],
  ["block all payments to Mia", "blocklist"], ["block everything over 1k unless my brother signs", "co-who"], ["block everything except Bob", "only-who"],
  ["payments above 1000", "above-what"]];
for (const [text, code] of NO) {
  const p = RW.parse(text, ctx);
  check(!p.rule && p.items.length === 1 && p.items[0].kind === "no" && p.items[0].code === code, `“${text}”: wanted no rule (${code}), got ${JSON.stringify(p.items.map(i => [i.kind, i.code]))}`);
}
check(RW.parse("co-sign above 1000", { now: NOW }).items[0].code === "co-who", "a co-signature without a co-signer and without the Guardian asks who");
check(RW.parse("max 500, max 100 a day", ctx).rule.cap === 500, "a part that is not possible leaves the other parts standing");
check(/my brother/.test(RW.parse("block everything over 1k unless my brother signs", ctx).items[0].why), "an unknown co-signer is not named in the answer");
check(RW.parse("max 2.5k", ctx).rule.cap === 2500, "2.5k is a whole amount");
/* words of an understood part that are not in the rule are said, never dropped in silence */
const UNUSED = [["at most 100 to Mia", "“to Mia”"], ["at most 500 before Friday", "“before Friday”"], ["only to Mia and Bob", "“Bob”"], ["only to Mia before Friday", "“before Friday”"], ["freeze my llama", "“my llama”"]];
for (const [text, want] of UNUSED) { const p = RW.parse(text, ctx); check(p.rule && p.items[0].unused === want, `“${text}”: wanted ${want} reported as not used, got ${p.items[0].unused}`); }
for (const [text] of WORDS) check(RW.parse(text, ctx).items.every(i => !i.unused), `“${text}”: words reported as not used: ${RW.parse(text, ctx).items.map(i => i.unused).filter(Boolean).join(" ")}`);

/* ---- 2 to 4. the rules it writes, read by the exact reader ---- */
let kinds = 0, tests = 0;
const caseOf = cell => {
  const v = cell.v, signed = [];
  for (let k = 0; k < 8; k++) { const x = v["i" + (18 + k)]; signed.push(x != null && BigInt(x) !== 0n ? hex96(x) : ""); }
  return { amount: Number(v.i1 ?? 1), to: v.i4 != null ? hex96(v.i4) : "5e".repeat(48), ts: v.i5 != null ? Number(v.i5) : 0, signed, d: RF.OUTCOME[cell.d] };
};
const inputs = p => ({ i1: String(p.amount), i4: "#x" + p.to, i5: String(p.ts), i18: p.signed[0] ? "#x" + p.signed[0] : "0" });
for (const [text] of WORDS) {
  const p = RW.parse(text, ctx), r = RF.read(p.text);
  check(r.ok && !r.has.open && !r.has.none, `“${text}”: the exact reader finds a payment without exactly one answer`);
  if (!r.ok) continue;
  const cases = r.cells.map(caseOf);
  kinds += cases.length;
  for (const c of cases) check((RW.judge(p.rule, c).length ? "block" : "pass") === c.d, `“${text}”: plain reading and exact reader differ for ${JSON.stringify(c)}`);
  for (const t of RW.tests(p.rule, { now: NOW })) {
    tests++;
    const a = RF.answer(p.text, inputs(t));
    check(a.outcome === (t.stop.length ? "block" : "pass"), `“${text}”: test “${t.says}” predicted ${t.stop.length ? "block" : "pass"}, the reader says ${a.outcome}`);
  }
  const back = RW.fromTau(p.text);
  check(back && RW.build(back) === p.text, `“${text}”: the rule read back from its Tau text does not give the same text`);
  check(RW.idle(p.rule, cases).length === 0, `“${text}”: a part is reported as never deciding: ${RW.idle(p.rule, cases)}`);
}
{ /* a limit of 500 stops everything a co-signature above 1,000 would stop: that part never decides */
  const p = RW.parse("max 500 per payment, co-sign above 1,000", ctx), cases = RF.read(p.text).cells.map(caseOf);
  check(JSON.stringify(RW.idle(p.rule, cases)) === '["co"]', "the co-signature above the limit is not found as a part that never decides");
}
check(RW.fromTau("always ( (i1[t]:bv[24] > { 5000 }:bv[24]) -> (o5[t]:bv[24] = { #x000000 }:bv[24]) ).") === null, "a hand-written rule is taken for one of the wallet's");

const lines = [`## Rule words: ${checked} checks`, "",
  `- ${WORDS.length} sentences that give a rule, ${NO.length} that say why they cannot, ${UNUSED.length} that say which words they did not use`,
  `- ${kinds} kinds of payment where the plain reading must match the exact reader, ${tests} test payments`, ""];
if (fails.length) lines.push(`### ❌ ${fails.length} failed`, "", ...fails.map(f => "- " + f));
else lines.push("Every answer matches. ✅");
console.log(lines.join("\n"));
process.exit(fails.length ? 1 : 0);
