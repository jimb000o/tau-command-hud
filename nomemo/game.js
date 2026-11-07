/* No Memo: a terminal game on Tau Testnet Alpha. The crew of the Black Sequence (the pirate ship that tests the chain
   every Tuesday, infra/relay/cruise.py TRICKS) hands out twelve contracts. Each one is a real transaction from the
   visitor's own test wallet (the key /wallet/ and White Rabbit Key use, made in this browser): a payment that must land
   before a block height, a payment the chain must refuse for the right reason (the same answers the pirates expect:
   INVALID_SEQUENCE, TX_EXPIRED, FEE_LIMIT_TOO_LOW, INVALID_SIGNATURE, TX_INVALID, INSUFFICIENT_FUNDS, INVALID_PARAMS), a
   retractable payment taken back before its release. The name is the first rule of the ship: a Tau transaction carries
   from, to and amount, no memo. If you have something to say, say it in the amount.

   Live: the relay at node.tauhud.com (WebSocket, the same commands the wallet uses: getsequence, getbalance,
   gettxstatus, getretractables, sendtx). Simulation (tau-mode=sim, or ?mode=sim): a small practice node in this browser
   (SimNode) that answers the way the testnet does for these cases, so the contracts can be tried without the chain.
   The weekly case file (command `case`) reads the hack of the week (relay GET /hack) and the pirates' logbook
   (GET /cruise/log); in the simulation it shows a labelled sample.

   State in localStorage (tauhud-nomemo): contracts done with their hashes and answers, the taken contract and its block
   deadline, the case files solved. A trick the chain takes although it must not is kept there too (findings), shown to
   the player with the record, never posted anywhere by itself.

   Debug: ?take=<id> takes a contract on load. */
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
  const WKEY = "tauhud-wallet-key", SAVE = "tauhud-nomemo", RELAY = "https://node.tauhud.com", WS = "wss://node.tauhud.com";
  /* the crew's dead drop: a wallet made for the game whose key stays with the game's keeper, never in this code */
  const DROP = "9309956d5f97d1b91b409b0b2995470f5f646f2c43c3b8eb2203a42135c7caf1a9b4ff99cbdfc9ad16bd44fcea5d5065";
  const FAUCET = 100000, GIANT = 1 << 24, TRACE = 45, RACE = 6, WAYBACK_MIN = 5;
  const short = h => (h && h.length > 14 ? h.slice(0, 6) + "…" + h.slice(-4) : h || "");
  const fmt = n => Number(n).toLocaleString("en-US");
  const now = () => Math.floor(Date.now() / 1000);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const clock = t => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  const lang = () => (window.TauI18n && TauI18n.lang !== "en" ? "?lang=" + TauI18n.lang : "");
  const txUrl = h => "/explorer/?tx=" + h + (lang() ? "&lang=" + TauI18n.lang : "");

  /* ---------- state ---------- */
  let S = null;
  function load() {
    try { S = JSON.parse(store.get(SAVE) || "null"); } catch (e) { S = null; }
    if (!S || S.v !== 1) S = { v: 1, done: {}, taken: null, deadline: null, cases: {}, findings: [], hist: [] };
    S.done = S.done || {}; S.cases = S.cases || {}; S.findings = S.findings || []; S.hist = S.hist || [];
  }
  const save = () => store.set(SAVE, JSON.stringify(S));
  const rep = () => Object.keys(S.done).length + Object.keys(S.cases).length;
  const RANKS = [[0, "stowaway"], [1, "deckhand"], [4, "rigger"], [8, "navigator"], [12, "quartermaster’s mate"]];
  const rank = () => { const r = rep(); let out = RANKS[0][1]; for (const [n, name] of RANKS) if (r >= n) out = name; return out; };

  /* ---------- the crew ---------- */
  const CREW = { qm: "Quartermaster", look: "Lookout", bosun: "Bosun" };

  /* ---------- the contracts ---------- */
  /* want: "in" (sealed in a block), "back" (taken back before its release) or the node's codes that mean the chain said
     no for the right reason (infra/relay/cruise.py TRICKS, hackweek.py). trace: blocks from taking it to its deadline. */
  const CONTRACTS = [
    { id: "mark", name: "Make your mark", who: "qm", want: "in", trace: TRACE,
      brief: "New hand. Before you touch anything, pay the drop 1 test AGRS. Then I know your wallet, and the chain knows it too.",
      task: "Pay 1 test AGRS to the crew’s drop.",
      learn: "A Tau transaction is from, to, amount, signed. Your first payment opened your account: the testnet credits an unseen wallet 100,000 test AGRS when it first pays (the auto-faucet)." },
    { id: "amount", name: "Say it in the amount", who: "look", want: "in", trace: TRACE,
      brief: "Rule one on this ship: no memo. There is no field for words in a Tau transaction. The number I give you is the message; pay exactly that to the drop.",
      task: "Pay the lookout’s number, and nothing else, to the drop.",
      learn: "No memo field: a payment carries from, to and amount. The amount is the only thing you said, and anyone reading the chain can read it." },
    { id: "ghost", name: "The ghost", who: "qm", want: ["INVALID_SEQUENCE"], trace: TRACE,
      brief: "Pay the drop once, wait for the block, then send the very same signed payment again. The chain must throw the second one back. If it does not, we have a problem worth more than the coins.",
      task: "Send a sealed payment a second time.",
      learn: "Every payment carries a sequence number; the chain takes each number once. A copy of a sealed transaction is refused: INVALID_SEQUENCE. No replay, no double spend." },
    { id: "dead", name: "Dead letter", who: "look", want: ["TX_EXPIRED"], trace: TRACE,
      brief: "Sign a payment whose time ran out two minutes ago and send it anyway. The chain reads the clock in the signature, not the one on the wall.",
      task: "Send a payment whose expiry time has passed.",
      learn: "A payment carries its own expiry time, signed. Past it, the chain refuses it: TX_EXPIRED. A payment cannot be kept in a drawer and sent later." },
    { id: "stale", name: "Stale by height", who: "look", want: ["TX_EXPIRED"], trace: TRACE,
      brief: "Same again, by blocks this time: a payment whose block-height deadline is already behind the tip.",
      task: "Send a payment whose block-height deadline has passed.",
      learn: "Beside the clock, a payment names the last block it may land in (expire_at_height). Behind the tip, it is refused: TX_EXPIRED. The block clock is the one that counts." },
    { id: "freeride", name: "Free ride", who: "qm", want: ["FEE_LIMIT_TOO_LOW"], trace: TRACE,
      brief: "Try to pay the drop while allowing no fee at all. Nobody rides for free, not even on this ship.",
      task: "Send a payment with a fee limit of 0.",
      learn: "The fee is a limit you sign, not a price you are quoted: at most this much. Below the chain’s base fee the payment is refused: FEE_LIMIT_TOO_LOW." },
    { id: "overspend", name: "Overspend", who: "qm", want: ["INSUFFICIENT_FUNDS", "TX_REJECTED"], trace: TRACE,
      brief: "Pay the drop more than you have. A thousand over your balance will do.",
      task: "Pay more than the wallet holds.",
      learn: "The chain checks the balance against the amount plus the fee: INSUFFICIENT_FUNDS. The transfer rule may say no first, as TX_REJECTED; both mean the chain did its job." },
    { id: "giant", name: "The giant", who: "look", want: ["TX_INVALID", "INVALID_PARAMS"], trace: TRACE,
      brief: "Pay 16,777,216 test AGRS to the drop. You do not have it; that is not the point. The point is the size of the number.",
      task: "Pay more than a transfer can carry (2^24 test AGRS).",
      learn: "A transfer amount on this testnet is 24 bits wide: 16,777,215 at most. One more and the payment is not even a payment: TX_INVALID or INVALID_PARAMS." },
    { id: "forged", name: "The forgery", who: "qm", want: ["INVALID_SIGNATURE"], trace: TRACE,
      brief: "Sign a payment from your wallet with a key that is not yours. Any key: the terminal makes a throwaway one. Send it and watch.",
      task: "Sign with the wrong key.",
      learn: "The signature must match the sender’s key, nothing else counts: INVALID_SIGNATURE. Whoever holds your key is you to the chain, and nobody else is." },
    { id: "impostor", name: "The impostor", who: "qm", want: ["TX_INVALID"], trace: TRACE,
      brief: "Now the other way round: a payment that names the drop as the payer, signed with your key. Spend somebody else’s coins, if the chain lets you.",
      task: "Pay from another wallet with your own signature.",
      learn: "The payer named inside the transfer must be the wallet that signed it: TX_INVALID. A good signature on the wrong wallet moves nothing." },
    { id: "wayback", name: "The way back", who: "bosun", want: "back", trace: TRACE,
      brief: "Pay the drop 50 with the way back on: the money waits in escrow for five minutes. Before that time is up, take it back. Miss it and the drop keeps your coins.",
      task: "Send a retractable payment, then take it back before its release.",
      learn: "A retractable transfer parks the money until a release time or height; until then only the sender can take it back (retract_transfer, feeless). From the release on, the first block pays the recipient by itself. The hack of the week leans on exactly this window." },
    { id: "race", name: "Race the block", who: "look", want: "in", trace: RACE,
      brief: "Last one. A payment that may land in the next six blocks and not one later. The terminal sets the deadline the moment you take it. Go.",
      task: "Land a payment within six blocks of taking the contract.",
      learn: "expire_at_height is the trace: the chain enforces the deadline, nobody has to. A payment that missed its block is TX_EXPIRED, however fast you were." },
  ];
  const byId = id => CONTRACTS.find(c => c.id === id);
  const num = c => CONTRACTS.indexOf(c) + 1;

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
  async function sendtx(tx) {
    const t0 = performance.now(), r = await ask("sendtx " + JSON.stringify(tx)), ms = Math.round(performance.now() - t0);
    if (isOk(r)) { CHAIN.next = tx.sequence_number + 1; logWallet(tx, r); } else if (r) CHAIN.next = 0;
    return { r, ms, hash: isOk(r) ? (r.data && r.data.tx_hash) || null : null };
  }
  function logWallet(tx, r) {   // the wallet page's own activity list, so the payment shows there too
    try {
      const lk = "tauhud-wallet-log-live-" + tx.sender_pubkey, logs = JSON.parse(store.get(lk) || "[]"), amount = tx.tx_type === "user_tx" ? tx.operations["1"][0][2] : tx.amount;
      logs.unshift({ hash: r.data && r.data.tx_hash, kind: tx.tx_type === "retract_transfer" ? "retract" : "pay", label: "No Memo" + (amount != null ? ": " + amount : ""), at: Date.now(), status: "queued", seq: tx.sequence_number, paid: tx.fee_limit !== "0" });
      if (!SIM) store.set(lk, JSON.stringify(logs.slice(0, 40)));
    } catch (e) {}
  }
  /* waits for the block: gettxstatus until it is in, refused, or the deadline has passed */
  async function sealed(hash, deadline, onTick) {
    for (let i = 0; i < 90; i++) {
      await sleep(i < 3 ? 2500 : 5000);
      const m = await ask("gettxstatus " + hash, 8000);
      if (m && m.status === "ok") {
        const d = m.data || {}, st = String(d.status || d.state || "").toLowerCase();
        if (d.block_number != null || /confirmed|included|mined|sealed|applied/.test(st)) return { in: true, block: d.block_number ?? d.height ?? null };
        if (/reject|fail|dropped|expired|invalid/.test(st)) return { in: false, why: d.reason || d.error || st };
      }
      if (i % 2 === 1) { const k = myPk(); if (k) await envelope(k).catch(() => {}); }
      if (onTick) onTick(i);
      if (deadline && CHAIN.tip != null && CHAIN.tip > deadline + 2) return { in: false, why: "TX_EXPIRED" };
    }
    return { in: false, why: "no answer in time" };
  }

  /* ---------- the block clock ---------- */
  function tick(tip) {
    const t = Date.now();
    if (CHAIN.tip != null && tip > CHAIN.tip && CHAIN.tipAt) { const p = (t - CHAIN.tipAt) / 1000 / (tip - CHAIN.tip); CHAIN.pace = CHAIN.pace ? CHAIN.pace * 0.6 + p * 0.4 : p; }
    if (CHAIN.tip == null || tip !== CHAIN.tip) { CHAIN.tip = tip; CHAIN.tipAt = t; }
    setState(true); instruments();
    if (S.taken && S.deadline != null && tip > S.deadline && !RUN.busy) traced();
  }
  const inTime = blocks => { const s = SIM && window.TauSim ? TauSim.pace : CHAIN.pace; if (!s || blocks < 0) return ""; const m = blocks * s / 60; return m < 1 ? T("under a minute") : F("about {m} min", { m: Math.round(m) }); };
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

  /* ---------- the screen ---------- */
  const screen = () => $("screen");
  function say(kind, text, ...more) {
    const p = el("p", { class: kind }); if (text != null) p.append(typeof text === "string" ? document.createTextNode(text) : text); for (const m of more) if (m != null) p.append(" ", m);
    screen().append(p); const w = $("screenWrap"); w.scrollTop = w.scrollHeight; return p;
  }
  const crew = (who, text) => say("crew", null, el("b", { text: T(CREW[who]) + ":" }), " " + text);
  const link = (href, text) => el("a", { href, target: "_blank", rel: "noopener", text });
  const code = t => el("code", { text: t });
  const cols = pairs => { const d = el("div", { class: "cols" }); for (const [a, b] of pairs) d.append(el("span", { text: a }), el("span", { text: b })); return say("sys", d); };
  function cmdLine(s) { say("you", s); }
  function clearScreen() { screen().replaceChildren(); }

  /* ---------- the panes ---------- */
  function jobs() {
    const ol = $("jobs"); if (!ol) return;
    const next = CONTRACTS.find(c => !S.done[c.id]);
    ol.replaceChildren(...CONTRACTS.map(c => {
      const d = S.done[c.id], taken = S.taken === c.id;
      return el("li", { class: (d ? "done" : "") + (taken ? " taken" : "") + (!d && next === c ? " next" : ""), onclick: () => run("take " + num(c)), title: T(c.task) },
        el("span", { class: "n", text: String(num(c)).padStart(2, "0") }), el("span", { class: "t", text: T(c.name) }),
        el("span", { class: "st", text: d ? T("done") : taken ? T("taken") : T(c.who === "qm" ? "Quartermaster" : c.who === "look" ? "Lookout" : "Bosun") }),
        el("span", { class: "w", text: T(c.task) }));
    }));
    $("jobsCount").textContent = F("{a} of {b}", { a: Object.keys(S.done).length, b: CONTRACTS.length });
  }
  function instruments() {
    const box = $("inst"); if (!box) return;
    const pk = myPk(), tip = CHAIN.tip, left = S.taken && S.deadline != null && tip != null ? S.deadline - tip : null, c = S.taken ? byId(S.taken) : null;
    const span = c ? c.trace : TRACE, frac = left == null ? 0 : Math.max(0, Math.min(1, left / span));
    const row = (h, b, p, cls) => el("div", { class: "row " + (cls || "") }, el("h3", { text: h }), el("b", { text: b }), p ? el("p", null, p) : null);
    box.replaceChildren(
      row(T("Node"), SIM ? T("Simulation") : CHAIN.ok ? T("Live node") : CHAIN.ok === false ? T("Out of reach") : T("Connecting"), SIM ? T("a practice node in this browser; nothing reaches the testnet") : T("node.tauhud.com, the community relay"), "state-" + (SIM ? "sim" : CHAIN.ok ? "live" : CHAIN.ok === false ? "off" : "")),
      row(T("Block"), tip != null ? "#" + fmt(tip) : "—", (SIM && window.TauSim ? TauSim.pace : CHAIN.pace) ? F("about {n} s a block", { n: (SIM && window.TauSim ? TauSim.pace : CHAIN.pace).toFixed(0) }) : T("measuring the pace")),
      (() => { const r = row(T("Trace"), c ? (left != null ? F("{n} blocks", { n: Math.max(0, left) }) : "…") : T("no contract taken"), c ? (left != null && left >= 0 ? F("until block {n} · {t}", { n: fmt(S.deadline), t: inTime(left) }) : T("the deadline is set from the tip at taking")) : T("take a contract: the block clock starts")); const bar = el("div", { class: "trace" + (frac < 0.25 ? " hot" : "") + (left != null && left < 0 ? " out" : "") }, el("i", { style: "width:" + Math.round(frac * 100) + "%" })); r.append(bar); return r; })(),
      row(T("Wallet"), pk ? short(pk) : T("not made yet"), pk ? el("a", { href: "/wallet/" + lang(), text: T("open in the wallet") }) : T("made at your first contract")),
      row(T("Balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS"), CHAIN.bal === 0 ? T("unseen wallet: the faucet’s 100,000 at the first payment") : T("test AGRS have no value")),
      row(T("Standing"), T(rank()), F("{n} contracts and case files settled", { n: rep() }), "rk"),
    );
    const b = box.querySelector(".rk b"); if (b) b.classList.add("rank");
  }
  async function balance() { const pk = myPk(); if (!pk) return; const b = await ask("getbalance " + pk); if (b && b.status === "ok") { CHAIN.bal = Number((b.data || {}).balance) || 0; instruments(); } }

  /* ---------- running a contract ---------- */
  const RUN = { busy: false, ret: null };
  const fail = (why) => { throw Object.assign(new Error(why), { soft: true }); };
  function take(c) {
    if (S.taken === c.id) { say("sys", F("Contract {n} is yours already. Type run.", { n: num(c) })); return; }
    if (RUN.busy) { say("warn", T("A contract is under way; wait for the chain’s answer.")); return; }
    S.taken = c.id; S.deadline = CHAIN.tip != null ? CHAIN.tip + c.trace : null; save(); jobs(); instruments();
    say("sys", F("Contract {n} taken: {t}", { n: num(c), t: T(c.name) }));
    crew(c.who, T(c.brief));
    if (c.id === "amount") say("sys", F("The lookout’s number: {n}", { n: lookoutNumber() }));
    say("sys", S.deadline != null ? F("Trace: until block {n} ({t}). Type run.", { n: fmt(S.deadline), t: inTime(c.trace) || F("{n} blocks", { n: c.trace }) }) : T("Trace: set from the tip as soon as the node answers. Type run."));
    if (S.deadline == null) { const k = myPk(); (k ? envelope(k) : ask("getsequence " + DROP).then(st => { if (st && st.status === "ok") tick(Number(st.data.tip_height) || 0); })).then(() => { if (S.taken === c.id && S.deadline == null && CHAIN.tip != null) { S.deadline = CHAIN.tip + c.trace; save(); instruments(); say("sys", F("Trace: until block {n} ({t}).", { n: fmt(S.deadline), t: inTime(c.trace) || F("{n} blocks", { n: c.trace }) })); } }).catch(() => {}); }
    watch();
  }
  const lookoutNumber = () => 100 + ((CHAIN.tip || 0) * 7 + new Date().getUTCDate()) % 900;   // the day's number: from the tip and the date, no secret in it
  function traced() {
    const c = byId(S.taken); S.taken = null; S.deadline = null; save(); jobs(); instruments();
    say("no", F("Trace complete: block {n} passed and contract {m} is back on the board. The chain forgot you; take it again.", { n: fmt(CHAIN.tip), m: num(c) }));
  }
  async function carry() {
    const c = S.taken ? byId(S.taken) : null;
    if (!c) { say("sys", T("No contract taken. Type jobs, then take 1.")); return; }
    if (RUN.busy) { say("warn", T("Already under way.")); return; }
    if (!B) { say("no", T("This browser cannot sign (no BLS library loaded).")); return; }
    if (!SIM && CHAIN.ok === false) { say("no", T("The node is out of reach; nothing was sent. Try again in a minute, or switch to the simulation in the header.")); return; }
    RUN.busy = true; chips();
    const k = myKey(true);
    try {
      if (S.deadline == null) { const e = await envelope(k.pk); S.deadline = e.tip + c.trace; save(); }
      const steps = { mark: () => pay(c, k, 1), amount: () => pay(c, k, lookoutNumber()), ghost: () => ghost(c, k), dead: () => refuse(c, k, 1, { expired: true }), stale: () => refuse(c, k, 1, { stale: true }),
        freeride: () => refuse(c, k, 1, { freeride: true }), overspend: () => overspend(c, k), giant: () => refuse(c, k, GIANT, {}), forged: () => refuse(c, k, 1, { signer: B.keygen() }),
        impostor: () => refuse(c, k, 1, { from: DROP }), wayback: () => wayback(c, k), race: () => pay(c, k, 1, true) };
      await steps[c.id]();
    } catch (e) {
      if (e && e.soft) say("no", e.message);
      else say("no", T("The node did not answer in time; nothing is lost. The contract stays yours: type run again."));
    }
    RUN.busy = false; chips(); jobs(); instruments(); balance();
  }
  function settle(c, rec) {
    S.done[c.id] = { at: Date.now(), ...rec }; S.taken = null; S.deadline = null; save(); jobs(); instruments();
    say("ok", F("Contract {n} settled. Standing: {r}.", { n: num(c), r: T(rank()) }));
    say("learn", T(c.learn));
    const next = CONTRACTS.find(x => !S.done[x.id]);
    if (next) say("sys", F("Next on the board: {n} {t}. Type take {n}.", { n: num(next), t: T(next.name) }));
    else crew("qm", T("Twelve of twelve. The board is empty and the ledger is clean; you know this chain better than most. The next ship’s case file opens on Thursday: type case."));
  }
  const explorer = h => link(txUrl(h), short(h));
  function sent(tx, s) {
    say("step", F("signed in this browser (BLS, sequence {n}), sent", { n: tx.sequence_number }), s.hash ? explorer(s.hash) : null, el("span", { class: "sys", text: " · " + F("{n} ms", { n: s.ms }) }));
  }
  /* a payment that must land */
  async function pay(c, k, amount, race) {
    say("step", F("building a payment: {n} test AGRS to the drop {h}", { n: fmt(amount), h: short(DROP) }));
    const tx = await payment(k, DROP, amount, race ? { deadline: S.deadline } : {});
    if (race) say("step", F("expire_at_height {n}: the chain itself will refuse it after that block", { n: fmt(tx.expire_at_height) }));
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    if (!s.hash) { say("no", F("Refused before the mempool: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("The payment did not go out. Type run to try again.")); }
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline);
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
    if (!s.hash) { say("no", F("Refused before the mempool: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("The payment did not go out. Type run to try again.")); }
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline);
    if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why)) traced(); else fail(T("Type run to try again.")); return; }
    say("ok", F("Sealed in block {n}.", { n: fmt(w.block) }), explorer(s.hash));
    say("step", T("now the ghost: the same bytes, the same signature, sent again"));
    await verdict(c, tx);
  }
  async function verdict(c, tx) {
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    const want = c.want, c0 = codeOf(s.r);
    if (s.hash) {   // the chain took what it should have refused: a finding, kept with the record, never posted by itself
      sent(tx, s);
      say("no", T("The chain took it. That is not how it should be."));
      S.findings.push({ at: Date.now(), id: c.id, tx, answer: s.r }); save();
      say("warn", T("A finding: the testnet did something it must not. The record is kept in this browser (type findings) and nowhere else. Please pass it on:"), link("/findings/" + lang(), T("how to report a finding")));
      S.taken = null; S.deadline = null; save(); return;
    }
    const right = want.includes(c0);
    say(right ? "ok" : "warn", F("The chain said no in {n} ms: {x}", { n: s.ms, x: c0 || plain(s.r) }) + (right ? " ✓" : ""));
    if (!right) { say("warn", F("Refused, but with another answer than {x}. {y}", { x: want.join(" / "), y: plain(s.r) })); say("sys", T("That still counts: the chain said no. Type run to hear it again, or take the next contract.")); }
    settle(c, { code: c0, ms: s.ms, right });
  }
  async function wayback(c, k) {
    const release = now() + WAYBACK_MIN * 60;
    const { seq, tip } = await envelope(k.pk), f = await fee();
    const tx = sign({ tx_type: "retractable_transfer", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.min(now() + 600, release - 1), expire_at_height: tip + 1000, fee_limit: String(f * 5), recipient_pubkey: DROP, amount: 50, release_at_time: release }, k.sk);
    say("step", F("building a retractable transfer: 50 test AGRS to the drop, release at {t}", { t: clock(release) }));
    const s = await sendtx(tx);
    if (!s.r) fail(T("No answer from the node; nothing was sent. Type run again."));
    if (!s.hash) { say("no", F("Refused before the mempool: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("The payment did not go out. Type run to try again.")); }
    sent(tx, s);
    say("step", T("waiting for a block …"));
    const w = await sealed(s.hash, S.deadline);
    if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); if (/EXPIRED/.test(w.why)) traced(); else fail(T("Type run to try again.")); return; }
    say("ok", F("Sealed in block {n}: the money waits in escrow.", { n: fmt(w.block) }), explorer(s.hash));
    let rid = s.r.data && s.r.data.retractable_id;
    if (!rid) { const rt = await ask("getretractables " + k.pk + " out"); const open = ((rt && rt.data && rt.data.retractables) || []).filter(r => r.status !== "released" && r.status !== "retracted"); if (open.length) rid = (open[open.length - 1].retractable_id || open[open.length - 1].id); }
    if (!rid) rid = s.hash;
    RUN.ret = S.ret = { id: rid, release, c: c.id }; save();
    S.deadline = CHAIN.tip != null ? CHAIN.tip + Math.max(3, Math.round(((release - 60) - now()) / Math.max(4, (SIM && window.TauSim ? TauSim.pace : CHAIN.pace) || 8))) : S.deadline; save(); instruments();
    crew("bosun", F("Escrow id {h}. It releases at {t}. Type back before then; leave the chain a minute to seal it.", { h: short(rid), t: clock(release) }));
  }
  async function back() {
    const r = RUN.ret;
    if (RUN.busy) { say("warn", T("Already under way; wait for the chain’s answer.")); return; }
    if (!r || S.taken !== "wayback") { say("sys", T("Nothing waits in escrow from this terminal. Take contract 11 and run it first.")); return; }
    if (now() >= r.release) { say("no", T("Too late: the release time has passed and the first block pays the drop by itself. The contract is back on the board.")); RUN.ret = S.ret = null; S.taken = null; S.deadline = null; save(); jobs(); instruments(); return; }
    RUN.busy = true; chips();
    try {
      const k = myKey(true), { seq, tip } = await envelope(k.pk);
      const tx = sign({ tx_type: "retract_transfer", sender_pubkey: k.pk, sequence_number: seq, expiration_time: Math.min(now() + 600, r.release - 1), expire_at_height: tip + 100, fee_limit: "0", retractable_id: r.id }, k.sk);
      say("step", F("building the retract for {h}: feeless, only the sender may send it", { h: short(r.id) }));
      const s = await sendtx(tx);
      if (!s.r) fail(T("No answer from the node; nothing was sent. Type back again."));
      if (!s.hash) { say("no", F("Refused: {x}", { x: codeOf(s.r) || plain(s.r) })); fail(T("Type back to try again.")); }
      sent(tx, s);
      say("step", T("waiting for a block …"));
      const w = await sealed(s.hash, null);
      if (!w.in) { say("no", F("Not sealed: {x}", { x: w.why })); fail(T("Type back to try again, if there is time.")); }
      if (now() >= r.release) { say("no", T("The retract was sealed after the release: the drop was paid. Nothing to settle; take the contract again another time.")); RUN.ret = S.ret = null; S.taken = null; S.deadline = null; save(); }
      else { say("ok", F("Taken back in block {n}, {m} s before the release.", { n: fmt(w.block), m: r.release - now() }), explorer(s.hash)); RUN.ret = S.ret = null; settle(byId("wayback"), { hash: s.hash, block: w.block, retracted: r.id }); }
    } catch (e) { if (e && e.soft) say("no", e.message); else say("no", T("The node did not answer in time. Type back again.")); }
    RUN.busy = false; chips(); jobs(); instruments(); balance();
  }

  /* ---------- the case file: the week's hack replay and the pirates' logbook, read as a wallet would show them ---------- */
  const CASE = { data: null, pick: null };
  async function caseFile() {
    say("sys", T("Opening the case file …"));
    let hack = null, log = null;
    if (SIM) ({ hack, log } = sampleCase());
    else {
      try { hack = await (await fetch(RELAY + "/hack", { cache: "no-store" })).json(); } catch (e) { hack = null; }
      try { log = await (await fetch(RELAY + "/cruise/log?n=600", { cache: "no-store" })).json(); } catch (e) { log = null; }
    }
    if (!hack && !log) { say("no", T("The relay is out of reach; the case file cannot be read right now.")); return; }
    crew("bosun", T("Two things in the file: what the pirates tried at the island on Tuesday, and the hack of the week from Thursday."));
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
    if (!run || !W.friend || !W.poisoner) { say("sys", hack && hack.next && hack.next.t0 ? F("No hack replay yet. The first one runs on {t} German time; the case file fills itself after it.", { t: new Date(hack.next.t0 * 1000).toLocaleString("en-GB", { timeZone: "Europe/Berlin", weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) }) : T("No hack replay in the file yet.")); CASE.data = null; return; }
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
    cols([["a", ab[0]], ["b", ab[1]]]);
    say("sys", S.cases[run.id] ? T("You solved this file already; pick a or b to read it again.") : T("Type pick a or pick b."));
  }
  function pick(x) {
    const d = CASE.data; if (!d) { say("sys", T("Open a case file first: type case.")); return; }
    const chosen = d[x]; if (!chosen) { say("sys", T("Type pick a or pick b.")); return; }
    if (chosen === d.friend) {
      say("ok", T("Right: the friend. The other address was ground to match the first 6 and last 4 characters, the exact parts a wallet shows; the only way to tell is the whole address, or an address book you keep yourself."));
      if (!S.cases[d.id]) { S.cases[d.id] = { at: Date.now() }; save(); instruments(); say("ok", F("Case file {id} settled. Standing: {r}.", { id: d.id, r: T(rank()) })); }
    } else {
      say("no", T("That is the lookalike. It paid the victim 1 test AGRS so it would stand in the history; the victim copied it from there. Only the whole address tells them apart."));
    }
    say("learn", T("A wallet setting helps once the slip is made: payments to an address you never paid wait in escrow and can be taken back (contract 11). It is the wallet’s setting, not a chain rule: whoever holds the key can pay without it."));
  }
  function sampleCase() {
    const hex = s => s.padEnd(96, "0").slice(0, 96);
    const friend = "5a7c21" + "e3".repeat(43) + "9f0b", poison = "5a7c21" + "4d".repeat(43) + "9f0b";
    return { hack: { hacks: { poisoning: { name: "Address poisoning", how: "The attacker makes an address that starts and ends like one you pay often, sends you a tiny amount from it, and waits for you to copy the wrong one from your history." } },
      wallets: { friend: { address: hex(friend) }, poisoner: { address: hex(poison) } }, runs: [{ id: "sample-poisoning", hack: "poisoning", result: "held: the payment came back" }] },
      log: { entries: [{ ship: "pirates", kind: "trick", visit: "sample", trick: "replay", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "forged", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "overspend", ok: false }, { ship: "pirates", kind: "trick", visit: "sample", trick: "expired", ok: false }] } };
  }

  /* ---------- commands ---------- */
  function help() {
    cols([
      ["help", T("this list")],
      ["jobs", T("the contracts on the board")],
      ["take <n>", T("take contract n; the block clock starts")],
      ["run", T("carry out the taken contract: build, sign, send, read the answer")],
      ["back", T("take a waiting payment back (contract 11)")],
      ["drop", T("put the taken contract back")],
      ["case", T("this week’s case file: the pirates’ tricks and the hack of the week")],
      ["pick a|b", T("answer the case file")],
      ["status", T("node, block, trace, wallet, standing")],
      ["peek <cmd> <hex>", T("ask the node yourself: getbalance, getsequence, gettxstatus, getretractables")],
      ["findings", T("what this terminal saw the chain do that it must not (kept here only)")],
      ["crew", T("who is who on board")],
      ["clear", T("wipe the screen")],
    ]);
  }
  function status() {
    const pk = myPk(), c = S.taken ? byId(S.taken) : null;
    cols([
      [T("node"), SIM ? T("simulation, a practice node in this browser") : CHAIN.ok ? "node.tauhud.com · " + T("live") : T("out of reach")],
      [T("block"), CHAIN.tip != null ? "#" + fmt(CHAIN.tip) : "—"],
      [T("trace"), c ? F("contract {n} until block {m}", { n: num(c), m: S.deadline != null ? fmt(S.deadline) : "…" }) : T("no contract taken")],
      [T("wallet"), pk || T("not made yet")],
      [T("balance"), CHAIN.bal == null ? "—" : fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS")],
      [T("standing"), T(rank()) + " · " + F("{n} settled", { n: rep() })],
    ]);
  }
  function crewList() {
    cols([[T("Quartermaster"), T("hands out the contracts and keeps the ledger; the one who says no memo")], [T("Lookout"), T("reads the block clock and gives you the day’s number")], [T("Bosun"), T("keeps the case files: what the pirates tried, what the hack of the week found")]]);
    say("sys", T("Nobody on board is a real person. The Black Sequence is the pirate ship that tests the chain at White Rabbit Key every Tuesday; her logbook is public."), link("/cruise/" + lang(), T("cruise logbook")));
  }
  async function peek(args) {
    const [c, a, b] = args;
    if (!["getbalance", "getsequence", "gettxstatus", "getretractables"].includes(c) || !/^[0-9a-f]{64,96}$/.test(a || "")) { say("sys", T("peek getbalance <address> · peek getsequence <address> · peek gettxstatus <hash> · peek getretractables <address>")); return; }
    const r = await ask([c, a, b].filter(Boolean).join(" "));
    if (!r) { say("no", T("No answer from the node.")); return; }
    say(r.status === "ok" ? "sys" : "no", JSON.stringify(r.data || r.error || r, null, 1).slice(0, 1200));
  }
  function findings() {
    if (!S.findings.length) { say("sys", T("Nothing. Every refusal so far was the chain doing its job.")); return; }
    for (const f of S.findings) say("warn", `${new Date(f.at).toISOString().slice(0, 16)} ${f.id}: ` + JSON.stringify({ tx: f.tx, answer: f.answer }).slice(0, 1500));
    say("sys", T("Please pass this on:"), link("/findings/" + lang(), T("how to report a finding")));
  }
  function exec(line) {
    const s = line.trim(); if (!s) return; cmdLine(s);
    const [c, ...args] = s.toLowerCase().split(/\s+/);
    if (c === "help" || c === "?") return help();
    if (c === "jobs" || c === "contracts" || c === "board") { cols(CONTRACTS.map(x => [String(num(x)).padStart(2, " ") + (S.done[x.id] ? " ✓" : S.taken === x.id ? " ●" : "  "), T(x.name) + " · " + T(x.task)])); return say("sys", T("take <n> takes one.")); }
    if (c === "take") { const n = parseInt(args[0], 10), x = args[0] === "next" ? CONTRACTS.find(y => !S.done[y.id]) : n >= 1 && n <= CONTRACTS.length ? CONTRACTS[n - 1] : byId(args[0]); return x ? take(x) : say("sys", T("take <n>: a number from the board, or take next.")); }
    if (c === "run" || c === "go") return carry();
    if (c === "back" || c === "retract") return back();
    if (c === "drop" || c === "abort") { if (!S.taken) return say("sys", T("No contract taken.")); if (RUN.busy) return say("warn", T("A contract is under way; wait for the chain’s answer.")); S.taken = null; S.deadline = null; RUN.ret = S.ret = null; save(); jobs(); instruments(); return say("sys", T("Back on the board.")); }
    if (c === "case" || c === "file") return caseFile();
    if (c === "pick") return pick(args[0]);
    if (c === "status") return status();
    if (c === "peek") return peek(args);
    if (c === "findings") return findings();
    if (c === "crew") return crewList();
    if (c === "clear" || c === "cls") return clearScreen();
    if (c === "wallet") { window.open("/wallet/" + lang(), "_blank", "noopener"); return; }
    if (c === "lang") { if (window.TauI18n && TauI18n.set && ["en", "zh", "ja"].includes(args[0])) TauI18n.set(args[0]); else say("sys", "lang en · lang zh · lang ja"); return; }
    say("sys", F("Unknown: {x}. Type help.", { x: c }));
  }
  const run = line => exec(line);
  function chips() {
    const box = $("chips"); if (!box) return;
    const next = CONTRACTS.find(c => !S.done[c.id]);
    const list = [["help", "help"], ["jobs", "jobs"]];
    if (S.taken) { if (RUN.ret && S.taken === "wayback") list.push(["back", "back", true]); else if (!RUN.busy) list.push(["run", "run", true]); }
    else if (next) list.push([F("take {n}", { n: num(next) }), "take " + num(next), true]);
    list.push(["status", "status"], ["case", "case"]);
    box.replaceChildren(...list.map(([t, cmd, go]) => el("button", { type: "button", class: go ? "go" : "", text: t, onclick: () => { run(cmd); $("cmd").focus({ preventScroll: true }); } })));
  }

  /* ---------- boot ---------- */
  async function boot() {
    load(); jobs(); instruments(); chips();
    const hist = []; let hi = 0;
    const input = $("cmd");
    $("cmdForm").addEventListener("submit", e => { e.preventDefault(); const v = input.value; input.value = ""; if (v.trim()) { hist.push(v); hi = hist.length; } run(v); });
    input.addEventListener("keydown", e => { if (e.key === "ArrowUp" && hist.length) { hi = Math.max(0, hi - 1); input.value = hist[hi]; e.preventDefault(); } else if (e.key === "ArrowDown") { hi = Math.min(hist.length, hi + 1); input.value = hist[hi] || ""; e.preventDefault(); } });
    $("mtabs").addEventListener("click", e => { const b = e.target.closest("button[data-pane]"); if (!b) return; for (const x of $("mtabs").querySelectorAll("button")) x.classList.toggle("on", x === b); const map = { jobs: "paneJobs", term: "paneTerm", stat: "paneStat" }; for (const k in map) $(map[k]).classList.toggle("show", k === b.dataset.pane); });
    $("screenWrap").addEventListener("click", e => { if (!e.target.closest("a") && !window.getSelection().toString()) input.focus({ preventScroll: true }); });
    say("sys", "NO MEMO · " + T("crew terminal of the Black Sequence") + " · Tau Testnet Alpha");
    const pk = myPk();
    say("sys", SIM ? T("simulation: a practice node in this browser, nothing reaches the testnet") : T("connecting to node.tauhud.com …"));
    const st = await ask("getsequence " + (pk || DROP));
    if (st && st.status === "ok") { tick(Number(st.data.tip_height) || 0); say("sys", (SIM ? T("practice node ready") : T("connected")) + " · " + F("block #{n}", { n: fmt(CHAIN.tip) })); if (pk) { CHAIN.seq = Number(st.data.sequence_number) || 0; await balance(); } }
    else { setState(false); say("warn", T("The node is out of reach from here (a blocker, a VPN, a restart). The board can be read; contracts wait until it answers. The header switch opens the simulation.")); }
    say("sys", pk ? F("your wallet {h}", { h: short(pk) }) + (CHAIN.bal != null ? " · " + fmt(CHAIN.bal === 0 ? FAUCET : CHAIN.bal) + " " + T("test AGRS") : "") : T("no test wallet yet: one is made in this browser at your first contract"));
    crew("qm", T("Rule one on this ship: no memo. A payment is from, to, amount, signed. Nothing else goes on the chain, so if you have something to say, say it in the amount. Twelve contracts on the board; each is a real transaction from your test wallet, and the chain itself is the judge."));
    const done = Object.keys(S.done).length;
    if (done) say("sys", F("{n} of {m} contracts settled before. Standing: {r}.", { n: done, m: CONTRACTS.length, r: T(rank()) }));
    if (S.taken === "wayback" && S.ret && S.ret.release > now() + 30) { RUN.ret = S.ret; crew("bosun", F("Your 50 test AGRS still wait in escrow ({h}), release at {t}. Type back.", { h: short(S.ret.id), t: clock(S.ret.release) })); }
    else if (S.taken) { const c = byId(S.taken); if (c && c.id !== "wayback") say("sys", F("Contract {n} is still yours: {t}. Type run.", { n: num(c), t: T(c.name) })); else { S.taken = null; S.deadline = null; S.ret = null; save(); } }
    say("sys", T("Type help, or take 1."), el("span", { class: "cur" }));
    jobs(); instruments(); chips(); watch();
    if (q.get("take")) { const x = byId(q.get("take")) || CONTRACTS[parseInt(q.get("take"), 10) - 1]; if (x) take(x); }
    document.addEventListener("visibilitychange", () => { if (!document.hidden) watch(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
