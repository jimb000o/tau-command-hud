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

  /* ---------- the island, painted once per size ---------- */
  function house(g, x, y, w, h, wall, roof, o = {}) {
    const d = o.d || w * 0.35;   // depth seen from above
    g.save();
    g.fillStyle = "rgba(20,40,20,.28)"; g.beginPath(); g.ellipse(x + w * 0.1, y + 4, w * 0.62, d * 0.45, 0, 0, Math.PI * 2); g.fill();
    let gr = g.createLinearGradient(x - w / 2, 0, x + w / 2, 0); gr.addColorStop(0, wall[0]); gr.addColorStop(1, wall[1]);
    g.fillStyle = gr; g.fillRect(x - w / 2, y - h, w, h);
    g.fillStyle = "rgba(0,0,0,.12)"; g.fillRect(x + w / 2 - w * 0.12, y - h, w * 0.12, h);   // the shaded end
    /* the roof */
    gr = g.createLinearGradient(0, y - h - d, 0, y - h); gr.addColorStop(0, roof[0]); gr.addColorStop(1, roof[1]);
    g.fillStyle = gr; g.beginPath();
    g.moveTo(x - w / 2 - 6, y - h); g.lineTo(x - w / 2 + w * 0.18, y - h - d); g.lineTo(x + w / 2 - w * 0.18, y - h - d); g.lineTo(x + w / 2 + 6, y - h); g.closePath(); g.fill();
    g.strokeStyle = "rgba(255,255,255,.25)"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(x - w / 2 + w * 0.18, y - h - d); g.lineTo(x + w / 2 - w * 0.18, y - h - d); g.stroke();
    /* windows and a door; their places are kept so they can light up in the evening */
    const win = [], n = o.win ?? Math.max(2, Math.round(w / 26));
    for (let i = 0; i < n; i++) {
      const wx = x - w / 2 + (i + 0.5) * w / n - 5, wy = y - h * 0.72;
      g.fillStyle = "rgba(30,50,60,.75)"; g.fillRect(wx, wy, 10, h * 0.3); win.push([wx, wy, 10, h * 0.3]);
      g.fillStyle = "rgba(255,255,255,.5)"; g.fillRect(wx - 1, wy + h * 0.3, 12, 2);
    }
    if (o.door !== false) { g.fillStyle = o.doorC || "rgba(90,50,30,.9)"; g.fillRect(x - 7, y - h * 0.42, 14, h * 0.42); }
    g.restore();
    return win;
  }
  function palmBase(g, x, y) { g.fillStyle = "rgba(20,50,20,.25)"; g.beginPath(); g.ellipse(x + 10, y + 2, 22, 6, 0, 0, Math.PI * 2); g.fill(); }

  const WINDOWS = [];
  function paintIsland(g) {
    WINDOWS.length = 0;
    const R = rnd(77);
    /* shallow water and the reef around the coast */
    g.save(); g.filter = "blur(18px)"; g.fillStyle = "rgba(90,235,215,.55)"; shape(g, 1.13, 8); g.fill(); g.restore();
    g.save(); g.filter = "blur(6px)"; g.fillStyle = "rgba(150,250,230,.5)"; shape(g, 1.05, 4); g.fill(); g.restore();
    /* sand */
    let gr = g.createLinearGradient(0, 330, 0, 780); gr.addColorStop(0, "#efd9a0"); gr.addColorStop(1, "#f6e6b8");
    g.fillStyle = gr; shape(g); g.fill();
    g.strokeStyle = "rgba(255,255,255,.55)"; g.lineWidth = 2; shape(g); g.stroke();
    /* grass */
    g.save(); shape(g, 0.88, -10); g.clip();
    gr = g.createLinearGradient(0, 320, 0, 720); gr.addColorStop(0, "#3d8a3a"); gr.addColorStop(0.6, "#5aa846"); gr.addColorStop(1, "#7cbf55");
    g.fillStyle = gr; g.fillRect(0, 0, WW, WH);
    for (let i = 0; i < 2600; i++) {   // the grass is many small strokes, never a flat fill
      const x = 220 + R() * 1160, y = 330 + R() * 400, s = 1 + R() * 2.5;
      g.fillStyle = `rgba(${30 + R() * 60 | 0},${100 + R() * 80 | 0},${30 + R() * 40 | 0},${0.25 + R() * 0.35})`;
      g.fillRect(x, y, s, s * 0.7);
    }
    g.restore();
    g.save(); g.filter = "blur(3px)"; g.strokeStyle = "rgba(240,220,160,.7)"; g.lineWidth = 6; shape(g, 0.88, -10); g.stroke(); g.restore();
    /* the hills at the back, with the old volcano in the middle */
    const hill = (cx, top, w, c0, c1) => {
      const gr = g.createLinearGradient(0, top, 0, 470); gr.addColorStop(0, c0); gr.addColorStop(1, c1);
      g.fillStyle = gr; g.beginPath(); g.moveTo(cx - w, 470);
      g.bezierCurveTo(cx - w * 0.55, 440, cx - w * 0.3, top, cx, top); g.bezierCurveTo(cx + w * 0.3, top, cx + w * 0.55, 440, cx + w, 470); g.closePath(); g.fill();
    };
    hill(500, 330, 200, "#2f6b33", "#3f8a3c");
    hill(1115, 345, 195, "#2c6532", "#3d863b");
    g.fillStyle = "#3a7a3a"; g.beginPath(); g.moveTo(560, 470); g.bezierCurveTo(700, 420, 760, 250, 860, 236); g.lineTo(905, 236); g.bezierCurveTo(990, 250, 1040, 420, 1180, 470); g.closePath();
    gr = g.createLinearGradient(0, 236, 0, 470); gr.addColorStop(0, "#8b7d64"); gr.addColorStop(0.28, "#5f7b48"); gr.addColorStop(1, "#3c823b"); g.fillStyle = gr; g.fill();
    g.fillStyle = "rgba(255,255,255,.12)"; g.beginPath(); g.moveTo(860, 236); g.bezierCurveTo(800, 270, 760, 360, 700, 440); g.lineTo(740, 440); g.bezierCurveTo(790, 360, 830, 280, 880, 238); g.closePath(); g.fill();
    g.fillStyle = "#5d5244"; g.beginPath(); g.ellipse(882, 238, 24, 6, 0, 0, Math.PI * 2); g.fill();
    /* jungle: canopies, darkest at the back */
    for (let i = 0; i < 260; i++) {
      const x = 260 + R() * 1080, y = 360 + R() * 120 + Math.abs(x - 800) * 0.03, r = 7 + R() * 12;
      if (Object.values(PLACES).some(p => Math.abs(p.x - x) < 70 && Math.abs(p.y - y) < 60)) continue;
      g.fillStyle = `rgba(${20 + R() * 30 | 0},${70 + R() * 50 | 0},${25 + R() * 20 | 0},.9)`; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(170,230,120,.22)"; g.beginPath(); g.arc(x - r * 0.3, y - r * 0.35, r * 0.5, 0, Math.PI * 2); g.fill();
    }
    /* paths between the places */
    g.save(); g.lineCap = "round"; g.strokeStyle = "rgba(236,214,160,.95)"; g.lineWidth = 9;
    const path = pts => { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); };
    path([[300, 610], [420, 620], [560, 630], [700, 628]]); path([[800, 515], [795, 590]]); path([[880, 630], [1000, 640], [1130, 640]]);
    path([[520, 480], [560, 560], [660, 610]]); path([[650, 432], [700, 520], [740, 590]]); path([[1080, 460], [1000, 560], [900, 615]]); path([[1000, 650], [1010, 700]]);
    g.restore();
    /* the market square: paving and stalls */
    g.fillStyle = "rgba(226,200,150,.95)"; g.beginPath(); g.ellipse(790, 628, 110, 34, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "rgba(180,150,100,.5)"; g.lineWidth = 1; for (let i = 1; i < 4; i++) { g.beginPath(); g.ellipse(790, 628, 110 * i / 4, 34 * i / 4, 0, 0, Math.PI * 2); g.stroke(); }
    [["#e85d4a", 712], ["#f2b134", 750], ["#3aa6a0", 830], ["#e86fa0", 868]].forEach(([c, x], i) => {
      const y = 622 + (i % 2) * 18;
      g.fillStyle = "rgba(0,0,0,.2)"; g.fillRect(x - 15, y, 30, 4);
      g.fillStyle = "#7a5a3a"; g.fillRect(x - 13, y - 18, 2, 18); g.fillRect(x + 11, y - 18, 2, 18);
      g.fillStyle = "#c79a62"; g.fillRect(x - 14, y - 8, 28, 8);
      for (let k = 0; k < 4; k++) { g.fillStyle = k % 2 ? "#fff6e6" : c; g.beginPath(); g.moveTo(x - 17 + k * 8.5, y - 18); g.lineTo(x - 17 + (k + 1) * 8.5, y - 18); g.lineTo(x - 15 + (k + 1) * 7.5, y - 26); g.lineTo(x - 15 + k * 7.5, y - 26); g.fill(); }
      for (let k = 0; k < 5; k++) { g.fillStyle = ["#ffcf3f", "#ff7f3f", "#7fd44f", "#ffe9a8", "#d94f3f"][(k + i) % 5]; g.beginPath(); g.arc(x - 10 + k * 5, y - 9, 2.4, 0, Math.PI * 2); g.fill(); }
    });
    /* the council hall: white, columns, a teal dome */
    WINDOWS.push(...house(g, 800, 500, 140, 58, ["#fbf7ee", "#e9e1cf"], ["#2c9c94", "#1d7a74"], { d: 26, win: 0, doorC: "#6b4a2e" }));
    g.fillStyle = "#fffaf0"; for (let i = 0; i < 6; i++) { g.fillRect(738 + i * 24, 452, 6, 46); }
    g.fillStyle = "rgba(0,0,0,.08)"; for (let i = 0; i < 6; i++) g.fillRect(742 + i * 24, 452, 2, 46);
    gr = g.createRadialGradient(790, 405, 4, 800, 420, 40); gr.addColorStop(0, "#5fd1c6"); gr.addColorStop(1, "#1b6f69");
    g.fillStyle = gr; g.beginPath(); g.ellipse(800, 432, 38, 34, 0, Math.PI, 0); g.fill();
    g.fillStyle = "#e8dfc8"; g.fillRect(762, 430, 76, 6);
    g.fillStyle = "#d9b44a"; g.fillRect(799, 388, 2, 12); g.beginPath(); g.arc(800, 386, 3, 0, Math.PI * 2); g.fill();
    WINDOWS.push([762, 466, 8, 22], [830, 466, 8, 22]);
    /* the embassies: two villas, each with its own garden wall */
    WINDOWS.push(...house(g, 520, 470, 92, 46, ["#cfe6f5", "#b3d0e6"], ["#3b5f8a", "#2c4a70"], { d: 22 }));
    g.strokeStyle = "rgba(255,255,255,.8)"; g.lineWidth = 3; g.strokeRect(466, 470, 108, 10);
    WINDOWS.push(...house(g, 650, 425, 82, 42, ["#f7e0c4", "#e9c9a4"], ["#c0533f", "#9b3e2f"], { d: 20 }));
    g.strokeStyle = "rgba(255,255,255,.75)"; g.lineWidth = 3; g.strokeRect(602, 425, 96, 9);
    /* Radio Coco: a hut on the hillside under its mast */
    WINDOWS.push(...house(g, 1080, 455, 74, 38, ["#f3e28a", "#e0c860"], ["#7c4b2a", "#5c361e"], { d: 18, win: 2 }));
    g.strokeStyle = "#5e5e66"; g.lineWidth = 2;
    g.beginPath(); g.moveTo(1100, 418); g.lineTo(1112, 312); g.lineTo(1124, 418); g.stroke();
    for (let i = 0; i < 7; i++) { const y = 418 - i * 15, k = i / 7; g.beginPath(); g.moveTo(1100 + 12 * k, y); g.lineTo(1124 - 12 * k, y - 15); g.stroke(); }
    /* Bar La Ola: a beach shack with a palm-leaf roof and umbrellas */
    WINDOWS.push(...house(g, 1210, 640, 96, 34, ["#c98c55", "#a86e3c"], ["#c9b262", "#9b8540"], { d: 22, win: 3 }));
    g.fillStyle = "#fff"; g.font = "700 11px Sora, sans-serif"; g.textAlign = "center"; g.fillText("LA OLA", 1210, 618);
    [[1150, 676, "#e8574a"], [1280, 668, "#2fb0a8"], [1312, 690, "#f2b134"]].forEach(([x, y, c]) => {
      g.fillStyle = "rgba(0,0,0,.18)"; g.beginPath(); g.ellipse(x + 6, y + 2, 20, 5, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = "#eee"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 26); g.stroke();
      for (let k = 0; k < 6; k++) { g.fillStyle = k % 2 ? "#fff8ee" : c; g.beginPath(); g.moveTo(x, y - 34); g.lineTo(x - 22 + k * 7.3, y - 24); g.lineTo(x - 22 + (k + 1) * 7.3, y - 24); g.fill(); }
    });
    /* the pier, out into the bay */
    g.fillStyle = "#8a6440"; g.beginPath(); g.moveTo(990, 690); g.lineTo(1030, 690); g.lineTo(1060, 790); g.lineTo(1010, 790); g.closePath(); g.fill();
    g.strokeStyle = "rgba(60,36,20,.55)"; g.lineWidth = 1; for (let i = 0; i < 16; i++) { const t = i / 16, y = 690 + t * 100; g.beginPath(); g.moveTo(990 + 20 * t, y); g.lineTo(1030 + 30 * t, y); g.stroke(); }
    /* the lighthouse on its point: white and red, with the Book's room at its foot */
    WINDOWS.push(...house(g, 300, 612, 56, 26, ["#f5efe2", "#ddd3bf"], ["#7a7a80", "#5a5a60"], { d: 14, win: 1 }));
    gr = g.createLinearGradient(284, 0, 316, 0); gr.addColorStop(0, "#fffdf8"); gr.addColorStop(1, "#d8d0c0");
    g.fillStyle = gr; g.beginPath(); g.moveTo(286, 590); g.lineTo(292, 450); g.lineTo(308, 450); g.lineTo(314, 590); g.closePath(); g.fill();
    g.fillStyle = "#c8443a"; [[560, 535], [505, 480]].forEach(([a, b]) => { const k0 = (590 - a) / 140, k1 = (590 - b) / 140; g.beginPath(); g.moveTo(286 + 6 * k0, a); g.lineTo(314 - 6 * k0, a); g.lineTo(314 - 6 * k1, b); g.lineTo(286 + 6 * k1, b); g.closePath(); g.fill(); });
    g.fillStyle = "#2a2a30"; g.fillRect(288, 438, 24, 14); g.fillStyle = "#3c3c44"; g.beginPath(); g.moveTo(286, 438); g.lineTo(300, 424); g.lineTo(314, 438); g.closePath(); g.fill();
    /* palm bases and rocks along the beach */
    PALMS.forEach(([x, y]) => palmBase(g, x, y));
    for (let i = 0; i < 26; i++) { const a = R() * Math.PI * 2, [x, y] = COAST[Math.floor(R() * COAST.length)]; if (y < 560) continue; g.fillStyle = `rgba(${110 + R() * 40 | 0},${100 + R() * 30 | 0},${90 + R() * 20 | 0},.85)`; g.beginPath(); g.ellipse(x, y, 4 + R() * 7, 3 + R() * 4, a, 0, Math.PI * 2); g.fill(); }
  }
  const PALMS = [[380, 660], [430, 690], [560, 705], [640, 700], [905, 700], [1100, 700], [1290, 615], [1350, 640], [1390, 560], [330, 520], [400, 470], [1260, 520], [710, 690], [1170, 700], [240, 580], [940, 470]];

  /* ---------- the moving parts ---------- */
  function palm(g, x, y, t, i) {
    const sway = Math.sin(t * 0.0011 + i * 1.7) * 4 + Math.sin(t * 0.0023 + i) * 1.5, h = 62 + (i * 7) % 22, lean = ((i * 13) % 9 - 4) * 2.4;
    const tx = x + lean + sway, ty = y - h;
    g.strokeStyle = "#7a5a3c"; g.lineWidth = 5; g.lineCap = "round"; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + lean * 0.3, y - h * 0.55, tx, ty); g.stroke();
    g.strokeStyle = "rgba(255,230,190,.35)"; g.lineWidth = 1; for (let k = 1; k < 8; k++) { const f = k / 8, px = lerp(x, tx, f) + lean * 0.3 * Math.sin(f * Math.PI) * 0.5, py = lerp(y, ty, f); g.beginPath(); g.moveTo(px - 2.5, py); g.lineTo(px + 2.5, py - 1); g.stroke(); }
    for (let k = 0; k < 7; k++) {
      const a = -Math.PI / 2 + (k - 3) * 0.55 + Math.sin(t * 0.0017 + i + k) * 0.06, L = 34 + (k % 3) * 6;
      const ex = tx + Math.cos(a) * L, ey = ty + Math.sin(a) * L * 0.55 + 16, mx = tx + Math.cos(a) * L * 0.5, my = ty + Math.sin(a) * L * 0.5 - 6;
      g.strokeStyle = k % 2 ? "#2f7d36" : "#3f9a40"; g.lineWidth = 4.5; g.beginPath(); g.moveTo(tx, ty); g.quadraticCurveTo(mx, my, ex, ey); g.stroke();
      g.strokeStyle = "rgba(160,230,120,.45)"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(tx, ty); g.quadraticCurveTo(mx, my - 1, ex, ey - 1); g.stroke();
    }
    g.fillStyle = "#5b3d22"; for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(tx - 3 + k * 3, ty + 3, 2.6, 0, Math.PI * 2); g.fill(); }
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
    g.fillStyle = "rgba(0,0,0,.22)"; g.beginPath(); g.ellipse(x, y + 1, 5, 1.8, 0, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "#3a3040"; g.lineWidth = 2; g.beginPath(); g.moveTo(x - 1.5, y - 7); g.lineTo(x - 1.5 + step, y); g.moveTo(x + 1.5, y - 7); g.lineTo(x + 1.5 - step, y); g.stroke();
    g.fillStyle = f.shirt; g.beginPath(); g.roundRect ? g.roundRect(x - 4, y - 16, 8, 10, 3) : g.rect(x - 4, y - 16, 8, 10); g.fill();
    g.fillStyle = f.skin; g.beginPath(); g.arc(x, y - 19.5, 3.4, 0, Math.PI * 2); g.fill();
  }
  function boat(g, x, y, t) {
    const b = Math.sin(t * 0.0018) * 2, r = Math.sin(t * 0.0013) * 0.04;
    g.save(); g.translate(x, y + b); g.rotate(r);
    g.fillStyle = "rgba(0,30,50,.25)"; g.beginPath(); g.ellipse(0, 6, 40, 6, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(-38, -4); g.lineTo(38, -4); g.lineTo(28, 8); g.lineTo(-30, 8); g.closePath(); g.fill();
    g.fillStyle = "#2fb0a8"; g.fillRect(-34, 0, 66, 3);
    g.strokeStyle = "#6a5040"; g.lineWidth = 2; g.beginPath(); g.moveTo(0, -4); g.lineTo(0, -54); g.stroke();
    g.fillStyle = "#fffaf0"; g.beginPath(); g.moveTo(2, -52); g.quadraticCurveTo(26 + Math.sin(t * 0.002) * 3, -30, 30, -8); g.lineTo(2, -8); g.closePath(); g.fill();
    g.fillStyle = "rgba(255,240,220,.85)"; g.beginPath(); g.moveTo(-2, -48); g.quadraticCurveTo(-18, -30, -20, -8); g.lineTo(-2, -8); g.closePath(); g.fill();
    g.restore();
  }
  function cloud(g, x, y, s, a) {
    g.fillStyle = `rgba(255,255,255,${a})`;
    [[0, 0, 26], [24, -8, 22], [48, 0, 24], [22, 6, 24], [-20, 6, 18], [68, 6, 16]].forEach(([dx, dy, r]) => { g.beginPath(); g.arc(x + dx * s, y + dy * s, r * s, 0, Math.PI * 2); g.fill(); });
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

  function frame(t) {
    const dt = Math.min(64, t - (S.last || t)); S.last = t;
    const k = 1 - Math.pow(0.0025, dt / 1000);
    S.hour += (S.hourT - S.hour) * Math.min(1, k * 0.9);
    for (const p of ["x", "y", "z"]) S.cam[p] += (S.camT[p] - S.cam[p]) * Math.min(1, k * 1.3);
    const g = S.g, W = S.c.width, H = S.c.height, sky = skyAt(S.hour);
    g.setTransform(1, 0, 0, 1, 0, 0);
    /* sky, from the top of the screen to the horizon */
    view(g); const [, hzY] = [0, (HZ - S.cam.y) * fitScale() * S.cam.z * S.K + H / 2];
    g.setTransform(1, 0, 0, 1, 0, 0);
    let gr = g.createLinearGradient(0, 0, 0, Math.max(1, hzY)); gr.addColorStop(0, rgb(sky.top)); gr.addColorStop(1, rgb(sky.bot));
    g.fillStyle = gr; g.fillRect(0, 0, W, Math.max(0, hzY) + 1);
    /* the sea, from the horizon down */
    gr = g.createLinearGradient(0, hzY, 0, H); gr.addColorStop(0, rgb(sky.sea)); gr.addColorStop(1, rgb(sky.seaB));
    g.fillStyle = gr; g.fillRect(0, hzY, W, H - hzY);
    view(g);
    const [wl] = toWorld(0, 0), [wr, wb] = toWorld(S.W, S.H), [, wt] = toWorld(0, 0);
    /* stars and the sun or moon */
    const night = Math.max(0, Math.min(1, (S.hour % 4) - 2.2)) * (S.hour % 4 < 3.9 ? 1 : 0) || (S.hour % 4 > 2.6 ? 1 : 0) * 0;
    const nt = Math.max(0, 1 - Math.abs((S.hour % 4) - 3) * 1.4);
    if (nt > 0) { const R = rnd(9); for (let i = 0; i < 160; i++) { const x = wl + R() * (wr - wl), y = wt + R() * (HZ - wt - 10); g.fillStyle = `rgba(255,255,255,${nt * (0.3 + R() * 0.7) * (0.7 + 0.3 * Math.sin(t * 0.002 + i))})`; g.fillRect(x, y, 1.6, 1.6); } }
    const hh = S.hour % 4, sunX = lerp(300, 1350, Math.min(1, hh / 2.4)), sunY = HZ - Math.sin(Math.min(1, hh / 2.4) * Math.PI * 0.95 + 0.08) * 170 + (hh > 2 ? (hh - 2) * 90 : 0);
    if (hh < 2.75) {
      gr = g.createRadialGradient(sunX, sunY, 0, sunX, sunY, 140); gr.addColorStop(0, rgb(sky.sun, 0.9)); gr.addColorStop(0.18, rgb(sky.sun, 0.5)); gr.addColorStop(1, rgb(sky.sun, 0));
      g.fillStyle = gr; g.fillRect(sunX - 140, sunY - 140, 280, 280);
      g.fillStyle = rgb(sky.sun); g.beginPath(); g.arc(sunX, sunY, 22, 0, Math.PI * 2); g.fill();
    }
    if (nt > 0.2) { g.fillStyle = `rgba(240,244,255,${nt})`; g.beginPath(); g.arc(1220, 120, 16, 0, Math.PI * 2); g.fill(); g.fillStyle = rgb(sky.top, nt); g.beginPath(); g.arc(1228, 115, 14, 0, Math.PI * 2); g.fill(); }
    /* clouds drift by */
    for (let i = 0; i < 6; i++) { const span = (wr - wl) + 600, x = wl - 300 + ((t * 0.006 * (1 + i * 0.2) + i * 380) % span), y = 80 + (i * 53) % 140; cloud(g, x, y, 0.7 + (i % 3) * 0.3, (0.55 - nt * 0.47) * (1 - i * 0.05)); }
    /* the sea moves: rows of small wave strokes, a path of light under the sun or moon */
    g.lineCap = "round";
    for (let r = 0; r < 34; r++) {
      const y = HZ + 6 + r * r * 0.62, a = 0.05 + r * 0.006, len = 6 + r * 0.9; if (y > wb + 20) break;
      g.strokeStyle = `rgba(255,255,255,${a * (1 - nt * 0.6)})`; g.lineWidth = 0.8 + r * 0.06;
      for (let x = wl - 40 + ((r * 37) % 60); x < wr + 40; x += 60 + r * 3) {
        const o = Math.sin(t * 0.0012 + r * 0.9 + x * 0.01) * 8;
        g.beginPath(); g.moveTo(x + o, y + Math.sin(t * 0.002 + x) * 1.2); g.lineTo(x + o + len, y + Math.sin(t * 0.002 + x) * 1.2); g.stroke();
      }
    }
    const gx = hh < 2.75 ? sunX : 1220;
    for (let i = 0; i < 40; i++) { const y = HZ + 4 + i * i * 0.35, w = 4 + i * 1.3, f = Math.sin(t * 0.004 + i * 1.7); if (f < 0.1) continue; g.fillStyle = rgb(hh < 2.75 ? sky.sun : [230, 236, 255], f * 0.35 * (1 - i / 40)); g.fillRect(gx - w / 2 + Math.sin(i * 3.1 + t * 0.001) * w, y, w * 0.6, 1.6); }
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
