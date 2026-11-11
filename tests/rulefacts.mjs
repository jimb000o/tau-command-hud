/* Checks assets/rulefacts.js, the reader behind the Playground's X-ray, "what would pass" and the case builder:
   1. against the real Tau engine: every answer in tests/rulefacts-cases.json (rules we wrote, run with tau-lang);
   2. against the lessons on /learn/: every run and every rule-shaped sat in learn/lessons.json that it can read
      gets the answer the lesson expects (the lessons themselves are checked against the engine by `up tau`);
   3. the facts the pages show for known rules (the Playground's examples, a rule that leaves its answer open, …);
   4. what a change to the network's rules decides differently (tests/meaning-cases.json, shared with the Python twin).
   Run: node tests/rulefacts.mjs */
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const RF = createRequire(import.meta.url)(join(ROOT, "assets", "rulefacts.js"));
const fails = [];
let checked = 0;
const check = (ok, what) => { checked++; if (!ok) fails.push(what); };
const big = v => typeof v === "bigint" ? v : BigInt(v);

/* ---- 1. the engine's own answers ---- */
const fx = JSON.parse(await readFile(join(ROOT, "tests", "rulefacts-cases.json"), "utf8"));
let engineAnswers = 0;
for (const c of fx.cases) {
  let reading = c.watch === "o5" ? RF.read(c.rule) : null;
  if (reading && !reading.ok && reading.code === "outputs") reading = null;   // also sets o1: answered per transfer only
  for (const p of c.probes) {
    engineAnswers++;
    let got;
    try { got = RF.answer(c.rule, p.in, { out: c.watch }); } catch (e) { check(false, `${c.id} / ${p.name}: ${e.message}`); continue; }
    check(got.value !== null && got.value === big(p.engine), `${c.id} / ${p.name}: engine ${p.engine}, reader ${got.value} (allowed ${got.allowed.join(" ")})`);
    if (reading) {
      check(reading.ok, `${c.id}: the X-ray cannot read it (${reading.why})`);
      if (!reading.ok) continue;
      const at = {};
      for (const x of reading.inputs) at[x.name] = big(/^#x/.test(p.in[x.name] || "") ? "0x" + p.in[x.name].slice(2) : p.in[x.name] || 0);
      const cell = reading.cells.find(cl => reading.inputs.every(x => RF.words.pieceOf(x.pieces, cl.v[x.name]) === RF.words.pieceOf(x.pieces, at[x.name])));
      const want = big(p.engine) === 0n ? "block" : "pass";
      check(cell && RF.OUTCOME[cell.d] === want, `${c.id} / ${p.name}: X-ray says ${cell && cell.d}, engine ${p.engine}`);
    }
  }
}

/* ---- 2. the lessons ---- */
const lessons = JSON.parse(await readFile(join(ROOT, "learn", "lessons.json"), "utf8")).lessons;
let lessonAnswers = 0;
const asRule = spec => /^\s*always\b/.test(spec) ? spec : `always ( ${spec} ).`;
for (const l of lessons) for (const [kind, t] of [...l.tries.map(t => ["try", t]), ["task", l.task]]) {
  const spec = kind === "task" ? t.solution : t.spec;
  if (!/\[t\]/.test(spec) || /\[t-\d+\]|\bsometimes\b/.test(spec)) continue;
  if (t.op === "run") {
    for (const [o, want] of Object.entries(t.expect.out || {})) {
      t.steps.forEach((step, i) => {
        let got;
        try { got = RF.answer(spec, step, { out: o }); } catch (e) { return; }   // outside what the reader covers
        lessonAnswers++;
        check(got.value !== null && String(got.value) === want[i], `lesson ${l.id} ${kind} “${t.label || t.text}”: step ${i + 1} ${o} expected ${want[i]}, reader ${got.value}`);
      });
    }
  } else if (t.op === "sat" && /\bo5\[t\]/.test(spec)) {
    const r = RF.read(asRule(spec));
    if (!r.ok) continue;
    lessonAnswers++;
    check(r.total === t.expect.verdict, `lesson ${l.id} ${kind} “${t.label || t.text}”: sat expected ${t.expect.verdict}, reader ${r.total}`);
  }
}

/* ---- 3. facts the pages show ---- */
const BOB = "a0f7d1a0b1b0c7e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2";
const addr = h => `{ #x${h} }:bv[384]`;
const O0 = "(o5[t]:bv[24] = { #x000000 }:bv[24])", O1 = "(o5[t]:bv[24] = { #x000001 }:bv[24])";
const groupsSay = (r, x) => { const inp = r.inputs.find(i => i.name === x); return inp.groups.map(g => [RF.words.groupWords(inp, g, { [BOB]: "Bob" }).join(" / "), r.cells.find(c => g.includes(RF.words.pieceOf(inp.pieces, c.v[x]))).d]); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

{ // a limit: one cut at 1,000, every transfer answered once
  const r = RF.read(`always ( (i1[t]:bv[24] > { 1000 }:bv[24]) ? ${O0} : ${O1} ).`);
  check(r.ok && r.total && r.decided && same(r.read, ["i1"]), "limit: read once, total, decided, reads i1");
  check(same(groupsSay(r, "i1"), [["up to 1,000", "pass"], ["1,001 or more", "block"]]), "limit: up to 1,000 passes, 1,001 or more blocked: " + JSON.stringify(groupsSay(r, "i1")));
  const e = RF.edges(r);
  check(e.length === 1 && e[0].below === 1000n && e[0].above === 1001n && e[0].belowSays === "pass" && e[0].aboveSays === "block", "limit: one edge, 1,000 passes and 1,001 is blocked");
  const w = RF.wouldPass(r, { i1: 5000 });
  check(w && w.now === "block" && w.ways.length === 1 && w.ways[0].input === "i1" && w.ways[0].nearest === 1000n, "limit: 5,000 would pass at 1,000");
}
{ // the wallet template in clause form: says only when to block, so every transfer of the author is blocked
  const r = RF.read(`always ( (i1[t]:bv[24] > { 5000 }:bv[24]) -> ${O0} ).`);
  check(r.ok && r.total && !r.decided && r.all === "block", "clause form: open below the limit, every transfer blocked");
  check(same(groupsSay(r, "i1"), [["up to 5,000", "open"], ["5,001 or more", "block"]]), "clause form: open up to 5,000: " + JSON.stringify(groupsSay(r, "i1")));
  check(same(RF.wouldPass(r, { i1: 100 }).ways, []), "clause form: no single change lets 100 through");
}
{ // a receiver list
  const r = RF.read(`always ( (i4[t]:bv[384] = ${addr(BOB)}) ? ${O1} : ${O0} ).`);
  check(same(groupsSay(r, "i4"), [["anyone else", "block"], ["Bob", "pass"]]) || same(groupsSay(r, "i4"), [["Bob", "pass"], ["anyone else", "block"]]), "receiver: Bob passes, anyone else blocked: " + JSON.stringify(groupsSay(r, "i4")));
}
{ // a time lock
  const r = RF.read(`always ( (i5[t]:bv[64] < { 1798761600 }:bv[64]) ? ${O0} : ${O1} ).`);
  check(same(groupsSay(r, "i5"), [["before 2027-01-01", "block"], ["on or after 2027-01-01", "pass"]]), "time lock: " + JSON.stringify(groupsSay(r, "i5")));
}
{ // two inputs: Bob exempt from the limit
  const r = RF.read(`always ( ((i4[t]:bv[384] = ${addr(BOB)}) || (i1[t]:bv[24] <= { 1000 }:bv[24])) ? ${O1} : ${O0} ).`);
  check(r.ok && same(r.read, ["i1", "i4"]) && r.has.pass && r.has.block && r.total && r.decided, "Bob exempt: reads amount and receiver");
  const w = RF.wouldPass(r, { i1: 5000, i4: "0x" + "11".repeat(48) });
  check(w.ways.length === 2, "Bob exempt: 5,000 to Carol passes with a smaller amount or to Bob");
}
{ // overlapping cases that disagree: no answer above 5,000
  const r = RF.read(`always ( ((i1[t]:bv[24] > { 5000 }:bv[24]) -> ${O0}) && ((i1[t]:bv[24] > { 1000 }:bv[24]) -> ${O1}) ).`);
  check(r.ok && !r.total && r.has.none && r.has.pass && r.has.open, "overlap: none above 5,000, pass between, open below");
}
{ // mentioned, never read
  const r = RF.read(`always ( (i4[t]:bv[384] = { 7 }:bv[384]) ? ((i1[t]:bv[24] > { 5000 }:bv[24]) ? ${O0} : ${O1}) : ((i1[t]:bv[24] > { 5000 }:bv[24]) ? ${O0} : ${O1}) ).`);
  check(r.ok && same(r.read, ["i1"]) && r.inputs.find(i => i.name === "i4").groups.length === 1, "receiver mentioned in both branches alike: not read");
}
{ // two inputs compared with each other
  const r = RF.read(`always ( (i3[t]:bv[384] = i4[t]:bv[384]) ? ${O0} : ${O1} ).`);
  check(r.ok && same(r.shared, ["i3", "i4"]) && r.has.pass && r.has.block, "sender = receiver: read with both inputs together");
}
{ // a rule that computes with an input is outside the X-ray, but answered for one transfer
  const t = `always ( ((i1[t]:bv[24] % { 2 }:bv[24]) = { 0 }:bv[24]) ? ${O1} : ${O0} ).`;
  const r = RF.read(t);
  check(!r.ok && r.code === "computes", "even amounts: outside the X-ray (computes)");
  check(RF.answer(t, { i1: 4 }).outcome === "pass" && RF.answer(t, { i1: 5 }).outcome === "block", "even amounts: 4 passes, 5 is blocked");
}
{ // other steps, other outputs, text
  check(RF.read(`always ( (i1[t-1]:bv[24] > { 1000 }:bv[24]) ? ${O0} : ${O1} ).`).code === "temporal", "an earlier step is outside");
  check(RF.read("always ( o9[t]:bv[24] = { #x000000 }:bv[24] ).").code === "noout", "a rule without o5");
  check(RF.read("always ( o5[t]:bv[24] = { #x000001 }:bv[24] && o8[t]:bv[24] = { 1 }:bv[24] ).").code === "outputs", "o5 with another output is outside");
  check(RF.read("Block anything above 1000").ok === false, "plain words are not a rule");
}
{ // two rules side by side
  const d = RF.diff(`always ( (i1[t]:bv[24] > { 1000 }:bv[24]) ? ${O0} : ${O1} ).`, `always ( (i1[t]:bv[24] > { 2000 }:bv[24]) ? ${O0} : ${O1} ).`);
  check(d.ok && d.changed.length > 0 && d.changed.every(c => c.v.i1 >= 1001n && c.v.i1 <= 2000n && c.was === "block" && c.now === "pass"), "diff: 1,001 to 2,000 now pass");
  check(RF.diff(`always ( (i1[t]:bv[24] > { 1000 }:bv[24]) ? ${O0} : ${O1} ).`, `always ( (i1[t]:bv[24] <= { 1000 }:bv[24]) ? ${O1} : ${O0} ).`).same, "diff: the same rule written two ways");
}

/* ---- 4. what a change to the network's rules decides differently (the box on /proposals/ and /history/; the
   Telegram posts write the same lines with infra/alerts/rulefacts.py, checked against the same file) ---- */
const mc = JSON.parse(await readFile(join(ROOT, "tests", "meaning-cases.json"), "utf8"));
for (const c of mc.cases) {
  const spec = RF.clausesOf(mc.spec);
  for (const r of c.before || []) Object.assign(spec, RF.clausesOf(r));
  const m = RF.meaning(spec, c.revisions);
  const lines = RF.words.meaningLines(m).map(l => `${l.topic} · ${RF.words.lineText(l)}`);
  const streams = m.streams.map(s => `${s.stream}:${s.ok ? (s.same ? "same" : "changed") : s.code}`).join(" ");
  check(m.ok === c.ok && m.same === c.same && streams === c.streams, `meaning ${c.id}: ${m.ok} ${m.same} "${streams}", expected "${c.streams}"`);
  check(same(lines, c.lines), `meaning ${c.id}: ${JSON.stringify(lines)}`);
}

const lines = [`## Rule reader: ${checked} checks`, "",
  `- ${engineAnswers} answers of the real Tau engine (tests/rulefacts-cases.json)`,
  `- ${lessonAnswers} lesson answers from learn/lessons.json`,
  `- ${mc.cases.length} rule changes read for /proposals/ and the Telegram posts (tests/meaning-cases.json)`, ""];
if (fails.length) lines.push(`### ❌ ${fails.length} failed`, "", ...fails.map(f => "- " + f));
else lines.push("Every answer matches. ✅");
console.log(lines.join("\n"));
process.exit(fails.length ? 1 : 0);
