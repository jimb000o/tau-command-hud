/* Agorzilla's look, as the evenings decided it: the same chain state agorzilla.com shows (its chain/latest.json).
   Every Agorzilla on Tau HUD (the HUD's puppet, the My Tau card, /start/) carries [data-agz-look]; this sets their
   pendant light and fur from the votes, so a new evening's result shows here by itself, with nobody changing a file.
   The pendant light is a mask of the collar LEDs and the medal (assets/rig/agz-pendant.webp, made by agorzilla.com's
   tools/pendant_lights.py) tinted in its colour, as on agorzilla.com. Pages that already read latest.json call
   AgzLook.apply(d); the others give the script data-poll and it reads it every 5 min. */
(() => {
  "use strict";
  const PEND = { gold: "#ffd36b", green: "#6ee7a0", blue: "#7dd3fc", rose: "#fda4af", white: "#ffffff" };
  const FUR = { natural: "none", copper: "sepia(.55) saturate(1.7) hue-rotate(-12deg) brightness(1.05)", silver: "grayscale(.85) brightness(1.25) contrast(1.05)",
    midnight: "sepia(.3) hue-rotate(180deg) saturate(1.6) brightness(.9)", moss: "sepia(.4) hue-rotate(50deg) saturate(1.5)", honey: "sepia(.7) saturate(2) brightness(1.15)" };
  const key = v => String(v || "").trim().toLowerCase();
  const apply = d => {
    const t = d && d.traits; if (!t) return;
    const pend = PEND[key(t.pendant)], fur = FUR[key(t.fur)];
    document.querySelectorAll("[data-agz-look]").forEach(el => {
      if (pend) el.style.setProperty("--agz-pend", pend);
      if (fur) el.style.setProperty("--agz-fur", fur);
      el.dataset.agzPendant = key(t.pendant); el.dataset.agzFur = key(t.fur);
    });
  };
  const poll = async () => {
    try { const r = await fetch("https://agorzilla.com/chain/latest.json", { cache: "no-store" }); if (r.ok) apply(await r.json()); } catch (e) { /* keeps the last look */ }
  };
  window.AgzLook = { apply };
  const me = document.currentScript;
  if (me && me.hasAttribute("data-poll")) {
    const go = () => { poll(); setInterval(() => { if (!document.hidden) poll(); }, 300000); };
    document.readyState === "loading" ? addEventListener("DOMContentLoaded", go) : go();
  }
})();
