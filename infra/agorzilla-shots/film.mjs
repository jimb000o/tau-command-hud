/* Films of tauhud.com for the YouTube videos (alerts/yt.py), taken the way a visitor sees the site: Live mode, real
   chain, after the live data has arrived. The same check as the post pictures (live-check.mjs): a page that shows the
   simulation, an offline header or a made-up address is not filmed, and the video is not made.

   yt.py writes a job into FILM_DIR (the yt_work volume, shared with it):  <id>.job.json
     {"id": "...", "format": "wide" | "tall", "level": "new",
      "scenes": [{"n": 0, "page": "/explorer/", "seconds": 12.5, "door": false,
                  "steps": [{"at": 3, "do": "zoom", "to": "#bars"}, {"at": 8, "do": "zoom"}]}]}
   and this service answers with <id>/<n>/000001.jpg ... (the page pictured as fast as the machine allows, about ten
   times a second, each as sharp as the screen) and <id>.done.json
     {"ok": true, "scenes": [{"n": 0, "ok": true, "dir": "0", "w": 2880, "h": 1620, "frames": [[file, seconds], ...],
                              "steps": [{"at": 3, "do": "zoom", "to": "#bars", "ok": true, "rect": [x, y, w, h]}]}]}
   The camera does not move here: a zoom step only says where its target lies (rect, in pixels of the pictures), and
   the cut (alerts/yt_cut.py) moves in on it smoothly. Steps never click: zoom, scroll, hover, wait. A step whose
   target is not on the page is named in the answer with ok false; the scene is still filmed.

   wide = 1920x1080 (FILM_WIDE_SCALE, default 1: finer costs pictures per second). tall = the site's own phone layout (432x768 CSS
   pixels) drawn 2.5 times as fine = 1080x1920, for shorts.

   node film.mjs            waits for jobs, forever
   node film.mjs <job.json> that job once (tests; FILM_CHECK=off films whatever shows, FILM_QUERY replaces ?mode=live) */
import { chromium } from "playwright";
import { mkdir, readFile, readdir, rename, writeFile, rm } from "node:fs/promises";
import { join, basename } from "node:path";
import { CHECK } from "./live-check.mjs";

const SITE = (process.env.SITE_URL || "https://tauhud.com").replace(/\/$/, "");
const DIR = process.env.FILM_DIR || "/work/film";
const CHECKED = (process.env.FILM_CHECK || "on") !== "off";
const QUERY = process.env.FILM_QUERY || "mode=live&lang=en";
const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));

export const FORMATS = {
  wide: { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: Number(process.env.FILM_WIDE_SCALE || 1) },
  tall: { viewport: { width: 432, height: 768 }, deviceScaleFactor: 2.5, isMobile: true, hasTouch: true },
};

// inside the page: where an element lies in the window, or null when it is not there to see
const RECT = sel => {
  const el = document.querySelector(sel);
  if (!el || !el.getClientRects().length) return null;
  const r = el.getBoundingClientRect();
  if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.top > innerHeight) return null;
  return [r.left, r.top, r.width, r.height];
};

async function step(page, s, k) {
  try {
    if (s.do === "zoom") {
      if (!s.to) return { ok: true, rect: null };
      const r = await page.evaluate(RECT, s.to);
      return r ? { ok: true, rect: r.map(v => Math.round(v * k)) } : { ok: false };
    }
    if (s.do === "scroll") return { ok: await page.evaluate(sel => { const el = document.querySelector(sel); if (!el) return false; el.scrollIntoView({ behavior: "smooth", block: "center" }); return true; }, s.to) };
    if (s.do === "hover") { await page.hover(s.to, { timeout: 2000 }); return { ok: true }; }
    if (s.do === "wait") return { ok: true };
    return { ok: false };                               // anything else (a click, typing) is not done
  } catch { return { ok: false }; }
}

async function scene(browser, job, sc, out) {
  const f = FORMATS[job.format] || FORMATS.wide, k = f.deviceScaleFactor;
  const dir = join(out, String(sc.n));
  await rm(dir, { recursive: true, force: true });
  await mkdir(dir, { recursive: true });
  const ctx = await browser.newContext({ viewport: f.viewport, deviceScaleFactor: k, isMobile: !!f.isMobile, hasTouch: !!f.hasTouch });
  await ctx.addInitScript(([level, door]) => { try {
    localStorage.setItem("tau-mode", "live"); localStorage.setItem("tau-level", level);
    localStorage.setItem("tau-tour", "1"); localStorage.setItem("tau-tour-seen", "1");     // no "new here?" card in the picture
    if (!door) localStorage.setItem("tau-seen", "1");                                      // the dashboard, not the front door
  } catch {} }, [job.level || "new", !!sc.door]);
  const page = await ctx.newPage();
  const res = { n: sc.n, ok: false, why: "", steps: [], frames: [], dir: String(sc.n), w: Math.round(f.viewport.width * k), h: Math.round(f.viewport.height * k) };
  try {
    await page.goto(`${SITE}${sc.page}${sc.page.includes("?") ? "&" : "?"}${QUERY}`, { waitUntil: "load", timeout: 60000 });
    let why = "";
    if (CHECKED) {
      why = "timeout";
      for (let i = 0; i < 30 && why; i++) { await page.waitForTimeout(2000); why = await page.evaluate(CHECK); }
      if (!why) { await page.waitForTimeout(2500); why = await page.evaluate(CHECK); }
    } else await page.waitForTimeout(2500);
    if (why) { res.why = why; return res; }
    const steps = [...(sc.steps || [])].filter(s => s.at < sc.seconds).sort((a, b) => a.at - b.at);
    const t0 = Date.now();
    for (let i = 1; ; i++) {
      const t = (Date.now() - t0) / 1000;
      if (t >= sc.seconds) break;
      while (steps.length && steps[0].at <= t) { const s = steps.shift(); res.steps.push({ at: s.at, do: s.do, to: s.to || null, ...(await step(page, s, k)) }); }
      const name = String(i).padStart(6, "0") + ".jpg";
      const at = (Date.now() - t0) / 1000;
      await page.screenshot({ path: join(dir, name), type: "jpeg", quality: 92 });
      res.frames.push([name, Math.round(at * 1000) / 1000]);
    }
    if (CHECKED) { const late = await page.evaluate(CHECK); if (late) { res.why = "during the take: " + late; return res; } }
    if (res.frames.length < 3) { res.why = "too few pictures taken"; return res; }
    res.ok = true; res.seconds = sc.seconds;
  } catch (e) {
    res.why = String(e && e.message || e).slice(0, 200);
  } finally {
    await ctx.close();
    if (!res.ok) { res.frames = []; await rm(dir, { recursive: true, force: true }); }
  }
  return res;
}

export async function film(jobPath) {
  const job = JSON.parse(await readFile(jobPath, "utf8"));
  const out = join(DIR, job.id);
  await mkdir(out, { recursive: true });
  const browser = await chromium.launch({ args: ["--disable-dev-shm-usage"] });
  const done = { id: job.id, format: job.format || "wide", ok: true, at: new Date().toISOString(), scenes: [] };
  try {
    for (const sc of job.scenes) {
      let r = await scene(browser, job, sc, out);
      if (!r.ok) { log("again", job.id, sc.n, r.why); await sleep(5000); r = await scene(browser, job, sc, out); }
      done.scenes.push(r);
      log(r.ok ? "ok  " : "fail", job.id, sc.n, sc.page, r.why || "");
      if (!r.ok) { done.ok = false; done.why = `scene ${sc.n + 1} (${sc.page}): ${r.why}`; break; }   // one view not fit to show: no video
    }
  } finally { await browser.close(); }
  const tmp = join(DIR, `.${job.id}.done.json`);
  await writeFile(tmp, JSON.stringify(done, null, 1));
  await rename(tmp, join(DIR, `${job.id}.done.json`));
  return done;
}

async function waiting() {
  let names = [];
  try { names = await readdir(DIR); } catch { return []; }
  return names.filter(n => n.endsWith(".job.json") && !n.startsWith(".") && !names.includes(n.replace(/\.job\.json$/, ".done.json"))).sort();
}

if (process.argv[1] && basename(process.argv[1]) === "film.mjs") {
  if (process.argv[2]) {
    const d = await film(process.argv[2]);
    console.log(JSON.stringify(d));
    process.exit(d.ok ? 0 : 1);
  }
  await mkdir(DIR, { recursive: true });
  log("film service waiting in", DIR);
  for (;;) {
    for (const n of await waiting()) {
      try { await film(join(DIR, n)); }
      catch (e) {
        log("job failed", n, e);
        await writeFile(join(DIR, n.replace(/\.job\.json$/, ".done.json")), JSON.stringify({ id: n.replace(/\.job\.json$/, ""), ok: false, why: String(e && e.message || e).slice(0, 300), scenes: [] }));
      }
    }
    await sleep(15000);
  }
}
