/* No Memo: a terminal game on Tau Testnet Alpha. The crew of the Black Sequence (the pirate ship that tests the chain
   every Tuesday, infra/relay/cruise.py TRICKS) hands out twelve contracts in three chapters. Each one is a real
   transaction from the visitor's own test wallet (the key /wallet/ and White Rabbit Key use, made in this browser): a
   payment that must land before a block height, a payment the chain must refuse for the right reason (the same answers
   the pirates expect: INVALID_SEQUENCE, TX_EXPIRED, FEE_LIMIT_TOO_LOW, INVALID_SIGNATURE, TX_INVALID, INSUFFICIENT_FUNDS,
   INVALID_PARAMS), a retractable payment taken back before its release. The name is the first rule of the ship: a Tau
   transaction carries from, to and amount, no memo. If you have something to say, say it in the amount.

   Live: the relay at node.tauhud.com (WebSocket, the same commands the wallet uses: getsequence, getbalance,
   gettxstatus, getretractables, sendtx). Simulation (tau-mode=sim, or ?mode=sim): a small practice node in this browser
   (SimNode) that answers the way the testnet does for these cases, and a practice crew purse (SimBot), so everything
   can be tried without the chain.

   The feel: the top bar is the block clock (every new block ticks), what is running shows as a slot with a bar
   (signing, sending, in the mempool, sealed), every transaction draws its way (wallet, relay, node, block), the
   trace is a glow at the screen's edge that quickens as the deadline nears, the screen types, and small synthetic
   sounds (nomemo/sfx/, drawn by infra/nomemo/synth.py; ElevenLabs versions from infra/nomemo/sfx.py win where they
   exist) carry the sea, the hull, keys, sends, refusals, seals and the ship's voice. All of it can be switched off: fx off,
   ambience off, sound off; prefers-reduced-motion is respected.

   The crew: three faces (nomemo/art/crew/<who>-<mood>.webp when the painted set is there, drawn placeholders until
   then) with moods, lines spoken aloud when the server has their clips (same clips store as the islanders',
   node.tauhud.com/rico/<key>.mp3), reactions to the testnet (GET /load) and to the Black Sequence's own call on
   Tuesdays (GET /cruise), and post: messages that arrive a block or two after something happened.

   Chapters: four contracts each. At a chapter's end the player claims the crew's share: a payment of 100 + chapter to
   the drop (the amount is the message), and the crew's purse on the server (infra/relay/nomemo.py) pays the share
   back and, once, the crew's mark. The server also keeps the players' board (wallets by standing, no names) and, when
   it is on, the Tracer: after chapter one a lookalike of the drop sends dust to the player's wallet, and the hunt is to
   tell the two apart by their whole address (GET /nomemo, /nomemo/wallet/<address>).

   The inbox: after chapter 1 the crew sends contracts of its own without end (KINDS): two to four offers, a new one
   every few blocks, lapsing after a couple of hours of blocks. Each is a puzzle about one part of the chain (TOPICS),
   answered with a real transaction the player builds in a draft (tx, set <field> <value>, send). They pay standing,
   never test AGRS; standing opens four tiers and nine ranks. why explains what the chain just did.

   Weekly ops: while the Black Sequence lies in port on Tuesday (GET /cruise), `op` opens live contracts that mirror
   what the pirates are trying that very hour. The case file (`case`) reads the hack of the week (GET /hack), the
   pirates' logbook (GET /cruise/log) and asks two riddles answered from the chain itself.

   State in localStorage (tauhud-nomemo). A trick the chain takes although it must not is kept there too (findings),
   shown to the player with the record, never posted anywhere by itself.

   Debug: ?take=<id> takes a contract on load; ?boot=1 shows the boot screen again. */
(() => {
  "use strict";
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
  const fill0 = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));   // filled, not translated: for a filler of F()
  const F = (s, v) => T(s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m)));   // filled first: the dictionaries match the numbers in place
  const $ = id => document.getElementById(id);
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const k in attrs || {}) { const v = attrs[k]; if (v == null || v === false) continue; if (k === "text") n.textContent = v; else if (k === "html") n.innerHTML = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v === true ? "" : v); }
    for (const c of kids.flat()) if (c != null && c !== false) n.append(c);
    return n;
  };
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const q = new URLSearchParams(location.search);
  const SIM = window.TauSim ? TauSim.mode() === "sim" : false;
  const B = window.TauBLS;
  const WKEY = "tauhud-wallet-key", SAVE = "tauhud-nomemo", RELAY = "https://node.tauhud.com", WS = "wss://node.tauhud.com", CLIPS = RELAY + "/rico/";
  /* the crew's dead drop: the game's wallet. Live, the server names its own (GET /nomemo "drop", a key made there, infra/relay/nomemo.py);
     until it answers, and in the simulation, this one, whose key stays with the game's keeper, never in this code */
  const BOWL = "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108";   // Agorzilla's bowl (agorzilla.com): a payment of 1 or more is a meal, one a wallet an hour
  let DROP = "9309956d5f97d1b91b409b0b2995470f5f646f2c43c3b8eb2203a42135c7caf1a9b4ff99cbdfc9ad16bd44fcea5d5065";
  const FAUCET = 100000, GIANT = 1 << 24, TRACE = 45, RACE = 6, WAYBACK_MIN = 5, SHARE = 500, CLAIM_BASE = 100;
  const short = h => (h && h.length > 14 ? h.slice(0, 6) + "…" + h.slice(-4) : h || "");
  const fmt = n => Number(n).toLocaleString("en-US");
  const now = () => Math.floor(Date.now() / 1000);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const clock = t => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  const lang = () => (window.TauI18n && TauI18n.lang !== "en" ? "?lang=" + TauI18n.lang : "");
  const txUrl = h => "/explorer/?tx=" + h + (lang() ? "&lang=" + TauI18n.lang : "");
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* one voice at a time: the ship's, the crew's, a transmission's. Each waits its turn in the order asked, with a breath
     between (2.5 s); a line that waited too long is dropped, it would come too late. run() ends when its voice has
     finished: true if it spoke, false if there was nothing to say. transmission.js uses the same line. */
  const LINE = { tail: Promise.resolve(), gap: 2500, last: -1e9 };
  function onAir(run, maxWait = 12000) {
    const asked = performance.now();
    const turn = LINE.tail.then(async () => {
      const rest = LINE.last + LINE.gap - performance.now(); if (rest > 0) await sleep(rest);
      if (performance.now() - asked > maxWait) return false;
      let spoke = false;
      try { spoke = await Promise.race([run(), sleep(60000)]); } catch (e) {}
      if (spoke) LINE.last = performance.now();
      return spoke;
    });
    LINE.tail = turn.catch(() => {});
    return turn;
  }
  /* every crew voice reaches you through the cabin's screen exactly as the ship's computer does: first what the server does
     to the ship's clips ("digital level 1" in ffmpeg: a band from 250 to 5200 Hz, about 10 bits, a 7 ms echo of the screen's
     glass), then what the ship's voice goes through here (the speaking tube: 380 to 3400 Hz, a soft drive that is
     also its limit).
     Done in the browser, so the crew's clips on the server stay as they are and no credits are spent. */
  function screenVoice(c, dest) {
    const f = (type, hz) => { const b = c.createBiquadFilter(); b.type = type; b.frequency.value = hz; b.Q.value = 0.707; return b; };
    const hp = f("highpass", 250), lp = f("lowpass", 5200);
    const crush = c.createWaveShaper(), n = 8192, cv = new Float32Array(n), mu = 255, L = 512;   // about 10 bits, finer where it is quiet
    for (let i = 0; i < n; i++) {
      const x = i / (n / 2 - 0.5) - 1, m = Math.log1p(mu * Math.min(1, Math.abs(x))) / Math.log1p(mu);
      cv[i] = Math.sign(x) * (Math.pow(1 + mu, Math.round(m * L) / L) - 1) / mu;
    }
    crush.curve = cv;
    const inG = c.createGain(); inG.gain.value = 0.8;
    const dl = c.createDelay(0.05); dl.delayTime.value = 0.007;
    const dg = c.createGain(); dg.gain.value = 0.35;
    const mix = c.createGain(); mix.gain.value = 0.5;   // 0.6 on the server; a little lower here, where the drive adds more
    const thp = f("highpass", 380), tlp = f("lowpass", 3400);
    const sh = c.createWaveShaper(), sc = new Float32Array(1024); for (let i = 0; i < 1024; i++) { const x = i / 511.5 - 1; sc[i] = Math.tanh(2.2 * x) / Math.tanh(2.2); } sh.curve = sc;
    const out = c.createGain(); out.gain.value = 0.95;
    hp.connect(lp); lp.connect(crush); crush.connect(inG); crush.connect(dl); dl.connect(dg);
    inG.connect(mix); dg.connect(mix); mix.connect(thp); thp.connect(tlp); tlp.connect(sh); sh.connect(out); out.connect(dest);
    hp.stopRing = () => {};   // nothing runs on its own any more; kept for transmission.js
    return hp;
  }
  window.NoMemoVoice = { onAir, screen: screenVoice };

  /* ---------- state ---------- */
  let S = null;
  function load() {
    try { S = JSON.parse(store.get(SAVE) || "null"); } catch (e) { S = null; }
    if (!S || !(S.v === 1 || S.v === 2)) S = { v: 2, done: {}, taken: null, deadline: null, cases: {}, findings: [], hist: [] };
    S.v = 2;
    for (const k of ["done", "cases", "ops", "riddles", "chap", "seen", "hunt"]) S[k] = S[k] || {};
    for (const k of ["findings", "hist", "mail", "inbox", "arch"]) S[k] = S[k] || [];
    for (const m of S.mail) if (!m.id) { S.mseq = (S.mseq || 0) + 1; m.id = S.mseq; }
    if (S.snd == null) S.snd = true; if (S.amb == null) S.amb = true; if (S.fx == null) S.fx = !REDUCED; if (S.voice == null) S.voice = true;
  }
  const save = () => store.set(SAVE, JSON.stringify(S));
  const rep = () => Object.keys(S.done).length + Object.keys(S.cases).length + Object.keys(S.ops).length + Object.keys(S.riddles).length + Object.keys(S.hunt).length + (S.rep || 0);
  const RANKS = [[0, "stowaway", "stowaway"], [1, "deckhand", "deckhand"], [4, "rigger", "rigger"], [8, "navigator", "navigator"], [12, "quartermaster’s mate", "master"], [20, "sailing master", "sailing"], [35, "first mate", "mate"], [55, "ghost of the ledger", "ghost"], [80, "no memo", "nomemo"]];
  const rankRow = () => { const r = rep(); let out = RANKS[0]; for (const x of RANKS) if (r >= x[0]) out = x; return out; };
  const rank = () => rankRow()[1];
  const nextRank = () => RANKS.find(x => x[0] > rep()) || null;

  /* ---------- the crew ---------- */
  const CREW = { qm: "Quartermaster", look: "Lookout", bosun: "Bosun" };
  const MOOD = { qm: "calm", look: "calm", bosun: "calm" };
  const ART = { have: null, base: "art/" };   // nomemo/art/manifest.json: what the painted set holds
  const FACES = {   // drawn placeholders: a hat, a spyglass, a pipe
    qm: '<path d="M10 26 q12 -8 24 0 M14 26 v-9 h16 v9 M12 17 h20"/><circle cx="22" cy="31" r="7"/><path d="M8 42 q14 -9 28 0"/>',
    look: '<circle cx="20" cy="22" r="8"/><path d="M26 28 l12 12 M30 25 l9 9"/><path d="M6 42 q14 -9 28 0"/>',
    bosun: '<circle cx="22" cy="21" r="9"/><path d="M28 28 l9 4 l3 -3 M8 42 q14 -9 28 0 M17 18 h10"/>',
  };
  function faces() {
    const box = $("crewBox"); if (!box) return;
    box.replaceChildren(...Object.keys(CREW).map(w => el("div", { class: "face " + MOOD[w], id: "face-" + w, title: T(CREW[w]), onclick: () => run("crew") },
      el("div", { class: "pic" }, ART.have && ART.have.crew && ART.have.crew[w] ? el("img", { src: ART.base + "crew/" + w + "-" + (ART.have.crew[w].includes(MOOD[w]) ? MOOD[w] : ART.have.crew[w][0]) + ".webp", alt: T(CREW[w]), loading: "lazy" }) : el("span", { html: '<svg viewBox="0 0 44 44">' + FACES[w] + "</svg>" })),
      el("b", { text: T(CREW[w]) }))));
  }
  function mood(who, m) { if (!CREW[who] || !m) return; MOOD[who] = m; faces(); }
  function talking(who) { const f = $("face-" + who); if (!f) return; f.classList.add("talk"); setTimeout(() => f.classList.remove("talk"), 2200); }
  async function art() {
    try { const r = await fetch(ART.base + "manifest.json", { cache: "no-cache" }); if (r.ok) ART.have = await r.json(); } catch (e) { ART.have = null; }
    faces();
    if (ART.have && ART.have.boot && ART.have.boot[0]) { const w = document.querySelector("#bootScreen .win"); if (w) w.style.backgroundImage = "url(" + ART.base + ART.have.boot[0] + ")"; }
  }
  /* the chapters: four contracts each; the next one opens when the one before is done */
  const CH = [
    { n: 1, name: "Signing on", ids: ["mark", "amount", "ghost", "dead"], text: "Four contracts to get you aboard: your mark, the ship’s one rule, a ghost, and a letter that came too late.", unlock: "peek" },
    { n: 2, name: "Dead letters", ids: ["stale", "freeride", "overspend", "giant"], text: "Four ways a payment dies before it is a payment: by height, by fee, by balance, by size.", unlock: "trace" },
    { n: 3, name: "Keys and masks", ids: ["forged", "impostor", "wayback", "race"], text: "Whose key, whose wallet, a payment with a way back, and a race against the block clock.", unlock: "hunt" },
  ];
  const chapterOf = c => CH.find(ch => ch.ids.includes(c.id));
  const chapterDone = ch => ch.ids.every(id => S.done[id]);
  const chapterOpen = ch => ch.n === 1 || chapterDone(CH[ch.n - 2]);
  const GEAR = [["jobs", "the board", true], ["case", "the case file", true], ["peek", "ask the node yourself", () => chapterDone(CH[0])], ["trace", "set your own deadline", () => chapterDone(CH[1])], ["hunt", "the Tracer", () => chapterDone(CH[2])],
    ["scan", "the mempool scanner: what waits for the next block", () => rep() >= 20], ["blocks", "the block log: what the last blocks sealed", () => rep() >= 35], ["dry", "a dry run of your draft: the node checks it without taking it", () => rep() >= 55]];
  const GEAR_AT = { scan: "sailing master", blocks: "first mate", dry: "ghost of the ledger" };
  const has = tool => { const g = GEAR.find(x => x[0] === tool); return !g || g[2] === true || g[2](); };

  /* ---------- the contracts ---------- */
  /* want: "in" (sealed in a block), "back" (taken back before its release) or the node's codes that mean the chain said
     no for the right reason (infra/relay/cruise.py TRICKS, hackweek.py). trace: blocks from taking it to its deadline.
     after: the post that arrives a block or two after the contract settled. */
  const CONTRACTS = [
    { id: "mark", name: "Make your mark", who: "qm", want: "in", trace: TRACE,
      brief: "New hand. Before you touch anything, pay the drop 1 test AGRS. Then I know your wallet, and the chain knows it too.",
      task: "Pay 1 test AGRS to the crew’s drop.",
      learn: "A Tau transaction is from, to, amount, signed. Your first payment opened your account: the testnet credits an unseen wallet 100,000 test AGRS when it first pays (the auto-faucet).",
      after: "Your mark is in the ledger. One coin, one block, one wallet I did not know before. Keep that key: to the chain, the key is you." },
    { id: "amount", name: "Say it in the amount", who: "look", want: "in", trace: TRACE,
      brief: "Rule one on this ship: no memo. There is no field for words in a Tau transaction. The number I give you is the message; pay exactly that to the drop.",
      task: "Pay the lookout’s number, and nothing else, to the drop.",
      learn: "No memo field: a payment carries from, to and amount. The amount is the only thing you said, and anyone reading the chain can read it.",
      after: "Got your number. Anyone with an explorer got it too, mind: the amount is the only word on this chain, and it is said out loud." },
    { id: "ghost", name: "The ghost", who: "qm", want: ["INVALID_SEQUENCE"], trace: TRACE,
      brief: "Pay the drop once, wait for the block, then send the very same signed payment again. The chain must throw the second one back. If it does not, we have a problem worth more than the coins.",
      task: "Send a sealed payment a second time.",
      learn: "Every payment carries a sequence number; the chain takes each number once. A copy of a sealed transaction is refused: INVALID_SEQUENCE. No replay, no double spend.",
      after: "The ghost bounced. That is the sequence number doing its one job. The pirates try the same every Tuesday with a payment they already made; the logbook keeps the score." },
    { id: "dead", name: "Dead letter", who: "look", want: ["TX_EXPIRED"], trace: TRACE,
      brief: "Sign a payment whose time ran out two minutes ago and send it anyway. The chain reads the clock in the signature, not the one on the wall.",
      task: "Send a payment whose expiry time has passed.",
      learn: "A payment carries its own expiry time, signed. Past it, the chain refuses it: TX_EXPIRED. A payment cannot be kept in a drawer and sent later.",
      after: "Dead on arrival, as it should be. A signed payment is not a cheque you can post next week; its time is inside the signature." },
    { id: "stale", name: "Stale by height", who: "look", want: ["TX_EXPIRED"], trace: TRACE,
      brief: "Same again, by blocks this time: a payment whose block-height deadline is already behind the tip.",
      task: "Send a payment whose block-height deadline has passed.",
      learn: "Beside the clock, a payment names the last block it may land in (expire_at_height). Behind the tip, it is refused: TX_EXPIRED. The block clock is the one that counts.",
      after: "Blocks, not minutes. When the testnet slows, a deadline in minutes lies and a deadline in blocks does not. That is why the trace on this terminal counts blocks." },
    { id: "freeride", name: "Free ride", who: "qm", want: ["FEE_LIMIT_TOO_LOW"], trace: TRACE,
      brief: "Try to pay the drop while allowing no fee at all. Nobody rides for free, not even on this ship.",
      task: "Send a payment with a fee limit of 0.",
      learn: "The fee is a limit you sign, not a price you are quoted: at most this much. Below the chain’s base fee the payment is refused: FEE_LIMIT_TOO_LOW.",
      after: "No free ride. Note what the chain did not do: it did not take a fee and refuse you anyway. The limit you sign is the most it may ever take." },
    { id: "overspend", name: "Overspend", who: "qm", want: ["INSUFFICIENT_FUNDS", "TX_REJECTED"], trace: TRACE,
      brief: "Pay the drop more than you have. A thousand over your balance will do.",
      task: "Pay more than the wallet holds.",
      learn: "The chain checks the balance against the amount plus the fee: INSUFFICIENT_FUNDS. The transfer rule may say no first, as TX_REJECTED; both mean the chain did its job.",
      after: "Overspend refused, and your balance untouched. The pirates send one of these every Tuesday; the day the chain takes one, the Bosun opens a file." },
    { id: "giant", name: "The giant", who: "look", want: ["TX_INVALID", "INVALID_PARAMS"], trace: TRACE,
      brief: "Pay the drop one more than a transfer can carry: two to the twenty-fourth. You do not have it; that is not the point. The point is the size of the number.",
      task: "Pay more than a transfer can carry (2^24 test AGRS).",
      learn: "A transfer amount on this testnet is 24 bits wide: 16,777,215 at most. One more and the payment is not even a payment: TX_INVALID or INVALID_PARAMS.",
      after: "Too big for the hold. 24 bits is the width of an amount here; a giant is not refused, it is not even read." },
    { id: "forged", name: "The forgery", who: "qm", want: ["INVALID_SIGNATURE"], trace: TRACE,
      brief: "Sign a payment from your wallet with a key that is not yours. Any key: the terminal makes a throwaway one. Send it and watch.",
      task: "Sign with the wrong key.",
      learn: "The signature must match the sender’s key, nothing else counts: INVALID_SIGNATURE. Whoever holds your key is you to the chain, and nobody else is.",
      after: "The forgery fell at the first check. It never reached the balance, the sequence, the fee: a wrong signature is the end of the line." },
    { id: "impostor", name: "The impostor", who: "qm", want: ["TX_INVALID"], trace: TRACE,
      brief: "Now the other way round: a payment that names the drop as the payer, signed with your key. Spend somebody else’s coins, if the chain lets you.",
      task: "Pay from another wallet with your own signature.",
      learn: "The payer named inside the transfer must be the wallet that signed it: TX_INVALID. A good signature on the wrong wallet moves nothing.",
      after: "You could not spend my coins with your key. Good. Remember it the other way round too: nobody spends yours without yours." },
    { id: "wayback", name: "The way back", who: "bosun", want: "back", trace: TRACE,
      brief: "Pay the drop 50 with the way back on: the money waits in escrow for five minutes. Before that time is up, take it back. Miss it and the drop keeps your coins.",
      task: "Send a retractable payment, then take it back before its release.",
      learn: "A retractable transfer parks the money until a release time or height; until then only the sender can take it back (retract_transfer, feeless). From the release on, the first block pays the recipient by itself. The hack of the week leans on exactly this window.",
      after: "Your fifty came home. On Thursday the hack of the week plays that window for real: a wallet pays a lookalike, notices, and takes it back. The case file will have it." },
    { id: "race", name: "Race the block", who: "look", want: "in", trace: RACE,
      brief: "Last one. A payment that may land in the next six blocks and not one later. The terminal sets the deadline the moment you take it. Go.",
      task: "Land a payment within six blocks of taking the contract.",
      learn: "expire_at_height is the trace: the chain enforces the deadline, nobody has to. A payment that missed its block is TX_EXPIRED, however fast you were.",
      after: "Made the block. Twelve of twelve: the story is told. Claim the crew’s share; the inbox keeps bringing work, harder as your rank grows, and on a Tuesday evening the ship is in for the live ops." },
  ];
  const byId = id => CONTRACTS.find(c => c.id === id);
  const num = c => CONTRACTS.indexOf(c) + 1;
  /* the pirates' tricks the live ops mirror (cruise.py TRICKS): the same answers, the same means */
  const OPS = { expired: ["dead", "a payment whose time ran out"], stale: ["stale", "a payment whose block-height deadline passed"], freeride: ["freeride", "a payment that allows no fee"],
    overspend: ["overspend", "a payment above the balance"], giant: ["giant", "an amount too wide for a transfer"], forged: ["forged", "a payment signed with another key"], impostor: ["impostor", "a payment from another wallet"], replay: ["ghost", "a sealed payment sent again"] };

  /* ---------- the node: the relay live, a practice node in the simulation ---------- */
  const CHAIN = { ws: null, wait: new Map(), ok: null, tip: null, tipAt: 0, pace: null, seq: 0, next: 0, fee: null, bal: null, follow: 0 };
  function relay() {
    return new Promise(res => {
      if (CHAIN.ws && CHAIN.ws.readyState === 1) return res(CHAIN.ws);
      let ws; try { ws = new WebSocket(WS); } catch (e) { return res(null); }
      let done = false;
      ws.onopen = () => { ws.send("hello version=1"); ws.send("via nomemo"); CHAIN.ws = ws; setTimeout(() => { done = true; res(ws); }, 150); };
      ws.onmessage = ev => { let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; } const w = CHAIN.wait.get(m.command); if (w && w.length) w.shift()(m); };
      ws.onerror = ws.onclose = () => { if (CHAIN.ws === ws) CHAIN.ws = null; if (!done) { done = true; res(null); } setState(false); };
    });
  }
  async function ask(cmd, ms = 12000) {
    if (SIM) { await sleep(120 + Math.random() * 180); return SimNode.answer(cmd); }
    const ws = await relay(); if (!ws) return null;
    return new Promise(res => {
      const c = cmd.split(" ")[0]; if (!CHAIN.wait.has(c)) CHAIN.wait.set(c, []); const w = CHAIN.wait.get(c); w.push(res);
      try { ws.send(cmd); } catch (e) { res(null); }
      setTimeout(() => { const i = w.indexOf(res); if (i >= 0) { w.splice(i, 1); res(null); } }, ms);
    });
  }
  const isOk = r => !!(r && r.status === "ok" && !(r.data && r.data.ok === false));
  const CODES = ["INSUFFICIENT_FUNDS", "TX_REJECTED", "INVALID_SEQUENCE", "TX_EXPIRED", "INVALID_SIGNATURE", "TX_INVALID", "FEE_LIMIT_TOO_LOW", "INVALID_PARAMS", "NOT_RETRACTABLE_SENDER", "FORBIDDEN", "RATE_LIMITED", "RULE_WITH_TRANSFERS", "MIXED_OUTPUT_RULE", "CLAUSE_SHAPE"];
  function codeOf(r) {   // the node's error code in a refusal, wherever the answer carries it (cruise.py code_of)
    if (!r || typeof r !== "object") return null;
    for (const d of [r.error, r.data, r]) if (d && typeof d === "object" && typeof d.code === "string") return d.code;
    const m = new RegExp("\\b(" + CODES.join("|") + ")\\b").exec(JSON.stringify(r)); return m ? m[1] : null;
  }
  const plain = r => { const e = r && (r.error || r.data || r); const s = e && typeof e === "object" ? e.message || e.error || e.reason || JSON.stringify(e) : String(e || ""); return s.length > 160 ? s.slice(0, 157) + "…" : s; };
  /* the server's side of the game (GET /nomemo, /nomemo/wallet/<address>); the practice purse in the simulation */
  async function serverInfo(path) {
    if (SIM) return SimBot.get(path);
    try { const r = await fetch(RELAY + "/nomemo" + path, { cache: "no-store" }); return r.ok ? await r.json() : null; } catch (e) { return null; }
  }

  /* the practice node: answers the way the testnet does for what the contracts send, nothing leaves the browser */
  const SimNode = (() => {
    const acc = {}, txs = {}, rets = {};
    const head = () => (window.TauSim ? TauSim.head() : Math.floor(Date.now() / 8000) % 100000);
    const a = pk => acc[pk] || (acc[pk] = { seq: 0, bal: 0 });
    const ok = (command, data) => ({ status: "ok", command, data });
    const err = (command, message, code) => ({ status: "error", command, error: { message, code } });
    const hashOf = tx => B.bytesToHex(B.sha256(new TextEncoder().encode(canon(tx))));
    function send(tx) {
      const t = now(), tip = head(), A = a(tx.sender_pubkey);
      if (!/^[0-9a-f]{96}$/.test(tx.sender_pubkey || "")) return err("sendtx", "sender_pubkey is not a key", "INVALID_PARAMS");
      let good = false; try { good = B.verify(B.hexToBytes(tx.signature), new TextEncoder().encode(canon(preimage(tx))), B.hexToBytes(tx.sender_pubkey)); } catch (e) { good = false; }
      if (!good) return err("sendtx", "signature does not verify for sender_pubkey", "INVALID_SIGNATURE");
      if (!(tx.expiration_time > t)) return err("sendtx", "transaction expired", "TX_EXPIRED");
      if (tx.expire_at_height != null && !(tx.expire_at_height > tip)) return err("sendtx", `expire_at_height ${tx.expire_at_height} is at or below the tip ${tip}`, "TX_EXPIRED");
      if (tx.sequence_number !== A.seq) return err("sendtx", `sequence ${tx.sequence_number} is not the account’s next (${A.seq})`, "INVALID_SEQUENCE");
      const fee = Number(tx.fee_limit), bal = A.bal === 0 ? FAUCET : A.bal;
      if (tx.tx_type === "user_tx") {
        const rule = tx.operations && tx.operations["0"], pays = (tx.operations && tx.operations["1"]) || [];
        if (rule != null) {   // the node's screens for a rule that writes o5, in the node's order
          const outs = [...new Set((String(rule).match(/\bo(\d+)\s*\[/g) || []).map(x => x.replace(/\D/g, "")))];
          if (outs.length > 1 && outs.includes("5")) return err("sendtx", "A rule writing o5 is registered as your policy clause and may write o5 only", "MIXED_OUTPUT_RULE");
          if (pays.length) return err("sendtx", "A policy rule (o5) and transfers cannot share one transaction", "RULE_WITH_TRANSFERS");
          if (comparisons(rule) > CLAUSE_MAX) return err("sendtx", "Shared rules: clause has " + comparisons(rule) + " comparisons; the limit is " + CLAUSE_MAX, "TX_REJECTED");
          if (!(fee >= 10)) return err("sendtx", "fee_limit below the base fee of 10", "FEE_LIMIT_TOO_LOW");
          const m = /i1\[t\]:bv\[24\]\s*>\s*\{\s*#x([0-9a-f]+)/i.exec(rule);
          A.clause = isNeutral(rule) ? null : m ? parseInt(m[1], 16) : A.clause; A.bal = bal - 10;
        }
        for (const op of pays) {
          const [from, to, amt] = op, n = Number(amt);
          if (!/^[0-9a-f]{96}$/.test(to || "")) return err("sendtx", "recipient is not a key", "INVALID_PARAMS");
          if (!(n > 0) || n >= GIANT || String(amt) !== String(Math.floor(n))) return err("sendtx", `amount ${amt} does not fit a 24-bit transfer`, "INVALID_PARAMS");
          if (from !== tx.sender_pubkey) return err("sendtx", "the transfer’s payer is not the signer", "TX_INVALID");
          if (!/^[89ab]/.test(to)) return err("sendtx", "'to' address is not a key: no point on the curve", "TX_INVALID");
          if (to === from) return err("sendtx", "'to' address is the sender", "TX_INVALID");
          if (!(fee >= 10)) return err("sendtx", "fee_limit below the base fee of 10", "FEE_LIMIT_TOO_LOW");
          if (A.clause != null && n > A.clause) return err("sendtx", `Transaction rejected: the sender's own policy clause blocked transfer #1 (${n})`, "TX_REJECTED");
          if (n + 10 > bal) return err("sendtx", `balance ${bal} is below ${n} plus the fee`, "INSUFFICIENT_FUNDS");
          A.bal = bal - n - 10; a(to).bal += n;
          SimBot.saw(tx.sender_pubkey, to, n, hashOf(tx), tip);
        }
      } else if (tx.tx_type === "retractable_transfer") {
        const n = Number(tx.amount);
        if (!(fee >= 10)) return err("sendtx", "fee_limit below the base fee of 10", "FEE_LIMIT_TOO_LOW");
        if (!(n > 0) || n >= GIANT) return err("sendtx", "amount out of range", "INVALID_PARAMS");
        if (n + 10 > bal) return err("sendtx", "insufficient funds", "INSUFFICIENT_FUNDS");
        A.bal = bal - n - 10;
        const id = hashOf(tx);
        rets[id] = { retractable_id: id, sender_pubkey: tx.sender_pubkey, recipient_pubkey: tx.recipient_pubkey, amount: n, release_at_time: tx.release_at_time, release_at_height: tx.release_at_height, status: "open" };
      } else if (tx.tx_type === "retract_transfer") {
        const r = rets[tx.retractable_id];
        if (!r) return err("sendtx", "no such retractable transfer", "TX_INVALID");
        if (r.sender_pubkey !== tx.sender_pubkey) return err("sendtx", "only the sender may retract", "NOT_RETRACTABLE_SENDER");
        if (r.status !== "open" || (r.release_at_time && r.release_at_time <= t) || (r.release_at_height && r.release_at_height <= tip)) return err("sendtx", "already released", "TX_INVALID");
        r.status = "retracted"; A.bal = (A.bal === 0 ? FAUCET : A.bal) + r.amount;
      } else return err("sendtx", "not a transaction the practice node knows", "INVALID_PARAMS");
      const h = hashOf(tx); txs[h] = { tip, tx }; A.seq += 1;
      return ok("sendtx", { ok: true, tx_hash: h });
    }
    return {
      credit(pk, n) { const A = a(pk); A.bal = (A.bal === 0 ? FAUCET : A.bal) + n; },
      answer(cmd) {
        const [c, ...args] = cmd.split(" ");
        try {
          if (c === "getsequence") return ok(c, { address: args[0], sequence_number: a(args[0]).seq, tip_height: head() });
          if (c === "getbalance") return ok(c, { address: args[0], balance: a(args[0]).bal });
          if (c === "getgovernance") return ok(c, { consensus_rules: "(o9[t]:bv[24] = {#x00000a}:bv[24])", active_validators: ["ab".repeat(48)], vote_quorum: "supermajority", approval_threshold: 1 });
          if (c === "getmempool") { const list = Object.entries(txs).filter(([, t]) => head() <= t.tip).map(([h, t]) => ({ tx_hash: h, sender: t.tx.sender_pubkey, sequence_number: t.tx.sequence_number, fee_limit: t.tx.fee_limit, status: "pending", tx_type: t.tx.tx_type })); return ok(c, { transactions: list, count: list.length }); }
          if (c === "getblocks") { const n = Math.max(1, Math.min(12, +args[0] || 5)), h = head(), blocks = []; for (let b = Math.max(0, h - n + 1); b <= h; b++) blocks.push({ header: { block_number: b }, tx_ids: Object.entries(txs).filter(([, t]) => t.tip + 1 === b).map(([x]) => x), block_hash: B.bytesToHex(B.sha256(new TextEncoder().encode("sim-block-" + b))) }); return ok(c, { blocks, total: h + 1 }); }
          if (c === "gettxstatus") { const t = txs[args[0]]; if (!t) return err(c, "unknown transaction", "NOT_FOUND"); return ok(c, head() > t.tip ? { status: "confirmed", block_number: t.tip + 1 } : { status: "pending" }); }
          if (c === "getretractables") return ok(c, { address: args[0], retractables: Object.values(rets).filter(r => r.status === "open" && (r.sender_pubkey === args[0] || r.recipient_pubkey === args[0])), mempool: [] });
          if (c === "sendtx") return send(JSON.parse(cmd.slice(7)));
          if (c === "via" || c === "hello") return ok(c, {});
        } catch (e) { return err(c, String(e.message || e), "INVALID_PARAMS"); }
        return err(c, "not allowed here", "FORBIDDEN");
      },
    };
  })();
  /* the practice purse: what the server's crew purse does live (infra/relay/nomemo.py), played here in the simulation:
     pays the share back a block after a claim, the mark once, and the Tracer's dust from a lookalike of the drop */
  const SimBot = (() => {
    const W = {};   // per wallet: claims, paid, dust
    const w = pk => W[pk] || (W[pk] = { claims: {}, dust: [] });
    const fake = seed => { let s = 0; for (const ch of seed) s = (s * 31 + ch.charCodeAt(0)) >>> 0; let out = ""; while (out.length < 96) { s = (s * 1103515245 + 12345) >>> 0; out += s.toString(16).padStart(8, "0"); } return out.slice(0, 96); };
    const shadow = () => DROP.slice(0, 6) + fake("shadow" + DROP).slice(6, 92) + DROP.slice(-4);
    return {
      saw(from, to, n, hash, tip) {
        if (to !== DROP || n <= CLAIM_BASE || n > CLAIM_BASE + CH.length) return;
        const ch = n - CLAIM_BASE, x = w(from); if (x.claims[ch]) return;
        x.claims[ch] = { hash, at: now(), block: tip + 1, paid: null };
        setTimeout(() => {
          const paid = { share: { amount: SHARE, hash: fake("share" + ch + from) } }; SimNode.credit(from, SHARE);
          if (ch === 1) { paid.mark = { amount: 1, hash: fake("mark" + from) }; SimNode.credit(from, 1); }
          x.claims[ch].paid = paid;
          if (ch === 1) setTimeout(() => { x.dust.push({ from: shadow(), amount: 1, hash: fake("dust" + from), at: now() }); SimNode.credit(from, 1); }, 9000);
        }, 9000);
      },
      get(path) {
        if (path === "") return { simulated: true, enabled: true, tracer: true, drop: DROP, share: SHARE, board: { wallets: 7 + (S.done.mark ? 1 : 0), ranks: { stowaway: 2, deckhand: 2, rigger: 1, navigator: 1, "quartermaster’s mate": 1 }, claims: [4, 2, 1], day: 3 + (S.done.mark ? 1 : 0), hour: 1 + (S.done.mark ? 1 : 0), now: Math.floor(Date.now() / 1000), last_move: Math.floor(Date.now() / 1000) - (S.done.mark ? 20 : 240), week_wallets: 4, week_top: [["3f9a21…07c4", 41], ["b80e5d…a912", 27], ["5c1177…e3d0", 12], ["e04b9a…6b25", 3]] } };
        const m = /^\/wallet\/([0-9a-f]{96})$/.exec(path); if (!m) return null;
        const x = w(m[1]); return { wallet: m[1], claims: x.claims, dust: x.dust, drop: DROP, nth: Object.keys(x.claims).length || S.done.mark ? 8 : null };
      },
    };
  })();

  /* ---------- the wallet: the visitor's test key in this browser, the same one /wallet/ and White Rabbit Key use ---------- */
  function myKey(make) {
    if (!B) return null;
    try { const k = JSON.parse(store.get(WKEY) || "null"); if (k && /^[0-9a-f]{64}$/.test(k.sk)) return { sk: B.hexToBytes(k.sk), pk: k.pk || B.bytesToHex(B.pubOf(B.hexToBytes(k.sk))) }; } catch (e) {}
    if (!make) return null;
    const skHex = B.bytesToHex(B.keygen()), pk = B.bytesToHex(B.pubOf(B.hexToBytes(skHex)));
    store.set(WKEY, JSON.stringify({ sk: skHex, pk }));
    say("sys", T("A test wallet was made for you in this browser. You find it at tauhud.com/wallet/; the key never leaves this browser."));
    return { sk: B.hexToBytes(skHex), pk };
  }
  const myPk = () => { const k = myKey(false); return k ? k.pk : null; };
  /* Python's json.dumps(sort_keys=True, separators=(",", ":")), what the node signs over */
  const canon = o => Array.isArray(o) ? "[" + o.map(canon).join(",") + "]" : o === null || typeof o !== "object" ? JSON.stringify(o === undefined ? null : o).replace(/[\u007f-￿]/g, c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")) : "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + canon(o[k])).join(",") + "}";
  const SIGNED = { user_tx: ["operations"], retractable_transfer: ["recipient_pubkey", "amount", "release_at_height", "release_at_time"], retract_transfer: ["retractable_id"] };
  function preimage(tx) {
    const d = { sender_pubkey: tx.sender_pubkey, sequence_number: tx.sequence_number, expiration_time: tx.expiration_time, fee_limit: tx.fee_limit, tx_type: tx.tx_type };
    if (tx.expire_at_height != null) d.expire_at_height = tx.expire_at_height;
    for (const k of SIGNED[tx.tx_type] || []) d[k] = k in tx ? tx[k] : null;
    return d;
  }
  /* the chain's rules are a Tau specification; the part the game reads: a stream, its bitvector width, a constant */
  const SIM_RULES = "(o9[t]:bv[24] = {#x00000a}:bv[24])";
  /* a wallet's own rule (a policy clause, IDNI tau-testnet 5ad1bb7, 13 November 2026): a user transaction whose operation
     "0" is one always ( … ). unit writing o5 (1 lets a payment through, 0 stops it). It may not share a transaction with
     transfers (RULE_WITH_TRANSFERS), may write o5 only (MIXED_OUTPUT_RULE), holds at most 32 comparisons
     (consensus/rule_offers.py MAX_CLAUSE_COMPARISONS), and the one spelling below that says o5 = 1 and nothing else takes
     the wallet's rule away (NEUTRAL_O5_CLAUSE_BODY) */
  const ALLOW_O5 = "(o5[t]:bv[24] = { #x000001 }:bv[24])", BLOCK_O5 = "(o5[t]:bv[24] = { #x000000 }:bv[24])", NEUTRAL = "always ( " + ALLOW_O5 + " ).", CLAUSE_MAX = 32;
  const hex6 = n => Math.max(0, Math.min(GIANT - 1, Math.floor(n))).toString(16).padStart(6, "0");
  function ruleText(d) {
    if (!d || !d.rule) return null;
    if (d.rule === "allow") return NEUTRAL;
    if (d.rule === "cap") return "always ( (i1[t]:bv[24] > { #x" + hex6(d.cap) + " }:bv[24]) ? " + BLOCK_O5 + " : " + ALLOW_O5 + " ).";
    if (d.rule === "mix") return "always ( ( o5[t]:bv[24] = { #x000001 }:bv[24] ) && ( o9[t]:bv[24] = { #x000000 }:bv[24] ) ).";
    if (d.rule === "size") return "always ( " + Array.from({ length: d.size }, () => "( o5[t]:bv[24] = { #x000001 }:bv[24] )").join(" && ") + " ).";
    return null;
  }
  const comparisons = t => (String(t || "").replace(/#(?![bx])[^\n]*/gi, "").match(/!=|<=|>=|(?<![-<])>|<(?!-)|=/g) || []).length;
  const isNeutral = t => String(t || "").replace(/\s+/g, "") === NEUTRAL.replace(/\s+/g, "");
  const ownRule = r => /own policy clause|user policy \(o5\)/i.test(JSON.stringify(r || ""));
  function parseRule(text) {
    const m = /\b([a-z]+)(\d+)\[t\]:bv\[(\d+)\]\s*=\s*\{\s*#x([0-9a-fA-F]+)\s*\}/.exec(String(text || ""));
    return m ? { stream: m[1] + m[2], io: m[1], num: +m[2], bits: +m[3], hex: m[4], val: parseInt(m[4], 16) } : null;
  }
  const ruleNow = () => parseRule(CHAIN.rules) || parseRule(SIM_RULES);
  const ones = n => n.toString(2).split("").filter(c => c === "1").length;
  const sign = (tx, sk) => ({ ...tx, signature: B.bytesToHex(B.sign(new TextEncoder().encode(canon(preimage(tx))), sk)) });
  async function fee() {
    if (CHAIN.fee != null) return CHAIN.fee;
    const g = await ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((g && g.data && g.data.consensus_rules) || "");
    CHAIN.rules = String((g && g.data && g.data.consensus_rules) || "") || CHAIN.rules || SIM_RULES;
    CHAIN.fee = m ? parseInt(m[1], 16) : 10; return CHAIN.fee;
  }
  /* sequence and tip from the node; the tip also feeds the block clock */
  async function envelope(pk) {
    const st = await ask("getsequence " + pk);
    if (!st || st.status !== "ok") throw new Error("node");
    const seq = Math.max(Number(st.data.sequence_number) || 0, CHAIN.next), tip = Number(st.data.tip_height) || 0;
    tick(tip); CHAIN.seq = seq;
    return { seq, tip };
  }
  /* a plain payment, with the tricks the contracts need */
  async function payment(k, to, amount, o = {}) {
    const { seq, tip } = await envelope(k.pk), f = await fee(), t = now();
    const tx = { tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: seq, expiration_time: o.expired ? t - 120 : t + 600,
      expire_at_height: o.stale ? Math.max(1, tip - 5) : (o.deadline || tip + 1000), fee_limit: o.freeride ? "0" : String(f * 5),
      operations: { "1": [[o.from || k.pk, to, String(amount)]] } };
    return sign(tx, o.signer || k.sk);
  }
  /* sends, and draws the way: wallet (signed), relay, node (answer), block (sealed, later) */
  async function sendtx(tx, way) {
    way = way || route(); way.at("wallet", true); slotStep(1);
    if (!SIM) way.at("relay", true); slotStep(2); snd.send();
    const t0 = performance.now(), r = await ask("sendtx " + JSON.stringify(tx)), ms = Math.round(performance.now() - t0);
    if (isOk(r)) { CHAIN.next = tx.sequence_number + 1; logWallet(tx, r); way.at("node", true); way.at("mempool", true); slotStep(3); } else if (r) { CHAIN.next = 0; way.at("node", false); way.say(codeOf(r) || T("refused")); } else way.at(SIM ? "node" : "relay", false);
    return { r, ms, hash: isOk(r) ? (r.data && r.data.tx_hash) || null : null, way };
  }
  function logWallet(tx, r) {   // the wallet page's own activity list, so the payment shows there too
    try {
      const lk = "tauhud-wallet-log-live-" + tx.sender_pubkey, logs = JSON.parse(store.get(lk) || "[]"), amount = tx.tx_type === "user_tx" ? (tx.operations["1"] ? tx.operations["1"][0][2] : null) : tx.amount;
      logs.unshift({ hash: r.data && r.data.tx_hash, kind: tx.tx_type === "retract_transfer" ? "retract" : "pay", label: "No Memo" + (amount != null ? ": " + amount : tx.operations && tx.operations["0"] ? ": rule" : ""), at: Date.now(), status: "queued", seq: tx.sequence_number, paid: tx.fee_limit !== "0" });
      if (!SIM) store.set(lk, JSON.stringify(logs.slice(0, 40)));
    } catch (e) {}
  }
  /* waits for the block: gettxstatus until it is in, refused, or the deadline has passed */
  async function sealed(hash, deadline, way) {
    for (let i = 0; i < 90; i++) {
      await sleep(i < 3 ? 2500 : 5000);
      const m = await ask("gettxstatus " + hash, 8000);
      if (m && m.status === "ok") {
        const d = m.data || {}, st = String(d.status || d.state || "").toLowerCase();
        if (d.block_number != null || /confirmed|included|mined|sealed|applied/.test(st)) { if (way) { way.at("block", true); way.say("#" + fmt(d.block_number ?? d.height ?? "")); } slotStep(4); return { in: true, block: d.block_number ?? d.height ?? null }; }
        if (/reject|fail|dropped|expired|invalid/.test(st)) { if (way) way.at("block", false); return { in: false, why: d.reason || d.error || st }; }
      }
      if (i % 2 === 1) { const k = myPk(); if (k) await envelope(k).catch(() => {}); }
      if (deadline && CHAIN.tip != null && CHAIN.tip > deadline + 2) { if (way) way.at("block", false); return { in: false, why: "TX_EXPIRED" }; }
    }
    if (way) way.at("block", false);
    return { in: false, why: "no answer in time" };
  }

  /* ---------- the block clock ---------- */
  function tick(tip) {
    const t = Date.now();
    if (CHAIN.tip != null && tip > CHAIN.tip && CHAIN.tipAt) { const p = (t - CHAIN.tipAt) / 1000 / (tip - CHAIN.tip); CHAIN.pace = CHAIN.pace ? CHAIN.pace * 0.6 + p * 0.4 : p; }
    const newBlock = CHAIN.tip != null && tip > CHAIN.tip;
    if (CHAIN.tip == null || tip !== CHAIN.tip) { CHAIN.tip = tip; CHAIN.tipAt = t; }
    setState(true); instruments(); topbar(newBlock);
    if (newBlock) { if (S.taken || S.job) { snd.block(); snd.tick(traceFrac() < 0.25); } else snd.tension(false); deliverMail(); }
    if (S.taken && S.deadline != null && tip > S.deadline && !RUN.busy) traced();
    if (S.job && S.deadline != null && tip > S.deadline && !RUN.busy) jobTraced();
    jobTick(tip);
  }
  const pace = () => (SIM && window.TauSim ? TauSim.pace : CHAIN.pace);
  const inTimeE = blocks => { const s = pace(); if (!s || blocks < 0) return ""; const m = blocks * s / 60; return m < 1 ? "under a minute" : "about " + Math.round(m) + " min"; };   // English: a filler of F(), translated with the line
  const inTime = blocks => { const s = pace(); if (!s || blocks < 0) return ""; const m = blocks * s / 60; return m < 1 ? T("under a minute") : F("about {m} min", { m: Math.round(m) }); };
  const traceLeft = () => ((S.taken || S.job) && S.deadline != null && CHAIN.tip != null ? S.deadline - CHAIN.tip : null);
  const traceFrac = () => { const left = traceLeft(), c = cur(); const span = c ? (S.span || c.trace) : TRACE; return left == null ? 0 : Math.max(0, Math.min(1, left / span)); };
  let poll = 0;
  function watch() {
    clearTimeout(poll);
    const go = async () => {
      if (!document.hidden) { const k = myPk(); if (k) await envelope(k).catch(() => setState(false)); else { const st = await ask("getsequence " + DROP); if (st && st.status === "ok") tick(Number(st.data.tip_height) || 0); else setState(false); } }
      poll = setTimeout(go, S.taken ? 6000 : 15000);
    };
    poll = setTimeout(go, 300);
  }
  function setState(ok) {
    if (CHAIN.ok === ok) return; CHAIN.ok = ok;
    const s = $("state"), t = $("stateText"); if (!s) return;
    s.className = "state " + (SIM ? "sim" : ok ? "live" : "off");
    t.textContent = SIM ? T("Simulation") : ok ? T("Live node") : T("Node out of reach");
    instruments();
  }

  /* ---------- sounds: the ship around you (sfx/, drawn by infra/nomemo/synth.py; ElevenLabs versions from
     infra/nomemo/sfx.py on the server win where they exist). Until a file has loaded, a small tone made here stands in.
     sound off silences all of it; ambience off only the sea, the hull and the hum; voice off the ship's voice. ---------- */
  const snd = (() => {
    let ctx = null, master = null, bed = null, voiceBus = null, lastKey = 0, creakT = 0, tens = null, lastCreak = 0;
    const LOCAL = "sfx/", SERVER = CLIPS + "nomemo-sfx/", buf = {}, wait = {}, layers = {};
    let meta = null, server = { sounds: [], voice: [] }, metaP = null;
    const on = () => S && S.snd && !q.get("quiet");
    const ambOn = () => on() && S.amb !== false;
    const ac = () => {
      if (!on()) return null;
      try {
        if (!ctx) {
          ctx = new (window.AudioContext || window.webkitAudioContext)();
          const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 4;
          master = ctx.createGain(); master.gain.value = 0.85; master.connect(comp).connect(ctx.destination);
          bed = ctx.createGain(); bed.gain.value = 0.7; bed.connect(master);
          // the ship's voice comes through the speaking tube: a narrow band, a little grit
          const hp = ctx.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 380;
          const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 3400;
          const sh = ctx.createWaveShaper(), cv = new Float32Array(1024); for (let i = 0; i < 1024; i++) { const x = i / 511.5 - 1; cv[i] = Math.tanh(2.2 * x) / Math.tanh(2.2); } sh.curve = cv;
          voiceBus = ctx.createGain(); voiceBus.gain.value = 0.95; voiceBus.connect(hp); hp.connect(lp); lp.connect(sh); sh.connect(master);
        }
        if (ctx.state === "suspended") ctx.resume();
        return ctx;
      } catch (e) { return null; }
    };
    function info() {
      if (metaP) return metaP;
      metaP = (async () => {
        try { const r = await fetch(LOCAL + "list.json"); const j = await r.json(); meta = {}; for (const s of j.sounds) meta[s.name] = s; } catch (e) { meta = {}; }
        try { const r = await fetch(SERVER + "index.json", { cache: "no-cache" }); if (r.ok) { const j = await r.json(); server = { sounds: j.sounds || [], voice: j.voice || [] }; } } catch (e) {}
      })();
      return metaP;
    }
    const decode = ab => new Promise((ok, no) => { const p = ctx.decodeAudioData(ab, ok, no); if (p && p.then) p.then(ok, no); });
    function load(name) {
      if (buf[name] || wait[name] || !ac()) return wait[name] || Promise.resolve(buf[name]);
      wait[name] = (async () => {
        await info();
        const urls = (server.sounds.includes(name) || server.voice.includes(name) ? [SERVER] : []).concat(name.startsWith("v-") ? [] : [LOCAL]);
        for (const u of urls) { try { const r = await fetch(u + name + ".mp3"); if (!r.ok) continue; buf[name] = await decode(await r.arrayBuffer()); return buf[name]; } catch (e) {} }
        return null;
      })();
      return wait[name];
    }
    const gainOf = name => (meta && meta[name] && meta[name].gain) || 0.5;
    function play(name, o = {}) {
      const c = ac(); if (!c) return true;   // silence asked for: nothing stands in either
      const b = buf[name]; if (!b) { load(name); return false; }
      const src = c.createBufferSource(), g = c.createGain(); src.buffer = b;
      if (o.rate) src.playbackRate.value = o.rate;
      g.gain.value = gainOf(name) * (o.gain == null ? 1 : o.gain);
      let out = g;
      if (o.pan && c.createStereoPanner) { const p = c.createStereoPanner(); p.pan.value = o.pan; g.connect(p); out = p; }
      src.connect(g); out.connect(o.bus || master);
      src.start(c.currentTime + (o.delay || 0));
      return true;
    }
    function duck(sec = 1.6) { if (!bed) return; const t = ctx.currentTime; bed.gain.cancelScheduledValues(t); bed.gain.setValueAtTime(bed.gain.value, t); bed.gain.linearRampToValueAtTime(0.35, t + 0.08); bed.gain.linearRampToValueAtTime(0.7, t + sec); }
    // a loop played from where its sound starts to where it ends, so an MP3's silent padding does not tick at the seam
    function layer(name, gain = 1) {
      const c = ac(), b = buf[name]; if (!c || !b || layers[name]) return layers[name];
      const d = b.getChannelData(0); let a = 0, z = d.length - 1; while (a < d.length && Math.abs(d[a]) < 2e-4) a++; while (z > a && Math.abs(d[z]) < 2e-4) z--;
      const src = c.createBufferSource(), g = c.createGain(); src.buffer = b; src.loop = true; src.loopStart = a / b.sampleRate; src.loopEnd = (z + 1) / b.sampleRate;
      g.gain.setValueAtTime(0.0001, c.currentTime); g.gain.exponentialRampToValueAtTime(gainOf(name) * gain, c.currentTime + 2.5);
      src.connect(g).connect(bed); src.start(c.currentTime, src.loopStart);
      return (layers[name] = { src, g });
    }
    function stopLayer(name, sec = 1.5) { const l = layers[name]; if (!l) return; delete layers[name]; const t = ctx.currentTime; l.g.gain.cancelScheduledValues(t); l.g.gain.setValueAtTime(Math.max(0.0001, l.g.gain.value), t); l.g.gain.exponentialRampToValueAtTime(0.0001, t + sec); l.src.stop(t + sec + 0.05); }
    function creak() {
      clearTimeout(creakT);
      creakT = setTimeout(() => {
        if (ambOn() && !document.hidden) { let n; do n = 1 + Math.floor(Math.random() * 3); while (n === lastCreak); lastCreak = n; if (play("creak-" + n, { bus: bed, gain: 0.6 + Math.random() * 0.4, rate: 0.85 + Math.random() * 0.25, pan: Math.random() * 1.2 - 0.6 })) {} }
        if (ambOn()) creak();
      }, 9000 + Math.random() * 17000);
    }
    async function ambience() {
      if (!ambOn()) { for (const k of Object.keys(layers)) stopLayer(k); clearTimeout(creakT); return; }
      if (!ac()) return;
      await Promise.all(["amb-sea", "amb-hum", "creak-1", "creak-2", "creak-3"].map(load));
      if (!ambOn()) return;
      layer("amb-sea"); layer("amb-hum"); creak();
      if (tens) layer("amb-tension");
    }
    let woke = false;
    function wake() {
      if (!ac()) return null;
      if (!woke) { woke = true; info().then(() => { for (const n of Object.keys(meta || {})) if (!n.startsWith("amb-")) load(n); }); }
      ambience();
      return ctx;
    }
    document.addEventListener("visibilitychange", () => { if (!ctx) return; if (document.hidden) ctx.suspend(); else if (on()) { ctx.resume(); ambience(); } });
    // the small tones that stood in before (and still do until a file has loaded)
    function tone(f, ms, type = "square", gain = 0.05, slide = 0) {
      const c = ac(); if (!c) return;
      const o = c.createOscillator(), g = c.createGain(), t = c.currentTime;
      o.type = type; o.frequency.setValueAtTime(f, t); if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, f + slide), t + ms / 1000);
      g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
      o.connect(g).connect(master); o.start(t); o.stop(t + ms / 1000 + 0.02);
    }
    const ok = () => { tone(660, 90, "triangle", 0.05); setTimeout(() => tone(990, 140, "triangle", 0.05), 90); };
    const no = () => tone(140, 180, "sawtooth", 0.05, -60);
    const cue = (name, fallback, o) => { if (!play(name, o) && fallback) fallback(); };
    const event = (name, fallback) => { duck(); cue(name, fallback); };
    function say(name) {   // the ship's voice: fixed lines the server made, only when they exist and voice is on
      if (!on() || !S.voice || !server.voice.includes(name)) return;
      onAir(async () => {   // after any voice still speaking, never over it
        const b = buf[name] || await load(name); if (!b || !on() || !S.voice) return false;
        duck(b.duration + 0.8); if (!play(name, { bus: voiceBus, delay: 0.2, gain: 1 })) return false;
        await sleep(b.duration * 1000 + 250); return true;
      }, 8000);
    }
    async function crew(url, who) {   // a crew clip through the cabin's screen; ends when it has been said (transmission.js moves the face with it)
      const c = ac(); if (!c) return false;
      let b = null;
      try { const r = await fetch(url); if (!r.ok) return false; b = await decode(await r.arrayBuffer()); } catch (e) { return false; }
      if (!on() || !S.voice) return false;
      duck(b.duration + 0.8);
      const src = c.createBufferSource(); src.buffer = b; const inp = screenVoice(c, master); src.connect(inp);
      const at = c.currentTime + 0.05;
      document.dispatchEvent(new CustomEvent("nomemo:crewvoice", { detail: { who, buffer: b, at, ctx: c } }));
      await new Promise(r => { src.onended = r; src.start(at); });
      document.dispatchEvent(new CustomEvent("nomemo:crewvoice", { detail: { who, end: true } }));
      inp.stopRing(); return true;
    }
    info();
    return {
      wake, ambience, say, crew,
      key: () => { let n; do n = 1 + Math.floor(Math.random() * 4); while (n === lastKey); lastKey = n; cue("key-" + n, () => tone(1800 + Math.random() * 400, 18, "square", 0.012), { rate: 0.94 + Math.random() * 0.12 }); },
      enter: () => cue("enter", null),
      send: () => cue("send", () => { tone(520, 70, "square", 0.03, 400); setTimeout(() => tone(900, 60, "square", 0.025, 500), 70); }),
      ok: () => cue("accepted", ok),
      no: () => cue("refused", no),
      block: () => cue("block", () => tone(1000, 30, "square", 0.015)),
      tick: hot => { if (hot) cue("tick", () => tone(1400, 40, "square", 0.03)); snd.tension(!!hot); },
      tension: hot => { if (hot === !!tens) return; tens = hot || null; if (!ctx) return; if (hot) { if (ambOn()) load("amb-tension").then(() => { if (tens && ambOn()) layer("amb-tension"); }); } else stopLayer("amb-tension", 3); },
      out: () => { snd.tension(false); event("out", () => { tone(200, 300, "sawtooth", 0.06, -120); setTimeout(() => tone(160, 350, "sawtooth", 0.05, -100), 220); }); say("v-out"); },
      mail: () => event("mail", () => { tone(1200, 60, "triangle", 0.04); setTimeout(() => tone(1600, 90, "triangle", 0.04), 80); }),
      boot: () => event("boot", () => { tone(80, 900, "sawtooth", 0.03, 300); setTimeout(() => tone(440, 120, "triangle", 0.04), 900); }),
      seal: () => event("seal", ok),
      paid: () => event("paid", ok),
      mark: () => event("mark", ok),
      dust: () => event("dust", () => { tone(1200, 60, "triangle", 0.04); setTimeout(() => tone(1600, 90, "triangle", 0.04), 80); }),
      hunt: () => event("hunt", ok),
      chapter: () => event("chapter", ok),
      board: () => cue("board", null),
    };
  })();

  /* ---------- the screen: it types ---------- */
  const screen = () => $("screen");
  const Q = []; let typing = false;
  const scrollDown = () => { const w = $("screenWrap"); if (w) w.scrollTop = w.scrollHeight; };
  async function pump() {
    if (typing) return; typing = true;
    while (Q.length) {
      const p = Q.shift(); if (!p.isConnected) continue;
      const nodes = [...p.childNodes].map(n => [n, n.nodeType === 3 ? n.nodeValue : null]);
      for (const [n, text] of nodes) if (text != null) n.nodeValue = "";
      p.hidden = false; p.classList.add("typing"); p.setAttribute("translate", "no"); scrollDown();   // half-typed words are not words: the translation layer waits for the line
      const total = nodes.reduce((a, [, t]) => a + (t ? t.length : 0), 0), perChar = Math.min(14, Math.max(2, 520 / Math.max(1, total)));
      for (const [n, text] of nodes) {
        if (text == null) continue;
        for (let i = 1; i <= text.length; i += perChar < 4 ? 3 : 1) { n.nodeValue = text.slice(0, i); await sleep(perChar); }
        n.nodeValue = text;
      }
      p.classList.remove("typing"); p.removeAttribute("translate");
      for (const [n, text] of nodes) if (text != null) { n.nodeValue = ""; n.nodeValue = text; }   // the whole line, seen once by the translation layer
      scrollDown();
    }
    typing = false;
  }
  function say(kind, text, ...more) {
    const p = el("p", { class: kind }); if (text != null) p.append(typeof text === "string" ? document.createTextNode(text) : text); for (const m of more) if (m != null) p.append(" ", m);
    screen().append(p);
    if (S.fx && !REDUCED && typeof text === "string" && text.length < 700) { p.hidden = true; Q.push(p); pump(); } else scrollDown();
    return p;
  }
  function crew(who, text, m) { if (m) mood(who, m); talking(who); document.dispatchEvent(new CustomEvent("nomemo:crewline", { detail: { who, mood: MOOD[who], text: T(text), voice: !SIM && !!(S.voice && S.snd) } })); heard(who, speak(who, text)); return say("crew", null, el("b", { text: T(CREW[who]) + ":" }), " " + T(text)); }
  function transmit(who, text, job, m) {   // a contract's brief: the sender appears and reads it out (transmission.js); without that file, the plain crew line
    const ev = new CustomEvent("nomemo:transmission", { cancelable: true, detail: { who, mood: m || "calm", text, shown: T(text), from: T(CREW[who]), job: job || null, voice: !!(S.voice && S.snd), sim: SIM } });
    if (document.dispatchEvent(ev)) return crew(who, text, m || "calm");
    mood(who, m || "calm"); talking(who); return say("crew", null, el("b", { text: T(CREW[who]) + ":" }), " " + T(text));
  }
  const link = (href, text) => el("a", { href, target: "_blank", rel: "noopener", text });
  const code = t => el("code", { text: t });
  const cols = pairs => { const d = el("div", { class: "cols" }); for (const [a, b] of pairs) d.append(typeof a === "string" ? el("span", { text: a }) : a, typeof b === "string" ? el("span", { text: b }) : b); return say("sys", d); };
  const btn = (text, cmd) => el("button", { type: "button", class: "abc", text, onclick: () => run(cmd) });
  function cmdLine(s) { say("you", s); }
  function clearScreen() { Q.length = 0; screen().replaceChildren(); }
  function flash(kind) { const t = document.querySelector(".term"); if (!t || !S.fx || REDUCED) return; t.classList.remove("flash-bad", "flash-ok"); void t.offsetWidth; t.classList.add("flash-" + kind); setTimeout(() => t.classList.remove("flash-" + kind), 600); }
  /* a transaction's way: wallet, relay, node, mempool, block; each lights as it is passed, or goes red where it ends */
  function route() {
    const STOPS = SIM ? ["wallet", "node", "mempool", "block"] : ["wallet", "relay", "node", "mempool", "block"], parts = {};
    const d = el("div", { class: "route" });
    STOPS.forEach((s, i) => { if (i) d.append(el("em", { text: "──▶" })); parts[s] = el("span", { text: T(s === "relay" ? "relay node.tauhud.com" : s) }); d.append(parts[s]); });
    const note = el("em", { class: "note" }); d.append(note);
    say("sys", d);
    return { at(s, ok) { const p = parts[s]; if (!p) return; p.classList.add(ok ? "on" : "bad"); if (ok) { const e = p.previousSibling; if (e && e.tagName === "EM") e.classList.add("on"); } }, say(t) { note.textContent = " " + t; } };
  }

  /* ---------- the top bar: the block clock, what runs, the post, the trace ---------- */
  const SLOT = { el: null, timer: 0 };
  function slot(name) {
    const box = $("slots"); if (!box) return;
    clearTimeout(SLOT.timer);
    SLOT.el = el("div", { class: "slot" }, el("span", { text: name }), el("i"), el("small", { text: T("signing") })); SLOT.el.style.setProperty("--p", "10%");
    box.replaceChildren(SLOT.el);
  }
  function slotStep(k) {   // 1 signed, 2 sent, 3 in the mempool, 4 sealed
    const s = SLOT.el; if (!s) return;
    const words = ["", T("signed"), T("sent"), T("in the mempool, waiting for a block"), T("sealed")];
    s.style.setProperty("--p", [10, 30, 55, 80, 100][k] + "%"); s.querySelector("small").textContent = words[k];
    if (k === 4) { s.classList.add("ok"); slotEnd(); }
  }
  function slotFail(what) { const s = SLOT.el; if (!s) return; s.classList.add("bad"); s.querySelector("small").textContent = what; slotEnd(); }
  function slotEnd() { clearTimeout(SLOT.timer); SLOT.timer = setTimeout(() => { if (SLOT.el) SLOT.el.remove(); SLOT.el = null; }, 7000); }
  function topbar(newBlock) {
    const b = $("topBlock"); if (!b) return;
    b.textContent = CHAIN.tip != null ? "#" + fmt(CHAIN.tip) : "—";
    if (newBlock && S.fx && !REDUCED) { b.classList.remove("tick"); void b.offsetWidth; b.classList.add("tick"); }
    $("topPace").textContent = pace() ? F("{n} s a block", { n: pace().toFixed(0) }) : "";
    const left = traceLeft(), frac = traceFrac(), tr = $("topTrace"), c = cur();
    tr.className = "tr" + (c ? (left != null && left < 0 ? " out" : frac < 0.25 ? " hot" : " on") : "");
    tr.style.setProperty("--p", Math.round(frac * 100) + "%");
    $("topTraceText").textContent = c ? (left != null ? F("trace {n} blocks", { n: Math.max(0, left) }) : T("trace …")) : T("no trace");
    const h = document.documentElement; h.classList.toggle("tr-on", !!c && frac >= 0.25); h.classList.toggle("tr-hot", !!c && frac < 0.25 && !(left != null && left < 0));
    const unread = S.mail.filter(m => !m.read && m.due <= (CHAIN.tip ?? 0)).length;
    const mb = $("mailBtn"); mb.textContent = unread ? F("post {n}", { n: unread }) : T("post"); mb.classList.toggle("has", unread > 0);
    $("sndBtn").textContent = S.snd ? "♪" : "♪̸"; $("sndBtn").title = T(S.snd ? "sound on (click: off)" : "sound off (click: on)"); $("rebootBtn").title = T("reboot: the terminal starts again and dials the node");
  }

  /* ---------- the post: real mail. Each letter has a sender, a subject and a body; some bring a special order (a contract
     of the inbox that pays more), some point at a command. Letters come after a contract settles, when the rank grows,
     when something new happens to you, and on the ship's days (Tuesday ops, the case file on Thursday). ---------- */
  const subOf = m => (Array.isArray(m.sub) ? m.sub : [m.sub || "A word from the crew"]).map(x => T(x)).join(" ").replace(/([：。]) /g, "$1");
  function post(who, text, blocks, m, o) {
    S.mseq = (S.mseq || 0) + 1;
    const x = { id: S.mseq, who, text, m, at: Date.now(), due: (CHAIN.tip ?? 0) + (blocks == null ? 1 : blocks), read: false, ...(o || {}) };
    S.mail.unshift(x); S.mail = S.mail.slice(0, 60); save(); topbar();
    if (blocks === 0) deliverMail();
    return x;
  }
  const mailOf = a => { const n = parseInt(String(a || "").replace(/^m/, ""), 10); return S.mail.find(x => x.id === n) || null; };
  const mailHave = () => S.mail.filter(m => m.due <= (CHAIN.tip ?? 0));
  /* the letters: each comes once, when its moment has come */
  const LETTERS = [
    { key: "mark", who: "qm", when: () => !!S.done.mark, sub: "Your mark is on the chain",
      text: "Your first payment sits in a block now, and nobody can take it out again. Every node that follows the chain keeps the same list of payments; that agreement is what this testnet tests. history shows the block yours landed in.", act: "history" },
    { key: "coins", who: "look", when: () => !!S.done.mark && CHAIN.bal != null && CHAIN.bal > 0, sub: "Where your coins came from",
      text: "Your wallet held 100,000 test AGRS before anyone paid you a thing. The testnet credits a wallet it has never seen when that wallet first pays. Anyone can get them, which is why test AGRS are worth nothing, and why you can spend them on mistakes.", act: "status" },
    { key: "inbox", who: "qm", when: () => !!S.inboxHi, sub: "Work of our own",
      text: "The inbox is the crew’s own work, and it does not run out. Each offer is a puzzle about how the chain decides. Read one, accept it, change the draft with set, send it. A word you do not know: what <word>. Declining costs nothing.", act: "inbox" },
    { key: "miss", who: "bosun", when: () => S.arch.some(a => a.out === "missed"), sub: "Read the answer",
      text: "When the node says no, it says why: a code such as FEE_LIMIT_TOO_LOW or INVALID_SEQUENCE. That code is the whole lesson. why explains the last topic; archive keeps what you sent and what came back.", act: "archive" },
    { key: "clock", who: "look", when: () => S.arch.some(a => a.out === "lapsed" || a.out === "traced"), sub: "The trace counts blocks",
      text: "A lost contract costs little. The trace bar at the top counts blocks, not minutes: when the chain is quick, so is the trace. Take the next one and send early; a draft can be changed and sent again.", act: "inbox" },
    { key: "tau", who: "qm", when: () => S.arch.some(a => a.out === "settled" && ["p-fee", "p-bits", "p-stream", "r-fee9", "p-tight"].includes(a.k)), sub: "The rules are written in Tau",
      text: "You read the chain’s rule to pay that one. The rule is a line of Tau Language, the same language anyone can write in the tau program at home. rule takes it apart word by word; the Learn page shows how to start the REPL.", act: "rule" },
    { key: "repl", who: "look", when: () => !!(S.letters && S.letters.tau) && rep() >= 20, sub: "Your own REPL",
      text: "Install tau, start it, and type sat x = 0. at the tau> prompt. Then help examples. Everything the chain decides, it decides by rules written that way; one day you write one. what top explains the first trap.", act: "what top" },
    { key: "seq", who: "bosun", when: () => rep() >= 4, sub: ["Special order:", "Yesterday’s number"], offer: "r-seq",
      text: "Every wallet counts its own payments: the sequence number. A payment that uses a number again is refused, so the same payment cannot be played twice. Show me that refusal. This order pays two points more than the inbox." },
    { key: "fee", who: "qm", when: () => rep() >= 8, sub: ["Special order:", "Read the rules"], offer: "p-fee",
      text: "The base fee is not written in this terminal. It is in the chain’s own rules, and anyone can read them: peek getgovernance. On Tau the rules can change when the validators agree, so read them fresh each time. Two points more than the inbox." },
    { key: "order", who: "bosun", when: () => rep() >= 12, sub: ["Special order:", "Two faults"], offer: "predict",
      text: "A payment can be wrong in two ways and the node names only one: the first check it fails. Learn the order of the checks and you know the answer before you send. Say it with predict. Two points more than the inbox." },
    { key: "blind", who: "bosun", when: () => rep() >= 35, sub: ["Special order:", "Blind order"], offer: "r-blind",
      text: "From here on I name the answer and you find the payment, without hints. Every code you have seen is a rule the chain keeps; now make it show one on demand. Two points more than the inbox." },
    { key: "top", who: "qm", when: () => rep() >= 80, sub: "No memo",
      text: "You read the chain the way the chain reads itself: from, to, amount, signed, and the rules around them. That is the rank the ship is named for. Every refusal you caused was the chain doing its job, and every one tested it. Thank you for that." },
  ];
  function letters() {
    if (!S.booted) return;
    S.letters = S.letters || {};
    for (const L of LETTERS) if (!S.letters[L.key] && L.when()) {
      if (L.offer) { const kd = KINDS.find(x => x.k === L.offer); if (!kd || kd.t > tierMax()) continue; }
      S.letters[L.key] = true; post(L.who, L.text, 1, null, { sub: L.sub, offer: L.offer || null, act: L.act || null, key: L.key });
    }
    if (inboxOpen() && !S.letters["wk-" + weekNo()]) { const th = theme(); S.letters["wk-" + weekNo()] = true; post(th.who, th.text, 1, null, { sub: th.name, act: "week" }); }
    /* the ship's days, by German time: Tuesday's op while the ship is in, Thursday's case file */
    const d = new Date(), day = d.toLocaleDateString("en-CA", { timeZone: "Europe/Berlin" }), wd = d.toLocaleDateString("en-GB", { timeZone: "Europe/Berlin", weekday: "short" }), hr = +d.toLocaleString("en-GB", { timeZone: "Europe/Berlin", hour: "2-digit", hourCycle: "h23" });
    if (Object.keys(S.done).length && !SIM && shipIn() && !S.letters["op-" + day]) { S.letters["op-" + day] = true; post("bosun", "The Black Sequence lies off White Rabbit Key tonight. While she is in, op opens live contracts: the same tricks the pirates try on the chain, for you to play with them. About two hours, then she sails.", 0, null, { sub: "The ship is in", act: "op" }); }
    if (Object.keys(S.done).length && wd === "Thu" && hr >= 12 && !S.letters["case-" + day]) { S.letters["case-" + day] = true; post("look", "Thursday is case day. The case file collects what the pirates tried at the island on Tuesday and the hack of the week, with riddles only the chain can answer.", 0, null, { sub: "This week’s case file", act: "case" }); }
  }
  function deliverMail() {
    letters();
    const due = S.mail.filter(x => !x.told && x.due <= (CHAIN.tip ?? 0)); if (!due.length) return;
    for (const x of due) x.told = true; save(); topbar(); chips(); snd.mail();
    const x = due[0];
    say("sys", (F("New mail from the {x}:", { x: CREW[x.who] }) + " " + subOf(x)).replace(/： /g, "：") + (due.length > 1 ? " " + F("(+{n} more)", { n: due.length - 1 }) : ""), btn(T("read"), "mail " + x.id));
  }
  /* a special order from a letter: a contract of the inbox, made now, that pays two points more */
  function takeOffer(m) {
    if (!m || !m.offer) { say("sys", T("That letter brings no order.")); return; }
    if (m.took) { const j = jobOf(m.took); if (j) return readJob(jname(j)); say("sys", T("That order is taken already; it is in the archive.")); return; }
    if (!inboxOpen()) { say("sys", T("The inbox opens when chapter 1 is done: four contracts, then the crew sends work of its own, without end.")); return; }
    const kd = KINDS.find(x => x.k === m.offer); if (!kd) return;
    S.jseq = (S.jseq || 0) + 1;
    const j = { n: S.jseq, k: kd.k, t: kd.t, who: m.who, topic: kd.topic, born: CHAIN.tip ?? 0, until: (CHAIN.tip ?? 0) + 300, special: 2 };
    j.trace = { 1: 40, 2: 30, 3: 24, 4: 16 }[j.t] + 10;
    if (kd.mk) kd.mk(j);
    S.inbox.unshift(j); m.took = j.n; save(); jobs(); instruments(); chips();
    say("ok", F("Special order {x} is in the inbox, +{n}:", { x: jname(j), n: PAYS[j.t] + 2 }) + " " + T(kd.name));
    readJob(jname(j));
  }
  function mailBtns(m) {
    const b = [];
    if (m.offer) b.push(m.took ? btn(T("open the order"), "accept m" + m.id) : btn(T("accept the order"), "accept m" + m.id));
    if (m.act) b.push(btn(m.act, m.act));
    return b;
  }
  function mailRead(a) {
    const m = mailOf(a); if (!m || m.due > (CHAIN.tip ?? 0)) { say("sys", T("No such letter. mail lists them.")); return; }
    say("sys", F("m{n} · from the {x}", { n: m.id, x: CREW[m.who] }) + " · " + subOf(m));
    say("crew", null, el("b", { text: T(CREW[m.who]) + ":" }), " " + T(m.text));
    const b = mailBtns(m); if (b.length) say("sys", T("This letter:"), ...b);
    m.read = true; save(); topbar(); chips();
    /* a letter never ends the way on: the newest button after it is the game's next step, not "read" again (9 of 9 tappers looped here, 9.11) */
    if (NEXTGO && NEXTGO[1] !== "mail") say("sys", T("Next:"), btn(NEXTGO[0], NEXTGO[1]));
  }
  function mailList() {
    const have = mailHave();
    if (!have.length) { say("sys", T("Nothing yet. The crew writes after a contract settles, and when something happens on the chain.")); return; }
    say("sys", F("Post: {n} letters, {m} unread.", { n: have.length, m: have.filter(m => !m.read).length }));
    cols(have.slice(0, 12).map(m => [(m.read ? "  " : "● ") + "m" + m.id, T(CREW[m.who]) + " · " + subOf(m) + (m.offer && !m.took ? " · " + T("special order") : "")]));
    say("sys", T("mail <n> reads one."), btn(F("mail {n}", { n: have[0].id }), "mail " + have[0].id));
  }
  function mailOpen(a) {
    if (a === "list") return mailList();
    if (a) return mailRead(a);
    const list = $("mailList"); $("mailTitle").textContent = T("Post");
    const have = mailHave(), first = have.find(m => !m.read);
    const row = m => {
      const li = el("li", { class: (m.read ? "" : "new") + (m === first ? " open" : "") });
      const head = el("div", { class: "mh", role: "button", tabindex: "0" }, el("b", { text: T(CREW[m.who]) }), el("span", { class: "ms", text: subOf(m) }), m.offer && !m.took ? el("em", { text: T("special order") }) : null, el("small", { text: new Date(m.at).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" }) }));
      const open = () => { li.classList.toggle("open"); if (!m.read) { m.read = true; li.classList.remove("new"); save(); topbar(); chips(); } };
      head.addEventListener("click", open); head.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
      const acts = mailBtns(m).map(b => { const o = b.onclick; b.onclick = () => { $("mailWin").classList.remove("show"); o(); }; return b; });
      li.append(head, el("div", { class: "mb" }, el("p", { text: T(m.text) }), acts.length ? el("div", { class: "ma" }, ...acts) : null));
      return li;
    };
    list.replaceChildren(...(have.length ? have.map(row) : [el("li", { text: T("Nothing yet. The crew writes after a contract settles, and when something happens on the chain.") })]));
    if (first) { first.read = true; save(); topbar(); chips(); }
    $("mailWin").classList.add("show");
  }

  /* ---------- the panes ---------- */
  function jobs() {
    const ol = $("jobs"); if (!ol) return;
    const tabs = $("ptabs"), open = inboxOpen(), pane = open && S.pane === "inbox" ? "inbox" : "story";
    if (tabs) { tabs.hidden = !open; for (const b of tabs.querySelectorAll("button")) { b.classList.toggle("on", b.dataset.p === pane); if (b.dataset.p === "inbox") b.textContent = S.inbox.length ? F("Inbox {n}", { n: S.inbox.length }) : T("Inbox"); } }
    if (pane === "inbox") {
      const rows = S.inbox.map(j => el("li", { class: (S.job === j.n ? "taken" : "") + (j === S.inbox.find(x => x.n !== S.job) && !S.job ? " next" : ""), onclick: () => run("read " + jname(j)), title: fill((heistOf(j) || kindOf(j)).brief, j) },
        el("span", { class: "n", text: jname(j) }), el("span", { class: "t", text: jobName(j) }),
        el("span", { class: "st", text: S.job === j.n ? T("taken") : stars(j.t) }),
        el("span", { class: "w", text: T(CREW[j.who]) + " · " + F("+{n}", { n: PAYS[j.t] + (j.special || 0) }) + (heistOf(j) ? " · " + T("heist") : j.themed ? " · " + T((THEMES.find(x => x.k === j.themed) || theme()).name) : j.special ? " · " + T("special order") : "") + (j.topic ? " · " + T(TOPICS[j.topic][0]) : "") })));
      if (!rows.length) rows.push(el("li", { class: "lock" }, el("span", { class: "n", text: "" }), el("span", { class: "t", text: T("Empty for the moment") }), el("span", { class: "w", text: T("a new contract comes within a few blocks") })));
      const done = S.arch.filter(a => a.out === "settled").length;
      rows.push(el("li", { class: "chap", onclick: () => run("archive") }, el("span", { class: "n", text: "" }), el("span", { class: "t", text: T("Archive") }), el("span", { class: "st", text: F("{n} settled", { n: done }) })));
      ol.replaceChildren(...rows);
      $("jobsCount").textContent = F("{n} open", { n: S.inbox.length });
      return;
    }
    const next = CONTRACTS.find(c => !S.done[c.id]);
    const rows = [], calm = !Object.keys(S.done).length;   // a first visit sees chapter 1 only, and no instruments, until the first contract settles
    document.documentElement.classList.toggle("nm-calm", calm);
    for (const ch of calm ? CH.slice(0, 1) : CH) {
      const open = chapterOpen(ch), done = chapterDone(ch);
      rows.push(el("li", { class: "chap" + (open ? "" : " lock"), onclick: () => run("chapter " + ch.n) }, el("span", { class: "n", text: "" }), el("span", { class: "t", text: F("Chapter {n}: {x}", { n: ch.n, x: ch.name }) }),
        el("span", { class: "st", text: done ? (S.chap[ch.n] ? T("claimed") : T("claim the share")) : open ? F("{a} of {b}", { a: ch.ids.filter(id => S.done[id]).length, b: ch.ids.length }) : T("locked") })));
      for (const id of ch.ids) {
        const c = byId(id), d = S.done[c.id], taken = S.taken === c.id;
        const icon = ART.have && ART.have.icons && ART.have.icons.includes(c.id) ? el("img", { src: ART.base + "icons/" + c.id + ".webp", alt: "", class: "ico" }) : null;
        rows.push(el("li", { class: (d ? "done" : "") + (taken ? " taken" : "") + (!d && next === c ? " next" : "") + (open ? "" : " lock"), onclick: () => run(open ? "take " + num(c) : "chapter " + ch.n), title: T(c.task) },
          el("span", { class: "n", text: String(num(c)).padStart(2, "0") }), el("span", { class: "t" }, icon, T(c.name)),
          el("span", { class: "st", text: d ? T("done") : taken ? T("taken") : T(CREW[c.who]) }),
          el("span", { class: "w", text: T(c.task) })));
      }
    }
    if (calm) rows.push(el("li", { class: "lock" }, el("span", { class: "n", text: "" }), el("span", { class: "t", text: T("Eight more after these") }), el("span", { class: "w", text: T("chapters 2 and 3, then an inbox of puzzles without end") })));
    ol.replaceChildren(...rows);
    $("jobsCount").textContent = F("{a} of {b}", { a: Object.keys(S.done).length, b: CONTRACTS.length });
  }
  const BOARD = { data: null, at: 0 };
  function instruments() {
    const box = $("inst"); if (!box) return;
    const pk = myPk(), tip = CHAIN.tip, left = traceLeft(), c = cur(), frac = traceFrac();
    const row = (h, b, p, cls) => el("div", { class: "row " + (cls || "") }, el("h3", { text: h }), el("b", { text: b }), p ? el("p", null, p) : null);
    const nr = nextRank(), badge = ART.have && ART.have.badges && ART.have.badges.includes(rankRow()[2]) ? el("img", { src: ART.base + "badges/" + rankRow()[2] + ".webp", alt: "", style: "width:28px;height:28px;vertical-align:middle;margin-right:6px" }) : null;
    const gear = el("div", { class: "gear" }, ...GEAR.map(([k, what]) => el("span", { class: has(k) ? "on" : "", text: k, title: T(what) })));
    const bd = BOARD.data && BOARD.data.board;
    box.replaceChildren(
      row(T("Node"), SIM ? T("Simulation") : CHAIN.ok ? T("Live node") : CHAIN.ok === false ? T("Out of reach") : T("Connecting"), SIM ? T("a practice node in this browser; nothing reaches the testnet") : T("node.tauhud.com, the community relay"), "state-" + (SIM ? "sim" : CHAIN.ok ? "live" : CHAIN.ok === false ? "off" : "")),
      row(T("Block"), tip != null ? "#" + fmt(tip) : "—", pace() ? F("about {n} s a block", { n: pace().toFixed(0) }) : T("measuring the pace")),
      (() => { const r = row(T("Trace"), c ? (left != null ? F("{n} blocks", { n: Math.max(0, left) }) : "…") : T("no contract taken"), c ? (left != null && left >= 0 ? F("until block {n} · {t}", { n: fmt(S.deadline), t: inTimeE(left) }) : T("the deadline is set from the tip at taking")) : T("take a contract: the block clock starts")); if (heat()) { const p = r.querySelector("p"); if (p) p.append(" · ", el("a", { href: "#", text: F("Tracer heat {n}", { n: heat() }), onclick: e => { e.preventDefault(); run("heat"); } })); } const bar = el("div", { class: "trace" + (frac < 0.25 ? " hot" : "") + (left != null && left < 0 ? " out" : "") }, el("i", { style: "width:" + Math.round(frac * 100) + "%" })); r.append(bar); return r; })(),
      row(T("Wallet"), pk ? short(pk) : T("not made yet"), pk ? el("a", { href: "/wallet/" + lang(), text: T("open in the wallet") }) : T("made at your first contract")),
      row(T("Balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS"), CHAIN.bal === 0 ? T("unseen wallet: the faucet’s 100,000 at the first payment") : T("test AGRS have no value")),
      (() => { const r = row(T("Standing"), "", nr ? F("{n} points · {m} more to {x}", { n: rep(), m: nr[0] - rep(), x: nr[1] }) : F("{n} points · the top of the ladder", { n: rep() }), "rk"); const b = r.querySelector("b"); b.classList.add("rank"); if (badge) b.append(badge); b.append(T(rank())); return r; })(),
      row(T("Inbox"), inboxOpen() ? (S.job ? F("{x} taken", { x: "j" + S.job }) : F("{n} open", { n: S.inbox.length })) : T("closed"), inboxOpen() ? F("tier {n} of 4 · {m} settled", { n: tierMax(), m: S.arch.filter(a => a.out === "settled").length }) : T("opens when chapter 1 is done")),
      (() => { const r = row(T("Gear"), "", null); r.querySelector("b").remove(); r.append(gear); return r; })(),
      row(T("Board"), bd ? F("{n} wallets", { n: bd.wallets || 0 }) : "—", bd ? [bd.day != null ? F("{n} today · {m} this hour", { n: bd.day, m: bd.hour || 0 }) : "", Object.entries(bd.ranks || {}).filter(([, n]) => n).map(([k, n]) => T(k) + " " + n).join(" · ")].filter(Boolean).join(" · ") || T("nobody yet") : T("wallets, not people; read from the server when it is there")),
    );
  }
  async function balance() { const pk = myPk(); if (!pk) return; const b = await ask("getbalance " + pk); if (b && b.status === "ok") { CHAIN.bal = Number((b.data || {}).balance) || 0; instruments(); } }
  async function boardLoad() { if (Date.now() - BOARD.at < 60000) return BOARD.data; BOARD.at = Date.now(); const d = await serverInfo(""); if (d) { BOARD.data = d; if (!SIM && d.drop && /^[0-9a-f]{96}$/.test(d.drop)) DROP = d.drop; instruments(); } return BOARD.data; }

  /* ---------- running a contract ---------- */
  const RUN = { busy: false, ret: null };
  const fail = (why) => { throw Object.assign(new Error(why), { soft: true }); };
  function take(c, again) {
    if (S.done[c.id] && !again) { say("sys", F("Contract {n} is settled already. To play it again anyway: take {n} again (it counts once).", { n: num(c) }), nextChip()); return; }
    if (S.taken === c.id) { say("sys", F("Contract {n} is yours already. Type run.", { n: num(c) }), btn("run", "run")); return; }
    if (RUN.busy) { say("warn", T("A contract is under way; wait for the chain’s answer.")); return; }
    if (S.job) { say("warn", F("{x} from the inbox is taken: send it, or drop it first.", { x: "j" + S.job })); return; }
    const ch = chapterOf(c);
    if (!chapterOpen(ch)) { say("warn", F("Chapter {n} first: its four contracts open chapter {m}.", { n: ch.n - 1, m: ch.n })); const nx = CONTRACTS.find(x => !S.done[x.id]); if (nx) say("sys", F("Next on the board: {n} {t}.", { n: num(nx), t: nx.name }), btn(F("take {n}", { n: num(nx) }), "take " + num(nx))); return; }
    S.taken = c.id; S.span = c.trace; S.deadline = CHAIN.tip != null ? CHAIN.tip + c.trace : null; save(); jobs(); instruments(); topbar(); chips();
    say("sys", F("Contract {n} taken: {t}", { n: num(c), t: c.name }));
    if (c.id === "mark") say("learn", T("The drop: the crew’s own wallet, an address on the chain. You pay it in your contracts; it reads every payment and pays your share back at each chapter’s end."));   // before the word is used bare
    transmit(c.who, c.brief, { id: c.id, name: c.name });
    tutAt({ mark: "take1", amount: "take2", ghost: "take3" }[c.id]);
    if (c.id === "amount") { S.num = lookoutNumber(); save(); say("sys", F("The lookout’s number: {n}", { n: S.num })); }
    say("sys", S.deadline != null ? F("Trace: until block {n} ({t}). Type run.", { n: fmt(S.deadline), t: inTimeE(c.trace) || fill0("{n} blocks", { n: c.trace }) }) : T("Trace: set from the tip as soon as the node answers. Type run."), btn("run", "run"));
    if (S.deadline == null) { const k = myPk(); (k ? envelope(k) : ask("getsequence " + DROP).then(st => { if (st && st.status === "ok") tick(Number(st.data.tip_height) || 0); })).then(() => { if (S.taken === c.id && S.deadline == null && CHAIN.tip != null) { S.deadline = CHAIN.tip + c.trace; save(); instruments(); topbar(); say("sys", F("Trace: until block {n} ({t}).", { n: fmt(S.deadline), t: inTimeE(c.trace) || fill0("{n} blocks", { n: c.trace }) })); } }).catch(() => {}); }
    watch();
  }
  const lookoutNumber = () => 100 + ((CHAIN.tip || 0) * 7 + new Date().getUTCDate()) % 900;   // the day's number: from the tip and the date, no secret in it
  function traced() {
    const c = byId(S.taken); S.taken = null; S.deadline = null; S.span = null; save(); jobs(); instruments(); topbar(); chips();
    const h = document.documentElement; h.classList.add("tr-out"); setTimeout(() => h.classList.remove("tr-out"), 2500); snd.out(); flash("bad");
    say("no", F("Trace complete: block {n} passed, connection dropped by the chain. Contract {m} is back on the board; the chain forgot you. Take it again.", { n: fmt(CHAIN.tip), m: num(c) }), btn(F("take {n}", { n: num(c) }), "take " + num(c)));
    if (c) crew(c.who, "Too slow for the block clock. It happens to everyone once; the clock does not care who you are.", "sour");
  }
  async function carry() {
    const c = S.taken ? byId(S.taken) : null;
    if (!c) { const nx = CONTRACTS.find(x => !S.done[x.id]); say("sys", T("No contract taken."), nx ? btn(F("take {n}", { n: num(nx) }), "take " + num(nx)) : null); return; }
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    if (c.id === "wayback" && RUN.ret) { say("sys", F("Your 50 test AGRS already wait in escrow ({h}). Type back, not run.", { h: short(RUN.ret.id) }), btn("back", "back")); return; }
    if (!B) { say("no", T("This browser cannot sign (no BLS library loaded).")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent. Try again in a minute, or switch to the simulation in the header."), btn("reboot", "reboot")); return; }
    RUN.busy = true; chips(); slot(F("contract {n}", { n: num(c) }));
    const k = myKey(true);
    try {
      if (S.deadline == null) { const e = await envelope(k.pk); S.deadline = e.tip + c.trace; save(); }
      const steps = { mark: () => pay(c, k, 1), amount: () => pay(c, k, S.num || lookoutNumber()), ghost: () => ghost(c, k), dead: () => refuse(c, k, 1, { expired: true }), stale: () => refuse(c, k, 1, { stale: true }),
        freeride: () => refuse(c, k, 1, { freeride: true }), overspend: () => overspend(c, k), giant: () => refuse(c, k, GIANT, {}), forged: () => refuse(c, k, 1, { signer: B.keygen() }),
        impostor: () => refuse(c, k, 1, { from: DROP }), wayback: () => wayback(c, k), race: () => pay(c, k, 1, true) };
      await steps[c.id]();
    } catch (e) {
      slotFail(T("stopped"));
      if (e && e.soft) say("no", e.message, btn("run", "run"));
      else say("no", T("The node did not answer in time; nothing is lost. The contract stays yours: type run again."), btn("run", "run"));
    }
    RUN.busy = false; chips(); jobs(); instruments(); topbar(); balance();
  }
  function settle(c, rec) {
    const again = !!S.done[c.id];
    S.done[c.id] = { at: Date.now(), ...rec }; S.taken = null; S.deadline = null; S.span = null; save(); jobs(); instruments(); topbar();
    snd.tension(false); snd.seal(); snd.say("v-sealed"); flash("ok"); mood(c.who, "glad");
    say("ok", F("Contract {n} settled. Standing: {r}.", { n: num(c), r: rank() }));
    if (Object.keys(S.done).length === 1 && !again) { say("sys", T("First one done. The instruments are open now: block, trace, wallet, balance and your standing, on the right.")); youAre(); }
    say("learn", T(c.learn));
    /* one quiet line at a good moment, each once: the refusal you just earned is also on a tee; after the third contract, who pays the node */
    if (!again) {
      const tee = (c.want || []).find(x => ["INSUFFICIENT_FUNDS", "INVALID_SIGNATURE", "TX_EXPIRED", "FEE_LIMIT_TOO_LOW"].includes(x));
      if (tee && !settle.tee) { settle.tee = true; say("sys", T("{x} is the chain doing its job. That answer is also printed on a tee:").replace("{x}", tee), link("https://tau-hud-shop.fourthwall.com/?utm_source=tauhud&utm_medium=nomemo", T("the Tau HUD shop"))); }
      else if (Object.keys(S.done).length === 3) say("sys", T("Three contracts settled. The node this terminal dials has a monthly bill. Nobody has to, but whoever wants can carry a part of it:"), link("/crew/?ref=nomemo", "tauhud.com/crew"));
    }
    if (c.id === "mark") tutAt("done1");
    if (chapterDone(CH[0]) && chapterOf(c).n === 1) tutAt("chap1");
    if (again) { chips(); return; }
    post(c.who, c.after, 1 + Math.floor(Math.random() * 2), null, { sub: ["Re:", c.name] });
    const ch = chapterOf(c);
    if (chapterDone(ch)) { chapterCard(ch); return; }
    const next = CONTRACTS.find(x => !S.done[x.id]);
    if (next) say("sys", F("Next on the board: {n} {t}.", { n: num(next), t: next.name }), btn(F("take {n}", { n: num(next) }), "take " + num(next)));
    chips();
  }
  const explorer = h => link(txUrl(h), short(h));
  function sent(tx, s) {
    say("step", F("signed in this browser (BLS, sequence {n}), sent", { n: tx.sequence_number }), s.hash ? explorer(s.hash) : null, el("span", { class: "sys", text: " · " + F("{n} ms", { n: s.ms }) }));
  }
  const refusedEarly = s => { snd.no(); snd.say("v-refused"); flash("bad"); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused before the mempool: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("The payment did not go out. Type run to try again.")); };
  /* a payment that must land */
  async function pay(c, k, amount, race) {
    say("step", F("building a payment: {n} test AGRS to the drop {h}", { n: fmt(amount), h: short(DROP) }));
    const tx = await payment(k, DROP, amount, race ? { deadline: S.deadline } : {});
    if (race) say("step", F("expire_at_height {n}: the chain itself will refuse it after that block", { n: fmt(tx.expire_at_height) }));
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    if (!s.hash) refusedEarly(s);
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline, s.way);
    if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why)) traced(); else fail(T("Type run to try again.")); return; }
    say("ok", F("Sealed in block {n}.", { n: fmt(w.block) }), explorer(s.hash));
    S.hist.unshift({ id: c.id, hash: s.hash, block: w.block, amount }); S.hist = S.hist.slice(0, 20);
    settle(c, { hash: s.hash, block: w.block, amount });
  }
  /* a payment the chain must refuse */
  async function refuse(c, k, amount, o) {
    say("step", F("building a payment: {n} test AGRS to the drop {h}", { n: fmt(amount), h: short(DROP) }));
    if (o.expired) say("step", T("expiration_time: two minutes ago"));
    if (o.stale) say("step", T("expire_at_height: five blocks behind the tip"));
    if (o.freeride) say("step", T("fee_limit: 0"));
    if (o.signer) say("step", T("signing key: a throwaway key made just now, not the wallet’s"));
    if (o.from) say("step", F("payer named in the transfer: the drop {h}; signer: you", { h: short(DROP) }));
    const tx = await payment(k, DROP, amount, o);
    await verdict(c, tx);
  }
  async function overspend(c, k) {
    const b = await ask("getbalance " + k.pk); if (!b || b.status !== "ok") fail(T("No answer from the node to getbalance. Type run again."));
    const bal = Number((b.data || {}).balance) || 0, have = bal === 0 ? FAUCET : bal, amount = have + 1000;
    CHAIN.bal = bal;
    say("step", F("balance {a} test AGRS; building a payment of {b} to the drop", { a: fmt(have), b: fmt(amount) }));
    const tx = await payment(k, DROP, amount, {});
    await verdict(c, tx);
  }
  async function ghost(c, k) {
    say("step", F("first the real thing: 1 test AGRS to the drop {h}", { h: short(DROP) }));
    const tx = await payment(k, DROP, 1, {});
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    if (!s.hash) refusedEarly(s);
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline, s.way);
    if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why)) traced(); else fail(T("Type run to try again.")); return; }
    say("ok", F("Sealed in block {n}.", { n: fmt(w.block) }), explorer(s.hash));
    say("step", T("now the ghost: the same bytes, the same signature, sent again"));
    slot(F("contract {n}: the ghost", { n: num(c) }));
    await verdict(c, tx);
  }
  async function verdict(c, tx, op) {
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    const want = c.want, c0 = codeOf(s.r);
    if (s.hash) {   // the chain took what it should have refused: a finding, kept with the record, never posted by itself
      sent(tx, s); slotFail(T("taken: a finding"));
      say("no", T("The chain took it. That is not how it should be."));
      S.findings.push({ at: Date.now(), id: c.id, tx, answer: s.r }); save();
      say("warn", T("A finding: the testnet did something it must not. The record is kept in this browser (type findings) and nowhere else. Please pass it on:"), link("/findings/" + lang(), T("how to report a finding")));
      if (!op) { S.taken = null; S.deadline = null; save(); } return false;
    }
    const right = want.includes(c0);
    snd.no(); flash(right ? "ok" : "bad"); slotFail(c0 || T("refused"));
    say(right ? "ok" : "warn", F("The chain said no in {n} ms: {x}", { n: s.ms, x: c0 || plain(s.r) }) + (right ? " ✓" : ""));
    if (!right) { say("warn", F("Refused, but with another answer than {x}. {y}", { x: want.join(" / "), y: plain(s.r) })); say("sys", T("That still counts: the chain said no. Type run to hear it again, or take the next contract.")); }
    if (!op) settle(c, { code: c0, ms: s.ms, right });
    return true;
  }
  async function wayback(c, k) {
    const release = now() + WAYBACK_MIN * 60;
    const { seq, tip } = await envelope(k.pk), f = await fee();
    const tx = sign({ tx_type: "retractable_transfer", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.min(now() + 600, release - 1), expire_at_height: tip + 1000, fee_limit: String(f * 5), recipient_pubkey: DROP, amount: 50, release_at_time: release }, k.sk);
    say("step", F("building a retractable transfer: 50 test AGRS to the drop, release at {t}", { t: clock(release) }));
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    if (!s.hash) refusedEarly(s);
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline, s.way);
    if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why)) traced(); else fail(T("Type run to try again.")); return; }
    say("ok", F("Sealed in block {n}: the money waits in escrow.", { n: fmt(w.block) }), explorer(s.hash));
    let rid = s.r.data && s.r.data.retractable_id;
    if (!rid) { const rt = await ask("getretractables " + k.pk + " out"); const open = ((rt && rt.data && rt.data.retractables) || []).filter(r => r.status !== "released" && r.status !== "retracted"); if (open.length) rid = (open[open.length - 1].retractable_id || open[open.length - 1].id); }
    if (!rid) rid = s.hash;
    RUN.ret = S.ret = { id: rid, release, c: c.id }; save();
    S.deadline = CHAIN.tip != null ? CHAIN.tip + Math.max(3, Math.round(((release - 60) - now()) / Math.max(4, pace() || 8))) : S.deadline; S.span = S.deadline != null && CHAIN.tip != null ? S.deadline - CHAIN.tip : null; save(); instruments(); topbar();
    crew("bosun", F("Escrow id {h}. It releases at {t}. Type back before then; leave the chain a minute to seal it.", { h: short(rid), t: clock(release) }), "calm");
    say("sys", T("The way back:"), btn("back", "back"));
  }
  async function back() {
    const r = RUN.ret;
    if (RUN.busy) { say("warn", T("Already under way; wait for the chain’s answer.")); return; }
    if (!r) { say("sys", T("Nothing waits in escrow from this terminal. Take contract 11 and run it first.")); return; }
    if (now() >= r.release) { say("no", T("Too late: the release time has passed and the first block pays the drop by itself. The contract is back on the board.")); RUN.ret = S.ret = null; S.taken = null; S.deadline = null; save(); jobs(); instruments(); topbar(); return; }
    RUN.busy = true; chips(); slot(T("the way back"));
    try {
      const k = myKey(true), { seq, tip } = await envelope(k.pk);
      const tx = sign({ tx_type: "retract_transfer", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.min(now() + 600, r.release - 1), expire_at_height: tip + 100, fee_limit: "0", retractable_id: r.id }, k.sk);
      say("step", F("building the retract for {h}: feeless, only the sender may send it", { h: short(r.id) }));
      const s = await sendtx(tx);
      if (!s.r) fail(T("No answer from the node; nothing was sent. Type back again."));
      if (!s.hash) { snd.no(); snd.say("v-refused"); flash("bad"); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("Type back to try again.")); }
      sent(tx, s);
      say("step", T("waiting for a block …"));
      const w = await sealed(s.hash, null, s.way);
      if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); fail(T("Type back to try again, if there is time.")); }
      if (now() >= r.release) { say("no", T("The retract was sealed after the release: the drop was paid. Nothing to settle; take the contract again another time.")); RUN.ret = S.ret = null; S.taken = null; S.deadline = null; save(); }
      else { say("ok", F("Taken back in block {n}, {m} s before the release.", { n: fmt(w.block), m: r.release - now() }), explorer(s.hash)); RUN.ret = S.ret = null; if (S.taken === "wayback") settle(byId("wayback"), { hash: s.hash, block: w.block, retracted: r.id }); await moreEscrow(k); }
    } catch (e) { slotFail(T("stopped")); if (e && e.soft) say("no", e.message, btn("back", "back")); else say("no", T("The node did not answer in time. Type back again."), btn("back", "back")); }
    RUN.busy = false; chips(); jobs(); instruments(); topbar(); balance();
  }

  /* another payment of this wallet still open in escrow to the drop (contract 11 run twice): offered for back as well */
  async function moreEscrow(k) {
    const rt = await ask("getretractables " + k.pk + " out"), open = ((rt && rt.data && rt.data.retractables) || []).filter(r => r.status !== "released" && r.status !== "retracted" && (r.recipient_pubkey || r.recipient) === DROP && (r.sender_pubkey || r.sender) === k.pk);
    if (!open.length) return;
    const r = open[0], release = Number(r.release_at_time) || now() + 60;
    RUN.ret = S.ret = { id: r.retractable_id || r.id, release, c: "wayback" }; save();
    say("sys", F("Another payment of yours still waits in escrow ({h}), release at {t}. Type back again.", { h: short(RUN.ret.id), t: clock(release) }), btn("back", "back"));
  }

  /* ---------- chapters: the card, the claim, the crew's share ---------- */
  function chapterCard(ch) {
    const pic = $("cardPic"), has = ART.have && ART.have.chapters && ART.have.chapters.includes(ch.n);
    pic.style.backgroundImage = has ? "url(" + ART.base + "chapters/" + ch.n + ".webp)" : "linear-gradient(160deg, #0b1a12, #050506)";
    $("cardTitle").replaceChildren(el("small", { text: F("Chapter {n}", { n: ch.n }) }), document.createTextNode(T(ch.name)));
    const done = chapterDone(ch), claimed = !!S.chap[ch.n];
    $("cardBody").replaceChildren(
      el("p", { text: T(ch.text) }),
      el("p", { text: done ? (claimed ? F("Claimed: the crew’s share of {n} test AGRS came back from the drop.", { n: SHARE }) : F("Done. Claim the crew’s share: a payment of {n} test AGRS to the drop (the amount is the message), and the drop pays {m} back within a few blocks.", { n: CLAIM_BASE + ch.n, m: SHARE })) : chapterOpen(ch) ? F("{a} of {b} contracts settled.", { a: ch.ids.filter(id => S.done[id]).length, b: ch.ids.length }) : F("Opens when chapter {n} is done.", { n: ch.n - 1 }) }),
      ch.unlock ? el("p", { class: "sys", text: F("Unlocks the tool {x}.", { x: ch.unlock }) }) : null,
      el("div", { class: "row" }, done && !claimed ? el("button", { type: "button", text: T("Claim the crew’s share"), onclick: () => { cardClose(); run("claim"); } }) : null, el("button", { type: "button", class: "ghost", text: T("close"), onclick: cardClose })));
    $("card").classList.add("show"); snd.chapter(); snd.say("v-chapter");
  }
  const cardClose = () => $("card").classList.remove("show");
  async function claim(pick, again) {
    /* the lowest finished chapter first (the hints name that one; the hunt opens with chapter 1); claim <n> picks one, claim <n> again resends an unpaid claim */
    let ch = pick ? CH.find(x => x.n === pick) : CH.find(x => chapterDone(x) && !S.chap[x.n]);
    if (pick && !ch) { say("warn", T("Chapters are 1, 2 and 3.")); return; }
    if (pick && !chapterDone(ch)) { say("sys", F("Nothing to claim yet: chapter {n} is not done.", { n: ch.n })); return; }
    if (pick && S.chap[ch.n]) {
      const c = S.chap[ch.n];
      if (c.paid) { say("sys", F("Chapter {n} is claimed and paid: {h}", { n: ch.n, h: short(c.hash) })); return; }
      if (!again) { say("sys", F("The claim for chapter {n} is on the chain ({h}); the purse pays within a few blocks. If nothing comes: claim {n} again", { n: ch.n, h: short(c.hash) }), btn(F("claim {n} again", { n: ch.n }), "claim " + ch.n + " again")); watchPayback(ch.n); return; }
    }
    if (!ch) { const open = CH.find(x => !chapterDone(x)); say("sys", open ? F("Nothing to claim yet: chapter {n} is not done.", { n: open.n }) : T("Every chapter’s share is claimed.")); return; }
    if (RUN.busy) { say("warn", T("A contract is under way; wait for the chain’s answer.")); return; }
    if (S.taken || S.job) { say("warn", T("Put the taken contract back first (drop), or finish it.")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent.")); return; }
    RUN.busy = true; chips(); slot(F("claim, chapter {n}", { n: ch.n }));
    const k = myKey(true), amount = CLAIM_BASE + ch.n;
    try {
      await boardLoad();
      say("step", F("building the claim: {n} test AGRS to the drop {h} (the amount says which chapter)", { n: amount, h: short(DROP) }));
      const tx = await payment(k, DROP, amount, {});
      const s = await sendtx(tx);
      if (!s.r) fail(T("No answer from the node; nothing was sent. Type claim again."));
      if (!s.hash) { snd.no(); snd.say("v-refused"); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("Type claim to try again.")); }
      sent(tx, s);
      say("step", T("waiting for a block …"));
      const w = await sealed(s.hash, null, s.way);
      if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); fail(T("Type claim to try again.")); }
      say("ok", F("Sealed in block {n}. The crew’s purse reads the chain and pays the share back; it can take a few blocks.", { n: fmt(w.block) }), explorer(s.hash));
      S.chap[ch.n] = { hash: s.hash, block: w.block, at: Date.now(), paid: null, drop: DROP }; save(); jobs(); chips();
      snd.seal(); mood("qm", "glad");
      crew("qm", ch.n === 1 ? "Signed on. The share comes from the drop, and with it the crew’s mark: one test AGRS, the hash of which is your badge on this chain." : ch.n === 2 ? "Second chapter closed. You now know four ways a payment dies before it is one; most wallets never learn the fourth." : "Third chapter closed and the board is clear. The drop pays the last share. From here the real work is on Tuesdays, when the ship is in.", "glad");
      if (!SIM && (!BOARD.data || BOARD.data.enabled === false)) say("warn", T("The crew’s purse on the server is not on yet; the share comes once it is. Your claim is on the chain and counts."));
      watchPayback(ch.n);
    } catch (e) { slotFail(T("stopped")); if (e && e.soft) say("no", e.message, btn("claim", "claim")); else say("no", T("The node did not answer in time. Type claim again."), btn("claim", "claim")); }
    RUN.busy = false; chips(); instruments(); topbar(); balance();
  }
  let markTimer = 0;
  function watchMark(tries = 0) {
    clearTimeout(markTimer);
    markTimer = setTimeout(async () => {
      const pk = myPk(); if (!pk) return;
      const w = await serverInfo("/wallet/" + pk), c = w && w.claims && (w.claims[1] || w.claims["1"]);
      if (c && c.paid && c.paid.mark) {
        S.chap[1] = { ...S.chap[1], paid: c.paid }; save(); balance(); snd.mark(); snd.say("v-mark");
        say("ok", T("And the crew’s mark: 1 test AGRS from the drop. Its hash is your badge."), c.paid.mark.hash ? explorer(c.paid.mark.hash) : null);
        return;
      }
      if (tries < 12) watchMark(tries + 1);
    }, 15000);
  }
  let pbTimer = 0;
  function watchPayback(n, tries = 0) {
    clearTimeout(pbTimer);
    pbTimer = setTimeout(async () => {
      const pk = myPk(); if (!pk) return;
      const w = await serverInfo("/wallet/" + pk), c = w && w.claims && (w.claims[n] || w.claims[String(n)]);
      if (c && c.paid) {
        S.chap[n] = { ...S.chap[n], paid: c.paid }; save(); balance(); snd.paid(); snd.say("v-paid"); if (c.paid.mark) setTimeout(() => snd.mark(), 1800); flash("ok");
        say("ok", F("The drop paid the share: {n} test AGRS.", { n: c.paid.share ? c.paid.share.amount : SHARE }), c.paid.share && c.paid.share.hash ? explorer(c.paid.share.hash) : null);
        if (c.paid.mark) say("ok", T("And the crew’s mark: 1 test AGRS from the drop. Its hash is your badge."), c.paid.mark.hash ? explorer(c.paid.mark.hash) : null);
        else if (n === 1) watchMark();   // the mark is a payment of its own, a little after the share
        post("qm", "The share is paid and the ledger balanced. Spend it on nothing: it is worth nothing, like all test AGRS, and that is the point of a testnet.", 1, null, { sub: "Your share is paid" });
        if (n === 1) setTimeout(() => huntWatch(), 12000);
        return;
      }
      if (tries < 20) watchPayback(n, tries + 1);
      else say("warn", F("No share yet for chapter {n}. The purse pays within minutes while it is on; if it stays out: claim {n} again", { n }), btn(F("claim {n} again", { n }), "claim " + n + " again"));
    }, tries < 3 ? 6000 : 15000);
  }

  /* ---------- the crew watches the testnet: GET /load (how hard it works) and GET /cruise (is the ship in) ---------- */
  const WORLD = { load: null, cruise: null, at: 0 };
  const LOAD_LINES = { calm: "Chain weather: calm. {n} sealed in the last hour, blocks on time. A good hour for a race.", busy: "Chain weather: busy. {n} sealed in the last hour; leave the chain a block longer before you call something lost.",
    strained: "Chain weather: strained. Transactions wait, blocks come late. Do not race the block tonight; the dead letters do not mind.", stalled: "The chain has stalled: no block for ten minutes with something waiting. Nothing you send lands until it moves; watch the block clock." };
  async function world() {
    if (SIM || Date.now() - WORLD.at < 90000) return; WORLD.at = Date.now();
    try { const r = await fetch(RELAY + "/load", { cache: "no-store" }); if (r.ok) WORLD.load = await r.json(); } catch (e) {}
    try { const r = await fetch(RELAY + "/cruise", { cache: "no-store" }); if (r.ok) WORLD.cruise = await r.json(); } catch (e) {}
    const st = WORLD.load && WORLD.load.state;
    if (st && LOAD_LINES[st] && S.seen.load !== st) { S.seen.load = st; save(); crew("look", F(LOAD_LINES[st], { n: (WORLD.load.now || {}).sealed_hour || 0 }), st === "calm" ? "glad" : st === "strained" || st === "stalled" ? "sour" : "calm"); }
    const nowv = WORLD.cruise && WORLD.cruise.now;
    if (nowv && nowv.ship === "pirates" && S.seen.visit !== nowv.visit) { S.seen.visit = nowv.visit; save(); crew("look", "Ship in! The Black Sequence lies off the island right now and the crew is trying its tricks on the chain. Live ops are open: type op.", "glad"); say("sys", T("Live ops:"), btn("op", "op")); }
    chips();
  }
  const shipIn = () => SIM || !!(WORLD.cruise && WORLD.cruise.now && WORLD.cruise.now.ship === "pirates" && ["here", "landed", "visit", "in"].some(x => String(WORLD.cruise.now.phase || "here").includes(x)));

  /* ---------- live ops: while the ship is in, mirror the pirates' tricks of this very hour ---------- */
  const OP = { list: null, i: 0 };
  async function op() {
    if (!SIM && !WORLD.cruise) await world();
    if (!shipIn()) {
      const nx = WORLD.cruise && WORLD.cruise.next, t = nx && nx.t0 ? new Date(nx.t0 * 1000) : null;
      say("sys", T("No ship in. Live ops open while the Black Sequence lies off the island: Tuesdays from 18:00 German time, for about two hours.") + (t ? " " + F("Next call: {x}.", { x: t.toLocaleString("en-GB", { timeZone: "Europe/Berlin", weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) }) : ""), link("/cruise/" + lang(), T("cruise logbook")));
      return;
    }
    const v = SIM ? { visit: "sample", tricks: { tried: { replay: 2, forged: 1, overspend: 1, expired: 1 } }, end: now() + 600 } : WORLD.cruise.now;
    const id = "op-" + v.visit;
    if (S.ops[id]) { say("ok", F("Tonight’s op is settled already ({x}). The next ship is next Tuesday.", { x: v.visit })); return; }
    if (RUN.busy || S.taken || S.job) { say("warn", T("Finish or drop the taken contract first; the op needs the terminal.")); return; }
    const tried = Object.keys((v.tricks && (v.tricks.tried || v.tricks.by)) || {}).filter(k => OPS[k]);
    const picks = (tried.length ? tried : ["expired", "forged", "overspend"]).slice(0, 3);
    OP.list = picks; OP.i = 0; OP.id = id; OP.end = v.end;
    crew("bosun", F("Live op, visit {x}. The pirates are sending {n} kinds of trick this hour; make the chain refuse the same three from your wallet before the ship leaves. Every answer is read live.", { x: v.visit, n: picks.length }), "calm");
    cols(picks.map((k, i) => [String(i + 1), T(OPS[k][1]) + " (" + k + ")"]));
    say("sys", T("Type go to send the first one."), btn("go", "go"));
    chips();
  }
  async function opGo() {
    if (!OP.list) { return carry(); }
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    if (OP.end && now() > OP.end) { say("no", T("The ship has left; the op is over. Next Tuesday.")); OP.list = null; chips(); return; }
    const k = myKey(true), trick = OP.list[OP.i], [cid, what] = OPS[trick], c = byId(cid);
    RUN.busy = true; chips(); slot(F("op {n} of {m}: {x}", { n: OP.i + 1, m: OP.list.length, x: trick }));
    try {
      say("sys", F("Op {n} of {m}: {x}", { n: OP.i + 1, m: OP.list.length, x: what }));
      let ok;
      if (cid === "ghost") { say("step", T("first a real payment, then the same one again")); const tx = await payment(k, DROP, 1, {}); const s = await sendtx(tx); if (!s.hash) refusedEarly(s); sent(tx, s); const w = await sealed(s.hash, null, s.way); if (!w.in) fail(T("Not sealed; type go again.")); ok = await verdict(c, tx, true); }
      else if (cid === "overspend") { const b = await ask("getbalance " + k.pk); const bal = Number(((b || {}).data || {}).balance) || 0; ok = await verdict(c, await payment(k, DROP, (bal === 0 ? FAUCET : bal) + 1000, {}), true); }
      else { const o = { dead: { expired: true }, stale: { stale: true }, freeride: { freeride: true }, giant: {}, forged: { signer: B.keygen() }, impostor: { from: DROP } }[cid]; ok = await verdict(c, await payment(k, DROP, cid === "giant" ? GIANT : 1, o), true); }
      if (ok) { OP.i += 1; if (OP.i >= OP.list.length) { S.ops[OP.id] = { at: Date.now(), tricks: OP.list }; save(); OP.list = null; snd.seal(); flash("ok"); say("ok", F("Op settled: three refusals, live, beside the pirates’. Standing: {r}.", { r: rank() })); crew("bosun", "That is the real thing: the same answers the chain gives the pirates, from your wallet, the same hour. The logbook has theirs; your terminal has yours.", "glad"); } else say("sys", F("Next: op {n}. Type go.", { n: OP.i + 1 }), btn("go", "go")); }
      else say("warn", T("That one stands as a finding; the op goes on with the next. Type go."));
    } catch (e) { slotFail(T("stopped")); say("no", e && e.soft ? e.message : T("The node did not answer in time. Type go again."), btn("go", "go")); }
    RUN.busy = false; chips(); instruments(); topbar(); balance();
  }

  /* ---------- the case file: the week's hack replay, the pirates' logbook, and two riddles the chain answers ---------- */
  const CASE = { data: null, pick: null, riddle: null };
  async function caseFile() {
    say("sys", T("Opening the case file …"));
    let hack = null, log = null;
    if (SIM) ({ hack, log } = sampleCase());
    else {
      try { hack = await (await fetch(RELAY + "/hack", { cache: "no-store" })).json(); } catch (e) { hack = null; }
      try { log = await (await fetch(RELAY + "/cruise/log?n=600", { cache: "no-store" })).json(); } catch (e) { log = null; }
    }
    if (!hack && !log) { say("no", T("The relay is out of reach; the case file cannot be read right now.")); return; }
    crew("bosun", "Three things in the file: what the pirates tried at the island on Tuesday, the hack of the week from Thursday, and two riddles only the chain can answer.", "calm");
    if (SIM) say("warn", T("Simulation: a sample case with invented wallets, so you can see how one reads."));
    /* the pirates: the newest visit's tricks, what the chain answered */
    const tricks = ((log && log.entries) || []).filter(e => e.ship === "pirates" && e.kind === "trick");
    if (tricks.length) {
      const visit = tricks[0].visit, mine = tricks.filter(e => e.visit === visit), stopped = mine.filter(e => e.ok === false).length, held = mine.filter(e => e.held).length;
      say("sys", F("Black Sequence, visit {v}: {n} tricks sent, {m} refused by the chain{x}.", { v: visit, n: mine.length, m: stopped, x: held ? F(", {k} held back (a finding, reported privately first)", { k: held }) : "" }));
      const by = {}; for (const e of mine) if (e.ok === false) by[e.trick] = (by[e.trick] || 0) + 1;
      cols(Object.entries(by).map(([t, n]) => [t, F("{n}× refused", { n })]));
    } else say("sys", T("No pirate visit in the logbook yet: the Black Sequence first calls on Tuesday at 18:00 German time."));
    /* the hack: the victim's history as a wallet shows it, the lookalike among the full addresses */
    const run = hack && hack.runs && hack.runs[0];
    const W = (hack && hack.wallets) || {};
    if (!run || !W.friend || !W.poisoner) { say("sys", hack && hack.next && hack.next.t0 ? F("No hack replay yet. The first one runs on {t} German time; the case file fills itself after it.", { t: new Date(hack.next.t0 * 1000).toLocaleString("en-GB", { timeZone: "Europe/Berlin", weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) }) : T("No hack replay in the file yet.")); CASE.data = null; }
    else {
      const hk = (hack.hacks || {})[run.hack] || {};
      say("sys", F("Hack of the week, run {id}: {title}. {what}", { id: run.id, title: hk.name || run.hack, what: hk.how || "" }));
      if (run.held) say("sys", T("Outcome: held back, a finding reported privately first.")); else if (run.result || run.status) say("sys", F("Outcome: {x}", { x: run.result || run.status }));
      const friend = W.friend.address || W.friend, poison = W.poisoner.address || W.poisoner;
      say("sys", T("The victim’s history, the way a wallet shows it (first 6 and last 4 characters):"));
      const h = el("div", { class: "hist" });
      for (const [w, what, n] of [[short(friend), T("paid (the weekly habit)"), 10], [short(poison), T("received (dust)"), 1], [short(poison), T("paid (the slip)"), 50]]) h.append(el("span", { text: w }), el("span", { text: fmt(n) + " " + T("test AGRS") }), el("span", { text: what }));
      say("sys", h);
      const ab = Math.random() < 0.5 ? [friend, poison] : [poison, friend];
      CASE.data = { id: run.id, a: ab[0], b: ab[1], friend };
      say("sys", T("Two full addresses carry those characters. Which one is the friend, the one the victim meant to pay?"));
      cols([[btn("a", "pick a"), ab[0]], [btn("b", "pick b"), ab[1]]]);
      say("sys", S.cases[run.id] ? T("You solved this file already; pick a or b to read it again.") : T("Type pick a or pick b, or click."));
    }
    await riddle();
  }
  function pick(x) {
    const d = CASE.data; if (!d) { say("sys", T("Open a case file first: type case.")); return; }
    const chosen = d[x]; if (!chosen) { say("sys", T("Type pick a or pick b.")); return; }
    if (chosen === d.friend) {
      snd.hunt(); flash("ok");
      say("ok", T("Right: the friend. The other address was ground to match the first 6 and last 4 characters, the exact parts a wallet shows; the only way to tell is the whole address, or an address book you keep yourself."));
      if (!S.cases[d.id]) { S.cases[d.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Case file {id} settled. Standing: {r}.", { id: d.id, r: rank() })); mood("bosun", "glad"); }
    } else {
      snd.no(); flash("bad");
      say("no", T("That is the lookalike. It paid the victim 1 test AGRS so it would stand in the history; the victim copied it from there. Only the whole address tells them apart."));
    }
    say("learn", T("A wallet setting helps once the slip is made: payments to an address you never paid wait in escrow and can be taken back (contract 11). It is the wallet’s setting, not a chain rule: whoever holds the key can pay without it."));
  }
  /* riddles with answers only the chain has: the lowest fee the chain takes, your wallet's next sequence number, and
     the two levels of rules (IDNI's Q&A, November 2026): a rule for everyone needs the validators' agreement, read from
     getgovernance; a rule on your own wallet needs nobody's vote */
  async function governance() {
    try {
      const g = await ask("getgovernance"), d = g && g.data;
      if (!d || !Array.isArray(d.active_validators) || !d.active_validators.length) return null;
      const n = d.active_validators.length, q = String(d.vote_quorum || "supermajority"), c = /^count:(\d+)$/.exec(q);
      const thr = Number.isInteger(d.approval_threshold) && d.approval_threshold > 0 ? d.approval_threshold
        : q === "majority" ? Math.floor(n / 2) + 1 : c ? Math.max(1, Math.min(+c[1], n)) : Math.max(1, Math.floor((2 * n + 2) / 3));
      return { n, thr, words: q === "majority" ? T("more than half") : c ? F("a fixed count of {n}", { n: c[1] }) : T("two thirds (supermajority)") };
    } catch (e) { return null; }
  }
  async function riddle() {
    const pk = myPk(), f = await fee(), week = new Date().toISOString().slice(0, 10), id = "r-" + week;
    let seq = null; if (pk) { try { seq = (await envelope(pk)).seq; } catch (e) { seq = null; } }
    const list = [["fee", F("Riddle 1: the base fee on this chain is {n} (getgovernance, o9). A payment is signed with fee_limit 5 times that. What is the MOST the chain may take from it, in test AGRS?", { n: f }), f * 5]];
    if (seq != null) list.push(["seq", F("Riddle 2: your wallet is at sequence {n} (getsequence). Which sequence number must your next payment carry to be taken?", { n: seq }), seq]);
    const gv = await governance();
    if (gv) {
      list.push(["gov", F("Riddle on rules for everyone: the chain has {n} validators, and a change needs {w} of them (getgovernance: active_validators, vote_quorum). How many validators must say yes before the fee changes for everybody?", { n: gv.n, w: gv.words }), gv.thr]);
      list.push(["own", T("Riddle on your own rule: you give your wallet a rule, no payment over 500. How many validators must vote for it?"), 0]);
    }
    CASE.riddle = { id, list, i: 0 };
    say("sys", T("The riddles. Answer with answer <number>."));
    say("sys", list[0][1]);
    if (S.riddles[id]) say("sys", T("Solved this week already; answer again if you like."));
  }
  function answer(x) {
    const r = CASE.riddle; if (!r) { say("sys", T("No riddle open: type case.")); return; }
    const [key, , want] = r.list[r.i], n = parseInt(x, 10);
    if (!(n >= 0)) { say("sys", T("answer <number>")); return; }
    if (n === want) {
      snd.ok(); say("ok", T(RIGHT[key]));
      r.i += 1;
      if (r.i < r.list.length) say("sys", r.list[r.i][1]);
      else { if (!S.riddles[r.id]) { S.riddles[r.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Riddles of {x} settled. Standing: {r}.", { x: r.id.slice(2), r: rank() })); mood("bosun", "glad"); } CASE.riddle = null; }
    } else { snd.no(); say("no", T(WRONG[key])); }
  }
  const RIGHT = {
    fee: "Right: the fee limit is the most, never a promise to pay it; what the chain takes is the base fee, and the rest stays.",
    seq: "Right: the next number, exactly once. A number used twice is the ghost from contract 3; a number skipped waits for the one before it.",
    gov: "Right. A rule for everyone is the protocol level: a validator proposes it, enough of them must agree, and it applies only some blocks later, so nobody is surprised.",
    own: "Right: none. A rule on your own wallet is the user level: you sign it, the chain checks every payment you make against it, and nobody votes.",
  };
  const WRONG = {
    fee: "No. Read the riddle again: the limit is a ceiling, and the ceiling is what you signed.",
    seq: "No. The chain takes each number once and in order; getsequence names the next one.",
    gov: "No. peek getgovernance: approval_threshold is the number of yes votes a change for everyone needs right now.",
    own: "No. Your own rule binds only your wallet, so it is yours alone to set. Type what levels.",
  };
  function sampleCase() {
    const hex = s => s.padEnd(96, "0").slice(0, 96);
    const friend = "5a7c21" + "e3".repeat(43) + "9f0b", poison = "5a7c21" + "4d".repeat(43) + "9f0b";
    return { hack: { hacks: { poisoning: { name: "Address poisoning", how: "The attacker makes an address that starts and ends like one you pay often, sends you a tiny amount from it, and waits for you to copy the wrong one from your history." } },
      wallets: { friend: { address: hex(friend) }, poisoner: { address: hex(poison) } }, runs: [{ id: "sample-poisoning", hack: "poisoning", result: "held: the payment came back" }] },
      log: { entries: [{ ship: "pirates", kind: "trick", visit: "sample", trick: "replay", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "forged", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "overspend", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "expired", ok: false }] } };
  }

  /* ---------- the hunt: the Tracer's dust, a lookalike of the drop, told apart by the whole address ---------- */
  const HUNT = { data: null };
  let huntTimer = 0;
  function huntWatch(tries = 0) {
    clearTimeout(huntTimer);
    huntTimer = setTimeout(async () => {
      const pk = myPk(); if (!pk || !has("hunt") && !S.chap[1]) return;
      const w = await serverInfo("/wallet/" + pk);
      const dust = (w && w.dust) || [];
      if (dust.length && !S.seen.dust) { S.seen.dust = dust[0].hash || "1"; save(); snd.dust(); snd.say("v-dust"); crew("look", "Dust! A payment of 1 test AGRS came into your wallet from an address I would swear is the drop’s, if I only read the ends. I do not trust it. Type hunt.", "sour"); say("sys", T("The hunt:"), btn("hunt", "hunt")); chips(); return; }
      if (!dust.length && tries < 12) huntWatch(tries + 1);
    }, tries ? 20000 : 3000);
  }
  async function hunt() {
    if (!has("hunt") && !S.chap[1]) { say("sys", T("The hunt opens after the first chapter’s share is claimed: the Tracer only follows wallets the drop has paid.")); return; }
    const pk = myPk(); if (!pk) { say("sys", T("No wallet yet; take contract 1 first.")); return; }
    const w = await serverInfo("/wallet/" + pk), dust = (w && w.dust) || [], drop = (w && w.drop) || DROP;
    if (!dust.length) { say("sys", T("No dust in your wallet yet. The Tracer sends it some blocks after the first share is paid; the Lookout calls out when it lands.") + (SIM ? "" : " " + T("(The server’s Tracer may be switched off.)"))); return; }
    const d = dust[0];
    crew("look", F("Two addresses look the same the way every wallet shows them: {h}. One is the drop, the crew’s own; the other sent you the dust. Which full address is the DROP?", { h: short(drop) }), "calm");
    const ab = Math.random() < 0.5 ? [drop, d.from] : [d.from, drop];
    HUNT.data = { id: "hunt-" + (d.hash || d.from).slice(0, 12), a: ab[0], b: ab[1], drop };
    cols([[btn("a", "mark a"), ab[0]], [btn("b", "mark b"), ab[1]]]);
    say("sys", T("Type mark a or mark b, or click."));
  }
  function markPick(x) {
    const d = HUNT.data; if (!d) { say("sys", T("Open the hunt first: type hunt.")); return; }
    const chosen = d[x]; if (!chosen) { say("sys", T("Type mark a or mark b.")); return; }
    if (S.hunt[d.id]) { say("sys", F("This hunt is settled: the drop is {h}. The next one comes with the next dust.", { h: short(d.drop) }), nextChip()); return; }
    if (chosen === d.drop) {
      snd.hunt(); flash("ok");
      say("ok", T("Right: that is the drop. The dust came from the lookalike, a key ground until its first and last characters matched the drop’s. Never pay an address from your history without reading the whole of it."));
      if (!S.hunt[d.id]) { S.hunt[d.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Hunt settled. Standing: {r}.", { r: rank() })); mood("look", "glad"); }
    } else { snd.no(); flash("bad"); say("no", T("That is the lookalike. Read the middle, not the ends: the ends are what it was made to match.")); }
    say("learn", T("The same trick the hack of the week replays on Thursdays, now done to you. The drop’s whole address is in this terminal (status); a wallet’s address book is the only cure."));
  }

  /* ---------- the crew's voices: clips the server made (infra/rico/make.py), played when they exist ---------- */
  const VOICE = { have: null, at: 0, audio: null };
  async function clips() {
    if (SIM || VOICE.have || Date.now() - VOICE.at < 60000) return; VOICE.at = Date.now();
    try { const r = await fetch(CLIPS + "index.json", { cache: "no-cache" }); const j = r.ok ? await r.json() : null; VOICE.have = new Set((j && j.clips) || []); } catch (e) { VOICE.have = new Set(); }
  }
  function heard(who, spoke) {   // a line whose voice never came: its face talks without it (transmission.js)
    Promise.resolve(spoke).then(ok => { if (!ok) document.dispatchEvent(new CustomEvent("nomemo:crewvoice", { detail: { who, none: true } })); });
  }
  async function speak(who, text) {
    if (SIM || !S.voice || !window.crypto || !crypto.subtle) return;
    return onAir(async () => {   // its turn on the line: after the ship's voice or another crew line has finished, and a breath
      await clips(); if (!VOICE.have || !VOICE.have.size || !S.voice) return false;
      const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + text));   // the clips are English; the line shown may be translated
      const key = [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
      if (!VOICE.have.has(key)) return false;
      return snd.crew(CLIPS + key + ".mp3", who);
    });
  }

  /* ---------- the boot screen: once per browser, or ?boot=1, or the command reboot ---------- */
  /* the door: a first visit gets what this is in four lines and two ways in, before anything else */
  const DOOR = [
    "A hacker game on Tau Testnet Alpha: a pirate crew hands you contracts, and each one is a real transaction on the live test chain.",
    "You play the same chain as everybody else, right now. No setup; test coins have no value.",
  ];
  function door() {
    const box = $("bootLines"), over = $("bootScreen"); if (!box || !over) return Promise.resolve(null);
    return new Promise(res => {
      const go = v => { over.classList.remove("show", "door"); S.booted = true; save(); res(v); };
      box.replaceChildren(el("h2", { text: "No Memo" }), ...DOOR.map((t, i) => el("p", { class: i ? "dim" : "", text: T(t) })));
      const row = over.querySelector(".row");
      row.replaceChildren(el("button", { type: "button", text: T("First contract"), onclick: () => go("take 1") }), el("button", { type: "button", class: "ghost", text: T("Tutorial"), onclick: () => go("tutorial") }), el("button", { type: "button", class: "ghost", id: "bootSkip", text: T("just look"), onclick: () => go(null) }));
      over.classList.add("show", "door");
    });
  }
  async function bootScreen(again) {
    const box = $("bootLines"), over = $("bootScreen"); if (!box || !over) return;
    const pk0 = myPk(), dial = again ? ask("getsequence " + (pk0 || DROP), 8000) : null;   // reboot: the handshake is real, asked while the lines type
    box.replaceChildren(); over.classList.add("show");
    let skipped = false; const skip = () => { skipped = true; over.classList.remove("show"); };
    over.querySelector(".row").replaceChildren(el("button", { type: "button", class: "ghost", id: "bootSkip", text: T("skip"), onclick: skip }));
    snd.boot();
    const pk = myPk();
    const lines = [["BLACK SEQUENCE · crew terminal", ""], [T("no memo · from, to, amount, signed"), "dim"], [SIM ? T("practice node: this browser") : "node.tauhud.com · " + T("relay"), "dim"], [T("authorisation required"), ""],
      [pk ? F("access code: wallet {h} (made in this browser)", { h: short(pk) }) : T("access code: none yet, a wallet is made at the first contract"), "dim"], [T("granted. welcome aboard."), ""]];
    if (again) {
      lines.unshift([T("reboot · wallet, standing and contracts stay in this browser"), "dim"]);
      lines.splice(4, 0, [() => dial.then(st => st && st.status === "ok" ? F("handshake · block #{n}", { n: fmt(Number(st.data.tip_height) || 0) }) : T("no handshake · the node is silent")), ""]);
    }
    for (let [t, cls] of lines) {
      if (skipped) break;
      if (typeof t === "function") t = await t();
      const p = el("p", { class: cls }); box.append(p);
      p.textContent = t;   // the whole line is in the page from the start (readers and checks see it); the reveal is a width
      if (S.fx && !REDUCED) { p.classList.add("typing"); for (let i = 1; i <= t.length; i++) { p.style.width = i + "ch"; if (i % 2 === 0) snd.key(); await sleep(14); if (skipped) break; } p.classList.remove("typing"); p.style.width = ""; }
      await sleep(260);
    }
    if (!skipped) { await sleep(700); over.classList.remove("show"); }
    S.booted = true; save();
  }
  /* reboot: the boot screen again, then a fresh line to the node (a new socket, block, balance, board, mail) and the
     start lines. Nothing of the player is touched: wallet, standing, open contract and trace stay as they are. */
  let rebooting = false;
  async function reboot() {
    if (rebooting) return;
    if (RUN.busy) { say("sys", T("Not now: a payment is on its way. Reboot once it has landed.")); return; }
    rebooting = true;
    try {
      if (CHAIN.ws) { const ws = CHAIN.ws; CHAIN.ws = null; ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null; try { ws.close(); } catch (e) { } }
      for (const w of CHAIN.wait.values()) while (w.length) w.shift()(null);
      CHAIN.ok = null; { const st = $("state"), tx = $("stateText"); if (st) st.className = "state" + (SIM ? " sim" : ""); if (tx) tx.textContent = SIM ? T("Simulation") : T("Connecting"); }
      clearScreen(); snd.wake();
      await bootScreen(true);
      await hello();
      jobs(); instruments(); chips(); topbar(); watch(); world(); boardLoad(); deliverMail();
    } finally { rebooting = false; }
  }

  /* ---------- the inbox: contracts that keep coming. It opens with chapter 1's end; there are always two to four
     offers, a new one every few blocks, and an offer nobody takes lapses after a couple of hours of blocks. Each is a
     puzzle about one part of the chain (TOPICS), answered by a real transaction built in the draft (tx, set, send):
     a refusal for the right reason, made in the asked way, or a payment whose amount or fields solve a riddle.
     They pay standing, never test AGRS: the crew's purse pays chapters only. ---------- */
  const TOPICS = {
    fee: ["Fees", "The fee is a limit you sign: at most this much may be taken. The chain’s base fee is in its rules (peek getgovernance: o9). A limit below the base fee is refused: FEE_LIMIT_TOO_LOW."],
    height: ["Block height", "expire_at_height names the last block a payment may land in. At or behind the tip it is refused: TX_EXPIRED. Blocks are the clock that counts on this chain."],
    clock: ["Expiry time", "expiration_time is a moment written into the signed payment. Once it has passed, the chain refuses the payment: TX_EXPIRED, whatever the block."],
    seq: ["Sequence", "Every wallet numbers its payments: the sequence number. The chain takes only the next number, each once; any other is refused: INVALID_SEQUENCE. peek getsequence <address> shows the next."],
    sig: ["Signature", "The signature must verify for the sender’s key, or the payment is refused: INVALID_SIGNATURE. To the chain, whoever holds the key is the wallet."],
    payer: ["Payer", "The payer named inside a transfer must be the wallet that signed it, or it is refused: TX_INVALID. A good signature on the wrong wallet moves nothing."],
    funds: ["Balance", "The chain checks the balance against the amount plus the fee: INSUFFICIENT_FUNDS, or TX_REJECTED when the transfer rule says no first."],
    width: ["Amount width", "An amount is 24 bits wide here: 16,777,215 at most. 2^24 = 16,777,216 is not even read: TX_INVALID or INVALID_PARAMS."],
    addr: ["Addresses", "An address is a public key written as 96 hex characters (0–9, a–f), each one worth 0 to 15. Lookalikes copy the ends; only the whole address is the wallet."],
    bool: ["Boolean functions", "In Tau a Boolean function is built with & (and), | (or), ' (not, written after) and ^ (exclusive or); ' binds first, then &, then ^, then |. Over the two values 0 and 1 a function is just its table; Tau works the same way over much bigger Boolean algebras."],
    rule: ["Tau Language", "The chain’s rules are a Tau specification. In (o9[t]:bv[24] = {#x00000a}:bv[24]), o9[t] is output stream 9 at every step t, :bv[24] makes it a bitvector 24 bits wide, and {#x00000a} is a constant written in hex: 10. Learn to write such lines yourself: tauhud.com/learn/."],
    order: ["Order of checks", "A payment wrong in two ways is refused for one of them: the node answers with the first check it fails. Which check comes first is the node’s own order; its answer shows it."],
    guard: ["Personal rules", "A wallet can carry a rule of its own, written in Tau, and the chain checks each of its payments against it: o5 = 1 lets the payment through, 0 stops it, and i1 is the amount. Where the rule says nothing, the engine answers 0, so a rule that only says when to block blocks everything."],
    clause: ["Rules on the chain", "A wallet’s own rule is a transaction of its own: operation 0 carries the rule, operation 1 the payments, and one transaction may not carry both (RULE_WITH_TRANSFERS). A rule that writes o5 may write nothing else (MIXED_OUTPUT_RULE), and it holds at most 32 comparisons. A wallet has one rule at a time: a new one replaces it, and the rule that says o5 = 1 and nothing else takes it away."],
  };
  const CODE_TOPIC = { RULE_WITH_TRANSFERS: "clause", MIXED_OUTPUT_RULE: "clause", CLAUSE_SHAPE: "clause", FEE_LIMIT_TOO_LOW: "fee", TX_EXPIRED: "height", INVALID_SEQUENCE: "seq", INVALID_SIGNATURE: "sig", TX_INVALID: "payer", INVALID_PARAMS: "width", INSUFFICIENT_FUNDS: "funds", TX_REJECTED: "funds" };
  const PAYS = { 1: 1, 2: 2, 3: 3, 4: 5 };
  /* the week's theme, the same for every player: weeks counted from Monday 00:00 UTC; its topics come more often and pay double */
  const THEMES = [
    { k: "fee", who: "qm", name: "Fee week", topics: ["fee", "funds", "width"], text: "This week is fee week. Contracts about the fee, empty pockets and amount widths come more often and pay double. Learn what the base fee is, where the chain keeps it, and what a fee limit really promises." },
    { k: "deadline", who: "look", name: "Deadline week", topics: ["height", "clock"], text: "This week is deadline week. Contracts about block heights and expiry times come more often and pay double. Two clocks guard every payment; learn to tell them apart." },
    { k: "tau", who: "bosun", name: "Tau week", topics: ["rule", "bool", "guard", "clause"], text: "This week is Tau week. Contracts about the chain’s rule and Boolean functions come more often and pay double. The rules of this chain are written in Tau; read them, then write your own." },
    { k: "mask", who: "bosun", name: "Disguise week", topics: ["sig", "payer", "seq"], text: "This week is disguise week. Contracts about signatures, payers and sequence numbers come more often and pay double. Learn what the chain checks to know a payment is really yours." },
    { k: "eyes", who: "look", name: "Sharp eyes week", topics: ["addr", "order"], text: "This week is sharp eyes week. Contracts about addresses and the order of the node’s checks come more often and pay double. Read the middle of an address, and know which check comes first." },
  ];
  const weekNo = () => Math.floor((Date.now() / 86400000 + 3) / 7);   // day 0 was a Thursday: +3 starts weeks on Monday
  const theme = () => THEMES[weekNo() % THEMES.length];
  function weekCmd() {
    const th = theme(), left = 7 - ((Math.floor(Date.now() / 86400000) + 3) % 7);
    say("sys", F("This week: {x}. Contracts on {y} pay double and come more often.", { x: th.name, y: th.topics.map(t => TOPICS[t] ? TOPICS[t][0] : t).join(", ") }));
    say("sys", left > 1 ? F("{n} days until the next theme.", { n: left }) : T("The next theme starts tomorrow."), btn("inbox", "inbox"));
  }
  const DRAFT0 = () => ({ to: "drop", amount: 1, fee: null, expiry: "ok", height: "auto", signer: "you", payer: "you", seq: "next", rule: null, pay: true });
  const rnd = n => Math.floor(Math.random() * n);
  /* the kinds of offer: t = the lowest tier that gets it; brief/hint may hold {k} {a} {b}; check(d, x) says what is wrong
     with the draft for this contract, or null; x = { tx, base, tip } */
  const KINDS = [
    { k: "r-fee", t: 1, who: "qm", topic: "fee", want: ["FEE_LIMIT_TOO_LOW"], name: "Short change", brief: "Make the chain refuse a payment for its fee.", hint: "set fee 0" },
    { k: "r-sig", t: 1, who: "qm", topic: "sig", want: ["INVALID_SIGNATURE"], name: "Wrong hand", brief: "Make the chain refuse your payment for its signature.", hint: "set signer other" },
    { k: "r-height", t: 1, who: "look", topic: "height", want: ["TX_EXPIRED"], name: "Behind the tip", brief: "TX_EXPIRED by the block height alone: the expiry time must still be good.", hint: "set height past",
      check: d => d.height !== "past" ? "the height deadline is not behind the tip" : d.expiry === "past" ? "the expiry time has passed too; this one wants the height alone" : null },
    { k: "r-funds", t: 1, who: "qm", topic: "funds", want: ["INSUFFICIENT_FUNDS", "TX_REJECTED"], name: "Empty pockets", brief: "Pay the drop more than your wallet holds, but no more than a transfer can carry.", hint: "status shows your balance; set amount <a number above it>",
      check: d => d.amount >= GIANT ? "the amount is wider than a transfer; this one wants a real amount" : null },
    { k: "p-seq", t: 1, who: "qm", topic: "seq", want: "in", name: "Count your steps", brief: "Pay the drop your wallet’s next sequence number times {m}. The payment itself carries that number.", hint: "peek getsequence <your address>, then set amount", mk: j => { j.m = 2 + rnd(8); },
      check: (d, x, j) => d.amount !== x.tx.sequence_number * j.m ? F("{a} is not {b} × {m}", { a: d.amount, b: x.tx.sequence_number, m: j.m }) : null },
    { k: "p-race", t: 1, who: "look", topic: "height", want: "in", name: "Tight window", brief: "Land a payment to the drop whose own deadline (expire_at_height) is at most {m} blocks past the tip when you send it.", hint: "set height +{m}", mk: j => { j.m = 3 + rnd(4); },
      check: (d, x, j) => typeof d.height !== "number" || d.height > j.m ? F("the deadline is not within {m} blocks of the tip", { m: j.m }) : null },
    { k: "r-clock", t: 2, who: "look", topic: "clock", want: ["TX_EXPIRED"], name: "Stopped clock", brief: "TX_EXPIRED by the clock alone: the block-height deadline must still lie ahead.", hint: "set expiry past",
      check: d => d.expiry !== "past" ? "the expiry time has not passed" : d.height === "past" ? "the height deadline has passed too; this one wants the clock alone" : null },
    { k: "r-payer", t: 2, who: "qm", topic: "payer", want: ["TX_INVALID"], name: "Borrowed name", brief: "Name the drop as the payer, sign with your own key, and let the chain see through it.", hint: "set payer drop",
      check: d => d.payer !== "drop" ? "the payer is not the drop" : d.signer !== "you" ? "sign it with your own key" : null },
    { k: "r-seq", t: 2, who: "bosun", topic: "seq", want: ["INVALID_SEQUENCE"], name: "Yesterday’s number", brief: "A fresh payment, rightly signed, but with a sequence number your wallet has already used.", hint: "set seq old",
      check: d => d.seq !== "old" ? "the sequence number is the next one" : d.signer !== "you" ? "sign it with your own key" : null },
    { k: "r-width", t: 2, who: "look", topic: "width", want: ["TX_INVALID", "INVALID_PARAMS"], name: "One too wide", brief: "The smallest amount that is too wide for a transfer. Not one more.", hint: "two to the twenty-fourth",
      check: d => d.amount !== GIANT ? "that is not the smallest amount too wide" : null },
    { k: "p-hex", t: 2, who: "look", topic: "addr", want: "in", name: "Hidden in the address", brief: "Characters {a} to {b} of the drop’s address, counted from 1, are a number in hex. Pay the drop that number.", hint: "status shows the drop’s whole address; hex: a=10 … f=15",
      mk: j => { for (let i = 0; i < 20; i++) { j.a = 1 + rnd(90); j.b = j.a + (j.t >= 3 ? 2 : 1); if (parseInt(DROP.slice(j.a - 1, j.b), 16) > 0) break; } },
      check: (d, x, j) => { const n = parseInt(DROP.slice(j.a - 1, j.b), 16); return d.amount !== n ? F("{a} is not what characters {x} to {y} say", { a: d.amount, x: j.a, y: j.b }) : null; } },
    { k: "p-fee", t: 2, who: "qm", topic: "fee", want: "in", name: "Read the rules", brief: "Pay the drop the chain’s base fee times {m}.", hint: "peek getgovernance: the base fee is o9, in hex", mk: j => { j.m = 2 + rnd(19); },
      check: (d, x, j) => d.amount !== x.base * j.m ? F("{a} is not the base fee × {m}", { a: d.amount, m: j.m }) : null },
    { k: "p-doors", t: 2, who: "look", topic: "addr", want: "in", name: "Three doors", brief: "Three addresses, one of them the drop. Pay 1 test AGRS to the right one: set to a, b or c. The wrong one keeps your coin.", hint: "status shows the drop; read the middle, not the ends",
      mk: j => { j.door = rnd(3); j.mids = [0, 1, 2].map(() => Array.from({ length: 86 }, () => "0123456789abcdef"[rnd(16)]).join("")); },
      check: d => d.to !== "drop" && d.to !== "a" && d.to !== "b" && d.to !== "c" ? "set to a, b or c" : d.amount !== 1 ? "1 test AGRS, no more" : null },
    /* the node's transfer checks of 10 November 2026: a recipient that is no key, and a payment to the sender itself, are refused (TX_INVALID) */
    { k: "r-self", t: 1, who: "qm", topic: "addr", want: ["TX_INVALID"], ok: () => newChecks(), name: "Mirror", brief: "Make the chain refuse a payment for where it goes, and for nothing else: pay your own wallet.", hint: "set to me",
      check: d => d.to !== "me" ? "the payment does not go to your own wallet" : d.payer !== "you" ? "pay it from your own wallet" : null },
    { k: "p-nokey", t: 2, who: "look", topic: "addr", want: ["TX_INVALID"], ok: () => !!B && newChecks(), name: "No such wallet", brief: "Three addresses. Two are real wallets; one only looks like one and is no key at all. Send 1 test AGRS to that one: set to a, b or c. The chain must throw it back. Pick a real wallet and your coin is gone.", hint: "what curve",
      mk: j => { const real = () => B.bytesToHex(B.pubOf(B.keygen())); j.door = rnd(3); j.addrs = [0, 1, 2].map(i => i === j.door ? "01234567"[rnd(8)] + real().slice(1) : real()); },
      check: d => d.to !== "a" && d.to !== "b" && d.to !== "c" ? "set to a, b or c" : d.amount !== 1 ? "1 test AGRS, no more" : null },
    { k: "p-bits", t: 2, who: "qm", topic: "rule", want: "in", name: "How wide", brief: "The chain’s rule gives the base fee a type: bv[n], a bitvector n bits wide. Pay the drop n times {m}.", hint: "rule takes the rule apart", mk: j => { j.m = 2 + rnd(9); },
      check: (d, x, j) => !x.rule || d.amount !== x.rule.bits * j.m ? F("{a} is not the width times {m}", { a: d.amount, m: j.m }) : null },
    { k: "p-stream", t: 2, who: "look", topic: "rule", want: "in", name: "Which stream", brief: "In the chain’s rule the base fee is a stream with a number, written like o1[t]. Pay the drop that stream’s number plus the base fee.", hint: "rule takes the rule apart",
      check: (d, x) => !x.rule || d.amount !== x.rule.num + x.base ? F("{a} is not the stream’s number plus the base fee", { a: d.amount }) : null },
    { k: "p-ones", t: 3, who: "bosun", topic: "rule", want: "in", name: "Count the ones", brief: "Tau can write a constant in binary: {#b1010} is 10. Write the chain’s base fee in binary and pay the drop the number of 1s in it, times {m}.", hint: "what #b; the base fee is in rule", mk: j => { j.m = 3 + rnd(8); },
      check: (d, x, j) => d.amount !== ones(x.base) * j.m ? F("{a} is not the count of 1s times {m}", { a: d.amount, m: j.m }) : null },
    { k: "p-top", t: 3, who: "qm", topic: "rule", want: "in", name: "The top", brief: "In Tau a bare 1 in a bitvector is not the number one: 1:bv[{m}] is the top, every bit set. Pay the drop the value of 1:bv[{m}].", hint: "what top", mk: j => { j.m = 4 + rnd(5); },
      check: (d, x, j) => d.amount !== 2 ** j.m - 1 ? F("{a} is not 1:bv[{m}]", { a: d.amount, m: j.m }) : null },
    { k: "p-spec", t: 3, who: "bosun", topic: "rule", tau: true, want: null, name: "Write the rule", brief: "{x}", hint: "{y}",
      mk: j => { const ks = Object.keys(SPECS); j.spec = ks[rnd(ks.length)]; } },
    { k: "p-table", t: 2, who: "look", topic: "bool", tau: true, table: true, want: null, name: "Fill the table", brief: "A Boolean function of x and y, in Tau. Its table is on your screen: find a term that gives it. & is and, | is or, ' is not, ^ is exclusive or. Answer with tau and the term.", hint: "{y}",
      mk: j => { const ks = Object.keys(TABLES).filter(k => TABLES[k].v === 2); j.tab = ks[rnd(ks.length)]; } },
    { k: "p-table3", t: 3, who: "bosun", topic: "bool", tau: true, table: true, want: null, name: "Three wires", brief: "A Boolean function of x, y and z, in Tau. Its table is on your screen: find a term that gives it. Answer with tau and the term.", hint: "{y}",
      mk: j => { const ks = Object.keys(TABLES).filter(k => TABLES[k].v === 3); j.tab = ks[rnd(ks.length)]; } },
    /* heists: three contracts in a row under one trace; the pay comes at the end, the stage kinds do the work */
    { k: "h-vault", t: 3, who: "qm", heist: ["p-seq", "r-seq", "r-fee"], name: "The vault run", brief: "A job in three parts, one trace for all of it. Count the vault’s steps, then try yesterday’s number on its door, then knock with too little fee. Each part is a real payment; the pay comes at the end." },
    { k: "h-tide", t: 3, who: "look", heist: ["p-race", "r-height", "r-clock"], name: "Clock and tide", brief: "Three deadlines in a row, one trace for all of them. Land a payment inside a tight window, then get one refused by the block height alone, then by the clock alone." },
    { k: "h-ghost", t: 4, who: "bosun", heist: ["r-sig", "r-payer", "r-seq"], name: "The ghost key", brief: "Three disguises the chain must see through, one trace for all of them: a stranger’s signature, a borrowed payer, a used sequence number. Make it refuse each one." },
    { k: "h-rule", t: 4, who: "bosun", heist: ["p-bits", "p-table", "p-spec"], name: "The rule room", brief: "Into the room where the rules are kept, one trace for all of it. Read the width in the chain’s own rule, fill a truth table in Tau, then write a rule yourself." },
    { k: "r-fee9", t: 3, who: "qm", topic: "fee", want: ["FEE_LIMIT_TOO_LOW"], name: "Just under", brief: "FEE_LIMIT_TOO_LOW, but the fee limit may not be 0: exactly one under the base fee.", hint: "peek getgovernance: o9 is the base fee, in hex",
      check: (d, x) => d.fee !== x.base - 1 ? "the fee limit is not one under the base fee" : null },
    { k: "p-tight", t: 3, who: "qm", topic: "fee", want: "in", name: "Thin margin", brief: "Land a payment to the drop with a fee limit of at most twice the base fee.", hint: "peek getgovernance, then set fee",
      check: (d, x) => d.fee == null || d.fee > 2 * x.base ? "the fee limit is above twice the base fee" : null },
    { k: "p-last", t: 3, who: "look", topic: "height", want: "in", name: "Where it landed", brief: "Pay the drop the last three digits of the block your last sealed payment from this terminal landed in, plus one.", hint: "history lists your sealed payments and their blocks",
      ok: () => !!(S.hist[0] && S.hist[0].block != null),
      check: (d, x) => x.last == null || d.amount !== (x.last % 1000) + 1 ? F("{a} is not the right number", { a: d.amount }) : null },
    { k: "predict", t: 3, who: "bosun", topic: "order", want: "any", name: "Two faults", brief: "The draft is wrong in two ways already: {x} and {y}. Before you send, say which answer the node will give: predict <CODE>. Right pays in full.", hint: "the node stops at the first check it fails; which runs first?",
      mk: j => { const P = [[["fee", 0], ["payer", "drop"]], [["signer", "other"], ["expiry", "past"]], [["seq", "old"], ["fee", 0]], [["height", "past"], ["signer", "other"]], [["amount", GIANT], ["expiry", "past"]], [["payer", "drop"], ["seq", "old"]]][rnd(6)]; j.lock = P; } },
    { k: "r-blind", t: 4, who: "bosun", topic: null, want: null, name: "Blind order", brief: "Make the chain answer {x}. No hint from me this time.", hint: null,
      mk: j => { const C = ["FEE_LIMIT_TOO_LOW", "INVALID_SIGNATURE", "INVALID_SEQUENCE", "TX_EXPIRED", "INSUFFICIENT_FUNDS"][rnd(5)]; j.code = C; j.want = [C]; j.topic = CODE_TOPIC[C]; } },
    /* intel contracts: a wallet guarded by a personal rule nobody has shown you. Each probe is one transfer the real Tau
       engine on our server judges with that rule (intelAsk below); nothing goes to the chain. m = the probes that pay a
       point more; lead: the Lookout gives one number of the rule, so a window or hole is found by thinking, not sweeping */
    { k: "i-cap", t: 2, who: "look", topic: "guard", intel: true, want: null, ok: () => intelUp(), name: "The locked purse", brief: "A wallet guarded by a rule nobody has shown us. It lets transfers through up to some amount, or from some amount up: a round hundred, 20,000 at most. Find which and where with probe <amount>, then name cap <n> or name floor <n>. {m} probes or fewer pays a point more.", hint: "probe 0 first: a cap lets 0 through, a floor does not. Then halve: probe 10000, then the middle of what is left",
      mk: j => { j.seed = seedHex(); j.m = 9; j.trace = 50; } },
    { k: "i-edge", t: 2, who: "qm", topic: "guard", intel: true, final: true, want: null, ok: () => intelUp(), name: "One shot", brief: "A guard that lets transfers through up to some amount, a round hundred, 20,000 at most. Find the edge, the last amount that passes. Probe as often as you like, then final <amount>: one shot, and a miss loses the contract. {m} probes or fewer pays a point more.", hint: "halve the range: probe 10000, then the middle of what is left. The edge passes, and one more does not",
      mk: j => { j.seed = seedHex(); j.m = 9; j.trace = 50; } },
    { k: "i-band", t: 3, who: "bosun", topic: "guard", intel: true, lead: true, want: null, ok: () => intelUp(), name: "Window or hole", brief: "This guard lets only a window of amounts through, or everything but a hole: 500 to 5,000 wide, between round hundreds up to 20,000. The Lookout made out one of its numbers. Probe for the rest, then name band <from> <to> or name hole <from> <to>. {m} probes or fewer pays a point more.", hint: "probe the Lookout’s number: a window lets it through, a hole does not. The other end is 500 to 5,000 above it; halve towards it",
      mk: j => { j.seed = seedHex(); j.m = 8; j.trace = 60; } },
    { k: "i-blind", t: 4, who: "bosun", topic: "guard", intel: true, lead: true, want: null, ok: () => intelUp(), name: "The blind guard", brief: "A guard, and little to go on: a cap, a floor, a window, a hole, or a rule that lets nothing through. The Lookout made out one number in it. Probe, think, then name it. Mind what a rule leaves unsaid. {m} probes or fewer pays a point more. No hint from me.", hint: null,
      mk: j => { j.seed = seedHex(); j.m = 10; j.trace = 60; } },
    /* rules on the chain (IDNI tau-testnet 5ad1bb7, 13 November 2026): a wallet's own rule is a transaction of its own.
       The three refusals bind nothing: a refused rule never reaches the wallet */
    { k: "r-pack", t: 2, who: "qm", topic: "clause", rules: true, want: ["RULE_WITH_TRANSFERS"], name: "One parcel", brief: "Make the chain refuse a payment for what else it carries: put a rule into the same transaction. The rule that changes nothing will do.", hint: "set rule allow",
      check: d => !d.rule ? "the transaction carries no rule" : d.pay === false ? "the payment is off" : null },
    { k: "r-mix", t: 3, who: "bosun", topic: "clause", rules: true, want: ["MIXED_OUTPUT_RULE"], name: "Two pens", brief: "A rule that writes your wallet’s o5 and the chain’s fee stream o9 at once. Send it alone and let the chain refuse it for that.", hint: "set rule mix, set pay off",
      check: d => d.rule !== "mix" ? "the rule does not write two streams" : null },
    { k: "r-long", t: 3, who: "look", topic: "clause", rules: true, want: ["TX_REJECTED"], name: "One too long", brief: "A wallet’s rule may hold only so many comparisons. Send the shortest rule that is one too long, alone, without a payment.", hint: "what clause; set rule size <n>, set pay off",
      check: d => d.rule !== "size" ? "that is not a rule of plain comparisons (set rule size <n>)" : d.size !== CLAUSE_MAX + 1 ? F("{n} comparisons is not the shortest rule too long", { n: d.size }) : null },
    /* a heist on your own wallet: put a rule on it, be stopped by it, take it off. Every part is a real transaction; unguard
       takes the rule off at any time */
    { k: "h-hands", t: 2, who: "qm", heist: ["g-set", "g-hit", "g-off"], ok: () => !S.guard, name: "Your own hands", brief: "Three parts, one trace: put a rule on your own wallet, let it stop you, take it off again. Nobody else can sign a rule for your wallet, and nobody but you can lift it." },
    { k: "g-set", t: 2, who: "qm", topic: "clause", rules: true, guard: true, stage: true, want: "in", name: "Bind your hands", brief: "Put a rule on your own wallet: at most {a} test AGRS a payment. A rule is a transaction of its own, without a payment.", hint: "set rule cap {a}, set pay off",
      mk: j => { if (j.a == null) j.a = 100 * (2 + rnd(8)); },
      check: (d, x, j) => d.rule !== "cap" || d.cap !== j.a ? F("the rule is not a cap of {a}", { a: j.a }) : d.pay !== false ? "the payment is still on" : null },
    { k: "g-hit", t: 2, who: "qm", topic: "guard", guard: true, stage: true, want: ["TX_REJECTED"], name: "Stopped by yourself", brief: "Now pay the drop more than {a}. Your own rule must stop you, before a coin moves.", hint: "set amount <more than your cap>",
      check: (d, x, j) => !ownRule(x.said) ? "the chain refused it, but not for your own rule" : d.amount <= j.a ? "that amount is within your cap" : null },
    { k: "g-off", t: 2, who: "qm", topic: "clause", rules: true, guard: true, stage: true, want: "in", name: "Hands free", brief: "Take the rule off again: send the rule that says o5 = 1 and nothing else, alone.", hint: "set rule allow, set pay off",
      check: d => d.rule !== "allow" ? "that is not the rule that takes a rule away" : d.pay !== false ? "the payment is still on" : null },
    /* the three showcase wallets Tau HUD runs on the testnet (infra/relay/showcase.py): their rules are real and in force,
       and anyone may read them (showcase) */
    { k: "s-four", t: 2, who: "look", topic: "guard", want: "in", ok: () => showUp("foureyes"), name: "Four eyes", brief: "Tau HUD’s four-eyes wallet carries a rule on the testnet: above some amount, it needs its co-signer. Read the rule and pay the drop the smallest amount that needs the co-signer.", hint: "showcase: in the rule, i1 is the amount, in hex",
      check: d => { const n = showNum("foureyes"); return n == null ? "the four-eyes wallet’s rule could not be read" : d.amount !== n + 1 ? F("{a} is not the smallest amount that needs the co-signer", { a: d.amount }) : null; } },
    { k: "s-piggy", t: 2, who: "qm", topic: "guard", want: "in", ok: () => showUp("piggy"), name: "The piggy bank", brief: "Tau HUD’s piggy bank carries a rule that reads i5, the block’s time in seconds since 1970. Until that moment nothing leaves it. Pay the drop the year in which it opens, German time.", hint: "showcase, then when <seconds>",
      check: d => { const y = showYear(); return y == null ? "the piggy bank’s rule could not be read" : d.amount !== y ? F("{a} is not the year it opens", { a: d.amount }) : null; } },
    { k: "s-feed", t: 1, who: "bosun", topic: "guard", want: "in", ok: () => showUp("feeding"), name: "Feed it right", brief: "Tau HUD’s feeding fund may only pay Agorzilla’s bowl, and only so much a meal. Read its rule and feed Agorzilla exactly that much, from your own wallet.", hint: "showcase: i1 is the amount, in hex; set to bowl",
      check: d => { const n = showNum("feeding"); return d.to !== "bowl" ? "the payment does not go to Agorzilla’s bowl" : n == null ? "the feeding fund’s rule could not be read" : d.amount !== n ? F("{a} is not what the fund may pay a meal", { a: d.amount }) : null; } },
  ];
  const kindOf = j => { const b = KINDS.find(x => x.k === j.k); return b && b.heist && j.hs != null ? KINDS.find(x => x.k === b.heist[j.hs]) : b; };
  const heistOf = j => { const b = KINDS.find(x => x.k === j.k); return b && b.heist ? b : null; };
  const jobName = j => { const h = heistOf(j); return h ? T(h.name) + " · " + F("{a}/{b}", { a: (j.hs || 0) + 1, b: h.heist.length }) : T(kindOf(j).name); };
  function heistShow(j) {
    const h = heistOf(j); if (!h) return;
    cols(h.heist.map((k, i) => [(i < j.hs ? "✓ " : i === j.hs ? "● " : "○ ") + F("part {n}", { n: i + 1 }), T(KINDS.find(x => x.k === k).name)]));
  }
  /* a heist's next stage: the stage kind sets its own numbers */
  function heistStage(j, n) {
    const h = heistOf(j); j.hs = n; delete j.m; delete j.tab; delete j.spec;
    const kd = KINDS.find(x => x.k === h.heist[n]); if (kd.mk) kd.mk(j);
  }
  /* the hint's first step as a command, one click away: the answer itself for the plain refusals, the place to look it up for the puzzles */
  const TRY = { "r-fee": "set fee 0", "r-sig": "set signer other", "r-height": "set height past", "r-funds": "status", "p-seq": "peek getsequence me", "p-race": "set height +{m}",
    "r-clock": "set expiry past", "r-payer": "set payer drop", "r-seq": "set seq old", "r-width": "what width", "p-hex": "status", "p-fee": "peek getgovernance", "p-doors": "status", "r-self": "set to me", "p-nokey": "what curve",
    "r-fee9": "peek getgovernance", "p-tight": "peek getgovernance", "p-last": "history", "predict": "what order",
    "p-bits": "rule", "p-stream": "rule", "p-ones": "what #b", "p-top": "what top", "p-spec": "what stream", "p-table": "what and", "p-table3": "what and",
    "i-cap": "probe 0", "i-edge": "probe 10000", "i-band": "probe {lead}",
    "r-pack": "set rule allow", "r-mix": "set rule mix", "r-long": "what clause", "g-set": "set rule cap {a}", "g-hit": "tx", "g-off": "set rule allow", "s-four": "showcase", "s-piggy": "showcase", "s-feed": "showcase" };
  const tryCmd = j => { const k = j && kindOf(j).k; if (!k || !TRY[k]) return null; const v = { m: j.m, a: j.a }; if (j.lead != null) v.lead = j.lead; const c = fill0(TRY[k], v); return c.includes("{") ? null : c; };
  const hintLine = j => { const kd = kindOf(j), go = tryCmd(j), plainHint = !(j.lock || j.code || j.tab || j.spec);   // an English filler, so the dictionaries translate the whole line
    say("learn", F("Hint: {x}", { x: plainHint ? fill0(kd.hint, { m: j.m, a: j.a, b: j.b }) : fill(kd.hint, j) }), go ? btn(go, go) : null); };
  const LOCK_TEXT = { fee: "fee limit 0", payer: "the drop named as payer", signer: "a stranger’s signing key", expiry: "an expiry time in the past", seq: "a used sequence number", height: "a height deadline behind the tip", amount: "an amount of 2^24" };
  const inboxOpen = () => chapterDone(CH[0]);
  const tierMax = () => { const r = rep(); return r >= 35 ? 4 : r >= 12 ? 3 : r >= 4 ? 2 : 1; };
  const jobOf = n => S.inbox.find(j => j.n === n) || null;
  const curJob = () => (S.job ? jobOf(S.job) : null);
  const cur = () => (S.taken ? byId(S.taken) : curJob());
  const jname = j => "j" + j.n;
  const fill = (s, j) => { const v = {}; for (const k of ["m", "a", "b"]) if (j[k] != null) v[k] = j[k]; if (j.lock) { v.x = T(LOCK_TEXT[j.lock[0][0]]); v.y = T(LOCK_TEXT[j.lock[1][0]]); } else if (j.code) v.x = j.code; else if (j.tab && TABLES[j.tab] && s === "{y}") return T(TABLES[j.tab].hint); else if (j.spec && SPECS[j.spec]) return s === "{x}" ? T(SPECS[j.spec].brief) : s === "{y}" ? T(SPECS[j.spec].hint) : F(s, v); return F(s, v); };
  function makeJob() {
    const max = tierMax(), have = new Set(S.inbox.map(j => j.k));
    const heistIn = S.inbox.some(j => heistOf(j)), pool = KINDS.filter(x => x.t <= max && !x.stage && !have.has(x.k) && (!x.ok || x.ok()) && (!x.heist || (!heistIn && Math.random() < 0.35)));
    if (!pool.length) return null;
    const th = theme(), hot = pool.filter(x => th.topics.includes(x.topic)), top = pool.filter(x => x.t === max);
    const pickFrom = hot.length && Math.random() < 0.4 ? hot : top.length && Math.random() < 0.5 ? top : pool, kd = pickFrom[rnd(pickFrom.length)];
    S.jseq = (S.jseq || 0) + 1;
    const j = { n: S.jseq, k: kd.k, t: Math.max(kd.t, Math.min(max, kd.t + rnd(2))), who: kd.who, topic: kd.topic, born: CHAIN.tip ?? 0, until: (CHAIN.tip ?? 0) + 100 + rnd(80) };
    j.trace = { 1: 40, 2: 30, 3: 24, 4: 16 }[j.t];
    if (kd.mk) kd.mk(j);
    if (th.topics.includes(kd.topic)) { j.special = (j.special || 0) + PAYS[j.t]; j.themed = th.k; }
    if (kd.heist) { heistStage(j, 0); j.special = 2 * kd.heist.length; j.trace = 26 * kd.heist.length; j.until += 60; }
    return j;
  }
  /* the two contracts above need a node that has the transfer checks of 10 November 2026: before them, a node took a
     payment to the sender or to no key. Asked once a visit with a dry run (checktx) of a payment to itself from a throwaway
     key: TX_INVALID means the node has them; anything else keeps the two contracts off the board */
  let NEWCHK = null;
  function newChecks() {
    if (SIM) return true;
    if (NEWCHK === null && B) {
      NEWCHK = "asking";
      (async () => {
        try {
          const sk = B.keygen(), pk = B.bytesToHex(B.pubOf(sk)), st = await ask("getsequence " + pk), tip = Number(st && st.data && st.data.tip_height) || 0, base = await fee();
          const tx = sign({ tx_type: "user_tx", sender_pubkey: pk, sequence_number: 0, expiration_time: now() + 600, expire_at_height: tip + 1000, fee_limit: String(base * 5),
            operations: { "1": [[pk, pk, "1"]] } }, sk);
          const r = await ask("checktx " + JSON.stringify(tx));
          NEWCHK = !!r && !isOk(r) && codeOf(r) === "TX_INVALID";
        } catch (e) { NEWCHK = false; }
      })();
    }
    return NEWCHK === true;
  }
  function jobTick(tip) {
    if (!inboxOpen() || tip == null) return;
    let changed = false;
    if (!S.inboxHi) {
      S.inboxHi = true; S.pane = "inbox"; S.nextJob = tip + 3; changed = true;
      while (S.inbox.length < 3) { const j = makeJob(); if (!j) break; S.inbox.push(j); }
      setTimeout(() => tutAt("inbox"), 4000);
      crew("qm", "Chapter one is behind you, so the crew trusts you with its own work. The inbox fills by itself, a contract every few blocks. Each is a puzzle about the chain, answered with a real transaction you build yourself. Clear what you can, decline what you do not want; harder work comes as your rank grows.", "glad");
      say("sys", T("The inbox is open."), btn("inbox", "inbox"));
    }
    for (const j of S.inbox.filter(x => x.until < tip && S.job !== x.n)) { archive(j, "lapsed", 0); changed = true; }
    const news = [];
    while (S.inbox.length < 2) { const j = makeJob(); if (!j) break; S.inbox.push(j); news.push(j); }
    if (S.inbox.length < 4 && tip >= (S.nextJob || 0)) { const j = makeJob(); if (j) { S.inbox.push(j); news.push(j); } S.nextJob = tip + 5 + rnd(6); }
    const dj = dailyTick(tip); if (dj) { news.push(dj); changed = true; }
    if (news.length || changed) { save(); jobs(); instruments(); chips(); }
    if (news.length && S.booted) {
      snd.mail(); const j = news[news.length - 1];
      say("sys", news.length > 1 ? F("{n} new contracts in the inbox.", { n: news.length }) : F("New contract in the inbox: {x} {t}, from the {w}.", { x: jname(j), t: heistOf(j) ? heistOf(j).name : kindOf(j).name, w: CREW[j.who] }), btn(F("read {x}", { x: jname(j) }), "read " + jname(j)));
      if (dj) say("ok", F("★ Today’s order: {x}. It pays {n} more for the streak; settle it today, German time.", { x: jname(dj), n: dj.dbonus }), btn(F("read {x}", { x: jname(dj) }), "read " + jname(dj)));
    }
  }
  function archive(j, out, pts, extra) {
    S.inbox = S.inbox.filter(x => x.n !== j.n);
    if (S.job === j.n) { S.job = null; S.deadline = null; S.span = null; S.draft = null; S.pred = null; }
    S.arch.unshift({ n: j.n, k: j.k, t: j.t, out, pts, at: Date.now(), block: CHAIN.tip, ...(extra || {}) }); S.arch = S.arch.slice(0, 60);
    save();
  }
  const parseJ = a => { const m = /^j?(\d+)$/.exec(a || ""); return m ? jobOf(+m[1]) : null; };
  const stars = t => "▮".repeat(t) + "▯".repeat(4 - t);
  function inboxList() {
    if (!inboxOpen()) { say("sys", T("The inbox opens when chapter 1 is done: four contracts, then the crew sends work of its own, without end.")); return; }
    jobTick(CHAIN.tip);
    if (!S.inbox.length) { say("sys", T("The inbox is empty for the moment; a new contract comes within a few blocks.")); return; }
    say("sys", F("Inbox: {n} open. Tier {t} of 4 is open to you.", { n: S.inbox.length, t: tierMax() }) + " " + F("This week: {x}.", { x: theme().name }), btn("week", "week"));
    cols(S.inbox.map(j => [jname(j) + (S.job === j.n ? " ●" : "") + (j.daily ? " ★" : ""), jobName(j) + " · " + stars(j.t) + " · " + T(CREW[j.who]) + " · " + F("+{n}", { n: PAYS[j.t] + (j.special || 0) }) + " · " + F("lapses at block {n}", { n: fmt(j.until) })]));
    const j = S.inbox.find(x => S.job !== x.n) || S.inbox[0];
    say("sys", T("read <j> opens one; accept <j> takes it; decline <j> clears it."), btn(F("read {x}", { x: jname(j) }), "read " + jname(j)));
  }
  function readJob(a) {
    const j = parseJ(a) || (a ? null : curJob() || S.inbox[0]); if (!j) { noJob(a); return; }
    const kd = kindOf(j), h = heistOf(j);
    say("sys", F("{x} · {t} · tier {n} · from the {w}", { x: jname(j), t: h ? h.name : kd.name, n: j.t, w: CREW[j.who] }));
    transmit(j.who, fill((h || kd).brief, j), { k: j.k, n: j.n, name: (h || kd).name, tier: j.t });
    if (h) heistShow(j);
    if (j.daily) say("ok", F("★ Today’s order: {n} points more for your streak, if you settle it today.", { n: j.dbonus || 1 }));
    if (doors(j)) cols(["a", "b", "c"].map((x, i) => [x, doorAddr(j, i)]));
    if (j.tab) tableShow(j);
    if (j.t <= 2 && kd.hint) hintLine(j);
    if (S.job !== j.n) { S.lastRead = j.n; save(); chips(); }
    say("sys", F("Pays +{n} standing. Trace once taken: {m} blocks.", { n: PAYS[j.t] + (j.special || 0), m: j.trace }) + (j.topic ? " " + F("Topic: {x}.", { x: TOPICS[j.topic][0] }) : ""),
      S.job === j.n ? btn("tx", "tx") : btn(F("accept {x}", { x: jname(j) }), "accept " + jname(j)), S.job === j.n ? null : btn(F("decline {x}", { x: jname(j) }), "decline " + jname(j)));
  }
  /* a contract that is not (or no longer) in the inbox: say why and offer what is there */
  function noJob(a) {
    if (!inboxOpen()) { say("sys", T("The inbox opens when chapter 1 is done: four contracts, then the crew sends work of its own, without end."), nextChip()); return; }
    const gone = a && S.arch.find(x => "j" + x.n === String(a).replace(/^j?/, "j"));
    say("sys", gone ? F("{x} is no longer in the inbox ({y}).", { x: jname(gone), y: gone.out }) : T("No such contract in the inbox."));
    if (S.inbox.length) say("sys", T("Open now:"), ...S.inbox.map(j => btn(F("read {x}", { x: jname(j) }), "read " + jname(j))));
    else say("sys", T("The inbox is empty for the moment; a new contract comes within a few blocks."));
  }
  const doors = j => !!j && (j.k === "p-doors" || j.k === "p-nokey");
  const doorAddr = (j, i) => (j.k === "p-nokey" ? j.addrs[i] : i === j.door ? DROP : DROP.slice(0, 6) + j.mids[i] + DROP.slice(-4));
  const draftTo = (j, d, pk) => (d.to === "me" ? pk : d.to === "drop" ? DROP : d.to === "bowl" ? BOWL : doorAddr(j, "abc".indexOf(d.to)));
  function accept(a) {
    const j = parseJ(a) || (a ? null : S.inbox[0]); if (!j) { say("sys", T("No such contract in the inbox. Type inbox.")); return; }
    if (S.job === j.n) { say("sys", F("{x} is yours already. Build it: tx, set, send.", { x: jname(j) }), btn("tx", "tx")); return; }
    if (RUN.busy) { say("warn", T("A contract is under way; wait for the chain’s answer.")); return; }
    if (S.taken || S.job) { say("warn", T("Finish or drop the taken contract first (drop).")); return; }
    if (heat() >= 80) { say("warn", F("Tracer heat {n}: the crew hands out no work while the Tracer has your scent. It falls 1 a block.", { n: heat() }), btn("heat", "heat")); return; }
    S.job = j.n; S.draft = DRAFT0(); S.pred = null; j.hinted = j.t <= 2; S.lastRead = null; S.jobStep = false; S.jobMiss = false;
    if (j.lock) for (const [f, v] of j.lock) S.draft[f] = v;
    const span = heatSpan(j.trace);
    S.span = span; S.deadline = CHAIN.tip != null ? CHAIN.tip + span : null; save(); jobs(); instruments(); topbar(); chips();
    say("sys", F("{x} taken: {t}.", { x: jname(j), t: heistOf(j) ? heistOf(j).name : kindOf(j).name }) + " " + (S.deadline != null ? F("Trace: until block {n} ({t}).", { n: fmt(S.deadline), t: inTimeE(span) || fill0("{n} blocks", { n: span }) }) : ""));
    if (span < j.trace) say("warn", F("Tracer heat {n}: this trace is {m} blocks shorter.", { n: heat(), m: j.trace - span }), btn("heat", "heat"));
    if (heistOf(j)) say("sys", F("A heist: {n} parts, one trace. Part {a} now: {t}.", { n: heistOf(j).heist.length, a: (j.hs || 0) + 1, t: kindOf(j).name }));
    if (kindOf(j).table) { say("sys", T("This one is answered in Tau, not with a payment: type tau and a term in x and y (and z). This terminal checks it against every row."), btn("what and", "what and")); tableShow(j); }
    else if (kindOf(j).tau) say("sys", T("This one is answered in Tau, not with a payment: type tau and your line. The Tau checker on our server runs it."), btn("what tau", "what tau"));
    else if (kindOf(j).intel) intelStart(j);
    else { say("sys", T("Your draft is a plain payment of 1 test AGRS to the drop. Change it with set, look at it with tx, send it with send."));
    draftShow(); }
    if (j.hinted && kindOf(j).hint) hintLine(j);
    if (j.t >= 3 && kindOf(j).hint) say("sys", T("No hint at this tier. hint gives one, for 1 point of the pay."), btn("hint", "hint"));
    watch();
  }
  function decline(a) {
    const j = parseJ(a); if (!j) { say("sys", T("decline <j>: a contract from the inbox (inbox lists them).")); return; }
    if (S.job === j.n) { say("warn", T("That one is taken: drop it first, then decline.")); return; }
    archive(j, "declined", 0); jobs(); instruments(); chips();
    say("sys", F("{x} cleared from the inbox. A new one comes within a few blocks.", { x: jname(j) }));
  }
  function hintJob() {
    const j = curJob(); if (!j) { say("sys", T("Take a contract from the inbox first.")); return; }
    const kd = kindOf(j); if (!kd.hint) { say("sys", T("The Bosun gives no hints for this one.")); return; }
    if (!j.hinted) { j.hinted = true; save(); say("sys", T("Hint taken: this contract pays 1 point less.")); }
    S.jobStep = false; save(); hintLine(j); chips();
  }
  function draftShow() {
    { const ij = intelJob(); if (ij) { intelShow(ij); return; } }
    const d = S.draft; if (!d) { say("sys", T("No draft: accept a contract from the inbox first.")); return; }
    const j = curJob(), locked = new Set(((j && j.lock) || []).map(x => x[0]));
    const L = k => (locked.has(k) ? " 🔒" : "");
    cols([
      ["to", (d.to === "drop" ? T("the drop") + " " + short(DROP) : d.to === "bowl" ? T("Agorzilla’s bowl") + " " + short(BOWL) : d.to === "me" ? T("your own wallet") + (myPk() ? " " + short(myPk()) : "") : d.to + " " + short(doorAddr(j, "abc".indexOf(d.to)))) + L("to")],
      ["amount", fmt(d.amount) + " " + T("test AGRS") + L("amount")],
      ["fee", (d.fee == null ? T("auto: 5 × the base fee") : String(d.fee)) + L("fee")],
      ["expiry", (d.expiry === "past" ? T("two minutes ago") : T("in ten minutes")) + L("expiry")],
      ["height", (d.height === "past" ? T("five blocks behind the tip") : d.height === "auto" ? T("1,000 blocks ahead") : F("{n} blocks past the tip", { n: d.height })) + L("height")],
      ["signer", (d.signer === "other" ? T("a stranger’s key, made now") : T("your key")) + L("signer")],
      ["payer", (d.payer === "drop" ? T("the drop") : T("your wallet")) + L("payer")],
      ["seq", (d.seq === "old" ? T("a used one (next − 1)") : T("the next one")) + L("seq")],
      ...(kindOf(j).rules || d.rule || d.pay === false ? [
        ["rule", !d.rule ? T("none") : d.rule === "allow" ? T("o5 = 1 and nothing else: takes a rule away") : d.rule === "cap" ? F("at most {n} test AGRS a payment", { n: fmt(d.cap) }) : d.rule === "mix" ? T("writes o5 and o9") : F("{n} comparisons", { n: d.size })],
        ["pay", d.pay === false ? T("off: the rule goes alone") : T("on: the payment above goes too")]] : []),
    ]);
    if (d.rule) say("sys", ruleText(d).length > 200 ? ruleText(d).slice(0, 197) + "…" : ruleText(d));
    say("sys", kindOf(j).rules ? T("set to|amount|fee|expiry|height|signer|payer|seq|rule|pay <value> · reset · send") : T("set to|amount|fee|expiry|height|signer|payer|seq <value> · reset · send"), btn("send", "send"));
  }
  function setDraft(args) {
    const d = S.draft, j = curJob(); if (!d || !j) { say("sys", T("No draft: accept a contract from the inbox first.")); return; }
    if (kindOf(j).intel) { say("sys", T("This one has no draft: probe <amount> asks the guard."), btn("probes", "probes")); return; }
    const [f, v] = args;
    if (j.lock && j.lock.some(x => x[0] === f)) { say("warn", F("{x} is locked in this contract: it is one of the two faults.", { x: f })); return; }
    const n = v != null && /^\d+$/.test(v) ? parseInt(v, 10) : null;
    const ok = (() => {
      if (f === "amount" && n != null && n <= GIANT * 2) return d.amount = n, true;
      if (f === "fee" && (v === "auto" || n != null && n < 1e6)) return d.fee = v === "auto" ? null : n, true;
      if (f === "expiry" && (v === "past" || v === "ok")) return d.expiry = v, true;
      if (f === "height") { const m = /^\+?(\d+)$/.exec(v || ""); if (v === "past" || v === "auto") return d.height = v, true; if (m && +m[1] >= 1 && +m[1] <= 1000) return d.height = +m[1], true; }
      if (f === "signer" && (v === "you" || v === "other")) return d.signer = v, true;
      if (f === "payer" && (v === "you" || v === "drop")) return d.payer = v, true;
      if (f === "seq" && (v === "next" || v === "old")) return d.seq = v, true;
      if (f === "to" && (v === "drop" || v === "me" || v === "bowl" || (doors(j) && ["a", "b", "c"].includes(v)))) return d.to = v, true;
      if (f === "pay" && (v === "on" || v === "off")) return d.pay = v === "on", true;
      if (f === "rule") {
        const k = args[2] != null && /^\d+$/.test(args[2]) ? parseInt(args[2], 10) : null;
        if (v === "off" || v === "none") return d.rule = null, true;
        if (v === "allow" || v === "mix") return d.rule = v, true;
        if (v === "size" && k >= 1 && k <= 64) return d.rule = "size", d.size = k, true;
        if (v === "cap" && k >= 1 && k < GIANT) {
          if (!kindOf(j).guard) return say("warn", T("A cap would become your wallet’s own rule for every payment it makes. Only the contract Your own hands puts one on.")), "said";
          return d.rule = "cap", d.cap = k, true;
        }
      }
      return false;
    })();
    if (ok === "said") return;
    if (!ok) { cols([["set amount <n>", T("whole test AGRS")], ["set fee <n>|auto", T("the fee limit you sign")], ["set expiry past|ok", T("the expiry time")], ["set height past|+<n>|auto", T("the last block it may land in")], ["set signer you|other", T("whose key signs")], ["set rule allow|mix|size <n>|off · set pay on|off", T("a rule in the same transaction")], ["set payer you|drop", T("who pays, inside the transfer")], ["set seq next|old", T("the sequence number")], ["set to drop|me" + (doors(j) ? "|a|b|c" : ""), T("who receives")]]); return; }
    save(); say("ok", F("{f} set.", { f }), btn("tx", "tx"), btn("send", "send"));
  }
  function predict(a) {
    const j = curJob(); if (!j || j.k !== "predict") { say("sys", T("predict belongs to the contract Two faults.")); return; }
    const c = String(a || "").toUpperCase(); if (!CODES.includes(c)) { say("sys", T("predict <CODE>, one of:") + " " + CODES.slice(0, 8).join(" · ")); return; }
    S.pred = c; save(); say("ok", F("Prediction: {x}. Now send.", { x: c }), btn("send", "send"));
  }
  /* the draft's faults: what the chain must refuse whatever the contract wants */
  const faults = (d, x) => [d.fee != null && d.fee < x.base && "fee", d.expiry === "past" && "expiry", d.height === "past" && "height", d.signer === "other" && "signer", d.payer === "drop" && "payer", d.seq === "old" && "seq", d.pay !== false && d.amount >= GIANT && "amount",
    d.rule && d.pay !== false && "parcel", d.rule === "mix" && "mix", d.rule === "size" && d.size > CLAUSE_MAX && "size"].filter(Boolean);
  async function jobSend() {
    const j = curJob(), d = S.draft; if (!j || !d) { say("sys", T("No contract from the inbox taken. Type inbox.")); return; }
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    if (kindOf(j).tau) { say("sys", T("This one is answered in Tau: tau <your line>."), btn("what tau", "what tau")); return; }
    if (kindOf(j).intel) { say("sys", kindOf(j).final ? T("This one is answered with probes, not with a payment: probe <amount>, then final <amount>.") : T("This one is answered with probes, not with a payment: probe <amount>, then name what the guard does."), btn("probes", "probes")); return; }
    if (!B) { say("no", T("This browser cannot sign (no BLS library loaded).")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent. Try again in a minute, or switch to the simulation in the header."), btn("reboot", "reboot")); return; }
    if (j.k === "predict" && !S.pred) { say("sys", T("Predict first: predict <CODE>. Then send."), btn("predict TX_INVALID", "predict TX_INVALID")); return; }
    if (doors(j) && (d.to === "drop" || d.to === "me")) { say("sys", T("Choose a door first: set to a, b or c.")); return; }
    const kd = kindOf(j), want = j.want || kd.want;
    RUN.busy = true; chips(); slot(jname(j));
    const k = myKey(true), last = S.hist[0] && S.hist[0].block != null ? Number(S.hist[0].block) : null;   // the last sealed payment before this one (Where it landed)
    try {
      const { seq, tip } = await envelope(k.pk), base = await fee(), t = now();
      if (d.seq === "old" && seq === 0) fail(T("This wallet has no used sequence number yet."));
      const to = draftTo(j, d, k.pk), rt = ruleText(d), ops = {};
      if (rt) ops["0"] = rt;
      if (d.pay !== false) ops["1"] = [[d.payer === "drop" ? DROP : k.pk, to, String(d.amount)]];
      if (!rt && d.pay === false) fail(T("Nothing to send: the payment is off and the draft has no rule."));
      if (d.rule === "size" && d.size <= CLAUSE_MAX && d.pay === false) fail(F("A rule of {n} comparisons fits: sent alone, it would become your wallet’s own rule. This contract wants one the chain refuses.", { n: d.size }));
      if (d.rule === "cap" && !kd.guard) fail(T("A cap would become your wallet’s own rule for every payment it makes. Only the contract Your own hands puts one on."));
      const tx = sign({ tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: d.seq === "old" ? seq - 1 : seq, expiration_time: d.expiry === "past" ? t - 120 : t + 600,
        expire_at_height: d.height === "past" ? Math.max(1, tip - 5) : d.height === "auto" ? tip + 1000 : tip + d.height, fee_limit: String(d.fee == null ? base * 5 : d.fee),
        operations: ops }, d.signer === "other" ? B.keygen() : k.sk);
      const x = { tx, base, tip, last, rule: ruleNow() }, bad = faults(d, x);
      if (ops["1"] && (to === k.pk || !/^[89ab]/.test(to))) bad.push("to");   // to the sender itself, or to no key: refused since 10 November 2026
      say("step", ops["1"] ? F("signing the draft: {a} test AGRS, fee limit {b}, sequence {c}, deadline block {n}", { a: fmt(d.amount), b: tx.fee_limit, c: tx.sequence_number, n: fmt(tx.expire_at_height) })
        + (rt ? " · " + T("with a rule in the same transaction") : "") : F("signing a rule of its own: {n} comparisons, fee limit {b}, sequence {c}", { n: comparisons(rt), b: tx.fee_limit, c: tx.sequence_number }));
      if (RUN.dry) {
        const r = await ask("checktx " + JSON.stringify(tx)); if (!r) fail(T("No answer from the node; nothing was sent."));
        const bad2 = r.status !== "ok" || (r.data && r.data.ok === false), c1 = bad2 ? codeOf(r) : null;
        say(bad2 ? "warn" : "ok", bad2 ? F("Dry run: the node would refuse it: {x}", { x: c1 || plain(r) }) : T("Dry run: the node would take it."));
        say("sys", T("Nothing was sent. send sends it for real."), btn("send", "send"));
        return;
      }
      const s = await sendtx(tx);
      if (!s.r) fail(T("No answer from the node; nothing was sent. Type send again."));
      if (s.hash) {
        sent(tx, s);
        if (bad.length) {   // taken although it must be refused: a finding, kept in this browser only
          slotFail(T("taken: a finding")); say("no", T("The chain took it. That is not how it should be."));
          S.findings.push({ at: Date.now(), id: j.k, tx, answer: s.r }); save();
          say("warn", T("A finding: the testnet did something it must not. The record is kept in this browser (type findings) and nowhere else. Please pass it on:"), link("/findings/" + lang(), T("how to report a finding")));
          return;
        }
        say("step", T("waiting for a block …"));
        const w = await sealed(s.hash, S.deadline, s.way);
        if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why) && S.deadline != null && CHAIN.tip > S.deadline) jobTraced(); return; }
        say("ok", F("Sealed in block {n}.", { n: fmt(w.block) }), explorer(s.hash));
        if (rt && !ops["1"]) { S.guard = isNeutral(rt) ? null : d.rule === "cap" ? { cap: d.cap, block: w.block } : S.guard; save(); instruments();
          say("learn", S.guard ? F("Your wallet now carries its own rule: at most {n} test AGRS a payment. The chain checks every payment it makes against it. unguard takes it off.", { n: fmt(S.guard.cap) }) : T("Your wallet carries no rule of its own now.")); }
        if (ops["1"]) { S.hist.unshift({ id: j.k, hash: s.hash, block: w.block, amount: d.amount }); S.hist = S.hist.slice(0, 20); save(); }
        if (ops["1"] && to === BOWL) say("sys", T("Agorzilla counts it as a meal: one a wallet an hour."), link("https://agorzilla.com/", "agorzilla.com"));
        if (j.k === "p-nokey") { snd.no(); flash("bad"); say("no", T("That was a real wallet: your coin went to a stranger, and it stays there. The address that is no key gives itself away in its first character.")); jobMiss(j, x); return; }
        if (want !== "in") { say("warn", ops["1"] ? T("The payment was good, so the chain took it; this contract wanted a refusal. Look at the draft again.") : T("The rule was good, so the chain took it; this contract wanted a refusal. Look at the draft again.")); learnTopic(j.topic); heatAdd(8); return; }
        if (j.k === "p-doors" && to !== DROP) { snd.no(); flash("bad"); say("no", T("That door was a lookalike: your coin went to a wallet that is not the drop, and it stays there. The middle of an address is where it differs.")); jobMiss(j, x); return; }
        const why = kd.check && kd.check(d, x, j);
        if (why) { say("warn", F("Sealed, but not what was asked: {x}.", { x: why })); learnTopic(j.topic); say("sys", T("The contract stays yours while the trace lasts.")); heatAdd(8); return; }
        jobWin(j, { hash: s.hash, block: w.block });
        return;
      }
      const c0 = codeOf(s.r); x.said = s.r;
      if (ownRule(s.r) && kd.k !== "g-hit") { if (!S.guard) { S.guard = { cap: null }; save(); } say("sys", T("Your wallet’s own rule stopped this payment. unguard takes the rule off."), btn("unguard", "unguard")); }
      snd.no(); slotFail(c0 || T("refused"));
      say(want === "in" ? "no" : "sys", F("The chain said no in {n} ms: {x}", { n: s.ms, x: c0 || plain(s.r) }));
      const topic0 = ownRule(s.r) ? "guard" : CODE_TOPIC[c0] || j.topic;
      if (want === "in") { flash("bad"); say("sys", T("This contract wants a payment that lands. Nothing was spent.")); learnTopic(topic0); heatAdd(8); return; }
      if (want === "any") { const right = S.pred === c0; S.predOut = right; jobWin(j, { code: c0, predicted: S.pred }, right ? 0 : PAYS[j.t] - 1); return; }
      if (!want.includes(c0)) { flash("bad"); say("warn", F("Refused, but this contract wants {x}.", { x: want.join(" / ") })); learnTopic(topic0); heatAdd(8); return; }
      const why = kd.check && kd.check(d, x, j);
      if (why) { flash("bad"); say("warn", F("Right answer, but not the way asked: {x}.", { x: why })); heatAdd(8); return; }
      flash("ok"); jobWin(j, { code: c0 });
    } catch (e) {
      slotFail(T("stopped"));
      say("no", e && e.soft ? e.message : T("The node did not answer in time; nothing is lost. Type send again."), btn("send", "send"));
    } finally { if (S.job === j.n && !RUN.dry) { S.jobMiss = true; S.jobStep = false; save(); } RUN.busy = false; chips(); jobs(); instruments(); topbar(); balance(); }
  }
  /* Tracer heat: a game rule, not a chain rule. Wrong answers, missed checks and traces raise it; it falls 1 a block and
     with clean work. High heat shortens the next trace; at 80 the crew will not hand you work until you lie low */
  const heat = () => { const t = CHAIN.tip ?? S.heatAt ?? 0; return Math.max(0, Math.min(100, Math.round((S.heat || 0) - Math.max(0, t - (S.heatAt ?? t))))); };
  function heatAdd(n) {
    const was = heat(); S.heat = Math.max(0, Math.min(100, was + n)); S.heatAt = CHAIN.tip ?? S.heatAt ?? 0; save();
    const h = heat();
    if (n > 0) say("warn", F("Tracer heat {n}.", { n: h }) + (h >= 80 ? " " + T("The Tracer has your scent: no new contract until it falls below 80.") : h >= 50 ? " " + T("Your next trace will be shorter.") : ""), btn("heat", "heat"));
    if (n > 0 && was < 50 && h >= 50) crew("look", "The Tracer is sniffing around our wallet. Fewer wild shots: think, then send.", "sour");
    instruments();
  }
  const heatSpan = t => Math.max(8, Math.round(t * (1 - Math.min(heat(), 79) / 160)));
  function heatCmd() {
    const h = heat();
    say("sys", F("Tracer heat: {n} of 100.", { n: h }));
    cols([[T("raises it"), T("a refusal you did not want, a payment that lands but misses the ask, a wrong Tau answer: +8 · a trace run out: +25")],
      [T("lowers it"), T("1 a block, and 10 for each contract settled")],
      [T("50 and up"), T("the next trace is shorter")], [T("80 and up"), T("no new contract until it falls below 80")]]);
    say("learn", T("The Tracer is part of the game, not of the chain. The testnet itself never punishes a refused payment: it refuses it, for free, and tells you why. The heat is there so that thinking pays more than guessing."));
  }
  function learnTopic(t) { if (!t || !TOPICS[t]) return; S.lastTopic = t; save(); say("learn", T(TOPICS[t][1])); }
  function jobWin(j, rec, less) {
    const h = heistOf(j);
    if (h && j.hs < h.heist.length - 1) {   // a part of a heist: the next part, same trace, no pay yet
      if (j.t >= 3 && j.hinted) j.hpen = (j.hpen || 0) + 1;
      const done = kindOf(j);
      heistStage(j, j.hs + 1); S.draft = DRAFT0(); S.pred = null; j.hinted = false; S.jobStep = false; S.jobMiss = false; save();
      snd.seal(); flash("ok"); learnTopic(done.topic);
      say("ok", F("Part {a} of {b} done. The trace runs on: block {n}.", { a: j.hs, b: h.heist.length, n: fmt(S.deadline) }));
      const kd = kindOf(j); heistShow(j);
      transmit(j.who, fill(kd.brief, j), { k: kd.k, n: j.n, name: kd.name, tier: j.t });
      if (kd.table) { say("sys", T("This one is answered in Tau, not with a payment: type tau and a term in x and y (and z). This terminal checks it against every row."), btn("what and", "what and")); tableShow(j); }
      else if (kd.tau) say("sys", T("This one is answered in Tau, not with a payment: type tau and your line. The Tau checker on our server runs it."), btn("what tau", "what tau"));
      else { say("sys", T("A fresh draft: a plain payment of 1 test AGRS to the drop.")); draftShow(); }
      if (kd.hint) say("sys", T("No hint at this tier. hint gives one, for 1 point of the pay."), btn("hint", "hint"));
      jobs(); instruments(); topbar(); chips(); return;
    }
    const pts = Math.max(1, PAYS[j.t] + (j.special || 0) - (j.t >= 3 && j.hinted ? 1 : 0) - (j.hpen || 0) - (j.dried ? 1 : 0) - (less || 0));
    if (heat()) heatAdd(-10);
    const before = rank();
    S.rep = (S.rep || 0) + pts; archive(j, "settled", pts, rec); dailyWin(j);
    snd.tension(false); snd.seal(); flash("ok"); mood(j.who, "glad");
    if (rec.predicted) say(rec.predicted === rec.code ? "ok" : "warn", rec.predicted === rec.code ? F("Predicted {x}, and so it was.", { x: rec.code }) : F("You said {x}; the node said {y}. It stopped at another check first.", { x: rec.predicted, y: rec.code }));
    if (h) say("ok", F("The heist is done: all {n} parts.", { n: h.heist.length }));
    say("ok", F("{x} settled: +{n}. Standing: {r}.", { x: jname(j), n: pts, r: rank() }));
    learnTopic(h ? kindOf(j).topic : j.topic);
    if (rank() !== before) { snd.chapter(); crew("qm", F("New rank: {r}. Harder work comes to your inbox now.", { r: rank() }), "glad");
      const g = Object.keys(GEAR_AT).find(k => GEAR_AT[k] === rank()); if (g) say("ok", F("New gear: {x}, {y}.", { x: g, y: T(GEAR.find(x => x[0] === g)[1]) }), btn(g, g)); }
    letters();
    jobs(); instruments(); topbar(); chips(); jobTick(CHAIN.tip);
    const nx = S.inbox[0]; if (nx) say("sys", T("Next in the inbox:"), btn(F("read {x}", { x: jname(nx) }), "read " + jname(nx)));
  }
  function jobMiss(j) { archive(j, "missed", 0); mood(j.who, "sour"); jobs(); instruments(); topbar(); chips(); jobTick(CHAIN.tip); }
  function jobTraced() {
    const j = curJob(); if (!j) return;
    const loss = heistOf(j) ? 2 : j.t >= 2 ? 1 : 0; S.rep = Math.max(0, (S.rep || 0) - loss);
    archive(j, "traced", -loss);
    const h = document.documentElement; h.classList.add("tr-out"); setTimeout(() => h.classList.remove("tr-out"), 2500); snd.out(); flash("bad");
    say("no", F("Trace complete: block {n} passed. {x} is lost.", { n: fmt(CHAIN.tip), x: jname(j) })); if (loss) say("warn", loss > 1 ? T("A blown heist costs 2 points of standing.") : T("It costs 1 point of standing."));
    crew(j.who, "The block clock does not wait. There is more work in the inbox.", "sour"); heatAdd(25);
    if (S.guard) say("warn", T("Your wallet still carries its own rule. unguard takes it off."), btn("unguard", "unguard"));
    jobs(); instruments(); topbar(); chips(); jobTick(CHAIN.tip);
  }
  function archiveList() {
    if (!S.arch.length) { say("sys", T("The archive is empty: settled, declined and lapsed contracts land here.")); return; }
    const OUT = { settled: "settled", declined: "declined", lapsed: "lapsed", traced: "traced", missed: "missed" };
    cols(S.arch.slice(0, 15).map(a => ["j" + a.n, T(kindOf(a) ? kindOf(a).name : a.k) + " · " + T(OUT[a.out] || a.out) + (a.pts ? " · " + (a.pts > 0 ? "+" : "") + a.pts : "") + (a.code ? " · " + a.code : "")]));
    const s = S.arch.filter(a => a.out === "settled").length;
    say("sys", F("{n} settled from the inbox, {m} points.", { n: s, m: S.rep || 0 }));
  }
  function historyList() {
    if (!S.hist.length) { say("sys", T("No sealed payment from this terminal yet.")); return; }
    cols(S.hist.slice(0, 10).map(h => ["#" + fmt(h.block), F("{a} test AGRS", { a: fmt(h.amount) }) + " · " + short(h.hash)]));
  }
  function why(a) {
    if (a && TOPICS[a]) { S.lastTopic = a; save(); say("learn", T(TOPICS[a][0]) + ": " + T(TOPICS[a][1])); return; }
    if (S.lastTopic && !a) say("learn", T(TOPICS[S.lastTopic][0]) + ": " + T(TOPICS[S.lastTopic][1]));
    cols(Object.entries(TOPICS).map(([k, v]) => [btn("why " + k, "why " + k), T(v[0])]));
  }

  /* ---------- what <word>: the glossary; tutorial: the walk-through for a first visit ---------- */
  const WORDS = [
    [["drop", "dead drop"], "The drop", "The crew’s own wallet, the dead drop. Most contracts pay it; a claim pays it 100 + the chapter; it pays your share back. status shows its whole address."],
    [["wallet", "my wallet"], "Your wallet", "Your test wallet: a key made in this browser, the same one /wallet/ and White Rabbit Key use. The key never leaves the browser; to the chain, whoever holds it is the wallet."],
    [["key", "signature", "sign", "signed", "bls"], "Key and signature", "Every payment is signed with the wallet’s private key; the chain checks the signature against the sender’s public key. A wrong key: INVALID_SIGNATURE."],
    [["curve", "point", "no key", "flags", "first character"], "Not every address is a key", "A wallet’s address is a point on the BLS12-381 curve, written in 48 bytes. Its first bits are flags, so every real address starts with 8, 9, a or b. Anything else is no key at all. Since 10 November 2026 the node refuses a payment to it: TX_INVALID. Before that, such a payment waited in the node’s queue."],
    [["levels", "vote", "validators", "rule for everyone", "my rule", "own rule"], "Two levels of rules", "Tau has rules for everyone and rules for one wallet. Rules for everyone (the fee, who seals blocks, how many must agree) change only when the validators agree: a proposal, enough yes votes, then a wait of some blocks before it applies. A rule on your own wallet (a cap, a list of who you pay, a second signature above an amount) needs no vote: you sign it, and the chain checks every payment of yours against it. IDNI explained the two levels in its Q&A of November 2026."],
    [["me", "self", "myself", "mirror", "pay myself"], "Paying yourself", "A payment to the wallet that sends it is refused: TX_INVALID. The node checks it since 10 November 2026, when a payment arrives and again when a block is applied."],
    [["address", "pubkey", "hex"], "Address", "An address is a public key written as 96 hex characters (0–9, a–f), each one worth 0 to 15. Lookalikes copy the ends; only the whole address is the wallet."],
    [["payment", "tx", "transaction", "transfer"], "A transaction", "A Tau payment: from, to, amount, signed, with a sequence number, an expiry time, a block-height deadline and a fee limit. Nothing else, no memo."],
    [["memo", "no memo"], "No memo", "There is none: a Tau payment has no field for words. The amount is the only thing it says, and anyone can read it. Hence the game’s name."],
    [["fee", "fees", "base fee", "fee limit", "fee_limit"], "Fees", "The fee is a limit you sign: at most this much may be taken. The chain’s base fee is in its rules (peek getgovernance: o9). A limit below the base fee is refused: FEE_LIMIT_TOO_LOW."],
    [["block", "blocks", "tip", "height", "block height"], "Blocks", "The chain seals transactions into blocks, one after another. The newest block’s number is the tip; the top bar counts it and the instruments show the pace."],
    [["deadline", "expire_at_height"], "Block-height deadline", "expire_at_height names the last block a payment may land in. At or behind the tip it is refused: TX_EXPIRED. Blocks are the clock that counts on this chain."],
    [["expiry", "expiration", "expiration_time"], "Expiry time", "expiration_time is a moment written into the signed payment. Once it has passed, the chain refuses the payment: TX_EXPIRED, whatever the block."],
    [["sealed", "confirmed", "mempool"], "Mempool and sealed", "A payment the node accepts waits in the mempool; the next block seals it, and then it is in the chain for good."],
    [["sequence", "seq", "nonce"], "Sequence", "Every wallet numbers its payments: the sequence number. The chain takes only the next number, each once; any other is refused: INVALID_SEQUENCE. peek getsequence <address> shows the next."],
    [["ghost", "replay", "double spend"], "The ghost", "A sealed payment sent a second time: the same bytes, the same signature. The chain refuses it (INVALID_SEQUENCE): no replay, no double spend."],
    [["refused", "refusal", "code", "codes", "error"], "Refusals", "The chain says no with a code that names the reason (TX_EXPIRED, FEE_LIMIT_TOO_LOW …), and nothing moves. In many contracts a refusal for the right reason is the win."],
    [["faucet"], "The faucet", "The testnet credits an unseen wallet 100,000 test AGRS when it first pays. It pays only wallets whose balance is 0."],
    [["agrs", "test agrs", "coin", "coins", "balance"], "Test AGRS", "The testnet’s coin. Test AGRS have no value; the testnet hands them out so that everybody can test with them."],
    [["escrow", "retractable", "retract", "back"], "Escrow", "A retractable transfer parks the money until a release time or height; until then only the sender can take it back (retract_transfer, feeless). From the release on, the first block pays the recipient by itself."],
    [["trace"], "The trace", "Your deadline on a taken contract, in blocks. Pass it and the contract is lost; the bar at the top runs down with every block. trace <blocks> sets your own (after chapter 2)."],
    [["contract", "contracts", "job", "jobs"], "Contracts", "A job from the crew: one real transaction with a goal. Twelve tell the story in three chapters (jobs); after chapter 1 the inbox brings new ones without end."],
    [["chapter", "claim", "share"], "Chapters and the share", "Four contracts make a chapter. claim pays the drop 100 + the chapter’s number (the amount says which), and the crew’s purse pays 500 test AGRS back."],
    [["purse"], "The crew’s purse", "A wallet our server runs: it reads the chain and pays the shares back. Its budget is small, so it pays chapters only, never inbox contracts."],
    [["mark", "crew mark"], "The crew’s mark", "1 test AGRS from the drop with your first share; its hash is your badge on the chain."],
    [["tracer", "dust", "lookalike", "hunt"], "The Tracer", "After chapter 1 a lookalike of the drop, with the same first and last characters, sends you 1 test AGRS of dust. hunt asks which address is the real drop."],
    [["rank", "ranks", "standing", "points", "tier", "tiers"], "Standing and ranks", "Points for what you settled: contracts, cases, ops, hunts and the inbox’s pay. Nine ranks from stowaway to no memo; higher ranks open harder inbox tiers."],
    [["inbox", "draft"], "The inbox", "After chapter 1: puzzles that keep coming. accept one, look at the draft (tx), change it (set), send it. Every answer is a real transaction."],
    [["case", "op", "ops"], "Case and ops", "case: this week’s case file, from the pirates’ logbook and the hack of the week. op: live ops while the Black Sequence is in port on Tuesdays."],
    [["node", "relay", "peek"], "The node", "The node keeps the chain and answers questions; this terminal talks to it through our relay at node.tauhud.com. peek asks it yourself."],
    [["governance", "rules", "o9"], "Governance", "The chain’s rules, readable by anyone: peek getgovernance. They are written in Tau Language; rule takes them apart. o9 is the base fee, in hex."],
    [["tau language", "tau lang", "tau", "spec", "specification"], "Tau Language", "The language the chain’s rules are written in. A Tau specification (a spec) says how a program’s inputs and outputs relate over time. You can write and test specs on your own computer in the tau REPL: tauhud.com/learn/."],
    [["stream", "streams", "o1", "i1", "[t]", "t"], "Streams", "A spec talks to the world through streams: o1[t] is output stream 1 at time step t, i1[t] is input stream 1. o1[t-1] is the same stream one step back. In the chain’s rule, o9[t] is the base fee."],
    [["bv", "bitvector", "bv[24]", "bits"], "Bitvectors", "bv[n] is a bitvector n bits wide: a whole number from 0 to 2^n − 1. The chain’s rule makes the base fee a bv[24]; amounts on this chain are 24 bits wide too."],
    [["#x", "#b", "constant", "constants", "braces"], "Constants", "A constant sits in braces with its type: {#x0a}:bv[8] is 10 written in hex, {#b1010}:bv[8] the same in binary, {10}:bv[8] in decimal."],
    [["top", "all ones", "1:bv"], "The top", "In a bitvector a bare 1 is the top, every bit set: 1:bv[8] is 255. The number one is written {1}:bv[8]. A classic first mistake in Tau."],
    [["g", "f", "globally", "eventually", "always"], "G and F", "G says a local spec holds at every time step, F that it holds at some step. G o1[t] = 0 means output 1 is 0 at all steps."],
    [["and", "or", "not", "xor", "^", "boolean function", "truth table", "table"], "Boolean functions", "In Tau a Boolean function is built with & (and), | (or), ' (not, written after: x' is not x) and ^ (exclusive or). ' binds first, then &, then ^, then |. (x & y)' is not both; x' | y is if x then y."],
    [["&&", "||", "!", "logic", "boolean", "&", "|", "'"], "Two kinds of and/or", "Tau has Boolean operators inside a term (&, |, ' for complement) and logical ones between formulas (&&, ||, !). x & y = 0 is one formula; x = 0 && y = 0 joins two."],
    [["sat", "repl", "satisfiable"], "sat and the REPL", "In the tau REPL, sat asks whether a spec is satisfiable: whether it can run forever, whatever the inputs. Try sat x = 0. Start with help examples."],
    [["black sequence", "ship", "pirates", "crew"], "The Black Sequence", "The pirate ship that tests the chain at White Rabbit Key every Tuesday. Her crew are game characters; their transactions are real."],
    [["players", "player", "multiplayer", "others", "other players", "online", "who"], "Other players", "Everybody at a terminal like this one plays the same chain with you, at the same time: every contract is a real transaction on Tau Testnet Alpha. The board counts the wallets that paid the drop today and this hour; it never shows names."],
    [["hash", "tx hash", "transaction hash"], "Hash", "A transaction’s fingerprint: a string of hex characters made from its bytes. The same payment always has the same hash; the explorer finds a payment by it."],
    [["explorer"], "The explorer", "tauhud.com/explorer/ shows every block and every payment of the testnet. Click a hash in this terminal and it opens there."],
    [["hint", "hints"], "Hints", "The crew’s help for an inbox contract. Up to tier 2 it is free and comes with a button for its first step; from tier 3, hint costs 1 point of the pay."],
    [["board", "leaderboard", "score"], "The board", "board: how many wallets paid the drop today and this hour, and how many stand at each rank. Wallets, not people; nobody is named."],
    [["findings", "finding", "bug"], "Findings", "A trick the chain takes although it must refuse it. The terminal keeps the record in this browser (findings) and shows how to pass it on; nothing is posted by itself."],
    [["width", "amount width", "24 bits", "2^24"], "Amount width", "An amount is 24 bits wide here: 16,777,215 at most. 2^24 = 16,777,216 is not even read: TX_INVALID or INVALID_PARAMS."],
    [["order", "order of checks", "first check"], "Order of checks", "A payment wrong in two ways is refused for one of them: the node answers with the first check it fails. Which check comes first is the node’s own order; its answer shows it."],
    [["testnet", "tau", "chain"], "Tau Testnet Alpha", "IDNI’s public test chain. Its coins have no value; it is there to be tested. This game is one way to test it, together with every other player."],
    [["guard", "guards", "intel", "probe", "probes", "personal rule", "open answer"], "Guards and probes", "An intel contract hides a wallet’s personal rule: a line of Tau the chain checks each of that wallet’s payments against. A probe asks the real Tau engine on our server whether the rule lets a transfer of that amount through (o5 = 1) or blocks it (o5 = 0); nothing goes to the chain. Where a rule says nothing, the engine answers 0: blocked."],
    [["recurring", "standing order", "subscription", "percent", "percentage"], "Standing orders and percent", "Tau Testnet Alpha has no standing orders yet: a rule can let a payment through or stop it, never start one. The nearest thing is the way back turned around: timed payments that pay themselves out at a set block or time, up to 16 open per wallet and 90 days ahead, each yours to take back until then. A percentage works only as a fee on your own payments, worked out from the amount; it goes to whoever seals the block."],
    [["clause", "rule size", "comparisons", "parcel", "rule tx"], "A wallet’s own rule", "A wallet’s own rule is a transaction of its own: operation 0 carries it, and no payment may ride along (RULE_WITH_TRANSFERS). It is one always ( … ). unit that writes o5 and nothing else (MIXED_OUTPUT_RULE), with at most 32 comparisons (=, <, >, <=, >= and != count one each); a rule with more is refused: TX_REJECTED. A new rule replaces the old one; the rule that says o5 = 1 and nothing else takes it away (unguard)."],
    [["i5", "time", "seconds", "when", "unix"], "i5, the time", "In a wallet’s rule, i5 is the block’s time in seconds since 1 January 1970, UTC. when <seconds> turns such a number into a date."],
    [["showcase", "piggy bank", "four-eyes", "four eyes", "feeding fund"], "The showcase wallets", "Three wallets Tau HUD runs on the testnet, each with a rule of its own: a piggy bank locked until New Year, a four-eyes wallet that needs a co-signer, and Agorzilla’s feeding fund. Their rules are in force on the chain and anyone may read them: showcase."],
    [["daily", "streak", "today"], "The daily order", "One contract a day, marked ★, German days. Each day in a row adds a point to it, up to five; a missed day starts the streak again."],
  ];
  /* rule: the chain's rules, taken apart token by token */
  async function ruleCmd() {
    const r = await ask("getgovernance"); const text = String((r && r.status === "ok" && r.data && r.data.consensus_rules) || "");
    if (text) CHAIN.rules = text;
    const src = text || SIM_RULES, p = parseRule(src);
    say("sys", text ? T("The chain’s rules, as the node gives them:") : T("No answer from the node; the rule as it stood when this game was written:"));
    say("sys", code(src.slice(0, 600)));
    if (!p) { say("sys", T("This rule has a shape the game does not know yet. Read it with the words: what stream, what bv, what constant."), link("/learn/" + lang(), T("Learn Tau Language"))); return; }
    cols([
      [p.stream, p.io === "o" ? F("output stream number {n}. On this chain: the base fee.", { n: p.num }) : F("input stream number {n}.", { n: p.num })],
      ["[t]", T("at every time step t; [t-1] would be one step back")],
      [":bv[" + p.bits + "]", F("a bitvector {n} bits wide: 0 to {m}", { n: p.bits, m: fmt(2 ** p.bits - 1) })],
      ["=", T("must be equal to")],
      ["{#x" + p.hex + "}", F("a constant in braces; #x means hex: {n}", { n: p.val })],
    ]);
    say("learn", F("Read aloud: at every step, the base fee is {n}.", { n: p.val }), btn("what tau", "what tau"), link("/learn/" + lang(), T("Learn Tau Language")));
    learnTopic("rule");
  }
  /* p-spec: a rule in words, answered with a line of Tau. The Tau checker on our server (POST /tau, infra/checker) runs the
     line over a few input steps and the outputs are compared; while it is not reachable (or in the simulation), the line is
     checked against the shapes we know are right, and the game says that it did so */
  /* p-table: a truth table in x, y (and z); the player's term is evaluated here, row by row, with Tau's operators and
     precedence (IDNI's README: ' > & > ^ > |, & may be left out between operands) */
  const TABLES = {
    and: { v: 2, f: (x, y) => x & y, hint: "one row is 1: both x and y" },
    or: { v: 2, f: (x, y) => x | y, hint: "one row is 0: neither x nor y" },
    xor: { v: 2, f: (x, y) => x ^ y, hint: "1 where x and y differ" },
    nand: { v: 2, f: (x, y) => 1 - (x & y), hint: "the opposite of and; ' after a bracket negates it" },
    nor: { v: 2, f: (x, y) => 1 - (x | y), hint: "the opposite of or" },
    xnoty: { v: 2, f: (x, y) => x & (1 - y), hint: "x, but not y" },
    imp: { v: 2, f: (x, y) => (1 - x) | y, hint: "0 only where x is 1 and y is 0" },
    eq: { v: 2, f: (x, y) => 1 - (x ^ y), hint: "1 where x and y are the same" },
    maj: { v: 3, f: (x, y, z) => (x & y) | (x & z) | (y & z), hint: "1 where at least two of the three are 1" },
    mux: { v: 3, f: (x, y, z) => x ? y : z, hint: "if x then y, else z" },
    odd: { v: 3, f: (x, y, z) => x ^ y ^ z, hint: "1 where an odd number of them are 1" },
    all3: { v: 3, f: (x, y, z) => x & y & z, hint: "one row is 1" },
  };
  function boolEval(src, env) {   // a term over x y z, 0 1, ( ) ' & ^ |; throws on anything else
    const t = String(src).replace(/\s+/g, "").replace(/\.$/, ""); let i = 0;
    const peek = () => t[i], eat = c => { if (t[i] !== c) throw new Error(c); i++; };
    const atom = () => { let v; const c = peek(); if (c === "(") { i++; v = or(); eat(")"); } else if (c === "0" || c === "1") { i++; v = +c; } else if (c && "xyz".includes(c)) { i++; v = env[c]; if (v == null) throw new Error(c); } else throw new Error(c || "end"); while (peek() === "'") { i++; v = 1 - v; } return v; };
    const and = () => { let v = atom(); while (peek() === "&" || (peek() && "xyz01(".includes(peek()))) { if (peek() === "&") i++; v &= atom(); } return v; };
    const xor = () => { let v = and(); while (peek() === "^" || peek() === "+") { i++; v ^= and(); } return v; };
    const or = () => { let v = xor(); while (peek() === "|") { i++; v |= xor(); } return v; };
    const v = or(); if (i !== t.length) throw new Error(t[i]); return v;
  }
  const rowsOf = n => (n === 3 ? [[0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1], [1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1]] : [[0, 0], [0, 1], [1, 0], [1, 1]]);
  function tableShow(j) {
    const tb = TABLES[j.tab]; if (!tb) return;
    const names = tb.v === 3 ? "x y z" : "x y";
    cols([[names, "→"], ...rowsOf(tb.v).map(r => [r.join(" "), String(tb.f(...r))])]);
  }
  function tableCheck(j, term) {
    const tb = TABLES[j.tab]; if (!tb) return;
    let bad = null; const out = [];
    try { for (const r of rowsOf(tb.v)) { const env = { x: r[0], y: r[1], z: r[2] }, got = boolEval(term, env), want = tb.f(...r); out.push([r.join(" "), got + (got === want ? " ✓" : " ✗ " + F("(wanted {n})", { n: want }))]); if (got !== want && !bad) bad = r; } }
    catch (e) { say("no", T("That is not a term this terminal can read: use x, y, z, 0, 1, brackets and & | ' ^.")); return; }
    cols([[tb.v === 3 ? "x y z" : "x y", "→"], ...out]);
    if (!bad) { jobWin(j, { tau: term }); return; }
    say("no", T("Not every row matches. Change the term and send it again with tau.")); heatAdd(8);
  }
  const SPECS = {
    copy: { brief: "Write a spec where output o1 always equals input i1, both 8-bit bitvectors.", hint: "G(o1[t]:bv[8] = i1[t]:bv[8]) is close to the whole answer; a stream is typed with :bv[8]",
      steps: [{ i1: "5" }, { i1: "200" }, { i1: "0" }], out: i => i.i1, shapes: ["o1[t]=i1[t]"] },
    inc: { brief: "Write a spec where output o1 is always input i1 plus one, as 8-bit bitvectors. Careful: in Tau a bare 1 is not one.", hint: "the number one is {1}:bv[8]; what top",
      steps: [{ i1: "5" }, { i1: "41" }, { i1: "255" }], out: i => (i.i1 + 1) % 256, shapes: ["o1[t]=i1[t]+{1}", "o1[t]={1}+i1[t]"] },
    zero: { brief: "Write a spec where output o1 is zero at every step, 8 bits wide.", hint: "G says at every step; {0}:bv[8] is zero",
      steps: [{}, {}, {}], out: () => 0, shapes: ["o1[t]={0}", "o1[t]=0"] },
    max: { brief: "Write a spec where output o1 is always the bigger of inputs i1 and i2, 8-bit bitvectors.", hint: "max(x, y) is built in for bitvectors",
      steps: [{ i1: "5", i2: "9" }, { i1: "200", i2: "7" }, { i1: "3", i2: "3" }], out: i => Math.max(i.i1, i.i2), shapes: ["o1[t]=max(i1[t],i2[t])", "o1[t]=max(i2[t],i1[t])"] },
    cut: { brief: "Write a spec where output o1 is always one percent of input i1, rounded down, both 24-bit bitvectors: the cut a fee rule takes from an amount.", hint: "/ divides bitvectors and rounds down; a hundred is {100}:bv[24]",
      steps: [{ i1: "1000" }, { i1: "250" }, { i1: "99" }], out: i => Math.floor(i.i1 / 100), shapes: ["o1[t]=i1[t]/{100}"] },
  };
  /* the shape of a line, for the offline check: no spaces, no types, no G( ), no final dot */
  const shapeOf = line => { let x = line.replace(/\s+/g, "").replace(/\.$/, "").replace(/:bv\[\d+\]/g, ""); if (/^G\(.*\)$/.test(x)) x = x.slice(2, -1); else if (/^G/.test(x)) x = x.slice(1); if (/^\(.*\)$/.test(x)) x = x.slice(1, -1); return x; };
  async function tauAsk(body) {
    if (SIM) return null;
    try { const r = await fetch(RELAY + "/tau", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), cache: "no-store" }); if (r.status === 404) return null; return await r.json(); } catch (e) { return null; }
  }
  async function tauCmd(line) {
    line = String(line || "").trim();
    if (!line) { say("sys", T("tau <line>: a line of Tau. With a Tau contract taken it is your answer; otherwise the checker says whether the line can hold (sat)."), btn("what tau", "what tau"), link("/learn/" + lang(), T("Learn Tau Language"))); return; }
    if (line.length > 2048) { say("warn", T("Too long for the checker: 2048 characters at most.")); return; }
    const j = curJob(), kd = j && kindOf(j);
    if (!kd || !kd.tau) {
      say("step", T("asking the Tau checker: sat"));
      const r = await tauAsk({ op: "sat", spec: line });
      if (!r) { say("sys", T("The Tau checker on our server is not answering yet. Try the line in your own tau REPL in the meantime."), link("/learn/" + lang(), T("Learn Tau Language"))); return; }
      if (!r.ok) { say("no", F("The checker refused the line: {x}", { x: String(r.error || "").slice(0, 300) })); return; }
      say(r.verdict ? "ok" : "warn", r.verdict ? T("Satisfiable: this spec can run forever, whatever the inputs.") : T("Not satisfiable: some inputs would leave it no way to go on."));
      return;
    }
    if (kd.table) { tableCheck(j, line); return; }
    const sp = SPECS[j.spec]; if (!sp) return;
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    RUN.busy = true; chips();
    try {
      say("step", T("asking the Tau checker: run, three steps"));
      const r = await tauAsk({ op: "run", spec: line, steps: sp.steps });
      if (r && r.ok && Array.isArray(r.outputs)) {
        const rows = sp.steps.map((st, i) => { const o = r.outputs[i] || {}, got = o.out ? Number(o.out.o1) : NaN, ins = {}; for (const [k, v] of Object.entries(st)) ins[k] = Number(v); return { st, got, want: sp.out(ins) }; });
        cols(rows.map((x, i) => ["t=" + i, Object.entries(x.st).map(([k, v]) => k + "=" + v).join(" ") + (Object.keys(x.st).length ? " → " : "") + "o1=" + (isNaN(x.got) ? "—" : x.got) + (x.got === x.want ? " ✓" : " ✗ " + F("(wanted {n})", { n: x.want }))]));
        if (rows.every(x => x.got === x.want)) { jobWin(j, { tau: line, engine: r.engine || "tau" }); return; }
        say("no", T("The checker ran your line, and o1 is not what the crew asked for at every step.")); mood(j.who, "sour"); heatAdd(8); return;
      }
      if (r && !r.ok) { say("no", F("The checker refused the line: {x}", { x: String(r.error || "").slice(0, 300) }) + (r.timeout ? " " + T("(it ran out of time)") : "")); mood(j.who, "sour"); return; }
      /* no checker: the shapes we know are right */
      const sh = shapeOf(line);
      say("sys", T("The Tau checker on our server is not answering, so the line is compared with the shapes we know are right."));
      if (sp.shapes.includes(sh)) { say("ok", T("That is one of them.")); jobWin(j, { tau: line, engine: "offline" }); return; }
      say("no", T("That is not one of the shapes we know. It may still be right Tau; try it in your own REPL, or when the checker is up."));
    } finally { RUN.busy = false; chips(); }
  }
  /* ---------- intel contracts (KINDS i-…): a wallet guarded by a personal rule nobody has shown you ----------
     The rule is dealt on our server from the contract's seed and a secret kept there (infra/checker/intel.py), so it is not
     in this page. Each probe is one transfer the real Tau engine on the server judges with it (POST /tau/intel), the engine
     /learn uses; nothing goes to the chain. The answer is what the guard does, compared amount by amount: a rule that says
     "above 4,000" is named floor 4,100. Asked once a visit whether the server has the contracts (GET /tau/health) */
  let INTEL = null, REVEAL = 0;
  function intelUp() {
    if (SIM) return false;
    if (INTEL === null) {
      INTEL = "asking";
      fetch(RELAY + "/tau/health", { cache: "no-store" }).then(r => (r.ok ? r.json() : null))
        .then(h => { INTEL = !!(h && Array.isArray(h.intel) && h.intel.includes("i-blind")); }).catch(() => { INTEL = false; });
    }
    return INTEL === true;
  }
  const seedHex = () => Array.from(crypto.getRandomValues(new Uint8Array(8)), b => b.toString(16).padStart(2, "0")).join("");
  const amountOf = s => { const m = /^(\d{1,8})(k?)$/.exec(String(s == null ? "" : s).toLowerCase().replace(/[\s,_']/g, "")); if (!m) return null; const n = +m[1] * (m[2] ? 1000 : 1); return n < GIANT ? n : null; };
  const b64 = s => btoa(unescape(encodeURIComponent(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");   // as /learn/ reads #q=
  const intelJob = () => { const j = curJob(); return j && kindOf(j).intel ? j : null; };
  function intelNone(what) { say("sys", F("{x} belongs to the intel contracts: accept one from the inbox.", { x: what }), btn("inbox", "inbox")); }
  function intelSim() {
    if (!SIM) return false;
    say("sys", T("The intel contracts ask the Tau checker on our server, which the simulation does not reach. Switch to the live node in the header."));
    return true;
  }
  async function intelAsk(j, body) {
    try {
      const r = await fetch(RELAY + "/tau/intel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ case: j.k, seed: j.seed, ...body }), cache: "no-store" });
      const x = await r.json().catch(() => null);
      if (r.status === 429) return { ok: false, wait: Number((x && x.retry_after) || r.headers.get("Retry-After")) || 30 };
      return x || { ok: false, error: "HTTP " + r.status };
    } catch (e) { return null; }
  }
  /* an answer from the checker: false (and why, on the screen) when there is none to use. A new round there (the server's
     secret changed, so every rule was dealt anew) clears the contract's probes: they were about another rule. A probe's
     answer is about the new rule and stays; a name or a shot made from the old probes does not count (keep false) */
  function intelOk(j, r, keep = true) {
    if (!r) { say("no", T("The Tau checker on our server is not answering. Nothing was counted; try again in a minute.")); return false; }
    if (r.wait) { say("warn", F("The checker asks for a pause: too many questions from this address. Try again in {n} s.", { n: r.wait })); return false; }
    if (!r.ok) { say("no", F("The checker could not judge it: {x}", { x: String(r.error || "no answer").slice(0, 200) })); return false; }
    if (r.round && j.round && r.round !== j.round) {
      j.probes = []; j.wrong = 0; j.lead = null;
      say("warn", T("The guard has a new rule since your last probe: our server dealt the rules anew. Your probes are cleared; start again."));
      if (kindOf(j).lead) setTimeout(() => intelLead(j), 0);
      if (!keep) { j.round = r.round; save(); return false; }
    }
    if (r.round) j.round = r.round;
    save(); return true;
  }
  /* the Lookout's number: the rule's first amount, for the window, the hole and the blind guard */
  async function intelLead(j) {
    if (SIM || j.lead != null) return;
    const r = await intelAsk(j, { lead: true });
    if (!intelOk(j, r) || r.lead == null) return;
    j.lead = r.lead; save();
    if (S.job === j.n) { crew("look", F("One number in the guard’s rule I could make out: {n}. Where it sits is yours to find.", { n: fmt(r.lead) }), "calm"); chips(); }
  }
  function intelStart(j) {
    const kd = kindOf(j);
    say("sys", T("This one is answered with probes, not with a payment. probe <amount> asks the guard whether it lets a transfer of that amount through; the real Tau engine on our server judges it with the hidden rule. Nothing goes to the chain."));
    say("sys", kd.final ? T("When you know the edge, final <amount> is your one shot: the last amount that passes. A miss loses the contract.")
      : T("When you know it, name says what the guard does: name cap <n>, floor <n>, band <a> <b>, hole <a> <b> or none. Three wrong names lose the contract."), btn("what probe", "what probe"));
    if (kd.lead) intelLead(j);
  }
  /* what the probes said so far, in one line: sorted by amount, ✓ passes, ✗ blocked */
  function intelSeen(j) {
    const p = j.probes || [];
    if (!p.length) { say("sys", F("No probes yet; {m} or fewer pays a point more.", { m: j.m })); return; }
    say("sys", F("Probes so far ({n}; {m} or fewer pays a point more):", { n: p.length, m: j.m }) + " " + p.map(([a, ok]) => fmt(a) + (ok ? " ✓" : " ✗")).join(" · "));
  }
  function intelShow(j) {
    const kd = kindOf(j);
    if (j.lead != null) say("sys", F("The lookout’s number: {n}", { n: fmt(j.lead) }));
    intelSeen(j);
    say("sys", kd.final ? T("probe <amount> asks the guard · final <amount> is your one shot at the edge · reveal gives up")
      : T("probe <amount> asks the guard · name cap|floor <n>, band|hole <a> <b> or none · reveal gives up"));
    if (kd.lead && j.lead == null) intelLead(j);
  }
  async function probeCmd(arg) {
    const j = intelJob(); if (!j) { intelNone("probe"); return; }
    if (!arg) { intelShow(j); return; }
    const n = amountOf(arg);
    if (n == null) { say("warn", T("probe <amount>: a whole number from 0 to 16,777,215.")); return; }
    const had = (j.probes || []).find(p => p[0] === n);
    if (had) { say("sys", had[1] ? F("{n} was probed already: it passes.", { n: fmt(n) }) : F("{n} was probed already: it is blocked.", { n: fmt(n) })); intelSeen(j); return; }
    if (intelSim()) return;
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    RUN.busy = true; chips();
    try {
      say("step", F("probing the guard: a transfer of {n}", { n: fmt(n) }));
      const r = await intelAsk(j, { probe: n });
      if (!intelOk(j, r)) return;
      j.probes = [...(j.probes || []), [n, !!r.pass]].sort((a, b) => a[0] - b[0]); save();
      if (r.pass) snd.ok(); else snd.no();
      say(r.pass ? "ok" : "warn", r.pass ? F("{n} passes: o5 = 1.", { n: fmt(n) }) : F("{n} is blocked: o5 = 0.", { n: fmt(n) }));
      intelSeen(j);
    } finally { RUN.busy = false; chips(); }
  }
  /* name: what the guard lets through. above and below are said as the floor or cap they are */
  const NAMEWORDS = { cap: "cap", floor: "floor", band: "band", window: "band", hole: "hole", none: "none", nothing: "none", above: "above", below: "below" };
  function guessOf(args) {
    const kind = NAMEWORDS[args[0]], nums = args.slice(1).join(" ").replace(/[,_']/g, "").split(/\s*(?:\.\.|–|-|\bto\b|\s)\s*/).filter(Boolean).map(amountOf);
    if (!kind || nums.some(n => n == null)) return null;
    if (kind === "none") return nums.length ? null : { kind: "none" };
    if (kind === "above") return nums.length === 1 && nums[0] < GIANT - 1 ? { kind: "floor", a: nums[0] + 1 } : null;
    if (kind === "below") return nums.length === 1 && nums[0] > 0 ? { kind: "cap", a: nums[0] - 1 } : null;
    if (kind === "band" || kind === "hole") return nums.length === 2 && nums[0] <= nums[1] ? { kind, a: nums[0], b: nums[1] } : null;
    return nums.length === 1 ? { kind, a: nums[0] } : null;
  }
  const guessWords = g => (g.kind === "none" ? T("it lets nothing through") : g.kind === "cap" ? F("it lets through every amount up to {a}", { a: fmt(g.a) })
    : g.kind === "floor" ? F("it lets through every amount from {a} up", { a: fmt(g.a) }) : g.kind === "band" ? F("it lets through only the amounts from {a} to {b}", { a: fmt(g.a), b: fmt(g.b) })
    : F("it lets through everything but the amounts from {a} to {b}", { a: fmt(g.a), b: fmt(g.b) }));
  async function nameCmd(args) {
    const j = intelJob(); if (!j) { intelNone("name"); return; }
    if (kindOf(j).final) { say("sys", T("This contract is answered in one shot: final <amount>, the last amount that passes."), btn("final", "final")); return; }
    const g = args.length ? guessOf(args) : null;
    if (!g) {
      say("sys", T("name says what the guard lets through:"));
      cols([["name cap <n>", T("every amount up to n")], ["name floor <n>", T("every amount from n up")], ["name band <a> <b>", T("from a to b, and nothing else")],
        ["name hole <a> <b>", T("everything but a to b")], ["name none", T("nothing at all")]]);
      say("sys", F("Three wrong names lose the contract; {n} so far.", { n: j.wrong || 0 }));
      return;
    }
    if (intelSim()) return;
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    RUN.busy = true; chips();
    try {
      say("step", F("naming the guard: {x}", { x: guessWords(g) }));
      const r = await intelAsk(j, { name: g });
      if (!intelOk(j, r, false)) return;
      if (r.right) { say("ok", F("Right, the guard’s rule: {x}.", { x: guessWords(g) })); intelWin(j, r); return; }
      j.wrong = (j.wrong || 0) + 1; save(); flash("bad"); snd.no(); mood(j.who, "sour");
      if (j.wrong >= 3) {
        say("no", T("Three wrong names: the guard is closed to you. Its rule:"));
        const v = await intelAsk(j, { reveal: true }); if (v && v.ok) intelRule(j, v);
        jobMiss(j); return;
      }
      say("no", F("Wrong: the guard’s rule is not “{x}”. Wrong names: {n} of 3.", { x: guessWords(g), n: j.wrong }));
      heatAdd(8);
    } finally { RUN.busy = false; chips(); }
  }
  async function finalCmd(arg) {
    const j = intelJob(); if (!j) { intelNone("final"); return; }
    if (!kindOf(j).final) { say("sys", T("final belongs to the contract One shot. Here name says what the guard does."), btn("name", "name")); return; }
    const n = arg ? amountOf(arg) : null;
    if (n == null || n >= GIANT - 1) { say("sys", T("final <amount>: your one shot at the edge, the last amount the guard lets through. A miss loses the contract.")); intelSeen(j); return; }
    if (intelSim()) return;
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    RUN.busy = true; chips();
    try {
      say("step", F("one shot: {a} must pass and {b} must not", { a: fmt(n), b: fmt(n + 1) }));
      const r = await intelAsk(j, { final: n });
      if (!intelOk(j, r, false)) return;
      if (r.edge) { say("ok", F("{a} passes and {b} is blocked: that is the edge.", { a: fmt(n), b: fmt(n + 1) })); intelWin(j, r); return; }
      flash("bad"); snd.no();
      say("no", r.pass ? F("{a} passes, and so does {b}: the edge lies higher. The shot missed.", { a: fmt(n), b: fmt(n + 1) }) : F("{a} is blocked already: the edge lies lower. The shot missed.", { a: fmt(n) }));
      intelRule(j, r); jobMiss(j);
    } finally { RUN.busy = false; chips(); }
  }
  async function revealCmd() {
    const j = intelJob(); if (!j) { intelNone("reveal"); return; }
    if (REVEAL !== j.n) { REVEAL = j.n; say("warn", T("reveal gives the contract up and shows the guard’s rule. Type reveal again to do it."), btn("reveal", "reveal")); return; }
    REVEAL = 0;
    if (intelSim()) return;
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    RUN.busy = true; chips();
    try {
      const r = await intelAsk(j, { reveal: true });
      if (!intelOk(j, r)) return;
      say("sys", T("Given up. The guard’s rule:")); intelRule(j, r); jobMiss(j);
    } finally { RUN.busy = false; chips(); }
  }
  /* the rule, once named, shot at or given up: its Tau, what it does in words, and a link that runs it at its edges on /learn/ */
  function intelRule(j, r) {
    if (!r || !r.rule) return;
    const d = r.dealt || {}, a = d.a, b = d.b;
    say("sys", T("The guard’s rule, in Tau:"), code(r.rule));
    const words = {
      cap: () => F("It lets through every amount up to {a}.", { a: fmt(a) }),
      floor: () => F("It lets through every amount from {a} up.", { a: fmt(a) }),
      band: () => F("It lets through the amounts from {a} to {b}, and nothing else.", { a: fmt(a), b: fmt(b) }),
      hole: () => F("It lets through everything but the amounts from {a} to {b}.", { a: fmt(a), b: fmt(b) }),
      none: () => F("It only says when to block: above {a}. At {a} and below it says nothing, and where a rule says nothing the engine answers 0. So nothing passes at all.", { a: fmt(a) }),
      above: () => F("It only says when to let through: above {a}. At {a} and below it says nothing, and where a rule says nothing the engine answers 0: blocked. So it is a floor at {b}.", { a: fmt(a), b: fmt(a + 1) }),
    }[d.kind];
    if (words) say("learn", words());
    const at = { cap: [a, a + 1], floor: [a - 1, a], band: [a - 1, a, b, b + 1], hole: [a - 1, a, b, b + 1], none: [0, a, a + 1], above: [a, a + 1] }[d.kind];
    if (at) say("sys", T("Run it yourself, at its edges:"), link("/learn/" + lang() + "#q=" + b64(JSON.stringify({ op: "run", spec: r.rule, in: "i1 = " + at.filter(x => x >= 0).join(", ") })), T("on the Learn page")));
  }
  function intelWin(j, r) {
    const n = (j.probes || []).length, more = n <= j.m;
    intelRule(j, r);
    say(more ? "ok" : "sys", more ? F("{n} probes, {m} or fewer: a point more.", { n, m: j.m }) : F("{n} probes; {m} or fewer would have paid a point more.", { n, m: j.m }));
    jobWin(j, { intel: (r.dealt && r.dealt.kind) || "edge", probes: n }, more ? -1 : 0);
  }
  const TAUWORDS = ["Boolean functions", "Tau Language", "Streams", "Bitvectors", "Constants", "The top", "G and F", "Two kinds of and/or", "sat and the REPL", "Guards and probes"];
  function what(term) {
    const t = term.trim().toLowerCase().replace(/^(is|a|an|the)\s+/, "").replace(/[?.!]+$/, "");
    const w = WORDS.find(x => x[0].includes(t)) || WORDS.find(x => x[0].some(k => t.includes(k)));
    if (!w) { say("sys", F("No entry for {x}. Words I can explain:", { x: term.trim() })); say("sys", el("span", null, ...WORDS.map(x => [btn(x[0][0], "what " + x[0][0]), " "]).flat())); return; }
    say("learn", T(w[1]) + ": " + T(w[2]));
    if (TAUWORDS.includes(w[1])) say("sys", T("Write Tau yourself:"), link("/learn/" + lang(), T("Learn Tau Language")), btn("rule", "rule"));
    const more = WORDS.filter(x => x !== w).sort(() => Math.random() - 0.5).slice(0, 3);
    say("sys", T("More:"), ...more.map(x => btn("what " + x[0][0], "what " + x[0][0])));
  }
  const TUT = [
    ["What this is", "No Memo is a game on Tau Testnet Alpha, a public test chain. You and the other players test the same chain together; every move is a real transaction from your own test wallet. Test AGRS have no value, so nothing here can cost you money.", "status"],
    ["Your wallet", "A test wallet is made in this browser at your first contract; its key never leaves it. On its first payment the testnet credits a new wallet 100,000 test AGRS to play with.", "what wallet"],
    ["A payment", "A Tau payment is from, to, amount, signed. There is no memo field: the amount is the only thing you can say, and everybody can read it.", "what memo"],
    ["The drop", "The drop is the crew’s own wallet. Most contracts pay it, and it pays your share back at a chapter’s end.", "what drop"],
    ["The block clock", "The chain seals transactions into blocks, one after another; the top bar counts them. A taken contract has a trace: a deadline in blocks. Miss it and the contract is lost.", "what trace"],
    ["Your first contract", "take 1, then run: the terminal builds the payment, signs it, sends it and draws its way from wallet to block. Some contracts want the chain to say no: a refusal for the right reason is a win, and nothing is spent.", "take 1"],
    ["Chapters", "Four contracts make a chapter. Then claim: you pay the drop 100 + the chapter’s number, and the crew’s purse pays 500 back.", "what claim"],
    ["The inbox", "After chapter 1 the inbox fills with puzzles that never run out. You build each answer yourself: tx shows the draft, set changes it, send sends it. why explains what the chain did, what <word> explains a word, help lists every command.", "help"],
  ];
  /* the tutorial while playing (the door's Tutorial, or tutorial before the first contract): short notes at the moments they are about */
  const TUTP = {
    take1: "Tutorial · This contract is a real payment. Type run, or click it: the terminal builds the payment, signs it in your browser and sends it to the chain.",
    done1: "Tutorial · That was your first transaction. A test wallet was made for you, and the testnet credited it 100,000 test AGRS. The instruments show block, trace, wallet and balance.",
    take2: "Tutorial · A Tau payment is from, to, amount, signed. No memo: the amount is the only thing you say, and everybody can read it.",
    take3: "Tutorial · The top bar counts blocks; your trace is the deadline in blocks. This contract wants a refusal: the chain says no for the right reason, and that is the win.",
    chap1: "Tutorial · Chapter done. claim pays the drop 101 test AGRS, and the crew’s purse pays 500 back. Then the inbox opens: puzzles you build yourself with set and send.",
    inbox: "Tutorial · That is all you need. what <word> explains any word, help lists every command, feedback tells us what was unclear.",
  };
  function tutAt(ev) {
    if (!S.tutPlay || !TUTP[ev] || (S.tutSaid || []).includes(ev)) return;
    S.tutSaid = [...(S.tutSaid || []), ev]; if (ev === "inbox") S.tutPlay = false; save();
    say("learn", T(TUTP[ev]));
  }
  function tutorial(arg) {
    if (!arg && !Object.keys(S.done).length && !S.taken && !S.job) { S.tutPlay = true; S.tutSaid = []; save(); take(CONTRACTS[0]); return; }
    if (arg === "end" || arg === "off") { S.tut = null; save(); chips(); say("sys", T("Tutorial closed. tutorial opens it again.")); return; }
    let n = parseInt(arg, 10); if (!(n >= 1 && n <= TUT.length)) n = arg === "next" ? Math.min(TUT.length, (S.tut || 0) + 1) : 1;
    S.tut = n; save();
    const [h, text, tryCmd] = TUT[n - 1];
    say("sys", F("Tutorial {n} of {m}: {x}", { n, m: TUT.length, x: h }));
    crew(n === 5 ? "look" : n === 6 || n === 7 ? "qm" : n === 8 ? "bosun" : "qm", text, "calm");
    say("sys", T("Try it:"), btn(tryCmd, tryCmd), n < TUT.length ? btn(F("tutorial {n}", { n: n + 1 }), "tutorial " + (n + 1)) : btn("tutorial end", "tutorial end"));
    if (n === TUT.length) { S.tut = null; save(); say("ok", T("That is all you need. The crew is waiting.")); }
    chips();
  }

  /* ---------- commands ---------- */
  /* help: every command on one screen, in groups side by side; a click on a command types it */
  const HELP = [
    ["Story", [["jobs", "the twelve contracts"], ["take <n>", "take one"], ["run", "build, sign, send"], ["back", "retract a payment"], ["drop", "put it back"], ["claim [n]", "the chapter’s share"], ["chapter <n>", "the chapter’s card"]]],
    ["Inbox", [["inbox", "new work, always"], ["read · accept · decline <j>", ""], ["tx", "your draft"], ["set <field> <value>", "change it"], ["send", "sign and send"], ["hint", "costs a point"], ["predict <CODE>", "your bet"], ["probe · name · final", "intel contracts"], ["why [topic]", "what just happened"], ["archive · history", "your record"], ["daily · unguard", "the day’s order · your rule off"]]],
    ["Ship", [["case", "the week’s case file"], ["pick a|b · answer <n>", ""], ["hunt · mark a|b", "the Tracer’s dust"], ["op", "live ops, Tuesdays"], ["board", "wallets by standing"], ["mail · mail <n>", "letters; some bring special orders"], ["crew", "who is who"], ["scan · blocks · dry", "gear for rank"]]],
    ["Tools", [["tutorial", "the first steps"], ["what <word>", "a word explained"], ["rule", "the chain’s rule, in Tau"], ["showcase · when <s>", "real wallet rules, read them"], ["tau <line>", "a line of Tau, checked"], ["status", "node, wallet, rank"], ["peek <cmd> <hex>", "ask the node"], ["trace <blocks>", "your own deadline"], ["findings", "what must not be"], ["feedback <text>", "tell us"], ["upkeep", "who pays the node"]]],
    ["Terminal", [["sound · ambience on|off", ""], ["fx · voice on|off", ""], ["full · reboot · clear", "reboot: dial the node again"], ["scene · transmission on|off", "the cabin; the crew on screen"]]],
  ];
  function help() {
    const g = el("div", { class: "helpg" });
    for (const [head, rows] of HELP) {
      const box = el("div", null, el("h4", { text: T(head) }));
      for (const [c, d] of rows) box.append(el("p", { title: d ? c + " · " + T(d) : c }, el("button", { type: "button", class: "hc", translate: "no", text: c, onclick: () => { const i = $("cmd"); i.value = c.split(/[ ·<\[]/)[0] + (/[<\[]/.test(c) ? " " : ""); if (!/[<\[]/.test(c) && !/ · /.test(c)) run(c); else i.focus(); } }), d ? el("span", { text: T(d) }) : null));
      g.append(box);
    }
    say("sys", g);
  }
  function status() {
    const pk = myPk(), c = S.taken ? byId(S.taken) : null, j = curJob();
    cols([
      [T("node"), SIM ? T("simulation, a practice node in this browser") : CHAIN.ok ? "node.tauhud.com · " + T("live") : T("out of reach")],
      [T("block"), CHAIN.tip != null ? "#" + fmt(CHAIN.tip) : "—"],
      [T("trace"), c ? F("contract {n} until block {m}", { n: num(c), m: S.deadline != null ? fmt(S.deadline) : "…" }) : j ? F("{x} until block {m}", { x: jname(j), m: S.deadline != null ? fmt(S.deadline) : "…" }) : T("no contract taken")],
      [T("wallet"), pk || T("not made yet")],
      [T("drop"), DROP],
      [T("balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS")],
      [T("standing"), T(rank()) + " · " + F("{n} points", { n: rep() })],
      [T("inbox"), inboxOpen() ? F("{n} open · tier {m} of 4", { n: S.inbox.length, m: tierMax() }) : T("opens when chapter 1 is done")],
      [T("own rule"), S.guard ? (S.guard.cap != null ? F("at most {n} test AGRS a payment", { n: fmt(S.guard.cap) }) : T("one, set elsewhere")) + " · unguard" : T("none")],
      [T("daily"), F("streak {n}", { n: streakNow() }) + (S.dailyLast === dayKey() ? " · " + T("today’s order settled") : "")],
      [T("chapters"), CH.map(ch => ch.n + (S.chap[ch.n] ? " ✓" : chapterDone(ch) ? " ●" : chapterOpen(ch) ? " ○" : " ·")).join("  ")],
    ]);
  }
  function crewList() {
    cols([[T("Quartermaster"), T("hands out the contracts and keeps the ledger; the one who says no memo")], [T("Lookout"), T("reads the block clock, the chain weather and the ship’s calls; gives you the day’s number")], [T("Bosun"), T("keeps the case files and runs the live ops: what the pirates tried, what the hack of the week found")]]);
    say("sys", T("The three of them are game characters. The players are real: everybody at a terminal like this one tests the same chain with you, and every move is a real transaction on it. The Black Sequence is the pirate ship that tests the chain at White Rabbit Key every Tuesday; her logbook is public."), link("/cruise/" + lang(), T("cruise logbook")));
  }
  async function peek(args) {
    if (!has("peek")) { say("sys", T("peek opens with chapter 1: four contracts, then the node answers you directly.")); return; }
    const [c, a0, b] = args, a = a0 === "me" ? myPk() || "" : a0 === "drop" ? DROP : a0;
    if (c === "getgovernance") {
      const r = await ask("getgovernance"); if (!r || r.status !== "ok") { say("no", T("No answer from the node.")); return; }
      const rules = String((r.data && r.data.consensus_rules) || ""); say("sys", rules.slice(0, 1200) || JSON.stringify(r.data).slice(0, 1200));
      const m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec(rules); if (m) say("learn", F("o9 is the base fee: #x{x} in hex.", { x: m[1] }));
      return;
    }
    if (!["getbalance", "getsequence", "gettxstatus", "getretractables"].includes(c) || !/^[0-9a-f]{64,96}$/.test(a || "")) { say("sys", T("peek getbalance <address> · peek getsequence <address> · peek gettxstatus <hash> · peek getretractables <address> · peek getgovernance; me and drop stand for the two addresses")); return; }
    const r = await ask([c, a, b].filter(Boolean).join(" "));
    if (!r) { say("no", T("No answer from the node.")); return; }
    say(r.status === "ok" ? "sys" : "no", JSON.stringify(r.data || r.error || r, null, 1).slice(0, 1200));
  }
  /* ---------- the showcase wallets: three wallets Tau HUD runs on the testnet with real rules of their own
     (infra/relay/showcase.py, GET node.tauhud.com/showcase); the practice node shows the same three, made up ---------- */
  const SHOW = { data: null, at: 0, busy: null };
  const berlinAt = t => new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(t * 1000));
  function simShow() {
    const pk = c => c + "0".repeat(95), until = 1798758000, t = Math.floor(Date.now() / 1000);
    return { ready: true, simulated: true, piggy_until: until, wallets: {
      piggy: { pk: pk("a"), name: "Tau HUD’s piggy bank", rule_text: "always ( (i5[t]:bv[64] < { " + until + " }:bv[64]) ? " + BLOCK_O5 + " : " + ALLOW_O5 + " ).", in_force: true, last_try: { t: t - 7200, outcome: "stopped" } },
      foureyes: { pk: pk("b"), name: "Tau HUD’s four-eyes wallet", rule_text: "always ( ((i1[t]:bv[24] > { #x000064 }:bv[24] || i2[t]:bv[24] < { #x015f90 }:bv[24]) && !(i18[t]:bv[384] = { #x" + pk("8") + " }:bv[384])) ? " + BLOCK_O5 + " : " + ALLOW_O5 + " ).", in_force: true, last_try: { t: t - 3600, outcome: "stopped" } },
      feeding: { pk: pk("9"), name: "Tau HUD’s Agorzilla feeding fund", rule_text: "always ( (i4[t]:bv[384] = { #x" + BOWL + " }:bv[384] && !(i1[t]:bv[24] > { #x000014 }:bv[24]) && !(i2[t]:bv[24] < { #x015f90 }:bv[24])) ? " + ALLOW_O5 + " : " + BLOCK_O5 + " ).", in_force: true, last_try: null } } };
  }
  function showLoad(now) {
    if (SIM) { SHOW.data = SHOW.data || simShow(); return Promise.resolve(SHOW.data); }
    if (SHOW.busy) return SHOW.busy;
    if (!now && Date.now() - SHOW.at < 10 * 60 * 1000) return Promise.resolve(SHOW.data);
    SHOW.at = Date.now();
    SHOW.busy = fetch(RELAY + "/showcase", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(x => { if (x && x.ready) SHOW.data = x; SHOW.busy = null; return SHOW.data; });
    return SHOW.busy;
  }
  const showW = name => { const x = SHOW.data; return x && x.ready && x.wallets && x.wallets[name] && x.wallets[name].in_force ? x.wallets[name] : null; };
  const showUp = name => { showLoad(false); return !!showW(name); };
  const showNum = name => { const w = showW(name), m = w && /i1\[t\]:bv\[24\]\s*>\s*\{\s*#x([0-9a-f]+)/i.exec(w.rule_text || ""); return m ? parseInt(m[1], 16) : null; };
  const showYear = () => { const w = showW("piggy"), m = w && /i5\[t\]:bv\[64\]\s*<\s*\{\s*(\d+)\s*\}/.exec(w.rule_text || ""); return m ? Number(berlinAt(Number(m[1])).slice(0, 4)) : null; };
  const SHOW_NAMES = { piggy: "Tau HUD’s piggy bank", foureyes: "Tau HUD’s four-eyes wallet", feeding: "Tau HUD’s Agorzilla feeding fund" };
  async function showcaseCmd() {
    say("step", T("asking our relay for the showcase wallets …"));
    const x = await showLoad(true);
    if (!x || !x.wallets) { say("no", T("The showcase wallets are not answering just now. Try again in a minute.")); return; }
    for (const k of Object.keys(SHOW_NAMES)) {
      const w = x.wallets[k]; if (!w) continue;
      say("sys", T(SHOW_NAMES[k]) + " · " + short(w.pk) + " · " + (w.in_force ? T("rule in force on the chain") : T("rule not confirmed yet")));
      say("sys", String(w.rule_text || ""));
      const lt = w.last_try; if (lt && lt.t) say(lt.outcome === "stopped" ? "ok" : "warn", F("Last forbidden try: {t}, German time: {x}.", { t: berlinAt(lt.t), x: lt.outcome === "stopped" ? "stopped by its own rule" : lt.outcome === "took" ? "the chain took it, a finding" : "refused for another reason" }));
    }
    say("learn", T("Each of them tries once a day to pay what its own rule forbids (11:00, 15:00 and 19:00 German time); the node refuses it before the mempool, so it costs nothing. In a rule, i1 is the amount, i2 the balance, i4 where the payment goes, i5 the time in seconds, i18 a co-signer."));
    if (x.simulated) say("sys", T("These three are made up by the practice node; on the live node they are Tau HUD’s real wallets."));
  }
  function whenCmd(a) {
    if (!/^\d{1,12}$/.test(a || "")) { say("sys", T("when <seconds since 1970>: that moment, German time and UTC. A rule reads the time as i5, in seconds.")); return; }
    const n = Number(a);
    say("sys", F("{a} German time · {b} UTC", { a: berlinAt(n), b: new Date(n * 1000).toISOString().slice(0, 16).replace("T", " ") }));
  }
  /* unguard: the rule that says o5 = 1 and nothing else, alone in a transaction, takes the wallet's own rule away */
  async function unguard() {
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    if (!B) { say("no", T("This browser cannot sign (no BLS library loaded).")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent. Try again in a minute, or switch to the simulation in the header."), btn("reboot", "reboot")); return; }
    RUN.busy = true; chips();
    try {
      const k = myKey(true), { seq, tip } = await envelope(k.pk), base = await fee();
      const tx = sign({ tx_type: "user_tx", sender_pubkey: k.pk, sequence_number: seq, expiration_time: now() + 600, expire_at_height: tip + 1000, fee_limit: String(base * 5), operations: { "0": NEUTRAL } }, k.sk);
      say("step", T("signing the rule that takes your wallet’s own rule away: o5 = 1 and nothing else"));
      const s = await sendtx(tx);
      if (!s.r) { say("no", T("No answer from the node; nothing was sent. Type unguard again.")); return; }
      if (!s.hash) { say("no", F("The chain said no: {x}", { x: codeOf(s.r) || plain(s.r) })); return; }
      sent(tx, s); say("step", T("waiting for a block …"));
      const w = await sealed(s.hash, null, s.way);
      if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); return; }
      S.guard = null; save(); instruments();
      say("ok", F("Sealed in block {n}. Your wallet carries no rule of its own now.", { n: fmt(w.block) }), explorer(s.hash));
    } catch (e) { say("no", T("The node did not answer in time; nothing is lost. Type unguard again.")); }
    finally { RUN.busy = false; chips(); balance(); }
  }
  /* ---------- the daily order: one contract a day (German days) that pays a point more for each day in a row, up to five.
     The streak lives in this browser ---------- */
  const dayKey = (t = Date.now()) => new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(t));
  const dayBefore = k => dayKey(Date.parse(k + "T12:00:00Z") - 86400000);
  const streakNow = () => (S.dailyLast === dayKey() || S.dailyLast === dayBefore(dayKey()) ? S.streak || 0 : 0);
  const streakNext = () => Math.min(5, S.dailyLast === dayBefore(dayKey()) ? (S.streak || 0) + 1 : 1);
  function dailyTick(tip) {
    const today = dayKey();
    if (S.dailyMade === today || S.dailyLast === today || S.inbox.some(j => j.daily === today)) return null;
    const j = makeJob(); if (!j) return null;
    j.daily = today; j.dbonus = streakNext(); j.special = (j.special || 0) + j.dbonus; j.until = Math.max(j.until, tip + 1500); S.dailyMade = today;
    S.inbox.push(j); return j;
  }
  function dailyWin(j) {
    if (!j.daily) return;
    S.streak = S.dailyLast === dayBefore(j.daily) ? (S.streak || 0) + 1 : S.dailyLast === j.daily ? S.streak || 1 : 1; S.dailyLast = j.daily; save();
    say("ok", F("Today’s order is done. Daily streak: {n} days.", { n: S.streak }));
    if (S.streak >= 3) crew("qm", F("{n} days in a row. The crew notices who comes back.", { n: S.streak }), "glad");
  }
  function dailyCmd() {
    const today = dayKey(), j = S.inbox.find(x => x.daily === today), n = streakNow();
    say("sys", n ? F("Daily streak: {n} days.", { n }) : T("No daily streak yet."));
    if (!inboxOpen()) say("sys", T("Daily orders start once the inbox is open: chapter 1 first."), nextChip());
    else if (S.dailyLast === today) say("ok", T("Today’s order is settled. The next one comes tomorrow, German time."));
    else if (j) say("sys", F("Today’s order: {x}, {n} points more for the streak.", { x: jname(j), n: j.dbonus || 1 }), btn(F("read {x}", { x: jname(j) }), "read " + jname(j)));
    else say("sys", T("Today’s order comes with the next block."));
    say("learn", T("One order a day, German days. Each day in a row adds a point to it, up to five; a day missed starts the streak again. The streak lives in this browser."));
  }
  /* gear for standing: real tools on the real chain */
  const gearLocked = k => { say("sys", F("{x} is gear for the rank {r}.", { x: k, r: GEAR_AT[k] }) + " " + F("You: {x}.", { x: rank() })); };
  const shortH = h => (h ? String(h).slice(0, 6) + "…" + String(h).slice(-4) : "—");
  async function scanCmd() {
    if (!has("scan")) return gearLocked("scan");
    say("step", T("scanning the mempool …"));
    const r = await ask("getmempool"); if (!r || r.status !== "ok") { say("no", T("No answer from the node.")); return; }
    const list = (r.data && r.data.transactions) || [], me = myPk();
    say("sys", F("The mempool: {n} transactions taken by the node, waiting for a block.", { n: list.length }));
    if (list.length) cols(list.slice(0, 8).map(x => [shortH(x.tx_hash), shortH(x.sender) + (x.sender === me ? " · " + T("you") : "") + " · " + F("sequence {n}", { n: x.sequence_number }) + (x.fee_limit != null ? " · " + F("fee limit {n}", { n: x.fee_limit }) : "")]));
    say("learn", T("A payment the node takes waits in the mempool until a block seals it. The fee limit is the most it may cost; the block takes only the base fee."));
  }
  async function blocksCmd() {
    if (!has("blocks")) return gearLocked("blocks");
    const r = await ask("getblocks 5"); if (!r || r.status !== "ok") { say("no", T("No answer from the node.")); return; }
    const bl = ((r.data && r.data.blocks) || []).slice(-5).reverse(), mine = new Set(S.hist.map(h => h.hash));
    cols(bl.map(b => { const ids = b.tx_ids || [], n = (b.header && b.header.block_number); const m = ids.filter(x => mine.has(x)).length;
      return ["#" + fmt(n), F("{n} transactions", { n: ids.length }) + (m ? " · " + F("{n} of yours", { n: m }) : "") + " · " + shortH(b.block_hash)]; }));
    say("learn", T("Each block seals what waited in the mempool, in order, and names the block before it by its hash: that is the chain."));
  }
  async function dryCmd() {
    if (!has("dry")) return gearLocked("dry");
    const j = curJob(); if (!j || !S.draft || kindOf(j).tau || kindOf(j).intel) { say("sys", T("dry checks the draft of a taken contract: accept one, set it up, then dry.")); return; }
    if (SIM) { say("sys", T("The practice node has no dry run. On the live node, dry asks the node’s own checktx.")); return; }
    if (!j.dried) { j.dried = true; save(); say("sys", T("A dry run makes this contract pay 1 point less.")); }
    RUN.dry = true; try { await jobSend(); } finally { RUN.dry = false; }
  }
  function traceSet(arg) {
    if (!has("trace")) { say("sys", T("trace opens with chapter 2.")); return; }
    const n = parseInt(arg, 10), c = cur();
    if (!c) { say("sys", T("Take a contract first; then trace <blocks> sets its deadline.")); return; }
    if (!(n >= 2 && n <= 500)) { say("sys", T("trace <blocks>: 2 to 500.")); return; }
    if (CHAIN.tip == null) { say("sys", T("The block clock has no tip yet.")); return; }
    S.deadline = CHAIN.tip + n; S.span = n; save(); instruments(); topbar();
    say("sys", F("Trace set: until block {n} ({t}).", { n: fmt(S.deadline), t: inTimeE(n) || fill0("{n} blocks", { n }) }));
    if (n <= 3) crew("look", "Three blocks or fewer. Brave. The chain will not wait for your fingers.", "glad");
  }
  /* the other players: how many wallets paid the drop lately (GET /nomemo board.day/hour/last_move, kept by the server) */
  function lastMove(b) {
    if (!b || !b.last_move) return null;
    const sec = Math.max(0, (b.now || Date.now() / 1000) - b.last_move);
    return sec < 90 ? T("The last move was just now.") : sec < 3600 ? F("The last move was {n} min ago.", { n: Math.round(sec / 60) }) : sec < 86400 ? F("The last move was {n} h ago.", { n: Math.round(sec / 3600) }) : F("The last move was {n} days ago.", { n: Math.round(sec / 86400) });
  }
  function crowdLine(b) {
    if (!b || b.day == null) return null;
    return F("{n} wallets paid the crew’s drop in the last 24 hours, {m} in the last hour.", { n: b.day, m: b.hour || 0 }) + (lastMove(b) ? (/lang=(zh|ja)/.test(lang()) ? "" : " ") + lastMove(b) : "");
  }
  async function youAre() {
    const pk = myPk(); if (!pk) return;
    BOARD.at = 0; const d = await boardLoad(), w = await serverInfo("/wallet/" + pk);
    if (w && w.nth) say("sys", F("You are wallet number {n} to pay the crew’s drop. The others play the same chain with you.", { n: w.nth }));
    const l = crowdLine(d && d.board); if (l) say("sys", l);
  }
  async function board() {
    const d = await boardLoad();
    if (!d || !d.board) { say("sys", T("The board is on the server; it is out of reach right now.")); return; }
    const b = d.board;
    if (SIM) say("sys", T("practice board") + ": " + T("made-up numbers in this browser; the live board is on the server."));
    snd.board(); say("sys", F("The players’ board: {n} wallets have paid the drop. Wallets, not people; nobody is named.", { n: b.wallets || 0 }));
    cols(Object.entries(b.ranks || {}).map(([k, n]) => [T(k), String(n)]));
    if (b.claims) say("sys", F("Chapters claimed: {a} · {b} · {c}", { a: b.claims[0] || 0, b: b.claims[1] || 0, c: b.claims[2] || 0 }));
    const l = crowdLine(b); if (l) say("sys", l);
    const pk = myPk(), mine = pk ? pk.slice(0, 6) + "…" + pk.slice(-4) : null;
    if (Array.isArray(b.week_top) && b.week_top.length) {
      say("sys", F("This week’s board: {n} wallets paid the drop since Monday. A payment counts at most once every 30 seconds; it starts from zero every Monday.", { n: b.week_wallets || b.week_top.length }));
      cols(b.week_top.map(([w, n], i) => ["#" + (i + 1), w + " · " + F("{n} payments", { n }) + (w === mine ? " · " + T("you") : "")]));
    } else if (b.week_top) say("sys", T("Nobody has paid the drop this week yet: the first payment leads the week."));
    const w = pk ? await serverInfo("/wallet/" + pk) : null;
    say("sys", F("You: {x}.", { x: rank() }) + (w && w.nth ? " " + F("Wallet number {n} to pay the drop.", { n: w.nth }) : ""));
    if (w && w.week && w.week_place) say("sys", F("This week you stand at number {a}, with {b} payments.", { a: w.week_place, b: w.week }));
  }
  function findings() {
    if (!S.findings.length) { say("sys", T("Nothing. Every refusal so far was the chain doing its job.")); return; }
    for (const f of S.findings) say("warn", `${new Date(f.at).toISOString().slice(0, 16)} ${f.id}: ` + JSON.stringify({ tx: f.tx, answer: f.answer }).slice(0, 1500));
    say("sys", T("Please pass this on:"), link("/findings/" + lang(), T("how to report a finding")));
  }
  /* feedback <text>: the player's words to us, kept on the server (infra/relay/nomemo_feedback.py) with the wallet and how
     far the player is; nothing is shown to anyone else */
  async function feedback(text) {
    if (text.length < 3) { say("sys", T("feedback <text>: what is unclear, too hard, too slow or missing. One line, up to 600 characters."), el("button", { type: "button", class: "abc", text: "feedback …", onclick: () => { const i = $("cmd"); i.value = "feedback "; i.focus(); } })); return; }
    if (text.length > 600) { say("warn", F("Too long: {n} characters. 600 at most, please.", { n: text.length })); return; }
    const q = new URLSearchParams({ t: text, d: String(Object.keys(S.done).length), c: String(Object.keys(S.chap).length), l: (window.TauI18n && TauI18n.lang) || "en" });
    const pk = myPk(); if (pk) q.set("w", pk);
    let r = null;
    try { const x = await fetch(RELAY + "/nomemo/feedback?" + q.toString(), { cache: "no-store" }); r = x.ok ? await x.json() : null; } catch (e) { r = null; }
    if (r && r.ok) { snd.ok(); say("ok", T("Logged. The crew reads every line; thank you.")); return; }
    const why = r && r.error;
    say("warn", why === "wait" ? F("One at a time: try again in {n} s.", { n: r.wait || 30 }) : why === "today" ? T("That is enough for today; thank you. Tomorrow the log is open again.") : why === "short" ? T("A few words more, please.") : why === "long" ? T("600 characters at most, please.") : T("The log is out of reach right now; please try again later."));
  }
  function full(on) {
    const root = document.documentElement, want = on == null ? !root.classList.contains("nm-full") : on;
    root.classList.toggle("nm-full", want);
    try { if (want && root.requestFullscreen && !document.fullscreenElement) root.requestFullscreen({ navigationUI: "hide" }).catch(() => {}); else if (!want && document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {}); } catch (e) {}
    $("fsBtn").textContent = want ? "⤢" : "⛶";
  }
  function exec(line) {
    const s = line.trim(); if (!s) return; cmdLine(s); snd.wake(); snd.enter();
    const [c, ...args] = s.toLowerCase().split(/\s+/);
    if (c !== "reveal") REVEAL = 0;   // giving up an intel contract takes reveal twice in a row
    if (S.job && /^(set|peek|status|history|hist|what|predict)$/.test(c) && !S.jobStep) { S.jobStep = true; save(); setTimeout(chips, 0); }
    if (c === "help" || c === "?") return help();
    if (c === "jobs" || c === "contracts" || c === "board" && args[0] === "jobs") { for (const ch of CH) { say("sys", F("Chapter {n}: {x}", { n: ch.n, x: ch.name }) + (chapterOpen(ch) ? "" : " · " + T("locked"))); cols(ch.ids.map(id => byId(id)).map(x => [String(num(x)).padStart(2, " ") + (S.done[x.id] ? " ✓" : S.taken === x.id ? " ●" : "  "), T(x.name) + " · " + T(x.task)])); } const nx = CONTRACTS.find(y => !S.done[y.id]); return say("sys", T("take <n> takes one."), nx ? btn(F("take {n}", { n: num(nx) }), "take " + num(nx)) : null); }
    if (c === "take") { const n = parseInt(args[0], 10), x = args[0] === "next" || !args[0] ? CONTRACTS.find(y => !S.done[y.id]) : n >= 1 && n <= CONTRACTS.length ? CONTRACTS[n - 1] : byId(args[0]); return x ? take(x, args[1] === "again") : say("sys", T("take <n>: a number from the board, or take next.")); }
    if (c === "tutorial" || c === "tut" || c === "run" && args[0] === "tutorial") return tutorial(c === "run" ? args[1] : args[0]);
    if (c === "what" && /^what (is )?(this|it|no memo|nomemo|this game|the game)\??$/.test(s.toLowerCase())) return about();
    if (c === "what" && args.length && !/^(do|should|now|next|to)$/.test(args[0])) return what(s.slice(4));
    if (c === "run") return OP.list ? opGo() : S.job ? jobSend() : carry();
    if (c === "inbox" || c === "in") return inboxList();
    if (c === "read" || c === "open") return readJob(args[0]);
    if (c === "accept") return /^m\d+$/.test(args[0] || "") ? takeOffer(mailOf(args[0])) : accept(args[0]);
    if (c === "decline" || c === "delete" || c === "del") return decline(args[0]);
    if (c === "tx" || c === "draft") return draftShow();
    if (c === "set") return setDraft(args);
    if (c === "reset") { if (S.draft && curJob()) { const j = curJob(); S.draft = DRAFT0(); if (j.lock) for (const [f, v] of j.lock) S.draft[f] = v; save(); return draftShow(); } return say("sys", T("No draft: accept a contract from the inbox first.")); }
    if (c === "send") return S.job ? jobSend() : say("sys", T("No contract from the inbox taken. Type inbox."));
    if (c === "predict") return predict(args[0]);
    if (c === "probe") return probeCmd(args.join(" "));
    if (c === "probes") return intelJob() ? intelShow(intelJob()) : intelNone("probes");
    if (c === "name") return nameCmd(args);
    if (c === "final") return finalCmd(args.join(" "));
    if (c === "reveal") return revealCmd();
    if (c === "hint") return hintJob();
    if (c === "why" || c === "learn") return why(args[0]);
    if (c === "archive") return archiveList();
    if (c === "history" || c === "hist") return historyList();
    if (c === "go") return opGo();
    if (c === "back" || c === "retract") return back();
    if (c === "drop" || c === "abort") { if (OP.list) { OP.list = null; chips(); return say("sys", T("The op is put down.")); } if (S.job && !RUN.busy) { const x = "j" + S.job; S.job = null; S.deadline = null; S.span = null; S.draft = null; S.pred = null; save(); jobs(); instruments(); topbar(); chips(); return say("sys", F("{x} is back in the inbox.", { x })); } if (!S.taken) return say("sys", T("No contract taken.")); if (RUN.busy) return say("warn", T("A contract is under way; wait for the chain’s answer.")); S.taken = null; S.deadline = null; S.span = null; RUN.ret = S.ret = null; save(); jobs(); instruments(); topbar(); chips(); return say("sys", T("Back on the board.")); }
    if (c === "claim") { if (/^\d+$/.test(args[0] || "") && !/^[123]$/.test(args[0])) return say("warn", T("Chapters are 1, 2 and 3.")); return claim(/^[123]$/.test(args[0] || "") ? +args[0] : 0, args.includes("again")); }
    if (c === "chapter" || c === "ch") { const ch = CH[parseInt(args[0], 10) - 1] || CH.find(x => !chapterDone(x)) || CH[2]; return chapterCard(ch); }
    if (c === "mail" || c === "post") return mailOpen(args[0]);
    if (c === "op" || c === "ops") return op();
    if (c === "case" || c === "file") return caseFile();
    if (c === "pick") return pick(args[0]);
    if (c === "answer") return answer(args[0]);
    if (c === "hunt") return hunt();
    if (c === "mark") return markPick(args[0]);
    if (c === "status") return status();
    if (c === "peek") return peek(args);
    if (c === "trace") return traceSet(args[0]);
    if (c === "heat") return heatCmd();
    if (c === "week") return weekCmd();
    if (c === "scan") return scanCmd();
    if (c === "blocks") return blocksCmd();
    if (c === "dry") return dryCmd();
    if (c === "showcase" || c === "showcases") return showcaseCmd();
    if (c === "when") return whenCmd(args[0]);
    if (c === "unguard") return unguard();
    if (c === "daily" || c === "streak") return dailyCmd();
    if (c === "board") return board();
    if (c === "tau") return tauCmd(s.slice(3));
    if (c === "rule" || c === "rules" || (c === "explain" && /^rules?$/.test(args[0] || ""))) return ruleCmd();
    if (c === "findings") return findings();
    if (c === "crew") return crewList();
    if (c === "upkeep") return say("sys", T("This terminal dials node.tauhud.com, a community node with a monthly bill. The Tau HUD crew is a paid membership that carries part of it:"), link("/crew/?ref=nomemo", "tauhud.com/crew"));
    if (c === "feedback" || c === "fb") return feedback(s.slice(s.search(/\s/) < 0 ? s.length : s.search(/\s/)).trim());
    if (c === "clear" || c === "cls") return clearScreen();
    if (c === "wallet") { window.open("/wallet/" + lang(), "_blank", "noopener"); return; }
    if (c === "lang" || /^(language|languages|chinese|japanese|english|中文|汉语|日本語|日本语)$/.test(c)) { const want = { chinese: "zh", 中文: "zh", 汉语: "zh", japanese: "ja", 日本語: "ja", 日本语: "ja", english: "en" }[c] || args[0]; if (window.TauI18n && TauI18n.set && ["en", "zh", "ja"].includes(want)) TauI18n.set(want); else say("sys", T("Language:"), btn("lang en", "lang en"), btn("lang zh", "lang zh"), btn("lang ja", "lang ja")); return; }
    if (c === "sound" || c === "fx" || c === "voice" || c === "ambience" || c === "amb") { const k = c === "amb" ? "ambience" : c; if (!["on", "off"].includes(args[0])) return say("sys", k + " on · " + k + " off"); S[k === "sound" ? "snd" : k === "ambience" ? "amb" : k] = args[0] === "on"; save(); topbar(); if (S.snd) snd.wake(); else snd.ambience(); return switched(k, args[0] === "on"); }
    if (c === "full" || c === "fullscreen") return full();
    if (c === "reboot" || c === "boot" || c === "restart") return reboot();
    if (alias(c, args, s)) return;
    if (/^(what|how|where|next|start|begin|go|hi|hello|hilfe|was|wie|\?)$/.test(c) || /what (do|should|now|next)/.test(s.toLowerCase())) return nextStep();
    say("sys", F("Unknown: {x}. Type help, or click:", { x: c }), nextChip(), btn("help", "help"));
  }
  /* sound, ambience, fx, voice on|off: what it changed, in words (the command line already shows what was typed) */
  function switched(k, on) {
    const L = { sound: ["Sound is on.", "Sound is off."], ambience: ["The sea and the hull are on.", "The sea and the hull are off."], fx: ["Effects are on.", "Effects are off."], voice: ["The crew’s voices are on.", "The crew’s voices are off."] }[k];
    say("ok", T(L[on ? 0 : 1]));
    if (on && (k === "voice" || k === "ambience") && !S.snd) say("sys", T("Sound is off, so you hear nothing yet:"), btn("sound on", "sound on"));
    if (on && k === "voice" && SIM) say("sys", T("The voices play on the live node only, not in the simulation."));
  }
  /* what players type before they know the commands: the nearest command, or a short answer and the next step */
  function about() {
    say("sys", T(DOOR[0])); say("sys", T(DOOR[1]));
    say("sys", T("The tutorial plays the first contracts with you, step by step:"), btn("tutorial", "tutorial"), nextChip());
  }
  function alias(c, args, s) {
    const line = s.toLowerCase();
    if (/^\d{1,2}$/.test(c) && +c >= 1 && +c <= CONTRACTS.length) { take(CONTRACTS[+c - 1]); return true; }
    if (/^(score|scores|me|stats|profile|level|xp|rank|balance|money|inventory|inv|items|gear)$/.test(c)) { status(); return true; }
    if (/^(leaderboard|highscore|highscores|top|players|player|multiplayer|online|others|who)$/.test(c) || /who (else )?(is )?(playing|online|here)/.test(line)) {
      say("sys", T("You are not alone: everybody at a terminal like this one plays the same chain with you, right now. The board counts their wallets; it never shows names.")); board(); return true; }
    if (/^(missions?|quests?|tasks?|list|ls|dir|menu|contract)$/.test(c)) { exec("jobs"); return true; }
    if (/^(whoami|id)$/.test(c)) { const pk = myPk(); say("sys", pk ? F("You are wallet {h}: to the chain, whoever holds its key is you.", { h: short(pk) }) : T("Nobody yet: a test wallet is made in this browser at your first contract."), nextChip()); return true; }
    if (/^(pwd|cd|ssh|telnet|connect|login|logon|register|signup|signin)$/.test(c)) { say("sys", T("No login and no setup: your wallet is your access, made in this browser at your first contract. You are aboard the Black Sequence, at the crew terminal."), nextChip()); return true; }
    if (/^(sudo|su|root|nmap|hack|crack|exploit|rm|chmod|ping|bruteforce)$/.test(c)) { crew("bosun", "Nice try. On this ship root is a signature, and only your key makes yours. If you want to break something, break the chain’s rules: every contract here is that attempt, and a trick the chain takes is a finding.", "calm"); say("sys", T("Next:"), nextChip()); return true; }
    if (/^(buy|faucet|coins|agrs|shop|free)$/.test(c)) { what("faucet"); say("sys", T("Next:"), nextChip()); return true; }
    if (/^(restart|reset|undo|new|newgame)$/.test(c) || /^new game/.test(line)) { say("sys", T("Nothing to restart: your progress lives in this browser and on the chain. A settled contract can be played again: take <n> again."), nextChip()); return true; }
    if (/^(quit|exit|logout|bye|q)$/.test(c)) { say("sys", T("There is no way off a ship at sea. Close the tab whenever you like: the board keeps your place."), nextChip()); return true; }
    if (/^(about|info|intro|story|game)$/.test(c)) { about(); return true; }
    if (/^(ok|okay|yes|y|sure|k|yep|ja|play|pay|continue|home|map|skip|now)$/.test(c)) { nextStep(); return true; }
    if (/^(no|n|nope|nein)$/.test(c)) { say("sys", T("Fine. Whenever you are ready:"), nextChip()); return true; }
    if (/^(settings|options|config)$/.test(c)) { say("sys", T("Settings are commands: sound, ambience, fx, voice, transmission and scene on|off; lang en|zh|ja.")); return true; }
    return false;
  }
  /* the inbox's next step for the main button: a contract read is accepted next; a taken one gets the hint's step first
     (once), the hint after a miss, else send */
  function inboxGo() {
    const r = S.lastRead && jobOf(S.lastRead), j = S.inbox[0];
    return r ? [F("accept {x}", { x: jname(r) }), "accept " + jname(r), true] : [F("read {x}", { x: jname(j) }), "read " + jname(j), true];
  }
  function jobGo() {
    const j = curJob(), go = tryCmd(j);
    if (j && kindOf(j).intel) return !(j.probes || []).length && go && j.hinted ? [go, go, true] : ["probe …", "probe", true];
    if (j && j.hinted && go && !S.jobStep) return [go, go, true];
    if (j && !j.hinted && kindOf(j).hint && S.jobMiss) return ["hint", "hint", true];
    return ["send", "send", true];
  }
  /* what to do now, as a line and a chip: the one answer to "what should I do" */
  function nextChip() {
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    if (OP.list) return btn("go", "go");
    if (S.taken) return RUN.ret && S.taken === "wayback" ? btn("back", "back") : btn("run", "run");
    if (S.job) { const g = jobGo(); return btn(g[0], g[1]); }
    if (claimable) return btn("claim", "claim");
    if (next) return btn(F("take {n}", { n: num(next) }), "take " + num(next));
    if (S.inbox.length) { const g = inboxGo(); return btn(g[0], g[1]); }
    return btn("case", "case");
  }
  function nextStep() {
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]), c = S.taken ? byId(S.taken) : null;
    if (OP.list) say("sys", T("An op is open: type go to send the next trick."), nextChip());
    else if (c && RUN.ret && c.id === "wayback") say("sys", T("Your payment waits in escrow: type back to take it back before the release."), nextChip());
    else if (c) say("sys", F("Contract {n} is yours: type run to carry it out.", { n: num(c) }), nextChip());
    else if (intelJob()) say("sys", F("{x} is yours: probe <amount> asks the guard; probes lists what it said.", { x: jname(curJob()) }), btn("probes", "probes"), nextChip());
    else if (curJob()) say("sys", F("{x} is yours: tx shows the draft, set changes it, send sends it.", { x: jname(curJob()) }), btn("tx", "tx"), nextChip());
    else if (claimable) say("sys", F("Chapter {n} is done: type claim, and the drop pays the crew’s share back.", { n: claimable.n }), nextChip());
    else if (next) say("sys", F("Take the next contract: take {n}. Then run.", { n: num(next) }), nextChip());
    else if (S.inbox.length) say("sys", T("The story board is clear; the inbox keeps coming. Read one, accept it, build the draft, send."), nextChip());
    else say("sys", T("The board is clear. The case file (case) and the live ops on Tuesdays (op) are what is left; the hunt (hunt) once the Tracer has found you."), nextChip());
  }
  const run = line => exec(line);
  /* the chips: the next sensible command is always one click away */
  let NEXTGO = null;   // the green chip's [label, command], for a "Next:" button where the terminal would otherwise end on "read"
  function chips() {
    const box = $("chips"); if (!box) return;
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    const list = [["help", "help"]];
    if (OP.list) { if (!RUN.busy) list.push(["go", "go", true]); }
    else if (S.taken) { if (RUN.ret && S.taken === "wayback") list.push(["back", "back", true]); else if (!RUN.busy) list.push(["run", "run", true]); }
    else if (intelJob()) { const j = intelJob(), kd = kindOf(j); if (!RUN.busy) list.push(jobGo()); if ((j.probes || []).length) list.push(["probes", "probes"]); list.push(kd.final ? ["final …", "final"] : ["name …", "name"]); if (!j.hinted && kd.hint) list.push(["hint", "hint"]); }
    else if (S.job) { if (!RUN.busy) list.push(jobGo()); if (jobGo()[1] !== "send") list.push(["send", "send"]); list.push(["tx", "tx"]); if (curJob() && curJob().k === "predict" && !S.pred) list.push(["predict …", "predict"]); if (curJob() && !curJob().hinted) list.push(["hint", "hint"]); }
    else if (claimable) list.push([T("claim"), "claim", true]);
    else if (next) list.push([F("take {n}", { n: num(next) }), "take " + num(next), true]);
    else if (S.inbox.length) list.push(inboxGo());
    if (inboxOpen()) list.push([S.inbox.length ? F("inbox {n}", { n: S.inbox.length }) : T("inbox"), "inbox"]);
    if (HUNT.data) list.push(["mark a", "mark a"], ["mark b", "mark b"]);
    else if (CASE.data && !S.cases[CASE.data.id]) list.push(["pick a", "pick a"], ["pick b", "pick b"]);
    list.push(["jobs", "jobs"], ["status", "status"], ["case", "case"]);
    if (S.lastTopic) list.push(["why", "why"]);
    if (S.tut && S.tut < TUT.length) list.splice(1, 0, [F("tutorial {n}", { n: S.tut + 1 }), "tutorial " + (S.tut + 1), true]);
    else if (!Object.keys(S.done).length && !S.taken) list.splice(1, 0, ["tutorial", "tutorial"]);
    if (shipIn() && !OP.list && !SIM) list.push(["op", "op", true]);
    if (S.mail.some(m => !m.read && m.due <= (CHAIN.tip ?? 0))) list.push([T("mail"), "mail"]);
    NEXTGO = list.find(x => x[2]) || null;
    box.replaceChildren(...list.map(([t, cmd, go]) => el("button", { type: "button", class: go ? "go" : "", text: t, onclick: () => { run(cmd); $("cmd").focus({ preventScroll: true }); } })));
  }

  /* the start lines: the node is asked afresh (block, wallet, balance, the board), then what is still yours.
     boot() runs it once; reboot runs it again after the boot screen, and nothing of the player is reset */
  async function hello() {
    say("sys", "NO MEMO · " + T("a hacker game on Tau Testnet Alpha: every contract is a real transaction from a test wallet in your browser, and everybody plays the same chain."));
    const pk = myPk();
    if (SIM) say("sys", T("simulation: a practice node in this browser, nothing reaches the testnet"));
    const st = await ask("getsequence " + (pk || DROP));
    if (st && st.status === "ok") { tick(Number(st.data.tip_height) || 0); if (!SIM) snd.say("v-online"); say("sys", (SIM ? T("practice node ready") : T("connected")) + " · " + F("block #{n}", { n: fmt(CHAIN.tip) })); if (pk) { CHAIN.seq = Number(st.data.sequence_number) || 0; await balance(); } }
    else { setState(false); say("warn", T("The node is out of reach from here (a blocker, a VPN, a restart). The board can be read; contracts wait until it answers. The header switch opens the simulation.")); say("sys", T("When it is back, reboot dials it again:"), btn("reboot", "reboot")); }
    say("sys", pk ? F("your wallet {h}", { h: short(pk) }) + (CHAIN.bal != null ? " · " + fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS") : "") : T("no test wallet yet: one is made in this browser at your first contract"));
    const done = Object.keys(S.done).length;
    { const d = await Promise.race([boardLoad(), new Promise(r => setTimeout(() => r(null), 2500))]); const l = crowdLine(d && d.board); if (l) say("sys", (SIM ? T("practice board") + " · " : "") + l); }
    if (!done) crew("qm", "Rule one on this ship: no memo. A payment is from, to, amount, signed; if you have something to say, say it in the amount. Take the first contract.", "calm");
    else { say("sys", F("{n} of {m} contracts settled before. Standing: {r}.", { n: done, m: CONTRACTS.length, r: rank() })); crew("qm", "Back aboard. The board remembers you; so does the chain.", "calm"); }
    if (S.taken === "wayback" && S.ret && S.ret.release > now() + 30) { RUN.ret = S.ret; crew("bosun", F("Your 50 test AGRS still wait in escrow ({h}), release at {t}. Type back.", { h: short(S.ret.id), t: clock(S.ret.release) })); }
    else if (S.taken) { const c = byId(S.taken); if (c && c.id !== "wayback") say("sys", F("Contract {n} is still yours: {t}. Type run.", { n: num(c), t: c.name }), btn("run", "run")); else { S.taken = null; S.deadline = null; S.ret = null; save(); } }
    if (S.job) { const j = curJob(); if (j && kindOf(j).intel) say("sys", F("{x} is still yours: {t}. probe <amount> asks the guard.", { x: jname(j), t: kindOf(j).name }), btn("probes", "probes")); else if (j) say("sys", F("{x} is still yours: {t}. tx shows the draft, send sends it.", { x: jname(j), t: heistOf(j) ? heistOf(j).name : kindOf(j).name }), btn("tx", "tx"), btn("send", "send")); else { S.job = null; S.draft = null; S.deadline = null; save(); } }
    const claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    if (claimable) say("sys", F("Chapter {n} is done and its share unclaimed.", { n: claimable.n }), btn("claim", "claim"));
    else if (!done) say("sys", T("New here? The tutorial plays the first contracts with you. Or type help, or click:"), btn("tutorial", "tutorial"), btn("take 1", "take 1"), el("span", { class: "cur" }));
    else { const nx = CONTRACTS.find(x => !S.done[x.id]); say("sys", T("Type help, or click:"), nx ? btn(F("take {n}", { n: num(nx) }), "take " + num(nx)) : btn("case", "case"), el("span", { class: "cur" })); }
  }

  /* ---------- boot ---------- */
  async function boot() {
    load(); faces(); jobs(); instruments(); chips(); topbar(); art();
    const hist = []; let hi = 0;
    const input = $("cmd");
    $("cmdForm").addEventListener("submit", e => { e.preventDefault(); const v = input.value; input.value = ""; if (v.trim()) { hist.push(v); hi = hist.length; } run(v); });
    input.addEventListener("keydown", e => { if (e.key.length === 1) snd.key(); if (e.key === "ArrowUp" && hist.length) { hi = Math.max(0, hi - 1); input.value = hist[hi]; e.preventDefault(); } else if (e.key === "ArrowDown") { hi = Math.min(hist.length, hi + 1); input.value = hist[hi] || ""; e.preventDefault(); } });
    $("mtabs").addEventListener("click", e => { const b = e.target.closest("button[data-pane]"); if (!b) return; for (const x of $("mtabs").querySelectorAll("button")) x.classList.toggle("on", x === b); const map = { jobs: "paneJobs", term: "paneTerm", stat: "paneStat" }; for (const k in map) $(map[k]).classList.toggle("show", k === b.dataset.pane); });
    $("screenWrap").addEventListener("click", e => { if (!e.target.closest("a") && !e.target.closest("button") && !window.getSelection().toString()) input.focus({ preventScroll: true }); });
    $("ptabs").addEventListener("click", e => { const b = e.target.closest("button[data-p]"); if (!b) return; S.pane = b.dataset.p; save(); jobs(); });
    $("mailBtn").addEventListener("click", () => run("mail")); $("mailClose").addEventListener("click", () => $("mailWin").classList.remove("show"));
    $("sndBtn").addEventListener("click", () => { S.snd = !S.snd; save(); topbar(); if (S.snd) { snd.wake(); snd.ok(); } else snd.ambience(); });
    document.addEventListener("pointerdown", () => snd.wake(), { once: true }); $("fsBtn").addEventListener("click", () => full()); $("rebootBtn").addEventListener("click", () => run("reboot"));
    for (const id of ["card", "mailWin"]) $(id).addEventListener("click", e => { if (e.target === $(id)) $(id).classList.remove("show"); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") for (const id of ["card", "mailWin"]) $(id).classList.remove("show"); });
    let first = null;
    if (!S.booted) first = await door(); else if (q.get("boot")) await bootScreen();
    await hello();
    jobs(); instruments(); chips(); topbar(); watch(); world(); boardLoad(); deliverMail();
    for (const n of [1, 2, 3]) if (S.chap[n] && !S.chap[n].paid) watchPayback(n);
    if (first) run(first);
    /* "First contract" at the door is the decision: contract 1 (1 test AGRS to the drop) runs by itself after the crew's line,
       so the first sealed block comes about 5 s sooner (24 s median in the 9.11 run, 20 s is the aim) */
    if (first === "take 1" && S.taken && !S.done[CONTRACTS[0].id]) setTimeout(() => { if (S.taken && !RUN.busy) run("run"); }, 1500);
    if (S.chap[1] && !S.seen.dust) huntWatch();
    if (q.get("take")) { const x = byId(q.get("take")) || CONTRACTS[parseInt(q.get("take"), 10) - 1]; if (x) take(x); }
    document.addEventListener("visibilitychange", () => { if (!document.hidden) { watch(); world(); } });
    setInterval(world, 120000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
