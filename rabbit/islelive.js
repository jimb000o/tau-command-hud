/* What the islanders know about Tau Net today, so they can talk about it (White Rabbit Key, talk.js).
   Two readings of the relay, every five minutes, turned into plain facts that a line in talk.js can wait for:

   the wallets that walk on the island (GET node.tauhud.com/walkers, the same list walkers.js draws):
     walk        at least one real wallet (not ours, not IDNI's) was active in the last day and walks here
     walkMany    a dozen or more of them          walkFew   one to three        walkNone   none at all today
     walkNew     a newcomer: its first transaction was in the last day
     walkRule    a walker whose wallet wrote its own rule (or whose rule guards, caps, locks, picks or freezes)
     walkGuard   a walker with a guardian (its rule asks for a second signature)
     walkOwl     a night owl (most of its transactions 22:00 to 05:00 German time)    walkBird   an early bird
     walkFeeder  it fed Agorzilla     walkCat   it fed Déjà     walkHacker   No Memo crew     walkPol   it plays this game
     walkWinner  it won an island election     walkIdni   one of IDNI's genesis accounts walks (grey)
     walkBusy    fifty or more transactions in a day     walkVet   first seen two weeks ago or more
     walkBig     it moved a lot of test AGRS     walkMe    your own test wallet walks here
   the personal rules on the chain (GET node.tauhud.com/rules/numbers, tauhud.com/rules/numbers/):
     rules       at least one wallet that is not ours or IDNI's holds its own rule now
     rulesAny    any wallet holds one (our showcase wallets included)
     ruleCap ruleOnly ruleTime ruleCosign ruleFloor ruleFreeze   a wallet holds a rule of that kind (most per payment,
                 only certain receivers, a time lock, a second signature, a reserve read from the balance, nothing leaves)
     ruleOffer   a wallet offered its rule to another wallet in the blocks our relay keeps; ruleOfferTaken: one was accepted
     ruleHeld    today our node refused a payment because the sender's own rule said no
     ruleRestart the testnet started over today: every rule went with the old chain

   Nothing here is said with a number: the lines are spoken (rico.js, voices.json), so they only wait for a fact.
   No reading (offline, the simulation): no fact, and the islanders say their other lines.
   Test: ?live=demo (every fact) or ?live=walkNew,ruleHeld (just those).
   window.RABBIT_LIVE_WHEN() -> facts; .keys = every fact name (tests/voices.mjs checks talk.js against it) */
(() => {
  "use strict";
  const RELAY = "https://node.tauhud.com", EVERY = 5 * 60 * 1000;
  const KEYS = ["walk", "walkMany", "walkFew", "walkNone", "walkNew", "walkRule", "walkGuard", "walkOwl", "walkBird", "walkFeeder", "walkCat",
    "walkHacker", "walkPol", "walkWinner", "walkIdni", "walkBusy", "walkVet", "walkBig", "walkMe",
    "rules", "rulesAny", "ruleCap", "ruleOnly", "ruleTime", "ruleCosign", "ruleFloor", "ruleFreeze", "ruleOffer", "ruleOfferTaken", "ruleHeld", "ruleRestart"];
  const RULEISH = ["lawmaker", "guardian", "vault", "picky", "capped", "frozen"];
  const KIND = { cap: "ruleCap", only: "ruleOnly", time: "ruleTime", cosign: "ruleCosign", reserve: "ruleFloor", freeze: "ruleFreeze" };
  const L = { walk: {}, rule: {} };
  let Q = null;
  try { Q = new URLSearchParams(location.search).get("live"); } catch (e) {}
  const myPk = () => { try { const k = JSON.parse(localStorage.getItem("tauhud-wallet-key") || "null"); return k && k.pk ? String(k.pk).toLowerCase() : null; } catch (e) { return null; } };
  const n = v => (Number.isFinite(+v) ? +v : 0);

  function walkFacts(j) {
    const f = {}, rows = (j.walkers || []).filter(w => w && typeof w.a === "string"), people = rows.filter(w => !w.idni);
    const total = n(j.total), has = t => people.some(w => (w.traits || []).includes(t)), me = myPk();
    f.walk = total > 0; f.walkMany = total >= 12; f.walkFew = total > 0 && total <= 3; f.walkNone = total === 0;
    f.walkNew = has("newcomer"); f.walkRule = people.some(w => (w.traits || []).some(t => RULEISH.includes(t))); f.walkGuard = has("guardian");
    f.walkOwl = has("nightowl"); f.walkBird = has("earlybird"); f.walkFeeder = has("feeder"); f.walkCat = has("catfriend"); f.walkHacker = has("hacker");
    f.walkPol = has("politician"); f.walkWinner = has("winner"); f.walkIdni = n(j.idni) > 0 || rows.some(w => w.idni); f.walkBusy = has("busy");
    f.walkVet = has("veteran"); f.walkBig = has("bigspender"); f.walkMe = !!me && rows.some(w => w.a === me);
    return f;
  }
  function ruleFacts(j) {
    const f = {}, now = j.now || {}, h = now.holders || {}, k = now.kinds || {}, o = j.offers || {};
    const sum = (m, who) => who.reduce((s, w) => s + n((m || {})[w]), 0), mine = ["people", "ours"];
    f.rules = n(h.people) > 0; f.rulesAny = sum(h, ["people", "ours", "idni"]) > 0;
    for (const kind in KIND) f[KIND[kind]] = mine.some(w => n((k[w] || {})[kind]) > 0);
    f.ruleOffer = mine.some(w => n((o[w] || {}).made) > 0); f.ruleOfferTaken = mine.some(w => n((o[w] || {}).accepted) > 0);
    const days = ((j.history || {}).days) || {}, today = days[new Date().toISOString().slice(0, 10)] || {};
    f.ruleHeld = sum(today.held, ["people", "ours", "idni"]) > 0; f.ruleRestart = !!today.restart;
    return f;
  }
  async function get(path) {
    try { const r = await fetch(RELAY + path, { cache: "no-store" }); return r.ok ? await r.json() : null; } catch (e) { return null; }
  }
  async function poll() {
    if (Q || (window.TauSim && TauSim.on)) return;   // a preview, or the simulation: no real chain to talk about
    if (document.hidden && L.at) return;
    const [w, r] = await Promise.all([get("/walkers"), get("/rules/numbers")]);
    if (w && Array.isArray(w.walkers)) L.walk = walkFacts(w);
    if (r && r.now) L.rule = ruleFacts(r);
    L.at = Date.now();
  }
  function facts() {
    if (Q === "demo") return Object.fromEntries(KEYS.filter(k => !/^(walkNone|walkFew|ruleRestart)$/.test(k)).map(k => [k, true]));
    if (Q) return Object.fromEntries(Q.split(",").filter(k => KEYS.includes(k)).map(k => [k, true]));
    return Object.assign({}, L.walk, L.rule);
  }
  window.RABBIT_LIVE_WHEN = Object.assign(facts, { keys: KEYS, walkFacts, ruleFacts });
  if (typeof fetch === "function" && typeof document !== "undefined") {
    poll(); setInterval(poll, EVERY);
    document.addEventListener("visibilitychange", () => { if (!document.hidden && Date.now() - (L.at || 0) > EVERY) poll(); });
  }
})();
