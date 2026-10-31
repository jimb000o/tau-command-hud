/* White Rabbit Key, played by many visitors at once: each one opens /rabbit/ in a headless browser on a phone, a
   tablet or a desktop screen, picks a candidate and plays all five days by TAPPING what a visitor would tap (a place
   on the painted island, a button on a plate), with a play style of their own. Nothing leaves the machine: the
   painted island 22 and its layout come from this folder (infra/rabbit-art/plates), the relay is a mock that takes
   every transaction, and the clock is fake, so a whole game runs in seconds.

   What it reports (tests/out/rabbit-sim.md):
   - JavaScript errors, players stuck (nothing to tap that moves the game on), games that never end
   - places a visitor cannot reach on a screen (off the picture, covered, or a tap target under 44 px)
   - buttons covered or out of reach, text under 11 px, plates that need scrolling on a phone
   - balance: who wins by candidate and by play style, coins, laws, the White Rabbit Key found or not
   - the chain box: one test transaction per own move, never one without the box ticked

   Run: node tests/rabbit-sim.mjs            100 players
        PLAYERS=20 node tests/rabbit-sim.mjs
   Fails (exit 1) on a JavaScript error, a stuck player or an unfinished game. */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, stat, mkdir, writeFile } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium, devices } = createRequire(import.meta.url)("playwright");
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "tests", "out");
const PLAYERS = +(process.env.PLAYERS || 100), WORKERS = +(process.env.WORKERS || 6);
const SPEED = +(process.env.SPEED || 8);

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
const LAYOUT = JSON.parse(await readFile(join(ROOT, "infra/rabbit-art/plates/island-22.json"), "utf8"));
const ISLAND = await readFile(join(ROOT, "infra/rabbit-art/plates/island.jpg"));
const ART_INDEX = JSON.stringify({ scenes: { island: "island.jpg" }, layout: LAYOUT, boxes: {} });

/* the screens visitors come with */
const SCREENS = [
  { name: "phone portrait 390×844", w: 390, h: 844, touch: true, weight: 30 },
  { name: "phone landscape 844×390", w: 844, h: 390, touch: true, weight: 20 },
  { name: "small phone 360×740", w: 360, h: 740, touch: true, weight: 10 },
  { name: "tablet 1024×768", w: 1024, h: 768, touch: true, weight: 10 },
  { name: "laptop 1366×768", w: 1366, h: 768, touch: false, weight: 15 },
  { name: "desktop 1920×1080", w: 1920, h: 1080, touch: false, weight: 15 },
];
/* how they play: what they prefer to tap on the island and on a plate */
const STYLES = {
  newcomer: { follow: 0.8, note: "follows the white rabbit" },
  lawmaker: { places: { hall: 6, market: 2, bar: 2, book: 1 } },
  talker: { places: { market: 6, school: 2, hall: 1 } },
  schemer: { places: { radio: 5, north: 2, south: 2, bar: 2, hall: 2 } },
  money: { places: { north: 3, south: 3, works: 4, hall: 2, radio: 2 } },
  explorer: { quest: true, places: { ama: 3, ship: 2, stone: 3, drums: 3, circle: 3, grotto: 5, hall: 1, market: 1 } },
  wanderer: { places: null },   // anything, at random, and leaves plates without choosing now and then
};
const LANGS = ["en", "en", "en", "en", "en", "en", "zh", "ja"];

const rnd = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
const pickW = (R, w) => { const t = Object.values(w).reduce((a, b) => a + b, 0); let r = R() * t; for (const k in w) { r -= w[k]; if (r <= 0) return k; } return Object.keys(w)[0]; };

const browser = await chromium.launch();
const results = [];

async function play(n) {
  const R = rnd(1000 + n * 7919);
  const scr = SCREENS.flatMap(s => Array(s.weight).fill(s))[(n * 37) % 100];   // every screen as often as its weight says
  const style = Object.keys(STYLES)[n % Object.keys(STYLES).length], S = STYLES[style];
  const lang = LANGS[Math.floor(R() * LANGS.length)], chain = R() < 0.4, cand = ["marisol", "tobias", "baako", "hana"][Math.floor(R() * 4)];
  const out = { n, screen: scr.name, style, lang, chain, cand, errors: [], stuck: null, unreachable: new Set(), covered: [], small: new Set(), scroll: new Set(), tiny: new Set(), visits: {}, steps: 0, sent: 0, own: 0, over: null };
  const ctx = await browser.newContext({ viewport: { width: scr.w, height: scr.h }, hasTouch: scr.touch, isMobile: scr.touch && scr.w < 900, deviceScaleFactor: 1, locale: lang === "zh" ? "zh-CN" : lang === "ja" ? "ja-JP" : "en-US", timezoneId: "UTC" });
  await ctx.route(u => !u.href.startsWith(BASE), r => {
    const u = r.request().url();
    if (u.startsWith("https://node.tauhud.com/rico/art/index.json")) return r.fulfill({ status: 200, contentType: "application/json", body: ART_INDEX, headers: { "access-control-allow-origin": "*" } });
    if (u.startsWith("https://node.tauhud.com/rico/art/island.jpg")) return r.fulfill({ status: 200, contentType: "image/jpeg", body: ISLAND, headers: { "access-control-allow-origin": "*" } });
    return r.abort("internetdisconnected");
  });
  /* the relay: answers what the game asks, takes every transaction */
  await ctx.routeWebSocket(() => true, ws => {
    ws.onMessage(m => {
      const s = String(m), c = s.split(" ")[0], ok = data => ws.send(JSON.stringify({ status: "ok", command: c, data }));
      if (c === "getbalance") ok({ address: s.split(" ")[1], balance: 3 });
      else if (c === "islandmove") ok({ queued: true });
      else if (c === "getgovernance") ok({ consensus_rules: "" });
      else if (c === "getsequence") ok({ sequence_number: 0, tip_height: 100 });
      else if (c === "sendtx") { out.sent++; ok({ tx_hash: "ab".repeat(32) }); }
      else if (c === "getmempool") ok([]);
      else if (c === "getblocks") ok({ blocks: [] });
      else if (c === "via") ok({});
    });
  });
  const page = await ctx.newPage();
  /* the game runs faster than life: every timer and the page's clock go SPEED times as fast */
  await page.addInitScript(k => {
    const st = setTimeout, si = setInterval, pn = performance.now.bind(performance), t0 = pn();
    window.setTimeout = (f, d, ...a) => st(f, (d || 0) / k, ...a);
    window.setInterval = (f, d, ...a) => si(f, (d || 0) / k, ...a);
    performance.now = () => t0 + (pn() - t0) * k;
    const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = f => raf(t => f(performance.now()));
  }, SPEED);
  page.on("pageerror", e => out.errors.push(`${e.name}: ${e.message}`));
  page.on("console", m => { if (m.type() === "error" && !/Failed to load|ERR_|WebSocket|NetworkError|Failed to fetch/i.test(m.text())) out.errors.push("console: " + m.text()); });
  const run = ms => page.waitForTimeout(ms / SPEED);
  const t0 = Date.now();
  try {
    await page.goto(`${BASE}rabbit/?lang=${lang}`, { waitUntil: "load" });
    await run(3000);
    /* the start screen: tick the box (or not), pick the candidate */
    const intro = page.locator(".cv-card.intro");
    await intro.waitFor({ timeout: 5000 * SPEED });
    await measure(page, out, "start screen");
    if (chain) await tap(page, out, page.locator("#cvChain"), "chain box");
    await tap(page, out, page.locator(".cv-cand").nth(["marisol", "tobias", "baako", "hana"].indexOf(cand)), "candidate");
    await run(1500);
    /* where every place stands on this screen: on the picture, uncovered, big enough to tap */
    const geo = await page.evaluate(() => {
      const SC = window.COVE_SCENE, cv = document.getElementById("cvScene"), r = cv.getBoundingClientRect(), o = {};
      for (const id in SC.places) {
        const [bx, by, bw, bh] = SC.places[id].box, [x0, y0] = SC.toScreen(bx, by), [x1, y1] = SC.toScreen(bx + bw, by + bh);
        const cx = (Math.max(x0, 0) + Math.min(x1, r.width)) / 2, cy = (Math.max(y0, 0) + Math.min(y1, r.height)) / 2;
        const on = x1 > 0 && x0 < r.width && y1 > 0 && y0 < r.height, top = on && document.elementFromPoint(r.left + cx, r.top + cy);
        o[id] = { w: Math.round(x1 - x0), h: Math.round(y1 - y0), on, covered: on && top !== cv ? (top && (top.id || top.className || top.tagName)) : null, hit: on ? SC.hit(cx, cy) : null };
      }
      return o;
    });
    out.geo = geo;
    for (const [id, g] of Object.entries(geo)) {
      if (!g.on) out.unreachable.add(id + " (outside the view: drag or ☰)");
      else if (g.covered) out.unreachable.add(id + " (covered by " + String(g.covered).slice(0, 30) + ")");
      else if (g.hit !== id && !["stone", "drums", "circle", "grotto"].includes(id)) out.unreachable.add(id + " (tap finds " + g.hit + ")");
      if (g.on && Math.min(g.w, g.h) < 44) out.tiny.add(id);
    }
    let last = "", same = 0;
    for (let step = 0; step < 400; step++) {
      out.steps = step;
      const st = await page.evaluate(() => { const G = window.COVE_GAME.state; return G && { day: G.day, move: G.move, over: !!G.over, counting: !!G.counting, seen: G.seen || {}, chart: !!G.chart, key: !!G.key, book: G.book.length }; });
      if (st && st.over) { await run(4000); break; }   // the result is on screen (or comes back by itself)
      const sig = JSON.stringify([st && st.day, st && st.move, st && st.book, await page.evaluate(() => { const c = document.querySelector(".cv-card"); return c ? c.className : "none"; })]);
      same = sig === last ? same + 1 : 0; last = sig;
      if (same > 25) { out.stuck = { at: sig, screen: await page.evaluate(() => { const c = document.querySelector(".cv-card"); return c ? c.innerText.slice(0, 200) : "no plate open"; }) }; break; }
      const card = page.locator(".cv-card").first();
      if (await card.count()) {
        const cls = await page.evaluate(() => { const c = document.querySelector(".cv-card"); return c ? c.className : ""; });
        if (/end/.test(cls)) break;
        await measure(page, out, /paper/.test(cls) ? "morning paper" : /locked/.test(cls) ? "vote" : (await card.getAttribute("data-place", { timeout: 1000 }).catch(() => "")) || "plate");
        const acts = card.locator(".cv-acts button.cv-b:not([disabled])");
        const k = await acts.count();
        const wander = style === "wanderer" && R() < 0.25 && !/paper|locked/.test(cls);
        const idle = same >= 2 && await card.locator(".cv-x").isVisible().catch(() => false);   // tapped, and nothing changed: a visitor would leave
        if (k && !wander && !idle) {
          const labels = await acts.allInnerTexts();
          let i = Math.floor(R() * k);
          /* the vote: the lawmaker votes yes on what helps, everyone else at random */
          const pref = labels.findIndex(t => /Continue|继续|続け|Start the day|To the council|开始|議会|Yes/.test(t));
          if (/paper|locked/.test(cls) && pref >= 0 && R() < 0.8) i = pref;
          if (/Read how|Licence|Follow the footprints|许可|ライセンス/.test(labels[i])) i = (i + 1) % k;   // would open a new tab
          await tap(page, out, acts.nth(i), labels[i].split("\n")[0]);
        } else if (await card.locator(".cv-x").isVisible().catch(() => false)) {
          await tap(page, out, card.locator(".cv-x"), "close");
        } else if (!/locked|paper|intro/.test(cls)) {
          await page.keyboard.press("Escape");
        }
        await run(1200);
        continue;
      }
      /* the island: where to go */
      if (st && st.move >= 3) { await run(1500); continue; }
      let target = null;
      if (S.follow && R() < S.follow) target = "rabbit";
      else {
        const open = await page.evaluate(() => Object.keys(window.COVE_SCENE.places).filter(id => !window.COVE_SCENE.locked(id)));
        const w = {}; for (const id of open) w[id] = S.places ? S.places[id] || 0.3 : 1;
        if (S.quest && st) { if (!st.seen.ama) w.ama = 20; if (st.day >= 2 && !st.chart) w.ship = 20; for (const q of ["stone", "drums", "circle", "grotto"]) if (open.includes(q) && !st.seen[q]) w[q] = 30; }
        target = pickW(R, w);
      }
      let pt = null;
      for (let tries = 0; tries < 4 && !(pt && pt[2]); tries++) {   // the camera may still be on its way back from the last place
        if (tries) await run(700);
        pt = await page.evaluate(id => {
        const SC = window.COVE_SCENE, cv = document.getElementById("cvScene"), r = cv.getBoundingClientRect();
        if (id === "rabbit") { for (let y = 0; y < r.height; y += 4) for (let x = 0; x < r.width; x += 4) if (SC.hit(x, y) === "rabbit") return [r.left + x, r.top + y, true]; return null; }
        const [bx, by, bw, bh] = SC.places[id].box, [x0, y0] = SC.toScreen(bx, by), [x1, y1] = SC.toScreen(bx + bw, by + bh);
        const cx = (Math.max(x0, 0) + Math.min(x1, r.width)) / 2, cy = (Math.max(y0, 0) + Math.min(y1, r.height)) / 2;
        if (x1 <= 0 || x0 >= r.width || y1 <= 0 || y0 >= r.height) return null;
        const top = document.elementFromPoint(r.left + cx, r.top + cy);
        return [r.left + cx, r.top + cy, top === cv && SC.hit(cx, cy) === id];
      }, target);
      }
      if (!pt || !pt[2]) { out.unreachable.add(target + (pt ? " (tap missed)" : " (outside the view: drag or ☰)")); continue; }
      out.visits[target] = (out.visits[target] || 0) + 1;
      if (scr.touch) await page.touchscreen.tap(pt[0], pt[1]); else await page.mouse.click(pt[0], pt[1]);
      await run(1200);
    }
    const G = await page.evaluate(() => { const G = window.COVE_GAME.state; return G && { over: G.over, day: G.day, coins: G.coins, laws: G.laws, key: !!G.key, chart: !!G.chart, seen: G.seen || {}, onchain: G.onchain, book: G.book, deals: G.deals, pacts: G.pacts, lies: G.lies.length }; });
    out.over = G && G.over; out.game = G;
    out.own = G ? G.book.filter(b => b.who === G.me || b.who === cand).length : 0;
    if (G && !G.over && !out.stuck) out.stuck = { at: `day ${G.day}, game did not end in 400 steps` };
  } catch (e) { out.errors.push("harness: " + e.message.split("\n")[0]); }
  out.ms = Date.now() - t0;
  await ctx.close();
  results.push(out);
  process.stdout.write(`${n + 1}/${PLAYERS} ${scr.name} ${style} ${cand}${chain ? " chain" : ""}: ${out.over ? "won by " + out.over.win : "NOT FINISHED"} ${out.errors.length ? "ERRORS " : ""}${out.stuck ? "STUCK " : ""}(${(out.ms / 1000).toFixed(1)} s)\n`);
}

/* a tap a visitor can make: the button is there, on screen, nothing covers it, and it is big enough for a finger */
async function tap(page, out, loc, what) {
  try {
    await loc.scrollIntoViewIfNeeded({ timeout: 1500 * SPEED });   // the page's clock runs SPEED times as fast, Playwright's waits too
    const b = await loc.boundingBox();
    if (b && Math.min(b.width, b.height) < 44 && out.screen.includes("phone") && what !== "chain box") out.small.add(`${what.slice(0, 40)} (${Math.round(b.width)}×${Math.round(b.height)})`);
    await loc.click({ timeout: 2000 * SPEED });
  } catch (e) { out.covered.push(`${what.slice(0, 50)}: ${e.message.split("\n")[0].slice(0, 120)}`); await loc.click({ force: true, timeout: 1000 * SPEED }).catch(() => {}); }
}
/* the open plate on a phone: smallest text, and whether it needs scrolling to reach its buttons */
async function measure(page, out, where) {
  const m = await page.evaluate(() => {
    const c = document.querySelector(".cv-card"); if (!c) return null;
    let min = 99, minT = "";
    for (const e of c.querySelectorAll("*")) { if (!e.childNodes.length || ![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue; const s = parseFloat(getComputedStyle(e).fontSize); if (s < min && e.offsetParent) { min = s; minT = e.textContent.trim().slice(0, 30); } }
    const st = document.getElementById("cvStage").getBoundingClientRect(), r = c.getBoundingClientRect();
    return { min, minT, scrolls: c.scrollHeight > c.clientHeight + 4, over: r.top < st.top - 1 || r.bottom > st.bottom + 1, share: r.height / st.height };
  }).catch(() => null);
  if (!m) return;
  if (m.min < 11) out.small.add(`text ${m.min}px in ${where}: "${m.minT}"`);
  if (m.scrolls) out.scroll.add(where);
}

let next = 0;
const ONLY = process.env.ONLY ? process.env.ONLY.split(",").map(Number) : null;   // ONLY=9,12: just these players, with details
if (ONLY) { for (const n of ONLY) await play(n); for (const r of results) console.log(JSON.stringify({ n: r.n, stuck: r.stuck, errors: r.errors, covered: r.covered, unreachable: [...r.unreachable], visits: r.visits }, null, 1)); }
else await Promise.all(Array.from({ length: WORKERS }, async () => { while (next < PLAYERS) await play(next++); }));
await browser.close(); server.close();

/* ---------- the report ---------- */
results.sort((a, b) => a.n - b.n);
const L = [`## White Rabbit Key: ${PLAYERS} simulated players`, ""];
const count = (arr, f) => { const o = {}; arr.forEach(x => { const k = f(x); if (k != null) o[k] = (o[k] || 0) + 1; }); return o; };
const tbl = (head, rows) => { L.push("| " + head.join(" | ") + " |", "|" + head.map(() => "---").join("|") + "|"); rows.forEach(r => L.push("| " + r.join(" | ") + " |")); L.push(""); };
const done = results.filter(r => r.over), err = results.filter(r => r.errors.length), stuck = results.filter(r => r.stuck);
L.push(`Finished: **${done.length}/${PLAYERS}** · JavaScript errors: **${err.length}** · stuck: **${stuck.length}**`, "");
if (err.length) { L.push("### JavaScript errors"); [...new Set(err.flatMap(r => r.errors))].forEach(e => L.push("- " + e)); L.push(""); }
if (stuck.length) { L.push("### Stuck"); stuck.forEach(r => L.push(`- #${r.n} ${r.screen} ${r.style}: ${r.stuck.at} · ${r.stuck.screen || ""}`)); L.push(""); }
L.push("### Places a visitor cannot tap, by screen");
const byScreen = {};
results.forEach(r => { const s = byScreen[r.screen] || (byScreen[r.screen] = { n: 0, un: {}, tiny: {} }); s.n++; r.unreachable.forEach(u => (s.un[u] = (s.un[u] || 0) + 1)); r.tiny.forEach(u => (s.tiny[u] = (s.tiny[u] || 0) + 1)); });
tbl(["Screen", "Players", "Cannot reach", "Tap target under 44 px"], Object.entries(byScreen).map(([k, s]) => [k, s.n, Object.keys(s.un).sort().join(", ") || "—", Object.keys(s.tiny).sort().join(", ") || "—"]));
const small = {}, scroll = {}, covered = {};
results.forEach(r => { r.small.forEach(s => (small[r.screen + ": " + s] = 1)); r.scroll.forEach(s => (scroll[s] = (scroll[s] || new Set()).add(r.screen))); r.covered.forEach(c => (covered[c.split(":")[0]] = (covered[c.split(":")[0]] || 0) + 1)); });
if (Object.keys(small).length) { L.push("### Small text or buttons on phones"); Object.keys(small).slice(0, 30).forEach(s => L.push("- " + s)); L.push(""); }
if (Object.keys(scroll).length) { L.push("### Plates that need scrolling"); Object.entries(scroll).forEach(([k, v]) => L.push(`- ${k}: ${[...v].join(", ")}`)); L.push(""); }
if (Object.keys(covered).length) { L.push("### Buttons that could not be tapped"); Object.entries(covered).forEach(([k, v]) => L.push(`- ${k} (${v}×)`)); L.push(""); }
L.push("### Who wins");
const cands = ["marisol", "tobias", "baako", "hana"];
tbl(["Played as", "Games", "Won", "Win rate", "Winner when lost"], cands.map(c => { const g = done.filter(r => r.cand === c), w = g.filter(r => r.over.win === c); return [c, g.length, w.length, g.length ? Math.round(100 * w.length / g.length) + "%" : "—", Object.entries(count(g.filter(r => r.over.win !== c), r => r.over.win)).map(([k, v]) => k + " " + v).join(", ")]; }));
tbl(["Style", "Games", "Won", "Avg own laws", "Avg coins at the end", "Key found"], Object.keys(STYLES).map(s => { const g = done.filter(r => r.style === s); const avg = f => g.length ? (g.reduce((a, r) => a + f(r), 0) / g.length).toFixed(1) : "—"; return [s, g.length, g.filter(r => r.over.win === r.cand).length, avg(r => r.game.laws.filter(l => l.by === r.cand).length), avg(r => r.game.coins[r.cand]), g.filter(r => r.game.key).length]; }));
L.push(`Overall winners: ${Object.entries(count(done, r => r.over.win)).map(([k, v]) => `${k} ${v}`).join(", ")}`, "");
const lawsPassed = count(done.flatMap(r => r.game.laws), l => l.id);
L.push(`Laws passed (all games): ${Object.entries(lawsPassed).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(", ")}`, "");
const quest = done.filter(r => r.style === "explorer");
L.push(`Explorers: Ama's house seen ${quest.filter(r => r.game.seen.ama).length}/${quest.length}, chart ${quest.filter(r => r.game.chart).length}, Tide Stone ${quest.filter(r => r.game.seen.stone).length}, drums ${quest.filter(r => r.game.seen.drums).length}, circle ${quest.filter(r => r.game.seen.circle).length}, key ${quest.filter(r => r.game.key).length}`, "");
const ch = done.filter(r => r.chain), noCh = done.filter(r => !r.chain);
L.push(`Chain box ticked: ${ch.length} players, ${ch.reduce((a, r) => a + r.sent, 0)} test transactions for ${ch.reduce((a, r) => a + r.own, 0)} own lines in the Book · box not ticked: ${noCh.reduce((a, r) => a + r.sent, 0)} transactions (must be 0)`, "");
L.push(`Average game: ${(done.reduce((a, r) => a + r.steps, 0) / Math.max(1, done.length)).toFixed(0)} taps, ${(results.reduce((a, r) => a + r.ms, 0) / results.length / 1000).toFixed(1)} s simulated`, "");
await mkdir(OUT, { recursive: true });
await writeFile(join(OUT, "rabbit-sim.md"), L.join("\n"));
await writeFile(join(OUT, "rabbit-sim.json"), JSON.stringify(results, (k, v) => (v instanceof Set ? [...v] : v), 1));
console.log("\n" + L.join("\n"));
process.exit(err.length || stuck.length || done.length < PLAYERS ? 1 : 0);
