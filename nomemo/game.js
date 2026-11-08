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
   sounds (WebAudio, nothing loaded) mark keys, sends, refusals and seals. All of it can be switched off: fx off,
   sound off; prefers-reduced-motion is respected.

   The crew: three faces (nomemo/art/crew/<who>-<mood>.webp when the painted set is there, drawn placeholders until
   then) with moods, lines spoken aloud when the server has their clips (same clips store as the islanders',
   node.tauhud.com/rico/<key>.mp3), reactions to the testnet (GET /load) and to the Black Sequence's own call on
   Tuesdays (GET /cruise), and post: messages that arrive a block or two after something happened.

   Chapters: four contracts each. At a chapter's end the player claims the crew's share: a payment of 100 + chapter to
   the drop (the amount is the message), and the crew's purse on the server (infra/relay/nomemo.py) pays the share
   back and, once, the crew's mark. The server also keeps the players' board (wallets by standing, no names) and, when
   it is on, the Tracer: after chapter one a lookalike of the drop sends dust to the player's wallet, and the hunt is to
   tell the two apart by their whole address (GET /nomemo, /nomemo/wallet/<address>).

   Weekly ops: while the Black Sequence lies in port on Tuesday (GET /cruise), `op` opens live contracts that mirror
   what the pirates are trying that very hour. The case file (`case`) reads the hack of the week (GET /hack), the
   pirates' logbook (GET /cruise/log) and asks two riddles answered from the chain itself.

   State in localStorage (tauhud-nomemo). A trick the chain takes although it must not is kept there too (findings),
   shown to the player with the record, never posted anywhere by itself.

   Debug: ?take=<id> takes a contract on load; ?boot=1 shows the boot screen again. */
(() => {
  "use strict";
  const T = s => (window.TauI18n ? TauI18n.t(s) : s);
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

  /* ---------- state ---------- */
  let S = null;
  function load() {
    try { S = JSON.parse(store.get(SAVE) || "null"); } catch (e) { S = null; }
    if (!S || !(S.v === 1 || S.v === 2)) S = { v: 2, done: {}, taken: null, deadline: null, cases: {}, findings: [], hist: [] };
    S.v = 2;
    for (const k of ["done", "cases", "ops", "riddles", "chap", "seen", "hunt"]) S[k] = S[k] || {};
    for (const k of ["findings", "hist", "mail"]) S[k] = S[k] || [];
    if (S.snd == null) S.snd = true; if (S.fx == null) S.fx = !REDUCED; if (S.voice == null) S.voice = true;
  }
  const save = () => store.set(SAVE, JSON.stringify(S));
  const rep = () => Object.keys(S.done).length + Object.keys(S.cases).length + Object.keys(S.ops).length + Object.keys(S.riddles).length + Object.keys(S.hunt).length;
  const RANKS = [[0, "stowaway", "stowaway"], [1, "deckhand", "deckhand"], [4, "rigger", "rigger"], [8, "navigator", "navigator"], [12, "quartermaster’s mate", "master"]];
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
  const GEAR = [["jobs", "the board", true], ["case", "the case file", true], ["peek", "ask the node yourself", () => chapterDone(CH[0])], ["trace", "set your own deadline", () => chapterDone(CH[1])], ["hunt", "the Tracer", () => chapterDone(CH[2])]];
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
      after: "Made the block. Twelve of twelve: the board is clear. Claim the crew’s share, then come by on a Tuesday evening when the ship is in; the live ops are the real thing." },
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
  const CODES = ["INSUFFICIENT_FUNDS", "TX_REJECTED", "INVALID_SEQUENCE", "TX_EXPIRED", "INVALID_SIGNATURE", "TX_INVALID", "FEE_LIMIT_TOO_LOW", "INVALID_PARAMS", "NOT_RETRACTABLE_SENDER", "FORBIDDEN", "RATE_LIMITED"];
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
        for (const op of (tx.operations && tx.operations["1"]) || []) {
          const [from, to, amt] = op, n = Number(amt);
          if (!/^[0-9a-f]{96}$/.test(to || "")) return err("sendtx", "recipient is not a key", "INVALID_PARAMS");
          if (!(n > 0) || n >= GIANT || String(amt) !== String(Math.floor(n))) return err("sendtx", `amount ${amt} does not fit a 24-bit transfer`, "INVALID_PARAMS");
          if (from !== tx.sender_pubkey) return err("sendtx", "the transfer’s payer is not the signer", "TX_INVALID");
          if (!(fee >= 10)) return err("sendtx", "fee_limit below the base fee of 10", "FEE_LIMIT_TOO_LOW");
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
          if (c === "getgovernance") return ok(c, { consensus_rules: "(o9[t]:bv[24] = {#x00000a}:bv[24])" });
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
        if (path === "") return { simulated: true, enabled: true, tracer: true, drop: DROP, share: SHARE, board: { wallets: 7, ranks: { stowaway: 2, deckhand: 2, rigger: 1, navigator: 1, "quartermaster’s mate": 1 }, claims: [4, 2, 1] } };
        const m = /^\/wallet\/([0-9a-f]{96})$/.exec(path); if (!m) return null;
        const x = w(m[1]); return { wallet: m[1], claims: x.claims, dust: x.dust, drop: DROP };
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
  const sign = (tx, sk) => ({ ...tx, signature: B.bytesToHex(B.sign(new TextEncoder().encode(canon(preimage(tx))), sk)) });
  async function fee() {
    if (CHAIN.fee != null) return CHAIN.fee;
    const g = await ask("getgovernance"), m = /o9\[t\]:bv\[24\]\s*=\s*\{\s*#x([0-9a-fA-F]+)/.exec((g && g.data && g.data.consensus_rules) || "");
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
      const lk = "tauhud-wallet-log-live-" + tx.sender_pubkey, logs = JSON.parse(store.get(lk) || "[]"), amount = tx.tx_type === "user_tx" ? tx.operations["1"][0][2] : tx.amount;
      logs.unshift({ hash: r.data && r.data.tx_hash, kind: tx.tx_type === "retract_transfer" ? "retract" : "pay", label: "No Memo" + (amount != null ? ": " + amount : ""), at: Date.now(), status: "queued", seq: tx.sequence_number, paid: tx.fee_limit !== "0" });
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
    if (newBlock) { snd.tick(S.taken && traceFrac() < 0.25); deliverMail(); }
    if (S.taken && S.deadline != null && tip > S.deadline && !RUN.busy) traced();
  }
  const pace = () => (SIM && window.TauSim ? TauSim.pace : CHAIN.pace);
  const inTime = blocks => { const s = pace(); if (!s || blocks < 0) return ""; const m = blocks * s / 60; return m < 1 ? T("under a minute") : F("about {m} min", { m: Math.round(m) }); };
  const traceLeft = () => (S.taken && S.deadline != null && CHAIN.tip != null ? S.deadline - CHAIN.tip : null);
  const traceFrac = () => { const left = traceLeft(), c = S.taken ? byId(S.taken) : null; const span = c ? (S.span || c.trace) : TRACE; return left == null ? 0 : Math.max(0, Math.min(1, left / span)); };
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

  /* ---------- sounds: small synthetic ones, made here, nothing loaded ---------- */
  const snd = (() => {
    let ctx = null;
    const on = () => S && S.snd && !q.get("quiet");
    const ac = () => { if (!on()) return null; try { ctx = ctx || new (window.AudioContext || window.webkitAudioContext)(); if (ctx.state === "suspended") ctx.resume(); return ctx; } catch (e) { return null; } };
    function tone(f, ms, type = "square", gain = 0.05, slide = 0) {
      const c = ac(); if (!c) return;
      const o = c.createOscillator(), g = c.createGain(), t = c.currentTime;
      o.type = type; o.frequency.setValueAtTime(f, t); if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, f + slide), t + ms / 1000);
      g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
      o.connect(g).connect(c.destination); o.start(t); o.stop(t + ms / 1000 + 0.02);
    }
    return {
      wake: () => ac(),
      key: () => tone(1800 + Math.random() * 400, 18, "square", 0.012),
      send: () => { tone(520, 70, "square", 0.03, 400); setTimeout(() => tone(900, 60, "square", 0.025, 500), 70); },
      ok: () => { tone(660, 90, "triangle", 0.05); setTimeout(() => tone(990, 140, "triangle", 0.05), 90); },
      no: () => { tone(140, 180, "sawtooth", 0.05, -60); },
      tick: hot => tone(hot ? 1400 : 1000, hot ? 40 : 30, "square", hot ? 0.03 : 0.015),
      out: () => { tone(200, 300, "sawtooth", 0.06, -120); setTimeout(() => tone(160, 350, "sawtooth", 0.05, -100), 220); },
      mail: () => { tone(1200, 60, "triangle", 0.04); setTimeout(() => tone(1600, 90, "triangle", 0.04), 80); },
      boot: () => { tone(80, 900, "sawtooth", 0.03, 300); setTimeout(() => tone(440, 120, "triangle", 0.04), 900); },
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
  function crew(who, text, m) { if (m) mood(who, m); talking(who); speak(who, text); return say("crew", null, el("b", { text: T(CREW[who]) + ":" }), " " + T(text)); }
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
    const left = traceLeft(), frac = traceFrac(), tr = $("topTrace"), c = S.taken ? byId(S.taken) : null;
    tr.className = "tr" + (c ? (left != null && left < 0 ? " out" : frac < 0.25 ? " hot" : " on") : "");
    tr.style.setProperty("--p", Math.round(frac * 100) + "%");
    $("topTraceText").textContent = c ? (left != null ? F("trace {n} blocks", { n: Math.max(0, left) }) : T("trace …")) : T("no trace");
    const h = document.documentElement; h.classList.toggle("tr-on", !!c && frac >= 0.25); h.classList.toggle("tr-hot", !!c && frac < 0.25 && !(left != null && left < 0));
    const unread = S.mail.filter(m => !m.read && m.due <= (CHAIN.tip ?? 0)).length;
    const mb = $("mailBtn"); mb.textContent = unread ? F("post {n}", { n: unread }) : T("post"); mb.classList.toggle("has", unread > 0);
    $("sndBtn").textContent = S.snd ? "♪" : "♪̸"; $("sndBtn").title = T(S.snd ? "sound on (click: off)" : "sound off (click: on)");
  }

  /* ---------- the post: what the crew sends a block or two later ---------- */
  function post(who, text, blocks, m) {
    S.mail.unshift({ who, text, m, at: Date.now(), due: (CHAIN.tip ?? 0) + (blocks == null ? 1 : blocks), read: false }); S.mail = S.mail.slice(0, 40); save(); topbar();
    if (blocks === 0) deliverMail();
  }
  function deliverMail() {
    const due = S.mail.filter(x => !x.told && x.due <= (CHAIN.tip ?? 0)); if (!due.length) return;
    for (const x of due) x.told = true; save(); topbar(); snd.mail();
    const x = due[due.length - 1];
    say("sys", F("post from the {x}: type mail", { x: T(CREW[x.who]) }), btn(T("read"), "mail"));
  }
  function mailOpen() {
    const list = $("mailList"); $("mailTitle").textContent = T("Post");
    const have = S.mail.filter(m => m.due <= (CHAIN.tip ?? 0));
    list.replaceChildren(...(have.length ? have.map(m => el("li", { class: m.read ? "" : "new" }, el("b", { text: T(CREW[m.who]) }), el("small", { text: new Date(m.at).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" }) }), el("p", { text: T(m.text), style: "margin:3px 0 0" }))) : [el("li", { text: T("Nothing yet. The crew writes after a contract settles, and when something happens on the chain.") })]));
    for (const m of have) m.read = true; save(); topbar();
    $("mailWin").classList.add("show");
  }

  /* ---------- the panes ---------- */
  function jobs() {
    const ol = $("jobs"); if (!ol) return;
    const next = CONTRACTS.find(c => !S.done[c.id]);
    const rows = [];
    for (const ch of CH) {
      const open = chapterOpen(ch), done = chapterDone(ch);
      rows.push(el("li", { class: "chap" + (open ? "" : " lock"), onclick: () => run("chapter " + ch.n) }, el("span", { class: "n", text: "" }), el("span", { class: "t", text: F("Chapter {n}: {x}", { n: ch.n, x: T(ch.name) }) }),
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
    ol.replaceChildren(...rows);
    $("jobsCount").textContent = F("{a} of {b}", { a: Object.keys(S.done).length, b: CONTRACTS.length });
  }
  const BOARD = { data: null, at: 0 };
  function instruments() {
    const box = $("inst"); if (!box) return;
    const pk = myPk(), tip = CHAIN.tip, left = traceLeft(), c = S.taken ? byId(S.taken) : null, frac = traceFrac();
    const row = (h, b, p, cls) => el("div", { class: "row " + (cls || "") }, el("h3", { text: h }), el("b", { text: b }), p ? el("p", null, p) : null);
    const nr = nextRank(), badge = ART.have && ART.have.badges && ART.have.badges.includes(rankRow()[2]) ? el("img", { src: ART.base + "badges/" + rankRow()[2] + ".webp", alt: "", style: "width:28px;height:28px;vertical-align:middle;margin-right:6px" }) : null;
    const gear = el("div", { class: "gear" }, ...GEAR.map(([k, what]) => el("span", { class: has(k) ? "on" : "", text: k, title: T(what) })));
    const bd = BOARD.data && BOARD.data.board;
    box.replaceChildren(
      row(T("Node"), SIM ? T("Simulation") : CHAIN.ok ? T("Live node") : CHAIN.ok === false ? T("Out of reach") : T("Connecting"), SIM ? T("a practice node in this browser; nothing reaches the testnet") : T("node.tauhud.com, the community relay"), "state-" + (SIM ? "sim" : CHAIN.ok ? "live" : CHAIN.ok === false ? "off" : "")),
      row(T("Block"), tip != null ? "#" + fmt(tip) : "—", pace() ? F("about {n} s a block", { n: pace().toFixed(0) }) : T("measuring the pace")),
      (() => { const r = row(T("Trace"), c ? (left != null ? F("{n} blocks", { n: Math.max(0, left) }) : "…") : T("no contract taken"), c ? (left != null && left >= 0 ? F("until block {n} · {t}", { n: fmt(S.deadline), t: inTime(left) }) : T("the deadline is set from the tip at taking")) : T("take a contract: the block clock starts")); const bar = el("div", { class: "trace" + (frac < 0.25 ? " hot" : "") + (left != null && left < 0 ? " out" : "") }, el("i", { style: "width:" + Math.round(frac * 100) + "%" })); r.append(bar); return r; })(),
      row(T("Wallet"), pk ? short(pk) : T("not made yet"), pk ? el("a", { href: "/wallet/" + lang(), text: T("open in the wallet") }) : T("made at your first contract")),
      row(T("Balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS"), CHAIN.bal === 0 ? T("unseen wallet: the faucet’s 100,000 at the first payment") : T("test AGRS have no value")),
      (() => { const r = row(T("Standing"), "", nr ? F("{n} settled · {m} more to {x}", { n: rep(), m: nr[0] - rep(), x: T(nr[1]) }) : F("{n} settled · the top of the ladder", { n: rep() }), "rk"); const b = r.querySelector("b"); b.classList.add("rank"); if (badge) b.append(badge); b.append(T(rank())); return r; })(),
      (() => { const r = row(T("Gear"), "", null); r.querySelector("b").remove(); r.append(gear); return r; })(),
      row(T("Board"), bd ? F("{n} wallets", { n: bd.wallets || 0 }) : "—", bd ? Object.entries(bd.ranks || {}).filter(([, n]) => n).map(([k, n]) => T(k) + " " + n).join(" · ") || T("nobody yet") : T("wallets, not people; read from the server when it is there")),
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
    const ch = chapterOf(c);
    if (!chapterOpen(ch)) { say("warn", F("Chapter {n} first: its four contracts open chapter {m}.", { n: ch.n - 1, m: ch.n })); const nx = CONTRACTS.find(x => !S.done[x.id]); if (nx) say("sys", F("Next on the board: {n} {t}.", { n: num(nx), t: T(nx.name) }), btn(F("take {n}", { n: num(nx) }), "take " + num(nx))); return; }
    S.taken = c.id; S.span = c.trace; S.deadline = CHAIN.tip != null ? CHAIN.tip + c.trace : null; save(); jobs(); instruments(); topbar(); chips();
    say("sys", F("Contract {n} taken: {t}", { n: num(c), t: T(c.name) }));
    crew(c.who, c.brief, "calm");
    if (c.id === "amount") { S.num = lookoutNumber(); save(); say("sys", F("The lookout’s number: {n}", { n: S.num })); }
    say("sys", S.deadline != null ? F("Trace: until block {n} ({t}). Type run.", { n: fmt(S.deadline), t: inTime(c.trace) || F("{n} blocks", { n: c.trace }) }) : T("Trace: set from the tip as soon as the node answers. Type run."), btn("run", "run"));
    if (S.deadline == null) { const k = myPk(); (k ? envelope(k) : ask("getsequence " + DROP).then(st => { if (st && st.status === "ok") tick(Number(st.data.tip_height) || 0); })).then(() => { if (S.taken === c.id && S.deadline == null && CHAIN.tip != null) { S.deadline = CHAIN.tip + c.trace; save(); instruments(); topbar(); say("sys", F("Trace: until block {n} ({t}).", { n: fmt(S.deadline), t: inTime(c.trace) || F("{n} blocks", { n: c.trace }) })); } }).catch(() => {}); }
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
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent. Try again in a minute, or switch to the simulation in the header.")); return; }
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
    snd.ok(); flash("ok"); mood(c.who, "glad");
    say("ok", F("Contract {n} settled. Standing: {r}.", { n: num(c), r: T(rank()) }));
    say("learn", T(c.learn));
    if (again) { chips(); return; }
    post(c.who, c.after, 1 + Math.floor(Math.random() * 2));
    const ch = chapterOf(c);
    if (chapterDone(ch)) { chapterCard(ch); return; }
    const next = CONTRACTS.find(x => !S.done[x.id]);
    if (next) say("sys", F("Next on the board: {n} {t}.", { n: num(next), t: T(next.name) }), btn(F("take {n}", { n: num(next) }), "take " + num(next)));
    chips();
  }
  const explorer = h => link(txUrl(h), short(h));
  function sent(tx, s) {
    say("step", F("signed in this browser (BLS, sequence {n}), sent", { n: tx.sequence_number }), s.hash ? explorer(s.hash) : null, el("span", { class: "sys", text: " · " + F("{n} ms", { n: s.ms }) }));
  }
  const refusedEarly = s => { snd.no(); flash("bad"); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused before the mempool: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("The payment did not go out. Type run to try again.")); };
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
      if (!s.hash) { snd.no(); flash("bad"); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("Type back to try again.")); }
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
    $("card").classList.add("show"); snd.ok();
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
    if (S.taken) { say("warn", T("Put the taken contract back first (drop), or finish it.")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent.")); return; }
    RUN.busy = true; chips(); slot(F("claim, chapter {n}", { n: ch.n }));
    const k = myKey(true), amount = CLAIM_BASE + ch.n;
    try {
      await boardLoad();
      say("step", F("building the claim: {n} test AGRS to the drop {h} (the amount says which chapter)", { n: amount, h: short(DROP) }));
      const tx = await payment(k, DROP, amount, {});
      const s = await sendtx(tx);
      if (!s.r) fail(T("No answer from the node; nothing was sent. Type claim again."));
      if (!s.hash) { snd.no(); slotFail(codeOf(s.r) || T("refused")); say("no", F("Refused: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("Type claim to try again.")); }
      sent(tx, s);
      say("step", T("waiting for a block …"));
      const w = await sealed(s.hash, null, s.way);
      if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); fail(T("Type claim to try again.")); }
      say("ok", F("Sealed in block {n}. The crew’s purse reads the chain and pays the share back; it can take a few blocks.", { n: fmt(w.block) }), explorer(s.hash));
      S.chap[ch.n] = { hash: s.hash, block: w.block, at: Date.now(), paid: null, drop: DROP }; save(); jobs(); chips();
      snd.ok(); mood("qm", "glad");
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
        S.chap[1] = { ...S.chap[1], paid: c.paid }; save(); balance(); snd.ok();
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
        S.chap[n] = { ...S.chap[n], paid: c.paid }; save(); balance(); snd.ok(); flash("ok");
        say("ok", F("The drop paid the share: {n} test AGRS.", { n: c.paid.share ? c.paid.share.amount : SHARE }), c.paid.share && c.paid.share.hash ? explorer(c.paid.share.hash) : null);
        if (c.paid.mark) say("ok", T("And the crew’s mark: 1 test AGRS from the drop. Its hash is your badge."), c.paid.mark.hash ? explorer(c.paid.mark.hash) : null);
        else if (n === 1) watchMark();   // the mark is a payment of its own, a little after the share
        post("qm", "The share is paid and the ledger balanced. Spend it on nothing: it is worth nothing, like all test AGRS, and that is the point of a testnet.", 1);
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
    if (RUN.busy || S.taken) { say("warn", T("Finish or drop the taken contract first; the op needs the terminal.")); return; }
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
      say("sys", F("Op {n} of {m}: {x}", { n: OP.i + 1, m: OP.list.length, x: T(what) }));
      let ok;
      if (cid === "ghost") { say("step", T("first a real payment, then the same one again")); const tx = await payment(k, DROP, 1, {}); const s = await sendtx(tx); if (!s.hash) refusedEarly(s); sent(tx, s); const w = await sealed(s.hash, null, s.way); if (!w.in) fail(T("Not sealed; type go again.")); ok = await verdict(c, tx, true); }
      else if (cid === "overspend") { const b = await ask("getbalance " + k.pk); const bal = Number(((b || {}).data || {}).balance) || 0; ok = await verdict(c, await payment(k, DROP, (bal === 0 ? FAUCET : bal) + 1000, {}), true); }
      else { const o = { dead: { expired: true }, stale: { stale: true }, freeride: { freeride: true }, giant: {}, forged: { signer: B.keygen() }, impostor: { from: DROP } }[cid]; ok = await verdict(c, await payment(k, DROP, cid === "giant" ? GIANT : 1, o), true); }
      if (ok) { OP.i += 1; if (OP.i >= OP.list.length) { S.ops[OP.id] = { at: Date.now(), tricks: OP.list }; save(); OP.list = null; snd.ok(); flash("ok"); say("ok", F("Op settled: three refusals, live, beside the pirates’. Standing: {r}.", { r: T(rank()) })); crew("bosun", "That is the real thing: the same answers the chain gives the pirates, from your wallet, the same hour. The logbook has theirs; your terminal has yours.", "glad"); } else say("sys", F("Next: op {n}. Type go.", { n: OP.i + 1 }), btn("go", "go")); }
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
      snd.ok(); flash("ok");
      say("ok", T("Right: the friend. The other address was ground to match the first 6 and last 4 characters, the exact parts a wallet shows; the only way to tell is the whole address, or an address book you keep yourself."));
      if (!S.cases[d.id]) { S.cases[d.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Case file {id} settled. Standing: {r}.", { id: d.id, r: T(rank()) })); mood("bosun", "glad"); }
    } else {
      snd.no(); flash("bad");
      say("no", T("That is the lookalike. It paid the victim 1 test AGRS so it would stand in the history; the victim copied it from there. Only the whole address tells them apart."));
    }
    say("learn", T("A wallet setting helps once the slip is made: payments to an address you never paid wait in escrow and can be taken back (contract 11). It is the wallet’s setting, not a chain rule: whoever holds the key can pay without it."));
  }
  /* two riddles with answers only the chain has: the lowest fee the chain takes, and your wallet's next sequence number */
  async function riddle() {
    const pk = myPk(), f = await fee(), week = new Date().toISOString().slice(0, 10), id = "r-" + week;
    let seq = null; if (pk) { try { seq = (await envelope(pk)).seq; } catch (e) { seq = null; } }
    const list = [["fee", F("Riddle 1: the base fee on this chain is {n} (getgovernance, o9). A payment is signed with fee_limit 5 times that. What is the MOST the chain may take from it, in test AGRS?", { n: f }), f * 5]];
    if (seq != null) list.push(["seq", F("Riddle 2: your wallet is at sequence {n} (getsequence). Which sequence number must your next payment carry to be taken?", { n: seq }), seq]);
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
      snd.ok(); say("ok", key === "fee" ? T("Right: the fee limit is the most, never a promise to pay it; what the chain takes is the base fee, and the rest stays.") : T("Right: the next number, exactly once. A number used twice is the ghost from contract 3; a number skipped waits for the one before it."));
      r.i += 1;
      if (r.i < r.list.length) say("sys", r.list[r.i][1]);
      else { if (!S.riddles[r.id]) { S.riddles[r.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Riddles of {x} settled. Standing: {r}.", { x: r.id.slice(2), r: T(rank()) })); mood("bosun", "glad"); } CASE.riddle = null; }
    } else { snd.no(); say("no", key === "fee" ? T("No. Read the riddle again: the limit is a ceiling, and the ceiling is what you signed.") : T("No. The chain takes each number once and in order; getsequence names the next one.")); }
  }
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
      if (dust.length && !S.seen.dust) { S.seen.dust = dust[0].hash || "1"; save(); snd.mail(); crew("look", "Dust! A payment of 1 test AGRS came into your wallet from an address I would swear is the drop’s, if I only read the ends. I do not trust it. Type hunt.", "sour"); say("sys", T("The hunt:"), btn("hunt", "hunt")); chips(); return; }
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
    if (chosen === d.drop) {
      snd.ok(); flash("ok");
      say("ok", T("Right: that is the drop. The dust came from the lookalike, a key ground until its first and last characters matched the drop’s. Never pay an address from your history without reading the whole of it."));
      if (!S.hunt[d.id]) { S.hunt[d.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Hunt settled. Standing: {r}.", { r: T(rank()) })); mood("look", "glad"); }
    } else { snd.no(); flash("bad"); say("no", T("That is the lookalike. Read the middle, not the ends: the ends are what it was made to match.")); }
    say("learn", T("The same trick the hack of the week replays on Thursdays, now done to you. The drop’s whole address is in this terminal (status); a wallet’s address book is the only cure."));
  }

  /* ---------- the crew's voices: clips the server made (infra/rico/make.py), played when they exist ---------- */
  const VOICE = { have: null, at: 0, audio: null };
  async function clips() {
    if (SIM || VOICE.have || Date.now() - VOICE.at < 60000) return; VOICE.at = Date.now();
    try { const r = await fetch(CLIPS + "index.json", { cache: "no-cache" }); const j = r.ok ? await r.json() : null; VOICE.have = new Set((j && j.clips) || []); } catch (e) { VOICE.have = new Set(); }
  }
  async function speak(who, text) {
    if (SIM || !S.voice || !window.crypto || !crypto.subtle) return;
    await clips(); if (!VOICE.have || !VOICE.have.size) return;
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + text))   // the clips are English; the line shown may be translated, key = [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
    if (!VOICE.have.has(key)) return;
    try { if (VOICE.audio) VOICE.audio.pause(); VOICE.audio = new Audio(CLIPS + key + ".mp3"); VOICE.audio.volume = 0.9; await VOICE.audio.play(); } catch (e) {}
  }

  /* ---------- the boot screen: once per browser, or ?boot=1, or the command boot ---------- */
  async function bootScreen() {
    const box = $("bootLines"), over = $("bootScreen"); if (!box || !over) return;
    box.replaceChildren(); over.classList.add("show");
    let skipped = false; const skip = () => { skipped = true; over.classList.remove("show"); };
    $("bootSkip").onclick = skip; $("bootSkip").textContent = T("skip");
    snd.boot();
    const pk = myPk();
    const lines = [["BLACK SEQUENCE · crew terminal", ""], [T("no memo · from, to, amount, signed"), "dim"], [SIM ? T("practice node: this browser") : "node.tauhud.com · " + T("relay"), "dim"], [T("authorisation required"), ""],
      [pk ? F("access code: wallet {h} (made in this browser)", { h: short(pk) }) : T("access code: none yet, a wallet is made at the first contract"), "dim"], [T("granted. welcome aboard."), ""]];
    for (const [t, cls] of lines) {
      if (skipped) break;
      const p = el("p", { class: cls }); box.append(p);
      p.textContent = t;   // the whole line is in the page from the start (readers and checks see it); the reveal is a width
      if (S.fx && !REDUCED) { p.classList.add("typing"); for (let i = 1; i <= t.length; i++) { p.style.width = i + "ch"; if (i % 2 === 0) snd.key(); await sleep(14); if (skipped) break; } p.classList.remove("typing"); p.style.width = ""; }
      await sleep(260);
    }
    if (!skipped) { await sleep(700); over.classList.remove("show"); }
    S.booted = true; save();
  }

  /* ---------- commands ---------- */
  function help() {
    cols([
      ["help", T("this list")],
      ["jobs", T("the contracts on the board, in three chapters")],
      ["take <n>", T("take contract n; the block clock starts")],
      ["run", T("carry out the taken contract: build, sign, send, read the answer")],
      ["back", T("take a waiting payment back (contract 11)")],
      ["drop", T("put the taken contract back")],
      ["claim [n]", T("claim the crew’s share at a chapter’s end (the drop pays it back); claim <n> again resends an unpaid one")],
      ["chapter <n>", T("the chapter’s card")],
      ["mail", T("the post from the crew")],
      ["op", T("live ops while the Black Sequence is in port (Tuesdays)")],
      ["case", T("this week’s case file: the pirates’ tricks, the hack of the week, two riddles")],
      ["pick a|b · answer <n>", T("answer the case file")],
      ["hunt · mark a|b", T("the Tracer’s dust: which address is the drop (after chapter 1)")],
      ["status", T("node, block, trace, wallet, standing")],
      ["peek <cmd> <hex>", T("ask the node yourself: getbalance, getsequence, gettxstatus, getretractables (after chapter 1)")],
      ["trace <blocks>", T("set your own deadline on the taken contract (after chapter 2)")],
      ["board", T("the players’ board: wallets by standing")],
      ["findings", T("what this terminal saw the chain do that it must not (kept here only)")],
      ["crew", T("who is who on board")],
      ["sound on|off · fx on|off · voice on|off · full · boot · clear", T("the terminal itself")],
    ]);
  }
  function status() {
    const pk = myPk(), c = S.taken ? byId(S.taken) : null;
    cols([
      [T("node"), SIM ? T("simulation, a practice node in this browser") : CHAIN.ok ? "node.tauhud.com · " + T("live") : T("out of reach")],
      [T("block"), CHAIN.tip != null ? "#" + fmt(CHAIN.tip) : "—"],
      [T("trace"), c ? F("contract {n} until block {m}", { n: num(c), m: S.deadline != null ? fmt(S.deadline) : "…" }) : T("no contract taken")],
      [T("wallet"), pk || T("not made yet")],
      [T("drop"), DROP],
      [T("balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS")],
      [T("standing"), T(rank()) + " · " + F("{n} settled", { n: rep() })],
      [T("chapters"), CH.map(ch => ch.n + (S.chap[ch.n] ? " ✓" : chapterDone(ch) ? " ●" : chapterOpen(ch) ? " ○" : " ·")).join("  ")],
    ]);
  }
  function crewList() {
    cols([[T("Quartermaster"), T("hands out the contracts and keeps the ledger; the one who says no memo")], [T("Lookout"), T("reads the block clock, the chain weather and the ship’s calls; gives you the day’s number")], [T("Bosun"), T("keeps the case files and runs the live ops: what the pirates tried, what the hack of the week found")]]);
    say("sys", T("Nobody on board is a real person. The Black Sequence is the pirate ship that tests the chain at White Rabbit Key every Tuesday; her logbook is public."), link("/cruise/" + lang(), T("cruise logbook")));
  }
  async function peek(args) {
    if (!has("peek")) { say("sys", T("peek opens with chapter 1: four contracts, then the node answers you directly.")); return; }
    const [c, a, b] = args;
    if (!["getbalance", "getsequence", "gettxstatus", "getretractables"].includes(c) || !/^[0-9a-f]{64,96}$/.test(a || "")) { say("sys", T("peek getbalance <address> · peek getsequence <address> · peek gettxstatus <hash> · peek getretractables <address>")); return; }
    const r = await ask([c, a, b].filter(Boolean).join(" "));
    if (!r) { say("no", T("No answer from the node.")); return; }
    say(r.status === "ok" ? "sys" : "no", JSON.stringify(r.data || r.error || r, null, 1).slice(0, 1200));
  }
  function traceSet(arg) {
    if (!has("trace")) { say("sys", T("trace opens with chapter 2.")); return; }
    const n = parseInt(arg, 10), c = S.taken ? byId(S.taken) : null;
    if (!c) { say("sys", T("Take a contract first; then trace <blocks> sets its deadline.")); return; }
    if (!(n >= 2 && n <= 500)) { say("sys", T("trace <blocks>: 2 to 500.")); return; }
    if (CHAIN.tip == null) { say("sys", T("The block clock has no tip yet.")); return; }
    S.deadline = CHAIN.tip + n; S.span = n; save(); instruments(); topbar();
    say("sys", F("Trace set: until block {n} ({t}).", { n: fmt(S.deadline), t: inTime(n) || F("{n} blocks", { n }) }));
    if (n <= 3) crew("look", "Three blocks or fewer. Brave. The chain will not wait for your fingers.", "glad");
  }
  async function board() {
    const d = await boardLoad();
    if (!d || !d.board) { say("sys", T("The board is on the server; it is out of reach right now.")); return; }
    const b = d.board;
    say("sys", F("The players’ board: {n} wallets have paid the drop. Wallets, not people; nobody is named.", { n: b.wallets || 0 }));
    cols(Object.entries(b.ranks || {}).map(([k, n]) => [T(k), String(n)]));
    if (b.claims) say("sys", F("Chapters claimed: {a} · {b} · {c}", { a: b.claims[0] || 0, b: b.claims[1] || 0, c: b.claims[2] || 0 }));
    say("sys", F("You: {x}.", { x: T(rank()) }));
  }
  function findings() {
    if (!S.findings.length) { say("sys", T("Nothing. Every refusal so far was the chain doing its job.")); return; }
    for (const f of S.findings) say("warn", `${new Date(f.at).toISOString().slice(0, 16)} ${f.id}: ` + JSON.stringify({ tx: f.tx, answer: f.answer }).slice(0, 1500));
    say("sys", T("Please pass this on:"), link("/findings/" + lang(), T("how to report a finding")));
  }
  function full(on) {
    const root = document.documentElement, want = on == null ? !root.classList.contains("nm-full") : on;
    root.classList.toggle("nm-full", want);
    try { if (want && root.requestFullscreen && !document.fullscreenElement) root.requestFullscreen({ navigationUI: "hide" }).catch(() => {}); else if (!want && document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {}); } catch (e) {}
    $("fsBtn").textContent = want ? "⤢" : "⛶";
  }
  function exec(line) {
    const s = line.trim(); if (!s) return; cmdLine(s); snd.wake();
    const [c, ...args] = s.toLowerCase().split(/\s+/);
    if (c === "help" || c === "?") return help();
    if (c === "jobs" || c === "contracts" || c === "board" && args[0] === "jobs") { for (const ch of CH) { say("sys", F("Chapter {n}: {x}", { n: ch.n, x: T(ch.name) }) + (chapterOpen(ch) ? "" : " · " + T("locked"))); cols(ch.ids.map(id => byId(id)).map(x => [String(num(x)).padStart(2, " ") + (S.done[x.id] ? " ✓" : S.taken === x.id ? " ●" : "  "), T(x.name) + " · " + T(x.task)])); } const nx = CONTRACTS.find(y => !S.done[y.id]); return say("sys", T("take <n> takes one."), nx ? btn(F("take {n}", { n: num(nx) }), "take " + num(nx)) : null); }
    if (c === "take") { const n = parseInt(args[0], 10), x = args[0] === "next" || !args[0] ? CONTRACTS.find(y => !S.done[y.id]) : n >= 1 && n <= CONTRACTS.length ? CONTRACTS[n - 1] : byId(args[0]); return x ? take(x, args[1] === "again") : say("sys", T("take <n>: a number from the board, or take next.")); }
    if (c === "run") return OP.list ? opGo() : carry();
    if (c === "go") return opGo();
    if (c === "back" || c === "retract") return back();
    if (c === "drop" || c === "abort") { if (OP.list) { OP.list = null; chips(); return say("sys", T("The op is put down.")); } if (!S.taken) return say("sys", T("No contract taken.")); if (RUN.busy) return say("warn", T("A contract is under way; wait for the chain’s answer.")); S.taken = null; S.deadline = null; S.span = null; RUN.ret = S.ret = null; save(); jobs(); instruments(); topbar(); chips(); return say("sys", T("Back on the board.")); }
    if (c === "claim") { if (/^\d+$/.test(args[0] || "") && !/^[123]$/.test(args[0])) return say("warn", T("Chapters are 1, 2 and 3.")); return claim(/^[123]$/.test(args[0] || "") ? +args[0] : 0, args.includes("again")); }
    if (c === "chapter" || c === "ch") { const ch = CH[parseInt(args[0], 10) - 1] || CH.find(x => !chapterDone(x)) || CH[2]; return chapterCard(ch); }
    if (c === "mail" || c === "post") return mailOpen();
    if (c === "op" || c === "ops") return op();
    if (c === "case" || c === "file") return caseFile();
    if (c === "pick") return pick(args[0]);
    if (c === "answer") return answer(args[0]);
    if (c === "hunt") return hunt();
    if (c === "mark") return markPick(args[0]);
    if (c === "status") return status();
    if (c === "peek") return peek(args);
    if (c === "trace") return traceSet(args[0]);
    if (c === "board") return board();
    if (c === "findings") return findings();
    if (c === "crew") return crewList();
    if (c === "clear" || c === "cls") return clearScreen();
    if (c === "wallet") { window.open("/wallet/" + lang(), "_blank", "noopener"); return; }
    if (c === "lang") { if (window.TauI18n && TauI18n.set && ["en", "zh", "ja"].includes(args[0])) TauI18n.set(args[0]); else say("sys", "lang en · lang zh · lang ja"); return; }
    if (c === "sound" || c === "fx" || c === "voice") { if (!["on", "off"].includes(args[0])) return say("sys", c + " on · " + c + " off"); S[c === "sound" ? "snd" : c] = args[0] === "on"; save(); topbar(); return say("sys", c + " " + args[0]); }
    if (c === "full" || c === "fullscreen") return full();
    if (c === "boot") return bootScreen();
    if (/^(what|how|where|next|start|begin|go|hi|hello|hilfe|was|wie|\?)$/.test(c) || /what (do|should|now|next)/.test(s.toLowerCase())) return nextStep();
    say("sys", F("Unknown: {x}. Type help, or click:", { x: c }), nextChip(), btn("help", "help"));
  }
  /* what to do now, as a line and a chip: the one answer to "what should I do" */
  function nextChip() {
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    if (OP.list) return btn("go", "go");
    if (S.taken) return RUN.ret && S.taken === "wayback" ? btn("back", "back") : btn("run", "run");
    if (claimable) return btn("claim", "claim");
    if (next) return btn(F("take {n}", { n: num(next) }), "take " + num(next));
    return btn("case", "case");
  }
  function nextStep() {
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]), c = S.taken ? byId(S.taken) : null;
    if (OP.list) say("sys", T("An op is open: type go to send the next trick."), nextChip());
    else if (c && RUN.ret && c.id === "wayback") say("sys", T("Your payment waits in escrow: type back to take it back before the release."), nextChip());
    else if (c) say("sys", F("Contract {n} is yours: type run to carry it out.", { n: num(c) }), nextChip());
    else if (claimable) say("sys", F("Chapter {n} is done: type claim, and the drop pays the crew’s share back.", { n: claimable.n }), nextChip());
    else if (next) say("sys", F("Take the next contract: take {n}. Then run.", { n: num(next) }), nextChip());
    else say("sys", T("The board is clear. The case file (case) and the live ops on Tuesdays (op) are what is left; the hunt (hunt) once the Tracer has found you."), nextChip());
  }
  const run = line => exec(line);
  /* the chips: the next sensible command is always one click away */
  function chips() {
    const box = $("chips"); if (!box) return;
    const next = CONTRACTS.find(c => !S.done[c.id]), claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    const list = [["help", "help"]];
    if (OP.list) { if (!RUN.busy) list.push(["go", "go", true]); }
    else if (S.taken) { if (RUN.ret && S.taken === "wayback") list.push(["back", "back", true]); else if (!RUN.busy) list.push(["run", "run", true]); }
    else if (claimable) list.push([T("claim"), "claim", true]);
    else if (next) list.push([F("take {n}", { n: num(next) }), "take " + num(next), true]);
    if (HUNT.data) list.push(["mark a", "mark a"], ["mark b", "mark b"]);
    else if (CASE.data && !S.cases[CASE.data.id]) list.push(["pick a", "pick a"], ["pick b", "pick b"]);
    list.push(["jobs", "jobs"], ["status", "status"], ["case", "case"]);
    if (shipIn() && !OP.list && !SIM) list.push(["op", "op", true]);
    if (S.mail.some(m => !m.read && m.due <= (CHAIN.tip ?? 0))) list.push([T("mail"), "mail"]);
    box.replaceChildren(...list.map(([t, cmd, go]) => el("button", { type: "button", class: go ? "go" : "", text: t, onclick: () => { run(cmd); $("cmd").focus({ preventScroll: true }); } })));
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
    $("mailBtn").addEventListener("click", () => run("mail")); $("mailClose").addEventListener("click", () => $("mailWin").classList.remove("show"));
    $("sndBtn").addEventListener("click", () => { S.snd = !S.snd; save(); topbar(); if (S.snd) snd.ok(); }); $("fsBtn").addEventListener("click", () => full());
    for (const id of ["card", "mailWin"]) $(id).addEventListener("click", e => { if (e.target === $(id)) $(id).classList.remove("show"); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") for (const id of ["card", "mailWin"]) $(id).classList.remove("show"); });
    if (!S.booted || q.get("boot")) await bootScreen();
    say("sys", "NO MEMO · " + T("crew terminal of the Black Sequence") + " · Tau Testnet Alpha");
    const pk = myPk();
    say("sys", SIM ? T("simulation: a practice node in this browser, nothing reaches the testnet") : T("connecting to node.tauhud.com …"));
    const st = await ask("getsequence " + (pk || DROP));
    if (st && st.status === "ok") { tick(Number(st.data.tip_height) || 0); say("sys", (SIM ? T("practice node ready") : T("connected")) + " · " + F("block #{n}", { n: fmt(CHAIN.tip) })); if (pk) { CHAIN.seq = Number(st.data.sequence_number) || 0; await balance(); } }
    else { setState(false); say("warn", T("The node is out of reach from here (a blocker, a VPN, a restart). The board can be read; contracts wait until it answers. The header switch opens the simulation.")); }
    say("sys", pk ? F("your wallet {h}", { h: short(pk) }) + (CHAIN.bal != null ? " · " + fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS") : "") : T("no test wallet yet: one is made in this browser at your first contract"));
    const done = Object.keys(S.done).length;
    if (!done) crew("qm", "Rule one on this ship: no memo. A payment is from, to, amount, signed. Nothing else goes on the chain, so if you have something to say, say it in the amount. Twelve contracts on the board in three chapters; each is a real transaction from your test wallet, and the chain itself is the judge. Take the first.", "calm");
    else { say("sys", F("{n} of {m} contracts settled before. Standing: {r}.", { n: done, m: CONTRACTS.length, r: T(rank()) })); crew("qm", "Back aboard. The board remembers you; so does the chain.", "calm"); }
    if (S.taken === "wayback" && S.ret && S.ret.release > now() + 30) { RUN.ret = S.ret; crew("bosun", F("Your 50 test AGRS still wait in escrow ({h}), release at {t}. Type back.", { h: short(S.ret.id), t: clock(S.ret.release) })); }
    else if (S.taken) { const c = byId(S.taken); if (c && c.id !== "wayback") say("sys", F("Contract {n} is still yours: {t}. Type run.", { n: num(c), t: T(c.name) }), btn("run", "run")); else { S.taken = null; S.deadline = null; S.ret = null; save(); } }
    const claimable = CH.find(ch => chapterDone(ch) && !S.chap[ch.n]);
    if (claimable) say("sys", F("Chapter {n} is done and its share unclaimed.", { n: claimable.n }), btn("claim", "claim"));
    else if (!done) say("sys", T("Type help, or click:"), btn("take 1", "take 1"), el("span", { class: "cur" }));
    else { const nx = CONTRACTS.find(x => !S.done[x.id]); say("sys", T("Type help, or click:"), nx ? btn(F("take {n}", { n: num(nx) }), "take " + num(nx)) : btn("case", "case"), el("span", { class: "cur" })); }
    jobs(); instruments(); chips(); topbar(); watch(); world(); boardLoad(); deliverMail();
    for (const n of [1, 2, 3]) if (S.chap[n] && !S.chap[n].paid) watchPayback(n);
    if (S.chap[1] && !S.seen.dust) huntWatch();
    if (q.get("take")) { const x = byId(q.get("take")) || CONTRACTS[parseInt(q.get("take"), 10) - 1]; if (x) take(x); }
    document.addEventListener("visibilitychange", () => { if (!document.hidden) { watch(); world(); } });
    setInterval(world, 120000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
