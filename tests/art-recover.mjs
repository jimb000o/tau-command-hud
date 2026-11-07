/* White Rabbit Key's painted island comes back: a page opened while the art server (node.tauhud.com/rico/art) does not
   answer, for instance during an up, shows the drawn island after a few seconds, and once the server answers again the
   painting takes its place without a reload. A server that answers without a painting is not asked again.
   Nothing leaves the machine: index.json and the painting are stand-ins the run switches on and off.
   Run: node tests/art-recover.mjs   (about one minute) */
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

/* the stand-in art server: "off" (nothing answers), "on" (the list and the painting), "bare" (the list, no painting in it) */
const LAYOUT = JSON.parse(await readFile(join(ROOT, "infra/rabbit-art/plates/island-22.json"), "utf8"));
const PAINTING = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAFQAAAAkCAIAAACYK4pXAAAARElEQVR42u3PMQEAMAgAIF0aMxnC/udSeAkNyJqOq14cJi8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vLy8vv+UDf0wBOJ6Fe3UAAAAASUVORK5CYII=", "base64");   // a small 21:9 stand-in for the painting
let state = "off", asked = 0;
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, timezoneId: "UTC" });
await ctx.route(u => !u.href.startsWith(BASE), async r => {
  const u = new URL(r.request().url());
  if (u.host !== "node.tauhud.com" || !u.pathname.startsWith("/rico/art/") || state === "off") return r.abort("internetdisconnected");
  const cors = { "access-control-allow-origin": "*" };
  if (u.pathname === "/rico/art/index.json") { asked++; return r.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ scenes: state === "bare" ? {} : { island: "island.png" }, layout: LAYOUT }) }); }
  if (u.pathname === "/rico/art/island.png") return r.fulfill({ status: 200, contentType: "image/png", headers: cors, body: PAINTING });
  return r.fulfill({ status: 404, headers: cors, body: "" });
});
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(e.message));

/* what shows: "wait" (sky and sea, the painting on its way), "drawn" (the drawn island), "painted" (the painting, laid out) */
const PAINTED = LAYOUT.places.hall.name;
const shows = () => page.evaluate(n => { const S = window.COVE_SCENE; if (!S || !S.art) return "?"; const A = S.art;
  return A.pending ? "wait" : A.img.island && S.places.hall.name === n ? "painted" : A.img.island ? "painting without its layout" : "drawn"; }, PAINTED);
async function waitFor(want, ms, what) {
  const end = Date.now() + ms; let got;
  while (Date.now() < end) { got = await shows(); if (got === want) return true; await page.waitForTimeout(500); }
  console.log(`FAIL ${what}: "${got}" after ${ms / 1000} s, expected "${want}"`); return false;
}
let ok = true;
await page.goto(BASE + "rabbit/?lang=en&clock=free&hour=11:00", { waitUntil: "load" });
ok = await waitFor("drawn", 20000, "art server off") && ok;
console.log("art server off: the drawn island");
state = "on"; const back = Date.now();
if (await waitFor("painted", 40000, "art server back")) console.log(`art server back: the painting after ${Math.round((Date.now() - back) / 1000)} s, no reload`); else ok = false;

state = "bare"; asked = 0;   // a server without a painting: the drawn island, asked once and then left alone
await page.goto(BASE + "rabbit/?lang=en&clock=free&hour=11:00", { waitUntil: "load" });
await page.waitForTimeout(35000);
const now = await shows();
if (now !== "drawn" || asked !== 1) { console.log(`FAIL no painting on the server: "${now}", the list asked for ${asked} times (expected the drawn island, asked once)`); ok = false; }
else console.log("no painting on the server: the drawn island, the list asked for once in 35 s");
if (errs.length) { console.log("page errors:", errs); ok = false; }
await browser.close(); server.close();
console.log(ok ? "PASS" : "FAILED"); process.exit(ok ? 0 : 1);
