// The list of every line the islanders speak aloud, as the server reads it (rabbit/voices.json), made from rabbit/rico.js
// (with what the islanders answer, rabbit/talk.js) and the lines of the island's quarters in rabbit/cast.json (each must be in rabbit/game.js word for word).
//   node tests/voices.mjs           checks that rabbit/voices.json matches rico.js
//   node tests/voices.mjs --write   writes it again after a line changed
import { readFileSync, writeFileSync } from "node:fs";
const root = new URL("..", import.meta.url);
globalThis.window = {}; globalThis.addEventListener = globalThis.removeEventListener = () => {}; globalThis.fetch = () => Promise.reject(new Error("offline"));
new Function(readFileSync(new URL("rabbit/talk.js", root), "utf8"))();
new Function(readFileSync(new URL("rabbit/rico.js", root), "utf8"))();
/* a line that waits for a cruise ship names only facts talk.js RABBIT_SHIP_WHEN gives, or it is never said and its clip is wasted */
const SHIPK = window.RABBIT_SHIP_WHEN.keys, whens = [...Object.values(window.RABBIT_TALK).flatMap(t => [...(t.back || []).map(([w]) => w),
  ...(t.ask || []).flatMap(q => [q.when || "", ...q.a.map(([w]) => w), ...(q.more ? q.more.a.map(([w]) => w) : [])])]), ...window.RICO.CALLS.map(c => c.when || "")];
for (const w of whens) for (const k of w.split("+").map(k => k.replace(/^!/, "")))
  if (/^ship|^queen$|^dryrun$/.test(k) && !SHIPK.includes(k)) { console.error(`a line waits for "${w}": ${k} is not a ship fact (talk.js RABBIT_SHIP_WHEN)`); process.exit(1); }
const game = readFileSync(new URL("rabbit/game.js", root), "utf8"), cast = JSON.parse(readFileSync(new URL("rabbit/cast.json", root), "utf8"));
for (const c of cast) if (!game.includes(JSON.stringify(c.text))) { console.error(`rabbit/cast.json: not in game.js: ${c.text}`); process.exit(1); }
const seen = new Set(), list = [...window.RICO.all().map(([who, text]) => ({ who, text })), ...cast].filter(c => !seen.has(c.who + "|" + c.text) && seen.add(c.who + "|" + c.text));
/* the show's opener is shouted for joy: make.py reads "how": "hype" */
const R = window.RICO, hype = new Set(Object.keys(R.SETS).filter(k => /^wake/.test(k)).flatMap(k => R.SETS[k]).map(k => R.L[k]));
for (const c of list) if (c.who === "rico" && hype.has(c.text)) c.how = "hype";
/* the Night Line is spoken calm and low, Rico and his callers alike: make.py reads "how": "night" */
const night = new Set([...(R.NIGHT || []).flatMap(c => c.say.map((t, i) => (i % 2 ? "rico" : c.who) + "|" + t)), ...["nlOpen", "nlRing", "nlBye", "nlClose"].flatMap(k => R.SETS[k] || []).map(k => "rico|" + R.L[k])]);
for (const c of list) if (night.has(c.who + "|" + c.text)) c.how = "night";
const json = JSON.stringify(list, null, 1) + "\n", file = new URL("rabbit/voices.json", root);
if (process.argv.includes("--write")) { writeFileSync(file, json); console.log(`rabbit/voices.json: ${list.length} lines`); }
else {
  let now = ""; try { now = readFileSync(file, "utf8"); } catch (e) {}
  if (now !== json) { console.error("rabbit/voices.json is out of date: run node tests/voices.mjs --write"); process.exit(1); }
  console.log(`rabbit/voices.json ok: ${list.length} lines`);
}
