# Checks

Every pull request runs `.github/workflows/checks.yml`. The same checks run locally:

| Check | Command | Fails when |
|---|---|---|
| Pages | `npm i --no-save playwright && npx playwright install chromium && node tests/pages.mjs` | a page throws a JavaScript error (simulation, or live with the node offline), a Chinese page shows an English text, or a page scrolls at 2560 × 1440 or 2000 × 1125 |
| Updates log | `node tests/updates.mjs` | `assets/updates.json` is not valid, lost an entry of the target branch, or an entry has no Chinese text in `assets/i18n/zh/hud.js`; a merge-conflict marker anywhere in the shared files |
| Server | `tests/python.sh` | any `infra/*/test_*.py` fails (the checker test needs the built engine and runs in the node image) |

`node tests/pages.mjs vote account` checks only those pages. The browser never leaves the machine: every request outside the
local server is refused, and the clock is fixed, so the simulation shows the same chain on every run.

English that may stay on Chinese pages (names, code, addresses) is listed in `zh-known-english.txt`.
