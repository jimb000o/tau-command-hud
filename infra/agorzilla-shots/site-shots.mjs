/* Screenshots of tauhud.com for the posts, taken the way a visitor sees the site: Live mode, real chain, after the live
   data has arrived. 11 Nov 2026: a post showed the rules wall with the header red ("Live · Offline", "– online") and
   the simulation's made-up wallets (a1a1…, b2b2…) under "LIVE NODE", because its picture had been taken where our node
   could not be reached. Here every picture is checked before it is kept:

     the header's mode chip is green (Live · Connected or catching up), not Offline, Connecting or Simulation
     block height and nodes online are numbers, not "–"
     no simulation banner and no made-up addresses (a1a1a1a1…, the same two signs again and again) on the page

   A page that fails is not pictured; the post then goes without a picture (alerts.py live_shot). Pages: the front page,
   /status/, and every page a closer look, a planned spotlight or a site update of the last 30 days links to, read from
   tauhud.com itself. Output in /out (alerts_public → node.tauhud.com/pageshots/): <page>.jpg and index.json
   {page: {path, at, ok, why}}.

   node site-shots.mjs          every page, then every SITE_SHOTS_HOURS (default 6) again
   node site-shots.mjs --once   every page once and stop (up shots)
   node site-shots.mjs --once rules status   only these */
import { chromium } from "playwright";
import { mkdir, readFile, rename, writeFile, unlink } from "node:fs/promises";
import { join } from "node:path";

const SITE = (process.env.SITE_URL || "https://tauhud.com").replace(/\/$/, "");
const OUT = process.env.PAGESHOTS_DIR || "/out";
const EVERY = Number(process.env.SITE_SHOTS_HOURS || 6) * 3600 * 1000;
const KEEP_DAYS = 7;   // a checked picture older than this is dropped when the page fails now
const log = (...a) => console.log(new Date().toISOString(), ...a);
const UA = { "Cache-Control": "no-cache", "User-Agent": "tauhud-site-shots/1 (+https://tauhud.com)" };

export const pageName = path => (path.replace(/^\/+|\/+$/g, "") || "hud").replace(/\//g, "-");

async function json(p) {
  try {
    const r = await fetch(SITE + p, { headers: UA });
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

function localPath(link) {
  if (!link) return null;
  try {
    const u = new URL(link, SITE);
    if (!/^(www\.)?tauhud\.com$/.test(u.hostname)) return null;
    return "/" + u.pathname.replace(/^\/+|\/+$/g, "") + (u.pathname.replace(/^\/+|\/+$/g, "") ? "/" : "");
  } catch { return null; }
}

async function pages() {
  const out = new Set(["/", "/status/"]);
  const since = Date.now() - 30 * 86400 * 1000;
  const dd = await json("/assets/deepdives.json");
  for (const p of (dd && dd.posts) || []) out.add(localPath(p.link));
  const plan = await json("/assets/posts-plan.json");
  for (const p of (Array.isArray(plan) ? plan : (plan && plan.posts) || [])) out.add(localPath(p.link));
  const up = await json("/assets/updates.json");
  for (const e of Array.isArray(up) ? up : []) {
    const m = e && e.major;
    if (m && m.link && (!e.on || Date.parse(e.on) >= since)) out.add(localPath(m.link));
  }
  out.delete(null);
  return [...out];
}

// what is wrong with the page as it shows now; "" when it is fit for a post
const CHECK = () => {
  const t = s => (document.querySelector(s)?.textContent || "").trim();
  const hud = document.querySelector("#chipMode");   // the front page has its own mode chip (index.html)
  const mode = hud || document.querySelector("#tnMode");
  if (!mode) return "no header";
  const m = (mode.querySelector("b")?.textContent || "").trim();
  if (/simulation/i.test(m)) return `mode chip says ${m}`;
  if (!mode.classList.contains("live")) return `mode chip not green (${m || "empty"})`;
  if (!hud) {
    if (/^[–-]?$/.test(t("#tnHeight b"))) return "block height missing";
    if (/^[–-]?$/.test(t("#tnOnline b"))) return "nodes online missing";
  }
  const dashes = [...document.querySelectorAll("header .chip b, .rail .chip b")].filter(b => b.offsetParent && /^[–-]$/.test(b.textContent.trim()));
  if (dashes.length) return `${dashes.length} header chips still empty`;
  const body = document.body.innerText;
  if (/SIMULATION\s*·/.test(body)) return "simulation banner on the page";
  const fake = body.match(/\b([0-9a-f]{2})\1{3,}/i);
  if (fake) return `made-up address on the page (${fake[0]})`;
  return "";
};

async function shoot(browser, path) {
  const name = pageName(path);
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  await ctx.addInitScript(() => { try { localStorage.setItem("tau-mode", "live"); } catch {} });
  const page = await ctx.newPage();
  try {
    await page.goto(`${SITE}${path}?mode=live&lang=en`, { waitUntil: "load", timeout: 60000 });
    let why = "timeout";
    for (let i = 0; i < 30; i++) {          // up to a minute for the live data
      await page.waitForTimeout(2000);
      why = await page.evaluate(CHECK);
      if (!why) break;
    }
    if (!why) {
      await page.waitForTimeout(3000);       // the page's own panels a moment longer, then check once more
      why = await page.evaluate(CHECK);
    }
    if (why) return { name, path, ok: false, why };
    const tmp = join(OUT, `.${name}.jpg`);
    await page.screenshot({ path: tmp, type: "jpeg", quality: 85 });
    await rename(tmp, join(OUT, `${name}.jpg`));
    return { name, path, ok: true, why: "" };
  } catch (e) {
    return { name, path, ok: false, why: String(e && e.message || e).slice(0, 160) };
  } finally {
    await ctx.close();
  }
}

async function round(only) {
  await mkdir(OUT, { recursive: true });
  let index = {};
  try { index = JSON.parse(await readFile(join(OUT, "index.json"), "utf8")); } catch {}
  const list = (await pages()).filter(p => !only.length || only.includes(pageName(p)));
  const browser = await chromium.launch({ args: ["--disable-dev-shm-usage"] });
  try {
    for (const path of list) {
      const r = await shoot(browser, path);
      const was = index[r.name];
      if (r.ok) index[r.name] = { path, at: new Date().toISOString(), ok: true };
      else if (was && was.ok && Date.now() - Date.parse(was.at) < KEEP_DAYS * 86400 * 1000) index[r.name] = { ...was, last_fail: r.why };
      else {
        index[r.name] = { path, at: new Date().toISOString(), ok: false, why: r.why };
        await unlink(join(OUT, `${r.name}.jpg`)).catch(() => {});
      }
      log(r.ok ? "ok  " : "skip", path, r.why);
    }
  } finally {
    await browser.close();
  }
  await writeFile(join(OUT, ".index.json"), JSON.stringify(index, null, 1));
  await rename(join(OUT, ".index.json"), join(OUT, "index.json"));
  const ok = Object.values(index).filter(v => v.ok).length;
  log(`${ok} of ${Object.keys(index).length} pages have a checked picture`);
}

const args = process.argv.slice(2);
if (args[0] === "--once") {
  await round(args.slice(1));
} else {
  for (;;) {
    try { await round([]); } catch (e) { log("round failed", e); }
    await new Promise(r => setTimeout(r, EVERY));
  }
}
