/* What the islanders say when you come back, and what they answer when you ask them something (White Rabbit Key).
   window.RABBIT_TALK[who] = { back: [[when, line], ...], ask: [{ q, a: [[when, line], ...], more: { q, a } }, ...] }
   back: said instead of their first line once you have heard that; the first one whose "when" holds and that you have
   not heard yet wins, then they take turns. ask: questions you can put to them for free (no move, nothing in the Book);
   "more" is the deeper question that opens once the first one is answered. "when" is one of the facts game.js knows
   ("" always, early, mid, last, myLaw, noLaw, pact, broke, deal, lied, caught, truth, smeared, lead, poor, chart, key,
   drummed, circled, dove, worked, plans, rich, amb, ambFortune, ambReform, ambKingmaker, ambClean, roof, lamp, stoneSet, and every law id in force: night quiet reef harbour boat lunch concerts road copy tax;
   your dealings with an embassy: southOffer southDeal southOwed southKept, northOffer northDeal northOwed northKept; what has happened to the island: eventBoiler eventStorm eventCoup eventCatch eventRoof;
   the cruise ships, RABBIT_SHIP_WHEN at the end: ship, queen, dryrun, shipSoon shipTomorrow shipToday shipNear, shipHere, shipGone shipCut shipAfter).
   "a+b" holds when both hold, "!a" when a does not, so "last+southOwed+!road" is the last day, the resort's money taken and no road yet.
   A question with a "when" of its own is offered only while that holds (the cruise ships: "ship").
   Every line is spoken in that islander's voice (infra/rico/make.py, through rico.js all() and rabbit/voices.json),
   so a line never holds a number, a name of the player or anything else that changes. */
(() => {
  "use strict";
  window.RABBIT_TALK = {
    ama: {
      back: [
        ["pirateSight", "Black sails off the reef. Nobody told the council. Nobody tells the council anything, but usually they at least send a letter."],
        ["pirateHere", "Pirates. They stay on their boat, which is the first polite thing pirates have ever done. The tree stays where it is."],
        ["pirateAfter", "The pirates came and went. They tried their tricks on the chain, not on the island, and the chain answered. That is what a good elder does too."],
        ["pirateHere+tGovernance", "A pirate hid a change to the rules inside a payment for rum. Rules are not changed in a bottle. Here they change when the island agrees, and on the chain the same. Refused."],
        ["pirateClean", "Every trick the pirates tried, the chain refused, and each time it said why. When I was young, a no came without a reason. This chain explains itself. I approve."],
        ["pirateNext", "The children played pirates all morning. One was the pirate, the others were the chain. The chain won every round. Nobody wanted to be the pirate twice."],
        ["shipNear", "A ship is on its way, I hear. Visitors are welcome under this tree. Groups are a different animal. A visitor sits down. A group takes pictures of people sitting down."],
        ["shipHere", "The ship is in. The tree is not on the tour, and the tour is not on the tree. We agreed that in council. It may be the only thing we agreed on all year."],
        ["last", "The last day. Suddenly everyone is very polite to me. It happens every election, like the rains."],
        ["broke", "You broke a pact. I am not angry. The Book is not angry either. It simply remembers, which is worse."],
        ["harbour", "The deep harbour is law now. Laws arrive quickly. What they do to the reef comes on the slow boat."],
        ["myLaw", "One of your laws stands. Good. A law is easy to pass and hard to live with. We will see which kind yours is."],
        ["early", "Sit, if you like. Young candidates stand. Old ones have learned that a vote takes as long as it takes."],
        ["", "The council is quiet today. Either the island is at peace, or everyone is at Lola’s. Usually it is Lola’s."],
        ["", "Back again. This tree has seen more elections than anyone. It never voted once, and it is still the most respected thing on the island."],
      ],
      ask: [
        { when: "ship", q: "Why is the council tree closed to the tour groups?", a: [["", "Anyone may come and listen, and that holds for a passenger too. But forty people at once do not listen. They look. A council that is looked at starts to perform. We prefer to argue."]],
          more: { q: "Do you mind the ships, then?", a: [["", "No. This island has always had visitors. Some came to trade, some to stay, some to tell us how to live. The ship stays ninety minutes. That is the most polite kind."]] } },
        { q: "Why does the council meet under a tree?", a: [["", "Because a roof can be locked and a tree cannot. Anyone may come and listen. Most come for the shade and stay for the arguments."]],
          more: { q: "And when nobody agrees?", a: [["", "Then nothing changes, and that is allowed. People think a council is there to decide. It is there so that nobody decides alone."]] } },
        { q: "Who really runs this island?", a: [["deal", "You took an envelope, so you may think the embassies do. They pay for promises. Promises are cheap. Two votes out of three are not."], ["", "Nobody, and that is the point. There is no chief with a master key. What we agreed is on the stone and in the Book, and anyone can read both."]],
          more: { q: "Not even you?", a: [["", "Especially not me. I am old. I forget where I put my glasses. Imagine if the rules depended on where I put them."]] } },
        { q: "Have you ever seen Agorzilla?", a: [["harbour", "Since the harbour passed, the footprints come down to the beach at night. I am not saying he is upset. I am saying he paces."], ["", "My grandmother said he grows the way the island votes. So when people ask me what he looks like, I tell them: look at what you voted for."]] },
      ],
    },
    marisol: {
      back: [
        ["pirateSight", "Black sails! Every fisherman on the square is whispering. In ten minutes this is the rumour of the year. In twenty, there are three versions."],
        ["pirateHere+tImpostor", "One of the pirates wore a false moustache and paid from another pirate’s wallet. The chain checked the signature, not the moustache. Refused. I’m telling everyone."],
        ["pirateHere", "The pirates buy from the market by rope and basket. Nobody goes near the boat. Everybody watches it. That’s the café’s whole evening."],
        ["pirateAfter", "Everyone at the café has a pirate story now. Half of them weren’t there. The logbook was, so I believe the logbook."],
        ["pirateHere+tOverspend", "A pirate just tried to pay more than his wallet holds. The chain looked at his balance and said no. At the café we call that the Tuesday tab. Nobody gets one here either."],
        ["pirateClean", "The logbook is out: every pirate trick refused, each one with the chain’s own reason next to it. Three versions of the story at the café, and for once they all end the same way."],
        ["pirateNext", "The day after the pirates and the café is still full. Half the island swears a pirate winked at them. The logbook doesn’t record winks. Only payments."],
        ["shipNear+queen", "The Queen Mempool is coming. A hundred and twenty coffees, a hundred and twenty new rumours. I’ve ordered more cups. The rumours bring their own."],
        ["shipNear+dryrun", "The expedition ship is coming. Forty people who want to know where the coffee grows. I’ve put a little sign on every cup: Baako’s hill. Baako is unbearable already."],
        ["shipHere+queen", "Look at my square! Hats everywhere. They all ask the same three things: is the water clean, is the fish fresh, is the cat for sale. Yes, yes, and Déjà is not for sale."],
        ["shipHere+dryrun", "The expedition people order one coffee each and then ask forty questions. I answer, they write it down. By tonight I’ll be a source in somebody’s travel diary."],
        ["shipGone", "The ship has gone. The square smells of sun cream, and my till is happy. Now, where were we? Ah, yes. Politics."],
        ["ambKingmaker", "Your candidate is still at the bottom. A pact, a few laws, a word on the square. Do you want the story or not?"],
        ["last", "Last day. My feet hurt, my voice is gone, and I still owe three people a coffee. Go on, the square is listening."],
        ["reef", "The reef law passed. The fishermen bought me a coffee for once. I didn’t know they could."],
        ["harbour", "A cruise harbour, then. My nets will catch fewer fish and more flip-flops."],
        ["lied", "I heard the line you bought on Radio Coco. People believed it at breakfast. By lunch they had read the Book."],
        ["mid", "Halfway through the week, and people have started quoting me back to myself. That’s when you find out what you actually said."],
        ["early", "Morning! Everyone’s here. Buying fish, selling gossip, pretending not to listen. Say something they care about."],
        ["", "You again! Good. People trust a face they’ve seen twice. Three times, and they start telling you their problems."],
      ],
      ask: [
        { when: "ship", q: "Are the cruise ships good for the island?", a: [["", "For my till, yes. For my nets, ask me after the harbour vote. Two ships a week anchor outside the reef. A harbour full of them would fish in my bay."]],
          more: { q: "So you’re against the harbour?", a: [["", "I’m for whatever keeps the fish and the coffee drinkers. If you find a law that does both, tell me first. I’ll make it my rumour of the week."]] } },
        { q: "What do people here really want?", a: [["", "Fish on the table, a road that doesn’t eat their tyres, and quiet when the baby sleeps. Nobody gets all three at once. That’s politics."]],
          more: { q: "So how do you win them over?", a: [["", "You listen first. Then you write down what you promised, where they can read it. People forgive a slow law. They don’t forgive a promise that changes."]] } },
        { q: "Why run, with a café to look after?", a: [["", "I heard the same complaints over coffee for ten years. At some point you either put up a complaints box or stand for council. The box was more expensive."]] },
        { q: "Do you trust the other candidates?", a: [["pact", "I trust the ones who shook hands at Lola’s. Not because they’re nice. Because the Book saw the handshake."], ["", "I trust what’s written down. Tobias has a speech for every envelope, Baako has a ledger for every coconut, Hana has a footnote for everyone. I have coffee, and coffee hears things."]] },
        { q: "Do the rumours really start at your café?", a: [["", "Rumours don’t start anywhere. They wander in, sit down and order a coffee. I only help them find the radio. A café has to live on something."]],
          more: { q: "And when they aren’t true?", a: [["", "Then Hana’s class has found out by lunch. Those children check everything. My gossip has never been so honest. Business is worse. The coffee is better."]] } },
      ],
    },
    lola: {
      back: [
        ["pirateSight+dark", "Lanterns on a ship I don’t know. Torches on at the bar, the good rum under the counter. Not hiding it. Pricing it."],
        ["pirateHere+tReplay", "Pirates pay for their rum, would you believe it. One of them tried to pay twice with the same payment. The chain said no before I could."],
        ["pirateHere", "Pirates at my bar, by rope and basket. They pay the same price as everyone, through the same chain. I’ve never had such well-behaved pirates. I’ve never had pirates."],
        ["pirateAfter", "The pirates have gone, and the rum they paid for is paid for. Whatever else they tried, the logbook has the chain’s answer. I’d rather read that than a pirate’s promise."],
        ["pirateHere+tExpired", "A pirate sent me a payment whose time had already run out. Like paying with last week’s bar tab. The chain checked the clock and said no. I didn’t even have to look up."],
        ["pirateClean", "Every trick they tried bounced off the chain. The rum they paid for properly went through the same door as yours. Best-behaved bad customers I’ve ever had."],
        ["pirateNext", "Morning after the pirates. The good rum is back on the shelf, and the bar still smells of lantern oil. Lovely evening. Strict chain."],
        ["shipNear+queen", "The Queen is on her way. A hundred and twenty thirsty people and one bartender. I’ve hidden the good lemons. Pacts first, passengers second."],
        ["shipHere+queen", "A table of eight, one bill. One transaction, and it pays my bar, Rico’s song and the Works’ coconut snacks at once. Nobody argues about who had the extra lemonade. I love these people."],
        ["shipHere+dryrun", "The expedition people order one lemonade and ask where the lemons grow, who witnesses the pacts and why there’s a Book. I told them: the Book, because I forget."],
        ["shipGone+queen", "They’ve gone. The glasses are washed, the bills are in the Book, and somebody left a hat. Captain Wren has labelled it already."],
        ["broke", "Well, look who’s back. The one who broke a pact. Lemonade’s still free. My smile costs extra today."],
        ["pact", "My favourite kind of customer: one with a pact. You keep yours, I keep pouring."],
        ["last", "Last night before the vote. Suddenly everybody loves everybody. I’ve seen this one before. I know how it ends."],
        ["early", "First days of the campaign. Everybody’s friends, nobody’s signed anything yet. My favourite time to listen."],
        ["", "You look thirsty. Or nervous. In election week on this island, it’s usually both."],
        ["", "Back so soon? Sit down. Pacts first, gossip second, lemonade always."],
      ],
      ask: [
        { when: "ship", q: "Do the passengers come in here?", a: [["", "Sooner or later, every one of them. The bar is where people go when they don’t know anybody. On this island, that’s the bar’s whole job."]],
          more: { q: "Do they make pacts too?", a: [["", "Not yet. They only stay ninety minutes. A good pact takes longer than that. So does a good lemonade."]] } },
        { q: "Why are pacts made here, not at the council?", a: [["", "Because the council is where you argue and the bar is where you make up. And I’m a good witness. I don’t take sides, I take orders."]],
          more: { q: "What happens when someone breaks one?", a: [["", "Nothing loud. No shouting, no glasses thrown. It just goes into the Book, and the next time that person holds out a hand, everybody looks at it first."]] } },
        { q: "Who comes in here at night?", a: [["", "Fishermen, surveyors, and one ambassador in a very big hat who thinks nobody recognises him. Everybody does. He tips well, so we pretend."]] },
        { q: "Have you ever seen Agorzilla?", a: [["", "Something took every banana from the crate out back and closed the lid again. Honestly? Best-behaved customer I ever had."]] },
      ],
    },
    rico: {
      back: [
        ["pirateSight", "Pirates, baby! Nobody announced them, nobody booked them, and Rico has no jingle for this. Rico is writing one now."],
        ["pirateAfter", "The pirates are gone, baby. What the chain said to their tricks is in the logbook. Rico read it on air. Twice. Best ratings since the storm."],
        ["pirateHere", "You can see the black ship from my window, baby. Rico waved. The pirates did not wave back. They waved at Lola. Everybody waves at Lola."],
        ["pirateClean", "Every pirate trick refused, baby, and Rico read every refusal on air. The chain’s answers even have names: insufficient funds, invalid signature, fee limit too low. Poetry."],
        ["pirateNext", "Rico still has no pirate jingle, baby. A dozen drafts, and they all rhyme refused with amused. The chain is amused. The pirates, less so."],
        ["shipGone+shipTuned", "The ship wrote in her logbook what she changes for next time, baby, and why. Rico has never once written down why he changed anything. Inspiring."],
        ["shipNear+queen", "The Queen Mempool is coming, baby! Named after the chain’s waiting room, where transactions wait for a block. Rico hopes she doesn’t wait as long."],
        ["shipHere+queen", "Song requests from the Queen, baby! Each one a real transaction on the lagoon. Our relay makes the passengers up, but the coins are signed. Best crowd Rico ever had that doesn’t exist."],
        ["shipHere+dryrun", "The Wednesday ship never visits the studio, baby. Forty people, and not one song request. They want the lighthouse. Rico will survive. Barely."],
        ["shipCut", "The ship didn’t stay, baby. It lands only when the lagoon is calm, and it leaves the moment something goes wrong. The logbook says what. Rico read it. Twice."],
        ["caught", "Oof. They read the Book and found your name under that rumour. Rico warned you. Rico still has your coins."],
        ["lied", "My best customer! The rumour’s still out there, baby. So is the Book. I’d start being extra nice to people."],
        ["truth", "You paid for a true line. Rare! Rico played it again for free, just to hear how the truth sounds on air."],
        ["last", "Last day before the vote! The phones are ringing, the bananas are disappearing, and Rico hasn’t slept. Business is great."],
        ["mid", "Halfway to the vote, baby. The rumours are getting tired and the Book is getting thicker. Rico loves this part."],
        ["", "Welcome back to the studio, baby. Mind the cables. The yellow one is the radio. The green one is Rico’s fan."],
      ],
      ask: [
        { when: "ship", q: "Are the cruise passengers real?", a: [["", "Honest answer, baby: no. Our relay makes them up, and the ship’s card says so. But every coin they pay is a real test transaction in a real block, and anyone can check it."]],
          more: { q: "Then why send real transactions at all?", a: [["", "To see how the lagoon copes with a crowd. Twelve a minute at most, half when it strains, and the ship leaves the moment the chain stumbles. A dry run before the real party. That’s why the Wednesday ship is called what it’s called."]] } },
        { q: "Do you ever check what you play?", a: [["", "Rico plays, the Book checks. That’s the deal on this island. Rico could lie all day, but every coin has a name on it, and the name goes in the Book."]],
          more: { q: "Then why would anyone pay for a lie?", a: [["", "Because a lie runs faster than a page. For about a day. Then people read, and the lie trips over its own name. Rico has seen it a hundred times. Rico still takes the coins."]] } },
        { q: "Could the council switch you off?", a: [["", "Nobody can. There’s no big red button under the council tree. If people stop listening, that’s the off switch. And so far, baby, they listen."]] },
        { q: "What’s the deal with Agorzilla?", a: [["", "Off the record? One night Rico left the window open and came back to the turntable spinning a slow song. Nobody in the studio. One banana peel, folded. Rico respects a fellow music lover."]] },
      ],
    },
    sam: {
      back: [
        ["pirateSight", "A ship I can’t name. The lighthouse saw her first. The Book will see her last: whatever they try, it writes down what the chain said."],
        ["pirateAfter", "The pirates are in the Book now, between a fisherman and the school. The Book does not care who they are. Only who signed, and what the chain took."],
        ["pirateHere+tDouble", "Two pirate payments with the same number, sent together. The Book has one line for every number. The first payment got the line. The second found it taken. Refused."],
        ["pirateHere+tStale", "A pirate payment with a block deadline that had already passed. The chain counts blocks the way I count pages. Past the page, past the deadline. Refused."],
        ["pirateClean", "The pirates’ tricks are not in the Book. The Book keeps only what the chain took. Their rum is in there, though, and the landing fee. Even pirates leave a paper trail when they pay properly."],
        ["shipGone+shipClean", "Not one refusal today. Every payment the passengers made, the chain took, and the Book has them all. Dull for the radio. Beautiful for the Book."],
        ["shipTomorrow", "A ship tomorrow. Every coin the passengers pay will go in the Book, like everyone else’s. The Book doesn’t care who sailed in. Only who signed."],
        ["shipHere+dryrun", "Forty strangers climbed my stairs today. They read the Book with their noses very close. One asked if she could add a line. I said: only with a coin, like everyone. She paid two."],
        ["shipHere+queen", "The Queen’s passengers come up for the view, not for the Book. A few read it anyway. One of them laughed at my poem. Fair."],
        ["shipGone", "The ship has gone, and the Book is thicker by a ship. Somebody asked me if those passengers were real. I said: the coins are. The Book only ever knew coins."],
        ["lamp", "Your lamp. I read by it now. Half the island reads by it, and the Book has never had so many visitors at night."],
        ["ambClean", "Still clean, as far as I can read. The last days are when most people slip."],
        ["caught", "The Book showed up a rumour this morning. I didn’t do anything. I never do. I just turn the pages, and the pages do the rest."],
        ["copy", "There’s a copy of the Book on the square now. Half my visitors are gone. I have never been happier."],
        ["last", "Last day. People come in to read who have never read before. Elections are good for reading."],
        ["early", "The first days are always thin. A few lines, a few promises. By the end of the week the Book will be heavy with them."],
        ["", "Sit, sit. I was just reading yesterday again. It hasn’t changed. That’s the nice thing about it."],
        ["", "Come in, come in. I’ve just dusted the Book. Not that it needs it. Nothing in it ever changes. It only grows."],
      ],
      ask: [
        { when: "ship", q: "Do the passengers end up in the Book too?", a: [["", "Every coin they pay, with the hour and the wallet, like yours. The passengers are invented, Rico says. But each one has a wallet, and every coin is signed. The Book believes the signature. About the hats it keeps an open mind."]],
          more: { q: "Doesn’t that bother you?", a: [["", "Out there they count wallets, not people. One person can hold many wallets, and one relay can hold a hundred and sixty. The Book never claimed to know who stands behind a signature. Only that it was signed."]] } },
        { q: "Have you ever wanted to tear out a page?", a: [["", "Once. A very bad poem, written by me, when I was young. It’s still in there. Everyone has read it. That is the price of a record nobody can edit."]],
          more: { q: "Why not make just one exception?", a: [["", "Because the first exception is a key, and somebody will want to borrow it. A Book that one person can change is only a diary with ambitions."]] } },
        { q: "What do people look up most?", a: [["", "Who paid for what. Then who voted how. Then, every single time, whether Marisol really fishes inside the reef. She doesn’t. They check anyway. Checking is the whole idea."]] },
        { q: "Is the Book like Tau Testnet Alpha?", a: [["", "In a way. Out there every block points back to the one before, so nobody can slip a page into the middle. And out there they count wallets, not people. One person can hold many wallets. The Book only knows names."]] },
      ],
    },
    tobias: {
      back: [
        ["pirateSight", "A ship! Not on my timetable! No flag I know, no answer to my horn. I’m putting on the uniform. Both uniforms."],
        ["pirateHere+dark", "They anchored in the dark and stayed aboard. No tenders, no welcome, no speech. My speech is still in my pocket. It’s a very good speech."],
        ["pirateHere", "Pirates at anchor, and not one of them came to the pier. I rang the bell anyway. They waved. I think they waved."],
        ["pirateAfter", "Gone, without a word. I’ve added a page to the harbour book: ships that do not announce themselves. It’s a short page. One name."],
        ["pirateHere", "The pirates paid the landing fee at the pier. For a landing! They never land! I have been paid for nothing. I don’t know what to do with my hands."],
        ["pirateClean", "The harbour book, pirate page: arrived unannounced, paid the landing fee, never landed, every trick refused, left on time. The best-documented pirates on any sea."],
        ["pirateNext", "I sat on the pier all morning with the telescope. No black sails. She won’t write ahead, so I will watch every evening. Every evening. The uniform stays ready."],
        ["shipSoon+queen", "The Queen Mempool, on Saturday! A hundred and twenty passengers. I have started on the welcome speech. So far it welcomes them for eleven minutes, and they have not yet left the boat."],
        ["shipTomorrow+queen", "Tomorrow at two, the Queen! I have polished the bell, the medal and the pier. The pier objected. It is a very old pier."],
        ["shipToday", "She comes today! I have been on this pier since dawn, in full uniform. The gulls think I am a statue. Let them. Statues get flowers."],
        ["shipHere+queen", "Look at them coming up the steps! I gave the speech. The first boat heard all of it. The second heard the end. The third pretended to."],
        ["shipGone+queen", "She has sailed, and they waved! Well, some waved. Some were taking pictures of Lola. I am counting it as waving."],
        ["shipSoon+dryrun", "MS Dry Run, on Wednesday. Forty passengers, all of them with notebooks. I am preparing a shorter speech. Short for me, you understand."],
        ["shipTomorrow+dryrun", "The expedition ship comes tomorrow. Curious people. Curious people ask questions after a speech. I must prepare answers. This is new for me."],
        ["shipHere+dryrun", "The expedition people asked me what a harbour master does. I told them. All of it. They took notes! Nobody has ever taken notes."],
        ["shipCut", "She left before her time. Something on the lagoon was not right, Rico says, and the logbook says exactly what. My speech will keep. Speeches keep very well."],
        ["ambFortune", "How is the jar? The hill does not get cheaper, and the election does not wait."],
        ["harbour", "The deep harbour is law! I have already written the opening speech. It runs to forty minutes. The ships will have to wait."],
        ["reef", "No big ships in the bay. Very well. I shall welcome the small ones with twice the ceremony."],
        ["concerts", "Beach concerts on Sundays! At last the island has a stage worthy of my announcements."],
        ["last", "The final day! Tomorrow, the count. I have polished my medal, my cap and my modesty. Mostly the medal."],
        ["mid", "Halfway through the campaign. I have given eleven speeches. The gulls have heard every one of them. The gulls are not voting."],
        ["", "Ah, a visitor to my pier! Every boat that ties up here is greeted by me, personally, with a short speech. Short for me."],
      ],
      ask: [
        { when: "ship", q: "Are you looking forward to the ships?", a: [["", "Looking forward? I have rehearsed all week. Visitors clap, my friend. Islanders nod. A man needs both."]],
          more: { q: "And if they don’t clap?", a: [["", "Then I bow anyway. A bow is never wasted. The gulls have seen hundreds."]] } },
        { q: "What does a harbour master actually do?", a: [["", "I write down every boat that comes and goes, with the hour. Rather like Sam with his Book, only with more salt and more dignity."]],
          more: { q: "And if someone lies about their boat?", a: [["", "Then the next harbour’s list says otherwise, and the two lists have a little chat. Lies hate company. Put two honest records side by side, and the fibber has nowhere to anchor."]] } },
        { q: "Why do you want visitors so much?", a: [["", "Visitors clap. The island stopped clapping for me years ago. Also they pay for the music, and music is the only thing on this island louder than me."]] },
        { q: "Is it true you have a theory about everyone?", a: [["", "Slander! Well, yes. Kai is secretly a fish. Pim measures his own shadow at night. And Agorzilla is a council member in a very good costume. I have no proof. Proof is for the Book. I do theories."]] },
        { q: "Do you take money from the embassies?", a: [["", "Take? I receive. With a brass band, a ribbon and a short speech. What they paid me for goes in the Book, like every promise on this island. You may read it. Bring a chair."]],
          more: { q: "Doesn’t the money buy your vote?", a: [["", "It buys a ceremony. The law still needs the council’s yes, and the council cannot be bought with a ribbon. I tried. Hana sent the ribbon back with corrections."]] } },
      ],
    },
    hana: {
      back: [
        ["pirateSight", "A dark ship, unannounced? Children, inside, please. Not because of the pirates. Because we are going to watch them properly."],
        ["pirateHere", "We are watching from the window. Every time a pirate tries a trick, the class writes down what the chain answered. The children call it pirate bingo. I call it checking."],
        ["pirateAfter", "Homework: find the pirates’ tricks in the logbook and write down the chain’s answer to each one. Then explain why the chain had to say no. In whole sentences."],
        ["pirateHere+tForged", "A pirate signed a payment with another pirate’s key. The class asked how the chain knew. A signature has to match the wallet that pays. This one didn’t. Lesson over, everyone back to the window."],
        ["pirateClean", "Pirate bingo results: every trick on the card, refused by the chain, each with its own answer. The whole class got a full card. I have never given so many gold stars to a blockchain."],
        ["shipGone+shipSkipped", "The class found something in the logbook: the ship planned more stops than she made. Our node took its time answering, and she sends one at a time. A late stop is skipped, not forced. Good manners, for a ship."],
        ["shipNear+dryrun", "The expedition ship always visits the school. The children are preparing questions for the passengers. Hard ones. I have seen the list."],
        ["shipHere+dryrun", "Forty passengers in my back row. The children asked them: who said it, and where is it written? Two of them had to go and look it up. A very good afternoon."],
        ["shipGone+dryrun", "They have gone. Before the break the children counted the ship’s transactions in the blocks. Every one matched the logbook. Then they counted again, to be sure. Then it was break."],
        ["shipHere+queen", "The Queen’s passengers don’t come up to the school. So the children went down to the pier to count them, with a list. Everyone says a hundred and twenty. They want to check."],
        ["roof", "The roof you paid for still holds. When it rains the children look up and say your name, which is more than most governors get."],
        ["ambReform", "The blackboard still has room. Laws, not speeches."],
        ["boat", "The school boat runs every morning now. Attendance is up, and so is seasickness. I write down both."],
        ["lunch", "Fresh fish for lunch. The children are delighted. The cat outside the window is more delighted."],
        ["smeared", "The children heard a rumour on Radio Coco. They checked the Book before break. It was a short break."],
        ["last", "Last day before the vote. I have marked every promise anyone made this week. Some of you will not like your marks."],
        ["early", "Good morning. The children are copying out every candidate’s promises, neatly, so they can compare them at the end of the week."],
        ["", "Welcome back. Sit at the back, please. The front row is for people who did their homework."],
      ],
      ask: [
        { when: "pirates", q: "What are the pirates trying?", a: [["", "Paying more than they hold, sending the same payment twice, a payment whose time ran out, a signature from somebody else’s key. Each is a rule the chain checks on every payment, yours too. The pirates only check that it checks."]] },
        { when: "pirateAfter", q: "What did the chain answer the pirates?", a: [["", "Each refusal has a name in the logbook. Insufficient funds, when the wallet is too poor. Invalid sequence, for a number already taken. Tx expired, when its time or its block deadline ran out. Invalid signature, for the wrong key. Fee limit too low, for no fee. Tx invalid or tx rejected, when the payment itself breaks the rules: the wrong payer, too big, too many transfers. The class has them all on the wall."]],
          more: { q: "Why does the chain give a reason at all?", a: [["", "So that anyone can see why. A plain no teaches nothing. A no with a reason is a lesson, and the chain gives one with every payment it turns down. Yours too."]] } },
        { when: "ship", q: "What do you think of the cruise ships?", a: [["", "Curious visitors are a gift. Crowds are weather. The Wednesday ship brings questions, the Saturday ship brings hats. I like both, but only one fits in a classroom."]],
          more: { q: "Would you stop the big ships if you won?", a: [["", "No. I would write down what they cost the reef and what they bring the island, side by side, where everyone can read it. Then the island decides. That is the whole lesson, really."]] } },
        { q: "What do the children learn here?", a: [["", "Reading, sums, and checking. I teach them two questions for anything they hear: who said it, and where is it written. It makes them terrible at believing adverts."]],
          more: { q: "Isn’t that a little cold?", a: [["", "No. Trust is warm. Checking only keeps it from being spent on the wrong people. The children still believe in each other. They only check the grown-ups."]] } },
        { q: "Why run for council?", a: [["", "Because a good law is a lesson that keeps teaching after the teacher goes home. A speech stops when the speaker sits down."]] },
        { q: "What do the children say about Agorzilla?", a: [["", "Half the class says he is real, the other half says he is Kiko in a coat. They held a debate. Both sides quoted the same blurry photo. Everyone got a B."]] },
        { q: "Do the children hear the rumours too?", a: [["", "Before anyone. A rumour reaches the playground before it reaches the radio. The children bring them to class like shells from the beach, and we hold each one up to the Book. Most of them are empty."]] },
      ],
    },
    kai: {
      back: [
        ["pirateSight", "Dark ship near the reef, and no mooring request. The sensors have started signing every reading twice. Nervous sensors. Or just thorough."],
        ["pirateHere", "The pirates stay off the reef, which I respect. The turtle has gone deeper anyway. She doesn’t trust a ship without a timetable."],
        ["pirateNext", "The turtle is back in the shallows. She watched the black ship leave and decided the reef is hers again. She is right about that."],
        ["shipGone+shipQuiet", "Some of today’s sends got no answer in time. Not a no, just a long silence. The ship waited, slowed down and carried on. I’d do the same on a dive."],
        ["shipNear+dryrun", "The expedition ship is coming! Divers who read the briefing. The reef will love them. The turtle is already doing her hair."],
        ["shipHere+dryrun", "Divers everywhere, three sensors each, every reading signed. Some booked their dive and can still change their minds: the coins wait until the hour, then the chain pays us by itself."],
        ["shipGone+dryrun", "They’ve gone. The sensors signed the water before they came and after they left. Same water. That’s the best review a reef can get."],
        ["shipHere+queen", "The big one anchors outside the reef. Good. Her anchor alone weighs more than my boat. A few of her people come diving. Most come for a photo of the people diving."],
        ["harbour", "Since the harbour law, the readings look sad. The sensors don’t do politics. They just sign what they see."],
        ["dove", "Our dive is in the Book! Signed, sealed, slightly salty."],
        ["reef", "Big ships out of the bay, and the parrotfish are back. The sensors signed it, I signed it. The parrotfish didn’t, but you could tell."],
        ["", "Perfect visibility today. You can see the sand, the fish, and three sensors arguing with a turtle."],
        ["", "Hey, back for more? The reef is open. The coffee machine is not. Priorities."],
      ],
      ask: [
        { when: "ship", q: "Are the ships bad for the reef?", a: [["", "Two ships a week, anchored outside, are fine. The sensors say so, and they sign it. A harbour full of them, dredged deep? Ask the parrotfish. Better, ask the sensors. They’re more precise."]] },
        { q: "Why sign every reading?", a: [["", "Because the reef can’t talk and people can. Without a signature anyone can say the water is clean. With one, the sensor said it, right then, and nobody can change that later."]],
          more: { q: "Couldn’t someone fake a sensor?", a: [["", "They could try. But every diver carries three sensors, and every reading points back to the one before. To fool us you’d have to fool all three, the same way, at the same moment. The fish would notice first."]] } },
        { q: "What do the embassies want with the bay?", a: [["", "Pim says something deep. A cruise harbour is deep. So is the trench off the north point. I’d love to know which one they mean."]] },
        { q: "Seen anything odd down there?", a: [["", "A piano key, once. Captain Wren labelled it. And big footprints on the shallow shelf at low tide. Something heavy walks there. I’m not saying who. I’m saying it isn’t a crab."]] },
      ],
    },
    baako: {
      back: [
        ["pirateHere+tFreeride", "The pirates ordered coconuts from the boat. One of them sent a payment that allowed no fee at all. The chain didn’t take it. Even pirates pay the ferryman."],
        ["pirateHere", "Pirates ordering coconuts from the boat, one basket at a time. One price on the board, the same for pirates. Noor wanted a pirate price. I said no."],
        ["pirateHere+tPoison", "A pirate sent one payment for a whole row of baskets, Noor, and the last basket cost more than he has. The chain didn’t send the others and keep the last. It sent none. Whole order or no order."],
        ["pirateNext", "The baskets came back, Noor. Empty, and rinsed. Pirates rinse baskets. Nobody believes me."],
        ["shipNear+queen", "The Queen is coming! The co-op has picked extra coconuts. One price on the board, the same for islanders and passengers. Noor wanted a passenger price. I said no. She said fine. She did not say it nicely."],
        ["shipHere+queen", "Coconut snacks on the bar bills! One transaction, and a share comes straight to the Works. The co-op’s book adds it up by itself. I love a sum that does itself."],
        ["shipHere+dryrun", "The expedition people asked how the press works. I showed them the bicycles, the organ and Noor. They were most afraid of Noor."],
        ["shipGone", "The ship has sailed, the jar is heavier, and every coin in it has a name. The co-op counted it twice, out loud. The goats left."],
        ["deal", "Ah, you met the ambassadors! Lovely people. Generous. Just remember: the envelope is quiet, the Book is not."],
        ["road", "A road round the island! My coconuts will travel in style. Some of them have never seen the other side."],
        ["worked", "You worked a shift! You smell exactly right. Like someone who earned something."],
        ["early", "A fine morning! The coconuts are ripe, the co-op’s books balance, and nobody has asked me a hard question yet."],
        ["", "Welcome back, friend! Mind the organ. Did I say that already? I say it to everyone. Twice to Tobias."],
      ],
      ask: [
        { when: "ship", q: "Do the ships help the co-op?", a: [["", "They buy coconuts, so yes. But I tell every farmer: a ship comes twice a week, a neighbour comes every day. Price your coconuts for the neighbour."]] },
        { q: "Why a co-op?", a: [["", "One farmer alone sells at the embassies’ price. Forty farmers together set their own. Every coconut goes into the co-op’s book, and anyone may count them. People do. Loudly."]],
          more: { q: "And the embassy envelopes?", a: [["", "They offered me one. I asked for a receipt. They have not offered again. Try the pier: Tobias gives every envelope a welcome speech."]] } },
        { q: "How does the machine really work?", a: [["", "Three bicycles turn the press, the organ pumps the air, and Noor tells everyone to pedal faster. Nobody understands the organ. It was here before the factory."]] },
        { q: "Is Agorzilla stealing your coconuts?", a: [["", "Never a coconut. Only bananas. A creature with standards. I leave one banana by the gate on Fridays now. Good relations with the neighbours."]] },
      ],
    },
    /* Noor only meets you when you play Baako: she runs the Coconut Works, his co-op brings her the coconuts, and here she is the boss */
    noor: {
      back: [
        ["pirateHere+tGiant", "Pirates, Baako. One of them tried to pay with a sum bigger than a payment can even hold. The chain refused. So did I."],
        ["pirateHere", "Pirates, Baako. They want soap. Of course they want soap. Nobody goes near the boat. The soap goes in a basket."],
        ["pirateClean", "The pirates bought their coconuts properly in the end. One price, their own wallets, a fee allowed. The free-ride trick got them nothing but a refusal. Business as usual."],
        ["shipNear+queen", "The Queen is coming, Baako. Double shift. Soap shaped like little ships. Don’t ask. It sells."],
        ["shipHere", "Passengers at my gate, Baako. They want to see the organ. Nobody sees the organ. They can see the soap."],
        ["deal", "An embassy envelope, Baako? The co-op’s farmers will ask where it went. I only make soap, and even I asked."],
        ["lied", "Rico played something you paid for. My workers heard it on the night shift. Then they read the Book on the day shift."],
        ["worked", "A candidate on bicycle three. Not bad. Your legs are better than your speeches. Don’t tell anyone I said that."],
        ["road", "The road is law. Good. Trucks are coming, and trucks need someone who tells them where to park. That’s me, not the governor."],
        ["last", "Last day. Win or lose, my press starts at six tomorrow, and your coconuts had better be at the gate."],
        ["early", "Morning, candidate. The night shift made rope. Mostly rope. Some of it was supposed to be soap. My fault. I’ll fix it."],
        ["", "Back again? Shifts are short, the pay is honest, and the organ is still off limits. Even for candidates."],
        ["", "You count coconuts, Baako. I count the hours they sit at my gate. Between us, nothing on this island goes uncounted."],
      ],
      ask: [
        { when: "ship", q: "Is the ship good business?", a: [["", "Ninety minutes of business and a week of sweeping sand out of the press. Ask me in a month. I count hours, Baako, not hats."]] },
        { q: "Who really runs the Works?", a: [["", "I do. You bring the coconuts, I turn them into things people pay for. The co-op owns the farms. The machine owns me."]],
          more: { q: "Then why does everyone think it’s me?", a: [["", "Because you talk to everyone and I talk to the organ. Fine by me. Fewer visitors."]] } },
        { q: "Will you vote for me?", a: [["", "I don’t vote, Baako. I’m not one of the ten. But if I did, I’d want to see your laws first. Speeches don’t make soap."]] },
        { q: "Would you work for me if I win?", a: [["", "I’d keep doing what I do, and you’d keep bringing coconuts. A governor isn’t a foreman. Don’t mix them up."]] },
        { q: "Why is the organ off limits?", a: [["", "Last time someone touched it, the machine played a waltz for three days and made nothing but soap. Very nice soap. Nobody needed that much soap."]] },
      ],
    },
    pim: {
      back: [
        ["pirateSight", "I measured her from the cliff. Black hull, three chain links on the flag, not on any list I have. The North Wind wants to know if pirates count as cruise traffic."],
        ["pirateNext", "I measured the horizon all morning. No black hull. I have added a column to my notebook: pirates, yes or no. Today: no. Tomorrow: probably no. Probably."],
        ["shipNear+queen", "The Queen is coming. The North Wind asked me to measure how deep she sits in the water. I did. Then they asked me to measure the bay again. It is still the same size."],
        ["shipHere+queen", "I measured the Queen from the cliff. Two hundred metres and a bit. The embassy wants to know what the bit would cost to dredge. I said: ask the council. They sighed."],
        ["deal", "Ah. You have signed with an embassy. That is not my business. I only measure. Although it was quite a thick envelope."],
        ["reef", "No big ships in the bay. The embassy asked me to measure the bay again. I did. It is still the same size."],
        ["", "I measured the distance to your feet. Sorry. Habit. Two metres and a bit. The bit is the interesting part."],
        ["", "Oh. Hello again. Please don’t step on the string. That string is the coast, officially."],
      ],
      ask: [
        { when: "ship", q: "Why does the embassy care about the ships?", a: [["", "Because they anchor outside. The North Wind says a deep harbour would bring them to the pier. I only measure. Whether the island wants them at the pier is not a measurement. It is a vote."]] },
        { q: "Who are you really working for?", a: [["", "The embassies pay, I measure. What they do with the numbers is between them and the council, and the council votes in public. I find that very relaxing."]],
          more: { q: "And if the council says no?", a: [["", "Then I have very accurate maps of a harbour that will never exist. It happens. My drawer is full of them. Some are quite beautiful."]] } },
        { q: "Why do you look so nervous?", a: [["", "I always look like this. My mother says I was born checking a measurement twice. Here it helps. On this island everything gets checked twice, even me."]] },
        { q: "Have you measured Agorzilla’s footprints?", a: [["", "Forty-two centimetres. Twice. Then the third one was forty-four. Either he is growing, or he walks faster when he is upset. I wrote a report. Nobody has asked for it."]] },
      ],
    },
    wren: {
      back: [
        ["pirateSight+dark", "Lanterns on a black ship, dear, coming round the reef in the dark. I told the passengers there were no pirates. Item four hundred and fifteen: I was wrong."],
        ["pirateSight", "Look at that flag, dear. Three chain links. I told everyone there were no pirates. I may have to relabel something."],
        ["pirateHere", "Pirates, dear. Made up by the relay, like the passengers, but their tricks go to the real chain. I’m cataloguing them from the Old Ship. From a safe distance."],
        ["pirateAfter", "Item four hundred and sixteen, dear: one pirate ship, one evening, and the chain’s answer to their tricks in the logbook. I’ve filed it under maritime history."],
        ["pirateHere+tCram", "A pirate packed more transfers into one payment than one may carry, dear. I tried to count them from the Old Ship. The chain counted faster. Refused. Catalogued under overpacking."],
        ["pirateClean", "Item four hundred and seventeen, dear: every lock the pirates tried, and the chain’s answer to each. Not one opened. Filed under good locks, and slightly disappointed pirates."],
        ["pirateNext", "The black ship has gone, dear, and she never says when she’ll be back. I’ve left a space in the catalogue. Pirates are the only exhibit that books itself."],
        ["shipNear+dryrun", "The expedition ship is coming, dear. They always visit my Old Ship. I’ve labelled the gangway, the rail and the bucket. The bucket was nervous."],
        ["shipHere+dryrun", "Item four hundred and thirteen, dear: forty passengers, one sun hat each, all the same hat. Item four hundred and fourteen: a question about pirates. There were no pirates. There was paperwork."],
        ["shipGone+dryrun", "They’ve gone, dear, and one of them left me a postcard. Of my own ship. I’ve labelled it."],
        ["key", "So you found what was behind the waterfall. I knew it, dear. The sea gives things back to the patient ones."],
        ["chart", "Still got my chart, dear? Good. Follow the water, not the path. Paths are made by people in a hurry."],
        ["", "Back already, dear? I’ve just labelled the kettle. It was feeling left out."],
        ["", "Come aboard, dear, and mind the third step. It’s labelled, but nobody reads labels."],
      ],
      ask: [
        { when: "pirates", q: "Are they real pirates?", a: [["", "No, dear. The relay makes them up, like the cruise passengers. Their tricks are real, though: real test transactions that the chain has to refuse. A pirate is only as good as the lock he tries."]],
          more: { q: "Why let pirates try tricks at all?", a: [["", "Better to try every lock while the coins are test coins, dear. A lock nobody ever tries is only a hope."]] } },
        { when: "ship", q: "Do you like the cruise ships?", a: [["", "The small one, very much, dear. Its passengers read the labels. The big one stays out at sea, which suits a liner. Nobody wants a liner reading their labels."]] },
        { q: "What’s the oddest thing the sea gave back?", a: [["", "A ship’s log from a crew who swore they had never been here. The log said otherwise, in their own hand. Records outlive excuses, dear. That’s archaeology in one sentence."]],
          more: { q: "So you trust records more than people?", a: [["", "I trust records about people. People change their minds, which is healthy. Records stop them changing the past, which is healthier."]] } },
        { q: "Why retire on this island?", a: [["", "This island keeps its agreements on a stone and in a Book. I wanted to see how a place lives that remembers everything. Politely, it turns out. Mostly."]] },
        { q: "Do you believe in Agorzilla?", a: [["", "I catalogue things, dear, I don’t believe in them. Item four hundred and twelve: one banana peel, folded, found on my deck. Origin unknown. Manners excellent."]] },
      ],
    },
    kiko: {
      back: [
        ["pirateHere", "A pirate ship out there, lanterns on the water. Small waves. Polite pirates. The canoe stays up the beach anyway."],
        ["pirateNext", "The canoe is back in the water. The pirates are gone, and the waves are the same small waves. Pirates never change the sea. Only the gossip."],
        ["shipHere", "Big ship out there. Big waves. I built the sides higher this morning. The passengers took pictures of my canoe. Nobody asked if it floats."],
        ["shipGone", "Ship’s gone. The waves stay a while. Like gossip."],
        ["harbour", "The harbour law passed. Big ships, big waves. I’m building the sides higher."],
        ["last", "Last day before the vote. Everyone’s in a hurry. The wood doesn’t care."],
        ["early", "Morning. The wood is dry, the sea is calm, and nobody has asked me who I vote for. Yet."],
        ["", "Back again. The canoe is one plank further than yesterday. That’s fast, for a canoe."],
      ],
      ask: [
        { when: "ship", q: "What do you think of the cruise ships?", a: [["", "A big canoe that somebody else paddles. I like the ones I paddle myself."]] },
        { q: "How do you know a canoe is ready?", a: [["", "You put three people in it. If they argue and it still floats, it’s ready."]],
          more: { q: "That sounds like the council.", a: [["", "It is the council. Ama taught me. It isn’t finished when one man says so. It’s finished when it holds everyone."]] } },
        { q: "Where did you see Agorzilla?", a: [["", "Behind the drums, at dusk. Big. Calm. He looked at the canoe like he was checking my work. Then he left. Took a banana. Fair."]] },
        { q: "Who will you vote for?", a: [["", "Whoever cares about fish and music. I tell everyone the same, so nobody has to guess."]] },
      ],
    },
    tano: {
      back: [
        ["pirateHere", "The drums are quiet tonight. Not from fear. When a stranger comes, you listen first. They try their tricks, the chain answers, and we listen."],
        ["pirateClean", "Tonight the drums play the chain’s song: no, and no, and no again. Every trick, and every no with its reason. A good rhythm. Hard to dance to, if you are a pirate."],
        ["shipTomorrow", "A ship tomorrow. The drums won’t play for it. They play for the island. The passengers may listen from the path, like anyone."],
        ["shipHere", "Hear the ship’s horn? The drums don’t answer horns. When it has gone, we’ll play. Not for them. For the quiet after."],
        ["stoneSet", "Your stone sits in the circle. It does not vote. It listens, like you did. That is why it stays."],
        ["drummed", "The drums carried your truth across the hills. The hills don’t usually agree on anything. That evening they did."],
        ["circled", "You sat in the circle and listened. Rare, for a candidate. The others noticed. So did I."],
        ["", "You came back. The drums like that. Most people only come up here when there is bad news."],
        ["", "Welcome back. The drums are resting. A drummer rests between the beats. That’s half the music."],
      ],
      ask: [
        { when: "ship", q: "Why are the drums closed to the tours?", a: [["", "The drums carry what the circle agreed. A tour wants a show. If we played a show, the hills would hear the lie in the rhythm. The hills don’t forgive that."]] },
        { q: "Why can’t anyone bribe a drummer?", a: [["", "Oh, they tried. But every message goes out from three hills, and all three must match what the stone says. You’d have to bribe three drummers and a stone. The stone is very hard to talk to."]],
          more: { q: "And if the three hills disagree?", a: [["", "Then nothing is carried, and everyone comes down to the circle to find out why. Silence is the drums’ way of saying: not yet."]] } },
        { q: "What can the circle decide?", a: [["", "Anything that doesn’t break what we already agreed. Anyone can stand up and show the contradiction. If nobody can, it stands. It’s slow. Slow is how you know it’s real."]] },
        { q: "Are those Agorzilla’s footprints by the drums?", a: [["", "He likes the low drum. Some mornings the skin is warm, as if someone sat close all night, listening. He never plays. He only listens. A better audience than most."]] },
      ],
    },
    frost: {
      ask: [
        { when: "ship", q: "What does the North Wind make of the cruise ships?", a: [["", "Twice a week a ship anchors outside the reef, like a guest left on the doorstep. With a deep harbour she would tie up at the pier. We are not telling you how to vote. We are merely pointing at a very large ship."]],
          more: { q: "And the reef?", a: [["", "The reef has many admirers on this island. We admire it too. From a respectful depth."]] } },
        { q: "What does the North Wind really want?", a: [["", "A deep harbour. We say so openly. It is even in your Book. Ships need depth, and depth needs a vote. Ours is not a secret. It is merely expensive."]],
          more: { q: "And if the island says no?", a: [["", "Then we wait for the next election. The North Wind is patient. Unfortunately, so is your Book. It remembers who promised and did not deliver."]] } },
        { q: "Why not simply build it?", a: [["", "Because there is nobody here who can sign it for us. No chief, no master key, only a council and a Book. Honestly, it is exhausting. Elsewhere one handshake is enough."]] },
      ],
    },
    /* the resort's offer is game.js EMB.south; coming back, he talks about where your deal with him stands */
    salado: {
      back: [
        ["pirateSight", "A ship without a booking! No escrow, no reservation, no towels! I don’t know whether to panic or send a brochure."],
        ["pirateHere", "I sent the pirates a brochure. They didn’t come up. Nobody comes up to a spa from a pirate ship. My investors say that is a gap in the market. It is a gap in the sea."],
        ["pirateAfter", "They never came up to the spa. Pirates. My investors asked if they could be a new market. I said: only if they learn to pay from their own wallets."],
        ["pirateNext", "Still no pirates at the spa. Not one booking. So I made a pirate package: towel, eye patch, rum massage. My investors think it is a joke. It is a business model."],
        ["road+southKept", "You did it, the road is law! I called my investors and for once they had nothing to say. Nothing! I think that means they’re happy. Come, have a smoothie, it’s on the house."],
        ["road+southOwed", "So the road passed. Wonderful. Only somebody else proposed it, and in the Book your name is next to my coins, not next to the road. My investors noticed before I did. About the road I’m happy. About you I’m still thinking."],
        ["road", "The road is law. I keep saying it out loud, just to hear it. My guests will arrive like normal people now, in a minibus with the air conditioning on. Nobody has to cry."],
        ["last+southOwed+!road", "Last day, and I still don’t see “A road round the island” in the Book. You have my coins. If it isn’t there tonight, I have to tell the island before the vote. I hate that part. I really do."],
        ["last+southOffer+!road", "Last day, and we never did business, you and me. I respect that. I don’t like it, but I respect it. If you change your mind before the vote, the coins are right here, and the road still needs somebody."],
        ["shipTomorrow+queen", "Tomorrow at two! I folded a hundred and twenty towels. Then I counted the loungers: eleven. Then I counted the towels again. Optimism is a lot of laundry."],
        ["shipNear+queen", "The Queen is coming! Her passengers book my spa, and the coins wait in escrow until the hour. If they change their minds, the coins go back. My investors hate that part. I love it. It means they trust me."],
        ["shipHere+queen", "They’re here! The loungers are full! I sent a photo to my investors. They asked if it’s edited. It isn’t. Well. The light is."],
        ["shipGone+queen", "They’ve gone. The treatments were paid at their hour, by the chain, all by itself. A few cancelled in time and got their coins back. My investors ask why we let people change their minds. I said: so they come back."],
        ["shipNear+dryrun", "The Wednesday ship doesn’t come up to the spa. Expedition people. They want a reef, not a cucumber on their eyes. I respect it. I don’t understand it, but I respect it."],
        ["shipCut+queen", "She didn’t stay. Something on the lagoon wasn’t right, and the captain doesn’t argue with the lagoon. My cucumbers are sliced. Would you like a cucumber?"],
        ["southKept+!road", "You proposed it, I saw it in the Book. The council said no. Fine, that’s the council. You kept your word, and in my business that happens so rarely I don’t know what to do with my hands."],
        ["northDeal+southOffer+!road", "I hear Frost paid you. That’s okay, he pays more, I know. But he wants a harbour full of cruise ships, and I only want a little road. A road is very quiet, compared to a cruise ship. Think about it."],
        ["poor+southOffer+!road", "Running low, hm? Everybody is by now, campaigns are expensive. You know what I’m going to say, so I won’t say it. I’ll just sit here, next to the coins."],
        ["southOwed+!road", "Ah, my partner! Your name is next to my coins in the Book, so we’re practically family now. The council tree is just down the hill. Propose “A road round the island” whenever you like. Before the election, ideally."],
        ["southOwed+!road", "Did you go to the council tree yet? No? That’s fine. It’s fine. I’ll tell my investors you’re thinking about it. They love that. They love it when people think."],
        ["southOwed+!road", "My investors call me every morning at six and ask the same thing: has our candidate proposed “A road round the island” yet? Please. Give me something to tell them."],   // his reminder (game.js EMB.south), so it is heard too
        ["southOffer+!road", "Ah, you came back! It’s the loungers, everybody comes back for the loungers. Same offer as before: the coins today, and you propose “A road round the island” before the election."],
        ["eventCoup", "About the council tree. That was my investors, not me, I swear on my moustache. I told them you can’t buy a tree on this island. They didn’t listen. Now they’ve met Ama, and they’re very quiet."],
      ],
      ask: [
        { when: "ship", q: "Is the cruise ship good for the resort?", a: [["", "One ship a week, treatments booked, coins in escrow until the hour. That’s not mass tourism, that’s a reservation. I love a reservation."]],
          more: { q: "So you want a cruise harbour too?", a: [["", "No, no. Frost wants a harbour full of ships. I want one ship, and a road up to the spa. Very different. Mine is quieter. And it has towels."]] } },
        { q: "Why do you need a road so badly?", a: [["road", "Needed. Past tense! The road is law now, so now I need guests, which is a much nicer problem. You should see my booking calendar. Actually, don’t. Give it a week."],
            ["!road", "Right now there are two ways up to the resort: the jungle path, or my nephew’s wheelbarrow. The guests write about the wheelbarrow in their reviews. Every single one. With a road, the minibus stops at my gate."]],
          more: { q: "And the people who want quiet nights?", a: [["", "I know, I know. Hana already came up here with a list. But my guests want quiet too, that’s what they pay me for. They just want to arrive at the quiet in a minibus."]] } },
        { q: "Is the resort doing well?", a: [["", "Very well! Eleven rooms, and on a good night almost four of them are full. The pool is beautiful, you should see it with people in it. I saw it once. It was a Tuesday."]],
          more: { q: "Then why do your investors keep paying?", a: [["", "Because I make beautiful slides, and I say “synergy” a lot. They’ve never been here. If they came up the jungle path and saw the empty loungers… So, between us, please don’t invite them."]] } },
        { q: "Do you ever get to relax?", a: [["", "Me? I sell relaxing, I don’t do it. Every morning I join the guests for yoga, and every morning my phone rings in the middle of the tree pose. It’s always the investors. I have never once finished a tree."]] },
        { q: "Have you ever seen Agorzilla?", a: [["", "Something big drinks from my pool at night. In the morning the water is lower and there’s a banana peel on a lounger, folded. Now I leave a towel out for him. Folded too. We have an understanding."]] },
      ],
    },
  };
  /* every line here, as [who, English], for the voices (rico.js all()) */
  window.RABBIT_TALK_LINES = () => Object.entries(window.RABBIT_TALK).flatMap(([who, t]) => [
    ...(t.back || []).map(([, s]) => [who, s]),
    ...(t.ask || []).flatMap(q => [...q.a.map(([, s]) => [who, s]), ...(q.more ? q.more.a.map(([, s]) => [who, s]) : [])]),
  ]);
  /* The cruise ships as the islanders and Rico talk about them (game.js facts() and the radio): which ship and how near,
     from the relay's timetable (GET /cruise: now, the visit under way; next, the next call; last, the last visit over),
     counted in days in Germany, as the ships keep German time:
       queen, dryrun   which ship: Queen Mempool (Saturdays at two) or MS Dry Run (Wednesdays at four)
       shipSoon        it comes in two or three days    shipTomorrow  tomorrow    shipToday  later today, or in sight
       shipNear        any of these three
       shipHere        its passengers are ashore
       shipGone        it left on time, today           shipCut  it left early or never landed, today (the logbook says why)
       shipAfter       either of these two
       ship            any of the above
       shipSkipped shipQuiet shipClean shipTuned   with shipAfter, from her logbook summary: stops skipped (our node's
                       answers took their time), sends our node left unanswered in time, not one refusal, a change for next time
       pirates         the pirate ship Black Sequence, which comes unannounced: nothing at all before she is in sight, then
       pirateSight     in sight or waiting off the reef     pirateHere   at anchor (her crew stays aboard)
       pirateGone      left, that evening    pirateNext   the day after    pirateAfter   either    pirateCut   left early
       pirateClean     every trick she tried was refused (never while a trick that got through is held back)
       tOverspend tReplay tExpired tStale tForged tImpostor tFreeride tGiant tDouble tPoison tCram tGovernance   that trick was refused at least once (live, or
                       after the visit); a trick that got through is never a fact, so no line names it
     The visit under way counts first, then one that ended today, then the next call. Nothing while the ships are
     switched off (the relay announces no call then) or the relay cannot be reached: nobody talks about a ship that will not come. */
  const BERLIN = (() => { try { return new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", year: "numeric", month: "numeric", day: "numeric" }); } catch (e) { return null; } })();
  const dayOf = t => {   // the day in Germany as a number: tomorrow is today + 1
    if (!BERLIN) return Math.floor(t / 86400 + 1 / 24);   // no time zones here: central European winter time
    const p = {}; BERLIN.formatToParts(new Date(t * 1000)).forEach(x => { p[x.type] = +x.value; });
    return Date.UTC(p.year, p.month - 1, p.day) / 864e5;
  };
  /* the pirates' eight tricks (relay cruise.py TRICKS), as facts once the chain refused one: what a line may name */
  const TRICKF = { overspend: "tOverspend", replay: "tReplay", expired: "tExpired", stale: "tStale", forged: "tForged", impostor: "tImpostor", freeride: "tFreeride", giant: "tGiant",
    double: "tDouble", poison: "tPoison", cram: "tCram", governance: "tGovernance" };
  const WHEN = ["ship", "queen", "dryrun", "shipSoon", "shipTomorrow", "shipToday", "shipNear", "shipHere", "shipGone", "shipCut", "shipAfter",
    "shipSkipped", "shipQuiet", "shipClean", "shipTuned",
    "pirates", "pirateSight", "pirateHere", "pirateGone", "pirateNext", "pirateAfter", "pirateCut", "pirateClean", ...Object.values(TRICKF)];
  const mark = (ship, w) => {
    const f = {}; if ((ship !== "queen" && ship !== "dryrun") || !WHEN.includes(w)) return f;
    f.ship = f[ship] = f[w] = true;
    if (w === "shipSoon" || w === "shipTomorrow" || w === "shipToday") f.shipNear = true;
    if (w === "shipGone" || w === "shipCut") f.shipAfter = true;
    return f;
  };
  const shipOf = v => v && (v.ship || (v.style === "liner" ? "queen" : v.style === "expedition" ? "dryrun" : v.style === "pirate" ? "pirates" : null));
  const sum = o => typeof o === "number" ? o : Object.values(o || {}).reduce((a, b) => a + (Number(b) || 0), 0);
  const cutOf = l => !l.landed || /^(no landing|left early)/.test(l.note || "");
  /* what a visit's summary (relay "last": the logbook's public summary) says the ship learned or met */
  const learned = l => {
    const f = {}; if (!l || !l.landed) return f;
    if ((Number(l.skipped) || 0) > 0 && !(Number(l.half_strained) > 0)) f.shipSkipped = true;   // skipped while our node was slow, not a strained testnet
    if ((Number(l.unanswered) || 0) > 0) f.shipQuiet = true;
    if (!cutOf(l) && !sum(l.refused) && sum(l.sent) > 0) f.shipClean = true;
    if ((l.changed || []).some(c => c && !c.held && c.what)) f.shipTuned = true;
    return f;
  };
  /* the pirates' tricks the chain refused (each trick by name, tOverspend …): live from "by", after from the summary.
     A trick that got through is held back (relay: {held: true}) and never counted, so no line ever names it */
  const refusedOf = (T, live) => {
    const f = {}; if (!T) return f;
    for (const [k, n] of Object.entries(live ? T.by || {} : T)) if (TRICKF[k] && (live ? Number(n) > 0 : n && !n.held && !n.through && Number(n.stopped) > 0)) f[TRICKF[k]] = true;
    return f;
  };
  const cleanOf = T => { const c = Object.values(T || {}); return c.length > 0 && c.every(x => x && !x.held && !x.through && Number(x.tried) > 0 && x.tried === x.stopped); };
  /* the pirates come unannounced: nothing about them before they are in sight, then shock, then talk until the next day */
  function pirate(c, now, today) {
    const f = {}, v = c.now, on = (...k) => { f.pirates = true; k.forEach(x => { f[x] = true; }); };
    if (v && shipOf(v) === "pirates" && v.phase) {
      if (v.phase === "approach" || v.phase === "waiting") on("pirateSight");
      else if (v.phase === "landing" || v.phase === "ashore" || v.phase === "boarding") { on("pirateHere"); Object.assign(f, refusedOf(v.tricks, true)); }
      else if (v.phase === "gone") { on("pirateGone", "pirateAfter"); if (v.why) f.pirateCut = true; else Object.assign(f, refusedOf(v.tricks, true)); }
      return f;
    }
    const l = c.last;
    if (l && shipOf(l) === "pirates" && l.end && l.end <= now) {
      const d = today - dayOf(l.end);
      if (d === 0 || d === 1) {
        on(d ? "pirateNext" : "pirateGone", "pirateAfter");
        if (cutOf(l)) f.pirateCut = true;
        else { Object.assign(f, refusedOf(l.tricks, false)); if (cleanOf(l.tricks)) f.pirateClean = true; }
      }
    }
    return f;
  }
  window.RABBIT_SHIP_WHEN = Object.assign((c, now) => {
    if (!c) return {};
    const today = dayOf(now), pf = pirate(c, now, today), out = f => Object.assign(f, pf);
    const v = c.now && shipOf(c.now) !== "pirates" ? c.now : null;
    if (v && v.phase) {
      if (v.phase === "landing" || v.phase === "ashore" || v.phase === "boarding") return out(mark(shipOf(v), "shipHere"));
      if (v.phase === "approach" || v.phase === "waiting") return out(mark(shipOf(v), "shipToday"));
      if (v.phase === "gone") return out(mark(shipOf(v), v.why ? "shipCut" : "shipGone"));
    }
    const l = c.last;
    if (l && shipOf(l) !== "pirates" && l.end && l.end <= now && dayOf(l.end) === today)
      return out(Object.assign(mark(shipOf(l), l.landed && !/^(no landing|left early)/.test(l.note || "") ? "shipGone" : "shipCut"), learned(l)));
    const n = c.next, d = n && n.t0 > now ? dayOf(n.t0) - today : -1;   // a pirate call as the next one (an older relay): mark says nothing
    return out(d === 0 ? mark(shipOf(n), "shipToday") : d === 1 ? mark(shipOf(n), "shipTomorrow") : d === 2 || d === 3 ? mark(shipOf(n), "shipSoon") : {});
  }, { keys: WHEN, mark, TRICKF,
    /* a preview (?ship=pirates&phase=approach|land|here|turn|gone|next|cut): the pirate facts of that moment */
    pirate: (phase, tricks) => {
      const f = { pirates: true }, k = phase === "approach" || phase === "wait" ? "pirateSight" : phase === "gone" || phase === "cut" ? "pirateGone" : phase === "next" ? "pirateNext" : "pirateHere";
      f[k] = true; if (k === "pirateGone" || k === "pirateNext") f.pirateAfter = true;
      if (phase === "cut") f.pirateCut = true; else Object.assign(f, refusedOf(tricks, true));
      return f;
    } });
})();
