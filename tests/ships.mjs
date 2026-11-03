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
console.log("Ship assets, fallback selection, heading, turn continuity, waterline transforms and overview clearance passed.");
