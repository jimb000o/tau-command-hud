// The HUD news line's hand-written content (assets/ticker.json): every headline leaves the line by itself one day
// ("since", then "days" later) or is marked a standing pointer ("keep": true), and every text and hover has its
// Chinese and Japanese (assets/i18n/zh|ja/hud.js), or ticker.js leaves it out on those pages.
// Run: node tests/ticker.mjs
import { readFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const cfg = JSON.parse(await readFile(join(ROOT, "assets", "ticker.json"), "utf8"));
const strings = {};
for (const l of ["zh", "ja"]) {
  const src = await readFile(join(ROOT, "assets", "i18n", l, "hud.js"), "utf8");
  const got = new Map();
  new Function("TauI18n", src)({ add: o => { for (const [k, v] of Object.entries((o && o.strings) || {})) got.set(k, v); } });
  strings[l] = got;
}
const has = (l, s) => strings[l].has(s) || strings[l].has(s.replace(/\.$/, "")) || strings[l].has(s + ".");
const bad = [];
if (!(+cfg.days > 0)) bad.push(`"days" must be a number of days (it is ${JSON.stringify(cfg.days)})`);
const DAY = /^\d{4}-\d{2}-\d{2}$/;
for (const h of cfg.headlines || []) {
  const name = `headline “${h.text}”`;
  if (!h.keep && !h.since) bad.push(`${name}: no "since" (the day it goes on the line, YYYY-MM-DD) and no "keep": true, so it would never leave the line`);
  if (h.since && (!DAY.test(h.since) || isNaN(Date.parse(h.since)))) bad.push(`${name}: "since" ${JSON.stringify(h.since)} is not a day like 2026-11-06`);
  if (h.until && isNaN(Date.parse(h.until))) bad.push(`${name}: "until" ${JSON.stringify(h.until)} is not a time`);
  const done = h.until && Date.parse(h.until) < Date.now();
  for (const l of ["zh", "ja"]) for (const [what, s] of [["text", h.text], ["tip", h.tip]]) {
    if (s && !done && !has(l, s)) bad.push(`${name}: ${what} has no ${l} in assets/i18n/${l}/hud.js, so ${l} pages leave it out`);
  }
}
const n = (cfg.headlines || []).length, kept = (cfg.headlines || []).filter(h => h.keep).length;
if (bad.length) {
  console.log(`❌ assets/ticker.json:\n- ${bad.join("\n- ")}`);
  process.exit(1);
}
console.log(`✅ assets/ticker.json: ${n} headlines, ${n - kept} leave after ${cfg.days} days, ${kept} standing; all have zh and ja`);
