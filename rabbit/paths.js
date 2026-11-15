/* Where people walk on White Rabbit Key: the ways of the painted island, traced by hand on the painting (world units,
   the same as the layout's: x = picture x * 900 / 2138 - 260.8, y = picture y * 900 / 2138). The beach, the market
   lanes, the café deck and the pier, the road up past the resort to the camp, the rope bridges, the stairs to the
   lighthouse, the winding path to the drum hut. Nobody walks through a house, over a roof, up a cliff or over water:
   an islander goes from where it stands to a place's door along these ways (the shortest, A*), with its corners
   rounded so it turns softly, and stands about there for a while. A node's third number is how far people spread when
   they stand there (0: a narrow way, a bridge, stairs, where nobody stops).

   A painting without traced ways (a new island, the drawn island when the server is away) gets none: the walkers
   there walk as before. window.ISLE_PATHS = { of(file) → nav | null }; nav = { door(place), near(x, y), stand(node),
   route(x, y, from, to, lane) → [[x, y] …], node(i) } */
(() => {
  "use strict";
  const WAYS = {
    /* island 36 (picked 7.11.2026): lighthouse on the green hill, camp above the resort, canoe house on the west beach */
    "island-36-090df65a": {
      nodes: {
        shipb: [405, 668, 10], b1: [440, 712, 8], mk: [535, 640, 10], mkn: [530, 595, 6], wk0: [520, 565, 0], mks: [555, 705, 14],
        mke: [650, 640, 6], pond: [690, 600, 8], st1: [630, 745, 10], bc: [720, 760, 12], bm: [840, 770, 12], bp: [915, 725, 10],
        cafeW: [705, 690, 4], cafe: [790, 682, 8], cafeE: [880, 700, 4], lamps: [892, 640, 3], hall: [880, 600, 6], bar: [960, 672, 6],
        pier1: [1020, 684, 0], pier2: [1075, 692, 4], e1: [1005, 640, 6], swing: [1090, 640, 10], e3: [1175, 650, 6],
        schoolS: [1200, 625, 0], school: [1240, 605, 6], brW: [998, 508, 0], br1: [1060, 516, 3], br2: [1125, 500, 0],
        br3: [1165, 482, 0], brE: [1203, 462, 0], gate1: [1235, 440, 0], gate: [1268, 415, 5], works: [538, 535, 5], pe: [760, 580, 0],
        pondN: [785, 520, 0], r0: [830, 462, 0], r1: [810, 428, 0], r2: [757, 396, 0], r3: [731, 358, 0], r4: [733, 318, 0],
        r5: [757, 297, 0], sT: [785, 335, 0], south: [845, 362, 10], k1: [800, 272, 0], k2: [840, 257, 0], k3: [895, 247, 0],
        k4: [955, 233, 0], camp: [928, 215, 10], bt: [905, 462, 0], mbW: [490, 550, 0], bwE: [472, 512, 0], bw2: [400, 520, 0],
        bw1: [360, 508, 0], bwW: [338, 478, 0], c1: [375, 425, 0], c2: [360, 385, 0], c3: [290, 360, 0], c4: [215, 380, 0],
        c5: [205, 425, 0], c6: [260, 455, 0], circle: [285, 440, 6], v1: [150, 370, 4], v2: [95, 395, 4], v3: [115, 330, 4],
        vp1: [240, 282, 0], vp2: [195, 305, 0], vp3: [152, 312, 3], ama: [100, 280, 4], v4: [255, 262, 4], v5: [310, 262, 4],
        cw1: [55, 435, 0], cw2: [60, 490, 6], canoe: [130, 505, 8], cE: [310, 495, 6], d0: [262, 248, 0], d1: [276, 228, 0],
        d2: [297, 208, 0], d2b: [289, 188, 0], d3: [291, 175, 0], d4: [308, 165, 0], d5: [320, 153, 0], drums: [306, 143, 3],
        l1: [330, 258, 0], l2: [370, 225, 0], l3: [408, 196, 0], book: [440, 197, 3], rv1: [400, 255, 0], rv2: [440, 285, 0],
        radio: [480, 306, 3]
      },
      edges:
        "shipb-b1 shipb-mk b1-mks mk-mkn mk-mks mk-mke mke-pond mks-st1 st1-bc bc-bm bm-bp bc-cafeW cafeW-cafe cafe-cafeE " +
        "cafeE-bar cafeE-lamps lamps-hall bp-cafeE bar-pier1 pier1-pier2 bar-e1 e1-swing swing-e3 e3-schoolS schoolS-school r0-bt " +
        "bt-brW brW-br1 br1-br2 br2-br3 br3-brE brE-gate1 gate1-gate mkn-wk0 wk0-works pond-pe pe-pondN pondN-r0 r0-r1 r1-r2 " +
        "r2-r3 r3-r4 r4-r5 r4-sT sT-south r5-k1 k1-k2 k2-k3 k3-k4 k4-camp wk0-mbW mbW-bwE bwE-bw2 bw2-bw1 bw1-bwW bwW-c1 c1-c2 " +
        "c2-c3 c3-c4 c4-c5 c5-c6 c6-c1 c6-circle c1-circle c4-v1 v1-v2 v1-v3 v3-ama v4-vp1 vp1-vp2 vp2-vp3 vp3-v3 cE-bwW v4-v5 " +
        "v2-cw1 cw1-cw2 cw2-canoe canoe-cE v4-d0 d0-d1 d1-d2 d2-d2b d2b-d3 d3-d4 d4-d5 d5-drums v5-l1 l1-l2 l2-l3 l3-book l1-rv1 " +
        "rv1-rv2 rv2-radio",
      /* where a place's people stand; a place nobody can walk to (the dive centre on its stilts in the reef, the stone
         tower on the cliff) sends them to the nearest place on foot */
      doors: {
      market: "mk", cafe: "cafe", hall: "hall", bar: "bar", pier: "pier2", school: "school", north: "gate", grotto: "br1", works: "works",
      south: "south", camp: "camp", circle: "circle", ama: "ama", canoe: "canoe", drums: "drums", book: "book", radio: "radio", ship:
      "shipb", dive: "b1", stone: "ama"
      },
    },
  };
  const built = {};
  function build(def) {
    const ids = Object.keys(def.nodes), at = new Map(ids.map((k, i) => [k, i])), P = ids.map(k => def.nodes[k]);
    const adj = P.map(() => []);
    def.edges.split(/\s+/).filter(Boolean).forEach(e => {
      const [a, b] = e.split("-").map(k => at.get(k)); if (a == null || b == null) return;
      const d = Math.hypot(P[a][0] - P[b][0], P[a][1] - P[b][1]); adj[a].push([b, d]); adj[b].push([a, d]);
    });
    const door = {}; for (const id in def.doors) if (at.has(def.doors[id])) door[id] = at.get(def.doors[id]);
    /* A* over a few dozen nodes: cheap enough to run whenever someone sets off; the answers are kept */
    const memo = new Map();
    function path(s, t) {
      const key = s * 1000 + t; if (memo.has(key)) return memo.get(key);
      const n = P.length, g = new Float64Array(n).fill(Infinity), from = new Int32Array(n).fill(-1), done = new Uint8Array(n);
      const h = i => Math.hypot(P[i][0] - P[t][0], P[i][1] - P[t][1]);
      g[s] = 0; const open = [s];
      while (open.length) {
        let bi = 0; for (let k = 1; k < open.length; k++) if (g[open[k]] + h(open[k]) < g[open[bi]] + h(open[bi])) bi = k;
        const u = open.splice(bi, 1)[0]; if (u === t) break; if (done[u]) continue; done[u] = 1;
        for (const [v, d] of adj[u]) if (g[u] + d < g[v]) { g[v] = g[u] + d; from[v] = u; open.push(v); }
      }
      const out = []; if (s === t || from[t] >= 0) for (let u = t; u !== -1; u = u === s ? -1 : from[u]) out.unshift(u);
      if (memo.size > 4000) memo.clear(); memo.set(key, out); return out;
    }
    function near(x, y) {
      let bi = 0, bd = Infinity; P.forEach((p, i) => { const d = Math.hypot(p[0] - x, (p[1] - y) * 1.6); if (d < bd) { bd = d; bi = i; } }); return bi;
    }
    function stand(i) {   // somewhere about the node: an ellipse, wider than deep (the painting looks down at a slant)
      const p = P[i], r = p[2] || 0, a = Math.random() * Math.PI * 2, f = Math.sqrt(Math.random());
      return [p[0] + Math.cos(a) * r * f, p[1] + Math.sin(a) * r * f * 0.45];
    }
    /* the way from (x, y), which stands at node s, to a spot about node t: corners rounded (Chaikin, twice), and each
       walker keeps a little to its own side of the way (lane, world units) so a crowd does not walk in single file */
    function route(x, y, s, t, lane) {
      const ns = path(s, t); if (!ns.length) return null;
      const end = stand(t), pts = [[x, y], ...ns.slice(1, -1).map(i => [P[i][0], P[i][1]]), end];
      if (ns.length === 1) return pts;
      if (lane) for (let k = 1; k < pts.length - 1; k++) {
        const a = pts[k - 1], b = pts[k + 1], dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1;
        const room = Math.min(1, (P[ns[k]][2] || 0) / 4 + 0.35);   // on a bridge or stairs: barely
        pts[k] = [pts[k][0] - dy / d * lane * room, pts[k][1] + dx / d * lane * room * 0.5];
      }
      let q = pts;
      for (let it = 0; it < 2; it++) {
        const o = [q[0]];
        for (let k = 0; k < q.length - 1; k++) {
          const a = q[k], b = q[k + 1];
          if (k > 0) o.push([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25]);
          if (k < q.length - 2) o.push([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75]);
        }
        o.push(q[q.length - 1]); q = o;
      }
      return q;
    }
    return { door: id => (id in door ? door[id] : null), near, stand, route, path, node: i => P[i], size: P.length, ids };
  }
  window.ISLE_PATHS = {
    /* the ways of a painting, by its file name (a clean copy, island-…-clean-1234abcd, and a path before it count too) */
    of(f) {
      const name = String(f || "").replace(/^.*\//, "");
      for (const k in WAYS) if (name.startsWith(k)) return built[k] || (built[k] = build(WAYS[k]));
      return null;
    },
    ways: WAYS,
  };
})();
