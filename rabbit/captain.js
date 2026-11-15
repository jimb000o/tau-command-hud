/* White Rabbit Key: the captains of the cruise ships, aboard while a ship is in (game.js aboard()).
   Each ship has a captain who talks like a live broadcast about what her or his ship is testing on Tau Testnet Alpha
   right now, from the relay's real data (GET /cruise: the ship in port; GET /cruise/log?visit=: its logbook), and why
   that test matters. The captains are characters, and so are their passengers: every captain says so first. What the
   passengers send is real. A trick that got through is held back by the relay (cruise.py public()), so no captain
   ever names one: they only say that something was held back and reported privately first.

   Every line is { s: English text with {placeholders}, v: values }; game.js shows it with F() (translated through
   assets/i18n/<lang>/rabbit.js) and never voices it (no clips yet). No DOM here: tests/captain.mjs loads this file
   in Node and checks every line for its facts and its translations. */
(() => {
  "use strict";
  /* the three captains: who they are, how they look (game.js draws them like the islanders until painted busts exist) */
  const CAPTAINS = {
    pirates: { id: "scarlett", name: "Captain Scarlett Nonce", role: "Black Sequence, pirate captain (a made-up character)",
      look: { skin: "#c68642", hair: "#8a1f1a", style: "curls", acc: "scarf", accC: "#b3202a", shirt: "#1f2428" },
      head: { w: 22, h: 27, jaw: 0.5, nose: "hook", bg: "#3a3f45" } },
    dryrun: { id: "lindqvist", name: "Captain Ingrid Lindqvist", role: "MS Dry Run, expedition captain (a made-up character)",
      look: { skin: "#f3d6c0", hair: "#e6d6a0", style: "bun", acc: "glasses", accC: "#333", shirt: "#2f5468" },
      head: { w: 20, h: 29, jaw: 0.3, nose: "straight", bg: "#4fa3a0" } },
    queen: { id: "fairweather", name: "Commodore Augustus Fairweather", role: "Queen Mempool, commodore (a made-up character)",
      look: { skin: "#e0b08a", hair: "#e4e4e4", style: "side", acc: "mustache", accC: "#e4e4e4", shirt: "#f4f1ea" },
      head: { w: 26, h: 29, jaw: 0.85, nose: "round", bg: "#1f3550" } },
  };
  /* the pirates of the Black Sequence by number (the relay's passenger p): made up like the rest of the crew */
  const CREW = ["One-Eyed Piet", "Mags", "Barnaby Bilge", "Little Oskar", "Tilly Two-Hooks", "Grog", "Salty Ines", "Fenwick", "Old Jory",
    "Rosa the Rat", "Dutch", "Polly", "Hamish", "Nell", "Crooked Kit", "Bosun Bea", "Ziggy", "Moll", "Quill", "Cookie"];
  const L = (s, v) => ({ s, v: v || null });

  /* ---------- the first thing each captain says aboard: who they are, and that they are made up ---------- */
  const HELLO = {
    pirates: "Ahoy! Scarlett Nonce, captain of the Black Sequence. Let me be straight, since nothing else about me is: I'm made up, my crew is made up, our relay steers the lot of us. But every trick we try goes to Tau Testnet Alpha for real, and the chain has to say no. That's the show. Pull up a barrel.",
    dryrun: "Welcome aboard MS Dry Run. Ingrid Lindqvist. For the record: I am a character, and so are my forty passengers; our relay plays all of us. The transactions are not made up. Each one is real, on Tau Testnet Alpha. This ship exists to try the rarer kinds of transaction before anybody needs them.",
    queen: "Augustus Fairweather, Commodore of the Queen Mempool. Welcome to the ballroom. A confession before the music: I am fiction, and so are my hundred and twenty guests; the relay plays us all. What is real is every payment they make ashore, on Tau Testnet Alpha. My ship brings what the others don't: volume.",
  };

  /* ---------- why each test matters: the captain's own words, between the news ---------- */
  const MEANING = {
    pirates: [
      "Here's why a pirate ship is on a timetable: a payment network is only as good as its no. Paying money you don't have, paying twice with one payment, signing for someone else: if one of those ever got through, no wallet would be safe.",
      "Every refusal comes with a reason code. That code is the chain explaining itself. Same trick, same answer, every single time: that's what you want from a rulebook.",
      "Fancy trying the tricks yourself? While we're in port, my Quartermaster hands out live contracts at the crew terminal in No Memo. Type op. Real transactions, same chain, and the chain says no to you too.",
      "If a trick ever gets through, you won't hear me crow about it here. It's held back and reported privately to the team behind the testnet first. That's how you treat a hole you find in somebody else's hull.",
      "Some of the chain's no's are plain checks: signature, sequence number, balance. Others come from rules written in Tau: the network's fee rule, and the personal rules wallets set for themselves. My crew pokes at both. Each time we fail, the rules are worth a little more.",
    ],
    dryrun: [
      "Why a dry run: a booking with the right to withdraw is a different kind of transaction from a plain payment. Better to find its rough edges on a Wednesday with made-up passengers than later with real money.",
      "We note how long our node takes to answer every send. An average would lie: on 10 November half the answers came in 0.4 seconds and the other half in 5 to 8. So the plan is made for the slow half.",
      "Hypothesis for every booking: at its hour it either pays the place or has gone back to the passenger. There is no third outcome. After the visit we look each one up on the chain, and the logbook says which.",
      "A booking waits in escrow on the chain itself: not with me, not with the dive shop. At its time the chain pays the place by itself. Only the passenger who booked can take it back, and only before that time.",
    ],
    queen: [
      "Volume is a question, not a boast. How many payments a minute can the testnet seal while real visitors still get through? We never take more than half of the island's daily budget to find out.",
      "Twelve a minute at most, and only in the island bot's free slots. The real players always go first. A good host never lets the band drown out the guests.",
      "When the testnet strains, we dance at half tempo. When it stalls, every guest goes back aboard at once and I write an incident report. I would rather leave early than be the reason the music stopped.",
      "One bill, three tills: a table at Bar La Ola pays the bar, Radio Coco and the Coconut Works in a single transaction. One signature, one transaction, three tills paid.",
    ],
  };

  /* ---------- the pirates' tricks: what each one tries, and why the chain's no matters ---------- */
  const TRICK = {
    overspend: ["{x} tries to pay more than the wallet holds.", "Nobody pays with money they don't have. The very first thing a ledger has to get right."],
    replay: ["{x} sends a payment the chain already took, a second time.", "Anyone who sees a signed payment can copy it. The sequence number makes it count once. Otherwise a till could charge you as often as it liked."],
    expired: ["{x} sends a payment whose time ran out.", "Every payment carries an expiry. A signed payment found in a drawer next year is worth nothing."],
    stale: ["{x} sends a payment after its block deadline.", "A deadline can be counted in blocks too, by the chain itself, so no clock can be argued with."],
    forged: ["{x} signs a payment with another pirate's key.", "The signature must belong to the wallet that pays. Only the key holder can spend."],
    impostor: ["{x} pays from another pirate's wallet with a signature of their own.", "Signing well is not enough: you can only sign for your own wallet. Your key can't move anybody else's money."],
    freeride: ["{x} allows no fee at all.", "Every payment must allow a fee. A network that carries payments for free can be flooded for free."],
    giant: ["{x} tries to pay more than one transfer can carry.", "A transfer has a ceiling written into the rules. A limit in the rules beats a surprise in the code."],
    double: ["{x} sends two different payments with the same sequence number at once.", "Two payments, one number: only one may ever count. That's double spending, the oldest trick at sea."],
    poison: ["{x} pays several places in one payment, and the last part is more than the wallet holds.", "The chain refuses the whole payment. Nobody gets paid half a bill."],
    cram: ["{x} packs more transfers into one payment than it may carry.", "The chain caps how many one payment may carry, so no single payment can grow without limit."],
    governance: ["{x} sends a payment with a field only the chain's own transactions may set.", "A wallet can't dress up as the network."],
    taxman: ["{x} submits a fee rule that would tax every wallet's transfers, not only their own.", "A personal rule binds its own wallet and nobody else's. That's the line between your rules and everybody's rules."],
    stranger: ["{x} tries to take back another pirate's booking.", "Only the one who booked can take it back. Not a shipmate, not even the captain."],
    phantom: ["{x} tries to take back a booking the chain never had.", "The chain only knows what it sealed. You can't withdraw a ghost."],
    late: ["{x} tries to take back a booking after its time.", "Once the hour has passed, the place is paid. The right to withdraw has a deadline, and the chain keeps it."],
    edge: ["{x} allows one test AGRS less fee than the network's fee rule asks for that very payment.", "One coin short: refused. Right after, the same payment with the exact fee has to go through. That's a rule read to the coin."],
    selfrule: ["{x} sends a rule for their own wallet and a coin in the same payment.", "Rules and coins travel separately, so each one stays simple to check."],
    mixrule: ["{x} writes a rule that mixes their own policy with the chain's own fee stream.", "Your rules are about your wallet, never about the network's income."],
    bigclause: ["{x} offers a rule with more comparisons than one clause may carry.", "One clause may carry at most 32. A rule stays cheap to check, for every node."],
  };
  const SCARLETT = ["Ha! {x} Refused: {r}. {y}", "Watch this. {x} And the chain says {r}. {y}", "There it goes. {x} Answer: {r}. I'll add it to my list. {y}"];

  /* ---------- the logbook's news, in each captain's words ---------- */
  function who(ship, p) {
    if (ship === "pirates") return CREW[(Number(p) || 0) % CREW.length];
    return null;
  }
  /* one logbook entry (relay cruise.py write) as a line, or null when it is nothing to talk about */
  function event(ship, e, ctx) {
    const at = id => ctx.place(id), ms = Number(e.ms) || 0;
    if (e.held || e.route === "held") return L({ pirates: "That one I'm not allowed to talk about yet. Held back, and reported privately to the team behind the testnet first. You'll read it in the logbook once it's released.",
      dryrun: "One result is held back: reported privately to the team behind the testnet first. The logbook will show it once it is released.",
      queen: "A small matter is held back, reported privately to the team behind the testnet first. Discretion, my dear. The logbook shows it once it is released." }[ship] || "Held back: reported privately first.");
    if (e.kind === "trick" && e.stopped && TRICK[e.trick]) {
      const [what, why] = TRICK[e.trick], k = (Number(e.i) || 0) % SCARLETT.length;
      return L(SCARLETT[k], { x: what.replace("{x}", who(ship, e.p) || "A pirate"), r: e.code || "refused", y: why });
    }
    if (e.kind === "trick" && e.stopped) return L("A pirate tried something new: {x}. The chain said {r}. Refused.", { x: e.what || "a trick", r: e.code || "no" });
    if (e.new_wallet) return L({ pirates: "Some of my crew stay aboard today: our own node is full up with wallet addresses and can't take new ones. Not the chain's fault, a limit of our node. They'll try again next visit.",
      dryrun: "Observation: a few passengers stay aboard. Our node can hold only so many wallet addresses, and theirs are new to it. That is our node's limit, noted, not a refusal.",
      queen: "Some guests remain aboard: our node keeps only so many wallet addresses, and theirs are new. Our limit, not the chain's. They will dance next time." }[ship] || null);
    if (e.ok === null && /no answer/.test(e.note || "")) return L({ pirates: "Our node went quiet on a send. That's on our side, not the chain's. We hold for a moment and go at half pace.",
      dryrun: "No answer from our node in time. On our side of the line, so we wait, then go at half pace for a while. Noted in the log.",
      queen: "Our node missed a beat. Our side of the room, not the chain's. We pause, then dance at half tempo for a while." }[ship] || null);
    if (e.ok === false && e.kind !== "trick") return L({ pirates: "One of our honest payments was refused: {r}. If five of the last twenty get refused, we weigh anchor at once.",
      dryrun: "A {x} was refused by the node: {r}. The rule: five refusals in the last twenty sends and we leave at once. The logbook keeps the signed transaction for anyone to check.",
      queen: "A guest's {x} was refused: {r}. Five in the last twenty, and the whole party goes back aboard. A rule, not a mood." }[ship], { x: { pay: "payment", bill: "group bill", book: "booking", cancel: "withdrawal" }[e.kind] || "transaction", r: e.code || "refused" });
    if (e.ok !== true) return null;
    const amt = Number(e.amount) || 0;
    if (e.kind === "book") return L({ dryrun: "A passenger just booked at {x} for {t}: {n} test AGRS now wait in escrow. At {t} the chain pays {x} by itself. Nobody has to remember. That is the experiment.",
      queen: "A guest booked a treatment at {x} for {t}: {n} test AGRS in escrow, paid out by the chain itself at {t}." }[ship] || "A booking at {x} for {t}: {n} test AGRS in escrow.",
      { x: at(e.to), t: e.release_at_time ? ctx.time(e.release_at_time) : "its hour", n: amt });
    if (e.kind === "cancel") return L({ dryrun: "A passenger changed their mind and took the booking back. Only they could, and only before its hour. The money is back in their wallet. Withdrawal works: noted.",
      queen: "A guest cancelled their treatment. Only the one who booked may, and only before its hour. The money went straight back. Elegant." }[ship] || "A booking was taken back before its hour.");
    if (e.kind === "bill") return L("A table at Bar La Ola just paid one bill: the bar, Radio Coco and the Coconut Works, all in one transaction. One signature, three tills.");
    if (e.kind === "pay") return ms && ship === "dryrun" ? L("Measurement: {n} test AGRS paid at {x}, our node answered in {a} ms.", { n: amt, x: at(e.to), a: ms })
      : ship === "queen" ? L("A guest paid {n} test AGRS at {x}. Our node answered in {a} ms.", { n: amt, x: at(e.to), a: ms })
      : L("{x} bought supplies: {n} test AGRS at {y}. Honest money, now and then. Keeps the chain guessing.", { x: who(ship, e.p) || "A pirate", n: amt, y: at(e.to) });
    if (e.kind === "chain restarted") return L("The whole testnet started over from block one. The logbook notes it, so nobody mistakes it for a stall.");
    if (e.kind === "escrow" && e.status === "settled") return L("Every booking ahead of this call is looked up on the chain now: paid out to the till, or refunded to the passenger. The logbook has each one.");
    return null;
  }
  const RARE = { trick: 3, book: 3, cancel: 3, bill: 2, "chain restarted": 3, escrow: 2 };
  /* how much a captain wants to talk about an entry: tricks, bookings and refusals before plain payments */
  const weight = e => e.held ? 3 : e.ok === false || e.new_wallet || (e.ok === null && /no answer/.test(e.note || "")) ? 3 : RARE[e.kind] || 1;

  /* ---------- where the visit stands (relay GET /cruise now) ---------- */
  function status(ship, v, load, ctx) {
    const out = [], S = v.sent || {}, sent = Object.values(S).reduce((a, b) => a + (Number(b) || 0), 0), ph = v.phase;
    if (ph === "approach") out.push(L({ pirates: "We drop anchor at {t}, German time. Nobody on the island was told we'd come. That's what an inspection is for.",
      dryrun: "We land at {t}, German time. Forty passengers, each with a test wallet our relay made. On the plan: plain payments, and bookings with the right to withdraw.",
      queen: "The Queen lands at {t}, German time, with {n} guests. The tenders bring them in waves over thirty minutes, so the island never meets all of them at once." }[ship], { t: ctx.time(v.t0), n: v.passengers }));
    else if (ph === "waiting") out.push(L("We wait off the reef. We land only on a calm or busy testnet, and if it doesn't calm down within ten minutes, we sail on. A test that floods a struggling network teaches you nothing new."));
    else if (ph === "landing") out.push(L({ pirates: "Anchor's down. My crew stays aboard and trades from the boat: rum from Bar La Ola, supplies from the market. And the odd trick.",
      dryrun: "The tenders are taking them ashore now: the lighthouse, the Old Ship, the school, the dive shop. Every stop is a real transaction to that place's till.",
      queen: "The guests come ashore in waves. The South Current spa, Bar La Ola, a song request on Radio Coco: every stop a real transaction to that place's till." }[ship]));
    else if (ph === "boarding") out.push(L({ pirates: "Last ten minutes. Barrels in, ropes up. Nothing new gets tried now.", dryrun: "Last ten minutes: everyone back aboard. No more stops; the log stays open.",
      queen: "The last dance. Guests back aboard, and not a single new payment from here on." }[ship]));
    else if (ph === "gone") out.push(L(v.why === "no landing" ? "We sailed on without landing: the testnet was not calm. That's the rule."
      : v.why === "refused" ? "We left early: the node refused too many of our transactions, so we took everyone back at once. The logbook says which, and why."
      : v.why === "stalled" ? "We left early: the testnet stalled, and we took everyone back at once. The incident report has the last transactions before it."
      : "That's the visit. Everything we sent is in the logbook."));
    if (/^(landing|ashore|boarding)$/.test(ph)) {
      if (ship === "pirates") out.push(L("{n} tricks refused by the chain so far today. Every one with an answer. I keep the list; the chain keeps the score.", { n: (v.tricks || {}).stopped || 0 }));
      else out.push(L("{a} of {b} passengers ashore. {n} transactions sent so far, {m} refused by the node.", { a: v.ashore || 0, b: v.passengers, n: sent, m: v.refused || 0 }));
      if (v.brake === "half") out.push(L({ pirates: "The testnet is straining, so we go at half pace. Even pirates don't kick a ship that's already listing.", dryrun: "The testnet is straining: half pace. A stress test must never be the stress.",
        queen: "The testnet is straining, so we dance at half tempo until it breathes again." }[ship]));
      else if (v.brake === "slow") out.push(L("Our own node was slow to answer, so we go at half pace for a while. Our side of the line, not the chain's."));
      else if (v.per_min) out.push(L("Our pace today: at most {n} transactions a minute, and only when the island's own players have nothing to send.", { n: v.per_min }));
    }
    if (load && load.state && /^(landing|ashore|boarding|waiting)$/.test(ph)) out.push(L("The testnet right now: {x}. {n} transactions waiting, {m} sealed in the last hour.", { x: load.state, n: load.waiting || 0, m: load.sealed || 0 }));
    return out;
  }

  /* ---------- after a visit: what it showed, and what changed for the next call (relay last_of[ship]) ---------- */
  function debrief(ship, s, ctx) {
    if (!s) return [L("No visit in the logbook yet. Come back after the next call.")];
    const out = [L("Recorded after our last call, {x}, {t} German time.", { x: ctx.day(s.t0), t: ctx.time(s.t0) })];
    const S = s.sent || {}, sent = Object.values(S).reduce((a, b) => a + (Number(b) || 0), 0), R = s.refused || {}, refused = Object.values(R).reduce((a, b) => a + (Number(b) || 0), 0);
    if (!s.landed) out.push(L("We didn't land: the testnet wasn't calm. Sailing on is part of the test."));
    else if (ship === "pirates") {
      const T = s.tricks || {}, stopped = Object.values(T).reduce((a, c) => a + (c && !c.held ? Number(c.stopped) || 0 : 0), 0), kinds = Object.keys(T).filter(k => T[k] && !T[k].held && T[k].stopped).length;
      out.push(L("{n} tricks, {m} kinds of them, and the chain refused every one it was shown with the right answer. My list keeps growing. So does my respect.", { n: stopped, m: kinds }));
      if (Object.values(T).some(c => c && c.held)) out.push(L("One result is still held back: reported privately to the team behind the testnet first."));
    } else out.push(L("{n} transactions sent, {m} refused by the node, {a} stops skipped.", { n: sent, m: refused, a: Number(s.skipped) || 0 }));
    if (s.unanswered) out.push(L("{n} sends got no answer from our node in time. Our side of the line: noted, and the pace follows it.", { n: s.unanswered }));
    if (s.left_out) out.push(L("{n} passengers stayed aboard: our node couldn't take their new wallets. Our node's limit, not the chain's.", { n: s.left_out.passengers }));
    for (const c of (s.changed || []).slice(0, 2)) {
      if (c.held) continue;
      out.push(L("For the next call: {x}, from {y} to {z}. Because {w}.", { x: c.what, y: String(c.from), z: String(c.to), w: c.because || "the last visit showed it" }));
    }
    if (!(s.changed || []).length) out.push(L("Nothing changed for the next call: the same plan, the same limits."));
    return out;
  }

  /* ---------- questions a visitor can ask the captain: fixed answers, checked against cruise.py ---------- */
  const ASKS = [
    { q: "Are your passengers real people?", a: {
      pirates: "Not one. Twenty pirates, all invented by our relay, each with a test wallet whose key never leaves our server. The tricks are real transactions, though, and the chain's answers are real.",
      dryrun: "No. Forty characters, made up by our relay, each with a test wallet. What they send is real, which is the only part that matters for the test. Every page that shows them says so.",
      queen: "Heavens, no. A hundred and twenty invented guests. Their payments, however, are perfectly real test transactions on Tau Testnet Alpha. The guests are a costume; the load is not." } },
    { q: "Why does this test matter for Tau Net?", a: {
      pirates: "A chain that runs rules has to refuse what breaks them, every time, with a reason. My crew tries the classic ways to cheat a ledger. Every refusal is evidence that the rules hold.",
      dryrun: "New kinds of transaction break in new ways. Bookings in escrow, withdrawals, deadlines: we try each one small and slow first, five at most on its first visit, and only then in full.",
      queen: "A network that works for ten payments may wobble at a thousand. We bring steady, measured volume, write down how our node answers, and stop the moment the testnet strains too hard." } },
    { q: "What if the testnet stalls while you're here?", a: {
      pirates: "Then we leave at once, and the logbook writes an incident report: the last transactions before it, the newest block. If we broke something, we want to know exactly what.",
      dryrun: "We leave at once. The incident report lists the last fifty logbook entries, the newest block and the one that waited longest. If it was us, the log shows it. If it wasn't, it shows that too.",
      queen: "Everyone back aboard, immediately. An incident report follows: what we sent last, the newest block, what waited longest. A good host knows when to leave the party." } },
    { q: "Has a trick ever got through?", only: "pirates", a: {
      pirates: "If one does, you won't hear it from me first. It's held back from the public logbook and reported privately to the team behind the testnet. The count you see aboard is only what the chain refused." } },
    { q: "What is escrow, really?", only: "dryrun", a: {
      dryrun: "Money that waits on the chain for a set time. Nobody holds it. At that time the chain pays the place by itself. Before it, the one who booked can take it back. It is a promise with a built-in deadline." } },
    { q: "Why not send a million at once?", only: "queen", a: {
      queen: "Because a flood tells you only that floods are bad. Twelve a minute at most, half pace when it strains, never more than half the island's daily budget: measured load teaches you where the limits are without hurting anyone else on the testnet." } },
  ];
  const asks = ship => ASKS.filter(a => !a.only || a.only === ship).map(a => ({ q: a.q, a: a.a[ship] }));

  /* ---------- a preview (?ship=…): a made-up logbook, so the broadcast can be seen without a ship in port ---------- */
  function previewLog(ship, now) {
    const t = Math.floor(now), out = [];
    if (ship === "pirates") {
      ["overspend", "replay", "forged", "taxman", "double", "late"].forEach((k, i) => out.push({ t: t - i * 40, kind: "trick", trick: k, stopped: true, ok: false, i, p: i * 3,
        code: { overspend: "INSUFFICIENT_FUNDS", replay: "INVALID_SEQUENCE", forged: "INVALID_SIGNATURE", taxman: "UNSCOPED_USER_RULE", double: "INVALID_SEQUENCE", late: "RETRACT_TOO_LATE" }[k] }));
      out.push({ t: t - 260, kind: "pay", ok: true, p: 4, to: "bar", amount: 5, ms: 620 });
    } else if (ship === "dryrun") {
      out.push({ t: t - 10, kind: "book", ok: true, to: "dive", amount: 12, release_at_time: t + 1800, ms: 540 }, { t: t - 60, kind: "pay", ok: true, to: "ship", amount: 3, ms: 410 },
        { t: t - 120, kind: "cancel", ok: true, to: "book", amount: 2, ms: 6800 }, { t: t - 180, kind: "pay", ok: null, note: "no answer from the node to sendtx" });
    } else {
      out.push({ t: t - 10, kind: "bill", ok: true, to: "bar", amount: 34, ms: 480 }, { t: t - 50, kind: "pay", ok: true, to: "south", amount: 20, ms: 390 },
        { t: t - 90, kind: "book", ok: true, to: "south", amount: 20, release_at_time: t + 2400, ms: 700 }, { t: t - 140, kind: "pay", ok: true, to: "radio", amount: 25, ms: 5200 });
    }
    return out;
  }

  const api = { CAPTAINS, CREW, HELLO, MEANING, TRICK, SCARLETT, ASKS, hello: ship => L(HELLO[ship]), meaning: ship => (MEANING[ship] || []).map(s => L(s)),
    event, weight, status, debrief, asks, previewLog };
  if (typeof window !== "undefined") window.RABBIT_CAPTAIN = api;
  if (typeof module !== "undefined") module.exports = api;
})();
