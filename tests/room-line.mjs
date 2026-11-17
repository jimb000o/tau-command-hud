/* The room, 1999: the line on the main screen (assets/room.js) understands the questions a beginner types, and every
   question it suggests itself ("try: …", "next: …") is one its own script answers, so it never sends anyone in a circle.
   Reads the INTENT list and the follow-up words straight from room.js; no browser.

   Run: node tests/room-line.mjs */
import { readFileSync } from "node:fs";
const src = readFileSync(new URL('../assets/room.js', import.meta.url), 'utf8');
const INTENT = eval(src.slice(src.indexOf('const INTENT = [') + 15, src.indexOf('  const MORE =')).replace(/;\s*$/, ''));
const MORE = eval(src.match(/const MORE = (\/.*\/);/)[1]);
const decide = (s0, topic) => { const s = s0.trim().toLowerCase(); const hit = INTENT.find(([re]) => re.test(s)), short = s.split(/\s+/).length <= 3;
  if (topic && MORE.test(s) && !hit) return "more:" + topic; return hit ? hit[1] : (/^#?\d+$/.test(s) ? "block" : "ASK"); };
const T = [["what are the rules?","rules"],["what is a block?","block"],["who seals them?","validators"],["show me a transaction","tx"],["hi","hello"],["hello!","hello"],
["who are you?","me"],["are you an AI?","me"],["help","help"],["what can i do here","help"],["how do the rules change?","changes"],["is there a rule change open","changes"],
["what's the fee","fee"],["how much does a transaction cost","fee"],["how many validators are there","validators"],["what is tau","tau"],["what is tau net","tau"],
["how do i start","start"],["i want a wallet","start"],["is the node online","status"],["thanks!","thanks"],["block 12","block"],["#105","block"],["105","block"],
["show me the last 5 blocks","blocks"],["blocks","blocks"],["what is waiting","pending"],["pending","pending"],["rules","rules"],["validators","validators"],["tx a1fe","tx"],
["what's the newest block","block"],["what does a block contain","block"],["what are personal rules","rules"],["who votes","changes"],["what is a merkle tree","ASK"],["why is the sky blue","ASK"],
["what is consensus","ASK"]];
let bad = 0; for (const [q, w] of T) { const g = decide(q); if (g !== w) { bad++; console.log("MISS", JSON.stringify(q), "→", g, "want", w); } }
for (const [q, t, w] of [["more","block","more:block"],["yes","rules","more:rules"],["why?","tx","more:tx"],["how do i start","rules","start"],["and the fee?","rules","fee"],["tell me more","changes","more:changes"]]) { const g = decide(q, t); if (g !== w) { bad++; console.log("MISS", q, t, "→", g, "want", w); } }
// every suggestion the line makes must be answerable by the script
const sugg = [...src.matchAll(/(?:try|ask|next|say): ([^"]+?)["']/g)].map(m => m[1]).join(" · ").split(/ · | or: |, or /).map(x => x.replace(/^(or: |say: )/, "").trim()).filter(x => x.length > 2);
for (const q of new Set(sugg)) if (!MORE.test(q)) { const g = decide(q); if (g === "ASK") { bad++; console.log("SUGGESTION NOT MINE", JSON.stringify(q)); } }
console.log(bad ? `❌ the room's line: ${bad} question(s) misunderstood` : `✅ the room's line understands all ${T.length} test questions and every question it suggests`);
process.exit(bad ? 1 : 0);
