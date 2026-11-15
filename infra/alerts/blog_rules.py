"""Tau HUD's house rules for every blog article, in one place (Kilian, 15 November 2026: "I don't want to discuss the
same stuff for every article again"). Every writer prompt gets them (blog.py's ship articles, news_article.py,
testnet_week.py) and the second read (editor.py) checks every draft against them. Gathered from Kilian's corrections
since October 2026; when he corrects an article, the lesson goes here, so the next one is right by itself."""

RULES = """1. Meaning first. Open with what defined the period and what it means for the people who use or follow the Tau \
Net testnet (their balances, rules, games, the chance to try something), then back it with numbers. Say what the \
numbers come to (shares, changes, what held up, what did not) and what they do not prove. A post that only lists \
numbers fails.
2. Worth reading, well grounded. A specific headline with subject and verb that names the news; concrete stakes for the \
reader in the first lines, so they feel they would miss something without it. No clickbait, no teasers, no drama, no \
trolling, nothing overdone.
3. Natural spoken English. Every sentence, label, picture tile and chart caption reads as something a person would say \
("transactions by users of our apps", never "transactions, our test traffic not counted"). No clipped, inverted or \
telegraph phrases, no internal names or codes (a ship is "Queen Mempool", never "queen").
4. Naming: the network is Tau Net; its test network is Tau Testnet Alpha or "the Tau Net testnet". Tau alone is the \
language rules are written in, and the Tau engine checks them; never call the network just "Tau".
5. Fair to IDNI. Never blame, mock or lecture IDNI or the testnet; credit what held up; own what went wrong on our \
side plainly ("our node", "our relay", "our ships" are ours).
6. Causes only as known. What IDNI said, say as IDNI said it and go no further; what nobody said, say plainly that we do \
not know. A chain restart during or right after our ships' test traffic: never rule our traffic out.
7. Users. Only users of our apps (Agorzilla, Tau HUD, White Rabbit Key, players in No Memo) and other wallets are \
people's transactions. Simulated cruise passengers, the island bot, No Memo's own wallets, the hack-of-the-week wallets \
and IDNI's genesis accounts (IDNI's own testing) are never users. No Memo's players are real people. Wallets, not people.
8. Numbers. Every number comes from the facts; a few per paragraph, rounded where that reads better, shares and \
changes where they say more than raw counts. Only events inside the period.
9. Shape. Short paragraphs with air; "why it matters" says it at a glance (for the people using the testnet, for the \
community and IDNI, one honest limit). Plain words for non-developers; no code, file or field names.
10. Our apps named in the text are linked to their pages. It is a testnet: its coins have no value and it can start \
over (say it once). Tau HUD is a community project, not run by IDNI.
11. No hype or marketing words, no price or coin talk, no exclamation marks, no emoji, no names of people.
12. No bold safety promises: never "cannot lose", "risk-free", "no risk", "guaranteed", "completely safe", "cannot be \
stolen" or the like; they are a regulatory risk and nothing we can stand behind. Say what is true and limited instead \
("free test coins with no value", "the Guardian protects against mistaken or tricked payments, not a stolen key")."""

FOR_WRITERS = "\n\nHouse rules for every Tau HUD article (they win over anything above that differs):\n" + RULES
