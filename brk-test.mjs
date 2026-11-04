import { createRequire } from "node:module"; const { chromium } = createRequire(import.meta.url)("playwright");
const b = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
async function run(q) {
  const p = await b.newPage(); const errs = [];
  p.on("pageerror", e => errs.push(String(e)));
  await p.goto("http://localhost:8765/rabbit/" + q, { waitUntil: "load" });
  await p.mouse.click(400, 300); await p.waitForTimeout(1500); await p.click(".cv-cand"); for (let i = 0; i < 6; i++) { await p.waitForTimeout(1500); await p.keyboard.press("Escape"); } await p.evaluate(() => { window.__place = []; setInterval(() => window.__place.push(COVE_SOUND.song.id), 5000); });
  await p.evaluate(() => { const S = window.COVE_SOUND, f = S && S._b; window.__log = []; const orig = Object.getOwnPropertyDescriptor(S, "onbreak"); });
  // wrap the handler game.js registered: re-register through the setter with a logger around RICO.brk
  await p.evaluate(() => { const o = RICO.brk; RICO.brk = (...a) => { const r = o(...a); window.__log.push({ at: Math.round(performance.now() / 1000), from: a[0], to: a[1], k: r && r.k, n: r && r.parts.length }); return r; }; });
  return { p, errs, q };
}
const runs = await Promise.all(["?r=2", "?r=2&nightline=1"].map(run));
for (let i = 0; i < 17; i++) {
  await runs[0].p.waitForTimeout(10000);
  const st = await Promise.all(runs.map(r => r.p.evaluate(() => ({ on: COVE_SOUND.on, song: COVE_SOUND.song.id, gap: COVE_SOUND.gap, strip: (document.getElementById("cvNews") || {}).textContent }))));
  console.log(i * 10 + 10, JSON.stringify(st.map(s => [s.on, s.song, s.gap && s.gap.to, (s.strip || "").slice(0, 70)])));
}
for (const r of runs) console.log(r.q, JSON.stringify(await r.p.evaluate(() => window.__log)), r.errs);
await b.close();
