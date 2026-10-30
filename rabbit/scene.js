/* The island: a small tropical island drawn in the visitor's browser (no photographs, no image files).
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
    let r = 1 + 0.05 * Math.sin(a * 3 + 1) + 0.035 * Math.sin(a * 7 + 2) + (R0() - 0.5) * 0.02;
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
    south:  { x: 650, y: 425, box: [600, 360, 110, 85], name: "South Current Embassy" },
    bar:    { x: 1215, y: 640, box: [1140, 575, 160, 95], name: "Bar La Ola" },
    book:   { x: 300, y: 600, box: [255, 395, 95, 225], name: "The Lighthouse" },
    pier:   { x: 1010, y: 735, box: [950, 690, 170, 80], name: "The pier" },
  };

  /* times of day: 0 morning, 1 noon, 2 evening, 3 night (the game moves between them) */
  const SKY = [
    { top: [92, 160, 220], bot: [255, 214, 170], sea: [38, 140, 170], seaB: [20, 92, 130], sun: [255, 236, 190], tint: [255, 214, 170, 0.06], light: 0 },
    { top: [40, 130, 220], bot: [160, 214, 245], sea: [24, 150, 190], seaB: [10, 90, 140], sun: [255, 250, 230], tint: [255, 255, 255, 0], light: 0 },
    { top: [70, 60, 140], bot: [255, 140, 90], sea: [60, 80, 130], seaB: [28, 40, 80], sun: [255, 170, 90], tint: [255, 110, 60, 0.2], light: 0.6 },
    { top: [6, 10, 32], bot: [26, 40, 84], sea: [10, 24, 50], seaB: [4, 10, 26], sun: [220, 230, 255], tint: [16, 26, 70, 0.55], light: 1 },
  ];
  const skyAt = h => {
    const i = Math.floor(h) % 4, j = (i + 1) % 4, f = h - Math.floor(h), a = SKY[i], b = SKY[j];
    return { top: mix(a.top, b.top, f), bot: mix(a.bot, b.bot, f), sea: mix(a.sea, b.sea, f), seaB: mix(a.seaB, b.seaB, f), sun: mix(a.sun, b.sun, f),
      tint: [...mix(a.tint.slice(0, 3), b.tint.slice(0, 3), f), lerp(a.tint[3], b.tint[3], f)], light: lerp(a.light, b.light, f) };
  };

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
  function paintIsland(g) {
    WINDOWS.length = 0;
    const R = rnd(77);
    /* the lagoon: two flat rings of shallow water, the reef drawn as broken ink dashes */
    g.fillStyle = "rgba(127,208,194,.55)"; wobble(g, coastPts(1.12, 8), true, R, 3); g.fill();
    g.fillStyle = P.lagoon; wobble(g, coastPts(1.05, 4), true, R, 2); g.fill();
    g.setLineDash([7, 9]); wobble(g, coastPts(1.1, 7), true, R, 2); ink(g, 1.3, 0.35); g.setLineDash([]);
    /* sand, with its shade printed in dots on the sea side */
    g.fillStyle = P.sand; wobble(g, coastPts(), true, R); g.fill();
    g.save(); wobble(g, coastPts(), true, R, 0); g.clip(); dots(g, 200, 560, 1420, 790, 6, 1.6, "rgba(160,110,50,.35)", "y"); g.restore();
    wobble(g, coastPts(), true, R, 1.6); ink(g, 2.2);
    /* grass: one flat green, light where the sun falls, dots in the dips */
    g.save(); wobble(g, coastPts(0.88, -10), true, R, 0); g.clip();
    g.fillStyle = P.leaf; g.fillRect(0, 0, WW, WH);
    g.fillStyle = P.leafL; g.beginPath(); g.ellipse(760, 600, 420, 90, -0.05, 0, Math.PI * 2); g.fill();
    dots(g, 220, 330, 1380, 520, 7, 1.7, "rgba(36,81,58,.55)", "y");
    g.strokeStyle = "rgba(36,81,58,.45)"; g.lineWidth = 1.1; g.beginPath();
    for (let i = 0; i < 380; i++) { const x = 240 + R() * 1120, y = 520 + R() * 210; g.moveTo(x, y); g.lineTo(x + 1.5, y - 4); g.moveTo(x + 3, y); g.lineTo(x + 3.5, y - 3); }
    g.stroke();
    g.restore();
    wobble(g, coastPts(0.88, -10), true, R, 1.4); ink(g, 1.6, 0.7);
    /* the hills and the old volcano, flat colour, hatched on their shade side */
    const hill = (cx, top, w, c) => {
      const pts = []; for (let i = 0; i <= 24; i++) { const f = i / 24, x = cx - w + f * 2 * w, y = 470 - (470 - top) * Math.pow(Math.sin(f * Math.PI), 1.6); pts.push([x, y]); }
      g.fillStyle = c; wobble(g, pts, true, R, 0.8); g.fill();
      g.save(); g.clip(); hatch(g, cx + w * 0.1, top, cx + w, 470, 5, "rgba(20,40,30,.32)", 1.2); g.restore();
      wobble(g, pts.slice(0, -0), false, R, 0.8); ink(g, 1.8);
    };
    hill(500, 330, 200, "#4a8a4a"); hill(1115, 345, 195, "#468446");
    const vol = [[560, 470], [690, 410], [790, 300], [858, 238], [905, 238], [970, 300], [1060, 410], [1180, 470]];
    g.fillStyle = "#9a8a6c"; wobble(g, vol, true, R, 0.8); g.fill();
    g.save(); g.clip();
    g.fillStyle = "#5e8a4c"; g.beginPath(); g.moveTo(560, 470); for (let i = 0; i <= 20; i++) { const x = 600 + i * 28, y = 360 + Math.sin(i * 1.3) * 14 + Math.abs(i - 10) * 6; g.lineTo(x, y); } g.lineTo(1180, 470); g.closePath(); g.fill();
    hatch(g, 880, 236, 1190, 470, 6, "rgba(40,30,20,.3)", 1.3);
    g.fillStyle = "rgba(251,243,223,.35)"; g.beginPath(); g.moveTo(862, 240); g.lineTo(760, 360); g.lineTo(790, 362); g.lineTo(872, 244); g.fill();
    g.restore();
    wobble(g, vol, false, R, 0.8); ink(g, 2);
    g.fillStyle = "#5d5244"; g.beginPath(); g.ellipse(882, 238, 24, 6, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.5);
    /* jungle: clumps of canopy with one shared ink outline, each with a pale crescent where the light hits */
    const crowns = [];
    for (let i = 0; i < 230; i++) {
      const x = 260 + R() * 1080, y = 360 + R() * 120 + Math.abs(x - 800) * 0.03, r = 8 + R() * 12;
      if (Object.values(PLACES).some(p => Math.abs(p.x - x) < 70 && Math.abs(p.y - y) < 60)) continue;
      crowns.push([x, y, r]);
    }
    crowns.sort((a, b) => a[1] - b[1]);
    crowns.forEach(([x, y, r], i) => {
      g.fillStyle = INK; g.beginPath(); g.arc(x, y, r + 1.6, 0, Math.PI * 2); g.fill();
      g.fillStyle = i % 3 ? P.leafD : P.jungle; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(134,184,90,.85)"; g.beginPath(); g.arc(x - r * 0.18, y - r * 0.22, r * 0.62, Math.PI * 0.95, Math.PI * 1.75); g.arc(x - r * 0.05, y - r * 0.05, r * 0.5, Math.PI * 1.75, Math.PI * 0.95, true); g.fill();
    });
    /* paths: pale sand with a dotted ink edge */
    g.save(); g.lineCap = "round"; g.lineJoin = "round";
    const PATHS = [[[300, 610], [420, 620], [560, 630], [700, 628]], [[800, 515], [795, 590]], [[880, 630], [1000, 640], [1130, 640]], [[520, 480], [560, 560], [660, 610]], [[650, 432], [700, 520], [740, 590]], [[1080, 460], [1000, 560], [900, 615]], [[1000, 650], [1010, 700]]];
    PATHS.forEach(p => { wobble(g, p, false, R, 0.6); g.strokeStyle = "rgba(34,48,58,.55)"; g.lineWidth = 11; g.stroke(); });
    PATHS.forEach(p => { wobble(g, p, false, R, 0.6); g.strokeStyle = P.cream; g.lineWidth = 8; g.stroke(); });
    g.restore();
    /* the market square: paving rings and four striped stalls */
    g.fillStyle = "#e9d3a4"; g.beginPath(); g.ellipse(790, 628, 110, 34, 0, 0, Math.PI * 2); g.fill(); ink(g, 1.8);
    g.strokeStyle = "rgba(34,48,58,.3)"; g.lineWidth = 1; for (let i = 1; i < 4; i++) { g.beginPath(); g.ellipse(790, 628, 110 * i / 4, 34 * i / 4, 0, 0, Math.PI * 2); g.stroke(); }
    [[P.coral, 712], [P.mustard, 750], [P.teal, 830], ["#e889a6", 868]].forEach(([c, x], i) => {
      const y = 622 + (i % 2) * 18;
      g.fillStyle = "rgba(34,48,58,.25)"; g.fillRect(x - 15, y, 30, 4);
      g.fillStyle = INK; g.fillRect(x - 13, y - 18, 2, 18); g.fillRect(x + 11, y - 18, 2, 18);
      g.fillStyle = "#c79a62"; g.fillRect(x - 14, y - 8, 28, 8); g.beginPath(); g.rect(x - 14, y - 8, 28, 8); ink(g, 1.2);
      for (let k = 0; k < 4; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.moveTo(x - 17 + k * 8.5, y - 18); g.lineTo(x - 17 + (k + 1) * 8.5, y - 18); g.lineTo(x - 15 + (k + 1) * 7.5, y - 26); g.lineTo(x - 15 + k * 7.5, y - 26); g.fill(); }
      g.beginPath(); g.moveTo(x - 17, y - 18); g.lineTo(x + 17, y - 18); g.lineTo(x + 15, y - 26); g.lineTo(x - 15, y - 26); g.closePath(); ink(g, 1.2);
      for (let k = 0; k < 5; k++) { g.fillStyle = [P.mustard, P.coral, P.leafL, P.cream, "#c4453a"][(k + i) % 5]; g.beginPath(); g.arc(x - 10 + k * 5, y - 9, 2.4, 0, Math.PI * 2); g.fill(); }
    });
    /* the council hall: white columns under a teal dome */
    WINDOWS.push(...house(g, 800, 500, 140, 58, [P.cream, "#e6d8b8"], [P.teal], { d: 26, win: 0, doorC: P.coral }));
    for (let i = 0; i < 6; i++) { g.fillStyle = "#fffaf0"; g.fillRect(738 + i * 24, 452, 6, 46); g.beginPath(); g.rect(738 + i * 24, 452, 6, 46); ink(g, 1); }
    g.fillStyle = P.teal; g.beginPath(); g.ellipse(800, 432, 38, 34, 0, Math.PI, 0); g.closePath(); g.fill();
    g.save(); g.clip(); hatch(g, 800, 396, 840, 432, 4, "rgba(20,40,40,.35)"); g.restore();
    g.beginPath(); g.ellipse(800, 432, 38, 34, 0, Math.PI, 0); ink(g, 1.8);
    g.fillStyle = "#e8dfc8"; g.fillRect(762, 430, 76, 6); g.beginPath(); g.rect(762, 430, 76, 6); ink(g, 1.2);
    g.fillStyle = P.mustard; g.fillRect(799, 388, 2, 12); g.beginPath(); g.arc(800, 386, 3, 0, Math.PI * 2); g.fill();
    WINDOWS.push([762, 466, 8, 22], [830, 466, 8, 22]);
    /* the embassies */
    WINDOWS.push(...house(g, 520, 470, 92, 46, ["#cfe1ec", P.cream], [P.navy], { d: 22, doorC: P.navy }));
    g.strokeStyle = P.cream; g.lineWidth = 3; g.strokeRect(466, 470, 108, 10); g.beginPath(); g.rect(464, 468, 112, 14); ink(g, 1);
    WINDOWS.push(...house(g, 650, 425, 82, 42, ["#f6dcc0", P.cream], [P.coral], { d: 20, doorC: P.teal }));
    g.strokeStyle = P.cream; g.lineWidth = 3; g.strokeRect(602, 425, 96, 9); g.beginPath(); g.rect(600, 423, 100, 13); ink(g, 1);
    /* Radio Coco under its mast */
    WINDOWS.push(...house(g, 1080, 455, 74, 38, [P.mustard, P.cream], ["#7c4b2a"], { d: 18, win: 2, doorC: P.coral }));
    g.strokeStyle = INK; g.lineWidth = 2;
    g.beginPath(); g.moveTo(1100, 418); g.lineTo(1112, 312); g.lineTo(1124, 418); g.stroke();
    for (let i = 0; i < 7; i++) { const y = 418 - i * 15, k = i / 7; g.beginPath(); g.moveTo(1100 + 12 * k, y); g.lineTo(1124 - 12 * k, y - 15); g.stroke(); }
    /* Bar La Ola */
    WINDOWS.push(...house(g, 1210, 640, 96, 34, ["#c98c55", P.cream], ["#d9bf6a"], { d: 22, win: 3, doorC: P.teal }));
    g.fillStyle = P.cream; g.font = "800 11px Sora, sans-serif"; g.textAlign = "center"; g.fillText("LA OLA", 1210, 618);
    [[1150, 676, P.coral], [1280, 668, P.teal], [1312, 690, P.mustard]].forEach(([x, y, c]) => {
      g.fillStyle = "rgba(34,48,58,.22)"; g.beginPath(); g.ellipse(x + 6, y + 2, 20, 5, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = INK; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 26); g.stroke();
      for (let k = 0; k < 6; k++) { g.fillStyle = k % 2 ? P.cream : c; g.beginPath(); g.moveTo(x, y - 34); g.lineTo(x - 22 + k * 7.3, y - 24); g.lineTo(x - 22 + (k + 1) * 7.3, y - 24); g.fill(); }
      g.beginPath(); g.moveTo(x, y - 34); g.lineTo(x - 22, y - 24); g.lineTo(x + 22, y - 24); g.closePath(); ink(g, 1.2);
    });
    /* the pier */
    g.fillStyle = "#a57a4c"; wobble(g, [[990, 690], [1030, 690], [1060, 790], [1010, 790]], true, R, 0.6); g.fill(); ink(g, 1.6);
    g.strokeStyle = "rgba(34,48,58,.55)"; g.lineWidth = 1; for (let i = 0; i < 16; i++) { const t = i / 16, y = 690 + t * 100; g.beginPath(); g.moveTo(990 + 20 * t, y); g.lineTo(1030 + 30 * t, y); g.stroke(); }
    /* the lighthouse: cream and coral bands, the Book's room at its foot */
    WINDOWS.push(...house(g, 300, 612, 56, 26, [P.cream, "#e6d8b8"], ["#6a6a72"], { d: 14, win: 1, doorC: P.navy }));
    const tower = [[286, 590], [292, 450], [308, 450], [314, 590]];
    g.fillStyle = P.cream; wobble(g, tower, true, R, 0.4); g.fill();
    g.fillStyle = P.coral; [[560, 535], [505, 480]].forEach(([a, b]) => { const k0 = (590 - a) / 140, k1 = (590 - b) / 140; g.beginPath(); g.moveTo(286 + 6 * k0, a); g.lineTo(314 - 6 * k0, a); g.lineTo(314 - 6 * k1, b); g.lineTo(286 + 6 * k1, b); g.closePath(); g.fill(); });
    g.save(); wobble(g, tower, true, R, 0); g.clip(); dots(g, 302, 450, 316, 590, 4, 1.4, "rgba(34,48,58,.4)"); g.restore();
    wobble(g, tower, true, R, 0.4); ink(g, 1.8);
    g.fillStyle = INK; g.fillRect(288, 438, 24, 14); g.fillStyle = "#3c3c44"; g.beginPath(); g.moveTo(286, 438); g.lineTo(300, 424); g.lineTo(314, 438); g.closePath(); g.fill(); ink(g, 1.4);
    PALMS.forEach(([x, y]) => palmBase(g, x, y));
    for (let i = 0; i < 26; i++) { const a = R() * Math.PI * 2, [x, y] = COAST[Math.floor(R() * COAST.length)]; if (y < 560) continue; g.fillStyle = P.rock; g.beginPath(); g.ellipse(x, y, 4 + R() * 7, 3 + R() * 4, a, 0, Math.PI * 2); g.fill(); ink(g, 1.2, 0.8); }
  }
  const PALMS = [[380, 660], [430, 690], [560, 705], [640, 700], [905, 700], [1100, 700], [1290, 615], [1350, 640], [1390, 560], [330, 520], [400, 470], [1260, 520], [710, 690], [1170, 700], [240, 580], [940, 470]];

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
    const step = Math.sin(t * 0.012 + i) * 1.6;
    g.fillStyle = "rgba(34,48,58,.25)"; g.beginPath(); g.ellipse(x + 2, y + 1, 5.5, 1.8, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = INK; g.lineWidth = 2; g.lineCap = "round"; g.beginPath(); g.moveTo(x - 1.5, y - 7); g.lineTo(x - 1.5 + step, y); g.moveTo(x + 1.5, y - 7); g.lineTo(x + 1.5 - step, y); g.stroke();
    g.fillStyle = f.shirt; g.beginPath(); g.moveTo(x - 4.5, y - 6); g.lineTo(x - 3.5, y - 16); g.lineTo(x + 3.5, y - 16); g.lineTo(x + 4.5, y - 6); g.closePath(); g.fill(); g.lineWidth = 1.1; g.stroke();
    g.fillStyle = f.skin; g.beginPath(); g.arc(x, y - 19.5, 3.4, 0, Math.PI * 2); g.fill(); g.stroke();
    if (i % 3 === 0) { g.fillStyle = P.mustard; g.beginPath(); g.ellipse(x, y - 22, 5.5, 1.6, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.beginPath(); g.arc(x, y - 22.5, 2.6, Math.PI, 0); g.fill(); g.stroke(); }
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

  /* the white rabbit: hops from place to place, sits up and twitches its ears; it shows newcomers where to go */
  const RB = { x: 860, y: 690, tx: 860, ty: 690, hop: 0, dir: 1, next: 0 };
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

  /* ---------- the stage ---------- */
  const S = { c: null, g: null, W: 0, H: 0, K: 1, base: null, world: null, wg: null, hour: 0, hourT: 0, cam: { x: 800, y: 450, z: 1 }, camT: { x: 800, y: 450, z: 1 },
    hover: null, glow: null, gather: 0, cat: null, still: false, onFrame: null, last: 0 };
  function size() {
    const r = S.c.getBoundingClientRect(); S.K = Math.min(2, devicePixelRatio || 1);
    S.W = Math.max(1, r.width); S.H = Math.max(1, r.height);
    S.c.width = Math.round(S.W * S.K); S.c.height = Math.round(S.H * S.K);
    const fit = Math.min(S.W / WW, S.H / WH), q = Math.min(fit * S.K * 1.6, 4096 / WW);
    if (!S.base || Math.abs(S.base.q - q) > 0.05) {
      const b = document.createElement("canvas"); b.width = Math.round(WW * q); b.height = Math.round(WH * q); b.q = q;
      const g = b.getContext("2d"); g.scale(q, q); paintIsland(g); S.base = b;
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
  function frame(t) {
    const dt = Math.min(64, t - (S.last || t)); S.last = t;
    const k = 1 - Math.pow(0.0025, dt / 1000);
    S.hour += (S.hourT - S.hour) * Math.min(1, k * 0.9);
    for (const p of ["x", "y", "z"]) S.cam[p] += (S.camT[p] - S.cam[p]) * Math.min(1, k * 1.3);
    const g = S.g, W = S.c.width, H = S.c.height, sky = skyAt(S.hour);
    g.setTransform(1, 0, 0, 1, 0, 0);
    /* sky, from the top of the screen to the horizon: printed in flat bands, as a poster would be */
    view(g); const hzY = (HZ - S.cam.y) * fitScale() * S.cam.z * S.K + H / 2;
    g.setTransform(1, 0, 0, 1, 0, 0);
    const NB = 7, top = Math.min(0, hzY - H);
    for (let i = 0; i < NB; i++) { const f0 = Math.pow(i / NB, 0.7), f1 = Math.pow((i + 1) / NB, 0.7); g.fillStyle = rgb(mix(sky.top, sky.bot, i / (NB - 1))); g.fillRect(0, lerp(top, hzY, f0), W, lerp(top, hzY, f1) - lerp(top, hzY, f0) + 1); }
    /* the sea, from the horizon down, in four bands */
    for (let i = 0; i < 4; i++) { const f0 = Math.pow(i / 4, 1.6), f1 = Math.pow((i + 1) / 4, 1.6); g.fillStyle = rgb(mix(sky.sea, sky.seaB, i / 3)); g.fillRect(0, lerp(hzY, H, f0), W, lerp(hzY, H, f1) - lerp(hzY, H, f0) + 1); }
    view(g);
    const [wl] = toWorld(0, 0), [wr, wb] = toWorld(S.W, S.H), [, wt] = toWorld(0, 0);
    /* stars as small printed crosses, the sun as a disc in rings with slow rays, the moon as a crescent */
    const nt = Math.max(0, 1 - Math.abs((S.hour % 4) - 3) * 1.4);
    if (nt > 0) { const R = rnd(9); for (let i = 0; i < 140; i++) { const x = wl + R() * (wr - wl), y = wt + R() * (HZ - wt - 10), r = 0.8 + R() * 1.8, al = nt * (0.35 + R() * 0.65) * (0.7 + 0.3 * Math.sin(t * 0.002 + i)); g.fillStyle = `rgba(251,243,223,${al})`; g.fillRect(x - r, y - 0.5, r * 2, 1); g.fillRect(x - 0.5, y - r, 1, r * 2); } }
    const hh = S.hour % 4, sunX = lerp(300, 1350, Math.min(1, hh / 2.4)), sunY = HZ - Math.sin(Math.min(1, hh / 2.4) * Math.PI * 0.95 + 0.08) * 170 + (hh > 2 ? (hh - 2) * 90 : 0);
    if (hh < 2.75) {
      g.save(); g.beginPath(); g.rect(wl - 10, wt - 10, wr - wl + 20, HZ - wt + 10); g.clip();
      g.save(); g.translate(sunX, sunY); g.rotate(t * 0.00004);
      g.fillStyle = rgb(sky.sun, 0.16); for (let k = 0; k < 16; k++) { g.rotate(Math.PI / 8); g.beginPath(); g.moveTo(0, 0); g.lineTo(-24, -420); g.lineTo(24, -420); g.closePath(); g.fill(); }
      g.restore();
      [[96, 0.16], [70, 0.24], [48, 0.4]].forEach(([r, al]) => { g.fillStyle = rgb(sky.sun, al); g.beginPath(); g.arc(sunX, sunY, r, 0, Math.PI * 2); g.fill(); });
      g.fillStyle = rgb(sky.sun); g.beginPath(); g.arc(sunX, sunY, 30, 0, Math.PI * 2); g.fill();
      g.strokeStyle = "rgba(34,48,58,.25)"; g.lineWidth = 1.2; g.stroke();
      g.restore();
    }
    if (nt > 0.2) {
      g.fillStyle = `rgba(251,243,223,${nt * 0.12})`; g.beginPath(); g.arc(1220, 120, 44, 0, Math.PI * 2); g.fill();
      g.fillStyle = `rgba(251,243,223,${nt})`; g.beginPath(); g.arc(1220, 120, 18, 0, Math.PI * 2); g.arc(1229, 114, 15, 0, Math.PI * 2, true); g.fill();
    }
    /* clouds drift by */
    for (let i = 0; i < 6; i++) { const span = (wr - wl) + 600, x = wl - 300 + ((t * 0.006 * (1 + i * 0.2) + i * 380) % span), y = 80 + (i * 53) % 140; cloud(g, x, y, 0.7 + (i % 3) * 0.3, (0.55 - nt * 0.47) * (1 - i * 0.05)); }
    /* the sea moves: rows of little scalloped waves that grow toward the viewer, and a broken path of light */
    g.lineCap = "round"; g.lineJoin = "round";
    const foam = `rgba(251,243,223,${0.34 * (1 - nt * 0.55)})`, under = `rgba(16,40,60,${0.2 * (1 - nt * 0.3)})`;
    for (let r = 0; r < 30; r++) {
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
    for (let i = 0; i < 26; i++) { const y = HZ + 6 + i * i * 0.5, w0 = 6 + i * 2, f = Math.sin(t * 0.003 + i * 1.7); if (f < 0.15) continue; g.fillStyle = rgb(hh < 2.75 ? sky.sun : [251, 243, 223], f * 0.55 * (1 - i / 26)); g.fillRect(gx - w0 / 2 + Math.sin(i * 3.1 + t * 0.001) * w0 * 0.6, y, w0, 2); }
    /* the island and everything on it, drawn on one layer so the light of the hour tints it in one go */
    const w = S.wg; w.setTransform(1, 0, 0, 1, 0, 0); w.clearRect(0, 0, W, H); view(w);
    /* surf: a pale ring that comes and goes around the coast */
    const surf = 0.5 + 0.5 * Math.sin(t * 0.0015);
    w.strokeStyle = `rgba(255,255,255,${0.25 + surf * 0.35})`; w.lineWidth = 3; shape(w, 1.015 + surf * 0.012, 2); w.stroke();
    w.strokeStyle = `rgba(255,255,255,${0.12 * (1 - surf)})`; w.lineWidth = 2; shape(w, 1.05 + surf * 0.02, 4); w.stroke();
    w.drawImage(S.base, 0, 0, WW, WH);
    if (S.glow) { const p = PLACES[S.glow]; const [x, y, bw, bh] = p.box; w.fillStyle = "rgba(255,255,230,.18)"; w.beginPath(); w.ellipse(x + bw / 2, y + bh * 0.85, bw * 0.62, bh * 0.32, 0, 0, Math.PI * 2); w.fill(); }
    flag(w, 470, 470, t, "#3b5f8a", "#fff", "wind"); flag(w, 606, 425, t + 900, "#c0533f", "#fff", "wave");
    boat(w, 1110, 770, t);
    /* palms and people in depth order */
    const items = PALMS.map(([x, y], i) => [y, () => palm(w, x, y, t, i)]);
    FOLK.forEach((f, i) => {
      if (!S.still) { f.k += f.v * dt * f.dir; if (f.k > 1 || f.k < 0) { f.dir *= -1; f.k = Math.max(0, Math.min(1, f.k)); } }
      let [x, y] = alongPath(f.path, f.k);
      if (S.gather > 0) { const a = i / FOLK.length * Math.PI * 2, gx2 = 790 + Math.cos(a) * 70, gy2 = 640 + Math.sin(a) * 18; x = lerp(x, gx2, S.gather); y = lerp(y, gy2, S.gather); }
      items.push([y, () => person(w, x, y, t, f, i)]);
    });
    rabbitStep(S.still ? 999 : dt, t); items.push([RB.y, () => rabbit(w, t)]);
    if (S.cat) {
      const c = S.cat, f = (t - c.t0) / c.d; if (f > 1) S.cat = c.twice ? { ...c, t0: t, twice: false } : null;
      else items.push([700, () => cat(w, lerp(c.x0, c.x1, f), lerp(c.y0, c.y1, f), t, c.x1 > c.x0 ? 1 : -1)]);
    }
    items.sort((a, b) => a[0] - b[0]).forEach(([, d]) => d());
    /* the light of the hour */
    w.setTransform(1, 0, 0, 1, 0, 0);
    if (sky.tint[3] > 0.01) { w.globalCompositeOperation = "source-atop"; w.fillStyle = rgb(sky.tint, sky.tint[3]); w.fillRect(0, 0, W, H); w.globalCompositeOperation = "source-over"; }
    g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(S.world, 0, 0);
    /* evening and night: windows glow, the radio mast blinks, the lighthouse sweeps its green beam */
    view(g);
    if (sky.light > 0.05) {
      g.globalCompositeOperation = "lighter";
      WINDOWS.forEach(([x, y, ww, wh], i) => { const fl = 0.85 + 0.15 * Math.sin(t * 0.003 + i * 2.1); g.fillStyle = `rgba(255,190,90,${sky.light * 0.75 * fl})`; g.fillRect(x, y, ww, wh); g.fillStyle = `rgba(255,170,70,${sky.light * 0.08})`; g.beginPath(); g.arc(x + ww / 2, y + wh / 2, 8, 0, Math.PI * 2); g.fill(); });
      const a = t * 0.0006, bx = 300, by = 445;
      gr = g.createRadialGradient(bx, by, 0, bx, by, 520); gr.addColorStop(0, `rgba(57,255,138,${0.42 * sky.light})`); gr.addColorStop(1, "rgba(57,255,138,0)");
      g.fillStyle = gr; g.beginPath(); g.moveTo(bx, by); g.arc(bx, by, 520, a - 0.08, a + 0.08); g.closePath(); g.fill();
      g.globalCompositeOperation = "source-over";
    }
    g.fillStyle = `rgba(57,255,138,${0.65 + 0.35 * Math.sin(t * 0.004)})`; g.beginPath(); g.arc(300, 445, 4.5, 0, Math.PI * 2); g.fill();
    if (Math.floor(t / 700) % 2) { g.fillStyle = "#ff4a3a"; g.beginPath(); g.arc(1112, 311, 3, 0, Math.PI * 2); g.fill(); }
    /* gulls */
    for (let i = 0; i < 4; i++) { const x = wl + ((t * 0.02 * (1 + i * 0.15) + i * 420) % ((wr - wl) + 200)) - 100, y = 170 + i * 26 + Math.sin(t * 0.0009 + i) * 18; gull(g, x, y, t, i); }
    /* the paper: a fine grain over everything and the edges a shade darker, as on a print */
    g.setTransform(1, 0, 0, 1, 0, 0);
    if (!S.grain) S.grain = g.createPattern(grainTile(), "repeat");
    g.fillStyle = S.grain; g.fillRect(0, 0, W, H);
    if (!S.vig || S.vig.w !== W || S.vig.h !== H) { const v = g.createRadialGradient(W / 2, H * 0.55, Math.min(W, H) * 0.45, W / 2, H * 0.55, Math.hypot(W, H) * 0.62); v.addColorStop(0, "rgba(34,48,58,0)"); v.addColorStop(1, "rgba(34,48,58,.28)"); S.vig = { g: v, w: W, h: H }; }
    g.fillStyle = S.vig.g; g.fillRect(0, 0, W, H);
    if (S.onFrame) S.onFrame(t);
    requestAnimationFrame(frame);
  }

  function hit(px, py) {
    const [x, y] = toWorld(px, py);
    if (Math.abs(x - RB.x) < 16 && y < RB.y + 6 && y > RB.y - 30) return "rabbit";
    for (const id in PLACES) { const [bx, by, bw, bh] = PLACES[id].box; if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) return id; }
    return null;
  }
  /* lean in on a place, keeping the space for the card on the far side; null goes back to the whole cove */
  /* the whole island, as large as the screen allows: on a tall phone the island fills the width, the sky gives way */
  function home() {
    const f = fitScale(), z = Math.max(1, Math.min(S.W / (1220 * f), S.H / (690 * f)));
    return { x: 800, y: z > 1.05 ? Math.max(450, 900 - S.H / (f * z) / 2 - 10) : 450, z };
  }
  function focus(id, side = 0) {
    if (!id) { S.camT = home(); S.focusId = null; return; }
    S.focusId = id; S.focusSide = side;
    const p = PLACES[id], phone = S.W < 760, z = Math.max(home().z * 1.25, phone ? 1.5 : 1.7), s = fitScale() * z;
    const shift = side * (S.W * 0.22) / s;   // the card takes about the right (or left) half
    S.camT = { x: p.x + shift, y: phone ? p.y + (0.5 - 0.17) * S.H / s - 30 : p.y - 30, z };   // on a phone the sheet covers the lower part
  }
  function mount(canvas) {
    S.c = canvas; S.g = canvas.getContext("2d");
    S.still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    size(); addEventListener("resize", size);
    if (window.ResizeObserver) new ResizeObserver(size).observe(canvas);
    requestAnimationFrame(frame);
  }
  window.COVE_SCENE = {
    mount, hit, focus, places: PLACES, toScreen,
    setHour(h, now) { S.hourT = h; if (now) S.hour = h; },
    glow(id) { S.glow = id; },
    gather(v) { S.gather = v; },
    cat(twice) { S.cat = { t0: performance.now(), d: 9000, x0: 370, y0: 700, x1: 1180, y1: 712, twice: !!twice }; },
    onFrame(f) { S.onFrame = f; },
    /* the rabbit hops to a place and waits beside it (null: it wanders) */
    rabbit(id) { RB.goal = id; if (id && PLACES[id]) { const p = PLACES[id]; RB.tx = p.x + (id === "book" ? 46 : 0) + (p.x > 800 ? -40 : 40); RB.ty = p.y + 16; } },
    get hour() { return S.hour; },
  };
})();
