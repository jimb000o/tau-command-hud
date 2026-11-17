/* Wide screens (2560 × 1440, an ultrawide 3440 × 1440, a TV): a subpage uses the whole screen instead of standing in a
   narrow column with empty sides or an empty lower half.

   On a screen wider than 1700 CSS px (landscape), <html> gets the class "wfit": the page's .wrap drops its max-width and
   is zoomed by --z. The zoom is the largest one at which the page still fits the screen without scrolling: the wider the
   screen, the more columns the page lays out (its grids fill the width), so it gets shorter and can grow larger.
   A page a little too long for the screen (1920 × 1080 with the browser's bars) shrinks by up to 15 % instead of scrolling.
   Laptops (1366 × 768), small screens and phones keep the page as it was.

   Use: <script src="../assets/widefit.js"></script> after the page's markup, then TauWideFit.fit() once the page has
   drawn its content (it fits itself again on resize, when the fonts arrive and when the page's text changes).
   A page that scrolls inside its own panels: <html data-wfit="one" data-wfit-in=".list, aside">. It is zoomed at least as if
   laid out for 1600 × 860, and further while those panels still show all they hold. */
(function () {
  const root = document.documentElement;
  const FROM = 1700;                // narrower screens keep the page as designed
  const MIN_W = 1300;               // never laid out narrower than this many CSS px
  const ZMAX = 2.4;
  let busy = false, last = 0, timer = 0;
  const wrap = () => document.querySelector(".wrap");
  /* fits: the page does not scroll, and the panels that scroll inside (data-wfit-in, a "one" page) show all they hold */
  const fits = () => root.scrollHeight <= innerHeight + 1 && [...document.querySelectorAll(root.dataset.wfitIn || "x-none")].every(e => !e.offsetParent || e.scrollHeight <= e.clientHeight + 1);
  function set(z) {
    const cs = getComputedStyle(document.body), pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    root.style.setProperty("--z", z.toFixed(3)); root.style.setProperty("--wfH", Math.floor((innerHeight - pad) / z) + "px");   // the screen's height in the page's own (zoomed) pixels
  }
  let settle = 0;
  function fit(again) {
    const w = innerWidth, h = innerHeight, el = wrap();
    const on = !!el && w > FROM && w / h >= 1.3 && h >= 640;
    root.classList.toggle("wfit", on);
    if (!on) { root.style.removeProperty("--z"); root.style.removeProperty("--wfH"); last = 0; return; }
    busy = true;
    const hi = Math.min(ZMAX, w / MIN_W);
    let z;
    {
      /* a page that scrolls inside its panels starts laid out for about 1600 × 860; it grows past that while its panels still show everything */
      const one = root.dataset.wfit === "one", base = one ? Math.max(1, Math.min(hi, w / 1600, h / 860)) : 1;
      let lo = base, top = hi;
      set(lo);
      if (!fits()) {   // too long at its normal size: a little smaller (down to 85 %), if that fits
        let a = base * .85, b = base; set(a);
        if (fits()) { for (let i = 0; i < 7; i++) { const m = (a + b) / 2; set(m); if (fits()) a = m; else b = m; } lo = a; }
      }
      else if (fits()) {
        set(top);
        if (fits()) lo = top;
        else for (let i = 0; i < 9; i++) { const m = (lo + top) / 2; set(m); if (fits()) lo = m; else top = m; }
      }
      z = Math.floor(lo * 100) / 100;   // a hair under the limit, so a changing number cannot tip it into a scroll bar
    }
    set(z); last = z;
    busy = false;
    /* the header rows (assets/nav.js) undo the zoom for themselves a moment later, which changes the page's height: measure once more then */
    clearTimeout(settle); if (again !== true) settle = setTimeout(() => fit(true), 250);
    window.dispatchEvent(new Event("tau:widefit"));
  }
  function later(ms) { clearTimeout(timer); timer = setTimeout(() => fit(), ms || 120); }
  addEventListener("resize", () => later(120));
  document.fonts && document.fonts.ready.then(() => later(0));
  addEventListener("load", () => later(0));
  /* new text (live numbers, a filter, a language) can make the page longer or shorter: fit again, quietly */
  const watch = () => {
    const el = wrap(); if (!el || !window.MutationObserver) return;
    let at = 0;
    new MutationObserver(() => {
      if (busy || !root.classList.contains("wfit")) return;
      if (root.scrollHeight > innerHeight + 1 || Date.now() - at > 10000) { at = Date.now(); later(400); }   // at once when it spills, otherwise at most every ten seconds
    }).observe(el, { childList: true, subtree: true, characterData: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { watch(); fit(); }); else { watch(); fit(); }
  window.TauWideFit = { fit, z: () => last || 1 };
})();
