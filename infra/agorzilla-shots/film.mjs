/* Short films of the live site for the feature posts on X (alerts/xfeatures.py): a headless Chromium opens the page like a
   visitor, a drawn pointer does the one thing the post is about, the camera zooms slowly onto the place that changed.
   Nothing here posts: xfeatures.py cuts the film to mp4 and hands it to the owner privately; only `up x send <id>` posts.

   The job: xfeatures.py writes <FILMS_DIR>/want/<id>.json, {"id", "film": {"url", "steps", "seconds", "check"}}. This
   loop looks every FILMS_EVERY seconds (default 60), films each job once and writes <id>.webm and <id>.meta.json
   {"start": seconds into the recording where the steps begin, "seconds", "ok", "why"}, then removes the job.

   Steps (each a list; a target is a CSS selector or [x, y] in the 1280×720 frame):
     ["wait", ms]                     nothing happens for ms
     ["move", target, ms?]            the pointer glides there (default 900 ms)
     ["click", target]                glides there and clicks; ["click?", target] the same, skipped when it is not there
     ["zoom", target, scale, ms?]     the camera closes in on the target (default 1.5×, 1600 ms); ["unzoom", ms?] back
     ["js", "code"]                   run in the page (an async function body; it may await)
   On tauhud.com the page is filmed only in Live mode after the live data arrived (live-check.mjs), as the post pictures;
   "check": false skips that (agorzilla.com has no such header).

   node film.mjs            the loop
   node film.mjs --once     every waiting job once and stop
   node film.mjs --try spec.json out.webm   one film from a spec file, for a test */
import { chromium } from "playwright";
import { chmod, mkdir, readdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { CHECK } from "./live-check.mjs";

const DIR = process.env.FILMS_DIR || "/out/xfilms";
const EVERY = Number(process.env.FILMS_EVERY || 60) * 1000;
const W = 1280, H = 720;
const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

// the visitor's pointer, drawn: headless Chromium records no cursor. It hangs on <html>, outside <body>, so the
// camera's zoom (a transform on <body>) does not move it away from where the mouse really is.
const POINTER = () => {
  if (document.getElementById("xf-pointer")) return;
  const p = document.createElement("div");
  p.id = "xf-pointer";
  p.innerHTML = '<svg width="26" height="26" viewBox="0 0 26 26"><path d="M3 2 L3 21 L8 16 L12 24 L15.5 22.5 L11.5 14.5 L18 14.5 Z" fill="#fff" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  p.style.cssText = "position:fixed;left:-40px;top:-40px;z-index:2147483647;pointer-events:none;transition:transform .08s;filter:drop-shadow(0 2px 3px rgba(0,0,0,.5))";
  document.documentElement.appendChild(p);
  addEventListener("mousemove", e => { p.style.left = e.clientX - 3 + "px"; p.style.top = e.clientY - 2 + "px"; }, true);
  addEventListener("mousedown", () => { p.style.transform = "scale(.82)"; }, true);
  addEventListener("mouseup", () => { p.style.transform = ""; }, true);
};

async function where(page, target) {
  if (Array.isArray(target)) return { x: target[0], y: target[1] };
  const el = await page.$(target);
  const b = el && await el.boundingBox();
  return b ? { x: b.x + b.width / 2, y: b.y + b.height / 2 } : null;
}

export async function run(page, steps, mouse) {
  for (const s of steps || []) {
    const [op, a, b, c] = s;
    if (op === "wait") await sleep(Number(a) || 0);
    else if (op === "move" || op === "click" || op === "click?") {
      const to = await where(page, a);
      if (!to) { if (op === "click?") continue; throw new Error(`step ${JSON.stringify(s)}: nothing there`); }
      const ms = op === "move" ? Number(b) || 900 : 900, n = Math.max(8, Math.round(ms / 16));
      for (let i = 1; i <= n; i++) {
        const t = i / n, e = t < .5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;   // ease in and out
        await page.mouse.move(mouse.x + (to.x - mouse.x) * e, mouse.y + (to.y - mouse.y) * e);
        await sleep(ms / n);
      }
      mouse.x = to.x; mouse.y = to.y;
      if (op !== "move") { await sleep(250); await page.mouse.down(); await sleep(90); await page.mouse.up(); await sleep(300); }
    } else if (op === "zoom") {
      const to = await where(page, a) || { x: W / 2, y: H / 2 };
      const ms = Number(c) || 1600;
      await page.evaluate(([x, y, k, ms]) => {
        const s = document.body.style;
        s.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`;
        s.transformOrigin = `${x + scrollX}px ${y + scrollY}px`;
        s.transform = `scale(${k})`;
      }, [to.x, to.y, Number(b) || 1.5, ms]);
      await sleep(ms);
    } else if (op === "unzoom") {
      const ms = Number(a) || 1200;
      await page.evaluate(ms => { document.body.style.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`; document.body.style.transform = ""; }, ms);
      await sleep(ms);
    } else if (op === "js") {
      await page.evaluate(code => new Function(`return (async () => { ${code} })()`)(), String(a));
    } else throw new Error(`unknown step ${op}`);
  }
}

export async function film(browser, spec, out) {
  const f = spec.film || spec;
  const url = new URL(f.url);
  const tau = /(^|\.)tauhud\.com$/.test(url.hostname) || f.check === true;
  if (tau && !url.searchParams.has("mode")) url.searchParams.set("mode", "live");
  if (!url.searchParams.has("lang")) url.searchParams.set("lang", "en");
  const dir = join(tmpdir(), "xf-" + Date.now());
  const t0 = Date.now();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: W, height: H } } });
  await ctx.addInitScript(() => { try { localStorage.setItem("tau-mode", "live"); } catch {} });
  await ctx.addInitScript(POINTER);
  const page = await ctx.newPage();
  let why = "", start = 0;
  try {
    await page.goto(url.href, { waitUntil: "load", timeout: 60000 });
    if (tau && f.check !== false) {
      why = "timeout";
      for (let i = 0; i < 30 && why; i++) { await sleep(2000); why = await page.evaluate(CHECK); }
      if (why) throw new Error(`not fit to film: ${why}`);
    }
    await sleep(Number(f.settle) || 1500);
    const mouse = { x: W * 0.62, y: H * 0.7 };
    await page.mouse.move(mouse.x, mouse.y);
    start = (Date.now() - t0) / 1000;
    await run(page, f.steps, mouse);
    const left = (Number(f.seconds) || 10) * 1000 - (Date.now() - t0 - start * 1000);
    if (left > 0) await sleep(left);
  } catch (e) {
    why = String(e.message || e);
  }
  const video = page.video();
  await ctx.close();
  const raw = video && await video.path();
  if (raw && !why) await rename(raw, out);
  await rm(dir, { recursive: true, force: true });
  return { start: Math.round(start * 100) / 100, seconds: Number(f.seconds) || 10, ok: !why, why };
}

async function round(browser) {
  let jobs = [];
  try { jobs = (await readdir(join(DIR, "want"))).filter(n => n.endsWith(".json")); } catch { return; }
  for (const n of jobs) {
    const p = join(DIR, "want", n);
    let spec;
    try { spec = JSON.parse(await readFile(p, "utf8")); } catch (e) { log("job", n, "unreadable:", e.message); await rm(p, { force: true }); continue; }
    const id = String(spec.id || n.replace(/\.json$/, "")).replace(/[^a-z0-9-]/gi, "");
    log("filming", id, spec.film && spec.film.url);
    const meta = await film(browser, spec, join(DIR, `${id}.webm.part`));
    if (meta.ok) { await rename(join(DIR, `${id}.webm.part`), join(DIR, `${id}.webm`)); await chmod(join(DIR, `${id}.webm`), 0o666).catch(() => {}); }
    await writeFile(join(DIR, `${id}.meta.json`), JSON.stringify({ ...meta, at: new Date().toISOString() }), { mode: 0o666 });
    await rm(p, { force: true });
    log(id, meta.ok ? "filmed" : "not filmed: " + meta.why);
  }
}

async function main() {
  const args = process.argv.slice(2);
  // this service runs as root, the xfeatures service (which asks for films and cuts them) as the alerts user: both may
  // write and remove here
  await mkdir(join(DIR, "want"), { recursive: true }).catch(() => {});
  for (const d of [DIR, join(DIR, "want")]) await chmod(d, 0o777).catch(() => {});
  const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
  try {
    if (args[0] === "--try") {
      const spec = JSON.parse(await readFile(args[1], "utf8"));
      console.log(JSON.stringify(await film(browser, spec, args[2])));
      return;
    }
    if (args[0] === "--once") return await round(browser);
    for (;;) {
      try { await round(browser); } catch (e) { log("round failed:", e.message); }
      await sleep(EVERY);
    }
  } finally {
    await browser.close();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
