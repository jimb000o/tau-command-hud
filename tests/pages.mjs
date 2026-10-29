/* Opens every page of the site in a headless browser and fails on what a visitor would hit:
   - a JavaScript error (an uncaught exception or a console error), in the simulation and with the live node offline
   - an English text left on a Chinese page (?lang=zh&i18n=missing)
   - a page that scrolls or spills sideways on the wide screens the site is designed for

   Nothing leaves the machine: the site is served from this folder and every other address (the relay at node.tauhud.com,
   fonts, GitHub) is refused, so the run shows the offline paths too and does not depend on the live testnet.

   The clock is set to the same moment on every run (CLOCK, a weekday morning with a visitor vote open), so the simulated
   chain shows the same blocks and texts each time and a check cannot pass at one hour and fail at another.

   Chinese: texts listed in tests/zh-known-english.txt (names that stay English, and older gaps still to translate) are
   reported but do not fail the run; any other English text on a Chinese page does. Numbers and hashes are ignored.

   Run: npm i --no-save playwright && npx playwright install chromium && node tests/pages.mjs
        node tests/pages.mjs account vote     only these pages
   Writes tests/out/report.md (and a screenshot per failing page) for the GitHub summary. */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, readdir, stat, mkdir, writeFile } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");   // CommonJS lookup, so a global install (NODE_PATH) works too
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "tests", "out");
const SETTLE = +(process.env.SETTLE_MS || 4000);   // the pages build in steps (sim chain, dictionaries, first fetches)
const SKIP = new Set(["assets", "go", "infra", "kit", "tests", "node_modules", "embed"]);   // embed is a widget, checked on its own below
const LAYOUT = ["account", "chronicle", "explorer", "findings", "gazette", "history", "hud", "missions", "nodes", "playground", "proposals", "stats", "status", "vote", "wallet", "whatif", "developers"];
const SCREENS = [[2560, 1440], [2000, 1125]];
const CLOCK = new Date(process.env.CLOCK || "2026-10-28T10:24:00Z");

/* a missing Chinese text in a form that does not change with the block, the hash or the hour */
const norm = s => String(s).replace(/<[^>]*>/g, " ").replace(/[0-9a-f]{4,}…[0-9a-f]{4,}|\b[0-9a-f]{12,}\b/gi, "{h}").replace(/\d+([.,:]\d+)*/g, "{n}").replace(/\s+/g, " ").trim();
const KNOWN = new Set((await readFile(join(ROOT, "tests", "zh-known-english.txt"), "utf8").catch(() => "")).split("\n").map(l => l.trim()).filter(l => l && !l.startsWith("#")).map(norm));

/* ---------- a static server for the repo folder ---------- */
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm", ".ico": "image/x-icon", ".webmanifest": "application/manifest+json", ".woff2": "font/woff2", ".txt": "text/plain" };
const server = createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.includes("..")) { res.writeHead(400).end(); return; }
  let f = join(ROOT, p);
  try { if ((await stat(f)).isDirectory()) f = join(f, "index.html"); res.writeHead(200, { "content-type": TYPES[extname(f)] || "application/octet-stream" }).end(await readFile(f)); }
  catch (e) { res.writeHead(404).end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

/* ---------- which pages ---------- */
const dirs = [];
for (const d of await readdir(ROOT, { withFileTypes: true })) {
  if (!d.isDirectory() || d.name.startsWith(".") || SKIP.has(d.name)) continue;
  try { await stat(join(ROOT, d.name, "index.html")); dirs.push(d.name); } catch (e) {}
}
const only = process.argv.slice(2);
const pages = [["hud", ""], ...dirs.sort().map(d => [d, d + "/"]), ["embed", "embed/?h=320"], ["story-zh", "story/zh/"]]
  .filter(([n]) => !only.length || only.includes(n));

/* console noise that is not a bug: refused network requests are the point of this run */
const NETWORK = /Failed to load resource|net::ERR_|WebSocket connection to|ERR_FAILED|ERR_BLOCKED|ERR_CONNECTION|Failed to fetch|NetworkError|Load failed|CORS|ResizeObserver loop/i;

const browser = await chromium.launch();
const problems = [];   // {page, run, kind, text}
const add = (page, run, kind, text) => problems.push({ page, run, kind, text: String(text) });

async function visit(name, path, { mode, lang, w = 1600, h = 900, layout = false, again = false }) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, locale: lang === "zh" ? "zh-CN" : "en-US", timezoneId: "UTC" });
  await ctx.route(u => !u.href.startsWith(BASE), r => r.abort("internetdisconnected"));
  await ctx.routeWebSocket(() => true, ws => ws.close());   // the relay's socket: offline, never the real chain
  const page = await ctx.newPage();
  await page.clock.install({ time: CLOCK });
  const run = `${mode}${lang === "zh" ? " zh" : ""}${layout ? ` ${w}×${h}` : ""}`;
  const errs = new Set();
  page.on("pageerror", e => errs.add(`uncaught ${e.name}: ${e.message}` + (e.stack ? ` (${(e.stack.split("\n").find(l => l.includes(BASE)) || "").trim().replace(BASE, "/")})` : "")));
  page.on("console", m => { if (m.type() === "error" && !NETWORK.test(m.text())) errs.add(`console: ${m.text()}`); });
  const q = new URLSearchParams(path.includes("?") ? path.split("?")[1] : "");
  q.set("mode", mode);
  if (lang === "zh") { q.set("lang", "zh"); q.set("i18n", "missing"); } else q.set("lang", "en");
  const url = BASE + path.split("?")[0] + "?" + q;
  try {
    const r = await page.goto(url, { waitUntil: "load", timeout: 30000 });
    if (!r || r.status() !== 200) add(name, run, "load", `HTTP ${r && r.status()}`);
    await page.waitForTimeout(SETTLE);
  } catch (e) { add(name, run, "load", e.message.split("\n")[0]); }
  for (const e of errs) add(name, run, "js", e);
  if (lang === "zh") {
    const miss = await page.evaluate(() => [...(window.__i18nMissing || [])]).catch(() => []);
    /* a text seen only for a moment (a page half built) is checked on a second visit: it fails only if it shows up again */
    const fresh = miss.filter(k => !KNOWN.has(norm(k)));
    const confirmed = fresh.length && !again ? new Set((await visitZhAgain(name, path, mode)).map(norm)) : null;
    for (const k of miss) add(name, run, KNOWN.has(norm(k)) ? "zh-known" : !confirmed || confirmed.has(norm(k)) ? "zh" : "zh-once", k);
  }
  if (layout) {
    const m = await page.evaluate(() => { const s = document.scrollingElement || document.documentElement; return { sh: s.scrollHeight, sw: s.scrollWidth, ih: innerHeight, iw: innerWidth }; }).catch(() => null);
    if (m && m.sh > m.ih + 2) add(name, run, "layout", `page scrolls: content ${m.sh}px tall in a ${m.ih}px window`);
    if (m && m.sw > m.iw + 2) add(name, run, "layout", `page spills sideways: content ${m.sw}px wide in a ${m.iw}px window`);
  }
  if (problems.some(p => p.page === name && p.run === run && !["zh-known", "zh-once"].includes(p.kind))) {
    await mkdir(OUT, { recursive: true });
    await page.screenshot({ path: join(OUT, `${name}-${run.replace(/[ ×]/g, "-")}.png`) }).catch(() => {});
  }
  await ctx.close();
}

/* the second visit of a Chinese page: only its misses, nothing reported */
async function visitZhAgain(name, path, mode) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: "zh-CN", timezoneId: "UTC" });
  await ctx.route(u => !u.href.startsWith(BASE), r => r.abort("internetdisconnected"));
  await ctx.routeWebSocket(() => true, ws => ws.close());
  const page = await ctx.newPage();
  await page.clock.install({ time: CLOCK });
  const q = new URLSearchParams(path.includes("?") ? path.split("?")[1] : "");
  q.set("mode", mode); q.set("lang", "zh"); q.set("i18n", "missing");
  let miss = [];
  try { await page.goto(BASE + path.split("?")[0] + "?" + q, { waitUntil: "load", timeout: 30000 }); await page.waitForTimeout(SETTLE * 1.5); miss = await page.evaluate(() => [...(window.__i18nMissing || [])]); } catch (e) {}
  await ctx.close();
  return miss;
}

const jobs = [];
for (const [name, path] of pages) {
  jobs.push(() => visit(name, path, { mode: "sim", lang: "en" }));
  jobs.push(() => visit(name, path, { mode: "live", lang: "en" }));
  if (name !== "story-zh") jobs.push(() => visit(name, path, { mode: "sim", lang: "zh" }));
  if (LAYOUT.includes(name)) for (const [w, h] of SCREENS) jobs.push(() => visit(name, path, { mode: "sim", lang: "en", w, h, layout: true }));
}
let next = 0;
const worker = async () => { while (next < jobs.length) await jobs[next++](); };
await Promise.all(Array.from({ length: +(process.env.WORKERS || 4) }, worker));
await browser.close();
server.close();

/* ---------- report ---------- */
const KIND = { load: "Page did not load", js: "JavaScript errors", zh: "English left on the Chinese page", layout: "Scrolls or spills on a wide screen" };
const failing = problems.filter(p => !["zh-known", "zh-once"].includes(p.kind));
const known = new Set(problems.filter(p => p.kind === "zh-known").map(p => norm(p.text)));
const lines = [`## Page check: ${pages.length} pages, ${jobs.length} runs`, ""];
if (!failing.length) lines.push("All pages load without JavaScript errors, every Chinese text is there and no page scrolls on 2560 or 2000 wide. ✅");
for (const kind of Object.keys(KIND)) {
  const ps = problems.filter(p => p.kind === kind);
  if (!ps.length) continue;
  lines.push(`### ❌ ${KIND[kind]} (${ps.length})`, "", "| Page | Run | What |", "|---|---|---|");
  const seen = new Set();
  for (const p of ps) { const key = p.page + norm(p.text); if (kind === "zh" && seen.has(key)) continue; seen.add(key); lines.push(`| /${p.page === "hud" ? "" : p.page} | ${p.run} | ${p.text.slice(0, 400).replace(/\|/g, "\\|").replace(/\n/g, " ")} |`); }
  lines.push("");
}
if (failing.some(p => p.kind === "zh")) lines.push("Add each English text with its Chinese to `assets/i18n/zh/<page>.js` (or `common.js` for the header). A name that should stay English goes into `tests/zh-known-english.txt`.", "");
const once = [...new Set(problems.filter(p => p.kind === "zh-once").map(p => `/${p.page === "hud" ? "" : p.page}: ${p.text.slice(0, 160)}`))];
if (once.length) lines.push(`English seen once on a Chinese page while it was still building, not failing (${once.length}):`, "", ...once.map(t => "- " + t.replace(/\n/g, " ")), "");
if (known.size) lines.push(`Known English on Chinese pages, not failing: ${known.size} texts listed in \`tests/zh-known-english.txt\`.`);
if (process.env.WRITE_KNOWN) {   // maintainer helper: appends this run's new misses to the list, to sort into a section by hand
  const file = join(ROOT, "tests", "zh-known-english.txt"), fresh = [...new Set(problems.filter(p => p.kind === "zh").map(p => norm(p.text)))].sort();
  if (fresh.length) await writeFile(file, (await readFile(file, "utf8").catch(() => "")) + "\n# New, sort into a section above:\n" + fresh.join("\n") + "\n");
}
await mkdir(OUT, { recursive: true });
await writeFile(join(OUT, "report.md"), lines.join("\n") + "\n");
console.log(lines.join("\n"));
process.exit(failing.length ? 1 : 0);
