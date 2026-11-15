/* Agorzilla's look, as the evenings decided it: the same chain state agorzilla.com shows (its chain/latest.json).
   Every Agorzilla on Tau HUD (the HUD's puppet, the My Tau card, /start/) carries [data-agz-look]; this sets their
   pendant light and fur from the votes, so a new evening's result shows here by itself, with nobody changing a file.
   The pendant light is a mask of the collar LEDs and the medal (assets/rig/agz-pendant.webp, made by agorzilla.com's
   tools/pendant_lights.py) tinted in its colour, as on agorzilla.com. Pages that already read latest.json call
   AgzLook.apply(d); the others give the script data-poll and it reads it every 5 min.
   He grows up here too: each stage has its own pictures (tools/agz/stages.py bakes agorzilla.com's growing-up fields
   into assets/rig/age/, assets/rig/hi/age/ and assets/age/), swapped in by name; eyes and lids shrink, the skin darkens and
   the head sits higher and a little smaller on the risen back, as on agorzilla.com. The voted build, back and muzzle
   show as there. The last stage is remembered, so the next page opens with it before the first fetch. */
(() => {
  "use strict";
  const PEND = { gold: "#ffd36b", green: "#6ee7a0", blue: "#7dd3fc", rose: "#fda4af", white: "#ffffff" };
  const FUR = { natural: "none", copper: "sepia(.55) saturate(1.7) hue-rotate(-12deg) brightness(1.05)", silver: "grayscale(.85) brightness(1.25) contrast(1.05)",
    midnight: "sepia(.3) hue-rotate(180deg) saturate(1.6) brightness(.9)", moss: "sepia(.4) hue-rotate(50deg) saturate(1.5)", honey: "sepia(.7) saturate(2) brightness(1.15)" };
  const key = v => String(v || "").trim().toLowerCase();
  /* growing up (agorzilla.com assets/rig.js AGE, style.css --ahs; build, back and muzzle as its style.css "growing up") */
  const AGE = { baby: 0, kid: .18, young: .38, grown: .62, elder: .82, ancient: 1 };
  const AHS = { baby: 1, kid: .985, young: .97, grown: .95, elder: .935, ancient: .925 };
  const BUILD = { slender: [1.05, .94], sturdy: [1, 1.04], broad: [.97, 1.08] };
  const BACK = { "silver back": [.75, "grayscale(1) brightness(2.1) contrast(.9)"], "golden back": [.7, "sepia(1) saturate(2.4) brightness(1.7)"],
    "moonlit back": [.7, "grayscale(1) sepia(.6) hue-rotate(170deg) saturate(2) brightness(1.9)"] };
  const MUZ = { grey: [.75, "grayscale(1) brightness(2.2) contrast(.85)"], "snow white": [1, "grayscale(1) brightness(3) contrast(.8)"],
    ginger: [.8, "sepia(1) saturate(3) hue-rotate(-15deg) brightness(1.6)"] };
  const smooth = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const gauss = (x, y, cx, cy, r) => Math.exp(-((x - cx) * (x - cx) + (y - cy) * (y - cy)) / (r * r));
  const neck = a => {   // rig.js ageTrunk at the neck (520, 560): the back rises and the head with it; in % of the 760x1140 frame
    const x = 520, y = 560;
    const dy = -a * (34 * smooth(940, 600, y) + 20 * (gauss(x, y, 250, 600, 120) + gauss(x, y, 700, 580, 110)) * smooth(940, 700, y));
    const dx = (x - 480) * .14 * a * smooth(470, 620, y) * smooth(960, 780, y);
    return [dx / 760 * 100, dy / 1140 * 100];
  };
  const recall = () => { try { return localStorage.getItem("agz-stage"); } catch (e) { return null; } };
  const keep = st => { try { localStorage.setItem("agz-stage", st); localStorage.setItem("agz-stage-at", String(Date.now())); } catch (e) { /* the next page fetches it again */ } };
  const RIG = /(assets\/rig\/(?:hi\/)?)(?:age\/[a-z]+\/)?((?:agz-)?(?:head|body|brow-l|brow-r|moves)\.webp)/, PIC = /assets\/(?:age\/)?agorzilla(?:-[a-z]+)?\.webp/;
  const src = (u, st) => {   // the same picture at this stage: the baby's are the originals
    if (RIG.test(u)) return u.replace(RIG, (m, dir, f) => dir + (st === "baby" || (dir.includes("hi/") && f === "moves.webp") ? "" : `age/${st}/`) + f);
    if (PIC.test(u)) return u.replace(PIC, st === "baby" ? "assets/agorzilla.webp" : `assets/age/agorzilla-${st}.webp`);
    return u;
  };
  let stage = AGE[recall()] != null ? recall() : "baby";
  const overlay = (el, img, cls) => {   // the voted back and muzzle: the same picture, tinted, through a soft mask (as agorzilla.com's .silver/.grey)
    if (!img || el.querySelector("img." + cls)) return;
    const o = document.createElement("img"); o.className = cls; o.src = img.getAttribute("src"); o.alt = ""; o.draggable = false; o.setAttribute("aria-hidden", "true");
    const nx = img.nextElementSibling; (nx && nx.tagName === "CANVAS" ? nx : img).after(o);
  };
  const grow = (st, t) => {
    if (AGE[st] == null) return;
    const changed = st !== stage; stage = st; keep(st);
    const a = AGE[st], [nx, ny] = neck(a), b = BUILD[key(t && t.build)] || [1, 1], bk = BACK[key(t && t.back)], mz = MUZ[key(t && t.muzzle)];
    document.querySelectorAll("[data-agz-look]").forEach(el => {
      if (t) { overlay(el, el.querySelector("img.trunk"), "agz-back"); overlay(el, el.querySelector(".hd > img, img.face"), "agz-muz"); }
      el.querySelectorAll("img").forEach(im => { const u = im.getAttribute("src") || "", v = src(u, st); if (v !== u) im.setAttribute("src", v); });
      const set = (k, v) => el.style.setProperty(k, v);
      set("--agz-eye", (1 - .3 * a).toFixed(4)); set("--agz-skin", (1 - .55 * a).toFixed(3)); set("--agz-grey", (.55 * a * .5).toFixed(3)); set("--agz-iris", (1 - .18 * a).toFixed(3));
      set("--agz-nx", nx.toFixed(3) + "%"); set("--agz-ny", ny.toFixed(3) + "%"); set("--agz-hs", (AHS[st] * b[0]).toFixed(4)); set("--agz-bw", b[1]);
      set("--agz-back", bk ? bk[0] : 0); if (bk) set("--agz-backf", bk[1]); set("--agz-muz", mz ? mz[0] : 0); if (mz) set("--agz-muzf", mz[1]);
      el.dataset.agzStage = st;
    });
    // the small pictures elsewhere on the page (menus, the services list)
    document.querySelectorAll('img[src*="agorzilla"]').forEach(im => { const u = im.getAttribute("src"), v = src(u, st); if (v !== u) im.setAttribute("src", v); });
    return changed;
  };
  /* From Grown on agorzilla.com draws him from paintings of their own (its assets/rig/<painting>/, the way the feeders chose
     when that way is painted). latest.json names the painting and where its eyes, lids, brows, mouth and pendant sit on it
     (paint: {id, dir, at}); every Agorzilla here then shows those same pictures, straight from agorzilla.com, in those same
     places (15.11.2026: "whatever stage and optics it has there, automatically"). A new painting there needs nothing here. */
  const AGZ = "https://agorzilla.com/";
  let paint = (() => { try { return JSON.parse(localStorage.getItem("agz-paint") || "null"); } catch (e) { return null; } })();
  const PIECE = /(?:^|\/)(?:agz-)?(head|body|brow-l|brow-r|eye-l|eye-r|feet)\.webp(?:\?.*)?$/, FLAT = /agorzilla(?:-[a-z]+)?\.webp/;
  const mine = new WeakMap();   // what this set inline, so it can be taken back
  const put = (e, k, v) => { if (v == null || v === "") return; e.style.setProperty(k, v); if (!mine.has(e)) mine.set(e, new Set()); mine.get(e).add(k); };
  const takeBack = root => [root, ...root.querySelectorAll("*")].forEach(e => { const m = mine.get(e); if (m) { m.forEach(k => e.style.removeProperty(k)); mine.delete(e); } });
  const absUrl = v => String(v || "").replace(/url\("?([^")]+)"?\)/g, (m, u) => `url("${/^https?:/.test(u) ? u : AGZ + "assets/" + u}")`);
  const swap = (im, to) => { const u = im.getAttribute("src") || ""; if (!im.dataset.agzOrig && !u.startsWith(AGZ)) im.dataset.agzOrig = u; if (u !== to) im.setAttribute("src", to); };
  const unswap = im => { if (im.dataset.agzOrig) { im.setAttribute("src", im.dataset.agzOrig); delete im.dataset.agzOrig; } };
  function painted(p) {
    const dir = AGZ + (p.dir || `assets/rig/${p.id}/`), at = p.at || {}, A = s => at[s] || {};
    document.querySelectorAll("[data-agz-look]").forEach(el => {
      takeBack(el);
      el.querySelectorAll("img").forEach(im => {
        const u = im.dataset.agzOrig || im.getAttribute("src") || "", m = PIECE.exec(u);
        if (m) swap(im, dir + m[1] + ".webp"); else if (FLAT.test(u)) swap(im, dir + "feet.webp");
      });
      const box = (sel, d, keys) => el.querySelectorAll(sel).forEach(e => keys.forEach(k => put(e, k, d[k])));
      for (const s of ["l", "r"]) {
        box(`.eye.${s}, .lid.${s}`, A(`:is(.eye, .lid).${s}`), ["left", "top", "width", "height"]);
        box(`.brow.${s}`, A(`img.brow.${s}`), ["left", "top", "width"]); el.querySelectorAll(`.brow.${s}`).forEach(e => put(e, "height", "auto"));
        for (const t of ["b", "s"]) el.querySelectorAll(`.lid.${s} ${t}`).forEach(e => put(e, "background-image", absUrl(A(`.lid.${s} ${t}`)["background-image"])));
      }
      box(".mouth", A(".mouth"), ["left", "top", "width"]); box(".tgw", A(".tgw"), ["left", "top", "width"]);
      const mask = (sel, v) => el.querySelectorAll(sel).forEach(e => { put(e, "mask-image", absUrl(v)); put(e, "-webkit-mask-image", absUrl(v)); });
      mask(".agz-pl", A(".plight")["mask-image"]); mask("img.agz-back", A(".silver")["mask-image"]); mask("img.agz-muz", A(".grey")["mask-image"]);
      el.querySelectorAll(".hd, .head, .gaze").forEach(e => put(e, "transform-origin", A(".gaze")["transform-origin"] || A(".head")["transform-origin"]));
      // the painting is already its age: no shrinking eyes, darker skin or lifted head on top
      for (const [k, v] of [["--agz-eye", "1"], ["--agz-skin", "1"], ["--agz-grey", "0"], ["--agz-iris", "1"], ["--agz-nx", "0%"], ["--agz-ny", "0%"], ["--agz-hs", "1"]]) put(el, k, v);
      el.dataset.agzPaint = p.id;
    });
    document.querySelectorAll('img[src*="agorzilla"]').forEach(im => { if (!im.closest("[data-agz-look]") && FLAT.test(im.dataset.agzOrig || im.getAttribute("src"))) swap(im, dir + "feet.webp"); });
  }
  function unpainted() {
    document.querySelectorAll("[data-agz-look]").forEach(el => { takeBack(el); delete el.dataset.agzPaint; });
    document.querySelectorAll("img[data-agz-orig]").forEach(unswap);
  }
  const drawn = (prev, now, t) => {   // the painting (or none) after the stage: grow() sets the baby-based age, a painting overrides it
    const was = prev && prev.id;
    paint = now; try { localStorage.setItem("agz-paint", JSON.stringify(now)); } catch (e) { /* the next page fetches it again */ }
    if (now) painted(now); else if (was) { unpainted(); grow(stage, t); }
    return (was || null) !== (now ? now.id : null);
  };
  const apply = d => {
    const t = d && d.traits; if (!t) return;
    // agorzilla.com's rules v8 (from 20.11.2026): a colour drawn from the hash is named by its hue, "Teal 187°"
    const hue = v => { const m = /\s(\d{1,3})°$/.exec(String(v || "")); return m ? Number(m[1]) : null; };
    const hp = hue(t.pendant), hf = hue(t.fur);
    const pend = hp != null ? `hsl(${hp} 90% 75%)` : PEND[key(t.pendant)], fur = hf != null ? `sepia(.6) saturate(1.7) hue-rotate(${hf - 35}deg) contrast(1.08)` : FUR[key(t.fur)];
    document.querySelectorAll("[data-agz-look]").forEach(el => {
      if (pend) el.style.setProperty("--agz-pend", pend);
      if (fur) el.style.setProperty("--agz-fur", fur);
      el.dataset.agzPendant = key(t.pendant); el.dataset.agzFur = key(t.fur);
    });
    const prev = paint; paint = d.paint && d.paint.id ? d.paint : null;   // before grow, so the pages' listeners see it
    const grew = grow(key(d.stage), t), repainted = drawn(prev, paint, t);
    if (grew || repainted) dispatchEvent(new CustomEvent("agz-stage", { detail: stage }));
  };
  const poll = async () => {
    try { const r = await fetch("https://agorzilla.com/chain/latest.json", { cache: "no-store" }); if (r.ok) apply(await r.json()); } catch (e) { /* keeps the last look */ }
  };
  window.AgzLook = { apply, src: u => src(u, stage), get stage() { return stage; }, get paint() { return paint; } };
  // the remembered stage at once, so a grown-up never opens as a baby for the first seconds
  const early = () => { if (stage !== "baby") grow(stage, null); if (paint) painted(paint); };
  document.readyState === "loading" && !document.querySelector("[data-agz-look]") ? addEventListener("DOMContentLoaded", early) : early();
  const me = document.currentScript;
  if (me && me.hasAttribute("data-poll")) {
    const go = () => { poll(); setInterval(() => { if (!document.hidden) poll(); }, 300000); };
    document.readyState === "loading" ? addEventListener("DOMContentLoaded", go) : go();
  }
})();
