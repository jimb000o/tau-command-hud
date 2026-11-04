/* The Live node light comes back: a page open on the live chain sees the relay (or only our node) go offline, the light turns red,
   and once everything answers again the light must turn green without a reload.
   Nothing leaves the machine: the relay at node.tauhud.com (/status, /health-score and its WebSocket) is a stand-in here that the run
   switches off and on. Run: node tests/live-recover.mjs   (about two minutes) */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".woff2": "font/woff2" };
const server = createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.includes("..")) { res.writeHead(400).end(); return; }
  let f = join(ROOT, p);
  try { if ((await stat(f)).isDirectory()) f = join(f, "index.html"); res.writeHead(200, { "content-type": TYPES[extname(f)] || "application/octet-stream" }).end(await readFile(f)); }
  catch (e) { res.writeHead(404).end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

/* the stand-in relay: "up" (all well), "relay" (nothing answers), "node" (the relay answers, our node does not),
   "after" (our node answers again, but the relay's score is still below 50 from the outage: blocks resumed, the last hour and day look bad) */
let state = "up", height = 500;
const sockets = new Set();
const t0 = Math.floor(Date.now() / 1000);
const block = n => ({ block_hash: n.toString(16).padStart(64, "0"), header: { block_number: n, timestamp: t0 - (height - n) * 8, proposer_pubkey: "a".repeat(96), state_hash: "b".repeat(64) }, tx_ids: [], transactions: [] });
const status = () => state === "node"
  ? { upstream_connected: false, height: 0, online: 1, live_default: true, health: { state: "down", score: 30, label: "down" } }
  : { upstream_connected: true, height, canonical_height: height, tip_height: height, online: 1, live_default: true, health: state === "after" ? { state: "down", score: 46, label: "down" } : { state: "healthy", score: 97, label: "healthy" } };
const healthScore = () => ({ factors: state === "node" ? [{ key: "node", weight: 20, points: 0 }, { key: "sync", weight: 15, points: 0 }]
  : state === "after" ? [{ key: "node", weight: 20, points: 20 }, { key: "stability", weight: 15, points: 0 }, { key: "availability", weight: 10, points: 0 }, { key: "pace", weight: 10, points: 1 }, { key: "last_block", weight: 20, points: 20, value: 6 }] : [] });
const answer = cmd => {
  const c = cmd.split(" ")[0];
  if (state === "node" || state === "relay") return { command: c, status: "error", error: { code: "UPSTREAM", message: "node not connected" } };
  if (c === "getblocks") return { command: c, status: "ok", data: { blocks: [block(height - 1), block(height)], total: height + 1 } };
  if (c === "getmempool") return { command: c, status: "ok", data: { transactions: [] } };
  return { command: c, status: "ok", data: {} };
};
setInterval(() => { if (state === "up" || state === "after") height++; }, 4000);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, timezoneId: "UTC" });
await ctx.route(u => !u.href.startsWith(BASE), async r => {
  const u = new URL(r.request().url());
  if (u.host !== "node.tauhud.com" || state === "relay") return r.abort("internetdisconnected");
  if (u.pathname === "/status") return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(status()) });
  if (u.pathname === "/health-score") return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(healthScore()) });
  return r.fulfill({ status: 404, headers: { "access-control-allow-origin": "*" }, body: "{}" });
});
await ctx.routeWebSocket(() => true, ws => {
  if (state === "relay") { ws.close(); return; }
  sockets.add(ws);
  ws.onMessage(m => { const s = String(m); if (s.startsWith("hello")) { ws.send("ok version=1"); return; } ws.send(JSON.stringify(answer(s))); });
  ws.onClose(() => sockets.delete(ws));
});
await ctx.addInitScript(() => { try { localStorage.setItem("tau-mode", "live"); } catch (e) {} });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.add ? 0 : errs.push(e.message));

const light = () => page.evaluate(() => { const d = document.getElementById("liveDot"); return d ? d.className.replace(/\bdot\b/, "").trim() || "green" : "?"; });
async function waitFor(want, ms, what) {
  const end = Date.now() + ms; let got;
  while (Date.now() < end) { got = await light(); if (got === want) return true; await page.waitForTimeout(500); }
  console.log(`FAIL ${what}: the light is "${got}" after ${ms / 1000} s, expected "${want}"`); return false;
}
let ok = true;
await page.goto(BASE + "?lang=en", { waitUntil: "load" });
ok = await waitFor("green", 30000, "at start") && ok;
for (const cut of ["relay", "node", "node+score"]) {
  state = cut === "relay" ? "relay" : "node"; if (cut === "relay") for (const ws of sockets) ws.close();
  ok = await waitFor("off", 100000, `${cut} offline`) && ok;
  console.log(`${cut} offline: red`);
  if (cut === "node+score") {   // the node answers again; for a while the relay's score still says "down": never red then
    state = "after"; const t = Date.now(); let red = false;
    await page.waitForTimeout(22000);   // one /status round (every 20 s)
    while (Date.now() - t < 90000) { if (await light() === "off") red = true; await page.waitForTimeout(1000); }
    if (red) { console.log(`FAIL ${cut}: the light was still red with our node answering again`); ok = false; } else console.log(`${cut} back, score still low: ${await light()}, not red`);
  }
  state = "up";
  const back = Date.now();
  const g = await waitFor("green", 90000, `${cut} back`); ok = g && ok;
  if (g) console.log(`${cut} back: green after ${Math.round((Date.now() - back) / 1000)} s`);
}
if (errs.length) { console.log("page errors:", errs); ok = false; }
await browser.close(); server.close();
console.log(ok ? "PASS" : "FAILED"); process.exit(ok ? 0 : 1);
