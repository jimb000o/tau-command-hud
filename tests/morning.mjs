// Coco Sunrise, Radio Coco's morning show (rabbit/rico.js sunrise): opens at eight German time, names nine, closes at ten;
// the night report, the day, the Tau word and who's up read from the relay as msRead does; the songs it names exist.
//   node tests/morning.mjs
import { readFileSync } from "node:fs";
const root = new URL("..", import.meta.url);
globalThis.window = {}; globalThis.addEventListener = globalThis.removeEventListener = () => {}; globalThis.fetch = () => Promise.reject(new Error("offline"));
globalThis.localStorage = { m: {}, getItem(k) { return this.m[k] ?? null; }, setItem(k, v) { this.m[k] = String(v); } };
new Function(readFileSync(new URL("rabbit/rico.js", root), "utf8"))();
const R = window.RICO, bad = [], ok = (c, m) => { if (!c) bad.push(m); };
const music = readFileSync(new URL("rabbit/music.js", root), "utf8"), pl = JSON.parse(music.match(/const PLAYLIST = (\[[\s\S]*?\]);/)[1]);
for (const id of pl) { ok(R.L["nx_" + id], "no nx_ line for song " + id); ok(R.SETS.songs.includes("sn_" + id), "no sn_ line for song " + id); }
ok(pl.length >= 16, "the playlist has " + pl.length + " songs");
// Wednesday 18 Nov 2026, German time (UTC+1 in November)
const at = (h, m) => { const t = Date.UTC(2026, 10, 18, h - 1, m); return { h, m, s: 0, dow: 3, day: "2026-11-18", t }; };
const seen = [];
const b0 = R.brk("coco", "mango", { berlin: at(8, 2), hr: 8 }); seen.push(b0.k);
ok(R.SETS.wakeMs.includes(b0.k), "8:02 opens with " + b0.k);
for (let i = 0; i < 16; i++) { const b = R.brk("mango", "sunrise", { berlin: at(8, 10 + i), hr: 8 }); seen.push(b.k); ok(b.parts.length, "empty break"); }
ok(seen.some(k => /^morning:\d+$/.test(k)), "no morning caller in 16 breaks: " + seen.join(","));
ok(seen.some(k => /^tw\d+$/.test(k)) && seen.some(k => /^td\d$/.test(k)), "no Tau word or today line: " + seen.join(","));
const b9 = R.brk("mango", "coco", { berlin: at(9, 1), hr: 9 }); ok(R.SETS.msNine.includes(b9.k), "nine o'clock: " + b9.k);
const b10 = R.brk("mango", "coco", { berlin: at(10, 1), hr: 10 }); ok(R.SETS.msClose.includes(b10.k), "ten o'clock: " + b10.k);
const b11 = R.brk("mango", "coco", { berlin: at(10, 5), hr: 10 }); ok(!/^ms|^morning:/.test(b11.k), "after the close: " + b11.k);
// msRead: the hours since midnight German time, a restart after midnight, who's up, a ship docking today
const b = at(8, 30), mid = Math.floor(b.t / 1000) - 8.5 * 3600, H = 3600;
const h = { fields: ["blocks", "txs"], hours: [[mid - H, 2, 50, 9], [mid, 2, 300, 40], [mid + 3 * H, 3, 200, 30]], chains: [{ n: 2, start: mid - 86400 }, { n: 3, start: mid + 3 * H }] };
const r = R.msRead(h, { n: { rabbit: 30, cruise: 9, nomemo: 1 } }, { next: { ship: "queen", t0: mid + 14 * H } }, b);
ok(r.night.blocks === 500 && r.night.txs === 70 && r.night.restart, "night: " + JSON.stringify(r.night));
ok(r.roll === "rcNomemo", "roll: " + r.roll);
ok(r.ship === "queen", "ship today: " + r.ship);
ok(R.msRead(null, { n: { rabbit: 3, bot: 2, "tauhud:relay": 1 } }, { next: { ship: "queen", t0: mid + 38 * H } }, b).roll === "rcNone", "own traffic only is nobody");
ok(!R.msRead(null, null, { next: { ship: "queen", t0: mid + 38 * H } }, b).ship, "a ship tomorrow is not today");
ok(!R.msRead(null, null, { next: { ship: "pirates", t0: mid + 14 * H } }, b).ship, "the pirates are never announced");
if (bad.length) { console.error("❌ " + bad.join("\n❌ ")); process.exit(1); }
console.log("✅ Coco Sunrise: opens at eight, callers and segments in turn, nine and ten o'clock, the night report read right; " + pl.length + " songs, each with its lines");
