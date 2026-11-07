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
  for (const point of [...(m.deck || []), m.captain].filter(Boolean)) {
    assert.ok(point.length === 2 && point[0] >= 0 && point[0] < width && point[1] >= 0 && point[1] < height, name + " deck point outside image");
  }
  if (m.deck) {   // a crew sheet for the ship, as the game needs it (scene.js crew): a figure for each deck point, the captain
    const crew = JSON.parse(await readFile(root + "rabbit/art/ships/crew-" + (m.crew || name) + ".json", "utf8"));
    const sheet = await readFile(root + "rabbit/art/ships/" + crew.src);
    const sw = sheet.readUIntLE(24, 3) + 1, sh = sheet.readUIntLE(27, 3) + 1;
    assert.ok(crew.unit > 0 && crew.cols > 0 && crew.cell[0] > 0 && crew.cell[1] > 0, name + " crew sheet geometry");
    assert.ok(crew.figures.length >= 1 && crew.figures.length >= m.deck.length, name + " needs a figure for each deck point");
    assert.ok(!m.captain || (crew.guides && crew.guides[m.crew || name]), name + " has a captain point but no captain");
    for (const f of [...crew.figures, ...Object.values(crew.guides || {})]) {
      for (const c of [f.a, f.b]) assert.ok(Number.isInteger(c) && (Math.floor(c / crew.cols) + 1) * crew.cell[1] <= sh && (c % crew.cols + 1) * crew.cell[0] <= sw, f.id + " cell outside the sheet");
      assert.ok(f.foot[0] >= 0 && f.foot[0] <= crew.cell[0] && f.foot[1] >= 0 && f.foot[1] <= crew.cell[1], f.id + " foot outside its cell");
      assert.ok(/^(back|front|side)$/.test(f.view) && (f.face === 1 || f.face === -1), f.id + " view");
    }
    // a pirate is a grown-up: 16 world units from the sheet, so on the ship about 70 of her 1000 px
    const tall = crew.figures.map(f => f.foot[1] / crew.unit);
    assert.ok(Math.min(...tall) > 13 && Math.max(...tall) < 19, name + " crew height " + tall.join(","));
  }
}

const source = await readFile(root + "rabbit/scene.js", "utf8");
let now = 1000;
const ctx = vm.createContext({
  fetch: () => Promise.resolve({ ok: false }), Image: class {},
  Date: { now: () => now * 1000 }, Math,
  S: { base: { painted: true } }, location: { search: "" }, SPOT: { anchor: [1395, 780] },
  SHIP: { s: { phase: "ashore", t0: 500, end: 1200, style: "liner" } },
  gesture: () => false, crowdOk: () => false,
});
// Exercise the rendering functions directly without adding a testing API to the game.
vm.runInContext(source.slice(source.indexOf("  const BOATS ="), source.indexOf("  function cruiseShip(")) +
  ";this.api={BOATS,CREW,boatArt,boatPose,boatTransform,shipPos,paintedBoat,paintedTender};", ctx);
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

/* The crew on the Black Sequence (scene.js crew): with the sheet loaded, paintedBoat draws the ship and then one figure
   for each deck point and the captain, each standing inside the ship's painting; without the sheet, the ship alone. */
{
  const m = manifest.pirate, crewMan = JSON.parse(await readFile(root + "rabbit/art/ships/crew-pirate.json", "utf8"));
  const draws = [], g = Object.assign(canvas(), {
    drawImage(im, ...a) { draws.push([im, a.length === 8 ? [a[4] + a[6] / 2, a[5] + a[7]] : null]); },
    beginPath() {}, ellipse() {}, arc() {}, fill() {}, stroke() {}, fillRect() {}, set fillStyle(v) {}, set strokeStyle(v) {}, set lineWidth(v) {},
  });
  const im = {}; api.BOATS.pirate = { ...m, im };
  ctx.S.base.painted = true; ctx.SHIP.s.style = "pirate";
  api.paintedBoat(g, 1395, 828, 1000, "pirate", 1);
  assert.equal(draws.filter(d => d[0] === im).length, 1, "the ship alone without the crew sheet");
  const sheet = {}; api.CREW.pirate = { m: crewMan, im: sheet };
  draws.length = 0; api.paintedBoat(g, 1395, 828, 1000, "pirate", 1);
  const crew = draws.filter(d => d[0] === sheet);
  assert.equal(crew.length, m.deck.length + 1, "a figure for each deck point and the captain");
  for (const [, [fx, fy]] of crew) assert.ok(fx > m.stern[0] - 20 && fx < m.bow[0] + 40 && fy > 300 && fy < m.stern[1], "a pirate stands on the ship (the forecastle may reach past the bow waterline): " + [fx, fy]);
  delete api.CREW.pirate; ctx.SHIP.s.style = "liner";
}

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
/* The pirates (Black Sequence, Tuesday 10 November at six): unannounced, so nothing about them before she is in sight;
   the week's other ship is still talked about around her; only refused tricks become facts, never one held back */
const pir = { ship: "pirates", style: "pirate", t0: utc(10, 17) }, dry3 = { ship: "dryrun", t0: utc(11, 15) }, queen2 = { ship: "queen", t0: utc(14, 13) };
const clean = { overspend: { tried: 2, stopped: 2, right: 2, through: 0 }, replay: { tried: 2, stopped: 2, right: 2, through: 0 } };
const pwas = (tricks, note = "") => ({ id: "2026-11-10-pirates", ship: "pirates", t0: pir.t0, end: pir.t0 + 5400, landed: true, note, sent: { pay: 30 }, refused: {}, tricks });
const on = f => Object.keys(f).filter(k => f[k]).sort().join(" ");
const pweek = [
  ["Monday: the relay names Wednesday, never the pirates", utc(9, 10), { next: dry3, last: was("queen", utc(7, 14, 30)) }, "dryrun ship shipNear shipSoon"],
  ["Monday, an older relay naming the pirates next: nobody says a word", utc(9, 10), { next: pir }, ""],
  ["Tuesday 17:35, in sight", utc(10, 16, 35), { now: { ...pir, phase: "approach" }, next: dry3 }, "dryrun pirateSight pirates ship shipNear shipTomorrow"],
  ["Tuesday 18:40, at anchor, a replay refused", utc(10, 17, 40), { now: { ...pir, phase: "ashore", tricks: { tried: 1, stopped: 1, by: { replay: 1 } } }, next: dry3 }, "dryrun pirateHere pirates ship shipNear shipTomorrow tReplay"],
  ["Tuesday 21:00, gone, every trick refused", utc(10, 20), { next: dry3, last: pwas(clean) }, "dryrun pirateAfter pirateClean pirateGone pirates ship shipNear shipTomorrow tOverspend tReplay"],
  ["Tuesday 21:00, gone, an overspend held back", utc(10, 20), { next: dry3, last: pwas({ ...clean, overspend: { held: true } }) }, "dryrun pirateAfter pirateGone pirates ship shipNear shipTomorrow tReplay"],
  ["Tuesday 21:00, left early", utc(10, 20), { next: dry3, last: pwas(clean, "left early: the testnet stalled") }, "dryrun pirateAfter pirateCut pirateGone pirates ship shipNear shipTomorrow"],
  ["Wednesday morning: the pirates were last night, the Dry Run today", utc(11, 9), { next: dry3, last: pwas(clean) }, "dryrun pirateAfter pirateClean pirateNext pirates ship shipNear shipToday tOverspend tReplay"],
  ["Thursday: the pirates are history", utc(12, 9), { next: queen2, last: pwas(clean) }, "queen ship shipNear shipSoon"],
];
for (const [what, now, c, want] of pweek) assert.equal(on(W(c, now)), want, what);
/* what a visit's summary says she met: stops skipped, sends unanswered in time, not one refusal, a change for next time */
const qsum = { ship: "queen", end: utc(7, 14, 30), landed: true, note: "", sent: { pay: 409 }, refused: {}, skipped: 162, unanswered: 10,
  changed: [{ what: "stops planned a minute", from: "as timetabled", to: 7.5, because: "our node answered a send in 6.8 s" }] };
assert.equal(on(W({ next: dry2, last: qsum }, utc(7, 20))), "queen ship shipAfter shipClean shipGone shipQuiet shipSkipped shipTuned", "the Queen's evening, from her logbook");
assert.equal(on(W({ next: dry2, last: { ...qsum, refused: { pay: 1 }, skipped: 0, unanswered: 0, changed: [{ what: "a pirate trick", held: true }] } }, utc(7, 20))), "queen ship shipAfter shipGone", "a held change is no change to talk about");
assert.equal(on(talk.window.RABBIT_SHIP_WHEN.pirate("approach")), "pirateSight pirates");
assert.equal(on(talk.window.RABBIT_SHIP_WHEN.pirate("next")), "pirateAfter pirateNext pirates");
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
/* the pirates on air: a line for every trick the relay can refuse, both kinds of evening, the numbers as a band */
for (const n of ["pirSight", "pirSightN", "pirHere", "pirHereN", "pirBoard", "pirGone", "pirClean", "pirCut", "pirNext", "shipSkip"]) assert.ok(R.SETS[n]?.length, n);
const tricks = [...cruise.matchAll(/^    "(\w+)": \(\("[A-Z_]+"/gm)].map(m => m[1]);
assert.ok(tricks.length === 8, "the relay's eight tricks: " + tricks);
for (const t of tricks) for (const i of [1, 2]) assert.ok(R.L[`pp_t_${t}${i}`], `no line for the pirates' ${t} trick (pp_t_${t}${i})`);
for (const t of tricks) assert.ok(talk.window.RABBIT_SHIP_WHEN.TRICKF[t], "a fact for the trick " + t);
for (const k of ["pp_recap", "sk_skip1", "sk_skip2", "sk_quiet"]) assert.ok(R.NUMERIC[k] === "count" && R.L[k].includes("{n}"), k + ": a number spoken as a band");
/* before she is in sight, no line of hers may be said: no pirate line waits for a ship fact of the week ahead */
for (const [w] of Object.values(talk.window.RABBIT_TALK).flatMap(t => t.back || [])) if (/pirate/.test(w)) assert.ok(!/ship(Soon|Tomorrow|Today|Near)/.test(w), w);
for (const k of Object.keys(R.L).filter(k => /^pp_/.test(k))) assert.ok(!/tomorrow at|tuesday at|on tuesday|at six/i.test(R.L[k]), k + ": never says when she comes");
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
/* The passengers ashore (scene.js crowdItems): the painted groups stand on the layout's ground, one figure for each
   passenger counted at a place as far as the ground holds them, face their guide, come and go one by one (whole, never
   half see-through), gesture now and then each on their own, and leave the pennants exactly as before while there is
   no art (or ?art=drawn, or the drawn island). */
const LAYOUT = JSON.parse(await readFile(root + "infra/rabbit-art/plates/island-22.json", "utf8"));
const crowdSrc = source.slice(source.indexOf("  const placePt ="), source.indexOf("  function shipItems(")) +
  source.slice(source.indexOf("  const inPoly ="), source.indexOf("\n", source.indexOf("  const inPoly =")) + 1);
const pennants = [];
const cx = vm.createContext({
  fetch: () => Promise.resolve({ ok: false }), Image: class {}, Math, JSON, Number, Object, Array, Set,
  S: { base: { painted: true, e: 0 }, still: false }, location: { search: "" }, WW: 1600, WH: 900,
  SPOT: { stand: LAYOUT.stand, over: LAYOUT.over, crowd: 1 }, PLACES: LAYOUT.places, SHIPS: { liner: { funnel: "#e2674f" }, expedition: { funnel: "#2c8c88" } },
  pennant: (g, x, y, t, col) => pennants.push([x, y, col]),
});
vm.runInContext(crowdSrc + ";this.cr={CROWD,crowdOk,crowdArt,standSlots,crowdCast,crowdItems,gesture,inPoly};", cx);
const cr = cx.cr;
const VIEWS = ["back", "back", "back", "back", "back", "back", "back", "back", "front", "front", "front", "front", "side", "side", "side", "side"];
const figs = VIEWS.map((view, i) => ({ id: "p" + String(i + 1).padStart(2, "0"), view, face: [-1, 1][Math.floor(i / 2) % 2], a: 2 * i, b: 2 * i + 1, foot: [32, 90.6], contacts: [[28, 90, 3], [37, 89, 2.5]] }));
const man = { src: "tourists.webp", cols: 12, cell: [79, 117], unit: 5, figures: figs, guides: { expedition: { id: "guide-dryrun", view: "front", face: 1, a: 32, b: 33, foot: [39, 110], contacts: [[39, 110, 4]] }, liner: { id: "guide-queen", view: "front", face: -1, a: 34, b: 35, foot: [39, 110] } } };
assert.ok(cr.crowdOk(man));
for (const bad of [null, { ...man, src: "../x.webp" }, { ...man, unit: 0 }, { ...man, figures: [] }, { ...man, figures: [{ ...figs[0], foot: [1] }] },
  { ...man, figures: [{ ...figs[0], view: "up" }] }, { ...man, guides: { liner: { a: 1 } } }, { ...man, figures: [{ ...figs[0], contacts: [[1, 2]] }] },
  { ...man, figures: [{ ...figs[0], contacts: "feet" }] }]) assert.ok(!cr.crowdOk(bad), JSON.stringify(bad)?.slice(0, 60));
assert.ok(!cr.crowdArt(), "no art loaded: nothing changes");
cr.CROWD.m = man; cr.CROWD.im = {};
assert.ok(cr.crowdArt());
cx.location.search = "?art=drawn"; assert.ok(!cr.crowdArt()); cx.location.search = "";
cx.S.base.painted = false; assert.ok(!cr.crowdArt()); cx.S.base.painted = true;
/* every ship stop has ground, inside its outline, nearest the guide first, nobody on top of anybody */
const stops2 = [...new Set([...cruise.matchAll(/"stops": \{([^}]*)\}/g)].flatMap(m => [...m[1].matchAll(/"(\w+)":/g)].map(x => x[1])))];
for (const id of [...stops2, "pier"]) {
  const s = cr.standSlots(id), [[gx, gy], ...P] = LAYOUT.stand[id];
  assert.ok(s && s.length >= 6 && s.length <= 40, `${id}: ${s && s.length} places to stand`);
  assert.equal(cr.standSlots(id), s, "laid out once");
  const d = ([x, y]) => Math.hypot(x - gx, (y - gy) * 1.7);
  for (const p of s) assert.ok(cr.inPoly(P, p[0], p[1]) && d(p) > 5, id);
  assert.ok(d(s[0]) < d(s[s.length - 1]), id + ": nearest the guide first");
  for (let i = 0; i < s.length; i++) for (let j = 0; j < i; j++) assert.ok(Math.hypot(s[i][0] - s[j][0], (s[i][1] - s[j][1]) * 1.7) > 3.4, `${id}: two people on one spot`);
}
assert.equal(cr.standSlots("hall"), null);
/* a group: no one twice while there are figures left, most of them turned to the guide */
const cast = cr.crowdCast("south", "queen|1", cr.standSlots("south"));
assert.equal(new Set(cast.slice(0, 16).map(f => f.id)).size, Math.min(16, cast.length));
assert.equal(cr.crowdCast("south", "queen|1", cr.standSlots("south")), cast, "the same for the whole visit");
let turned = 0;
cr.standSlots("south").forEach(([x], i) => { const [gx] = LAYOUT.stand.south[0]; if (Math.abs(gx - x) < 2 || cast[i].face === Math.sign(gx - x)) turned++; });
assert.ok(turned >= cast.length * 0.6, `only ${turned} of ${cast.length} turned to their guide`);
/* the counts: one figure for each passenger as far as the ground holds them; a guide where the pennant was, none on
   the pier while they land; arrivals come one by one; at boarding they go one by one; places without ground keep their
   pennant; every figure with its shadows (one under it, one under each foot or wheel) */
const G = { globalAlpha: 1, save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, clip() { G.clips++; }, ellipse(...a) { G.shadows.push(a); }, fill() {},
  drawImage(...a) { (a.length === 5 ? G.overs : G.drawn).push(a); }, drawn: [], shadows: [], overs: [], clips: 0 };
const run = (v, t) => { const items = []; cr.crowdItems(items, G, t, v, v.style); return items; };
const dv = { ship: "dryrun", t0: 1, style: "expedition", phase: "landing", at: { book: 8, pier: 3, hall: 2, dive: 99 } };
let items = run(dv, 1000);
const slotsN = id => cr.standSlots(id).length, ovN = LAYOUT.over.pier.length, figN = 8 + 3 + slotsN("dive");
assert.ok(ovN >= 3 && !LAYOUT.over.book && !LAYOUT.over.dive, "the pier has its bollards in front; nothing laid out in front of the lighthouse or the dive deck here");
assert.equal(items.length, figN + 1 + ovN + 1 + 1, "8 at the lighthouse and their guide, 3 on the pier behind its bollards, the dive deck full and its guide, the pennant at the Council Tree");
const hall = []; cr.crowdItems(hall, G, 1001, { ...dv, at: { hall: 2 } }, "expedition"); hall.forEach(([, d]) => d());
assert.equal(pennants.length, 1, "no ground at the Council Tree: the pennant as before");
G.drawn = []; G.shadows = []; G.overs = []; G.clips = 0; items.forEach(([, d]) => d());
assert.ok(G.drawn.length === figN + 2 && G.drawn.every(a => a.length === 9 && a.slice(1).every(Number.isFinite) && G.globalAlpha === 1), "figures drawn from the sheet, whole");
assert.equal(G.shadows.length, figN * 3 + 2 * 2, "a shadow under each figure and under each of its feet (two guides, one foot each)");
/* what stands in front (layout over): the painting again, clipped to each shape, at the depth the shape stands at, so the
   figures behind it are under it and those in front of it over it; a malformed entry is left out */
assert.ok(G.clips === ovN && G.overs.length === ovN && G.overs.every(a => a[1] === 0 && a[3] === 1600 && a[4] === 900), "the bollards painted again over the pier group, clipped");
assert.deepEqual(items.filter(([y]) => LAYOUT.over.pier.some(o => o.d === y)).map(([y]) => y).sort(), LAYOUT.over.pier.map(o => o.d).sort(), "each at its own depth");
cx.SPOT.over.book = [{ d: 1 }, { d: 2, p: [[1, 2]] }, { d: 3, p: [[1, 2], [3, 4], [5]] }, "post", null];
cr.CROWD.visit = null; assert.equal(run(dv, 1000).length, items.length, "nothing drawn for shapes that are not shapes");
delete cx.SPOT.over.book;
const [, sx, sy, cw0, ch0, dx, dy, dw, dh] = G.drawn[0];
assert.ok(Math.abs(dw - cw0 / 5) < 1e-9 && Math.abs(dh - ch0 / 5) < 1e-9 && sx % 79 === 0 && sy % 117 === 0, "a cell at its own scale: 5 sheet pixels to the world unit");
cr.CROWD.visit = null; items = run({ ...dv, phase: "ashore", at: { pier: 3 } }, 2000);
assert.equal(items.length, 4 + ovN, "ashore, the pier has its guide too");
items = run({ ...dv, phase: "ashore", at: { pier: 3, school: 4 } }, 2100);
assert.equal(items.length, 4 + ovN, "a new group does not show half of anybody");
for (let t = 2200; t <= 3000; t += 100) items = run({ ...dv, phase: "ashore", at: { pier: 3, school: 4 } }, t);
assert.equal(items.length, 4 + ovN + 1 + 1, "after a moment its first passenger and its guide are there");
for (let t = 3100; t <= 2100 + 4 * 900 + 100; t += 100) items = run({ ...dv, phase: "ashore", at: { pier: 3, school: 4 } }, t);
assert.equal(items.length, 4 + ovN + 5, "and then all four, one by one");
items = run({ ...dv, phase: "boarding", at: { pier: 3, school: 4 } }, 5900);
assert.ok(items.length > 0, "boarding: they go one by one, not all at once");
for (let t = 6000; t < 20000; t += 100) items = run({ ...dv, phase: "boarding", at: {} }, t);
assert.equal(items.length, 0, "and then the island is theirs again");
assert.equal(Object.keys(cr.CROWD.at).length, 0);
cx.S.still = true; assert.equal(cr.gesture("book", 1, 12345), false); cx.S.still = false;
/* gestures: each figure on its own, held 1.2 to 3 s, at least 1.6 s apart, in varied pauses, never all at once */
let all = 0, together = 0;
const runs = {};
for (let i = 0; i < 12; i++) {
  let on = null, last = -1e9;
  runs[i] = [];
  for (let t = 0; t < 600000; t += 50) {
    const g = cr.gesture("book", i, t);
    if (g && on === null) { on = t; assert.ok(t - last >= 1550, `figure ${i} rests ${t - last} ms`); }
    if (!g && on !== null) { assert.ok(t - on >= 1150 && t - on <= 3050, `figure ${i} holds ${t - on} ms`); runs[i].push(on); last = t; on = null; }
  }
  all += runs[i].length;
  const gaps = runs[i].slice(1).map((t, k) => t - runs[i][k]);
  assert.ok(Math.max(...gaps) - Math.min(...gaps) > 6000, `figure ${i}: its pauses vary`);
}
for (let t = 0; t < 600000; t += 250) { let n = 0; for (let i = 0; i < 12; i++) n += cr.gesture("book", i, t) ? 1 : 0; if (n >= 6) together++; }
assert.ok(all / 12 > 15 && all / 12 < 70, `a gesture now and then: ${all / 12} in ten minutes`);
assert.ok(together < 10, `half the group at once ${together} times in ten minutes`);
console.log("Passengers ashore: ground at every stop, groups, counts, one by one, shadows, what stands in front, gestures, guides and the pennant fallback passed.");

console.log("Ship talk: a week of windows in German time, Rico's ship pools, bands and odds, passed.");
