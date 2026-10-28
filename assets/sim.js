/* Tau HUD simulation: one made-up Tau testnet chain, the same on every page.

   Simulation mode (the Live node / Simulation switch in the header, remembered as tau-mode) shows invented activity that
   follows the documented tau-testnet protocol instead of the real chain. Every page reads it from this file, so the
   Explorer, Stats, Time travel, Accounts, Nodes, Proposals and Status all describe one chain: the chain is a function of
   the clock, not of the page. Block n is sealed at a fixed second of the day (about eight seconds per block), its content
   comes from a random generator seeded with the day, and the chain starts over at 00:00 UTC, the way the real testnet
   restarted now and then. Two browsers at the same moment see the same block with the same transactions.

   Pages use it in place of the relay. TauSim.socket() behaves like a WebSocket to wss://node.tauhud.com: it answers
   hello, getblocks, getblockrange, getgovernance, getmempool, getaccountstate, getbalance, getsequence, getruleoffers and
   gettxstatus with the node's envelopes and pushes new blocks as they are sealed. TauSim.fetch(path) answers the relay's
   GET endpoints (/status, /stats, /uptime, /health-score, /community, /peers, /community/board, /api/v1/summary and the
   tracker's /proposals.json) with the same shapes. No real chain data; nothing leaves the browser.

   TauSim.on      true when this page runs in simulation mode (?sample previews stay what they are)
   TauSim.mode()  "sim" | "live"      TauSim.set("sim"|"live")  remembers the choice and reloads the page
   TauSim.head()  current height       TauSim.block(n)  the raw block   TauSim.genesis  balances at block 0
   TauSim.chain   the generator itself (ts, rulesAt, proposals, arrivals), for a page that wants more than the relay protocol

   Visitors vote: the one input from people. Every hourly rule change (proposed hh:20, in force hh:30) is put to the visitors
   until hh:27; the relay counts the votes (infra/relay/simvotes.py, GET /sim/votes) and the simulated validators follow the
   majority. More yes than no, or no votes at all: they agree from hh:28 and the change is in force at hh:30. More no than yes:
   only the proposer's vote stands and the change is dropped at hh:30. Every browser reads the same outcome, so the chain
   stays the same everywhere; when an outcome arrives that a page already generated differently, the day is generated again.
   TauSim.me()             the visitor's anonymous identity {token, name, colour}: a random token and two words, browser only
   TauSim.vote(item, yes)  cast or change a vote (Promise of {ok, error, item})
   TauSim.ballots()        the day's tallies {items: {"slot:<k>": {yes, no, opens, closes, open, outcome, voters, mine}}}
   TauSim.onBallots(fn)    called whenever the tallies change */
(() => {
  "use strict";
  const PACE = 8, DAY = 86400, FEE0 = 10, BUDGET0 = 8, QUORUM0 = "supermajority", NETWORK = "tau-testnet-v2", KEY = "tau-mode";
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const q = new URLSearchParams(location.search), urlMode = q.get("mode");
  if (urlMode === "sim" || urlMode === "live") {
    store.set(KEY, urlMode);
    try { const u = new URL(location.href); u.searchParams.delete("mode"); history.replaceState(null, "", u.pathname + u.search + u.hash); } catch (e) {}
  }
  const ON = store.get(KEY) === "sim" && !q.has("sample");

  /* ---------- deterministic randomness ---------- */
  const prng = seed => { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  const mix = x => { let h = Math.imul((x ^ 0x9E3779B9) >>> 0, 0x85EBCA6B); h ^= h >>> 13; h = Math.imul(h, 0xC2B2AE35); h ^= h >>> 16; return h >>> 0; };
  const HEX = "0123456789abcdef", B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  const hexOf = (r, n) => { let s = ""; for (let i = 0; i < n; i++) s += HEX[(r() * 16) | 0]; return s; };
  const peerOf = r => { let s = "12D3KooW"; for (let i = 0; i < 44; i++) s += B58[(r() * 58) | 0]; return s; };
  const pick = (r, a) => a[(r() * a.length) | 0];
  const short = h => h ? `${h.slice(0, 6)}…${h.slice(-4)}` : "";
  const now = () => Date.now() / 1000, at = t => t == null ? now() : t;
  const iso = t => new Date(t * 1000).toISOString();

  /* ---------- identities: the same every day, so an address can be bookmarked ---------- */
  const idR = prng(0x7a75);
  const VALIDATORS0 = Array.from({ length: 4 }, () => hexOf(idR, 96));
  const ACCOUNTS = Array.from({ length: 14 }, () => hexOf(idR, 96));
  const SPARE = Array.from({ length: 6 }, () => hexOf(idR, 96));          // validators a proposal may admit
  const GENESIS_HASH = "4bf5ee70" + hexOf(idR, 48) + "fbce";
  const GENESIS = {};                                                     // 2,000,000 AGRS at block 0, like the real genesis
  VALIDATORS0.forEach(v => { GENESIS[v] = 200000; });
  ACCOUNTS.forEach((a, i) => { GENESIS[a] = i === 0 ? 160000 : 80000; });
  const NODES = [
    { id: hexOf(idR, 12), name: "alice-node", peer: peerOf(idR), kit: "3", days: 12, uptime: 0.998, online: true, lag: 0 },
    { id: hexOf(idR, 12), name: "bob", peer: peerOf(idR), kit: "2", days: 6, uptime: 0.91, online: true, lag: 1 },
    { id: hexOf(idR, 12), name: "lab-box", peer: null, kit: "2", days: 2.2, uptime: 0.74, online: false, lag: 0 },
  ];
  const BOOTNODE = peerOf(idR), STRANGERS = [peerOf(idR), peerOf(idR)];
  const QT = { supermajority: "two thirds", majority: "more than half" };

  /* ---------- visitors: an anonymous name and colour, and the votes the relay counts ---------- */
  // the same lists, in the same order, as infra/relay/simvotes.py (NAME_A, NAME_B, COLOURS_HEX); test_simvotes.py compares them
  const ID_A = ["Quiet", "Swift", "Bright", "Calm", "Bold", "Clever", "Gentle", "Brave", "Keen", "Lucky", "Merry", "Noble",
    "Patient", "Proud", "Rapid", "Silent", "Steady", "Sunny", "Wise", "Witty", "Daring", "Eager", "Fair", "Jolly"];
  const ID_B = ["Otter", "Heron", "Fox", "Owl", "Lynx", "Badger", "Falcon", "Hare", "Wolf", "Raven", "Seal", "Crane",
    "Panda", "Tiger", "Whale", "Robin", "Bison", "Koala", "Gecko", "Moose", "Ibex", "Swan", "Yak", "Wren"];
  const ID_A_ZH = ["安静", "迅捷", "明亮", "沉着", "大胆", "聪明", "温和", "勇敢", "敏锐", "幸运", "快乐", "高贵", "耐心", "骄傲", "飞快", "无声", "稳重", "阳光", "睿智", "风趣", "果敢", "热切", "公正", "欢乐"];
  const ID_B_ZH = ["水獭", "苍鹭", "狐狸", "猫头鹰", "猞猁", "獾", "猎隼", "野兔", "狼", "渡鸦", "海豹", "仙鹤", "熊猫", "老虎", "鲸", "知更鸟", "野牛", "考拉", "壁虎", "驼鹿", "羱羊", "天鹅", "牦牛", "鹪鹩"];
  const ID_COLOURS = ["#8fa3d9", "#b39ddb", "#d9a3c4", "#d9c49a", "#8fc7d9", "#a7a0d9", "#c4a3d9", "#c8c8d0"];
  const zhPage = () => document.documentElement.classList.contains("i18n-zh") || /^zh/i.test(document.documentElement.lang || "");
  const nameOf = (a, b) => ID_A[a] == null || ID_B[b] == null ? (zhPage() ? "一位访客" : "A visitor") : zhPage() ? `${ID_A_ZH[a]}的${ID_B_ZH[b]}` : `${ID_A[a]} ${ID_B[b]}`;
  let ME = null;
  function me() {
    if (!ME) {
      try { const m = JSON.parse(store.get("tau-sim-id") || "null"); if (m && /^[0-9a-f]{32}$/.test(m.token) && ID_A[m.a] && ID_B[m.b] && ID_COLOURS[m.c]) ME = m; } catch (e) {}
      if (!ME) {
        const rnd = n => { try { const u = new Uint32Array(n); crypto.getRandomValues(u); return [...u]; } catch (e) { return Array.from({ length: n }, () => (Math.random() * 2 ** 32) >>> 0); } };
        const r = rnd(7);
        ME = { token: r.slice(0, 4).map(x => x.toString(16).padStart(8, "0")).join(""), a: r[4] % ID_A.length, b: r[5] % ID_B.length, c: r[6] % ID_COLOURS.length };
        store.set("tau-sim-id", JSON.stringify(ME));
      }
    }
    return { token: ME.token, a: ME.a, b: ME.b, c: ME.c, name: nameOf(ME.a, ME.b), colour: ID_COLOURS[ME.c] };
  }
  const RELAY = window.TAU_SIM_RELAY || "https://node.tauhud.com";
  // what came from outside the clock, per day: the visitors' outcome of every hourly ballot ("yes" | "no" | "none").
  // Cached so a reload knows it at once; makeBlock reads it. Another source (visitor proposals) adds its own field.
  let OUTSIDE = { day: -1, slots: {} };
  try { const o = JSON.parse(store.get("tau-sim-outside") || "null"); if (o && typeof o.day === "number" && o.slots) OUTSIDE = o; } catch (e) {}
  let BALLOTS = { day: null, now: 0, items: {} }, BAL_AT = 0;
  const BAL_FNS = new Set();
  const slotOutcome = k => OUTSIDE.day === DAYI ? OUTSIDE.slots[k] || null : null;
  /* the day's programme: one special rule change every hour, proposed 20 minutes in (block 150), in force ten minutes later, the same every day.
     The consensus switch is the rare one, twice a day: proof of stake on at 10:30 UTC, the fixed validator list back at 16:30 UTC (the alerts
     service announces these two on Telegram from the same clock: infra/alerts/alerts.py SIM_SWITCHES). The other hours cycle through a validator
     admitted, the majority threshold, a validator removed, the two-thirds threshold again. */
  const SLOT_AT = 150, SLOT_LEN = 450, SLOT_WAIT = 75, BALLOT_SECONDS = 420, BALLOT_BLOCKS = 60, STAKE_SLOT = 10, FIXED_SLOT = 16, HOURLY = ["admit", "major", "remove", "super"];
  const specialOf = k => k === STAKE_SLOT ? "stake" : k === FIXED_SLOT ? "fixed" : HOURLY[(k - (k > STAKE_SLOT) - (k > FIXED_SLOT)) % HOURLY.length];
  const specialAt = n => n >= SLOT_AT && (n - SLOT_AT) % SLOT_LEN === 0 ? specialOf((n - SLOT_AT) / SLOT_LEN) : null;
  /* the failure paths of governance, every hour: at hh:40 a proposal that contradicts the live rules is refused at the door,
     at hh:50 a contested one is proposed, gets the proposer's vote alone and is dropped when its deadline passes at hh:58 */
  const extraAt = n => n < SLOT_AT ? null : (n - SLOT_AT) % SLOT_LEN === 150 ? "contra" : (n - SLOT_AT) % SLOT_LEN === 225 ? "contested" : null;
  const CONTRA_WHY = "contradicts the rules in force: the text sets o6 to 0 where the live spec needs 1, so the staging compile failed and the node never admitted it";
  const CONFLICT_WHY = name => `the offered rule contradicts the rule the account already runs (${name}): both together would refuse every transfer, o5 = 0 for all`;
  const SPECIAL_TITLE = { stake: "Switch consensus to proof of stake", fixed: "Back to the fixed validator list", admit: "A new validator is admitted", remove: "A validator is removed",
    super: "Agreement threshold → two thirds of the validators", major: "Agreement threshold → more than half of the validators", restart: "The simulated testnet starts over" };
  const SHORT = { stake: "proof of stake", fixed: "fixed list again", admit: "new validator", remove: "validator leaves", super: "two-thirds rule", major: "majority rule", restart: "chain restarts" };
  /* the genesis consensus rules of tau-testnet-v2, with the base fee (o9) as the one line a fee proposal changes */
  const SPEC = fee => `# Tau-Driven Consensus v1 Interface\n#\n# i6: Block height\n# i7: Block timestamp\n# i8: Proposer identity (yid)\n# i9: Previous block hash (yid)\n# i10: Host proof validity (1 for valid, 0 for invalid)\n# i11: Claims summary (yid)\n#\n# o6: Block validity\n# o7: Proposer eligibility\n\n# Initial V1 Rule:\n# All authorized proposals handled by host PoA are considered eligible (o7 = 1)\n# Blocks are valid strictly if the host cryptographically verifies the proof (o6 = i10)\nalways (\n    o6[t]:bv[16] = i10[t]:bv[16] &&\n    o7[t]:bv[16] = { 1 }:bv[16]\n &&\n    o9[t]:bv[24] = { #x${fee.toString(16).padStart(6, "0")} }:bv[24]\n)\n`;

  /* ---------- the day's chain ---------- */
  let DAYI = -1, G = 0, R = null, B = [], ST = null, RESET = 0;
  const TXI = new Map(), DROP = new Map(), ACC = new Map();
  function init(dayIndex) {
    DAYI = dayIndex; G = dayIndex * DAY; R = prng(mix(dayIndex * 7919 + 17));
    ST = { seq: new Map(), bal: new Map(Object.entries(GENESIS)), rules: new Map(), offers: [], open: [], retractables: [], props: [], dropped: [], nextPropAt: 12 + ((R() * 20) | 0), curH: -1, cur: null };
    TXI.clear(); DROP.clear(); ACC.clear();
    B = [{ header: { block_number: 0, previous_hash: "0".repeat(64), timestamp: 0, merkle_root: "0".repeat(64), proposer_pubkey: "0".repeat(96), state_hash: hexOf(R, 64) },
      transactions: [], tx_ids: [], block_hash: GENESIS_HASH, _arrive: [], _dropped: [], _fee: FEE0 }];
  }
  // block n is sealed at a fixed second of the day: eight seconds per block, give or take one
  const ts = n => n <= 0 ? 0 : G + n * PACE + ((n - SLOT_AT) % SLOT_WAIT === 0 ? 0 : (mix(DAYI * 100003 + n) % 3) - 1);   // ±1 s, except on the programme's blocks: hh:20:00 and hh:30:00 sharp, as the alerts service expects
  function rollDay(t) { const d = Math.floor(t / DAY); if (d !== DAYI) { init(d); RESET++; } }
  function headAt(t) {
    let n = Math.max(0, Math.floor((t - G) / PACE));
    while (n > 0 && ts(n) > t) n--;
    while (ts(n + 1) <= t) n++;
    return n;
  }
  function sync(t) { t = t == null ? now() : t; rollDay(t); const h = headAt(t); gen(h + 1); return h; }
  function gen(upTo) { while (B.length <= upTo) makeBlock(B.length); }

  /* rules in force after block h: the genesis rules plus every agreed change that took effect by then */
  const threshold = (quorum, N) => quorum === "majority" ? Math.floor(N / 2) + 1 : Math.max(1, Math.ceil(2 * N / 3));
  const statusAt = (p, h) => h < p.proposed_at ? null : p.approved_at != null && p.approved_at <= h ? (h >= p.activate_at ? "active" : "agreed") : h >= p.activate_at ? "dropped" : "voting";
  function rulesAt(h) {
    const o = { fee: FEE0, validators: VALIDATORS0.slice(), quorum: QUORUM0, budget: BUDGET0, elig: "validator_set", rev: 1, active: [] };
    ST.props.filter(p => p.approved_at != null && p.activate_at <= h).sort((a, b) => a.activate_at - b.activate_at || a.n - b.n).forEach(p => {
      o.rev++; o.active.push(p);
      if (p.kind === "fee") o.fee = p.value; else if (p.kind === "validator") { if (!o.validators.includes(p.value)) o.validators.push(p.value); }
      else if (p.kind === "remove") o.validators = o.validators.filter(v => v !== p.value);
      else if (p.kind === "budget") o.budget = p.value; else if (p.kind === "quorum") o.quorum = p.value;
      else if (p.kind === "stake") o.elig = "stake"; else if (p.kind === "fixed") o.elig = "validator_set";
    });
    return o;
  }
  /* a personal transfer rule (stream o5), as accounts deploy or offer them */
  function randomRule(owner) {
    const r = R(), hex16 = v => "#x" + v.toString(16).padStart(16, "0");
    if (r < 0.45) { const lim = pick(R, [500, 1000, 2500, 4000]); return { name: "Spending limit", text: `o5[t] = i2[t] <= { ${hex16(lim)} }:bv[64]`, blocks: amt => amt > lim }; }
    if (r < 0.7) { const to = pick(R, ACCOUNTS.filter(a => a !== owner)); return { name: "Recipient whitelist", text: `o5[t] = (i4[t]:bv[384] = { #x${to} }:bv[384])`, blocks: (amt, t) => t !== to }; }
    if (r < 0.85) { const h = B.length + 4 + ((R() * 40) | 0); return { name: "Locked until a block", text: `o5[t] = (i6[t]:bv[64] >= { ${h} }:bv[64])`, blocks: () => B.length < h }; }
    const lim = pick(R, [2000, 3000]), who = pick(R, ACCOUNTS.filter(a => a !== owner));
    return { name: "Co-signature", text: `o5[t] = (i2[t] <= { ${hex16(lim)} }:bv[64]) || (i18[t]:bv[384] = { #x${who} }:bv[384])`, blocks: amt => amt > lim };
  }
  /* a rule change: an ordinary one picks its kind at random; a special one (want: the day's programme) is told what to be and gets everyone's vote */
  function proposal(n, rules, want) {
    const contested = want === "contested"; if (contested) want = null;   // the hourly contested one: a sixfold fee that nobody but the proposer votes for
    const N = rules.validators.length, proposer = pick(R, rules.validators), r = R();
    const p = { id: hexOf(R, 64), n: ST.props.length + 1, proposer, proposed_at: n, activate_at: n + (want ? SLOT_WAIT : contested ? 60 : 15 + ((R() * 10) | 0)), approved_at: null,
      thr: threshold(rules.quorum, N), votes: [], special: want || null, contested, slot: want ? (n - SLOT_AT) / SLOT_LEN : null,
      abstain: want ? new Set() : new Set(rules.validators.filter(v => v !== proposer && (contested || R() < 0.2))), patch: null, revisions: [], kind: "", value: null, explain: null };
    const ex = (title, changes, why, severity) => ({ title, label: null, changes, unchanged: [], why, severity: severity || "normal" });
    const frees = SPARE.filter(v => !rules.validators.includes(v) && !ST.props.some(x => x.kind === "validator" && x.value === v && ["voting", "agreed"].includes(statusAt(x, n))));
    const spare = frees.length ? frees[((n / SLOT_LEN) | 0) % frees.length] : null;
    const extra = rules.validators.filter(v => !VALIDATORS0.includes(v)), gone = extra.length ? extra[extra.length - 1] : rules.validators[N - 1];
    let kind = contested ? "fee" : want === "admit" ? (spare ? "validator" : "noop") : want === "super" || want === "major" ? "quorum" : want ? want
      : r < 0.40 ? "fee" : r < 0.52 && spare && N < 5 ? "validator" : r < 0.72 ? "budget" : "noop";
    const quorum = want === "super" ? "supermajority" : want === "major" ? "majority" : rules.quorum === "majority" ? "supermajority" : "majority";
    if ((kind === "quorum" && quorum === rules.quorum) || (kind === "stake" && rules.elig === "stake") || (kind === "fixed" && rules.elig !== "stake") || (kind === "remove" && N <= 3)) kind = "noop";
    if (kind === "fee") { const v = contested ? rules.fee * 6 : pick(R, [6, 8, 12, 15, 20].filter(x => x !== rules.fee)); Object.assign(p, { kind, value: v, revisions: [SPEC(v)], explain: ex(`Base fee ${rules.fee} → ${v} AGRS`, [{ topic: "Base fee per transaction", text: `${rules.fee} → ${v} AGRS` }], contested ? `Every transaction would cost ${v} AGRS instead of ${rules.fee}: six times today's fee. Only the proposer votes yes; the other validators let the deadline pass.` : `Every transaction would cost ${v} AGRS instead of ${rules.fee}.`) }); }
    else if (kind === "validator") Object.assign(p, { kind, value: spare, patch: { validator_additions: [spare] }, explain: ex(`Admit validator ${short(spare)}`, [{ topic: "Validators", text: `add ${short(spare)}` }], "One more party would make blocks and vote on rule changes.") });
    else if (kind === "remove") Object.assign(p, { kind, value: gone, patch: { validator_removals: [gone] }, explain: ex(`Remove validator ${short(gone)}`, [{ topic: "Validators", text: `remove ${short(gone)}` }], "One party fewer would make blocks and vote on rule changes.") });
    else if (kind === "budget") { const v = rules.budget === 8 ? 12 : 8; Object.assign(p, { kind, value: v, patch: { max_rule_txs_per_block: v }, explain: ex(`Allow ${v} rule transactions per block`, [{ topic: "Rule transactions per block", text: `${rules.budget} → ${v}` }], `A block could carry ${v > rules.budget ? "more" : "fewer"} rule deployments and offers.`) }); }
    else if (kind === "quorum") Object.assign(p, { kind, value: quorum, patch: { vote_quorum: quorum }, explain: ex(`Agreement threshold → ${QT[quorum]} of the validators`, [{ topic: "Votes needed for a rule change", text: `${QT[rules.quorum]} → ${QT[quorum]} of the validators` }], "The rule that governs rule changes would change itself: every later proposal needs this share of the validators.") });
    else if (kind === "stake") Object.assign(p, { kind, value: "stake", patch: { eligibility_mode: "stake" }, explain: ex(SPECIAL_TITLE.stake, [{ topic: "Who may make blocks", text: "fixed validator list → by stake (o7)" }], "Block making would follow stake instead of a fixed list: the richest accounts seal the blocks.") });
    else if (kind === "fixed") Object.assign(p, { kind, value: "validator_set", patch: { eligibility_mode: "validator_set" }, explain: ex(SPECIAL_TITLE.fixed, [{ topic: "Who may make blocks", text: "by stake → fixed validator list (o7)" }], "Block making would follow the fixed validator list again instead of stake.") });
    else Object.assign(p, { kind: "noop", revisions: [SPEC(rules.fee)], explain: ex("Same rules as now (no real change)", [], "Nothing would change: the text equals the rules already in force. Often a test of the voting itself.", "none") });
    return p;
  }
  const txType = tx => tx.tx_type ? tx.tx_type : tx.operations && tx.operations["0"] ? "rule_deploy" : "user_tx";

  function curRules(h) {
    if (ST.curH !== h) { ST.cur = ST.curH === h - 1 && ST.cur && !ST.props.some(p => p.activate_at === h && p.approved_at != null) ? ST.cur : rulesAt(h); ST.curH = h; }
    return ST.cur;
  }
  function makeBlock(n) {
    const prev = B[n - 1], rules = curRules(n - 1), N = rules.validators.length, fee = rules.fee;
    // who seals this block: the validators in turn, or under proof of stake the six richest accounts (validators included) in turn
    const makers = rules.elig === "stake" ? [...ST.bal.entries()].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, 6).map(e => e[0]) : rules.validators;
    const t = ts(n), prevT = n > 1 ? ts(n - 1) : t - PACE;
    const txs = [], ids = [], arrive = [], dropped = [];
    const seqOf = a => { const s = ST.seq.get(a) || 0; ST.seq.set(a, s + 1); return s; };
    const bal = a => ST.bal.get(a) || 0, move = (a, d) => ST.bal.set(a, bal(a) + d);
    const base = sender => ({ sender_pubkey: sender, sequence_number: seqOf(sender), fee_limit: "100", expiration_time: t + 3600 });
    const put = tx => { txs.push(tx); const id = hexOf(R, 64); ids.push(id); arrive.push(Math.round(prevT + (0.05 + R() * 0.9) * (t - prevT))); move(tx.sender_pubkey, -fee); TXI.set(id, { h: n, i: txs.length - 1 }); };
    const refuse = (type, sender, why) => { const d = { tx_hash: hexOf(R, 64), type, sender, seq: ST.seq.get(sender) || 0, seen: Math.round(prevT + (0.05 + R() * 0.9) * (t - prevT)), left: t, why, h: n }; dropped.push(d); ST.dropped.push(d); DROP.set(d.tx_hash, d); };
    const setRule = (a, rule) => ST.rules.set(a, rule);
    // every counted vote is a yes: the node's governance code counts votes, it does not weigh them (alerts/alerts.py replays it the same way)
    const vote = (p, v, h) => { put({ ...base(v), tx_type: "consensus_rule_vote", update_id: p.id, approve: true }); p.votes.push({ h, voter: v, counted: true, approve: true }); if (p.approved_at == null && p.votes.length >= p.thr) p.approved_at = h; };
    // governance: validators vote on every open proposal; the day's programme proposes its special change at the fixed block, an ordinary one comes when nothing is open
    for (const p of ST.props) {
      if (statusAt(p, n - 1) !== "voting" || n >= p.activate_at) continue;
      if (p.special) {
        // the hourly change waits for the visitors: from hh:28 the validators follow their majority, one vote per block; a "no" leaves the proposer alone
        if (n < p.proposed_at + BALLOT_BLOCKS || slotOutcome(p.slot) === "no") continue;
        const v = rules.validators.find(x => !p.votes.some(y => y.voter === x));
        if (v) vote(p, v, n);
        continue;
      }
      for (const v of rules.validators) {
        if (p.abstain.has(v) || p.votes.some(x => x.voter === v) || R() >= 0.4) continue;
        vote(p, v, n);
      }
    }
    const want = specialAt(n), extra = extraAt(n), last = ST.props[ST.props.length - 1], busy = last && ["voting", "agreed"].includes(statusAt(last, n - 1));
    if (extra === "contra") refuse("consensus_rule_update", pick(R, rules.validators), CONTRA_WHY);   // refused at the door: never a proposal, never a vote
    const forced = want || (extra === "contested" ? "contested" : null);
    if (forced || (n >= ST.nextPropAt && !busy)) {
      const p = proposal(n, rules, forced);
      if (!forced) ST.nextPropAt = n + 75 + ((R() * 150) | 0);
      if (!forced && R() < 0.15) refuse("consensus_rule_update", p.proposer, "the proposed spec does not compile against the rules in force");
      else {
        put({ ...base(p.proposer), tx_type: "consensus_rule_update", update_id: p.id, rule_revisions: p.revisions, activate_at_height: p.activate_at, ...(p.patch ? { host_contract_patch: p.patch } : {}) });
        p.tx_id = ids[ids.length - 1]; ST.props.push(p);
        vote(p, p.proposer, n);   // a proposal is not a vote: the proposer votes like everyone else, with a transaction
      }
    }
    // rule offers get an answer a few blocks later, or run out
    for (const o of ST.open.slice()) {
      if (n >= o.expire) { o.status = "expired"; }
      else if (o.conflict && n >= o.h + 2) { o.reason = CONFLICT_WHY(ST.rules.get(o.to).name); put({ ...base(o.to), tx_type: "rule_offer_reject", offer_id: o.id, reason: o.reason }); o.status = "rejected"; }   // two whitelists would refuse everything
      else if (n < o.h + 2 || R() >= 0.3) continue;
      else if (R() < 0.72) { put({ ...base(o.to), tx_type: "rule_offer_accept", offer_id: o.id, rule_text: o.rule.text }); setRule(o.to, o.rule); o.status = "accepted"; }
      else { put({ ...base(o.to), tx_type: "rule_offer_reject", offer_id: o.id }); o.status = "rejected"; }
      ST.open.splice(ST.open.indexOf(o), 1);
    }
    // a retractable transfer can be pulled back until its release block; now and then the sender does, and the money returns
    for (const r of ST.retractables.slice()) {
      if (n >= r.release) { ST.retractables.splice(ST.retractables.indexOf(r), 1); continue; }
      if (n < r.h + 3 || R() >= 0.012 || bal(r.to) < r.amount) continue;
      put({ ...base(r.from), tx_type: "retract_transfer", retractable_id: r.id }); move(r.to, -r.amount); move(r.from, r.amount);
      ST.retractables.splice(ST.retractables.indexOf(r), 1);
    }
    // the first blocks give three accounts a rule of their own, so the rule world is never empty
    if (n <= 3) { const a = ACCOUNTS[n - 1], rule = randomRule(a); put({ ...base(a), operations: { "0": rule.text } }); setRule(a, rule); }
    // the day breathes: every half hour a three-minute burst, a six-minute lull, ordinary traffic in between
    const minute = (n % 225) * PACE / 60, phase = minute >= 8 && minute < 11 ? "burst" : minute >= 20 && minute < 26 ? "quiet" : "normal";
    const k = n <= 3 ? 1 : phase === "burst" ? 4 + ((R() * 6) | 0) : phase === "quiet" ? (R() < 0.75 ? 0 : 1) : R() < 0.2 ? 0 : 1 + ((R() * R() * 5) | 0);
    for (let i = 0; i < k; i++) {
      const r = R(), sender = pick(R, ACCOUNTS), r2 = R();
      // what the node refuses: it waits in the queue, then leaves it with a reason (gettxstatus) and lands in the dropped list
      if (r2 < 0.02) { const have = bal(sender), wants = have + 1 + ((R() * 5000) | 0); refuse("user_tx", sender, `not enough balance: ${wants + fee} AGRS needed with the fee, ${have} available`); continue; }
      if (r2 < 0.035) { const sq = ST.seq.get(sender) || 0; refuse("user_tx", sender, `sequence number ${Math.max(0, sq - 1 - ((R() * 3) | 0))} already used, the next one is ${sq}`); continue; }
      if (r2 < 0.045) { refuse("user_tx", sender, `fee limit ${Math.max(1, fee - 1 - ((R() * 4) | 0))} AGRS is below the base fee of ${fee} AGRS`); continue; }
      if (r2 < 0.052) { refuse("user_tx", sender, `expired at block #${n - 1} before a block took it`); continue; }
      if (r < 0.12) {
        const to = pick(R, ACCOUNTS.filter(x => x !== sender)), has = ST.rules.get(to), rule = randomRule(to), expire = n + 40, id = hexOf(R, 64);
        const conflict = !!has && has.name === "Recipient whitelist" && rule.name === "Recipient whitelist" && has.text !== rule.text;
        put({ ...base(sender), tx_type: "rule_offer", recipient_pubkey: to, rule_text: rule.text, expire_at_height: expire, offer_id: id });
        const o = { id, from: sender, to, rule, h: n, expire, status: "offered", conflict }; ST.offers.push(o); ST.open.push(o);
        continue;
      }
      if (r < 0.2) {
        if (R() < 0.12) { refuse("rule_deploy", sender, "the rule does not compile: o5 must be a boolean clause over the transaction streams"); continue; }
        const rule = randomRule(sender); put({ ...base(sender), operations: { "0": rule.text } }); setRule(sender, rule); continue;
      }
      const to = pick(R, ACCOUNTS.filter(x => x !== sender)), amount = 1 + ((R() * (R() < 0.3 ? 6000 : 1200)) | 0);
      if (bal(sender) < amount + fee) continue;
      const rule = ST.rules.get(sender);
      if (rule && rule.blocks(amount, to)) { if (R() < 0.12) refuse("user_tx", sender, `the sender's own rule said no (o5 = 0 · ${rule.name})`); continue; }   // most people know their own rule
      if (r < 0.26) { put({ ...base(sender), tx_type: "retractable_transfer", recipient_pubkey: to, amount: String(amount), release_at_height: n + 30 }); ST.retractables.push({ id: ids[ids.length - 1], h: n, from: sender, to, amount, release: n + 30 }); }
      else put({ ...base(sender), operations: { "1": [[sender, to, String(amount)]] } });
      move(sender, -amount); move(to, amount);
    }
    B.push({ header: { block_number: n, previous_hash: prev.block_hash, timestamp: t, merkle_root: hexOf(R, 64), proposer_pubkey: makers[n % makers.length], state_hash: hexOf(R, 64) },
      transactions: txs, tx_ids: ids, block_hash: hexOf(R, 64), _arrive: arrive, _dropped: dropped, _fee: fee });
  }

  /* ---------- what the relay answers, from the chain ---------- */
  const pub = b => ({ header: b.header, transactions: b.transactions, tx_ids: b.tx_ids, block_hash: b.block_hash });
  const amountOf = tx => { const tr = tx.operations && tx.operations["1"]; if (tr) return tr.reduce((s, x) => s + (Number(x[2]) || 0), 0); return Number(tx.amount) || 0; };
  const toOf = tx => { const tr = tx.operations && tx.operations["1"]; return tr && tr[0] ? tr[0][1] : tx.recipient_pubkey || ""; };
  const retracted = tx => { const pos = TXI.get(tx.retractable_id); if (!pos) return null; const o = B[pos.h].transactions[pos.i]; return { to: o.recipient_pubkey, amount: Number(o.amount) || 0 }; };
  function mempool(t) {
    t = at(t);
    const h = sync(t), nb = B[h + 1], fee = nb._fee, list = [];
    const entry = (hash, sender, seq, at, type) => ({ tx_hash: hash, sender, sequence_number: seq, received_at: iso(at), expires_at: iso(at + 3600), operation_count: 1, status: "pending", fee_limit: 100, estimated_fee: fee, tx_type: type });
    nb.transactions.forEach((tx, i) => { if (nb._arrive[i] <= t) list.push(entry(nb.tx_ids[i], tx.sender_pubkey, tx.sequence_number, nb._arrive[i], txType(tx))); });
    nb._dropped.forEach(d => { if (d.seen <= t) list.push(entry(d.tx_hash, d.sender, d.seq, d.seen, d.type)); });
    list.sort((a, b) => a.received_at < b.received_at ? -1 : 1);
    return { transactions: list, count: list.length };
  }
  function governance(t) {
    t = at(t);
    const h = sync(t), ru = rulesAt(h), N = ru.validators.length;
    const upd = p => ({ update_id: p.id, activate_at_height: p.activate_at, rule_revisions: p.revisions, ...(p.patch ? { host_contract_patch: p.patch } : {}), proposer_pubkey: p.proposer, included_at_height: p.proposed_at });
    const ps = ST.props.filter(p => p.proposed_at <= h), by = s => ps.filter(p => statusAt(p, h) === s);
    return { head_number: h, head_hash: B[h].block_hash, next_block_height: h + 1, network_tip: { number: h, hash: B[h].block_hash },
      eligibility_mode: ru.elig, active_validators: ru.validators, active_validator_count: N, vote_quorum: ru.quorum, approval_threshold: threshold(ru.quorum, N),
      min_activation_height_for_next_update: h + 1 + N, consensus_rules: SPEC(ru.fee), spec_revision: ru.rev,
      pending_updates: by("voting").map(upd), scheduled_updates: by("agreed").map(upd),
      archival_update_details: [...by("active").map(p => ({ ...upd(p), lifecycle: "activated" })), ...by("dropped").map(p => ({ ...upd(p), lifecycle: "expired" }))].sort((a, b) => a.activate_at_height - b.activate_at_height),
      votes: ps.flatMap(p => p.votes.filter(v => v.h <= h).map(v => ({ update_id: p.id, voter_pubkey: v.voter, approve: v.approve, height: v.h }))) };
  }
  function account(addr, t) {
    t = at(t);
    const h = sync(t); addr = String(addr).toLowerCase();
    const key = addr + ":" + h;
    if (!ACC.has(key)) {
      let bal = GENESIS[addr] || 0, seq = 0;
      for (let n = 1; n <= h; n++) for (const tx of B[n].transactions) {
        const back = tx.tx_type === "retract_transfer" ? retracted(tx) : null;   // a pulled-back transfer returns its amount
        if (tx.sender_pubkey === addr) { bal -= B[n]._fee; seq++; if (txType(tx) === "user_tx" || tx.tx_type === "retractable_transfer") bal -= amountOf(tx); else if (back) bal += back.amount; }
        else if (toOf(tx) === addr && (txType(tx) === "user_tx" || tx.tx_type === "retractable_transfer")) bal += amountOf(tx);
        else if (back && back.to === addr) bal -= back.amount;
      }
      if (ACC.size > 2000) ACC.clear();
      ACC.set(key, { bal, seq });
    }
    const a = ACC.get(key), nb = B[h + 1];
    let out = 0, inc = 0, fees = 0;
    nb.transactions.forEach((tx, i) => { if (nb._arrive[i] > t) return; if (tx.sender_pubkey === addr) { fees += nb._fee; if (txType(tx) === "user_tx" || tx.tx_type === "retractable_transfer") out += amountOf(tx); } else if (toOf(tx) === addr) inc += amountOf(tx); });
    return { address: addr, chain_balance: String(a.bal), pending_outgoing: String(out), pending_incoming: String(inc), pending_fees: String(fees), escrowed_out: "0", sequence_number: a.seq };
  }
  function ruleOffers(addr, dir, t) {
    t = at(t);
    const h = sync(t); addr = String(addr).toLowerCase(); dir = dir || "all";
    const rows = ST.offers.filter(o => o.h <= h && ((dir !== "out" && o.to === addr) || (dir !== "in" && o.from === addr))).map(o => ({
      offer_id: o.id, offerer_pubkey: o.from, recipient_pubkey: o.to, rule_text: o.rule.text, expire_at_height: o.expire, created_at_height: o.h,
      status: o.status === "offered" && h >= o.expire ? "expired" : o.status, ...(o.reason ? { reason: o.reason } : {}) }));
    const acc = ST.rules.get(addr);
    return { address: addr, direction: dir, offers: rows, accepted_clauses: acc ? [{ target_stream: "o5", clause_body: acc.text }] : [] };
  }
  function txStatus(hash, t) {
    t = at(t);
    const h = sync(t); hash = String(hash).toLowerCase();
    const pos = TXI.get(hash);
    if (pos && pos.h <= h) return { tx_hash: hash, status: "confirmed", block_number: pos.h, block_hash: B[pos.h].block_hash, index: pos.i };
    const d = DROP.get(hash);
    if (d && d.left <= t) return { tx_hash: hash, status: "rejected", reason: d.why, received_at: iso(d.seen) };
    if (mempool(t).transactions.some(m => m.tx_hash === hash)) return { tx_hash: hash, status: "queued" };
    return { tx_hash: hash, status: "unknown" };
  }
  /* chain restarts: the simulated testnet starts over every day at 00:00 UTC; the last days are on record */
  function restarts(t, days) {
    t = at(t);
    const out = [], tip = Math.floor((DAY - 1) / PACE);
    for (let d = Math.min(days, 7); d >= 1; d--) {
      const g0 = (DAYI - d) * DAY, g1 = (DAYI - d + 1) * DAY;
      out.push({ detected_at: g1 + PACE + 4, old: { block1_ts: g0 + PACE, tip, tip_ts: g0 + tip * PACE }, new_block1_ts: g1 + PACE });
    }
    return out;
  }
  function stats(t) {
    t = at(t);
    const h = sync(t), accounts = new Map(), proposers = new Map(), idx = (m, k) => { if (!m.has(k)) m.set(k, m.size); return m.get(k); };
    const rows = [];
    for (let n = 0; n <= h; n++) {
      const b = B[n], types = {}, senders = new Set(); let transfers = 0, volume = 0;
      for (const tx of b.transactions) {
        const ty = txType(tx); types[ty] = (types[ty] || 0) + 1; senders.add(idx(accounts, tx.sender_pubkey));
        const tr = tx.operations && tx.operations["1"]; if (tr) for (const x of tr) { transfers++; volume += Number(x[2]) || 0; }
      }
      rows.push([n, b.header.timestamp, b.transactions.length, transfers, volume, idx(proposers, b.header.proposer_pubkey), types, [...senders].sort((a, b) => a - b)]);
    }
    const ru = rulesAt(h), ps = ST.props.filter(p => p.proposed_at <= h), cnt = s => ps.filter(p => statusAt(p, h) === s).length;
    const dropped = ST.dropped.filter(d => d.left <= t).map(d => ({ tx_hash: d.tx_hash, type: d.type, sender: d.sender, seen: d.seen, left: d.left, reason: d.why }));
    return { generated_at: Math.round(t), tracking_since: G - 7 * DAY, head: h, canonical_height: h, tip_height: h, total_blocks: h + 1,
      fields: ["height", "timestamp", "txs", "transfers", "volume", "proposer", "types", "senders"], blocks: rows,
      accounts: [...accounts.keys()], proposers: [...proposers.keys()], restarts: restarts(t, 3), dropped: dropped.slice(-500), dropped_total: dropped.length,
      governance: { pending: cnt("voting"), scheduled: cnt("agreed"), activated: cnt("active"), expired: cnt("dropped"), validators: ru.validators.length }, simulation: true };
  }
  /* availability of the simulated node: a quiet month with a few short outages, the same ones for everybody */
  function incidentsOfDay(d) {
    const r = prng(mix(d * 31 + 5)), base = d * DAY, out = [];
    if (r() < 0.18) { const s = base + ((r() * 86000) | 0); out.push({ kind: "node", start: s, end: s + 240 + ((r() * 1500) | 0) }); }
    if (r() < 0.25) { const s = base + ((r() * 86000) | 0); out.push({ kind: "sync", start: s, end: s + 120 + ((r() * 700) | 0), max_lag: 3 + ((r() * 40) | 0) }); }
    if (r() < 0.10) { const s = base + ((r() * 86000) | 0); out.push({ kind: "relay", start: s, end: s + 60 + ((r() * 400) | 0) }); }
    return out;
  }
  function uptimeHours(t) {
    t = at(t);
    const since = Math.floor((t - 31 * DAY) / 3600) * 3600, incidents = [];
    for (let d = Math.floor(since / DAY); d <= DAYI; d++) for (const i of incidentsOfDay(d)) if (i.end <= t && i.start >= since) incidents.push(i);
    const down = (H, kind) => incidents.filter(i => i.kind === kind).reduce((s, i) => s + Math.max(0, Math.min(i.end, H + 3600) - Math.max(i.start, H)), 0) / 60;
    const hours = [];
    for (let H = since; H < t; H += 3600) {
      const n = Math.max(1, Math.min(60, Math.floor((Math.min(H + 3600, t) - H) / 60)));
      const relay = Math.min(n, Math.round(down(H, "relay"))), node = Math.min(n - relay, Math.round(down(H, "node"))), lag = Math.min(n - relay - node, Math.round(down(H, "sync")));
      const r = n - relay, ok = r - node, sy = ok - lag;
      const avg = Math.round((90 - 55 * ((relay + node) / n) - 20 * (lag / n)) * 10) / 10, low = relay + node ? 25 : lag ? 60 : 88;
      hours.push([H, n, ok, sy, Math.round(avg * n), low, n]);
    }
    return { since, incidents, hours };
  }
  function health(t) {
    t = at(t);
    const h = sync(t), u = uptimeHours(t), cut = t - DAY;
    const lin = (x, good, bad) => Math.max(0, Math.min(1, (x - bad) / (good - bad)));
    const F = [], add = (key, label, w, frac, value, note) => F.push({ key, label, weight: w, points: Math.round(w * frac * 10) / 10, value, note: note || "" });
    const age = Math.max(0, t - ts(h)), window = Math.max(600, Math.min(3600, t - ts(1))), made = Math.max(0, h - headAt(t - window)), want = window / PACE;
    add("node", "Node answering", 20, 1, "yes");
    add("sync", "In sync with the network", 15, 1, "in sync");
    add("last_block", "Time since the last block", 20, lin(age, 180, 1800), Math.round(age), `usually ${PACE} s between blocks`);
    add("pace", "Blocks in the last hour", 10, lin(made / want, 0.75, 0), made, `about ${Math.round(want)} expected` + (window < 3600 ? ` in ${Math.round(window / 60)} min` : ""));
    let samples = 0, synced = 0; for (const r of u.hours) if (r[0] >= cut - 3599) { samples += r[1]; synced += r[3]; }
    add("availability", "Live and in sync, 24 h", 10, samples ? lin(synced / samples, 0.99, 0.8) : 1, samples ? Math.round(synced / samples * 10000) / 10000 : null, `${samples} checks`);
    const rs = restarts(t, 7).filter(r => r.detected_at >= cut).length;
    add("stability", "Restarts, reorgs and stalls, 24 h", 15, Math.max(0, 1 - 10 * rs / 15), { restarts: rs, reorgs: 0, stalls: 0 }, "a restart costs 10 points, a stall over 10 min 4, a reorg 3");
    const pool = mempool(t).transactions, oldest = pool.length ? Math.max(...pool.map(m => t - Date.parse(m.received_at) / 1000)) : 0;
    add("mempool", "Waiting transactions", 10, lin(oldest, 600, 3600), { waiting: pool.length, sealed: 0, oldest: Math.round(oldest) }, pool.length ? "a real one waiting long costs points" : "mempool empty");
    const score = Math.round(F.reduce((s, f) => s + f.points, 0)), state = score < 50 ? "down" : score >= 80 ? "healthy" : "degraded";
    return { generated_at: Math.round(t), score, state, label: { healthy: "Healthy", degraded: "Degraded", down: "Down" }[state], at: Math.round(t), expected_block_seconds: PACE,
      factors: F, known_issues: [], thresholds: { healthy: 80, degraded: 50 }, fields: ["hour", "average", "lowest"], hours: u.hours.map(r => [r[0], Math.round(r[4] / r[6] * 10) / 10, r[5]]), simulation: true };
  }
  function status(t) {
    t = at(t);
    const h = sync(t), hs = health(t);
    return { upstream_connected: true, height: h, canonical_height: h, tip_height: h, live_default: true, open_governance_admission: false, total_blocks: h + 1,
      clients: 1, online: 1, community_nodes: NODES.filter(n => n.online).length, restarts: restarts(t, 7).slice(-10).map(r => ({ detected_at: r.detected_at, old_tip: r.old.tip })), reorgs: [],
      health: { score: hs.score, state: hs.state, label: hs.label }, age_seconds: { getblocks: Math.round((t - ts(h)) * 10) / 10 }, uptime_seconds: Math.round(t - G), network: NETWORK, simulation: true };
  }
  function uptime(t) {
    t = at(t);
    const h = sync(t), u = uptimeHours(t);
    return { generated_at: Math.round(t), since: u.since, sample_seconds: 60, sync_lag_blocks: 2, stall_seconds: 600,
      fields: ["hour", "samples", "node_ok", "synced", "score_sum", "score_min", "score_samples"], hours: u.hours, incidents: u.incidents,
      restarts: restarts(t, 7).map(r => ({ detected_at: r.detected_at, old_tip: r.old.tip, old_tip_ts: r.old.tip_ts, new_block1_ts: r.new_block1_ts })),
      reorgs: [], stalls: [], last_block_ts: ts(h), status: status(t), simulation: true };
  }
  // bob falls behind every hour from minute 35: one block per ten seconds, up to 60 behind, then catches up over two minutes from minute 45
  const lagOf = (n, t) => { if (n.name !== "bob") return n.lag; const m = ((t % 3600) + 3600) % 3600; return m >= 2100 && m < 2700 ? Math.min(60, 1 + (((m - 2100) / 10) | 0)) : m >= 2700 && m < 2820 ? Math.max(n.lag, 60 - (((m - 2700) / 2) | 0)) : n.lag; };
  const nodeRow = (n, t, h) => { const lag = Math.min(lagOf(n, t), h); return { id: n.id, name: n.name, height: h - lag, head: B[h - lag].block_hash, tip: h, kit: n.kit, ref: "539d1e2", peer: n.peer,
    first_seen: Math.round(t - n.days * DAY), last_seen: Math.round(t - (n.online ? 20 + 30 * Math.min(lag, 2) : 3 * DAY)) }; };
  function community(t) {
    t = at(t);
    const h = sync(t);
    return { reference: { name: "tauhud.com", height: h, head: B[h].block_hash, tip: h, upstream_connected: true },
      nodes: NODES.filter(n => n.online).map(n => ({ ...nodeRow(n, t, h), agrees: lagOf(n, t) > 2 ? "behind" : "same", age_seconds: 20 + 30 * Math.min(lagOf(n, t), 2) })), ttl_seconds: 900, generated_at: Math.round(t), simulation: true };
  }
  function board(t) {
    t = at(t);
    const h = sync(t);
    return { nodes: NODES.map(n => { const r = nodeRow(n, t, h); return { id: r.id, name: r.name, first_seen: r.first_seen, last_seen: r.last_seen, online: n.online, days: Math.floor(n.days), uptime: n.uptime, height: n.online ? r.height : h - 1300, kit: n.kit, ref: "539d1e2", agrees: n.online ? (lagOf(n, t) > 2 ? "behind" : "same") : null }; }),
      keep_days: 30, generated_at: Math.round(t), simulation: true };
  }
  function peers(t) {
    t = at(t);
    const h = sync(t), mk = (id, days, head, extra) => ({ id, label: null, community: null, first_seen: Math.round(t - days * DAY), last_direct: Math.round(t - 40), last_heard: null, last_seen: Math.round(t - 40), head, connected: true, ...extra });
    const list = [mk(BOOTNODE, 9, h, {}), ...NODES.filter(n => n.online && n.peer).map(n => mk(n.peer, n.days, Math.max(0, h - lagOf(n, t)), { community: { id: n.id, name: n.name } })),
      mk(STRANGERS[0], 3, h - 1, {}), mk(STRANGERS[1], 0.2, h, { connected: false, last_direct: Math.round(t - 2 * 3600), last_seen: Math.round(t - 2 * 3600) })];
    const within = s => list.filter(p => p.last_seen >= t - s).length;
    return { peers: list, counts: { connected: list.filter(p => p.connected).length, met_30m: within(1800), met_24h: within(DAY), seen_24h: within(DAY), seen_30d: list.length },
      bootnode: BOOTNODE, since: Math.round(G - 9 * DAY), keep_days: 30, generated_at: Math.round(t), simulation: true };
  }
  function summary(t) {
    t = at(t);
    const h = sync(t), ru = rulesAt(h), hs = health(t), ps = ST.props.filter(p => p.proposed_at <= h), cnt = s => ps.filter(p => statusAt(p, h) === s).length;
    const proposals = { waiting: cnt("voting"), agreed: cnt("agreed"), in_force: cnt("active"), dropped: cnt("dropped") }; proposals.total = ps.length;
    return { api: "tauhud/v1", network: NETWORK, generated_at: Math.round(t), status: "synced", height: h, tip_height: h, last_block_ts: ts(h), last_block_age_seconds: Math.round(t - ts(h)),
      pace_seconds: PACE, spec_revision: ru.rev, base_fee: ru.fee, validators: ru.validators.length, proposals, mempool: mempool(t).count, viewers: 1,
      community_nodes: NODES.filter(n => n.online).length, health: { score: hs.score, state: hs.state, label: hs.label }, docs: "https://tauhud.com/developers/", simulation: true };
  }
  /* the visitors' ballot on the hourly change k: open hh:20 to hh:27, the tally from the relay, the outcome once closed */
  function ballotOf(k, t) { const opens = G + (SLOT_AT + SLOT_LEN * k) * PACE; return ballotFor("slot:" + k, t, opens, opens + BALLOT_SECONDS, slotOutcome(k)); }
  /* any item the relay counts (a visitor proposal too): the same shape, so every page treats it the same way */
  function ballotFor(item, t, opens, closes, cached) {
    t = at(t);
    const b = BALLOTS.day === dayKey() && BALLOTS.items[item] || null;
    opens = opens != null ? opens : b ? b.opens : null; closes = closes != null ? closes : b ? b.closes : null;
    const outcome = closes != null && t >= closes ? (b && b.outcome) || cached || (b ? "none" : null) : null;
    return { item, opens, closes, open: opens != null && t >= opens && t < closes, yes: b ? b.yes : 0, no: b ? b.no : 0, voters: b ? b.voters || [] : [], mine: b && b.mine != null ? b.mine : null, outcome, counted: !!b, meta: b ? b.meta || {} : {} };
  }
  const dayKey = () => new Date(DAYI * DAY * 1000).toISOString().slice(0, 10);

  /* the programme ahead: the next special rule changes (proposed hh:20, in force hh:30) and the restart at midnight, for the countdowns */
  function upcoming(t) {
    t = at(t);
    const h = sync(t), out = [];
    for (let n = SLOT_AT; n + SLOT_WAIT < 10800 && out.length < 3; n += SLOT_LEN) {
      if (n + SLOT_WAIT <= h) continue;
      const kind = specialAt(n), p = ST.props.find(x => x.special === kind && x.proposed_at === n);
      out.push({ kind, short: SHORT[kind], title: p ? p.explain.title : SPECIAL_TITLE[kind], proposed_at: n, proposed_ts: ts(n), activate_at: n + SLOT_WAIT, at_ts: ts(n + SLOT_WAIT),
        status: p ? statusAt(p, h) : "scheduled", id: p ? p.id : null, votes: p ? p.votes.filter(v => v.h <= h).length : 0, thr: p ? p.thr : null, ballot: ballotOf((n - SLOT_AT) / SLOT_LEN, t) });
    }
    out.push({ kind: "restart", short: SHORT.restart, title: SPECIAL_TITLE.restart, proposed_at: null, proposed_ts: null, activate_at: 1, at_ts: (DAYI + 1) * DAY + PACE, status: "scheduled", id: null, votes: 0, thr: null });
    return out.sort((a, b) => a.at_ts - b.at_ts).slice(0, 3);
  }
  /* the proposal tracker's file: every rule change with its votes, the rules in force, the newest events, the programme ahead */
  function proposals(t) {
    t = at(t);
    const h = sync(t), ru = rulesAt(h), ps = ST.props.filter(p => p.proposed_at <= h), chain = B[1] ? B[1].block_hash.slice(0, 16) : "";
    const active = ps.filter(p => statusAt(p, h) === "active").sort((a, b) => a.activate_at - b.activate_at || a.n - b.n);
    const rows = ps.map(p => {
      const s = statusAt(p, h), votes = p.votes.filter(v => v.h <= h), ok = p.approved_at != null && p.approved_at <= h;
      return { id: p.id, n: p.n, title: p.explain.title, parts: [], status: s, proposer: p.proposer, proposed_at: p.proposed_at, proposed_ts: ts(p.proposed_at), activate_at: p.activate_at,
        approved_at: ok ? p.approved_at : null, approved_ts: ok ? ts(p.approved_at) : null, activated_at: s === "active" ? p.activate_at : null, activated_ts: s === "active" ? ts(p.activate_at) : null,
        expired_at: s === "dropped" ? p.activate_at : null, expired_ts: s === "dropped" ? ts(p.activate_at) : null, thr: p.thr, counted_votes: votes.filter(v => v.approve).length,
        rev: s === "active" ? 2 + active.indexOf(p) : null, revisions: p.revisions, patch: p.patch, dups: [], tx_id: p.tx_id, explain: p.explain, votes, ballot: p.special ? ballotOf(p.slot, t) : null };
    }).reverse();
    const events = [];
    for (const p of rows) {
      const say = (kind, hh, headline, body) => events.push({ key: `${kind}:${p.id}`, kind, h: hh, ts: ts(hh), seen: ts(hh), id: p.id, headline, body, link: null, chain });
      say("proposed", p.proposed_at, `New proposal: ${p.title}`, `${p.explain.why} Needs ${p.thr} of ${rulesAt(p.proposed_at).validators.length} validators by block #${p.activate_at}.`);
      if (p.approved_at != null) say("agreed", p.approved_at, `Agreed: ${p.title}`, `${p.counted_votes} votes, enough. Takes effect at block #${p.activate_at}.`);
      if (p.status === "active") say("active", p.activate_at, `In force: ${p.title}`, `Revision ${p.rev} of the rules applies from block #${p.activate_at}.`);
      if (p.status === "dropped") say("dropped", p.activate_at, `Dropped: ${p.title}`, (p.ballot && p.ballot.outcome === "no" ? `The visitors voted no (${p.ballot.no} no, ${p.ballot.yes} yes), so the validators did not agree. ` : "") + `Only ${p.counted_votes} of ${p.thr} votes by block #${p.activate_at}. The old rules stand.`);
    }
    // what Tau refused before any vote: a rule change that does not fit the rules in force never becomes a proposal
    for (const d of ST.dropped) if (d.type === "consensus_rule_update" && d.left <= t)
      events.push({ key: "refused:" + d.tx_hash, kind: "refused", h: d.h, ts: d.left, seen: d.left, id: null, headline: "Refused before the vote: a rule change that contradicts the rules in force",
        body: `Tau checks a proposed rule against the rules in force before anyone may vote on it. Reason: ${d.why}.`, link: null, chain });
    if (h >= 1) events.push({ key: "restart:" + DAYI, kind: "restart", h: 1, ts: ts(1), seen: ts(1), id: null, headline: "The simulated testnet started over", body: "A new day, a new chain: block numbers restart at genesis, as the real testnet did after its restarts.", link: null, chain });
    events.sort((a, b) => b.ts - a.ts || b.h - a.h);
    return { generated_at: Math.round(t), chain: { block1_hash: B[1] ? B[1].block_hash : null, head: h, head_ts: ts(h), first: 0, seconds_per_block: PACE, node_head: h },
      rules: { revision: ru.rev, base_fee: ru.fee, validators: ru.validators.length, quorum: ru.quorum, votes_needed: threshold(ru.quorum, ru.validators.length), open_admission: false, consensus_mode: ru.elig },
      proposals: rows, events: events.slice(0, 100), upcoming: upcoming(t), channels: {}, simulation: true };
  }

  /* ---------- the visitors' votes: fetched from the relay, applied to the chain ---------- */
  const SOCKSEEN = () => Math.max(-1, ...[...SOCKETS].map(s => s._seen));
  // the first block a change of outside input touches (Infinity: none). A further source adds its own comparison here.
  function firstTouched(prev, next) {
    let first = Infinity;
    const no = (o, k) => o.day === DAYI && o.slots[k] === "no";   // "yes" and "none" make the same chain
    for (let k = 0; k < 24; k++) if (no(prev, k) !== no(next, k)) first = Math.min(first, SLOT_AT + SLOT_LEN * k + BALLOT_BLOCKS);
    return first;
  }
  function applyOutside(next) {
    const prev = OUTSIDE, first = firstTouched(prev, next);
    OUTSIDE = next; store.set("tau-sim-outside", JSON.stringify(next));
    if (first < B.length) {   // a block already generated came out differently: generate the day again, the blocks before it stay as they were
      const h = B.length - 2, seen = SOCKSEEN();
      init(DAYI); gen(Math.max(0, h) + 1);
      if (seen >= first) RESET++;   // a page already holds a block that changed: it gets the chain afresh
    }
  }
  async function refreshOutside() {
    sync();
    const r = await fetch(`${RELAY}/sim/votes?voter=${me().token}`, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    if (!j || !j.items) return;
    const was = JSON.stringify(BALLOTS.items);
    BALLOTS = j; BAL_AT = Date.now();
    if (j.day === dayKey()) {
      const slots = {};
      for (const [id, it] of Object.entries(j.items)) { const m = /^slot:(\d+)$/.exec(id); if (m && it && it.outcome) slots[m[1]] = it.outcome; }
      // (a further source of outside input merges its own field into next here)
      applyOutside({ ...OUTSIDE, day: DAYI, slots });
    }
    if (JSON.stringify(j.items) !== was) BAL_FNS.forEach(fn => { try { fn(BALLOTS); } catch (e) {} });
  }
  // poll quickly while a ballot is open or has just closed, slowly otherwise
  function ballotPace() {
    const t = now(), k = Math.floor(((t - G) / PACE - SLOT_AT) / SLOT_LEN), opens = G + (SLOT_AT + SLOT_LEN * k) * PACE;
    return k >= 0 && t >= opens - 30 && t < opens + BALLOT_SECONDS + 60 ? 5000 : 30000;
  }
  function pollBallots() {
    const go = () => refreshOutside().catch(() => {}).finally(() => setTimeout(pollBallots, document.hidden ? 30000 : ballotPace()));
    go();
  }
  let FIRST = Promise.resolve();
  if (ON) { sync(); FIRST = new Promise(res => { setTimeout(res, 1500); refreshOutside().catch(() => {}).finally(res); }).then(() => setTimeout(pollBallots, ballotPace())); }
  async function castVote(item, yes) {
    const m = me();
    try {
      const r = await fetch(`${RELAY}/sim/vote?item=${encodeURIComponent(item)}&voter=${m.token}&yes=${yes ? 1 : 0}&a=${m.a}&b=${m.b}&c=${m.c}`, { cache: "no-store" });
      const j = await r.json();
      if (j && j.item) { BALLOTS.items = { ...BALLOTS.items, [item]: j.item }; BAL_FNS.forEach(fn => { try { fn(BALLOTS); } catch (e) {} }); }
      return j || { ok: false, error: "bad" };
    } catch (e) { return { ok: false, error: "offline" }; }
  }

  /* ---------- a WebSocket to the simulation, and fetch for its GET endpoints ---------- */
  const ok = (command, data) => JSON.stringify({ status: "ok", command, data });
  const err = (command, message, code) => JSON.stringify({ status: "error", command, error: { code, message } });
  const isHex = (s, n) => typeof s === "string" && new RegExp(`^[0-9a-fA-F]{${n}}$`).test(s);
  function answer(line) {
    const parts = String(line).trim().split(/\s+/), cmd = (parts[0] || "").toLowerCase(), args = parts.slice(1), t = now();
    if (cmd === "hello") return "ok version=1 env=simulation node=tau-hud-sim";
    if (cmd === "getblocks") {
      const lim = args[0] && /^\d+$/.test(args[0]) ? Math.max(1, Math.min(20000, Number(args[0]))) : 12, h = sync(t);
      const blocks = B.slice(Math.max(0, h + 1 - lim), h + 1).map(pub);
      return ok(cmd, { blocks, total: h + 1, truncated: blocks.length < h + 1 });
    }
    if (cmd === "getblockrange") {
      if (args.length !== 2 || !/^\d+$/.test(args[0]) || !/^\d+$/.test(args[1]) || Number(args[1]) < 1 || Number(args[1]) > 500) return err(cmd, "Usage: getblockrange <from_height> <count 1..500>", "INVALID_PARAMS");
      const from = Number(args[0]), count = Number(args[1]), h = sync(t);
      return ok(cmd, { blocks: B.slice(from, Math.min(from + count, h + 1)).map(pub), from, total: h + 1, head: h });
    }
    if (cmd === "getgovernance") return ok(cmd, governance(t));
    if (cmd === "getmempool") return ok(cmd, mempool(t));
    if (cmd === "gettaustate") { const h = sync(t); return ok(cmd, { head_number: h, consensus_rules: SPEC(rulesAt(h).fee) }); }
    if (cmd === "presence") return ok(cmd, { online: 1, pushed: false });
    if (["getaccountstate", "getbalance", "getsequence", "getruleoffers", "gettxstatus"].includes(cmd)) {
      if (!args.length || !isHex(args[0], cmd === "gettxstatus" ? 64 : 96)) return err(cmd, "Invalid arguments.", "INVALID_PARAMS");
      if (cmd === "gettxstatus") return ok(cmd, txStatus(args[0], t));
      if (cmd === "getruleoffers") return ok(cmd, ruleOffers(args[0], (args[1] || "all").toLowerCase(), t));
      const a = account(args[0], t);
      if (cmd === "getbalance") return ok(cmd, { address: a.address, balance: a.chain_balance });
      if (cmd === "getsequence") return ok(cmd, { address: a.address, sequence_number: a.sequence_number });
      return ok(cmd, a);
    }
    return err(cmd, "Not in the simulation. Allowed: getblocks, getblockrange, getmempool, getgovernance, gettaustate, presence, getaccountstate, getbalance, getsequence, getruleoffers, gettxstatus", "FORBIDDEN");
  }
  const SOCKETS = new Set();
  function socket() {
    const s = { readyState: 0, url: "sim://tau-hud", onopen: null, onmessage: null, onclose: null, onerror: null, _t: new Set(), _seen: -1, _reset: RESET, _mp: "", _gov: "" };
    const later = (fn, ms) => { const id = setTimeout(() => { s._t.delete(id); if (s.readyState === 1) fn(); }, ms); s._t.add(id); };
    s._emit = text => { if (s.readyState === 1 && typeof s.onmessage === "function") s.onmessage({ data: text }); };
    s.send = cmd => { if (s.readyState !== 1) return; later(() => s._emit(answer(cmd)), 8 + Math.random() * 25); };
    s.close = () => { if (s.readyState === 3) return; s.readyState = 3; s._t.forEach(clearTimeout); s._t.clear(); SOCKETS.delete(s); };
    s.addEventListener = (type, fn) => { s["on" + type] = fn; };
    FIRST.then(() => setTimeout(() => { if (s.readyState === 3) return; s.readyState = 1; s._seen = sync(); SOCKETS.add(s); if (typeof s.onopen === "function") s.onopen({}); }, 15));   // after the visitors' outcomes are in, so the first blocks are the final ones
    return s;
  }
  /* new blocks, queue changes and governance changes reach every open socket as the relay pushes them */
  function pushLoop() {
    if (!SOCKETS.size) return;
    const t = now(), h = sync(t);
    const mp = JSON.stringify(mempool(t)), g = governance(t);
    const gkey = JSON.stringify([g.pending_updates.map(u => u.update_id), g.scheduled_updates.map(u => u.update_id), g.archival_update_details.length, g.votes.length, g.consensus_rules.length, g.active_validator_count]);
    for (const s of SOCKETS) {
      if (s._reset !== RESET) { s._reset = RESET; s._seen = -1; s._emit(ok("getblocks", { blocks: B.slice(0, h + 1).slice(-12).map(pub), total: h + 1, truncated: h + 1 > 12, reset: true })); s._seen = h; s._mp = ""; s._gov = ""; }
      else if (h > s._seen) { s._emit(ok("getblocks", { blocks: B.slice(s._seen + 1, h + 1).slice(-12).map(pub), total: h + 1, truncated: true })); s._seen = h; }
      if (mp !== s._mp) { s._mp = mp; s._emit(ok("getmempool", JSON.parse(mp))); }
      if (gkey !== s._gov) { s._gov = gkey; s._emit(ok("getgovernance", g)); }
    }
  }
  setInterval(pushLoop, 1000);
  async function fetchSim(url) {
    await FIRST;   // the visitors' outcomes first, so every answer describes the final chain
    const path = String(url).replace(/^[a-z]+:\/\/[^/]+/i, "").split("?")[0].replace(/\/$/, "") || "/", t = now();
    const data = path === "/status" || path === "/health" ? status(t) : path === "/stats" ? stats(t) : path === "/uptime" ? uptime(t) : path === "/health-score" ? health(t)
      : path === "/community" ? community(t) : path === "/community/board" ? board(t) : path === "/peers" ? peers(t) : path === "/api/v1/summary" ? summary(t) : path === "/proposals.json" ? proposals(t) : null;
    const okay = data != null;
    return new Promise(res => setTimeout(() => res({ ok: okay, status: okay ? 200 : 404, url: String(url), json: async () => { if (!okay) throw new Error("404"); return data; }, text: async () => okay ? JSON.stringify(data) : "not in the simulation" }), 15 + Math.random() * 30));
  }

  window.TauSim = {
    on: ON, pace: PACE, network: NETWORK, genesis: GENESIS, validators: VALIDATORS0, accounts: ACCOUNTS, genesisHash: GENESIS_HASH,
    mode: () => (store.get(KEY) === "sim" ? "sim" : "live"),
    set(mode) {
      store.set(KEY, mode === "sim" ? "sim" : "live");
      try { const u = new URL(location.href); u.searchParams.delete("mode"); u.searchParams.delete("sample"); if (u.href === location.href) location.reload(); else location.href = u.href; } catch (e) { location.reload(); }
    },
    head: () => sync(), block: n => { sync(); return B[n] ? pub(B[n]) : null; }, ts: n => { sync(); return ts(n); },
    refresh: () => refreshOutside().catch(() => {}), me, vote: castVote, ballots: () => BALLOTS, ballot: k => ballotOf(k), ballotFor: item => ballotFor(item), onBallots: fn => { BAL_FNS.add(fn); return () => BAL_FNS.delete(fn); }, nameOf, colourOf: c => ID_COLOURS[c] || "#c8c8d0", colours: ID_COLOURS, ballotSeconds: BALLOT_SECONDS, ready: () => FIRST,
    socket, fetch: fetchSim, answer, status, stats, uptime, health, community, board, peers, summary, proposals, upcoming, governance, mempool, account,
    chain: { rulesAt: h => { sync(); return rulesAt(h); }, props: () => { sync(); return ST.props; }, arrivals: n => { sync(); return B[n] ? B[n]._arrive : []; }, dropped: n => { sync(); return B[n] ? B[n]._dropped : []; }, headAt: t => { rollDay(t); return headAt(t); }, genesisTs: () => { sync(); return G; } },
    /* marks a page: the title says so, and a footer line that names the data source gets the simulation's line instead */
    mark(opts) {
      if (!ON) return;
      const o = opts || {};
      if (o.title !== false && !/^Simulation/.test(document.title)) document.title = "Simulation · " + document.title;
      const foot = o.foot === undefined ? document.querySelector("footer p") : o.foot ? document.querySelector(o.foot) : null;
      if (foot) {
        const links = [...foot.querySelectorAll("a")].filter(a => !/node\.tauhud\.com/.test(a.href));
        foot.replaceChildren(document.createTextNode("Simulation: a made-up chain that follows the documented protocol, generated in your browser and the same on every page. No real chain data. "));
        links.forEach((a, i) => { if (i) foot.append(" · "); foot.append(a); });
      }
    },
  };
})();
