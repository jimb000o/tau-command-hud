/* Checks assets/rulewords.js, the plain words behind tauhud.com/builder/:
   1. sentences → the wallet's blocks (limit, list, day, co-signer, freeze), and what is not possible says so;
   2. every rule it writes is read by the exact reader (assets/rulefacts.js): one answer for every kind of payment,
      and the plain reading of the blocks (judge) gives that same answer for each kind;
   3. the test payments it makes get the answer it predicts from the exact reader too;
   4. a part that never decides is found, and a wallet rule read back from its Tau text gives the same text again;
   5. sentences in German, Chinese and Japanese give the same blocks and the same "no, because" as the English ones.
   Run: node tests/rulewords.mjs */
import { createRequire } from "node:module";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const req = createRequire(import.meta.url);
const RW = req(join(ROOT, "assets", "rulewords.js")), RF = req(join(ROOT, "assets", "rulefacts.js"));
const fails = [];
let checked = 0;
const check = (ok, what) => { checked++; if (!ok) fails.push(what); };

const NOW = new Date(2026, 10, 12, 10, 0, 0);   // Thursday 12 Nov 2026, local time
const G = "cd".repeat(48), MIA = "ab".repeat(48), LEE = "12".repeat(48), X = "ef".repeat(48);
const ctx = { now: NOW, guardian: G, book: [{ name: "Mia", addr: MIA }, { name: "Mia Lee", addr: LEE }] };
const day = (y, m, d) => Math.floor(new Date(y, m - 1, d).getTime() / 1000);
const hex96 = v => BigInt(v).toString(16).padStart(96, "0");

/* ---- 1. words → blocks ---- */
const WORDS = [
  ["At most 5,000 per payment", { cap: 5000 }],
  ["max 500", { cap: 500 }],
  ["no more than 1.000 per transfer", { cap: 1000 }],
  ["up to 2k", { cap: 2000 }],
  ["under 50", { cap: 49 }],
  ["no payments over 2000", { cap: 2000 }],
  ["nothing above 300", { cap: 300 }],
  ["co-sign above 1,000", { co: [1000, G] }],
  ["Above 1k the Guardian co-signs", { co: [1000, G] }],
  ["above 1000 Mia must co-sign", { co: [1000, MIA] }],
  ["above 250 a second signature from " + X, { co: [250, X] }],
  ["nothing before Friday", { from: day(2026, 11, 13) }],
  ["nothing before Thursday", { from: day(2026, 11, 19) }],
  ["no money leaves before Fri", { from: day(2026, 11, 13) }],
  ["locked until 2026-12-24", { from: day(2026, 12, 24) }],
  ["nothing leaves before 1 Dec", { from: day(2026, 12, 1) }],
  ["not before January 5, 2027", { from: day(2027, 1, 5) }],
  ["lock for 90 days", { from: day(2027, 2, 10) }],
  ["nothing until tomorrow", { from: day(2026, 11, 13) }],
  ["only to Mia", { only: [MIA] }],
  ["only to Mia Lee", { only: [LEE] }],
  ["only to " + X, { only: [X] }],
  ["only to my address book", { only: [MIA, LEE] }],
  ["freeze", { freeze: true }],
  ["block everything", { freeze: true }],
  ["At most 5,000 per payment, above 1,000 the Guardian co-signs, nothing before Friday", { cap: 5000, co: [1000, G], from: day(2026, 11, 13) }],
  ["Only to Mia and at most 300 per payment; nothing before 2027-01-01", { only: [MIA], cap: 300, from: day(2027, 1, 1) }],
  ["max 100\nmax 200", { cap: 200 }],
  /* a word for "everything" followed by an amount is a limit, never a freeze */
  ["block everything over 1000", { cap: 1000 }],
  ["stop all payments above 2k", { cap: 2000 }],
  ["payments over 500 are blocked", { cap: 500 }],
  ["don't let me send more than 200", { cap: 200 }],
  ["only 100 per payment", { cap: 100 }],
  ["stop all payments", { freeze: true }],
  ["no payments", { freeze: true }],
  ["pause my wallet", { freeze: true }],
  ["block everything over 1000 unless Mia signs", { co: [1000, MIA] }],
  ["above 1000, the Guardian co-signs", { co: [1000, G] }],
  ["block everything except Mia", { only: [MIA] }],
  ["nothing to anyone but Mia", { only: [MIA] }],
  ["block payments to strangers", { only: [MIA, LEE] }],
  ["only to Mia at most 300 per payment", { only: [MIA], cap: 300 }],
  ["lock my savings until 2028", { from: day(2028, 1, 1) }],
  ["nothing before the end of 2027", { from: day(2028, 1, 1) }],
  ["nothing until next month, then at most 100", { cap: 100, from: day(2026, 12, 1) }],
  /* the exception may come first, and a time span may be said in words */
  ["Except Mia, block everything", { only: [MIA] }],
  ["except for Mia, nothing leaves", { only: [MIA] }],
  ["locked for two weeks", { from: day(2026, 11, 26) }],
  ["nothing in the next 90 days", { from: day(2027, 2, 10) }],
  /* a day that opens the wallet: said as "from", "after", or as what is closed before it */
  ["payments from Friday", { from: day(2026, 11, 13) }],
  ["only after 1 Dec", { from: day(2026, 12, 1) }],
  ["from now on nothing before Friday", { from: day(2026, 11, 13) }],
  ["hold everything till 1 Jan", { from: day(2027, 1, 1) }],
  /* the second half says the list again, it is no freeze; a polite word and a unit are not parts of their own */
  ["only to Mia, block everything else", { only: [MIA] }],
  ["only to Mia, nobody else", { only: [MIA] }],
  ["please, at most 500", { cap: 500 }],
  ["at most 500 Test-AGRS", { cap: 500 }],
  ["max. 500", { cap: 500 }],
  ["nothing before Friday, per payment at most 300", { cap: 300, from: day(2026, 11, 13) }],
  ["nothing before Friday, under 50", { cap: 49, from: day(2026, 11, 13) }],
  ["at most 500, nobody except Mia", { cap: 500, only: [MIA] }],
  ["above 1000 only with Mia", { co: [1000, MIA] }],
  ["above 1000 only with second signature\nonly to Mia, all else block", { co: [1000, G], only: [MIA] }],
];
const shape = r => { r = r || {}; return JSON.stringify({ ...(r.cap != null ? { cap: r.cap } : {}), ...(r.co ? { co: [r.co.limit, r.co.who[0]] } : {}), ...(r.from != null ? { from: r.from } : {}), ...(r.only && r.only.length ? { only: r.only } : {}), ...(r.freeze ? { freeze: true } : {}) }); };
const wanted = w => JSON.stringify({ ...(w.cap != null ? { cap: w.cap } : {}), ...(w.co ? { co: w.co } : {}), ...(w.from != null ? { from: w.from } : {}), ...(w.only ? { only: w.only } : {}), ...(w.freeze ? { freeze: true } : {}) });
const reads = (text, want, c) => {
  const p = RW.parse(text, c);
  check(shape(p.rule) === wanted(want), `“${text}”: wanted ${JSON.stringify(want)}, got ${shape(p.rule)}`);
  check(p.items.every(i => i.kind !== "no"), `“${text}”: a part was not understood: ${p.items.filter(i => i.kind === "no").map(i => i.src).join(" | ")}`);
};
const refuses = (text, code, c) => {
  const p = RW.parse(text, c);
  check(!p.rule && p.items.length === 1 && p.items[0].kind === "no" && p.items[0].code === code, `“${text}”: wanted no rule (${code}), got ${JSON.stringify(p.items.map(i => [i.kind, i.code]))}`);
};
for (const [text, want] of WORDS) reads(text, want, ctx);
/* what is not possible, or not understood, builds nothing and says which */
const NO = [["max 100 a day", "period"], ["at most 500 per week", "period"], ["only on weekdays", "clock"], ["between 9 and 17 o'clock", "clock"], ["keep at least 1000", "balance"],
  ["never to " + X, "blocklist"], ["hello world", "unknown"], ["only to Bob", "only-who"], ["nothing before", "day"], ["co-sign everything", "co-amount"], ["max 99999999", "range"],
  /* part of a coin is never rounded; an exception, a forbidden payee and an unknown co-signer build nothing and say so */
  ["at most 1,5 per payment", "whole"], ["at most 1.5 per payment", "whole"], ["above 2.5 the Guardian co-signs", "whole"],
  ["send at most 100 to anyone except Mia", "except"], ["above 1000 the Guardian co-signs except for Mia", "except"],
  ["block all payments to Mia", "blocklist"], ["block everything over 1k unless my brother signs", "co-who"], ["block everything except Bob", "only-who"],
  ["payments above 1000", "above-what"],
  /* a day that closes the wallet is an end date; it is never turned round into "nothing before" */
  ["no payments after 1 Dec", "end"], ["no more payments after 1 Dec", "end"], ["nothing after Friday", "end"], ["nothing from Friday on", "end"],
  ["payments only until Friday", "end"], ["pay by Friday", "end"], ["locked after 2028", "end"], ["starting Friday nothing leaves", "end"], ["from Friday until Sunday nothing", "end"],
  /* "do not block" is no block, and a freeze is never built from it; a day word without a day asks which day */
  ["don't freeze", "allow"], ["never block payments", "allow"], ["do not block payments to strangers", "allow"], ["don't lock my wallet", "allow"],
  ["block payments before", "day"], ["block everything else", "unknown"]];
for (const [text, code] of NO) refuses(text, code, ctx);
check(RW.parse("co-sign above 1000", { now: NOW }).items[0].code === "co-who", "a co-signature without a co-signer and without the Guardian asks who");
check(RW.parse("max 500, max 100 a day", ctx).rule.cap === 500, "a part that is not possible leaves the other parts standing");
check(/my brother/.test(RW.parse("block everything over 1k unless my brother signs", ctx).items[0].why), "an unknown co-signer is not named in the answer");
check(RW.parse("max 2.5k", ctx).rule.cap === 2500, "2.5k is a whole amount");
/* words of an understood part that are not in the rule are said, never dropped in silence */
const UNUSED = [["at most 100 to Mia", "“to Mia”"], ["at most 500 before Friday", "“before Friday”"], ["only to Mia and Bob", "“Bob”"], ["only to Mia before Friday", "“before Friday”"], ["freeze my llama", "“my llama”"]];
for (const [text, want] of UNUSED) { const p = RW.parse(text, ctx); check(p.rule && p.items[0].unused === want, `“${text}”: wanted ${want} reported as not used, got ${p.items[0].unused}`); }
for (const [text] of WORDS) check(RW.parse(text, ctx).items.every(i => !i.unused), `“${text}”: words reported as not used: ${RW.parse(text, ctx).items.map(i => i.unused).filter(Boolean).join(" ")}`);

/* ---- 5. German, Chinese and Japanese: the same blocks, the same "no, because" ---- */
const XM = "34".repeat(48), ctxL = { ...ctx, book: [...ctx.book, { name: "小明", addr: XM }] };
const DE = [
  ["Höchstens 500 pro Zahlung", { cap: 500 }],
  ["höchstens 5.000 Test-AGRS je Überweisung", { cap: 5000 }],
  ["Maximal 500", { cap: 500 }],
  ["Nicht mehr als 1.000", { cap: 1000 }],
  ["Nie mehr als 500 pro Zahlung", { cap: 500 }],
  ["Bis zu 2000 pro Zahlung", { cap: 2000 }],
  ["bis 500", { cap: 500 }],
  ["Unter 50", { cap: 49 }],
  ["Nichts über 300", { cap: 300 }],
  ["Keine Zahlungen über 2000", { cap: 2000 }],
  ["Zahlungen über 500 sperren", { cap: 500 }],
  ["Zahlungen auf 250 begrenzen", { cap: 250 }],
  ["Nur an Mia", { only: [MIA] }],
  ["Nur an Mia Lee", { only: [LEE] }],
  ["Zahlungen nur an Mia", { only: [MIA] }],
  ["Nur an mein Adressbuch", { only: [MIA, LEE, XM] }],
  ["Keine Zahlungen an Fremde", { only: [MIA, LEE, XM] }],
  ["Alles sperren außer Mia", { only: [MIA] }],
  ["Außer an Mia nichts senden", { only: [MIA] }],
  ["Außer an Mia, nichts senden", { only: [MIA] }],
  ["Niemand außer Mia", { only: [MIA] }],
  ["Nichts vor Freitag", { from: day(2026, 11, 13) }],
  ["Nichts vor dem 1. Dezember", { from: day(2026, 12, 1) }],
  ["Nicht vor dem 1.12.2026", { from: day(2026, 12, 1) }],
  ["Erst ab dem 5. Januar 2027", { from: day(2027, 1, 5) }],
  ["Gesperrt bis 2028", { from: day(2028, 1, 1) }],
  ["Bis Freitag gesperrt", { from: day(2026, 11, 13) }],
  ["Bis zum 24.12.2026 gesperrt", { from: day(2026, 12, 24) }],
  ["Gesperrt für 90 Tage", { from: day(2027, 2, 10) }],
  ["Nichts bis morgen", { from: day(2026, 11, 13) }],
  ["Nichts vor nächster Woche", { from: day(2026, 11, 16) }],
  ["Zahlungen erst nächsten Monat", { from: day(2026, 12, 1) }],
  ["Nichts in den nächsten zwei Wochen", { from: day(2026, 11, 26) }],
  ["Nichts vor dem 1.12. senden", { from: day(2026, 12, 1) }],
  ["Über 1000 zeichnet der Guardian mit", { co: [1000, G] }],
  ["Über 1.000 muss der Guardian mitzeichnen", { co: [1000, G] }],
  ["Ab 1000 zeichnet Mia mit", { co: [1000, MIA] }],
  ["Über 1000 muss Mia unterschreiben", { co: [1000, MIA] }],
  ["Über 1000 nur mit zweiter Unterschrift", { co: [1000, G] }],
  ["Zahlungen über 1000 brauchen eine zweite Unterschrift", { co: [1000, G] }],
  ["Über 250, zeichnet der Guardian mit", { co: [250, G] }],
  ["Alle Zahlungen sperren", { freeze: true }],
  ["Wallet einfrieren", { freeze: true }],
  ["Sperre alles", { freeze: true }],
  ["Nichts geht raus", { freeze: true }],
  ["Keine Zahlungen", { freeze: true }],
  ["Höchstens 5.000 pro Zahlung, über 1.000 zeichnet der Guardian mit, nichts vor Freitag", { cap: 5000, co: [1000, G], from: day(2026, 11, 13) }],
  ["Nur an Mia und höchstens 300 pro Zahlung; nichts vor dem 1.1.2027", { cap: 300, from: day(2027, 1, 1), only: [MIA] }],
  ["Nur an Mia, höchstens 300 pro Zahlung", { cap: 300, only: [MIA] }],
  ["Nichts vor Freitag, pro Zahlung höchstens 300", { cap: 300, from: day(2026, 11, 13) }],
  ["Höchstens 500. Nur an Mia.", { cap: 500, only: [MIA] }],
  ["Nur an Mia, alle anderen sperren", { only: [MIA] }],
  ["Bitte, höchstens 500", { cap: 500 }],
  ["Ich möchte, dass höchstens 200 pro Zahlung rausgehen", { cap: 200 }],
  ["Zahlungen, die über 1000 liegen, sperren", { cap: 1000 }],
  ["Ohne zweite Unterschrift nichts über 1000", { co: [1000, G] }],
  ["Zahlungen nur noch an Mia", { only: [MIA] }],
  ["Bitte sperre mein Wallet", { freeze: true }],
  ["Mein Konto einfrieren", { freeze: true }],
  ["Friere das Wallet ein", { freeze: true }],
  ["Stoppe alle Zahlungen", { freeze: true }],
  ["Es darf nichts mehr rausgehen", { freeze: true }],
  ["Ich will nur an Mia zahlen", { only: [MIA] }],
  ["Ab dem 1.1.2027 dürfen Zahlungen raus", { from: day(2027, 1, 1) }],
  ["Zahlungen sind erst ab 2028 erlaubt", { from: day(2028, 1, 1) }],
  ["Limit von 500 pro Zahlung", { cap: 500 }],
  ["Obergrenze 2.000", { cap: 2000 }],
  ["Mehr als 1000 nur mit Mia", { co: [1000, MIA] }],
  ["Nur an Mia Lee und Mia, max. 100", { cap: 100, only: [LEE, MIA] }],
];
const DE_NO = [["Höchstens 100 pro Tag", "period"], ["Maximal 500 pro Woche", "period"], ["Nur werktags", "clock"], ["Zwischen 9 und 17 Uhr", "clock"], ["Mindestens 1000 behalten", "balance"], ["Guthaben nie unter 1000", "balance"], ["Nie an Mia senden", "blocklist"], ["Keine Zahlungen an Mia", "blocklist"], ["Zahlungen an Mia sperren", "blocklist"], ["Nur an Bob", "only-who"], ["Nichts vor", "day"], ["Höchstens 1,5 pro Zahlung", "whole"], ["Höchstens 100 an alle außer Mia", "except"], ["Keine Zahlungen nach dem 1. Dezember", "end"], ["Zahlungen nur bis Freitag", "end"], ["Ab Freitag nichts mehr", "end"], ["Nichts nach Freitag", "end"], ["Wallet nicht sperren", "allow"], ["Zahlungen nicht blockieren", "allow"], ["Über 1000 muss mein Bruder unterschreiben", "co-who"], ["Zahlungen über 1000", "above-what"], ["Nichts unter der Woche", "clock"]];
const ZH = [
  ["每笔最多500", { cap: 500 }],
  ["每笔付款最多5000", { cap: 5000 }],
  ["最多500", { cap: 500 }],
  ["每次不超过1000", { cap: 1000 }],
  ["不能超过五百", { cap: 500 }],
  ["单笔上限是1万", { cap: 10000 }],
  ["500以内", { cap: 500 }],
  ["每笔不到50", { cap: 49 }],
  ["超过300的付款都拒绝", { cap: 300 }],
  ["不能付超过2000的款", { cap: 2000 }],
  ["只能付给Mia", { only: [MIA] }],
  ["只付给Mia Lee", { only: [LEE] }],
  ["仅限小明", { only: [XM] }],
  ["只能转账给小明和Mia", { only: [MIA, XM] }],
  ["只能付给Mia、小明", { only: [MIA, XM] }],
  ["只能付给我的地址簿", { only: [MIA, LEE, XM] }],
  ["只付给通讯录里的人", { only: [MIA, LEE, XM] }],
  ["不要付给陌生人", { only: [MIA, LEE, XM] }],
  ["除了Mia以外都不能付款", { only: [MIA] }],
  ["除了Mia以外，其他人都不能付款", { only: [MIA] }],
  ["除了小明，谁也不付", { only: [XM] }],
  ["12月1日之前不能付款", { from: day(2026, 12, 1) }],
  ["2026年12月24日之前锁定", { from: day(2026, 12, 24) }],
  ["周五之前不能付款", { from: day(2026, 11, 13) }],
  ["星期五前什么都不能转", { from: day(2026, 11, 13) }],
  ["明天之前不能转账", { from: day(2026, 11, 13) }],
  ["锁定到2028年", { from: day(2028, 1, 1) }],
  ["2028年之前锁定", { from: day(2028, 1, 1) }],
  ["12月1日以后才能付款", { from: day(2026, 12, 1) }],
  ["从12月1日起可以付款", { from: day(2026, 12, 1) }],
  ["90天后才能付款", { from: day(2027, 2, 10) }],
  ["锁定90天", { from: day(2027, 2, 10) }],
  ["下个月之前不能付款", { from: day(2026, 12, 1) }],
  ["十二月一日之前不能付款", { from: day(2026, 12, 1) }],
  ["超过1000需要守护者共同签名", { co: [1000, G] }],
  ["超过1000需要Guardian共同签名", { co: [1000, G] }],
  ["超过1000需要Mia签名", { co: [1000, MIA] }],
  ["1000以上需要第二个签名", { co: [1000, G] }],
  ["超过一千，需要小明确认", { co: [1000, XM] }],
  ["如果金额超过1000，就需要Mia签名", { co: [1000, MIA] }],
  ["冻结钱包", { freeze: true }],
  ["冻结", { freeze: true }],
  ["停止所有付款", { freeze: true }],
  ["所有付款都不行", { freeze: true }],
  ["什么都不能付", { freeze: true }],
  ["每笔最多5000，超过1000需要守护者共同签名，周五之前不能付款", { cap: 5000, co: [1000, G], from: day(2026, 11, 13) }],
  ["只能付给Mia，每笔最多300；2027年1月1日之前不能付款", { cap: 300, from: day(2027, 1, 1), only: [MIA] }],
  ["每笔最多500。只能付给Mia。", { cap: 500, only: [MIA] }],
  ["只能付给Mia，其他人都不能付款", { only: [MIA] }],
  ["請凍結錢包", { freeze: true }],
  ["每筆最多500", { cap: 500 }],
  ["只能付給Mia", { only: [MIA] }],
  ["超過1000需要守護者共同簽名", { co: [1000, G] }],
  ["５００以内", { cap: 500 }],
  ["每笔最多五千", { cap: 5000 }],
  ["每笔最多1万5千", { cap: 15000 }],
  ["两千以上需要Mia签名", { co: [2000, MIA] }],
  ["三天后才能付款", { from: day(2026, 11, 15) }],
  ["周日之前不能付款", { from: day(2026, 11, 15) }],
  ["月底之前不能付款", { from: day(2026, 12, 1) }],
  ["2027年底之前不能付款", { from: day(2028, 1, 1) }],
  ["到2028年为止锁定", { from: day(2028, 1, 1) }],
  ["我只想付给Mia", { only: [MIA] }],
  ["不能给陌生人转账", { only: [MIA, LEE, XM] }],
  ["任何付款都不能超过1000", { cap: 1000 }],
  ["单笔限额2000", { cap: 2000 }],
  ["限额500", { cap: 500 }],
  ["付款不得超过300", { cap: 300 }],
  ["明年之前不能付款", { from: day(2027, 1, 1) }],
  ["本月底之前锁定钱包", { from: day(2026, 12, 1) }],
  ["把钱包冻结", { freeze: true }],
  ["暂停所有转账", { freeze: true }],
  ["大于1000需要小明批准", { co: [1000, XM] }],
  ["金额超过5000时需要守护者确认", { co: [5000, G] }],
  ["只有Mia可以收款", { only: [MIA] }],
];
const ZH_NO = [["每天最多500", "period"], ["每周不超过1000", "period"], ["一天最多500", "period"], ["只在工作日付款", "clock"], ["余额至少保留1000", "balance"], ["不要付给Mia", "blocklist"], ["禁止付款给Mia", "blocklist"], ["只能付给Bob", "only-who"], ["只能付给老王", "only-who"], ["之前不能付款", "day"], ["每笔最多1.5", "whole"], ["12月1日以后不能付款", "end"], ["12月1日之前可以付款", "end"], ["90天后不能付款", "end"], ["不要冻结", "allow"], ["你好世界", "unknown"], ["超过1000需要我哥哥签名", "co-who"], ["超过1000的付款", "above-what"], ["周末不能付款", "clock"], ["晚上不能付款", "clock"]];
const JA = [
  ["1回あたり最大500", { cap: 500 }],
  ["1回の支払いは500まで", { cap: 500 }],
  ["最大500", { cap: 500 }],
  ["送金は1回5000まで", { cap: 5000 }],
  ["上限は1万", { cap: 10000 }],
  ["500以下", { cap: 500 }],
  ["50未満", { cap: 49 }],
  ["300を超える支払いはできない", { cap: 300 }],
  ["2000を超える送金は禁止", { cap: 2000 }],
  ["Miaにだけ送金", { only: [MIA] }],
  ["Miaだけ", { only: [MIA] }],
  ["Mia Leeにのみ送金する", { only: [LEE] }],
  ["小明にしか送らない", { only: [XM] }],
  ["MiaとMia Leeにだけ送金", { only: [LEE, MIA] }],
  ["Mia、小明にだけ送金", { only: [MIA, XM] }],
  ["アドレス帳の人だけ", { only: [MIA, LEE, XM] }],
  ["知らない人には送らない", { only: [MIA, LEE, XM] }],
  ["Mia以外には送らない", { only: [MIA] }],
  ["Mia以外、送金しない", { only: [MIA] }],
  ["12月1日まで送金しない", { from: day(2026, 12, 1) }],
  ["2026年12月24日までロック", { from: day(2026, 12, 24) }],
  ["金曜日まで送金できない", { from: day(2026, 11, 13) }],
  ["明日まで何も送らない", { from: day(2026, 11, 13) }],
  ["2028年までロック", { from: day(2028, 1, 1) }],
  ["12月1日以降のみ送金できる", { from: day(2026, 12, 1) }],
  ["12月1日から送金できる", { from: day(2026, 12, 1) }],
  ["90日間ロック", { from: day(2027, 2, 10) }],
  ["来月まで送金しない", { from: day(2026, 12, 1) }],
  ["1000を超える支払いはガーディアンの共同署名が必要", { co: [1000, G] }],
  ["1000を超える場合、ガーディアンの署名が必要", { co: [1000, G] }],
  ["1000以上はMiaの署名が必要", { co: [1000, MIA] }],
  ["1000を超えたら二人目の署名が必要", { co: [1000, G] }],
  ["1000を超える支払いは、小明の承認が必要", { co: [1000, XM] }],
  ["ウォレットを凍結", { freeze: true }],
  ["凍結する", { freeze: true }],
  ["すべての支払いを止める", { freeze: true }],
  ["何も送らない", { freeze: true }],
  ["1回あたり最大5000、1000を超える支払いはガーディアンの共同署名が必要、金曜日まで送金しない", { cap: 5000, co: [1000, G], from: day(2026, 11, 13) }],
  ["Miaにだけ送金、1回あたり最大300。2027年1月1日まで送金しない", { cap: 300, from: day(2027, 1, 1), only: [MIA] }],
  ["金曜日まで送金しない、Miaにだけ送金", { from: day(2026, 11, 13), only: [MIA] }],
  ["3日後まで送金しない", { from: day(2026, 11, 15) }],
  ["1週間ロック", { from: day(2026, 11, 19) }],
  ["3か月間ロック", { from: day(2027, 2, 12) }],
  ["来年まで送金しない", { from: day(2027, 1, 1) }],
  ["Miaにのみ支払う", { only: [MIA] }],
  ["Mia以外への送金は禁止", { only: [MIA] }],
  ["支払いは最大1000", { cap: 1000 }],
  ["送金上限は2000", { cap: 2000 }],
  ["1回の送金は300以下", { cap: 300 }],
  ["来年までロックする", { from: day(2027, 1, 1) }],
  ["月末まで送金しない", { from: day(2026, 12, 1) }],
  ["ウォレットをロックする", { freeze: true }],
  ["全部止める", { freeze: true }],
  ["送金を全て停止", { freeze: true }],
  ["5000以上は小明の承認が必要", { co: [5000, XM] }],
  ["1000を超える送金にはガーディアンの確認が必要", { co: [1000, G] }],
];
const JA_NO = [["1日あたり500まで", "period"], ["毎週1000まで", "period"], ["平日だけ", "clock"], ["残高を1000残す", "balance"], ["Miaには送らない", "blocklist"], ["Bobにだけ送金", "only-who"], ["田中さんにだけ送金", "only-who"], ["1回あたり最大1.5", "whole"], ["12月1日以降は送金しない", "end"], ["12月1日まで送金できる", "end"], ["90日後は送金しない", "end"], ["凍結しない", "allow"], ["こんにちは世界", "unknown"], ["1000を超える支払いは兄の署名が必要", "co-who"], ["1000を超える支払い", "above-what"], ["週末は送金しない", "clock"], ["夜間は送金できない", "clock"]];
const TONGUES = [["German", "de", DE, DE_NO], ["Chinese", "zh", ZH, ZH_NO], ["Japanese", "ja", JA, JA_NO]];
for (const [, , yes, no] of TONGUES) {
  for (const [text, want] of yes) { reads(text, want, ctxL); check(RW.parse(text, ctxL).items.every(i => !i.unused), `“${text}”: words reported as not used: ${RW.parse(text, ctxL).items.map(i => i.unused).filter(Boolean).join(" ")}`); }
  for (const [text, code] of no) refuses(text, code, ctxL);
}
/* a rule from another language is the same text as the English one: the same reader wrote it */
const FULL = "At most 5,000 per payment, above 1,000 the Guardian co-signs, nothing before Friday";
for (const a of ["Höchstens 5.000 pro Zahlung, über 1.000 zeichnet der Guardian mit, nichts vor Freitag", "每笔最多5000，超过1000需要守护者共同签名，周五之前不能付款", "1回あたり最大5000、1000を超える支払いはガーディアンの共同署名が必要、金曜日まで送金しない"])
  check(RW.parse(a, ctxL).text && RW.parse(a, ctxL).text === RW.parse(FULL, ctxL).text, `“${a}” does not give the same rule text as “${FULL}”`);
/* each part keeps the words it was written in; a word that was not used is shown as it was written, not as it was read */
const srcs = (text, want) => check(JSON.stringify(RW.parse(text, ctxL).items.map(i => i.src)) === JSON.stringify(want), `“${text}”: parts ${JSON.stringify(RW.parse(text, ctxL).items.map(i => i.src))}, wanted ${JSON.stringify(want)}`);
srcs("Höchstens 500 pro Zahlung, nur an Mia und nichts vor dem 1. Dezember.", ["Höchstens 500 pro Zahlung", "nur an Mia", "nichts vor dem 1. Dezember"]);
srcs("每笔最多500，周五之前不能付款。只能付给小明和Mia。", ["每笔最多500", "周五之前不能付款", "只能付给小明和Mia"]);
srcs("1回あたり最大500、金曜日まで送金しない。Miaにだけ送金", ["1回あたり最大500", "金曜日まで送金しない", "Miaにだけ送金"]);
const UNUSED_L = [["Höchstens 500 bis Freitag", "“Freitag”"], ["Höchstens 100 an Mia", "“Mia”"], ["Nur an Mia und Bob", "“Bob”"], ["最多100给Mia", "“Mia”"], ["Miaに最大100", "“Mia”"]];
for (const [text, want] of UNUSED_L) { const p = RW.parse(text, ctxL); check(p.rule && p.items[0].unused === want, `“${text}”: wanted ${want} reported as not used, got ${p.items[0].unused}`); }
check(/Bruder/.test(RW.parse("Über 1000 muss mein Bruder unterschreiben", ctxL).items[0].why), "an unknown co-signer in German is not named in the answer as he was written");
check(/老王/.test(RW.parse("只能付给老王", ctxL).items[0].why), "an unknown name in Chinese is not named in the answer as it was written");
/* an English sentence stays with the English reader, also when it holds a word German has too */
for (const text of ["only to Nie", "only to Den", "at most 500 an hour", "max 500", "above 1000 Mia must co-sign", ...WORDS.map(x => x[0])]) check(RW.langOf(text.replace(/Mia Lee|Mia/g, " ").replace(/[0-9a-f]{96}/g, " ")) === null, `“${text}” is taken for another language`);
check(RW.langOf("bis 500") === "de" && RW.langOf("每笔最多500") === "zh" && RW.langOf("1回あたり最大500") === "ja", "a sentence is not taken for its language");

/* ---- 2 to 4. the rules it writes, read by the exact reader ---- */
let kinds = 0, tests = 0;
const caseOf = cell => {
  const v = cell.v, signed = [];
  for (let k = 0; k < 8; k++) { const x = v["i" + (18 + k)]; signed.push(x != null && BigInt(x) !== 0n ? hex96(x) : ""); }
  return { amount: Number(v.i1 ?? 1), to: v.i4 != null ? hex96(v.i4) : "5e".repeat(48), ts: v.i5 != null ? Number(v.i5) : 0, signed, d: RF.OUTCOME[cell.d] };
};
const inputs = p => ({ i1: String(p.amount), i4: "#x" + p.to, i5: String(p.ts), i18: p.signed[0] ? "#x" + p.signed[0] : "0" });
for (const [text] of WORDS) {
  const p = RW.parse(text, ctx), r = RF.read(p.text);
  check(r.ok && !r.has.open && !r.has.none, `“${text}”: the exact reader finds a payment without exactly one answer`);
  if (!r.ok) continue;
  const cases = r.cells.map(caseOf);
  kinds += cases.length;
  for (const c of cases) check((RW.judge(p.rule, c).length ? "block" : "pass") === c.d, `“${text}”: plain reading and exact reader differ for ${JSON.stringify(c)}`);
  for (const t of RW.tests(p.rule, { now: NOW })) {
    tests++;
    const a = RF.answer(p.text, inputs(t));
    check(a.outcome === (t.stop.length ? "block" : "pass"), `“${text}”: test “${t.says}” predicted ${t.stop.length ? "block" : "pass"}, the reader says ${a.outcome}`);
  }
  const back = RW.fromTau(p.text);
  check(back && RW.build(back) === p.text, `“${text}”: the rule read back from its Tau text does not give the same text`);
  check(RW.idle(p.rule, cases).length === 0, `“${text}”: a part is reported as never deciding: ${RW.idle(p.rule, cases)}`);
}
{ /* a limit of 500 stops everything a co-signature above 1,000 would stop: that part never decides */
  const p = RW.parse("max 500 per payment, co-sign above 1,000", ctx), cases = RF.read(p.text).cells.map(caseOf);
  check(JSON.stringify(RW.idle(p.rule, cases)) === '["co"]', "the co-signature above the limit is not found as a part that never decides");
}
check(RW.fromTau("always ( (i1[t]:bv[24] > { 5000 }:bv[24]) -> (o5[t]:bv[24] = { #x000000 }:bv[24]) ).") === null, "a hand-written rule is taken for one of the wallet's");

const lines = [`## Rule words: ${checked} checks`, "",
  `- ${WORDS.length} sentences that give a rule, ${NO.length} that say why they cannot, ${UNUSED.length} that say which words they did not use`,
  ...TONGUES.map(([name, , yes, no]) => `- ${name}: ${yes.length} sentences that give a rule, ${no.length} that say why they cannot`),
  `- ${kinds} kinds of payment where the plain reading must match the exact reader, ${tests} test payments`, ""];
if (fails.length) lines.push(`### ❌ ${fails.length} failed`, "", ...fails.map(f => "- " + f));
else lines.push("Every answer matches. ✅");
console.log(lines.join("\n"));
process.exit(fails.length ? 1 : 0);
