# Checks

Every pull request runs `.github/workflows/checks.yml`. The same checks run locally:

| Check | Command | Fails when |
|---|---|---|
| Pages | `npm i --no-save playwright && npx playwright install chromium && node tests/pages.mjs` | a page throws a JavaScript error (simulation, or live with the node offline), a Chinese page shows an English text, or a page scrolls at 2560 × 1440 or 2000 × 1125 |
| Rule words | `node tests/rulewords.mjs` | a sentence on `/builder/` no longer gives the wallet block it should, something not possible on the testnet builds a rule anyway, or a rule it writes is read differently by the exact reader (`assets/rulefacts.js`) than by its own plain reading |
| Updates log | `node tests/updates.mjs` | `assets/updates.json` is not valid (a "link" must be a tauhud.com path like `/gxp/` or an https address), lost an entry of the target branch, or an entry has no Chinese text in `assets/i18n/zh/hud.js`; a merge-conflict marker anywhere in the shared files |
| News line | `node tests/ticker.mjs` | a headline in `assets/ticker.json` has neither `since` nor `keep: true` (it would never leave the line), a bad date, or a text or hover without its Chinese or Japanese |
| White Rabbit Key's places at night | `node tests/room-night.mjs` (about one minute) | a place with a painted night (`<id>-night`) does not show it after dark, fetches it by day, or a place without one is darker than about half its noon light or sinks into the night's blue |
| White Rabbit Key, 100 players | `node tests/rabbit-sim.mjs` (by hand, about 30 min; `PLAYERS=10` for a short run) | a player throws a JavaScript error, gets stuck or never reaches the election; the report (`tests/out/rabbit-sim.md`) also lists places out of reach per screen, small text, plates that scroll, who wins by candidate and play style, and the test transactions sent |
| Live node light | `node tests/live-recover.mjs` (by hand, about 4 min) | the HUD's Live node light does not turn red when a stand-in relay or its node goes offline, stays red once the node answers again, or does not return to green without a reload |
| Painted island | `node tests/art-recover.mjs` (by hand, about one minute) | White Rabbit Key keeps the drawn island after its art server (`node.tauhud.com/rico/art`) answers again, or keeps asking a server that has no painting |
| Server | `tests/python.sh` | any `infra/*/test_*.py` fails (the checker test needs the built engine and runs in the node image; the Guardian test needs IDNI's tau-testnet checkout in `TAU_TESTNET_DIR`, which the CI job fetches at our node's commit) |

`node tests/pages.mjs vote account` checks only those pages. The browser never leaves the machine: every request outside the
local server is refused, and the clock is fixed, so the simulation shows the same chain on every run.

English that may stay on Chinese pages (names, code, addresses) is listed in `zh-known-english.txt`.
