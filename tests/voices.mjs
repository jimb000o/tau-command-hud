// The list of every line the islanders speak aloud, as the server reads it (rabbit/voices.json), made from rabbit/rico.js.
//   node tests/voices.mjs           checks that rabbit/voices.json matches rico.js
//   node tests/voices.mjs --write   writes it again after a line changed
import { readFileSync, writeFileSync } from "node:fs";
const root = new URL("..", import.meta.url);
globalThis.window = {}; globalThis.fetch = () => Promise.reject(new Error("offline"));
new Function(readFileSync(new URL("rabbit/rico.js", root), "utf8"))();
const list = window.RICO.all().map(([who, text]) => ({ who, text }));
const json = JSON.stringify(list, null, 1) + "\n", file = new URL("rabbit/voices.json", root);
if (process.argv.includes("--write")) { writeFileSync(file, json); console.log(`rabbit/voices.json: ${list.length} lines`); }
else {
  let now = ""; try { now = readFileSync(file, "utf8"); } catch (e) {}
  if (now !== json) { console.error("rabbit/voices.json is out of date: run node tests/voices.mjs --write"); process.exit(1); }
  console.log(`rabbit/voices.json ok: ${list.length} lines`);
}
