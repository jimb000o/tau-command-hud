/* The places of White Rabbit Key at night (rabbit/scene.js): a place with a painted night (rooms/<id>-night, paint.py
   isle) shows that picture after dark and fetches it only then, never by day; a place without one is lit by its lamps,
   warm and at least about half as bright as at noon, not drowned in the night's blue. And the art server's list of
   pictures drives it all: a night picture of a place is never shown without its day picture.

   Stand-in pictures (the drawn plates in infra/rabbit-art/plates and a night picture of one colour made here), the
   relay a mock: nothing leaves the machine.

   Run: node tests/room-night.mjs        (needs playwright, as tests/pages.mjs) */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".css": "text/css", ".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".woff2": "font/woff2", ".txt": "text/plain" };
const server = createServer(async (req, res) => {
  let f = join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  try { if ((await stat(f)).isDirectory()) f = join(f, "index.html"); res.writeHead(200, { "content-type": TYPES[extname(f)] || "application/octet-stream" }).end(await readFile(f)); }
  catch (e) { res.writeHead(404).end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;
const PLATES = join(ROOT, "infra/rabbit-art/plates");
const LAYOUT = JSON.parse(await readFile(join(PLATES, "island-22.json"), "utf8"));
const browser = await chromium.launch();
let failed = 0;
const check = (name, ok, got) => { console.log((ok ? "ok   " : "FAIL ") + name + (ok ? "" : "  (" + JSON.stringify(got) + ")")); if (!ok) failed++; };

/* the night picture of the market: one deep green, unlike anything on the plates, so it is plain to see when it shows */
const shot = await browser.newPage();
const NIGHT = Buffer.from(await shot.evaluate(() => {
  const c = document.createElement("canvas"); c.width = 1600; c.height = 900; const g = c.getContext("2d");
  g.fillStyle = "rgb(30,170,70)"; g.fillRect(0, 0, 1600, 900);
  return c.toDataURL("image/png").split(",")[1];
}), "base64");
await shot.close();
const FILES = { "island.jpg": join(PLATES, "island.jpg"), "market.jpg": join(PLATES, "market.jpg"), "bar.jpg": join(PLATES, "bar.jpg"), "radio.jpg": join(PLATES, "radio.jpg") };

async function room(id, hour, scenes) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, timezoneId: "UTC" });
  const asked = [], errors = [];
  await ctx.route(u => !u.href.startsWith(BASE), async r => {
    const u = new URL(r.request().url()), cors = { "access-control-allow-origin": "*" };
    if (u.host === "node.tauhud.com" && u.pathname === "/rico/art/index.json")
      return r.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ scenes, layout: LAYOUT }) });
    if (u.host === "node.tauhud.com" && u.pathname.startsWith("/rico/art/")) {
      const f = u.pathname.slice(10); asked.push(f);
      if (f === "market-night.png") return r.fulfill({ status: 200, contentType: "image/png", headers: cors, body: NIGHT });
      if (FILES[f]) return r.fulfill({ status: 200, contentType: "image/jpeg", headers: cors, body: await readFile(FILES[f]) });
      return r.fulfill({ status: 404, headers: cors, body: "" });
    }
    return r.abort("internetdisconnected");
  });
  await ctx.routeWebSocket(() => true, ws => ws.onMessage(m => { const c = String(m).split(" ")[0]; ws.send(JSON.stringify({ status: "ok", command: c, data: c === "getsequence" ? { sequence_number: 0, tip_height: 100 } : {} })); }));
  const page = await ctx.newPage();
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`${BASE}rabbit/?lang=en&clock=free&hour=${hour}&live=0`, { waitUntil: "load" });
  await page.waitForFunction(() => window.COVE_SCENE && window.COVE_SCENE.art && window.COVE_SCENE.art.img.island && !window.COVE_SCENE.art.pending, null, { timeout: 30000 });
  await page.waitForFunction(ids => ids.every(i => window.COVE_SCENE.art.img[i]), Object.keys(scenes).filter(k => !k.endsWith("-night")), { timeout: 30000 });
  await page.evaluate(id => window.COVE_SCENE.focus(id, 0), id);
  await page.waitForTimeout(3500);   // the room opens, a night picture comes and fades in
  /* the room's colour where nobody stands: the left quarter of the scene, as drawn on the screen */
  const rgb = await page.evaluate(() => {
    const c = document.getElementById("cvScene"), g = c.getContext("2d");
    const d = g.getImageData(Math.round(c.width * 0.04), Math.round(c.height * 0.15), Math.round(c.width * 0.22), Math.round(c.height * 0.6)).data;
    let r = 0, gg = 0, b = 0, n = 0; for (let i = 0; i < d.length; i += 16) { r += d[i]; gg += d[i + 1]; b += d[i + 2]; n++; }
    return [r / n, gg / n, b / n];
  });
  await ctx.close();
  return { rgb, asked, errors, lum: 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2] };
}

const WITH = { island: "island.jpg", market: "market.jpg", "market-night": "market-night.png", bar: "bar.jpg", radio: "radio.jpg" };
const green = ([r, g, b]) => g > r * 1.6 && g > b * 1.6;

const noon = await room("market", "12:00", WITH);
check("noon: no JavaScript error", !noon.errors.length, noon.errors);
check("noon: the market's night picture is not even fetched", !noon.asked.includes("market-night.png"), noon.asked);
check("noon: the market by day", !green(noon.rgb), noon.rgb);

const night = await room("market", "22:00", WITH);
check("night: no JavaScript error", !night.errors.length, night.errors);
check("night: the market's night picture fetched", night.asked.includes("market-night.png"), night.asked);
check("night: the market shows its painted night", green(night.rgb), night.rgb);

const elsewhere = await room("bar", "22:00", WITH);
check("night: the night pictures come after dark, the open place's first", elsewhere.asked.includes("market-night.png"), elsewhere.asked);
check("night: a place without one does not show another's", !green(elsewhere.rgb), elsewhere.rgb);

/* a place without a painted night is lit by its lamps: warm, and at least about half as bright as at noon */
for (const id of ["bar", "radio"]) {
  const day = await room(id, "12:00", WITH), dark = await room(id, "22:00", WITH);
  check(`${id} at night: at least about half the light of noon (${Math.round(100 * dark.lum / day.lum)} %)`, dark.lum >= 0.48 * day.lum, [dark.lum, day.lum]);
  const warm = (dark.rgb[0] / dark.rgb[2]) / (day.rgb[0] / day.rgb[2]);   // red over blue, against noon: the night's blue alone gives about 0.4
  check(`${id} at night: lamp light, not the night's blue (red to blue ${warm.toFixed(2)} of noon's)`, warm >= 0.9, [dark.rgb, day.rgb]);
}

/* a night picture listed without its day picture is never shown (it was made from that very picture) */
const lone = await room("bar", "22:00", { island: "island.jpg", bar: "bar.jpg", "market-night": "market-night.png" });
check("a night without its day picture is not fetched", !lone.asked.includes("market-night.png"), lone.asked);

await browser.close(); server.close();
console.log(failed ? `\n${failed} FAILED` : "\nall passed");
process.exit(failed ? 1 : 0);
