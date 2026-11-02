/* The islanders' voices. Every line anyone can say aloud is fixed and listed here: Rico's lines on the radio strip
   (RICO.L) and what each islander says when you walk in (RICO.CAST). The server speaks each one once with that
   islander's voice (infra/rico/make.py) and keeps the clips at node.tauhud.com/rico/<key>.mp3, listed in index.json;
   the key is the first 16 hex of sha1("<who>|<English text>"). Numbers and block heights are never spoken, only
   shown, so a fixed set covers everything. A line whose clip is missing is simply shown as text, as before.
   rabbit/voices.json is the list the server reads (node tests/voices.mjs --write makes it; the tests check it).
   window.RICO = { L, SETS, CAST, CALLS, all(), speak(parts, who), hud(), call(c, ring, bye), wake() }: a line is a list of parts { t: shown text, v: spoken English or null,
   who: whose voice, when not the speaker's }. */
(() => {
  "use strict";
  const BASE = "https://node.tauhud.com/rico/";
  const NAMES = ["Marisol", "Tobias", "Baako", "Hana"];   // the four candidates (game.js CANDS)
  const DAYS = 7;
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
    /* the fog by how long it lasts (an hour, hours, a day), and what Rico says in between while the chain stands still */
    fh1: "Fog for over an hour now. No new block. Rico has counted the waves twice. Both times, the same number.",
    fh2: "An hour without a block. The validators are surely just thinking very hard. Rico respects a long thought.",
    fh3: "Still no block, over an hour now. Lola has started serving the lemonade in bigger glasses.",
    fl1: "Hours without a block now. The chain is having a siesta, and nobody on this island argues with a siesta.",
    fl2: "Several hours of fog over the chain. Old Sam says he has seen worse. Then he admits he hasn't.",
    fl3: "Still no new block, hours now. Somebody on the pier is writing a song about the last one. It's a ballad.",
    fl4: "Hours of silence on the chain. Remember, folks, this is a testnet. Testing your patience counts too.",
    fd1: "No new block for most of a day. Rico has started talking to the last one. It's a very good listener.",
    fd2: "A whole day of fog, folks. The last page of the Book is getting famous. Tourists take pictures of it.",
    fd3: "A day or more without a block. If anybody sees the next one, tell it Radio Coco says hello, and please come home.",
    st1: "While the chain naps, a reminder: no block means no new rules, no new transfers, and no new excuses. Just the old ones.",
    st2: "Breaking news: nothing. Still nothing. Rico will keep you posted the moment nothing changes.",
    st3: "Listeners ask if the chain is broken. Rico says: it's an alpha, it's allowed a nap. And the coins aren't going anywhere. They can't.",
    st4: "Kiko says when the wind is gone, the canoes wait. No blocks, and the radio waits. Same weather, different boats.",
    st5: "Marisol says when the fish stop biting, you mend the nets. So Rico is dusting off the records until the blocks come back.",
    st6: "Dear chain, Radio Coco is still on the air. Are you? Blink twice if you're validating.",
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
    deja1: "A wallet just agreed to feed Déjà: one test AGRS in the café cat's bowl, sealed in a block. She needs three a day, and Rico has never found out who the other two are.",
    deja2: "Somebody paid into Déjà's bowl. Marisol says the cat pretends not to notice. Rico has seen her notice.",
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
    c4: "A listener writes: Rico, why are blocks numbered? So we know which one came after the last one, my friend. That's the whole secret.",
    c6: "A text from a listener: my wallet put a rule on itself and now it won't let me spend. That's not a bug, my friend. That's character.",
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
    /* the show opens: the first thing Rico says when the game starts and the radio comes on, shouted for joy
       (make.py speaks the lines in SETS.wake as a euphoric shout, after a drum roll and the station horn) */
    wakeAm: "Wakey wakey, White Rabbit Keeeey! Radio Coco, ninety-seven point threeee! The sun is up, the blocks are fresh, and Rico is LOUD!",
    wakePm: "Heeeeey, White Rabbit Keeeey! Radio Coco, ninety-seven point threeee! Out of the hammock, the island needs you!",
    wakeEv: "Goood eeevening, island! This is Radio Coco, ninety-seven point threeee, and the night is young! Rico is not, but the night is!",
    wakeNt: "Still uuuup, White Rabbit Keeeey? So is Radio Coco, ninety-seven point threeee! The chain never sleeps, and tonight neither does Rico!",
    wake1: "Coco, coco, coco... RADIO COCOOOO! Ninety-seven point three, the loudest little station on any testnet!",
    wake2: "Ladies, gentlemen and wallets of all sizes! Welcome to the island! This is Rico, this is Radio Coco, and this is your wake-up caaaall!",
    /* the songs Radio Coco plays (music.js SONGS), announced while they play */
    sn_coco: "On Radio Coco now: Coco Calypso, the island's own tune. If you can't hum it yet, you will by Thursday.",
    sn_mango: "Here's Mango Run! Fast, sticky and sweet. Do not dance near the fruit stall.",
    sn_lowtide: "Low Tide, on Radio Coco. Lean back and let the bass do the walking.",
    sn_tinroof: "Tin Roof Shuffle, straight from the Coconut Works. Some say that's the organ. Some say it's three bicycles.",
    sn_hammock: "Hammock Hours. Rico recommends one cold drink and zero decisions.",
    sn_moon: "Moon Over the Pier. Grab someone you like, or a coconut that listens.",
    /* when the caller has said goodbye */
    bye1: "Thanks for calling! The lines are open, island. Keep them warm.",
    bye2: "And that's the phone-in on Radio Coco. Rico loves a caller who hangs up on time.",
    bye3: "Thank you, caller! Next one, ring away.",
    bye4: "Bye bye! Back to the music.",
    bye5: "Take care! On Radio Coco every caller is a VIP: a Very Island Person.",
    bye6: "Thanks for the call! Rico's phone is always on. The battery isn't, but the phone is.",
    bye7: "Goodbye and good tides! Here's a song.",
    bye8: "What a call. Rico has goosebumps. Or it's the air conditioning. Either way, more music!",
    /* what the chain itself shows, told as island news (game.js reads it from the newest blocks):
       one hand sealing every block lately, that hand sending nothing itself, a second hand joining in */
    solo1: "Election results from the chain: one candidate, one vote, and the winner takes every block today. Landslide.",
    solo2: "Every block lately was sealed by the same hand. Rico admires the dedication. Rico also wonders who covers the lunch break.",
    solo3: "The chain's choir is one voice right now. A beautiful solo. Somebody please join in on the chorus.",
    solo4: "News from the block-sealing committee: they met today. Attendance: one. Motion carried unanimously.",
    solo5: "One keeper sealing every page of the chain. Old Sam knows the feeling. He says: get a deputy, and a hammock.",
    solo6: "Rico checked who sealed the latest blocks. It took a second. Same name every time. Lovely handwriting, though.",
    solo7: "The chain is a one-man band today: drums, bass and every single block. Rico respects that. Rico is also a one-man band, and look how that turned out.",
    solo8: "Fun fact: right now one validator seals every block on the testnet. For a dress rehearsal, fine. For opening night, you want the whole cast.",
    postman1: "The one sealing every block hasn't sent a single transaction lately. Like a postman who delivers everything and never writes home.",
    postman2: "Every block, the same sealer, and not one transaction of their own. Pure service. Rico would at least send himself a postcard.",
    duet1: "Hold on, island: more than one hand is sealing blocks now! The choir has a second voice. Rico is tearing up a little.",
    duet2: "The chain's solo just became a duet! Two sealers, one Book. Rico is calling it a band.",
    /* the chain started over from block zero on the first of November, after a rule voted in by one voice stopped it */
    fresh1: "The chain is brand new this week. It started over from block zero, and all the old blocks are gone from the live chain. Like footprints at high tide.",
    fresh2: "The story so far: somebody's proposal got voted in by a single voice, took effect, and the chain stopped right there. So the testnet started over at block zero. Rico calls that a test that worked.",
    fresh3: "New house rule on the chain: only the ones who seal the blocks get to vote on the rules now. Everybody else, the suggestion box is closed for renovation.",
    fresh4: "Fresh chain, fresh start. Rico lost all his favourite old blocks. He'd be sadder, but most of them were empty.",
    fresh5: "Remember: a testnet that never breaks has never been tested. This one has been tested. Thoroughly. Last weekend.",
    record1: "The chain just passed block five thousand and twenty-eight, the page where the old chain stood still. New personal best! Somebody give it a medal.",
    record2: "Past block five thousand and twenty-eight and still going. The old chain never got this far. Rico is proud like a parent at sports day.",
    /* the testnet as anyone can see it, any day */
    net1: "Testnet tip: if something breaks, congratulations, you are now a tester. Write it down, tell the developers, take a bow.",
    net2: "Somewhere out there a brand-new node is reading the whole chain from block zero. Rico salutes you, little node. Drink water.",
    net3: "The chain has no opening hours. It works nights, weekends and holidays, and it has never once asked for a raise.",
    net4: "On this testnet every rule has to agree with every other rule. Rico tried that with his relatives once. It took three Christmases.",
    net5: "Reminder: the coins on this chain are for testing. If somebody sells you some, Rico has a lighthouse to sell you too.",
    net6: "A block just came in empty. Rico doesn't judge. Some mornings Rico comes in empty too.",
    /* the mainland: somewhere over the sea, a ferry that is always coming soon (never a date) */
    ml1: "Ferry news: the big ferry to the mainland is coming soon. Rico has been saying that since he got this job. The timetable just says: when it's ready.",
    ml2: "A listener asks what's on the mainland. Rico has never been. People say the rules there work like ours, only for many more islands.",
    ml3: "Old Sam says the mainland is real. He has seen its lights on clear nights. Lola says that's the lighthouse, reflecting in his glasses.",
    ml4: "Packing tip for the mainland: bring your Book. Nobody over there will believe what you did here without it.",
    ml5: "Kiko is building a canoe big enough to reach the mainland. He says it's done when it's done. The only honest timetable on this island.",
    ml6: "Rico will not give you a date for the mainland ferry. Anybody who does is selling tickets.",
  };
  /* which lines can stand in for each other: Rico picks one he has not said lately (game.js remembers what he said) */
  const SETS = {
    open: ["op1", "op2", "op3", "op4", "op5"],
    general: Array.from({ length: 30 }, (_, i) => "g" + (i + 1)),
    fog: ["fog", "fog2"], fogHour: ["fh1", "fh2", "fh3"], fogLong: ["fl1", "fl2", "fl3", "fl4"], fogDay: ["fd1", "fd2", "fd3"], stall: ["st1", "st2", "st3", "st4", "st5", "st6"], calm: ["calm", "calm2"], breeze: ["breeze", "breeze2"], choppy: ["choppy", "choppy2"], showers: ["showers", "showers2"], clear: ["clear", "clear2"],
    rule: ["rule1", "rule2", "rule3", "rule4"], cosign: ["cosign1", "cosign2"], cosvote: ["cosvote"], lock: ["lock1", "lock2"], back: ["back1", "back2"],
    offer: ["offer"], offerYes: ["offerYes"], law: ["law1", "law2"], lawSim: ["lawSim"], lawVote: ["lawVote"],
    refusedLaw: ["refusedLaw"], refusedOwn: ["refusedOwn"], refused: ["refused"], burst: ["burst1", "burst2"], deja: ["deja1", "deja2"], ghost: ["ghost1", "ghost2", "ghost3"],
    toStake: ["toStake"], toFixed: ["toFixed"], nowStake: ["nowStake"], nowFixed: ["nowFixed"], midnight: ["midnight"], restart: ["restart"],
    joke: Array.from({ length: 36 }, (_, i) => "j" + (i + 1)), call: ["c4", "c6"],
    corner: Array.from({ length: 8 }, (_, i) => "tc" + (i + 1)), segue: Array.from({ length: 8 }, (_, i) => "s" + (i + 1)),
    flash: Array.from({ length: 6 }, (_, i) => "flash" + (i + 1)), tag: Array.from({ length: 6 }, (_, i) => "tag" + (i + 1)),
    valIn: ["valIn"], valOut: ["valOut"], feeUp: ["feeUp"], feeDown: ["feeDown"], rev: ["rev"], whale: ["whale1", "whale2"],
    ghostHalloween: ["hw1", "hw2", "hw3", "hw4"], ghostAfter: ["po1", "po2", "po3", "po4", "po5", "po6"],
    ring: ["ring1", "ring2", "ring3"],
    legend: ["agz1", "agz2", "agz3", "agz4", "agz5", "agz6"],
    morning: ["am1", "am2"], afternoon: ["pm1", "pm2"], evening: ["ev1", "ev2"], night: ["nt1", "nt2"],
    wake: ["wake1", "wake2"], wakeAm: ["wakeAm"], wakePm: ["wakePm"], wakeEv: ["wakeEv"], wakeNt: ["wakeNt"],
    songs: ["sn_coco", "sn_mango", "sn_lowtide", "sn_tinroof", "sn_hammock", "sn_moon"],
    bye: Array.from({ length: 8 }, (_, i) => "bye" + (i + 1)),
    solo: Array.from({ length: 8 }, (_, i) => "solo" + (i + 1)), postman: ["postman1", "postman2"], duet: ["duet1", "duet2"],
    fresh: Array.from({ length: 5 }, (_, i) => "fresh" + (i + 1)), record: ["record1", "record2"],
    net: Array.from({ length: 6 }, (_, i) => "net" + (i + 1)), mainland: Array.from({ length: 6 }, (_, i) => "ml" + (i + 1)),
  };
  /* callers who phone the studio, each in their own voice through the telephone: listeners (ready voices, make.py
     CALLERS) and the islanders themselves. A call is a little conversation: who, then what is said in turn, the
     caller first, then Rico, and so on; after the caller's goodbye Rico signs off with a line from SETS.bye, unless
     the line dropped (cut). game: about the election, only in the game; when: only while the chain shows it
     (solo: one hand sealing every block; fresh: the chain started over and has not yet passed its old height). */
  const CALLS = [
    { who: "zia", say: ["Hi Rico, it's Zia from Miss Hana's class! Do I have to learn Boolean algebra to write rules on Tau?",
      "Good question, Zia. Rico can tell you what he sees: the rules on the testnet are written in logic today. A little logic goes a long way, like a little salt in a soup. Miss Hana will be thrilled you asked.",
      "So if I learn it, can I write a rule that says no homework on Fridays?",
      "For your own wallet, Zia, sure. Getting Miss Hana to sign it, that's the hard part.",
      "Worth a try! Bye Rico!"] },
    { who: "zia", say: ["Rico, it's Zia again. If a rule says always, does it really have to hold forever?",
      "In Tau logic, always means at every step in time, yes. That's why people think hard before they write it. Rico once promised always, and meant until Thursday.",
      "Until Thursday? What happened on Thursday?",
      "Lola's lemonade happened, Zia. Some promises melt.",
      "Ha! Bye Rico!"] },
    { who: "ozzie", say: ["G'day Rico! Ozzie here, on holiday. Where do I buy some of those test coins? I want a big bag.",
      "You can't buy them, mate. They're free, and worth exactly that. Rico doesn't do prices. Rico does songs. Here's one for your holiday.",
      "Free? Then I'll take two bags!",
      "Take ten, mate. The faucet doesn't judge.",
      "Legend. Cheers, Rico!"] },
    { who: "ozzie", say: ["Ozzie again! Rico, when's the mainnet? I've got a flight on Friday.",
      "Rico doesn't know, mate, and anyone who gives you a date on the radio is selling something. Enjoy the testnet. It's free, and the view is great.",
      "Fair enough. Can I at least get a T-shirt?",
      "Rico has one. It says: I survived the testnet. It's still being printed.",
      "Ha! Cheers mate, see ya!"] },
    { who: "bert", say: ["Rico, it's old Bertie from the pier. In my day every ship had a captain. Who's the captain of this blockchain?",
      "Nobody, Bertie. On this chain the rules steer, and the rules only change when enough validators agree. Think of a ship where the crew votes on the map.",
      "A crew that votes on the map? We'd still be in port.",
      "Some days the chain is, Bertie. That's the fog in Rico's weather report.",
      "Aye, I've seen that fog. Mind how you go, Rico."] },
    { who: "bert", say: ["Bertie again. Can the validators vote to change the rules for changing the rules?",
      "They can, Bertie, if enough of them agree. A rule that changes its own amendment rule. Makes your head spin like a capstan.",
      "And what stops them changing it every Tuesday?",
      "Only that enough of them have to agree. Getting sailors to agree on a Tuesday is harder than it sounds.",
      "That it is. Fair winds, lad."] },
    { who: "dom", say: ["Rico, it's Dom, from the hammock. I have a theory. What if somebody sneaks in a rule that contradicts the old ones?",
      "Then the chain refuses it at the door, Dom, before anyone votes. Your theory has been tested. It lost.",
      "Okay, but what if it only contradicts them a little?",
      "There's no a little in logic, Dom. It holds or it doesn't. Like a hammock.",
      "Deep. I'm going back to the hammock. Later, Rico."] },
    { who: "dom", say: ["Dom again. Rico, is it true all of this is just one guy with a lot of wallets?",
      "The chain only sees wallets, Dom. One guy or a whole village, it treats them all the same. Equality, island style.",
      "So I could be a whole village if I make enough wallets?",
      "On the chain, yes. At Lola's bar you still pay for one lemonade at a time.",
      "Worth knowing. Later, Rico."] },
    { who: "nell", say: ["Rico, Nell here, from the fish stall. The testnet said no to my transfer. My own rule, it said! Who wrote that rule?",
      "You did, Nell. Personal rules, darling: the chain holds you to your own word, even on the days you'd rather it didn't.",
      "Can I take my word back?",
      "Only the way your own rule allows, Nell. That's the charm of it, and the curse.",
      "Then I'm writing smaller promises. Bye, love."] },
    { who: "nell", say: ["Nell again. How do I know my transfer really happened?",
      "Look it up in a block, Nell. Every block has a number, and anyone can check what's inside. Just like the Book in the lighthouse, only with more zeros.",
      "And anybody can look at mine?",
      "Anybody, Nell. That's the deal. Rico only snoops for rumours, and even those end up in the Book.",
      "Good to know. Ta-ta, Rico."] },
    { who: "mae", say: ["Rico dear, it's Auntie Mae from the bakery. Everybody's talking about AI. Will Tau be a robot that bakes my bread?",
      "Nobody will touch your bread, Auntie Mae. As Rico understands it, Tau is about rules a machine can read and check, not robots in the kitchen. Your rolls are safe.",
      "So the machine just checks the rules?",
      "That's how Rico understands it, Auntie. You write down what you mean, and it checks that it all fits together.",
      "Well, I mean my rolls. Bye now, dear."] },
    { who: "mae", say: ["Auntie Mae again. Rico, is there somewhere I can read the code for this testnet?",
      "There is, Auntie. The testnet code is public on GitHub. Rico read some of it. Then Rico needed a nap.",
      "A nap? Was it that boring?",
      "Not boring, Auntie. Just very honest. Every line says exactly what it does.",
      "Like my recipes. Bye now, dear."] },
    /* the islanders phone in too */
    { who: "lola", say: ["Rico, it's Lola. A man at the bar says Radio Coco only ever plays one song.",
      "Tell him we have six now, Lola. Six! Rico has been composing at night.",
      "He says they all sound happy.",
      "It's an island, Lola. Sad songs get a sunburn.",
      "Ha! Come by later, your lemonade's getting warm. Bye, honey."] },
    { who: "sam", say: ["Rico, it's Sam at the lighthouse. Just checking the radio works. It's been very quiet up here.",
      "It works, Sam! You're on the air right now.",
      "Am I? Well. Hello, island. Read the Book. That's all.",
      "Short and true, Sam. Your trademark.",
      "Goodnight, Rico. Keep the lamp on."] },
    { who: "tobias", game: 1, say: ["Rico! Tobias here, harbour master and humble candidate. I wish to dedicate a song to myself.",
      "To yourself, Tobias?",
      "Who else has worked so hard for me?",
      "Fair point. Here's one for Tobias, from Tobias.",
      "Splendid! Louder, if you please. Farewell!"] },
    { who: "marisol", game: 1, say: ["Rico, it's Marisol. The fish want to know who's voting for the reef.",
      "The fish can read the Book like everybody else, Marisol.",
      "They can't read, Rico. They're fish.",
      "Then they'll have to trust the ones who can. Isn't that politics?",
      "Hmph. Gotta go, the nets won't mend themselves. Bye!"] },
    { who: "baako", say: ["Rico, Baako from the Coconut Works! The organ is playing by itself again.",
      "By itself, Baako?",
      "Well, Noor sat on it. But it sounded good! Can you put it on the radio?",
      "If it happens again, Rico will record it. Number one on the island charts.",
      "Ha ha! I'll tell her. Bye bye!"] },
    { who: "noor", say: ["Rico, it's Noor. Baako says the organ thing was me.",
      "Was it, Noor?",
      "It was a chair. I sat on a chair. The chair was on the organ.",
      "Island, that's how great music starts.",
      "It's how great backaches start. Bye."] },
    { who: "hana", say: ["Rico, Hana from the school. The children want to know why blocks have numbers but no names.",
      "Because a number never lies about its age, Hana.",
      "That's not an answer. That's a fridge magnet.",
      "Rico's whole career is fridge magnets.",
      "I'll give you a C. Goodbye, Rico."] },
    { who: "frost", game: 1, say: ["Good evening. This is the North Wind Embassy. We would like to request a song.",
      "Ambassador Frost! What would you like to hear?",
      "Something about surveyors. Something deep.",
      "Rico doesn't take requests that come in envelopes, Ambassador.",
      "Who said anything about envelopes? Goodnight."] },
    { who: "salado", game: 1, say: ["Rico, my friend! Salado, South Current. We love your station. We love it so much.",
      "Thank you, Ambassador. Is there a but?",
      "No but. Only a road. Around the island. Play something about a road.",
      "Rico plays songs, Ambassador, not roads.",
      "Everyone plays something, my friend. Ciao!"] },
    { who: "ama", say: ["Rico, this is Ama. The tide is low tonight.",
      "Thank you, Ama. Is that news?",
      "Everything that comes back on time is news, Rico. Your blocks could learn from the tide.",
      "Rico will pass that on to the chain.",
      "Pass it on gently. Good night, child."] },
    { who: "kai", say: ["Rico, Kai from Reef Proof! Our sensors just signed their thousandth reading!",
      "Congratulations, Kai! What did it say?",
      "Water. Wet. Signed and timestamped.",
      "Breaking news, island: the sea is wet, and now it's on record.",
      "Ha! Come diving sometime, Rico! Bye!"] },
    { who: "pim", say: ["Rico, it's Pim, the surveyor. Could you play something exactly four minutes and twelve seconds long?",
      "Why exactly that long, Pim?",
      "It's how long the walk is from the camp to the... to nowhere in particular.",
      "Pim, are you measuring the radio?",
      "No! Yes. Only a little. Goodbye."] },
    { who: "kiko", say: ["Rico, Kiko at the canoes. I saw him again. In the jungle.",
      "Agorzilla?",
      "He took a banana and left a footprint. A big one.",
      "Kiko, did you take a picture?",
      "I took the banana back. Priorities. Bye, Rico."] },
    { who: "wren", say: ["Rico dear, Captain Wren. The sea gave something odd back today.",
      "What was it, Captain?",
      "A sock. Labelled: transaction, still waiting.",
      "Ghost transactions are washing up on the beach now?",
      "Everything washes up eventually, dear. Toodle-oo."] },
    { who: "tano", say: ["Rico, it's Tano up on the hill. My drums just carried your last joke to all three hills.",
      "And? How did it land?",
      "The far hill sent back one word.",
      "Laughter?",
      "Why. Goodbye, Rico."] },
    /* the mainland ferry, which is always coming soon */
    { who: "gus", say: ["Rico, Gus again. When does the ferry to the mainland leave?",
      "When it's ready, Gus. Same answer as yesterday.",
      "And tomorrow?",
      "Tomorrow too. Consistency, Gus. It's our brand.",
      "I'll pack slowly, then. Cheerio."] },
    { who: "tobias", say: ["Rico! Tobias. I have already ordered a hat for the day the mainland ferry arrives.",
      "Has anyone told you when it arrives, Tobias?",
      "No. That is why I ordered a very patient hat.",
      "Island, the harbour master is ready. The ferry, we'll see.",
      "Splendid. Farewell!"] },
    /* new listeners, and calls that go wrong */
    { who: "gus", say: ["Hello? Is this the bakery?",
      "This is Radio Coco, sir. You're on the air.",
      "Oh. Well, while I have you. Two loaves, please.",
      "Rico will pass it on to Auntie Mae.",
      "Much obliged. And play something slow. Cheerio."] },
    { who: "gus", say: ["Rico, it's Gus. I've been on hold since the old chain.",
      "Gus, the old chain is gone. You're the longest-waiting transaction on this island.",
      "Do I get a prize?",
      "You get a song, Gus. Here it comes.",
      "I'll take it. Cheerio."] },
    { who: "vik", cut: 1, say: ["Rico, quick question about the ghost transac",
      "And he's gone. The phone line runs past Baako's goats. They chew on it."] },
    { who: "zia", cut: 1, say: ["Rico, can you say hi to my mum? She's",
      "We lost her! Zia's mum, if you're listening: hi from Zia. And from Rico."] },
    { who: "pearl", when: "solo", say: ["Rico, Pearl here, I'm new on the island. Who stamps all the blocks? I keep seeing the same signature.",
      "Right now one hand seals every block, Pearl. On a testnet that's the warm-up act.",
      "Isn't that a bit lonely?",
      "Very. Rico plays them a song every night. This one's for you, whoever you are.",
      "That's sweet. Thank you, Rico. Bye now!"] },
    { who: "rudy", when: "fresh", say: ["Rico, Rudy here. All my old transactions are gone! Everything from last week!",
      "Rudy, the testnet started over from block zero. Everybody's old blocks went with it.",
      "So I'm poor again?",
      "You were never rich, Rudy. Test coins. You're exactly as rich as before: pretend.",
      "Huh. That's weirdly comforting. Thanks, Rico."] },
    { who: "tess", when: "fresh", say: ["Rico, it's Tess. I read that somebody voted a rule in all by themselves, and the whole chain stopped. Is that true?",
      "One vote, one rule, and the chain stood still right where it took effect. So it started over, and now only the block sealers vote on the rules.",
      "So the suggestion box is closed?",
      "Closed for renovation, Tess. That's what testnets are for: you find the loose plank before the party.",
      "Ha. Okay, love the show, bye!"] },
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
    ["sam", "Three moves a day, seven days from Monday to Sunday, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."],
    ["sam", "The island’s numbers are out of reach just now. Your campaign goes on as before."],
    ["marisol", "Nobody owns her, and nobody feeds her alone: she eats on a day only when three wallets agree, one test AGRS each. Say yes and you are one of the three. The other two? Whoever passes through."],
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
    return [...out.map(t => ["rico", t]), ...CAST, ...CALLS.flatMap(c => c.say.map((t, i) => [i % 2 ? "rico" : c.who, t])), ...(window.RABBIT_TALK_LINES ? window.RABBIT_TALK_LINES() : [])];   // talk.js: coming back, asking more
  }

  /* the clips the server has made so far */
  let have = null;
  const ready = fetch(BASE + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null))
    .then(j => { have = new Set((j && j.clips) || []); }, () => { have = new Set(); });
  async function key(who, s) {
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + s));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }
  /* which radio lines have their clips already (Rico's L keys, and the calls whose every line is spoken): game.js
     prefers those, so the radio keeps talking while new lines still wait for their voices */
  const VOICED = { l: null, c: null };
  ready.then(async () => {
    if (!have || !have.size || !window.crypto || !crypto.subtle) return;
    const l = new Set(), c = new Set();
    for (const [k, t] of Object.entries(L)) if (!t.includes("{") && have.has(await key("rico", t))) l.add(k);
    for (let i = 0; i < CALLS.length; i++) {
      const x = CALLS[i], ks = await Promise.all(x.say.map((t, j) => key(j % 2 ? "rico" : x.who, t)));
      if (ks.every(k => have.has(k))) c.add(i);
    }
    VOICED.l = l; VOICED.c = c;
  }, () => {});
  /* true or false once known; null while the clip list is still loading (or a line with a name in it) */
  const voiced = k => { if (!VOICED.l) return null; if (/^call:/.test(k)) return VOICED.c.has(+k.slice(5)); return L[k] == null || L[k].includes("{") ? null : VOICED.l.has(k); };
  const cache = new Map();
  const clip = k => { if (!cache.has(k)) cache.set(k, fetch(BASE + k + ".mp3").then(r => (r.ok ? r.arrayBuffer() : null), () => null)); return cache.get(k); };
  /* speak a line in someone's voice: all its spoken parts, in order, or nothing at all when one clip is missing */
  const why = { last: "" };
  async function speak(parts, who = "rico", o = {}) {
    const SND = window.COVE_SOUND;
    if (!SND || !SND.on || !SND.speak) { why.last = "sound not on (" + (SND ? SND.state : "no player") + ")"; return false; }
    if (!window.crypto || !crypto.subtle) { why.last = "no crypto.subtle"; return false; }
    await ready;
    const said = parts.filter(p => p.v), keys = await Promise.all(said.map(p => key(p.who || who, p.v)));
    if (!keys.length) { why.last = "nothing to say aloud"; return false; }
    if (!have.size) { why.last = "clip list not loaded"; return false; }
    if (!keys.every(k => have.has(k))) { why.last = "clip missing: " + keys.filter(k => !have.has(k)).join(","); return false; }
    const bufs = await Promise.all(keys.map(clip));
    if (bufs.some(b => !b)) { why.last = "clip download failed"; return false; }
    const secs = await SND.speak(bufs.map((b, i) => (said[i].who && said[i].who !== who ? { b: b.slice(0), tel: true } : b.slice(0))), o);   // a caller sounds like a telephone
    if (secs) { why.last = "ok"; return secs; }
    /* the sound card would not decode the clip (some phone browsers): the same clips through a plain audio element */
    why.last = "web audio: " + (SND.why || "off") + ", trying the audio element";
    return element(keys);
  }
  /* one audio element, unlocked by the visitor's first tap, plays the clips in a row */
  let EL = null;
  const SILENT = (() => {   // a tenth of a second of silence, as a WAV file
    const n = 800, b = new Uint8Array(44 + n * 2), v = new DataView(b.buffer), w = (o, t) => [...t].forEach((c, i) => (b[o + i] = c.charCodeAt(0)));
    w(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); w(8, "WAVEfmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 8000, true); v.setUint32(28, 16000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, n * 2, true);
    return "data:audio/wav;base64," + btoa(String.fromCharCode(...b));
  })();
  const unlock = () => {
    if (EL) return;
    try { EL = new Audio(); EL.preload = "auto"; EL.src = SILENT; EL.play().then(() => EL.pause(), () => {}); } catch (e) { EL = null; }
    ["pointerdown", "touchend", "keydown"].forEach(n => removeEventListener(n, unlock, true));
  };
  if (typeof addEventListener === "function") ["pointerdown", "touchend", "keydown"].forEach(n => addEventListener(n, unlock, true));
  function element(keys) {
    if (!EL) { why.last += "; audio element not unlocked yet"; return false; }
    return new Promise(res => {
      let i = 0, total = 0, started = false;
      const next = () => {
        if (i >= keys.length) return;
        EL.src = BASE + keys[i++] + ".mp3";
        EL.onloadedmetadata = () => { if (!started) { started = true; total = keys.length * (EL.duration || 3); res(total); why.last = "ok (audio element)"; } };
        EL.onended = next; EL.onerror = () => { why.last = "audio element could not play the clip"; if (!started) res(false); };
        EL.play().catch(() => { why.last = "audio element refused to play"; if (!started) res(false); });
      };
      next();
    });
  }
  /* the voice check (?voice=check): what the phone does with Rico's first line, step by step */
  async function check() {
    const out = [], SND = window.COVE_SOUND;
    out.push("sound: " + (SND ? SND.state + (SND.on ? ", on" : ", not on") : "no player"));
    out.push("crypto.subtle: " + !!(window.crypto && crypto.subtle));
    await ready; out.push("clip list: " + (have ? have.size : 0) + " clips");
    const k = await key("rico", L.op1); out.push("first line " + k + ": " + (have && have.has(k) ? "listed" : "NOT listed"));
    const b = await clip(k); out.push("download: " + (b ? b.byteLength + " bytes" : "failed"));
    const secs = await speak([{ t: L.op1, v: L.op1 }], "rico"); out.push("speak: " + (secs ? Math.round(secs) + " s" : "no") + " · " + why.last);
    return out;
  }
  /* lines that make sense away from the game (the radio in the site header, assets/radio.js): the hellos and Rico's
     testnet humour, jokes, the listeners' letters, the phone-in (the caller in their own voice) and Tau corner, without the ones about the election. Each is a parts list, shown translated where the page has it. */
  const tr = s => (window.TauI18n ? TauI18n.t(s) : s);
  const hud = () => [...SETS.open, ...SETS.general.filter(k => k !== "g11" && k !== "g14"), ...SETS.joke.filter(k => !["j24", "j25"].includes(k)), ...SETS.call, ...SETS.corner, ...SETS.legend, ...SETS.net, ...SETS.mainland].map(k => [{ t: tr(L[k]), v: L[k] }])
    .concat(CALLS.filter(c => !c.game && !c.when).map((c, i) => call(c, SETS.ring[i % SETS.ring.length], SETS.bye[i % SETS.bye.length])));
  /* a call as parts: the phone rings, the conversation, Rico's goodbye (keys from SETS.ring and SETS.bye) */
  function call(c, ring, bye) {
    const p = (who, s) => (who === "rico" ? { t: tr(s), v: s } : { t: tr(s), v: s, who });
    return [p("rico", L[ring]), ...c.say.map((s, i) => p(i % 2 ? "rico" : c.who, s)), ...(c.cut ? [] : [p("rico", L[bye])])];
  }
  /* the show's opener for the hour of the day (or one of the ones for any hour) */
  function wake(hr = new Date().getHours()) {
    const set = Math.random() < 0.35 ? "wake" : hr >= 5 && hr < 11 ? "wakeAm" : hr >= 11 && hr < 17 ? "wakePm" : hr >= 17 && hr < 22 ? "wakeEv" : "wakeNt";
    const ok = SETS[set].filter(k => voiced(k) !== false), any = ["wakeAm", "wakePm", "wakeEv", "wakeNt", "wake"].flatMap(x => SETS[x]).filter(k => voiced(k) !== false);
    const from = ok.length ? ok : any.length ? any : VOICED.l ? SETS.open.filter(k => voiced(k)) : [];   // no opener voiced yet: an ordinary hello that is
    const list = from.length ? from : SETS[set];
    return list[Math.floor(Math.random() * list.length)];
  }
  window.RICO = { L, SETS, CAST, CALLS, NAMES, all, speak, fill, key, hud, call, wake, voiced, check, stop: () => { if (EL && !EL.paused) { EL.onended = null; EL.pause(); } }, get why() { return why.last; } };
})();
