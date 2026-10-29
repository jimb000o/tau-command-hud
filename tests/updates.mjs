/* Checks assets/updates.json, the Updates log every page reads:
   - it is valid JSON, a list of {tag, on, html[, major]} with a date in "on" and a unique id in each "major"
   - no merge-conflict markers in it or in the Chinese dictionaries
   - with BASE=<file> (the log on the target branch): no entry there is missing here, so a merge did not drop one
   - with BASE and PR_TITLE (a pull request): the pull request adds at least one entry, so every release is in the log;
     a change nobody would notice (a test, a typo in a comment) says "[no log]" in its title
   - every entry has its Chinese text in assets/i18n/zh/hud.js (keyed by the English html)

   Run: node tests/updates.mjs        BASE=/tmp/base-updates.json node tests/updates.mjs */
import { readFile, readdir } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const fail = m => errors.push(m);

/* conflict markers anywhere a busy day tends to leave them */
const files = ["assets/updates.json", "index.html", "assets/nav.js", ...(await readdir(join(ROOT, "assets/i18n/zh"))).map(f => "assets/i18n/zh/" + f)];
for (const f of files) {
  const text = await readFile(join(ROOT, f), "utf8");
  text.split("\n").forEach((l, i) => { if (/^(<{7}|={7}|>{7})( |$)/.test(l)) fail(`${f}:${i + 1} merge-conflict marker "${l.slice(0, 20)}"`); });
}

let list = null;
try { list = JSON.parse(await readFile(join(ROOT, "assets/updates.json"), "utf8")); }
catch (e) { fail(`assets/updates.json is not valid JSON: ${e.message}`); }
if (list && !Array.isArray(list)) { fail("assets/updates.json must be a list"); list = null; }

if (list) {
  const majors = new Set();
  list.forEach((e, i) => {
    const at = `entry ${i + 1} (${e && e.tag})`;
    if (!e || typeof e !== "object") return fail(`${at} is not an object`);
    for (const k of ["tag", "on", "html"]) if (typeof e[k] !== "string" || !e[k].trim()) fail(`${at} has no "${k}"`);
    if (typeof e.on === "string" && !/^\d{4}-\d{2}-\d{2}$/.test(e.on)) fail(`${at} "on" is not a date like 2026-10-28: ${e.on}`);
    if ("major" in e) {   // the Telegram site post: {id, title, text, link}; the id keeps it from being posted twice
      const m = e.major;
      if (!m || typeof m !== "object") fail(`${at} "major" should be {id, title, text, link}`);
      else {
        for (const k of ["id", "title", "text", "link"]) if (typeof m[k] !== "string" || !m[k].trim()) fail(`${at} "major" has no "${k}"`);
        if (majors.has(m.id)) fail(`${at} "major" id "${m.id}" is used twice`);
        majors.add(m.id);
      }
    }
    for (const k of Object.keys(e)) if (!["tag", "on", "html", "major", "backfill"].includes(k)) fail(`${at} has an unknown field "${k}"`);
  });

  if (process.env.BASE) {
    let base = [];
    try { base = JSON.parse(await readFile(process.env.BASE, "utf8")); } catch (e) { console.log(`(no readable base log at ${process.env.BASE}, skipping the dropped-entry check)`); }
    /* counted per tag and day, so rewording an old entry is fine but losing one is not */
    const count = l => l.reduce((m, e) => m.set(e.tag + " of " + e.on, (m.get(e.tag + " of " + e.on) || 0) + 1), new Map());
    const here = count(list);
    for (const [k, n] of count(base)) if ((here.get(k) || 0) < n) fail(`entry ${k} from the target branch is missing (a merge dropped it?): ${n} there, ${here.get(k) || 0} here`);
    const title = process.env.PR_TITLE;
    if (title !== undefined && base.length && list.length <= base.length && !/\[no log\]/i.test(title))
      fail(`this pull request adds no entry to the Updates log. Every release gets one: append {tag, on, html} to assets/updates.json `
         + `(and its Chinese to assets/i18n/zh/hud.js); a new page or big feature also gets "major" for its own Telegram post. `
         + `Only a change no visitor would notice may say "[no log]" in its title.`);
  }

  /* the zh dictionary for the log; a dictionary only calls TauI18n.add */
  const dict = {};
  globalThis.TauI18n = { add: o => Object.assign(dict, o.strings || {}) };
  for (const f of ["common", "hud"]) {
    try { new Function(await readFile(join(ROOT, `assets/i18n/zh/${f}.js`), "utf8"))(); }
    catch (e) { fail(`assets/i18n/zh/${f}.js does not run: ${e.message}`); }
  }
  /* the log is translated as text: the links in an entry are kept, their words translated in place */
  const text = h => h.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
  const keys = new Set([...Object.keys(dict), ...Object.keys(dict).map(text)]);
  for (const e of list) if (e && typeof e.html === "string" && !keys.has(e.html) && !keys.has(text(e.html))) fail(`entry ${e.tag} of ${e.on} has no Chinese in assets/i18n/zh/hud.js: "${e.html.slice(0, 80)}…"`);
}

/* every Chinese dictionary must at least run */
globalThis.TauI18n = { add: () => {} };
for (const f of await readdir(join(ROOT, "assets/i18n/zh"))) {
  try { new Function(await readFile(join(ROOT, "assets/i18n/zh", f), "utf8"))(); }
  catch (e) { fail(`assets/i18n/zh/${f} does not run: ${e.message}`); }
}

if (errors.length) { console.log(`❌ Updates log and dictionaries: ${errors.length} problem(s)\n` + errors.map(e => "- " + e).join("\n")); process.exit(1); }
console.log(`✅ Updates log: ${list.length} entries, valid, each with its Chinese text; dictionaries run; no conflict markers.`);
