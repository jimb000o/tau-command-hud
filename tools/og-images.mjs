/* The link preview picture of every page (og:image / twitter:image), 1200×630 PNG in assets/og/<page>.png.
   Each one is the page itself on a 1920 px screen in Simulation mode (made-up chain, no real data), shrunk to 1200 px,
   with a band at the bottom that names the page and the address. Run it again after a page changes its look:

     npm i --no-save playwright && npx playwright install chromium && node tools/og-images.mjs
     node tools/og-images.mjs explorer vote      only these pages */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "assets", "og");
const CLOCK = new Date(process.env.CLOCK || "2026-10-28T10:24:00Z");   // a rule change is open in the simulation

/* page → [path, the name in the band, one line under it] */
export const PAGES = {
  hud:        ["/", "Tau HUD", "Live view of Tau Testnet Alpha, where the rules change by agreement"],
  explorer:   ["/explorer/", "Explorer", "Trace any block, transaction or address"],
  proposals:  ["/proposals/", "Proposals", "Every rule change from proposal to law"],
  account:    ["/account/", "Accounts", "Balance, own rules and refusals of any address"],
  nodes:      ["/nodes/", "Community nodes", "Who runs a node, for how long, on which chain"],
  stats:      ["/stats/", "Testnet stats", "Block pace, transactions, accounts and restarts"],
  devpulse:   ["/devpulse/", "Build pulse", "How Tau's code is moving, from public git history"],
  history:    ["/history/", "Time travel", "Every block with the rules in force at that moment"],
  story:      ["/story/", "Tau in 60 seconds", "How Tau changes its rules without a fork"],
  chronicle:  ["/chronicle/", "Chronicle", "Twelve years of Tau, from Zennet to the testnet"],
  playground: ["/playground/", "Rule Playground", "Write a rule, see what the testnet would say"],
  missions:   ["/missions/", "Missions", "Six short tasks on a practice chain"],
  whatif:     ["/whatif/", "What if", "Move a lever and watch the chain react"],
  vote:       ["/vote/", "Vote for real", "Vote on Tau's rules yourself, practised first"],
  wallet:     ["/wallet/", "Wallet", "A testnet account with its own rules"],
  status:     ["/status/", "Status", "Uptime, sync gaps and testnet restarts"],
  findings:   ["/findings/", "Findings", "Bugs found while running a node, with their status"],
  meta:       ["/meta/", "Tau HUD in numbers", "Visitors per day, counted without cookies"],
  developers: ["/developers/", "Developers", "Widgets, badges and a free JSON API"],
  press:      ["/press/", "Press kit", "Films, logo, screenshots and facts, free to use"],
  legal:      ["/legal/", "Privacy", "No cookies, no tracking, no third-party analytics"],
};

const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".woff2": "font/woff2", ".mp4": "video/mp4", ".webmanifest": "application/manifest+json" };
const server = createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  try { const b = await readFile(join(ROOT, p)); res.writeHead(200, { "content-type": TYPES[extname(p)] || "application/octet-stream" }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;

const band = (name, line) => `
  for (const e of document.querySelectorAll("body *")) if (e.childElementCount === 0 && e.textContent.trim() === "New here?") {   // the first-visit tour offer
    let x = e; while (x && x !== document.body && getComputedStyle(x).position !== "fixed") x = x.parentElement;
    if (x && x !== document.body) x.style.display = "none";
  }
  const b = document.createElement("div");
  b.style.cssText = "position:fixed;left:0;right:0;bottom:0;height:150px;z-index:2147483647;display:flex;align-items:center;gap:36px;padding:0 64px;box-sizing:border-box;background:linear-gradient(180deg,rgba(5,6,8,.9),#050608 40%);border-top:2px solid rgba(57,255,138,.55);font-family:Sora,'Segoe UI',sans-serif;color:#fff";
  b.innerHTML = '<svg viewBox="0 0 64 64" width="84" height="84" fill="none" stroke="#39ff8a" stroke-width="3"><circle cx="32" cy="32" r="25"/><path d="M13 33 H23 L27.5 24 L34.5 43 L39 33 H51" stroke-linejoin="round" stroke-linecap="round"/></svg>'
    + '<div style="flex:1;min-width:0"><div style="font-size:50px;font-weight:700;letter-spacing:-.01em;line-height:1.1">' + ${JSON.stringify(name)} + '</div>'
    + '<div style="font-size:28px;color:#b8bcc6;margin-top:8px;white-space:nowrap">' + ${JSON.stringify(line)} + '</div></div>'
    + '<div style="font:600 34px \\'JetBrains Mono\\',monospace;color:#39ff8a;white-space:nowrap">tauhud.com</div>';
  document.body.append(b);`;

const only = process.argv.slice(2);
const browser = await chromium.launch();
await mkdir(OUT, { recursive: true });
for (const [key, [path, name, line]] of Object.entries(PAGES)) {
  if (only.length && !only.includes(key)) continue;
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1008 }, deviceScaleFactor: 0.625, locale: "en-US", timezoneId: "UTC" });
  await ctx.route(u => !u.href.startsWith(BASE), r => r.abort("internetdisconnected"));
  await ctx.routeWebSocket(() => true, ws => ws.close());
  const page = await ctx.newPage();
  await page.clock.install({ time: CLOCK });
  await page.goto(`${BASE}${path}?mode=sim&lang=en`, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(+(process.env.SETTLE_MS || 6000));
  await page.evaluate(band(name, line));
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(OUT, `${key}.png`) });
  await ctx.close();
  console.log(`assets/og/${key}.png`);
}
await browser.close();
server.close();
