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
    if (changed) dispatchEvent(new CustomEvent("agz-stage", { detail: st }));
  };
  const apply = d => {
    const t = d && d.traits; if (!t) return;
    const pend = PEND[key(t.pendant)], fur = FUR[key(t.fur)];
    document.querySelectorAll("[data-agz-look]").forEach(el => {
      if (pend) el.style.setProperty("--agz-pend", pend);
      if (fur) el.style.setProperty("--agz-fur", fur);
      el.dataset.agzPendant = key(t.pendant); el.dataset.agzFur = key(t.fur);
    });
    grow(key(d.stage), t);
  };
  const poll = async () => {
    try { const r = await fetch("https://agorzilla.com/chain/latest.json", { cache: "no-store" }); if (r.ok) apply(await r.json()); } catch (e) { /* keeps the last look */ }
  };
  window.AgzLook = { apply, src: u => src(u, stage), get stage() { return stage; } };
  // the remembered stage at once, so a grown-up never opens as a baby for the first seconds
  const early = () => { if (stage !== "baby") grow(stage, null); };
  document.readyState === "loading" && !document.querySelector("[data-agz-look]") ? addEventListener("DOMContentLoaded", early) : early();
  const me = document.currentScript;
  if (me && me.hasAttribute("data-poll")) {
    const go = () => { poll(); setInterval(() => { if (!document.hidden) poll(); }, 300000); };
    document.readyState === "loading" ? addEventListener("DOMContentLoaded", go) : go();
  }
})();
