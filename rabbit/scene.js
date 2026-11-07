/* The island: a small tropical island drawn in the visitor's browser. When the server has painted pictures of the
   island and its rooms (infra/rabbit-art, listed in node.tauhud.com/rico/art/index.json), they take the place of the
   drawn ones; the sea, smoke, fire, light, people and the hour still come from here, on top of them.
   The world is 1600 × 900 units, always shown whole: the sea and the sky run on to the edges of any screen,
   the island and every place on it stay inside the visible frame. The sun moves with the game's hour,
   the sea moves, palms sway, flags fly, people walk, and the lighthouse that keeps the Book sweeps
   a green beam at night. window.COVE_SCENE = { mount, setHour, focus, places, hit, people } */
(() => {
  const WW = 1600, WH = 900, HZ = 250;   // world size and the horizon line
  const rnd = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const lerp = (a, b, t) => a + (b - a) * t;
  const mix = (a, b, t) => a.map((v, i) => Math.round(lerp(v, b[i], t)));
  const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  /* the island's outline: an ellipse with a seeded, gentle coast; a point on the left for the lighthouse */
  const R0 = rnd(5150), COAST = [];
  for (let i = 0; i < 96; i++) {
    const a = i / 96 * Math.PI * 2;
    let r = 1 + 0.05 * Math.sin(a * 3 + 1) + 0.035 * Math.sin(a * 7 + 2) + 0.022 * Math.sin(a * 11 + 0.5) + 0.012 * Math.sin(a * 19) + (R0() - 0.5) * 0.025;
    const left = Math.max(0, -Math.cos(a)) ** 6 * Math.max(0, Math.sin(a) + 0.4) * 0.16;   // the lighthouse point
    r += left;
    COAST.push([800 + Math.cos(a) * 560 * r, 548 + Math.sin(a) * 215 * r]);
  }
  const shape = (g, k = 1, dy = 0) => {
    g.beginPath();
    COAST.forEach(([x, y], i) => { const X = 800 + (x - 800) * k, Y = 548 + (y - 548) * k + dy; i ? g.lineTo(X, Y) : g.moveTo(X, Y); });
    g.closePath();
  };

  /* the places: where they stand (ground point) and the box a click or a tap finds them in */
  const PLACES = {
    hall:   { x: 800, y: 500, box: [720, 395, 160, 125], name: "Council Hall" },
    market: { x: 790, y: 640, box: [690, 585, 200, 85], name: "Market square" },
    radio:  { x: 1080, y: 455, box: [1025, 300, 120, 170], name: "Radio Coco" },
    north:  { x: 520, y: 470, box: [460, 400, 120, 90], name: "North Wind Embassy" },
    south:  { x: 650, y: 425, box: [600, 360, 110, 85], name: "South Current Wellness Resort" },
    bar:    { x: 1215, y: 640, box: [1140, 575, 160, 95], name: "Bar La Ola" },
    book:   { x: 300, y: 600, box: [255, 395, 95, 225], name: "The Lighthouse" },
    pier:   { x: 1010, y: 735, box: [950, 690, 170, 80], name: "The pier" },
  };

  /* times of day: 0 morning, 1 noon, 2 evening, 3 night, and round again (3.5 is first light).
     mul is the light a painted picture is multiplied with: white at noon, warm at the ends of the day, deep blue at night */
  const SKY = [
    { top: [92, 160, 220], bot: [255, 214, 170], sea: [38, 140, 170], seaB: [20, 92, 130], sun: [255, 236, 190], tint: [255, 214, 170, 0.06], light: 0, mul: [255, 232, 206] },
    { top: [40, 130, 220], bot: [160, 214, 245], sea: [24, 150, 190], seaB: [10, 90, 140], sun: [255, 250, 230], tint: [255, 255, 255, 0], light: 0, mul: [255, 255, 255] },
    { top: [70, 60, 140], bot: [255, 140, 90], sea: [60, 80, 130], seaB: [28, 40, 80], sun: [255, 170, 90], tint: [255, 110, 60, 0.2], light: 0.6, mul: [246, 160, 128] },
    { top: [6, 10, 32], bot: [26, 40, 84], sea: [10, 24, 50], seaB: [4, 10, 26], sun: [220, 230, 255], tint: [16, 26, 70, 0.55], light: 1, mul: [58, 76, 140] },
  ];
  const skyAt = h => {
    h = ((h % 4) + 4) % 4;
    const i = Math.floor(h) % 4, j = (i + 1) % 4, f = h - Math.floor(h), a = SKY[i], b = SKY[j];
    return { top: mix(a.top, b.top, f), bot: mix(a.bot, b.bot, f), sea: mix(a.sea, b.sea, f), seaB: mix(a.seaB, b.seaB, f), sun: mix(a.sun, b.sun, f),
      tint: [...mix(a.tint.slice(0, 3), b.tint.slice(0, 3), f), lerp(a.tint[3], b.tint[3], f)], light: lerp(a.light, b.light, f), mul: mix(a.mul, b.mul, f) };
  };
  /* the island keeps the clock of Germany (Europe/Berlin), with the sun of a tropical island: first light about six,
     morning sun at seven, noon, a long golden afternoon, a short red dusk after six and night from about half past eight.
     The light changes all the time, a little every minute. ?hour=21:30 holds a time, ?light=fast runs a day in two minutes,
     ?light=game lets the game's own hour (moves of the day) set the light as before. */
  const CLOCK = [[0, 3], [5 * 60 + 15, 3], [6 * 60 + 15, 3.55], [7 * 60 + 15, 4], [9 * 60 + 30, 4.55], [12 * 60, 5], [15 * 60 + 30, 5.3],
    [17 * 60 + 45, 6], [19 * 60, 6.55], [20 * 60 + 15, 7], [24 * 60, 7]];
  const LIGHT = (() => {
    const q = location.search, m = q.match(/[?&]hour=(\d{1,2})(?::(\d{2}))?/);
    return { game: /[?&]light=game/.test(q), fast: /[?&]light=fast/.test(q), fixed: m ? (+m[1] % 24) * 60 + (+(m[2] || 0)) : null, t0: Date.now() };
  })();
  let berlinFmt = null;
  function berlinMinutes() {
    if (LIGHT.fixed != null) return LIGHT.fixed;
    if (LIGHT.fast) return (((Date.now() - LIGHT.t0) / 120000) * 1440 + 6 * 60) % 1440;   // from six in the morning, round the clock
    try {
      berlinFmt = berlinFmt || new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", hourCycle: "h23", hour: "2-digit", minute: "2-digit", second: "2-digit" });
      const p = {}; berlinFmt.formatToParts(new Date()).forEach(x => { p[x.type] = +x.value; });
      return ((p.hour % 24) * 60 + p.minute + p.second / 60) % 1440;
    } catch (e) { const d = new Date(); return (d.getUTCHours() * 60 + d.getUTCMinutes() + 60) % 1440; }   // no time zones: winter time
  }
  function clockHour(min) {
    for (let i = 1; i < CLOCK.length; i++) if (min <= CLOCK[i][0]) { const [m0, h0] = CLOCK[i - 1], [m1, h1] = CLOCK[i]; return lerp(h0, h1, (min - m0) / (m1 - m0)) % 4; }
    return 3;
  }

  /* ---------- the island, painted once per size, like a screen-printed travel poster:
     a few flat inks on warm paper, dark ink lines drawn by hand, dots and hatching for shade ---------- */
  const INK = "#22303a";
  const P = { paper: "#f3e7c9", sand: "#efd49c", sandD: "#d9b57a", leaf: "#5c9a4c", leafL: "#86b85a", leafD: "#2f6440", jungle: "#24513a", teal: "#2c8c88", lagoon: "#7fd0c2", coral: "#e2674f", mustard: "#e9b44c", navy: "#284b63", cream: "#fbf3df", rock: "#8b7a66" };
  /* a hand-drawn line: the path is walked in small steps that wander a little */
  function wobble(g, pts, closed, R, amp = 1.2) {
    g.beginPath();
    pts.forEach(([x, y], i) => { const jx = (R() - 0.5) * amp, jy = (R() - 0.5) * amp; i ? g.lineTo(x + jx, y + jy) : g.moveTo(x + jx, y + jy); });
    if (closed) g.closePath();
  }
  function ink(g, w = 2, a = 0.9) { g.strokeStyle = INK; g.globalAlpha = a; g.lineWidth = w; g.lineJoin = "round"; g.lineCap = "round"; g.stroke(); g.globalAlpha = 1; }
  /* printed dots, larger where the shade is deeper (k from 0 to 1 across the box) */
  function dots(g, x0, y0, x1, y1, step, rmax, color, dir = "x") {
    g.fillStyle = color;
    for (let y = y0; y < y1; y += step) for (let x = x0 + ((y / step) % 2 ? step / 2 : 0); x < x1; x += step) {
      const k = dir === "x" ? (x - x0) / (x1 - x0) : (y - y0) / (y1 - y0), r = rmax * Math.max(0, k);
      if (r > 0.25) { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); }
    }
  }
  function hatch(g, x0, y0, x1, y1, gap, color, w = 1) {
    g.strokeStyle = color; g.lineWidth = w; g.beginPath();
    for (let x = x0 - (y1 - y0); x < x1; x += gap) { g.moveTo(x, y1); g.lineTo(x + (y1 - y0), y0); }
    g.stroke();
  }
  const coastPts = (k = 1, dy = 0) => COAST.map(([x, y]) => [800 + (x - 800) * k, 548 + (y - 548) * k + dy]);

  function house(g, x, y, w, h, wall, roof, o = {}) {
    const d = o.d || w * 0.35, R = rnd(x * 7 + y);
    g.save();
    g.fillStyle = "rgba(34,48,58,.22)"; g.beginPath(); g.ellipse(x + w * 0.16, y + 3, w * 0.62, d * 0.42, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = wall[0]; g.fillRect(x - w / 2, y - h, w, h);
    g.save(); g.beginPath(); g.rect(x + w / 2 - w * 0.2, y - h, w * 0.2, h); g.clip(); dots(g, x + w / 2 - w * 0.2, y - h + 2, x + w / 2, y, 4, 1.5, "rgba(34,48,58,.45)"); g.restore();
    wobble(g, [[x - w / 2, y], [x - w / 2, y - h], [x + w / 2, y - h], [x + w / 2, y]], true, R); ink(g, 1.8);
    g.fillStyle = roof[0]; wobble(g, [[x - w / 2 - 6, y - h], [x - w / 2 + w * 0.18, y - h - d], [x + w / 2 - w * 0.18, y - h - d], [x + w / 2 + 6, y - h]], true, R, 0.6); g.fill(); ink(g, 1.8);
    g.save(); g.clip(); hatch(g, x, y - h - d, x + w / 2 + 6, y - h, 4, "rgba(34,48,58,.28)"); g.restore();
    const win = [], n = o.win ?? Math.max(2, Math.round(w / 26));
    for (let i = 0; i < n; i++) {
      const wx = x - w / 2 + (i + 0.5) * w / n - 5, wy = y - h * 0.72;
      g.fillStyle = INK; g.fillRect(wx, wy, 10, h * 0.3); win.push([wx, wy, 10, h * 0.3]);
      g.fillStyle = wall[1]; g.fillRect(wx - 1.5, wy + h * 0.3, 13, 2.5);
    }
    if (o.door !== false) { g.fillStyle = o.doorC || P.coral; g.fillRect(x - 7, y - h * 0.42, 14, h * 0.42); g.beginPath(); g.rect(x - 7, y - h * 0.42, 14, h * 0.42); ink(g, 1.2); }
    g.restore();
    return win;
  }
  function palmBase(g, x, y) { g.fillStyle = "rgba(34,48,58,.22)"; g.beginPath(); g.ellipse(x + 12, y + 2, 22, 5, 0, 0, Math.PI * 2); g.fill(); }

  const WINDOWS = [];
  /* things on the island that move or glow: smoke, fires, torches, the waterfall (drawn each frame by islandFx) */
  const FX = [];
  /* the places the jungle keeps clear of: the clickable places and the camp, the factory and the falls */
  const CLEAR = [[390, 405, 78, 48], [1282, 468, 78, 56], [975, 438, 34, 26], [455, 545, 70, 34]];
  function bush(g, x, y, r, c0, c1) {
    g.fillStyle = INK; g.beginPath(); g.arc(x, y, r + 1.4, 0, Math.PI * 2); g.fill();
    g.fillStyle = c0; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    g.fillStyle = c1; g.beginPath(); g.arc(x - r * 0.25, y - r * 0.3, r * 0.55, 0, Math.PI * 2); g.fill();
  }
  function crate(g, x, y, s = 1, c = "#b98a52") {
    g.fillStyle = c; g.fillRect(x - 6 * s, y - 10 * s, 12 * s, 10 * s); g.beginPath(); g.rect(x - 6 * s, y - 10 * s, 12 * s, 10 * s); ink(g, 1);
    g.beginPath(); g.moveTo(x - 6 * s, y - 10 * s); g.lineTo(x + 6 * s, y); g.moveTo(x + 6 * s, y - 10 * s); g.lineTo(x - 6 * s, y); ink(g, 0.7, 0.6);
  }
  function barrel(g, x, y, c = "#8a5a32") {
    g.fillStyle = c; g.beginPath(); g.ellipse(x, y - 6, 5, 7, 0, 0, Math.PI * 2); g.fill(); ink(g, 1);
    g.strokeStyle = "rgba(34,48,58,.7)"; g.lineWidth = 1; g.beginPath(); g.moveTo(x - 5, y - 9); g.lineTo(x + 5, y - 9); g.moveTo(x - 5, y - 3); g.lineTo(x + 5, y - 3); g.stroke();
  }
  /* a thatched roof: straw strokes over a flat golden shape */
  function thatch(g, pts, R, c = "#d8b25a") {
    g.fillStyle = c; wobble(g, pts, true, R, 0.8); g.fill();
    g.save(); g.clip(); g.strokeStyle = "rgba(110,70,20,.55)"; g.lineWidth = 1;
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    for (let x = x0; x < x1; x += 3) { g.beginPath(); g.moveTo(x + (R() - 0.5) * 2, y0); g.lineTo(x + (x - (x0 + x1) / 2) * 0.12, y1); g.stroke(); }
    for (let y = y0 + 6; y < y1; y += 6) { g.strokeStyle = "rgba(110,70,20,.35)"; g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y + 1); g.stroke(); }
    g.restore(); wobble(g, pts, true, R, 0.8); ink(g, 1.6);
  }
  function banana(g, x, y, R) {
    g.strokeStyle = "#6b7a3a"; g.lineWidth = 2.4; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 1, y - 16); g.stroke();
    for (let k = 0; k < 5; k++) {
      const a = -Math.PI / 2 + (k - 2) * 0.7 + (R() - 0.5) * 0.2, L = 12 + R() * 5, ex = x + Math.cos(a) * L, ey = y - 16 + Math.sin(a) * L * 0.8 + 4;
      g.fillStyle = k % 2 ? "#8fc04e" : "#6ea43e"; g.beginPath(); g.moveTo(x + 1, y - 16);
      g.quadraticCurveTo((x + ex) / 2 - Math.sin(a) * 5, (y - 16 + ey) / 2 - 4, ex, ey); g.quadraticCurveTo((x + ex) / 2 + Math.sin(a) * 4, (y - 16 + ey) / 2 + 2, x + 1, y - 16); g.fill(); ink(g, 0.9, 0.8);
    }
    if (R() < 0.55) { g.fillStyle = "#e8c43a"; g.beginPath(); g.ellipse(x + 3, y - 11, 2.4, 3.6, 0.3, 0, Math.PI * 2); g.fill(); ink(g, 0.8, 0.8); }
  }
  function paintIsland(g) {
    WINDOWS.length = 0; FX.length = 0;
    const R = rnd(77);
    /* the lagoon: two flat rings of shallow water, coral heads under the surface, the reef drawn as broken ink dashes */
    g.fillStyle = "rgba(127,208,194,.55)"; wobble(g, coastPts(1.12, 8), true, R, 3); g.fill();
    g.fillStyle = P.lagoon; wobble(g, coastPts(1.05, 4), true, R, 2); g.fill();
    for (let i = 0; i < 60; i++) {
      const [cx, cy] = COAST[Math.floor(R() * COAST.length)], k = 1.03 + R() * 0.07, x = 800 + (cx - 800) * k, y = 548 + (cy - 548) * k + 5;
      g.fillStyle = R() < 0.5 ? "rgba(226,103,79,.32)" : "rgba(44,140,136,.35)"; g.beginPath(); g.ellipse(x, y, 3 + R() * 6, 1.5 + R() * 2.5, R() * 3, 0, Math.PI * 2); g.fill();
    }
    g.setLineDash([7, 9]); wobble(g, coastPts(1.1, 7), true, R, 2); ink(g, 1.3, 0.35); g.setLineDash([]);
    /* sand: dry and pale inland, darker where the waves wet it, dots for shade on the sea side */
    g.fillStyle = P.sand; wobble(g, coastPts(), true, R); g.fill();
    g.save(); wobble(g, coastPts(), true, R, 0); g.clip();
    g.strokeStyle = "rgba(190,150,90,.55)"; g.lineWidth = 7; wobble(g, coastPts(0.995, 1), true, R, 1); g.stroke();
    dots(g, 200, 560, 1420, 790, 6, 1.6, "rgba(160,110,50,.35)", "y");
    for (let i = 0; i < 40; i++) { const [cx, cy] = COAST[Math.floor(R() * COAST.length)], x = 800 + (cx - 800) * 0.96, y = 548 + (cy - 548) * 0.96; g.fillStyle = R() < 0.5 ? "#fbf3df" : "#e9a58a"; g.beginPath(); g.arc(x, y, 1.2 + R(), 0, Math.PI * 2); g.fill(); }
    g.restore();
    wobble(g, coastPts(), true, R, 1.6); ink(g, 2.2);
    /* grass: a patchwork of greens, fields and meadows, flowers dotted in, tufts drawn stroke by stroke */
    g.save(); wobble(g, coastPts(0.88, -10), true, R, 0); g.clip();
    g.fillStyle = P.leaf; g.fillRect(0, 0, WW, WH);
    [[760, 600, 420, 90, P.leafL], [430, 560, 120, 40, "#73a84f"], [1150, 560, 150, 45, "#6aa14b"], [620, 690, 120, 30, "#7fb455"], [980, 690, 110, 28, "#8cbc5c"], [1290, 600, 80, 40, "#79ad52"]].forEach(([x, y, rx, ry, c], i) => {
      g.fillStyle = c; g.beginPath(); g.ellipse(x, y, rx, ry, (i - 2) * 0.05, 0, Math.PI * 2); g.fill();
    });
    /* the ploughed field by the factory and the garden plots behind the embassies: furrows in two browns */
    [[1180, 545, 70, 18, 0.12], [585, 520, 40, 12, -0.1]].forEach(([x, y, rx, ry, a]) => {
      g.save(); g.translate(x, y); g.rotate(a); g.fillStyle = "#b98a52"; g.beginPath(); g.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2); g.fill(); g.clip();
      g.strokeStyle = "rgba(90,60,30,.55)"; g.lineWidth = 1.4; for (let k = -rx; k < rx; k += 6) { g.beginPath(); g.moveTo(k, -ry); g.lineTo(k + 8, ry); g.stroke(); }
      g.fillStyle = "#5c9a4c"; for (let k = -rx + 4; k < rx; k += 12) for (let j = -ry + 4; j < ry; j += 8) { g.beginPath(); g.arc(k + j * 0.4, j, 1.6, 0, Math.PI * 2); g.fill(); }
      g.restore(); g.beginPath(); g.ellipse(x, y, rx, ry, a, 0, Math.PI * 2); ink(g, 1.2, 0.7);
    });
    dots(g, 220, 330, 1380, 520, 7, 1.7, "rgba(36,81,58,.55)", "y");
    g.strokeStyle = "rgba(36,81,58,.5)"; g.lineWidth = 1.1; g.beginPath();
    for (let i = 0; i < 520; i++) { const x = 240 + R() * 1120, y = 500 + R() * 230; g.moveTo(x, y); g.lineTo(x + 1.5, y - 4); g.moveTo(x + 3, y); g.lineTo(x + 3.5, y - 3); g.moveTo(x - 2, y); g.lineTo(x - 3, y - 3); }
    g.stroke();
    for (let i = 0; i < 160; i++) { const x = 260 + R() * 1080, y = 520 + R() * 200; if (Math.abs(x - 790) < 130 && Math.abs(y - 628) < 45) continue; g.fillStyle = [P.coral, P.mustard, P.cream, "#e889a6", "#c9a0ff"][i % 5]; g.beginPath(); g.arc(x, y, 1.3, 0, Math.PI * 2); g.fill(); }
    g.restore();
    wobble(g, coastPts(0.88, -10), true, R, 1.4); ink(g, 1.6, 0.7);
    /* the hills and the old volcano: flat colour, rock strata, boulders, hatched on the shade side */
    const hill = (cx, top, w, c) => {
      const pts = []; for (let i = 0; i <= 24; i++) { const f = i / 24, x = cx - w + f * 2 * w, y = 470 - (470 - top) * Math.pow(Math.sin(f * Math.PI), 1.6) + (R() - 0.5) * 3; pts.push([x, y]); }
      g.fillStyle = c; wobble(g, pts, true, R, 0.8); g.fill();
      g.save(); g.clip(); hatch(g, cx + w * 0.1, top, cx + w, 470, 5, "rgba(20,40,30,.32)", 1.2);
      g.fillStyle = "rgba(251,243,223,.16)"; g.beginPath(); g.ellipse(cx - w * 0.35, top + 40, w * 0.3, 30, -0.4, 0, Math.PI * 2); g.fill(); g.restore();
      wobble(g, pts, false, R, 0.8); ink(g, 1.8);
    };
    hill(500, 330, 200, "#4a8a4a"); hill(1115, 345, 195, "#468446");
    const vol = [[560, 470], [690, 410], [790, 300], [852, 236], [868, 244], [890, 240], [911, 236], [970, 300], [1060, 410], [1180, 470]];
    g.fillStyle = "#9a8a6c"; wobble(g, vol, true, R, 0.8); g.fill();
    g.save(); g.clip();
    /* strata: thin curved bands of a darker rock, then the old lava tongue, then the green skirt */
    g.strokeStyle = "rgba(70,55,40,.4)"; g.lineWidth = 1.3;
    for (let k = 0; k < 9; k++) { const y = 270 + k * 22; g.beginPath(); for (let x = 640; x < 1120; x += 12) { const yy = y + Math.sin(x * 0.02 + k) * 4 + Math.abs(x - 880) * 0.18; x === 640 ? g.moveTo(x, yy) : g.lineTo(x, yy); } g.stroke(); }
    g.fillStyle = "#5d4a3c"; g.beginPath(); g.moveTo(866, 244); g.bezierCurveTo(860, 300, 830, 330, 812, 390); g.lineTo(836, 392); g.bezierCurveTo(850, 330, 876, 300, 880, 246); g.closePath(); g.fill();
    g.fillStyle = "#5e8a4c"; g.beginPath(); g.moveTo(560, 470); for (let i = 0; i <= 20; i++) { const x = 600 + i * 28, y = 360 + Math.sin(i * 1.3) * 14 + Math.abs(i - 10) * 6; g.lineTo(x, y); } g.lineTo(1180, 470); g.closePath(); g.fill();
    hatch(g, 880, 236, 1190, 470, 6, "rgba(40,30,20,.3)", 1.3);
    g.fillStyle = "rgba(251,243,223,.35)"; g.beginPath(); g.moveTo(858, 240); g.lineTo(760, 360); g.lineTo(790, 362); g.lineTo(868, 244); g.fill();
    for (let i = 0; i < 14; i++) { const x = 760 + R() * 240, y = 300 + R() * 60 + Math.abs(x - 880) * 0.3; g.fillStyle = "#7d6e56"; g.beginPath(); g.ellipse(x, y, 4 + R() * 5, 2.5 + R() * 2, 0, 0, Math.PI * 2); g.fill(); ink(g, 0.9, 0.7); }
    g.restore();
    wobble(g, vol, false, R, 0.8); ink(g, 2);
    g.fillStyle = "#5d5244"; g.beginPath(); g.ellipse(882, 238, 26, 6.5, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.5);
    g.fillStyle = "#c4453a"; g.beginPath(); g.ellipse(882, 237, 15, 3, 0, 0, Math.PI * 2); g.fill();
    FX.push({ k: "smoke", x: 884, y: 232, s: 2.2, c: "#cfc6b6" }, { k: "crater", x: 882, y: 237 });
    /* the falls: a ledge on the volcano's shoulder, the water down to a pool in the jungle */
    g.fillStyle = "#6f604c"; wobble(g, [[948, 336], [984, 332], [988, 342], [950, 346]], true, R, 0.6); g.fill(); ink(g, 1.4);
    g.fillStyle = "#bfe8ee"; g.beginPath(); g.moveTo(958, 342); g.lineTo(976, 340); g.lineTo(984, 432); g.lineTo(966, 434); g.closePath(); g.fill(); ink(g, 1.2, 0.8);
    FX.push({ k: "falls", x: 958, y: 342, w: 18, h: 92 });
    /* the jungle: clumps of canopy in three greens, each with a pale crescent where the light hits; some banana leaves and red blossoms */
    const crowns = [];
    for (let i = 0; i < 270; i++) {
      const x = 260 + R() * 1080, y = 360 + R() * 125 + Math.abs(x - 800) * 0.03, r = 7 + R() * 13;
      if (Object.values(PLACES).some(p => Math.abs(p.x - x) < 70 && Math.abs(p.y - y) < 60)) continue;
      if (CLEAR.some(([cx, cy, w, h]) => Math.abs(cx - x) < w && Math.abs(cy - y) < h)) continue;
      crowns.push([x, y, r, i % 4]);
    }
    crowns.sort((a, b) => a[1] - b[1]);
    crowns.forEach(([x, y, r, kind], i) => {
      g.fillStyle = INK; g.beginPath(); g.arc(x, y, r + 1.6, 0, Math.PI * 2); g.fill();
      g.fillStyle = [P.leafD, P.jungle, "#3a7442", "#2b5e3e"][kind]; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(134,184,90,.85)"; g.beginPath(); g.arc(x - r * 0.18, y - r * 0.22, r * 0.62, Math.PI * 0.95, Math.PI * 1.75); g.arc(x - r * 0.05, y - r * 0.05, r * 0.5, Math.PI * 1.75, Math.PI * 0.95, true); g.fill();
      if (kind === 2 && r > 12) { g.strokeStyle = "rgba(20,40,30,.5)"; g.lineWidth = 0.9; g.beginPath(); for (let k = 0; k < 5; k++) { const a = k * 1.25; g.moveTo(x, y); g.lineTo(x + Math.cos(a) * r * 0.8, y + Math.sin(a) * r * 0.8); } g.stroke(); }
      if (i % 9 === 0) { g.fillStyle = i % 2 ? "#e2674f" : "#f2b134"; g.beginPath(); g.arc(x + r * 0.3, y + r * 0.2, 1.8, 0, Math.PI * 2); g.arc(x - r * 0.4, y + r * 0.35, 1.5, 0, Math.PI * 2); g.fill(); }
    });
    /* the pool under the falls and the stream down to the sea, with two little bridges */
    g.fillStyle = "#7fd0c2"; g.beginPath(); g.ellipse(978, 442, 20, 7, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.4);
    FX.push({ k: "splash", x: 975, y: 438 });
    const STREAM = [[980, 446], [998, 486], [1030, 520], [1070, 548], [1102, 590], [1112, 640], [1140, 690], [1168, 740], [1182, 776]];
    g.save(); g.lineCap = "round"; g.lineJoin = "round";
    wobble(g, STREAM, false, R, 1.4); g.strokeStyle = INK; g.lineWidth = 9; g.stroke();
    wobble(g, STREAM, false, R, 1.4); g.strokeStyle = "#6fc3c6"; g.lineWidth = 6.5; g.stroke();
    wobble(g, STREAM, false, R, 3); g.strokeStyle = "rgba(251,243,223,.6)"; g.lineWidth = 1; g.setLineDash([4, 7]); g.stroke(); g.setLineDash([]);
    g.restore();
    FX.push({ k: "stream", pts: STREAM });
    /* paths: trodden earth with a darker rim, stones along the edge, the odd tuft */
    g.save(); g.lineCap = "round"; g.lineJoin = "round";
    const PATHS = [[[300, 610], [420, 620], [560, 630], [700, 628]], [[800, 515], [795, 590]], [[880, 630], [1000, 640], [1130, 640]], [[520, 480], [560, 560], [660, 610]], [[650, 432], [700, 520], [740, 590]], [[1080, 460], [1000, 560], [900, 615]], [[1000, 650], [1010, 700]], [[1130, 640], [1190, 600], [1250, 520], [1282, 500]], [[520, 480], [440, 440], [400, 420]]];
    PATHS.forEach(p => { wobble(g, p, false, R, 0.8); g.strokeStyle = "rgba(90,60,30,.6)"; g.lineWidth = 11; g.stroke(); });
    PATHS.forEach(p => { wobble(g, p, false, R, 0.8); g.strokeStyle = "#d9b67e"; g.lineWidth = 8; g.stroke(); });
    PATHS.forEach(p => { wobble(g, p, false, R, 1.5); g.strokeStyle = "rgba(251,243,223,.45)"; g.lineWidth = 2.5; g.stroke(); });
    g.restore();
    PATHS.forEach(p => { for (let k = 1; k < p.length; k++) for (let f = 0; f < 1; f += 0.18) { const x = lerp(p[k - 1][0], p[k][0], f), y = lerp(p[k - 1][1], p[k][1], f), s = R() < 0.5 ? -1 : 1; g.fillStyle = "#a89a84"; g.beginPath(); g.ellipse(x + s * 7, y + s * 2, 2, 1.3, 0, 0, Math.PI * 2); g.fill(); } });
    /* bridges where the paths cross the stream */
    [[1110, 640, 0.15], [1031, 521, -0.7]].forEach(([x, y, a]) => {
      g.save(); g.translate(x, y); g.rotate(a);
      g.fillStyle = "#a57a4c"; g.fillRect(-12, -6, 24, 12); g.beginPath(); g.rect(-12, -6, 24, 12); ink(g, 1.2);
      g.strokeStyle = "rgba(34,48,58,.6)"; g.lineWidth = 0.8; for (let k = -9; k < 12; k += 4) { g.beginPath(); g.moveTo(k, -6); g.lineTo(k, 6); g.stroke(); }
      g.strokeStyle = INK; g.lineWidth = 1.4; g.beginPath(); g.moveTo(-12, -7); g.lineTo(12, -7); g.moveTo(-12, 7); g.lineTo(12, 7); g.stroke();
      g.restore();
    });

    /* ---- the rebels' camp, up in the clearing on the west hill: tents, a fire, a lookout and their flag ---- */
    g.fillStyle = "#b6915e"; wobble(g, [[340, 420], [360, 390], [420, 378], [452, 398], [446, 432], [380, 440]], true, R, 2); g.fill(); ink(g, 1.2, 0.6);
    dots(g, 340, 380, 452, 440, 5, 1.1, "rgba(90,60,30,.35)", "y");
    [[362, 414, 26, 22, "#7a7a4a"], [398, 400, 30, 26, "#8a8452"], [434, 418, 22, 18, "#6d6c40"]].forEach(([x, y, w, h, c]) => {
      g.fillStyle = "rgba(34,48,58,.25)"; g.beginPath(); g.ellipse(x + 6, y + 2, w * 0.7, 4, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = c; g.beginPath(); g.moveTo(x - w / 2, y); g.lineTo(x, y - h); g.lineTo(x + w / 2, y); g.closePath(); g.fill();
      g.save(); g.clip(); hatch(g, x, y - h, x + w / 2, y, 3, "rgba(30,30,10,.35)"); g.restore();
      g.beginPath(); g.moveTo(x - w / 2, y); g.lineTo(x, y - h); g.lineTo(x + w / 2, y); g.closePath(); ink(g, 1.4);
      g.fillStyle = INK; g.beginPath(); g.moveTo(x - 3, y); g.lineTo(x, y - h * 0.55); g.lineTo(x + 3, y); g.closePath(); g.fill();
    });
    /* the lookout: four poles, a platform, a ladder */
    g.strokeStyle = INK; g.lineWidth = 1.8;
    g.beginPath(); g.moveTo(436, 392); g.lineTo(440, 350); g.moveTo(452, 392); g.lineTo(448, 350); g.moveTo(436, 392); g.lineTo(452, 372); g.moveTo(452, 392); g.lineTo(436, 372); g.stroke();
    g.fillStyle = "#8a5a32"; g.fillRect(434, 346, 20, 5); g.beginPath(); g.rect(434, 346, 20, 5); ink(g, 1.2);
    g.fillStyle = "#c79a62"; g.beginPath(); g.moveTo(432, 346); g.lineTo(444, 334); g.lineTo(456, 346); g.closePath(); g.fill(); ink(g, 1.2);
    FX.push({ k: "flag", x: 444, y: 334, c0: "#4c5a2e", c1: "#f2b134", h: 22 });
    /* the fire: a ring of stones and two logs; the flames and the smoke move */
    g.fillStyle = "#7d6e56"; for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2; g.beginPath(); g.ellipse(392 + Math.cos(a) * 8, 426 + Math.sin(a) * 3, 2.6, 1.8, 0, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = "#6b4422"; g.save(); g.translate(392, 425); g.rotate(0.4); g.fillRect(-7, -1.5, 14, 3); g.rotate(-0.8); g.fillRect(-7, -1.5, 14, 3); g.restore();
    FX.push({ k: "fire", x: 392, y: 424, s: 1 }, { k: "smoke", x: 392, y: 414, s: 0.7, c: "#d9d2c4" });
    crate(g, 352, 432, 0.9, "#7a6a42"); crate(g, 364, 434, 0.8, "#857348"); barrel(g, 418, 438, "#5a5a3a");
    g.strokeStyle = "rgba(34,48,58,.8)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(372, 397); g.quadraticCurveTo(384, 404, 396, 398); g.stroke();
    [[377, 401, "#e2674f"], [384, 403, "#fbf3df"], [391, 401, "#e9b44c"]].forEach(([x, y, c]) => { g.fillStyle = c; g.fillRect(x - 2, y, 4, 5); });

    /* ---- the coconut works on the east slope: brick hall with a sawtooth roof, chimney, water tower, a heap of nuts ---- */
    g.fillStyle = "rgba(34,48,58,.24)"; g.beginPath(); g.ellipse(1292, 502, 66, 10, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#c0674a"; g.fillRect(1238, 456, 96, 44);
    g.save(); g.beginPath(); g.rect(1238, 456, 96, 44); g.clip();
    g.strokeStyle = "rgba(90,30,20,.45)"; g.lineWidth = 0.8; for (let y = 460; y < 500; y += 5) { g.beginPath(); g.moveTo(1238, y); g.lineTo(1334, y); g.stroke(); for (let x = 1238 + ((y / 5) % 2) * 5; x < 1334; x += 10) { g.beginPath(); g.moveTo(x, y); g.lineTo(x, y + 5); g.stroke(); } }
    dots(g, 1310, 458, 1334, 500, 4, 1.5, "rgba(34,48,58,.45)"); g.restore();
    g.beginPath(); g.rect(1238, 456, 96, 44); ink(g, 1.8);
    for (let k = 0; k < 4; k++) { const x = 1238 + k * 24; g.fillStyle = k % 2 ? "#8a8a90" : "#a2a2a8"; g.beginPath(); g.moveTo(x, 456); g.lineTo(x + 18, 440); g.lineTo(x + 24, 456); g.closePath(); g.fill(); ink(g, 1.3); g.fillStyle = "#cfe8f0"; g.fillRect(x + 18, 442, 4, 13); }
    for (let k = 0; k < 4; k++) { g.fillStyle = INK; g.fillRect(1246 + k * 22, 468, 10, 12); WINDOWS.push([1246 + k * 22, 468, 10, 12]); }
    g.fillStyle = "#5a3a2a"; g.fillRect(1280, 484, 16, 16); g.beginPath(); g.rect(1280, 484, 16, 16); ink(g, 1.2);
    /* the sign: a painted coconut, cut open */
    g.fillStyle = P.cream; g.fillRect(1262, 446, 30, 9); g.beginPath(); g.rect(1262, 446, 30, 9); ink(g, 1);
    g.fillStyle = "#6b4422"; g.beginPath(); g.arc(1277, 450.5, 3.6, 0, Math.PI * 2); g.fill(); g.fillStyle = P.cream; g.beginPath(); g.arc(1277, 450.5, 2, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#9a5a40"; g.fillRect(1322, 392, 10, 64); g.beginPath(); g.rect(1322, 392, 10, 64); ink(g, 1.4);
    g.fillStyle = INK; g.fillRect(1320, 390, 14, 4); g.strokeStyle = P.cream; g.lineWidth = 1.4; g.beginPath(); g.moveTo(1322, 404); g.lineTo(1332, 404); g.moveTo(1322, 410); g.lineTo(1332, 410); g.stroke();
    FX.push({ k: "smoke", x: 1327, y: 388, s: 1.2, c: "#c8c2b8" });
    g.strokeStyle = INK; g.lineWidth = 1.5; g.beginPath(); g.moveTo(1346, 500); g.lineTo(1350, 470); g.moveTo(1366, 500); g.lineTo(1362, 470); g.moveTo(1346, 500); g.lineTo(1362, 480); g.stroke();
    g.fillStyle = "#4f86a8"; g.beginPath(); g.ellipse(1356, 466, 12, 4, 0, 0, Math.PI * 2); g.fill(); g.fillRect(1344, 452, 24, 14); g.beginPath(); g.ellipse(1356, 452, 12, 4, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.2);
    g.beginPath(); g.rect(1344, 452, 24, 14); ink(g, 1.2);
    g.fillStyle = "#6b4422"; for (let k = 0; k < 14; k++) { const x = 1222 + (k % 5) * 5 + (k > 9 ? 5 : 0), y = 500 - Math.floor(k / 5) * 4; g.beginPath(); g.arc(x, y, 2.6, 0, Math.PI * 2); g.fill(); g.strokeStyle = INK; g.lineWidth = 0.7; g.stroke(); }
    g.strokeStyle = INK; g.lineWidth = 1.2; g.beginPath(); g.moveTo(1232, 492); g.lineTo(1250, 478); g.stroke();
    crate(g, 1302, 512, 0.9); crate(g, 1314, 512, 0.9); crate(g, 1308, 503, 0.9);

    /* ---- the islanders' cottages: each its own colour, a garden, washing on a line, hens in the yard ---- */
    [[610, 572, "#f2b134", P.coral], [660, 560, "#7fd0c2", P.navy], [862, 578, "#e889a6", "#7c4b2a"], [912, 562, P.cream, P.teal], [1050, 606, "#c9a0ff", P.coral]].forEach(([x, y, wall, roof], i) => {
      WINDOWS.push(...house(g, x, y, 34, 20, [wall, P.cream], [roof], { d: 12, win: 1, doorC: i % 2 ? P.coral : P.navy }));
      bush(g, x + 22, y - 2, 5, "#3f7a46", "#6aa14b");
      g.fillStyle = [P.coral, P.mustard, "#e889a6"][i % 3]; g.beginPath(); g.arc(x + 20, y - 5, 1.3, 0, Math.PI * 2); g.arc(x + 24, y - 1, 1.3, 0, Math.PI * 2); g.fill();
    });
    g.strokeStyle = "rgba(34,48,58,.75)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(624, 560); g.quadraticCurveTo(636, 566, 646, 556); g.moveTo(876, 566); g.quadraticCurveTo(888, 572, 898, 560); g.stroke();
    [[628, 561, P.coral], [634, 563, P.cream], [640, 561, P.teal], [880, 567, P.mustard], [887, 569, P.cream], [893, 566, "#6fa8ff"]].forEach(([x, y, c]) => { g.fillStyle = c; g.fillRect(x - 2, y, 4, 5); g.strokeStyle = INK; g.lineWidth = 0.5; g.strokeRect(x - 2, y, 4, 5); });
    [[640, 582], [646, 585], [930, 584], [1068, 618], [1074, 620]].forEach(([x, y], i) => { g.fillStyle = i % 2 ? "#fbf3df" : "#c98c55"; g.beginPath(); g.ellipse(x, y, 2.6, 1.8, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = "#c4453a"; g.fillRect(x + 1.5, y - 2.5, 1.2, 1.2); });
    /* a well on the green between the cottages */
    g.fillStyle = "#9e8e78"; g.beginPath(); g.ellipse(700, 594, 7, 3, 0, 0, Math.PI * 2); g.fill(); ink(g, 1); g.fillRect(693, 586, 14, 8); g.beginPath(); g.rect(693, 586, 14, 8); ink(g, 1);
    g.strokeStyle = INK; g.lineWidth = 1.2; g.beginPath(); g.moveTo(694, 586); g.lineTo(694, 574); g.moveTo(706, 586); g.lineTo(706, 574); g.stroke(); g.fillStyle = "#7c4b2a"; g.beginPath(); g.moveTo(690, 575); g.lineTo(700, 568); g.lineTo(710, 575); g.closePath(); g.fill(); ink(g, 1);
    /* ---- the banana grove below the west hill, in rows ---- */
    for (let r = 0; r < 3; r++) for (let k = 0; k < 6; k++) banana(g, 400 + k * 21 + r * 7, 535 + r * 14, R);

    /* the market square: paving rings, four striped stalls, crates and baskets of fruit */
    g.fillStyle = "#e9d3a4"; g.beginPath(); g.ellipse(790, 628, 110, 34, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.8);
    g.save(); g.beginPath(); g.ellipse(790, 628, 110, 34, 0, 0, Math.PI * 2); g.clip(); g.strokeStyle = "rgba(34,48,58,.2)"; g.lineWidth = 0.8;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 14) { g.beginPath(); g.moveTo(790, 628); g.lineTo(790 + Math.cos(a) * 120, 628 + Math.sin(a) * 40); g.stroke(); } g.restore();
    g.strokeStyle = "rgba(34,48,58,.3)"; g.lineWidth = 1; for (let i = 1; i < 4; i++) { g.beginPath(); g.ellipse(790, 628, 110 * i / 4, 34 * i / 4, 0, 0, Math.PI * 2); g.stroke(); }
    g.fillStyle = "#bfe8ee"; g.beginPath(); g.ellipse(790, 628, 13, 5, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.3); g.fillStyle = P.cream; g.fillRect(788, 616, 4, 10); g.beginPath(); g.rect(788, 616, 4, 10); ink(g, 0.9);
    FX.push({ k: "fountain", x: 790, y: 615 });
    [[P.coral, 712], [P.mustard, 750], [P.teal, 830], ["#e889a6", 868]].forEach(([c, x], i) => {
      const y = 622 + (i % 2) * 18;
      g.fillStyle = "rgba(34,48,58,.25)"; g.fillRect(x - 15, y, 30, 4);
      g.fillStyle = INK; g.fillRect(x - 13, y - 18, 2, 18); g.fillRect(x + 11, y - 18, 2, 18);
      g.fillStyle = "#c79a62"; g.fillRect(x - 14, y - 8, 28, 8); g.beginPath(); g.rect(x - 14, y - 8, 28, 8); ink(g, 1.2);
      for (let k = 0; k < 4; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.moveTo(x - 17 + k * 8.5, y - 18); g.lineTo(x - 17 + (k + 1) * 8.5, y - 18); g.lineTo(x - 15 + (k + 1) * 7.5, y - 26); g.lineTo(x - 15 + k * 7.5, y - 26); g.fill(); }
      g.beginPath(); g.moveTo(x - 17, y - 18); g.lineTo(x + 17, y - 18); g.lineTo(x + 15, y - 26); g.lineTo(x - 15, y - 26); g.closePath(); ink(g, 1.2);
      for (let k = 0; k < 5; k++) { g.fillStyle = [P.mustard, P.coral, P.leafL, P.cream, "#c4453a"][(k + i) % 5]; g.beginPath(); g.arc(x - 10 + k * 5, y - 9, 2.4, 0, Math.PI * 2); g.fill(); }
    });
    [[690, 640], [892, 646], [742, 652]].forEach(([x, y], i) => { crate(g, x, y, 0.8); g.fillStyle = [P.coral, P.mustard, P.leafL][i]; for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(x - 3 + k * 3, y - 9, 2, 0, Math.PI * 2); g.fill(); } });
    [[856, 654], [712, 606]].forEach(([x, y]) => { g.fillStyle = "#c79a62"; g.beginPath(); g.ellipse(x, y, 6, 3.5, 0, 0, Math.PI); g.fill(); ink(g, 1); g.fillStyle = "#e8c43a"; g.beginPath(); g.ellipse(x, y - 1, 5, 2, 0, 0, Math.PI * 2); g.fill(); });

    /* ---- the council hall: on a plinth with steps, white columns under a teal dome, a potted palm each side ---- */
    g.fillStyle = "#e6d8b8"; g.fillRect(722, 500, 156, 8); g.beginPath(); g.rect(722, 500, 156, 8); ink(g, 1.3);
    [[0, 762, 76], [1, 756, 88], [2, 750, 100]].forEach(([k, x, w]) => { g.fillStyle = k % 2 ? "#efe3c6" : "#f7eedb"; g.fillRect(x, 508 + k * 4, w, 4); g.beginPath(); g.rect(x, 508 + k * 4, w, 4); ink(g, 0.9, 0.7); });
    WINDOWS.push(...house(g, 800, 500, 140, 58, [P.cream, "#e6d8b8"], [P.teal], { d: 26, win: 0, doorC: P.coral }));
    for (let i = 0; i < 6; i++) { g.fillStyle = "#fffaf0"; g.fillRect(738 + i * 24, 452, 6, 46); g.beginPath(); g.rect(738 + i * 24, 452, 6, 46); ink(g, 1); g.fillStyle = "rgba(34,48,58,.18)"; g.fillRect(742 + i * 24, 452, 2, 46); }
    g.fillStyle = P.teal; g.beginPath(); g.ellipse(800, 432, 38, 34, 0, Math.PI, 0); g.closePath(); g.fill();
    g.save(); g.clip(); hatch(g, 800, 396, 840, 432, 4, "rgba(20,40,40,.35)"); g.strokeStyle = "rgba(251,243,223,.45)"; g.lineWidth = 1; for (let k = -2; k <= 2; k++) { g.beginPath(); g.ellipse(800, 432, Math.abs(k) * 9 + 0.5, 34, 0, Math.PI, 0); g.stroke(); } g.restore();
    g.beginPath(); g.ellipse(800, 432, 38, 34, 0, Math.PI, 0); ink(g, 1.8);
    g.fillStyle = "#e8dfc8"; g.fillRect(762, 430, 76, 6); g.beginPath(); g.rect(762, 430, 76, 6); ink(g, 1.2);
    g.fillStyle = P.mustard; g.fillRect(799, 388, 2, 12); g.beginPath(); g.arc(800, 386, 3, 0, Math.PI * 2); g.fill();
    FX.push({ k: "flag", x: 800, y: 384, c0: "#2c8c88", c1: "#fbf3df", h: 20 });
    [[728, 512], [872, 512]].forEach(([x, y]) => { g.fillStyle = "#c0674a"; g.beginPath(); g.moveTo(x - 6, y - 8); g.lineTo(x + 6, y - 8); g.lineTo(x + 4, y); g.lineTo(x - 4, y); g.closePath(); g.fill(); ink(g, 1); for (let k = 0; k < 5; k++) { const a = -Math.PI / 2 + (k - 2) * 0.55; g.strokeStyle = P.leafD; g.lineWidth = 2.2; g.beginPath(); g.moveTo(x, y - 8); g.quadraticCurveTo(x + Math.cos(a) * 6, y - 18, x + Math.cos(a) * 11, y - 12 + Math.abs(k - 2) * 2); g.stroke(); } });
    WINDOWS.push([762, 466, 8, 22], [830, 466, 8, 22]);

    /* ---- the North Wind embassy: a white colonial house with a veranda, a wind vane, a hedge and a picket fence ---- */
    WINDOWS.push(...house(g, 520, 470, 92, 46, ["#cfe1ec", P.cream], [P.navy], { d: 22, doorC: P.navy }));
    g.fillStyle = P.cream; g.fillRect(470, 452, 100, 4); g.beginPath(); g.rect(470, 452, 100, 4); ink(g, 1);
    for (let i = 0; i < 6; i++) { g.fillStyle = "#fffaf0"; g.fillRect(472 + i * 19, 456, 3, 14); g.beginPath(); g.rect(472 + i * 19, 456, 3, 14); ink(g, 0.8); }
    g.strokeStyle = INK; g.lineWidth = 1.2; g.beginPath(); g.moveTo(540, 426); g.lineTo(540, 410); g.moveTo(532, 412); g.lineTo(548, 412); g.stroke();
    g.fillStyle = P.mustard; g.beginPath(); g.moveTo(548, 412); g.lineTo(542, 408); g.lineTo(542, 416); g.closePath(); g.fill();
    g.strokeStyle = P.cream; g.lineWidth = 1.6; g.beginPath(); for (let x = 462; x <= 580; x += 6) { g.moveTo(x, 486); g.lineTo(x, 478); } g.moveTo(460, 482); g.lineTo(582, 482); g.stroke();
    g.strokeStyle = "rgba(34,48,58,.5)"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(460, 486.5); g.lineTo(582, 486.5); g.stroke();
    [[458, 476, 7], [586, 476, 7]].forEach(([x, y, r]) => bush(g, x, y, r, "#3f7a46", "#6aa14b"));
    g.fillStyle = "#e889a6"; [[466, 474], [474, 473], [568, 474], [576, 473]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 1.8, 0, Math.PI * 2); g.fill(); });

    /* ---- the South Current embassy: terracotta and arches, a walled courtyard with a gate and a fountain ---- */
    WINDOWS.push(...house(g, 650, 425, 82, 42, ["#f6dcc0", P.cream], [P.coral], { d: 20, win: 0, doorC: P.teal }));
    for (let i = 0; i < 3; i++) { const x = 622 + i * 28; g.fillStyle = INK; g.beginPath(); g.moveTo(x - 6, 412); g.lineTo(x - 6, 400); g.arc(x, 400, 6, Math.PI, 0); g.lineTo(x + 6, 412); g.closePath(); g.fill(); if (i !== 1) WINDOWS.push([x - 5, 398, 10, 13]); }
    g.save(); g.beginPath(); g.moveTo(603, 383); g.lineTo(615, 363); g.lineTo(685, 363); g.lineTo(697, 383); g.closePath(); g.clip(); g.strokeStyle = "rgba(120,40,30,.55)"; g.lineWidth = 1; for (let y = 366; y < 384; y += 4) { g.beginPath(); for (let x = 600; x < 700; x += 6) g.arc(x + 3, y, 3, 0, Math.PI); g.stroke(); } g.restore();
    g.fillStyle = "#f0cfa8"; g.fillRect(598, 432, 104, 8); g.beginPath(); g.rect(598, 432, 104, 8); ink(g, 1.1);
    g.fillStyle = "#c0674a"; g.fillRect(598, 430, 104, 3);
    g.fillStyle = INK; g.fillRect(644, 432, 12, 8);
    g.fillStyle = "#bfe8ee"; g.beginPath(); g.ellipse(616, 424, 7, 2.5, 0, 0, Math.PI * 2); g.fill(); ink(g, 0.9);
    g.strokeStyle = "#8fd8e8"; g.lineWidth = 1; g.beginPath(); g.moveTo(616, 423); g.quadraticCurveTo(613, 415, 610, 421); g.moveTo(616, 423); g.quadraticCurveTo(619, 415, 622, 421); g.stroke();
    bush(g, 690, 428, 6, "#3f7a46", "#6aa14b");

    /* ---- Radio Coco: a painted wooden shack, a tall mast with guy wires, loudspeakers on a pole, a record on the roof ---- */
    WINDOWS.push(...house(g, 1080, 455, 74, 38, [P.mustard, P.cream], ["#7c4b2a"], { d: 18, win: 2, doorC: P.coral }));
    g.save(); g.beginPath(); g.rect(1043, 417, 74, 38); g.clip(); g.strokeStyle = "rgba(120,70,20,.35)"; g.lineWidth = 0.8; for (let x = 1045; x < 1117; x += 5) { g.beginPath(); g.moveTo(x, 417); g.lineTo(x, 455); g.stroke(); } g.restore();
    g.fillStyle = INK; g.beginPath(); g.arc(1058, 400, 10, 0, Math.PI * 2); g.fill(); g.fillStyle = "#e2674f"; g.beginPath(); g.arc(1058, 400, 3.6, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "rgba(251,243,223,.35)"; g.lineWidth = 0.7; for (let r = 5; r < 10; r += 1.6) { g.beginPath(); g.arc(1058, 400, r, -0.8, 0.6); g.stroke(); }
    g.strokeStyle = INK; g.lineWidth = 2;
    g.beginPath(); g.moveTo(1100, 418); g.lineTo(1112, 300); g.lineTo(1124, 418); g.stroke();
    for (let i = 0; i < 8; i++) { const y = 418 - i * 14.7, k = i / 8; g.beginPath(); g.moveTo(1100 + 12 * k, y); g.lineTo(1124 - 12 * k, y - 14.7); g.stroke(); }
    g.strokeStyle = "rgba(34,48,58,.55)"; g.lineWidth = 0.7; g.beginPath(); g.moveTo(1112, 304); g.lineTo(1064, 430); g.moveTo(1112, 304); g.lineTo(1150, 440); g.moveTo(1112, 330); g.quadraticCurveTo(1090, 380, 1086, 418); g.stroke();
    g.strokeStyle = INK; g.lineWidth = 1.6; g.beginPath(); g.moveTo(1036, 462); g.lineTo(1036, 420); g.stroke();
    [[1036, 422, -1], [1036, 432, 1]].forEach(([x, y, d]) => { g.fillStyle = "#a2a2a8"; g.beginPath(); g.moveTo(x, y - 2); g.lineTo(x + d * 10, y - 6); g.lineTo(x + d * 10, y + 6); g.lineTo(x, y + 2); g.closePath(); g.fill(); ink(g, 1); });
    crate(g, 1124, 462, 0.8, "#c98c55"); crate(g, 1132, 462, 0.8, "#b07a48");

    /* ---- Bar La Ola: a thatched beach bar on stilts, a deck, tiki torches, a string of lights, surfboards ---- */
    g.fillStyle = "#8a5a32"; g.fillRect(1152, 640, 116, 6); g.beginPath(); g.rect(1152, 640, 116, 6); ink(g, 1.2);
    g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); for (let x = 1158; x <= 1262; x += 26) { g.moveTo(x, 646); g.lineTo(x, 656); } g.stroke();
    WINDOWS.push(...house(g, 1210, 640, 96, 34, ["#c98c55", P.cream], ["#d9bf6a"], { d: 22, win: 3, doorC: P.teal }));
    thatch(g, [[1154, 608], [1176, 582], [1244, 582], [1268, 608], [1260, 612], [1160, 612]], R);
    g.fillStyle = P.cream; g.font = "800 11px Sora, sans-serif"; g.textAlign = "center"; g.fillText("LA OLA", 1210, 625);
    g.strokeStyle = "rgba(34,48,58,.8)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(1156, 612); g.quadraticCurveTo(1182, 622, 1210, 613); g.quadraticCurveTo(1238, 622, 1266, 612); g.stroke();
    for (let k = 0; k < 9; k++) { const f = k / 8, x = 1156 + f * 110, y = 612 + Math.sin(f * Math.PI * 2) ** 2 * 8; g.fillStyle = [P.coral, P.mustard, P.teal][k % 3]; g.beginPath(); g.arc(x, y + 1, 1.8, 0, Math.PI * 2); g.fill(); FX.push({ k: "bulb", x, y: y + 1, c: k % 3 }); }
    [[1140, 650], [1282, 650]].forEach(([x, y]) => { g.strokeStyle = "#6b4422"; g.lineWidth = 2; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 24); g.stroke(); g.fillStyle = "#3a2a1a"; g.fillRect(x - 2.5, y - 28, 5, 5); FX.push({ k: "torch", x, y: y - 29 }); });
    [[1290, 640, P.teal], [1298, 642, P.coral]].forEach(([x, y, c]) => { g.save(); g.translate(x, y); g.rotate(0.18); g.fillStyle = c; g.beginPath(); g.ellipse(0, -12, 3.5, 13, 0, 0, Math.PI * 2); g.fill(); ink(g, 1); g.fillStyle = P.cream; g.fillRect(-0.5, -24, 1, 24); g.restore(); });
    [[1300, 690, P.coral], [1334, 676, P.teal], [1150, 690, P.mustard]].forEach(([x, y, c]) => {
      g.fillStyle = "rgba(34,48,58,.22)"; g.beginPath(); g.ellipse(x + 6, y + 2, 20, 5, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = INK; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 26); g.stroke();
      for (let k = 0; k < 6; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.moveTo(x, y - 34); g.lineTo(x - 22 + k * 7.3, y - 24); g.lineTo(x - 22 + (k + 1) * 7.3, y - 24); g.fill(); }
      g.beginPath(); g.moveTo(x, y - 34); g.lineTo(x - 22, y - 24); g.lineTo(x + 22, y - 24); g.closePath(); ink(g, 1.2);
    });
    [[1316, 694], [1172, 700]].forEach(([x, y]) => { g.fillStyle = P.cream; g.save(); g.translate(x, y); g.rotate(-0.1); g.fillRect(-11, -3, 22, 5); g.beginPath(); g.rect(-11, -3, 22, 5); ink(g, 0.9); g.fillStyle = P.coral; g.fillRect(-11, -1.5, 22, 1.5); g.restore(); });

    /* ---- the pier: planks and posts, bollards with rope, barrels and crates, a lantern at the end, a little fishing boat tied up ---- */
    g.fillStyle = "#a57a4c"; wobble(g, [[990, 690], [1030, 690], [1060, 790], [1010, 790]], true, R, 0.6); g.fill(); ink(g, 1.6);
    g.strokeStyle = "rgba(34,48,58,.55)"; g.lineWidth = 1; for (let i = 0; i < 16; i++) { const t = i / 16, y = 690 + t * 100; g.beginPath(); g.moveTo(990 + 20 * t, y); g.lineTo(1030 + 30 * t, y); g.stroke(); }
    g.fillStyle = "#6b4422"; [[1004, 720], [1046, 720], [1010, 760], [1056, 760], [1014, 792], [1062, 792]].forEach(([x, y]) => { g.fillRect(x - 2.5, y - 6, 5, 9); g.beginPath(); g.rect(x - 2.5, y - 6, 5, 9); ink(g, 0.9); });
    barrel(g, 1003, 712); barrel(g, 1012, 714, "#a06a3a"); crate(g, 1044, 745, 0.9); crate(g, 1050, 736, 0.8, "#c98c55");
    g.strokeStyle = INK; g.lineWidth = 1.4; g.beginPath(); g.moveTo(1036, 790); g.lineTo(1036, 768); g.stroke(); g.fillStyle = "#3a2a1a"; g.fillRect(1032.5, 763, 7, 6); WINDOWS.push([1033.5, 764, 5, 4]);
    g.save(); g.translate(952, 776); g.fillStyle = "rgba(20,50,70,.3)"; g.beginPath(); g.ellipse(2, 5, 26, 4, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#3f8aa8"; g.beginPath(); g.moveTo(-24, -3); g.lineTo(24, -3); g.lineTo(18, 5); g.lineTo(-18, 5); g.closePath(); g.fill(); ink(g, 1.2); g.fillStyle = P.cream; g.fillRect(-22, -3, 44, 2);
    g.strokeStyle = INK; g.lineWidth = 1.2; g.beginPath(); g.moveTo(-4, -3); g.lineTo(-4, -22); g.stroke(); g.restore();
    g.strokeStyle = "rgba(34,48,58,.7)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(974, 774); g.quadraticCurveTo(990, 780, 1004, 762); g.stroke();

    /* ---- the lighthouse: on a heap of rocks, cream and coral bands, a gallery rail, the keeper's house at its foot ---- */
    for (let i = 0; i < 9; i++) { const x = 270 + (i % 5) * 14 + R() * 6, y = 598 + Math.floor(i / 5) * 10 + R() * 4; g.fillStyle = i % 2 ? "#8b7a66" : "#9e8e78"; g.beginPath(); g.ellipse(x, y, 9 + R() * 4, 6 + R() * 2, R(), 0, Math.PI * 2); g.fill(); ink(g, 1.1, 0.8); }
    WINDOWS.push(...house(g, 300, 612, 56, 26, [P.cream, "#e6d8b8"], ["#6a6a72"], { d: 14, win: 1, doorC: P.navy }));
    const tower = [[286, 590], [292, 450], [308, 450], [314, 590]];
    g.fillStyle = P.cream; wobble(g, tower, true, R, 0.4); g.fill();
    g.fillStyle = P.coral; [[560, 535], [505, 480]].forEach(([a, b]) => { const k0 = (590 - a) / 140, k1 = (590 - b) / 140; g.beginPath(); g.moveTo(286 + 6 * k0, a); g.lineTo(314 - 6 * k0, a); g.lineTo(314 - 6 * k1, b); g.lineTo(286 + 6 * k1, b); g.closePath(); g.fill(); });
    g.save(); wobble(g, tower, true, R, 0); g.clip(); dots(g, 302, 450, 316, 590, 4, 1.4, "rgba(34,48,58,.4)"); g.restore();
    wobble(g, tower, true, R, 0.4); ink(g, 1.8);
    g.fillStyle = INK; g.fillRect(296, 520, 8, 12); WINDOWS.push([297, 521, 6, 10]);
    g.fillStyle = INK; g.fillRect(288, 438, 24, 14); g.fillStyle = "#3c3c44"; g.beginPath(); g.moveTo(286, 438); g.lineTo(300, 424); g.lineTo(314, 438); g.closePath(); g.fill(); ink(g, 1.4);
    g.strokeStyle = INK; g.lineWidth = 1; g.beginPath(); g.moveTo(283, 452); g.lineTo(317, 452); g.moveTo(283, 446); g.lineTo(317, 446); for (let x = 284; x <= 316; x += 4) { g.moveTo(x, 446); g.lineTo(x, 452); } g.stroke();
    g.fillStyle = "#e9b44c"; g.beginPath(); g.arc(300, 421, 2, 0, Math.PI * 2); g.fill();

    /* ---- the fishing village: huts on stilts in the shallows, nets drying on poles, canoes pulled up on the sand ---- */
    [[470, 756, 34], [528, 766, 30]].forEach(([x, y, w], i) => {
      g.strokeStyle = INK; g.lineWidth = 1.8; g.beginPath(); for (let k = 0; k < 4; k++) { const sx = x - w / 2 + 3 + k * (w - 6) / 3; g.moveTo(sx, y); g.lineTo(sx, y + 12); } g.stroke();
      g.strokeStyle = "rgba(255,255,255,.6)"; g.lineWidth = 1; g.beginPath(); for (let k = 0; k < 4; k++) { const sx = x - w / 2 + 3 + k * (w - 6) / 3; g.moveTo(sx - 3, y + 12); g.lineTo(sx + 3, y + 12); } g.stroke();
      g.fillStyle = "#a57a4c"; g.fillRect(x - w / 2 - 3, y - 2, w + 6, 4); g.beginPath(); g.rect(x - w / 2 - 3, y - 2, w + 6, 4); ink(g, 1);
      g.fillStyle = i ? "#c98c55" : "#b07a48"; g.fillRect(x - w / 2, y - 18, w, 16); g.beginPath(); g.rect(x - w / 2, y - 18, w, 16); ink(g, 1.3);
      g.fillStyle = INK; g.fillRect(x - 4, y - 13, 8, 11); WINDOWS.push([x + w / 2 - 9, y - 14, 5, 5]); g.fillRect(x + w / 2 - 9, y - 14, 5, 5);
      thatch(g, [[x - w / 2 - 6, y - 17], [x, y - 34], [x + w / 2 + 6, y - 17]], R);
    });
    g.strokeStyle = INK; g.lineWidth = 1.4; g.beginPath(); g.moveTo(588, 736); g.lineTo(588, 714); g.moveTo(620, 738); g.lineTo(620, 716); g.stroke();
    g.save(); g.beginPath(); g.moveTo(588, 716); g.quadraticCurveTo(604, 730, 620, 718); g.lineTo(620, 730); g.quadraticCurveTo(604, 740, 588, 730); g.closePath(); g.fillStyle = "rgba(160,120,70,.35)"; g.fill(); g.clip();
    g.strokeStyle = "rgba(34,48,58,.55)"; g.lineWidth = 0.6; for (let k = 0; k < 40; k += 3) { g.beginPath(); g.moveTo(586 + k, 712); g.lineTo(586 + k - 10, 742); g.moveTo(586 + k - 10, 712); g.lineTo(586 + k, 742); g.stroke(); } g.restore();
    [[420, 744, P.coral, -0.15], [640, 744, P.teal, 0.1]].forEach(([x, y, c, a]) => { g.save(); g.translate(x, y); g.rotate(a); g.fillStyle = c; g.beginPath(); g.moveTo(-16, -2); g.quadraticCurveTo(0, -7, 16, -2); g.quadraticCurveTo(0, 4, -16, -2); g.fill(); ink(g, 1); g.restore(); });

    PALMS.forEach(([x, y]) => palmBase(g, x, y));
    for (let i = 0; i < 34; i++) { const a = R() * Math.PI * 2, [x, y] = COAST[Math.floor(R() * COAST.length)]; if (y < 560) continue; if (Math.abs(x - 1030) < 60 && y > 700) continue; g.fillStyle = i % 2 ? P.rock : "#9e8e78"; g.beginPath(); g.ellipse(x, y, 4 + R() * 7, 3 + R() * 4, a, 0, Math.PI * 2); g.fill(); ink(g, 1.2, 0.8); }
    /* driftwood and shells on the beach */
    [[700, 742], [880, 748], [1240, 712]].forEach(([x, y]) => { g.strokeStyle = "#8a6a4a"; g.lineWidth = 2.5; g.beginPath(); g.moveTo(x - 9, y); g.lineTo(x + 9, y - 2); g.moveTo(x + 2, y - 1); g.lineTo(x + 6, y - 5); g.stroke(); });
  }
  const PALMS = [[380, 660], [430, 690], [560, 705], [652, 702], [905, 700], [1100, 700], [1290, 615], [1350, 640], [1390, 560], [330, 520], [345, 470], [1210, 520], [710, 690], [1196, 708], [240, 580], [940, 470]];

  /* the moving parts of the island's places: smoke, fire, torches, falling water, the fountain, flags, bulbs at night */
  function islandFx(g, t, light) {
    for (const f of FX) {
      if (f.k === "smoke") {
        if (spr(g, (f.s || 1) >= 1 ? "smoke-chimney" : "smoke-wisp", f.x, f.y + 3, t, 1, 0, ((f.s || 1) >= 1 ? 80 : 40) * (f.s || 1))) continue;   // the painted strip, once it is there
        for (let i = 0; i < 7; i++) {
          const p = ((t * 0.00012 * (1 + f.s * 0.1) + i / 7) % 1), r = (3 + p * 14) * f.s, x = f.x + Math.sin(p * 5 + i) * 6 * f.s + p * 26 * f.s, y = f.y - p * 70 * f.s;
          g.fillStyle = f.c; g.globalAlpha = (1 - p) * 0.55; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
          g.globalAlpha = (1 - p) * 0.35; g.strokeStyle = INK; g.lineWidth = 0.8; g.stroke();
        }
        g.globalAlpha = 1;
      } else if (f.k === "fire" || f.k === "torch") {
        const s = f.k === "torch" ? 0.7 : 1;
        for (let i = 0; i < 3; i++) {
          const h = (9 + Math.sin(t * 0.011 + i * 2 + f.x) * 1.4) * s, w = (4 - i) * s;
          g.fillStyle = ["#e2674f", "#f2b134", "#fff2b0"][i]; g.beginPath(); g.moveTo(f.x - w, f.y); g.quadraticCurveTo(f.x - w * 0.6, f.y - h * 0.6, f.x + Math.sin(t * 0.013 + i) * 1.5, f.y - h + i * 2 * s); g.quadraticCurveTo(f.x + w * 0.6, f.y - h * 0.6, f.x + w, f.y); g.closePath(); g.fill();
        }
      } else if (f.k === "falls") {
        /* the fall as the painting has it: from its top edge (x, w) to its bottom edge (x1, w1), straight down and widening;
           strands of water of uneven width and brightness fall at their own pace and sway a little, the sheet brightens in
           waves, mist rises from the foot, rings spread in the pool. A layout without x1/w1 gets the old slant. */
        const x1 = f.x1 != null ? f.x1 : f.x + 8, w1 = f.w1 || f.w, yb = f.y + f.h;
        g.save(); g.beginPath(); g.moveTo(f.x, f.y); g.lineTo(f.x + f.w, f.y - 2); g.lineTo(x1 + w1, yb + 4); g.lineTo(x1, yb + 6); g.closePath(); g.clip();
        const N = Math.max(6, Math.round(f.w / 3.5));
        for (let i = 0; i < N; i++) {
          const u = (i + 0.5) / N, sway = Math.sin(t * 0.0021 + i * 1.7) * 0.9, speed = 0.05 + (i % 3) * 0.012, gap = 22 + (i % 4) * 7;
          const xt = f.x + u * f.w + sway, xb = x1 + u * w1 + sway, bright = 0.35 + 0.4 * (0.5 + 0.5 * Math.sin(t * 0.0033 + i * 2.3));
          g.strokeStyle = `rgba(255,255,255,${bright})`; g.lineWidth = 0.8 + (i % 3) * 0.7;
          const o = (t * speed + i * 13) % gap;
          for (let y = f.y - gap + o; y < yb; y += gap) {
            const k0 = (y - f.y) / f.h, k1 = (y + gap * 0.55 - f.y) / f.h;
            g.beginPath(); g.moveTo(xt + (xb - xt) * k0, y); g.lineTo(xt + (xb - xt) * k1, y + gap * 0.55); g.stroke();
          }
        }
        for (let i = 0; i < 3; i++) {   // the sheet itself, lighter in slow waves running down
          const k = ((t * 0.00025 + i / 3) % 1), y = f.y + k * f.h; const gr = g.createLinearGradient(0, y - 18, 0, y + 18);
          gr.addColorStop(0, "rgba(255,255,255,0)"); gr.addColorStop(0.5, "rgba(255,255,255,.16)"); gr.addColorStop(1, "rgba(255,255,255,0)");
          g.fillStyle = gr; g.fillRect(Math.min(f.x, x1) - 4, y - 18, Math.max(f.w, w1) + 8, 36);
        }
        g.restore();
        for (let i = 0; i < 5; i++) {   // mist at the foot: soft puffs rising and fading
          const k = ((t * 0.0004 + i / 5) % 1), x = x1 + w1 * (0.15 + 0.7 * ((i * 0.37) % 1)) + Math.sin(t * 0.001 + i) * 3, y = yb + 2 - k * 26, r = 6 + k * 14;
          const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(255,255,255,${0.28 * (1 - k)})`); gr.addColorStop(1, "rgba(255,255,255,0)");
          g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
        }
        for (let i = 0; i < 3; i++) {   // rings in the pool
          const k = ((t * 0.0007 + i / 3) % 1); g.strokeStyle = `rgba(255,255,255,${0.5 * (1 - k)})`; g.lineWidth = 1;
          g.beginPath(); g.ellipse(x1 + w1 / 2, yb + 10, w1 * (0.3 + 0.5 * k), 4 + 10 * k, 0, 0, Math.PI * 2); g.stroke();
        }
      } else if (f.k === "splash") {
        for (let i = 0; i < 3; i++) { const p = (t * 0.001 + i / 3) % 1; g.strokeStyle = `rgba(255,255,255,${0.7 * (1 - p)})`; g.lineWidth = 1; g.beginPath(); g.ellipse(f.x + 4, f.y + 3, 6 + p * 12, 2 + p * 4, 0, 0, Math.PI * 2); g.stroke(); }
      } else if (f.k === "stream") {
        const p = f.pts; g.fillStyle = "rgba(255,255,255,.8)";
        for (let i = 0; i < 9; i++) { const k = ((t * 0.00005 + i / 9) % 1), [x, y] = alongPath(p, k); g.fillRect(x - 1.5, y - 0.5, 3, 1); }
      } else if (f.k === "fountain") {
        g.strokeStyle = "rgba(220,245,250,.9)"; g.lineWidth = 1;
        for (let i = 0; i < 4; i++) { const s = (i - 1.5) * 4 + Math.sin(t * 0.004 + i) * 0.6; g.beginPath(); g.moveTo(f.x, f.y); g.quadraticCurveTo(f.x + s, f.y - 8, f.x + s * 2, f.y + 12); g.stroke(); }
      } else if (f.k === "flag") {
        const top = f.y - f.h;
        g.strokeStyle = INK; g.lineWidth = 1.2; g.beginPath(); g.moveTo(f.x, f.y); g.lineTo(f.x, top); g.stroke();
        g.beginPath(); g.moveTo(f.x, top); for (let k = 0; k <= 8; k++) g.lineTo(f.x + k * 2, top + Math.sin(t * 0.007 - k * 0.8 + f.x) * 1.6 * k / 8);
        for (let k = 8; k >= 0; k--) g.lineTo(f.x + k * 2, top + 9 + Math.sin(t * 0.007 - k * 0.8 + f.x) * 1.6 * k / 8);
        g.closePath(); g.fillStyle = f.c0; g.fill(); g.strokeStyle = INK; g.lineWidth = 0.8; g.stroke();
        g.fillStyle = f.c1; g.beginPath(); g.arc(f.x + 8, top + 4.5 + Math.sin(t * 0.007 - 3 + f.x) * 0.6, 2, 0, Math.PI * 2); g.fill();
      } else if (f.k === "crater") {
        g.fillStyle = `rgba(255,140,60,${0.25 + 0.2 * Math.sin(t * 0.002) + light * 0.4})`; g.beginPath(); g.ellipse(f.x, f.y, 13, 2.6, 0, 0, Math.PI * 2); g.fill();
      }
    }
  }
  /* at dusk and at night: fires, torches and the bar's bulbs throw a warm light around them */
  function islandGlow(g, t, light) {
    for (const f of FX) {
      if (f.k === "fire" || f.k === "torch" || f.k === "crater") {
        const r = f.k === "fire" ? 34 : f.k === "crater" ? 46 : 20, fl = flick(t, f.x, f.y);
        const gr = g.createRadialGradient(f.x, f.y - 4, 0, f.x, f.y - 4, r); gr.addColorStop(0, `rgba(255,150,60,${0.5 * light * fl})`); gr.addColorStop(1, "rgba(255,150,60,0)");
        g.fillStyle = gr; g.beginPath(); g.arc(f.x, f.y - 4, r, 0, Math.PI * 2); g.fill();
      } else if (f.k === "bulb") {
        g.fillStyle = [`rgba(255,120,90,${light})`, `rgba(255,210,90,${light})`, `rgba(90,255,220,${light})`][f.c]; g.beginPath(); g.arc(f.x, f.y, 2.4 + Math.sin(t * 0.004 + f.x) * 0.4, 0, Math.PI * 2); g.fill();
      }
    }
  }

  /* ---------- the island at night: every place its own light ----------
     The layout's "lights" (world units). Each one lights the painting around it in its own colour: the night is not one
     flat blue laid over the picture but a light map (lightMap), the blue of the hour everywhere and around each lamp the
     lamp's own colour, so the painting keeps its colours where a lamp shines on it. The lamps themselves are drawn bright
     on top (nightLamps): from the painted strips in rabbit/fx (fx.json) when they are there, drawn until then.
       glow {x,y,r,c,a,f,sy}  light only; c a colour of LC or [r,g,b]; f "fire" lives like a flame, "breathe" swells
       torch {x,y,s}          a bamboo torch standing on x,y         fire {x,y,s}   a fire on the ground or in a bowl
       lamp {x,y,c,r}         a small lamp or a lit doorway           candle {x,y}   a candle in a jar on a table
       lantern {x,y,c,s}      a paper lantern hanging from x,y, swaying: c "red" | "stripes" | "warm"
       string {pts,c,sag}     bulbs hung between the points: c "warm" | "pink" | "multi"
       win {x,y,w,h,c,arch}   a lit window, x,y its middle            pool {poly}    water lit from below
       flood {x,y,w,h,c}      a floodlight on a wall, washing it upwards from x,y
       motes {x,y,r,n,c}      motes of light drifting                 buoy {x,y,c}   a blinking light on a buoy
       sparks {x,y}           sparks flying from a chimney
     "w": n mirrors a light in the water n units under it; "p" names the place the light belongs to. */
  const LIGHTS = [];
  const LC = { fire: [255, 160, 76], warm: [255, 206, 140], cream: [255, 236, 204], pink: [255, 146, 198], teal: [92, 236, 214], cyan: [110, 212, 255], red: [255, 92, 72], moon: [192, 214, 255], gold: [255, 212, 116], green: [57, 255, 138] };
  const LANTERN = { red: [255, 104, 76], stripes: [255, 190, 160], warm: [255, 200, 120] };
  const BULBS = { warm: [[255, 214, 150]], pink: [[255, 150, 200], [255, 200, 226]], multi: [[255, 96, 80], [255, 210, 90], [90, 236, 214], [255, 150, 200]] };
  const lc = c => (Array.isArray(c) ? c : LC[c] || LC.warm);
  /* only a flame lives: slowly and a little (torches, fires, candles, oil lamps, paper lanterns); electric light stays
     still, "breathe" swells gently over seconds, a buoy glows up softly every few seconds */
  const flick = (t, x, y) => 0.95 + 0.035 * Math.sin(t * 0.0047 + x) + 0.015 * Math.sin(t * 0.0113 + y * 1.7);
  const burns = L => L.k === "torch" || L.k === "fire" || L.k === "candle" || L.k === "lantern" || L.k === "sparks" || L.f === "fire" || !!L.oil || (L.k === "lamp" && L.c === "fire");
  const life = (L, t) => (L.f === "steady" ? 1 : L.f === "breathe" ? 0.92 + 0.08 * Math.sin(t * 0.0009 + (L.x || 0)) : burns(L) ? flick(t, L.x || 0, L.y || 0) : 1);
  const buoyAt = (L, t) => { const p = ((t + L.x * 37) % 3200) / 3200; return p < 0.32 ? Math.sin(p / 0.32 * Math.PI) : 0; };
  const lampsOn = sky => Math.max(0, (sky.light - 0.45) / 0.55);   // the lamps come on from about five in the afternoon, fully lit by night
  function bulbs(L) {   // where the bulbs of a string hang: every few units, each span sagging in the middle
    if (L._b) return L._b;
    const out = [], P = L.pts;
    for (let i = 0; i + 1 < P.length; i++) {
      const [x0, y0] = P[i], [x1, y1] = P[i + 1], d = Math.hypot(x1 - x0, y1 - y0), n = Math.max(2, Math.round(d / (L.gap || 6))), sag = L.sag != null ? L.sag : d * 0.07;
      for (let k = i ? 1 : 0; k <= n; k++) { const u = k / n; out.push([x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + Math.sin(u * Math.PI) * sag]); }
    }
    return (L._b = out);
  }
  const lightOf = L => (L.k === "torch" || L.k === "fire" || L.k === "sparks" ? LC.fire : L.k === "lantern" ? LANTERN[L.c] || LANTERN.warm : L.k === "string" ? (BULBS[L.c] || BULBS.warm)[0] : L.k === "candle" || L.k === "win" ? lc(L.c || "gold") : L.k === "pool" ? LC.teal : lc(L.c || (L.k === "flood" ? "moon" : L.k === "buoy" ? "cyan" : L.k === "motes" ? "teal" : "warm")));
  /* the painted strips of rabbit/fx, as they come (fx.json: file, w, h, frames, fps, anchor, blend); world heights here */
  const SPR = {}, SPRH = { "smoke-chimney": 80, "smoke-wisp": 40, "torch-bamboo": 24, "torch-bamboo-b": 24, campfire: 16, "lantern-paper-red": 8, "lantern-paper-stripes": 8, "lamp-oil": 7, "bulb-warm": 2.6, "bulb-pink": 2.6, "candle-jar": 3.6, sparks: 34, "buoy-blink": 5, "glow-motes": 22 };
  try {
    fetch("fx/fx.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null)).then(j => {
      for (const id in j || {}) { const d = j[id]; if (!d || !d.file || !d.frames) continue; const im = new Image(); im.onload = () => { SPR[id] = Object.assign({}, d, { im }); }; im.src = "fx/" + d.file; }
    }).catch(() => {});
  } catch (e) {}
  function spr(g, id, x, y, t, a = 1, ph = 0, h = SPRH[id]) {   // a painted strip, its anchor on x,y and h units high; false while it is not there
    const d = SPR[id]; if (!d || !h) return false;
    const k = h / d.h, f = Math.floor((t / 1000) * (d.fps || 8) + ph) % d.frames, [ax, ay] = d.anchor || [d.w / 2, d.h];
    g.save(); g.globalAlpha = a; if (d.blend === "add") g.globalCompositeOperation = "lighter";
    g.drawImage(d.im, f * d.w, 0, d.w, d.h, x - ax * k, y - ay * k, d.w * k, d.h * k); g.restore();
    return true;
  }
  /* the light map: the light of the hour everywhere, and the lamps' own light around them (at a quarter of the
     screen's pixels: light is soft). The painted island is multiplied with it. */
  function lightMap(W, H, m, n, t) {
    const q = 4, c = S.lm || (S.lm = document.createElement("canvas")), w = Math.ceil(W / q), h = Math.ceil(H / q);
    if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    const g = c.getContext("2d"); g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "source-over"; g.fillStyle = rgb(m); g.fillRect(0, 0, w, h);
    const s = fitScale() * S.cam.z * S.K / q; g.setTransform(s, 0, 0, s, W / q / 2 - S.cam.x * s, H / q / 2 - S.cam.y * s);
    const pool = (x, y, r, col, a, sy = 1) => {
      if (a < 0.01) return; a = Math.min(1, a);
      g.save(); g.translate(x, y); if (sy !== 1) g.scale(1, sy);
      const gr = g.createRadialGradient(0, 0, 0, 0, 0, r); gr.addColorStop(0, rgb(col, a)); gr.addColorStop(0.4, rgb(col, a * 0.62)); gr.addColorStop(1, rgb(col, 0));
      g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r, 0, Math.PI * 2); g.fill(); g.restore();
    };
    WINDOWS.forEach(([x, y, ww, wh]) => pool(x + ww / 2, y + wh / 2, 15, LC.warm, 0.55 * n));
    for (const f of FX) if (f.k === "fire" || f.k === "torch" || f.k === "crater") pool(f.x, f.y - 4, f.k === "fire" ? 44 : f.k === "crater" ? 54 : 28, LC.fire, 0.85 * n * flick(t, f.x, f.y));
    for (const L of LIGHTS) {
      const s = (L.s || 1) * (L.k === "lantern" ? 1.35 : 1), col = lightOf(L), fl = life(L, t);
      if (L.k === "glow") pool(L.x, L.y, L.r || 30, col, (L.a || 0.8) * n * fl, L.sy || 1);
      else if (L.k === "torch") pool(L.x, L.y - 15 * s, 30 * s, col, 0.85 * n * fl);
      else if (L.k === "fire") pool(L.x, L.y - 4 * s, 46 * s, col, 0.9 * n * fl);
      else if (L.k === "lamp") pool(L.x, L.y, L.r || 18, col, (L.a || 0.75) * n * fl);
      else if (L.k === "candle") pool(L.x, L.y - 2, 9, col, 0.55 * n * fl);
      else if (L.k === "win") pool(L.x, L.y, Math.max(L.w, L.h) * 0.75, col, (L.a || 0.55) * n, Math.min(1.6, L.h / L.w * 0.5));
      else if (L.k === "lantern") pool(L.x, L.y + 6 * s, 20 * s, col, 0.75 * n * fl);
      else if (L.k === "string") { const B = bulbs(L), cs = BULBS[L.c] || BULBS.warm; B.forEach(([x, y], i) => pool(x, y + 3, 10, cs[i % cs.length], 0.5 * n)); }
      else if (L.k === "pool") {
        g.fillStyle = rgb(col, 0.8 * n); g.beginPath(); L.poly.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.fill();
        const xs = L.poly.map(p => p[0]), ys = L.poly.map(p => p[1]), cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        pool(cx, cy, (Math.max(...xs) - Math.min(...xs)) * 0.75, col, 0.45 * n * (0.97 + 0.03 * Math.sin(t * 0.0012)), 0.6);
      }
      else if (L.k === "flood") pool(L.x, L.y - L.h * 0.45, L.w * 0.62, col, (L.a || 0.7) * n, L.h / (L.w * 1.24));
      else if (L.k === "motes") pool(L.x, L.y, (L.r || 30) * 1.3, col, (L.a || 0.35) * n * fl);
      else if (L.k === "buoy") pool(L.x, L.y, 14, col, 0.6 * n * buoyAt(L, t));
      else if (L.k === "sparks") pool(L.x, L.y, 16, col, 0.45 * n * fl);
    }
    pool(SPOT.beam[0], SPOT.beam[1], 26, LC.green, 0.7 * n);   // the lighthouse lamp and the radio mast's light
    if (Math.floor(t / 700) % 2) pool(SPOT.blink[0], SPOT.blink[1], 14, LC.red, 0.6 * n);
    return c;
  }
  /* ---- the lamps themselves, bright over the night ---- */
  function halo(g, x, y, r, col, a) {
    if (a < 0.01) return; const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, rgb(col, Math.min(1, a))); gr.addColorStop(1, rgb(col, 0));
    g.globalCompositeOperation = "lighter"; g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.globalCompositeOperation = "source-over";
  }
  function flame(g, x, y, h, w, t, ph, a) {   // a flame standing on x,y: three tongues, red outside, white-gold inside
    g.globalAlpha = a;
    for (let i = 0; i < 3; i++) {
      const hh = h * (1 - i * 0.24) * (0.91 + 0.09 * Math.sin(t * 0.0105 + ph + i * 2.1)), ww = w * (1 - i * 0.3), tip = Math.sin(t * 0.0065 + ph + i) * w * 0.3;
      g.fillStyle = ["#ef5f3a", "#ffb23a", "#fff1b8"][i]; g.beginPath(); g.moveTo(x - ww, y); g.quadraticCurveTo(x - ww * 0.75, y - hh * 0.55, x + tip, y - hh); g.quadraticCurveTo(x + ww * 0.75, y - hh * 0.55, x + ww, y); g.closePath(); g.fill();
    }
    g.globalAlpha = 1;
  }
  const dot = (g, x, y, r, col) => { g.fillStyle = col; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); };
  function nightLamps(g, t, n) {
    const on = Math.min(1, n * 1.6);
    LIGHTS.forEach((L, i) => {
      const s = (L.s || 1) * (L.k === "lantern" ? 1.35 : 1), col = lightOf(L), x = L.x, y = L.y;
      if (L.k === "torch") {
        if (!spr(g, i % 2 ? "torch-bamboo-b" : "torch-bamboo", x, y, t, on, i * 3.7, 24 * s)) {
          g.globalAlpha = on; g.strokeStyle = "#3a2a1e"; g.lineWidth = 1.3 * s; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 0.4 * s, y - 14 * s); g.stroke();
          g.fillStyle = "#5a4028"; g.beginPath(); g.moveTo(x - 1.9 * s, y - 16.5 * s); g.lineTo(x + 2.3 * s, y - 16.5 * s); g.lineTo(x + 1.3 * s, y - 13.5 * s); g.lineTo(x - 0.9 * s, y - 13.5 * s); g.closePath(); g.fill(); g.globalAlpha = 1;
          flame(g, x + 0.2 * s, y - 16 * s, 7 * s, 1.9 * s, t, i * 1.3, on);
        }
        halo(g, x, y - 19 * s, 11 * s, col, 0.5 * on * flick(t, x, y));
      } else if (L.k === "fire") {
        if (!spr(g, "campfire", x, y, t, on, i * 2.1, 16 * s)) {
          g.fillStyle = `rgba(255,120,50,${0.6 * on})`; g.beginPath(); g.ellipse(x, y, 5 * s, 1.6 * s, 0, 0, Math.PI * 2); g.fill();
          flame(g, x - 2.2 * s, y, 6.5 * s, 2.2 * s, t, i + 0.7, on); flame(g, x + 2.4 * s, y, 5.5 * s, 2 * s, t, i + 2.9, on); flame(g, x, y, 9 * s, 2.8 * s, t, i, on);
          for (let j = 0; j < 4; j++) { const p = (t * 0.0008 + j / 4 + i * 0.13) % 1; dot(g, x + Math.sin(j * 2.7 + p * 5) * 3 * s, y - 6 * s - p * 16 * s, 0.6 * s, `rgba(255,210,120,${(1 - p) * on})`); }
        }
        halo(g, x, y - 5 * s, 22 * s, col, 0.45 * on * flick(t, x, y));
      } else if (L.k === "lamp") {
        if (!(L.oil && spr(g, "lamp-oil", x, y - 3, t, on, i * 1.9))) dot(g, x, y, 1.3 * s, rgb(mix(col, [255, 255, 255], 0.6), on));
        halo(g, x, y, 7 * s, col, 0.7 * on * life(L, t));
      } else if (L.k === "candle") {
        if (!spr(g, "candle-jar", x, y, t, on, i * 2.3)) dot(g, x, y - 1.2, 0.7, rgb([255, 236, 170], on));
        halo(g, x, y - 1.5, 4.5, col, 0.6 * on * flick(t, x, y));
      } else if (L.k === "lantern") {
        const sway = Math.sin(t * 0.0011 + x * 0.7) * 0.06, bx = x + Math.sin(sway) * 5 * s, by = y + Math.cos(sway) * 5 * s;
        if (!spr(g, L.c === "stripes" ? "lantern-paper-stripes" : "lantern-paper-red", x, y, t, on, i * 1.1, 8 * s)) {
          g.save(); g.translate(x, y); g.rotate(-sway); g.globalAlpha = on;
          g.strokeStyle = "rgba(34,48,58,.9)"; g.lineWidth = 0.5; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, 2 * s); g.stroke();
          const gr = g.createRadialGradient(0, 5 * s, 0, 0, 5 * s, 3.2 * s); gr.addColorStop(0, rgb(mix(col, [255, 250, 220], 0.7))); gr.addColorStop(1, rgb(L.c === "stripes" ? [235, 70, 60] : col));
          g.fillStyle = gr; g.beginPath(); g.ellipse(0, 5 * s, 2.6 * s, 3.1 * s, 0, 0, Math.PI * 2); g.fill();
          if (L.c === "stripes") { g.save(); g.clip(); g.fillStyle = "rgba(255,248,236,.85)"; [-1.5, 0.3].forEach(u => g.fillRect(u * s, 1.8 * s, 0.9 * s, 6.5 * s)); g.restore(); }
          g.fillStyle = "#3a2a1e"; g.fillRect(-1.2 * s, 1.7 * s, 2.4 * s, 0.7 * s); g.fillRect(-1.2 * s, 7.7 * s, 2.4 * s, 0.7 * s);
          g.restore(); g.globalAlpha = 1;
        }
        halo(g, bx, by, 9 * s, col, 0.5 * on * flick(t, x, y));
      } else if (L.k === "string") {
        const B = bulbs(L), cs = BULBS[L.c] || BULBS.warm;
        g.globalAlpha = on; g.strokeStyle = "rgba(34,48,58,.8)"; g.lineWidth = 0.45; g.beginPath(); B.forEach(([bx, by], k) => (k ? g.lineTo(bx, by) : g.moveTo(bx, by))); g.stroke(); g.globalAlpha = 1;
        B.forEach(([bx, by], k) => {
          const c = cs[k % cs.length], tw = 1;
          if (!spr(g, L.c === "pink" ? "bulb-pink" : "bulb-warm", bx, by + 1, t, on, k * 0.7)) dot(g, bx, by + 1, 0.95, rgb(mix(c, [255, 255, 255], 0.45), on));
          halo(g, bx, by + 1, 4.2, c, 0.6 * on * tw);
        });
      } else if (L.k === "pool") {
        const xs = L.poly.map(p => p[0]), ys = L.poly.map(p => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
        g.save(); g.beginPath(); L.poly.forEach(([px, py], k) => (k ? g.lineTo(px, py) : g.moveTo(px, py))); g.closePath(); g.clip();
        g.globalCompositeOperation = "lighter"; g.fillStyle = rgb(col, 0.2 * on); g.fillRect(x0, y0, x1 - x0, y1 - y0);
        if (!spr(g, "pool-caustics", (x0 + x1) / 2, (y0 + y1) / 2, t, on * 0.8, 0, y1 - y0)) {   // light nets that ripple across the water
          g.lineWidth = 0.6;
          for (let k = 0; k < 2; k++) for (let r = y0 - 6; r < y1 + 6; r += 4.5) {
            g.strokeStyle = `rgba(220,255,250,${(0.16 + 0.04 * Math.sin(t * 0.0012 + r)) * on})`; g.beginPath();
            for (let px = x0; px <= x1; px += 3) { const py = r + (k ? (px - x0) * 0.25 : -(px - x0) * 0.25) % 9 + Math.sin(px * 0.21 + t * (k ? 0.0011 : -0.0013) + r * 0.7) * 1.6; px === x0 ? g.moveTo(px, py) : g.lineTo(px, py); }
            g.stroke();
          }
        }
        g.restore(); g.globalCompositeOperation = "source-over";
      } else if (L.k === "win") {
        const w = L.w, h = L.h, x0 = x - w / 2, y0 = y - h / 2, gr = g.createLinearGradient(0, y0, 0, y0 + h);
        gr.addColorStop(0, rgb(col, 0.32 * on)); gr.addColorStop(1, rgb(col, 0.6 * on));
        g.globalCompositeOperation = "lighter"; g.fillStyle = gr; g.beginPath();
        if (L.arch) { g.moveTo(x0, y0 + h); g.lineTo(x0, y0 + w / 2); g.arc(x, y0 + w / 2, w / 2, Math.PI, 0); g.lineTo(x0 + w, y0 + h); g.closePath(); } else g.rect(x0, y0, w, h);
        g.fill(); g.globalCompositeOperation = "source-over";
      } else if (L.k === "flood") {   // a wash of light up the wall, brightest at the lamp, soft at the edges
        g.save(); g.translate(x, y); g.scale(1, L.h / L.w);
        const gr = g.createRadialGradient(0, -L.w * 0.2, 0, 0, -L.w * 0.2, L.w * 0.8); gr.addColorStop(0, rgb(col, 0.16 * on)); gr.addColorStop(0.5, rgb(col, 0.06 * on)); gr.addColorStop(1, rgb(col, 0));
        g.globalCompositeOperation = "lighter"; g.fillStyle = gr; g.beginPath(); g.arc(0, -L.w * 0.2, L.w * 0.8, 0, Math.PI * 2); g.fill(); g.restore(); g.globalCompositeOperation = "source-over";
        dot(g, x, y, 1.1, rgb(mix(col, [255, 255, 255], 0.7), on)); halo(g, x, y, 6, col, 0.6 * on);
      } else if (L.k === "motes") {
        if (!spr(g, "glow-motes", x, y, t, on, i * 2, (L.r || 30) * 1.1)) {
          for (let j = 0; j < (L.n || 9); j++) {
            const r = L.r || 30, mx = x + Math.sin(t * 0.00037 * (1 + (j % 3) * 0.35) + j * 2.4) * r, my = y + Math.cos(t * 0.00029 * (1 + (j % 2) * 0.5) + j * 1.7) * r * 0.42 - (j % 4) * 2;
            const tw = 0.65 + 0.35 * Math.sin(t * 0.0013 + j * 1.3); halo(g, mx, my, 3.4, col, 0.7 * on * tw); dot(g, mx, my, 0.55, rgb([235, 255, 250], on * tw));
          }
        }
      } else if (L.k === "buoy") {
        const b = buoyAt(L, t); if (b > 0.02 && !spr(g, "buoy-blink", x, y, t, on * b, i)) { dot(g, x, y, 1.2, rgb(mix(col, [255, 255, 255], 0.6), on * b)); halo(g, x, y, 6, col, 0.8 * on * b); }
      } else if (L.k === "sparks") {
        if (!spr(g, "sparks", x, y, t, on, i)) for (let j = 0; j < 9; j++) {
          const p = (t * 0.00055 + j / 9) % 1, sx = x + Math.sin(j * 3.1 + p * 4) * 4 * p + p * 9, sy = y - p * 32;
          dot(g, sx, sy, 0.7, `rgba(255,${170 + Math.round(60 * (1 - p))},90,${(1 - p) * on})`); halo(g, sx, sy, 2.6, LC.fire, 0.4 * (1 - p) * on);
        }
      }
      if (L.w && (L.k !== "buoy" || buoyAt(L, t) > 0.02)) {   // the light in the water under it: short strokes that shimmer a little
        const wy = (L.k === "lantern" ? y + 6 * s : y) + (+L.w || 4);
        g.globalCompositeOperation = "lighter";
        for (let k = 0; k < 5; k++) { const ww = (6 - k) * 1.3 * (0.78 + 0.22 * Math.sin(t * 0.0021 + k * 1.7 + x)); g.fillStyle = rgb(col, 0.32 * (1 - k / 5) * on * (L.k === "buoy" ? buoyAt(L, t) : 1)); g.fillRect(x - ww / 2 + Math.sin(t * 0.0012 + k) * 0.5, wy + k * 2.6, ww, 0.9); }
        g.globalCompositeOperation = "source-over";
      }
    });
  }

  /* ---------- the moving parts ---------- */
  function palm(g, x, y, t, i) {
    const sway = Math.sin(t * 0.0011 + i * 1.7) * 4 + Math.sin(t * 0.0023 + i) * 1.5, h = 62 + (i * 7) % 22, lean = ((i * 13) % 9 - 4) * 2.4;
    const tx = x + lean + sway, ty = y - h, cx = x + lean * 0.3, cy = y - h * 0.55;
    /* the trunk: a tapering band in two browns, ringed like a printed engraving */
    const at = f => [(1 - f) * (1 - f) * x + 2 * (1 - f) * f * cx + f * f * tx, (1 - f) * (1 - f) * y + 2 * (1 - f) * f * cy + f * f * ty];
    const L = [], Rr = [];
    for (let k = 0; k <= 10; k++) { const f = k / 10, [px, py] = at(f), wdt = 3.6 - f * 1.6; L.push([px - wdt, py]); Rr.unshift([px + wdt, py]); }
    g.fillStyle = "#b07a48"; g.beginPath(); [...L, ...Rr].forEach(([a, b], k) => k ? g.lineTo(a, b) : g.moveTo(a, b)); g.closePath(); g.fill();
    g.strokeStyle = INK; g.lineWidth = 1.4; g.lineJoin = "round"; g.stroke();
    g.lineWidth = 1; for (let k = 1; k < 10; k++) { const [px, py] = at(k / 10), wdt = 3.6 - k / 10 * 1.6; g.beginPath(); g.moveTo(px - wdt, py); g.quadraticCurveTo(px, py + 1.6, px + wdt, py - 0.5); g.stroke(); }
    /* the fronds: long leaves with a toothed edge, flat green with a pale midrib, outlined in ink */
    for (let k = 0; k < 8; k++) {
      const a = -Math.PI / 2 + (k - 3.5) * 0.5 + Math.sin(t * 0.0017 + i + k) * 0.07, len = 36 + (k % 3) * 6;
      const ex = tx + Math.cos(a) * len, ey = ty + Math.sin(a) * len * 0.5 + 18, mx = tx + Math.cos(a) * len * 0.5, my = ty + Math.sin(a) * len * 0.5 - 7;
      const nx = -Math.sin(a) * 5, ny = Math.cos(a) * 3;
      g.fillStyle = k % 2 ? P.leafD : P.leaf;
      g.beginPath(); g.moveTo(tx, ty);
      for (let q = 1; q <= 6; q++) { const f = q / 6, bx = (1 - f) * (1 - f) * tx + 2 * (1 - f) * f * mx + f * f * ex, by = (1 - f) * (1 - f) * ty + 2 * (1 - f) * f * my + f * f * ey, wv = Math.sin(f * Math.PI) * (q % 2 ? 1.25 : 0.7); g.lineTo(bx + nx * wv, by + ny * wv); }
      for (let q = 5; q >= 1; q--) { const f = q / 6, bx = (1 - f) * (1 - f) * tx + 2 * (1 - f) * f * mx + f * f * ex, by = (1 - f) * (1 - f) * ty + 2 * (1 - f) * f * my + f * f * ey, wv = Math.sin(f * Math.PI) * (q % 2 ? 1.25 : 0.7); g.lineTo(bx - nx * wv, by - ny * wv); }
      g.closePath(); g.fill(); g.strokeStyle = INK; g.lineWidth = 1.2; g.stroke();
      g.strokeStyle = "rgba(251,243,223,.55)"; g.lineWidth = 0.9; g.beginPath(); g.moveTo(tx, ty); g.quadraticCurveTo(mx, my, ex, ey); g.stroke();
    }
    g.fillStyle = "#6b4422"; g.strokeStyle = INK; g.lineWidth = 1; for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(tx - 3 + k * 3, ty + 3, 2.6, 0, Math.PI * 2); g.fill(); g.stroke(); }
  }
  function flag(g, x, y, t, c0, c1, mark) {
    g.strokeStyle = "#ddd"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 42); g.stroke();
    g.beginPath(); g.moveTo(x, y - 42);
    for (let k = 0; k <= 10; k++) g.lineTo(x + k * 2.6, y - 42 + Math.sin(t * 0.006 - k * 0.7) * 2.2 * k / 10);
    for (let k = 10; k >= 0; k--) g.lineTo(x + k * 2.6, y - 26 + Math.sin(t * 0.006 - k * 0.7) * 2.2 * k / 10);
    g.closePath(); g.fillStyle = c0; g.fill();
    const fy = y - 34 + Math.sin(t * 0.006 - 3.5) * 1.1; g.strokeStyle = c1; g.lineWidth = 1.6; g.beginPath();
    if (mark === "wind") { for (let k = 0; k < 2; k++) { g.moveTo(x + 6, fy - 2 + k * 4); g.quadraticCurveTo(x + 13, fy - 5 + k * 4, x + 20, fy - 2 + k * 4); } }
    else { g.arc(x + 13, fy + 3, 5, Math.PI * 1.1, Math.PI * 1.9); }
    g.stroke();
  }
  /* people walking between the places; the game can ask a few of them to gather on the square */
  const WALK = [[[300, 615], [560, 630], [700, 628]], [[880, 630], [1130, 640]], [[800, 520], [795, 600]], [[1080, 470], [900, 615]], [[560, 560], [660, 610]], [[1000, 650], [1010, 700]]];
  const FOLK = Array.from({ length: 11 }, (_, i) => ({ path: WALK[i % WALK.length], k: (i * 0.37) % 1, v: 0.00002 + (i % 4) * 0.000006, dir: i % 2 ? 1 : -1,
    shirt: ["#e85d4a", "#f2b134", "#3aa6a0", "#ffffff", "#e86fa0", "#6fa8ff", "#a3e05a", "#ff9f40", "#c9a0ff", "#ffe066", "#4fd1c5"][i], skin: ["#8d5524", "#c68642", "#e0ac69", "#f1c27d", "#6b3e1f"][i % 5] }));
  const alongPath = (p, k) => {
    const L = []; let tot = 0; for (let i = 1; i < p.length; i++) { const d = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); L.push(d); tot += d; }
    let s = k * tot; for (let i = 0; i < L.length; i++) { if (s <= L[i]) { const f = s / L[i]; return [lerp(p[i][0], p[i + 1][0], f), lerp(p[i][1], p[i + 1][1], f)]; } s -= L[i]; }
    return p[p.length - 1];
  };
  function person(g, x, y, t, f, i) {
    if (painted("folk")) return sprite(g, x, y, t, f, i);
    const step = Math.sin(t * 0.012 + i) * 1.6;
    g.fillStyle = "rgba(34,48,58,.25)"; g.beginPath(); g.ellipse(x + 2, y + 1, 5.5, 1.8, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = INK; g.lineWidth = 2; g.lineCap = "round"; g.beginPath(); g.moveTo(x - 1.5, y - 7); g.lineTo(x - 1.5 + step, y); g.moveTo(x + 1.5, y - 7); g.lineTo(x + 1.5 - step, y); g.stroke();
    g.fillStyle = f.shirt; g.beginPath(); g.moveTo(x - 4.5, y - 6); g.lineTo(x - 3.5, y - 16); g.lineTo(x + 3.5, y - 16); g.lineTo(x + 4.5, y - 6); g.closePath(); g.fill(); g.lineWidth = 1.1; g.stroke();
    g.fillStyle = f.skin; g.beginPath(); g.arc(x, y - 19.5, 3.4, 0, Math.PI * 2); g.fill(); g.stroke();
    if (i % 3 === 0) { g.fillStyle = P.mustard; g.beginPath(); g.ellipse(x, y - 22, 5.5, 1.6, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.arc(x, y - 22.5, 2.6, Math.PI, 0); g.fill(); g.stroke(); }
  }
  /* a painted islander from the strip: cut out like a paper puppet, rocking on its feet and bobbing as it walks,
     turned the way it goes, with a soft shadow under it */
  function sprite(g, x, y, t, f, i) {
    const im = ART.img.folk, CW = 80, CH = 120, n = Math.max(1, Math.floor(im.naturalWidth / CW)), h = 30, w = h * CW / CH;
    const a = alongPath(f.path, Math.min(1, f.k + 0.01)), b = alongPath(f.path, Math.max(0, f.k - 0.01)), face = (a[0] - b[0]) * f.dir < 0 ? -1 : 1;
    const ph = t * 0.011 + i * 1.7, go = S.still || S.gather > 0.5 ? 0 : 1, bob = Math.abs(Math.sin(ph)) * 1.4 * go, rock = Math.sin(ph) * 0.06 * go;
    g.fillStyle = "rgba(20,34,40,.28)"; g.beginPath(); g.ellipse(x, y + 0.5, w * 0.32, 2.2, 0, 0, Math.PI * 2); g.fill();
    g.save(); g.translate(x, y - bob); g.rotate(rock); g.scale(face, 1);
    g.drawImage(im, (i % n) * CW, 0, CW, CH, -w / 2, -h, w, h); g.restore();
  }
  function boat(g, x, y, t) {
    const b = Math.sin(t * 0.0018) * 2, r = Math.sin(t * 0.0013) * 0.04;
    g.save(); g.translate(x, y + b); g.rotate(r); g.strokeStyle = INK; g.lineJoin = "round"; g.lineWidth = 1.6;
    g.fillStyle = "rgba(20,50,70,.3)"; g.beginPath(); g.ellipse(4, 7, 42, 5, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = P.cream; g.beginPath(); g.moveTo(-38, -4); g.lineTo(38, -4); g.lineTo(28, 8); g.lineTo(-30, 8); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = P.coral; g.fillRect(-34, 0, 66, 3.5);
    g.lineWidth = 2; g.beginPath(); g.moveTo(0, -4); g.lineTo(0, -54); g.stroke(); g.lineWidth = 1.4;
    g.fillStyle = P.cream; g.beginPath(); g.moveTo(2, -52); g.quadraticCurveTo(26 + Math.sin(t * 0.002) * 3, -30, 30, -8); g.lineTo(2, -8); g.closePath(); g.fill(); g.stroke();
    g.save(); g.clip(); for (let k = 0; k < 4; k++) { g.fillStyle = k % 2 ? P.cream : P.teal; g.fillRect(2, -52 + k * 11, 30, 5.5); } g.restore();
    g.fillStyle = P.mustard; g.beginPath(); g.moveTo(-2, -48); g.quadraticCurveTo(-18, -30, -20, -8); g.lineTo(-2, -8); g.closePath(); g.fill(); g.stroke();
    g.restore();
  }
  /* a cruise ship at anchor off the island (relay cruise.py): drawn here until the art pipeline paints one. It comes in
     from the east before it lands, its tenders ferry the simulated passengers to the pier and back, a guide's pennant
     stands at each place where a group is, and a ring rises from a place whenever one of their transactions is sealed */
  const SHIP = { s: null, pings: [] };
  const SHIPS = {
    liner: { L: 186, hull: P.navy, band: P.cream, funnel: P.coral, decks: [0.8, 0.64, 0.44], tall: 9 },
    expedition: { L: 128, hull: "#2f5468", band: "#e9ecea", funnel: P.teal, decks: [0.58, 0.42], tall: 9, crane: true },
    pirate: { L: 128, hull: "#1f2428", band: "#3a3f45", funnel: "#15181b", decks: [0.5, 0.36], tall: 8 },
  };
  /* the pirates' Black Sequence: its own painting (pirate.webp) once there is one; until then MS Dry Run's, darkened
     like tarred wood, with no smoke and a black flag of three white chain links on its mast */
  const shipKind = v => v.style === "liner" ? "liner" : v.style === "pirate" ? (BOATS.pirate ? "pirate" : "pirateStandIn") : "expedition";
  function standIn(m) {
    const c = document.createElement("canvas"); c.width = m.im.naturalWidth; c.height = m.im.naturalHeight;
    const x = c.getContext("2d"); x.filter = "brightness(0.42) saturate(0.45) contrast(1.15)"; x.drawImage(m.im, 0, 0);
    const { funnel, ...rest } = m;
    BOATS.pirateStandIn = { ...rest, im: c, flag: funnel };
  }
  function blackFlag(g, x, y, k, t) {   // pole up from (x, y), in the sprite's own pixels (k: pixels per world unit)
    const h = 15 * k, w = 13 * k, f = 8 * k, wave = Math.sin(t * 0.006) * k;
    g.strokeStyle = INK; g.lineWidth = 1.2 * k; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - h - f); g.stroke();
    g.fillStyle = "#121416"; g.beginPath(); g.moveTo(x, y - h - f); g.quadraticCurveTo(x + w / 2, y - h - f - wave, x + w, y - h - f + wave);
    g.lineTo(x + w, y - h + wave); g.quadraticCurveTo(x + w / 2, y - h - wave, x, y - h); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = "#f2efe6"; g.lineWidth = 0.9 * k;
    for (let i = 0; i < 3; i++) { g.beginPath(); g.ellipse(x + w * (0.26 + i * 0.24), y - h - f / 2 + wave * 0.3, 2.1 * k, 1.3 * k, 0, 0, Math.PI * 2); g.stroke(); }
  }
  /* Painted boats share a single waterline transform, including the dusk pass. A missing
     asset leaves the original drawing below in charge until that particular image loads. */
  const BOATS = {};
  fetch("/rabbit/art/ships/ships.json").then(r => r.ok ? r.json() : {}).then(manifest => {
    for (const kind of ["liner", "expedition", "pirate", "tender", "wake"]) {
      const m = manifest[kind];
      if (!m || typeof m.src !== "string" || !/^[a-z]+\.webp$/.test(m.src)) continue;
      const point = p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite);
      if (kind === "wake" ? !point(m.tip) : !point(m.stern) || !point(m.bow) || !(m.length > 0)) continue;
      if (kind !== "wake" && Math.hypot(m.bow[0] - m.stern[0], m.bow[1] - m.stern[1]) < 1) continue;
      const im = new Image(); im.decoding = "async";
      im.onload = () => { BOATS[kind] = { ...m, im }; if (kind === "expedition") standIn(BOATS[kind]); };
      im.src = "/rabbit/art/ships/" + m.src;
    }
  }).catch(() => {});
  const boatArt = kind => S.base?.painted && !/[?&]art=drawn(?:&|$)/.test(location.search) && BOATS[kind];
  /* The crew of the Black Sequence (rabbit/art/ships/crew-pirate.*, cut and laid out from the painted pirates by
     infra/rabbit-art/tourists.py --set pirates): the pirates never land, so they stand on their ship, one at each "deck"
     point of her manifest and the captain at "captain", in the painting's own pixels, so they bob, turn and mirror with
     her; now and then one makes their small gesture (the figure's second frame), as the passengers ashore do. Without
     the sheet she sails with nobody on deck. */
  const CREW = {};
  fetch("/rabbit/art/ships/crew-pirate.json").then(r => r.ok ? r.json() : null).then(m => {
    if (!crowdOk(m)) return;
    const im = new Image(); im.decoding = "async";
    im.onload = () => { CREW.pirate = { m, im }; };
    im.src = "/rabbit/art/ships/" + m.src;
  }).catch(() => {});
  function crew(g, m, scale, t) {
    const c = CREW[m.crew || "pirate"], deck = Array.isArray(m.deck) ? m.deck.filter(p => Array.isArray(p) && p.length === 2) : [];
    if (!c || !deck.length) return;
    const cm = c.m, [cw, ch] = cm.cell, k = 1 / scale / cm.unit, F = cm.figures, cap = cm.guides && cm.guides[m.crew || "pirate"];
    const who = deck.map((p, i) => [p, F[i % F.length], i]);
    if (cap && Array.isArray(m.captain) && m.captain.length === 2) who.push([m.captain, cap, "captain"]);
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
    for (const [[x, y], f, i] of who.sort((a, b) => a[0][1] - b[0][1])) {
      const fr = gesture("crew", i, t) ? f.b : f.a, sw = (f.sw > 0 ? f.sw : 3) / scale;
      g.fillStyle = "rgba(20,34,40,.24)"; g.beginPath(); g.ellipse(x + sw * 0.15, y, sw, sw * 0.34, 0, 0, Math.PI * 2); g.fill();
      g.drawImage(c.im, (fr % cm.cols) * cw, Math.floor(fr / cm.cols) * ch, cw, ch, x - f.foot[0] * k, y - f.foot[1] * k, cw * k, ch * k);
    }
  }
  const unit = f => Math.max(0, Math.min(1, f));
  function boatPose(x, y, t, a = 1) {
    const v = SHIP.s, now = Date.now() / 1000, underway = v.phase === "approach" || v.phase === "gone";
    const turn = v.phase === "gone" ? 1 : v.phase === "approach" ? 0 : ease(unit(1 - (v.end - now) / 90));
    const heading = -Math.cos(turn * Math.PI);
    // At the bow-on moment blend the two narrow views, rather than jumping their sign.
    const right = ease(unit((heading + 0.12) / 0.24));
    const progress = v.phase === "approach" ? unit(1 - (v.t0 - now) / 1800) : unit((now - v.end) / 240);
    const speed = underway ? 4 * progress * (1 - progress) : 0;
    return { x: x + (underway ? 0 : Math.sin(t * 0.00016) * 1.5),
      y: y + Math.sin(t * 0.0012) * 1.2, roll: Math.sin(t * 0.0007) * Math.PI / 300,
      squash: Math.max(0.25, Math.abs(heading)), right, a, speed };
  }
  function boatTransform(g, m, p, draw) {
    const dx = m.bow[0] - m.stern[0], dy = m.bow[1] - m.stern[1], scale = m.length / Math.hypot(dx, dy);
    const cx = (m.bow[0] + m.stern[0]) / 2, cy = (m.bow[1] + m.stern[1]) / 2;
    for (const [dir, weight] of [[-1, 1 - p.right], [1, p.right]]) {
      if (weight <= 0) continue;
      g.save(); g.globalAlpha *= p.a * weight; g.translate(p.x, p.y); g.rotate(p.roll);
      g.scale(dir * p.squash, 1);
      draw(scale, () => { g.scale(scale, scale); g.rotate(-Math.atan2(dy, dx)); g.translate(-cx, -cy); });
      g.restore();
    }
  }
  function boatWake(g, length, amount, t) {
    const wake = BOATS.wake;
    if (!wake || amount <= 0) return;
    const scale = length * 0.78 / wake.im.naturalWidth;
    g.save(); g.globalAlpha *= amount * (0.85 + 0.15 * Math.sin(t * 0.002));
    g.translate(-length / 2, 0); g.scale(scale, scale);
    g.drawImage(wake.im, -wake.tip[0], -wake.tip[1]); g.restore();
  }
  function paintedBoat(g, x, y, t, kind, a) {
    const m = boatArt(kind); if (!m) return false;
    const p = boatPose(x, y, t, a);
    g.save(); g.globalAlpha *= a; g.fillStyle = "rgba(10,30,45,.22)";
    g.beginPath(); g.ellipse(p.x + 4, p.y + 4, m.length * 0.56 * p.squash, 7, p.roll, 0, Math.PI * 2); g.fill(); g.restore();
    boatTransform(g, m, p, (scale, pixels) => {
      boatWake(g, m.length, p.speed * 0.7, t);
      // The narrow waterline foam is already painted into the hull; a faint pulse keeps it alive at anchor.
      if (p.speed < 0.1) {
        g.strokeStyle = `rgba(235,255,255,${0.07 + 0.035 * Math.sin(t * 0.0009)})`; g.lineWidth = 1.1;
        g.beginPath(); g.ellipse(0, 1, m.length * 0.48, 2, 0, 0, Math.PI * 2); g.stroke();
      }
      pixels(); g.drawImage(m.im, 0, 0);
      if (m.flag) blackFlag(g, m.flag[0], m.flag[1], 1 / scale, t);
      crew(g, m, scale, t);
      if (m.funnel) {
        const [fx, fy] = m.funnel;
        for (let k = 0; k < 4; k++) {
          const f = (t * 0.00012 + k / 4) % 1;
          g.fillStyle = `rgba(236,236,240,${0.32 * (1 - f)})`; g.beginPath();
          g.arc(fx - f * 46 / scale, fy - f * 20 / scale, (4 + f * 9) / scale, 0, Math.PI * 2); g.fill();
        }
      }
    });
    return true;
  }
  function paintedTender(g, x, y, t, dir) {
    const m = boatArt("tender"); if (!m) return false;
    const p = { x, y: y + Math.sin(t * 0.004 + x) * 0.8, roll: Math.sin(t * 0.002 + x) * 0.01, squash: 1, right: dir > 0 ? 1 : 0, a: 1 };
    boatTransform(g, m, p, (scale, pixels) => { boatWake(g, m.length, 0.45, t); pixels(); g.drawImage(m.im, 0, 0); });
    return true;
  }
  function shipWindows(g, t, light) {
    const pos = shipPos(Date.now() / 1000); if (!pos) return;
    const m = boatArt(shipKind(SHIP.s));
    if (!m || !m.windows) return;
    boatTransform(g, m, boatPose(pos[0], pos[1], t, pos[2]), (scale, pixels) => {
      pixels();
      for (const [x0, x1, y] of m.windows) {
        for (let x = x0; x <= x1; x += 5 / scale) {
          g.fillStyle = `rgba(255,190,90,${light * 0.65})`; g.fillRect(x, y - 0.7 / scale, 1.7 / scale, 1.4 / scale);
          g.fillStyle = `rgba(255,170,70,${light * 0.045})`; g.beginPath(); g.arc(x, y, 3 / scale, 0, Math.PI * 2); g.fill();
        }
      }
    });
  }

  const ease = f => f * f * (3 - 2 * f);
  function shipPos(now) {
    const v = SHIP.s, [ax, ay] = SPOT.anchor;
    if (!v) return null;
    if (v.phase === "approach") { const f = Math.max(0, Math.min(1, 1 - (v.t0 - now) / 1800)); return [ax + 430 * (1 - ease(f)), ay, Math.min(1, f * 5)]; }
    if (v.phase === "gone") { const f = Math.max(0, Math.min(1, (now - v.end) / 240)); return f >= 1 ? null : [ax + 430 * ease(f), ay, 1 - Math.max(0, f - 0.8) * 5]; }
    return [ax, ay, 1];
  }
  function cruiseShip(g, x, y, t, kind, light, a) {
    if (paintedBoat(g, x, y, t, kind, a)) return;
    const D = SHIPS[kind] || SHIPS[/^pirate/.test(kind) ? "pirate" : "liner"], L = D.L, bob = Math.sin(t * 0.0012) * 1.2, hh = 15;
    g.save(); g.globalAlpha = a; g.translate(x, y + bob); g.lineJoin = "round"; g.strokeStyle = INK; g.lineWidth = 1.5;
    g.fillStyle = "rgba(10,30,45,.28)"; g.beginPath(); g.ellipse(4, 4, L * 0.56, 7, 0, 0, Math.PI * 2); g.fill();   // its shadow on the water
    /* the hull: a long low body, the bow raised to the right */
    g.fillStyle = D.hull; g.beginPath(); g.moveTo(-L / 2, -hh); g.lineTo(L / 2 - 6, -hh); g.quadraticCurveTo(L / 2 + 8, -hh - 3, L / 2 + 10, -hh - 6);
    g.lineTo(L / 2 - 4, 0); g.lineTo(-L / 2 + 8, 0); g.quadraticCurveTo(-L / 2 - 2, -2, -L / 2, -hh); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = D.band; g.fillRect(-L / 2 + 2, -hh + 1, L - 10, 5);
    g.fillStyle = P.coral; g.fillRect(-L / 2 + 7, -3, L - 14, 2.2);
    /* the decks, stepping up and back; their windows light up after dusk */
    let top = -hh;
    D.decks.forEach((w, i) => {
      const dw = L * w, x0 = -L / 2 + (D.crane ? L * 0.34 : L * 0.12) + (L * D.decks[0] - dw) * (D.crane ? 0.1 : 0.55), h = D.tall - i;
      g.fillStyle = D.band; g.beginPath(); g.rect(x0, top - h, dw, h); g.fill(); g.stroke();
      const n = Math.floor(dw / 6);
      for (let k = 0; k < n; k++) {
        const lit = light > 0.05 && ((k * 7 + i * 3) % 5) !== 0;
        g.fillStyle = lit ? `rgba(255,200,110,${0.55 + 0.45 * light})` : "rgba(34,48,58,.55)";
        g.fillRect(x0 + 2 + k * 6, top - h + 2.4, 3, 2.6);
      }
      if (i === 0) for (let k = 0; k < 5; k++) { g.fillStyle = P.mustard; g.beginPath(); g.ellipse(x0 + dw * (0.16 + k * 0.17), top - 1.2, 4.2, 1.6, 0, 0, Math.PI * 2); g.fill(); }   // the lifeboats
      top -= h;
    });
    /* the funnel, with smoke drifting off it, and the mast at the bow */
    const fx = D.crane ? -L / 2 + L * 0.5 : -L * 0.04;
    g.fillStyle = D.funnel; g.beginPath(); g.moveTo(fx - 7, top); g.lineTo(fx - 5, top - 17); g.lineTo(fx + 8, top - 17); g.lineTo(fx + 8, top); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = INK; g.fillRect(fx - 5, top - 17, 13, 3);
    for (let k = 0; k < 4; k++) { const f = ((t * 0.00012 + k / 4) % 1); g.fillStyle = `rgba(236,236,240,${0.32 * (1 - f)})`; g.beginPath(); g.arc(fx + 2 - f * 46, top - 22 - f * 20, 4 + f * 9, 0, Math.PI * 2); g.fill(); }
    g.lineWidth = 1.2; g.beginPath(); g.moveTo(L / 2 - 26, -hh); g.lineTo(L / 2 - 26, -hh - 30); g.stroke();
    g.fillStyle = D.funnel; g.beginPath(); g.moveTo(L / 2 - 26, -hh - 30); g.lineTo(L / 2 - 14, -hh - 27 + Math.sin(t * 0.006) * 1.2); g.lineTo(L / 2 - 26, -hh - 24); g.closePath(); g.fill();
    if (D.crane) { g.strokeStyle = P.mustard; g.lineWidth = 2.2; g.beginPath(); g.moveTo(-L / 2 + 18, -hh); g.lineTo(-L / 2 + 18, -hh - 22); g.lineTo(-L / 2 + 40, -hh - 14); g.stroke(); }
    if (light > 0.05) { g.fillStyle = `rgba(255,90,70,${light})`; g.beginPath(); g.arc(L / 2 - 26, -hh - 31, 1.8, 0, Math.PI * 2); g.fill(); }
    g.restore();
  }
  /* a tender: a small white boat with an orange canopy and a short wake */
  function tender(g, x, y, t, dir) {
    if (paintedTender(g, x, y, t, dir)) return;
    g.save(); g.translate(x, y + Math.sin(t * 0.004 + x) * 0.8); g.scale(dir, 1); g.strokeStyle = INK; g.lineWidth = 1.1;
    g.strokeStyle = "rgba(255,255,255,.55)"; g.beginPath(); g.moveTo(-9, 2); g.lineTo(-26, 4); g.moveTo(-9, 0); g.lineTo(-22, -2); g.stroke();
    g.strokeStyle = INK; g.fillStyle = P.cream; g.beginPath(); g.moveTo(-9, -3); g.lineTo(9, -3); g.lineTo(7, 2); g.lineTo(-8, 2); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = P.coral; g.fillRect(-6, -7, 9, 4);
    g.restore();
  }
  /* where the tenders are: two shuttles while passengers land or board, one slower one while they are ashore */
  function tenders(now, x0, y0) {
    const v = SHIP.s, pier = PLACES.pier || {}, [px, py] = pier.c ? [pier.c[0] + 30, pier.c[1] + 40] : [(pier.x || 1010) + 50, (pier.y || 735) + 38];
    if (!v || !["landing", "ashore", "boarding"].includes(v.phase)) return [];
    const busy = v.phase !== "ashore", out = [];
    for (let i = 0; i < (busy ? 2 : 1); i++) {
      const per = busy ? 100 : 240, f = ((now + i * per / 2) % per) / per;   // there 40 %, wait at the pier, back 40 %, wait at the ship
      let k = f < 0.4 ? f / 0.4 : f < 0.5 ? 1 : f < 0.9 ? 1 - (f - 0.5) / 0.4 : 0;
      k = ease(k);
      out.push([lerp(x0 - 70, px, k), lerp(y0 + 6, py, k) + Math.sin(k * Math.PI) * 10, f < 0.5 ? -1 : 1]);
    }
    return out;
  }
  /* a guide's pennant where a group of passengers is */
  function pennant(g, x, y, t, col) {
    const w = Math.sin(t * 0.005 + x) * 1.5;
    g.strokeStyle = INK; g.lineWidth = 1.3; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 24); g.stroke();
    g.fillStyle = col; g.beginPath(); g.moveTo(x, y - 24); g.lineTo(x + 12, y - 21 + w); g.lineTo(x, y - 17); g.closePath(); g.fill(); g.stroke();
  }
  const placePt = id => { const p = PLACES[id]; return !p ? null : p.c ? [p.c[0], p.c[1]] : [p.x, p.y - 18]; };
  /* The passengers ashore, painted (rabbit/art/tourists: one sheet and its manifest, scaled and laid out from the
     painted figures by infra/rabbit-art/tourists.py, both frames of a figure from their whole canvases alike, so they
     line up to the pixel). Where the relay counts passengers (v.at), a group stands on the layout's ground for that
     place (stand: its first point is where the guide stands, the others are the corners of the ground the group may
     use), one figure for each passenger as far as the ground holds them, filled from the guide outwards and the same
     for the whole visit. They face their guide, from behind or from the front or in profile as she stands to them, and
     now and then one of them makes their small gesture (each figure's second frame, swapped in whole: no cross-fade);
     nobody walks. Those who come appear one by one, those who go on leave one by one; on the pier they wait for the
     tenders. A grown-up is 16 world units tall, as the painting measures (loungers, doors and umbrellas: about 8.5
     units to the metre); layout "crowd" scales them. What stands in front of the ground (layout "over": a railing,
     a bollard, a post, each a polygon with the depth d it stands at) is painted again over the figures behind it, so
     feet behind a railing stay hidden. Without the art (or with ?art=drawn), and at a place without ground, the
     guide's pennant shows as before. */
  const CROWD = { at: {}, cast: {}, slots: {}, t: 0 }, CROWD_STEP = 900;   // ms between two passengers coming or going
  fetch("/rabbit/art/tourists/tourists.json").then(r => r.ok ? r.json() : null).then(m => {
    if (!crowdOk(m)) return;
    const im = new Image(); im.decoding = "async";
    im.onload = () => { CROWD.m = m; CROWD.im = im; };   // one picture holds both frames of everyone: nothing to load later
    im.src = "/rabbit/art/tourists/" + m.src;
  }).catch(() => {});
  function crowdOk(m) {
    const num = v => Array.isArray(v) && v.every(Number.isFinite);
    const fig = f => !!f && Number.isInteger(f.a) && Number.isInteger(f.b) && num(f.foot) && f.foot.length === 2
      && (f.contacts === undefined || Array.isArray(f.contacts) && f.contacts.every(c => num(c) && c.length === 3));
    return !!m && typeof m.src === "string" && /^[a-z0-9-]+\.webp$/.test(m.src) && m.unit > 0 && Number.isInteger(m.cols) && m.cols > 0
      && Array.isArray(m.cell) && m.cell.length === 2 && m.cell.every(v => v > 0) && Array.isArray(m.figures) && m.figures.length > 0
      && m.figures.every(f => fig(f) && /^(back|front|side)$/.test(f.view) && (f.face === 1 || f.face === -1)) && Object.values(m.guides || {}).every(fig);
  }
  const crowdArt = () => !!CROWD.im && !!S.base?.painted && !/[?&]art=drawn(?:&|$)/.test(location.search);
  const h01 = (...v) => { let h = 2166136261; for (const ch of v.join("|")) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return (h >>> 0) / 4294967296; };
  /* where a group stands: a loose, slightly uneven lattice on the place's ground (people about 7 units apart, 4 deep
     on the screen), nearest the guide first, at most 40 (inPoly: further down, with the click areas) */
  function standSlots(id) {
    const st = SPOT.stand && SPOT.stand[id], c = CROWD.slots[id];
    if (c && c.st === st) return c.s;
    let s = null;
    if (Array.isArray(st) && st.length >= 4 && st.every(p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite))) {
      const [[gx, gy], ...P] = st, xs = P.map(p => p[0]), ys = P.map(p => p[1]);
      s = [];
      for (let y = Math.min(...ys) + 1.5, r = 0; y < Math.max(...ys); y += 3.9, r++)
        for (let x = Math.min(...xs) + 1.5 + (r % 2) * 3.6; x < Math.max(...xs); x += 7.2) {
          const px = x + (h01(id, x, y, "x") - 0.5) * 3.2, py = y + (h01(id, x, y, "y") - 0.5) * 1.8, d = Math.hypot(px - gx, (py - gy) * 1.7);
          if (d > 5 && inPoly(P, px, py)) s.push([px, py, d + h01(id, x, y, "d") * 3]);
        }
      s = s.sort((p, q) => p[2] - q[2]).slice(0, 40);
    }
    CROWD.slots[id] = { st, s };
    return s;
  }
  /* who stands where, for the whole visit: no one twice in a group while there are figures left, each turned towards
     the guide (from behind when she stands beyond them, from the front when she is nearer to us, else in profile) */
  function crowdCast(id, visit, slots) {
    const c = CROWD.cast[id];
    if (c && c.slots === slots) return c.c;
    const F = CROWD.m.figures, [gx, gy] = SPOT.stand[id][0], out = [];
    let left = [];
    slots.forEach(([x, y], i) => {
      if (!left.length) left = F.map((f, k) => [f, h01(visit, id, i, k)]).sort((p, q) => p[1] - q[1]).map(p => p[0]);
      const dx = gx - x, dy = gy - y, face = Math.abs(dx) < 2 ? (h01(visit, id, i) < 0.5 ? -1 : 1) : Math.sign(dx), view = dy < -3 ? "back" : dy > 3 ? "front" : "side";
      let best = 0, top = -1;
      left.forEach((f, k) => { const s = (f.face === face ? 2 : 0) + (f.view === view ? 1 : 0); if (s > top) { top = s; best = k; } });
      out.push(left.splice(best, 1)[0]);
    });
    CROWD.cast[id] = { slots, c: out };
    return out;
  }
  /* now and then a small gesture, each figure on its own: its time runs in stretches of its own length (6 to 15 s), in
     about two of three it gestures once, at a moment of its own, for 1.2 to 3 s, and rests at least 1.6 s between two:
     never all at once, never a flicker; with reduced motion nobody gestures */
  function gesture(id, i, t) {
    if (S.still) return false;
    const L = 6000 + h01(id, i, "L") * 9000, u = t + h01(i, id, "o") * L, n = Math.floor(u / L);
    if (h01(id, i, n, "go") > 0.65) return false;
    const d = 1200 + h01(id, i, n, "d") * 1800, s = 800 + h01(id, i, n, "s") * (L - d - 1600), w = u - n * L;
    return w >= s && w < s + d;
  }
  /* one figure standing at x, y: a faint shadow under it, a darker touch under each foot, wheel or stick that meets the
     ground (the manifest's contacts), a little to the right, as the light comes from the upper left; then the figure */
  function tourist(g, f, x, y, b) {
    const m = CROWD.m, [cw, ch] = m.cell, c = b ? f.b : f.a, sc = SPOT.crowd > 0 ? SPOT.crowd : 1, k = sc / m.unit, [fx, fy] = f.foot;
    const cs = Array.isArray(f.contacts) && f.contacts.length ? f.contacts : [[fx, fy, 3 * m.unit]];
    let x0 = Infinity, x1 = -Infinity, yb = -Infinity;
    for (const [cx, cy, hw] of cs) { x0 = Math.min(x0, cx - hw); x1 = Math.max(x1, cx + hw); yb = Math.max(yb, cy); }
    const rx = (x1 - x0) / 2 * k + 1.6 * sc;
    g.fillStyle = "rgba(20,34,40,.13)"; g.beginPath(); g.ellipse(x + ((x0 + x1) / 2 - fx) * k + 0.6 * sc, y + (yb - fy) * k, rx, rx * 0.3, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(20,34,40,.26)"; g.beginPath();
    for (const [cx, cy, hw] of cs) {
      const r = Math.max(0.8 * sc, hw * k * 1.15), ex = x + (cx - fx) * k + 0.3 * sc, ey = y + (cy - fy) * k;
      g.moveTo(ex + r, ey); g.ellipse(ex, ey, r, Math.max(0.45 * sc, r * 0.36), 0, 0, Math.PI * 2);
    }
    g.fill();
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
    g.drawImage(CROWD.im, (c % m.cols) * cw, Math.floor(c / m.cols) * ch, cw, ch, x - fx * k, y - fy * k, cw * k, ch * k);
  }
  function crowdItems(items, g, t, v, kind) {
    const visit = v.ship + "|" + v.t0, fresh = CROWD.visit !== visit, dt = fresh ? 0 : Math.min(250, Math.max(0, t - CROWD.t)), guide = CROWD.m.guides && CROWD.m.guides[kind];
    if (fresh) { CROWD.visit = visit; CROWD.at = {}; CROWD.cast = {}; }
    CROWD.t = t;
    const here = ["landing", "ashore"].includes(v.phase) ? v.at || {} : {}, landing = v.phase === "landing";
    for (const id of new Set([...Object.keys(here), ...Object.keys(CROWD.at)])) {
      const slots = standSlots(id), want = Math.max(0, Math.floor(+here[id] || 0));
      if (!slots || !slots.length) {   // no ground laid out here: the pennant, as before
        delete CROWD.at[id];
        const pt = placePt(id); if (pt && want > 0 && !(id === "pier" && landing)) items.push([pt[1] + 2, () => pennant(g, pt[0] + 16, pt[1] + 4, t, SHIPS[kind].funnel)]);
        continue;
      }
      const n0 = Math.min(slots.length, want), st = CROWD.at[id] || (CROWD.at[id] = { n: fresh || S.still ? n0 : 0 });
      st.n = S.still ? n0 : st.n + Math.sign(n0 - st.n) * Math.min(Math.abs(n0 - st.n), dt / CROWD_STEP);
      const shown = Math.min(slots.length, Math.floor(st.n + 1e-6));   // whole figures only: nobody is half there
      if (!shown) { if (!n0) delete CROWD.at[id]; continue; }
      const cast = crowdCast(id, visit, slots), [gx, gy] = SPOT.stand[id][0];
      for (let i = 0; i < shown; i++) {
        const [x, y] = slots[i], f = cast[i];
        items.push([y, () => tourist(g, f, x, y, gesture(id, i, t))]);
      }
      for (const o of overs(id)) items.push([o.d, () => over(g, o.p)]);
      if (id === "pier" && landing) continue;   // off the tenders: their guides wait at the places
      items.push([gy, guide ? () => tourist(g, guide, gx, gy, gesture(id, "guide", t)) : () => pennant(g, gx + 2, gy, t, SHIPS[kind].funnel)]);
    }
  }
  /* what the painting has in front of a place's ground (layout "over": [{d, p}]): drawn again, from the painting, at
     its own depth, so the figures behind it stay behind it and those in front of it stay in front */
  const overs = id => (Array.isArray(SPOT.over && SPOT.over[id]) ? SPOT.over[id] : []).filter(o => o && Number.isFinite(o.d)
    && Array.isArray(o.p) && o.p.length >= 3 && o.p.every(q => Array.isArray(q) && q.length === 2 && q.every(Number.isFinite)));
  function over(g, p) {
    g.save(); g.beginPath(); p.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.clip();
    g.drawImage(S.base, -S.base.e, 0, WW + 2 * S.base.e, WH); g.restore();
  }
  function shipItems(items, g, t, sky) {
    const now = Date.now() / 1000, pos = shipPos(now), v = SHIP.s;
    if (!pos) return;
    const [x, y, a] = pos, art = shipKind(v), kind = art === "liner" || art === "expedition" ? art : "pirate";
    items.push([y, () => cruiseShip(g, x, y, t, art, sky.light, a)]);
    tenders(now, x, y).forEach(([tx, ty, d]) => items.push([ty, () => tender(g, tx, ty, t, d)]));
    if (crowdArt()) return crowdItems(items, g, t, v, kind);
    if (["landing", "ashore"].includes(v.phase)) for (const id in v.at || {}) {
      const pt = placePt(id); if (!pt || !(v.at[id] > 0) || id === "pier" && v.phase === "landing") continue;
      items.push([pt[1] + 2, () => pennant(g, pt[0] + 16, pt[1] + 4, t, SHIPS[kind].funnel)]);
    }
  }
  function shipPings(g, t) {
    SHIP.pings = SHIP.pings.filter(p => t - p.t0 < 1800);
    for (const p of SHIP.pings) {
      const pt = placePt(p.id); if (!pt) continue;
      const f = Math.max(0, (t - p.t0) / 1800), r = 7 + 30 * ease(f);
      g.strokeStyle = `rgba(255,255,240,${0.9 * (1 - f)})`; g.lineWidth = 2.2; g.beginPath(); g.ellipse(pt[0], pt[1], r, r * 0.42, 0, 0, Math.PI * 2); g.stroke();
    }
  }
  /* clouds: flat cut-paper shapes with a shaded underside and an ink edge */
  function cloud(g, x, y, s, a) {
    const B = [[0, 0, 26], [24, -10, 22], [48, -2, 24], [-20, 6, 18], [68, 6, 16]];
    g.save(); g.globalAlpha = Math.min(1, a * 1.6);
    g.beginPath(); B.forEach(([dx, dy, r]) => { g.moveTo(x + (dx + r) * s, y + dy * s); g.arc(x + dx * s, y + dy * s, r * s, 0, Math.PI * 2); });
    g.rect(x - 38 * s, y + 6 * s, 122 * s, 16 * s);
    g.fillStyle = P.cream; g.fill();
    g.save(); g.clip(); g.fillStyle = "rgba(240,190,160,.55)"; g.fillRect(x - 40 * s, y + 8 * s, 130 * s, 20 * s); g.restore();
    g.restore();
  }
  function gull(g, x, y, t, i) {
    const f = Math.sin(t * 0.008 + i) * 4;
    g.strokeStyle = "rgba(40,40,50,.7)"; g.lineWidth = 1.4; g.beginPath(); g.moveTo(x - 7, y - f * 0.4); g.quadraticCurveTo(x - 3, y - 3 - f * 0.2, x, y); g.quadraticCurveTo(x + 3, y - 3 - f * 0.2, x + 7, y - f * 0.4); g.stroke();
  }
  /* Déjà, the café's black cat, now and then strolls along the beach (and, once, twice) */
  function cat(g, x, y, t, dir) {
    const s = Math.sin(t * 0.02) * 1.5;
    g.save(); g.translate(x, y); g.scale(dir, 1);
    g.fillStyle = "rgba(0,0,0,.25)"; g.beginPath(); g.ellipse(0, 1, 9, 2, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#111114";
    g.beginPath(); g.ellipse(0, -6, 8, 4, 0, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.arc(8, -10, 3.6, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.moveTo(6, -13); g.lineTo(7, -17); g.lineTo(9, -13.5); g.fill(); g.beginPath(); g.moveTo(9, -13); g.lineTo(11, -16.5); g.lineTo(11.5, -12); g.fill();
    g.strokeStyle = "#111114"; g.lineWidth = 1.6; g.beginPath(); g.moveTo(-6, -3); g.lineTo(-6 + s, 0); g.moveTo(-2, -3); g.lineTo(-2 - s, 0); g.moveTo(3, -3); g.lineTo(3 + s, 0); g.moveTo(6, -3); g.lineTo(6 - s, 0); g.stroke();
    g.beginPath(); g.moveTo(-8, -6); g.quadraticCurveTo(-14, -8, -13, -15 + Math.sin(t * 0.006) * 2); g.stroke();
    g.fillStyle = "#39ff8a"; g.fillRect(8.5, -11, 1.3, 1);
    g.restore();
  }

  /* the painted creatures (paint.py creatures): Déjà, the café cat, who turns up now and then, sometimes in a room;
     and the legend of the jungle, Agorzilla, seen for a few seconds every few minutes, half hidden in the leaves */
  const FORCE = /[?&]rare=1/.test(location.search);
  const RARE = { zilla: null, next: performance.now() + (FORCE ? 3000 : 60000 + Math.random() * 60000) };
  function creature(g, im, x, y, h, a = 1) {   // standing on (x, y), h world units tall
    const w = h * im.naturalWidth / im.naturalHeight; g.save(); g.globalAlpha *= a; g.drawImage(im, x - w / 2, y - h, w, h); g.restore();
    return [x - w / 2, y - h, w, h];
  }
  /* the leaves in front: one painted cluster, at the left edge and mirrored at the right, as tall as the screen and wide
     enough to cover the side beside the island on a wide screen; they sway in the breeze and lean from the pointer.
     On a screen held upright, as tall as the screen would make them wider than the screen itself and hide the island:
     there they are a small tuft in each bottom corner, a hint of jungle in front, no more */
  function fronds(g, t, a) {
    const im = ART.img.fronds, W = S.c.width, H = S.c.height, r = im.naturalHeight / im.naturalWidth;
    const e = ART.wide || 0, margin = Math.max(0, toScreen(-e, 0)[0] * S.K);
    let w = Math.max(margin + W * 0.07, W * 0.13), h = w * r;
    if (H > W) { w = Math.min(W * 0.36, H * 0.24 / r); h = w * r; }
    else if (h < H * 1.04) { h = H * 1.04; w = h / r; }
    g.save(); g.globalAlpha = a; g.imageSmoothingQuality = "high";
    [[1, 0], [-1, W]].forEach(([d, x0], i) => {
      const sw = (S.still ? 0 : Math.sin(t * 0.0006 + i * 2.1) * 0.012) - d * (S.peek || 0) * 0.01;
      g.setTransform(d, 0, 0, 1, x0, 0); g.translate(0, H); g.rotate(sw); g.drawImage(im, -w * 0.04, -h, w, h);
    });
    g.restore(); g.setTransform(1, 0, 0, 1, 0, 0);
  }

  /* the white rabbit: hops from place to place, sits up and twitches its ears; it shows newcomers where to go */
  const RB = { x: 860, y: 690, tx: 860, ty: 690, hop: 0, dir: 1, next: 0 };
  /* the lighthouse lamp, the radio mast's light, where people gather, where the cat walks and where a cruise ship anchors:
     a new layout moves them. The anchor sits high enough that the hull stays clear of the radio bar on a small laptop (1280×720) */
  const SPOT = { beam: [300, 445], blink: [1112, 299], gather: [790, 640], cat: [370, 700, 1180, 712], anchor: [1395, 780], stand: {}, over: {}, crowd: 1,
    jungle: [[760, 235], [985, 205], [455, 440], [1180, 560], [330, 285]] };   // where the legend may look out of the leaves
  function rabbitStep(dt, t) {
    const d = Math.hypot(RB.tx - RB.x, RB.ty - RB.y);
    if (d > 2) { RB.hop += dt * 0.012; const v = Math.min(d, dt * 0.11); RB.x += (RB.tx - RB.x) / d * v; RB.y += (RB.ty - RB.y) / d * v; RB.dir = RB.tx > RB.x ? 1 : -1; }
    else { RB.hop = 0; if (t > RB.next && !RB.goal) { RB.next = t + 5000 + Math.random() * 7000; RB.tx = RB.x + (Math.random() - 0.5) * 40; RB.ty = RB.y + (Math.random() - 0.5) * 10; } }
  }
  function rabbit(g, t) {
    const up = RB.hop ? Math.abs(Math.sin(RB.hop * Math.PI)) * 7 : 0, x = RB.x, y = RB.y - up, ear = Math.sin(t * 0.004) > 0.96 ? 0.35 : 0;
    g.fillStyle = "rgba(0,0,0,.22)"; g.beginPath(); g.ellipse(RB.x, RB.y + 1, 8 - up * 0.4, 2.2, 0, 0, Math.PI * 2); g.fill();
    g.save(); g.translate(x, y); g.scale(RB.dir, 1);
    g.fillStyle = "#fbfbf7"; g.beginPath(); g.ellipse(0, -6, 7.5, 6, 0, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.arc(-7, -5, 2.6, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.arc(6, -12, 4.4, 0, Math.PI * 2); g.fill();
    g.save(); g.translate(5, -15); g.rotate(-0.25 - ear); g.beginPath(); g.ellipse(0, -6, 1.8, 6, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = "#f3b8c0"; g.beginPath(); g.ellipse(0, -6, 0.8, 4.5, 0, 0, Math.PI * 2); g.fill(); g.restore();
    g.save(); g.translate(7.5, -15); g.rotate(0.15); g.beginPath(); g.ellipse(0, -6, 1.8, 6, 0, 0, Math.PI * 2); g.fill(); g.restore();
    g.fillStyle = "#c33"; g.beginPath(); g.arc(8, -12.5, 1, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#f3b8c0"; g.beginPath(); g.arc(10.3, -11, 0.8, 0, Math.PI * 2); g.fill();
    g.restore();
    if (RB.goal) { const a = 0.5 + 0.5 * Math.sin(t * 0.005); g.strokeStyle = `rgba(255,255,255,${0.35 + a * 0.4})`; g.lineWidth = 1.5; g.beginPath(); g.ellipse(RB.x, RB.y, 13 + a * 3, 4.5 + a, 0, 0, Math.PI * 2); g.stroke(); }
  }

  /* ---------- inside the places: a click on a place takes the whole view inside it ----------
     each room is painted once (1600 × 900, same inks as the island); its windows are cut out, so the
     sky and the sea of the hour show through them, and a few things in it move */
  const RW = 1600, RH = 900, RHZ = 430;
  function floorPlanks(g, y0, c0, c1, vx = 800) {
    g.fillStyle = c0; g.fillRect(0, y0, RW, RH - y0);
    g.strokeStyle = c1; g.lineWidth = 2;
    for (let x = -1600; x <= 3200; x += 110) { g.beginPath(); g.moveTo(vx + (x - vx) * 0.18, y0); g.lineTo(x, RH); g.stroke(); }
    for (let k = 1; k < 7; k++) { const y = y0 + (RH - y0) * Math.pow(k / 7, 1.7); g.globalAlpha = 0.5; g.beginPath(); g.moveTo(0, y); g.lineTo(RW, y); g.stroke(); g.globalAlpha = 1; }
    g.beginPath(); g.moveTo(0, y0); g.lineTo(RW, y0); ink(g, 3);
  }
  function tiles(g, y0, a, b, vx = 800) {
    const rows = 9;
    for (let r = 0; r < rows; r++) {
      const f0 = Math.pow(r / rows, 1.6), f1 = Math.pow((r + 1) / rows, 1.6), ya = y0 + (RH - y0) * f0, yb = y0 + (RH - y0) * f1;
      for (let c = -14; c < 14; c++) {
        const xa0 = vx + c * 120 * (0.18 + 0.82 * f0), xa1 = vx + (c + 1) * 120 * (0.18 + 0.82 * f0), xb0 = vx + c * 120 * (0.18 + 0.82 * f1), xb1 = vx + (c + 1) * 120 * (0.18 + 0.82 * f1);
        g.fillStyle = (r + c) % 2 ? a : b; g.beginPath(); g.moveTo(xa0, ya); g.lineTo(xa1, ya); g.lineTo(xb1, yb); g.lineTo(xb0, yb); g.closePath(); g.fill();
      }
    }
    g.beginPath(); g.moveTo(0, y0); g.lineTo(RW, y0); ink(g, 3);
  }
  const cut = (g, f) => { g.save(); g.globalCompositeOperation = "destination-out"; g.fillStyle = "#000"; g.beginPath(); f(); g.fill(); g.restore(); };
  const box = (g, x, y, w, h, c, lw = 3) => { g.fillStyle = c; g.fillRect(x, y, w, h); g.beginPath(); g.rect(x, y, w, h); ink(g, lw); };
  const archPath = (g, x, y, w, h) => { g.moveTo(x, y + h); g.lineTo(x, y + w / 2); g.arc(x + w / 2, y + w / 2, w / 2, Math.PI, 0); g.lineTo(x + w, y + h); g.closePath(); };
  function frameWin(g, x, y, w, h, c = P.cream, arch = false) {
    g.beginPath(); arch ? archPath(g, x, y, w, h) : g.rect(x, y, w, h); g.strokeStyle = c; g.lineWidth = 14; g.stroke(); ink(g, 3);
    g.strokeStyle = c; g.lineWidth = 7; g.beginPath(); g.moveTo(x + w / 2, y + (arch ? 0 : 0)); g.lineTo(x + w / 2, y + h); g.moveTo(x, y + h * 0.55); g.lineTo(x + w, y + h * 0.55); g.stroke();
    box(g, x - 16, y + h, w + 32, 16, c, 2.5);
  }
  function palmLeaves(g, x, y, s, c = "#24513a") {
    g.fillStyle = c; g.strokeStyle = INK; g.lineWidth = 2.5;
    for (let k = 0; k < 7; k++) { const a = -Math.PI * 0.95 + k * 0.32; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a) * 90 * s, y + Math.sin(a) * 60 * s - 30 * s, x + Math.cos(a) * 170 * s, y + Math.sin(a) * 90 * s + 40 * s); g.quadraticCurveTo(x + Math.cos(a) * 80 * s, y + Math.sin(a) * 40 * s, x, y); g.fill(); g.stroke(); }
  }
  function plant(g, x, y, s) {
    box(g, x - 40 * s, y - 70 * s, 80 * s, 70 * s, P.coral, 2.5);
    hatch(g, x, y - 70 * s, x + 40 * s, y, 7, "rgba(34,48,58,.3)", 1.5);
    for (let k = 0; k < 9; k++) { const a = -Math.PI / 2 + (k - 4) * 0.33; g.fillStyle = k % 2 ? P.leaf : P.leafD; g.beginPath(); g.moveTo(x, y - 70 * s); g.quadraticCurveTo(x + Math.cos(a) * 80 * s - 20 * s, y - 70 * s + Math.sin(a) * 120 * s, x + Math.cos(a) * 130 * s, y - 70 * s + Math.sin(a) * 150 * s); g.quadraticCurveTo(x + Math.cos(a) * 70 * s + 20 * s, y - 70 * s + Math.sin(a) * 60 * s, x, y - 70 * s); g.fill(); ink(g, 2); }
  }
  function chair(g, x, y, c, s = 1) {
    box(g, x - 34 * s, y - 150 * s, 68 * s, 120 * s, c, 3);
    hatch(g, x + 10 * s, y - 150 * s, x + 34 * s, y - 30 * s, 6, "rgba(34,48,58,.3)", 1.5);
    box(g, x - 42 * s, y - 40 * s, 84 * s, 18 * s, c, 3);
    g.fillStyle = INK; g.fillRect(x - 36 * s, y - 22 * s, 7 * s, 22 * s); g.fillRect(x + 29 * s, y - 22 * s, 7 * s, 22 * s);
  }
  const ROOMS = {
    hall(g, R) {
      g.fillStyle = P.cream; g.fillRect(0, 0, RW, 620);
      dots(g, 0, 0, RW, 620, 9, 2.2, "rgba(201,170,120,.35)", "y");
      g.fillStyle = P.teal; g.beginPath(); g.ellipse(800, 0, 900, 190, 0, 0, Math.PI); g.fill(); ink(g, 3);
      for (let k = -4; k <= 4; k++) { g.beginPath(); g.moveTo(800, -40); g.lineTo(800 + k * 200, 180 - Math.abs(k) * 22); ink(g, 2, 0.5); }
      [[220, 190], [690, 160], [1160, 190]].forEach(([x, y]) => cut(g, () => archPath(g, x, y, 220, 330)));
      [[220, 190], [690, 160], [1160, 190]].forEach(([x, y]) => frameWin(g, x, y, 220, 330, P.cream, true));
      for (let i = 0; i < 4; i++) { const x = [120, 520, 1000, 1440][i]; box(g, x, 120, 46, 500, "#fffaf0", 2.5); dots(g, x + 24, 124, x + 46, 616, 6, 1.8, "rgba(34,48,58,.4)"); box(g, x - 10, 110, 66, 20, "#e8dfc8", 2.5); box(g, x - 10, 600, 66, 20, "#e8dfc8", 2.5); }
      tiles(g, 620, P.mustard, P.cream);
      g.fillStyle = "#a57a4c"; g.beginPath(); g.moveTo(200, 700); g.quadraticCurveTo(800, 560, 1400, 700); g.lineTo(1400, 760); g.quadraticCurveTo(800, 620, 200, 760); g.closePath(); g.fill(); ink(g, 3);
      g.save(); g.clip(); hatch(g, 200, 560, 1400, 760, 8, "rgba(34,48,58,.25)", 1.5); g.restore();
      [[560, 640, P.coral], [800, 610, P.teal], [1040, 640, P.navy]].forEach(([x, y, c]) => chair(g, x, y, c, 1.1));
      g.fillStyle = "#8a5f38"; g.beginPath(); g.moveTo(720, 900); g.lineTo(745, 760); g.lineTo(855, 760); g.lineTo(880, 900); g.closePath(); g.fill(); ink(g, 3);
      box(g, 715, 742, 170, 26, "#b07a48", 3);
      g.fillStyle = P.mustard; g.beginPath(); g.arc(800, 830, 26, 0, Math.PI * 2); g.fill(); ink(g, 2.5);
      g.fillStyle = INK; g.beginPath(); g.arc(800, 824, 8, 0, Math.PI * 2); g.fill(); g.fillRect(797, 828, 6, 22);
    },
    radio(g, R) {
      g.fillStyle = P.teal; g.fillRect(0, 0, RW, 600);
      for (let y = 30; y < 560; y += 60) for (let x = 30; x < 760; x += 60) { g.fillStyle = (x + y) % 120 ? "#2a7f7b" : "#33968f"; g.fillRect(x, y, 50, 50); g.beginPath(); g.rect(x, y, 50, 50); ink(g, 1.2, 0.35); }
      cut(g, () => g.rect(960, 110, 480, 330)); frameWin(g, 960, 110, 480, 330, P.cream);
      palmLeaves(g, 1500, 120, 1.1);
      box(g, 120, 100, 120, 150, P.mustard, 3); g.fillStyle = P.coral; g.beginPath(); g.arc(180, 175, 40, 0, Math.PI * 2); g.fill(); ink(g, 2.5);
      for (let k = 0; k < 12; k++) { g.save(); g.translate(180, 175); g.rotate(k * Math.PI / 6); g.fillStyle = P.coral; g.fillRect(-3, -62, 6, 14); g.restore(); }
      box(g, 300, 330, 540, 24, "#7c4b2a", 2.5);
      for (let k = 0; k < 26; k++) { const h = 90 + (k * 37) % 40; box(g, 312 + k * 20, 330 - h, 18, h, [P.coral, P.mustard, P.cream, P.navy, P.leaf, "#e889a6"][k % 6], 1.8); }
      floorPlanks(g, 600, "#9b6b40", "rgba(34,48,58,.45)");
      g.fillStyle = "#5d4630"; g.beginPath(); g.moveTo(100, 900); g.lineTo(220, 640); g.lineTo(1380, 640); g.lineTo(1500, 900); g.closePath(); g.fill(); ink(g, 3);
      g.fillStyle = "#3d2f24"; g.beginPath(); g.moveTo(220, 640); g.lineTo(1380, 640); g.lineTo(1400, 680); g.lineTo(200, 680); g.closePath(); g.fill(); ink(g, 2.5);
      for (let i = 0; i < 14; i++) { const x = 380 + i * 60; box(g, x - 4, 720, 8, 120, INK, 1); box(g, x - 14, 740 + (i * 29) % 70, 28, 16, [P.cream, P.mustard, P.coral][i % 3], 2); g.fillStyle = P.cream; g.beginPath(); g.arc(x, 700, 9, 0, Math.PI * 2); g.fill(); ink(g, 1.8); }
      g.fillStyle = "#2b2b30"; g.beginPath(); g.arc(1220, 760, 90, 0, Math.PI * 2); g.fill(); ink(g, 3);
      for (let r = 20; r < 90; r += 12) { g.beginPath(); g.arc(1220, 760, r, 0, Math.PI * 2); g.strokeStyle = "rgba(255,255,255,.12)"; g.lineWidth = 1.5; g.stroke(); }
      g.fillStyle = P.coral; g.beginPath(); g.arc(1220, 760, 24, 0, Math.PI * 2); g.fill();
      g.strokeStyle = INK; g.lineWidth = 9; g.beginPath(); g.moveTo(660, 640); g.lineTo(600, 470); g.lineTo(760, 400); g.stroke();
      g.fillStyle = "#3a3a40"; g.beginPath(); g.ellipse(790, 395, 34, 52, 0.4, 0, Math.PI * 2); g.fill(); ink(g, 3);
      g.strokeStyle = "rgba(255,255,255,.25)"; g.lineWidth = 2; for (let k = -3; k <= 3; k++) { g.beginPath(); g.moveTo(770 + k * 8, 360); g.lineTo(800 + k * 8, 432); g.stroke(); }
      box(g, 1240, 470, 160, 70, INK, 3);
    },
    north(g, R) {
      g.fillStyle = "#cfe1ec"; g.fillRect(0, 0, RW, 620);
      for (let x = 0; x < RW; x += 40) { g.fillStyle = x % 80 ? "#c3d8e5" : "#cfe1ec"; g.fillRect(x, 0, 40, 440); }
      box(g, -10, 440, RW + 20, 180, P.navy, 3);
      for (let x = 40; x < RW; x += 200) { g.beginPath(); g.rect(x, 470, 160, 120); ink(g, 2, 0.6); }
      cut(g, () => g.rect(560, 80, 480, 330)); frameWin(g, 560, 80, 480, 330, P.cream);
      [[470, 1], [1130, -1]].forEach(([x, d]) => { g.fillStyle = "#2c4f8c"; g.beginPath(); g.moveTo(x - 70 * d, 40); g.lineTo(x + 80 * d, 40); g.quadraticCurveTo(x + 40 * d, 250, x + 100 * d, 470); g.lineTo(x - 70 * d, 470); g.closePath(); g.fill(); ink(g, 3); for (let k = 0; k < 4; k++) { g.beginPath(); g.moveTo(x - 40 * d + k * 30 * d, 50); g.quadraticCurveTo(x - 30 * d + k * 30 * d, 260, x - 20 * d + k * 34 * d, 460); ink(g, 1.5, 0.5); } });
      box(g, 0, 30, RW, 20, "#e8dfc8", 2.5);
      box(g, 120, 140, 220, 160, P.cream, 3); g.fillStyle = P.leaf; g.beginPath(); g.ellipse(230, 220, 70, 30, 0.2, 0, Math.PI * 2); g.fill(); ink(g, 2);
      g.strokeStyle = P.coral; g.lineWidth = 3; g.setLineDash([6, 6]); g.beginPath(); g.moveTo(150, 280); g.quadraticCurveTo(230, 160, 320, 170); g.stroke(); g.setLineDash([]);
      floorPlanks(g, 620, "#7d5a3c", "rgba(34,48,58,.45)");
      g.fillStyle = "#6b4a30"; g.beginPath(); g.moveTo(380, 900); g.lineTo(450, 700); g.lineTo(1150, 700); g.lineTo(1220, 900); g.closePath(); g.fill(); ink(g, 3);
      box(g, 430, 680, 740, 30, "#8a6440", 3);
      g.save(); g.beginPath(); g.moveTo(380, 900); g.lineTo(450, 710); g.lineTo(1150, 710); g.lineTo(1220, 900); g.closePath(); g.clip(); hatch(g, 800, 700, 1220, 900, 9, "rgba(34,48,58,.3)", 1.5); g.restore();
      g.fillStyle = P.leafD; g.beginPath(); g.moveTo(520, 680); g.lineTo(560, 620); g.lineTo(600, 680); g.closePath(); g.fill(); ink(g, 2.5); box(g, 556, 590, 8, 40, P.mustard, 2);
      g.fillStyle = "#6fa8c8"; g.beginPath(); g.arc(1030, 620, 52, 0, Math.PI * 2); g.fill(); ink(g, 3);
      g.fillStyle = P.leafL; g.beginPath(); g.ellipse(1015, 605, 22, 14, 0.5, 0, Math.PI * 2); g.ellipse(1050, 640, 14, 9, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = P.mustard; g.lineWidth = 5; g.beginPath(); g.arc(1030, 620, 64, Math.PI * 0.6, Math.PI * 1.9); g.stroke(); box(g, 1022, 680, 16, 14, P.mustard, 2);
      box(g, 760, 650, 90, 30, P.cream, 2); box(g, 860, 656, 60, 24, P.cream, 2);
      g.strokeStyle = INK; g.lineWidth = 4; g.beginPath(); g.moveTo(1340, 900); g.lineTo(1340, 300); g.stroke();
    },
    south(g, R) {
      g.fillStyle = "#f2c9a8"; g.fillRect(0, 0, RW, 620);
      g.save(); g.beginPath(); g.rect(0, 0, RW, 620); g.clip(); hatch(g, 0, 0, RW, 620, 24, "rgba(226,103,79,.12)", 6); g.restore();
      [[260, 130], [1100, 130]].forEach(([x, y]) => { cut(g, () => archPath(g, x, y, 240, 360)); frameWin(g, x, y, 240, 360, P.cream, true); });
      box(g, 0, 560, RW, 60, P.coral, 3);
      for (let x = 0; x < RW; x += 40) { g.fillStyle = x % 80 ? P.teal : P.mustard; g.beginPath(); g.moveTo(x, 560); g.lineTo(x + 20, 540); g.lineTo(x + 40, 560); g.fill(); }
      box(g, 600, 150, 400, 250, "#cdeee8", 3);
      g.strokeStyle = "rgba(34,48,58,.25)"; for (let k = 0; k < 5; k++) { g.beginPath(); g.moveTo(620, 370 - k * 8); g.quadraticCurveTo(700, 340 - k * 20, 640 + k * 10, 200); g.lineWidth = 3; g.stroke(); }
      box(g, 590, 400, 420, 30, "#7c4b2a", 3);
      tiles(g, 620, "#e9b07a", "#f6dcc0");
      box(g, 520, 700, 560, 40, "#b07a48", 3); g.fillStyle = "#a56c3e"; g.fillRect(540, 740, 24, 160); g.fillRect(1036, 740, 24, 160);
      g.beginPath(); g.rect(540, 740, 24, 160); g.rect(1036, 740, 24, 160); ink(g, 2.5);
      [[340, 860], [1260, 860]].forEach(([x, y]) => { g.fillStyle = "#d4a76a"; g.beginPath(); g.ellipse(x, y - 120, 90, 120, 0, Math.PI, 0); g.closePath(); g.fill(); ink(g, 3); g.save(); g.clip(); for (let k = -8; k < 8; k++) { g.beginPath(); g.moveTo(x + k * 14, y - 240); g.lineTo(x + k * 14 + 40, y); ink(g, 1.2, 0.4); } g.restore(); box(g, x - 80, y - 130, 160, 30, P.teal, 2.5); });
      plant(g, 140, 900, 1.3); plant(g, 1480, 900, 1.2);
      box(g, 680, 650, 70, 50, P.cream, 2); g.fillStyle = P.coral; g.beginPath(); g.arc(715, 640, 18, Math.PI, 0); g.fill(); ink(g, 2);
    },
    bar(g, R) {
      g.fillStyle = "#c98c55"; g.fillRect(0, 0, RW, 620);
      for (let x = 0; x < RW; x += 70) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 620); ink(g, 1.6, 0.4); }
      cut(g, () => g.rect(0, 70, 430, 480)); g.fillStyle = "#7c4b2a"; g.fillRect(420, 40, 40, 580); g.beginPath(); g.rect(420, 40, 40, 580); ink(g, 3);
      palmLeaves(g, 120, 40, 1.2, P.leafD);
      box(g, 520, 140, 960, 22, "#7c4b2a", 2.5); box(g, 520, 300, 960, 22, "#7c4b2a", 2.5);
      for (let row = 0; row < 2; row++) for (let k = 0; k < 22; k++) { const x = 540 + k * 43, y = row ? 300 : 140, h = 70 + (k * 23 + row * 11) % 40, c = ["#3e8f5a", "#b0472f", P.mustard, "#4b6fa0", P.cream, "#8d3f6a"][(k + row) % 6]; g.fillStyle = c; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - h * 0.6); g.quadraticCurveTo(x, y - h * 0.75, x + 8, y - h * 0.8); g.lineTo(x + 8, y - h); g.lineTo(x + 18, y - h); g.lineTo(x + 18, y - h * 0.8); g.quadraticCurveTo(x + 26, y - h * 0.75, x + 26, y - h * 0.6); g.lineTo(x + 26, y); g.closePath(); g.fill(); ink(g, 1.8); g.fillStyle = "rgba(251,243,223,.5)"; g.fillRect(x + 4, y - h * 0.55, 4, h * 0.4); }
      box(g, 760, 380, 320, 120, P.teal, 3);
      g.fillStyle = P.cream; g.font = "800 64px Sora, sans-serif"; g.textAlign = "center"; g.fillText("LA OLA", 920, 462);
      floorPlanks(g, 620, "#8a5f38", "rgba(34,48,58,.45)", 900);
      g.fillStyle = "#6b4422"; g.beginPath(); g.moveTo(380, 900); g.lineTo(460, 660); g.lineTo(1600, 660); g.lineTo(1600, 900); g.closePath(); g.fill(); ink(g, 3);
      box(g, 440, 630, 1180, 40, "#b07a48", 3);
      g.save(); g.beginPath(); g.moveTo(380, 900); g.lineTo(460, 670); g.lineTo(1600, 670); g.lineTo(1600, 900); g.closePath(); g.clip(); for (let x = 400; x < 1600; x += 90) { g.beginPath(); g.moveTo(x + 60, 670); g.lineTo(x, 900); ink(g, 2, 0.4); } g.restore();
      [[560, 560, P.coral], [840, 590, P.cream]].forEach(([x, y, c]) => { g.fillStyle = c; g.beginPath(); g.moveTo(x - 20, y); g.lineTo(x + 20, y); g.lineTo(x + 6, y + 40); g.lineTo(x - 6, y + 40); g.closePath(); g.fill(); ink(g, 2); box(g, x - 2, y + 40, 4, 26, INK, 1); g.fillStyle = P.leafL; g.beginPath(); g.arc(x + 18, y - 4, 10, 0, Math.PI * 2); g.fill(); ink(g, 1.5); });
      [[240, 900], [420, 900]].forEach(([x, y]) => { g.fillStyle = INK; g.fillRect(x - 4, y - 190, 8, 190); g.fillStyle = P.coral; g.beginPath(); g.ellipse(x, y - 190, 60, 16, 0, 0, Math.PI * 2); g.fill(); ink(g, 3); });
    },
    book(g, R) {
      g.fillStyle = "#b8ab95"; g.fillRect(0, 0, RW, 640);
      for (let row = 0; row < 14; row++) for (let k = -1; k < 18; k++) { const y = row * 48, x = k * 100 + (row % 2) * 50 + (R() - 0.5) * 10; g.fillStyle = ["#b8ab95", "#a99c86", "#c4b8a2"][(row * 7 + k) % 3]; g.fillRect(x + 3, y + 3, 94, 42); g.beginPath(); g.rect(x + 3, y + 3, 94, 42); ink(g, 1.6, 0.6); }
      cut(g, () => archPath(g, 1180, 120, 140, 300)); frameWin(g, 1180, 120, 140, 300, "#8b7a66", true);
      for (let k = 0; k < 8; k++) { const y = 640 - k * 80, x = 60 + k * 26; box(g, x, y - 26, 220 - k * 12, 26, "#8b7a66", 2.5); }
      g.strokeStyle = INK; g.lineWidth = 5; g.beginPath(); g.moveTo(80, 640); g.lineTo(300, 0); g.stroke();
      floorPlanks(g, 640, "#6a5a48", "rgba(34,48,58,.5)");
      g.fillStyle = "rgba(57,255,138,.0)";
      g.fillStyle = "#6b4422"; g.beginPath(); g.moveTo(700, 900); g.lineTo(740, 700); g.lineTo(860, 700); g.lineTo(900, 900); g.closePath(); g.fill(); ink(g, 3);
      g.fillStyle = "#8a5f38"; g.beginPath(); g.moveTo(560, 700); g.lineTo(1040, 700); g.lineTo(980, 640); g.lineTo(620, 640); g.closePath(); g.fill(); ink(g, 3);
      g.fillStyle = "#fbf3df"; g.beginPath(); g.moveTo(800, 655); g.quadraticCurveTo(700, 610, 600, 640); g.lineTo(630, 690); g.quadraticCurveTo(720, 670, 800, 700); g.closePath(); g.fill(); ink(g, 2.5);
      g.beginPath(); g.moveTo(800, 655); g.quadraticCurveTo(900, 610, 1000, 640); g.lineTo(970, 690); g.quadraticCurveTo(880, 670, 800, 700); g.closePath(); g.fill(); ink(g, 2.5);
      g.strokeStyle = "rgba(34,48,58,.4)"; g.lineWidth = 2; for (let k = 0; k < 6; k++) { g.beginPath(); g.moveTo(640 + k * 4, 650 + k * 7); g.quadraticCurveTo(720, 640 + k * 7, 780, 662 + k * 7); g.moveTo(820, 662 + k * 7); g.quadraticCurveTo(880, 640 + k * 7, 960 - k * 4, 650 + k * 7); g.stroke(); }
      g.fillStyle = P.coral; g.fillRect(796, 690, 8, 60);
      g.strokeStyle = INK; g.lineWidth = 4; g.beginPath(); g.moveTo(800, 0); g.lineTo(800, 120); g.stroke();
      g.fillStyle = "#2f6440"; g.beginPath(); g.moveTo(740, 170); g.lineTo(860, 170); g.lineTo(830, 120); g.lineTo(770, 120); g.closePath(); g.fill(); ink(g, 3);
    },
    market(g, R) {
      cut(g, () => g.rect(0, 0, RW, RH));
      g.fillStyle = "#4a8a4a"; g.beginPath(); g.moveTo(0, 470); for (let x = 0; x <= RW; x += 40) g.lineTo(x, 430 - Math.sin(x * 0.004 + 1) * 60 - Math.sin(x * 0.011) * 20); g.lineTo(RW, 520); g.lineTo(0, 520); g.closePath(); g.fill(); ink(g, 3);
      g.save(); g.clip(); hatch(g, 0, 330, RW, 520, 7, "rgba(20,40,30,.3)", 1.5); g.restore();
      g.fillStyle = "#e9d3a4"; g.fillRect(0, 500, RW, 400); g.beginPath(); g.moveTo(0, 500); g.lineTo(RW, 500); ink(g, 3);
      g.strokeStyle = "rgba(34,48,58,.25)"; g.lineWidth = 2; for (let k = 1; k < 6; k++) { g.beginPath(); g.ellipse(800, 1000, 300 * k, 90 * k, 0, Math.PI, 0); g.stroke(); }
      g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); g.moveTo(0, 80); g.quadraticCurveTo(800, 220, RW, 80); g.stroke();
      for (let k = 0; k < 13; k++) { const f = k / 12, x = f * RW, y = 80 + Math.sin(f * Math.PI) * 70; g.fillStyle = [P.coral, P.mustard, P.teal, P.cream][k % 4]; g.beginPath(); g.moveTo(x - 18, y); g.lineTo(x + 18, y); g.lineTo(x, y + 34); g.closePath(); g.fill(); ink(g, 2); }
      const stall = (x, w, c, fruit) => {
        g.fillStyle = INK; g.fillRect(x + 8, 300, 12, 420); g.fillRect(x + w - 20, 300, 12, 420);
        box(g, x, 600, w, 130, "#c79a62", 3); g.save(); g.beginPath(); g.rect(x, 600, w, 130); g.clip(); for (let k = 0; k < w; k += 30) { g.beginPath(); g.moveTo(x + k, 600); g.lineTo(x + k, 730); ink(g, 1.5, 0.4); } g.restore();
        for (let k = 0; k < 8; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.moveTo(x - 30 + k * (w + 60) / 8, 330); g.lineTo(x - 30 + (k + 1) * (w + 60) / 8, 330); g.lineTo(x - 10 + (k + 1) * (w + 20) / 8, 240); g.lineTo(x - 10 + k * (w + 20) / 8, 240); g.closePath(); g.fill(); }
        g.beginPath(); g.moveTo(x - 30, 330); g.lineTo(x + w + 30, 330); g.lineTo(x + w + 10, 240); g.lineTo(x - 10, 240); g.closePath(); ink(g, 3);
        for (let k = 0; k < 8; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.arc(x - 30 + (k + 0.5) * (w + 60) / 8, 330, (w + 60) / 16, 0, Math.PI); g.fill(); ink(g, 2); }
        for (let k = 0; k < Math.floor(w / 34); k++) for (let r = 0; r < 2; r++) { g.fillStyle = fruit[(k + r) % fruit.length]; g.beginPath(); g.arc(x + 26 + k * 34 + r * 17, 590 - r * 22, 16, 0, Math.PI * 2); g.fill(); ink(g, 2); }
      };
      stall(80, 380, P.coral, [P.mustard, "#e2674f", P.leafL]); stall(620, 360, P.teal, ["#e889a6", P.mustard, "#c4453a"]); stall(1140, 400, P.mustard, [P.leafL, "#e2674f", "#f0d060"]);
      box(g, 500, 760, 120, 80, "#a57a4c", 3); box(g, 1020, 780, 100, 70, "#a57a4c", 3);
      for (let k = 0; k < 6; k++) { g.fillStyle = [P.leafL, P.mustard][k % 2]; g.beginPath(); g.arc(520 + k * 16, 760, 12, 0, Math.PI * 2); g.fill(); ink(g, 1.8); }
    },
    pier(g, R) {
      cut(g, () => g.rect(0, 0, RW, RH));
      g.fillStyle = "#a57a4c"; g.beginPath(); g.moveTo(200, 900); g.lineTo(720, RHZ + 40); g.lineTo(880, RHZ + 40); g.lineTo(1400, 900); g.closePath(); g.fill(); ink(g, 3);
      g.strokeStyle = "rgba(34,48,58,.5)"; g.lineWidth = 2;
      for (let k = 1; k < 26; k++) { const f = Math.pow(k / 26, 1.8), y = RHZ + 40 + (900 - RHZ - 40) * f; g.beginPath(); g.moveTo(lerp(720, 200, f), y); g.lineTo(lerp(880, 1400, f), y); g.stroke(); }
      [[0.15], [0.4], [0.75], [1]].forEach(([f]) => { [[720, 200], [880, 1400]].forEach(([a, b]) => { const x = lerp(a, b, f), y = RHZ + 40 + (900 - RHZ - 40) * f, h = 30 + f * 140, w = 6 + f * 22; box(g, x - w / 2, y - h, w, h, "#7c4b2a", 2.5); }); });
      g.strokeStyle = "#d9bf6a"; g.lineWidth = 5; [[720, 200], [880, 1400]].forEach(([a, b]) => { g.beginPath(); for (let k = 0; k <= 3; k++) { const f0 = [0.15, 0.4, 0.75, 1][k], x = lerp(a, b, f0), y = RHZ + 40 + (900 - RHZ - 40) * f0 - (30 + f0 * 140) + 10; k ? g.quadraticCurveTo((g.px + x) / 2, (g.py + y) / 2 + 26 * f0, x, y) : g.moveTo(x, y); g.px = x; g.py = y; } g.stroke(); });
      g.fillStyle = INK; g.fillRect(1196, 300, 10, 420); box(g, 1176, 260, 50, 50, P.mustard, 3);
      g.fillStyle = "#e9d3a4"; g.beginPath(); g.ellipse(150, 905, 380, 90, 0, Math.PI, 0); g.fill(); ink(g, 3);
    },
  };
  /* what moves in each room, drawn on top every frame (room coordinates) */
  const ROOMFX = {
    hall(g, t, day) { if (day > 0.2) { g.globalCompositeOperation = "lighter"; [[220, 190], [690, 160], [1160, 190]].forEach(([x, y], i) => { g.fillStyle = `rgba(255,236,190,${0.1 * day * (0.8 + 0.2 * Math.sin(t * 0.001 + i))})`; g.beginPath(); g.moveTo(x, y + 100); g.lineTo(x + 220, y + 100); g.lineTo(x + 420, 900); g.lineTo(x + 100, 900); g.closePath(); g.fill(); }); g.globalCompositeOperation = "source-over"; } },
    radio(g, t) {
      const on = Math.floor(t / 900) % 2; g.fillStyle = on ? P.coral : "#7a3a30"; g.beginPath(); g.arc(1320, 505, 22, 0, Math.PI * 2); g.fill(); ink(g, 2.5);
      for (let k = 0; k < 10; k++) { const h = 6 + Math.abs(Math.sin(t * 0.008 + k * 0.9) * Math.sin(t * 0.003 + k)) * 40; g.fillStyle = k > 7 ? P.coral : P.leafL; g.fillRect(1250 + k * 8, 530 - h, 6, h); }
      g.save(); g.translate(1220, 760); g.rotate(t * 0.004); g.fillStyle = P.cream; g.fillRect(-3, -70, 6, 20); g.restore();
    },
    north(g, t) { flagFx(g, 1340, 300, t, "#3b5f8a", "wind"); },
    south(g, t) { fan(g, 800, 40, t); g.fillStyle = P.mustard; for (let k = 0; k < 3; k++) { const x = 650 + ((t * 0.04 * (1 + k * 0.3) + k * 120) % 300), y = 220 + k * 50 + Math.sin(t * 0.003 + k) * 10; g.beginPath(); g.ellipse(x, y, 16, 9, 0, 0, Math.PI * 2); g.moveTo(x - 14, y); g.lineTo(x - 26, y - 9); g.lineTo(x - 26, y + 9); g.fill(); ink(g, 1.6); } },
    bar(g, t) { fan(g, 1000, 30, t); g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); g.moveTo(440, 40); g.quadraticCurveTo(1000, 130, 1600, 50); g.stroke(); for (let k = 0; k < 16; k++) { const f = k / 15, x = lerp(440, 1600, f), y = lerp(40, 50, f) + Math.sin(f * Math.PI) * 45; g.fillStyle = `rgba(255,214,120,${0.6 + 0.4 * Math.sin(t * 0.004 + k * 1.3)})`; g.beginPath(); g.arc(x, y + 10, 8, 0, Math.PI * 2); g.fill(); ink(g, 1.4); } },
    book(g, t) {
      g.globalCompositeOperation = "lighter";
      const gr = g.createLinearGradient(0, 170, 0, 700); gr.addColorStop(0, "rgba(57,255,138,.34)"); gr.addColorStop(1, "rgba(57,255,138,.04)");
      g.fillStyle = gr; g.beginPath(); g.moveTo(760, 170); g.lineTo(840, 170); g.lineTo(1060, 700); g.lineTo(540, 700); g.closePath(); g.fill();
      for (let k = 0; k < 24; k++) { const x = 640 + ((k * 97 + t * 0.006 * (k % 3 + 1)) % 320), y = 200 + ((k * 61 + t * 0.012) % 480); g.fillStyle = `rgba(200,255,220,${0.3 + 0.3 * Math.sin(t * 0.003 + k)})`; g.fillRect(x, y, 3, 3); }
      g.globalCompositeOperation = "source-over";
    },
    market(g, t) { },
    pier(g, t) { g.fillStyle = `rgba(255,214,120,${0.5 + 0.3 * Math.sin(t * 0.003)})`; g.beginPath(); g.arc(1201, 285, 14, 0, Math.PI * 2); g.fill(); boat(g, 520, RHZ + 50, t); },
  };
  function fan(g, x, y, t) {
    g.fillStyle = INK; g.fillRect(x - 4, 0, 8, y + 20);
    g.save(); g.translate(x, y + 26); g.scale(1, 0.22); g.rotate(t * 0.006);
    for (let k = 0; k < 4; k++) { g.rotate(Math.PI / 2); g.fillStyle = "#7c4b2a"; g.beginPath(); g.ellipse(0, -120, 22, 110, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = INK; g.lineWidth = 8; g.stroke(); }
    g.restore(); g.fillStyle = P.mustard; g.beginPath(); g.ellipse(x, y + 26, 22, 12, 0, 0, Math.PI * 2); g.fill(); ink(g, 2);
  }
  function flagFx(g, x, y, t, c, mark) {
    g.save(); g.translate(x, y); g.scale(5, 5); flag(g, 0, 42, t, c, "#fff", mark); g.restore();
  }
  /* the room behind its windows: the sky and the sea of the hour, in the same printed bands */
  function roomBackdrop(g, sky, t) {
    const NB = 6; for (let i = 0; i < NB; i++) { g.fillStyle = rgb(mix(sky.top, sky.bot, i / (NB - 1))); g.fillRect(0, RHZ * Math.pow(i / NB, 0.7), RW, RHZ * (Math.pow((i + 1) / NB, 0.7) - Math.pow(i / NB, 0.7)) + 1); }
    for (let i = 0; i < 4; i++) { const a = RHZ + (RH - RHZ) * Math.pow(i / 4, 1.6), b = RHZ + (RH - RHZ) * Math.pow((i + 1) / 4, 1.6); g.fillStyle = rgb(mix(sky.sea, sky.seaB, i / 3)); g.fillRect(0, a, RW, b - a + 1); }
    const hh = S.hour % 4;
    if (hh < 2.75) { const sx = lerp(250, 1350, Math.min(1, hh / 2.4)), sy = RHZ - 60 - Math.sin(Math.min(1, hh / 2.4) * Math.PI) * 200 + (hh > 2 ? (hh - 2) * 160 : 0); [[110, 0.18], [80, 0.3]].forEach(([r, al]) => { g.fillStyle = rgb(sky.sun, al); g.beginPath(); g.arc(sx, sy, r, 0, Math.PI * 2); g.fill(); }); g.fillStyle = rgb(sky.sun); g.beginPath(); g.arc(sx, sy, 50, 0, Math.PI * 2); g.fill(); }
    else { g.fillStyle = "rgba(251,243,223,.9)"; g.beginPath(); g.arc(1250, 140, 30, 0, Math.PI * 2); g.arc(1264, 130, 26, 0, Math.PI * 2, true); g.fill(); }
    for (let i = 0; i < 4; i++) cloud(g, ((t * 0.01 * (1 + i * 0.3) + i * 500) % 2000) - 200, 90 + i * 60, 1.6, 0.5);
    g.strokeStyle = "rgba(251,243,223,.45)"; g.lineWidth = 2;
    for (let r = 0; r < 12; r++) { const y = RHZ + 10 + r * r * 3.4, sc = 4 + r * 1.4, gap = 90 + r * 20, dr = Math.sin(t * 0.0009 + r) * gap * 0.25; for (let x = -gap + ((r * 53) % gap) + (r % 2) * gap / 2 + dr; x < RW + gap; x += gap) { g.beginPath(); g.arc(x, y, sc, Math.PI * 1.1, Math.PI * 1.9); g.stroke(); } }
  }
  const roomCache = {};
  /* how wide a room is drawn: a wide painting (paint.py hires) keeps its own width, the middle 1600 stay where they were */
  const roomW = id => { const im = painted(id) && ART.img[id]; return im && im.naturalWidth / im.naturalHeight > 1.9 ? Math.round(RH * im.naturalWidth / im.naturalHeight) : RW; };
  function roomImage(id) {
    const rw = roomW(id), q = Math.min(2.6, 8192 / rw, Math.max(0.6, Math.max(S.W / rw, S.H / RH) * S.K));
    let c = roomCache[id]; if (c && Math.abs(c.q - q) < 0.05) return c;
    c = document.createElement("canvas"); c.width = Math.round(rw * q); c.height = Math.round(RH * q); c.q = q;
    const g = c.getContext("2d"); g.scale(q, q); g.imageSmoothingQuality = "high";
    if (painted(id)) cover(g, ART.img[id], rw, RH); else ROOMS[id](g, rnd(id.length * 131));
    return (roomCache[id] = c);
  }

  /* ---------- the painted pictures, when the server has them ---------- */
  /* while the painted island is on its way, only the sky and the sea of the hour show (ART.pending; frame: wait): the
     drawn island of the first days, with its palms, people, flags and boat, is a fallback for when the server has no
     painting, not a picture to flash before the real one */
  const ART = { base: "https://node.tauhud.com/rico/art/", img: {}, pending: true };
  /* no painting (the server restarting or out of reach): the drawn island stands in, and the painting is asked for
     again after 15 s, 30 s, 1 and 2 min, then every 5 min, so it comes back by itself without a reload */
  let again = 15000;
  const drawn = () => { clearTimeout(late); if (ART.pending && !ART.img.island) { ART.pending = false; S.base = null; if (S.c) size(); } };
  const settle = () => {
    drawn(); if (ART.img.island) return;
    clearTimeout(ART.retry); ART.retry = setTimeout(() => ask(0), again); again = Math.min(300000, again * 2);
  };
  let late = setTimeout(settle, 12000);   // a silent server: the drawn island after all
  /* the list of the paintings; a server that is restarting just then (up) is asked again, three times, before the drawn
     island shows */
  const ask = n => fetch(ART.base + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : Promise.reject(r.status))).then(j => {
    ART.box = (j && j.boxes) || {};   // where a talking or blinking frame differs from the still picture
    const scenes = (j && j.scenes) || {};
    /* each room's own lamps (paint.py lights), only while they were found in the very painting that shows */
    ART.lights = {};
    for (const id in (j && j.lights) || {}) { const L = j.lights[id]; if (L && Array.isArray(L.l) && (L.of === scenes[id] || L.of === ((j.orig || {})[id]))) ART.lights[id] = L; }
    if (!scenes.island) drawn();   // the server has no painting of the island: the drawn one, and no asking again
    else { clearTimeout(late); late = setTimeout(settle, 30000); }   // the painting is listed: a large picture on a slow line takes its time
    Object.entries(scenes).forEach(([id, f]) => {
      if (ART.img[id] && ART.img[id].f === f) return;   // asked again: a painting that came already stays
      const im = new Image(); im.crossOrigin = "anonymous"; im.decoding = "async"; im.f = f;
      im.onload = () => {
        if (id === "island" && ART.img.island) return;   // asked again meanwhile: the painting that came first stays
        ART.img[id] = im;
        if (id === "folk") return;   // the people, painted: a strip of figures (infra/rabbit-art paint.py folk)
        if (id !== "island") { delete roomCache[id]; return; }
        const ar = im.naturalWidth / im.naturalHeight;   // a wide painting (paint.py hires) carries on past the world's sides
        ART.wide = ar > 1.9 ? Math.round((WH * ar - WW) / 2) : 0;
        if (j.layout && painted("island")) useLayout(j.layout);
        const bare = ART.pending;   // only the bare sky and sea were there: the view starts where it belongs, the painting fades in
        ART.pending = false; S.base = null; if (bare) S.sized = false;
        clearTimeout(late); clearTimeout(ART.retry);
        if (S.c) size();
        ART.fade = bare;   // over the drawn island (a very slow line, a server back from a restart) it simply takes its place
      };
      if (id === "island") im.onerror = settle;
      im.src = ART.base + f;
    });
  }, () => (n < 3 ? setTimeout(() => ask(n + 1), 1000 * 2 ** n) : settle())).catch(settle);
  try { ask(0); } catch (e) { settle(); }
  const painted = id => !!ART.img[id] && !/[?&]art=drawn/.test(location.search);
  /* a painted island drawn from a new sketch (infra/rabbit-art/sketch.py) brings its layout: where the places stand,
     the streets people walk, the windows that light up, smoke, torches and water, the lamp and the mast */
  function useLayout(L) {
    for (const id in L.places || {}) PLACES[id] = Object.assign(PLACES[id] || {}, L.places[id]);   // new quarters come with the layout
    if (L.walk) { WALK.splice(0, WALK.length, ...L.walk); FOLK.forEach((f, i) => { f.path = WALK[i % WALK.length]; }); }
    if (L.fx) FX.splice(0, FX.length, ...L.fx);
    if (L.windows) WINDOWS.splice(0, WINDOWS.length, ...L.windows);
    if (L.lights) LIGHTS.splice(0, LIGHTS.length, ...L.lights);
    for (const k in SPOT) if (L[k]) SPOT[k] = L[k];
    if (L.rabbit) { RB.x = RB.tx = L.rabbit[0]; RB.y = RB.ty = L.rabbit[1]; }
    if (L.horizon) ART.hz = L.horizon;   // where the painting's far sea meets the sky (world units from the top)
    ART.layout = true; ART.whole = L.view === "whole";
    if (S.focusId) focus(S.focusId, S.focusSide);
  }
  /* a wide screen shows more than the painting: beside it, the same painting, wide, out of focus and a shade darker,
     so its sea and sky carry on to the edges without a seam or a strip of drawn sky (as a cinema does with a narrow film) */
  function sides(g, wl, wt, wr, wb) {
    const im = ART.img.island;
    if (!S.blur || S.blur.im !== im) {
      const c = document.createElement("canvas"); c.width = 96; c.height = 54; const cg = c.getContext("2d");
      cg.filter = "blur(3px)"; cg.drawImage(im, -6, -4, 108, 62); cg.filter = "none";
      cg.fillStyle = "rgba(10,24,34,.38)"; cg.fillRect(0, 0, 96, 54); c.im = im; S.blur = c;
    }
    const w = wr - wl, h = Math.max(wb - wt, w * 9 / 16), e = ART.wide || 0;
    g.save(); g.imageSmoothingQuality = "high"; g.drawImage(S.blur, wl, (wt + wb) / 2 - h / 2, w, h); g.restore();
    [[-e, -1], [WW + e, 1]].forEach(([x, d]) => {   // the painting's edge melts into it
      const gr = g.createLinearGradient(x, 0, x + d * 90, 0); gr.addColorStop(0, "rgba(10,24,34,.35)"); gr.addColorStop(1, "rgba(10,24,34,0)");
      g.fillStyle = gr; g.fillRect(Math.min(x, x + d * 90), wt, 90, wb - wt);
    });
  }
  /* a picture drawn to cover the box, cropped in the middle (the painted ones are not always exactly 16:9) */
  function cover(g, im, w, h) {
    const k = Math.max(w / im.naturalWidth, h / im.naturalHeight), iw = im.naturalWidth * k, ih = im.naturalHeight * k;
    g.drawImage(im, (w - iw) / 2, (h - ih) / 2, iw, ih);
  }
  /* life in a painted room: dust in a warm shaft of light by day (after dark the place's lamps light it: roomLight) */
  function roomLife(g, t, day) {
    if (day <= 0.2) return;
    g.globalCompositeOperation = "lighter";
    g.fillStyle = `rgba(255,232,180,${0.07 * day})`; g.beginPath(); g.moveTo(380, 0); g.lineTo(700, 0); g.lineTo(1100, 900); g.lineTo(640, 900); g.closePath(); g.fill();
    for (let i = 0; i < 40; i++) {
      const k = (i * 0.618) % 1, y = (k * 900 + t * 0.008 * (0.5 + (i % 5) * 0.2)) % 900, x = 420 + y * 0.48 + Math.sin(t * 0.0006 + i * 2.3) * 60 + ((i * 37) % 120);
      g.fillStyle = `rgba(255,240,200,${day * (0.18 + 0.2 * Math.sin(t * 0.002 + i))})`; g.beginPath(); g.arc(x, y, 1.6 + (i % 3) * 0.7, 0, Math.PI * 2); g.fill();
    }
    g.globalCompositeOperation = "source-over";
  }
  /* the light of the hour in a painted place, as on the island: the picture, and whoever stands in it, multiplied with
     the light of the hour (white at noon, warm at the ends of the day, deep blue at night), with the haze of the place
     after dark. From dusk every place is lit in its own way (ROOMNIGHT): the lamps painted in it come on (ART.lights,
     found in the painting by paint.py lights), each lighting the room around it in its own colour and glowing itself,
     a room keeps a little of its lamps' colour in the dark corners, and the one you talk to stands in a softer pool of
     the place's light. Out in the open (a hill top, the stone circle) it stays the island's night, the moon the main
     light. The light map is soft, so it is drawn at a quarter of the pixels. */
  const ROOMLAMP = [255, 200, 146];
  /* lamp: the colour of the place's light; fill: how much of it falls on the one you talk to; amb: how much of it stays
     in the room's dark corners; haze: the colour and strength of the night air; out: open air (moonlight) */
  const ROOMNIGHT = {
    hall:   { lamp: [255, 196, 128], fill: 0.7, amb: 0.04, out: 1 },              // the Council Tree: lanterns in the branches
    market: { lamp: [255, 206, 150], fill: 0.85, amb: 0.06, out: 1 },             // the Parasol Café: string lights over the terrace
    radio:  { lamp: [255, 186, 112], fill: 0.85, amb: 0.14 },                     // a desk lamp and the glow of the dials
    north:  { lamp: [226, 232, 255], fill: 0.75, amb: 0.1, haze: [10, 22, 60, 0.18] },   // the chandelier, cool and grand
    south:  { lamp: [255, 180, 150], fill: 0.85, amb: 0.14 },                     // warm and flattering, the pool glowing teal
    bar:    { lamp: [255, 176, 112], fill: 0.95, amb: 0.2 },                      // the bulbs on their string: the warmest room
    book:   { lamp: [196, 255, 206], fill: 0.8, amb: 0.08, haze: [6, 26, 30, 0.18] },     // the keeper's lamp throws a green cone
    pier:   { lamp: [255, 212, 150], fill: 0.6, amb: 0.03, out: 1 },              // the lamp post's square lantern
    school: { lamp: [236, 226, 200], fill: 0.45, amb: 0.04, haze: [12, 22, 50, 0.2] },   // nobody lights a school at night
    dive:   { lamp: [140, 232, 255], fill: 0.75, amb: 0.12, haze: [4, 30, 46, 0.16] },   // sensor buoys and the reef screen
    works:  { lamp: [255, 158, 88], fill: 0.85, amb: 0.14 },                      // the furnace under the chimney
    camp:   { lamp: [255, 160, 76], fill: 0.9, amb: 0.04, out: 1 },               // the campfire
    ship:   { lamp: [255, 198, 128], fill: 0.8, amb: 0.12 },                      // oil lamps among the finds
    ama:    { lamp: [255, 168, 96], fill: 0.9, amb: 0.14 },                       // the hearth
    canoe:  { lamp: [255, 188, 118], fill: 0.7, amb: 0.06, out: 1 },              // a lantern in the open shed
    stone:  { lamp: [190, 210, 255], fill: 0.35, amb: 0, out: 1, haze: [8, 18, 56, 0.2] },    // a hill top under the moon
    drums:  { lamp: [255, 168, 96], fill: 0.6, amb: 0.03, out: 1 },               // a torch by the drum
    circle: { lamp: [255, 168, 96], fill: 0.6, amb: 0.03, out: 1 },               // torches round the stones
    grotto: { lamp: [120, 236, 214], fill: 0.7, amb: 0.1, haze: [4, 28, 40, 0.18] },   // the pool's light dancing on the rock
  };
  const RLC = { warm: [255, 200, 132], fire: [255, 156, 72], cream: [255, 236, 204], gold: [255, 212, 116], green: [150, 255, 170], teal: [92, 236, 214], cyan: [120, 214, 255], pink: [255, 150, 200], red: [255, 96, 76], moon: [170, 196, 255] };
  const FLAME = { fire: 1, torch: 1, candle: 1, lantern: 1 };
  /* where a light of the painting (parts of the picture) stands on the screen: the picture covers the room's rw x RH,
     the room is drawn at sc, ox, oy */
  function roomSpot(L, T) {
    const [sc, ox, oy, rw, im] = T, iw = im ? im.naturalWidth : rw, ih = im ? im.naturalHeight : RH, k = Math.max(rw / iw, RH / ih);
    const x0 = (RW - rw) / 2 + (rw - iw * k) / 2, y0 = (RH - ih * k) / 2;
    return [(x0 + L.x * iw * k) * sc + ox, (y0 + L.y * ih * k) * sc + oy, L.w * iw * k * sc, L.h * ih * k * sc];
  }
  function roomLight(g, W, H, sky, nt, t, id, T) {
    const m = sky.mul, n = lampsOn(sky), mood = ROOMNIGHT[id] || { lamp: ROOMLAMP, fill: 0.82, amb: 0 }, found = ART.lights && ART.lights[id];
    const LL = (found && found.l) || [], out = found ? found.outside : !!mood.out, D = Math.min(W, H);
    const lit = L => (L.k === "window" ? 0.4 : 1) * (FLAME[L.k] ? flick(t, L.x * 97, L.y * 61) : L.k === "glow" || L.k === "screen" ? 0.94 + 0.06 * Math.sin(t * 0.0011 + L.x * 9) : 1);
    g.setTransform(1, 0, 0, 1, 0, 0);
    if (m[0] + m[1] + m[2] < 762) {
      g.globalCompositeOperation = "multiply";
      if (n > 0) {
        const q = 4, c = S.rlm || (S.rlm = document.createElement("canvas")), w = Math.ceil(W / q), h = Math.ceil(H / q);
        if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
        const lg = c.getContext("2d"), base = out ? m : mix(m, mood.lamp, Math.min(0.35, (mood.amb || 0) * (LL.length ? 1.6 : 1)) * n);
        lg.globalCompositeOperation = "source-over"; lg.fillStyle = rgb(base); lg.fillRect(0, 0, w, h);
        const pool = (x, y, r, col, a, sy = 1) => {
          if (a < 0.01 || r < 1) return; a = Math.min(1, a);
          lg.save(); lg.translate(x / q, y / q); if (sy !== 1) lg.scale(1, sy);
          const gr = lg.createRadialGradient(0, 0, 0, 0, 0, r / q);
          gr.addColorStop(0, rgb(mix(base, col, a))); gr.addColorStop(0.35, rgb(mix(base, col, a * 0.78))); gr.addColorStop(0.7, rgb(mix(base, col, a * 0.32))); gr.addColorStop(1, rgb(base, 0));
          lg.fillStyle = gr; lg.beginPath(); lg.arc(0, 0, r / q, 0, Math.PI * 2); lg.fill(); lg.restore();
        };
        /* the one you talk to, in the place's own light (softer where the room's lamps light it) */
        const [X, Y, Z] = S.hostAt || [W / 2, H * 0.3, D * 0.7];
        pool(X, Math.min(H * 0.62, Y + Z * 0.36), D * (LL.length ? 0.5 : 0.62), mood.lamp, (LL.length ? 0.62 : 0.82) * mood.fill * n);
        lg.globalCompositeOperation = "lighten";
        for (const L of LL) {
          const [x, y, sw, sh] = roomSpot(L, T), col = RLC[L.c] || mood.lamp, s = Math.max(sw, sh), a = n * lit(L);
          if (L.k === "window") pool(x, y, Math.max(s * 0.9, D * 0.15), col, 0.6 * a, Math.min(1.8, Math.max(0.6, sh / Math.max(1, sw))));
          else if (L.k === "bulbs") pool(x, y + sh * 0.3, Math.max(sw * 0.7, D * 0.2), col, 0.9 * a, Math.min(1, Math.max(0.35, (sh + D * 0.2) / Math.max(1, sw))));
          else if (L.k === "fire" || L.k === "torch") pool(x, y, Math.max(s * 4, D * 0.32), col, 0.95 * a);
          else if (L.k === "chandelier") pool(x, y + sh * 0.6, Math.max(s * 3.5, D * 0.4), col, 0.9 * a, 1.1);
          else if (L.k === "candle") pool(x, y, Math.max(s * 5, D * 0.1), col, 0.75 * a);
          else if (L.k === "screen" || L.k === "glow") pool(x, y, Math.max(s * 2, D * 0.12), col, 0.75 * a);
          else pool(x, y + sh * 0.5, Math.max(s * 6, D * 0.42), col, 0.95 * a);   // a lamp, a lantern: light round it and below
        }
        g.drawImage(c, 0, 0, W, H);
      } else { g.fillStyle = rgb(m); g.fillRect(0, 0, W, H); }
    }
    g.globalCompositeOperation = "source-over";
    const hz = mood.haze || [12, 20, 52, 0.16];
    if (nt > 0.01) { g.fillStyle = rgb(hz, hz[3] * nt * (out ? 1 : 0.75)); g.fillRect(0, 0, W, H); }
    /* the lamps themselves glow over the night: a bright heart and a halo, flames alive, a string's bulbs in a row */
    if (n > 0.02 && LL.length) {
      const on = Math.min(1, n * 1.6);
      g.globalCompositeOperation = "lighter";
      const glow = (x, y, r, col, a) => { if (a < 0.01 || r < 0.5) return; const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, rgb(mix(col, [255, 255, 255], 0.35), Math.min(1, a))); gr.addColorStop(0.3, rgb(col, Math.min(1, a) * 0.55)); gr.addColorStop(1, rgb(col, 0)); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); };
      for (const L of LL) {
        if (L.k === "window") continue;
        const [x, y, sw, sh] = roomSpot(L, T), col = RLC[L.c] || mood.lamp, s = Math.max(sw, sh), a = on * lit(L);
        if (L.k === "bulbs") {   // the string's bulbs: small bright dots along the middle of its box, sagging a little
          const nb = Math.max(4, Math.min(16, Math.round(sw / Math.max(14, D * 0.03))));
          for (let i = 0; i < nb; i++) { const u = (i + 0.5) / nb, bx = x - sw / 2 + u * sw, by = y + Math.sin(u * Math.PI) * sh * 0.3 - sh * 0.15; glow(bx, by, Math.max(6, D * 0.018), col, 0.55 * a); }
        } else if (L.k === "screen" || L.k === "glow") glow(x, y, Math.max(s * 0.8, D * 0.02), col, 0.35 * a);
        else glow(x, y, Math.max(s * (FLAME[L.k] ? 1.1 : 0.9), D * 0.022), col, (L.k === "fire" ? 0.5 : 0.6) * a);
      }
      g.globalCompositeOperation = "source-over";
    }
  }
  /* the bare picture of a place, without people, at noon: what the server's painter repaints (infra/rabbit-art) */
  /* sky and sea in flat bands, the whole world wide, nothing on them */
  function backdrop(g, sky) {
    for (let i = 0; i < 7; i++) { const f0 = Math.pow(i / 7, 0.7), f1 = Math.pow((i + 1) / 7, 0.7); g.fillStyle = rgb(mix(sky.top, sky.bot, i / 6)); g.fillRect(-WW, HZ * f0, 3 * WW, HZ * (f1 - f0) + 1); }
    for (let i = 0; i < 4; i++) { const f0 = Math.pow(i / 4, 1.6), f1 = Math.pow((i + 1) / 4, 1.6); g.fillStyle = rgb(mix(sky.sea, sky.seaB, i / 3)); g.fillRect(-WW, lerp(HZ, WH, f0), 3 * WW, lerp(HZ, WH, f1) - lerp(HZ, WH, f0) + 1); }
  }
  function plate(id) {
    const c = document.createElement("canvas"); c.width = 1600; c.height = 900; const g = c.getContext("2d"), sky = skyAt(1);
    if (id === "island") {
      backdrop(g, sky);
      paintIsland(g);
      PALMS.forEach(([x, y], i) => palm(g, x, y, 0, i)); flag(g, 470, 470, 0, "#3b5f8a", "#fff", "wind"); flag(g, 606, 425, 900, "#c0533f", "#fff", "wave"); boat(g, 1110, 770, 0);
    } else {
      const r = document.createElement("canvas"); r.width = RW; r.height = RH; ROOMS[id](r.getContext("2d"), rnd(id.length * 131));   // its windows are cut out
      const h = S.hour; S.hour = 1; roomBackdrop(g, sky, 0); S.hour = h; g.drawImage(r, 0, 0); ROOMFX[id](g, 0, 1);
    }
    return c;
  }

  /* ---------- the stage ---------- */
  const S = { c: null, g: null, W: 0, H: 0, K: 1, base: null, world: null, wg: null, hour: 0, hourT: 0, clockAt: -1e9, cam: { x: 800, y: 450, z: 1 }, camT: { x: 800, y: 450, z: 1 },
    hover: null, locked: new Set(), pan: { x: 0, y: 0 }, gather: 0, room: null, roomA: 0, roomT: 0, cat: null, still: false, onFrame: null, last: 0 };
  function size() {
    const r = S.c.getBoundingClientRect(); S.K = Math.min(2, devicePixelRatio || 1);
    S.W = Math.max(1, r.width); S.H = Math.max(1, r.height);
    S.c.width = Math.round(S.W * S.K); S.c.height = Math.round(S.H * S.K);
    const e = painted("island") ? ART.wide || 0 : 0, BW = WW + 2 * e;   // a wide painting reaches past the world's sides
    const fit = Math.min(S.W / WW, S.H / WH), q = Math.min(fit * S.K * 1.6, 8192 / BW, 4096 / WH);
    if (!S.base || Math.abs(S.base.q - q) > 0.05 || S.base.e !== e || S.base.pending !== ART.pending) {
      const b = document.createElement("canvas"); b.width = Math.round(BW * q); b.height = Math.round(WH * q); b.q = q; b.e = e; b.pending = ART.pending;
      const g = b.getContext("2d"); g.scale(q, q); g.translate(e, 0); S.base = b;
      if (painted("island")) { g.imageSmoothingQuality = "high"; e ? g.drawImage(ART.img.island, -e, 0, BW, WH) : cover(g, ART.img.island, WW, WH); b.painted = true; }
      else if (ART.pending) backdrop(g, skyAt(S.hour));   // sea and sky only, until the painting is here
      else paintIsland(g);
    }
    if (S.focusId) focus(S.focusId, S.focusSide); else { S.camT = home(); if (!S.sized) { S.cam = { ...S.camT }; S.sized = true; } }
    S.world = S.world || document.createElement("canvas"); S.world.width = S.c.width; S.world.height = S.c.height; S.wg = S.world.getContext("2d");
  }
  /* world → screen: the whole world fits, the camera can lean in on a place */
  const fitScale = () => Math.min(S.W / WW, S.H / WH);
  function view(g) {
    const s = fitScale() * S.cam.z * S.K;
    g.setTransform(s, 0, 0, s, S.W * S.K / 2 - S.cam.x * s, S.H * S.K / 2 - S.cam.y * s);
  }
  function toWorld(px, py) { const s = fitScale() * S.cam.z; return [(px - S.W / 2) / s + S.cam.x, (py - S.H / 2) / s + S.cam.y]; }
  function toScreen(x, y) { const s = fitScale() * S.cam.z; return [(x - S.cam.x) * s + S.W / 2, (y - S.cam.y) * s + S.H / 2]; }

  function grainTile() {
    const c = document.createElement("canvas"); c.width = c.height = 160; const g = c.getContext("2d"), R = rnd(31);
    for (let i = 0; i < 1500; i++) { const x = R() * 160, y = R() * 160, d = R() < 0.5; g.fillStyle = d ? `rgba(34,48,58,${0.05 + R() * 0.07})` : `rgba(255,248,230,${0.05 + R() * 0.07})`; g.fillRect(x, y, 1 + (R() < 0.15), 1); }
    g.strokeStyle = "rgba(34,48,58,.025)"; for (let i = 0; i < 18; i++) { g.beginPath(); const y = R() * 160; g.moveTo(0, y); g.lineTo(160, y + (R() - 0.5) * 6); g.stroke(); }
    return c;
  }
  /* the light over a painted island: the whole picture (and the blurred sea beside it) multiplied with the light of the
     hour, a blue haze at night, and a sky of its own. The painting is seen from high up and shows only sea up to its top
     edge, so the scene gives it a horizon (ART.hz, the layout's "horizon", world units from the top): above that line,
     wherever the painting shows open sea, the sky of the hour takes over, with stars and a moon at night; the mountains,
     towers and islets that rise above the line stand in front of it, and nothing is ever drawn on them. Just under the
     line the far sea is a shade darker at night and hazier by day, so sea and sky never run into one another. A warm
     glow on the horizon at sunrise (east, on the left) and sunset (west, on the right). */
  const SEAPX = (r, g, b) => g - r > 38 && b > 135 && b >= g - 6;   // open sea in the painting: clearly blue-green, never the grey-blue rock
  function paintRect() {   // where the island painting lies in the world (as size() draws it)
    const im = ART.img.island, e = ART.wide || 0;
    if (e) return [-e, 0, WW + 2 * e, WH];
    const k = Math.max(WW / im.naturalWidth, WH / im.naturalHeight), iw = im.naturalWidth * k, ih = im.naturalHeight * k;
    return [(WW - iw) / 2, (WH - ih) / 2, iw, ih];
  }
  /* the land of the painting in the band above and just under the horizon, as a soft-edged picture: opaque where land is */
  function landMask() {
    const im = ART.img.island, hz = ART.hz || 110;
    if (S.land && S.land.im === im && S.land.hz === hz) return S.land;
    S.land = { im, hz, c: null };
    try {
      const [rx, ry, rw, rh] = paintRect(), band = Math.min(WH, hz + 48);
      const PX = rw / Math.min(im.naturalWidth, 5200);   // the painting's own pixels, so the thin outlines hold the flood below
      const mw = Math.round(rw / PX), mh = Math.round((band - ry) / PX), src = document.createElement("canvas"); src.width = mw; src.height = mh;
      const sg = src.getContext("2d"); sg.drawImage(im, 0, 0, im.naturalWidth, im.naturalHeight * (band - ry) / rh, 0, 0, mw, mh);
      const px = sg.getImageData(0, 0, mw, mh).data, sea = new Uint8Array(mw * mh), land = new Uint8Array(mw * mh).fill(1), st = [];
      for (let i = 0; i < mw * mh; i++) sea[i] = SEAPX(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) ? 1 : 0;
      /* open sea is what joins the edges of the band: a blue flag or a blue window inside its outline stays painted */
      const seed = i => { if (sea[i] && land[i]) { land[i] = 0; st.push(i); } };
      for (let x = 0; x < mw; x++) { seed(x); seed((mh - 1) * mw + x); }
      for (let y = 0; y < mh; y++) { seed(y * mw); seed(y * mw + mw - 1); }
      while (st.length) { const i = st.pop(), x = i % mw; if (x > 0) seed(i - 1); if (x < mw - 1) seed(i + 1); if (i >= mw) seed(i - mw); if (i < (mh - 1) * mw) seed(i + mw); }
      const out = sg.createImageData(mw, mh);
      for (let i = 0; i < mw * mh; i++) out.data[i * 4 + 3] = land[i] ? 255 : 0;
      sg.putImageData(out, 0, 0);
      const c = document.createElement("canvas"); c.width = mw; c.height = mh; const cg = c.getContext("2d");
      cg.filter = "blur(1px)"; cg.drawImage(src, 0, 0); cg.filter = "none"; cg.drawImage(src, 0, 0);   // soft at the edge, solid inside
      Object.assign(S.land, { c, rx, ry, rw, rh: band - ry, land, mw, mh, PX });
    } catch (e) {}   // a picture from another server without leave to read it: no sky over the painting, as before
    return S.land;
  }
  const isLand = (M, x, y, d = 4) => {   // land at a world point, or within d units of it: no star sits on an outline
    for (let dy = -d; dy <= d; dy += d) for (let dx = -d; dx <= d; dx += d) {
      const mx = Math.floor((x + dx - M.rx) / M.PX), my = Math.floor((y + dy - M.ry) / M.PX);
      if (mx < 0 || mx >= M.mw || my < 0) continue; if (my >= M.mh || M.land[my * M.mw + mx]) return true;
    }
    return false;
  };
  /* the moon: a lit disc with the dark part in the colour of the sky behind it (a faint earthshine), clean at every size */
  function moon(g, x, y, r, a, skyC) {
    const gr = g.createRadialGradient(x, y, r * 0.8, x, y, r * 4); gr.addColorStop(0, `rgba(251,243,223,${0.22 * a})`); gr.addColorStop(1, "rgba(251,243,223,0)");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, r * 4, 0, Math.PI * 2); g.fill();
    g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.clip();
    g.fillStyle = `rgba(251,243,223,${a})`; g.fillRect(x - r, y - r, r * 2, r * 2);
    g.fillStyle = `rgba(226,214,186,${0.5 * a})`; [[-0.35, 0.25, 0.22], [-0.05, -0.4, 0.14], [-0.5, -0.15, 0.1]].forEach(([u, v, s]) => { g.beginPath(); g.arc(x + u * r, y + v * r, s * r, 0, Math.PI * 2); g.fill(); });
    g.fillStyle = rgb(mix(skyC, [251, 243, 223], 0.1), a); g.beginPath(); g.arc(x + r * 0.55, y - r * 0.3, r * 0.92, 0, Math.PI * 2); g.fill();
    g.restore();
  }
  function paintedSky(g, sky, t, nt, wl, wt, wr) {
    const M = landMask(); if (!M || !M.c) return;
    const hz = ART.hz || 110, top = Math.min(wt, 0) - 20, bot = hz + 46;
    view(g); const s = fitScale() * S.cam.z * S.K, Hs = Math.ceil((bot - S.cam.y) * s + S.c.height / 2);
    if (Hs <= 0) return;
    const L = S.skyL || (S.skyL = document.createElement("canvas"));
    if (L.width !== S.c.width || L.height !== Math.min(S.c.height, Hs)) { L.width = S.c.width; L.height = Math.min(S.c.height, Hs); }
    const lg = L.getContext("2d"); lg.setTransform(1, 0, 0, 1, 0, 0); lg.clearRect(0, 0, L.width, L.height); lg.globalCompositeOperation = "source-over"; view(lg);
    /* the sky of the hour, lighter towards the horizon: at night a pale band of haze sits on the line */
    const glow = mix(sky.bot, [92, 108, 150], 0.45 * nt), x0 = wl - 20, w = wr - wl + 40;
    let gr = lg.createLinearGradient(0, top, 0, hz); gr.addColorStop(0, rgb(sky.top)); gr.addColorStop(0.72, rgb(mix(sky.top, sky.bot, 0.75))); gr.addColorStop(1, rgb(glow));
    lg.fillStyle = gr; lg.fillRect(x0, top, w, hz - top);
    /* stars, thinner near the horizon, never on land */
    if (nt > 0.05) {
      if (!S.stars || S.stars.M !== M || S.stars.hz !== hz) {
        const R = rnd(9), list = [], e = ART.wide || 0;
        for (let i = 0; i < 900 && list.length < 230; i++) { const x = -e - 900 + R() * (WW + 2 * e + 1800), y = -400 + R() * (hz - 8 + 400), r = 0.7 + R() * 1.7, ph = R() * 6.3; if (!isLand(M, x, y)) list.push([x, y, r, ph]); }
        const cand = [[110, 50], [150, 44], [60, 52], [1500, 52], [1440, 44], [1660, 50], [-60, 50]];   // left first: the buttons sit top right
        S.stars = { M, hz, list, moon: cand.find(([x, y]) => [[0, 0], [-34, 0], [34, 0], [0, -34], [0, 34], [-24, 24], [24, 24]].every(([a, b]) => !isLand(M, x + a, y + b) && y + b < hz - 6)) };
      }
      S.stars.list.forEach(([x, y, r, ph], i) => {
        if (x < wl - 10 || x > wr + 10 || y < wt - 10) return;
        const al = nt * (0.35 + (i % 5) * 0.13) * (0.7 + 0.3 * Math.sin(t * 0.002 + ph)) * Math.min(1, (hz - y) / 40);
        lg.fillStyle = `rgba(251,243,223,${al})`; lg.fillRect(x - r, y - 0.5, r * 2, 1); lg.fillRect(x - 0.5, y - r, 1, r * 2);
      });
      const mo = S.stars.moon;
      if (mo && nt > 0.2) moon(lg, mo[0], mo[1], 13, Math.min(1, (nt - 0.2) * 2), mix(sky.top, sky.bot, Math.max(0, (mo[1] - top) / (hz - top))));
    }
    /* the line itself: a thin light edge, and under it the far sea a shade darker at night, hazier by day */
    lg.fillStyle = rgb(mix([235, 242, 250], [150, 170, 215], nt), 0.55 - 0.15 * nt); lg.fillRect(x0, hz - 0.6, w, 1.2);
    gr = lg.createLinearGradient(0, hz, 0, bot);
    const under = mix([226, 238, 248], [3, 8, 24], nt), ua = lerp(0.3, 0.5, nt);
    gr.addColorStop(0, rgb(under, ua)); gr.addColorStop(1, rgb(under, 0));
    lg.fillStyle = gr; lg.fillRect(x0, hz, w, bot - hz);
    /* what stands above the line stays in front of it */
    lg.globalCompositeOperation = "destination-out"; lg.imageSmoothingQuality = "high";
    lg.drawImage(M.c, M.rx, M.ry, M.rw, M.rh); lg.globalCompositeOperation = "source-over";
    g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(L, 0, 0); view(g);
  }
  function paintedLight(g, W, H, sky, t, nt, wl, wt, wr) {
    const m = sky.mul;
    g.setTransform(1, 0, 0, 1, 0, 0);
    if (m[0] + m[1] + m[2] < 762) {   // the light of the hour; after dusk with the lamps of the island in it (lightMap)
      g.globalCompositeOperation = "multiply";
      if (lampsOn(sky) > 0) g.drawImage(lightMap(W, H, m, lampsOn(sky), t), 0, 0, W, H); else { g.fillStyle = rgb(m); g.fillRect(0, 0, W, H); }
    }
    g.globalCompositeOperation = "source-over";
    if (nt > 0.01) { g.fillStyle = `rgba(12,20,52,${0.16 * nt})`; g.fillRect(0, 0, W, H); }
    paintedSky(g, sky, t, nt, wl, wt, wr);
    view(g);
    const HZ = ART.hz || 110;   // the glow sits on the painted horizon
    /* sunrise and sunset: a soft warm light along the horizon on the side of the sun */
    const hh = ((S.hour % 4) + 4) % 4, rise = Math.max(0, 1 - Math.abs(hh - 3.75) / 0.5) + Math.max(0, 1 - Math.abs(hh + 0.25) / 0.5) * (hh < 0.5 ? 1 : 0),
      set = Math.max(0, 1 - Math.abs(hh - 2.25) / 0.7);
    [[rise, wl + (wr - wl) * 0.18, [255, 168, 120]], [set, wl + (wr - wl) * 0.8, [255, 128, 70]]].forEach(([a, x, c]) => {
      if (a < 0.02) return; const rr = (wr - wl) * 0.55, gr = g.createRadialGradient(x, HZ, 0, x, HZ, rr);
      gr.addColorStop(0, rgb(c, 0.34 * a)); gr.addColorStop(0.5, rgb(c, 0.1 * a)); gr.addColorStop(1, rgb(c, 0));
      g.globalCompositeOperation = "screen"; g.fillStyle = gr; g.fillRect(x - rr, HZ - rr, rr * 2, rr * 2); g.globalCompositeOperation = "source-over";
    });
  }
  function frame(t) {
    const dt = Math.min(64, t - (S.last || t)); S.last = t;
    const k = 1 - Math.pow(0.0025, dt / 1000);
    if (!LIGHT.game && t - S.clockAt > (LIGHT.fast ? 60 : 1000)) {   // the clock, once a second: the nearest way round, never back through the day
      S.clockAt = t; const h = clockHour(berlinMinutes());
      if (!S.clockOn) { S.clockOn = true; S.hour = S.hourT = h; } else S.hourT = h + 4 * Math.round((S.hour - h) / 4);
    }
    S.hour += (S.hourT - S.hour) * Math.min(1, k * 0.9);
    if (S.hour > 8 || S.hour < 0) { const d = S.hour > 8 ? -4 : 4; S.hour += d; S.hourT += d; }
    for (const p of ["x", "y", "z"]) S.cam[p] += (S.camT[p] - S.cam[p]) * Math.min(1, k * 1.3);
    const g = S.g, W = S.c.width, H = S.c.height, sky = skyAt(S.hour);
    g.setTransform(1, 0, 0, 1, 0, 0);
    /* sky, from the top of the screen to the horizon: printed in flat bands, as a poster would be */
    view(g); const hzY = (HZ - S.cam.y) * fitScale() * S.cam.z * S.K + H / 2;
    g.setTransform(1, 0, 0, 1, 0, 0);
    const NB = 7, top = Math.min(0, hzY - H), bands = () => {
      for (let i = 0; i < NB; i++) { const f0 = Math.pow(i / NB, 0.7), f1 = Math.pow((i + 1) / NB, 0.7); g.fillStyle = rgb(mix(sky.top, sky.bot, i / (NB - 1))); g.fillRect(0, lerp(top, hzY, f0), W, lerp(top, hzY, f1) - lerp(top, hzY, f0) + 1); }
      /* the sea, from the horizon down, in four bands */
      for (let i = 0; i < 4; i++) { const f0 = Math.pow(i / 4, 1.6), f1 = Math.pow((i + 1) / 4, 1.6); g.fillStyle = rgb(mix(sky.sea, sky.seaB, i / 3)); g.fillRect(0, lerp(hzY, H, f0), W, lerp(hzY, H, f1) - lerp(hzY, H, f0) + 1); }
    };
    bands();
    view(g);
    const [wl] = toWorld(0, 0), [wr, wb] = toWorld(S.W, S.H), [, wt] = toWorld(0, 0);
    const pb = !!(S.base && S.base.painted), wait = !pb && ART.pending;   // wait: the painting is on its way, the bare sky and sea show
    const sk = !pb && !wait;   // a painted island brings its own sky: no drawn sun, moon, clouds or gulls over it
    if (pb && (wl < -(ART.wide || 0) || wr > WW + (ART.wide || 0))) sides(g, wl, wt, wr, wb);
    /* stars as small printed crosses, the sun as a disc in rings with slow rays, the moon as a crescent */
    const nt = Math.max(0, 1 - Math.abs((S.hour % 4) - 3) * 1.4);
    if (sk && nt > 0) { const R = rnd(9); for (let i = 0; i < 140; i++) { const x = wl + R() * (wr - wl), y = wt + R() * (HZ - wt - 10), r = 0.8 + R() * 1.8, al = nt * (0.35 + R() * 0.65) * (0.7 + 0.3 * Math.sin(t * 0.002 + i)); g.fillStyle = `rgba(251,243,223,${al})`; g.fillRect(x - r, y - 0.5, r * 2, 1); g.fillRect(x - 0.5, y - r, 1, r * 2); } }
    const hh = S.hour % 4, sunX = lerp(300, 1350, Math.min(1, hh / 2.4)), sunY = HZ - Math.sin(Math.min(1, hh / 2.4) * Math.PI * 0.95 + 0.08) * 170 + (hh > 2 ? (hh - 2) * 90 : 0);
    if (sk && hh < 2.75) {
      g.save(); g.beginPath(); g.rect(wl - 10, wt - 10, wr - wl + 20, HZ - wt + 10); g.clip();
      g.save(); g.translate(sunX, sunY); g.rotate(t * 0.00004);
      g.fillStyle = rgb(sky.sun, 0.16); for (let k = 0; k < 16; k++) { g.rotate(Math.PI / 8); g.beginPath(); g.moveTo(0, 0); g.lineTo(-24, -420); g.lineTo(24, -420); g.closePath(); g.fill(); }
      g.restore();
      [[96, 0.16], [70, 0.24], [48, 0.4]].forEach(([r, al]) => { g.fillStyle = rgb(sky.sun, al); g.beginPath(); g.arc(sunX, sunY, r, 0, Math.PI * 2); g.fill(); });
      g.fillStyle = rgb(sky.sun); g.beginPath(); g.arc(sunX, sunY, 30, 0, Math.PI * 2); g.fill();
      g.strokeStyle = "rgba(34,48,58,.25)"; g.lineWidth = 1.2; g.stroke();
      g.restore();
    }
    if (sk && nt > 0.2) {
      moon(g, 1220, 120, 18, nt, mix(sky.top, sky.bot, 0.5));
    }
    /* clouds drift by */
    if (sk) for (let i = 0; i < 6; i++) { const span = (wr - wl) + 600, x = wl - 300 + ((t * 0.006 * (1 + i * 0.2) + i * 380) % span), y = 80 + (i * 53) % 140; cloud(g, x, y, 0.7 + (i % 3) * 0.3, (0.55 - nt * 0.47) * (1 - i * 0.05)); }
    /* the sea moves: rows of little scalloped waves that grow toward the viewer, and a broken path of light */
    g.lineCap = "round"; g.lineJoin = "round";
    const foam = `rgba(251,243,223,${0.34 * (1 - nt * 0.55)})`, under = `rgba(16,40,60,${0.2 * (1 - nt * 0.3)})`;
    if (!wait) for (let r = 0; r < 30; r++) {
      const y = HZ + 8 + r * r * 0.7, sc = 2.6 + r * 0.42, gap = 70 + r * 9; if (y > wb + 20) break;
      g.lineWidth = 0.8 + r * 0.05;
      const drift = Math.sin(t * 0.0009 + r * 0.8) * gap * 0.25;
      for (let x = wl - gap + ((r * 53) % gap) + (r % 2) * gap / 2 + drift; x < wr + gap; x += gap) {
        const bob = Math.sin(t * 0.002 + x * 0.05 + r) * 1.2;
        g.strokeStyle = under; g.beginPath(); g.arc(x, y + bob + 1.2, sc, Math.PI * 1.1, Math.PI * 1.9); g.stroke();
        g.strokeStyle = foam; g.beginPath(); g.arc(x, y + bob, sc, Math.PI * 1.1, Math.PI * 1.9); g.arc(x + sc * 1.6, y + bob, sc * 0.8, Math.PI * 1.15, Math.PI * 1.85); g.stroke();
      }
    }
    const gx = hh < 2.75 ? sunX : 1220;
    if (sk) for (let i = 0; i < 26; i++) { const y = HZ + 6 + i * i * 0.5, w0 = 6 + i * 2, f = Math.sin(t * 0.003 + i * 1.7); if (f < 0.15) continue; g.fillStyle = rgb(hh < 2.75 ? sky.sun : [251, 243, 223], f * 0.55 * (1 - i / 26)); g.fillRect(gx - w0 / 2 + Math.sin(i * 3.1 + t * 0.001) * w0 * 0.6, y, w0, 2); }
    /* the island and everything on it, drawn on one layer so the light of the hour tints it in one go */
    const w = S.wg; w.setTransform(1, 0, 0, 1, 0, 0); w.clearRect(0, 0, W, H); view(w);
    const pi = !!S.base.painted;   // the painted island has its own palms, flags and boat
    if (!wait) {
      /* surf: a pale ring that comes and goes around the coast */
      const surf = 0.5 + 0.5 * Math.sin(t * 0.0015);
      w.strokeStyle = `rgba(255,255,255,${0.25 + surf * 0.35})`; w.lineWidth = 3; shape(w, 1.015 + surf * 0.012, 2); w.stroke();
      w.strokeStyle = `rgba(255,255,255,${0.12 * (1 - surf)})`; w.lineWidth = 2; shape(w, 1.05 + surf * 0.02, 4); w.stroke();
      w.drawImage(S.base, -S.base.e, 0, WW + 2 * S.base.e, WH);
      islandFx(w, t, sky.light);
    }
    if (!pi && !wait) { flag(w, 470, 470, t, "#3b5f8a", "#fff", "wind"); flag(w, 606, 425, t + 900, "#c0533f", "#fff", "wave"); boat(w, 1110, 770, t); }
    /* palms and people in depth order */
    const items = pi || wait ? [] : PALMS.map(([x, y], i) => [y, () => palm(w, x, y, t, i)]);
    if (!pi && !wait) FOLK.forEach((f, i) => {   // on the painted island nobody walks for now: only the white rabbit
      if (!S.still) { f.k += f.v * dt * f.dir; if (f.k > 1 || f.k < 0) { f.dir *= -1; f.k = Math.max(0, Math.min(1, f.k)); } }
      let [x, y] = alongPath(f.path, f.k);
      if (S.gather > 0) { const a = i / FOLK.length * Math.PI * 2, gx2 = SPOT.gather[0] + Math.cos(a) * 70, gy2 = SPOT.gather[1] + Math.sin(a) * 18; x = lerp(x, gx2, S.gather); y = lerp(y, gy2, S.gather); }
      items.push([y, () => person(w, x, y, t, f, i)]);
    });
    if (!wait) { rabbitStep(S.still ? 999 : dt, t); items.push([RB.y, () => rabbit(w, t)]); }
    if (S.cat && (wait || (pi && !painted("deja")))) S.cat = null;
    if (S.cat) {
      const c = S.cat, f = (t - c.t0) / c.d; if (f > 1) S.cat = c.twice ? { ...c, t0: t, twice: false } : null;
      else if (pi) items.push([700, () => creature(w, ART.img.deja, lerp(c.x0, c.x1, f), lerp(c.y0, c.y1, f) + Math.abs(Math.sin(t * 0.012)) * -1.5, 22)]);
      else items.push([700, () => cat(w, lerp(c.x0, c.x1, f), lerp(c.y0, c.y1, f), t, c.x1 > c.x0 ? 1 : -1)]);
    }
    if (pi && painted("agorzilla") && !S.focusId && S.roomA < 0.05 && !RARE.zilla && t > RARE.next) {
      const J = SPOT.jungle, [x, y] = J[Math.floor(Math.random() * J.length)];
      RARE.zilla = { t0: t, d: FORCE ? 30000 : 7500, x, y };
      RARE.next = t + (FORCE ? 40000 : 150000 + Math.random() * 210000);   // every few minutes, never on cue
    }
    if (RARE.zilla) {
      const z = RARE.zilla, f = (t - z.t0) / z.d;
      if (f > 1) RARE.zilla = null;
      else { const a = Math.min(1, f * 6, (1 - f) * 6); items.push([z.y, () => { z.box = creature(w, ART.img.agorzilla, z.x, z.y + (1 - a) * 8, 48, a); }]); }
    }
    if (SHIP.s && !wait) shipItems(items, w, t, sky);
    items.sort((a, b) => a[0] - b[0]).forEach(([, d]) => d());
    if (SHIP.pings.length && !wait) shipPings(w, t);
    /* the light of the hour */
    w.setTransform(1, 0, 0, 1, 0, 0);
    if (!pi && sky.tint[3] > 0.01) { w.globalCompositeOperation = "source-atop"; w.fillStyle = rgb(sky.tint, sky.tint[3]); w.fillRect(0, 0, W, H); w.globalCompositeOperation = "source-over"; }
    g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(S.world, 0, 0);
    if (pi) paintedLight(g, W, H, sky, t, nt, wl, wt, wr);
    /* evening and night: windows glow, the radio mast blinks, the lighthouse sweeps its green beam */
    view(g);
    if (sky.light > 0.05 && !wait) {
      g.globalCompositeOperation = "lighter";
      WINDOWS.forEach(([x, y, ww, wh], i) => { const fl = 0.85 + 0.15 * Math.sin(t * 0.003 + i * 2.1); g.fillStyle = `rgba(255,190,90,${sky.light * (pi ? 0.3 : 0.75) * fl})`; if (pi) { g.beginPath(); g.arc(x + ww / 2, y + wh / 2, Math.max(ww, wh) * 0.7, 0, Math.PI * 2); g.fill(); } else g.fillRect(x, y, ww, wh); g.fillStyle = `rgba(255,170,70,${sky.light * 0.08})`; g.beginPath(); g.arc(x + ww / 2, y + wh / 2, 8, 0, Math.PI * 2); g.fill(); });
      shipWindows(g, t, sky.light);
      islandGlow(g, t, sky.light);
      const a = t * 0.0006, [bx, by] = SPOT.beam;
      gr = g.createRadialGradient(bx, by, 0, bx, by, 520); gr.addColorStop(0, `rgba(57,255,138,${0.42 * sky.light})`); gr.addColorStop(1, "rgba(57,255,138,0)");
      g.fillStyle = gr; g.beginPath(); g.moveTo(bx, by); g.arc(bx, by, 520, a - 0.08, a + 0.08); g.closePath(); g.fill();
      g.globalCompositeOperation = "source-over";
      if (lampsOn(sky) > 0) nightLamps(g, t, lampsOn(sky));
    }
    if (!wait) {   // the lighthouse lamp and the red light on the radio mast
      g.fillStyle = `rgba(57,255,138,${0.65 + 0.35 * Math.sin(t * 0.004)})`; g.beginPath(); g.arc(SPOT.beam[0], SPOT.beam[1], 4.5, 0, Math.PI * 2); g.fill();
      if (Math.floor(t / 700) % 2) { g.fillStyle = "#ff4a3a"; g.beginPath(); g.arc(SPOT.blink[0], SPOT.blink[1], 3, 0, Math.PI * 2); g.fill(); }
    }
    /* gulls */
    if (sk) for (let i = 0; i < 4; i++) { const x = wl + ((t * 0.02 * (1 + i * 0.15) + i * 420) % ((wr - wl) + 200)) - 100, y = 170 + i * 26 + Math.sin(t * 0.0009 + i) * 18; gull(g, x, y, t, i); }
    /* the painting has just come: for half a second it rises out of the bare sky and sea it was waiting on (counted from
       the end of its first frame, which takes longest) */
    if (pb && ART.fade) {
      const now = performance.now(), f = ART.fade === true ? 0 : (now - ART.fade) / 500; if (ART.fade === true) ART.fade = now;
      if (f >= 1) ART.fade = 0; else { g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1 - f; bands(); g.globalAlpha = 1; }
    }
    /* inside a place: the room opens from the place in a widening circle and fills the view */
    S.roomA += (S.roomT - S.roomA) * Math.min(1, k * 1.15); if (Math.abs(S.roomT - S.roomA) < 0.004) S.roomA = S.roomT;
    if (S.room && S.roomA > 0.004) {
      const rw = roomW(S.room), a = S.roomA, e = a * a * (3 - 2 * a), phone = S.W < 760, zz = 1.06 + (1 - e) * 0.18, sc = Math.max(W / rw, H / RH) * zz;
      let ox = (W - rw * sc) / 2 - (phone ? 0 : S.focusSide * W * 0.16), oy = (H - RH * sc) / 2 - (phone ? H * 0.16 : 0);
      ox = Math.min(0, Math.max(W - rw * sc, ox)) + (rw - RW) / 2 * sc; oy = Math.min(0, Math.max(H - RH * sc, oy));
      w.setTransform(1, 0, 0, 1, 0, 0); w.clearRect(0, 0, W, H); w.setTransform(sc, 0, 0, sc, ox, oy);
      const day = Math.max(0, 1 - sky.light);
      if (painted(S.room)) { w.drawImage(roomImage(S.room), (RW - rw) / 2, 0, rw, RH); w.save(); roomLife(w, t, day); w.restore(); }
      else { roomBackdrop(w, sky, t); w.drawImage(roomImage(S.room), 0, 0, RW, RH); w.save(); ROOMFX[S.room](w, t, day); w.restore(); }
      if (S.roomCat) {   // Déjà, now and then, somewhere in the room: far at the back, or close by at the side
        const c = S.roomCat, a = Math.min(1, Math.max(0, (t - c.t0) / 900));
        const b = creature(w, ART.img.deja, c.x, c.y, c.h, a * e);
        S.roomCat.screen = [(b[0] * sc + ox) / S.K, (b[1] * sc + oy) / S.K, b[2] * sc / S.K, b[3] * sc / S.K];
      }
      S.hostAt = null;
      if (S.hostFn) {
        if (!S.hostC) { S.hostC = document.createElement("canvas"); S.hostC.width = S.hostC.height = 800; }
        const hg = S.hostC.getContext("2d"); S.hostFn(hg, t);
        /* a medium shot: in the middle of the room the card leaves free, eyes about a third down, standing on the radio
           bar instead of behind it, so the room around them (window, desk, map) still tells where we are */
        const cw = Math.min(470, S.W * 0.42) * S.K + 32 * S.K, fx = S.focusSide > 0 ? (W - cw) / 2 : S.focusSide < 0 ? cw + (W - cw) / 2 : W / 2;
        /* on a wide screen a painted person stands large in the room, the body running on behind the radio strip at the
           bottom of the screen, so they are there and not cut off; a drawn face stands clear above the strip */
        const tall = !phone && S.hostTall, hb = phone ? (S.hostBottom || S.H * 0.47) * S.K : tall ? H + 6 * S.K : H - 74 * S.K,
          hs = phone ? Math.max(W * 0.34, Math.min(W * 0.9, (hb - 6 * S.K) / 0.74)) : tall ? Math.min(H * 0.9, W * 0.62) : Math.min(H * 0.5, (W - cw) * 0.5),
          hx = phone ? W / 2 : fx, hy = hb - hs * (phone ? 0.74 : 0.99) + (1 - e) * hs * 0.25;
        let [X, Y, Z] = [hx, hy, hs];
        /* a phone held sideways: the plate stands on the right, the one you talk to in the free room on its left, large */
        if (!phone && S.hostLeft) { const fw = S.hostLeft * S.K; Z = Math.min(fw * 0.95, H * (S.hostTall ? 1.05 : 0.8)); X = fw / 2; Y = (S.hostTall ? H + 6 * S.K : H - 52 * S.K) - Z * 0.99; }
        w.setTransform(1, 0, 0, 1, 0, 0); w.drawImage(S.hostC, X - Z / 2, Y, Z, Z); S.hostAt = [X, Y, Z];
      }
      w.setTransform(1, 0, 0, 1, 0, 0);
      if (painted(S.room)) roomLight(w, W, H, sky, nt, t, S.room, [sc, ox, oy, rw, ART.img[S.room]]);
      else if (sky.tint[3] > 0.01) { w.globalCompositeOperation = "source-atop"; w.fillStyle = rgb(sky.tint, sky.tint[3] * 0.75); w.fillRect(0, 0, W, H); w.globalCompositeOperation = "source-over"; }
      if (sky.light > 0.05 && !painted(S.room)) { w.globalCompositeOperation = "lighter"; const lg = w.createRadialGradient(W / 2, H * 0.45, 0, W / 2, H * 0.45, Math.max(W, H) * 0.6); lg.addColorStop(0, `rgba(255,190,110,${0.22 * sky.light})`); lg.addColorStop(1, "rgba(255,190,110,0)"); w.fillStyle = lg; w.fillRect(0, 0, W, H); w.globalCompositeOperation = "source-over"; }
      const [px, py] = S.roomAt || [S.W / 2, S.H / 2], cx = px * S.K, cy = py * S.K, rr = e * Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) * 1.02;
      g.setTransform(1, 0, 0, 1, 0, 0); g.save(); g.beginPath(); g.arc(cx, cy, Math.max(1, rr), 0, Math.PI * 2); g.clip(); g.drawImage(S.world, 0, 0); g.restore();
      if (a < 0.999) { g.strokeStyle = INK; g.lineWidth = 6 * S.K; g.beginPath(); g.arc(cx, cy, Math.max(1, rr), 0, Math.PI * 2); g.stroke(); g.strokeStyle = P.cream; g.lineWidth = 2.5 * S.K; g.stroke(); }
    }
    /* the paper: a fine grain over everything and the edges a shade darker, as on a print */
    g.setTransform(1, 0, 0, 1, 0, 0);
    if (!S.grain) S.grain = g.createPattern(grainTile(), "repeat");
    g.fillStyle = S.grain; g.fillRect(0, 0, W, H);
    if (painted("fronds") && S.roomA < 0.99) fronds(g, t, 1 - S.roomA);
    if (!S.vig || S.vig.w !== W || S.vig.h !== H) { const v = g.createRadialGradient(W / 2, H * 0.55, Math.min(W, H) * 0.45, W / 2, H * 0.55, Math.hypot(W, H) * 0.62); v.addColorStop(0, "rgba(34,48,58,0)"); v.addColorStop(1, "rgba(34,48,58,.28)"); S.vig = { g: v, w: W, h: H }; }
    g.fillStyle = S.vig.g; g.fillRect(0, 0, W, H);
    if (S.onFrame) S.onFrame(t);
    requestAnimationFrame(frame);
  }

  const inPoly = (P, x, y) => { let c = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const [xi, yi] = P[i], [xj, yj] = P[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; } return c; };
  const inBox = (b, x, y) => b && x >= b[0] && x <= b[0] + b[2] && y >= b[1] && y <= b[1] + b[3];
  /* a quarter that is there but not open yet (S.locked): the game shows only a "?" over it, nothing to click */
  function lockedAt(px, py) {
    if (S.roomA > 0.3 || (ART.pending && !(S.base && S.base.painted))) return null;
    const [x, y] = toWorld(px, py);
    for (const id of S.locked) { const p = PLACES[id]; if (p && (p.poly ? inPoly(p.poly, x, y) : inBox(p.box, x, y))) return id; }
    return null;
  }
  function hit(px, py) {
    if (S.roomA > 0.3) return S.roomCat && inBox(S.roomCat.screen, px, py) ? "deja" : null;   // inside a place the island is out of reach
    if (ART.pending && !(S.base && S.base.painted)) return null;   // the painting is on its way: nothing to point at on the bare sea yet
    const [x, y] = toWorld(px, py);
    if (RARE.zilla && inBox(RARE.zilla.box, x, y)) return "agorzilla";
    if (Math.abs(x - RB.x) < 16 && y < RB.y + 6 && y > RB.y - 30) return "rabbit";
    for (const id in PLACES) {
      if (S.locked.has(id)) continue;
      const p = PLACES[id];
      if (p.poly ? inPoly(p.poly, x, y) : inBox(p.box, x, y)) return id;
    }
    /* a finger is wider than a small place on a phone: the nearest place within 22 px of the tap counts too */
    const tol = 22 / (fitScale() * S.cam.z); let best = null, bd = tol;
    for (const id in PLACES) {
      if (S.locked.has(id)) continue; const [bx, by, bw, bh] = PLACES[id].box;
      const d = Math.hypot(Math.max(bx - x, 0, x - bx - bw), Math.max(by - y, 0, y - by - bh)); if (d < bd) { bd = d; best = id; }
    }
    return best;
  }
  /* lean in on a place, keeping the space for the card on the far side; null goes back to the whole cove */
  /* the whole island, as large as the screen allows: on a tall phone the island fills the width, the sky gives way */
  const home = () => pan(homeBase());
  function homeBase() {
    /* a painted island framed as a whole picture is always seen whole; beside it on a wide screen the painting's own
       blurred sea carries on, and the painted leaves in front (paint.py creatures: fronds) cover the seam at the sides */
    if (ART.whole && S.W >= 760) return { x: 800, y: 450, z: 1 };
    const f = fitScale(), z = Math.max(1, Math.min(S.W / ((S.W < 760 && S.H > S.W ? 940 : 1220) * f), S.H / (690 * f)));   // a phone held upright comes closer; a drag shows the rest
    return ({ x: 800, y: z > 1.05 ? Math.max(450, 900 - S.H / (f * z) / 2 - 10) : 450, z });
  }
  /* on a screen that shows only part of the island (a phone held upright), a drag moves the view; it stops at the edges */
  function pan(c) {
    const s = fitScale() * c.z, hw = S.W / s / 2, hh = S.H / s / 2, e = painted("island") ? ART.wide || 0 : 0;
    const cl = (v, lo, hi) => (lo > hi ? (lo + hi) / 2 : Math.max(lo, Math.min(hi, v)));
    return { x: cl(c.x + S.pan.x, hw - e, WW + e - hw), y: cl(c.y + S.pan.y, hh, WH - hh), z: c.z };
  }
  const canPan = () => { const c = homeBase(), s = fitScale() * c.z; return S.W / s < WW - 4 || S.H / s < WH - 4; };
  function focus(id, side = 0) {
    if (!id) { S.camT = home(); S.focusId = null; S.roomT = 0; S.roomCat = null; S.left = true; return; }
    if (ROOMS[id] || painted(id)) {
      if (S.room !== id || S.left) {
        if (S.room !== id && S.roomA > 0.5) S.roomA = 0.35;
        S.room = id; S.left = false;
        const near = Math.random() < 0.3;   // one visit in six or so, she is there too
        S.roomCat = painted(id) && painted("deja") && (FORCE || Math.random() < 0.17) ? (near
          ? { x: Math.random() < 0.5 ? 170 : 1430, y: 905, h: 250, t0: performance.now() }
          : { x: 320 + Math.random() * 960, y: 600 + Math.random() * 40, h: 70, t0: performance.now() }) : null;
      }
      S.roomT = 1; S.roomAt = toScreen(...(PLACES[id].c || [PLACES[id].x, PLACES[id].y - 40]));
    }
    else S.roomT = 0;   // a quarter without a painted picture yet: the card opens over the island
    S.focusId = id; S.focusSide = side;
    const p = PLACES[id], phone = S.W < 760, z = Math.max(home().z * 1.25, phone ? 1.5 : 1.7), s = fitScale() * z;
    const shift = side * (S.W * 0.22) / s;   // the card takes about the right (or left) half
    S.camT = { x: p.x + shift, y: phone ? p.y + (0.5 - 0.17) * S.H / s - 30 : p.y - 30, z };   // on a phone the sheet covers the lower part
  }
  function mount(canvas) {
    S.c = canvas; S.g = canvas.getContext("2d");
    S.still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    size(); addEventListener("resize", size);
    /* drag to look around (only where the island does not fit whole and nothing is open); a drag is not a tap */
    let drag = null, dragged = 0;
    canvas.addEventListener("pointerdown", e => { if (!S.focusId && S.roomA < 0.3) drag = { x: e.clientX, y: e.clientY, px: S.pan.x, py: S.pan.y, moved: false }; });
    addEventListener("pointermove", e => {
      if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 10) return; if (!canPan()) return;
      drag.moved = true; const s = fitScale() * S.camT.z;
      S.pan = { x: drag.px - dx / s, y: drag.py - dy / s };
      const b = homeBase(), c = pan(b); S.pan = { x: c.x - b.x, y: c.y - b.y };   // held at the edges
      S.camT = c; S.cam.x = c.x; S.cam.y = c.y;
    });
    addEventListener("pointerup", () => { if (drag && drag.moved) dragged = performance.now(); drag = null; });
    addEventListener("pointercancel", () => { drag = null; });
    canvas.addEventListener("click", e => { if (performance.now() - dragged < 350) { e.stopImmediatePropagation(); e.preventDefault(); } });
    canvas.style.touchAction = "none";
    canvas.addEventListener("pointermove", e => {   // the leaves in front lean away from the pointer, a little
      const r = canvas.getBoundingClientRect(); S.peek = Math.max(-1, Math.min(1, ((e.clientX - r.left) / r.width - 0.5) * 2));
    });
    if (window.ResizeObserver) new ResizeObserver(size).observe(canvas);
    requestAnimationFrame(frame);
  }
  window.COVE_SCENE = {
    mount, hit, focus, places: PLACES, toScreen, canPan: () => canPan(),
    setHour(h, now) { if (!LIGHT.game) return; S.hourT = h; if (now) S.hour = h; },   // the light follows the clock in Germany (see CLOCK)
    clock: () => { const m = Math.floor(berlinMinutes()); return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); },
    host(fn, tall) { S.hostFn = fn; S.hostTall = !!tall; },
    lock(ids) { S.locked = new Set(ids); }, locked: id => S.locked.has(id), lockedAt,   // quarters not open yet cannot be clicked, only show a "?"
    hostAt(bottom, left) { S.hostBottom = bottom; S.hostLeft = left || null; },
    gather(v) { S.gather = v; },
    cat(twice) { S.cat = { t0: performance.now(), d: 9000, x0: SPOT.cat[0], y0: SPOT.cat[1], x1: SPOT.cat[2], y1: SPOT.cat[3], twice: !!twice }; },
    onFrame(f) { S.onFrame = f; },
    /* the cruise ship in port or coming in (relay cruise.py: {name, style, phase, t0, end, at}), null when there is none;
       ping(place): one of its passengers' transactions was sealed there */
    ship(v) { SHIP.s = v || null; },
    ping(id) { if (PLACES[id] && SHIP.pings.length < 40) SHIP.pings.push({ id, t0: performance.now() + Math.random() * 400 }); },
    /* the rabbit hops to a place and waits beside it (null: it wanders) */
    rabbit(id) { RB.goal = id; if (id && PLACES[id]) { const p = PLACES[id]; RB.tx = p.x + (id === "book" ? 46 : 0) + (p.x > 800 ? -40 : 40); RB.ty = p.y + 16; } },
    get hour() { return S.hour; },
    plate, art: ART,
  };
})();
