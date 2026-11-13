/* Where a testnet transaction comes from, as far as we know it (tauhud.com's chain core, and any page that wants it).
   Read from the transaction itself and from our relay, never guessed:
     - the sender is one of the accounts the testnet started with (IDNI's genesis), or
     - the sender is one of our own server wallets (White Rabbit Key's island bot and purses, simulated cruise passengers,
       the three showcase wallets with their personal rules: GET /showcase, named one by one with TauOrigin.name), or
     - the transaction pays an address of an app we know (Agorzilla, Déjà the café cat, White Rabbit Key's council, tills, ballot boxes), or
     - the sender did one of those before (relay GET /wallets/tags, walletdays.py; built from the public blocks only).
   Our own server wallets also come straight from GET /island (wallets, purses) and GET /cruise (wallets).
   A waiting transaction (getmempool) carries no recipient, so there only the sender counts.
   Anything else is "not known": a key is not a person, and an unknown sender stays unknown.
   Address lists: infra/relay/txsources.py (GENESIS, AGORZILLA, DEJA, RABBIT_*). Keep them the same there and here.
   A transaction sent from one of our games with a page of its own (No Memo) is named by its hash (GET /wallets/tags "via"):
   the same browser wallet plays White Rabbit Key and No Memo, so the wallet alone cannot say which game it came from.
   TauOrigin.of(sender, transfers, hash) -> { tag, name, what } or null. TauOrigin.ready(): a promise once the relay answered (or failed). */
(() => {
  "use strict";
  const set = a => new Set(a);
  const GENESIS = set([
    "838d089401687e4ba5fe844f1241b2f6cf63cf73a7f8fb6aa0e45b3c6b85454f4e7ca19960b71d847655486495b64cb4",
    "8a39b9d9498535492290c52b44959b5a6e9177dc85ae6a1d97f54462f03c15a38052a85c7ace5cd81858e343a3b789d0",
    "8df32da800ad4b0657e333774889e6b08f768ab055ffb964d5935bbc8460aa8f91fa60a6a042f64ec144c7ec18ae02a3",
    "916b92be0561ee21d042d033cabdf58d1c2f9ed110b2e173ab9cdd2a585442bec6232ffe0d97b779976a1dfd6a9d38fc",
    "93da919aed3b83e517190b8362528b35cbd51beb754289c5d99db12a306ac7f4980fbb96108a9cb812a46aede0c5f9ca",
    "9689f5f8ffe6b73bb549e4058e54a3fc6a96ef2e784c415adeffd83d9488c9b435f075b59a778308f86226074f8b09b0",
    "af1d997703d7c0a86a5988762bb9ac2642890b5f0599f9821372684487d580a5f211ec160c038c073cda604c3c646487",
    "b1337fcdf8d713a53518f0d6289c70bec2a09a7d6ec84548aac208988391cd66a9b627d03c07d922cd6ad15ebecf3ad7",
    "b3566dd294833030380d74b39fdb0bf214e9c64906b175f8822c3d4386602b1a9340231e553f9c299d6d8a82b9d441da",
    "b9e4b8fbe06a12f4702617f71ef031206426c4205ca0bc3436d2e0cb047fd18473ad125ceefc7ef18b851a19af2f370b",
    "f427fbf4cb8cc5ebcfc50add98ba574b94c03b1e32626e2e50cf60ba5e0a6d0c42d3ed702c2e0eeef7fae29bc4f3d2f9"]);
  const AGORZILLA = set([
    "92cfce4449523a48ab02f88d5acfa85b74860c87eaf501c48320c99a8a142191ba022199c3b20474ff19f7b72f4563a4",
    "931c4e3b949dd5a77c226e2409f617aa9603f15075f20902c849855f24fb5439113afa3869fc415a3786fe5f30321392",
    "940bad7f401e65b0ddfd2b891251cdb3f027dc96bbe4d64b5ea5547900338107186cc23d500c1888598ccc4343f6df2e",
    "947c2b8988769f9fb7ada19021e27c51f5d855e4e05ad258d2ca2322821987dbff93e0425f281edded5c372b97e6a108",
    "992d87e93030634c581fc3e6c574af0da06c70798d49f82135d8231147b79c071e277616d84fb6175dbeae2264377071",
    "ad628e861687c726aa780c4af1d4e10df4e16c169772686ada8ed81e430ec7bd70214bb732d9b7a75fb4d968136cec86",
    "afbdeb43eb62d4a95f2f679686488a14a033cbddb45dec0ac7181d40a668f4af3c8b1c9df05b3b2bc33e664a2a8dd98b",
    "b09ad0b1742efd5a4a4e7fa93a52b9f5954466ca2f694db9dfda4d593d9c15a73dfdd9055ad286e8f11f76b0f69395cf",
    "b6bdcade83f317c5a3e0402466a4f6c93a1b9018a3dd61026143c8284741fad2deeffda9a7fd3db587e86f4f44de3418"]);
  const DEJA = "8dbae75034a8cdc776e462f004dd686c8d0a32dbedd400483a026a01db4ce1f78b9d6450d2c832d8116d47a315fd8973";
  const RABBIT = set([
    "816cdcda9accef093332ca8356f87fb1a40aa612d999b55d8cc7229865508ad09bd1214ba6f4b16a6dc8b64d03fa852d",
    "81a080eed60d737f73623b80d3b1dcad85d37b5a5a4d5b0ba60c3c2379b995d470c8c2d3db2f92b803b7feb215091d16",
    "82a45ff8fd1bbba834c5c9f89e8ebb712935f83aa2709cdda051deebec517483e73fc6eeb997ebbaf2dc582a2eea56dc",
    "83546df43205836667fc104c6a56549b2b0c0cd5fd0bc188ad55e96ce656c8220991325fdd49ef8a5549bb7ca9d1cb3e",
    "87208cfd4313f66ec1baa2021ff0fdd5667285be5396a4a83480efc18d80ba3c2e41504d2bcd2b01a8d37a6cab54cd05",
    "897178ec1333edd5d3cb27f5746976e6cb8fd0d07360a8dcdfccd1f0a90d15f5a2f8b24616acb5ebfa360b86bc025175",
    "89798ff443b446b8392097e50bb61f383f24ed60f45b4f592e6b9d5356056e90698e7114f17692bdd2539bce24d73ac2",
    "899220e0128f24e1666fdaf53809c16854bc37cfcac3aa9a887e7e0205fff14de93c5b1272e1c5204ad4c1f1ee7c11de",
    "8ed60ef9cc93ec996d7eeac725539e720f86b701bdb7ac646434d177690e48869dbfdedc759c930dc88f1e3cd315c58b",
    "8ffb79523db95c885e3267633767246dda76cc9378804b02328835ba45667d7012be8b79f32e497d1822d1df96726d3d",
    "9266b7dbca59d06c60517e815e32169aaba70056101d394c6ab851a99925f18e23da324cf0c73ab5fe27c951c8bb024e",
    "96179f47d33ab65d9922c5652d7686f9e6be9d36ef4b9e9e04bdaac25b6e30d01928182c16da7aaa6dc954cccb88b62b",
    "96bf03fb7c34b84f916d928cf82bd332cd9558ab3c55e9a717381fe5c8cc6d4ec1e694e39855a680ea8f29351d6a2aea",
    "96e0c6d33c1848fa6a2355ababc5f66a7a8121c81a05f923c3e60d645f0110fe28a81db5176f750adec25b26b8746bf9",
    "981bfa68b487e86991cbd70d3c1c8ed4b151715031580976f0942610958a16e29d71c15ea4accdb3750db225f35c3f50",
    "98e2aa832d79c1689b6b3190d45e0c2319838c0f58293e6a837d606548f2c1e797b20550e0c5230a7cebbc13f74e849f",
    "98e8a33fa10f0dca59bb6fe8c9d14fb2e9b6be5cbeb95d862fc4eb9ad2d5957617f8b998757f9947065cd76c05a82578",
    "a752d4269c95abd44c6ec855ce3513f6ce8b3a8c94f58621ee1596ceb728a69aa329a541a9f75a188fdfff92ad6c045d",
    "a974149276f73fa2021068c89521bc68e8877cbfdb7d75b348951269bc3ab6c0677997f31bdbb1d28c95dc3aacacd34e",
    "adf1b27a6cfe88b1c73f12ed38eaaef535f892ee2f2b695030427ecaef7d4e43deb89f7849f2f5550cc5eec711652174",
    "b3909c612e07036be9504e3be10eef3b1483e0c1c7be4d05950ccb373f06292f186709c7344e5aa7b83501ce7f1d48af",
    "b44a202e884682b8677daf5f2685b5775f3c9ea9443a89651013bc455bc66061f2cf8d092897893bad3311e598f2cb11",
    "b6ef83b962c9e8be7345050bc34de31bc8996cfc3782947db4509f48750b53640b19d7211c591bc2e4e16d2b148bf945"]);
  const TAGS = {
    idni: ["IDNI genesis", "sent by one of the accounts the testnet started with, set up by IDNI"],
    bot: ["White Rabbit Key island bot", "sent by our own server: the island bot’s rival moves or the island’s purses"],
    cruise: ["cruise passenger (simulated)", "a simulated passenger of White Rabbit Key’s cruise ships, sent by our server"],
    rabbit: ["White Rabbit Key", "a player’s move in White Rabbit Key, the island game on tauhud.com"],
    nomemo: ["No Memo", "a player’s move in No Memo, the terminal game on tauhud.com"],
    agorzilla: ["Agorzilla", "a meal or a vote for Agorzilla, the creature on agorzilla.com"],
    deja: ["Déjà the café cat", "food for Déjà, the café cat of Agorzilla’s café"],
    showcase: ["Tau HUD showcase wallet", "one of Tau HUD’s showcase wallets: a personal rule, and once a day a payment that rule forbids, on purpose"],
  };
  // what we know about a wallet's own rule beyond its text: its purpose and who runs it (hover in the chain core and the Rules panel)
  const RUN = "Run by tauhud.com’s server with test AGRS. Once a day it tries a payment its own rule forbids, on purpose, and the node refuses it.";
  const ABOUT = {
    piggy: ["Purpose: shows a time-lock. The money stays put until New Year, whoever holds the key.", RUN],
    foureyes: ["Purpose: shows a second signature. Small payments go through; above 100 AGRS Tau HUD’s co-signer must sign as well, and once the balance is below 90,000 for every payment, so many small payments cannot empty it.", RUN],
    feeding: ["Purpose: shows a whitelist. This money can only go to Agorzilla’s bowl, at most 20 AGRS a meal, and nothing once the balance is below 90,000, so many small payments cannot empty it.", RUN],
    cosigner: ["The second signature the four-eyes wallet needs. Run by tauhud.com’s server; it never sends."],
  };
  const TAG_ABOUT = {
    idni: "One of the 11 accounts the testnet started with, set up by IDNI.",
    bot: "One of our own server wallets on White Rabbit Key.",
    cruise: "A simulated cruise passenger’s wallet, run by our server.",
    rabbit: "A White Rabbit Key player’s wallet: whoever holds its key set this rule.",
    nomemo: "A No Memo player’s wallet: whoever holds its key set this rule.",
    agorzilla: "An Agorzilla player’s wallet: whoever holds its key set this rule.",
  };
  const sim = () => !!(window.TauSim && TauSim.on);
  let known = new Map(), via = new Map(), names = new Map(), roles = new Map();
  const get = async path => { try { const r = await fetch("https://node.tauhud.com" + path, { cache: "no-store" }); return r.ok ? await r.json() : null; } catch (e) { return null; } };
  const load = async () => {
    if (sim()) return;
    // the relay's record of wallets seen before, plus our own server wallets straight from their lists, so the island bot
    // and the cruise passengers are named even before their first transaction reached a block (or before the relay knows /wallets/tags)
    const [tags, isle, ship, show] = await Promise.all([get("/wallets/tags"), get("/island"), get("/cruise"), get("/showcase")]);
    const m = new Map(Object.entries((tags && tags.tags) || {}).filter(([, v]) => TAGS[v]));
    const add = (keys, tag) => keys.forEach(k => { if (typeof k === "string" && k) m.set(k.toLowerCase(), tag); });
    if (isle) { add(Object.values(isle.wallets || {}), "bot"); add(Object.values(isle.purses || {}), "bot"); }
    if (ship && ship.wallets) add(Object.values(ship.wallets).flat(), "cruise");
    // the showcase wallets (relay showcase.py), each with its own name: "Tau HUD's piggy bank" and so on
    const nm = new Map(), rl = new Map();
    if (show && show.wallets) [...Object.entries(show.wallets), ["cosigner", show.cosigner]].forEach(([role, w]) => { if (w && typeof w.pk === "string" && w.name) { m.set(w.pk.toLowerCase(), "showcase"); nm.set(w.pk.toLowerCase(), String(w.name)); rl.set(w.pk.toLowerCase(), role); } });
    if (nm.size) { names = nm; roles = rl; }
    if (m.size || tags) known = m;
    if (tags && tags.via) via = new Map(Object.entries(tags.via).filter(([, v]) => TAGS[v]));
  };
  const first = load();
  setInterval(load, 300000);
  const mk = tag => ({ tag, name: TAGS[tag][0], what: TAGS[tag][1] });
  function of(sender, transfers, hash) {
    const s = String(sender || "").toLowerCase();
    if (!s || sim()) return null;   // the simulation's accounts are made up: no app or owner to name
    if (GENESIS.has(s)) return mk("idni");
    const k = known.get(s);
    if (k === "bot" || k === "cruise" || k === "showcase") return mk(k);
    const g = hash && via.get(String(hash).toLowerCase());
    if (g) return mk(g);
    for (const op of Array.isArray(transfers) ? transfers : []) {
      const to = String((op && op[1]) || "").toLowerCase();
      if (to === DEJA) return mk("deja");
      if (AGORZILLA.has(to)) return mk("agorzilla");
      if (RABBIT.has(to)) return mk("rabbit");
    }
    return k ? mk(k) : null;
  }
  // a short name for a label next to the dot (the chain core), in the page's language
  const SHORT = { idni: "IDNI", bot: "island bot", cruise: "cruise (sim)", rabbit: "White Rabbit Key", nomemo: "No Memo", agorzilla: "Agorzilla", deja: "Déjà", showcase: "showcase" };
  const label = tag => { const t = SHORT[tag] || tag; return window.TauI18n ? TauI18n.t(t) : t; };
  // a wallet's own name where it has one (the showcase wallets), else null
  const name = pk => (!sim() && names.get(String(pk || "").toLowerCase())) || null;
  // what we know about the wallet behind a rule, as lines (purpose, who runs it), or null when we know nothing
  const about = pk => {
    if (sim()) return null;
    const h = String(pk || "").toLowerCase(), r = roles.get(h);
    if (r && ABOUT[r]) return ABOUT[r].slice();
    const o = of(h, [], ""); return o && TAG_ABOUT[o.tag] ? [TAG_ABOUT[o.tag]] : null;
  };
  window.TauOrigin = { of, label, name, about, tags: TAGS, ready: () => first };
})();
