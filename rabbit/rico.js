/* The islanders' voices. Every line anyone can say aloud is fixed and listed here: Rico's lines on the radio strip
   (RICO.L) and what each islander says when you walk in (RICO.CAST). The server speaks each one once with that
   islander's voice (infra/rico/make.py) and keeps the clips at node.tauhud.com/rico/<key>.mp3, listed in index.json;
   the key is the first 16 hex of sha1("<who>|<English text>"). Numbers and block heights are never spoken, only
   shown, so a fixed set covers everything. A line whose clip is missing is simply shown as text, as before.
   rabbit/voices.json is the list the server reads (node tests/voices.mjs --write makes it; the tests check it).
   window.RICO = { L, CAST, all(), speak(parts, who) }: a line is a list of parts { t: shown text, v: spoken English or null }. */
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
    breeze: "A light breeze, a few txs in the last blocks.",
    choppy: "Choppy seas, plenty of txs rolling in. Hold on to your hats.",
    rule: "A wallet put a new rule on itself: a little local weather of its own.",
    showers: "Forecast: showers, txs are waiting for the next block.",
    clear: "Forecast: clear skies, unless somebody sends something.",
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
  window.RICO = { L, CAST, NAMES, all, speak, fill, key };
})();
