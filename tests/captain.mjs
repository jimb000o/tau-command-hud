// The cruise captains aboard in White Rabbit Key (rabbit/captain.js): every line has its Chinese and Japanese, every
// trick the relay's pirates can try (infra/relay/cruise.py TRICKS) has the captain's words for it, the numbers the
// captains say are the relay's own limits, every captain says first that they are made up, and nobody is blamed.
//   node tests/captain.mjs
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
const root = new URL("..", import.meta.url), read = p => readFileSync(new URL(p, root), "utf8");
const CAP = createRequire(import.meta.url)(new URL("rabbit/captain.js", root).pathname);
const fail = [];
const bad = m => fail.push(m);

/* every English line (a string with a space and words), as game.js shows it through TauI18n */
const src = read("rabbit/captain.js").replace(/\/\*[\s\S]*?\*\//g, "");
const NOT = new Set(["use strict", "no landing", "chain restarted", "no answer from the node to sendtx", ...CAP.CREW, ...Object.values(CAP.CAPTAINS).map(c => c.name)]);
const lines = [...new Set([...src.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map(m => m[1]).filter(t => / /.test(t) && /[a-z]{3}/.test(t) && !NOT.has(t)))];
const holes = t => [...t.matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort().join(",");
for (const lang of ["zh", "ja"]) {
  let dict = {};
  globalThis.TauI18n = { add: d => { dict = Object.assign(dict, d.strings); } };
  new Function(read(`assets/i18n/${lang}/rabbit.js`))();
  for (const t of [...lines, "payment", "booking", "withdrawal", "transaction", "calm", "busy", "strained"]) {
    if (!(t in dict)) bad(`${lang}: no translation for "${t.slice(0, 80)}"`);
    else if (holes(t) !== holes(dict[t])) bad(`${lang}: "${t.slice(0, 60)}" has {${holes(t)}}, the translation {${holes(dict[t])}}`);
  }
}

/* the relay's tricks and limits, as cruise.py has them */
const py = read("infra/relay/cruise.py");
const tricks = [...py.slice(py.indexOf("TRICKS = {"), py.indexOf("\n}\n", py.indexOf("TRICKS = {"))).matchAll(/^    "(\w+)": \(/gm)].map(m => m[1]);
if (tricks.length < 10) bad("could not read TRICKS from cruise.py");
for (const k of tricks) if (!CAP.TRICK[k]) bad(`cruise.py has the trick "${k}", captain.js has no words for it (TRICK)`);
const num = re => { const m = re.exec(py); return m ? Number(m[1]) : NaN; };
const facts = [
  [num(/^RATE = (\d+)/m), 12, "RATE (the captains say: twelve a minute at most)"],
  [num(/^TRIAL_MAX = (\d+)/m), 5, "TRIAL_MAX (five at most on a kind's first visit)"],
  [num(/^INCIDENT_TAIL = (\d+)/m), 50, "INCIDENT_TAIL (the last fifty logbook entries)"],
  [num(/^LAND_WAIT = (\d+) \* 60/m), 10, "LAND_WAIT (within ten minutes, or sail on)"],
  [num(/^BOARDING = (\d+)/m), 10, "BOARDING (the last ten minutes)"],
  [num(/"queen":[\s\S]*?"landing": (\d+)/), 30, "the Queen's landing (in waves over thirty minutes)"],
  [num(/"pirates":[\s\S]*?"passengers": (\d+)/), 20, "the Black Sequence's pirates (twenty)"],
  [num(/"dryrun":[\s\S]*?"passengers": (\d+)/), 40, "MS Dry Run's passengers (forty)"],
  [num(/"queen":[\s\S]*?"passengers": (\d+)/), 120, "Queen Mempool's guests (a hundred and twenty)"],
];
for (const [have, want, what] of facts) if (have !== want) bad(`cruise.py ${what}: ${have}, the captains say ${want}`);
if (!/never once half of that budget is used/.test(py)) bad("cruise.py no longer says the ships stop at half of the island's daily budget; the Commodore does");

/* every captain says first that they and their passengers are made up; nobody is blamed, nothing internal is named */
for (const [ship, t] of Object.entries(CAP.HELLO)) if (!/made up|fiction|a character/.test(t)) bad(`${ship}: the captain's first line must say they are made up`);
for (const t of lines) if (/\bIDNI\b|Matrix|Uplink|moon|to the moon|price/i.test(t)) bad(`a line names something it must not: "${t.slice(0, 80)}"`);

/* every kind of news in a preview has a line, and a held finding is never told */
const ctx = { place: id => id, time: () => "16:40", day: () => "Tuesday" };
for (const ship of ["pirates", "dryrun", "queen"]) {
  for (const e of CAP.previewLog(ship, 1e9)) if (!CAP.event(ship, e, ctx)) bad(`${ship}: no line for the preview entry ${e.kind}`);
  const h = CAP.event(ship, { kind: "trick", held: true, ok: null, note: "held back" }, ctx);
  if (!h || !/held back/i.test(h.s)) bad(`${ship}: a held finding must be told as held back`);
  if (!CAP.asks(ship).length) bad(`${ship}: no questions`);
  for (const ph of ["approach", "waiting", "landing", "ashore", "boarding", "gone"]) {
    const s = CAP.status(ship, { phase: ph, t0: 1e9, end: 1e9 + 5400, passengers: 20, sent: { pay: 3 }, refused: 0, tricks: { stopped: 2 }, brake: "none", per_min: 12 }, { state: "calm", waiting: 1, sealed: 9 }, ctx);
    if (!s.length) bad(`${ship}: nothing to say while ${ph}`);
  }
  const d = CAP.debrief(ship, { t0: 1e9, landed: true, sent: { pay: 9 }, refused: {}, skipped: 0, changed: [{ what: "transactions a minute", from: 12, to: 11, because: "3 sends got no answer" }], tricks: { replay: { tried: 2, stopped: 2 } } }, ctx);
  if (d.length < 3) bad(`${ship}: the debrief is too short`);
}
for (const k of Object.keys(CAP.TRICK)) {
  const l = CAP.event("pirates", { kind: "trick", trick: k, stopped: true, ok: false, code: "X", p: 1, i: 1 }, ctx);
  if (!l || !l.v || !/X/.test(l.v.r)) bad(`trick ${k}: the captain must name the chain's answer`);
}

if (fail.length) { console.error(fail.join("\n")); process.exit(1); }
console.log(`captain.js: ${lines.length} lines, each in zh and ja; ${tricks.length} tricks with words; the captains' numbers match cruise.py`);
