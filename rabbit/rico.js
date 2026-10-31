/* The islanders' voices. Every line anyone can say aloud is fixed and listed here: Rico's lines on the radio strip
   (RICO.L) and what each islander says when you walk in (RICO.CAST). The server speaks each one once with that
   islander's voice (infra/rico/make.py) and keeps the clips at node.tauhud.com/rico/<key>.mp3, listed in index.json;
   the key is the first 16 hex of sha1("<who>|<English text>"). Numbers and block heights are never spoken, only
   shown, so a fixed set covers everything. A line whose clip is missing is simply shown as text, as before.
   rabbit/voices.json is the list the server reads (node tests/voices.mjs --write makes it; the tests check it).
   window.RICO = { L, SETS, CAST, all(), speak(parts, who), hud() }: a line is a list of parts { t: shown text, v: spoken English or null }. */
(() => {
  "use strict";
  const BASE = "https://node.tauhud.com/rico/";
  const NAMES = ["Marisol", "Tobias", "Baako", "Hana"];   // the four candidates (game.js CANDS)
  const DAYS = 5;
  const L = {
    noLaws: "No laws yet on this island. Rico's only rule: the request line is open, the coconut stand is not.",
    topLaws: "{x} has written more laws than anyone. The island has asked for a nap.",
    pact: "Pact news: {x} and {y} shook hands at La Ola. Lola counted the fingers afterwards.",
    broken: "A pact was broken. Rico won't say who. The Book already did.",
    envelope: "An embassy envelope was seen near the council. Rico saw nothing. Rico is very expensive to see things.",
    rumours: "Rumours on air this week, and the Book keeps showing them up. Rico only plays them, folks.",
    quiet: "Quiet after ten is the law now. This is Rico, whispering.",
    reef: "The reef is protected. The fish have issued a statement: blub.",
    harbour: "A deep harbour for cruise ships. Tobias has already ordered a bigger hat.",
    night: "Night market every Friday! Rico will be there selling rumours at half price. Joke. The Book is watching.",
    concerts: "Beach concerts on Sundays are law. Rico has cancelled every other plan until the election.",
    copy: "There is a copy of the Book on the square now. More readers, fewer rumours. Bad for business, good for the island.",
    night5: "The lighthouse turns green, the candidates go quiet, and the Book keeps writing. Goodnight, island.",
    day: "Day {n} of {m}. If you still don't know who to vote for, neither do the gulls.",
    fact: "Fun fact: a law that contradicts one in force is refused before anyone votes. Rico tried 'Rico plays all night' and 'Quiet after ten'. Rico lost to Rico.",
    dedicate: "This next one goes out to whoever bought last night's rumour. You know who you are. So does the Book.",
    song: "Four candidates have asked for the same song tonight. It is called 'Vote for me'.",
    warm: "Weather: warm, with scattered promises and a front of envelopes moving in from the embassies.",
    sam: "Old Sam has read the Book every night this week. The Book has not read Sam once. Respect.",
    tips: "Rico accepts tips, song requests and alibis.",
    book: "Fresh from the Book!",
    /* the chain weather comes in bands; the numbers are shown beside it */
    wxChain: "Chain weather.",
    wxSim: "Simulation weather.",
    fog: "Thick fog. No new block for over ten minutes. Rico recommends patience and a lemonade.",
    calm: "Dead calm. The last blocks came in empty. A good day for fishing.",
    breeze: "A light breeze: a few transactions in the last blocks.",
    choppy: "Choppy seas, plenty of transactions rolling in. Hold on to your hats.",
    rule: "A wallet put a new rule on itself: a little local weather of its own.",
    showers: "Forecast: showers. Transactions are waiting for the next block.",
    clear: "Forecast: clear skies, unless somebody sends something.",
    fog2: "Fog over the chain. No new block in a while. Rico is lighting the lamp and making tea.",
    calm2: "Flat sea, empty blocks. The chain is ready, the island is asleep.",
    breeze2: "Gentle traffic on the chain: a few transactions bobbing along like fishing boats.",
    choppy2: "Busy waters! Transactions stacked up like crates on the pier.",
    showers2: "Some transactions are still waiting on the pier for the next block. Bring an umbrella.",
    clear2: "Nothing waiting on the pier. Every transaction has found its block.",
    /* the first line after the page opens */
    op1: "Radio Coco, ninety-seven point three, back on the air. Rico has had his coffee, the Book has had its ink.",
    op2: "You are listening to Radio Coco, the only station broadcasting from a testnet. If something breaks, that is the point.",
    op3: "Hello island! Fresh blocks, fresh rumours, same old Rico. Stay tuned.",
    op4: "Radio Coco, live from the studio by the harbour. Tonight: politics, gossip and the latest from the chain.",
    op5: "Good to have you, listener. Turn it up, the gulls can't hear.",
    /* between the news: the island and the testnet as Rico sees them */
    g1: "Reminder: on a testnet the money is pretend and the coconuts are real. Please don't mix them up at the market.",
    g2: "A caller asks how many people use the testnet. Rico can only count wallets. One person with three wallets is a party of one.",
    g3: "Nobody mines anything on this chain. No pickaxes, no noise. Blocks are sealed by agreement, the quiet island way.",
    g4: "A transaction walks into a block. The block says: you again? The transaction says: no, that was my ghost.",
    g5: "If your transaction is late, don't panic. Blocks come in like ferries: more or less on time, and never the same one twice.",
    g6: "Studio tip: write your own rules before somebody writes them for you. On this chain a wallet can put a rule on itself, and the chain holds it to it.",
    g7: "The Book in the lighthouse and the blocks on the testnet are cousins. Neither forgets, and neither forgives a typo.",
    g8: "Testnet means you can make mistakes for free. Rico has been testing his whole life.",
    g9: "Lost and found: one private key. Just kidding. Nobody can find that for you. Keep it the way your grandmother keeps her recipes.",
    g10: "Most requested song this week: Waiting for the Next Block. Runner-up: Fee Me Tender.",
    g11: "Rico asked the chain who will win the election. The chain said: I only write down what already happened. Smart chain.",
    g12: "A law on this island and a rule on Tau have one thing in common: if it contradicts the one in force, it doesn't get in. Not even with an envelope.",
    g13: "The gulls sit on the lighthouse all day. They don't vote, they don't sign, they just watch. Perfect observers. Terrible validators: no keys.",
    g14: "Message to the candidates: everything you do is written down. Message to the listeners: get popcorn.",
    g15: "Rico put a rule on himself: no more than three mangoes a day. The mangoes are lobbying hard.",
    g16: "Late-night question: if a block is sealed and nobody is watching, is it still final? Yes. Rico checked. Call in anyway.",
    g17: "Test coins are worth nothing, and that is the beauty of it. You can't lose your shirt here, only your patience.",
    g18: "No ads on Radio Coco. The embassies keep offering. Rico keeps the envelopes closed. Mostly.",
    g19: "Old Sam reminds you: the Book is free to read. It is the only free thing on this island. Enjoy it.",
    g20: "Wallets, not people: that is how the chain sees the world. Rico finds that very restful.",
    g21: "This is the hour when the validators sign and the islanders sleep. Rico does neither.",
    g22: "Every block that comes in is like a match result: final, posted, and somebody at the bar still argues about it.",
    g23: "Some people collect stamps. The testnet collects signatures. Rico collects excuses.",
    g24: "Breaking: the black cat crossed the square twice again. The Book has both crossings. The cat has no comment.",
    /* news from the chain: what Rico just saw in the newest blocks (game.js readChain) */
    rule1: "News from the chain: a wallet just wrote itself a personal rule. Most people make New Year's resolutions. On this chain, they are enforced.",
    rule2: "A wallet tied its own hands today, on purpose. Rico tried that with chocolate once. The chain is stricter than Rico.",
    rule3: "New personal rule on the testnet. The wallet said: from now on, not like that. And the chain said: noted.",
    rule4: "Another personal rule on the chain. So far most of them came from just two wallets. Two people, or one person with a lot of coffee: the chain only sees wallets.",
    cosign1: "A co-signed transfer is on the water. The money waits on the pier until the co-signers say yes. Romance, testnet style.",
    cosign2: "Somebody sent money that needs a second signature. Trust, but sign twice.",
    cosvote: "A co-signer has spoken. Somewhere on the testnet a transfer is either sailing or staying home.",
    lock1: "Someone sent money on a string: until its release, at a block or a time, the sender can still pull it back. Rico calls that a boomerang with a timer.",
    lock2: "A retractable transfer went out. The receiver may look, but not touch. Not yet.",
    back1: "And the boomerang came back! A sender pulled a transfer back before its release. The receiver is now staring at the sea.",
    back2: "Pulled back! A transfer went home before it was released. On this island we call that changing your mind in public.",
    offer: "A rule offer is on the table. Nothing binds until the other side says yes. Like a marriage, with fewer cakes.",
    offerYes: "Rule offer accepted! Two wallets agreed on a rule. Lola says that is more than most couples manage.",
    law1: "The validators put a network rule change on the table. If it is like the last few dozen, it proves once again that a times b is b times a. Rico checked on his fingers. Still true.",
    law2: "Another network rule change out there. The ones Rico has read so far changed nothing at all: rehearsals, not revolutions.",
    lawSim: "On the simulated chain the validators have a new rule change on the table. Rico will tell you if the sea changes colour.",
    lawVote: "Validator votes are coming in. On this chain the rules change only when enough validators agree. On this island, when Lola runs out of lemonade.",
    refusedLaw: "Somebody proposed a network rule that contradicts the rules in force. Turned away at the door, before anyone voted. Just like the Book does with our laws.",
    refusedOwn: "A wallet just tried to break its own rule. The chain said no, the way a lighthouse says no to a rock.",
    refused: "The chain turned a transaction away at the door. The numbers didn't add up. No drama, no appeal, next please.",
    burst1: "A wave of transactions just hit the beach! Somebody out there is either testing very hard or very happy.",
    burst2: "Rush hour on the chain! Full blocks, a busy pier, and Rico is impressed.",
    ghost1: "Ghost report from the harbour: transactions already sealed in a block, but still listed as waiting. The node hasn't noticed they left. Old Sam calls them guests who never go home.",
    ghost2: "Spooky! The waiting list still shows transactions that are already in a block. Ghosts. Harmless, says the Book. Rico sleeps with the light on anyway.",
    ghost3: "The ghosts are back on the waiting list. A known bug, reported to the builders. Rico has put out a lemonade for them.",
    toStake: "Big news on the simulated chain: the validators are voting to switch consensus to proof of stake. Whoever holds the most would seal the blocks. Rico is counting his coconuts.",
    toFixed: "Simulation flash: a vote to go back to the fixed validator list. The stakers would hand back their seats and the old guard returns. Like after every island revolution, only with fewer hats.",
    nowStake: "It's done! The simulated chain now runs on proof of stake. No tanks, no coup, just votes and a block height. Rico is almost disappointed.",
    nowFixed: "It's done: the simulation is back on the fixed validator list. Not one cannon fired. Boring for radio, beautiful for a chain.",
    midnight: "The simulated chain starts over in a few minutes, back at block one. Finish your drinks.",
    restart: "The chain has started over at block one. Same sea, fresh logbook.",
  };
  /* which lines can stand in for each other: Rico picks one he has not said lately (game.js remembers what he said) */
  const SETS = {
    open: ["op1", "op2", "op3", "op4", "op5"],
    general: Array.from({ length: 24 }, (_, i) => "g" + (i + 1)),
    fog: ["fog", "fog2"], calm: ["calm", "calm2"], breeze: ["breeze", "breeze2"], choppy: ["choppy", "choppy2"], showers: ["showers", "showers2"], clear: ["clear", "clear2"],
    rule: ["rule1", "rule2", "rule3", "rule4"], cosign: ["cosign1", "cosign2"], cosvote: ["cosvote"], lock: ["lock1", "lock2"], back: ["back1", "back2"],
    offer: ["offer"], offerYes: ["offerYes"], law: ["law1", "law2"], lawSim: ["lawSim"], lawVote: ["lawVote"],
    refusedLaw: ["refusedLaw"], refusedOwn: ["refusedOwn"], refused: ["refused"], burst: ["burst1", "burst2"], ghost: ["ghost1", "ghost2", "ghost3"],
    toStake: ["toStake"], toFixed: ["toFixed"], nowStake: ["nowStake"], nowFixed: ["nowFixed"], midnight: ["midnight"], restart: ["restart"],
  };
  /* what the islanders say in the places (the same English as in game.js, which the tests check) */
  const LAWT = { harbour: "A deep harbour for cruise ships", road: "A road round the island" };
  const EMBV = { frost: ["harbour", 40], salado: ["road", 35] };
  const CAST = [
    ["hana", "Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."],
    ["sam", "Sam keeps the minutes today. Pick a law; the other three candidates vote, two yes and it is law."],
    ["lola", "Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."],
    ["rico", "Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time."],
    ["lola", "A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house."],
    ["sam", "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing."],
    ["sam", "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."],
    ["sam", "Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks."],
    ["sam", "Three moves a day, five days, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."],
    ["sam", "Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law."],
    ["rico", "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me."],
    ["rico", "Done. And this one’s true, so let them check. The Book backs you up."],
    ["rico", "This just in on Radio Coco, ninety-seven point three!"],
    ...NAMES.map(n => n.toLowerCase()).flatMap(c => [[c, "Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory."], [c, "After what you did? Buy yourself a lemonade."], [c, "Not today. Show me how you vote first."]]),
    ...Object.entries(EMBV).flatMap(([who, [law, n]]) => [[who, `We are counting on you for “${LAWT[law]}”. We would hate to remind the island in public.`], [who, `${n} coins, today. All we ask is that you propose “${LAWT[law]}” before the election. A small thing between friends.`]]),
  ];
  /* what Rico can put on air: the four rumours that are not true, and the true things the Book has seen */
  const LIES = ["Marisol fishes inside the reef at night", "Tobias wants to sell the lighthouse", "Baako’s coconuts are imported", "Hana wants school on Sundays"];
  const EMBN = { "North Wind Embassy": 40, "South Current Embassy": 35 };
  const CLAIMS = [...LIES, ...NAMES.flatMap(x => [...Object.entries(EMBN).map(([y, n]) => `${x} took ${n} coins from the ${y}`), ...NAMES.filter(y => y !== x).map(y => `${x} paid for the rumour about ${y}`), `${x} broke a pact`])];
  CLAIMS.forEach(c => CAST.push(["rico", c + "!"]));
  const fill = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  /* every line anyone can speak, as [who, English]: the server makes one clip for each */
  function all() {
    const out = [];
    for (const [k, s] of Object.entries(L)) {
      if (k === "topLaws") NAMES.forEach(x => out.push(fill(s, { x })));
      else if (k === "pact") NAMES.forEach(x => NAMES.forEach(y => x !== y && out.push(fill(s, { x, y }))));
      else if (k === "day") for (let n = 1; n <= DAYS; n++) out.push(fill(s, { n, m: DAYS }));
      else out.push(s);
    }
    return [...out.map(t => ["rico", t]), ...CAST];
  }

  /* the clips the server has made so far */
  let have = null;
  const ready = fetch(BASE + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null))
    .then(j => { have = new Set((j && j.clips) || []); }, () => { have = new Set(); });
  async function key(who, s) {
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + s));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }
  const cache = new Map();
  const clip = k => { if (!cache.has(k)) cache.set(k, fetch(BASE + k + ".mp3").then(r => (r.ok ? r.arrayBuffer() : null), () => null)); return cache.get(k); };
  /* speak a line in someone's voice: all its spoken parts, in order, or nothing at all when one clip is missing */
  async function speak(parts, who = "rico") {
    const SND = window.COVE_SOUND;
    if (!SND || !SND.on || !SND.speak || !window.crypto || !crypto.subtle) return false;
    await ready;
    const keys = await Promise.all(parts.filter(p => p.v).map(p => key(who, p.v)));
    if (!keys.length || !keys.every(k => have.has(k))) return false;
    const bufs = await Promise.all(keys.map(clip));
    if (bufs.some(b => !b)) return false;
    return SND.speak(bufs.map(b => b.slice(0)));
  }
  /* lines that make sense away from the game (the radio in the site header, assets/radio.js): the hellos and Rico's
     testnet humour, without the ones about the election. Each is a parts list, shown translated where the page has it. */
  const tr = s => (window.TauI18n ? TauI18n.t(s) : s);
  const hud = () => [...SETS.open, ...SETS.general.filter(k => k !== "g11" && k !== "g14")].map(k => [{ t: tr(L[k]), v: L[k] }]);
  window.RICO = { L, SETS, CAST, NAMES, all, speak, fill, key, hud };
})();
