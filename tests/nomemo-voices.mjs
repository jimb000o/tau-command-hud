// The lines the crew of the Black Sequence speak aloud in No Memo, as the server reads them (nomemo/voices.json), made
// from nomemo/game.js: every fixed crew line (the briefs, the post, the greetings), without the ones filled with numbers.
//   node tests/nomemo-voices.mjs           checks that nomemo/voices.json matches game.js
//   node tests/nomemo-voices.mjs --write   writes it again after a line changed
import { readFileSync, writeFileSync } from "node:fs";
const root = new URL("..", import.meta.url);
const src = readFileSync(new URL("nomemo/game.js", root), "utf8");
const who = /^(qm|look|bosun)$/;
const list = [], seen = new Set();
const add = (w, t) => { if (!who.test(w) || t.includes("{") || seen.has(w + "|" + t)) return; seen.add(w + "|" + t); list.push({ who: w, text: t }); };
/* the contracts: who, brief, after */
for (const m of src.matchAll(/\{ id: "(\w+)", name: "[^"]*", who: "(\w+)",[\s\S]*?brief: "((?:[^"\\]|\\.)*)",[\s\S]*?after: "((?:[^"\\]|\\.)*)" \}/g)) { add(m[2], m[3]); add(m[2], m[4]); }
/* crew(who, "line") and post(who, "line") with a fixed English line */
for (const m of src.matchAll(/\b(?:crew|post)\("(qm|look|bosun)", "((?:[^"\\]|\\.)*)"/g)) add(m[1], m[2]);
for (const m of src.matchAll(/\bcrew\("(qm|look|bosun)", [^"\n]*?\? "((?:[^"\\]|\\.)*)" : [^"\n]*?\? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"/g)) { add(m[1], m[2]); add(m[1], m[3]); add(m[1], m[4]); }
const json = JSON.stringify(list, null, 1) + "\n", file = new URL("nomemo/voices.json", root);
if (process.argv.includes("--write")) { writeFileSync(file, json); console.log(`nomemo/voices.json: ${list.length} lines, ${list.reduce((a, l) => a + l.text.length, 0)} characters`); }
else {
  let now = ""; try { now = readFileSync(file, "utf8"); } catch (e) {}
  if (now !== json) { console.error("nomemo/voices.json is out of date: run node tests/nomemo-voices.mjs --write"); process.exit(1); }
  console.log(`nomemo/voices.json ok: ${list.length} lines`);
}
