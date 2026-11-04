/* Ship asset contracts and waterline transforms. Run: node tests/ships.mjs */
import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = fileURLToPath(new URL("../", import.meta.url));
const manifest = JSON.parse(await readFile(root + "rabbit/art/ships/ships.json", "utf8"));
for (const [name, m] of Object.entries(manifest)) {
  const file = root + "rabbit/art/ships/" + m.src, data = await readFile(file);
  assert.equal(data.toString("ascii", 0, 4), "RIFF");
  assert.equal(data.toString("ascii", 8, 12), "WEBP");
  assert.ok((await stat(file)).size < 400 * 1024, name + " exceeds 400 KB");
  assert.equal(data.toString("ascii", 12, 16), "VP8X");
  assert.ok(data[20] & 0x10, name + " needs alpha");
  const width = data.readUIntLE(24, 3) + 1, height = data.readUIntLE(27, 3) + 1;
  for (const point of [m.stern, m.bow, m.funnel, m.tip].filter(Boolean)) {
    assert.ok(point[0] >= 0 && point[0] < width && point[1] >= 0 && point[1] < height, name + " landmark outside image");
  }
  for (const [x0, x1, y] of m.windows || []) assert.ok(x0 <= x1 && x0 >= 0 && x1 < width && y >= 0 && y < height);
}

const source = await readFile(root + "rabbit/scene.js", "utf8");
let now = 1000;
const ctx = vm.createContext({
  fetch: () => Promise.resolve({ ok: false }), Image: class {},
  Date: { now: () => now * 1000 }, Math,
  S: { base: { painted: true } }, location: { search: "" }, SPOT: { anchor: [1395, 780] },
  SHIP: { s: { phase: "ashore", t0: 500, end: 1200, style: "liner" } },
});
// Exercise the rendering functions directly without adding a testing API to the game.
vm.runInContext(source.slice(source.indexOf("  const BOATS ="), source.indexOf("  function cruiseShip(")) +
  ";this.api={BOATS,boatArt,boatPose,boatTransform,shipPos,paintedBoat,paintedTender};", ctx);
const { api } = ctx;
for (const [name, m] of Object.entries(manifest)) api.BOATS[name] = { ...m, im: {} };
assert.ok(api.boatArt("liner"));
ctx.location.search = "?art=drawn";
assert.ok(!api.boatArt("liner"));
ctx.location.search = ""; ctx.S.base.painted = false;
assert.ok(!api.boatArt("liner"));
ctx.S.base.painted = true;
const saved = api.BOATS.tender; delete api.BOATS.tender;
assert.equal(api.paintedTender({}, 0, 0, 0, 1), false);
api.BOATS.tender = saved;

ctx.SHIP.s.phase = "approach"; ctx.SHIP.s.t0 = 1090;
assert.equal(api.boatPose(0, 0, 0).right, 0);
assert.ok(api.shipPos(1000)[0] > api.shipPos(1080)[0]);
assert.ok(api.boatPose(0, 0, 0).speed > 0);
now = 1090; assert.equal(api.boatPose(0, 0, 0).speed, 0);
ctx.SHIP.s.phase = "boarding"; ctx.SHIP.s.end = 1200;
let last = 0;
for (let time = 1110; time <= 1200; time += 0.1) {
  now = time; const p = api.boatPose(1395, 828, time * 1000);
  assert.ok(p.right >= last && p.right <= 1); last = p.right;
  assert.ok(p.squash >= 0.25 && p.squash <= 1);
  assert.ok(Math.abs(p.x - 1395) <= 1.5 && Math.abs(p.y - 828) <= 1.2);
  assert.ok(Math.abs(p.roll) <= Math.PI / 300);
}
now = 1155; assert.ok(Math.abs(api.boatPose(0, 0, 0).right - 0.5) < 1e-10);
ctx.SHIP.s.phase = "gone"; now = 1230;
assert.equal(api.boatPose(0, 0, 0).right, 1);
assert.ok(api.shipPos(1230)[0] < api.shipPos(1300)[0]);
assert.equal(api.shipPos(1440), null);

// Track a canvas affine matrix and ensure both landmark endpoints remain centred,
// at the requested world length, through mirroring, rolling and the narrow turn.
function canvas() {
  let m = [1, 0, 0, 1, 0, 0], stack = [];
  const multiply = n => { const [a,b,c,d,e,f] = m, [A,B,C,D,E,F] = n; m = [a*A+c*B,b*A+d*B,a*C+c*D,b*C+d*D,a*E+c*F+e,b*E+d*F+f]; };
  return { globalAlpha: 1, save() { stack.push([...m]); }, restore() { m = stack.pop(); },
    translate(x,y) { multiply([1,0,0,1,x,y]); }, scale(x,y) { multiply([x,0,0,y,0,0]); },
    rotate(a) { multiply([Math.cos(a),Math.sin(a),-Math.sin(a),Math.cos(a),0,0]); },
    point([x,y]) { return [m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]]; } };
}
for (const name of ["liner", "expedition", "tender"]) for (const right of [0, 0.5, 1]) for (const squash of [0.25, 1]) {
  const g = canvas(), m = manifest[name], pose = { x: 1395, y: 828, a: 1, roll: 0.01, right, squash };
  api.boatTransform(g, m, pose, (scale, pixels) => {
    pixels(); const a = g.point(m.stern), b = g.point(m.bow);
    assert.ok(Math.abs(Math.hypot(b[0]-a[0],b[1]-a[1])-m.length*squash) < 1e-8);
    assert.ok(Math.abs((a[0]+b[0])/2-pose.x) < 1e-8 && Math.abs((a[1]+b[1])/2-pose.y) < 1e-8);
  });
}
ctx.SHIP.s.phase = "ashore"; now = 1000;
for (const [width, height] of [[1568, 735], [1248, 525]]) {
  ctx.S.W = width; ctx.S.H = height;
  const scale = Math.min(width / 1600, height / 900);
  ctx.toWorld = (x, y) => [(x - width / 2) / scale + 800, (y - height / 2) / scale + 450];
  const pos = api.shipPos(now), bottom = height / 2 + (pos[1] + 8 - 450) * scale;
  assert.ok(bottom <= height - 64 + 1e-8, "ship touches the radio strip");
  assert.equal(pos[0], 1395);
}
ctx.S.base.painted = false; assert.equal(api.shipPos(now)[1], 780);

/* The islanders' talk about the ships (talk.js RABBIT_SHIP_WHEN): a week in November 2026, German winter time (UTC+1).
   MS Dry Run on Wednesday the 4th at four, Queen Mempool on Saturday the 7th at two. */
const talk = { window: {} };
vm.runInNewContext(await readFile(root + "rabbit/talk.js", "utf8"), talk);
const W = talk.window.RABBIT_SHIP_WHEN, utc = (d, h, m = 0) => Date.UTC(2026, 10, d, h, m) / 1000;
const dry = { ship: "dryrun", t0: utc(4, 15) }, queen = { ship: "queen", t0: utc(7, 13) }, dry2 = { ship: "dryrun", t0: utc(11, 15) };
const was = (ship, end, note = "") => ({ ship, end, landed: !note.startsWith("no landing"), note });
const lastQueen = was("queen", Date.UTC(2026, 9, 31, 14, 30) / 1000);   // last week's Queen: Saturday 31 October, 15:30
const week = [
  ["Sunday noon: Wednesday's ship in three days", utc(1, 11), { next: dry, last: lastQueen }, "shipSoon dryrun"],
  ["Monday: in two days", utc(2, 8), { next: dry, last: lastQueen }, "shipSoon dryrun"],
  ["Tuesday 23:30: tomorrow", utc(3, 22, 30), { next: dry }, "shipTomorrow dryrun"],
  ["Wednesday 00:30 (still Tuesday in UTC): today", utc(3, 23, 30), { next: dry }, "shipToday dryrun"],
  ["Wednesday 15:40, in sight", utc(4, 14, 40), { now: { ...dry, phase: "approach" }, next: dry }, "shipToday dryrun"],
  ["Wednesday 16:05, waiting offshore", utc(4, 15, 5), { now: { ...dry, phase: "waiting" }, next: queen }, "shipToday dryrun"],
  ["Wednesday 16:30, ashore", utc(4, 15, 30), { now: { ...dry, phase: "ashore" }, next: queen }, "shipHere dryrun"],
  ["Wednesday 16:20, sailed on without landing", utc(4, 15, 20), { now: { ...dry, phase: "gone", why: "no landing" }, next: queen }, "shipCut dryrun"],
  ["Wednesday evening, gone on time", utc(4, 17), { next: queen, last: was("dryrun", utc(4, 16, 30)) }, "shipGone dryrun"],
  ["Wednesday evening, left early", utc(4, 17), { next: queen, last: was("dryrun", utc(4, 15, 50), "left early: the testnet stalled") }, "shipCut dryrun"],
  ["Wednesday evening, never landed", utc(4, 17), { next: queen, last: was("dryrun", utc(4, 15, 30), "no landing: the testnet was stalled") }, "shipCut dryrun"],
  ["Wednesday evening, the relay was down when she left", utc(4, 18), { next: queen, last: was("dryrun", utc(4, 16, 30), " (the relay was down at its end)") }, "shipGone dryrun"],
  ["Thursday: the Queen in two days", utc(5, 9), { next: queen, last: was("dryrun", utc(4, 16, 30)) }, "shipSoon queen"],
  ["Friday night: tomorrow", utc(6, 19), { next: queen }, "shipTomorrow queen"],
  ["Saturday morning: today", utc(7, 8), { next: queen }, "shipToday queen"],
  ["Saturday 14:30, ashore", utc(7, 13, 30), { now: { ...queen, phase: "ashore" }, next: dry2 }, "shipHere queen"],
  ["Saturday 23:59, gone", utc(7, 22, 59), { next: dry2, last: was("queen", utc(7, 14, 30)) }, "shipGone queen"],
  ["Sunday 00:30: the Queen was yesterday, Wednesday's ship in three days", utc(7, 23, 30), { next: dry2, last: was("queen", utc(7, 14, 30)) }, "shipSoon dryrun"],
  ["Saturday evening before the relay closed the visit: Wednesday is four days off", utc(7, 15), { next: dry2 }, ""],
  ["ships switched off", utc(6, 12), { now: null, next: null, last: null }, ""],
];
for (const [what, now, c, want] of week) {
  const f = W(c, now), on = Object.keys(f).filter(k => f[k]).sort().join(" ");
  const [w, ship] = want.split(" "), exp = want ? ["ship", ship, w, ...(/Soon|Tomorrow|Today/.test(w) ? ["shipNear"] : []), ...(/Gone|Cut/.test(w) ? ["shipAfter"] : [])].sort().join(" ") : "";
  assert.equal(on, exp, what);
}
/* Rico on air about the ships (game.js shipLine): the pools he picks from by how near the ship is, the lines for what
   happens in port, the numbers spoken as a band, and how often he talks about the ship */
const rico = { addEventListener() {}, removeEventListener() {}, fetch: () => Promise.reject(new Error("offline")), btoa };
rico.window = rico; vm.runInNewContext(await readFile(root + "rabbit/talk.js", "utf8") + "\n" + await readFile(root + "rabbit/rico.js", "utf8"), rico);
const R = rico.RICO, game = await readFile(root + "rabbit/game.js", "utf8"), cruise = await readFile(root + "infra/relay/cruise.py", "utf8");
for (const st of ["Soon", "Tomorrow", "Today", "Close", "Approach", "Land", "Here", "Gone"]) for (const s of ["Q", "D"]) assert.ok(R.SETS["ship" + st + s]?.length, "ship" + st + s);
for (const n of ["shipWait", "shipBoard", "shipCut", "shipCutLand", "shipCutStall", "shipCutRefused", "shipWhy", "shipBook", "shipCancel", "shipBill", "shipCalm", "shipBusy", "shipTotal", "shipBlock"]) assert.ok(R.SETS[n]?.length, n);
for (const [n, keys] of Object.entries(R.SETS)) if (/^ship/.test(n)) for (const k of keys) assert.ok(R.L[k], `SETS.${n}: ${k} is not a line`);
for (const n of new Set(game.match(/"ship[A-Z]\w*"/g).map(x => x.slice(1, -1)))) if (!/^ship(Soon|Tomorrow|Today|Close|Approach|Wait|Land|Here|Board|Gone)$/.test(n)) assert.ok(R.SETS[n], `game.js picks from SETS.${n}, which rico.js does not have`);
for (const k of ["se_full", "se_ref1", "se_ref3", "ss_strain", "sl_recap", "sw5"]) assert.ok(R.L[k], k);
const stops = new Set([...cruise.matchAll(/"stops": \{([^}]*)\}/g)].flatMap(m => [...m[1].matchAll(/"(\w+)":/g)].map(x => x[1])));
for (const p of stops) assert.ok(R.L["sa_" + p], `no line for the passengers at ${p} (sa_${p})`);
for (const k of [...R.SETS.shipTotal, ...R.SETS.shipBlock, "sl_recap"]) assert.ok(R.NUMERIC[k] === "count" && R.L[k].includes("{n}"), `${k}: a number spoken as a band`);
for (const k of R.SETS.shipBlock) assert.ok(R.L[k].includes("{where}"), k);
/* every band reads as English where it stands ("a handful of of" would not) */
for (const [k, b] of Object.entries(R.NUMERIC)) for (const n of R.BANDS[b]) { const t = R.fill(R.L[k], { n, ...R.BLOCK }); assert.ok(!/\bof of\b|\bdozen of\b|\bmore of\b/.test(t), `${k}: ${t}`); }
/* the share of Rico's lines about the ship: it grows as the ship comes nearer, is highest in port, and fades after */
const odds = game.match(/const SHIP_P = [^\n]*\n  const shipOdds = [^\n]*\n[^\n]*\n/)[0], O = vm.runInNewContext(odds + "; shipOdds");
const before = [72, 60, 48, 36, 24, 12, 8, 6, 4, 3, 2, 1, 0.5].map(h => O({ stage: "soon", h }));
for (let i = 1; i < before.length; i++) assert.ok(before[i] >= before[i - 1], "nearer, more often");
assert.ok(before[0] >= 0.03 && before[0] <= 0.05, "two or three days before: about one line in twenty-five");
assert.ok(O({ stage: "today", h: 12 }) < 0.2 && O({ stage: "close", h: 1 }) >= 0.3, "the last day ramps up");
for (const s of ["approach", "wait", "land", "here", "board"]) assert.ok(O({ stage: s }) >= 0.4, s);
assert.ok(O({ stage: "gone", after: 0 }) > O({ stage: "gone", after: 2 }) && O({ stage: "gone", after: 8 }) <= 0.06, "fades after");
assert.equal(O(null), 0);
console.log("Ship assets, fallback selection, heading, turn continuity, waterline transforms and overview clearance passed.");
console.log("Ship talk: a week of windows in German time, Rico's ship pools, bands and odds, passed.");
