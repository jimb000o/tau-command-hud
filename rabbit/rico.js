/* Rico's voice on Radio Coco. Every line Rico can say aloud is fixed and listed here (RICO.L), so the server can
   speak each one once with a voice from the ElevenLabs account (infra/rico/make.py) and keep the clips at
   node.tauhud.com/rico/<sha1 of the English text, 16 hex>.mp3, listed in index.json. Numbers and block heights are
   never spoken, only shown, so a small fixed set covers everything. A line whose clip is missing is simply shown
   as text, as before.
   window.RICO = { L, all(), speak(parts) }: a line is a list of parts { t: shown text, v: spoken English or null }. */
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
  const fill = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  /* every English text Rico can speak: the server makes one clip for each */
  function all() {
    const out = [];
    for (const [k, s] of Object.entries(L)) {
      if (k === "topLaws") NAMES.forEach(x => out.push(fill(s, { x })));
      else if (k === "pact") NAMES.forEach(x => NAMES.forEach(y => x !== y && out.push(fill(s, { x, y }))));
      else if (k === "day") for (let n = 1; n <= DAYS; n++) out.push(fill(s, { n, m: DAYS }));
      else out.push(s);
    }
    return out;
  }

  /* the clips the server has made so far */
  let have = null;
  const ready = fetch(BASE + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null))
    .then(j => { have = new Set((j && j.clips) || []); }, () => { have = new Set(); });
  async function key(s) {
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }
  const cache = new Map();
  const clip = k => { if (!cache.has(k)) cache.set(k, fetch(BASE + k + ".mp3").then(r => (r.ok ? r.arrayBuffer() : null), () => null)); return cache.get(k); };
  /* speak a line: all its spoken parts, in order, or nothing at all when one clip is missing */
  async function speak(parts) {
    const SND = window.COVE_SOUND;
    if (!SND || !SND.on || !SND.speak || !window.crypto || !crypto.subtle) return false;
    await ready;
    const keys = await Promise.all(parts.filter(p => p.v).map(p => key(p.v)));
    if (!keys.length || !keys.every(k => have.has(k))) return false;
    const bufs = await Promise.all(keys.map(clip));
    if (bufs.some(b => !b)) return false;
    return SND.speak(bufs.map(b => b.slice(0)));
  }
  window.RICO = { L, NAMES, all, speak, fill };
})();
