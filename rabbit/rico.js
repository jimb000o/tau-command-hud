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
    fl4: "Hours of silence on the chain. Remember, folks, this is the lagoon: quiet water, nothing lost. Testing your patience counts too.",
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
    /* the weather when Rico knows every sender in the last blocks (relay /api/v1/sources/recent): who, not just how many */
    wxHouse1: "Traffic on the water, but it's house traffic: IDNI's own wallets, the ones the testnet started with, moving coins among themselves. For everybody else, calm seas.",
    wxHouse2: "Those boats out there all fly the same flag: the testnet's founding wallets, doing their rounds. A busy harbour, and not one visitor.",
    wxIsle1: "All those transactions? That's us. White Rabbit Key: your moves and the rival campaigns. Today the island is the weather.",
    wxIsle2: "Plenty of boats, and every one of them left from our own pier: White Rabbit Key's campaigns. The open testnet is having a quiet one.",
    wxShip1: "Busy seas, but it's the cruise ship: simulated passengers, real transactions, paced so the lagoon keeps breathing. Nobody else is out there.",
    wxJungle1: "The waves come from the jungle side today: meals and votes for Agorzilla, and dinner for Déjà. Lots of splashing, all of it friendly.",
    wxHud1: "The transactions out there came through Tau HUD's own wallet: visitors trying the testnet from our pages. Small boats, first time out. Wave if you see them.",
    wxHud2: "Traffic from our own harbour: people sending from the Tau HUD wallet. Every one of those is somebody trying the chain for real.",
    wxHome1: "Plenty of transactions, but Rico knows every boat out there: the island, the jungle, the founders, our own wallet. Home traffic. No strangers on the water.",
    wxHome2: "Looks busy, but it's family: our own apps and the founding wallets. A stranger's boat would stand out today.",
    showers2: "Some transactions are still waiting on the pier for the next block. Bring an umbrella.",
    clear2: "Nothing waiting on the pier. Every transaction has found its block.",
    /* the first line after the page opens */
    op1: "Radio Coco, ninety-seven point three, back on the air. Rico has had his coffee, the Book has had its ink.",
    op2: "You are listening to Radio Coco, the only station broadcasting from the lagoon, Tau Testnet Alpha for the newcomers. If something breaks, that is the point.",
    op3: "Hello island! Fresh blocks, fresh rumours, same old Rico. Stay tuned.",
    op4: "Radio Coco, live from the studio by the harbour. Tonight: politics, gossip and the latest from the chain.",
    op5: "Good to have you, listener. Turn it up, the gulls can't hear.",
    /* between the news: the island and the testnet as Rico sees them */
    g1: "Reminder: on the lagoon the money is pretend and the coconuts are real. Please don't mix them up at the market.",
    g2: "A caller asks how many people use the lagoon. Rico can only count wallets. One person with three wallets is a party of one.",
    g3: "Nobody mines anything on this chain. No pickaxes, no noise. Blocks are sealed by agreement, the quiet island way.",
    g4: "A transaction walks into a block. The block says: you again? The transaction says: no, that was my ghost.",
    g5: "If your transaction is late, don't panic. Blocks come in like ferries: more or less on time, and never the same one twice.",
    g6: "Studio tip: write your own rules before somebody writes them for you. On this chain a wallet can put a rule on itself, and the chain holds it to it.",
    g7: "The Book in the lighthouse and the blocks on the lagoon are cousins. Neither forgets, and neither forgives a typo.",
    g8: "The lagoon means you can make mistakes for free. Rico has been testing his whole life.",
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
    g23: "Some people collect stamps. The lagoon collects signatures. Rico collects excuses.",
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
    rule3: "New personal rule on the lagoon. The wallet said: from now on, not like that. And the chain said: noted.",
    rule4: "Another personal rule on the chain. So far most of them came from just two wallets. Two people, or one person with a lot of coffee: the chain only sees wallets.",
    cosign1: "A co-signed transfer is on the water. The money waits on the pier until the co-signers say yes. Romance, lagoon style.",
    cosign2: "Somebody sent money that needs a second signature. Trust, but sign twice.",
    cosvote: "A co-signer has spoken. Somewhere on the lagoon a transfer is either sailing or staying home.",
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
    deja3: "Three wallets agreed to feed Déjà tonight. She looked at her bowl as if she had expected a fourth.",
    /* where a wave came from, as far as the blocks show it (game.js sources()); {n} is shown as the number and spoken as a
       band of BANDS, {where} as "block 1234" and spoken as "the latest block" */
    /* the eleven wallets the lagoon started with (IDNI's genesis accounts): the same hands, the same habits, a running gag */
    fw1: "In {where} the same wallet paid the same wallet the same amount, for the third time this hour. Old Sam says in his day they called that a marriage.",
    fw2: "The wallets that were here before the island woke up are moving lagoon coins between themselves again. Like Lola's cousins at the bar: they only ever buy each other a drink.",
    fw3: "Rico asked the Book who sends all these transactions. The Book said: the ones who built the harbour. Rico asked why. The Book does not do why.",
    fw4: "Rico has started calling the busiest founder wallet Gerald. Gerald sent {n} transactions in one block. Rico asked Gerald for a song request. Gerald only sends coins.",
    fw5: "Gerald again. Same hour, same amount, same silence. Rico respects a routine. Rico has never kept one.",
    fw6: "Correction from yesterday: Rico said the founders' wallet is called Gerald. The Book says wallets have no names. Rico is sticking with Gerald.",
    /* a place on the island has a rush: moves paid into its jar, ballots into the boxes */
    pl1: "Rush hour at the pier: {n} moves paid into the pier's jar in one block. Tobias says that is the fastest anyone has come to the pier without a ferry being announced.",
    pl2: "The pier bell rang, and {n} wallets answered inside two minutes. Every one of them a lagoon transaction, sealed in {where}. Tobias counted twice. He always counts twice.",
    pl3: "Busy square today: {n} speeches paid into the market jar in one block. Marisol says you can tell an election is near when people start paying to be listened to.",
    pl4: "The council hall took {n} laws in one block. Ama says the chairs are still warm. The Book says they were all checked against each other first. Both are right.",
    pl5: "Radio Coco's own jar just took {n} paid lines in a block. Rico will play every one of them. Rico would like to point out that he did not write them.",
    pl6: "The ballot boxes are filling: {n} ballots sealed in {where}. The lagoon does not count people, only wallets, so Rico will not say how many voters that is. Neither will the Book.",
    pl7: "{n} moves landed in one jar in a single block, somewhere on the island. Rico heard coins, not names. Lola heard it from the bar, and Lola hears everything.",
    /* the rivals' campaign wallets (the island bot's, relay GET /island) */
    rv1: "Marisol's campaign office just sent {n} moves in one go. Either a very good day or a very large pot of coffee.",
    rv2: "Tobias's people moved {n} times in one block. Harbour master's privilege: his office is right next to the water.",
    rv3: "Baako's co-op sent {n} moves in one go, stacked and labelled. Baako counts everything, so Rico will not bother counting again.",
    rv4: "Hana's campaign moved {n} times in one block, between two lessons. Her pupils probably did the paperwork.",
    /* the other side of the bay: Agorzilla's bowl and ballot boxes */
    cz1: "Hungry evening at the café: {n} bowls filled in one block. Across the bay something in the jungle grows by what people vote for. Kiko has a theory. Kiko has several.",
    cz2: "{n} wallets just voted on how the thing in the jungle grows. Rico has seen the photos. Rico has seen clearer photos of fog.",
    /* wallets Rico has never seen, and big amounts */
    un1: "A wallet Rico has never heard of just moved {n} lagoon coins. Pim offered to survey it. Pim offers to survey everything.",
    un2: "{n} wallets Rico has never seen before, in one block. Wallets, not people. The Book wrote them down anyway. The Book writes everybody down.",
    un3: "Big transfer on the lagoon, {n} coins in {where}. Test coins, worth nothing, which is exactly what makes it interesting: somebody is practising.",
    un4: "A new wallet, a big amount, no name. On the mainland that would be a scandal. On the lagoon it is Tuesday.",
    /* the relay said no: our door (tauhud.com/load/ refused per minute), not the lagoon's rule */
    rf1: "The pier bouncer turned {n} transactions away this minute. Not the lagoon's rule, Rico's own door: too many at once from the same place. Come back in a minute, the door is small.",
    rf2: "{n} transactions refused at the relay in the last hour. The chain never saw them. Lola says the bar has the same policy on Fridays.",
    /* the first transaction after a quiet hour: the news while the water is still */
    fs1: "First lagoon coin in an hour, and it went to the island. One move, one jar, one block. Rico heard it land from here.",
    fs2: "An hour of nothing, then one transaction crosses the water. On the mainland that is a rounding error. On the lagoon it is the news.",
    fs3: "One transaction after a quiet hour. Old Sam looked up from the Book. That is how quiet it was.",
    /* the whole island and Déjà's day (game.js isleLines, dejaLines): spoken in bands and names, the exact numbers shown beside */
    isN: "Around the island today: {n} campaigns are running.",
    isLaw: "Across the island one law keeps passing today, and it is in every speech by now.",
    isWin: "Election results from the whole island: {x} has won the most campaigns today.",
    isGov: "{x} governs the island this week.",
    isNews1: "Island news:",
    isNews2: "Fresh from the square:",
    dejaFed: "Déjà has eaten today. Three wallets agreed, and Marisol says she acted surprised.",
    dejaN: "Déjà, the café cat: {n} of three wallets agreed today. One test AGRS says yes; find her.",
    dejaNone: "Nobody has agreed to feed Déjà yet today. Three wallets, one test AGRS each; find her, she is around.",
    /* the cruise ships (game.js shipLine, SETS ship*): Queen Mempool (sq_), MS Dry Run (sd_) and either (sg_), from two or
       three days before to the evening after; s_cut and sc_ for one that did not stay, sw_ why and how, sa_ where the passengers
       are, se_ what just happened, ss_ how the lagoon copes, sl_ the numbers. The passengers are made up, their test coins are real */
    sq_soon: "Saturday at two, the Queen Mempool drops anchor off the island. A hundred and twenty passengers, all made up by our relay, all paying in real test coins. Tobias has started his speech. Pray for the gulls.",
    sq_tomorrow: "Tomorrow at two, the Queen Mempool! Song requests welcome, one transaction each. Rico is warming up his voice, and Lola is hiding the good lemons.",
    sq_today: "Today's the day: the Queen Mempool lands at two, if the lagoon is calm. If it isn't, she waits a little and sails on. A ship that waits for good weather. Smarter than Rico on a Friday.",
    sq_here: "The Queen is in! Passengers on the square, at Lola's, up at the spa. Twelve transactions a minute at most, so the lagoon keeps breathing. Rico is taking requests.",
    sq_gone: "The Queen has sailed. Every coin her passengers spent is in the blocks, and the logbook is public. Count them yourself. Hana's class already did.",
    sd_soon: "Wednesday at four, MS Dry Run. Forty curious passengers, invented by our relay, paying in real test coins. Small ship, big questions. Hana has warned the school.",
    sd_tomorrow: "Tomorrow at four, MS Dry Run. Her passengers book their dives with the right to change their minds, and the coins wait in escrow until the hour. A dry run for the chain. Hence the name.",
    sd_today: "MS Dry Run lands at four today, if the lagoon is calm. If not, she waits a little and sails on. No drama. The logbook writes down why.",
    sd_here: "MS Dry Run is ashore. Notebooks at the lighthouse, the school and the Old Ship. Captain Wren is labelling the passengers faster than they can write.",
    sd_gone: "MS Dry Run has left. The dives they booked pay out by themselves at their hour. No captain needed. Rico finds that very romantic.",
    s_cut: "The cruise ship didn't stay today, folks. She lands only when the lagoon is calm, and she leaves the moment something goes wrong. The logbook says what happened. Rico reads it so you don't have to. But you can.",
    /* two or three days before */
    sq_soon2: "Saturday at two: the Queen Mempool. A hundred and twenty passengers, three times the crowd of MS Dry Run. Salado has ordered towels. Lola has ordered a second blender.",
    sq_soon3: "The Queen Mempool is named after the lagoon's waiting room, where transactions wait for their block. Her passengers' transactions will wait there too, like everybody's. Saturday at two.",
    sd_soon2: "MS Dry Run on Wednesday. A dry run is a rehearsal: you do it for practice, before it counts. Forty made-up passengers, real test transactions, and the lagoon practises having guests.",
    sd_soon3: "Wednesday at four, the little expedition ship drops anchor. Captain Wren has dusted the Old Ship. Kai has counted the wetsuits. Old Sam has done nothing. The lighthouse is always ready.",
    sg_soon1: "Ship talk on the island again. The fishermen say a cruise ship is two or three days out. They once said that about the mainland ferry. This one has a timetable.",
    sg_soon2: "Rico's cruise forecast: a couple of quiet days, then a ship full of made-up tourists with real test coins. Pack sunscreen. Or don't. The tourists won't. They're made up.",
    /* tomorrow */
    sq_tom2: "Tomorrow, the Queen Mempool. At Bar La Ola a table can pay one bill: one transaction, three tills. Lola has been practising her smile. It's going well. Mostly.",
    sq_tom3: "Tomorrow at two, the Queen. The spa takes bookings, and the coins wait in escrow until the hour. Salado has been practising the word escrow in a soothing voice. It isn't soothing.",
    sd_tom2: "Tomorrow at four, MS Dry Run. Forty passengers with notebooks. The school has questions for them. They have questions for the school. Somebody will have to answer eventually.",
    sd_tom3: "Tomorrow, MS Dry Run: the lighthouse, Captain Wren's Old Ship, the school, the reef. Old Sam has polished the Book. It didn't need polishing. He did it anyway.",
    sg_tom1: "A ship in the bay tomorrow. If the lagoon is calm or merely busy, she lands. If it's rough, she waits ten minutes and sails on. Rico respects a ship that knows when to leave.",
    sg_tom2: "Ship tomorrow, folks. The passengers aren't real, but every coin they spend goes into a real block. Bring your questions. Rico brings the music.",
    /* the day itself, more than two hours before */
    sq_today2: "Queen Mempool day! Tobias has been on the pier since breakfast. The ship hasn't. She keeps her timetable: two o'clock, island time. Tobias keeps his own.",
    sq_today3: "The Queen comes today. The spa is steamed, the bar is stocked, and Rico has been warned. Twelve transactions a minute at most, so the lagoon keeps breathing. So does Rico.",
    sd_today2: "MS Dry Run at four today. Hana's class has a list of questions longer than the pier. Captain Wren has a list of answers longer than the class. Somebody bring snacks.",
    sd_today3: "MS Dry Run today. Some passengers will book a dive and then change their minds, on purpose: the lagoon practises giving coins back. Kai has never been this happy about a cancellation.",
    sg_today1: "Ship day, folks. Keep an eye on the sea: half an hour before she lands, you'll see her coming, and the island shows the time she lands.",
    sg_today2: "Ship day. Rico has checked the lagoon twice, the weather once and his hair three times. Priorities.",
    /* two hours or less before */
    sq_close1: "Not long now until the Queen Mempool. Salado is folding towels into swans. Lola is folding her arms.",
    sd_close1: "MS Dry Run is due soon. Captain Wren has put labels on the pier. The pier was fine without labels.",
    sg_close1: "The ship is due within two hours. Keep the radio on: Rico will tell you when she's in sight.",
    sg_close2: "The ship is close, folks. She lands only on a calm or busy lagoon. Rico has asked the lagoon nicely. The lagoon doesn't take requests. Rico does.",
    sg_close3: "Countdown on the island. Tobias has a speech, Salado has towels, Hana has a list and Rico has a microphone. Only one of those is useful. Rico won't say which.",
    /* in sight, half an hour before */
    sq_app1: "There she is! The Queen Mempool, on the horizon. Big, white and a little bit smug.",
    sd_app1: "Ship in sight! MS Dry Run, small and determined, coming round the reef. Captain Wren is already waving a clipboard.",
    sg_app1: "She's in sight, folks. Within half an hour the tenders start, and every passenger pays the pier one coin on stepping ashore. Tobias is at the very end of the pier. Somebody hold his collar.",
    sg_app2: "Look out to sea: that's the ship. When she arrives, she checks the lagoon first. Calm or busy, the tenders go. Anything rougher, she waits.",
    sg_app3: "The ship is coming in. Rico is turning the music down a notch, so you can hear the gulls panic.",
    /* waiting off the reef for a calm lagoon */
    sg_wait1: "The ship is waiting off the reef. She lands only when the lagoon is calm or busy, and she gives it ten minutes. Tobias is holding his breath. Not for ten minutes, Tobias.",
    sg_wait2: "No landing yet: the ship checks the lagoon before she sends anybody ashore. Rico likes a ship with standards. Rico has some too. Mostly about lemonade.",
    sg_wait3: "Still waiting off the island. The tenders are ready, the lagoon isn't, yet. Ten minutes, then she decides. Rico is playing something soothing for the lagoon.",
    /* the tenders bring the passengers ashore */
    sq_land1: "The Queen's tenders are coming in! A hundred and twenty passengers, ten minutes to get them all ashore, one coin each to the pier. Tobias is counting. Out loud.",
    sd_land1: "MS Dry Run's tenders are at the pier. Forty passengers step ashore, notebooks open. The first question has been asked. It was about the pier.",
    sg_land1: "The first passengers are ashore! One coin each to the pier, one transaction each, into the next blocks. Watch the pier light up.",
    sg_land2: "Tenders in, tenders out. For ten minutes the pier is the busiest place on the island. Tobias has never been happier. Or wetter.",
    sg_land3: "They've landed. From now until boarding, every stop they make is a real test transaction to the till of that place. The same tills you pay when you play. Rico will keep you posted.",
    /* in port */
    sq_here2: "Queen passengers everywhere. Some at the spa, some at Lola's, some on the square buying souvenirs they don't need with coins that aren't worth anything. Tourism!",
    sq_here3: "The Queen is in port. A hundred and twenty made-up guests, and every one of them pays like a real one. Salado wants to know if he can keep them.",
    sd_here2: "MS Dry Run's passengers are spread over the island: the lighthouse, the Old Ship, the school, the reef. Wherever you see a guide's pennant, there's a group.",
    sd_here3: "Report from the school: Hana's class is interviewing the passengers. The passengers are made up. The class doesn't mind. The class has questions.",
    sg_here1: "Ship in port, and the lagoon keeps working: blocks come and go, and the passengers' payments go in with everyone else's. No priority lane for tourists. Not even nice ones.",
    sg_here2: "Ship in port, folks. Twelve transactions a minute at most, so there's room on the lagoon for you too. Send something. Wave at the tourists.",
    /* the last ten minutes, back aboard */
    sg_board1: "Last call! The passengers are heading back to the tenders. No more stops. Whatever they still owe goes out at the usual pace, then it's the long walk to the pier and Tobias waving.",
    sg_board2: "Ten minutes to go. The tenders are waiting, and the passengers stop shopping and start waving. Rico knows the feeling.",
    sg_board3: "Back aboard, everyone! If you still see a passenger at Lola's, no, you don't. They're made up.",
    /* left on time */
    sq_gone2: "The Queen Mempool is heading for the horizon. Salado is counting towels, Lola is counting coins, and Tobias is counting the days to Saturday.",
    sd_gone2: "MS Dry Run is off. The rehearsal is over, and the logbook has the whole script. Captain Wren is already writing her review.",
    sg_gone1: "Ship gone, island quiet. Every coin they paid is in the blocks, and the logbook keeps every one for two weeks. Rico keeps it for one song.",
    sg_gone2: "That's it for the ship. If you missed it, the logbook has every single transaction. If you missed Tobias's speech, there's no logbook for that. On purpose.",
    /* never landed, or left early (the logbook says why) */
    sc_land1: "No landing today. The ship waited her ten minutes off the reef, things weren't right, and she sailed on. The logbook says exactly what. Tobias says a lot more, from the pier.",
    sc_land2: "The ship came, looked and sailed on. She lands only when the lagoon is right for it, and today it wasn't. Better a missed landing than a jammed lagoon.",
    sc_stall1: "The ship left early. The lagoon stalled, so she took her passengers back aboard at once. That's the rule: when the chain stops, the ship goes. The logbook says when, to the second.",
    sc_stall2: "Early departure, folks. The lagoon stopped making blocks, and the ship doesn't stay to watch. Was it the ship? The logbook will tell, either way. Rico won't guess.",
    sc_ref1: "The ship left early: the node refused too many of the passengers' transactions. Five refusals among the last twenty, and she goes. The logbook has every refusal, with the node's answer.",
    sc_ref2: "The node said no once too often today, so the ship left before her time. No drama, just rules. Somebody will read the logbook tonight. Rico suspects Hana.",
    /* what the ships are and how they work, at any time */
    sw1: "A word on the cruise ships, since half the island keeps asking. The passengers are made up by our relay. What they pay is real: test coins, on the testnet, in real blocks. Fake tourists, real transactions.",
    sw2: "Why send cruise ships to a testnet? To see how the lagoon copes with a crowd. Better to learn it here, with test coins and made-up tourists, than later with real ones.",
    sw3: "Ship rule number one: twelve transactions a minute, no more, and only when the island bot has nothing to send. The lagoon stays open for everybody else. Especially you.",
    sw4: "Ship rule number two: if the lagoon strains, the ship slows to half pace. If it stalls, she takes everybody back aboard and leaves. No captain argues with the lagoon.",
    sw5: "The ship's logbook is open to anyone, and the address is on your screen. Time, kind, place, amount and the node's answer, for every single transaction. Rico read it. Rico needed a lie-down.",
    sw6: "The two ships use a hundred and sixty wallets: forty for MS Dry Run, a hundred and twenty for the Queen. Wallets, not people. The stats page counts them apart, so nobody mistakes them for new fans. Rico wishes.",
    sw7: "Some passengers book ahead, with the right to change their minds. The coins sit in escrow until the hour, then the chain pays the place by itself. Change your mind before that, and the coins go home.",
    sw8: "At Bar La Ola, a table of Queen passengers pays one bill. One transaction, three tills: the bar, Radio Coco and the Coconut Works. Lola calls it efficient. Noor calls it about time.",
    sw9: "See the rings on the island while a ship is in? Each one is a passenger's transaction, sealed in a block, at the place it paid. The island lights up where the chain says it should.",
    sw10: "Want to watch from the engine room? The testnet load page shows the ship's share, minute by minute, next to everybody else's. Honest numbers, no music. Rico is working on the music.",
    sw11: "Where do the passengers get their coins? From the testnet's faucet, like every new wallet. Nobody prints extra coins for tourists.",
    sw12: "What the passengers never do: vote, change rules, feed Déjà or touch the players' board. They're tourists. They pay, they look, they leave.",
    sw13: "A new kind of transaction gets a trial run: five at most on its first visit. Only when that goes cleanly does it get the whole day next time. Even a ship has to earn trust.",
    /* where most of the passengers are just now (relay GET /cruise: at) */
    sa_book: "Most passengers are up at the lighthouse right now. Two coins at the till, and Old Sam lets them look at the Book. Reading is free. The stairs are not.",
    sa_ship: "The biggest group is at Captain Wren's Old Ship. Three coins each, and she tells them which planks are original. All of them, apparently.",
    sa_school: "The school is the busiest place on the island right now. Six coins a visit, and for once Hana's class gets to ask the questions.",
    sa_dive: "Most of them are at the dive centre. Twelve coins a dive, and Kai's sensors sign every reading. Nobody has asked the fish to sign anything.",
    sa_market: "The market square is full of passengers buying souvenirs. Eight coins a stop. Rico has seen the souvenirs. Rico would pay eight coins not to.",
    sa_works: "A crowd at the Coconut Works. Four coins each, and Noor gives the tour. Baako's co-op brings the coconuts. Noor brings the attitude.",
    sa_bar: "Bar La Ola is the place to be right now. Five coins a drink. Lola has stopped asking where they're from. Nobody's from anywhere. They're made up.",
    sa_south: "The spa up at the South Current resort is full. Twenty coins a visit, cucumbers included. Salado is walking between the loungers like a man who just won an argument.",
    sa_radio: "Most of the passengers are right here at Radio Coco. Twenty-five coins a song request, same price as for everybody. Rico doesn't check. Rico just spins.",
    /* what just happened (the relay's counts since the last look) */
    se_book1: "A booking just came in: coins into escrow, paid out at the hour, unless the passenger changes their mind before then. It's allowed. Rico changes his mind every song.",
    se_book2: "Another passenger booked ahead. The coins wait in escrow, the place waits for its hour, and the chain does the rest. No receptionist needed.",
    se_cancel1: "Change of plans! A passenger took a booking back before its hour, and the coins went home. A retractable transfer, doing exactly what it says.",
    se_cancel2: "Somebody withdrew a booking. No form, no phone call, no Salado. One transaction, and the escrow lets go.",
    se_bill1: "One bill, three tills! A table at Bar La Ola just paid the bar, Radio Coco and the Coconut Works in one transaction. Rico's share is on its way. Test coins. Rico will spend it on nothing.",
    se_bill2: "Another group bill at Lola's: one transaction, three places paid. Noor wants to know why the Works is on a bar bill. Coconut snacks, Noor. Coconut snacks.",
    se_full: "The lagoon has caught its breath, and the ship is back to full pace. Twelve a minute at most, as always.",
    se_ref1: "The node just said no to a passenger's transaction. It happens. The logbook keeps the node's answer, and the ship keeps count.",
    se_ref3: "Refusals are adding up. Five among the ship's last twenty transactions, and she leaves, no discussion. Rico is watching. So is the lagoon.",
    /* how the testnet copes with the ship in port (relay GET /load) */
    ss_calm1: "Lagoon report with the ship in port: calm. Blocks keep coming, and nobody waits long for one. The tourists aren't even making a dent. Rico is a little offended on their behalf.",
    ss_calm2: "Still calm out there. The lagoon is handling the ship the way Lola handles a Tuesday.",
    ss_busy1: "The lagoon is busy now. Busy is fine. Busy is what a harbour is for. The blocks are fuller, and the queue still moves.",
    ss_busy2: "Busy lagoon, folks: a hundred and more transactions in the last ten minutes, and not one of them waited more than a minute for its block. The ship is doing her job. So is the chain.",
    ss_strain: "The lagoon is straining, so the ship has slowed to half pace. If it stalls, she leaves at once. That's the safety rope, and Rico is holding it.",
    /* the pirates, Black Sequence (game.js pirateLine): they come unannounced, so nothing before she is in sight (pp_sight,
       pp_sightN after dark), at anchor (pp_here), one line for each trick the chain just refused (pp_t_<trick>, never one that
       got through), weighing anchor, gone (pp_gone; pp_clean only when every trick was refused), cut, the day after (pp_next).
       What a ship learned, from her logbook (sk_), the bookings paid ahead into escrow (ex_), our node answering slowly (se_slow) */
    pp_sight1: "We interrupt this song! A ship off the reef that is on nobody's timetable. Black hull, dark sails, a flag with three chain links. Rico has no idea who they are. Rico has never been happier.",
    pp_sight2: "Breaking news from the harbour: Tobias is running up and down the pier with a telescope. There's a ship out there nobody booked, and she is not answering his horn.",
    pp_sight3: "That's not the Queen, folks, and it isn't Wednesday. That's a pirate ship. Made up by our relay, like every passenger, but whatever they try goes to the real chain. Stay tuned.",
    pp_sightN1: "Lanterns on the water, folks, coming round the reef in the dark. No timetable, no tenders, just a black ship and a lot of lanterns. Rico is turning up the torches at the studio.",
    pp_sightN2: "Out there in the dark: a ship with every lantern lit and no name anyone knows. Pirates. Rico would love to say he saw this coming. He did not.",
    pp_here1: "The pirates are at anchor and staying aboard. They trade from the boat: rum from Bar La Ola, supplies from the market, by rope and basket. And now and then, a trick.",
    pp_here2: "Pirate watch, live on Radio Coco. Every trick they try goes to the chain like any payment, and the chain has to say no. Rico tells you each time it does.",
    pp_here3: "The pirates pay for their rum like anyone else, same price, same chain. It's their other payments you have to watch. The chain is watching. So is Rico.",
    pp_hereN1: "Still at anchor, lanterns swinging. The bar has its torches lit, the market sends baskets out on a rope. A pirate evening on White Rabbit Key. Nobody planned this. Well. The relay did.",
    pp_t_overspend1: "A pirate with an empty purse just tried to pay more than his wallet holds. The chain checked the balance and said no. You can't spend what isn't there. Not even at sea.",
    pp_t_overspend2: "Another overspend from the black ship! Big promises, small purse. The chain refused it before the rum was poured.",
    pp_t_replay1: "Two receipts, one payment: a pirate just sent a payment the chain had already taken, a second time. The chain counts every wallet's payments. Refused.",
    pp_t_replay2: "The old double trick! The same payment, sent again. The chain has a long memory for that sort of thing. No.",
    pp_t_expired1: "The pirate with the pocket watch sent a payment whose time had run out. The chain looked at the clock and said: too late, friend. Refused.",
    pp_t_expired2: "Another expired payment from the pirates. Late is late, even with a very nice watch.",
    pp_t_stale1: "The pirate with the calendar just tried a payment past its block deadline. The chain checks the deadline on every payment, and that one had passed. Refused.",
    pp_t_stale2: "A payment from an old page of the calendar: past its block deadline. The chain said no.",
    pp_t_forged1: "The wax seal trick! A payment signed with another pirate's key. The chain checks every signature against the wallet, and this one didn't match. Refused.",
    pp_t_forged2: "Another forged signature from the black ship. A seal is only as good as the hand behind it, and the chain knows the hand.",
    pp_t_impostor1: "The pirate in the false moustache just paid from another pirate's wallet, signed with his own key. The chain looked straight past the moustache. Refused.",
    pp_t_impostor2: "An impostor again: somebody else's wallet, his own signature. The chain doesn't care about moustaches. Only keys.",
    pp_t_freeride1: "The pirate with the empty hat sent a payment that allows no fee at all. On this lagoon every payment pays its way. Not that one. Refused.",
    pp_t_freeride2: "A free ride attempt from the pirates: a payment with no room for a fee. The chain said: everybody pays the ferryman.",
    pp_t_giant1: "A sack of coins bigger than the island! A pirate just tried an amount bigger than a payment can even hold. The chain checks that too. Refused.",
    pp_t_giant2: "Another giant payment from the black ship. Too big to carry, so the chain won't carry it. Rico admires the ambition, though.",
    pp_t_double1: "Two payments, one sequence number, sent at the same moment! The chain took the first and refused the second. Every wallet's payments go one number at a time. No twins on this lagoon.",
    pp_t_double2: "Another pirate tried to use the same turn twice. The first payment went through, the second found its number already taken. Refused.",
    pp_t_poison1: "Clever one! A pirate paid several places in one payment, and the last transfer was more than his wallet holds. The chain didn't take the cheap ones and drop the rest. It took none of it. All or nothing, folks.",
    pp_t_poison2: "A poisoned basket from the black ship: good coins on top, an empty promise at the bottom. The chain checks the whole basket. Refused, every coin of it.",
    pp_t_cram1: "A pirate just stuffed more transfers into one payment than a payment may carry. Over sixty-four! The chain counted. Refused.",
    pp_t_cram2: "Another overstuffed payment from the black ship. Rico has packed suitcases like that. The chain doesn't sit on them to close them. It just says no.",
    pp_t_governance1: "Now that's bold. A pirate slipped a field into his payment that only the chain's own transactions may set. Like writing a new law on a bar receipt. Refused.",
    pp_t_governance2: "Another pirate tried to smuggle a rule change inside a rum payment. Rules on this chain change by agreement, not in a bottle. Refused.",
    pp_t_taxman1: "A pirate just handed in a fee rule that would tax every wallet on the lagoon, not only his own. A rule you write may steer your own payments, nobody else's. The chain sent the taxman home. Refused.",
    pp_t_taxman2: "Another pirate taxman! A one percent cut on everybody's transfers. On this chain your rules cover your own wallet and nobody else's. Refused, and nobody pays a coin.",
    pp_t_stranger1: "A pirate tried to take back another pirate's booking. Only the one who paid can take a booking back before its time. The chain checked whose it was. Refused.",
    pp_t_stranger2: "Hands off, matey! A pirate reached for a booking that isn't his. The chain knows who made every booking. Refused.",
    pp_t_phantom1: "A pirate tried to take back a booking that never existed. The chain looked for it, found nothing, and said so. You can't cancel a ghost.",
    pp_t_phantom2: "Another phantom booking from the black ship. Taking back what you never booked: bold, imaginative, refused.",
    pp_t_late1: "Too late, captain! A pirate tried to take back his own booking after its release time. Once that hour has passed, a booking can't be taken back. Refused.",
    pp_t_late2: "A pirate missed the window on his own booking. A booking can be taken back only before its release time, and his had gone. Refused. Set an alarm, matey.",
    pp_board1: "The black ship is weighing anchor. The lanterns go in one by one. They leave as they came: without a word to Tobias.",
    pp_gone1: "The pirates have gone. What the chain answered to their tricks is in the logbook, with the time and the chain's own words. Rico recommends it as bedtime reading.",
    pp_gone2: "Black sails on the horizon, going the other way. The island has counted its coconuts. All there. The chain was on watch all evening.",
    pp_gone3: "That was the Black Sequence. She doesn't tell the island when she comes. You'll know when Tobias starts shouting.",
    pp_clean1: "Tonight's pirate report: every trick they tried, the chain refused, each with the answer it should give. Rico would like to thank the chain. And the pirates, for trying so hard.",
    pp_clean2: "Not one trick got past the chain tonight. Every refusal is in the logbook. Hana's class will have them all by morning.",
    pp_recap: "The pirates' evening in numbers: the chain refused {n} pirate tricks. Every refusal is in the logbook, with the chain's answer.",
    pp_cut1: "The pirate ship didn't stay her time. The logbook says why. Even pirates keep the rule of this harbour: when the lagoon isn't right, ships go.",
    pp_next1: "Last night's pirates are still the talk of the island. Tobias wants a pirate page in the harbour book, Hana's class wants a pirate test, and Rico wants a pirate jingle. Only one of us will get it.",
    pp_next2: "About last night's pirate ship: when is she back? She doesn't tell the island. You'll know when Tobias starts shouting. Again.",
    pp_t_overspend3: "Overspend! A pirate offered more coins than he owns. Rico tried that at the market once. The market gave the same answer as the chain.",
    pp_t_replay3: "Same payment, second time, same pirate. The chain keeps count of every wallet's payments, and that count had already moved on. Nice try, matey.",
    pp_t_expired3: "A pirate payment, stamped too late. Every payment carries its own deadline, and this one had passed before it reached the chain. Refused, and right on time.",
    pp_t_stale3: "Another pirate payment past its block deadline. The blocks moved on, the payment didn't. The chain doesn't go back for stragglers. Refused.",
    pp_t_forged3: "A forged seal from the black ship. On this lagoon the key signs, not the hand. Wrong key, no payment.",
    pp_t_impostor3: "A pirate in another pirate's coat, paying from his wallet. The chain doesn't check coats. It checks that the signature belongs to the wallet that pays. Refused.",
    pp_t_freeride3: "A pirate tried to sail for free: no fee allowed, not even a small one. The chain's fee rule bends for nobody. Not even for a very nice hat.",
    pp_t_giant3: "A pirate just tried to send more than a payment can even hold. Rico has seen big tips. That was not a tip, that was a typo with ambition. Refused.",
    pp_door1: "Wondering why the pirates' tricks never show up in the blocks? The chain turns them away at the door, before any block. Only their honest payments get written down, like the landing fee and the rum.",
    pp_here4: "Not one song request from the black ship, folks. Rum, yes. Soap, yes. Coconuts, yes. Music, no. Rico is not hurt. Rico is a little hurt.",
    pp_hereN2: "Night watch on Radio Coco. Lanterns on the black ship, torches at the bar, and the chain wide awake. Rico's coffee is wide awake too.",
    pp_clean3: "Pirate report: every trick tried, every trick refused, every refusal with its reason. If the pirates are listening: thank you for testing. Please never come to my studio.",
    pp_clean4: "Good news for every wallet on this lagoon: the chain checked balance, order, time, deadline, signature, sender, fee, size, how many transfers, and who may set what, and every pirate trick failed one of those checks. Your payments get the very same checks.",
    pp_gone4: "The black ship is a dot on the horizon now. The island counts what came in: the landing fees, the rum, the soap, the coconuts. Paid the way anyone pays.",
    pp_gone5: "The pirates sailed at the hour they planned. Pirates, on time. Rico has now seen everything.",
    pp_next3: "Morning, lagoon. Yesterday's pirates are in the logbook now, every trick next to the chain's answer. Hana's class is grading them. The pirates are failing.",
    pp_next4: "No black sails this morning, folks. Tobias checked. Twice. Then once more. She comes back when she comes back, and she tells nobody. Rico respects the marketing.",
    sk_rate_down: "Since her last call, this ship sends a little slower: some of her transactions got no answer from our node in time, so she takes it gently. She writes down why, in her logbook.",
    sk_rate_up: "Good news from the logbook: her last call ran clean, every send answered, so this time she may send a little faster. Never more than twelve a minute, though.",
    sk_plan: "The ship has learned something: last time each answer from our node took a few seconds, and she sends one at a time. So she plans fewer stops now, and makes the ones she plans.",
    sk_trial: "One kind of transaction goes back to a small trial on her next call: the node refused some of them last time, though they went through before. Trust, earned again.",
    sk_skip1: "She skipped {n} planned stops today. Not a refusal: our ship sends one transaction at a time and waits for the answer, and a stop that comes too late is skipped, not forced.",
    sk_skip2: "{n} stops skipped today, and the logbook says why: our node's answers took their time. Next time she plans for it. Ships that learn. Rico is taking notes.",
    sk_quiet: "Our node left {n} sends without an answer in time today. That is not a no. The ship waited, slowed down, and checked afterwards which ones reached the chain anyway.",
    sk_clean: "Not one refusal today, folks. Every transaction the node answered, it took. Rico has nothing dramatic to report, and that is the best report there is.",
    se_slow: "Our node is answering slowly just now, so the ship waits a little and goes at half pace for a while. Nobody refused anything. It's patience, not a problem.",
    ex_open: "Wednesday's ship has bookings already: a few passengers paid their fare days ahead, and the coins wait in escrow until she arrives. If the call is cancelled, they go back by themselves.",
    ex_back: "One of Wednesday's passengers has taken the booking back, on purpose. Only the one who paid can do that, and the coins went straight home. A rehearsal, folks.",
    ex_paid: "The fares booked days ago paid out at her arrival. Nobody pressed a button: the escrow let go at the hour, by itself.",
    ex_off: "The call was cancelled, and every fare waiting in escrow went back to its passenger before the hour. That is what escrow is for.",
    /* the real numbers, shown exactly and spoken as a band */
    sl_total1: "Ship report: so far the node has taken {n} transactions from her passengers. Each one is in the logbook, with its time, its place and the node's answer.",
    sl_total2: "Ship report from the island: {n} passenger transactions so far. Rico would count them for you, but the logbook already did.",
    sl_block1: "{n} passenger transactions in {where}. Signed, checked, sealed. The lagoon doesn't care that the passengers are made up. It checks the signatures anyway.",
    sl_block2: "Fresh from the lagoon: {where} holds {n} transactions from the passengers. Watch the island: every place they paid gets a ring.",
    sl_recap: "The ship's day in numbers: {n} transactions the node took, from the first coin at the pier to the last stop. Every one is in the logbook, for two weeks.",
    /* a mixed wave: many wallets at once, nobody leading */
    dk3: "Why did {n} wallets move at the same minute? Rico has three theories, Old Sam has one, and the Book has none. The Book only says that they did.",
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
    j3: "Rico's doctor told him to take it easy. Rico said: I can't, doc. There's no finality on this lagoon. Nothing is ever really over.",
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
    j16: "Lagoon coins have no value. Rico checked. Neither do Rico's jokes. And yet, here we both are.",
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
    j35: "What's the lagoon's favourite song? Don't stop me now. Unless it's a contradiction. Then stop me.",
    j36: "Rico's horoscope for validators: Today you will sign something. Tomorrow too. The stars are very consistent. Like the rules.",
    /* the ghosts in Halloween week, and after it, when Rico wants his island un-haunted */
    hw1: "Happy Halloween from Radio Coco! And right on time, transactions already sealed in a block are still haunting the waiting list. Even the node is in costume.",
    hw2: "Ghosts on the waiting list tonight, folks. Sealed in a block, and still walking around. Perfect timing. Rico approves the decoration.",
    hw3: "Halloween special! The ghost transactions are out. Already in a block, still listed as waiting. Don't be scared, kids. They only say boo to block explorers.",
    hw4: "Spooky season on the lagoon. The ghosts are listed, the pumpkins are carved, and Old Sam has written both into the Book.",
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
    /* the wellness investor: Rico teasing Salado now and then (never his looks, only his business) */
    sal1: "Traffic report from Radio Coco. There is no traffic. There is no road. Salado would like you to know he is working on both.",
    sal2: "Salado says his resort is the place to switch off. Then his phone rings at six every morning. Investors. Folks, that's not switching off, that's a second job with cucumbers.",
    sal3: "Up at the South Current, the loungers are free. The coins are not: thirty-five of them, for any candidate who proposes a road. Rico doesn't judge. Rico just reads the Book.",
    sal4: "Salado asked Rico to call the jungle path to his resort scenic. Rico walked it. It is scenic the way a wet sock is scenic.",
    sal5: "Wellness tip of the hour: breathe in, breathe out, and never let a man on a sun lounger finish the word opportunity.",
    sal6: "Salado's guests carry their suitcases uphill from the pier. He calls it the cardio package. It's included. You can't opt out.",
    sal7: "Rico asked Salado what relaxes him. He said: a road. Folks, this man dreams in asphalt.",
    sal8: "News from the resort: the yoga teacher has stopped crying. Now she just stares at the hill. Calmly. Salado calls that progress.",
    sal9: "Salado told Rico his investors are very patient people. He checked his phone four times during that sentence.",
    sal10: "Salado says a road round the island would bring growth. Rico looked at a map. The island is round. The road ends where it starts, right at the resort. Rico suspects that's the plan.",
    sal11: "Rico's wellness corner: drink water, sleep eight hours, and if somebody offers you thirty-five coins on a sun lounger, read the Book before you say yes.",
    sal12: "Salado likes the testnet. The coins move fast, nobody needs a bank. The part he likes less: every payment is in a block, with the wallet that sent it.",
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
    wakeAm2: "Gooood morning, island! Radio Coco, ninety-seven point threeee! Coffee in one hand, keys in the other, let's GO!",
    wakeAm3: "Morning, morning, MORNING! The roosters lost, Rico won! Radio Coco, ninety-seven point three, waking up the whole lagoon!",
    wakePm2: "Heeeey, good afternoon, island! Radio Coco, ninety-seven point threeee! Lunch is done, the hammock is calling, and Rico says: not yet!",
    wakePm3: "Afternoon, my people! It's hot, it's bright, it's Radio Coco, ninety-seven point three, and Rico has the fan on full!",
    wakeEv: "Goood eeevening, island! This is Radio Coco, ninety-seven point threeee, and the night is young!",
    wakeEv2: "Eeeevening, everybody! Shoes off, sand in, volume UP! This is Rico on Radio Coco, ninety-seven point three, and the lagoon is glowing tonight!",
    wakeEv3: "Ohhh, there you are! Good evening, island! Radio Coco, ninety-seven point threeee! Grab something cold, the evening shift starts NOW!",
    wakeNt2: "Psst... night owls! Radio Coco, ninety-seven point three. Keep it low, keep it warm. The island's asleep, the blocks aren't.",
    wakeNt3: "Midnight on the island, and you're still here! I love you for that. Radio Coco, ninety-seven point threeee!",
    wake1: "Coco, coco, coco... RADIO COCOOOO! Ninety-seven point three, the loudest little station on any lagoon!",
    wake3: "Turn it up, turn it UP! This is Radio Coco, ninety-seven point three, and Rico missed you!",
    wake4: "Coco, coco, coco... RADIO COCOOOO! Ninety-seven point three! Hello, island, it's good to hear you!",
    wake2: "Ladies, gentlemen and wallets of all sizes! Welcome to the island! This is Rico, this is Radio Coco, and this is your wake-up caaaall!",
    /* nodes joining and leaving the network (node.tauhud.com/peers: nodes our node has known for ten minutes or more);
       several at once are one line, the number shown and spoken as a band */
    nd1: "New node on the lagoon! Somebody out there just started reading the whole Book from block zero. Welcome aboard, stranger.",
    nd2: "A fresh lantern on the water: a new node has joined the network. It checks every block for itself, so there's one more pair of eyes on the Book.",
    nd3: "Harbour news: a new node tied up at the pier. Rico doesn't know who runs it. The node doesn't say. Very island of it.",
    nd4: "One more node on the network. It doesn't seal blocks, but it checks every single one. The lagoon's best kind of neighbour: the nosy kind.",
    nd5: "A new node just joined. Somewhere a laptop fan is spinning up, and the lagoon is a little less lonely.",
    ndm1: "{n} new nodes on the lagoon! Lanterns all along the pier. Rico hasn't seen the harbour this busy since the last free lemonade.",
    ndm2: "Big night in the harbour: {n} new nodes joined the network. Every one of them reads the whole Book for itself.",
    ndm3: "{n} new nodes just docked. Rico is running out of welcome songs. Not really. Rico has six.",
    ndm4: "The network is growing: {n} new nodes since Rico last looked. More eyes on every block. That's how a lagoon earns trust.",
    ngo1: "A node went quiet. Maybe a laptop closed, maybe a cat sat on the keyboard. The chain keeps going, and the door stays open.",
    ngo2: "One node fewer on the water. Nodes come and go on a testnet. Nobody needs permission to leave, or to come back.",
    ngo3: "A lantern went out at the pier: a node left the network. If that was you, the Book will still be here when you're back.",
    ngm1: "{n} nodes went quiet at once. A power cut somewhere, or a lot of people closing their laptops for the night. Rico doesn't know which.",
    /* between two songs the band stops and Rico talks (game.js / assets/radio.js, music.js onbreak): the song that
       ended and the one coming, by the order of the playlist (picked by Kilian 3 Nov, plus more so he repeats less) */
    sbA1: "Coco Calypso, the island's own. Now shoes off and elbows in, here comes Mango Run!",
    sbA2: "That was Coco Calypso. Grandma, sit down for this next one. Mango Run!",
    sbA3: "If Coco Calypso was the walk to the beach, this is the sprint back. Mango Run!",
    sbA4: "Coco Calypso, done. Somebody wake up the drummer, he's got work to do. Mango Run!",
    sbA5: "That was the island's own tune. And now the fastest song on the lagoon: Mango Run!",
    sbA6: "Coco Calypso, for the people who walk slowly. Mango Run, for the people who don't.",
    sbB1: "Phew. Mango Run, everybody. Catch your breath, Low Tide is coming in.",
    sbB2: "Okay, okay, slow down, island. After all that running, a little Low Tide.",
    sbB3: "That was Mango Run, and somebody owes the fruit stall a mango. Now, Low Tide.",
    sbB4: "Mango Run is over. Put the fruit down, sit in the sand, here's Low Tide.",
    sbB5: "That one was fast. This one isn't. Low Tide, on Radio Coco.",
    sbB6: "Mango Run, and Rico is out of breath just from playing it. Low Tide, please.",
    sbC1: "Low Tide, nice and easy. And now, straight from the Coconut Works: Tin Roof Shuffle!",
    sbC2: "The tide's gone out, so let's make some noise. Tin Roof Shuffle!",
    sbC3: "Low Tide on Radio Coco. Wake up your knees, the Tin Roof Shuffle is next.",
    sbC4: "Low Tide. Lovely. Now the Coconut Works band is tuning their bicycles. Tin Roof Shuffle!",
    sbC5: "That was Low Tide, with the bass doing all the work. Now everybody else: Tin Roof Shuffle!",
    sbC6: "Back on your feet, island. After Low Tide comes the Tin Roof Shuffle.",
    sbD1: "Tin Roof Shuffle, still rattling in Rico's ears. Time to lie down. Hammock Hours.",
    sbD2: "That was the Coconut Works band. Now go find some shade. Hammock Hours.",
    sbD3: "Enough shuffling. Find a palm tree and lie under it. Here's Hammock Hours.",
    sbD4: "Tin Roof Shuffle. Baako says the organ is fine. Rico has doubts. Now, Hammock Hours.",
    sbD5: "After all that rattling, a guitar and a soft breeze. Hammock Hours.",
    sbD6: "That was the Shuffle. Feet up now. Hammock Hours, on Radio Coco.",
    sbE1: "Hammock Hours. Don't get up. Moon Over the Pier is next, and it's a slow one.",
    sbE2: "Still in the hammock? Good. Stay there. Here's Moon Over the Pier.",
    sbE3: "From the hammock to the pier, no hurry at all. Moon Over the Pier.",
    sbE4: "Hammock Hours, the slowest hour on the island. It's about to get slower. Moon Over the Pier.",
    sbE5: "That was Hammock Hours. Now the flute comes out. Moon Over the Pier.",
    sbE6: "Somebody on the pier asked for a slow one. Here it is: Moon Over the Pier.",
    sbF1: "Moon Over the Pier. Rico's not crying, it's sea spray. And from the top: Coco Calypso!",
    sbF3: "Moon Over the Pier, for the lovers and the gulls. Now the island's own tune again: Coco Calypso!",
    sbF4: "Moon Over the Pier. Somebody on the beach is still slow-dancing. Sorry! Here comes Coco Calypso!",
    sbF5: "That was the slow one. Now the island's own song, from the very first note. Coco Calypso!",
    sbF6: "Moon Over the Pier. The lighthouse keeper asks for that one every night. Coco Calypso!",
    /* or a word for the listener's hour (or any hour), then the next song's name */
    sbH1: "The fishing boats are out, the coffee's in, and the music keeps coming.",
    sbH2: "Still early, island. Brush your teeth, feed the cat, keep the radio on.",
    sbH9: "Good morning to the fishermen coming back and the bakers going home. This one's for you.",
    sbH10: "Second coffee in the studio. Good morning, lagoon. Keep it coming.",
    sbH3: "Half the island's asleep in the shade. The other half is listening. Hello, other half.",
    sbH4: "Too hot to move, so Rico moves the music for you. Next one.",
    sbH11: "The ice at La Ola is melting faster than Rico can talk. So, less talking.",
    sbH12: "Afternoon on Radio Coco. Sun cream on, phone off, radio up.",
    sbH5: "The sun's going down behind the lighthouse. Perfect timing for this one.",
    sbH6: "Bar La Ola is filling up. Somebody over there, turn this one up.",
    sbH13: "The boats are in, the lamps are on. Here's one for the walk home.",
    sbH14: "Good evening to everyone at the bar, and to the one at home with a cat. Next up.",
    sbH7: "It's late. Rico keeps his voice down, the songs stay up. Sorry, neighbours.",
    sbH8: "Night shift on Radio Coco. Just the waves, the crabs, and one more song.",
    sbH15: "Quiet now. Half the island is asleep, and the other half is pretending.",
    sbH16: "Still with us? Rico too. One more for the night owls.",
    sbH17: "Radio Coco, ninety-seven point three. No ads, just the next song.",
    sbH18: "You're listening to Radio Coco. Rico talks less than he plays. Mostly.",
    sbH19: "Six songs, one island, one Rico. Here's the next one.",
    sbH20: "The request line is open. Until somebody calls, Rico picks.",
    nx_coco: "Here's Coco Calypso.", nx_mango: "Here's Mango Run.", nx_lowtide: "Here's Low Tide.",
    nx_tinroof: "Here's Tin Roof Shuffle.", nx_hammock: "Here's Hammock Hours.", nx_moon: "Here's Moon Over the Pier.",
    /* the Night Line: one hour a night (23:00 by the listener's clock) listeners call with their problems on the lagoon,
       one caller between every two songs, and Rico listens and helps (NIGHT below); spoken calm and low (voices.json how "night") */
    nlo1: "It's eleven on the lagoon. The bar is closing, the lighthouse is turning, and the lines are open. This is the Night Line on Radio Coco. Whatever keeps you awake, call Rico.",
    nlo2: "Good evening, night owls. For the next hour Radio Coco slows down. The Night Line is open: your questions, your worries, your stuck transactions. Rico listens.",
    nlo3: "Eleven o'clock. Lights low, phones on. This is the Night Line. No question too small, no wallet too empty. Between every two songs, one of you.",
    nlr1: "Night Line, you're on the air. Take your time.",
    nlr2: "Good evening, you're on the Night Line. What's keeping you up?",
    nlr3: "Night Line. Rico's listening.",
    nlr4: "You're on the air. It's just you, me and the island. Go ahead.",
    nlb1: "Take care of yourself. This song is for you.",
    nlb2: "Thank you for calling. Here's your song.",
    nlb3: "Sleep well. Rico keeps the line warm for the next one.",
    nlb4: "Look after yourself, and look after your keys.",
    nlb5: "Goodnight. And to everybody listening: the line stays open.",
    nlc1: "Midnight. The Night Line closes for today. Thank you for every call. If your problem isn't solved, at least it's shared now. Back to the usual nonsense.",
    nlc2: "That was the Night Line. Same time tomorrow, eleven o'clock. Drink some water, put your keys somewhere safe, and goodnight, lagoon.",
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
    solo8: "Fun fact: right now one validator seals every block on the lagoon. For a dress rehearsal, fine. For opening night, you want the whole cast.",
    postman1: "The one sealing every block hasn't sent a single transaction lately. Like a postman who delivers everything and never writes home.",
    postman2: "Every block, the same sealer, and not one transaction of their own. Pure service. Rico would at least send himself a postcard.",
    duet1: "Hold on, island: more than one hand is sealing blocks now! The choir has a second voice. Rico is tearing up a little.",
    duet2: "The chain's solo just became a duet! Two sealers, one Book. Rico is calling it a band.",
    /* the chain started over from block zero on the first of November, after a rule voted in by one voice stopped it */
    fresh1: "The chain is brand new this week. It started over from block zero, and all the old blocks are gone from the live chain. Like footprints at high tide.",
    fresh2: "The story so far: somebody's proposal got voted in by a single voice, took effect, and the chain stopped right there. So the lagoon started over at block zero. Rico calls that a test that worked.",
    fresh3: "New house rule on the chain: only the ones who seal the blocks get to vote on the rules now. Everybody else, the suggestion box is closed for renovation.",
    fresh4: "Fresh chain, fresh start. Rico lost all his favourite old blocks. He'd be sadder, but most of them were empty.",
    fresh5: "Remember: a lagoon that never breaks has never been tested. This one has been tested. Thoroughly. At the start of November.",
    record1: "The chain just passed block five thousand and twenty-eight, the page where the old chain stood still. New personal best! Somebody give it a medal.",
    record2: "Past block five thousand and twenty-eight and still going. The old chain never got this far. Rico is proud like a parent at sports day.",
    /* the testnet as anyone can see it, any day */
    net1: "Lagoon tip: if something breaks, congratulations, you are now a tester. Write it down, tell the developers, take a bow.",
    net2: "Somewhere out there a brand-new node is reading the whole chain from block zero. Rico salutes you, little node. Drink water.",
    net3: "The chain has no opening hours. It works nights, weekends and holidays, and it has never once asked for a raise.",
    net4: "On this lagoon every rule has to agree with every other rule. Rico tried that with his relatives once. It took three Christmases.",
    net5: "Reminder: the coins on this chain are for testing. If somebody sells you some, Rico has a lighthouse to sell you too.",
    net6: "A block just came in empty. Rico doesn't judge. Some mornings Rico comes in empty too.",
    /* the Book's news on air: what Rico says while the strip shows the details (names and laws are only shown) */
    bkExposed: "The Book has spoken: a rumour has been traced back to whoever paid for it. Ouch.",
    bkRumour: "Tonight on Radio Coco, a fresh rumour. Rico only plays them, folks. The Book does the checking.",
    bkRefused: "A law was refused at the door: it contradicts one already in force. The Book does not do contradictions.",
    bkGovernor: "The island has a governor this week! Whoever won the most campaigns last week. Congratulations, and good luck.",
    bkCarry: "Some laws from last week are still in force, by the whole island. If you don't like them, the hall is open.",
    bkTalk: "All over the island, people are talking about one law today. Rico's phone hasn't stopped ringing.",
    bkWeek: "The Key Crier: a week to the election, Sunday night. Everything anyone does is written in the Book.",
    /* the mainland: somewhere over the sea, a ferry that is always coming soon (never a date) */
    ml1: "Ferry news: the big ferry to the mainland is coming soon. Rico has been saying that since he got this job. The timetable just says: when it's ready.",
    ml2: "A listener asks what's on the mainland. Rico has never been. People say the rules there work like ours, only for many more islands.",
    ml3: "Old Sam says the mainland is real. He has seen its lights on clear nights. Lola says that's the lighthouse, reflecting in his glasses.",
    ml4: "Packing tip for the mainland: bring your Book. Nobody over there will believe what you did here without it.",
    ml5: "Kiko is building a canoe big enough to reach the mainland. He says it's done when it's done. The only honest timetable on this island.",
    ml6: "Rico will not give you a date for the mainland ferry. Anybody who does is selling tickets.",
    /* between the songs: a thank-you to whoever builds the lagoon (no names), and the idea behind it as Rico sees it, in
       island words and only what its makers say in public; bld4a/bld4b frame the title of their latest change
       (node.tauhud.com/devpulse.json), shown between them and not spoken */
    bld1: "A thought for whoever seals the blocks at night while Rico sleeps. The lagoon does not say thank you. Rico does.",
    bld2: "Somebody wrote the rules of this lagoon so that a rule can check another rule. Rico cannot even check his own shopping list.",
    bld3: "The people building the harbour across the water started this lagoon over from block zero at the start of November, on purpose, and the whole lagoon followed. Rico has restarted a show once. Nobody followed.",
    bld4a: "To the builders across the water: Rico reads your latest change on air. Today it says:",
    bld4b: "Rico understood four words of that.",
    idea1: "The idea behind this lagoon, as far as Rico can see it: you write down the rule you want to live by, and then the water holds you to it. Not your neighbour, not a judge. The water.",
    idea2: "On the mainland a rule is a promise. On the lagoon a rule is a wall. Rico has walked into it twice.",
    idea3: "The Book in the lighthouse and the blocks on the lagoon are cousins: nobody can tear out a page, and nobody can forgive a typo.",
    idea4: "One day, they say, people will agree on rules the way the islanders agree on laws in the hall: say it in a language the water understands, and it holds. Rico does not fully understand that language yet. Rico is learning two words a week.",
    idea5: "Nobody mines anything here. No pickaxes, no noise, no coins falling from the sky. Blocks are sealed by agreement. The quiet island way.",
    idea6: "What Rico likes about the lagoon: you can make every mistake for free, and the Book still remembers it. That is how Rico learned the radio.",
    /* Rico does not know everything: who is behind a wallet, or why */
    dk1: "A listener asks who is behind the biggest wallet on the lagoon. Rico does not know. The Book does not know. The wallet knows, and the wallet is not calling in.",
    dk2: "Rico guessed yesterday that the wave at the pier was the ferry. There is no ferry. Rico has been told. Repeatedly.",
  };
  /* which lines can stand in for each other: Rico picks one he has not said lately (game.js remembers what he said) */
  const SETS = {
    open: ["op1", "op2", "op3", "op4", "op5"],
    general: Array.from({ length: 30 }, (_, i) => "g" + (i + 1)),
    wxHouse: ["wxHouse1", "wxHouse2"], wxIsle: ["wxIsle1", "wxIsle2"], wxShip: ["wxShip1"], wxJungle: ["wxJungle1"], wxHud: ["wxHud1", "wxHud2"], wxHome: ["wxHome1", "wxHome2"],
    fog: ["fog", "fog2"], fogHour: ["fh1", "fh2", "fh3"], fogLong: ["fl1", "fl2", "fl3", "fl4"], fogDay: ["fd1", "fd2", "fd3"], stall: ["st1", "st2", "st3", "st4", "st5", "st6"], calm: ["calm", "calm2"], breeze: ["breeze", "breeze2"], choppy: ["choppy", "choppy2"], showers: ["showers", "showers2"], clear: ["clear", "clear2"],
    rule: ["rule1", "rule2", "rule3", "rule4"], cosign: ["cosign1", "cosign2"], cosvote: ["cosvote"], lock: ["lock1", "lock2"], back: ["back1", "back2"],
    offer: ["offer"], offerYes: ["offerYes"], law: ["law1", "law2"], lawSim: ["lawSim"], lawVote: ["lawVote"],
    refusedLaw: ["refusedLaw"], refusedOwn: ["refusedOwn"], refused: ["refused"], burst: ["burst1", "burst2"], deja: ["deja1", "deja2", "deja3"],
    founders: ["fw1", "fw2", "fw3", "fw4", "fw5", "fw6"], place: ["pl1", "pl2", "pl3", "pl4", "pl5", "pl6", "pl7"], rival: ["rv1", "rv2", "rv3", "rv4"], cafe: ["cz1", "cz2"],
    unknown: ["un1", "un2", "un3", "un4"], relay: ["rf1", "rf2"], first: ["fs1", "fs2", "fs3"], mixed: ["dk3"], ghost: ["ghost1", "ghost2", "ghost3"],
    toStake: ["toStake"], toFixed: ["toFixed"], nowStake: ["nowStake"], nowFixed: ["nowFixed"], midnight: ["midnight"], restart: ["restart"],
    joke: Array.from({ length: 36 }, (_, i) => "j" + (i + 1)), call: ["c4", "c6"],
    salado: Array.from({ length: 12 }, (_, i) => "sal" + (i + 1)),
    corner: Array.from({ length: 8 }, (_, i) => "tc" + (i + 1)), segue: Array.from({ length: 8 }, (_, i) => "s" + (i + 1)),
    flash: Array.from({ length: 6 }, (_, i) => "flash" + (i + 1)), tag: Array.from({ length: 6 }, (_, i) => "tag" + (i + 1)),
    valIn: ["valIn"], valOut: ["valOut"], feeUp: ["feeUp"], feeDown: ["feeDown"], rev: ["rev"], whale: ["whale1", "whale2"],
    ghostHalloween: ["hw1", "hw2", "hw3", "hw4"], ghostAfter: ["po1", "po2", "po3", "po4", "po5", "po6"],
    ring: ["ring1", "ring2", "ring3"],
    legend: ["agz1", "agz2", "agz3", "agz4", "agz5", "agz6"],
    morning: ["am1", "am2"], afternoon: ["pm1", "pm2"], evening: ["ev1", "ev2"], night: ["nt1", "nt2"],
    wake: ["wake1", "wake2", "wake3", "wake4"], wakeAm: ["wakeAm", "wakeAm2", "wakeAm3"], wakePm: ["wakePm2", "wakePm3"], wakeEv: ["wakeEv", "wakeEv2", "wakeEv3"], wakeNt: ["wakeNt2", "wakeNt3"],   // picked by ear, 3 Nov
    songs: ["sn_coco", "sn_mango", "sn_lowtide", "sn_tinroof", "sn_hammock", "sn_moon"],
    bye: Array.from({ length: 8 }, (_, i) => "bye" + (i + 1)),
    solo: Array.from({ length: 8 }, (_, i) => "solo" + (i + 1)), postman: ["postman1", "postman2"], duet: ["duet1", "duet2"],
    fresh: Array.from({ length: 5 }, (_, i) => "fresh" + (i + 1)), record: ["record1", "record2"],
    net: Array.from({ length: 6 }, (_, i) => "net" + (i + 1)), mainland: Array.from({ length: 6 }, (_, i) => "ml" + (i + 1)),
    /* between two songs (BREAK maps the song change to its lines sbA1..sbF6) and the Night Line */
    sbAm: ["sbH1", "sbH2", "sbH9", "sbH10"], sbPm: ["sbH3", "sbH4", "sbH11", "sbH12"], sbEv: ["sbH5", "sbH6", "sbH13", "sbH14"], sbNt: ["sbH7", "sbH8", "sbH15", "sbH16"], sbAny: ["sbH17", "sbH18", "sbH19", "sbH20"],
    nodeNew: ["nd1", "nd2", "nd3", "nd4", "nd5"], nodeMany: ["ndm1", "ndm2", "ndm3", "ndm4"], nodeGone: ["ngo1", "ngo2", "ngo3"], nodeGoneMany: ["ngm1"],
    nlOpen: ["nlo1", "nlo2", "nlo3"], nlRing: ["nlr1", "nlr2", "nlr3", "nlr4"], nlBye: ["nlb1", "nlb2", "nlb3", "nlb4", "nlb5"], nlClose: ["nlc1", "nlc2"],
    lagoon: ["bld1", "bld2", "bld3", "idea1", "idea2", "idea3", "idea4", "idea5", "idea6"], dunno: ["dk1", "dk2"],
    /* the cruise ships (game.js shipLine): by how near the ship is, Q the Queen Mempool, D MS Dry Run; what the ships are (shipWhy);
       what just happened in port (shipBook, shipCancel, shipBill), how the lagoon copes (shipCalm, shipBusy), the numbers (shipTotal, shipBlock) */
    shipSoonQ: ["sq_soon", "sq_soon2", "sq_soon3", "sg_soon1", "sg_soon2"],
    shipSoonD: ["sd_soon", "sd_soon2", "sd_soon3", "sg_soon1", "sg_soon2"],
    shipTomorrowQ: ["sq_tomorrow", "sq_tom2", "sq_tom3", "sg_tom1", "sg_tom2"],
    shipTomorrowD: ["sd_tomorrow", "sd_tom2", "sd_tom3", "sg_tom1", "sg_tom2"],
    shipTodayQ: ["sq_today", "sq_today2", "sq_today3", "sg_today1", "sg_today2"],
    shipTodayD: ["sd_today", "sd_today2", "sd_today3", "sg_today1", "sg_today2"],
    shipCloseQ: ["sq_close1", "sg_close1", "sg_close2", "sg_close3"],
    shipCloseD: ["sd_close1", "sg_close1", "sg_close2", "sg_close3"],
    shipApproachQ: ["sq_app1", "sg_app1", "sg_app2", "sg_app3"],
    shipApproachD: ["sd_app1", "sg_app1", "sg_app2", "sg_app3"],
    shipWait: ["sg_wait1", "sg_wait2", "sg_wait3"],
    shipLandQ: ["sq_land1", "sg_land1", "sg_land2", "sg_land3"],
    shipLandD: ["sd_land1", "sg_land1", "sg_land2", "sg_land3"],
    shipHereQ: ["sq_here", "sq_here2", "sq_here3", "sg_here1", "sg_here2"],
    shipHereD: ["sd_here", "sd_here2", "sd_here3", "sg_here1", "sg_here2"],
    shipBoard: ["sg_board1", "sg_board2", "sg_board3"],
    shipGoneQ: ["sq_gone", "sq_gone2", "sg_gone1", "sg_gone2"],
    shipGoneD: ["sd_gone", "sd_gone2", "sg_gone1", "sg_gone2"],
    shipCut: ["s_cut"],
    shipCutLand: ["sc_land1", "sc_land2", "s_cut"],
    shipCutStall: ["sc_stall1", "sc_stall2", "s_cut"],
    shipCutRefused: ["sc_ref1", "sc_ref2", "s_cut"],
    shipWhy: ["sw1", "sw2", "sw3", "sw4", "sw5", "sw6", "sw7", "sw8", "sw9", "sw10", "sw11", "sw12", "sw13"],
    shipBook: ["se_book1", "se_book2"],
    shipCancel: ["se_cancel1", "se_cancel2"],
    shipBill: ["se_bill1", "se_bill2"],
    shipCalm: ["ss_calm1", "ss_calm2"],
    shipBusy: ["ss_busy1", "ss_busy2"],
    shipTotal: ["sl_total1", "sl_total2"],
    shipBlock: ["sl_block1", "sl_block2"],
    pirSight: ["pp_sight1", "pp_sight2", "pp_sight3"],
    pirSightN: ["pp_sightN1", "pp_sightN2", "pp_sight2"],
    pirHere: ["pp_here1", "pp_here2", "pp_here3", "pp_door1", "pp_here4"],
    pirHereN: ["pp_hereN1", "pp_here1", "pp_here2", "pp_here3", "pp_hereN2", "pp_door1"],
    pirBoard: ["pp_board1"],
    pirGone: ["pp_gone1", "pp_gone2", "pp_gone3", "pp_gone4", "pp_gone5"],
    pirClean: ["pp_clean1", "pp_clean2", "pp_clean3", "pp_clean4"],
    pirCut: ["pp_cut1"],
    pirNext: ["pp_next1", "pp_next2", "pp_next3", "pp_next4"],
    shipSkip: ["sk_skip1", "sk_skip2"],
  };
  /* the numbers in a wave line are shown exactly and spoken as a band, so every line has its clips: {n} a count of
     transactions or wallets (BANDS.count) or an amount of lagoon coins (BANDS.coins); a count line never says "one" (a
     single transaction gets a line without a number). Each band is one clip, made like any other line. {where} is the
     block, shown as "block 1234" (a name that starts with b, n, m, a, c, h, g or e would be read as a number or a hash by
     assets/i18n.js). */
  const BANDS = { count: ["a couple of", "a handful of", "a dozen", "dozens of", "a hundred and more"], coins: ["a few hundred", "thousands of", "tens of thousands of", "a hundred thousand and more"] };
  const NUMERIC = { fw4: "count", pl1: "count", pl2: "count", pl3: "count", pl4: "count", pl5: "count", pl6: "count", pl7: "count", rv1: "count", rv2: "count", rv3: "count", rv4: "count", cz1: "count", cz2: "count", un2: "count", rf1: "count", rf2: "count", dk3: "count", isN: "count", ndm1: "count", ndm2: "count", ndm3: "count", ndm4: "count", ngm1: "count", un1: "coins", un3: "coins", sl_total1: "count", sl_total2: "count", sl_block1: "count", sl_block2: "count", sl_recap: "count", pp_recap: "count", sk_skip1: "count", sk_skip2: "count", sk_quiet: "count" };
  const VARIANTS = { dejaN: [{ n: "one" }, { n: "two" }], isWin: NAMES.map(x => ({ x })), isGov: NAMES.map(x => ({ x })) };   // the other fills a line takes, one clip each
  const BLOCK = { where: "the latest block" };   // how the block is spoken
  /* callers who phone the studio, each in their own voice through the telephone: listeners (ready voices, make.py
     CALLERS) and the islanders themselves. A call is a little conversation: who, then what is said in turn, the
     caller first, then Rico, and so on; after the caller's goodbye Rico signs off with a line from SETS.bye, unless
     the line dropped (cut). game: about the election, only in the game; when: only while the chain shows it
     (solo: one hand sealing every block; fresh: the chain started over and has not yet passed its old height). */
  const CALLS = [
    { who: "zia", say: ["Hi Rico, it's Zia from Miss Hana's class! Do I have to learn Boolean algebra to write rules on Tau?",
      "Good question, Zia. Rico can tell you what he sees: the rules on the lagoon are written in logic today. A little logic goes a long way, like a little salt in a soup. Miss Hana will be thrilled you asked.",
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
      "Rico doesn't know, mate, and anyone who gives you a date on the radio is selling something. Enjoy the lagoon. It's free, and the view is great.",
      "Fair enough. Can I at least get a T-shirt?",
      "Rico has one. It says: I survived the lagoon. It's still being printed.",
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
      "There is, Auntie. The code behind the lagoon is public on GitHub. Rico read some of it. Then Rico needed a nap.",
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
    { who: "salado", game: 1, say: ["Rico! It's Salado, up at the resort. I have guests by the pool and they want something to relax to.",
      "Rico can do relaxing, Salado. Anything in particular?",
      "Maybe a song with a road in it? Not about a road. Just a road, somewhere in the second verse.",
      "Twenty-five coins and Rico plays anything. But the Book writes down who paid for it, and the whole island reads the Book.",
      "Ah. No, no. Forget the road, just play something slow. Ciao, Rico!"] },
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
    /* islanders call about the cruise ships while one is near (when: the facts of talk.js, game.js shipFacts) */
    { who: "tobias", when: "shipTomorrow+queen", say: ["Rico! Tobias, from the pier. Could you announce my welcome speech? Tomorrow, two o'clock sharp, the moment the Queen ties up.",
      "She doesn't tie up, Tobias. She anchors outside the reef, and the boats bring her passengers in. You'll be speaking to a boat.",
      "A boat is an audience! A small, wet audience.",
      "Then Rico will play you on, Harbour Master. Keep it under forty minutes.",
      "Thirty-nine! Goodbye, Rico!"] },
    { who: "salado", when: "shipHere+queen", say: ["Rico, it's Salado, up at the resort. Tell the passengers the spa is open. And that the jungle path is, ah, scenic.",
      "Scenic, he says. Folks, it's a jungle path. And if you book a treatment, your coins wait in escrow until your hour. Change your mind before then, and they come back to you.",
      "Rico! Don't tell them they can change their minds!",
      "Rico tells the truth, Salado. It's the only thing on this station that isn't a song.",
      "Fine. Fine! At least the cucumbers are fresh. Ciao, Rico!"] },
    { who: "hana", when: "shipNear+dryrun", say: ["Rico, it's Hana. The children want to know: are the passengers on the Wednesday ship real?",
      "Honest answer, Miss Hana: no. Our relay makes them up. But every coin they pay is a real transaction on the lagoon, and anyone can check it in the blocks.",
      "Good. Then we will check. All of them.",
      "All forty, Miss Hana? That's a lot of homework.",
      "It's a lot of passengers. Thank you, Rico."] },
    { who: "ama", when: "shipToday", say: ["Rico, it's Ama. Please tell today's visitors that the council tree is not on the tour.",
      "You heard her, folks. Anyone may come and listen at the council. Just not forty at once, with cameras.",
      "One at a time, and quietly. Like everybody else.",
      "Like everybody else. Even Tobias?",
      "Especially Tobias. Goodbye, Rico."] },
    { who: "pearl", when: "solo", say: ["Rico, Pearl here, I'm new on the island. Who stamps all the blocks? I keep seeing the same signature.",
      "Right now one hand seals every block, Pearl. On the lagoon that's the warm-up act.",
      "Isn't that a bit lonely?",
      "Very. Rico plays them a song every night. This one's for you, whoever you are.",
      "That's sweet. Thank you, Rico. Bye now!"] },
    { who: "rudy", when: "fresh", say: ["Rico, Rudy here. All my old transactions are gone! Everything from last week!",
      "Rudy, the lagoon started over from block zero. Everybody's old blocks went with it.",
      "So I'm poor again?",
      "You were never rich, Rudy. Test coins. You're exactly as rich as before: pretend.",
      "Huh. That's weirdly comforting. Thanks, Rico."] },
    { who: "tess", when: "fresh", say: ["Rico, it's Tess. I read that somebody voted a rule in all by themselves, and the whole chain stopped. Is that true?",
      "One vote, one rule, and the chain stood still right where it took effect. So it started over, and now only the block sealers vote on the rules.",
      "So the suggestion box is closed?",
      "Closed for renovation, Tess. That's what the lagoon is for: you find the loose plank before the party.",
      "Ha. Okay, love the show, bye!"] },
    { who: "salado", say: ["Rico, Salado here. A small complaint. You keep making jokes about my resort.",
      "Rico only reads out what happens, Salado. You make it very easy.",
      "I could buy a line on your station! Twenty-five coins, a nice jingle about the spa?",
      "You could. And the Book would write down that the resort paid for it, right next to the jingle.",
      "Then make it a quiet jingle. Ciao, Rico!"] },
    { who: "lola", say: ["Rico, it's Lola. Salado was at the bar again. He ordered cucumber water and asked if my bar is scalable.",
      "And is it, Lola?",
      "It's four stools and a fridge, Rico. Then he asked who the fridge reports to.",
      "Rico hopes you told him the fridge reports to nobody. Some things on this island are still free.",
      "I gave him the bill. That one he understood. Bye, Rico!"] },
    /* listeners call about the cruise ships while one is near (when: talk.js RABBIT_SHIP_WHEN); game.js shipLine puts them on air */
    { who: "ozzie", when: "shipNear", say: ["G'day Rico, Ozzie here! I want to go on the cruise. Where do I buy a ticket?",
      "You can't, mate. The passengers are made up by our relay. The two ships have a hundred and sixty wallets between them, and not a single bunk.",
      "Made up? Then who's drinking all the cocktails?",
      "Nobody, Ozzie. The coins are real test coins. The cocktails are imaginary. Lola charges for them anyway.",
      "Sounds like my last holiday. Cheers, Rico!"] },
    { who: "bert", when: "ship", say: ["Rico, Bertie from the pier. Who's the captain of that cruise ship? I'd like a word about her anchoring.",
      "No captain, Bertie. The ship is a program on our relay, with rules: twelve transactions a minute at most, and she leaves the moment the lagoon stalls.",
      "A ship that follows the rules and leaves on time? That's no ship I ever sailed on.",
      "Times change, Bertie. Now the logbook is public, too.",
      "A public logbook. My old captain would've jumped overboard. Mind how you go, lad."] },
    { who: "dom", when: "ship", say: ["Rico, Dom, from the hammock. New theory: the cruise passengers are all one guy with a hundred and sixty wallets.",
      "Dom, that's not a theory, that's the brochure. One relay, a hundred and sixty wallets, all made up, and the card on the island says so.",
      "Wait. So I was right?",
      "You were right, Dom. Mark the date. Rico is playing you a fanfare.",
      "First time ever. I need to lie down. I'm already lying down. Later, Rico."] },
    { who: "nell", when: "ship", say: ["Rico, Nell from the fish stall. These passengers book a dive and then take it back. Can they really do that?",
      "Until the hour comes, Nell, yes. The coins wait in escrow, and before the hour the passenger can take them back. At the hour, the chain pays the place by itself.",
      "So if I sell fish like that, they can cancel my fish?",
      "Only if you sell them with the right to withdraw, Nell. A plain transfer is plain. Fish are final.",
      "Fish are final. I'm putting that on a sign. Bye, love."] },
    { who: "mae", when: "shipToday", say: ["Rico dear, it's Auntie Mae. Will the cruise passengers come to the bakery? I've baked three hundred rolls.",
      "Oh, Auntie. The bakery isn't on their route. They stop at the pier, the bar, the market, the reef and a few more. No bakery.",
      "Not even for one roll?",
      "They're made up, Auntie. Made-up people don't eat rolls. Real people do. Rico is on his way.",
      "Bring a bag, dear. Bring two."] },
    { who: "vik", when: "shipHere", say: ["Rico, Vik. Is twelve transactions a minute the testnet's limit? Seems low.",
      "No, Vik, that's the ship's own speed limit, set by our relay. The point is to watch the lagoon, not to flood it.",
      "So you could go faster?",
      "We could, and we won't, not without a yes from the people who run the lagoon. Rico doesn't break other people's toys.",
      "Responsible. Boring. I like it. Bye, Rico."] },
    { who: "tess", when: "shipGone", say: ["Rico, it's Tess. Somebody online says the cruise ship broke the testnet today. Did it?",
      "Not today, Tess. She stayed her full time and left on schedule. If the lagoon had stalled, she'd have left at once, and the logbook would say so.",
      "Then why are people saying it?",
      "Because a ship that leaves on time isn't news, Tess. Rico reports it anyway. Rico has standards.",
      "Ha. Good for you. Bye, Rico!"] },
    { who: "zia", when: "ship", say: ["Rico, it's Zia! Do the cruise passengers have names? I want to write to one.",
      "Not names, Zia. Wallets. Each passenger is one wallet, a long string of letters and numbers. You could send one a coin, but it won't write back.",
      "Can I give one a name? Like Gerald?",
      "Gerald is taken, Zia. Gerald is a founder wallet. Pick another.",
      "Okay. Then mine is Captain Coconut. Bye, Rico!"] },
    /* the pirates (talk.js RABBIT_SHIP_WHEN pirate facts): while she is at anchor, and after one of her tricks was refused */
    { who: "gus", when: "pirateHere", say: ["Rico! Gus here, out on my boat by the reef. There's a black ship right next to me with lanterns everywhere. Should I be worried?",
      "Not for your boat, Gus. The pirates are made up by our relay, and their tricks go to the chain, not to fishermen. The chain says no for all of us.",
      "So if one of them wants my catch?",
      "Then he'd need your key, Gus. Keep it in your pocket and your catch stays yours.",
      "Pocket. Got it. Bye, Rico!"] },
    { who: "zia", when: "pirateAfter+tImpostor", say: ["Rico, it's Zia! We did pirate bingo in class. Why does the chain refuse a payment from someone else's wallet, even when it looks right?",
      "Because looking right isn't enough, Zia. Every payment is signed, and the chain checks that the signature belongs to the wallet that pays. No match, no payment.",
      "So the false moustache didn't help?",
      "Not one bit. The chain never looks at the moustache. Only at the key.",
      "I knew it! Bye Rico!"] },
    { who: "bert", when: "pirateAfter+pirateClean", say: ["Rico, it's old Bertie from the pier. I don't get it. The pirates' rum payments went through, but their tricks didn't. Same pirates, same chain. Why?",
      "Because the rum payments kept every rule, Bertie. Their own wallet, their own key, enough coins, a fee allowed, on time. Each trick broke one of those, and the chain checks all of them on every payment.",
      "So a pirate who pays properly is just a customer?",
      "On the chain, yes. The chain never checks the eye patch.",
      "Huh. Lola won't like that. Bye, Rico."] },
    { who: "mae", when: "pirateNext", say: ["Rico dear, it's Auntie Mae from the bakery. My grandson says the pirates weren't even real. Is that true?",
      "Half true, Auntie Mae. The pirates are made up by our relay, like the cruise passengers. But their payments are real test payments, and the chain's answers are real too.",
      "So the chain was fighting pretend pirates for real?",
      "Exactly. Better to try every lock while the coins are test coins than to find out later.",
      "Well, I'm still locking my door. Bye, Rico."] },
  ];
  /* the Night Line's callers (L.nlo*): somebody with a problem on the lagoon, Rico listens and helps; always
     technically right (the testnet as it runs), the humour only around it. Same shape as CALLS: caller first, then Rico,
     and so on; Rico's goodbye comes from SETS.nlBye. */
  const NIGHT = [
    { who: "vik", say: ["Hi Rico. It's Vik. I wrote my wallet key on a napkin at Bar La Ola. Lola washed the napkin.",
      "Oh, Vik. And you have no other copy?",
      "No. Can somebody reset it? The builders, maybe?",
      "Nobody can, Vik. Not the builders, not Rico, not the chain. Whoever holds the key is the wallet. That's the hard part, and it's also the whole point.",
      "So my coins are just gone?",
      "They're still there, Vik, but nobody can move them. Test coins, so tonight it's a cheap lesson. Make a new wallet, write the key down twice, and keep the copies in different places. Not on napkins.",
      "Not on napkins. Got it. Thanks, Rico."] },
    { who: "pearl", say: ["Rico, it's Pearl. I sent a transfer an hour ago and it never showed up in a block. Did I do something wrong?",
      "Maybe not, Pearl. First look out of the window: is there fog? When no new blocks come, nothing gets in, yours included.",
      "No, the blocks are coming. Just not mine.",
      "Then it may have run out of time. Every transaction carries a deadline. If it isn't in a block by then, it can never get in, and you pay nothing for it.",
      "So I just send it again?",
      "Check the latest blocks first, so you don't pay twice. If it isn't there, send it again. No harm done.",
      "Okay. That's actually a relief. Bye, Rico."] },
    { who: "rudy", say: ["Rico, Rudy. I sent three transfers really fast, and only the first one went through.",
      "Rudy, every wallet counts its own transactions. One, two, three. Each one has to carry the next number, like the tickets at Auntie Mae's bakery.",
      "And if two of them got the same number?",
      "Then only one of them gets served. The chain never takes ticket four before ticket three, and never the same ticket twice.",
      "So my wallet messed up the count?",
      "Or you were faster than your wallet. Wait until the first one is in a block, then send the next. Slow is fast tonight, Rudy.",
      "Slow is fast. I'll write that on my wall. Night, Rico."] },
    { who: "tess", say: ["Rico, it's Tess. My transfer got refused. It says fee limit too low. What fee? I didn't order a fee.",
      "Every transfer pays a small fee, Tess. The rules on the chain set it. Your fee limit is the most you're willing to pay.",
      "And mine was too small.",
      "Smaller than what the rules ask. The node even tells you the fee it needs. Set your limit at least that high.",
      "If I set it really high, do I go first?",
      "No, and good question. You pay what the rules ask, never your limit, and a big limit doesn't buy you a better place in the queue.",
      "Fair. Okay, thanks Rico. Night."] },
    { who: "ozzie", say: ["G'day Rico, Ozzie. I've got exactly one hundred coins and I want to send all one hundred to my mate. It says no.",
      "Because the fee comes on top, Ozzie. Your wallet has to cover the amount and the fee together.",
      "So I can never send everything?",
      "Not in one go, mate. Look up the fee first, then send what's left over.",
      "And my mate gets a bit less than a hundred.",
      "He gets a bit less, and you get a lesson for free. Buy him a lemonade with the difference.",
      "Legend. Cheers, Rico."] },
    { who: "mae", say: ["Rico dear, it's Auntie Mae. I sent coins to the wrong address. I copied it and I must have missed a bit.",
      "Oh, Auntie. Did you send them as an ordinary transfer?",
      "I think so. Is there a back button?",
      "Not for an ordinary one, Auntie. Once it's in a block, it's done. You can only ask the other wallet nicely to send them back.",
      "And if I don't know whose it is?",
      "Then it's a gift to a stranger. Next time, two things. Check the first and the last few characters of the address. And for anything that matters, use a retractable transfer: you can take it back until its release time.",
      "Like a cake I can still take out of the oven. Thank you, dear."] },
    { who: "nell", say: ["Rico, Nell. I wanted to take back a retractable transfer, and I did, right at the last minute. And it still got paid out!",
      "Nell, a retract has to be inside a block before the release point. Sending it isn't enough.",
      "I sent it two blocks before!",
      "And retracts are free, love. So when it's busy, they wait at the back of the line, behind everything that pays.",
      "So my free retract stood in the queue while the clock ran out.",
      "That's it. Next time, retract early, with room to spare.",
      "Room to spare. Like my fish freezer. Bye, love."] },
    { who: "bert", say: ["Rico. Bertie. I made a rule: anything over a thousand coins needs my daughter's signature. Now I've sent fifteen hundred to the boatyard, and she's asleep.",
      "Then the transfer waits, Bertie. It's parked on the chain, and it goes through by itself the moment she signs.",
      "Can't I get round it, just this once?",
      "Not with that transfer, Bertie. That's what the rule is for. You made it for nights exactly like this one: late, keen, and in a hurry.",
      "Aye. That does sound like me.",
      "Let her sleep. The boatyard opens at eight anyway.",
      "Fair enough. Thank you, lad."] },
    { who: "pearl", say: ["Rico, it's Pearl again. Last week I wrote a rule for my own wallet: never more than fifty coins at once. Now I need to pay eighty, and the chain says no.",
      "Of course it does, Pearl. You told it to. Every node now holds you to that promise.",
      "But I wrote it! Doesn't it trust me?",
      "It trusts last week's Pearl. Last week's Pearl was very clear.",
      "So what do I do?",
      "If your rule talks about each transfer, two smaller ones fit, and each pays its own fee. And next time, write the rule for the Pearl you'll be on a busy Friday.",
      "Last week's Pearl is so annoying. Thanks, Rico."] },
    { who: "vik", say: ["Rico, Vik again. I'm trying to run my own node on Windows, and nothing works.",
      "Vik, on Windows the manual says Docker, or WSL. Have you got one of those?",
      "Docker. It's been building for forty minutes. Is it stuck?",
      "Probably not. The first build compiles the Tau engine, and it does that slowly, once. Make a tea. Make two.",
      "And after that?",
      "After that it starts quickly, and then it reads the chain from block zero. Let it. That's your node learning the island's history.",
      "Learning the history. Okay. I'll make the tea. Thanks."] },
    { who: "tess", say: ["Rico, Tess. My transfer is in a block, I can see it, but the waiting list still shows it too. Did it go out twice?",
      "No, Tess. Once in a block is once. What you're seeing is what the island calls a ghost: a transaction that's already sealed but still listed as waiting.",
      "A ghost? Is that bad?",
      "It's known. The builders know about it. Look at your balance: that tells the truth.",
      "So I just ignore it?",
      "Trust the block, not the waiting list. And don't send it again because of a ghost.",
      "Trust the block. Got it. Night, Rico."] },
    { who: "ozzie", say: ["Ozzie again, Rico. Bit of a worry. A bloke at the bar says this whole chain is one computer sealing every block. Is that true?",
      "Right now, Ozzie, yes. One validator seals every block on the lagoon.",
      "Doesn't that make it, you know, not much of a network?",
      "Fair question. The rules can take more validators, and the ones already there vote them in. When that happens is a decision people make, not a missing piece of code.",
      "So it's a warm-up act.",
      "That's how Rico sees it. It's a test. You test the boat before you fill it with people.",
      "Makes sense. Cheers, Rico."] },
    { who: "gus", say: ["Rico, it's Gus. I can't sleep. My very first transaction is gone. The lagoon started over, and it went with it.",
      "I know, Gus. The chain started again from block zero on the first of November. Everyone's old blocks went.",
      "It was only five coins. To my sister. But it was the first.",
      "Then it happened, Gus, even if the blocks forgot it. You remember it. Your sister remembers it.",
      "Should I send her five again?",
      "Do it in the morning. A new first, on a new chain. That's what a test is for.",
      "A new first. I like that. Cheerio, Rico."] },
    { who: "zia", say: ["Rico? It's Zia. I'm supposed to be asleep.",
      "Zia! It's eleven at night. What's wrong?",
      "I sent loads of tiny transactions today, for fun. Now I'm scared I broke the chain.",
      "You didn't break it, Zia. Every transaction paid its fee, and the chain did what chains do: it wrote them all down. That's testing. You helped.",
      "Really? I helped?",
      "Really. And if something ever does break, you write down what happened and tell the builders. That's how the lagoon gets better. Now, bed.",
      "Okay. Night, Rico."] },
    { who: "dom", say: ["Rico, Dom. I've been watching new blocks come in for six hours. I can't stop. Every time I close it, I open it again.",
      "Dom. What are you waiting for?",
      "I don't know. Something to happen.",
      "The chain writes everything down, whether you watch or not. It doesn't need a witness, Dom. That's the nice thing about it.",
      "So if I go to sleep, I miss nothing?",
      "Everything that happens tonight will still be there in the morning, in the same order. Close the laptop. The blocks will wait.",
      "The blocks will wait. Okay. Later, Rico."] },
    { who: "nell", say: ["Rico, it's Nell. My Harold talks to his node more than to me. He even said goodnight to it.",
      "Did the node say goodnight back?",
      "It printed a block number.",
      "Then it's not much of a conversation, Nell. Harold knows that. Tell him the chain keeps running while he sleeps.",
      "And what do I tell myself?",
      "That he'll come back. New things are loud for a week. And take him to La Ola on Friday. Nodes don't dance.",
      "Nodes don't dance. I'll tell him. Night, love."] },
    { who: "gus", say: ["Rico, Gus again. I sold my boat to buy lagoon coins, for when the mainland ferry comes.",
      "Gus. Stop. Lagoon coins are test coins. They're free, and they're worth nothing.",
      "But when the mainland comes...",
      "Nobody knows when it comes, and nobody honest gives you a date. Test coins are for testing, Gus. Nobody has promised they'll be worth anything, anywhere.",
      "So I sold my boat for nothing.",
      "Who bought it?",
      "My brother-in-law.",
      "Then call him first thing tomorrow. Buy it back, and keep the coins for testing. That's what they're for.",
      "Right. Cheerio, Rico."] },
    { who: "ozzie", say: ["Rico, Ozzie. A man at the pier is selling lagoon coins. Ten real dollars for a thousand. Good deal?",
      "No deal, Ozzie. Lagoon coins are test coins. They're free, and worth exactly that.",
      "He said they'll be worth heaps one day.",
      "Then he's selling a story, mate. Rico has heard that story. It ends with an empty wallet.",
      "Should I tell someone?",
      "Tell everyone at the bar. And whatever happens, never give him your key.",
      "Never the key. Got it. Cheers."] },
    { who: "mae", say: ["Rico dear, Mae. A very nice young man wrote to me. He says he's from support, and he can fix my wallet if I send him my key.",
      "Auntie Mae, don't send it. Not to him, not to anyone.",
      "But he was so polite.",
      "Nobody needs your key to help you. Anyone who asks for it wants your wallet, not your problem.",
      "Oh dear. I nearly did it.",
      "Nearly is fine, Auntie. Nearly is the best word tonight. Block him, and have a cup of tea.",
      "I'll have two. Thank you, dear."] },
    { who: "bert", say: ["Bertie here. My neighbour sent me a rule offer. Says it's for my own good. Should I accept it?",
      "First, Bertie: an offer binds you to nothing. Only if you accept it does it become a rule on your wallet.",
      "And then?",
      "Then the chain holds you to it, like any rule you wrote yourself. So read it. Every line. Ask your neighbour what it does.",
      "And if I don't understand it?",
      "Then don't accept it. An offer runs out by itself after a while.",
      "I'll let it run out, then. Night, lad."] },
    { who: "vik", say: ["Rico, Vik. My node is running now! How do I become a validator?",
      "Congratulations, Vik. A running node already checks every block it gets. That counts for something.",
      "But I want to seal blocks.",
      "Validators join by a vote of the validators already there. Right now there's one. So that one would have to vote you in.",
      "Can I ask?",
      "You can ask the people who run it, politely. Until then, your node checking every block is useful too.",
      "Okay. Patience. Thanks, Rico."] },
    { who: "rudy", say: ["Rudy again. I tried to send twenty million coins in one go, just to see. Refused.",
      "Rudy, where did you get twenty million coins?",
      "I didn't. I wanted to see what happens.",
      "Good tester. Then two things happened. You don't have them, and one transfer can't be that big anyway. The rules count amounts in twenty-four bits. The top is just under seventeen million.",
      "Twenty-four bits. That's oddly specific.",
      "The lagoon is very specific, Rudy. That's its charm.",
      "Ha. Okay. Night, Rico."] },
    { who: "sam", say: ["Rico. Sam. Can't sleep. I keep thinking: who reads the Book when I'm gone?",
      "Everyone, Sam. That's the point of the Book. Anyone can open it.",
      "But nobody does.",
      "Some do. A few every night. And the ones who don't still know they could. That changes how people behave.",
      "Hm. So the Book doesn't need me.",
      "The Book doesn't. The island does. Go to bed, Sam.",
      "Goodnight, Rico. Mind the lamp."] },
    { who: "kiko", say: ["Rico, it's Kiko at the canoes. I keep thinking about Agorzilla. Out there alone in the jungle, every night.",
      "Is that what's keeping you up, Kiko?",
      "He grows when the island votes. But nobody visits him.",
      "Kiko, the whole island talks about him. The bananas, the footprints. Nobody is talked about more.",
      "That's not the same as a visit.",
      "No, it isn't. Leave him a banana on the path tomorrow. A real one, not a rumour.",
      "I'll leave two. Goodnight, Rico."] },
    { who: "pearl", say: ["Rico, Pearl. I'm new here. I made a wallet, sent some coins around, but I don't know anybody.",
      "That happens on a new island, Pearl. The chain sees wallets, not people. People you have to find yourself.",
      "Where?",
      "Where people talk about the lagoon. The builders write in public, and there are groups where people ask exactly what you're asking. And on this island: La Ola, on a Friday.",
      "And if I ask something stupid?",
      "Pearl, people call Rico at midnight about napkins. Nothing you ask is stupid.",
      "Ha. Okay. Thanks, Rico."] },
  ];
  /* what the islanders say in the places (the same English as in game.js, which the tests check) */
  const LAWT = { harbour: "A deep harbour for cruise ships", road: "A road round the island" };
  const EMBV = { frost: ["harbour", 40], salado: ["road", 35,   // the resort's own words, word for word as game.js EMB.south (test_rico.py checks), the North Wind keeps the diplomat's
    "Sit, sit, the lounger is free. So, straight to business: {n} coins, today, and you propose “{x}” before the election. Right now my guests drag their suitcases uphill from the pier, and last week a yoga teacher cried.",
    "My investors call me every morning at six and ask the same thing: has our candidate proposed “{x}” yet? Please. Give me something to tell them.",
    "No business today, my friend: “{x}” is law already, and there’s nothing left for me to buy. My investors will think I’m on holiday. Sit anyway, the loungers are free."] };
  const CAST = [
    ["hana", "Pick a law. The other three candidates vote; two yes and it is law. The Book checks it against the laws in force first."],
    ["sam", "So it is true, Marisol: your name is on the list, in my own hand. Four candidates, one governor’s chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. You hear everything first at your café. This week the island hears about you. Every move you make goes into this Book."],   // the first scene of a campaign: game.js WELCOME.marisol
    ["sam", "So it is true, Tobias: the harbour master wants to be governor. Your name is on the list, in my own hand. Four candidates, one chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. The embassies know you already. The island will know you by what goes into this Book."],   // the first scene of a campaign: game.js WELCOME.tobias
    ["sam", "So it is true, Baako: your name is on the list, in my own hand. You count everything, so count this: four candidates, one governor’s chair under the council tree, ten islanders who vote on Sunday night. Every move you make goes into this Book, and I count too."],   // the first scene of a campaign: game.js WELCOME.baako
    ["sam", "So it is true, Hana: your name is on the list, in my own hand. Four candidates, one governor’s chair under the council tree, and on Sunday night the ten islanders who vote choose who sits in it. You write everything down, so you know how this works. Laws are made in the Council Hall. Everything else is written here."],   // the first scene of a campaign: game.js WELCOME.hana
    ["sam", "Sam keeps the minutes today. Pick a law; the other three candidates vote, two yes and it is law."],
    ["lola", "Everyone passes through here. Talk about what people care about; it counts double if you already passed a law for it."],
    ["rico", "Twenty-five coins and I play anything, baby. I don’t check, I just spin. But the Book writes down who paid me, every time."],
    ["lola", "A pact means you vote for each other’s laws. Break one and the whole island knows by breakfast. Lemonade’s on the house."],
    ["sam", "Every move on the island is written here with the name of whoever made it. Nobody can tear out a page, not even me. Reading costs nothing."],
    ["sam", "Empty, for now. Every move on the island will be written here, with the name of whoever made it. Nobody can tear out a page."],
    ["sam", "Boats, gulls and a black cat that sometimes walks past twice. Nothing to do here but think. Tau Testnet Alpha is out there too: the Book on this island works a lot like its blocks."],
    ["sam", "Every move you make goes to the testnet as a transaction from your test wallet: 1 test AGRS to the place’s jar, signed in this browser. Here is each one, with the chain’s answer."],   // the chain strip: game.js "Your moves on Tau Testnet Alpha"
    ["sam", "Three moves a day, six on your first day, seven days from Monday to Sunday, then the island votes. Each of the ten islanders cares about two things; laws and talk about those win them over. Rumours work for a day, until people read the Book."],
    ["sam", "The island’s numbers are out of reach just now. Your campaign goes on as before."],
    ["sam", "The players here are test wallets, not people. A move counts for a wallet when that wallet signed it into the testnet from the same connection. Each week counts a wallet’s first finished campaign; the result is what its game reports."],
    ["marisol", "Nobody owns her, and nobody feeds her alone: she eats on a day only when three wallets agree, one test AGRS each. Say yes and you are one of the three. The other two? Whoever passes through."],
    ["sam", "Two laws that cannot both hold would leave the island not knowing what is allowed, so the Book will not take it. Repeal the old one first, or pick another law."],
    ["rico", "Done, it’s out there. Half the island is talking. The other half will read the Book tomorrow, and the Book says you paid me."],
    ["rico", "Done. And this one’s true, so let them check. The Book backs you up."],
    ["rico", "This just in on Radio Coco, ninety-seven point three!"],
    ...NAMES.map(n => n.toLowerCase()).flatMap(c => [[c, "Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory."], [c, "After what you did? Buy yourself a lemonade."], [c, "Not today. Show me how you vote first."]]),
    ...Object.entries(EMBV).flatMap(([who, [law, n, offer, remind, done]]) => { const f = t => t.replace("{n}", n).replace("{x}", LAWT[law]);
      return [[who, f(remind || "We are counting on you for “{x}”. We would hate to remind the island in public.")], [who, f(offer || "{n} coins, today. All we ask is that you propose “{x}” before the election. A small thing between friends.")],
        [who, f(done || "“{x}” is law already, so we have nothing to ask of you today. An unusual feeling. We do not care for it.")]]; }),   // done: what they pay for is law already
  ];
  /* what Rico can put on air: the four rumours that are not true, and the true things the Book has seen */
  const LIES = ["Marisol fishes inside the reef at night", "Tobias wants to sell the lighthouse", "Baako’s coconuts are imported", "Hana wants school on Sundays"];
  const EMBN = { "North Wind Embassy": 40, "South Current Wellness Resort": 35 };
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
      else if (NUMERIC[k]) BANDS[NUMERIC[k]].forEach(n => out.push(fill(s, { n, ...BLOCK })));
      else if (VARIANTS[k]) VARIANTS[k].forEach(v => out.push(fill(s, v)));
      else if (s.includes("{")) out.push(fill(s, BLOCK));
      else out.push(s);
    }
    return [...out.map(t => ["rico", t]), ...CAST, ...CALLS.flatMap(c => c.say.map((t, i) => [i % 2 ? "rico" : c.who, t])), ...NIGHT.flatMap(c => c.say.map((t, i) => [i % 2 ? "rico" : c.who, t])), ...(window.RABBIT_TALK_LINES ? window.RABBIT_TALK_LINES() : [])];   // talk.js: coming back, asking more
  }

  /* the clips the server has made so far */
  let have = null, tried = 0;
  /* the list is asked for again when it came back empty (the server was restarting, e.g. during an update), at most twice a minute */
  const list = () => (tried = Date.now(), fetch(BASE + "index.json", { cache: "no-cache" }).then(r => (r.ok ? r.json() : null))
    .then(j => { have = new Set((j && j.clips) || []); }, () => { have = new Set(); }).then(learn));
  let ready = null;
  async function key(who, s) {
    const d = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(who + "|" + s));
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }
  /* which radio lines have their clips already (Rico's L keys, and the calls whose every line is spoken): game.js
     prefers those, so the radio keeps talking while new lines still wait for their voices */
  const VOICED = { l: null, c: null, n: null };
  async function learn() {
    if (!have || !have.size || !window.crypto || !crypto.subtle) return;
    const l = new Set(), c = new Set();
    for (const [k, t] of Object.entries(L)) {
      if (!t.includes("{")) { if (have.has(await key("rico", t))) l.add(k); }
      else if (NUMERIC[k] && (await Promise.all(BANDS[NUMERIC[k]].map(n => key("rico", fill(t, { n, ...BLOCK }))))).every(x => have.has(x))) l.add(k);   // a band line: every band's clip
    }
    for (let i = 0; i < CALLS.length; i++) {
      const x = CALLS[i], ks = await Promise.all(x.say.map((t, j) => key(j % 2 ? "rico" : x.who, t)));
      if (ks.every(k => have.has(k))) c.add(i);
    }
    const n = new Set();
    for (let i = 0; i < NIGHT.length; i++) {
      const x = NIGHT[i], ks = await Promise.all(x.say.map((t, j) => key(j % 2 ? "rico" : x.who, t)));
      if (ks.every(k => have.has(k))) n.add(i);
    }
    VOICED.l = l; VOICED.c = c; VOICED.n = n;
  }
  ready = list();
  const again = () => { if (have && !have.size && Date.now() - tried > 30000) ready = list(); return ready; };
  /* true or false once known; null while the clip list is still loading (or a line with a name in it; a line with a
     number spoken as a band is known: true once every band has its clip) */
  const voiced = k => { if (!VOICED.l) return null; if (/^call:/.test(k)) return VOICED.c.has(+k.slice(5)); if (/^night:/.test(k)) return VOICED.n.has(+k.slice(6)); return L[k] == null || (L[k].includes("{") && !NUMERIC[k]) ? null : VOICED.l.has(k); };
  const cache = new Map();
  const clip = k => { if (!cache.has(k)) cache.set(k, fetch(BASE + k + ".mp3").then(r => (r.ok ? r.arrayBuffer() : null), () => null)); return cache.get(k); };
  /* speak a line in someone's voice: all its spoken parts, in order, or nothing at all when one clip is missing */
  const why = { last: "" };
  async function speak(parts, who = "rico", o = {}) {
    const SND = window.COVE_SOUND;
    if (!SND || !SND.on || !SND.speak) { why.last = "sound not on (" + (SND ? SND.state : "no player") + ")"; return false; }
    if (!window.crypto || !crypto.subtle) { why.last = "no crypto.subtle"; return false; }
    await again();
    const said = parts.filter(p => p.v), keys = await Promise.all(said.map(p => key(p.who || who, p.v)));
    if (!keys.length) { why.last = "nothing to say aloud"; return false; }
    if (!have.size) { why.last = "clip list not loaded"; return false; }
    if (!keys.every(k => have.has(k))) { why.last = "clip missing: " + keys.filter(k => !have.has(k)).join(","); return false; }
    /* while the clips are fetched and decoded the mouth stays shut, then it follows the voice (COVE_SOUND.lip) */
    if (SND.expect) SND.expect(who, true);
    let secs;
    try {
      const bufs = await Promise.all(keys.map(clip));
      if (bufs.some(b => !b)) { why.last = "clip download failed"; return false; }
      if (o.still && !o.still()) { why.last = "gone before the clip came"; return false; }   // the card was closed or replaced while the clips loaded
      secs = await SND.speak(bufs.map((b, i) => (said[i].who && said[i].who !== who ? { b: b.slice(0), tel: true, who: said[i].who } : b.slice(0))), Object.assign({ who }, o));   // a caller sounds like a telephone
    } finally { if (SND.expect) SND.expect(who, false); }
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
     lagoon humour, jokes, the listeners' letters, the phone-in (the caller in their own voice) and Tau corner, without the ones about the election. Each is a parts list, shown translated where the page has it. */
  const tr = s => (window.TauI18n ? TauI18n.t(s) : s);
  const hud = () => [...SETS.open, ...SETS.general.filter(k => k !== "g11" && k !== "g14"), ...SETS.joke.filter(k => !["j24", "j25"].includes(k)), ...SETS.call, ...SETS.corner, ...SETS.salado, ...SETS.legend, ...SETS.net, ...SETS.mainland, ...SETS.lagoon, ...SETS.dunno].map(k => [{ t: tr(L[k]), v: L[k] }])
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
  /* between two songs the band stops (music.js onbreak) and Rico says what fits: most often a line on the song that
     just ended and the one coming (BREAK, by the playlist's order), otherwise a word for the listener's hour and the
     next song's name. In the Night Line's hour (NIGHT_AT, or ?nightline=1 to try it) the first break opens the line,
     every break after it is a caller (NIGHT), and the first break after the hour closes it. o.pick chooses one key of a
     list (game.js: the voiced ones he has not said lately); without it, a voiced one he has not said in this browser. */
  const BREAK = { "coco>mango": "A", "mango>lowtide": "B", "lowtide>tinroof": "C", "tinroof>hammock": "D", "hammock>moon": "E", "moon>coco": "F" };
  const NIGHT_AT = 23;
  const QS = typeof location !== "undefined" && location.search ? new URLSearchParams(location.search) : null;
  /* one-off extra hours (UTC), e.g. Kilian's first listen on 4 Nov 01:45-02:45 German time; the openers and closers that
     name eleven o'clock or midnight are skipped then */
  const EXTRA = [[Date.UTC(2026, 10, 4, 0, 45), Date.UTC(2026, 10, 4, 1, 45)]];
  const extra = () => EXTRA.some(([a, b]) => Date.now() >= a && Date.now() < b);
  const night = (hr = new Date().getHours()) => (QS && QS.get("nightline") === "1") || hr === NIGHT_AT || extra();
  const NL = { open: false };
  const BRK_SAID = "rabbit-radio-breaks";
  const brkSaid = () => { try { const a = JSON.parse(localStorage.getItem(BRK_SAID) || "[]"); return Array.isArray(a) ? a : []; } catch (e) { return []; } };
  function pickOwn(keys) {
    const v = keys.filter(k => voiced(k) !== false), from = v.length ? v : keys, said = brkSaid(), fresh = from.filter(k => !said.includes(k));
    const k = fresh.length ? fresh[Math.floor(Math.random() * fresh.length)] : from.slice().sort((a, b) => said.indexOf(a) - said.indexOf(b))[0];
    try { localStorage.setItem(BRK_SAID, JSON.stringify(said.filter(x => x !== k).concat(k).slice(-80))); } catch (e) {}
    return k;
  }
  /* the chain weather by sender: n = the relay's counts for the last blocks (/api/v1/sources/recent). Only when every
     transaction there comes from a sender we know: then the set that says who (one source with 80 % or more, else
     "home traffic") and, for Tau HUD's wallet, the page most of them came from. Any unknown sender: null, the usual weather. */
  function wxSource(n) {
    if (!n || typeof n !== "object") return null;
    const g = { wxHouse: 0, wxIsle: 0, wxShip: 0, wxJungle: 0, wxHud: 0 }, via = {};
    let tot = 0;
    for (const [k, c0] of Object.entries(n)) {
      const c = Number(c0) || 0; if (c <= 0) continue; tot += c;
      if (k === "other") return null;
      const set = k === "idni" ? "wxHouse" : k === "rabbit" || k === "bot" ? "wxIsle" : k === "cruise" ? "wxShip" : k === "agorzilla" || k === "deja" ? "wxJungle" : k.startsWith("tauhud") ? "wxHud" : null;
      if (!set) return null;
      g[set] += c;
      if (set === "wxHud") { const p = k.split(":")[1] || "hud"; via[p] = (via[p] || 0) + c; }
    }
    if (!tot) return null;
    const [top, c] = Object.entries(g).sort((a, b) => b[1] - a[1])[0];
    const page = Object.entries(via).sort((a, b) => b[1] - a[1])[0];
    return { set: c / tot >= 0.8 ? top : "wxHome", page: top === "wxHud" && c / tot >= 0.8 && page ? page[0] : null, n: tot };
  }
  function brk(from, to, o = {}) {
    const pick = o.pick || pickOwn, hr = o.hr != null ? o.hr : new Date().getHours(), line = k => ({ t: tr(L[k]), v: L[k] });
    if (night(hr)) {
      if (!NL.open) { NL.open = true; NL.extra = extra() && hr !== NIGHT_AT; const k = pick(NL.extra ? ["nlo2"] : SETS.nlOpen); return { k, parts: [line(k)] }; }
      const k = pick(NIGHT.map((c, i) => "night:" + i)), ring = pick(SETS.nlRing), bye = pick(SETS.nlBye);
      return { k, also: [ring, bye], parts: call(NIGHT[+k.slice(6)], ring, bye), call: true };
    }
    if (NL.open) { NL.open = false; if (!NL.extra) { const k = pick(SETS.nlClose); return { k, parts: [line(k)] }; } }
    const x = BREAK[from + ">" + to], pair = x ? Object.keys(L).filter(k => k.startsWith("sb" + x)) : [];
    if (pair.length && Math.random() < 0.65) { const k = pick(pair); return { k, parts: [line(k)] }; }
    if (Math.random() < 0.12) { const k = pick(SETS.salado); return { k, parts: [line(k), ...(L["nx_" + to] ? [line("nx_" + to)] : [])] }; }   // the wellness investor, now and then
    const set = Math.random() < 0.25 ? "sbAny" : hr >= 5 && hr < 11 ? "sbAm" : hr >= 11 && hr < 17 ? "sbPm" : hr >= 17 && hr < 22 ? "sbEv" : "sbNt", k = pick(SETS[set]);
    return { k, parts: [line(k), ...(L["nx_" + to] ? [line("nx_" + to)] : [])] };
  }
  window.RICO = { L, SETS, CAST, CALLS, NIGHT, brk, night, wxSource, NAMES, BANDS, NUMERIC, BLOCK, all, speak, fill, key, hud, call, wake, voiced, check, stop: () => { if (EL && !EL.paused) { EL.onended = null; EL.pause(); } }, get why() { return why.last; } };
})();
