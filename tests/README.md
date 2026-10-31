# Checks

Every pull request runs `.github/workflows/checks.yml`. The same checks run locally:

| Check | Command | Fails when |
|---|---|---|
| Pages | `npm i --no-save playwright && npx playwright install chromium && node tests/pages.mjs` | a page throws a JavaScript error (simulation, or live with the node offline), a Chinese page shows an English text, or a page scrolls at 2560 × 1440 or 2000 × 1125 |
| Updates log | `node tests/updates.mjs` | `assets/updates.json` is not valid, lost an entry of the target branch, or an entry has no Chinese text in `assets/i18n/zh/hud.js`; a merge-conflict marker anywhere in the shared files |
| White Rabbit Key, 100 players | `node tests/rabbit-sim.mjs` (by hand, about 30 min; `PLAYERS=10` for a short run) | a player throws a JavaScript error, gets stuck or never reaches the election; the report (`tests/out/rabbit-sim.md`) also lists places out of reach per screen, small text, plates that scroll, who wins by candidate and play style, and the test transactions sent |
| Server | `tests/python.sh` | any `infra/*/test_*.py` fails (the checker test needs the built engine and runs in the node image) |

`node tests/pages.mjs vote account` checks only those pages. The browser never leaves the machine: every request outside the
local server is refused, and the clock is fixed, so the simulation shows the same chain on every run.

English that may stay on Chinese pages (names, code, addresses) is listed in `zh-known-english.txt`.
