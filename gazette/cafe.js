/* The Daily Consensus: the café around the paper, to walk through. "Look up" lays the paper down and the
   café opens around the reader: the window table, the counter, the wire corner, the back room and the door,
   each reached through the left or right edge, each with a regular to talk to. Every regular stamps the café
   ticket; with four stamps the door leads out onto Market Street, and an Extra! lands at the reader's feet.
   Everything is drawn and voiced here in the browser (no photographs, no recordings), in the paper's sepia.
   Words: CAFE_EN below; cafe-zh.js and cafe-ja.js carry the same keys. */
(() => {
  "use strict";
  const desk = document.getElementById("desk"), S = window.GAZETTE_SCENE;
  if (!desk || !S) return;
  const { tone, rnd } = S;
  const LANG = (window.TauI18n && TauI18n.lang) || "en";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const touch = matchMedia("(pointer: coarse)").matches;
  const small = () => desk.clientWidth < 760 || desk.clientHeight < 460;

  /* ============ the words (English) ============ */
  const CAFE_EN = {
    call: "From the counter, Mae: “Fresh pot on, hon, if you're looking up.”", loading: "One moment…", loadingSub: "The café is being set for you", enter: "Look up", enterTip: "Look up from the paper: walk through the café and meet the regulars",
    back: "The paper", backTip: "Back to the paper",
    cat: { bowl: "Her bowl is real: feed her at agorzilla.com/cat ›", deja: "Déjà vu: the cat went by twice, the very same way. In here that means a rule just changed.",
      lines: ["Déjà, the café cat. Nobody owns her. Everybody agreed to feed her, and that is a rule too: she eats on a day when three wallets feed her.", "Prrr. She sits on whatever proposal you are reading. That is her vote.",
        "Mrrp. She doesn't follow the chain. She follows the warm spot by the coffee urn.", "Mae says the cat was here before the house rules. She has never voted, and somehow she always gets her way."] },
    hint: "Walk with the edges of the room or ← →, and click someone to talk",
    hintTouch: "Swipe or tap the edges to walk, and tap someone to talk",
    soundHint: "Best with sound",
    ticket: "Café ticket", admit: "Admit one", ticketTip: "Talk to all four regulars, then find the door.",
    thisWeek: "this week", more: "Click to go on", stamped: "{name} stamped your ticket: {what}", stampFor: { mae: "Agreement", elias: "Chain", prof: "Logic", sully: "Testnet" }, full: "Your ticket is full. The door is open to you.",
    sep: ", ", and: " and ",
    places: { window: "Your table by the window", counter: "The counter", wire: "The wire corner", back: "The back room", door: "The door" },
    board: ["House Rules", "1. Mind the cups.", "2. Anyone may propose a rule.", "3. The regulars vote.", "4. Most hands carry it.", "5. Rule 4 may be voted on, too.", "Proposed: pie on Fridays", "Carried"],
    clocks: ["New York", "London", "Berlin", "Tokyo"], wireSign: "Wire Service · Telegrams",
    tape: h => h != null ? `BLOCK ${h.toLocaleString("en-US")} … LINKED TO ${(h - 1).toLocaleString("en-US")} … ` : "BLOCK … LINKED TO THE ONE BEFORE … ",
    logic: ["If A, then B.", "A.", "Therefore B.", "A and not A: ⊥"],
    people: {
      mae: { name: "Mae", role: "runs the counter",
        greet: ["Morning, hon. You've been reading that paper like it owes you money.", "Sit anywhere the sun isn't. What can I do for you?"],
        ask: [
          { id: "rules", key: true, q: "What's on that board, “House Rules”?", a: ["The regulars wrote every one of those. Nobody in some office upstairs.", "Somebody wants a new rule, they chalk it up as a proposal, and everybody with a stool gets a say.", "Enough hands go up, I chalk it in. Not enough, I wipe it off. That's the whole idea behind Tau, hon, only for software: the users vote, and the rules change by agreement."] },
          { id: "rule4", q: "Can you vote on the voting rule, too?", a: ["Rule four says how many hands it takes. And sure, you can vote on rule four.", "Took us a whole winter. But nobody had to shut the café and open a new one across the street.", "Elsewhere they'd call that a fork. Here we call it Tuesday."] },
          { id: "nonsense", q: "What if somebody chalks up nonsense?", a: ["Then the Professor in the back room gets that look on his face.", "Go ask him why nonsense never makes it onto my board."] },
        ],
        task: { q: "I'll chalk it in.", ask: ["Speaking of which: the regulars just voted on pie on Fridays. Four hands for, one against.", "Go on, hon, you chalk it in. The board's right there."], hint: "Click the board to chalk in the vote.",
          done: ["Look at that. Pie on Fridays, carried, because the regulars agreed and you chalked it in.", "That's how a rule changes in this house. It earns you the house stamp for Agreement."] },
        wait: "Hold on, hon. You haven't chalked anything in yet.",
        bye: { q: "Thanks, Mae.", a: ["Go on, the coffee's not going anywhere."] } },
      elias: { name: "Elias", role: "minds the wire",
        greet: ["Hold on… hold on… there. Another one, just came over the wire.", "Every slip on this tape is a block. Care to look?"],
        ask: [
          { id: "tape", key: true, q: "What's printed on the tape?", a: ["Each slip says what happened, and it carries the mark of the slip before it.", "Change an old slip and every mark after it stops matching. You'd have to fool every operator on the line at once.", { h: "That's a chain of blocks. The Tau testnet keeps one just like it: this very minute it's on block {h}.", n: "That's a chain of blocks. The Tau testnet keeps one just like it, thousands of slips long already." }] },
          { id: "who", q: "Who keeps the tape running?", a: ["Validators. Operators in different towns, each with a copy of the tape.", "They agree on the next slip before it's glued on. Nobody alone decides what's true.", "It's a test line, mind you. Still being tried, still being mended."] },
          { id: "vote", q: "And when Mae's regulars pass a new rule?", a: ["Then it comes over the wire like anything else, on a block.", "From that slip on, everybody on the line runs by the new rule. Same tape. No second line."] },
        ],
        task: { q: "Let me glue on the next slip.", ask: ["Here, make yourself useful. Three slips just came in, and only one belongs on the end of the tape.", { h: "The last slip on the tape is block {h}. Find the one that carries its mark.", n: "Find the one that carries the mark of the last slip on the tape." }],
          slip: "Block {n} · follows {m}", wrong: "That one doesn't carry the mark of the last slip. Look again.",
          done: ["Glued on, and it fits: it carries the mark of the last slip, so nobody can sneak a false one in between.", "You just kept a chain. That's the wire's stamp: Chain."] },
        wait: "Not so fast. The tape isn't done with you yet.",
        bye: { q: "I'll let you get back to it.", a: ["Mind the tape on your way."] } },
      prof: { name: "The Professor", role: "plays chess against himself",
        greet: ["Ah. A newcomer. Sit, sit. But do not touch the bishop.", "Do you play? No matter. The board is the point."],
        ask: [
          { id: "logic", key: true, q: "Why is the board the point?", a: ["On a chessboard an illegal move simply cannot be made. The rules are exact, so anyone can check them.", "Tau writes its rules in a language just as exact: the Tau Language. A machine can read a rule and work out precisely what it allows.", "So before anyone votes, a proposed rule is checked against the rules in force. If it contradicts them, that is caught before the vote."] },
          { id: "nonsense", q: "Mae says nonsense never reaches her board.", a: ["Nonsense is the polite word for a contradiction. “The doors open at seven” and “the doors never open.”", "Both cannot be true at once. The machine sees it and says so, before anyone has to argue.", "Mae's café runs on goodwill. Tau hopes to run on goodwill and logic."] },
          { id: "done", q: "Is any of this finished?", a: ["Finished? My dear friend, nothing worth doing is ever finished.", "This is a testnet: a rehearsal held in public. Plans change, mistakes are found and mended.", "Which is precisely why it is worth watching now."] },
        ],
        task: { q: "Let me find the contradiction.", ask: ["Then try it yourself. The rule in force: “The doors open at seven.”", "A regular proposes one of these. Which one could never pass the check?"],
          opts: ["Coffee is served from seven.", "The doors never open.", "Pie on Fridays."], right: 1, wrong: "No, that one can live beside the rule in force. Look for the one that cannot.",
          done: ["Precisely. Both cannot be true at once, so the check refuses it before anyone votes.", "You caught a contradiction before the vote. My stamp: Logic."] },
        wait: "Sit a moment longer. We have not finished.",
        bye: { q: "I'll leave you to your game.", a: ["Mind the bishop."] } },
      sully: { name: "Sully", role: "sells the morning edition",
        greet: ["Extra! Extra!… Oh, it's you, pal. Leaving already?", "You ain't heard the half of it yet."],
        greetDone: ["Extra! Extra!… Say, you look like you seen a ghost. A friendly one."],
        missing: "Go talk to {who} first. Then the door's all yours.",
        ask: [
          { id: "news", key: true, q: "What's the big news, Sully?", a: ["The news is it's happening right now, pal. Not someday. On a testnet, open to anybody.", "You can watch the blocks come in, try out rules in a playground, even make yourself a practice wallet.", "Practice money, mind. Nothing to buy, nothing to sell. It's for learning how the thing works."] },
          { id: "care", q: "Why should anybody care?", a: ["My pop says the rules always got made upstairs, by somebody he never met.", "This here's the first I heard of rules the people who use 'em get to write and vote on.", "That's a story. That's front page."] },
        ],
        task: { q: "Here's my ticket.", ask: ["Say, got a ticket? Hold it up, pal. Up there in the corner."], hint: "Click your café ticket.",
          done: ["Mae, Elias, the Professor… all there. And now you know it's happening right now, on a testnet anybody can try.", "That's my stamp: Testnet. Full house, pal. You're ready for the street."] },
        shut: "Door's shut till your ticket's full, pal. House rules.",
        out: { q: "Step outside", a: ["Go on, pal. Read all about it."] },
        bye: { q: "See you around, Sully.", a: ["Don't be a stranger."] } },
    },
    look: {"slip": {"block": "BLOCK", "mark": "carries the mark of block {m}", "markN": "carries the mark of the block before", "at": "came over the wire at {t} UTC", "head": "This Week on the Testnet", "papers": "Rules Change by Agreement"}, "urn": "Mae says it holds forty cups. The Professor says thirty-eight and a half. They have agreed to disagree.", "pie": "Four regulars for, one against. If it carries, it waits under glass until Friday, the day named in advance. On the chain a rule switches on at a block named in advance, the same way.", "register": "There is no drawer in it for rules. Nobody can pay to have a rule changed: only votes count.", "board": "Rule 5 is the clever one: the rule on how rules change is on the same board, and can be voted on too.", "ticker": "Each slip carries the mark of the one before. Tear one out and the next no longer fits.", "clocks": "Four cities, one tape. The validators sit in different places, and the chain keeps one order for all of them: block after block.", "gramophone": "The record skips at the second chorus. Nobody has proposed a new one yet.", "books": "The cookbook is the Professor's. He says baking is logic you can eat.", "slate": "⊥ is the logician's mark for “this cannot be.” When it appears, a proposal stops before any vote.", "coats": "The coat from 1919 has a ticket in its pocket. Nobody remembers whose. Nobody has voted to move it.", "bell": "It rings the same for everyone who leaves. Mae likes that about it.", "bundle": "Hot off the press: this week's front page, tied with string."},
    props: {
      cup: "Your coffee, still warm. Someone stirred a τ into the steam.",
      sugar: "A stack of sugar cubes, one on top of the other.",
      papers: "Yesterday's papers, folded on the table.",
      urn: "The big brass urn. It has been hissing since six.",
      pie: "A lemon pie under glass. Not on the house rules yet. Pie on Fridays is up for a vote.",
      register: "The register rings up cups, not rules. Rules go on the board.",
      board: "House Rules, in chalk. Every line on it was voted in.",
      ticker: h => h != null ? `The ticker clicks: block ${h.toLocaleString()}, linked to block ${(h - 1).toLocaleString()}.` : "The ticker clicks: another block, linked to the one before.",
      clocks: "New York, London, Berlin, Tokyo. The wire never sleeps, and neither does the chain.",
      gramophone: "A slow blues in F. Somebody in the back room keeps winding it.",
      books: "Logic, logic, more logic, chess, and one cookbook.",
      slate: "Chalk on slate: if A, then B. A. Therefore B. And A with not-A is where it stops.",
      coats: "The regulars' hats and coats. One of them has hung here since 1919.",
      bell: "A little brass bell over the door. It rings when somebody leaves.",
      bundle: "This morning's papers, still tied with string.",
    },
    end: {
      lines: ["The bell over the door rings once behind you.", "Market Street is louder than you remember: the streetcars, the newsboys, everyone hurrying to work as if nothing had changed.", "But you know something now.", "Somewhere out there, rules are being written that the people who live by them can vote on.", "And for once, you are early."],
      extra: "Extra!", head: "Reader Leaves Café Changed",
      deck: "Waitress: “the users vote.” Wire clerk: “every block carries the last.” Professor: “contradictions are caught before the vote.” Newsboy: “it's happening now, on a testnet open to anybody.”",
      block: { h: "Tau Testnet Alpha stood at block {h} as our reader stepped outside.", n: "Tau Testnet Alpha kept adding blocks as our reader stepped outside." },
      fine: "Testnet only. Nothing for sale; test AGRS are for practice.",
      share: "Pass the paper on", shareSub: "Walk a friend through the café: the link opens straight inside.", shareMore: "More…", onX: "Post on X", copy: "Copy the link", copied: "Link copied",
      shareText: "I walked through a 1920s café and came out knowing how Tau's rules change by agreement. #TauNet",
      paper: "Back to the paper", live: "Watch the testnet live", play: "Try a rule in the playground", again: "Walk in again",
    },
  };

  /* the visitor's language, filled up from English where a word is missing */
  const merge = (a, b) => { if (b == null) return a; if (typeof a !== "object" || Array.isArray(a) || typeof a === "function") return b;
    const o = {}; for (const k of Object.keys(a)) o[k] = merge(a[k], b[k]); return o; };
  let TX = CAFE_EN;
  const words = () => { TX = merge(CAFE_EN, { zh: window.CAFE_ZH, ja: window.CAFE_JA }[LANG]); };
  const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (m, k) => o[k] != null ? o[k] : m);
  const live = () => { const L = window.GAZETTE_LIVE || {}; return Number.isFinite(L.height) ? L.height : null; };
  const num = n => n.toLocaleString(LANG === "en" ? "en-US" : LANG);
  const line = l => { if (typeof l === "string") return l; const h = live(); return h != null ? fmt(l.h, { h: num(h) }) : l.n; };

  /* ============ drawing helpers ============ */
  const lin = (g, x0, y0, x1, y1, st) => { const gr = g.createLinearGradient(x0, y0, x1, y1); st.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };
  const rad = (g, x, y, r0, r1, st, x1 = x, y1 = y) => { const gr = g.createRadialGradient(x, y, r0, x1, y1, r1); st.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };
  const poly = (g, pts, fill) => { g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); if (fill) { g.fillStyle = fill; g.fill(); } };
  const quad = (g, P, a, fill) => poly(g, a.map(p => P(...p)), fill);   /* a flat piece of the world, corners in metres */
  const warm = a => `rgba(255,222,165,${a})`;
  const puff = (g, x, y, r, a) => { g.fillStyle = rad(g, x, y, 0, r, [[0, `rgba(238,228,208,${a})`], [1, "rgba(238,228,208,0)"]]); g.fillRect(x - r, y - r, r * 2, r * 2); };
  const glow = (g, x, y, r, a) => { g.fillStyle = rad(g, x, y, 0, r, [[0, warm(a)], [0.35, warm(a * 0.4)], [1, warm(0)]]); g.fillRect(x - r, y - r, r * 2, r * 2); };

  /* the room seen from where the reader stands: eye at 1.6 m, the far wall 6.2 m away, the ceiling at 3.6 m */
  const ZB = 6.2;
  const geom = (W, H, cam = 0) => { const f = H * 1.1, vx = W / 2, vy = H * 0.44;
    return { W, H, f, vx, vy, cam, P: (X, Y, z) => [vx + (X - cam) * f / z, vy - (Y - 1.6) * f / z], s: z => f / z, X: (x, z) => (x - vx) * z / f + cam }; };

  /* walls, ceiling and the lamp pools that every room shares */
  function walls(g, G, o) {
    const { W, H, P } = G, ov = H * 0.2, xl = G.X(-ov, ZB), xr = G.X(W + ov, ZB), R = rnd(o.seed || 7);
    const [, ceilY] = P(0, 3.6, ZB), [, floorY] = P(0, 0, ZB);
    /* the pressed-tin ceiling, running toward us */
    g.fillStyle = lin(g, 0, 0, 0, ceilY, [[0, tone(0.02)], [1, tone(0.1)]]); g.fillRect(-ov, 0, W + 2 * ov, ceilY + 1);
    g.strokeStyle = tone(0.2, 0.35); g.lineWidth = 1;
    for (let X = Math.floor(xl); X <= xr; X += 0.6) { const a = P(X, 3.6, ZB), b = P(X, 3.6, 1.1); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    for (let z = ZB; z > 1.2; z -= 0.6) { const a = P(xl - 4, 3.6, z), b = P(xr + 4, 3.6, z); g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); }
    /* the far wall: damask paper above dark panelling */
    const top = ceilY, wy = P(0, o.wain || 1.05, ZB)[1];
    g.fillStyle = lin(g, 0, top, 0, floorY, [[0, tone(0.14)], [0.6, tone(0.21)], [1, tone(0.16)]]); g.fillRect(-ov, top, W + 2 * ov, floorY - top);
    const sw = G.s(ZB) * 0.16;
    for (let x = -ov; x < W + ov; x += sw * 2) { g.fillStyle = tone(0.2, 0.32); g.fillRect(x, top, sw, wy - top);
      g.fillStyle = tone(0.28, 0.22); for (let y = top + sw; y < wy - sw * 0.5; y += sw * 2.2) { g.beginPath(); g.moveTo(x + sw * 1.5, y - sw * 0.5); g.lineTo(x + sw * 1.9, y); g.lineTo(x + sw * 1.5, y + sw * 0.5); g.lineTo(x + sw * 1.1, y); g.fill(); } }
    /* crown moulding and picture rail */
    g.fillStyle = tone(0.05); g.fillRect(-ov, top, W + 2 * ov, G.s(ZB) * 0.14); g.fillStyle = tone(0.3, 0.5); g.fillRect(-ov, top + G.s(ZB) * 0.14, W + 2 * ov, 1.5);
    const rail = P(0, 2.6, ZB)[1]; g.fillStyle = tone(0.06); g.fillRect(-ov, rail, W + 2 * ov, G.s(ZB) * 0.05);
    /* the panelling */
    g.fillStyle = lin(g, 0, wy, 0, floorY, [[0, tone(0.13)], [1, tone(0.06)]]); g.fillRect(-ov, wy, W + 2 * ov, floorY - wy);
    g.fillStyle = tone(0.3, 0.55); g.fillRect(-ov, wy, W + 2 * ov, 1.5);
    const pw = G.s(ZB) * 0.9;
    for (let x = -ov + (W / 2 % pw); x < W + ov; x += pw) { const y0 = wy + G.s(ZB) * 0.12, y1 = floorY - G.s(ZB) * 0.2;
      g.strokeStyle = tone(0.2, 0.5); g.lineWidth = 1; g.strokeRect(x + pw * 0.1, y0, pw * 0.8, y1 - y0);
      g.strokeStyle = tone(0, 0.6); g.strokeRect(x + pw * 0.1 + 1.5, y0 + 1.5, pw * 0.8, y1 - y0); }
    g.fillStyle = tone(0.02); g.fillRect(-ov, floorY - G.s(ZB) * 0.12, W + 2 * ov, G.s(ZB) * 0.12);
    /* pendant lamps: a cord, a glass globe, the light it throws on the wall */
    (o.lamps || []).forEach(([X, z = 4.2, Y = 2.75, k = 1]) => {
      const [x, y] = P(X, Y, z), [, cy] = P(X, 3.6, z), r = G.s(z) * 0.14;
      glow(g, x, y + r, G.s(ZB) * 2.6 * k, 0.16 * k);
      g.strokeStyle = tone(0.02); g.lineWidth = Math.max(1, r * 0.05); g.beginPath(); g.moveTo(x, cy); g.lineTo(x, y - r * 0.6); g.stroke();
      g.fillStyle = tone(0.05); g.fillRect(x - r * 0.3, y - r * 0.75, r * 0.6, r * 0.3);
      g.fillStyle = rad(g, x - r * 0.2, y - r * 0.2, 0, r, [[0, "rgba(255,246,222,1)"], [0.6, "rgba(250,215,150,.95)"], [1, "rgba(190,140,80,.85)"]]); g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
      glow(g, x, y, r * 4, 0.35 * k); });
    (o.sconces || []).forEach(([X, Y]) => { const [x, y] = P(X, Y, ZB), r = G.s(ZB) * 0.07; glow(g, x, y, r * 9, 0.22);
      g.fillStyle = tone(0.5); g.fillRect(x - r * 0.15, y, r * 0.3, r * 1.6); g.fillStyle = "rgba(255,240,205,.95)"; g.beginPath(); g.ellipse(x, y - r * 0.2, r * 0.55, r * 0.75, 0, 0, 7); g.fill(); });
    floor(g, G, o);
  }
  /* the floor: small black and white tiles, polished, the lamps shining in it */
  function floor(g, G, o) {
    const { W, H, P } = G, ov = H * 0.2, [, fy] = P(0, 0, ZB);
    g.fillStyle = lin(g, 0, fy, 0, H, [[0, tone(0.2)], [1, tone(0.1)]]); g.fillRect(-ov, fy, W + 2 * ov, H - fy);
    const step = 0.36, xl = G.X(-ov, ZB), xr = G.X(W + ov, ZB);
    for (let z = ZB, row = 0; z > 0.9; z -= step * (z > 3 ? 1 : 0.8), row++) { const z1 = z - step * (z > 3 ? 1 : 0.8);
      for (let X = Math.floor(xl / step) * step, c = 0; X < xr; X += step, c++) { if ((row + c) % 2) continue;
        const d = Math.min(1, (z - 1) / 5); quad(g, P, [[X, 0, z], [X + step, 0, z], [X + step, 0, z1], [X, 0, z1]], tone(0.42 - d * 0.18, 0.75)); } }
    /* lamp light pooled on the tiles and its shine */
    g.save(); g.globalCompositeOperation = "screen";
    (o.pools || []).forEach(([X, z, k = 1]) => { const [x, y] = P(X, 0, z), r = G.s(z) * 1.6; g.save(); g.translate(x, y); g.scale(1, 0.32); glow(g, 0, 0, r, 0.22 * k); g.restore();
      g.fillStyle = lin(g, x, fy, x, H, [[0, warm(0.12 * k)], [1, warm(0)]]); g.fillRect(x - r * 0.08, fy, r * 0.16, H - fy); });
    g.restore();
    g.fillStyle = lin(g, 0, fy, 0, H, [[0, "rgba(0,0,0,.35)"], [0.4, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,.45)"]]); g.fillRect(-ov, fy, W + 2 * ov, H - fy);
  }
  /* a solid box in the room (a counter, a table, a cabinet): front, top, and the side that faces the middle */
  function box(g, G, X0, X1, Y0, Y1, z0, z1, c) {
    const { P } = G, side = (X0 + X1) / 2 < G.cam ? X1 : X0;
    quad(g, P, [[side, Y0, z0], [side, Y1, z0], [side, Y1, z1], [side, Y0, z1]], c.side || tone(0.05));
    quad(g, P, [[X0, Y1, z0], [X1, Y1, z0], [X1, Y1, z1], [X0, Y1, z1]], c.top || tone(0.3));
    quad(g, P, [[X0, Y0, z0], [X1, Y0, z0], [X1, Y1, z0], [X0, Y1, z0]], c.front || tone(0.1));
  }
  const text = (g, s, x, y, px, o = {}) => { g.save(); g.font = `${o.w || 400} ${o.it ? "italic " : ""}${px}px ${o.face || "Georgia, 'Noto Serif SC', serif"}`; g.textAlign = o.al || "center"; g.textBaseline = "middle";
    if (o.max) { const w = g.measureText(s).width; if (w > o.max) { g.translate(x, y); g.scale(o.max / w, 1); x = 0; y = 0; } }
    if (o.stroke) { g.lineWidth = px * 0.08; g.strokeStyle = o.stroke; g.strokeText(s, x, y); } g.fillStyle = o.fill || tone(0.8); g.fillText(s, x, y); g.restore(); };

  /* ============ people ============ */
  /* a head, drawn in metres: lit from the upper left, eyes on the visitor unless told otherwise */
  function head(g, o) {
    const r = o.r, tx = (o.turn || 0) * r * 0.26, lk = o.look || [0, 0];
    g.save(); g.translate(o.x, o.y); g.rotate(o.tilt || 0);
    /* neck */
    g.fillStyle = lin(g, -r * 0.35, 0, r * 0.35, 0, [[0, tone(0.5)], [1, tone(0.22)]]); g.fillRect(-r * 0.36, r * 0.55, r * 0.72, r * 0.75);
    g.fillStyle = "rgba(0,0,0,.35)"; g.fillRect(-r * 0.36, r * 0.75, r * 0.72, r * 0.18);
    /* ears */
    for (const sd of [-1, 1]) { g.fillStyle = tone(sd < 0 ? 0.55 : 0.3); g.beginPath(); g.ellipse(sd * r * 0.8 + tx * 0.4, r * 0.05, r * 0.14, r * 0.22, 0, 0, 7); g.fill(); }
    /* the face */
    g.fillStyle = rad(g, -r * 0.35 + tx * 0.5, -r * 0.35, r * 0.1, r * 1.35, [[0, tone(o.skin || 0.8)], [0.55, tone((o.skin || 0.8) - 0.22)], [1, tone(0.2)]]);
    g.beginPath(); g.moveTo(-r * 0.78, -r * 0.2); g.bezierCurveTo(-r * 0.8, -r * 1.1, r * 0.8, -r * 1.1, r * 0.78, -r * 0.2);
    g.bezierCurveTo(r * 0.76, r * 0.45, r * 0.4, r * 0.95, tx * 0.3, r * 1.0); g.bezierCurveTo(-r * 0.4, r * 0.95, -r * 0.76, r * 0.45, -r * 0.78, -r * 0.2); g.fill();
    /* the shadow side and under the chin */
    g.fillStyle = lin(g, -r, 0, r, 0, [[0, "rgba(0,0,0,0)"], [0.6, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,.28)"]]); g.fill();
    /* eyes: sockets, whites, the iris looking at the visitor, a catchlight, lids and brows */
    for (const sd of [-1, 1]) { const ex = tx + sd * r * 0.33, ey = -r * 0.08;
      g.fillStyle = "rgba(20,12,6,.28)"; g.beginPath(); g.ellipse(ex, ey - r * 0.02, r * 0.19, r * 0.12, 0, 0, 7); g.fill();
      if (o.blink) { g.strokeStyle = tone(0.1); g.lineWidth = r * 0.04; g.beginPath(); g.moveTo(ex - r * 0.12, ey); g.quadraticCurveTo(ex, ey + r * 0.05, ex + r * 0.12, ey); g.stroke(); }
      else { g.fillStyle = tone(0.86, 0.95); g.beginPath(); g.ellipse(ex, ey, r * 0.13, r * 0.07, 0, 0, 7); g.fill();
        g.save(); g.beginPath(); g.ellipse(ex, ey, r * 0.13, r * 0.07, 0, 0, 7); g.clip();
        const ix = ex + lk[0] * r * 0.06, iy = ey + lk[1] * r * 0.03; g.fillStyle = tone(0.06); g.beginPath(); g.arc(ix, iy, r * 0.068, 0, 7); g.fill();
        g.fillStyle = "rgba(255,250,235,.95)"; g.beginPath(); g.arc(ix - r * 0.025, iy - r * 0.025, r * 0.02, 0, 7); g.fill(); g.restore();
        g.strokeStyle = tone(0.06); g.lineWidth = r * 0.035; g.beginPath(); g.moveTo(ex - r * 0.14, ey + r * 0.005); g.quadraticCurveTo(ex, ey - r * 0.1, ex + r * 0.14, ey + r * 0.005); g.stroke(); }
      const bu = (o.brow || 0) * r * 0.06; g.strokeStyle = tone(o.browTone != null ? o.browTone : 0.1); g.lineWidth = r * (o.browW || 0.05); g.lineCap = "round";
      g.beginPath(); g.moveTo(ex - r * 0.15, ey - r * 0.17 - bu * (sd < 0 ? 0.6 : 1)); g.quadraticCurveTo(ex, ey - r * 0.25 - bu, ex + r * 0.15, ey - r * 0.16 - bu * (sd < 0 ? 1 : 0.6)); g.stroke(); }
    /* nose */
    g.strokeStyle = "rgba(30,18,8,.45)"; g.lineWidth = r * 0.045; g.beginPath(); g.moveTo(tx + r * 0.06, -r * 0.02); g.quadraticCurveTo(tx + r * 0.14, r * 0.2, tx + r * 0.05, r * 0.28); g.stroke();
    g.fillStyle = tone(0.92, 0.5); g.beginPath(); g.arc(tx - r * 0.02, r * 0.22, r * 0.045, 0, 7); g.fill();
    g.fillStyle = "rgba(20,10,4,.5)"; g.beginPath(); g.arc(tx + r * 0.07, r * 0.29, r * 0.025, 0, 7); g.fill(); g.beginPath(); g.arc(tx - r * 0.08, r * 0.29, r * 0.025, 0, 7); g.fill();
    if (o.mous) o.mous(g, r, tx);
    /* mouth: a smile at rest, open in syllables while talking */
    const m = o.mouth || 0, my = r * 0.5, mw = r * 0.2, sm = (o.smile != null ? o.smile : 0.5) * r * 0.06;
    if (m > 0.08) { g.fillStyle = tone(0.04); g.beginPath(); g.ellipse(tx, my + r * 0.02, mw * (0.75 + m * 0.15), r * (0.03 + 0.08 * m), 0, 0, 7); g.fill();
      g.fillStyle = tone(0.75, 0.6); g.fillRect(tx - mw * 0.5, my - r * 0.03 + r * 0.012, mw, r * 0.025); }
    else { g.strokeStyle = tone(0.12); g.lineWidth = r * 0.04; g.beginPath(); g.moveTo(tx - mw, my - sm); g.quadraticCurveTo(tx, my + sm * 1.5, tx + mw, my - sm); g.stroke(); }
    g.fillStyle = "rgba(255,240,215,.18)"; g.beginPath(); g.ellipse(tx, my + r * 0.16, mw * 0.6, r * 0.05, 0, 0, 7); g.fill();
    if (o.top) o.top(g, r, tx);
    g.restore();
  }
  /* an arm: shoulder, elbow, hand, a sleeve and a hand at the end */
  function arm(g, a, b, c, w, cloth, skin = 0.62, cuff) {
    g.lineCap = "round"; g.lineJoin = "round";
    g.strokeStyle = cloth; g.lineWidth = w; g.beginPath(); g.moveTo(...a); g.quadraticCurveTo(b[0], b[1], (b[0] + c[0]) / 2, (b[1] + c[1]) / 2); g.lineTo(c[0] * 0.85 + b[0] * 0.15, c[1] * 0.85 + b[1] * 0.15); g.stroke();
    if (cuff) { g.strokeStyle = cuff; g.lineWidth = w * 0.9; g.beginPath(); const u = 0.62; g.moveTo(b[0] + (c[0] - b[0]) * u, b[1] + (c[1] - b[1]) * u); g.lineTo(b[0] + (c[0] - b[0]) * (u + 0.05), b[1] + (c[1] - b[1]) * (u + 0.05)); g.stroke(); }
    g.fillStyle = rad(g, c[0] - w * 0.2, c[1] - w * 0.2, 0, w * 0.8, [[0, tone(skin + 0.12)], [1, tone(skin - 0.25)]]); g.beginPath(); g.ellipse(c[0], c[1], w * 0.42, w * 0.36, 0, 0, 7); g.fill();
  }
  const blinkAt = (t, seed) => { const p = (t + seed * 1.7) % 4.3; return p < 0.13; };
  const mouthOf = st => st.talk ? st.mouth : 0;

  /* Mae, behind the counter, polishing a cup. Origin: the counter top under her, in metres. */
  function drawMae(g, t, st) {
    const br = Math.sin(t * 1.5) * 0.004, pol = st.talk ? 0.4 : 1, a = t * 2.4 * pol, sway = Math.sin(t * 0.5) * 0.01;
    g.save(); g.translate(sway, 0);
    /* blouse */
    g.fillStyle = lin(g, -0.22, 0, 0.22, 0, [[0, tone(0.7)], [0.5, tone(0.55)], [1, tone(0.24)]]);
    g.beginPath(); g.moveTo(-0.17, 0.12); g.bezierCurveTo(-0.2, -0.1, -0.23, -0.3, -0.2, -0.39 - br); g.quadraticCurveTo(-0.11, -0.45 - br, 0, -0.45 - br); g.quadraticCurveTo(0.11, -0.45 - br, 0.2, -0.39 - br); g.bezierCurveTo(0.23, -0.3, 0.2, -0.1, 0.17, 0.12); g.closePath(); g.fill();
    /* puffed sleeves */
    for (const sd of [-1, 1]) { g.fillStyle = rad(g, sd * 0.2 - 0.02, -0.37, 0, 0.08, [[0, tone(sd < 0 ? 0.8 : 0.5)], [1, tone(sd < 0 ? 0.45 : 0.2)]]); g.beginPath(); g.ellipse(sd * 0.19, -0.36 - br, 0.05, 0.045, 0, 0, 7); g.fill(); }
    /* the apron bib and its straps */
    g.fillStyle = lin(g, -0.1, 0, 0.1, 0, [[0, tone(0.92)], [1, tone(0.6)]]); g.beginPath(); g.moveTo(-0.11, 0.12); g.lineTo(-0.095, -0.26); g.lineTo(0.095, -0.26); g.lineTo(0.11, 0.12); g.fill();
    g.strokeStyle = tone(0.8); g.lineWidth = 0.018; g.beginPath(); g.moveTo(-0.09, -0.255); g.lineTo(-0.13, -0.43); g.moveTo(0.09, -0.255); g.lineTo(0.13, -0.43); g.stroke();
    g.strokeStyle = tone(0.5, 0.6); g.lineWidth = 0.004; g.beginPath(); g.moveTo(-0.07, -0.18); g.lineTo(0.07, -0.18); g.stroke();
    /* collar */
    for (const sd of [-1, 1]) { g.fillStyle = tone(0.95); g.beginPath(); g.ellipse(sd * 0.035, -0.44, 0.045, 0.022, sd * 0.4, 0, 7); g.fill(); }
    /* the cup in one hand, the cloth in the other going round */
    const ch = [-0.045, -0.13], cl = [0.0 + Math.cos(a) * 0.035, -0.17 + Math.sin(a) * 0.022];
    arm(g, [-0.2, -0.33], [-0.23, -0.12], ch, 0.06, tone(0.62), 0.62);
    g.fillStyle = lin(g, -0.09, 0, 0.0, 0, [[0, tone(0.7)], [0.4, tone(1)], [1, tone(0.6)]]); g.beginPath(); g.moveTo(-0.085, -0.2); g.lineTo(-0.075, -0.13); g.quadraticCurveTo(-0.045, -0.115, -0.015, -0.13); g.lineTo(-0.005, -0.2); g.fill();
    g.fillStyle = tone(0.98); g.beginPath(); g.ellipse(-0.045, -0.2, 0.04, 0.009, 0, 0, 7); g.fill();
    arm(g, [0.2, -0.33], [0.2, -0.1], cl, 0.06, tone(0.4), 0.55);
    g.fillStyle = tone(0.88, 0.95); g.beginPath(); g.ellipse(cl[0] - 0.01, cl[1] - 0.01, 0.045, 0.03, 0.4, 0, 7); g.fill();
    /* her head and the bob with its finger waves */
    head(g, { x: 0, y: -0.6 - br, r: 0.105, tilt: sway * 3 + (st.talk ? Math.sin(t * 2.2) * 0.04 : 0.05), blink: blinkAt(t, 1), mouth: mouthOf(st), smile: 0.8, look: st.look, brow: st.talk ? 0.6 + Math.sin(t * 1.3) * 0.4 : 0.2, skin: 0.82,
      top: (g, r) => { g.fillStyle = lin(g, -r, -r, r, r, [[0, tone(0.22)], [1, tone(0.04)]]);
        g.beginPath(); g.moveTo(-r * 0.86, r * 0.42); g.bezierCurveTo(-r * 1.15, -r * 0.4, -r * 0.8, -r * 1.25, 0, -r * 1.12); g.bezierCurveTo(r * 0.85, -r * 1.25, r * 1.15, -r * 0.4, r * 0.86, r * 0.42);
        g.quadraticCurveTo(r * 0.98, r * 0.1, r * 0.72, -r * 0.35); g.quadraticCurveTo(r * 0.2, -r * 0.62, -r * 0.1, -r * 0.5); g.quadraticCurveTo(-r * 0.55, -r * 0.62, -r * 0.72, -r * 0.3); g.quadraticCurveTo(-r * 0.95, r * 0.1, -r * 0.86, r * 0.42); g.fill();
        g.strokeStyle = tone(0.4, 0.55); g.lineWidth = r * 0.04; for (let k = 0; k < 3; k++) { const y = -r * (0.95 - k * 0.22); g.beginPath(); g.moveTo(-r * 0.8, y + r * 0.2); g.quadraticCurveTo(-r * 0.4, y - r * 0.08, 0, y + r * 0.04); g.quadraticCurveTo(r * 0.4, y + r * 0.16, r * 0.6, y); g.stroke(); }
        /* a little headband with a bow */
        g.strokeStyle = tone(0.75, 0.8); g.lineWidth = r * 0.07; g.beginPath(); g.moveTo(-r * 0.85, -r * 0.35); g.quadraticCurveTo(0, -r * 1.05, r * 0.85, -r * 0.35); g.stroke(); } });
    g.restore();
  }

  /* Elias at his desk by the ticker, in an eyeshade and sleeve garters; he taps the key. Origin: the desk top under him. */
  function drawElias(g, t, st) {
    const br = Math.sin(t * 1.3) * 0.004, tap = st.talk ? 0 : Math.max(0, Math.sin(t * 9)) * (Math.sin(t * 0.7) > 0 ? 1 : 0);
    /* vest over a white shirt */
    g.fillStyle = lin(g, -0.22, 0, 0.22, 0, [[0, tone(0.6)], [1, tone(0.2)]]);
    g.beginPath(); g.moveTo(-0.19, 0.1); g.bezierCurveTo(-0.22, -0.15, -0.24, -0.32, -0.2, -0.4 - br); g.quadraticCurveTo(0, -0.47 - br, 0.2, -0.4 - br); g.bezierCurveTo(0.24, -0.32, 0.22, -0.15, 0.19, 0.1); g.fill();
    g.fillStyle = lin(g, -0.2, 0, 0.2, 0, [[0, tone(0.2)], [1, tone(0.05)]]);
    g.beginPath(); g.moveTo(-0.17, 0.1); g.lineTo(-0.18, -0.3); g.lineTo(-0.05, -0.42); g.lineTo(0, -0.18); g.lineTo(0.05, -0.42); g.lineTo(0.18, -0.3); g.lineTo(0.17, 0.1); g.fill();
    g.fillStyle = tone(0.6, 0.8); for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(0.012, -0.12 + k * 0.07, 0.008, 0, 7); g.fill(); }
    /* a watch chain, and the bow tie */
    g.strokeStyle = "rgba(240,210,150,.7)"; g.lineWidth = 0.005; g.beginPath(); g.moveTo(0.012, -0.05); g.quadraticCurveTo(0.08, 0, 0.13, -0.06); g.stroke();
    g.fillStyle = tone(0.06); g.beginPath(); g.moveTo(0, -0.445); g.lineTo(-0.05, -0.47); g.lineTo(-0.05, -0.42); g.closePath(); g.moveTo(0, -0.445); g.lineTo(0.05, -0.47); g.lineTo(0.05, -0.42); g.closePath(); g.fill();
    /* one hand on the telegraph key, the other resting on the papers */
    arm(g, [-0.2, -0.36], [-0.3, -0.12], [-0.36, -0.02 - tap * 0.02], 0.065, tone(0.68), 0.62, "rgba(30,20,10,.9)");
    arm(g, [0.2, -0.36], [0.27, -0.1], st.talk ? [0.12 + Math.sin(t * 2) * 0.04, -0.2 + Math.cos(t * 2.6) * 0.03] : [0.16, -0.02], 0.065, tone(0.5), 0.55, "rgba(30,20,10,.9)");
    head(g, { x: 0, y: -0.59 - br, r: 0.108, turn: st.talk ? 0.1 : -0.35, look: st.talk ? st.look : [-0.9, 0.5], tilt: st.talk ? Math.sin(t * 1.7) * 0.03 : -0.06, blink: blinkAt(t, 2), mouth: mouthOf(st), smile: 0.35, brow: st.talk ? 0.4 : 0, skin: 0.76,
      mous: (g, r, tx) => { g.fillStyle = tone(0.1); g.beginPath(); g.moveTo(tx - r * 0.25, r * 0.42); g.quadraticCurveTo(tx, r * 0.3, tx + r * 0.25, r * 0.42); g.quadraticCurveTo(tx, r * 0.38, tx - r * 0.25, r * 0.42); g.fill(); },
      top: (g, r, tx) => { /* slicked hair with a parting */
        g.fillStyle = lin(g, 0, -r, 0, 0, [[0, tone(0.18)], [1, tone(0.05)]]); g.beginPath(); g.moveTo(-r * 0.82, -r * 0.1); g.bezierCurveTo(-r * 0.9, -r * 1.15, r * 0.9, -r * 1.15, r * 0.82, -r * 0.1); g.quadraticCurveTo(r * 0.7, -r * 0.55, r * 0.2, -r * 0.62); g.quadraticCurveTo(-r * 0.5, -r * 0.6, -r * 0.82, -r * 0.1); g.fill();
        g.strokeStyle = tone(0.45, 0.6); g.lineWidth = r * 0.03; g.beginPath(); g.moveTo(-r * 0.3, -r * 1.0); g.quadraticCurveTo(-r * 0.15, -r * 0.8, -r * 0.2, -r * 0.62); g.stroke();
        /* the eyeshade: a band and a translucent brim with lamplight under it */
        g.fillStyle = tone(0.08); g.fillRect(-r * 0.86, -r * 0.62, r * 1.72, r * 0.12);
        g.fillStyle = "rgba(225,190,120,.42)"; g.beginPath(); g.moveTo(-r * 0.95, -r * 0.55); g.quadraticCurveTo(tx, -r * 0.12, r * 0.95, -r * 0.55); g.lineTo(r * 0.86, -r * 0.62); g.lineTo(-r * 0.86, -r * 0.62); g.fill();
        g.strokeStyle = "rgba(250,225,170,.6)"; g.lineWidth = r * 0.025; g.beginPath(); g.moveTo(-r * 0.95, -r * 0.55); g.quadraticCurveTo(tx, -r * 0.12, r * 0.95, -r * 0.55); g.stroke(); } });
  }

  /* the Professor behind his chess table: tweed, waistcoat, round spectacles, a white beard and a pipe */
  function drawProf(g, t, st) {
    const br = Math.sin(t * 1.1) * 0.005, gest = st.talk ? Math.max(0, Math.sin(t * 0.9)) : 0;
    g.fillStyle = lin(g, -0.26, 0, 0.26, 0, [[0, tone(0.36)], [1, tone(0.1)]]);
    g.beginPath(); g.moveTo(-0.24, 0.1); g.bezierCurveTo(-0.27, -0.15, -0.28, -0.33, -0.22, -0.41 - br); g.quadraticCurveTo(0, -0.48 - br, 0.22, -0.41 - br); g.bezierCurveTo(0.28, -0.33, 0.27, -0.15, 0.24, 0.1); g.fill();
    /* tweed: a faint herringbone */
    g.save(); g.clip(); g.strokeStyle = "rgba(255,240,210,.06)"; g.lineWidth = 0.004; for (let y = -0.5; y < 0.1; y += 0.02) { g.beginPath(); for (let x = -0.3; x < 0.3; x += 0.02) { g.lineTo(x, y + ((x * 50) % 2 ? 0.006 : 0)); } g.stroke(); } g.restore();
    g.fillStyle = tone(0.55); g.beginPath(); g.moveTo(-0.08, 0.1); g.lineTo(-0.1, -0.33); g.lineTo(-0.03, -0.44); g.lineTo(0.03, -0.44); g.lineTo(0.1, -0.33); g.lineTo(0.08, 0.1); g.fill();
    g.fillStyle = tone(0.16); g.beginPath(); g.moveTo(-0.08, 0.1); g.lineTo(-0.09, -0.26); g.lineTo(0, -0.12); g.lineTo(0.09, -0.26); g.lineTo(0.08, 0.1); g.fill();
    g.strokeStyle = "rgba(245,215,150,.8)"; g.lineWidth = 0.005; g.beginPath(); g.moveTo(-0.06, -0.02); g.quadraticCurveTo(0, 0.03, 0.07, -0.03); g.stroke();
    /* one hand by the board, the other raised to make a point */
    arm(g, [-0.22, -0.36], [-0.3, -0.08], [-0.16, 0.0], 0.075, tone(0.28), 0.6);
    arm(g, [0.22, -0.36], [0.32, -0.12 - gest * 0.08], [0.22 - gest * 0.02, -0.06 - gest * 0.26], 0.075, tone(0.2), 0.58);
    if (gest > 0.3) { g.strokeStyle = tone(0.6); g.lineWidth = 0.018; g.lineCap = "round"; g.beginPath(); g.moveTo(0.2, -0.33 * gest); g.lineTo(0.19, -0.33 * gest - 0.06); g.stroke(); }
    head(g, { x: 0, y: -0.62 - br, r: 0.112, look: st.look, tilt: st.talk ? Math.sin(t * 1.2) * 0.04 : 0.08 + Math.sin(t * 0.4) * 0.03, blink: blinkAt(t, 3), mouth: mouthOf(st) * 0.7, smile: 0.3, brow: st.talk ? 0.8 : 0.3, skin: 0.74, browTone: 0.85, browW: 0.07,
      mous: (g, r, tx) => { /* the beard and moustache, white, over the chin */
        g.fillStyle = lin(g, 0, r * 0.2, 0, r * 1.4, [[0, tone(0.92)], [1, tone(0.55)]]); g.beginPath(); g.moveTo(-r * 0.72, r * 0.15); g.quadraticCurveTo(-r * 0.75, r * 1.1, tx, r * 1.45); g.quadraticCurveTo(r * 0.75, r * 1.1, r * 0.72, r * 0.15);
        g.quadraticCurveTo(r * 0.5, r * 0.65, tx + r * 0.25, r * 0.62); g.lineTo(tx - r * 0.25, r * 0.62); g.quadraticCurveTo(-r * 0.5, r * 0.65, -r * 0.72, r * 0.15); g.fill();
        g.strokeStyle = "rgba(60,40,20,.25)"; g.lineWidth = r * 0.02; for (let k = -3; k <= 3; k++) { g.beginPath(); g.moveTo(tx + k * r * 0.15, r * 0.7); g.quadraticCurveTo(tx + k * r * 0.17, r * 1.0, tx + k * r * 0.1, r * 1.3); g.stroke(); }
        g.fillStyle = tone(0.95); g.beginPath(); g.moveTo(tx - r * 0.42, r * 0.5); g.quadraticCurveTo(tx, r * 0.28, tx + r * 0.42, r * 0.5); g.quadraticCurveTo(tx, r * 0.42, tx - r * 0.42, r * 0.5); g.fill(); },
      top: (g, r, tx) => { /* bald on top, white at the sides; round spectacles that catch the lamp */
        g.fillStyle = tone(0.72); for (const sd of [-1, 1]) { g.beginPath(); g.ellipse(sd * r * 0.76, -r * 0.25, r * 0.12, r * 0.3, sd * 0.2, 0, 7); g.fill(); }
        g.fillStyle = "rgba(255,245,225,.35)"; g.beginPath(); g.ellipse(-r * 0.2, -r * 0.8, r * 0.3, r * 0.12, -0.3, 0, 7); g.fill();
        g.strokeStyle = tone(0.75); g.lineWidth = r * 0.035;
        for (const sd of [-1, 1]) { g.beginPath(); g.arc(tx + sd * r * 0.33, -r * 0.08, r * 0.2, 0, 7); g.stroke(); }
        g.beginPath(); g.moveTo(tx - r * 0.13, -r * 0.1); g.quadraticCurveTo(tx, -r * 0.16, tx + r * 0.13, -r * 0.1); g.stroke();
        const gl = 0.25 + 0.2 * Math.sin(t * 0.8); g.fillStyle = `rgba(255,245,220,${gl})`; for (const sd of [-1, 1]) { g.beginPath(); g.ellipse(tx + sd * r * 0.33 - r * 0.07, -r * 0.15, r * 0.06, r * 0.03, -0.6, 0, 7); g.fill(); }
        /* the pipe, out of the corner of his mouth */
        if (!st.talk || st.mouth < 0.1) { g.strokeStyle = tone(0.08); g.lineWidth = r * 0.06; g.beginPath(); g.moveTo(tx + r * 0.15, r * 0.5); g.quadraticCurveTo(tx + r * 0.5, r * 0.75, tx + r * 0.62, r * 0.68); g.stroke();
          g.fillStyle = lin(g, tx + r * 0.55, 0, tx + r * 0.8, 0, [[0, tone(0.3)], [1, tone(0.05)]]); g.fillRect(tx + r * 0.55, r * 0.42, r * 0.22, r * 0.3);
          g.fillStyle = `rgba(255,170,90,${0.4 + 0.3 * Math.sin(t * 3)})`; g.fillRect(tx + r * 0.57, r * 0.42, r * 0.18, r * 0.04); } } });
  }
  const PIPE = [0.112 * 0.66, -0.62 + 0.112 * 0.42];   /* where the pipe's smoke rises, relative to his origin */

  /* Sully the newsboy by the door: cap, jacket, knickerbockers, the morning edition under his arm */
  function drawSully(g, t, st) {
    const sh = Math.sin(t * 0.8) * 0.015, cry = !st.talk && ((t % 11) < 1.6), up = cry ? Math.sin(Math.min(1, (t % 11) / 0.3) * Math.PI / 2) : 0, bob = st.talk ? Math.sin(t * 3) * 0.006 : 0;
    g.save(); g.translate(sh, 0);
    /* shoes, socks, knickerbockers */
    for (const sd of [-1, 1]) { const x = sd * 0.08 - (sd > 0 ? sh * 2 : 0);
      g.fillStyle = tone(0.05); g.beginPath(); g.ellipse(x + 0.02, -0.02, 0.07, 0.03, 0, 0, 7); g.fill();
      g.fillStyle = lin(g, x - 0.04, 0, x + 0.04, 0, [[0, tone(0.6)], [1, tone(0.3)]]); g.fillRect(x - 0.04, -0.4, 0.075, 0.37);
      g.strokeStyle = tone(0.35, 0.5); g.lineWidth = 0.008; for (let y = -0.38; y < -0.05; y += 0.04) { g.beginPath(); g.moveTo(x - 0.04, y); g.lineTo(x + 0.035, y); g.stroke(); }
      g.fillStyle = lin(g, x - 0.07, 0, x + 0.07, 0, [[0, tone(0.36)], [1, tone(0.14)]]); g.beginPath(); g.moveTo(x - 0.075, -0.75); g.lineTo(x + 0.075, -0.75); g.quadraticCurveTo(x + 0.09, -0.5, x + 0.06, -0.4); g.quadraticCurveTo(x, -0.37, x - 0.06, -0.4); g.quadraticCurveTo(x - 0.09, -0.5, x - 0.075, -0.75); g.fill(); }
    /* jacket, open over a sweater */
    g.fillStyle = lin(g, -0.2, 0, 0.2, 0, [[0, tone(0.3)], [1, tone(0.08)]]);
    g.beginPath(); g.moveTo(-0.18, -0.68 + bob); g.bezierCurveTo(-0.21, -0.9, -0.21, -1.08, -0.16, -1.15 + bob); g.quadraticCurveTo(0, -1.2 + bob, 0.16, -1.15 + bob); g.bezierCurveTo(0.21, -1.08, 0.21, -0.9, 0.18, -0.68 + bob); g.fill();
    g.fillStyle = tone(0.5); g.beginPath(); g.moveTo(-0.06, -0.7); g.lineTo(-0.07, -1.12 + bob); g.lineTo(0.07, -1.12 + bob); g.lineTo(0.06, -0.7); g.fill();
    g.strokeStyle = tone(0.38, 0.6); g.lineWidth = 0.006; for (let y = -1.08; y < -0.72; y += 0.03) { g.beginPath(); g.moveTo(-0.06, y); g.lineTo(0.06, y); g.stroke(); }
    /* the bundle under his left arm */
    g.save(); g.translate(-0.2, -0.86); g.rotate(-0.15); g.fillStyle = lin(g, 0, -0.08, 0, 0.08, [[0, tone(0.92)], [1, tone(0.62)]]); g.fillRect(-0.09, -0.07, 0.2, 0.14);
    g.strokeStyle = tone(0.4, 0.6); g.lineWidth = 0.004; for (let k = 0; k < 6; k++) { g.beginPath(); g.moveTo(-0.08, -0.06 + k * 0.024); g.lineTo(0.1, -0.06 + k * 0.024); g.stroke(); } g.restore();
    arm(g, [-0.16, -1.1 + bob], [-0.25, -0.95], [-0.12, -0.8], 0.06, tone(0.24), 0.62);
    /* the right arm: at his side, or the paper held high for "Extra!" */
    const hand = cry ? [0.22, -1.3 - up * 0.15] : st.talk ? [0.2 + Math.sin(t * 2.4) * 0.05, -0.92 + Math.cos(t * 1.9) * 0.05] : [0.2, -0.72];
    arm(g, [0.16, -1.1 + bob], cry ? [0.3, -1.15] : [0.24, -0.9], hand, 0.06, tone(0.18), 0.6);
    if (cry) { g.save(); g.translate(hand[0] + 0.02, hand[1] - 0.06); g.rotate(-0.25); g.fillStyle = tone(0.9); g.fillRect(-0.09, -0.12, 0.2, 0.15);
      g.fillStyle = tone(0.2, 0.8); g.fillRect(-0.07, -0.1, 0.16, 0.025); g.fillStyle = tone(0.35, 0.5); for (let k = 0; k < 4; k++) g.fillRect(-0.07, -0.06 + k * 0.022, 0.16, 0.008); g.restore(); }
    head(g, { x: 0, y: -1.3 + bob, r: 0.1, look: st.look, tilt: st.talk ? Math.sin(t * 2.5) * 0.06 : sh * 2, blink: blinkAt(t, 4), mouth: cry ? 0.9 * up : mouthOf(st), smile: 1, brow: cry ? 1 : st.talk ? 0.5 : 0.2, skin: 0.8,
      top: (g, r) => { /* the newsboy cap, big and soft, with a short peak */
        g.fillStyle = lin(g, -r, -r, r, 0, [[0, tone(0.34)], [1, tone(0.1)]]); g.beginPath(); g.moveTo(-r * 0.95, -r * 0.42); g.bezierCurveTo(-r * 1.25, -r * 1.35, r * 1.35, -r * 1.45, r * 1.12, -r * 0.5); g.quadraticCurveTo(0, -r * 0.62, -r * 0.95, -r * 0.42); g.fill();
        g.fillStyle = tone(0.05); g.beginPath(); g.moveTo(-r * 0.8, -r * 0.48); g.quadraticCurveTo(r * 0.3, -r * 0.7, r * 1.15, -r * 0.48); g.quadraticCurveTo(r * 0.4, -r * 0.25, -r * 0.8, -r * 0.48); g.fill();
        g.fillStyle = tone(0.5); g.beginPath(); g.arc(r * 0.1, -r * 1.18, r * 0.06, 0, 7); g.fill();
        g.fillStyle = "rgba(120,80,40,.35)"; for (const [x, y] of [[-0.35, 0.2], [-0.28, 0.25], [0.35, 0.2], [0.42, 0.24], [-0.4, 0.27]]) { g.beginPath(); g.arc(x * r, y * r, r * 0.02, 0, 7); g.fill(); } } });
    g.restore();
  }

  /* ============ the rooms ============ */
  /* each room: layers baked once per size at a depth (they shift with the reader's head), live parts drawn on every frame,
     a regular standing at a depth, things to click, and how the café sounds from there */
  const clockHM = tz => { try { const p = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "numeric", minute: "numeric", hour12: false }).formatToParts(new Date()); const v = k => +(p.find(x => x.type === k) || {}).value || 0; return [v("hour"), v("minute")]; } catch (e) { return [8, 0]; } };
  const TALLY = { at: null };
  const AREAS = {
    window: { mix: { street: 1, music: 1 } },

    counter: {
      mix: { street: 0.55, music: 0.85 },
      layers: [
        { z: ZB, draw(g, G) {
          walls(g, G, { pools: [[-1.3, 4.2], [1.6, 4.2]], seed: 11, lamps: [[-1.3, 4.4], [1.6, 4.4]], wain: 0.9 });
          const { P } = G;
          /* the back bar: a long mirror, shelves of cups, gold lettering */
          quad(g, P, [[-2.6, 1.0, ZB - 0.02], [1.0, 1.0, ZB - 0.02], [1.0, 2.5, ZB - 0.02], [-2.6, 2.5, ZB - 0.02]], tone(0.04));
          const [mx0, my0] = P(-2.45, 2.4, ZB - 0.03), [mx1, my1] = P(0.85, 1.12, ZB - 0.03);
          g.fillStyle = lin(g, mx0, my0, mx1, my1, [[0, tone(0.3, 0.9)], [0.45, tone(0.14, 0.9)], [0.55, tone(0.24, 0.9)], [1, tone(0.1, 0.9)]]); g.fillRect(mx0, my0, mx1 - mx0, my1 - my0);
          g.save(); g.globalCompositeOperation = "screen"; g.fillStyle = "rgba(255,235,200,.06)"; for (let k = 0; k < 4; k++) { const x = mx0 + (mx1 - mx0) * (0.1 + k * 0.25); g.beginPath(); g.moveTo(x, my0); g.lineTo(x + 25, my0); g.lineTo(x - 30, my1); g.lineTo(x - 55, my1); g.fill(); } g.restore();
          for (const Y of [1.55, 2.0]) { quad(g, P, [[-2.45, Y, ZB - 0.05], [0.85, Y, ZB - 0.05], [0.85, Y + 0.03, ZB - 0.05], [-2.45, Y + 0.03, ZB - 0.05]], tone(0.35));
            for (let X = -2.35; X < 0.8; X += 0.17) { const [cx, cy] = P(X, Y + 0.03, ZB - 0.06), s = G.s(ZB);
              g.fillStyle = lin(g, cx - s * 0.05, 0, cx + s * 0.05, 0, [[0, tone(0.55)], [0.4, tone(0.9)], [1, tone(0.45)]]); g.fillRect(cx - s * 0.045, cy - s * 0.09, s * 0.09, s * 0.09); } }
          text(g, "CAFÉ · LUNCHEON · PASTRY", ...P(-0.8, 2.75, ZB), G.s(ZB) * 0.18, { w: 700, fill: lin(g, 0, P(0, 2.85, ZB)[1], 0, P(0, 2.65, ZB)[1], [[0, "rgba(250,225,160,.8)"], [1, "rgba(190,150,80,.75)"]]), stroke: "rgba(0,0,0,.5)" });
          /* the house-rules board: chalk on slate in a wooden frame */
          quad(g, P, [[1.35, 1.25, ZB - 0.02], [3.25, 1.25, ZB - 0.02], [3.25, 2.75, ZB - 0.02], [1.35, 2.75, ZB - 0.02]], tone(0.24));
          quad(g, P, [[1.42, 1.32, ZB - 0.03], [3.18, 1.32, ZB - 0.03], [3.18, 2.68, ZB - 0.03], [1.42, 2.68, ZB - 0.03]], lin(g, 0, P(0, 2.7, ZB)[1], 0, P(0, 1.3, ZB)[1], [[0, "#1e1d1a"], [1, "#151412"]]));
          g.save(); g.globalAlpha = 0.08; g.fillStyle = "#fff"; const [bx0, by0] = P(1.45, 2.65, ZB), [bx1, by1] = P(3.15, 1.35, ZB); for (let k = 0; k < 14; k++) { g.beginPath(); g.ellipse(bx0 + (bx1 - bx0) * ((k * 0.37) % 1), by0 + (by1 - by0) * ((k * 0.61) % 1), 30, 6, 0.3, 0, 7); g.fill(); } g.restore();
          const B = TX.board, cs = G.s(ZB) * 0.11, chalk = "rgba(235,232,222,.85)", bxL = P(1.55, 0, ZB)[0], bw = P(3.08, 0, ZB)[0] - bxL;
          text(g, B[0].toUpperCase(), ...P(2.3, 2.52, ZB), cs * 1.35, { w: 700, fill: chalk, face: "'Special Elite', 'Courier New', monospace", max: bw });
          for (let k = 1; k <= 5; k++) text(g, B[k], bxL, P(0, 2.33 - (k - 1) * 0.16, ZB)[1], cs, { al: "left", fill: "rgba(230,226,215,.75)", face: "'Special Elite', 'Courier New', monospace", max: bw });
          g.strokeStyle = "rgba(230,226,215,.5)"; g.lineWidth = 1; const [ux0, uy] = P(1.55, 1.6, ZB), [ux1] = P(3.05, 1.6, ZB); g.beginPath(); g.moveTo(ux0, uy); g.lineTo(ux1, uy); g.stroke();
          text(g, B[6], bxL, P(0, 1.5, ZB)[1], cs, { al: "left", fill: "rgba(240,236,225,.9)", face: "'Special Elite', 'Courier New', monospace", max: bw });
          /* the urn on the back counter */
          box(g, G, -2.7, 1.1, 0, 0.95, ZB - 0.6, ZB - 0.05, { front: tone(0.07), top: tone(0.35), side: tone(0.04) });
        }, live(g, G, t) {
          const { P } = G, cs = G.s(ZB) * 0.11;
          if (ST.task === "chalk") { const [gx, gy] = P(2.3, 2.0, ZB); g.save(); g.globalCompositeOperation = "screen"; glow(g, gx, gy, G.s(ZB) * 1.4, 0.12 + 0.06 * Math.sin(t * 3)); g.restore(); }
          /* the chalk: tally marks for pie on Fridays, one by one while Mae explains, and then "Carried" */
          const n = TALLY.at == null ? 2 : Math.min(7, 2 + Math.floor((performance.now() - TALLY.at) / 900));
          const [x0, y] = P(2.35, 1.4, ZB); g.strokeStyle = "rgba(240,236,225,.85)"; g.lineWidth = Math.max(1, cs * 0.09); g.lineCap = "round";
          for (let k = 0; k < n; k++) { const grp = Math.floor(k / 5), j = k % 5, x = x0 + grp * cs * 2.2 + j * cs * 0.32;
            g.beginPath(); if (j < 4) { g.moveTo(x, y - cs * 0.45); g.lineTo(x + cs * 0.05, y + cs * 0.4); } else { g.moveTo(x0 + grp * cs * 2.2 - cs * 0.15, y + cs * 0.3); g.lineTo(x0 + grp * cs * 2.2 + cs * 1.35, y - cs * 0.3); } g.stroke(); }
          if (n >= 7) { const a = Math.min(1, (performance.now() - TALLY.at - 6000) / 800); if (a > 0) text(g, "✓ " + TX.board[7], P(1.55, 0, ZB)[0], P(0, 1.4, ZB)[1], cs * 1.05, { al: "left", fill: `rgba(240,236,225,${0.9 * a})`, face: "'Special Elite', 'Courier New', monospace" }); }
          /* the urn: brass, a gauge, a little steam */
          const [ux, uy] = P(-1.9, 0.95, ZB - 0.35), s = G.s(ZB - 0.35);
          g.fillStyle = lin(g, ux - s * 0.25, 0, ux + s * 0.25, 0, [[0, "#5a4426"], [0.3, "#d8b878"], [0.5, "#f2dca8"], [1, "#4a3418"]]);
          g.beginPath(); g.moveTo(ux - s * 0.22, uy); g.lineTo(ux - s * 0.24, uy - s * 0.7); g.quadraticCurveTo(ux, uy - s * 1.05, ux + s * 0.24, uy - s * 0.7); g.lineTo(ux + s * 0.22, uy); g.fill();
          g.fillStyle = "#e8cf98"; g.beginPath(); g.arc(ux, uy - s * 1.0, s * 0.05, 0, 7); g.fill();
          g.fillStyle = tone(0.85); g.beginPath(); g.arc(ux, uy - s * 0.45, s * 0.07, 0, 7); g.fill(); g.strokeStyle = tone(0.1); g.lineWidth = 1; g.beginPath(); g.moveTo(ux, uy - s * 0.45); g.lineTo(ux + s * 0.05 * Math.cos(t), uy - s * 0.45 + s * 0.05 * Math.sin(t)); g.stroke();
          g.fillStyle = "#3a2a14"; g.fillRect(ux + s * 0.2, uy - s * 0.2, s * 0.12, s * 0.04);
          for (let k = 0; k < 10; k++) { const u = (t * 0.22 + k / 10) % 1; puff(g, ux + Math.sin(t * 0.8 + k * 1.7) * s * 0.05 * (1 + u * 2), uy - s * (1.05 + u * 0.7), s * (0.06 + u * 0.18), 0.12 * Math.sin(u * Math.PI)); }
        } },
        { z: 2.3, draw(g, G) {
          /* the counter: mahogany panels, a marble top, a brass foot rail; the register and a pie under glass on it */
          box(g, G, -3.4, 3.4, 0, 1.05, 2.3, 2.9, { front: lin(g, 0, G.P(0, 1.05, 2.3)[1], 0, G.H, [[0, tone(0.2)], [0.1, tone(0.13)], [1, tone(0.04)]]), top: lin(g, 0, G.P(0, 1.05, 2.9)[1], 0, G.P(0, 1.05, 2.3)[1], [[0, tone(0.55)], [1, tone(0.72)]]) });
          const { P } = G;
          quad(g, P, [[-3.4, 1.0, 2.28], [3.4, 1.0, 2.28], [3.4, 1.06, 2.28], [-3.4, 1.06, 2.28]], tone(0.75));
          for (let X = -3.2; X < 3.4; X += 0.8) { quad(g, P, [[X + 0.08, 0.15, 2.29], [X + 0.72, 0.15, 2.29], [X + 0.72, 0.9, 2.29], [X + 0.08, 0.9, 2.29]], tone(0.16));
            g.strokeStyle = tone(0.28, 0.6); g.lineWidth = 1; const a = P(X + 0.08, 0.9, 2.29), b = P(X + 0.72, 0.15, 2.29); g.strokeRect(a[0], a[1], b[0] - a[0], b[1] - a[1]); }
          g.strokeStyle = lin(g, 0, P(0, 0.22, 2.1)[1] - 3, 0, P(0, 0.22, 2.1)[1] + 3, [[0, "#f2dca8"], [1, "#5a4426"]]); g.lineWidth = Math.max(2, G.s(2.1) * 0.035); const r0 = P(-3.4, 0.22, 2.1), r1 = P(3.4, 0.22, 2.1); g.beginPath(); g.moveTo(...r0); g.lineTo(...r1); g.stroke();
          /* the register */
          { const [x, y] = P(1.5, 1.06, 2.55), s = G.s(2.55);
            g.fillStyle = lin(g, x - s * 0.22, 0, x + s * 0.22, 0, [[0, "#3a2a14"], [0.4, "#b89458"], [1, "#2a1c0c"]]); g.beginPath(); g.moveTo(x - s * 0.22, y); g.lineTo(x - s * 0.2, y - s * 0.28); g.lineTo(x - s * 0.12, y - s * 0.42); g.lineTo(x + s * 0.12, y - s * 0.42); g.lineTo(x + s * 0.2, y - s * 0.28); g.lineTo(x + s * 0.22, y); g.fill();
            g.fillStyle = tone(0.85); g.fillRect(x - s * 0.08, y - s * 0.4, s * 0.16, s * 0.07); g.fillStyle = tone(0.15); text(g, "0.00", x, y - s * 0.365, s * 0.05, { fill: tone(0.1), face: "'Special Elite', monospace" });
            for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++) { g.fillStyle = tone(0.85); g.beginPath(); g.arc(x - s * 0.14 + c * s * 0.07, y - s * 0.2 + r * s * 0.055, s * 0.018, 0, 7); g.fill(); } }
          /* lemon pie under a glass dome */
          { const [x, y] = P(-1.15, 1.06, 2.55), s = G.s(2.55);
            g.fillStyle = tone(0.75); g.beginPath(); g.ellipse(x, y, s * 0.2, s * 0.03, 0, 0, 7); g.fill(); g.fillRect(x - s * 0.02, y - s * 0.04, s * 0.04, s * 0.04);
            g.fillStyle = lin(g, 0, y - s * 0.12, 0, y - s * 0.04, [[0, tone(0.95)], [1, tone(0.6)]]); g.beginPath(); g.ellipse(x, y - s * 0.07, s * 0.15, s * 0.04, 0, 0, 7); g.fill(); g.fillRect(x - s * 0.15, y - s * 0.07, s * 0.3, s * 0.03);
            g.strokeStyle = "rgba(255,245,225,.35)"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x - s * 0.18, y - s * 0.04); g.bezierCurveTo(x - s * 0.18, y - s * 0.38, x + s * 0.18, y - s * 0.38, x + s * 0.18, y - s * 0.04); g.stroke();
            g.fillStyle = "rgba(255,245,225,.07)"; g.fill(); g.fillStyle = "rgba(255,250,235,.4)"; g.beginPath(); g.ellipse(x - s * 0.1, y - s * 0.2, s * 0.02, s * 0.08, 0.2, 0, 7); g.fill(); }
          /* a cup and saucer waiting on the marble */
          { const [x, y] = P(0.75, 1.06, 2.45), s = G.s(2.45); g.fillStyle = tone(0.85); g.beginPath(); g.ellipse(x, y, s * 0.08, s * 0.018, 0, 0, 7); g.fill(); g.fillStyle = tone(0.95); g.fillRect(x - s * 0.04, y - s * 0.06, s * 0.08, s * 0.05); }
        } },
        { z: 1.7, draw(g, G) {
          /* stools in the foreground, out of focus: red leather gone sepia, chrome posts */
          for (const X of [-1.5, 0.45, 2.4]) { const [x, y] = G.P(X, 0.78, 1.7), s = G.s(1.7);
            g.save(); g.fillStyle = tone(0.55, 0.9); g.fillRect(x - s * 0.02, y, s * 0.04, G.H - y);
            g.fillStyle = lin(g, 0, y - s * 0.08, 0, y + s * 0.06, [[0, tone(0.3)], [1, tone(0.03)]]); g.beginPath(); g.ellipse(x, y, s * 0.2, s * 0.06, 0, 0, 7); g.fill(); g.fillRect(x - s * 0.2, y, s * 0.4, s * 0.05);
            g.fillStyle = tone(0.65, 0.5); g.beginPath(); g.ellipse(x - s * 0.06, y - s * 0.02, s * 0.08, s * 0.015, 0, 0, 7); g.fill(); g.restore(); }
        } },
      ],
      person: { id: "mae", X: 0.2, Y: 1.05, z: 2.65, draw: drawMae, head: [0, -0.6] },
      props: [{ id: "urn", X: -1.9, Y: 1.3, z: ZB - 0.35, w: 0.6, h: 1.2 }, { id: "pie", X: -1.15, Y: 1.2, z: 2.55, w: 0.45, h: 0.4 }, { id: "register", X: 1.5, Y: 1.25, z: 2.55, w: 0.5, h: 0.5 }, { id: "board", X: 2.3, Y: 2.0, z: ZB, w: 1.9, h: 1.5 }],
    },

    wire: {
      mix: { street: 0.4, music: 0.7 },
      layers: [
        { z: ZB, draw(g, G) {
          walls(g, G, { pools: [[0.3, 4.4, 0.8], [-1.7, 4.2, 0.5]], seed: 23, lamps: [[0.3, 4.6, 2.8, 0.8]], sconces: [[-2.8, 2.2]] });
          const { P } = G;
          text(g, TX.wireSign.toUpperCase(), ...P(0.2, 3.05, ZB), G.s(ZB) * 0.15, { w: 700, fill: "rgba(240,215,160,.8)", stroke: "rgba(0,0,0,.5)", face: "Georgia, 'Noto Serif SC', serif" });
          /* a cork board with pinned telegrams */
          quad(g, P, [[1.2, 1.3, ZB - 0.02], [2.9, 1.3, ZB - 0.02], [2.9, 2.4, ZB - 0.02], [1.2, 2.4, ZB - 0.02]], tone(0.3)); quad(g, P, [[1.26, 1.36, ZB - 0.03], [2.84, 1.36, ZB - 0.03], [2.84, 2.34, ZB - 0.03], [1.26, 2.34, ZB - 0.03]], tone(0.22));
          const R = rnd(4); for (let k = 0; k < 9; k++) { const X = 1.35 + R() * 1.25, Y = 1.45 + R() * 0.65, [x, y] = P(X, Y + 0.22, ZB - 0.04), s = G.s(ZB);
            g.save(); g.translate(x, y); g.rotate((R() - 0.5) * 0.2); g.fillStyle = tone(0.72 + R() * 0.15); g.fillRect(0, 0, s * 0.32, s * 0.2); g.fillStyle = tone(0.3, 0.5); for (let l = 0; l < 4; l++) g.fillRect(s * 0.03, s * (0.04 + l * 0.04), s * 0.26 * (0.6 + R() * 0.4), s * 0.012);
            g.fillStyle = tone(0.1); g.beginPath(); g.arc(s * 0.16, s * 0.02, s * 0.015, 0, 7); g.fill(); g.restore(); }
          /* the ticker's pedestal and the telegraph table */
          box(g, G, -2.0, -1.1, 0, 0.95, 3.3, 3.9, { front: tone(0.1), top: tone(0.3) });
        }, live(g, G, t) {
          /* four clocks for four cities, with the real time there */
          const { P } = G; TX.clocks.forEach((name, i) => { const tz = ["America/New_York", "Europe/London", "Europe/Berlin", "Asia/Tokyo"][i], X = -1.1 + i * 0.75, [x, y] = P(X, 2.3, ZB - 0.02), r = G.s(ZB) * 0.24, [h, m] = clockHM(tz);
            g.fillStyle = tone(0.08); g.beginPath(); g.arc(x, y, r * 1.12, 0, 7); g.fill(); g.fillStyle = lin(g, x - r, y - r, x + r, y + r, [[0, tone(0.85)], [1, tone(0.62)]]); g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
            g.fillStyle = tone(0.15); for (let k = 0; k < 12; k++) { const a = k / 12 * 6.283; g.fillRect(x + Math.cos(a) * r * 0.82 - 1, y + Math.sin(a) * r * 0.82 - 1, 2, 2); }
            const hand = (a, l, w) => { g.strokeStyle = tone(0.05); g.lineWidth = w; g.lineCap = "round"; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.sin(a) * l, y - Math.cos(a) * l); g.stroke(); };
            hand(((h % 12) + m / 60) / 12 * 6.283, r * 0.5, Math.max(1.5, r * 0.08)); hand(m / 60 * 6.283, r * 0.75, Math.max(1, r * 0.05));
            text(g, name.toUpperCase(), x, y + r * 1.45, r * 0.32, { w: 700, fill: tone(0.7), max: r * 3 }); });
          /* the ticker under its glass bell, printing; the tape runs down into a basket */
          const [tx, ty] = P(-1.55, 0.95, 3.6), s = G.s(3.6), h = live(), msg = TX.tape(h).repeat(3);
          g.fillStyle = lin(g, tx - s * 0.2, 0, tx + s * 0.2, 0, [[0, "#3a2a14"], [0.45, "#c8a868"], [1, "#2a1c0c"]]); g.fillRect(tx - s * 0.18, ty - s * 0.12, s * 0.36, s * 0.12);
          g.fillStyle = tone(0.12); g.fillRect(tx - s * 0.12, ty - s * 0.32, s * 0.24, s * 0.2);
          g.fillStyle = "#d8b878"; g.beginPath(); g.arc(tx, ty - s * 0.36, s * 0.09, 0, 7); g.fill(); g.fillStyle = tone(0.1); g.save(); g.translate(tx, ty - s * 0.36); g.rotate(t * 4); g.fillRect(-s * 0.08, -s * 0.008, s * 0.16, s * 0.016); g.restore();
          g.strokeStyle = "rgba(255,245,225,.3)"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(tx - s * 0.2, ty - s * 0.12); g.bezierCurveTo(tx - s * 0.22, ty - s * 0.7, tx + s * 0.22, ty - s * 0.7, tx + s * 0.2, ty - s * 0.12); g.stroke();
          g.fillStyle = "rgba(255,250,235,.35)"; g.beginPath(); g.ellipse(tx - s * 0.12, ty - s * 0.4, s * 0.02, s * 0.1, 0.2, 0, 7); g.fill();
          /* the tape: out of the machine to the right, then curling down into the basket */
          const tw = s * 0.06, off = (t * s * 0.12) % (s * 10);
          g.save(); g.fillStyle = tone(0.88); g.beginPath(); g.moveTo(tx + s * 0.1, ty - s * 0.2); g.lineTo(tx + s * 0.45, ty - s * 0.2); g.quadraticCurveTo(tx + s * 0.62, ty - s * 0.18, tx + s * 0.6, ty + s * 0.15); g.lineTo(tx + s * 0.56, ty + s * 0.6); g.lineTo(tx + s * 0.5, ty + s * 0.6); g.lineTo(tx + s * 0.54, ty + s * 0.15); g.quadraticCurveTo(tx + s * 0.55, ty - s * 0.14, tx + s * 0.45, ty - s * 0.14); g.lineTo(tx + s * 0.1, ty - s * 0.14); g.fill();
          g.beginPath(); g.rect(tx + s * 0.1, ty - s * 0.2, s * 0.36, tw); g.clip(); g.font = `${tw * 0.75}px 'Special Elite', 'Courier New', monospace`; g.textBaseline = "middle"; g.fillStyle = tone(0.1);
          g.fillText(msg, tx + s * 0.46 - g.measureText(msg).width + off % g.measureText(TX.tape(h)).width, ty - s * 0.17); g.restore();
          /* the basket of tape */
          const [bx, by] = P(-0.95, 0, 3.1), bs = G.s(3.1); g.fillStyle = lin(g, bx - bs * 0.2, 0, bx + bs * 0.2, 0, [[0, tone(0.3)], [1, tone(0.1)]]); g.beginPath(); g.moveTo(bx - bs * 0.2, by - bs * 0.32); g.lineTo(bx + bs * 0.2, by - bs * 0.32); g.lineTo(bx + bs * 0.16, by); g.lineTo(bx - bs * 0.16, by); g.fill();
          g.strokeStyle = tone(0.45, 0.5); g.lineWidth = 1; for (let k = 0; k < 5; k++) { g.beginPath(); g.moveTo(bx - bs * 0.19, by - bs * 0.3 + k * bs * 0.06); g.lineTo(bx + bs * 0.19, by - bs * 0.3 + k * bs * 0.06); g.stroke(); }
          g.strokeStyle = tone(0.85, 0.9); g.lineWidth = Math.max(2, bs * 0.03); for (let k = 0; k < 6; k++) { g.beginPath(); g.ellipse(bx + Math.sin(k * 2) * bs * 0.07, by - bs * 0.34 - k * bs * 0.012, bs * 0.08, bs * 0.03, k, 0, 5); g.stroke(); }
        } },
        { z: 2.45, draw(g, G) {
          /* Elias's desk: the telegraph key, a banker's lamp, papers and a spike of telegrams */
          box(g, G, -0.75, 1.3, 0, 0.78, 2.45, 3.05, { front: lin(g, 0, G.P(0, 0.78, 2.45)[1], 0, G.H, [[0, tone(0.18)], [1, tone(0.04)]]), top: tone(0.36) });
          const { P } = G;
          { const [x, y] = P(-0.3, 0.78, 2.7), s = G.s(2.7); g.fillStyle = tone(0.12); g.fillRect(x - s * 0.12, y - s * 0.03, s * 0.24, s * 0.03);
            g.fillStyle = "#c8a868"; g.fillRect(x - s * 0.09, y - s * 0.06, s * 0.16, s * 0.02); g.fillStyle = tone(0.05); g.beginPath(); g.arc(x + s * 0.08, y - s * 0.06, s * 0.025, 0, 7); g.fill(); }
          { const [x, y] = P(0.95, 0.78, 2.8), s = G.s(2.8); g.fillStyle = "#c8a868"; g.fillRect(x - s * 0.015, y - s * 0.3, s * 0.03, s * 0.3); g.fillRect(x - s * 0.08, y - s * 0.02, s * 0.16, s * 0.02);
            g.fillStyle = lin(g, 0, y - s * 0.4, 0, y - s * 0.3, [[0, tone(0.45)], [1, tone(0.18)]]); g.beginPath(); g.moveTo(x - s * 0.2, y - s * 0.3); g.quadraticCurveTo(x, y - s * 0.45, x + s * 0.2, y - s * 0.3); g.fill();
            glow(g, x, y - s * 0.2, s * 0.8, 0.25); g.fillStyle = "rgba(255,240,200,.8)"; g.fillRect(x - s * 0.17, y - s * 0.305, s * 0.34, s * 0.015); }
          { const [x, y] = P(0.45, 0.78, 2.7), s = G.s(2.7); g.save(); g.translate(x, y); g.rotate(-0.05); g.fillStyle = tone(0.8); g.fillRect(-s * 0.2, -s * 0.02, s * 0.32, s * 0.02); g.fillStyle = tone(0.7); g.fillRect(-s * 0.16, -s * 0.035, s * 0.3, s * 0.015); g.restore(); }
        } },
        { z: 1.4, draw(g, G) {
          /* a hat stand close by, out of focus */
          const [x, y] = G.P(2.1, 0, 1.4), s = G.s(1.4); g.save(); g.fillStyle = tone(0.04); g.fillRect(x - s * 0.025, G.P(0, 1.9, 1.4)[1], s * 0.05, G.H);
          g.beginPath(); g.ellipse(x - s * 0.1, G.P(0, 1.85, 1.4)[1], s * 0.22, s * 0.07, 0, 0, 7); g.fill(); g.fillRect(x - s * 0.22, G.P(0, 1.95, 1.4)[1], s * 0.24, s * 0.11); g.restore();
        } },
      ],
      person: { id: "elias", X: 0.2, Y: 0.78, z: 2.85, draw: drawElias, head: [0, -0.61] },
      props: [{ id: "ticker", X: -1.45, Y: 1.15, z: 3.6, w: 0.8, h: 0.7 }, { id: "clocks", X: 0.0, Y: 2.3, z: ZB, w: 3.0, h: 0.8 }],
    },

    back: {
      mix: { street: 0.25, music: 2.4 },
      layers: [
        { z: ZB, draw(g, G) {
          walls(g, G, { pools: [[0, 3.0, 1.3]], seed: 41, lamps: [[0, 3.2, 2.15, 1.25]], wain: 0.95 });
          const { P } = G;
          /* bookshelves to both sides */
          for (const [a, b] of [[-3.6, -1.3], [1.5, 3.6]]) { quad(g, P, [[a, 0, ZB - 0.3], [b, 0, ZB - 0.3], [b, 2.9, ZB - 0.3], [a, 2.9, ZB - 0.3]], tone(0.05));
            const R = rnd(Math.round(a * 10 + 50)); for (let Y = 0.2; Y < 2.7; Y += 0.42) { quad(g, P, [[a + 0.05, Y, ZB - 0.32], [b - 0.05, Y, ZB - 0.32], [b - 0.05, Y + 0.03, ZB - 0.32], [a + 0.05, Y + 0.03, ZB - 0.32]], tone(0.2));
              for (let X = a + 0.08; X < b - 0.1;) { const w = 0.04 + R() * 0.05, h = 0.25 + R() * 0.1; quad(g, P, [[X, Y + 0.03, ZB - 0.33], [X + w, Y + 0.03, ZB - 0.33], [X + w, Y + 0.03 + h, ZB - 0.33], [X, Y + 0.03 + h, ZB - 0.33]], tone(0.1 + R() * 0.22)); X += w + 0.005; } } }
          /* a slate with logic on it */
          quad(g, P, [[-0.9, 1.5, ZB - 0.02], [0.9, 1.5, ZB - 0.02], [0.9, 2.55, ZB - 0.02], [-0.9, 2.55, ZB - 0.02]], tone(0.2));
          quad(g, P, [[-0.84, 1.56, ZB - 0.03], [0.84, 1.56, ZB - 0.03], [0.84, 2.49, ZB - 0.03], [-0.84, 2.49, ZB - 0.03]], "#191816");
          const cs = G.s(ZB) * 0.12, ch = "rgba(232,228,218,.78)"; TX.logic.forEach((l, i) => text(g, l, P(-0.72, 0, ZB)[0], P(0, 2.33 - i * 0.22, ZB)[1], cs, { al: "left", fill: ch, face: "'Special Elite', 'Courier New', monospace", it: i === 3, max: P(0.72, 0, ZB)[0] - P(-0.72, 0, ZB)[0] }));
          /* the gramophone cabinet */
          box(g, G, -2.9, -1.9, 0, 0.9, 4.4, 5.0, { front: tone(0.1), top: tone(0.32) });
        }, live(g, G, t) {
          /* the gramophone: the record turns, the horn shines */
          const [x, y] = G.P(-2.4, 0.9, 4.7), s = G.s(4.7);
          g.fillStyle = tone(0.15); g.fillRect(x - s * 0.22, y - s * 0.1, s * 0.44, s * 0.1);
          g.save(); g.translate(x, y - s * 0.12); g.scale(1, 0.3); g.fillStyle = "#0e0c0a"; g.beginPath(); g.arc(0, 0, s * 0.2, 0, 7); g.fill();
          g.strokeStyle = "rgba(255,240,210,.12)"; g.lineWidth = 1; for (let k = 1; k < 6; k++) { g.beginPath(); g.arc(0, 0, s * 0.035 * k, 0, 7); g.stroke(); }
          g.rotate(t * 3.5); g.fillStyle = tone(0.7); g.beginPath(); g.arc(0, 0, s * 0.05, 0, 7); g.fill(); g.fillStyle = tone(0.2); g.fillRect(-s * 0.04, -s * 0.004, s * 0.03, s * 0.008); g.restore();
          g.strokeStyle = "#c8a868"; g.lineWidth = Math.max(1.5, s * 0.015); g.beginPath(); g.moveTo(x + s * 0.18, y - s * 0.14); g.lineTo(x + s * 0.06, y - s * 0.15); g.stroke();
          /* the horn: a brass tube up from the tone arm, flaring into a bell that faces the room */
          const bx = x - s * 0.26, by = y - s * 0.72, br2 = s * 0.27;
          g.strokeStyle = lin(g, x, y, bx, by, [[0, "#5a4426"], [1, "#c8a868"]]); g.lineWidth = Math.max(2, s * 0.035); g.lineCap = "round"; g.beginPath(); g.moveTo(x + s * 0.17, y - s * 0.16); g.quadraticCurveTo(x + s * 0.2, y - s * 0.42, x - s * 0.02, y - s * 0.5); g.stroke();
          g.fillStyle = lin(g, x - s * 0.02, y - s * 0.5, bx, by, [[0, "#6a5030"], [0.6, "#d8b878"], [1, "#f2dca8"]]); g.beginPath(); g.moveTo(x - s * 0.01, y - s * 0.52); g.lineTo(bx + br2 * 0.7, by + br2 * 0.72); g.lineTo(bx - br2 * 0.7, by - br2 * 0.72); g.lineTo(x - s * 0.04, y - s * 0.48); g.fill();
          g.save(); g.translate(bx, by); g.rotate(-0.78); g.fillStyle = rad(g, 0, 0, br2 * 0.1, br2, [[0, "#140e08"], [0.55, "#3a2a14"], [0.85, "#b89458"], [1, "#f2dca8"]]); g.beginPath(); g.ellipse(0, 0, br2 * 0.45, br2, 0, 0, 7); g.fill();
          g.strokeStyle = "rgba(255,240,200,.6)"; g.lineWidth = 1.5; g.stroke(); g.restore();
          /* music in the air: notes rising from the horn, now and then */
          if (AUDIO.on()) for (let k = 0; k < 3; k++) { const u = ((t * 0.18) + k / 3) % 1; text(g, k % 2 ? "♪" : "♫", x - s * (0.4 + u * 0.3), y - s * (0.95 + u * 0.6), s * 0.1, { fill: `rgba(240,225,190,${0.35 * Math.sin(u * Math.PI)})` }); }
        } },
        { z: 2.3, draw(g, G) {
          /* the chess table under the lamp: a small round top, the board in perspective, the pieces mid-game */
          const { P } = G, top = 0.74;
          { const [x, y] = P(0.05, top, 2.35), s = G.s(2.35); g.fillStyle = tone(0.06); g.fillRect(x - s * 0.05, y, s * 0.1, G.H - y);
            g.fillStyle = lin(g, 0, y - s * 0.08, 0, y + s * 0.06, [[0, tone(0.42)], [1, tone(0.12)]]); g.beginPath(); g.ellipse(x, y, s * 0.55, s * 0.12, 0, 0, 7); g.fill(); g.fillStyle = tone(0.06); g.fillRect(x - s * 0.55, y, s * 1.1, s * 0.04); }
          const sq = 0.055; for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) { const X = -0.17 + c * sq, z = 2.5 - r * sq * 0.7; quad(g, P, [[X, top + 0.002, z], [X + sq, top + 0.002, z], [X + sq, top + 0.002, z - sq * 0.7], [X, top + 0.002, z - sq * 0.7]], (r + c) % 2 ? tone(0.15) : tone(0.75)); }
          const pcs = [[1, 6, 0.9], [2, 5, 0.9], [4, 4, 0.12], [5, 6, 0.12], [6, 2, 0.9], [3, 1, 0.12], [0, 3, 0.9], [7, 5, 0.12]];
          pcs.forEach(([c, r, col], i) => { const X = -0.17 + (c + 0.5) * sq, z = 2.5 - (r + 0.5) * sq * 0.7, [x, y] = P(X, top, z), s = G.s(z), h = s * (i === 0 ? 0.075 : 0.05);
            g.fillStyle = lin(g, x - s * 0.02, 0, x + s * 0.02, 0, [[0, tone(col + 0.08)], [1, tone(col - 0.1)]]); g.beginPath(); g.moveTo(x - s * 0.018, y); g.lineTo(x - s * 0.01, y - h); g.lineTo(x + s * 0.01, y - h); g.lineTo(x + s * 0.018, y); g.fill(); g.beginPath(); g.arc(x, y - h, s * 0.013, 0, 7); g.fill(); });
        } },
        { z: 1.3, draw(g, G) {
          /* an armchair's wing close by on the left, out of focus */
          const [x, y] = G.P(-1.55, 1.1, 1.3), s = G.s(1.3); g.save();
          g.fillStyle = lin(g, x - s * 0.3, 0, x + s * 0.3, 0, [[0, tone(0.02)], [1, tone(0.16)]]); g.beginPath(); g.moveTo(x - s * 0.4, G.H); g.lineTo(x - s * 0.35, y); g.quadraticCurveTo(x, y - s * 0.25, x + s * 0.25, y + s * 0.05); g.lineTo(x + s * 0.3, G.H); g.fill(); g.restore();
        } },
      ],
      person: { id: "prof", X: 0.05, Y: 0.74, z: 2.7, draw: drawProf, head: [0, -0.62], smoke: PIPE },
      props: [{ id: "gramophone", X: -2.4, Y: 1.3, z: 4.7, w: 0.9, h: 1.0 }, { id: "books", X: 2.5, Y: 1.6, z: ZB - 0.3, w: 2.0, h: 2.6 }, { id: "slate", X: 0, Y: 2.0, z: ZB, w: 1.8, h: 1.0 }],
    },

    door: {
      mix: { street: 1.25, music: 0.6 },
      layers: [
        { z: ZB, draw(g, G) {
          walls(g, G, { pools: [[1.4, 4.2, 0.7], [-0.6, 4.6, 1.2]], seed: 57, lamps: [[1.4, 4.4, 2.8, 0.7]], wain: 1.0 });
          const { P } = G, d = DOOR;
          /* the door frame and the door itself; its glass is filled in live, the street behind it */
          quad(g, P, [[d.x0 - 0.15, 0, ZB - 0.01], [d.x1 + 0.15, 0, ZB - 0.01], [d.x1 + 0.15, 2.55, ZB - 0.01], [d.x0 - 0.15, 2.55, ZB - 0.01]], tone(0.04));
          quad(g, P, [[d.x0, 0, ZB - 0.02], [d.x1, 0, ZB - 0.02], [d.x1, 2.4, ZB - 0.02], [d.x0, 2.4, ZB - 0.02]], lin(g, P(d.x0, 0, ZB)[0], 0, P(d.x1, 0, ZB)[0], 0, [[0, tone(0.2)], [1, tone(0.08)]]));
          quad(g, P, [[d.x0 + 0.1, 0.15, ZB - 0.03], [d.x1 - 0.1, 0.15, ZB - 0.03], [d.x1 - 0.1, 0.95, ZB - 0.03], [d.x0 + 0.1, 0.95, ZB - 0.03]], tone(0.12));
          /* the transom over the door and the bell on its spring */
          quad(g, P, [[d.x0, 2.42, ZB - 0.02], [d.x1, 2.42, ZB - 0.02], [d.x1, 2.75, ZB - 0.02], [d.x0, 2.75, ZB - 0.02]], tone(0.75, 0.55));
          /* a coat rack with hats and coats, and an umbrella stand */
          { const [x, y0] = P(2.3, 0, ZB - 0.4), [, y1] = P(0, 1.9, ZB - 0.4), s = G.s(ZB - 0.4); g.fillStyle = tone(0.05); g.fillRect(x - s * 0.03, y1, s * 0.06, y0 - y1);
            for (const [dx, dy, c] of [[-0.25, 0.25, 0.22], [0.2, 0.3, 0.14], [0.05, 0.2, 0.3]]) { g.fillStyle = lin(g, x + dx * s - s * 0.2, 0, x + dx * s + s * 0.2, 0, [[0, tone(c + 0.08)], [1, tone(c - 0.1)]]);
              g.beginPath(); g.moveTo(x + dx * s - s * 0.12, y1 + dy * s); g.lineTo(x + dx * s + s * 0.12, y1 + dy * s); g.lineTo(x + dx * s + s * 0.2, y1 + (dy + 1.0) * s); g.lineTo(x + dx * s - s * 0.2, y1 + (dy + 1.0) * s); g.fill(); }
            for (const [dx, c] of [[-0.2, 0.08], [0.2, 0.18]]) { g.fillStyle = tone(c); g.beginPath(); g.ellipse(x + dx * s, y1 + s * 0.02, s * 0.15, s * 0.035, 0, 0, 7); g.fill(); g.fillRect(x + dx * s - s * 0.09, y1 - s * 0.12, s * 0.18, s * 0.13); } }
          { const [x, y] = P(3.1, 0, ZB - 0.3), s = G.s(ZB - 0.3); g.fillStyle = lin(g, x - s * 0.15, 0, x + s * 0.15, 0, [[0, tone(0.45)], [1, tone(0.15)]]); g.fillRect(x - s * 0.13, y - s * 0.55, s * 0.26, s * 0.55);
            g.strokeStyle = tone(0.03); g.lineWidth = Math.max(2, s * 0.025); for (const dx of [-0.05, 0.04]) { g.beginPath(); g.moveTo(x + dx * s, y - s * 0.5); g.lineTo(x + dx * s * 1.5, y - s * 0.95); g.quadraticCurveTo(x + dx * s * 1.5 + s * 0.06, y - s * 1.02, x + dx * s * 1.5 + s * 0.08, y - s * 0.95); g.stroke(); } }
          /* bundles of this morning's papers on the floor */
          for (const [X, k] of [[-2.0, 0], [-2.35, 1]]) { const [x, y] = P(X, 0, ZB - 0.6 - k * 0.3), s = G.s(ZB - 0.6); g.fillStyle = lin(g, 0, y - s * 0.22, 0, y, [[0, tone(0.85)], [1, tone(0.5)]]); g.fillRect(x - s * 0.22, y - s * 0.22, s * 0.44, s * 0.22);
            g.strokeStyle = tone(0.4, 0.6); g.lineWidth = 1; for (let l = 0; l < 7; l++) { g.beginPath(); g.moveTo(x - s * 0.22, y - s * 0.2 + l * s * 0.03); g.lineTo(x + s * 0.22, y - s * 0.2 + l * s * 0.03); g.stroke(); }
            g.strokeStyle = tone(0.2); g.lineWidth = 2; g.beginPath(); g.moveTo(x, y - s * 0.22); g.lineTo(x, y); g.moveTo(x - s * 0.22, y - s * 0.11); g.lineTo(x + s * 0.22, y - s * 0.11); g.stroke(); }
        }, live(g, G, t) {
          /* the street through the door's glass: the same morning as through the window, streetcars and all */
          const { P } = G, d = DOOR, a = P(d.x0 + 0.12, 2.25, ZB - 0.03), b = P(d.x1 - 0.12, 1.1, ZB - 0.03), w = b[0] - a[0], h = b[1] - a[1];
          g.save(); g.beginPath(); g.rect(a[0], a[1], w, h); g.clip();
          const L = S.layers, sw = h * (G.W / G.H) * 1.6, sx = a[0] + w / 2 - sw * 0.2;
          for (const c of [L[0], L[1], L[2]]) g.drawImage(c, sx, a[1] - h * 0.2, sw, h * 1.6);
          g.fillStyle = `rgba(255,236,200,${0.18 + 0.05 * Math.sin(t / 7)})`; g.fillRect(a[0], a[1], w, h);
          g.globalCompositeOperation = "screen"; g.fillStyle = lin(g, a[0], a[1], b[0], b[1], [[0, "rgba(255,245,225,.14)"], [0.5, "rgba(255,245,225,0)"], [1, "rgba(255,245,225,.1)"]]); g.fillRect(a[0], a[1], w, h); g.restore();
          /* gold letters on the glass, read from inside */
          g.save(); g.translate(a[0] + w / 2, a[1] + h * 0.42); g.scale(-1, 1); text(g, "CAFÉ", 0, 0, w * 0.3, { w: 700, fill: "rgba(240,210,140,.7)", stroke: "rgba(10,8,5,.5)" }); g.restore();
          g.strokeStyle = tone(0.05); g.lineWidth = Math.max(2, G.s(ZB) * 0.04); g.strokeRect(a[0], a[1], w, h);
          /* sunlight from the door glass across the floor */
          if (!END.on) { g.save(); g.globalCompositeOperation = "screen"; const f0 = P(d.x0 + 0.1, 0, ZB - 0.1), f1 = P(d.x1 - 0.1, 0, ZB - 0.1), n0 = P(d.x0 + 0.9, 0, 2.2), n1 = P(d.x1 + 0.6, 0, 2.2);
            g.fillStyle = lin(g, 0, f0[1], 0, n0[1], [[0, "rgba(255,230,180,.16)"], [1, "rgba(255,230,180,0)"]]); poly(g, [f0, f1, n1, n0]); g.fill();
            g.fillStyle = lin(g, a[0], a[1], a[0], f0[1], [[0, "rgba(255,230,180,.06)"], [1, "rgba(255,230,180,.0)"]]); poly(g, [a, [b[0], a[1]], [n1[0], n1[1]], [n0[0], n0[1]]]); g.fill(); g.restore(); }
          /* with a full ticket the door's glass brightens, more so under the pointer: it can be opened now */
          if (ST.stamps.size === 4 && !END.on) { g.save(); g.globalCompositeOperation = "screen"; glow(g, a[0] + w / 2, a[1] + h / 2, Math.max(w, h) * 1.1, (ST.hoverProp === "door" ? 0.32 : 0.14) + 0.05 * Math.sin(t * 2.5)); g.restore(); }
          /* the brass push plate and handle */
          const [hx, hy] = P(d.x1 - 0.12, 1.0, ZB - 0.04), s = G.s(ZB); g.fillStyle = "#c8a868"; g.fillRect(hx - s * 0.05, hy - s * 0.15, s * 0.04, s * 0.3);
          /* the bell over the door, swinging when the door opens */
          const [bx, by] = P((d.x0 + d.x1) / 2 + 0.3, 2.5, ZB - 0.05), sw2 = END.on ? Math.sin((performance.now() - END.t0) / 90) * Math.max(0, 1 - (performance.now() - END.t0) / 2500) * 0.6 : Math.sin(t * 0.6) * 0.03;
          g.strokeStyle = tone(0.5); g.lineWidth = Math.max(1, s * 0.012); g.beginPath(); g.moveTo(bx - s * 0.25, by - s * 0.1); g.lineTo(bx, by - s * 0.1); g.stroke();
          g.save(); g.translate(bx, by - s * 0.1); g.rotate(sw2); g.fillStyle = lin(g, -s * 0.08, 0, s * 0.08, 0, [[0, "#5a4426"], [0.4, "#f2dca8"], [1, "#3a2a14"]]); g.beginPath(); g.moveTo(-s * 0.03, s * 0.02); g.quadraticCurveTo(-s * 0.04, s * 0.11, -s * 0.08, s * 0.14); g.lineTo(s * 0.08, s * 0.14); g.quadraticCurveTo(s * 0.04, s * 0.11, s * 0.03, s * 0.02); g.fill(); g.restore();
        } },
        { z: 1.4, draw(g, G) {
          /* the end of the counter close by on the right, out of focus */
          const [x, y] = G.P(1.6, 1.05, 1.4), s = G.s(1.4); g.save();
          g.fillStyle = lin(g, 0, y, 0, G.H, [[0, tone(0.5)], [0.05, tone(0.12)], [1, tone(0.02)]]); g.fillRect(x, y, G.W, G.H - y); g.restore();
        } },
      ],
      person: { id: "sully", X: 0.7, Y: 0, z: 2.9, draw: drawSully, head: [0, -1.3] },
      props: [{ id: "coats", X: 2.3, Y: 1.5, z: ZB - 0.4, w: 0.9, h: 1.2 }, { id: "bell", X: -0.6, Y: 2.45, z: ZB, w: 0.4, h: 0.35 }, { id: "bundle", X: -2.15, Y: 0.15, z: ZB - 0.7, w: 0.9, h: 0.4 }, { id: "door", X: -0.9, Y: 1.2, z: ZB, w: 1.2, h: 2.4 }],
    },
  };
  const DOOR = { x0: -1.5, x1: -0.3 };
  const ORDER = ["window", "counter", "wire", "back", "door"];
  const PEOPLE = { mae: "counter", elias: "wire", prof: "back", sully: "door" };

  /* ============ sound: everything through the café's own mixer, so Off / Quiet / Lively rule it ============ */
  const AUDIO = (() => {
    const c = () => S.amb.ctx();
    const env = (A, to, t, a, d, v) => { const g = A.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + d); g.connect(to); return g; };
    let NB = null; const noise = A => { if (!NB || NB.sampleRate !== A.sampleRate) { NB = A.createBuffer(1, A.sampleRate, A.sampleRate); const d = NB.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; } return NB; };
    const hit = (A, to, t, f, q, d, v) => { const s = A.createBufferSource(), b = A.createBiquadFilter(); s.buffer = noise(A); b.type = "bandpass"; b.frequency.value = f; b.Q.value = q; s.connect(b); b.connect(env(A, to, t, 0.003, d, v)); s.start(t, Math.random() * 0.5, d + 0.05); };
    const ping = (A, to, t, f, d, v, type = "sine") => { const o = A.createOscillator(); o.type = type; o.frequency.value = f; o.connect(env(A, to, t, 0.004, d, v)); o.start(t); o.stop(t + d + 0.05); };
    /* each regular's voice: a murmur in their own pitch and pace, the syllables shaped by two vowel formants */
    const VOWELS = [[730, 1090], [530, 1840], [270, 2290], [570, 840], [440, 1020], [660, 1700], [300, 870]];
    const VOICE = { mae: { f0: 255, rate: 1, wave: "triangle" }, elias: { f0: 150, rate: 1.15, wave: "sawtooth" }, prof: { f0: 112, rate: 0.82, wave: "sawtooth" }, sully: { f0: 310, rate: 1.25, wave: "triangle" } };
    return {
      on: () => !!c(),
      syllable(who, stress) { const C = c(); if (!C) return; const { A, out } = C, v = VOICE[who] || VOICE.mae, t = A.currentTime + 0.01, d = (0.07 + Math.random() * 0.06) / v.rate;
        const o = A.createOscillator(), f1 = A.createBiquadFilter(), f2 = A.createBiquadFilter(), mix = A.createGain(), [a, b] = VOWELS[Math.floor(Math.random() * VOWELS.length)];
        o.type = v.wave; const f = v.f0 * (1 + (Math.random() - 0.5) * 0.18) * (stress ? 1.12 : 1);
        o.frequency.setValueAtTime(f, t); o.frequency.linearRampToValueAtTime(f * (0.9 + Math.random() * 0.15), t + d);
        f1.type = f2.type = "bandpass"; f1.frequency.value = a; f2.frequency.value = b; f1.Q.value = 5; f2.Q.value = 7; mix.gain.value = 1;
        o.connect(f1); o.connect(f2); f1.connect(mix); f2.connect(mix); mix.connect(env(A, out, t, 0.012, d, 0.11)); o.start(t); o.stop(t + d + 0.08);
        if (Math.random() < 0.35) hit(A, out, t, 3500 + Math.random() * 2000, 1.5, 0.025, 0.02); },
      steps(n = 3, gap = 0.3) { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02;
        for (let k = 0; k < n; k++) { const tk = t + k * gap + Math.random() * 0.03; hit(A, out, tk, 180 + Math.random() * 40, 1.2, 0.09, 0.22); hit(A, out, tk + 0.01, 1300 + Math.random() * 300, 3, 0.03, 0.05); ping(A, out, tk, 95, 0.08, 0.04); } },
      stamp() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; hit(A, out, t, 150, 0.8, 0.14, 0.4); hit(A, out, t, 900, 1, 0.05, 0.12); hit(A, out, t + 0.08, 3000, 0.7, 0.12, 0.05); },
      ticker() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02, n = 8 + Math.floor(Math.random() * 14);
        for (let k = 0; k < n; k++) { const tk = t + k * (0.055 + Math.random() * 0.03); hit(A, out, tk, 2600 + Math.random() * 900, 6, 0.018, 0.07); if (k % 4 === 0) hit(A, out, tk + 0.01, 700, 4, 0.02, 0.05); } },
      key() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; [0.08, 0.08, 0.24, 0.08].reduce((at, d) => { hit(A, out, at, 1800, 5, 0.015, 0.06); hit(A, out, at + d, 1200, 5, 0.015, 0.04); return at + d + 0.07; }, t); },
      chalk() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; hit(A, out, t, 5200, 4, 0.12, 0.03); hit(A, out, t + 0.14, 4700, 5, 0.08, 0.025); },
      clack() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; hit(A, out, t, 2200, 8, 0.03, 0.14); ping(A, out, t, 1900, 0.06, 0.03); },
      hiss() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; hit(A, out, t, 6000, 0.6, 1.3, 0.04); },
      ching() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; for (let k = 0; k < 3; k++) hit(A, out, t + k * 0.05, 2500, 2, 0.03, 0.06); ping(A, out, t + 0.18, 2000, 0.9, 0.03); ping(A, out, t + 0.18, 3010, 0.6, 0.015); },
      rustle() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; for (let k = 0; k < 6; k++) hit(A, out, t + k * 0.06, 2500 + Math.random() * 2000, 0.8, 0.09, 0.05); },
      bell() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02; for (let k = 0; k < 7; k++) { const tk = t + k * (0.07 + Math.random() * 0.05), f = 2400 + Math.random() * 300; ping(A, out, tk, f, 0.9 - k * 0.08, 0.05 * (1 - k / 9)); ping(A, out, tk, f * 2.76, 0.4, 0.012); } },
      creak() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02, o = A.createOscillator(), b = A.createBiquadFilter(); o.type = "sawtooth"; o.frequency.setValueAtTime(90, t); o.frequency.linearRampToValueAtTime(140, t + 0.6); o.frequency.linearRampToValueAtTime(70, t + 1.1);
        b.type = "bandpass"; b.frequency.value = 900; b.Q.value = 9; o.connect(b); b.connect(env(A, out, t, 0.1, 1.1, 0.05)); o.start(t); o.stop(t + 1.3); },
      whoosh() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02, s = A.createBufferSource(), b = A.createBiquadFilter(), g = A.createGain();
        s.buffer = noise(A); s.loop = true; b.type = "bandpass"; b.Q.value = 1.2; b.frequency.setValueAtTime(400, t); b.frequency.exponentialRampToValueAtTime(3000, t + 1.4); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.12, t + 1.0); g.gain.linearRampToValueAtTime(0, t + 1.6);
        s.connect(b); b.connect(g); g.connect(out); s.start(t); s.stop(t + 1.7); hit(A, out, t + 1.6, 200, 1, 0.2, 0.3); },
      /* the café cat: a soft meow that rises and falls (or a short "mrrp"), and a purr */
      meow(short) { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02, d = short ? 0.22 : 0.62, o = A.createOscillator(), f1 = A.createBiquadFilter(), f2 = A.createBiquadFilter(), m = A.createGain(), r = 1 + (Math.random() - 0.5) * 0.12;
        o.type = "sawtooth"; o.frequency.setValueAtTime(520 * r, t); o.frequency.linearRampToValueAtTime((short ? 860 : 780) * r, t + d * 0.3); o.frequency.linearRampToValueAtTime((short ? 700 : 470) * r, t + d);
        f1.type = f2.type = "bandpass"; f1.frequency.setValueAtTime(900, t); f1.frequency.linearRampToValueAtTime(1400, t + d * 0.4); f1.frequency.linearRampToValueAtTime(800, t + d); f2.frequency.value = 2600; f1.Q.value = 4; f2.Q.value = 6; m.gain.value = 1;
        o.connect(f1); o.connect(f2); f1.connect(m); f2.connect(m); m.connect(env(A, out, t, 0.05, d, 0.05)); o.start(t); o.stop(t + d + 0.1); },
      /* a picture losing its hold: a few dry ticks and a short hum */
      glitch() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.01; for (let k = 0; k < 5; k++) hit(A, out, t + k * (0.03 + Math.random() * 0.04), 3000 + Math.random() * 4000, 3, 0.012, 0.035);
        ping(A, out, t, 120, 0.18, 0.02, "square"); },
      purr() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.02, s = A.createBufferSource(), lp = A.createBiquadFilter(), g = A.createGain(), lfo = A.createOscillator(), dep = A.createGain();
        s.buffer = noise(A); s.loop = true; lp.type = "lowpass"; lp.frequency.value = 320; lfo.frequency.value = 26; dep.gain.value = 0.05; lfo.connect(dep); dep.connect(g.gain);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.06, t + 0.3); g.gain.setValueAtTime(0.06, t + 1.6); g.gain.linearRampToValueAtTime(0, t + 2.1);
        s.connect(lp); lp.connect(g); g.connect(out); s.start(t); s.stop(t + 2.2); lfo.start(t); lfo.stop(t + 2.2); },
      /* the feeling at the end: a warm chord that opens slowly, like the morning */
      swell() { const C = c(); if (!C) return; const { A, out } = C, t = A.currentTime + 0.05, lp = A.createBiquadFilter(), g = A.createGain(); lp.type = "lowpass"; lp.frequency.setValueAtTime(300, t); lp.frequency.exponentialRampToValueAtTime(2600, t + 7);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.06, t + 5); g.gain.setValueAtTime(0.06, t + 11); g.gain.linearRampToValueAtTime(0, t + 18); lp.connect(g); g.connect(out);
        [174.61, 261.63, 349.23, 440, 523.25, 783.99].forEach((f, i) => { for (const dt of [-3, 3]) { const o = A.createOscillator(); o.type = i < 2 ? "sawtooth" : "triangle"; o.frequency.value = f; o.detune.value = dt; const k = A.createGain(); k.gain.value = 0.25 / (1 + i * 0.3); o.connect(k); k.connect(lp); o.start(t + i * 0.6); o.stop(t + 18.5); } }); },
    };
  })();

  /* ============ the reader's walk ============ */
  const ST = { arriveAt: 0, walked: true, talked: false, hover: null, on: false, area: "window", pan: null, cam: 0, camT: 0, zoom: 1, zoomT: 1, zx: 0, zy: 0, talk: null, stamps: new Set(), boxes: {}, mouth: 0, mouthT: 0, last: 0 };
  const END = { on: false, t0: 0 };
  let W = 0, H = 0, K = 1, raf = 0;
  const cv = document.createElement("canvas"); cv.className = "cafe-cv"; cv.setAttribute("aria-hidden", "true"); cv.dataset.noflip = "";
  desk.insertBefore(cv, desk.querySelector(".stage"));
  const g = cv.getContext("2d");
  const BAKED = {};
  function size() {
    W = desk.clientWidth; H = desk.clientHeight; K = Math.min(1.25, window.devicePixelRatio || 1, Math.sqrt(2.6e6 / Math.max(1, W * H)));
    cv.width = Math.round(W * K); cv.height = Math.round(H * K); for (const k in BAKED) delete BAKED[k]; for (const k in PART) delete PART[k]; FIN = null; STREET = null;
  }
  /* a room is drawn once per size, layer by layer, a frame apart, and each layer is painted once into a tiny
     canvas so the browser does the heavy work now and not on the first step into the room */
  const PART = {}, WARM = document.createElement("canvas"); WARM.width = WARM.height = 2;
  function bakeLayer(name) {
    const A = AREAS[name], ov = Math.round(H * 0.2), G = geom(W, H, 0), done = PART[name] || (PART[name] = []), L = A.layers[done.length];
    const c = document.createElement("canvas"); c.width = Math.round((W + 2 * ov) * K); c.height = Math.round(H * K);
    const x = c.getContext("2d"); x.setTransform(K, 0, 0, K, ov * K, 0); L.draw(x, G); WARM.getContext("2d").drawImage(c, 0, 0, 2, 2);
    done.push({ c, ov }); if (done.length === A.layers.length) { BAKED[name] = done; delete PART[name]; }
  }
  const ready = name => !AREAS[name].layers || !!BAKED[name];
  function bake(name) { while (!ready(name)) bakeLayer(name); return BAKED[name]; }
  /* get rooms ready a layer per frame; onStep(done, total) for the loading card */
  let PREP = null;
  function prep(names, onStep) {
    const todo = names.filter((n, i) => names.indexOf(n) === i && !ready(n)), total = todo.reduce((a, n) => a + AREAS[n].layers.length - (PART[n] || []).length, 0);
    let n = 0; const job = {}; PREP = job;
    return new Promise(res => { const step = () => { if (PREP !== job || !ST.on) return res(false); const nx = todo.find(k => !ready(k)); if (!nx) { onStep && onStep(total, total); return res(true); }
      bakeLayer(nx); n++; onStep && onStep(n, total); setTimeout(() => requestAnimationFrame(step), 0); }; requestAnimationFrame(step); });
  }
  /* only the room you are in and the two beside it stay drawn, so a big screen does not run out of memory */
  function keep() { const near = [ST.area, nb(1), nb(-1)]; for (const k in BAKED) if (!near.includes(k)) delete BAKED[k]; for (const k in PART) if (!near.includes(k)) delete PART[k]; }
  /* grain and the dark toward the edges, as in the street scene */
  let FIN = null;
  function finish() {
    if (FIN) return FIN; FIN = document.createElement("canvas"); FIN.width = Math.round(W * K); FIN.height = Math.round(H * K); const x = FIN.getContext("2d"); x.setTransform(K, 0, 0, K, 0, 0);
    const gr = x.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.3, W / 2, H * 0.5, Math.max(W, H) * 0.75); gr.addColorStop(0, "rgba(0,0,0,0.1)"); gr.addColorStop(1, "rgba(0,0,0,0.78)"); x.fillStyle = gr; x.fillRect(0, 0, W, H);
    const R = rnd(9), n = Math.round(W * H / 900); x.fillStyle = "rgba(255,240,210,0.04)"; for (let i = 0; i < n; i++) x.fillRect(R() * W, R() * H, 1, 1); x.fillStyle = "rgba(0,0,0,0.06)"; for (let i = 0; i < n; i++) x.fillRect(R() * W, R() * H, 1, 1);
    return FIN;
  }
  /* the motes in the lamplight: a few dozen specks drifting */
  const MOTES = (() => { const R = rnd(31); return Array.from({ length: 40 }, () => ({ x: R(), y: R(), v: 0.2 + R() * 0.6, p: R() * 6 })); })();

  /* one room on the screen, shifted by dx (walking) and by the reader's head (cam) */
  function drawArea(name, dx, t) {
    const A = AREAS[name]; g.save(); g.translate(dx, 0);
    if (name === "window") { for (const c of S.layers) g.drawImage(c, 0, 0, W, H); g.restore(); if (CAT.room === name) drawCat(dx, t);
      if (dx === 0) ST.boxes = { person: null, props: Object.entries((S.hits && S.hits()) || {}).map(([id, b]) => ({ id, x: b.x, y: b.y, w: b.w, h: b.h })) }; return; }
    const G = geom(W, H, ST.cam), layers = bake(name), P = A.person, items = A.layers.map((L, i) => ({ z: L.z, i })).concat(P ? [{ z: P.z, p: true }] : []).sort((a, b) => b.z - a.z);
    for (const it of items) {
      if (it.p) { const [x, y] = G.P(P.X, P.Y, P.z), s = G.s(P.z), talk = ST.talk && ST.talk.who === P.id && dx === 0, hx0 = x + P.head[0] * s, hy0 = y + P.head[1] * s;
        /* a regular who has not been spoken to yet: a little warmer in the light after a moment, more so under the pointer */
        const inv = dx || talk || END.on ? 0 : ST.hover === P.id ? 1 : !ST.talked && performance.now() - ST.arriveAt > 1800 ? 0.35 + 0.25 * Math.sin(t * 2) : 0;
        if (inv > 0) { g.save(); g.globalCompositeOperation = "screen"; glow(g, hx0, hy0 + s * 0.25, s * 0.6, 0.14 * inv); g.restore(); }
        g.save(); g.translate(x, y); g.scale(s, s); P.draw(g, RM ? 0 : t, { talk, mouth: ST.mouth, look: [-(ST.cam / 0.25) * 0.3 + (P.X < 0 ? 0.2 : -0.2), 0.1] }); g.restore();
        const hx = hx0, hy = hy0;
        if (inv > 0) text(g, TX.people[P.id].name + "  · · ·", hx, hy - s * 0.24, Math.max(13, s * 0.042), { it: true, fill: `rgba(245,228,190,${Math.min(1, 0.4 + 0.6 * inv)})`, stroke: "rgba(0,0,0,.55)", face: "'Old Standard TT', Georgia, 'Noto Serif SC', serif" });
        if (dx === 0) ST.boxes.person = { id: P.id, x: hx - s * 0.32, y: hy - s * 0.2, w: s * 0.64, h: (y - hy) + s * 0.25, hx, hy };
        /* the Professor's pipe smoke curls up into the lamp */
        if (P.smoke && !(talk && ST.mouth > 0.1)) for (let k = 0; k < 12; k++) { const u = ((t * 0.1) + k / 12) % 1, sx = x + P.smoke[0] * s + Math.sin(t * 0.6 + k * 1.3 + u * 4) * s * 0.025 * (1 + u * 4), sy = y + P.smoke[1] * s - u * s * 0.55;
          puff(g, sx, sy, s * (0.012 + u * 0.07), 0.16 * Math.sin(u * Math.PI) * (1 - u * 0.5)); }
        continue; }
      const L = A.layers[it.i], b = layers[it.i], sh = -ST.cam * G.f / L.z;
      g.drawImage(b.c, -b.ov + sh, 0, W + 2 * b.ov, H);
      if (L.live) L.live(g, G, t);
    }
    if (CAT.room === name) drawCat(0, t);
    /* dust in the lamplight */
    if (!RM) { g.save(); g.globalCompositeOperation = "screen"; for (const m of MOTES) { const x = ((m.x + Math.sin(t * 0.05 * m.v + m.p) * 0.05) % 1) * W, y = ((m.y - t * 0.006 * m.v) % 1 + 1) % 1 * H * 0.8;
      g.fillStyle = `rgba(255,236,200,${0.25 + 0.2 * Math.sin(t * m.v + m.p)})`; g.fillRect(x, y, 1.6, 1.6); } g.restore(); }
    if (dx === 0) ST.boxes.props = (A.props || []).map(p => { const a = G.P(p.X - p.w / 2, p.Y + p.h / 2, p.z), b = G.P(p.X + p.w / 2, p.Y - p.h / 2, p.z); return { id: p.id, x: a[0], y: a[1], w: b[0] - a[0], h: b[1] - a[1] }; });
    g.restore();
  }

  function frame(now) {
    raf = 0; if (!ST.on || document.hidden) return;
    const t = now / 1000, dt = Math.min(0.1, (now - (ST.last || now)) / 1000); ST.last = now;
    ST.cam += (ST.camT - ST.cam) * Math.min(1, dt * 3); ST.zoom += (ST.zoomT - ST.zoom) * Math.min(1, dt * 2.5); ST.mouth += (ST.mouthT - ST.mouth) * Math.min(1, dt * 22);
    g.setTransform(K, 0, 0, K, 0, 0); g.fillStyle = "#070605"; g.fillRect(0, 0, W, H);
    if (END.on) endFrame(now, t);
    else {
      /* the talk zoom: toward the regular's face */
      g.save(); if (ST.zoom > 1.001) { g.translate(ST.zx, ST.zy); g.scale(ST.zoom, ST.zoom); g.translate(-ST.zx, -ST.zy); }
      if (ST.pan) { const u = Math.min(1, (now - ST.pan.t0) / ST.pan.d), e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2, bob = Math.sin(u * Math.PI * 4) * H * 0.004 * (1 - u);
        if (ST.pan.fade) { drawArea(ST.pan.to, 0, t); g.globalAlpha = 1 - e; drawArea(ST.pan.from, 0, t); g.globalAlpha = 1; }
        else { g.translate(0, bob); drawArea(ST.pan.from, -ST.pan.dir * W * e, t); drawArea(ST.pan.to, ST.pan.dir * W * (1 - e), t); }
        if (u >= 1) { ST.pan = null; arrived(); } }
      else drawArea(ST.area, 0, t);
      g.restore();
      /* a faint glint on the thing under the pointer (or picked with Tab): it can be looked at more closely */
      const armed = ST.task === "chalk" && ST.hoverProp === "board", hp = !ST.pan && (!ST.talk || armed) && !LOOK && ST.hoverProp && ST.hoverProp !== "door" && (ST.boxes.props || []).find(q => q.id === ST.hoverProp);
      if (hp) { g.save(); g.globalCompositeOperation = "screen"; glow(g, hp.x + hp.w / 2, hp.y + hp.h / 2, Math.max(hp.w, hp.h) * 0.75, armed ? 0.22 + 0.06 * Math.sin(t * 4) : 0.09 + 0.03 * Math.sin(t * 3)); g.restore(); }
      if (ST.area !== "window" || ST.pan) g.drawImage(finish(), 0, 0, W, H);
    }
    loop();
  }
  function loop() { if (!raf && ST.on && !document.hidden) raf = requestAnimationFrame(n => (n - ST.last >= (RM ? 100 : small() ? 40 : 30) || !ST.last) ? frame(n) : (raf = 0, loop())); }
  document.addEventListener("visibilitychange", loop);

  /* ============ the reader's controls: words around the picture ============ */
  const ui = document.createElement("div"); ui.className = "cafe-ui"; ui.dataset.noflip = ""; ui.hidden = true;
  ui.innerHTML = `<div class="cafe-top"><button class="cafe-back" data-k="back"></button><div class="cafe-place" aria-live="polite"></div>
      <div class="cafe-right"><button class="cafe-snd" data-k="snd"></button><div class="cafe-ticket" role="img"><span class="ct-t"></span><span class="ct-s"></span></div></div></div>
    <button class="cafe-edge l" data-k="left"><span class="ce-ch">‹</span><span class="ce-n"></span></button><button class="cafe-edge r" data-k="right"><span class="ce-n"></span><span class="ce-ch">›</span></button>
    <div class="cafe-hint"></div><p class="cafe-call" aria-live="polite"></p><div class="cafe-note" role="status"></div>
    <div class="cafe-say" role="dialog" aria-live="polite" hidden><div class="cs-who"><b></b><i></i></div><p class="cs-line"></p><div class="cs-ch"></div><span class="cs-more" aria-hidden="true">▾</span></div>
    <div class="cafe-end" hidden><p class="ce-card"></p><div class="ce-paper" hidden></div></div>`;
  desk.appendChild(ui);
  /* the card that shows while the café is being set: the paper is already going, the rooms are being drawn */
  const wait = document.createElement("div"); wait.className = "cafe-load"; wait.dataset.noflip = ""; wait.setAttribute("role", "status"); wait.hidden = true;
  wait.innerHTML = `<b></b><i></i><span class="cl-bar"><span></span></span>`; desk.appendChild(wait);
  const waitShow = (on, u = 0) => { wait.hidden = !on; if (!on) return; wait.querySelector("b").textContent = TX.loading; wait.querySelector("i").textContent = TX.loadingSub; wait.querySelector(".cl-bar span").style.width = Math.round(u * 100) + "%"; };
  const $ = s => ui.querySelector(s);
  const say = $(".cafe-say"), sayLine = $(".cs-line"), sayCh = $(".cs-ch"), note = $(".cafe-note"), hintEl = $(".cafe-hint");
  /* stop the paper's own page turning while the reader walks the café */
  for (const ev of ["pointerdown", "pointerup", "click", "touchstart", "touchend"]) ui.addEventListener(ev, e => e.stopPropagation());

  /* the button on the paper's bar that starts it all */
  const ctl = document.getElementById("ctl"), bIn = document.createElement("button");
  bIn.id = "bCafe"; bIn.className = "cafe-in-btn";
  if (ctl) ctl.insertBefore(bIn, document.getElementById("bSnd")); else desk.appendChild(bIn);
  bIn.onclick = e => { e.stopPropagation(); enter(); };

  function labels() {
    words(); const narrow = desk.clientWidth < 560 || (ctl && getComputedStyle(ctl).flexDirection === "column");
    bIn.textContent = narrow ? "☕" : "☕ " + TX.enter; bIn.title = TX.enterTip; bIn.setAttribute("aria-label", TX.enterTip);
    $(".cafe-back").textContent = "‹ " + TX.back; $(".cafe-back").title = TX.backTip;
    $(".ct-t").textContent = TX.ticket; $(".cafe-ticket").title = TX.ticketTip; ticket(); edges(); sndLabel();
    hintEl.textContent = touch ? TX.hintTouch : TX.hint;
    if (ST.on) place();
  }
  function ticket() { const s = $(".ct-s"); s.innerHTML = ""; ["mae", "elias", "prof", "sully"].forEach((id, i) => { const w = document.createElement("span"), b = document.createElement("i"); w.className = "ct-slot"; b.className = ST.stamps.has(id) ? "on" : ""; b.textContent = ST.stamps.has(id) ? (TX.people[id].name.replace(/^The /, "")[0] || "") : ""; b.style.setProperty("--r", (i * 37 % 20 - 10) + "deg");
      const l = document.createElement("small"); l.textContent = TX.stampFor[id]; w.append(b, l); w.classList.toggle("on", ST.stamps.has(id)); s.appendChild(w); });
    $(".cafe-ticket").setAttribute("aria-label", `${TX.ticket}: ${ST.stamps.size} / 4`); }
  const nb = d => ORDER[(ORDER.indexOf(ST.area) + d + ORDER.length) % ORDER.length];
  function edges() { const l = $(".cafe-edge.l"), r = $(".cafe-edge.r"); l.hidden = IDX() === 0; r.hidden = IDX() === ORDER.length - 1; r.classList.toggle("shut", !canGo(1)); $(".cafe-edge.l .ce-n").textContent = TX.places[nb(-1)]; $(".cafe-edge.r .ce-n").textContent = TX.places[nb(1)];
    $(".cafe-edge.l").setAttribute("aria-label", TX.places[nb(-1)]); $(".cafe-edge.r").setAttribute("aria-label", TX.places[nb(1)]); }
  function place() { const p = $(".cafe-place"); p.classList.remove("on"); void p.offsetWidth; p.textContent = TX.places[ST.area]; p.classList.add("on"); edges(); }
  /* the sound button mirrors the café's own Off / Quiet / Lively */
  const sndLabel = () => { const b = S.amb_btn; $(".cafe-snd").textContent = "♪ " + (b ? b.textContent : ""); $(".cafe-snd").classList.toggle("hush", !AUDIO.on()); $(".cafe-snd").title = TX.soundHint; };
  window.addEventListener("gazette-cafe", sndLabel); window.addEventListener("gazette-labels", labels);

  /* ----- in and out ----- */
  /* in: the paper goes down at once and a card says the café is being set; the rooms on either side are drawn,
     then the café opens (a card is shown only if that takes longer than a blink) */
  function enter(quick) {
    if (ST.on) return; ST.on = true; ST.talked = false; ST.area = "window"; ST.cam = ST.camT = 0; ST.zoom = 1.08; ST.zoomT = 1; ST.last = 0;
    /* the café is heard from the first step whenever the site's sound is on: "Look up" is the click that may start it */
    let snd = "on"; try { snd = localStorage.getItem("gazette-sound") || "on"; } catch (e) {}
    if (snd !== "off" && S.amb_btn && !AUDIO.on()) { S.amb_btn.click(); setTimeout(() => { sndLabel(); mix(); }, 50); }
    catPut("window", "wait");
    desk.classList.add("cafe-on", "cafe-wait"); desk.classList.remove("cafe-away"); labels(); mix();
    const t0 = performance.now(); let shown = false; const card = setTimeout(() => { shown = true; waitShow(true, 0); }, 150);
    requestAnimationFrame(() => { if (!ST.on) return; if (W !== desk.clientWidth || H !== desk.clientHeight || !cv.width) size(); ST.zx = W / 2; ST.zy = H / 2; loop();
      (quick ? Promise.resolve(true) : prep([nb(1), nb(-1)], (n, t) => shown && waitShow(true, t ? n / t : 1))).then(ok => {
        clearTimeout(card); if (!ST.on) return; const rest = shown ? Math.max(0, 350 - (performance.now() - t0)) : 0;
        setTimeout(() => { if (!ST.on) return; waitShow(false); desk.classList.remove("cafe-wait"); ui.hidden = false; place();
          hintEl.classList.add("on"); clearTimeout(hintEl._t); ST.walked = false;
          /* the cat on the sill looks at the reader, gets up and pads to the way on; if nobody follows, a soft meow */
          catLead(1500); [6500, 17000].forEach((ms, i) => setTimeout(() => { if (ST.on && !ST.walked && ST.area === "window" && !CAT.walk) catMew(!!i); }, ms));
          /* nobody has moved yet: from the right, Mae calls over once and the way to the counter catches the light */
          clearTimeout(ST.callT); ST.callT = setTimeout(() => { if (!ST.on || ST.walked || ST.area !== "window") return; const e = $(".cafe-edge.r"), c = $(".cafe-call");
            e.classList.add("call"); c.textContent = TX.call; c.classList.add("on"); for (let k = 0; k < 9; k++) setTimeout(() => ST.on && !ST.walked && AUDIO.syllable("mae", k === 0), 300 + k * 110); }, 2400);
          setTimeout(() => $(".cafe-edge.r").focus({ preventScroll: true }), 300); }, rest); }); });
  }
  function leave() {
    if (!ST.on) return; ST.on = false; PREP = null; waitShow(false); desk.classList.remove("cafe-wait"); closeTalk(); END.on = false; $(".cafe-end").hidden = true; $(".ce-paper").hidden = true;
    desk.classList.remove("cafe-on", "cafe-away"); ui.hidden = true; S.amb.mix({ street: 1, open: 0, music: 1 }); bIn.focus({ preventScroll: true });
  }
  const mix = () => S.amb.mix(Object.assign({ open: 0 }, AREAS[ST.area].mix));
  /* the café is walked in order: rightward only once the regular here has stamped the ticket, back any time, never round
     the corner from the window to the door */
  const IDX = () => ORDER.indexOf(ST.area), HOST = { counter: "mae", wire: "elias", back: "prof", door: "sully" };
  const canGo = d => d < 0 ? IDX() > 0 : IDX() < ORDER.length - 1 && (ST.area === "window" || ST.stamps.has(HOST[ST.area]));
  function walk(d) {
    if (!ST.on || ST.pan || END.on || ST.busy) return;
    if (!canGo(d)) { if (d > 0 && HOST[ST.area] && IDX() < ORDER.length - 1) { const who = HOST[ST.area]; flash(TX.people[who].wait); for (let k = 0; k < 6; k++) setTimeout(() => AUDIO.syllable(who, !k), k * 110); } return; } closeTalk(); const to = nb(d), slow = RM || small();
    /* a room not drawn yet (a quick walker): the card for a moment, then the step */
    if (!ready(to)) { ST.busy = true; const card = setTimeout(() => waitShow(true, 0), 150); prep([to], (n, t) => waitShow(!wait.hidden, n / t)).then(() => { clearTimeout(card); waitShow(false); ST.busy = false; if (ST.on) walk(d); }); return; }
    catPut(to, catOpen(to) ? "exit" : "wait");
    ST.pan = { from: ST.area, to, dir: d, t0: performance.now(), d: slow ? 450 : 950, fade: slow }; ST.area = to; ST.zoomT = 1; ST.hover = null;
    if (!ST.walked) { ST.walked = true; clearTimeout(ST.callT); hintEl.classList.remove("on"); $(".cafe-edge.r").classList.remove("call"); $(".cafe-call").classList.remove("on"); }
    desk.classList.toggle("cafe-away", to !== "window"); AUDIO.steps(slow ? 2 : 3); note.classList.remove("on"); place(); mix(); bake(to); loop();
  }
  /* ----- the café cat: black, quiet, always a room ahead. It sits where the reader is, gets up once the way
     on is open, pads to it and sits again looking back over its shoulder. When a rule is carried it walks by
     twice, the very same way. Spots are fractions of the room: [x, y of the paws, sitting height]. ----- */
  const CAT_AT = { window: { wait: [0.47, 0.79, 0.17], exit: [0.925, 0.79, 0.17] }, counter: { wait: [0.11, 0.7, 0.13], exit: [0.92, 0.7, 0.13] },
    wire: { wait: [0.08, 0.8, 0.11], exit: [0.92, 0.8, 0.11] }, back: { wait: [0.08, 0.8, 0.11], exit: [0.92, 0.8, 0.11] }, door: { wait: [0.88, 0.8, 0.11], exit: [0.44, 0.77, 0.09] } };
  const CAT = { room: "window", spot: "wait", x: 0.47, y: 0.79, s: 0.17, walk: null, face: 1, look: 0, mew: 0, n: -1, box: null };
  const catOpen = r => r === "door" ? ST.stamps.size === 4 : r === "window" || ST.stamps.has(HOST[r]);
  function catPut(room, spot) { const a = CAT_AT[room][spot]; Object.assign(CAT, { room, spot, x: a[0], y: a[1], s: a[2], walk: null, gl: null, hide: false, face: room === "door" ? -1 : 1, look: 1 }); }
  function catGo(spot, ms, then) { const a = CAT_AT[CAT.room][spot], d = Math.hypot(a[0] - CAT.x, (a[1] - CAT.y) * 0.6);
    CAT.walk = { x0: CAT.x, y0: CAT.y, s0: CAT.s, a, t0: performance.now(), d: ms || Math.max(1100, d * 5600), then }; CAT.spot = spot; CAT.face = a[0] >= CAT.x ? 1 : -1; }
  /* after a stamp (or at the start), the cat gets up and goes to the way on */
  function catLead(delay) { const r = CAT.room; setTimeout(() => { if (ST.on && CAT.room === r && CAT.spot !== "exit" && !CAT.walk && catOpen(r)) catGo("exit"); }, delay); }
  function catMew(short) { CAT.mew = performance.now(); AUDIO.meow(short); }
  function drawCat(dx, t) {
    const now = performance.now(), w = CAT.walk; let x = CAT.x, y = CAT.y, s = CAT.s, u = 1;
    if (w) { u = Math.min(1, (now - w.t0) / w.d); const k = u * u * (3 - 2 * u);
      x = w.x0 + (w.a[0] - w.x0) * k; y = w.y0 + (w.a[1] - w.y0) * k; s = w.s0 + (w.a[2] - w.s0) * k;
      if (u >= 1) { Object.assign(CAT, { x: w.a[0], y: w.a[1], s: w.a[2], walk: null, look: 1 }); const f = w.then; w.then = null; f && f(); } }
    /* on a narrow screen the cat is smaller and never steps past the edge */
    const S = s * H * Math.min(1, W / H);
    let X = Math.max(S * 0.5, Math.min(W - S * 0.5, x * W)), Y = y * H;
    /* while the view leans in toward a regular she is kept inside what is still on the screen, never cut off at an edge */
    if (ST.zoom > 1.001 && dx === 0) { const z = ST.zoom, lo = ST.zx - ST.zx / z, hi = ST.zx + (W - ST.zx) / z, bot = ST.zy + (H - ST.zy) / z, top = ST.zy - ST.zy / z, m = S * 0.55;
      X = Math.max(lo + m, Math.min(hi - m, X)); Y = Math.max(top + S * 1.1, Math.min(bot - S * 0.06, Y)); }
    /* where the words of a talk would hide her (a short screen), she sits up on the top edge of the words' frame instead */
    if (dx === 0 && !say.hidden && say.style.visibility !== "hidden") { const r = say.getBoundingClientRect(), d = cv.getBoundingClientRect(), z = ST.zoom, sx = v => ST.zx + (v - ST.zx) * z,
        bx = r.left - d.left, by = r.top - d.top, l = sx(X - S * 0.45), rr = sx(X + S * 0.45), b = ST.zy + (Y + S * 0.05 - ST.zy) * z;
      if (rr > bx && l < bx + r.width && b > by) Y = ST.zy + (by - 2 - ST.zy) / z; }
    X += dx;
    const gl = CAT.gl, gu = gl ? Math.min(1, (now - gl.t0) / gl.d) : 0;
    if (gl && gu >= 1) { CAT.gl = null; CAT.hide = gl.dir === "out"; const f = gl.then; gl.then = null; f && f(); }
    if (CAT.hide && !CAT.gl) { if (dx === 0) CAT.box = null; return; }
    if (CAT.gl) catGlitchDraw(X, Y, S, now, t, CAT.gl.dir === "in" ? gu : 1 - gu); else { g.save(); g.translate(X, Y); catBody(g, S, now, t); g.restore(); }
    if (dx === 0) CAT.box = CAT.gl ? null : { x: X - S * 0.45, y: Y - S * 1.05, w: S * 0.9, h: S * 1.1 };
    if (dx === 0) { const z = ST.zoom, sx = v => ST.zx + (v - ST.zx) * z, sy = v => ST.zy + (v - ST.zy) * z; CAT.seen = { l: sx(X - S * 0.45), r: sx(X + S * 0.45), t: sy(Y - S * 1.05), b: sy(Y + S * 0.05) }; }
  }
  /* when the chain carries a rule, she breaks up into slipping bands of picture and comes back together:
     drawn once into a small canvas, then laid down strip by strip, each strip pushed sideways, with a pale and a dark
     double half a step apart; v = how much of her is there (0 gone, 1 whole) */
  const CATC = document.createElement("canvas"), cc = CATC.getContext("2d"), CATP = document.createElement("canvas"), pc = CATP.getContext("2d");
  function catGlitchDraw(X, Y, S, now, t, v) {
    const bw = Math.ceil(S * 1.8), bh = Math.ceil(S * 1.35), k = K; if (CATC.width !== Math.ceil(bw * k) || CATC.height !== Math.ceil(bh * k)) { CATC.width = Math.ceil(bw * k); CATC.height = Math.ceil(bh * k); }
    cc.setTransform(1, 0, 0, 1, 0, 0); cc.clearRect(0, 0, CATC.width, CATC.height); cc.setTransform(k, 0, 0, k, bw / 2 * k, bh * 0.93 * k); catBody(cc, S, now, t);
    if (CATP.width !== CATC.width || CATP.height !== CATC.height) { CATP.width = CATC.width; CATP.height = CATC.height; }
    pc.globalCompositeOperation = "copy"; pc.drawImage(CATC, 0, 0); pc.globalCompositeOperation = "source-in"; pc.fillStyle = "rgb(236,214,170)"; pc.fillRect(0, 0, CATP.width, CATP.height);
    const amp = Math.pow(1 - v, 0.7) * (0.7 + 0.3 * Math.random()), x0 = X - bw / 2, y0 = Y - bh * 0.93;
    if (Math.random() < 0.22 * (1 - v)) return;   /* a dropped frame now and then */
    g.save();
    /* bands of uneven height, each slipping its own way; the further gone, the more bands are missing */
    for (let sy = 0; sy < bh;) { const sh = Math.max(2, bh * (0.03 + Math.random() * 0.12)), drop = Math.random() > 0.2 + 0.8 * v;
      const off = (Math.random() - 0.5) * S * 1.1 * amp * (Math.random() < 0.25 ? 2 : 1);
      if (!drop) { g.globalAlpha = Math.min(1, 0.45 + v * 0.7); g.drawImage(CATC, 0, sy * k, CATC.width, Math.min(sh, bh - sy) * k, x0 + off, y0 + sy, bw, Math.min(sh, bh - sy)); }
      else if (Math.random() < 0.5) { g.globalAlpha = 0.5 * amp; g.drawImage(CATP, 0, sy * k, CATP.width, Math.min(sh, bh - sy) * k, x0 + off * 1.4, y0 + sy, bw, Math.min(sh, bh - sy)); }
      sy += sh; }
    /* a pale double half a step ahead of her and a dark one behind */
    g.globalAlpha = 0.32 * amp; g.drawImage(CATP, x0 + S * 0.09 * amp, y0 - S * 0.01, bw, bh);
    g.globalAlpha = 0.45 * amp; g.drawImage(CATC, x0 - S * 0.08 * amp, y0 + S * 0.01, bw, bh);
    /* thin lines across her, like a picture that lost its hold */
    g.globalAlpha = 0.35 * amp; g.fillStyle = "rgb(255,236,200)"; for (let i = 0; i < 5; i++) g.fillRect(x0 - S * 0.4 * Math.random(), y0 + Math.random() * bh, bw + S * 0.5, Math.random() < 0.3 ? 2 : 1);
    g.restore();
  }
  function catBody(g, S, now, t) {
    const f = CAT.face;
    /* the shadow under it */
    g.fillStyle = "rgba(0,0,0,.38)"; g.beginPath(); g.ellipse(0, 0, S * (CAT.walk ? 0.42 : 0.3), S * 0.04, 0, 0, 7); g.fill();
    g.scale(S * f, S);
    const fur = "#0b0907", rim = "rgba(255,232,196,.32)", lw = 1 / S;
    g.fillStyle = fur; g.strokeStyle = fur; g.lineCap = g.lineJoin = "round";
    const mew = Math.max(0, 1 - (now - CAT.mew) / 700), tilt = Math.sin(Math.min(1, (now - CAT.mew) / 700) * Math.PI) * 0.12;
    let hx, hy, eyes;
    if (CAT.walk) {
      /* walking: a long low body, four legs in a diagonal gait, the tail up like a question mark */
      const ph = (now - CAT.walk.t0) / 1000 * 7.5, bob = Math.abs(Math.sin(ph)) * 0.015;
      const leg = (lx, o, back) => { const a = Math.sin(ph + o) * 0.42, kx = lx + Math.sin(a) * 0.12, ky = -0.2, fx = lx + Math.sin(a) * 0.26 + (back ? -0.02 : 0.02), fy = -Math.max(0, Math.sin(ph + o + 1.6)) * 0.06;
        g.lineWidth = 0.085; g.beginPath(); g.moveTo(lx, -0.4 - bob); g.quadraticCurveTo(kx + (back ? -0.06 : 0.04), ky, fx, fy); g.stroke(); };
      leg(0.22, Math.PI, false); leg(-0.24, 0, true);
      g.beginPath(); g.moveTo(-0.37, -0.42 - bob); g.bezierCurveTo(-0.4, -0.62, -0.2, -0.64, -0.02, -0.59 - bob); g.bezierCurveTo(0.12, -0.56, 0.24, -0.66, 0.36, -0.62 - bob);
      g.bezierCurveTo(0.44, -0.58, 0.42, -0.36, 0.3, -0.3 - bob); g.bezierCurveTo(0.12, -0.22, -0.16, -0.24, -0.3, -0.29 - bob); g.closePath(); g.fill();
      leg(0.26, 0, false); leg(-0.2, Math.PI, true);
      const sw = Math.sin(ph * 0.5) * 0.05; g.lineWidth = 0.08; g.beginPath(); g.moveTo(-0.33, -0.5 - bob); g.bezierCurveTo(-0.52, -0.56, -0.56, -0.8, -0.5 + sw, -0.92); g.stroke();
      g.lineWidth = 0.06; g.beginPath(); g.moveTo(-0.5 + sw, -0.92); g.quadraticCurveTo(-0.46 + sw, -1.0, -0.4 + sw * 1.4, -0.97); g.stroke();
      hx = 0.44; hy = -0.68 - bob; eyes = 1;
    } else {
      /* sitting: a pear of a body, the chest toward the way on, the tail curled round the paws and flicking at the tip */
      const fl = Math.sin(t * 1.7) * 0.5 + Math.sin(t * 4.3) * 0.2, br = Math.sin(t * 1.9) * 0.006;
      g.beginPath(); g.moveTo(-0.3, 0); g.bezierCurveTo(-0.38, -0.26, -0.26, -0.6 - br, -0.04, -0.66 - br); g.bezierCurveTo(0.1, -0.67, 0.18, -0.5, 0.16, -0.34);
      g.bezierCurveTo(0.15, -0.2, 0.2, -0.06, 0.22, 0); g.closePath(); g.fill();
      g.lineWidth = 0.075; g.beginPath(); g.moveTo(-0.28, -0.03); g.bezierCurveTo(-0.12, 0.03, 0.2, 0.03, 0.34, -0.03); g.quadraticCurveTo(0.42, -0.08 - fl * 0.06, 0.4 + fl * 0.04, -0.17 - fl * 0.06); g.stroke();
      g.lineWidth = 0.07; g.beginPath(); g.moveTo(0.12, -0.3); g.lineTo(0.15, -0.01); g.stroke();
      hx = 0.03; hy = -0.78 - br; eyes = 0;
    }
    /* the head: turned toward the reader when it sits, ears up, two amber eyes that blink now and then */
    g.save(); g.translate(hx, hy); g.rotate(-tilt * (CAT.walk ? 0 : 1));
    g.beginPath(); g.ellipse(0, 0, 0.15, 0.13, 0, 0, 7); g.fill();
    if (!CAT.walk) { g.beginPath(); g.ellipse(0, 0.07, 0.08, 0.06, 0, 0, 7); g.fill(); }
    else { g.beginPath(); g.ellipse(0.11, 0.04, 0.07, 0.055, 0, 0, 7); g.fill(); }
    const ear = (ex, lean) => { g.beginPath(); g.moveTo(ex - 0.06, -0.08); g.lineTo(ex + lean, -0.24); g.lineTo(ex + 0.07, -0.07); g.closePath(); g.fill(); };
    if (CAT.walk) { ear(-0.02, 0.01); ear(0.07, 0.03); } else { ear(-0.08, -0.03); ear(0.08, 0.03); }
    const blink = (t % 4.7) < 0.14 ? 0.15 : 1, eh = 0.026 * blink, glow = "rgba(232,196,110,.95)";
    g.fillStyle = glow;
    const eye = ex => { g.beginPath(); g.ellipse(ex, -0.005, 0.03, eh, 0, 0, 7); g.fill(); if (blink > 0.5) { g.fillStyle = fur; g.beginPath(); g.ellipse(ex - (eyes ? -0.004 : 0.004 * f), -0.005, 0.008, eh * 0.9, 0, 0, 7); g.fill(); g.fillStyle = glow; } };
    if (CAT.walk) eye(0.1); else { eye(-0.055); eye(0.055); }
    if (mew > 0 && !CAT.walk) { g.fillStyle = "#2a1712"; g.beginPath(); g.ellipse(0, 0.085, 0.022, 0.03 * mew, 0, 0, 7); g.fill(); }
    g.restore();
    /* the lamp catches the top of the fur */
    g.globalCompositeOperation = "screen"; g.strokeStyle = rim; g.lineWidth = lw * 1.4;
    g.beginPath(); if (CAT.walk) { g.moveTo(-0.32, -0.58); g.bezierCurveTo(-0.15, -0.63, 0.12, -0.56, 0.3, -0.63); } else { g.moveTo(-0.27, -0.3); g.bezierCurveTo(-0.24, -0.55, -0.12, -0.64, -0.04, -0.66); } g.stroke();
    g.beginPath(); g.ellipse(hx, hy, 0.15, 0.13, 0, Math.PI * 1.1, Math.PI * 1.75); g.stroke();
    g.globalCompositeOperation = "source-over";
  }
  /* the rule is carried and the cat walks by. Then it walks by again, the very same way. */
  /* she breaks up and comes back (with reduced motion she just is there, or isn't) */
  function catGlitch(dir, d, then) { if (RM) { CAT.hide = dir === "out"; then && then(); return; } CAT.gl = { dir, t0: performance.now(), d, then }; AUDIO.glitch(); }
  /* the rule is carried and the cat crosses the counter: she flickers in, walks, breaks up at the far end, and then
     the very same walk again. The second time she stays, sitting at the way on. */
  function catDeja() { if (CAT.room !== "counter") return; const here = () => ST.on && ST.area === "counter" && CAT.room === "counter";
    const pass = last => { catPut("counter", "wait"); CAT.face = 1; CAT.hide = false; catGo("exit", 2300); catGlitch("in", 480);
      if (last) { CAT.walk.then = () => here() && flash(TX.cat.deja); return; }
      setTimeout(() => here() && catGlitch("out", 460, () => { CAT.walk = null; setTimeout(() => here() && pass(true), 320); }), 2300 - 460); };
    setTimeout(() => { if (here()) catGlitch("out", 420, () => setTimeout(() => here() && pass(false), 250)); }, 700); }
  function catClick() { const L = TX.cat.lines; CAT.n = (CAT.n + 1) % L.length; if (CAT.n % 2) AUDIO.purr(); else catMew(true); CAT.mew = performance.now(); flash(L[CAT.n], CAT.box);
    /* the first line is the one about her food, and that rule is real: her bowl is on the testnet */
    if (CAT.n === 0) { const a = document.createElement("a"); a.href = "https://agorzilla.com/cat/"; a.target = "_blank"; a.rel = "noopener"; a.textContent = TX.cat.bowl; note.appendChild(a); clearTimeout(flashT); flashT = setTimeout(() => note.classList.remove("on"), 9000); } }
  function arrived() { ST.arriveAt = performance.now(); if (ST.area === "wire") AUDIO.ticker(); keep(); prep([nb(1), nb(-1)]); }

  /* ----- talking ----- */
  let TYPE = null;
  function talk(who) {
    if (ST.talk || ST.pan) return; const P = TX.people[who], box = ST.boxes.person; ST.talk = { who, asked: new Set() }; ST.talked = true; ST.hover = null;
    if (box) { ST.zx = box.hx; ST.zy = box.hy + H * 0.08; ST.zoomT = small() ? 1.08 : 1.22; }
    say.hidden = false; $(".cs-who b").textContent = P.name; $(".cs-who i").textContent = P.role; hintEl.classList.remove("on"); note.classList.remove("on");
    let open = P.greet;
    if (who === "sully") { const miss = ["mae", "elias", "prof"].filter(k => !ST.stamps.has(k)).map(k => TX.people[k].name);
      open = miss.length ? P.greet.concat(fmt(P.missing, { who: miss.length > 1 ? miss.slice(0, -1).join(TX.sep) + TX.and + miss[miss.length - 1] : miss[0] })) : P.greetDone; }
    const W = wk(who); if (W && W.greet) { const k = who === "sully" && open !== P.greetDone ? P.greet.length : open.length; open = open.slice(0, k).concat(tr(W.greet), open.slice(k)); }
    lines(open, () => choices());
  }
  /* this week's talk: the Monday edition (infra/alerts/gazette.py cafe()) brings a line and a question for each regular */
  const wk = who => { const c = window.GAZETTE_WEEK && window.GAZETTE_WEEK.cafe; return c && c[who]; };
  const tr = o => o && typeof o === "object" ? (o[LANG] || o.en) : o;
  function lines(arr, done) { let i = 0; const nx = () => { if (i >= arr.length) return done(); typeLine(line(arr[i++]), nx); }; nx(); }
  function typeLine(s, next) {
    clearInterval(TYPE && TYPE.id); sayCh.innerHTML = ""; say.classList.remove("ask"); say.classList.add("typing");
    const chars = [...s], cps = /zh|ja/.test(LANG) ? 22 : 46, who = ST.talk.who; let n = 0;
    const doneTyping = () => { clearInterval(TYPE.id); sayLine.textContent = s; ST.mouthT = 0; say.classList.remove("typing"); TYPE.done = true; };
    TYPE = { s, next, done: false, id: setInterval(() => { n++; sayLine.textContent = chars.slice(0, n).join("");
      const c = chars[n - 1] || ""; if (/[\s,.;:!?…—、。，！？]/.test(c)) ST.mouthT = 0.1; else if (n % (/zh|ja/.test(LANG) ? 1 : 3) === 0) { ST.mouthT = 0.5 + Math.random() * 0.5; AUDIO.syllable(who, /[A-Z]/.test(c)); }
      if (n >= chars.length) doneTyping(); }, 1000 / cps) };
    if (RM) doneTyping();
  }
  /* a click on the words: finish the line, or go on to the next */
  say.addEventListener("click", e => { if (e.target.closest("button")) return; adv(); });
  function adv() { if (!TYPE) return; if (!TYPE.done) { clearInterval(TYPE.id); sayLine.textContent = TYPE.s; ST.mouthT = 0; say.classList.remove("typing"); TYPE.done = true; return; } if (!say.classList.contains("ask")) TYPE.next(); }
  function choices() {
    const T = ST.talk, P = TX.people[T.who], all = ["mae", "elias", "prof", "sully"].every(k => ST.stamps.has(k));
    say.classList.add("ask"); sayCh.innerHTML = "";
    const add = (q, fn, dim) => { const b = document.createElement("button"); b.textContent = q; if (dim) b.className = "dim"; b.onclick = e => { e.stopPropagation(); fn(); }; sayCh.appendChild(b); };
    P.ask.forEach(a => add(a.q, () => answer(a), T.asked.has(a.id)));
    const W = wk(T.who); if (W && W.q && W.a) { add(tr(W.q), () => { T.asked.add("week"); lines(W.a.map(tr), choices); }, T.asked.has("week")); const tag = document.createElement("i"); tag.className = "wk"; tag.textContent = TX.thisWeek; sayCh.lastChild.appendChild(tag); }
    const key = P.ask.find(a => a.key); if (key && T.asked.has(key.id) && !ST.stamps.has(T.who)) { sayCh.insertBefore(sayCh.lastChild, sayCh.firstChild); add(P.task.q, () => task()); sayCh.insertBefore(sayCh.lastChild, sayCh.firstChild); }
    if (T.who === "sully" && all) add(P.out.q, () => { lines(P.out.a, () => { closeTalk(); outside(); }); });
    add(P.bye.q, () => lines(P.bye.a, closeTalk));
    const f = sayCh.querySelector("button:not(.dim)") || sayCh.querySelector("button"); if (f) f.focus({ preventScroll: true });
  }
  function answer(a) {
    const T = ST.talk; T.asked.add(a.id);
    if (T.who === "elias" && a.id === "tape") { AUDIO.ticker(); }
    if (T.who === "prof" && a.id === "logic") { setTimeout(AUDIO.clack, 600); }
    lines(a.a, () => { if (a.key && !ST.stamps.has(T.who)) task(); else choices(); });
  }
  /* ----- each regular hands you something to do, and the stamp comes with it ----- */
  function task() {
    const T = ST.talk, who = T.who, K = TX.people[who].task; T.task = who;
    lines(K.ask, () => {
      say.classList.add("ask"); sayCh.innerHTML = "";
      if (who === "mae") { ST.task = "chalk"; flash(K.hint, ST.boxes.props && ST.boxes.props.find(p => p.id === "board")); }
      else if (who === "sully") { ST.task = "ticket"; $(".cafe-ticket").classList.add("offer"); $(".cafe-ticket").tabIndex = 0; $(".cafe-ticket").focus({ preventScroll: true }); }
      else { ST.task = who; const h = live(), base = h != null ? h : 3100;
        const opts = who === "elias" ? [[base + 1, base - 3], [base + 1, base], [base + 4, base + 2]].map(([n, m]) => fmt(K.slip, { n: num(n), m: num(m) })) : K.opts;
        const right = who === "elias" ? 1 : K.right, order = who === "elias" ? [2, 0, 1] : [0, 1, 2];
        order.forEach(i => { const b = document.createElement("button"); b.className = "pick " + (who === "elias" ? "slip" : "chalk"); b.textContent = opts[i];
          b.onclick = e => { e.stopPropagation(); if (i === right) { AUDIO.clack(); done(); } else { AUDIO.syllable(who); b.classList.add("no"); sayLine.textContent = K.wrong; } }; sayCh.appendChild(b); });
        sayCh.querySelector("button").focus({ preventScroll: true }); } });
  }
  function done() {
    const T = ST.talk; if (!T) return; const who = T.who, K = TX.people[who].task; ST.task = null; say.style.visibility = ""; if (ST.zoomBack) { ST.zoomT = ST.zoomBack; ST.zoomBack = 0; } $(".cafe-ticket").classList.remove("offer");
    if (who === "elias") AUDIO.ticker();
    say.classList.remove("ask"); sayCh.innerHTML = ""; lines(K.done, () => { stamp(who); edges(); choices(); });
  }
  /* the board, clicked while Mae waits: the tally goes up mark by mark and the rule is carried */
  function chalkIn() { ST.task = null; TALLY.at = performance.now() - 1800; ST.zoomBack = ST.zoomT; ST.zoomT = 1; say.style.visibility = "hidden"; catDeja(); [0, 900, 1800, 2700, 3600, 5400].forEach(ms => setTimeout(() => ST.area === "counter" && AUDIO.chalk(), ms)); note.classList.remove("on"); setTimeout(done, 6400); }
  $(".cafe-ticket").addEventListener("click", e => { if (ST.task !== "ticket") return; e.stopPropagation(); AUDIO.rustle(); done(); });
  $(".cafe-ticket").addEventListener("keydown", e => { if (ST.task === "ticket" && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); AUDIO.rustle(); done(); } });
  /* every stamp ever earned in this browser, for the reader's Tau card (/card/); the walk itself starts fresh each time */
  function keepStamp(who) { try { const k = "tauhud-cafe-stamps", had = JSON.parse(localStorage.getItem(k) || "[]").filter(x => typeof x === "string"); localStorage.setItem(k, JSON.stringify(had.includes(who) ? had : [...had, who])); } catch (e) {} }
  function stamp(who) {
    ST.stamps.add(who); keepStamp(who); ticket(); AUDIO.stamp(); const tk = $(".cafe-ticket"); tk.classList.remove("thud"); void tk.offsetWidth; tk.classList.add("thud");
    catLead(who === "sully" ? 1400 : 1100);
    let msg = fmt(TX.stamped, { name: TX.people[who].name, what: TX.stampFor[who] }); if (ST.stamps.size === 4) msg += " " + TX.full; flash(msg);
  }
  function closeTalk() { say.style.visibility = ""; ST.zoomBack = 0; if (!ST.talk) return; if (ST.task === "ticket") $(".cafe-ticket").classList.remove("offer"); if (ST.task !== "chalk") ST.task = null; clearInterval(TYPE && TYPE.id); TYPE = null; ST.talk = null; ST.mouthT = 0; ST.zoomT = 1; say.hidden = true; }
  let flashT = 0; function flash(s, box) { note.textContent = s; note.classList.add("on"); note.style.left = box ? Math.max(8, Math.min(W - 300, box.x + box.w / 2 - 150)) + "px" : ""; note.style.top = box ? Math.max(70, box.y - 60) + "px" : ""; note.classList.toggle("free", !!box);
    clearTimeout(flashT); flashT = setTimeout(() => note.classList.remove("on"), 6000); }

  /* ----- clicks on the room ----- */
  const PROP_SOUND = { urn: () => AUDIO.hiss(), register: () => AUDIO.ching(), ticker: () => AUDIO.ticker(), clocks: () => AUDIO.key(), books: () => AUDIO.rustle(), bundle: () => AUDIO.rustle(), bell: () => AUDIO.bell(), slate: () => AUDIO.chalk(), board: () => AUDIO.chalk(), pie: () => AUDIO.clack(), coats: () => AUDIO.rustle(), gramophone: () => AUDIO.clack() };
  /* ----- a closer look: a click on a thing in the room opens it up beside the reader, as if leaning in ----- */
  const look = document.createElement("div"); look.className = "cafe-look"; look.setAttribute("role", "dialog"); look.hidden = true;
  look.innerHTML = `<div class="lk-pic"></div><p class="lk-cap"></p><button class="lk-x" aria-label="✕">✕</button>`; ui.appendChild(look);
  let LOOK = null;
  const ZONES = { "New York": "America/New_York", London: "Europe/London", Berlin: "Europe/Berlin", Tokyo: "Asia/Tokyo" };
  const clockSvg = (d, tz) => { const p = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "numeric", minute: "numeric", second: "numeric", hourCycle: "h23" }).formatToParts(d).map(x => [x.type, +x.value]));
    const hand = (a, l, w) => `<line x1="50" y1="50" x2="${50 + l * Math.sin(a)}" y2="${50 - l * Math.cos(a)}" stroke-width="${w}" stroke-linecap="round"/>`;
    const ticks = [...Array(12)].map((_, i) => { const a = i * Math.PI / 6; return `<line x1="${50 + 38 * Math.sin(a)}" y1="${50 - 38 * Math.cos(a)}" x2="${50 + 43 * Math.sin(a)}" y2="${50 - 43 * Math.cos(a)}" stroke-width="${i % 3 ? 1.2 : 2.6}"/>`; }).join("");
    return `<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="47" class="rim"/><circle cx="50" cy="50" r="44" class="face"/><g class="ink">${ticks}${hand((p.hour % 12 + p.minute / 60) * Math.PI / 6, 24, 3.4)}${hand((p.minute + p.second / 60) * Math.PI / 30, 34, 2.2)}</g><g class="sec">${hand(p.second * Math.PI / 30, 38, 0.9)}</g><circle cx="50" cy="50" r="2.6" class="pin"/></svg>`; };
  const LOOKS = {
    ticker: () => { const h = live(), L = TX.look.slip, a = window.GAZETTE_LIVE && Number.isFinite(window.GAZETTE_LIVE.age) ? window.GAZETTE_LIVE.at - window.GAZETTE_LIVE.age * 1000 : null;
      const tm = a ? new Date(a).toISOString().slice(11, 19) : null;
      return `<div class="lk-tape">${[0, 1, 2].map(k => { const n = h != null ? h - k : null; return `<div class="lk-slip${k ? "" : " new"}"><b>${L.block} ${n != null ? num(n) : "…"}</b><span>${n != null ? fmt(L.mark, { m: num(n - 1) }) : L.markN}</span>${!k && tm ? `<i>${fmt(L.at, { t: tm })}</i>` : ""}</div>`; }).join("")}</div>`; },
    board: () => `<div class="lk-chalk board">${TX.board.map((l, i) => i === TX.board.length - 1 ? (ST.stamps.has("mae") ? `<p class="carried">${l} ✓</p>` : `<p class="tally">|||| &nbsp;|</p>`) : `<p${i ? (i === TX.board.length - 2 ? ' class="prop"' : "") : ' class="h"'}>${l}</p>`).join("")}</div>`,
    slate: () => `<div class="lk-chalk slate">${TX.logic.map((l, i) => `<p${i === TX.logic.length - 1 ? ' class="bot"' : ""}>${l}</p>`).join("")}</div>`,
    clocks: () => `<div class="lk-clocks">${TX.clocks.map((c, i) => `<figure>${clockSvg(new Date(), Object.values(ZONES)[i])}<figcaption>${c}</figcaption></figure>`).join("")}</div>`,
    papers: () => LOOKS.bundle(TX.look.slip.papers),
    bundle: head => { const wk = window.GAZETTE_WEEK, name = (window.GAZETTE_ZH && LANG === "zh" && window.GAZETTE_ZH.name) || (window.GAZETTE_JA && LANG === "ja" && window.GAZETTE_JA.name) || "The Daily Consensus";
      return `<div class="lk-paper"><div class="lp-name">${name}</div><div class="lp-rule"></div><div class="lp-head">${esc(head || (wk && wk.banner ? tr(wk.banner) : TX.look.slip.head))}</div><div class="lp-cols"><span></span><span></span><span></span></div><div class="lp-string"></div></div>`; },
  };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function crop(b) {
    const m = 0.22, x = Math.max(0, b.x - b.w * m), y = Math.max(0, b.y - b.h * m), w = Math.min(W - x, b.w * (1 + 2 * m)), h = Math.min(H - y, b.h * (1 + 2 * m));
    const c = document.createElement("canvas"), s = Math.min(3, 420 / Math.max(w, h)); c.width = Math.round(w * s * 1.5); c.height = Math.round(h * s * 1.5);
    c.getContext("2d").drawImage(cv, x * K, y * K, w * K, h * K, 0, 0, c.width, c.height); c.className = "lk-crop"; return c;
  }
  const TABLE = { cup: 1, sugar: 1, papers: 1 };   /* the things on your own table by the window (scene.js) */
  /* where the close-up goes: next to the thing, over as little of the story as it can (the regular, the board, the slate, the door, the words) */
  function spot(box, w, h) {
    const gap = 18, top = small() ? 96 : 70, bot = 12, keep = [], b = ST.boxes, pad = r => ({ x: r.x - 12, y: r.y - 12, w: r.w + 24, h: r.h + 24 });
    if (b.person) keep.push({ ...pad({ x: b.person.x, y: b.person.y - b.person.w * 0.4, w: b.person.w, h: b.person.h + b.person.w * 0.4 }), k: 3 });
    for (const q of b.props || []) if (q !== box && /^(board|slate|clocks|door|ticker|papers)$/.test(q.id)) keep.push({ ...pad(q), k: 2 });
    if (!say.hidden) { const r = say.getBoundingClientRect(), u = ui.getBoundingClientRect(); keep.push({ x: r.left - u.left, y: r.top - u.top, w: r.width, h: r.height, k: 3 }); }
    /* the painted signs over the counter and the wire are part of the picture too */
    for (const [a, x0, y0, x1, y1] of [["counter", 0.3, 0.17, 0.62, 0.3], ["wire", 0.38, 0.17, 0.64, 0.28]]) if (ST.area === a) keep.push({ x: W * x0, y: H * y0, w: W * (x1 - x0), h: H * (y1 - y0), k: 2 });
    keep.push({ ...pad(box), k: 6 });
    const ov = (a, c) => Math.max(0, Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x)) * Math.max(0, Math.min(a.y + a.h, c.y + c.h) - Math.max(a.y, c.y));
    const cl = (x, y) => ({ x: Math.max(12, Math.min(W - w - 12, x)), y: Math.max(top, Math.min(H - h - bot, y)), w, h });
    const cx = box.x + box.w / 2, cy = box.y + box.h / 2, c = [];
    for (const f of [0.5, 0.15, 0.85]) {
      c.push(cl(box.x + box.w + gap, cy - h * f), cl(box.x - gap - w, cy - h * f), cl(cx - w * f, box.y - gap - h), cl(cx - w * f, box.y + box.h + gap)); }
    let best = null;
    for (const r of c) { const cost = keep.reduce((a, k) => a + ov(r, k) * k.k, 0) / (w * h) * 1000 + Math.hypot(r.x + w / 2 - cx, r.y + h / 2 - cy) * 0.4; if (!best || cost < best.cost) best = { ...r, cost }; }
    return best;
  }
  function lookAt(id, box, tries = 0) {
    if (!box) return; const pic = look.querySelector(".lk-pic"), N = window.GAZETTE_NOTE || {}, v = TX.props[id];
    pic.innerHTML = ""; pic.className = "lk-pic " + (LOOKS[id] ? "lk-of-" + id : "lk-photo");
    if (LOOKS[id]) pic.innerHTML = LOOKS[id](); else pic.appendChild(crop(box));
    const L = window.GAZETTE_LIVE || {}, age = Number.isFinite(L.age) ? L.age + Math.round((Date.now() - L.at) / 1000) : null;
    const more = TABLE[id] && N[id] ? N[id](live(), age) : TX.look[id] || "";
    look.querySelector(".lk-cap").innerHTML = `<b>${esc(typeof v === "function" ? v(live()) : v || "")}</b> ${esc(more)}`;
    look.classList.remove("on"); look.hidden = false; look.style.visibility = "hidden"; look.style.left = "0px"; look.style.top = "0px";
    const w = look.offsetWidth, h = look.offsetHeight; if (!w || !h) { look.hidden = true; return tries < 40 && setTimeout(() => lookAt(id, box, tries + 1), 150); }
    const r = spot(box, w, h);
    look.style.left = Math.round(r.x) + "px"; look.style.top = Math.round(r.y) + "px"; look.style.visibility = "";
    look.style.transformOrigin = `${Math.round(Math.max(0, Math.min(1, (box.x + box.w / 2 - r.x) / w)) * 100)}% ${Math.round(Math.max(0, Math.min(1, (box.y + box.h / 2 - r.y) / h)) * 100)}%`;
    requestAnimationFrame(() => look.classList.add("on")); note.classList.remove("on"); hintEl.classList.remove("on");
    clearInterval(LOOK && LOOK.tick); LOOK = { id, tick: id === "clocks" ? setInterval(() => { const f = look.querySelectorAll(".lk-clocks figure svg"); f.forEach((s, i) => s.outerHTML = clockSvg(new Date(), Object.values(ZONES)[i])); }, 1000) : 0 };
    if (TABLE[id] && S.touch) S.touch(id); else (PROP_SOUND[id] || (() => {}))();
    look.querySelector(".lk-x").focus({ preventScroll: true });
  }
  function lookOff() { if (!LOOK) return false; clearInterval(LOOK.tick); LOOK = null; if (look.contains(document.activeElement)) document.activeElement.blur(); look.classList.remove("on"); setTimeout(() => { if (!LOOK) look.hidden = true; }, 260); return true; }
  look.addEventListener("click", e => { e.stopPropagation(); lookOff(); });
  const at = e => { const r = cv.getBoundingClientRect(); let x = e.clientX - r.left, y = e.clientY - r.top; if (ST.zoom > 1.001) { x = (x - ST.zx) / ST.zoom + ST.zx; y = (y - ST.zy) / ST.zoom + ST.zy; } return [x, y]; };
  const inside = (b, [x, y]) => b && x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h;
  function pick(e) {
    if (ST.pan || END.on) return null; const p = at(e), b = ST.boxes;
    if (!ST.talk && CAT.room === ST.area && inside(CAT.box, p)) return { cat: true };
    if (ST.area !== "window" && inside(b.person, p)) return { person: b.person.id };
    const pr = (b.props || []).find(q => inside(q, p)); return pr ? { prop: pr } : null;
  }
  let down = null;
  cv.addEventListener("pointerdown", e => { down = { x: e.clientX, y: e.clientY, t: Date.now() }; e.stopPropagation(); });
  cv.addEventListener("pointerup", e => { e.stopPropagation(); const d = down; down = null; if (!d || !ST.on) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) return walk(dx < 0 ? 1 : -1);
    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) return;
    if (lookOff()) return;
    const h = pick(e);
    /* Mae's task: the board takes the chalk even while her words are still on screen */
    if (h && h.prop && h.prop.id === "board" && ST.task === "chalk") return chalkIn();
    if (ST.talk) return adv();
    if (!h) return;
    if (h.cat) return catClick();
    if (h.person) return talk(h.person);
    if (h.prop.id === "board" && ST.task === "chalk") return chalkIn();
    if (h.prop.id === "door") { if (["mae", "elias", "prof", "sully"].every(k => ST.stamps.has(k))) return outside(); return flash(TX.people.sully.shut, h.prop); }
    lookAt(h.prop.id, h.prop); });
  cv.addEventListener("click", e => e.stopPropagation());
  cv.addEventListener("pointermove", e => { if (!ST.on) return; const r = cv.getBoundingClientRect(); if (!touch && !RM) ST.camT = ((e.clientX - r.left) / r.width - 0.5) * 0.36;
    const h = pick(e); cv.style.cursor = h ? "pointer" : ""; ST.hover = h && h.person || null; if (h && h.cat) { ST.hoverProp = null; return; } ST.hoverProp = h && h.prop ? h.prop.id : null; });
  ui.addEventListener("click", e => { const k = e.target.closest("[data-k]"); if (!k) return; e.stopPropagation();
    if (k.dataset.k === "back") leave(); else if (k.dataset.k === "left") walk(-1); else if (k.dataset.k === "right") walk(1);
    else if (k.dataset.k === "snd" && S.amb_btn) { S.amb_btn.click(); setTimeout(() => { sndLabel(); mix(); }, 50); } });
  /* the keyboard: arrows walk, Enter and Space go on, numbers choose, Escape steps back */
  addEventListener("keydown", e => { if (!ST.on) return; if (e.target.closest && e.target.closest("input, textarea, select")) return;
    e.stopImmediatePropagation();
    if (e.key === "Escape") { e.preventDefault(); return lookOff() || (ST.talk ? closeTalk() : leave()); }
    if (LOOK) { if (e.key === "Enter" || e.key === " " || /^Arrow/.test(e.key)) { e.preventDefault(); lookOff(); } return; }
    if (END.on) { if (e.key === "Enter" || e.key === " " || e.key === "ArrowRight") { if (!(e.target.closest && e.target.closest(".ce-paper"))) { e.preventDefault(); nextCard(); } } return; }
    if (ST.task === "chalk" && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); return chalkIn(); }
    if (ST.talk) { if (/^Arrow/.test(e.key)) { e.preventDefault(); const bs = [...sayCh.querySelectorAll("button:not(.no)")]; if (!bs.length) return;
        const i = bs.indexOf(document.activeElement), d = e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 1; bs[i < 0 ? (d > 0 ? 0 : bs.length - 1) : (i + d + bs.length) % bs.length].focus(); return; }
      if (/^[1-9]$/.test(e.key) && say.classList.contains("ask")) { const b = sayCh.querySelectorAll("button")[+e.key - 1]; if (b) b.click(); return; }
      if ((e.key === "Enter" || e.key === " ") && !(e.target.closest && e.target.closest(".cs-ch button"))) { e.preventDefault(); adv(); } return; }
    /* Tab picks out the things in the room one by one (a faint glint), Enter leans in */
    const things = (ST.boxes.props || []).filter(q => q.id !== "door" || ST.stamps.size === 4);
    if (e.key === "Tab" && !ST.pan && things.length && !(e.target.closest && e.target.closest("button"))) { const i = things.findIndex(q => q.id === ST.kProp), j = i + (e.shiftKey ? -1 : 1);
      if (i >= 0 && (j < 0 || j >= things.length)) { ST.kProp = ST.hoverProp = null; return; }   /* past the last thing: Tab goes on to the buttons */
      e.preventDefault(); ST.kProp = ST.hoverProp = things[i < 0 ? (e.shiftKey ? things.length - 1 : 0) : j].id; return; }
    if (e.key === "ArrowLeft") { e.preventDefault(); ST.kProp = null; walk(-1); } else if (e.key === "ArrowRight") { e.preventDefault(); ST.kProp = null; walk(1); }
    else if ((e.key === "Enter" || e.key === " ") && !(e.target.closest && e.target.closest("button"))) { const k = ST.kProp && things.find(q => q.id === ST.kProp);
      if (k) { e.preventDefault(); if (k.id === "door") return outside(); if (k.id === "board" && ST.task === "chalk") return chalkIn(); return lookAt(k.id, k); }
      if (AREAS[ST.area].person) { e.preventDefault(); talk(AREAS[ST.area].person.id); } } }, true);

  /* ============ the ending: out through the door onto Market Street ============ */
  let STREET = null;
  const street = () => { if (!STREET) { STREET = document.createElement("canvas"); STREET.width = Math.round(W * K); STREET.height = Math.round(H * K); const x = STREET.getContext("2d"); x.setTransform(K, 0, 0, K, 0, 0); S.street(x, W, H); } return STREET; };
  function outside() {
    END.on = true; END.t0 = performance.now(); END.card = -1; hintEl.classList.remove("on"); note.classList.remove("on"); desk.classList.add("cafe-ending"); ui.querySelector(".cafe-top").classList.add("gone");
    AUDIO.bell(); setTimeout(AUDIO.creak, 150); S.amb.mix({ street: 1.7, open: 1, music: 0.35 }); setTimeout(AUDIO.swell, 1400);
    $(".cafe-end").hidden = false; loop();
  }
  const OPEN = 1800, cardMs = k => Math.max(4000, 1000 + 60 * [...TX.end.lines[k]].length * (/zh|ja/.test(LANG) ? 2.2 : 1));
  function showCard(k, now = performance.now()) {
    const c = $(".ce-card"), n = TX.end.lines.length; END.card = k; END.cardAt = now; c.classList.remove("on");
    if (k >= n) { if (!END.paper) { END.paper = true; setTimeout(() => extra(RM || small()), 700); } return; }
    setTimeout(() => { if (END.card !== k) return; c.textContent = TX.end.lines[k]; c.classList.add("on"); }, k ? 900 : 0);
  }
  const nextCard = () => { if (END.on && END.card >= 0 && !END.paper && performance.now() - END.cardAt > 1200) showCard(END.card + 1); };
  ui.querySelector(".cafe-end").addEventListener("click", e => { if (!e.target.closest(".ce-paper")) nextCard(); });
  function endFrame(now, t) {
    const e = now - END.t0, quiet = RM || small(), n = TX.end.lines.length;
    if (e < OPEN) {
      /* the door swings in and the morning floods the room */
      drawArea("door", 0, t); const u = e / OPEN, a = Math.min(1, u * u * 1.4); g.drawImage(finish(), 0, 0, W, H);
      g.fillStyle = rad(g, W * 0.38, H * 0.45, 0, Math.max(W, H) * (0.2 + u * 1.2), [[0, `rgba(255,246,225,${a})`], [0.6, `rgba(250,225,175,${a * 0.85})`], [1, `rgba(250,225,175,${a * 0.2})`]]); g.fillRect(0, 0, W, H);
      return; }
    /* on the pavement: the street, sharp now, the streetcars running; the view drifts slowly down the street */
    const u = (e - OPEN) / 26000, z = quiet ? 1 : 1 + Math.min(1, u) * 0.16, cx = W * 0.2, cy = H * 0.46;
    g.save(); g.translate(cx, cy); g.scale(z, z); g.translate(-cx, -cy); g.drawImage(street(), 0, 0, W, H); g.drawImage(S.layers[1], 0, 0, W, H); g.drawImage(S.layers[2], 0, 0, W, H); g.restore();
    const vig = g.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.3, W / 2, H * 0.5, Math.max(W, H) * 0.8); vig.addColorStop(0, "rgba(0,0,0,0)"); vig.addColorStop(1, "rgba(0,0,0,.7)"); g.fillStyle = vig; g.fillRect(0, 0, W, H);
    const fl = Math.max(0, 1 - (e - OPEN) / 2200); if (fl > 0) { g.fillStyle = `rgba(255,246,225,${fl})`; g.fillRect(0, 0, W, H); }
    /* the cards, one by one, like a picture show; each stays long enough to read (a click or a key goes on) */
    if (END.card < 0 && e > OPEN + 1200) showCard(0, now);
    else if (END.card >= 0 && END.card < n && now - END.cardAt > cardMs(END.card)) showCard(END.card + 1, now);
  }
  /* the Extra! comes spinning in and lands, the reader's own front page */
  function extra(quiet) {
    const E = TX.end, h = live(), p = $(".ce-paper"), name = (window.GAZETTE_ZH && LANG === "zh" && window.GAZETTE_ZH.name) || (window.GAZETTE_JA && LANG === "ja" && window.GAZETTE_JA.name) || "The Daily Consensus";
    const d = new Date(), date = d.toLocaleDateString(LANG === "en" ? "en-US" : LANG, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    p.innerHTML = `<div class="cp-mast">${name.replace(/\{\{NAME\}\}/g, "")}</div><div class="cp-date">${date}</div><div class="cp-extra">${E.extra}</div><h2 class="cp-head">${E.head}</h2><p class="cp-deck">${E.deck}</p><p class="cp-block">${h != null ? fmt(E.block.h, { h: num(h) }) : E.block.n}</p><p class="cp-fine">${E.fine}</p>
      <div class="cp-share"><b class="cp-sh">☞ ${E.share}</b><i class="cp-sub">${E.shareSub}</i><span class="cp-row"><a data-e="x" target="_blank" rel="noopener">${E.onX}</a><button data-e="copy">${E.copy}</button><button data-e="share" hidden>${E.shareMore}</button></span></div>
      <div class="cp-go"><button data-e="paper">${E.paper}</button><a href="/">${E.live}</a><a href="/playground/">${E.play}</a><button data-e="again">${E.again}</button></div>`;
    p.hidden = false; p.classList.toggle("quiet", quiet); if (!quiet) AUDIO.whoosh(); else AUDIO.rustle();
    p.querySelector("[data-e=paper]").onclick = e => { e.stopPropagation(); reset(); leave(); };
    p.querySelector("[data-e=again]").onclick = e => { e.stopPropagation(); reset(); leave(); enter(); };
    /* pass the paper on: the phone's own share sheet where there is one, otherwise X and a link to copy */
    const url = "https://tauhud.com/gazette/walk/" + (LANG !== "en" ? "?lang=" + LANG : ""), x = p.querySelector("[data-e=x]");
    x.href = "https://x.com/intent/post?text=" + encodeURIComponent(E.shareText) + "&url=" + encodeURIComponent(url);
    const sh = p.querySelector("[data-e=share]"); sh.hidden = !navigator.share;
    sh.onclick = e => { e.stopPropagation(); navigator.share({ title: E.head, text: E.shareText, url }).catch(() => {}); };
    p.querySelector("[data-e=copy]").onclick = e => { e.stopPropagation(); const b = e.currentTarget, ok = () => { b.textContent = E.copied; setTimeout(() => b.textContent = E.copy, 2500); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(ok, () => prompt(E.copy, url)); else prompt(E.copy, url); };
    setTimeout(() => p.querySelector("[data-e=paper]").focus({ preventScroll: true }), quiet ? 300 : 1800);
  }
  function reset() { ST.stamps.clear(); TALLY.at = null; END.on = false; END.paper = false; desk.classList.remove("cafe-ending"); ui.querySelector(".cafe-top").classList.remove("gone"); ticket(); }

  /* the canvas follows the desk */
  let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(() => { labels(); if (ST.on) { size(); loop(); } }, 160); }).observe(desk);

  /* other languages come in their own small file */
  if ((LANG === "zh" && !window.CAFE_ZH) || (LANG === "ja" && !window.CAFE_JA)) { const s = document.createElement("script"); s.src = `cafe-${LANG}.js?v=11`; s.onload = labels; document.head.appendChild(s); }
  labels();
  /* ?walk (the shared link) opens the café straight away */
  if (/[?&]walk\b/.test(location.search)) setTimeout(() => enter(), 600);
  /* ?cafe=<room> opens the café there (and ?cafe-talk=<who>&cafe-line=<n> for pictures) */
  { const m = /[?&]cafe=(\w+)/.exec(location.search); if (m) window.CAFE_CAT = () => CAT.seen; if (m) setTimeout(() => { enter(); if (AREAS[m[1]] && m[1] !== "window") { ST.area = m[1]; catPut(m[1], "wait"); desk.classList.add("cafe-away"); place(); mix(); }
    const lk = /[?&]cafe-look=(\w+)/.exec(location.search); if (lk) setTimeout(() => { const b = (ST.boxes.props || []).find(q => q.id === lk[1]); lookAt(lk[1], b); }, 1200);
    const tk = /[?&]cafe-talk=(\w+)/.exec(location.search); if (tk) setTimeout(() => { if (tk[1] === "end") { ["mae", "elias", "prof", "sully"].forEach(k => ST.stamps.add(k)); ticket(); outside(); } else talk(tk[1]); }, 400); }, 300); }
})();
