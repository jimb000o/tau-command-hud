/* The link preview picture of every page (og:image / twitter:image): a 1200×630 card in assets/og/<page>.png
   (No Memo: .jpg, it carries a painting). A designed card, not a screenshot: at the size X and Telegram show it
   (about 500 px wide on a computer, 330 px on a phone) a shot of the dashboard is unreadable and showed the
   simulation. Each card says one thing in large type: what the page is and why someone would open it.

     npm i --no-save playwright && npx playwright install chromium && node tools/og-images.mjs
     node tools/og-images.mjs hud nomemo      only these cards

   Rules for the words: one message per card, every claim checkable on the page or the testnet, no promises,
   "Tau Net" for the network and "Tau" for the language. The bottom left corner stays empty: X lays the page
   title over it. After changing a card, raise ?v= in that page's og:image and twitter:image, or X and
   Telegram keep showing the old picture they fetched. */
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, mkdir, copyFile } from "node:fs/promises";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "assets", "og");

/* pill: "live" = read from the testnet (green dot), "sim" = a practice chain in the browser (amber), else a plain label */
const LIVE = ["live", "LIVE · Tau Testnet Alpha"];
const SIM = ["sim", "PRACTICE CHAIN · simulated"];
const tag = t => ["", t];

/* card → [path, pill, title, lead, small] */
export const PAGES = {
  explorer:   ["/explorer/", LIVE, "Explorer", "What happened to it? Trace any block, transaction or address.", "Read from our own verifying node."],
  proposals:  ["/proposals/", LIVE, "Proposals", "Every change to the chain's own rules, from proposal to law.", "Validators agree, and it takes effect at a later block."],
  account:    ["/account/", LIVE, "Accounts", "Every account keeps its own rules. Look one up.", "Balance, transfers, its rules and what it refused."],
  nodes:      ["/nodes/", LIVE, "Community nodes", "Who runs a Tau Net node, for how long, on which chain.", "One command to join."],
  stats:      ["/stats/", LIVE, "Testnet stats", "Block times, transactions, active accounts and restarts.", "Tau Testnet Alpha, block by block."],
  devpulse:   ["/devpulse/", tag("FROM PUBLIC GIT HISTORY"), "Build pulse", "How Tau's public code is moving.", "Which parts change, and which version the testnet node runs."],
  history:    ["/history/", LIVE, "Time travel", "Every block, with the rules in force at that moment.", "Watch the chain's rules change by agreement."],
  story:      ["/story/", tag("ONE MINUTE"), "Tau in 60 seconds", "Most blockchains change their rules with a hard fork. Tau Net changes them by agreement.", "Six steps, one minute."],
  chronicle:  ["/chronicle/", tag("CHRONICLE"), "Twelve years of Tau", "From Zennet in 2014 to a testnet that changes its own rules.", "The story so far, year by year."],
  playground: ["/playground/", SIM, "Rule Playground", "Write a Tau rule and see what the testnet would say.", "Then vote a rule change in from a practice validator seat."],
  missions:   ["/missions/", SIM, "Missions", "Change a chain's rules by agreement, in six short missions.", "Then see where the same happens on Tau Testnet Alpha."],
  whatif:     ["/whatif/", SIM, "What if", "Move a lever and watch the chain react.", "Faster blocks, more validators, a higher bar for rule changes."],
  vote:       ["/vote/", LIVE, "Vote on the rules", "Vote on Tau Testnet Alpha's rule changes yourself.", "Five commands, tried first on a practice chain."],
  wallet:     ["/wallet/", LIVE, "A wallet with rules", "Your test wallet carries rules, not only a balance.", "Send, take a payment back, ask a friend to co-sign. Testnet only."],
  status:     ["/status/", LIVE, "Status", "Is the testnet healthy right now?", "Health, uptime, sync gaps and restarts, with their history."],
  findings:   ["/findings/", LIVE, "Findings", "Bugs found while running a Tau Net node, with their status.", "Found one too? Report it."],
  meta:       ["/meta/", LIVE, "Tau HUD in numbers", "What our sites move on the testnet, and who visits.", "Wallets and transactions read from the blocks; visitors counted without cookies."],
  developers: ["/developers/", tag("DEVELOPERS"), "The testnet on your site", "A live widget, a badge or the free JSON API.", "Copy one line. No key needed."],
  press:      ["/press/", tag("ABOUT TAU HUD"), "Press kit", "Films, logo, screenshots and facts about Tau HUD.", "Free to use."],
  legal:      ["/legal/", tag("ABOUT TAU HUD"), "Privacy", "No cookies, no tracking, no third-party analytics.", "What Tau HUD processes, in plain words."],
  start:      ["/start/", LIVE, "Try Tau Net in four steps", "A test wallet, a rule of your own, a block that seals it.", "A few minutes. Nothing to install, no sign-up."],
  learn:      ["/learn/", tag("LEARN"), "Learn Tau Language", "Type a formula and a real Tau engine answers.", "Eight short lessons, up to real testnet rules."],
  brief:      ["/learn/brief/", tag("LEARN"), "Check a brief with Tau", "Five requirements. Three cannot all hold.", "A real Tau engine finds which three."],
  taba:       ["/learn/taba/", tag("LEARN"), "Tau's math in plain words", "Five ideas under Tau Language, in plain words.", "With questions you can ask a real Tau engine."],
  facts:      ["/facts/", tag("FACTS WITH SOURCES"), "Tau today", "Facts about Tau and its testnet, each with its source.", "Your AI assistant knows old Tau. Point it here."],
  rules:      ["/rules/", LIVE, "Rules wall", "Rules people gave their own wallets. Take one for yours.", "Read from the blocks of Tau Testnet Alpha."],
  rulenums:   ["/rules/numbers/", LIVE, "Rules in numbers", "What people protect with their wallet rules.", "Read from the chain."],
  builder:    ["/builder/", tag("RULE BUILDER"), "Say it in plain words", "Tell your test wallet what it may do. See the rule before you sign.", "Every possible payment, checked by a real Tau engine."],
  guardian:   ["/guardian/", LIVE, "Guardian", "A second key for your test wallet.", "A code from your authenticator app before a payment goes out."],
  services:   ["/services/", LIVE, "Services on the testnet", "Co-signers, rule givers and apps people pay.", "Listed by the chain itself, with live numbers."],
  hearts:     ["/hearts/", LIVE, "What you love most", "Every heart on Tau HUD is a real testnet transaction.", "Which parts visitors love most, read from the chain."],
  crew:       ["/crew/", tag("ABOUT TAU HUD"), "Support Tau HUD", "Tau HUD is free. Optional support helps fund the site and the work behind it.", "Nothing in return."],
  donate:     ["/donate/", tag("ABOUT TAU HUD"), "What Tau HUD costs", "Every month's costs and every donation received.", "Each donation with its transaction."],
  roadmap:    ["/roadmap/", tag("OUR VIEW"), "Road to mainnet", "Problems we found on the testnet, each with proof and a path to a fix.", "We may be wrong: tell us."],
  cruise:     ["/cruise/", LIVE, "Cruise logbook", "Simulated passengers, real test transactions.", "What each ship sent and what the node answered."],
  load:       ["/load/", LIVE, "Testnet load", "How hard the testnet is working, minute by minute.", "Sealed, waiting, and the time to a block."],
  blog:       ["/blog/", tag("BLOG"), "Tau HUD Blog", "What we learned running things on the testnet.", "Written from our own public logbooks."],
  gxp:        ["/gxp/", tag("OUR VIEW"), "Is Tau GxP-ready?", "What an auditor would ask before a pharma company relies on Tau.", "What the public sources show today."],
};

const LOGO = `<svg viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="25" stroke="#fff" stroke-opacity=".55" stroke-width="3.5"/><path d="M13 33 H23 L27.5 24 L34.5 43 L39 33 H51" stroke="#39ff8a" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const NOTE = "Unofficial community project, not run by IDNI";
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

const CSS = `
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1200px;height:630px;overflow:hidden}
body{background:#09090a;color:#f4f5f7;font-family:Sora,sans-serif;position:relative;-webkit-font-smoothing:antialiased}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:48px 48px;background-position:-1px -1px;-webkit-mask-image:radial-gradient(ellipse 80% 90% at 80% 30%,#000 10%,transparent 75%)}
.glow{position:absolute;right:-260px;top:-260px;width:900px;height:900px;background:radial-gradient(circle,rgba(57,255,138,.12),transparent 62%)}
.top{position:absolute;left:64px;right:64px;top:50px;display:flex;align-items:center;justify-content:space-between;gap:24px}
.brand{display:flex;align-items:center;gap:16px;font-weight:700;font-size:32px;letter-spacing:-.01em;white-space:nowrap}
.brand svg{width:54px;height:54px;flex:none}
.pill{font:500 21px 'JetBrains Mono',monospace;color:#b9bdc6;border:1.5px solid rgba(255,255,255,.22);border-radius:999px;padding:9px 20px;display:flex;gap:12px;align-items:center;letter-spacing:.04em;white-space:nowrap}
.pill i{width:12px;height:12px;border-radius:50%;flex:none}
.pill.live{color:#39ff8a;border-color:rgba(57,255,138,.4);background:rgba(57,255,138,.06)}
.pill.live i{background:#39ff8a;box-shadow:0 0 14px #39ff8a}
.pill.sim{color:#ffb547;border-color:rgba(255,181,71,.42);background:rgba(255,181,71,.06)}
.pill.sim i{background:#ffb547}
h1{font-weight:700;letter-spacing:-.025em;line-height:1.04}
.g{color:#39ff8a}
.foot{position:absolute;right:64px;bottom:36px;display:flex;align-items:baseline;gap:22px;white-space:nowrap}
.url{font:600 32px 'JetBrains Mono',monospace;color:#39ff8a;letter-spacing:-.01em}
.note{font-size:18px;color:#8a8f99}
`;

const page = (body, css, [kind, pill], url) => `<!doctype html><html lang="en"><meta charset="utf-8">
<link rel="stylesheet" href="/assets/fonts/sora-jetbrainsmono.css"><style>${CSS}${css}</style>
<div class="glow"></div><div class="grid"></div>
<div class="top"><div class="brand">${LOGO}<span>Tau HUD</span></div>${pill ? `<div class="pill ${kind}">${kind ? "<i></i>" : ""}${esc(pill)}</div>` : ""}</div>
${body}
<div class="foot"><span class="note">${NOTE}</span><span class="url">${esc(url)}</span></div>`;

/* the home card: the one thing Tau Net does that other chains do not, shown on a real refusal (13 Nov 2026: a fresh
   test account wrote itself "nothing above 1,000 AGRS leaves"; its own key then signed 5,000 with IDNI's command-line
   wallet, the node refused it, 500 went through; the HUD's "Enforced against the key holder" panel has the details) */
const home = () => page(`
<h1 class="h">Your wallet. Your rules.<br><span class="g">The chain enforces them.</span></h1>
<p class="sub">Watch Tau Net live, write a money rule, learn Tau, play games on the chain. No sign-up.</p>
<div class="proof"><div class="k">Seen on the testnet · 13 Nov</div>
<div class="row"><b>§</b><span class="t r">nothing above 1,000 leaves</span></div>
<div class="row no"><b>✕</b><span class="a">5,000</span><span class="t">refused</span></div>
<div class="row ok"><b>✓</b><span class="a">500</span><span class="t">sent</span></div></div>`, `
.h{position:absolute;left:64px;top:150px;font-size:86px}
.sub{position:absolute;left:64px;top:350px;font-size:29px;width:540px;line-height:1.38;color:#b9bdc6;text-wrap:balance}
.proof{position:absolute;right:64px;top:346px;width:470px;border:1.5px solid rgba(255,255,255,.16);border-radius:18px;background:rgba(18,18,20,.92);padding:15px 22px 8px}
.k{font:500 15px 'JetBrains Mono',monospace;color:#8a8f99;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px}
.row{display:flex;align-items:center;gap:16px;font:500 23px 'JetBrains Mono',monospace;padding:6px 0;border-top:1px solid rgba(255,255,255,.08)}
.k+.row{border-top:0}
.row b{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;font-size:21px;flex:none;background:rgba(255,255,255,.09);color:#fff}
.row.ok b{background:rgba(57,255,138,.16);color:#39ff8a}
.a{width:92px;text-align:right;font-weight:700}
.t{color:#b9bdc6;font-size:22px}.t.r{color:#f4f5f7}
.no .a{text-decoration:line-through;text-decoration-thickness:2px;color:#8a8f99}`, LIVE, "tauhud.com");

/* a page card: the page's name, then why someone would open it */
const card = (key, [path, pill, title, lead, small]) => page(`
<div class="txt"><h1 class="h" data-fit="1">${esc(title)}</h1><p class="lead" data-fit="2">${esc(lead)}</p><p class="small" data-fit="2">${esc(small)}</p></div>`, `
.txt{position:absolute;left:64px;right:64px;top:118px;bottom:96px;display:flex;flex-direction:column;justify-content:center}
.h{font-size:100px;white-space:nowrap}
.lead,.small{text-wrap:balance}
.lead{font-size:46px;line-height:1.22;color:#e3e5ea;font-weight:500;letter-spacing:-.01em;margin-top:26px;max-width:1040px}
.small{font-size:28px;line-height:1.35;color:#8a8f99;margin-top:20px;max-width:980px}`, pill, "tauhud.com" + path.replace(/\/$/, "/"));

/* No Memo: its own painting (the boot screen, a terminal glowing in a ship's cabin at night) beside the words */
const nomemo = () => page(`
<div class="art"></div>
<div class="txt"><h1 class="h">No Memo</h1><p class="lead">There is no memo field.<br><span class="g">Say it in the amount.</span></p>
<p class="small">Twelve contracts from the crew of the Black Sequence, each a real testnet transaction.</p></div>`, `
.glow,.grid{display:none}
.top{z-index:2}
.art{position:absolute;inset:0;z-index:0;background:url(/nomemo/art/boot.webp) 62% 50%/auto 100% no-repeat}
.art::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#09090a 0,#09090a 30%,rgba(9,9,10,.86) 46%,rgba(9,9,10,.25) 70%,rgba(9,9,10,.1)),linear-gradient(0deg,rgba(9,9,10,.92),transparent 22%),linear-gradient(180deg,rgba(9,9,10,.8),transparent 20%)}
.txt{position:absolute;left:64px;top:160px;width:600px}
.h{font-size:104px}
.lead{font-size:42px;line-height:1.2;font-weight:600;margin-top:22px;letter-spacing:-.01em}
.small{font-size:24px;line-height:1.4;color:#b9bdc6;margin-top:22px;width:540px;text-wrap:balance}`, ["live", "A GAME ON THE LIVE TESTNET"], "tauhud.com/nomemo/");

/* in the page: shrink a [data-fit=n] element until it fits n lines without running wide; report what never fits */
const FIT = () => {
  const bad = [];
  for (const e of document.querySelectorAll("[data-fit]")) {
    const n = +e.dataset.fit, lh = () => parseFloat(getComputedStyle(e).lineHeight) || parseFloat(getComputedStyle(e).fontSize) * 1.2;
    let size = parseFloat(getComputedStyle(e).fontSize); const min = size * 0.72;
    while ((e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().height > lh() * n + 2) && size > min) { size -= 1; e.style.fontSize = size + "px"; }
    if (e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().height > lh() * n + 2) bad.push(e.textContent);
  }
  const foot = document.querySelector(".foot").getBoundingClientRect();
  for (const e of document.querySelectorAll(".txt > *,.proof,.sub")) if (e.getBoundingClientRect().bottom > foot.top - 12) bad.push("runs into the foot: " + e.textContent.slice(0, 40));
  return bad;
};

const CARDS = { hud: [home, "png"], nomemo: [nomemo, "jpg"] };
for (const [k, v] of Object.entries(PAGES)) CARDS[k] = [() => card(k, v), "png"];

const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".woff2": "font/woff2", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg" };
const server = createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.startsWith("/__card/")) { const c = CARDS[p.slice(8)]; res.writeHead(c ? 200 : 404, { "content-type": TYPES[".html"] }); return res.end(c ? c[0]() : ""); }
  try { const b = await readFile(join(ROOT, p)); res.writeHead(200, { "content-type": TYPES[extname(p)] || "application/octet-stream" }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;

const only = process.argv.slice(2);
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1, locale: "en-US" });
await ctx.route(u => !u.href.startsWith(BASE), r => r.abort("internetdisconnected"));
const tab = await ctx.newPage();
await mkdir(OUT, { recursive: true });
let failed = 0;
for (const [key, [, type]] of Object.entries(CARDS)) {
  if (only.length && !only.includes(key)) continue;
  await tab.goto(`${BASE}/__card/${key}`, { waitUntil: "load" });
  await tab.evaluate(() => document.fonts.ready);
  const bad = await tab.evaluate(FIT);
  if (bad.length) { failed++; console.error(`${key}: does not fit: ${bad.join(" | ")}`); }
  const file = join(OUT, `${key}.${type}`);
  await tab.screenshot({ path: file, type: type === "jpg" ? "jpeg" : "png", ...(type === "jpg" ? { quality: 86 } : {}) });
  if (key === "hud") await copyFile(file, join(ROOT, "og.png"));   // the site's general picture (blog, alerts) is the home card
  console.log(`assets/og/${key}.${type}`);
}
await browser.close();
server.close();
process.exit(failed ? 1 : 0);
