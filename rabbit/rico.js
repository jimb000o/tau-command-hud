/* The islanders' voices. Every line anyone can say aloud is fixed and listed here: Rico's lines on the radio strip
   (RICO.L) and what each islander says when you walk in (RICO.CAST). The server speaks each one once with that
   islander's voice (infra/rico/make.py) and keeps the clips at node.tauhud.com/rico/<key>.mp3, listed in index.json;
   the key is the first 16 hex of sha1("<who>|<English text>"). Numbers and block heights are never spoken, only
   shown, so a fixed set covers everything. A line whose clip is missing is simply shown as text, as before.
   rabbit/voices.json is the list the server reads (node tests/voices.mjs --write makes it; the tests check it).
   window.RICO = { L, SETS, CAST, CALLS, all(), speak(parts, who), hud() }: a line is a list of parts { t: shown text, v: spoken English or null,
   who: whose voice, when not the speaker's }. */
(() => {
  "use strict";
  const BASE = "https://node.tauhud.com/rico/";
  const NAMES = ["Marisol", "Tobias", "Baako", "Hana"];   // the four candidates (game.js CANDS)
  const DAYS = 5;
  const L = {
    noLaws: "No laws yet on this island. Rico's only rule: the request line is open, the coconut stand is not.",
    topLaws: "{x} has written more laws than anyone. The island has asked for a nap.",
    pact: "Pact news: {x} and {y} shook hands at La Ola. Lola counted the fingers afterwards.",
    broken: "A pact was broken. Rico won't say who. The Book already did.",
    envelope: "An embassy envelope was seen near the council. Rico saw nothing. Rico is very expensive to see things.",
    rumours: "Rumours on air this week, and the Book keeps showing them up. Rico only plays them, folks.",
    quiet: "Quiet after ten is the law now. This is Rico, whispering.",
    reef: "The reef is protected. The fish have issued a statement: blub.",
    harbour: "A deep harbour for cruise ships. Tobias has already ordered a bigger hat.",
    night: "Night market every Friday! Rico will be there selling rumours at half price. Joke. The Book is watching.",
    concerts: "Beach concerts on Sundays are law. Rico has cancelled every other plan until the election.",
    copy: "There is a copy of the Book on the square now. More readers, fewer rumours. Bad for business, good for the island.",
    night5: "The lighthouse turns green, the candidates go quiet, and the Book keeps writing. Goodnight, island.",
    day: "Day {n} of {m}. If you still don't know who to vote for, neither do the gulls.",
    fact: "Fun fact: a law that contradicts one in force is refused before anyone votes. Rico tried 'Rico plays all night' and 'Quiet after ten'. Rico lost to Rico.",
    dedicate: "This next one goes out to whoever bought last night's rumour. You know who you are. So does the Book.",
    song: "Four candidates have asked for the same song tonight. It is called 'Vote for me'.",
    warm: "Weather: warm, with scattered promises and a front of envelopes moving in from the embassies.",
    sam: "Old Sam has read the Book every night this week. The Book has not read Sam once. Respect.",
    tips: "Rico accepts tips, song requests and alibis.",
    book: "Fresh from the Book!",
    /* the chain weather comes in bands; the numbers are shown beside it */
    wxChain: "Chain weather.",
    wxSim: "Simulation weather.",
    fog: "Thick fog. No new block for over ten minutes. Rico recommends patience and a lemonade.",
    calm: "Dead calm. The last blocks came in empty. A good day for fishing.",
    breeze: "A light breeze: a few transactions in the last blocks.",
    choppy: "Choppy seas, plenty of transactions rolling in. Hold on to your hats.",
    rule: "A wallet put a new rule on itself: a little local weather of its own.",
    showers: "Forecast: showers. Transactions are waiting for the next block.",
    clear: "Forecast: clear skies, unless somebody sends something.",
    fog2: "Fog over the chain. No new block in a while. Rico is lighting the lamp and making tea.",
    calm2: "Flat sea, empty blocks. The chain is ready, the island is asleep.",
    breeze2: "Gentle traffic on the chain: a few transactions bobbing along like fishing boats.",
    choppy2: "Busy waters! Transactions stacked up like crates on the pier.",
    showers2: "Some transactions are still waiting on the pier for the next block. Bring an umbrella.",
    clear2: "Nothing waiting on the pier. Every transaction has found its block.",
    /* the first line after the page opens */
    op1: "Radio Coco, ninety-seven point three, back on the air. Rico has had his coffee, the Book has had its ink.",
    op2: "You are listening to Radio Coco, the only station broadcasting from a testnet. If something breaks, that is the point.",
    op3: "Hello island! Fresh blocks, fresh rumours, same old Rico. Stay tuned.",
    op4: "Radio Coco, live from the studio by the harbour. Tonight: politics, gossip and the latest from the chain.",
    op5: "Good to have you, listener. Turn it up, the gulls can't hear.",
    /* between the news: the island and the testnet as Rico sees them */
    g1: "Reminder: on a testnet the money is pretend and the coconuts are real. Please don't mix them up at the market.",
    g2: "A caller asks how many people use the testnet. Rico can only count wallets. One person with three wallets is a party of one.",
    g3: "Nobody mines anything on this chain. No pickaxes, no noise. Blocks are sealed by agreement, the quiet island way.",
    g4: "A transaction walks into a block. The block says: you again? The transaction says: no, that was my ghost.",
    g5: "If your transaction is late, don't panic. Blocks come in like ferries: more or less on time, and never the same one twice.",
    g6: "Studio tip: write your own rules before somebody writes them for you. On this chain a wallet can put a rule on itself, and the chain holds it to it.",
    g7: "The Book in the lighthouse and the blocks on the testnet are cousins. Neither forgets, and neither forgives a typo.",
    g8: "Testnet means you can make mistakes for free. Rico has been testing his whole life.",
    g9: "Lost and found: one private key. Just kidding. Nobody can find that for you. Keep it the way your grandmother keeps her recipes.",
    g10: "Most requested song this week: Waiting for the Next Block. Runner-up: Fee Me Tender.",
    g11: "Rico asked the chain who will win the election. The chain said: I only write down what already happened. Smart chain.",
    g12: "A law on this island and a rule on Tau have one thing in common: if it contradicts the one in force, it doesn't get in. Not even with an envelope.",
    g13: "The gulls sit on the lighthouse all day. They don't vote, they don't sign, they just watch. Perfect observers. Terrible validators: no keys.",
    g14: "Message to the candidates: everything you do is written down. Message to the listeners: get popcorn.",
    g15: "Rico put a rule on himself: no more than three mangoes a day. The mangoes are lobbying hard.",
    g16: "Late-night question: if a block is sealed and nobody is watching, is it still final? Yes. Rico checked. Call in anyway.",
    g17: "Test coins are worth nothing, and that is the beauty of it. You can't lose your shirt here, only your patience.",
    g18: "No ads on Radio Coco. The embassies keep offering. Rico keeps the envelopes closed. Mostly.",
    g19: "Old Sam reminds you: the Book is free to read. It is the only free thing on this island. Enjoy it.",
    g20: "Wallets, not people: that is how the chain sees the world. Rico finds that very restful.",
    g21: "This is the hour when the validators sign and the islanders sleep. Rico does neither.",
    g22: "Every block that comes in is like a match result: final, posted, and somebody at the bar still argues about it.",
    g23: "Some people collect stamps. The testnet collects signatures. Rico collects excuses.",
    g24: "Breaking: the black cat crossed the square twice again. The Book has both crossings. The cat has no comment.",
    g25: "Kai from the Reef Proof dive centre says the reef is fine today. Kai checked. Twice. Underwater. That is what we call a proof.",
    g26: "Noor at the Coconut Works reports: every coconut counted, every count signed. Rico asked for one. Noor asked for a signature.",
    g27: "Kiko is building another canoe and says a good hull is like a good rule: no holes, no contradictions, and you test it before you trust it.",
    g28: "Captain Wren found something old on the seabed again, and says the sea keeps a better record than any of us. Old Sam says: almost.",
    g29: "Pim the surveyor measured the square for the embassies today. Rico asked what they are planning. Pim said: I only measure. Very diplomatic.",
    g30: "Elder Ama reminds the candidates: the island remembered things long before the Book did. Listen first, then promise.",
    /* news from the chain: what Rico just saw in the newest blocks (game.js readChain) */
    rule1: "News from the chain: a wallet just wrote itself a personal rule. Most people make New Year's resolutions. On this chain, they are enforced.",
    rule2: "A wallet tied its own hands today, on purpose. Rico tried that with chocolate once. The chain is stricter than Rico.",
    rule3: "New personal rule on the testnet. The wallet said: from now on, not like that. And the chain said: noted.",
    rule4: "Another personal rule on the chain. So far most of them came from just two wallets. Two people, or one person with a lot of coffee: the chain only sees wallets.",
    cosign1: "A co-signed transfer is on the water. The money waits on the pier until the co-signers say yes. Romance, testnet style.",
    cosign2: "Somebody sent money that needs a second signature. Trust, but sign twice.",
    cosvote: "A co-signer has spoken. Somewhere on the testnet a transfer is either sailing or staying home.",
    lock1: "Someone sent money on a string: until its release, at a block or a time, the sender can still pull it back. Rico calls that a boomerang with a timer.",
    lock2: "A retractable transfer went out. The receiver may look, but not touch. Not yet.",
    back1: "And the boomerang came back! A sender pulled a transfer back before its release. The receiver is now staring at the sea.",
    back2: "Pulled back! A transfer went home before it was released. On this island we call that changing your mind in public.",
    offer: "A rule offer is on the table. Nothing binds until the other side says yes. Like a marriage, with fewer cakes.",
    offerYes: "Rule offer accepted! Two wallets agreed on a rule. Lola says that is more than most couples manage.",
    law1: "The validators put a network rule change on the table. If it is like the last few dozen, it proves once again that a times b is b times a. Rico checked on his fingers. Still true.",
    law2: "Another network rule change out there. The ones Rico has read so far changed nothing at all: rehearsals, not revolutions.",
    lawSim: "On the simulated chain the validators have a new rule change on the table. Rico will tell you if the sea changes colour.",
    lawVote: "Validator votes are coming in. On this chain the rules change only when enough validators agree. On this island, when Lola runs out of lemonade.",
    refusedLaw: "Somebody proposed a network rule that contradicts the rules in force. Turned away at the door, before anyone voted. Just like the Book does with our laws.",
    refusedOwn: "A wallet just tried to break its own rule. The chain said no, the way a lighthouse says no to a rock.",
    refused: "The chain turned a transaction away at the door. The numbers didn't add up. No drama, no appeal, next please.",
    burst1: "A wave of transactions just hit the beach! Somebody out there is either testing very hard or very happy.",
    burst2: "Rush hour on the chain! Full blocks, a busy pier, and Rico is impressed.",
    ghost1: "Ghost report from the harbour: transactions already sealed in a block, but still listed as waiting. The node hasn't noticed they left. Old Sam calls them guests who never go home.",
    ghost2: "Spooky! The waiting list still shows transactions that are already in a block. Ghosts. Harmless, says the Book. Rico sleeps with the light on anyway.",
    ghost3: "The ghosts are back on the waiting list. A known bug, reported to the builders. Rico has put out a lemonade for them.",
    toStake: "Big news on the simulated chain: the validators are voting to switch consensus to proof of stake. Whoever holds the most would seal the blocks. Rico is counting his coconuts.",
    toFixed: "Simulation flash: a vote to go back to the fixed validator list. The stakers would hand back their seats and the old guard returns. Like after every island revolution, only with fewer hats.",
    nowStake: "It's done! The simulated chain now runs on proof of stake. No tanks, no coup, just votes and a block height. Rico is almost disappointed.",
    nowFixed: "It's done: the simulation is back on the fixed validator list. Not one cannon fired. Boring for radio, beautiful for a chain.",
    midnight: "The simulated chain starts over in a few minutes, back at block one. Finish your drinks.",
    restart: "The chain has started over at block one. Same sea, fresh logbook.",
    /* chain news told as a story: an opening sting before it, a word from the host after it */
    flash1: "Breaking news from the harbour!",
    flash2: "Hold the music. Something just happened on the chain.",
    flash3: "Rico interrupts this programme for a bulletin from the blocks.",
    flash4: "News flash! Rico has his reading glasses on. This is serious.",
    flash5: "The telegraph in the studio just rang. It never rings.",
    flash6: "Stop the dancing, folks. The chain has news.",
    tag1: "That's the chain, folks. Nobody asked it. It just happened.",
    tag2: "Rico never makes up the chain news. Only the rumours. Back to the music.",
    tag3: "Radio Coco: first with the news, always with the block number.",
    tag4: "Old Sam is already writing it down.",
    tag5: "And now, the weather. Just kidding. Back to the calypso.",
    tag6: "More on this as it happens. Which, on a chain, is every few seconds.",
    valIn: "A new validator has been admitted on the simulated chain. Welcome aboard. The others voted you in, so be nice and bring snacks.",
    valOut: "A validator has left the simulated chain. Voted out, or retired to a quieter island. The rest sign on, a little busier.",
    feeUp: "The base fee just went up on the simulated chain. The validators voted, the rules changed, and Rico's tip jar is jealous.",
    feeDown: "The base fee just went down on the simulated chain. Cheaper transactions for everyone. Rico has lowered his prices too, out of solidarity. Not really.",
    rev: "The rules of the simulated chain have a new revision in force. Not a riot, not a coup. A vote, a block height, and a number going up by one.",
    whale1: "A big transfer just went through! Somebody moved a pile of test coins in one go. Worthless, of course. But very impressively worthless.",
    whale2: "Whale sighting off the north beach! A huge transfer just crossed the chain. The gulls are following it, hoping for scraps.",
    /* jokes, now and then */
    j1: "Why did the transaction break up with the mempool? It needed some space. Preferably in a block.",
    j2: "How many validators does it take to change a light bulb? As many as the quorum says. And somebody has to propose the bulb first.",
    j3: "Rico's doctor told him to take it easy. Rico said: I can't, doc. There's no finality on this testnet. Nothing is ever really over.",
    j4: "Knock knock. Who's there? Reorg. Reorg who? Never mind, we've rewritten that part.",
    j5: "What do you call a wallet with a personal rule and no money? Principled.",
    j6: "A Tau rule walks into a bar. The bartender says: we don't serve contradictions here. The rule says: good, neither do I.",
    j7: "Why don't validators play poker on this island? Every hand is signed, and everybody can read the Book.",
    j8: "What did the retractable transfer say to the receiver? Don't get attached. I'm on a timer.",
    j9: "Rico's ex wanted a co-signer for every decision. Turns out that's a feature now.",
    j10: "Why was the empty block so relaxed? Nothing to carry, nothing to prove. Just a timestamp and a good attitude.",
    j11: "The base fee lives in a line called o nine. Rico asked it for a discount. It said: change the rules first. Very politely.",
    j12: "What's a validator's favourite dance? The quorum-ba.",
    j13: "Why won't the gull join the network? It doesn't want to deal with peers. It has enough of those on the pier.",
    j14: "How does a node say goodbye? See you at the next block. Probably. Give or take a reorg.",
    j15: "Rico once wrote a love letter in Tau logic. It was always true. She still said no. Logic isn't everything.",
    j16: "Testnet coins have no value. Rico checked. Neither do Rico's jokes. And yet, here we both are.",
    j17: "What do you call a transaction that waits forever? A regular at Bar La Ola.",
    j18: "Why did the ghost transaction come to the party? It was already sealed. It just wanted to be listed.",
    j19: "Rico's computer wanted to run a node. The manual said: on Windows, use Docker or WSL. The computer said: I don't speak whale.",
    j20: "Rico built the node image. The manual said the Tau engine compiles once, slowly. Rico has now aged once, slowly.",
    j21: "The validator set is like Rico's old band. You can only join if the others vote you in, and the drummer always says no.",
    j22: "A private key, a seed phrase and a password walk into a bar. Nobody remembers who invited them.",
    j23: "What's the difference between a rumour and a block? A block can be checked. Rico sells rumours.",
    j24: "Rico asked Old Sam for a loan. Sam said: fine, I'll write it in the Book. Rico said: never mind.",
    j25: "The black cat applied to become a validator. The council asked for its key. The cat knocked it off the table.",
    j26: "Rico wrote his New Year's resolution as a personal rule. Now the chain refuses his midnight mangoes. Worst idea ever. Best idea ever.",
    j27: "How do you comfort a refused transaction? Tell it: it's not you, it's the rules. And the rules were here first.",
    j28: "Rico left one banana on the studio windowsill last night. This morning, only the peel, folded neatly. Agorzilla has manners.",
    j29: "There is no mining on Tau. Rico's uncle came with a pickaxe anyway. Three days of digging on the beach. Two crabs and a sandal.",
    j30: "If a rule changes and all the validators agree, does it make a sound? Yes. A tiny revision number goes up by one.",
    j31: "What's a cryptographer's favourite fruit? The BLS-berry. Twelve, three, eighty-one varieties.",
    j32: "Our weatherman quit. He said forecasting the chain was too easy: it's either blocks, or fog.",
    j33: "Why did the block go to therapy? Everybody kept checking its header and nobody asked how it was doing.",
    j34: "Rico tried to bribe a Tau rule. It looked at the envelope, checked it against the rules in force, and refused it. Incorruptible. Also a bit rude.",
    j35: "What's the testnet's favourite song? Don't stop me now. Unless it's a contradiction. Then stop me.",
    j36: "Rico's horoscope for validators: Today you will sign something. Tomorrow too. The stars are very consistent. Like the rules.",
    /* the ghosts in Halloween week, and after it, when Rico wants his island un-haunted */
    hw1: "Happy Halloween from Radio Coco! And right on time, transactions already sealed in a block are still haunting the waiting list. Even the node is in costume.",
    hw2: "Ghosts on the waiting list tonight, folks. Sealed in a block, and still walking around. Perfect timing. Rico approves the decoration.",
    hw3: "Halloween special! The ghost transactions are out. Already in a block, still listed as waiting. Don't be scared, kids. They only say boo to block explorers.",
    hw4: "Spooky season on the testnet. The ghosts are listed, the pumpkins are carved, and Old Sam has written both into the Book.",
    po1: "Excuse me. Halloween is over. Why are there still ghosts on the waiting list? Sealed in a block and still listed. Somebody please tell them the party has ended.",
    po2: "Halloween is over and the island is still haunted. Ghost transactions all over the waiting list. Rico would like to speak to the manager of the mempool.",
    po3: "Dear builders, Halloween is over. The ghosts are still on the waiting list. The bug is reported, the island is patient, but Rico is running out of garlic.",
    po4: "Rico has put up a sign at the harbour: no ghosts after October. The ghost transactions cannot read. They are still listed as waiting.",
    po5: "Petition from the island: un-haunt the waiting list. Sealed transactions should rest in their blocks. Signed: Rico, Old Sam, and one very tired gull.",
    po6: "Still haunted. Rico called an exorcist. The exorcist said: that's not a ghost, that's a known bug, issue eighty-one. Send a developer, not a priest.",
    /* a caller on the line: Rico picks up */
    ring1: "Ring ring! You're on Radio Coco. Go ahead.",
    ring2: "We have a caller on the line. Go ahead, you're on the air.",
    ring3: "Line two is blinking. Hello, you're on Radio Coco.",
    /* the island legend: Agorzilla, glimpsed now and then in the jungle */
    agz1: "Sighting report from the jungle! Somebody saw Agorzilla behind the drums last night. The photo is very blurry. Rico thinks it's a palm tree. Rico is not sure.",
    agz2: "The bananas at the market went missing again. Nobody saw anything. Big footprints by the drums, though. Draw your own conclusions.",
    agz3: "Kiko says the old ones call him Agorzilla, and that he grows only the way the island votes. So, candidates: careful what you vote for.",
    agz4: "A caller swears Agorzilla waved at her from the treeline. Rico asked for proof. She sent a photo of a very surprised banana.",
    agz5: "The footprints by the drums are back. Bigger this time. Either Agorzilla has grown, or somebody bought new boots.",
    agz6: "Nobody has a clear photo of Agorzilla. Everybody has a theory. Rico's theory: he listens to this station. Hello, big fellow. The bananas are on the house.",
    /* the phone-in */
    c1: "We have a caller on line two. Go ahead. She says her transaction is pending. Madam, so is Rico's career. Next caller!",
    c2: "Line one: a fisherman asks if the testnet is safe for his savings. Sir, the coins are worth nothing. Keep your savings in the fish.",
    c3: "A caller from the north beach wants to know if validators ever sleep. They sign in their sleep, my friend. That's commitment.",
    c4: "A listener writes: Rico, why are blocks numbered? So we know which one came after the last one, my friend. That's the whole secret.",
    c5: "Caller asks: Rico, what's a consensus rule? A rule everybody has to follow and nobody can change alone. Like Lola's closing time.",
    c6: "A text from a listener: my wallet put a rule on itself and now it won't let me spend. That's not a bug, my friend. That's character.",
    c7: "On the line: a tourist asking where he can buy test coins. You can't, sir. They're free, and worth exactly that. Welcome to the island.",
    c8: "Line three is a gull. Rico can't understand a word, but the Book says it called. Go ahead, gull. Thank you, gull.",
    c9: "Somebody keeps calling to ask if this is live. Yes. Everything on this station is live. Except the coins. The coins are pretend.",
    c10: "A caller asks if Rico can make the next block come faster. Rico can play faster music. The block doesn't care. Respect.",
    /* Tau corner: what makes this chain different, in one breath */
    tc1: "Tau corner, short and sweet: on this chain the rules are written in Tau logic, and every new rule is checked against the old ones. Contradictions don't get a seat.",
    tc2: "Tau corner: which blocks count and who may make them is decided by rules on the chain itself. And those rules change only by a vote of the validators.",
    tc3: "Tau corner: the fees on this chain come out of the rules too. Change the rule, change the fee. No back room, just a vote.",
    tc4: "Tau corner: a wallet can write a rule for itself, like: never more than this much at once. Every node then refuses the transfers that break it.",
    tc5: "Tau corner: this is an alpha. No real money, no finality, and now and then a reorg. That's not a scandal. That's what a test is for.",
    tc6: "Tau corner: a retractable transfer waits in escrow until a block height or a time. Until then the sender can take it back. After that, it pays out on its own.",
    tc7: "Tau corner: a co-signed transfer parks on the chain and goes through by itself the moment the sender's own rule is satisfied. No chasing, no reminders.",
    tc8: "Tau corner: anybody can run a node and watch the chain. You don't need permission to read. Just a computer, some patience, and Docker.",
    /* between songs */
    s1: "That was the news. Now something for the heart, and something for the hips.",
    s2: "Stay with us. After the break: more rumours, more blocks, and a song nobody remembers, so it never gets old.",
    s3: "You're on Radio Coco. Don't touch that dial. There is no dial. But don't touch it anyway.",
    s4: "Short break while Rico drinks some water. The chain keeps going. It doesn't need water. Show-off.",
    s5: "Next up: a calypso for every validator who signed today. And one for the ones who overslept.",
    s6: "This one goes out to every transaction still waiting on the pier. Your block is coming.",
    s7: "Time check: it's always now on Radio Coco. The block height tells you the rest.",
    s8: "If you just tuned in: four candidates, one island, one Book, and Rico. In that order of reliability.",
    /* hello by the listener's own hour */
    am1: "Good morning, island! The coffee is hot, the blocks are fresh, and the gulls are already complaining.",
    am2: "Morning, early birds. The validators have been up all night. Rico has been up for five minutes. Let's go.",
    pm1: "Good afternoon from Radio Coco. The sun is high, the fees are low, and the rumours are warming up.",
    pm2: "Afternoon, island. Siesta time for people, block time for the chain.",
    ev1: "Good evening, island. The lighthouse is on, Bar La Ola is full, and the Book is still writing.",
    ev2: "Evening on Radio Coco. Pour yourself something cold. The chain is busy, Rico is not.",
    nt1: "Late night on Radio Coco. Just you, me, the waves, and a validator somewhere signing in the dark.",
    nt2: "Still awake? So is the chain. It never sleeps. Rico will, in about four songs.",
  };
  /* which lines can stand in for each other: Rico picks one he has not said lately (game.js remembers what he said) */
  const SETS = {
    open: ["op1", "op2", "op3", "op4", "op5"],
    general: Array.from({ length: 30 }, (_, i) => "g" + (i + 1)),
    fog: ["fog", "fog2"], calm: ["calm", "calm2"], breeze: ["breeze", "breeze2"], choppy: ["choppy", "choppy2"], showers: ["showers", "showers2"], clear: ["clear", "clear2"],
    rule: ["rule1", "rule2", "rule3", "rule4"], cosign: ["cosign1", "cosign2"], cosvote: ["cosvote"], lock: ["lock1", "lock2"], back: ["back1", "back2"],
    offer: ["offer"], offerYes: ["offerYes"], law: ["law1", "law2"], lawSim: ["lawSim"], lawVote: ["lawVote"],
    refusedLaw: ["refusedLaw"], refusedOwn: ["refusedOwn"], refused: ["refused"], burst: ["burst1", "burst2"], ghost: ["ghost1", "ghost2", "ghost3"],
    toStake: ["toStake"], toFixed: ["toFixed"], nowStake: ["nowStake"], nowFixed: ["nowFixed"], midnight: ["midnight"], restart: ["restart"],
    joke: Array.from({ length: 36 }, (_, i) => "j" + (i + 1)), call: Array.from({ length: 10 }, (_, i) => "c" + (i + 1)),
    corner: Array.from({ length: 8 }, (_, i) => "tc" + (i + 1)), segue: Array.from({ length: 8 }, (_, i) => "s" + (i + 1)),
    flash: Array.from({ length: 6 }, (_, i) => "flash" + (i + 1)), tag: Array.from({ length: 6 }, (_, i) => "tag" + (i + 1)),
    valIn: ["valIn"], valOut: ["valOut"], feeUp: ["feeUp"], feeDown: ["feeDown"], rev: ["rev"], whale: ["whale1", "whale2"],
    ghostHalloween: ["hw1", "hw2", "hw3", "hw4"], ghostAfter: ["po1", "po2", "po3", "po4", "po5", "po6"],
    ring: ["ring1", "ring2", "ring3"],
    legend: ["agz1", "agz2", "agz3", "agz4", "agz5", "agz6"],
    morning: ["am1", "am2"], afternoon: ["pm1", "pm2"], evening: ["ev1", "ev2"], night: ["nt1", "nt2"],
  };
  /* callers who phone the studio, each in their own voice (make.py make --voice who=Name), with a question in the
     vein of the testnet's public Q&As, and Rico's answer. A call is the caller's line, then Rico's. */
  const CALLS = [
    ["zia", "Hi Rico, it's Zia from Miss Hana's class! Do I have to learn Boolean algebra to write rules on Tau?",
      "Good question, Zia. Rico can tell you what he sees: the rules on the testnet are written in logic today. A little logic goes a long way, like a little salt in a soup. Miss Hana will be thrilled you asked."],
    ["zia", "Rico, it's Zia again. If a rule says always, does it really have to hold forever?",
      "In Tau logic, always means at every step in time, yes. That's why people think hard before they write it. Rico once promised always, and meant until Thursday."],
    ["ozzie", "G'day Rico! Ozzie here, on holiday. Where do I buy some of those test coins? I want a big bag.",
      "You can't buy them, mate. They're free, and worth exactly that. Rico doesn't do prices. Rico does songs. Here's one for your holiday."],
    ["ozzie", "Ozzie again! Rico, when's the mainnet? I've got a flight on Friday.",
      "Rico doesn't know, mate, and anyone who gives you a date on the radio is selling something. Enjoy the testnet. It's free, and the view is great."],
    ["bert", "Rico, it's old Bertie from the pier. In my day every ship had a captain. Who's the captain of this blockchain?",
      "Nobody, Bertie. On this chain the rules steer, and the rules only change when enough validators agree. Think of a ship where the crew votes on the map."],
    ["bert", "Bertie again. Can the validators vote to change the rules for changing the rules?",
      "They can, Bertie, if enough of them agree. A rule that changes its own amendment rule. Makes your head spin like a capstan."],
    ["dom", "Rico, it's Dom, from the hammock. I have a theory. What if somebody sneaks in a rule that contradicts the old ones?",
      "Then the chain refuses it at the door, Dom, before anyone votes. Your theory has been tested. It lost."],
    ["dom", "Dom again. Rico, is it true all of this is just one guy with a lot of wallets?",
      "The chain only sees wallets, Dom. One guy or a whole village, it treats them all the same. Equality, island style."],
    ["nell", "Rico, Nell here, from the fish stall. The testnet said no to my transfer. My own rule, it said! Who wrote that rule?",
      "You did, Nell. Personal rules, darling: the chain holds you to your own word, even on the days you'd rather it didn't."],
    ["nell", "Nell again. How do I know my transfer really happened?",
      "Look it up in a block, Nell. Every block has a number, and anyone can check what's inside. Just like the Book in the lighthouse, only with more zeros."],
    ["mae", "Rico dear, it's Auntie Mae from the bakery. Everybody's talking about AI. Will Tau be a robot that bakes my bread?",
      "Nobody will touch your bread, Auntie Mae. As Rico understands it, Tau is about rules a machine can read and check, not robots in the kitchen. Your rolls are safe."],
    ["mae", "Auntie Mae again. Rico, is there somewhere I can read the code for this testnet?",
      "There is, Auntie. The testnet code is public on GitHub. Rico read some of it. Then Rico needed a nap."],
  ];
  /* what the islanders say in the places (the same English as in game.js, which the tests check) */
  const LAWT = { harbour: "A deep harbour for cruise ships", road: "A road round the island" };
  const EMBV = { frost: ["harbour", 40], salado: ["road", 35] };
  const CAST = [
    ["hana", "Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."],
    ["sam", "Sam keeps the minutes today. Pick a law; the other three candidates vote, two yes and it is law."],
    ["lola", "Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."],
    ["rico", "Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time."],
    ["lola", "A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house."],
    ["sam", "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing."],
    ["sam", "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."],
    ["sam", "Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks."],
    ["sam", "Three moves a day, five days, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."],
    ["sam", "Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law."],
    ["rico", "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me."],
    ["rico", "Done. And this one’s true, so let them check. The Book backs you up."],
    ["rico", "This just in on Radio Coco, ninety-seven point three!"],
    ...NAMES.map(n => n.toLowerCase()).flatMap(c => [[c, "Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory."], [c, "After what you did? Buy yourself a lemonade."], [c, "Not today. Show me how you vote first."]]),
    ...Object.entries(EMBV).flatMap(([who, [law, n]]) => [[who, `We are counting on you for “${LAWT[law]}”. We would hate to remind the island in public.`], [who, `${n} coins, today. All we ask is that you propose “${LAWT[law]}” before the election. A small thing between friends.`]]),
  ];
  /* what Rico can put on air: the four rumours that are not true, and the true things the Book has seen */
  const LIES = ["Marisol fishes inside the reef at night", "Tobias wants to sell the lighthouse", "Baako’s coconuts are imported", "Hana wants school on Sundays"];
  const EMBN = { "North Wind Embassy": 40, "South Current Embassy": 35 };
  const CLAIMS = [...LIES, ...NAMES.flatMap(x => [...Object.entries(EMBN).map(([y, n]) => `${x} took ${n} coins from the ${y}`), ...NAMES.filter(y => y !== x).map(y => `${x} paid for the rumour about ${y}`), `${x} broke a pact`])];
  CLAIMS.forEach(c => CAST.push(["rico", c + "!"]));
  const fill = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
  /* every line anyone can speak, as [who, English]: the server makes one clip for each */
  function all() {
    const out = [];
    for (const [k, s] of Object.entries(L)) {
      if (k === "topLaws") NAMES.forEach(x => out.push(fill(s, { x })));
      else if (k === "pact") NAMES.forEach(x => NAMES.forEach(y => x !== y && out.push(fill(s, { x, y }))));
      else if (k === "day") for (let n = 1; n <= DAYS; n++) out.push(fill(s, { n, m: DAYS }));
      else out.push(s);
    }
    return [...out.map(t => ["rico", t]), ...CAST, ...CALLS.flatMap(([w, q, a]) => [[w, q], ["rico", a]])];
  }

  /* the clips the server has made so far */
  let have = null;
  const ready = fetch(BASE + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null))
    .then(j => { have = new Set((j && j.clips) || []); }, () => { have = new Set(); });
  async function key(who, s) {
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + s));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }
  const cache = new Map();
  const clip = k => { if (!cache.has(k)) cache.set(k, fetch(BASE + k + ".mp3").then(r => (r.ok ? r.arrayBuffer() : null), () => null)); return cache.get(k); };
  /* speak a line in someone's voice: all its spoken parts, in order, or nothing at all when one clip is missing */
  async function speak(parts, who = "rico") {
    const SND = window.COVE_SOUND;
    if (!SND || !SND.on || !SND.speak || !window.crypto || !crypto.subtle) return false;
    await ready;
    const said = parts.filter(p => p.v), keys = await Promise.all(said.map(p => key(p.who || who, p.v)));
    if (!keys.length || !keys.every(k => have.has(k))) return false;
    const bufs = await Promise.all(keys.map(clip));
    if (bufs.some(b => !b)) return false;
    return SND.speak(bufs.map((b, i) => (said[i].who && said[i].who !== who ? { b: b.slice(0), tel: true } : b.slice(0))));   // a caller sounds like a telephone
  }
  /* lines that make sense away from the game (the radio in the site header, assets/radio.js): the hellos and Rico's
     testnet humour, jokes, the phone-in and Tau corner, without the ones about the election. Each is a parts list, shown translated where the page has it. */
  const tr = s => (window.TauI18n ? TauI18n.t(s) : s);
  const hud = () => [...SETS.open, ...SETS.general.filter(k => k !== "g11" && k !== "g14"), ...SETS.joke.filter(k => !["j24", "j25"].includes(k)), ...SETS.call, ...SETS.corner, ...SETS.legend].map(k => [{ t: tr(L[k]), v: L[k] }]);
  window.RICO = { L, SETS, CAST, CALLS, NAMES, all, speak, fill, key, hud };
})();
