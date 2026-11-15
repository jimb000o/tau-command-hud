/* The rule kinds on tauhud.com/rules/numbers/ (assets/rulekinds.js) give the answers in tests/rulekinds-cases.json, the
   same the relay's infra/relay/ruledays.py must give (test_ruledays.py). Run: node tests/rulekinds.mjs */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const require = createRequire(import.meta.url);
const { kinds } = require("../assets/rulekinds.js");
const cases = JSON.parse(readFileSync(new URL("./rulekinds-cases.json", import.meta.url), "utf8"));
let bad = 0;
for (const c of cases) {
  const k = kinds(c.text), ok = JSON.stringify(k.kinds) === JSON.stringify(c.kinds) && k.size === c.size;
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${c.name}: ${k.kinds.join("+")} · ${k.size}${ok ? "" : ` (want ${c.kinds.join("+")} · ${c.size})`}`);
}
console.log(bad ? `${bad} of ${cases.length} cases differ` : `all ${cases.length} cases match`);
process.exit(bad ? 1 : 0);
