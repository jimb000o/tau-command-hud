/* One check for every picture and film taken of tauhud.com (site-shots.mjs, film.mjs): it runs inside the page and
   says what is wrong with it as it shows now. Live mode, real chain, the live data arrived, no simulation banner and
   no made-up address. */
// what is wrong with the page as it shows now; "" when it is fit for a post
export const CHECK = () => {
  const t = s => (document.querySelector(s)?.textContent || "").trim();
  const hud = document.querySelector("#chipMode");   // the front page has its own mode chip (index.html)
  const mode = hud || document.querySelector("#tnMode");
  if (!mode) return "no header";
  const m = (mode.querySelector("b")?.textContent || "").trim();
  if (/simulation/i.test(m)) return `mode chip says ${m}`;
  if (!mode.classList.contains("live")) return `mode chip not green (${m || "empty"})`;
  if (!hud) {
    if (/^[–-]?$/.test(t("#tnHeight b"))) return "block height missing";
    if (/^[–-]?$/.test(t("#tnOnline b"))) return "nodes online missing";
  }
  const dashes = [...document.querySelectorAll("header .chip b, .rail .chip b")].filter(b => b.offsetParent && /^[–-]$/.test(b.textContent.trim()));
  if (dashes.length) return `${dashes.length} header chips still empty`;
  const body = document.body.innerText;
  if (/SIMULATION\s*·/.test(body)) return "simulation banner on the page";
  const fake = body.match(/\b([0-9a-f]{2})\1{3,}/i);
  if (fake) return `made-up address on the page (${fake[0]})`;
  return "";
};
