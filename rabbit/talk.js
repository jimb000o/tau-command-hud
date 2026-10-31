/* What the islanders say when you come back, and what they answer when you ask them something (White Rabbit Key).
   window.RABBIT_TALK[who] = { back: [[when, line], ...], ask: [{ q, a: [[when, line], ...], more: { q, a } }, ...] }
   back: said instead of their first line once you have heard that; the first one whose "when" holds and that you have
   not heard yet wins, then they take turns. ask: questions you can put to them for free (no move, nothing in the Book);
   "more" is the deeper question that opens once the first one is answered. "when" is one of the facts game.js knows
   ("" always, early, mid, last, myLaw, noLaw, pact, broke, deal, lied, caught, truth, smeared, lead, poor, chart, key,
   drummed, circled, dove, worked, plans, and every law id in force: night quiet reef harbour boat lunch concerts road copy tax).
   Every line is spoken in that islander's voice (infra/rico/make.py, through rico.js all() and rabbit/voices.json),
   so a line never holds a number, a name of the player or anything else that changes. */
(() => {
  "use strict";
  window.RABBIT_TALK = {
    ama: {
      back: [
        ["last", "The last day. Suddenly everyone is very polite to me. It happens every election, like the rains."],
        ["broke", "You broke a pact. I am not angry. The Book is not angry either. It simply remembers, which is worse."],
        ["harbour", "The deep harbour is law now. Laws arrive quickly. What they do to the reef comes on the slow boat."],
        ["myLaw", "One of your laws stands. Good. A law is easy to pass and hard to live with. We will see which kind yours is."],
        ["early", "Sit, if you like. Young candidates stand. Old ones have learned that a vote takes as long as it takes."],
        ["", "The council is quiet today. Either the island is at peace, or everyone is at Lola’s. Usually it is Lola’s."],
        ["", "Back again. This tree has seen more elections than anyone. It never voted once, and it is still the most respected thing on the island."],
      ],
      ask: [
        { q: "Why does the council meet under a tree?", a: [["", "Because a roof can be locked and a tree cannot. Anyone may come and listen. Most come for the shade and stay for the arguments."]],
          more: { q: "And when nobody agrees?", a: [["", "Then nothing changes, and that is allowed. People think a council is there to decide. It is there so that nobody decides alone."]] } },
        { q: "Who really runs this island?", a: [["deal", "You took an envelope, so you may think the embassies do. They pay for promises. Promises are cheap. Two votes out of three are not."], ["", "Nobody, and that is the point. There is no chief with a master key. What we agreed is on the stone and in the Book, and anyone can read both."]],
          more: { q: "Not even you?", a: [["", "Especially not me. I am old. I forget where I put my glasses. Imagine if the rules depended on where I put them."]] } },
        { q: "Have you ever seen Agorzilla?", a: [["harbour", "Since the harbour passed, the footprints come down to the beach at night. I am not saying he is upset. I am saying he paces."], ["", "My grandmother said he grows the way the island votes. So when people ask me what he looks like, I tell them: look at what you voted for."]] },
      ],
    },
    marisol: {
      back: [
        ["last", "Last day. My feet hurt, my voice is gone, and I still owe three people a coffee. Go on, the square is listening."],
        ["reef", "The reef law passed. The fishermen bought me a coffee for once. I didn’t know they could."],
        ["harbour", "A cruise harbour, then. My nets will catch fewer fish and more flip-flops."],
        ["lied", "I heard the line you bought on Radio Coco. People believed it at breakfast. By lunch they had read the Book."],
        ["mid", "Halfway through the week, and people have started quoting me back to myself. That’s when you find out what you actually said."],
        ["early", "Morning! Everyone’s here. Buying fish, selling gossip, pretending not to listen. Say something they care about."],
        ["", "You again! Good. People trust a face they’ve seen twice. Three times, and they start telling you their problems."],
      ],
      ask: [
        { q: "What do people here really want?", a: [["", "Fish on the table, a road that doesn’t eat their tyres, and quiet when the baby sleeps. Nobody gets all three at once. That’s politics."]],
          more: { q: "So how do you win them over?", a: [["", "You listen first. Then you write down what you promised, where they can read it. People forgive a slow law. They don’t forgive a promise that changes."]] } },
        { q: "Why run, with a café to look after?", a: [["", "I heard the same complaints over coffee for ten years. At some point you either put up a complaints box or stand for council. The box was more expensive."]] },
        { q: "Do you trust the other candidates?", a: [["pact", "I trust the ones who shook hands at Lola’s. Not because they’re nice. Because the Book saw the handshake."], ["", "I trust what’s written down. Tobias has a theory about everyone, Baako has a handshake for everyone, Hana has a footnote for everyone. I have coffee."]] },
      ],
    },
    lola: {
      back: [
        ["broke", "Well, look who’s back. The one who broke a pact. Lemonade’s still free. My smile costs extra today."],
        ["pact", "My favourite kind of customer: one with a pact. You keep yours, I keep pouring."],
        ["last", "Last night before the vote. Suddenly everybody loves everybody. I’ve seen this one before. I know how it ends."],
        ["early", "First days of the campaign. Everybody’s friends, nobody’s signed anything yet. My favourite time to listen."],
        ["", "You look thirsty. Or nervous. In election week on this island, it’s usually both."],
        ["", "Back so soon? Sit down. Pacts first, gossip second, lemonade always."],
      ],
      ask: [
        { q: "Why are pacts made here, not at the council?", a: [["", "Because the council is where you argue and the bar is where you make up. And I’m a good witness. I don’t take sides, I take orders."]],
          more: { q: "What happens when someone breaks one?", a: [["", "Nothing loud. No shouting, no glasses thrown. It just goes into the Book, and the next time that person holds out a hand, everybody looks at it first."]] } },
        { q: "Who comes in here at night?", a: [["", "Fishermen, surveyors, and one ambassador in a very big hat who thinks nobody recognises him. Everybody does. He tips well, so we pretend."]] },
        { q: "Have you ever seen Agorzilla?", a: [["", "Something took every banana from the crate out back and closed the lid again. Honestly? Best-behaved customer I ever had."]] },
      ],
    },
    rico: {
      back: [
        ["caught", "Oof. They read the Book and found your name under that rumour. Rico warned you. Rico still has your coins."],
        ["lied", "My best customer! The rumour’s still out there, baby. So is the Book. I’d start being extra nice to people."],
        ["truth", "You paid for a true line. Rare! Rico played it again for free, just to hear how the truth sounds on air."],
        ["last", "Last day before the vote! The phones are ringing, the bananas are disappearing, and Rico hasn’t slept. Business is great."],
        ["mid", "Halfway to the vote, baby. The rumours are getting tired and the Book is getting thicker. Rico loves this part."],
        ["", "Welcome back to the studio, baby. Mind the cables. The yellow one is the radio. The green one is Rico’s fan."],
      ],
      ask: [
        { q: "Do you ever check what you play?", a: [["", "Rico plays, the Book checks. That’s the deal on this island. Rico could lie all day, but every coin has a name on it, and the name goes in the Book."]],
          more: { q: "Then why would anyone pay for a lie?", a: [["", "Because a lie runs faster than a page. For about a day. Then people read, and the lie trips over its own name. Rico has seen it a hundred times. Rico still takes the coins."]] } },
        { q: "Could the council switch you off?", a: [["", "Nobody can. There’s no big red button under the council tree. If people stop listening, that’s the off switch. And so far, baby, they listen."]] },
        { q: "What’s the deal with Agorzilla?", a: [["", "Off the record? One night Rico left the window open and came back to the turntable spinning a slow song. Nobody in the studio. One banana peel, folded. Rico respects a fellow music lover."]] },
      ],
    },
    sam: {
      back: [
        ["caught", "The Book showed up a rumour this morning. I didn’t do anything. I never do. I just turn the pages, and the pages do the rest."],
        ["copy", "There’s a copy of the Book on the square now. Half my visitors are gone. I have never been happier."],
        ["last", "Last day. People come in to read who have never read before. Elections are good for reading."],
        ["early", "The first days are always thin. A few lines, a few promises. By the end of the week the Book will be heavy with them."],
        ["", "Sit, sit. I was just reading yesterday again. It hasn’t changed. That’s the nice thing about it."],
        ["", "Come in, come in. I’ve just dusted the Book. Not that it needs it. Nothing in it ever changes. It only grows."],
      ],
      ask: [
        { q: "Have you ever wanted to tear out a page?", a: [["", "Once. A very bad poem, written by me, when I was young. It’s still in there. Everyone has read it. That is the price of a record nobody can edit."]],
          more: { q: "Why not make just one exception?", a: [["", "Because the first exception is a key, and somebody will want to borrow it. A Book that one person can change is only a diary with ambitions."]] } },
        { q: "What do people look up most?", a: [["", "Who paid for what. Then who voted how. Then, every single time, whether Marisol really fishes inside the reef. She doesn’t. They check anyway. Checking is the whole idea."]] },
        { q: "Is the Book like Tau Testnet Alpha?", a: [["", "In a way. Out there every block points back to the one before, so nobody can slip a page into the middle. And out there they count wallets, not people. One person can hold many wallets. The Book only knows names."]] },
      ],
    },
    tobias: {
      back: [
        ["harbour", "The deep harbour is law! I have already written the opening speech. It runs to forty minutes. The ships will have to wait."],
        ["reef", "No big ships in the bay. Very well. I shall welcome the small ones with twice the ceremony."],
        ["concerts", "Beach concerts on Sundays! At last the island has a stage worthy of my announcements."],
        ["last", "The final day! Tomorrow, the count. I have polished my medal, my cap and my modesty. Mostly the medal."],
        ["mid", "Halfway through the campaign. I have given eleven speeches. The gulls have heard every one of them. The gulls are not voting."],
        ["", "Ah, a visitor to my pier! Every boat that ties up here is greeted by me, personally, with a short speech. Short for me."],
      ],
      ask: [
        { q: "What does a harbour master actually do?", a: [["", "I write down every boat that comes and goes, with the hour. Rather like Sam with his Book, only with more salt and more dignity."]],
          more: { q: "And if someone lies about their boat?", a: [["", "Then the next harbour’s list says otherwise, and the two lists have a little chat. Lies hate company. Put two honest records side by side, and the fibber has nowhere to anchor."]] } },
        { q: "Why do you want visitors so much?", a: [["", "Visitors clap. The island stopped clapping for me years ago. Also they pay for the music, and music is the only thing on this island louder than me."]] },
        { q: "Is it true you have a theory about everyone?", a: [["", "Slander! Well, yes. Kai is secretly a fish. Pim measures his own shadow at night. And Agorzilla is a council member in a very good costume. I have no proof. Proof is for the Book. I do theories."]] },
      ],
    },
    hana: {
      back: [
        ["boat", "The school boat runs every morning now. Attendance is up, and so is seasickness. I write down both."],
        ["lunch", "Fresh fish for lunch. The children are delighted. The cat outside the window is more delighted."],
        ["smeared", "The children heard a rumour on Radio Coco. They checked the Book before break. It was a short break."],
        ["last", "Last day before the vote. I have marked every promise anyone made this week. Some of you will not like your marks."],
        ["early", "Good morning. The children are copying out every candidate’s promises, neatly, so they can compare them at the end of the week."],
        ["", "Welcome back. Sit at the back, please. The front row is for people who did their homework."],
      ],
      ask: [
        { q: "What do the children learn here?", a: [["", "Reading, sums, and checking. I teach them two questions for anything they hear: who said it, and where is it written. It makes them terrible at believing adverts."]],
          more: { q: "Isn’t that a little cold?", a: [["", "No. Trust is warm. Checking only keeps it from being spent on the wrong people. The children still believe in each other. They only check the grown-ups."]] } },
        { q: "Why run for council?", a: [["", "Because a good law is a lesson that keeps teaching after the teacher goes home. A speech stops when the speaker sits down."]] },
        { q: "What do the children say about Agorzilla?", a: [["", "Half the class says he is real, the other half says he is Kiko in a coat. They held a debate. Both sides quoted the same blurry photo. Everyone got a B."]] },
      ],
    },
    kai: {
      back: [
        ["harbour", "Since the harbour law, the readings look sad. The sensors don’t do politics. They just sign what they see."],
        ["dove", "Our dive is in the Book! Signed, sealed, slightly salty."],
        ["reef", "Big ships out of the bay, and the parrotfish are back. The sensors signed it, I signed it. The parrotfish didn’t, but you could tell."],
        ["", "Perfect visibility today. You can see the sand, the fish, and three sensors arguing with a turtle."],
        ["", "Hey, back for more? The reef is open. The coffee machine is not. Priorities."],
      ],
      ask: [
        { q: "Why sign every reading?", a: [["", "Because the reef can’t talk and people can. Without a signature anyone can say the water is clean. With one, the sensor said it, right then, and nobody can change that later."]],
          more: { q: "Couldn’t someone fake a sensor?", a: [["", "They could try. But every diver carries three sensors, and every reading points back to the one before. To fool us you’d have to fool all three, the same way, at the same moment. The fish would notice first."]] } },
        { q: "What do the embassies want with the bay?", a: [["", "Pim says something deep. A cruise harbour is deep. So is the trench off the north point. I’d love to know which one they mean."]] },
        { q: "Seen anything odd down there?", a: [["", "A piano key, once. Captain Wren labelled it. And big footprints on the shallow shelf at low tide. Something heavy walks there. I’m not saying who. I’m saying it isn’t a crab."]] },
      ],
    },
    baako: {
      back: [
        ["deal", "Ah, you met the ambassadors! Lovely people. Generous. Just remember: the envelope is quiet, the Book is not."],
        ["road", "A road round the island! My coconuts will travel in style. Some of them have never seen the other side."],
        ["worked", "You worked a shift! You smell exactly right. Like someone who earned something."],
        ["early", "A fine morning! The coconuts are ripe, the embassies are friendly, and nobody has asked me a hard question yet."],
        ["", "Welcome back, friend! Mind the organ. Did I say that already? I say it to everyone. Twice to Tobias."],
      ],
      ask: [
        { q: "Do you take money from the embassies?", a: [["", "Everybody asks. Yes, I talk to them, I shake their hands, I drink their tea. What I promise is in the Book, like everyone’s. You can count my envelopes. I’d rather you counted my coconuts."]],
          more: { q: "Doesn’t the money buy your vote?", a: [["", "It buys a meeting. They pay me to propose a law, and the other three still have to say yes. Money can knock on the door. It can’t open it."]] } },
        { q: "How does the machine really work?", a: [["", "Three bicycles turn the press, the organ pumps the air, and Noor tells everyone to pedal faster. Nobody understands the organ. It was here before the factory."]] },
        { q: "Is Agorzilla stealing your coconuts?", a: [["", "Never a coconut. Only bananas. A creature with standards. I leave one banana by the gate on Fridays now. Good relations with the neighbours."]] },
      ],
    },
    noor: {
      back: [
        ["last", "Last day of the campaign, and the boss is out shaking hands. Somebody has to keep the bicycles turning."],
        ["", "Back again? Good. Shifts are short, the pay is honest, and the organ is still off limits."],
      ],
      ask: [
        { q: "What’s it like working for a candidate?", a: [["", "Same as working for a farmer, only with more visitors. He promises, I deliver. The coconuts don’t vote, so they’re the calmest people here."]] },
        { q: "Why is the organ off limits?", a: [["", "Last time someone touched it, the machine played a waltz for three days and made nothing but soap. Very nice soap. Nobody needed that much soap."]] },
      ],
    },
    pim: {
      back: [
        ["deal", "Ah. You have signed with an embassy. That is not my business. I only measure. Although it was quite a thick envelope."],
        ["reef", "No big ships in the bay. The embassy asked me to measure the bay again. I did. It is still the same size."],
        ["", "I measured the distance to your feet. Sorry. Habit. Two metres and a bit. The bit is the interesting part."],
        ["", "Oh. Hello again. Please don’t step on the string. That string is the coast, officially."],
      ],
      ask: [
        { q: "Who are you really working for?", a: [["", "The embassies pay, I measure. What they do with the numbers is between them and the council, and the council votes in public. I find that very relaxing."]],
          more: { q: "And if the council says no?", a: [["", "Then I have very accurate maps of a harbour that will never exist. It happens. My drawer is full of them. Some are quite beautiful."]] } },
        { q: "Why do you look so nervous?", a: [["", "I always look like this. My mother says I was born checking a measurement twice. Here it helps. On this island everything gets checked twice, even me."]] },
        { q: "Have you measured Agorzilla’s footprints?", a: [["", "Forty-two centimetres. Twice. Then the third one was forty-four. Either he is growing, or he walks faster when he is upset. I wrote a report. Nobody has asked for it."]] },
      ],
    },
    wren: {
      back: [
        ["key", "So you found what was behind the waterfall. I knew it, dear. The sea gives things back to the patient ones."],
        ["chart", "Still got my chart, dear? Good. Follow the water, not the path. Paths are made by people in a hurry."],
        ["", "Back already, dear? I’ve just labelled the kettle. It was feeling left out."],
        ["", "Come aboard, dear, and mind the third step. It’s labelled, but nobody reads labels."],
      ],
      ask: [
        { q: "What’s the oddest thing the sea gave back?", a: [["", "A ship’s log from a crew who swore they had never been here. The log said otherwise, in their own hand. Records outlive excuses, dear. That’s archaeology in one sentence."]],
          more: { q: "So you trust records more than people?", a: [["", "I trust records about people. People change their minds, which is healthy. Records stop them changing the past, which is healthier."]] } },
        { q: "Why retire on this island?", a: [["", "This island keeps its agreements on a stone and in a Book. I wanted to see how a place lives that remembers everything. Politely, it turns out. Mostly."]] },
        { q: "Do you believe in Agorzilla?", a: [["", "I catalogue things, dear, I don’t believe in them. Item four hundred and twelve: one banana peel, folded, found on my deck. Origin unknown. Manners excellent."]] },
      ],
    },
    kiko: {
      back: [
        ["harbour", "The harbour law passed. Big ships, big waves. I’m building the sides higher."],
        ["last", "Last day before the vote. Everyone’s in a hurry. The wood doesn’t care."],
        ["early", "Morning. The wood is dry, the sea is calm, and nobody has asked me who I vote for. Yet."],
        ["", "Back again. The canoe is one plank further than yesterday. That’s fast, for a canoe."],
      ],
      ask: [
        { q: "How do you know a canoe is ready?", a: [["", "You put three people in it. If they argue and it still floats, it’s ready."]],
          more: { q: "That sounds like the council.", a: [["", "It is the council. Ama taught me. It isn’t finished when one man says so. It’s finished when it holds everyone."]] } },
        { q: "Where did you see Agorzilla?", a: [["", "Behind the drums, at dusk. Big. Calm. He looked at the canoe like he was checking my work. Then he left. Took a banana. Fair."]] },
        { q: "Who will you vote for?", a: [["", "Whoever cares about fish and music. I tell everyone the same, so nobody has to guess."]] },
      ],
    },
    tano: {
      back: [
        ["drummed", "The drums carried your truth across the hills. The hills don’t usually agree on anything. That evening they did."],
        ["circled", "You sat in the circle and listened. Rare, for a candidate. The others noticed. So did I."],
        ["", "You came back. The drums like that. Most people only come up here when there is bad news."],
        ["", "Welcome back. The drums are resting. A drummer rests between the beats. That’s half the music."],
      ],
      ask: [
        { q: "Why can’t anyone bribe a drummer?", a: [["", "Oh, they tried. But every message goes out from three hills, and all three must match what the stone says. You’d have to bribe three drummers and a stone. The stone is very hard to talk to."]],
          more: { q: "And if the three hills disagree?", a: [["", "Then nothing is carried, and everyone comes down to the circle to find out why. Silence is the drums’ way of saying: not yet."]] } },
        { q: "What can the circle decide?", a: [["", "Anything that doesn’t break what we already agreed. Anyone can stand up and show the contradiction. If nobody can, it stands. It’s slow. Slow is how you know it’s real."]] },
        { q: "Are those Agorzilla’s footprints by the drums?", a: [["", "He likes the low drum. Some mornings the skin is warm, as if someone sat close all night, listening. He never plays. He only listens. A better audience than most."]] },
      ],
    },
    frost: {
      ask: [
        { q: "What does the North Wind really want?", a: [["", "A deep harbour. We say so openly. It is even in your Book. Ships need depth, and depth needs a vote. Ours is not a secret. It is merely expensive."]],
          more: { q: "And if the island says no?", a: [["", "Then we wait for the next election. The North Wind is patient. Unfortunately, so is your Book. It remembers who promised and did not deliver."]] } },
        { q: "Why not simply build it?", a: [["", "Because there is nobody here who can sign it for us. No chief, no master key, only a council and a Book. Honestly, it is exhausting. Elsewhere one handshake is enough."]] },
      ],
    },
    salado: {
      ask: [
        { q: "Why do you want a road so badly?", a: [["", "Roads, my friend, are how good things arrive. Trucks, tourists, my cousin’s ice cream. The island will love it. Eventually. We can wait. We are very good at waiting, and at lunch."]],
          more: { q: "What do you get out of it?", a: [["", "Me? A road to drive on, and a very long line in your Book saying who paid for it. My government likes to be remembered. Your Book is happy to help."]] } },
        { q: "Do you and Ambassador Frost talk?", a: [["", "Every Thursday. We play cards. He cheats, I let him, and we both write it down. Diplomacy is mostly agreeing on who keeps the score."]] },
      ],
    },
  };
  /* every line here, as [who, English], for the voices (rico.js all()) */
  window.RABBIT_TALK_LINES = () => Object.entries(window.RABBIT_TALK).flatMap(([who, t]) => [
    ...(t.back || []).map(([, s]) => [who, s]),
    ...(t.ask || []).flatMap(q => [...q.a.map(([, s]) => [who, s]), ...(q.more ? q.more.a.map(([, s]) => [who, s]) : [])]),
  ]);
})();
