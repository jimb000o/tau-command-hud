// The bare pictures of the island and its rooms, as the browser draws them (rabbit/scene.js plate()), saved to
// infra/rabbit-art/plates/<place>.jpg. paint.py hands them to the painter, so the painted pictures keep every place
// where the game expects it. Run again after the drawn island or a room changes:
//   node infra/rabbit-art/plates.mjs        (needs Playwright, as the page tests do)
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { extname, join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const root = new URL("../..", import.meta.url).pathname, out = join(root, "infra/rabbit-art/plates");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2" };
const server = createServer(async (q, r) => {
  const p = decodeURIComponent(q.url.split("?")[0]); let f = join(root, p.endsWith("/") ? p + "index.html" : p);
  try { const b = await readFile(f); r.writeHead(200, { "content-type": TYPES[extname(f)] || "application/octet-stream" }); r.end(b); } catch (e) { r.writeHead(404); r.end(); }
}).listen(0);
const port = server.address().port, b = await chromium.launch(), page = await b.newPage({ viewport: { width: 1600, height: 900 } });
await page.route("https://node.tauhud.com/**", r => r.fulfill({ status: 404, body: "" }));
await page.goto(`http://localhost:${port}/rabbit/?mode=sim`); await page.waitForFunction(() => window.COVE_SCENE && COVE_SCENE.plate);
await mkdir(out, { recursive: true });
for (const id of ["island", ...Object.keys(await page.evaluate(() => COVE_SCENE.places))]) {
  const url = await page.evaluate(id => COVE_SCENE.plate(id).toDataURL("image/jpeg", 0.9), id);
  await writeFile(join(out, id + ".jpg"), Buffer.from(url.split(",")[1], "base64")); console.log("plates/" + id + ".jpg");
}
await b.close(); server.close();
