/* Troll box: the HUD's public live chat (server side infra/relay/chat.py).
   A pill at the bottom right opens the room; only then a socket to the relay opens, and it closes with the panel.
   The name is the simulation's random animal name (TauSim.me), written to this browser only when the visitor sends a
   message. The relay keeps a message 24 hours with that name and the text, never an address; links (except to tauhud.com and agorzilla.com), price talk and
   slurs are refused there, links to our own sites are clickable, three reports hide a message. Include with <link rel="stylesheet" href="assets/chat.css"> and
   <script src="assets/chat.js" defer></script>; window.TAU_CHAT_RELAY overrides the relay (a host, or a ws:// address for tests).
   A page with a visible <div id="tbHost"> (the HUD on wide screens) gets the room as a panel inside it instead of the pill:
   always open, connected while the tab is visible. When the host is hidden (a smaller screen) it is the pill again.
   A host with data-pill="no" (White Rabbit Key) keeps the room inside it and never shows the pill: hidden host, no socket.
   A host's data-room picks the room's name for that page from ROOMS below; it is the same room everywhere.
   When this browser's test wallet (tauhud.com/wallet/) walks on White Rabbit Key as an islander, a message sent here is
   also said by that islander: the page signs "tauhud.com walker <wallet> <day>" with the wallet's key once a day (as for
   walking it, relay steer.py) and the island shows the message over its head now and then (rabbit/walkers.js). */
(() => {
  "use strict";
  const RELAY = window.TAU_CHAT_RELAY || "node.tauhud.com", SOCKET = /^wss?:\/\//.test(RELAY) ? RELAY : `wss://${RELAY}`;
  const L = window.TauI18n ? TauI18n.lang : "en";
  const DICT = {
    zh: {
      "Chat with everyone on Tau HUD": "和 Tau HUD 上的所有人聊天", "Close": "关闭",
      "Be kind. No prices or trading; links only to tauhud.com or agorzilla.com. Messages vanish after 24 hours; three reports hide one.": "友善一点。不谈价格和交易；只能发 tauhud.com 或 agorzilla.com 的链接。消息 24 小时后消失；三次举报即隐藏。",
      "Say something…": "说点什么…", "Send": "发送", "Report": "举报", "Reported": "已举报",
      "You are {x} until 00:00 UTC": "今天你是 {x}，00:00 UTC 换新名字", "connecting…": "连接中…", "No messages in the last 24 hours. Say hello.": "过去 24 小时没有消息。打个招呼吧。",
      "The chat can’t reach the relay right now.": "聊天暂时连不上中继。", "The chat is closed right now.": "聊天暂时关闭。",
      "No links or handles here.": "这里不能发链接或账号。", "Only links to tauhud.com or agorzilla.com here; no handles.": "这里只能发 tauhud.com 或 agorzilla.com 的链接，不能发账号。", "No price, trading or giveaway talk: testnet AGRS has no value.": "不谈价格、交易或赠送：测试网 AGRS 没有价值。",
      "That word is not welcome here.": "这里不欢迎这个词。", "At most 200 characters.": "最多 200 个字符。", "Nothing to send.": "没有可发送的内容。",
      "One message every few seconds, please.": "请每隔几秒发一条。", "That is a lot for one hour; take a break.": "这一小时说得够多了，休息一下吧。",
      "You just said that.": "你刚说过这句。", "The room is busy; try again in a minute.": "聊天室太忙，请一分钟后再试。",
      "You are muted for today.": "你今天已被禁言。", "That did not look like a message.": "这看起来不像一条消息。",
      "Not sent.": "未发送。",
      "No price or trading talk: testnet AGRS has no value.": "不谈价格或交易：测试网 AGRS 没有价值。",
      "No wallet addresses or keys here.": "这里不能发钱包地址或密钥。",
      "That looks like a scam, so it is not posted.": "这看起来像诈骗，所以没有发出。",
      "No sexual content here.": "这里不能发色情内容。",
      "No insults or threats here.": "这里不能辱骂或威胁。",
      "Please don't shout in capitals.": "请不要全用大写字母喊。",
      "That looks like spam.": "这看起来像刷屏。",
      "That was just said.": "这句刚刚有人说过。",
      "You are muted for {n} more minutes.": "你还要禁言 {n} 分钟。",
      "You are out of the chat until 00:00 UTC.": "你被移出聊天，直到 UTC 00:00。",
      "This is a warning; the next strike mutes you for 10 minutes.": "这是一次警告；再犯一次将禁言 10 分钟。",
      "You are muted for {n} minutes.": "你被禁言 {n} 分钟。",
      "The same room as the Tau HUD troll box": "与 Tau HUD 闲聊箱是同一个聊天室",
      "Your islander on White Rabbit Key says it too, over its head.": "你在白兔岛上的岛民也会把它说出来，显示在头顶。",
    },
    ja: {
      "Chat with everyone on Tau HUD": "Tau HUD のみんなとチャット", "Close": "閉じる",
      "Be kind. No prices or trading; links only to tauhud.com or agorzilla.com. Messages vanish after 24 hours; three reports hide one.": "やさしく。価格・取引の話はなし。リンクは tauhud.com と agorzilla.com だけ。メッセージは 24 時間で消え、3 件の報告で非表示になります。",
      "Say something…": "なにか書く…", "Send": "送信", "Report": "報告", "Reported": "報告済み",
      "You are {x} until 00:00 UTC": "今日のあなたは {x}（00:00 UTC に新しい名前）", "connecting…": "接続中…", "No messages in the last 24 hours. Say hello.": "この 24 時間のメッセージはありません。あいさつをどうぞ。",
      "The chat can’t reach the relay right now.": "チャットは今リレーに接続できません。", "The chat is closed right now.": "チャットは今閉まっています。",
      "No links or handles here.": "リンクやアカウント名は書けません。", "Only links to tauhud.com or agorzilla.com here; no handles.": "リンクは tauhud.com と agorzilla.com だけ、アカウント名は書けません。", "No price, trading or giveaway talk: testnet AGRS has no value.": "価格・取引・配布の話はなし：テストネットの AGRS に価値はありません。",
      "That word is not welcome here.": "その言葉はここでは歓迎されません。", "At most 200 characters.": "200 文字まで。", "Nothing to send.": "送る内容がありません。",
      "One message every few seconds, please.": "数秒に 1 件でお願いします。", "That is a lot for one hour; take a break.": "この 1 時間はたくさん書きました。少し休みましょう。",
      "You just said that.": "それはさっき書きました。", "The room is busy; try again in a minute.": "混み合っています。1 分後にもう一度。",
      "You are muted for today.": "今日はミュートされています。", "That did not look like a message.": "メッセージとして読めませんでした。",
      "Not sent.": "送信されませんでした。",
      "No price or trading talk: testnet AGRS has no value.": "価格や取引の話はなし：テストネットの AGRS に価値はありません。",
      "No wallet addresses or keys here.": "ウォレットのアドレスや鍵は書けません。",
      "That looks like a scam, so it is not posted.": "詐欺のように見えるため投稿されません。",
      "No sexual content here.": "性的な内容は書けません。",
      "No insults or threats here.": "侮辱や脅しは書けません。",
      "Please don't shout in capitals.": "大文字で叫ばないでください。",
      "That looks like spam.": "スパムのように見えます。",
      "That was just said.": "それはさっき書かれました。",
      "You are muted for {n} more minutes.": "あと {n} 分ミュートされています。",
      "You are out of the chat until 00:00 UTC.": "UTC 00:00 までチャットから外されています。",
      "This is a warning; the next strike mutes you for 10 minutes.": "これは警告です。次の違反で 10 分間ミュートされます。",
      "You are muted for {n} minutes.": "{n} 分間ミュートされました。",
      "The same room as the Tau HUD troll box": "Tau HUD のトロールボックスと同じ部屋です",
      "Your islander on White Rabbit Key says it too, over its head.": "ホワイトラビット島のあなたの島民も、頭の上でそれを言います。",
    },
  };
  /* the room's name, one place per language; a page's host may call the same room by its own name (data-room) */
  const ROOMS = {
    hud: { en: "Troll box", zh: "闲聊箱", ja: "トロールボックス" },
    isle: { en: "The Coconut Wire", zh: "椰林传声", ja: "ヤシの木通信" },   // White Rabbit Key: the island's gossip line
  };
  const HOST = () => document.getElementById("tbHost");
  const ROOM = (() => { const h = HOST(), r = ROOMS[(h && h.dataset.room) || "hud"] || ROOMS.hud; return r[L] || r.en; })();
  const D = DICT[L] || {};
  const t = (s, x) => (D[s] || s).replace("{x}", x == null ? "" : x);
  /* a relay answer is one or two fixed sentences, a number in them as {n} */
  const tr = msg => String(msg).split(/(?<=\.) /).map(p => { const n = (p.match(/\d+/) || [""])[0], k = p.replace(/\d+/, "{n}"); return D[p] || (n && D[k] ? D[k].replace("{n}", n) : p); }).join(L === "en" ? " " : "");

  /* the visitor's name: the simulation's identity when the page has it, else one made here the same way */
  const ME = (() => {
    if (window.TauSim && TauSim.me) return keep => TauSim.me(keep);
    let m = null;
    return () => {
      if (!m) { const u = new Uint32Array(7); crypto.getRandomValues(u); m = { token: [...u].slice(0, 4).map(x => x.toString(16).padStart(8, "0")).join(""), a: u[4] % 24, b: u[5] % 24, c: u[6] % 8 }; }
      return { ...m, name: "A visitor", colour: "#c8c8d0" };
    };
  })();
  /* a new name every day at 00:00 UTC: worked out here from the browser's random token and the date, never stored;
     reports, strikes and bans do not follow the name, so a new one clears nothing */
  const DAY = () => Math.floor(Date.now() / 864e5);
  const pick = (token, day) => {
    let h = 2166136261;
    for (const ch of `${token}:${day}`) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 0x85ebca6b) >>> 0; h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0; h = (h ^ (h >>> 16)) >>> 0;
    return { a: h % 24, b: Math.floor(h / 24) % 24, c: Math.floor(h / 576) % 8 };
  };
  const today = m => {
    const d = DAY(), n = pick(m.token, d), y = pick(m.token, d - 1);
    if (n.a === y.a && n.b === y.b) n.b = (n.b + 1) % 24;   // never yesterday's name again
    return { ...m, ...n };
  };
  const COLOURS = ["#8fa3d9", "#b39ddb", "#d9a3c4", "#d9c49a", "#8fc7d9", "#a7a0d9", "#c4a3d9", "#c8c8d0"];
  const nameOf = m => (window.TauSim && TauSim.nameOf ? TauSim.nameOf(m.a, m.b) : m.name);

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const pill = el("button", "tb-pill");
  pill.type = "button"; pill.setAttribute("aria-expanded", "false"); pill.title = t("Chat with everyone on Tau HUD");
  pill.append(el("span", "tb-dot"), el("span", "tb-pl", ROOM));
  const box = el("section", "tb-box"); box.hidden = true; box.setAttribute("aria-label", ROOM);
  const head = el("div", "tb-head"); head.append(el("span", "tb-tl", ROOM));
  if (ROOM !== (ROOMS.hud[L] || ROOMS.hud.en)) head.title = t("The same room as the Tau HUD troll box");
  const x = el("button", "tb-x", "×"); x.type = "button"; x.title = x.ariaLabel = t("Close"); head.append(x);
  const rules = el("p", "tb-rules", t("Be kind. No prices or trading; links only to tauhud.com or agorzilla.com. Messages vanish after 24 hours; three reports hide one."));
  const list = el("ol", "tb-list"); list.setAttribute("translate", "no"); list.setAttribute("aria-live", "polite");
  const note = el("p", "tb-note", t("connecting…"));
  const form = el("form", "tb-form");
  const input = el("input", "tb-in"); input.maxLength = 200; input.placeholder = t("Say something…"); input.autocomplete = "off"; input.setAttribute("enterkeyhint", "send");
  const send = el("button", "tb-send", t("Send")); send.type = "submit";
  form.append(input, send);
  const who = el("p", "tb-who");
  box.append(head, rules, list, note, form, who);

  let ws = null, wait = 3000, retry = null, seen = new Set(), reported = new Set();
  const stamp = s => { const d = new Date(s * 1000); return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0"); };
  const setNote = s => { note.textContent = s || ""; note.hidden = !s; };
  const atBottom = () => list.scrollHeight - list.scrollTop - list.clientHeight < 40;
  /* the message text, with links to our own sites clickable (the relay refuses every other link; OWN in chat.py).
     Built from text nodes, never innerHTML; a trailing full stop or bracket stays text. */
  const OWN = /(^|[^\w.@/-])((?:https?:\/\/)?(?:[a-z0-9-]+\.)*(?:tauhud|agorzilla)\.com(?![\w@:-]|\.[\w-])(?:[/?#][^\s<>"'@]*)?)/gi;
  function linked(text) {
    const span = el("span", "tb-tx");
    let at = 0, m;
    OWN.lastIndex = 0;
    while ((m = OWN.exec(text))) {
      let url = m[2];
      const tail = (url.match(/[.,;:!?)\]]+$/) || [""])[0];
      url = url.slice(0, url.length - tail.length);
      const start = m.index + m[1].length;
      span.append(text.slice(at, start));
      const a = el("a", "tb-ln", url);
      a.href = /^https?:/i.test(url) ? url.replace(/^http:/i, "https:") : "https://" + url;
      a.target = "_blank"; a.rel = "noopener nofollow ugc";
      span.append(a);
      at = start + url.length;
      OWN.lastIndex = at;
    }
    span.append(text.slice(at));
    return span;
  }
  function add(m) {
    if (seen.has(m.id)) return;
    seen.add(m.id);
    const li = el("li", "tb-m"); li.dataset.id = m.id; li.title = stamp(m.ts);
    const nm = el("b", "tb-nm", nameOf(m)); nm.style.color = COLOURS[m.c] || COLOURS[7];
    const rp = el("button", "tb-rp", "⚑"); rp.type = "button"; rp.title = rp.ariaLabel = t("Report");
    rp.onclick = () => { if (!ws || ws.readyState !== 1 || reported.has(m.id)) return; reported.add(m.id); ws.send(`chat report ${m.id} ${ME(false).token}`); li.classList.add("gone"); rp.title = t("Reported"); };
    li.append(el("time", "tb-t", stamp(m.ts)), nm, linked(m.text), rp);
    const stick = atBottom();
    list.append(li);
    while (list.children.length > 120) list.firstChild.remove();
    if (stick) list.scrollTop = list.scrollHeight;
  }
  /* your islander on White Rabbit Key says it too: only when this browser's wallet walks on the island right now */
  const ISL = { list: null, at: 0, sig: null, bls: null };
  const myWallet = () => { try { const k = JSON.parse(localStorage.getItem("tauhud-wallet-key") || "null"); return k && /^[0-9a-f]{64}$/.test(k.sk || "") && /^[0-9a-f]{96}$/.test(k.pk || "") ? k : null; } catch (e) { return null; } };
  async function onIsland(pk) {
    const IW = window.ISLE_WALKERS;
    if (IW && IW.at && IW.at(pk)) return true;   // on the island page: it walks there now
    if (/^wss?:\/\//.test(RELAY)) return false;
    if (!ISL.list || Date.now() - ISL.at > 120000) {
      try { const r = await fetch(`https://${RELAY}/walkers`, { cache: "no-store" }); const j = r.ok ? await r.json() : null; ISL.list = new Set(((j && j.walkers) || []).map(w => w && w.a)); ISL.at = Date.now(); } catch (e) { return false; }
    }
    return ISL.list.has(pk);
  }
  const bls = () => window.TauBLS ? Promise.resolve(window.TauBLS) : (ISL.bls = ISL.bls || new Promise(res => {
    const sc = document.createElement("script"); sc.src = "/wallet/vendor/tau-bls.min.js"; sc.onload = () => res(window.TauBLS || null); sc.onerror = () => { ISL.bls = null; res(null); }; document.head.append(sc);
  }));
  async function islander(mid, w) {
    try {
      const k = myWallet(); if (!k || !(await onIsland(k.pk))) return;
      const day = new Date().toISOString().slice(0, 10);
      if (!ISL.sig || ISL.sig.day !== day || ISL.sig.pk !== k.pk) {
        const B = await bls(); if (!B) return;
        ISL.sig = { day, pk: k.pk, sig: B.bytesToHex(B.sign(new TextEncoder().encode(`tauhud.com walker ${k.pk} ${day}`), B.hexToBytes(k.sk))) };
      }
      if (w && w.readyState === 1) w.send(`chat islander ${Number(mid)} ${k.pk} ${day} ${ISL.sig.sig}`);
    } catch (e) {}
  }
  function hide(id) { const li = list.querySelector(`[data-id="${Number(id)}"]`); if (li) li.remove(); }
  function showWho() { const m = today(ME(false)); who.textContent = t("You are {x} until 00:00 UTC", nameOf(m)); who.style.setProperty("--me", COLOURS[m.c] || COLOURS[7]); }
  setInterval(() => { if (who.isConnected) showWho(); }, 60000);   // the new name shows up just after midnight UTC

  function connect() {
    if (ws) return;
    setNote(t("connecting…"));
    try { ws = new WebSocket(SOCKET); } catch (e) { ws = null; setNote(t("The chat can’t reach the relay right now.")); return; }
    const me = ws;
    me.onopen = () => { wait = 3000; me.send("hello version=1"); me.send("chat join"); };
    me.onmessage = ev => {
      let m; try { m = JSON.parse(String(ev.data)); } catch (e) { return; }
      if (!m || m.command !== "chat") return;
      if (m.status !== "ok") { setNote(tr((m.error && m.error.message) || "Not sent.")); send.disabled = false; return; }
      const d = m.data || {};
      if (d.messages) {
        list.textContent = ""; seen = new Set();
        d.messages.forEach(add); list.scrollTop = list.scrollHeight;
        setNote(d.enabled === false ? t("The chat is closed right now.") : d.messages.length ? "" : t("No messages in the last 24 hours. Say hello."));
        form.hidden = d.enabled === false;
      }
      (d.new || []).forEach(add);
      if (d.new && d.new.length) setNote("");
      if (d.sent) { add(d.sent); input.value = ""; send.disabled = false; setNote(""); list.scrollTop = list.scrollHeight; islander(d.sent.id, me); }
      if (d.islander) setNote(t("Your islander on White Rabbit Key says it too, over its head."));
      (d.hide || []).forEach(hide);
    };
    me.onclose = me.onerror = () => {
      if (me._dead) return; me._dead = true;
      if (ws === me) ws = null;
      send.disabled = false;
      if (!box.hidden) { setNote(t("The chat can’t reach the relay right now.")); retry = setTimeout(connect, wait); wait = Math.min(60000, wait * 2); }
    };
  }
  function disconnect() { clearTimeout(retry); if (ws) { const w = ws; ws = null; w._dead = true; try { w.send("chat leave"); w.close(); } catch (e) {} } }

  let inline = false;
  function open(on) {
    if (inline) return;
    box.hidden = !on; pill.hidden = on; pill.setAttribute("aria-expanded", String(on));
    document.documentElement.classList.toggle("tb-open", on);
    if (on) { showWho(); connect(); setTimeout(() => input.focus({ preventScroll: true }), 0); } else disconnect();
  }
  pill.onclick = () => open(true);
  x.onclick = () => { open(false); pill.focus(); };
  box.addEventListener("keydown", e => { if (e.key === "Escape" && !inline) { open(false); pill.focus(); } });
  form.onsubmit = e => {
    e.preventDefault();
    const text = input.value.replace(/\s+/g, " ").trim();
    if (!text || !ws || ws.readyState !== 1) return;
    const m = today(ME(true));   // the token is kept in this browser from the first message on, the name is today's
    showWho();
    send.disabled = true;
    ws.send(`chat say ${m.token} ${m.a} ${m.b} ${m.c} ${encodeURIComponent(text)}`);
    setTimeout(() => { send.disabled = false; }, 4000);
  };
  document.addEventListener("visibilitychange", () => { if (document.hidden) { if (inline) disconnect(); } else if (!box.hidden && !ws && (!ONLY || HOST().offsetWidth > 0)) connect(); });

  /* the panel form: inside #tbHost while that is shown, back to the pill when it is not */
  const ONLY = (() => { const h = HOST(); return !!(h && h.dataset.pill === "no"); })();
  function place() {
    const h = HOST(), show = !!(h && h.offsetWidth > 0);
    if (ONLY) {   // inside the host for good: connected while it is shown and the tab is visible
      if (!inline) { inline = true; h.append(box); box.classList.add("tb-inline"); box.hidden = false; pill.hidden = true; x.hidden = true; }
      if (show) { showWho(); if (!document.hidden) connect(); } else disconnect();
      return;
    }
    if (show && !inline) {
      const wasOpen = !box.hidden; if (wasOpen) open(false);
      inline = true; h.append(box); box.classList.add("tb-inline"); box.hidden = false; pill.hidden = true; x.hidden = true;
      showWho(); if (!document.hidden) connect();
    } else if (!show && inline) {
      inline = false; disconnect(); box.classList.remove("tb-inline"); x.hidden = false; document.body.append(box); box.hidden = true; pill.hidden = false;
    }
  }
  const mount = () => {
    if (!ONLY) document.body.append(pill, box);
    place(); addEventListener("resize", place);
    if (ONLY && window.ResizeObserver) new ResizeObserver(place).observe(HOST());   // shown or hidden by the page's own CSS
  };
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);
  window.TauChat = { open: () => open(true), close: () => open(false) };
})();
