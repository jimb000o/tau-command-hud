/* Agorzilla's evening pictures: after each evening (18:00 UTC) this opens agorzilla.com?shot=<evening> in a headless
   Chromium, paints the scene just before the evening closed and just after it, and keeps both as JPEGs in /shots:
   evening-<n>-before.jpg, evening-<n>-after.jpg and evenings.json (the list with what the part was before and after, for
   the evening card and the family album). The evening post
   (alerts/agorzilla.py) puts the two side by side; agorzilla.com serves them under /evenings/.
   It reads chain/latest.json every SHOTS_SECONDS (default 2 min) and pictures every evening listed there that it has not
   pictured yet, so a fresh start also fills in the last seven. Nothing is posted from here.

   node shots.mjs            the loop
   node shots.mjs --once 3   picture evening 3 now (also when it has a picture already) and stop */
import { chromium } from "playwright";
import { mkdir, readFile, rename, writeFile, access } from "node:fs/promises";
import { join } from "node:path";

const SITE = (process.env.AGORZILLA_SITE || "https://agorzilla.com").replace(/\/$/, "");
const OUT = process.env.SHOTS_DIR || "/shots";
const EVERY = Number(process.env.SHOTS_SECONDS || 120) * 1000;
const log = (...a) => console.log(new Date().toISOString(), ...a);
const exists = f => access(f).then(() => true, () => false);

async function latest() {
  const r = await fetch(`${SITE}/chain/latest.json`, { headers: { "Cache-Control": "no-cache", "User-Agent": "tauhud-agorzilla-shots/1 (+https://tauhud.com)" } });
  if (!r.ok) throw new Error(`latest.json: HTTP ${r.status}`);
  return r.json();
}

// one evening: the page replays its whole history, then paints before and after; the picture is the creature with its
// rock and plants, cut from the scene with room around it (the scene itself is as wide as the window)
async function picture(n) {
  const browser = await chromium.launch({ args: ["--disable-dev-shm-usage"] });
  try {
    const page = await (await browser.newContext({ viewport: { width: 900, height: 1000 }, deviceScaleFactor: 2, reducedMotion: "reduce" })).newPage();
    await page.goto(`${SITE}/?shot=${n}&lang=en`, { waitUntil: "load", timeout: 60000 });
    await page.waitForFunction(() => document.documentElement.dataset.shot, null, { timeout: 120000 });
    if (await page.evaluate(() => document.documentElement.dataset.shot) !== "ready") return false;
    const files = {};
    for (const side of ["before", "after"]) {
      const what = await page.evaluate(s => window.agorzillaShot(s), side);   // {category, value, color}: what this part was then
      if (!what) return false;
      await page.waitForTimeout(1200);   // pictures and colours settle
      const r = await page.evaluate(() => { const b = document.getElementById("creature").getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; });
      const w = Math.min(900, r.w * 1.5), h = Math.min(1000, r.h * 1.16);
      const clip = { x: Math.max(0, r.x + r.w / 2 - w / 2), y: Math.max(0, r.y + r.h * .52 - h / 2), width: w, height: h };
      const f = join(OUT, `evening-${n}-${side}.jpg`);
      await page.screenshot({ path: f + ".tmp.jpg", type: "jpeg", quality: 88, clip });
      await rename(f + ".tmp.jpg", f);
      files[side] = `evening-${n}-${side}.jpg`;
      files.category = what.category; files[side + "_value"] = what.value; files[side + "_color"] = what.color;
    }
    return files;
  } finally { await browser.close(); }
}

async function remember(n, files) {
  const f = join(OUT, "evenings.json");
  let list = [];
  try { list = JSON.parse(await readFile(f, "utf8")); } catch {}
  list = list.filter(x => x.n !== n).concat({ n, ...files, at: Math.floor(Date.now() / 1000) }).sort((a, b) => a.n - b.n);
  await writeFile(f + ".tmp", JSON.stringify(list, null, 1) + "\n");
  await rename(f + ".tmp", f);
}

async function pass(force) {
  const l = await latest();
  const todo = force != null ? [force] : (l.rounds || []).map(r => r.n);
  for (const n of todo) {
    if (force == null && await exists(join(OUT, `evening-${n}-after.jpg`))) continue;
    log(`evening ${n + 1}: picturing`);
    const files = await picture(n);
    if (files) { await remember(n, files); log(`evening ${n + 1}: done`); }
    else log(`evening ${n + 1}: the page does not know it yet, next pass`);
  }
}

await mkdir(OUT, { recursive: true });
const once = process.argv.indexOf("--once");
if (once >= 0) { await pass(Number(process.argv[once + 1])); process.exit(0); }
for (;;) {
  try { await pass(null); } catch (e) { log("pass failed:", e.message); }
  await new Promise(r => setTimeout(r, EVERY));
}
