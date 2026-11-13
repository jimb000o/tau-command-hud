#!/bin/sh
# One short command for the server after any merge: pull, rebuild whatever changed, recreate caddy once, speak any new
# voice lines, then print one block to paste into the chat. Safe to rerun; containers whose code did not change keep running.
# First time:  cd /opt/tau-command-hud && git pull && sh infra/up.sh
# After that:  up            everything above
#              up island     the same, then a new painted island with every room to match (a few minutes, see island.sh)
#              up room grotto  the same, then that room (or several) painted anew to match the island as it is (2 min each)
#              up touch canoe-camp  the same, then two versions of the island with those changes, to look at (not live)
#              up touch beach 28    the same, from island 28 of the drafts instead of the live island
#              up keep 27 canoe camp  the same, then island 27 live and those rooms painted anew to match it
#              up blog       the blog drafts waiting (the blog service rebuilt, node untouched); up blog publish <id>  puts one on tauhud.com/blog/
#                            and posts it once to Telegram and X; up blog draft <visit>  writes that visit's draft anew
#              up bust salado  the same, then that portrait (or several) painted anew, talking and blinking too (1 min each);
#                            up bust --recut salado  cuts the kept painting out again, paints nothing;
#                            up bust --from infra/rabbit-art/imports/codex hana  takes pictures painted elsewhere
#              up follow     the node following IDNI tau-testnet main by itself: its state; up follow now  one check at once,
#                            up follow off / on  stops / starts it (nothing rebuilt, the node left alone)
#              up idni       what the next daily IDNI progress post would say now (its two services rebuilt, nothing posted);
#                            up idni send  posts it now, up idni hold  keeps the next one back, up idni release  undoes that
#                            up idni restart  what the post for the newest testnet restart would say (nothing posted)
#                            up idni fixed  what IDNI solved of our reports and its post; up idni fixed send  sends the
#                            draft, up idni fixed no <n>  takes one back, up idni fixed auto / draft  posts without / with asking
#              up cruise     a cruise ship's last visit in numbers and the node's timeouts per hour (nothing rebuilt)
#                            up cruise next  the next call's announcement as it goes out by itself (posts nothing);
#                            announcements and reports run by themselves every week (alerts/cruise_crier.py);
#                            up cruise release 2026-11-10-pirates  shows a held-back finding (a pirate trick that got
#                            through) in the public logbook and lets the blog write that visit (after IDNI knows)
#              up clip       the pirates' clip of their newest visit to look at (posts nothing; a marked SAMPLE before
#                            the first); it goes to Telegram and X by itself after each Tuesday call; up clip send <visit>
#              up kling      Kling's clips (alerts/kling.py): the posting services rebuilt with the code just pulled (the
#                            node left alone, safe any time), then this month's clips; up kling test  one 5 s clip of the
#                            live island to look at (proves the key), up kling list  every clip, up kling send <key>  posts
#                            a draft, up kling off island  the island still again (until the next painting)
#              up shots      the post pictures of Tau HUD's pages taken anew in Live mode and checked (node left alone):
#                            which pages have a picture, why the others have none; up shots rules status  only these
#              up escrow     the relay alone restarted with the code just pulled (not while a ship is due), then the
#                            cruise bookings ahead in escrow, each with its state; up escrow status  only those
#              up nomemo     No Memo's crew purse (relay/nomemo.py): the drop, the players' board, what waits to be paid (nothing rebuilt)
#                            up nomemo feedback  what players wrote with `feedback <text>` since the last look (relay/nomemo_feedback.py),
#                            up nomemo feedback all  every remark kept
#              up hack       the hack of the week (relay/hackweek.py, Thursdays 11:00): next replay, last runs step by step
#                            (nothing rebuilt, nothing sent); up hack preview  the last replay's post texts and picture;
#                            up hack release 2026-11-12-poisoning  shows a held-back finding in public (after IDNI knows)
#              up report     the weekly report for IDNI as it stands (nothing filed; blog + nodelog rebuilt, node left alone): its text, a page
#                            and a pre-filled GitHub issue link; up report last  last week's; up report send  also to
#                            your Telegram (it comes there by itself every Sunday 18:00)
#              up guardian   the Guardian (tauhud.com/guardian/) started or restarted with the code just pulled, and Caddy
#                            given its door; nothing rebuilt, the node left alone; up guardian status  only its numbers
#              up services   the relay rebuilt with the code just pulled (tauhud.com/services/ reads it), the node left alone;
#                            refuses while a cruise ship is due (Wed 15-18, Sat 13-17 German time; up services --now overrides);
#                            up services status  only what the directory finds now
#              up showcase   the three showcase wallets (relay/showcase.py): the relay rebuilt alone with the code just pulled
#                            (the node left alone; not while a cruise ship is due), then each wallet's rule and last daily
#                            try; up showcase status  only those
#              up knowledge  Tau today for AI assistants (tauhud.com/facts/, llms.txt): the build pulse rebuilt with the code
#                            just pulled, Caddy given its two files, then both written at once and what they hold; the
#                            node left alone, safe any time; up knowledge status  only what they hold now
#              up lights     each painted room's lamps found for the night (nothing rebuilt, the node left alone);
#                            up lights all  every room looked at again; a full up does the new rooms by itself
#              up art        a set painted elsewhere taken over (infra/rabbit-art/imports/codex/isle-36: the island without
#                            people, every place by day and its painted night), nothing rebuilt, nothing painted, the node
#                            left alone, safe any time; up art isle-36  that set, up art check  only checks it
#              up crier      the posting service (alerts) rebuilt with the code just pulled and Caddy given /island/*, the
#                            node left alone, safe any time; then the island picture the posts carry, made from the live
#                            painting, to look at; up crier status  only the picture made anew
#              up cost       what the site's tools were paid, read from their receipts by mail (nothing rebuilt but that
#                            service, the node left alone); up cost gemini 10  a payment by hand; up cost mail  the mailbox
#              up tau        Tau Language on tauhud.com/learn: the checker recreated with the code just pulled (nothing built,
#                            the node left alone, safe any time), then every lesson example asked of the engine; up tau status  only that
#              up telegram   Tau HUD's Telegram group made ready: a closed News topic for the posts, General renamed Chat
#                            (posting services rebuilt, node left alone, posts nothing); up telegram @name  if the link is not @tauHUDchat
#              up owner      the same, then a one-time link: open it in your Telegram, and the news line's watchtower
#                            warns you there privately (never on the channel); up owner test  sends you one test message
set -e
cd "$(dirname "$(readlink -f "$0")")"
ln -sf "$(pwd)/up.sh" /usr/local/bin/up 2>/dev/null && chmod +x up.sh 2>/dev/null || true
if [ "$1" != "--pulled" ]; then
  git -C .. pull --ff-only
  exec sh "$(pwd)/up.sh" --pulled "$@"
fi
shift
# a picture post by hand, nothing rebuilt: up post cruise-dry-run  makes the picture from the live painting and shows the
# texts (look: https://node.tauhud.com/rico/art/drafts/<name>.jpg), up post cruise-dry-run send  posts it to Telegram and X
if [ "${1:-}" = "post" ] && [ -n "${2:-}" ]; then
  J="assets/share/$2.json"; [ -f "../$J" ] || { echo "no ../$J"; exit 1; }
  mkdir -p /opt/sites/rico/art/drafts
  docker compose run --rm -v /opt/tau-command-hud:/repo:ro -v /opt/sites/rico/art:/art:ro -v /tmp:/out alerts \
    python /repo/infra/alerts/cruise_pic.py /art /repo/rabbit/art/ships "/repo/$J" "/out/$2.jpg"
  cp "/tmp/$2.jpg" /opt/sites/rico/art/drafts/
  if [ "${3:-}" = "send" ]; then
    docker compose run --rm -v /opt/tau-command-hud:/repo:ro -v /tmp:/out alerts python /repo/infra/alerts/post_image.py "/out/$2.jpg" "/repo/$J"
    # posted by hand: today's call is not announced a second time by the blog service (alerts/cruise_crier.py)
    docker compose run --rm --no-deps -v /opt/tau-command-hud:/repo:ro alerts python /repo/infra/alerts/cruise_crier.py mark "$2" || true
  else
    docker compose run --rm -v /opt/tau-command-hud:/repo:ro -v /tmp:/out alerts python /repo/infra/alerts/post_image.py "/out/$2.jpg" "/repo/$J" --dry
    echo "look: https://node.tauhud.com/rico/art/drafts/$2.jpg   then post it: up post $2 send"
  fi
  exit 0
fi
# a set painted elsewhere (paint.py isle), nothing rebuilt, nothing painted, the node left alone: up art  the newest set in
# infra/rabbit-art/imports/codex, up art isle-36  that one, up art check [isle-36]  only checks it and writes nothing;
# then the lamps of the places taken over found for the night (one short look each, as a full up does). The blog service
# is rebuilt first (safe any time, as up kling does), so it knows a cleaned island is the same island (no new trailer)
if [ "${1:-}" = "art" ]; then
  if [ "${2:-}" = "check" ]; then sh rabbit-art/paint.sh isle ${3:-} --dry; exit 0; fi
  docker compose up -d --no-deps --build blog >/dev/null 2>&1 || docker compose up -d --no-deps --build blog || true
  A=$(mktemp)
  sh rabbit-art/paint.sh isle ${2:-} 2>&1 | tee "$A" || true
  sh rabbit-art/paint.sh lights --missing 2>&1 | grep -E '^lights:|Error|error|GEMINI|painter' | tail -2 || true
  echo
  echo "---------------- copy from here into the chat ----------------"
  grep -E '^isle:|took over|REFUSED|Traceback|Error' "$A" | grep -v '^isle: /' || true
  echo "look: https://tauhud.com/rabbit/?hour=22:00 (Ctrl+F5), then walk into a place; by day ?hour=12:00"
  echo "---------------- to here --------------------------------------"
  rm -f "$A"
  exit 0
fi
# each painted room's own lamps for the night, nothing rebuilt, the node left alone: up lights  the rooms not looked at
# yet, up lights all  every room again, up lights grotto  that one (paint.py lights)
if [ "${1:-}" = "lights" ]; then
  if [ -n "${2:-}" ] && [ "${2:-}" != "all" ]; then shift; sh rabbit-art/paint.sh lights "$@"; elif [ "${2:-}" = "all" ]; then sh rabbit-art/paint.sh lights all; else sh rabbit-art/paint.sh lights --missing; fi
  echo "look: https://tauhud.com/rabbit/?hour=22:00 (Ctrl+F5), then walk into a place"
  exit 0
fi
# a cruise ship's visit in numbers, nothing rebuilt, nothing sent (cruise-report.py): up cruise  the last visit,
# up cruise 2026-11-07-queen  that one; then the relay's sendtx timeouts per hour of the last 3 days
if [ "${1:-}" = "cruise" ]; then
  # up cruise next: the next call's announcement as it will go out by itself (texts and picture), posts nothing
  if [ "${2:-}" = "next" ]; then
    docker compose up -d blog >/dev/null 2>&1 || true
    docker compose exec -T blog python cruise_crier.py preview ${3:-}
    docker compose cp blog:/tmp/cruise-dryrun.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 || true
    docker compose cp blog:/tmp/cruise-queen.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 || true
    docker compose cp blog:/tmp/cruise-pirates.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 || true
    echo "look: https://node.tauhud.com/rico/art/drafts/cruise-queen.jpg (or cruise-dryrun.jpg, cruise-pirates.jpg)"
    exit 0
  fi
  # up cruise release <visit>: a finding held back (a pirate trick the chain took) becomes public in the logbook
  if [ "${2:-}" = "release" ]; then
    case "${3:-}" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[a-z]*) ;; *) echo "usage: up cruise release 2026-11-10-pirates"; exit 2;; esac
    docker compose exec -T relay python -c "
import json, os, sys
p = os.path.join(os.path.dirname(os.environ.get('CRUISE_STATE_PATH', '/data/cruise-state.json')), 'cruise-released.json')
p = os.environ.get('CRUISE_RELEASED_PATH', p)
try:
    r = json.load(open(p))
except Exception:
    r = []
r = sorted(set(r) | {sys.argv[1]})
json.dump(r, open(p, 'w'))
print('released:', ', '.join(r))
" "$3"
    echo "copy into the chat: cruise release $3 done; the blog drafts that visit within 10 minutes"
    exit 0
  fi
  docker compose cp cruise-report.py relay:/tmp/cruise-report.py >/dev/null
  docker compose exec -T relay python /tmp/cruise-report.py ${2:-}
  echo "sendtx timeouts per hour (UTC), last 3 days:"
  docker compose logs -t --since 72h relay 2>&1 | grep -E "(upstream|sender) sendtx failed" | awk '{print substr($3,1,13)}' | sort | uniq -c | sed 's/^/  /'
  exit 0
fi
# the pirates' clip after each Tuesday call (alerts/trick_clip.py, posted by itself), nothing rebuilt: up clip  the newest
# pirate visit's clip to look at (a SAMPLE, marked on every frame, before the first one), posts nothing;
# up clip send 2026-11-10-pirates  posts that visit's clip now, once (never one where a trick got through)
if [ "${1:-}" = "clip" ]; then
  mkdir -p /opt/sites/rico/art/drafts
  docker compose up -d blog >/dev/null 2>&1 || true
  if [ "${2:-}" = "send" ] && [ -n "${3:-}" ]; then
    docker compose exec -T blog python trick_clip.py send "$3"
  else
    docker compose exec -T blog python trick_clip.py preview ${2:-} /tmp/trick-clip.mp4
    docker compose cp blog:/tmp/trick-clip.mp4 /opt/sites/rico/art/drafts/trick-clip.mp4
    echo "look: https://node.tauhud.com/rico/art/drafts/trick-clip.mp4"
  fi
  exit 0
fi
# The post pictures of Tau HUD's own pages (agorzilla-shots/site-shots.mjs), the node left alone: the picture service
# built and started, Caddy given /pageshots/*, one round at once, then which pages have a checked picture and why the
# others have none. up shots rules status  only these pages.
if [ "${1:-}" = "shots" ]; then
  docker compose up -d --no-deps --build site-shots >/dev/null 2>&1 || docker compose up -d --no-deps --build site-shots
  docker compose up -d --no-deps --force-recreate caddy >/dev/null 2>&1 || true
  shift
  docker compose exec -T site-shots node site-shots.mjs --once "$@" | tail -40
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T site-shots sh -c 'cat /out/pageshots/index.json' | python3 -c '
import json, sys
d = json.load(sys.stdin)
ok = [k for k, v in d.items() if v.get("ok")]
print("page pictures: %d of %d checked" % (len(ok), len(d)))
for k, v in sorted(d.items()):
    print(("  ok    " if v.get("ok") else "  none  ") + k + ("" if v.get("ok") else "  (" + str(v.get("why")) + ")"))
'
  exit 0
fi
# Kling's clips (alerts/kling.py, kling_island.py), the node left alone: the blog and agorzilla services rebuilt with the
# code just pulled, Caddy given /kling/*, then: up kling  this month's clips, up kling test  a 5 s test clip (waits up to
# 10 min), up kling list, up kling send <key>  a draft posted, up kling off island
if [ "${1:-}" = "kling" ]; then
  docker compose up -d --no-deps --build blog agorzilla >/dev/null 2>&1 || docker compose up -d --no-deps --build blog agorzilla
  docker compose up -d --no-deps --force-recreate caddy >/dev/null 2>&1 || true
  case "${2:-}" in
    test) docker compose exec -T blog python kling.py test || true ;;
    list) docker compose exec -T blog python kling.py list ;;
    send) docker compose exec -T blog python kling.py send "${3:-}" || true ;;
    off) docker compose exec -T blog python kling.py off "${3:-island}" ;;
  esac
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T blog python kling.py line
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the hack of the week (relay/hackweek.py, posts by alerts/hack_crier.py), nothing rebuilt: up hack  the next replay and the
# last runs step by step, up hack preview  the last replay's post texts and picture (posts nothing),
# up hack release <run>  a held-back finding (the chain did what it must not) shown in public, after IDNI knows
if [ "${1:-}" = "hack" ]; then
  if [ "${2:-}" = "release" ]; then
    case "${3:-}" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[a-z]*) ;; *) echo "usage: up hack release 2026-11-12-poisoning"; exit 2;; esac
    docker compose exec -T relay python -c "
import json, os, sys
p = os.path.join(os.path.dirname(os.environ.get('HACK_STATE_PATH', '/data/hack-state.json')), 'hack-released.json')
try:
    r = json.load(open(p))
except Exception:
    r = []
r = sorted(set(r) | {sys.argv[1]})
json.dump(r, open(p, 'w'))
print('released:', ', '.join(r))
" "$3"
    echo "copy into the chat: hack release $3 done"
    exit 0
  fi
  if [ "${2:-}" = "preview" ]; then
    docker compose up -d blog >/dev/null 2>&1 || true
    docker compose exec -T blog python hack_crier.py preview ${3:-}
    mkdir -p /opt/sites/rico/art/drafts
    docker compose cp blog:/tmp/hack.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 && echo "look: https://node.tauhud.com/rico/art/drafts/hack.jpg"
    exit 0
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T blog python hack_crier.py status 2>&1 || true
  docker compose exec -T relay python -c 'import json,time,urllib.request
d=json.load(urllib.request.urlopen("http://127.0.0.1:8080/hack/held", timeout=20)); s=json.load(urllib.request.urlopen("http://127.0.0.1:8080/hack", timeout=20))
w=s.get("wallets") or {}
print("hack:    wallets " + (", ".join("%s %s" % (k, v["short"]) for k, v in w.items()) or "not made yet"))
held={r["id"] for r in d.get("runs") or []}
for r in json.load(open("/data/hack-state.json")).get("runs", [])[::-1][:3]:
    print("  %s %s: %s%s" % (r["id"], r.get("status"), r.get("result"), " (FINDING, held back)" if r["id"] in held else ""))
    for k, x in (r.get("steps") or {}).items():
        print("    %-12s ok=%s %s %s" % (k, x.get("ok"), x.get("code") or x.get("status") or "", (x.get("note") or "")[:70]))
    for n in (r.get("log") or [])[-3:]: print("    · " + n["note"][:110])' 2>&1 || echo "relay /hack not answering yet"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# What No Memo's players wrote with `feedback <text>` (relay/nomemo_feedback.py), nothing rebuilt: the remarks not read yet
# (or all), then marked read. /data/nomemo-feedback.seen keeps how many lines were shown.
if [ "${1:-}" = "nomemo" ] && [ "${2:-}" = "feedback" ]; then
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T relay python -c 'import json,os,sys
p="/data/nomemo-feedback.jsonl"; m="/data/nomemo-feedback.seen"; allr=sys.argv[1:2]==["all"]
rows=[json.loads(x) for x in open(p,encoding="utf-8") if x.strip()] if os.path.exists(p) else []
try: seen=int(open(m).read().strip() or 0)
except Exception: seen=0
if seen>len(rows): seen=0
show=rows if allr else rows[seen:]
print("nomemo feedback: %d new, %d kept in all%s" % (len(rows)-seen, len(rows), " (all shown)" if allr else ""))
for r in show:
  w=(r.get("wallet") or "")
  print("- %s  %s  %s  %s" % (r.get("at"), (w[:6]+"…"+w[-4:]) if w else "no wallet", "%s settled, %s claimed, %s" % (r.get("d"), r.get("c"), r.get("l")), r.get("text")))
open(m,"w").write(str(len(rows)))
if not show: print("  nothing new; players write it in the terminal: feedback <text>")' "${3:-}" 2>&1 || echo "relay not answering yet"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# No Memo's crew purse (relay/nomemo.py), nothing rebuilt: the drop's address, the board, what waits, the Tracer
if [ "${1:-}" = "nomemo" ]; then
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T relay python -c 'import json,urllib.request
s=json.load(urllib.request.urlopen("http://127.0.0.1:8080/nomemo", timeout=20)); b=s.get("board") or {}
print("nomemo:  purse %s, tracer %s, drop %s%s%s" % ("on" if s.get("enabled") else "OFF", "on" if s.get("tracer") else "off", s.get("drop_short") or "not made yet", " (making the keys now)" if s.get("making_wallets") else "", " (the bank is filling the drop)" if s.get("filling") else ""))
print("         board: %d wallets, %s; chapters claimed %s; %d payouts today, %d waiting" % (b.get("wallets",0), ", ".join("%s %d" % kv for kv in (b.get("ranks") or {}).items()), b.get("claims"), s.get("today",0), s.get("waiting",0)))
print("         test it: https://tauhud.com/nomemo/  (take 1, run; the drop above must match status)")
import os
p="/data/nomemo-feedback.jsonl"; n=sum(1 for x in open(p,encoding="utf-8") if x.strip()) if os.path.exists(p) else 0
try: seen=int(open("/data/nomemo-feedback.seen").read().strip() or 0)
except Exception: seen=0
print("         feedback: %d new of %d (read them: up nomemo feedback)" % (max(n-seen,0) if seen<=n else n, n))' 2>&1 || echo "relay /nomemo not answering yet"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# IDNI's progress of the day as ONE post (alerts/idni_digest.py), with the code just pulled: devpulse and alerts are
# rebuilt, the node and the relay are left alone. up idni  the last ones and what the
# next would say now (one model call, posts nothing), up idni send  writes it now and the alerts service posts it within a
# minute (up idni send --force: also when the check marked numbers or wording), up idni hold / up idni release
# bookings ahead of a cruise call, in escrow until its arrival (relay/cruise.py): up escrow  restarts the relay alone with
# the code just pulled (never while a ship is due or in port; the node keeps running), then shows every booking;
# up escrow status  only shows them
if [ "${1:-}" = "escrow" ]; then
  if [ "${2:-}" != "status" ]; then
    when=$(TZ=Europe/Berlin date +%u%H)
    case "$when" in 315|316|317|410|411|613|614|615|616)
      if [ "${2:-}" != "--now" ]; then
        echo "a cruise ship or the hack replay is due or under way now (German time $(TZ=Europe/Berlin date +%a\ %H:%M)); the relay stays as it is."
        echo "try again after the visit, or: up escrow --now"; exit 1
      fi ;;
    esac
    docker compose up -d --build --no-deps relay
    echo "waiting 20 s for the relay to start…"; sleep 20
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T relay python -c 'import json,time,urllib.request
d=json.load(urllib.request.urlopen("http://127.0.0.1:8080/cruise", timeout=20))
es=d.get("escrow") or []
print("escrow: ships %s, %d calls with bookings ahead" % ("on" if d.get("enabled") else "switched off", len(es)))
for e in es:
    off=(e.get("called_off") or {}).get("why")
    print("  %s arrival %s: %s%s" % (e["visit"], time.strftime("%a %d.%m. %H:%M UTC", time.gmtime(e["arrival"])), ", ".join("%s %s" % kv for kv in e["count"].items()), ", called off: "+off if off else ""))
    for b in e["bookings"]: print("    no. %-3s %s AGRS  %-13s %s" % (b["p"], b["amount"], b["status"], (b.get("note") or "")[:70]))' 2>&1 || echo "relay /cruise not answering yet"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
if [ "${1:-}" = "idni" ]; then
  shift
  # devpulse writes the IDNI posts, alerts sends them: both with the code just pulled (the node and the relay stay)
  docker compose up -d --build --no-deps devpulse alerts >/dev/null 2>&1 || docker compose up -d devpulse >/dev/null 2>&1 || true
  if [ "${1:-}" = "restart" ]; then   # what the post for the newest testnet restart would say now (restart_brief.py)
    docker compose exec -T devpulse python devpulse.py --restart
    exit $?
  fi
  if [ "${1:-}" = "repic" ]; then     # a site-update post on Telegram gets its right picture, in place: repic <t.me link> <major id>
    shift
    docker compose exec -T alerts python alerts.py --repic "$@"
    exit $?
  fi
  if [ "${1:-}" = "fixed" ]; then     # reported by us, solved by IDNI (fixwatch.py): status, send, no <n>, auto, draft
    shift
    docker compose exec -T devpulse python devpulse.py --fixed "$@"
    exit $?
  fi
  docker compose exec -T devpulse python devpulse.py --digest "$@"
  exit $?
fi
# the weekly report for IDNI, nothing filed (alerts/idni_report.py): the blog service and the node-log reader
# (nodelog, alerts/node_logs.py) rebuilt with the code just pulled, the node left alone, safe any time; then
# up report  this week so far, up report last  last week, up report send  the page link to the owner's Telegram as well
if [ "${1:-}" = "report" ]; then
  shift
  docker compose up -d --build --no-deps blog nodelog >/dev/null 2>&1 || docker compose up -d --build --no-deps blog nodelog || true
  docker compose exec -T nodelog python -c 'import node_logs; print("node log:", node_logs.keep(), "sync/peering lines kept from the last days")' 2>&1 || echo "node log: not readable yet"
  docker compose exec -T blog python idni_report.py "$@"
  exit $?
fi
# the Guardian (guardian/guardian.py), nothing rebuilt and the node left alone: it runs in the node image already built and
# reads its code from this checkout, so a restart takes what was just pulled; Caddy is recreated for its door
# node.tauhud.com/guardian/* (a few seconds without HTTPS). up guardian status  only prints its numbers.
if [ "${1:-}" = "guardian" ]; then
  if [ "${2:-}" != "status" ]; then
    docker compose up -d --no-deps guardian
    docker compose restart guardian >/dev/null
    docker compose up -d --no-deps --force-recreate caddy >/dev/null
    echo "waiting 8 s…"; sleep 8
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T guardian python /guardian/guardian.py status 2>&1 || docker compose logs --tail 15 guardian 2>&1
  curl -s -o /dev/null -w "          door https://node.tauhud.com/guardian/info answers %{http_code}\n" https://node.tauhud.com/guardian/info || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# Tau Language on tauhud.com/learn (checker/tau_sandbox.py, POST /tau): the checker recreated with the code just pulled,
# nothing built, Caddy given /tau, the node left alone (safe any time); then every lesson example asked of the real engine
if [ "${1:-}" = "tau" ]; then
  if [ "${2:-}" != "status" ]; then
    # No Memo's intel contracts deal their hidden rules from this secret (checker/intel.py): made once here, kept in .env,
    # so a restart of the checker does not deal every player's rule anew
    if ! grep -q '^INTEL_SECRET=.' .env 2>/dev/null; then
      [ -s .env ] && [ -n "$(tail -c1 .env)" ] && echo >> .env   # the last line ends first
      printf 'INTEL_SECRET=%s\n' "$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')" >> .env; chmod 600 .env
      echo "made INTEL_SECRET in .env (No Memo's intel contracts)"
    fi
    docker compose up -d --no-deps --force-recreate checker >/dev/null
    docker compose up -d --no-deps --force-recreate caddy >/dev/null
    echo "waiting 8 s…"; sleep 8
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T checker python -I /checker/tau_selftest.py 2>&1 || docker compose logs --tail 15 checker 2>&1
  curl -s -o /dev/null -w "          door https://node.tauhud.com/tau/health answers %{http_code}\n" https://node.tauhud.com/tau/health || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the relay alone, the node left alone (relay/services.py feeds tauhud.com/services/): rebuilt and restarted with the code
# just pulled. Pages reconnect by themselves within seconds; a cruise ship sends through the relay, so not while one is due.
if [ "${1:-}" = "services" ]; then
  if [ "${2:-}" != "status" ]; then
    when=$(TZ=Europe/Berlin date +%u%H)
    case "$when" in 315|316|317|410|411|613|614|615|616)
      if [ "${2:-}" != "--now" ]; then
        echo "a cruise ship or the hack replay is due or under way now (German time $(TZ=Europe/Berlin date +%a\ %H:%M)); the relay stays as it is."
        echo "try again after the visit, or: up services --now"; exit 1
      fi ;;
    esac
    docker compose up -d --build --no-deps relay
    echo "waiting 20 s for the relay to read the chain…"; sleep 20
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T relay python -c 'import json,urllib.request
d=json.load(urllib.request.urlopen("http://127.0.0.1:8080/services", timeout=20)); t=d["totals"]
print("services: %s found (co-signers %s, rule givers %s, paid with terms %s, paid by many %s), %s wallets served, blocks since %s" % (t["services"], t["cosign"], t["rules"], t["terms"], t["paid"], t["wallets"], d.get("since")))
for r in d["services"][:12]: print("  %-10s %s… %s, %s wallets" % (r["app"] or "", r["address"][:12], "+".join(r["kinds"]), r["wallets"]))' 2>&1 || echo "relay /services not answering yet"
  curl -s -o /dev/null -w "          page https://tauhud.com/services/ answers %{http_code}\n" https://tauhud.com/services/ || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the three showcase wallets (relay/showcase.py): each holds a personal rule and once a day tries a payment its rule
# forbids, so the HUD's feed shows "Stopped by the sender's own rule". up showcase  the relay rebuilt alone with the code
# just pulled (the node left alone; not while a cruise ship is due, --now overrides), then the wallets; the rules go on
# the chain within minutes by themselves. up showcase status  only the wallets, nothing rebuilt
if [ "${1:-}" = "showcase" ]; then
  if [ "${2:-}" != "status" ]; then
    when=$(TZ=Europe/Berlin date +%u%H)
    case "$when" in 315|316|317|410|411|613|614|615|616)
      if [ "${2:-}" != "--now" ]; then
        echo "a cruise ship or the hack replay is due or under way now (German time $(TZ=Europe/Berlin date +%a\ %H:%M)); the relay stays as it is."
        echo "try again after the visit, or: up showcase --now"; exit 1
      fi ;;
    esac
    docker compose up -d --build --no-deps relay
    echo "waiting 20 s for the relay to read the chain…"; sleep 20
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T relay python -c 'import json,time,urllib.request
d=json.load(urllib.request.urlopen("http://127.0.0.1:8080/showcase", timeout=20))
if not d.get("ready"): print("showcase: not ready (enabled=%s); see: docker compose logs relay | grep showcase" % d.get("enabled")); raise SystemExit
for k, w in d["wallets"].items():
    t = w.get("last_try") or {}
    print("%-9s %s… %-32s rule %s · try %02d:00 %s" % (k, w["pk"][:10], w["name"], "IN FORCE" if w["in_force"] else "not yet", w["daily_try"]["german_hour"], "(stopped: lock open)" if w["daily_try"]["stopped"] else ""))
    if t: print("          last try %s: %s · %s" % (time.strftime("%d.%m %H:%M", time.gmtime(t["t"])) + "Z", t["outcome"], t["what"]))
print("cosigner  %s… %s" % (d["cosigner"]["pk"][:10], d["cosigner"]["name"]))
for n in d.get("log", [])[-6:]: print("  · %s %s: %s" % (time.strftime("%d.%m %H:%M", time.gmtime(n["t"])) + "Z", n["wallet"], n["note"][:110]))' 2>&1 || echo "relay /showcase not answering yet"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# Tau today for AI assistants (alerts/knowledge.py, run by devpulse every 30 minutes): node.tauhud.com/tau-today.md and
# .json, read by tauhud.com/facts/ and llms.txt. The node is left alone; Caddy is recreated for the two files (a few
# seconds without HTTPS). A fact whose IDNI source changed since it was checked shows here as "to check again".
if [ "${1:-}" = "knowledge" ]; then
  if [ "${2:-}" != "status" ]; then
    docker compose up -d --build --no-deps devpulse
    docker compose up -d --no-deps --force-recreate caddy >/dev/null
    echo "waiting 8 s…"; sleep 8
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T devpulse python knowledge.py 2>&1 | grep -v ' INFO ' | tail -3
  curl -s -o /dev/null -w "          https://node.tauhud.com/tau-today.md answers %{http_code}\n" https://node.tauhud.com/tau-today.md || true
  curl -s -o /dev/null -w "          https://tauhud.com/llms.txt answers %{http_code}\n" https://tauhud.com/llms.txt || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the posts' island picture (alerts/island_pic.py): the Key Crier's X post and the closer look at the game carry the
# painting the game shows now, never a repo screenshot. The posting service is rebuilt alone (it gets the art folder),
# Caddy is recreated for node.tauhud.com/island/* (a few seconds without HTTPS); the node and the relay are left alone.
# Agorzilla's evening posts (alerts/agorzilla.py) with the code just pulled: only that service is rebuilt, the node and
# the relay are left alone (rules v5 on agorzilla.com: a kept look is posted as "stays", never "became")
if [ "${1:-}" = "agorzilla" ]; then
  docker compose up -d --build --no-deps agorzilla
  echo "waiting 8 s…"; sleep 8
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose ps agorzilla --format '          agorzilla: {{.Status}}' 2>/dev/null || docker compose ps agorzilla
  docker compose exec -T agorzilla python -c 'import agorzilla as A; print("          kept looks posted as stays:", "stays" in A.text({"n": 0, "category": "Sky", "options": ["A", "B", "C"], "tally": [1, 0, 0], "winner": "A", "kept": True}, {}))' 2>&1 | tail -1
  echo "---------------- to here --------------------------------------"
  exit 0
fi
if [ "${1:-}" = "crier" ]; then
  if [ "${2:-}" != "status" ]; then
    docker compose up -d --build --no-deps alerts
    docker compose up -d --no-deps --force-recreate caddy >/dev/null
    echo "waiting 8 s…"; sleep 8
  fi
  echo
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T alerts python -c 'import alerts
print("today:   " + str(alerts.island_picture()))
r = {"date": "6 November", "campaigns": 4, "moves": 23, "wins": [("Hana", 1)], "law": None}
print("preview: " + str(alerts.island_picture(alerts.island_card(r), "preview.jpg")))' 2>&1 | grep -v " INFO " || true
  curl -s -o /dev/null -w "          https://node.tauhud.com/island/today.jpg answers %{http_code}\n" https://node.tauhud.com/island/today.jpg || true
  echo "look: https://node.tauhud.com/island/preview.jpg (a sample story day, made-up numbers, never posted)"
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# what the site's tools were paid (alerts/receipts.py, the costs service; tauhud.com/donate/ shows it), the node left
# alone, safe any time: up cost  the service started with the code just pulled and Caddy given costs-paid.json, then one
# read of the receipts; up cost mail  asks for the mailbox and its app password once (ssh -t), writes them to .env;
# up cost gemini 10 [EUR] [2026-11-08]  a payment by hand (its receipt replaces it later); up cost drop <id>  one taken off
# what the X API costs this month, estimated from what was sent (X bills each post: $0.015, $0.20 with a link; the bill
# itself and the credit left: console.x.com): the alerts posts counted by alerts.py, plus one link post per blog article
# published this month (blog.py announce, X_BLOG_LINK); hand-sent pictures and clips (up post) are not counted
x_line() {
  XN=$(docker compose exec -T alerts python -c 'import json,time; x=json.load(open("/state/alerts.json")).get("x",{}); print(x.get("this_month",0) if x.get("month")==time.strftime("%Y-%m") else 0)' 2>/dev/null | tr -dc 0-9)
  XB=$(docker compose exec -T blog python -c 'import json,os,time; p=json.load(open(os.path.join(os.environ.get("PUBLIC_DIR","/public"),"blog","posts.json"))).get("posts",[]); m=time.strftime("%Y-%m"); print(sum(1 for a in p if str(a.get("on","")).startswith(m)))' 2>/dev/null | tr -dc 0-9)
  awk -v n="${XN:-0}" -v b="${XB:-0}" -v d="$(date -u +%d)" 'BEGIN { c = n * 0.015 + b * 0.20; printf "x:       %d posts and %d blog link posts this month, about $%.2f so far, about $%.2f for the whole month at this pace (estimate; the bill: console.x.com)\n", n, b, c, c * 30 / (d < 1 ? 1 : d) }'
}
# the crew's ship log (alerts/crewlog.py), a members-only post in the Tau HUD crew on Fourthwall, the node left alone:
# up crewlog  the posting service rebuilt with the code just pulled, the API user checked (tiers, members, the newest
# posts as stored) and this week's post printed, nothing posted; up crewlog send  posts it now; up crewlog on / off
# posts one every Monday after the weekly recap by itself, or stops that (CREWLOG_ENABLED in .env); up crewlog key  asks for
# the shop's API user once (ssh -t) and writes it to .env
if [ "${1:-}" = "crewlog" ]; then
  if [ "${2:-}" = "key" ]; then
    [ -t 0 ] || { echo "needs a terminal: ssh -t root@node.tauhud.com \"cd /opt/tau-command-hud && sh infra/up.sh crewlog key\""; exit 2; }
    printf "Fourthwall API username (Settings, For developers, Open API): "; read -r U
    printf "Fourthwall API password (nothing shows while typing): "
    stty -echo; read -r P; stty echo; echo
    [ -n "$U" ] && [ -n "$P" ] || { echo "nothing written"; exit 2; }
    touch .env; sed -i '/^FOURTHWALL_API_USER=/d; /^FOURTHWALL_API_PASS=/d' .env; [ -s .env ] && [ -n "$(tail -c1 .env)" ] && echo >> .env
    printf 'FOURTHWALL_API_USER=%s\nFOURTHWALL_API_PASS=%s\n' "$U" "$P" >> .env; chmod 600 .env
    echo "written to infra/.env"
  fi
  case "${2:-}" in
    on|off) touch .env; sed -i '/^CREWLOG_ENABLED=/d' .env; [ -s .env ] && [ -n "$(tail -c1 .env)" ] && echo >> .env
            printf 'CREWLOG_ENABLED=%s\n' "$([ "$2" = on ] && echo true || echo false)" >> .env; chmod 600 .env ;;
  esac
  docker compose up -d --build --no-deps alerts >/dev/null 2>&1 || docker compose up -d --build --no-deps alerts
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T alerts python alerts.py --crewlog $([ "${2:-}" = send ] && echo send) 2>&1 | grep -v " INFO " || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# Tau HUD in ONE Telegram group (alerts/tgnews.py): up telegram  rebuilds the services that post to Telegram with the
# code just pulled (the node left alone, safe any time) and makes the group ready: a closed News topic only the bot
# writes in, General renamed Chat; posts nothing. up telegram @name  first writes TELEGRAM_CHAT_ID=@name into infra/.env
# (only needed when the group's public link is not @tauHUDchat); up telegram -100123…  the same with the group's id.
if [ "${1:-}" = "telegram" ]; then
  case "${2:-}" in
    @*|-100*) touch .env; sed -i '/^TELEGRAM_CHAT_ID=/d' .env; [ -s .env ] && [ -n "$(tail -c1 .env)" ] && echo >> .env
              printf 'TELEGRAM_CHAT_ID=%s\n' "$2" >> .env; chmod 600 .env; echo "TELEGRAM_CHAT_ID=$2 written to infra/.env" ;;
  esac
  docker compose up -d --build --no-deps alerts bot blog donations agorzilla >/dev/null 2>&1 || docker compose up -d --build --no-deps alerts bot blog donations agorzilla
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T alerts python alerts.py --telegram-setup 2>&1 | grep -v " INFO " || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# our share of the shop's sales and the crew's memberships (alerts/earnings.py), drawn on tauhud.com/donate/; the node left
# alone, safe any time: up earnings  the service rebuilt with the code just pulled, Caddy given earnings.json, the shop
# read now: each order's numbers beside the share worked out (compare with the shop's dashboard), memberships counted
if [ "${1:-}" = "earnings" ]; then
  docker compose up -d --build --no-deps alerts >/dev/null 2>&1 || docker compose up -d --build --no-deps alerts
  docker compose up -d --no-deps --force-recreate caddy >/dev/null 2>&1 || true
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T alerts python alerts.py --earnings 2>&1 | grep -v " INFO " || true
  curl -s -o /dev/null -w "         https://node.tauhud.com/earnings.json answers %{http_code}\n" https://node.tauhud.com/earnings.json || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
if [ "${1:-}" = "cost" ] || [ "${1:-}" = "costs" ]; then
  if [ "${2:-}" = "mail" ]; then
    [ -t 0 ] || { echo "needs a terminal: ssh -t root@node.tauhud.com \"cd /opt/tau-command-hud && sh infra/up.sh cost mail\""; exit 2; }
    printf "Gmail address the receipts go to: "; read -r U
    printf "App password (16 letters, https://myaccount.google.com/apppasswords; nothing shows while typing): "
    stty -echo; read -r P; stty echo; echo
    P=$(printf %s "$P" | tr -d ' ')
    [ -n "$U" ] && [ -n "$P" ] || { echo "nothing written"; exit 2; }
    touch .env; sed -i '/^COSTS_IMAP_USER=/d; /^COSTS_IMAP_PASSWORD=/d' .env
    printf 'COSTS_IMAP_USER=%s\nCOSTS_IMAP_PASSWORD=%s\n' "$U" "$P" >> .env; chmod 600 .env
    echo "written to infra/.env"
  fi
  docker compose up -d --build --no-deps costs >/dev/null 2>&1 || docker compose up -d --build --no-deps costs
  if [ -z "${2:-}" ] || [ "${2:-}" = "mail" ]; then
    docker compose up -d --no-deps --force-recreate caddy >/dev/null 2>&1 || true
  fi
  case "${2:-}" in
    drop) shift 2; docker compose exec -T costs python receipts.py drop "$@" ;;
    ""|mail|check) docker compose exec -T costs python receipts.py check 2>&1 | grep -v " INFO " | grep -v "^costs:\|^         " || true ;;
    *) shift; docker compose exec -T costs python receipts.py add "$@" ;;
  esac
  echo "---------------- copy from here into the chat ----------------"
  docker compose exec -T costs python receipts.py line
  x_line
  curl -s -o /dev/null -w "         https://node.tauhud.com/costs-paid.json answers %{http_code}\n" https://node.tauhud.com/costs-paid.json || true
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the node following IDNI tau-testnet main by itself (follow/idni_follow.py, a systemd timer every 30 min that every up
# installs): up follow  its state and last log lines, up follow now  one check at once (in the background),
# up follow retry  tries a failed commit again, up follow off  stops following (the node stays on the commit it runs), up follow on  starts again; nothing rebuilt
if [ "${1:-}" = "follow" ]; then
  case "${2:-}" in
    now|on|off|retry) python3 follow/idni_follow.py "$2" ;;
    *) python3 follow/idni_follow.py install >/dev/null 2>&1 || true ;;
  esac
  echo "---------------- copy from here into the chat ----------------"
  echo "idni:    node follow"
  python3 follow/idni_follow.py status
  python3 follow/idni_follow.py log | sed 's/^/         /'
  echo "---------------- to here --------------------------------------"
  exit 0
fi
# the blog by hand, nothing rebuilt (alerts/blog.py): up blog  lists the drafts waiting and where to read them,
# up blog publish <id>  puts one on the blog and posts it once, up blog draft <visit-id>  writes one anew,
# up blog unpublish <id>  takes one off again, up blog pictures  makes every article's hero picture and link preview anew
if [ "${1:-}" = "blog" ]; then
  shift
  [ -n "${1:-}" ] || set -- drafts
  # rebuilt with the code just pulled first (safe any time, the node left alone; nothing changes when the code did not),
  # so publish, auto-publish and up blog pictures use it
  docker compose up -d --no-deps --build blog >/dev/null 2>&1 || docker compose up -d blog >/dev/null 2>&1 || true
  docker compose exec -T blog python blog.py "$@"
  exit $?
fi
cp sites/agorzilla.caddy /opt/sites/ 2>/dev/null || true
# The pinned tau-testnet commit follows the repo, not the server's old .env (as in setup.sh); a new pin
# rebuilds and restarts the node (a few minutes, tau-lang itself stays cached).
# Auto-follow (follow/idni_follow.py) may have moved the node to a newer IDNI main since: that commit stays while the
# repo pin is the one it followed from; a repin merged here wins over it.
REF=$(python3 follow/idni_follow.py ref 2>/dev/null || true)
[ -n "$REF" ] || REF=$(grep '^TAU_TESTNET_REF=' .env.example | cut -d= -f2)
[ -n "$REF" ] && [ -f .env ] && sed -i "s/^TAU_TESTNET_REF=.*/TAU_TESTNET_REF=${REF}/" .env
docker compose up -d --build
# Node images of older pins are several GB each and are never used again (the disk filled up on 2026-10-27).
[ -n "$REF" ] && docker images tau-testnet-standalone --format '{{.Repository}}:{{.Tag}}' | grep -v ":${REF}\$" \
  | xargs -r docker rmi >/dev/null 2>&1 || true
docker compose up -d --force-recreate caddy
echo "waiting 20 s…"
sleep 20
NOTE=$(mktemp)
# the node and the relay, then White Rabbit Key's island: the day, the running week and what last week decided
curl -s https://node.tauhud.com/status > "$NOTE.status" || true
curl -s https://node.tauhud.com/isle > "$NOTE.isle" || true
curl -s https://node.tauhud.com/cruise > "$NOTE.cruise" || true
curl -s https://node.tauhud.com/devpulse.json > "$NOTE.pulse" || true
python3 - "$NOTE.status" "$NOTE.isle" "$NOTE.cruise" "$NOTE.pulse" <<'PY' | tee -a "$NOTE"
import json, sys
def read(path, what):
    try:
        return json.load(open(path))
    except Exception:
        print(f"{what}no answer from the relay"); return None
s = read(sys.argv[1], "node:    ")
if s:
    h = s.get("health") or {}
    print(f"node:    height {s.get('height')} (tip {s.get('tip_height')}), {s.get('clients')} sockets, {s.get('online')} online, "
          f"{h.get('label')} {h.get('score')}, relay up {s.get('uptime_seconds')} s")
    if s.get("sender_connected") is not None:
        print(f"         ship+bot connection: {'up' if s.get('sender_connected') else 'DOWN (they borrow the visitors one after 60 s)'}")
s = read(sys.argv[2], "island:  ")
if s:
    w = s.get("week") or {}; l = s.get("last") or {}
    print(f"island:  day {s.get('day')}, {len(s.get('players') or [])} players, week {w.get('id')}: {w.get('campaigns', 0)} campaigns, "
          f"{w.get('finished', 0)} finished, wins {w.get('wins') or {}}")
    print(f"         last week: governor {l.get('governor') or 'none yet'}, laws {l.get('laws') or []}")
# the cruise ships (relay/cruise.py): in port or the next call, the passengers' wallets, the kinds already used cleanly
s = read(sys.argv[3], "ships:   ")
if s:
    import datetime as dt
    try:
        from zoneinfo import ZoneInfo
        tz, zn = ZoneInfo("Europe/Berlin"), "German time"
    except Exception:
        tz, zn = dt.timezone.utc, "UTC"
    at = lambda t: dt.datetime.fromtimestamp(t, tz).strftime("%a %d.%m. %H:%M")
    v, n = s.get("now") or {}, s.get("next") or {}
    wallets = sum(len(x) for x in (s.get("wallets") or {}).values())
    seats = sum(x.get("passengers", 0) for x in (s.get("ships") or {}).values())
    tried = [k for k, x in (s.get("tried") or {}).items() if x] or ["none yet"]
    if not s.get("enabled"):
        print("ships:   switched off (CRUISE_ENABLED=0 in .env)")
    else:
        here = f"{v.get('name')} {v.get('phase')}, {v.get('ashore', 0)} ashore; " if v else ""
        print(f"ships:   {here}next {n.get('name')} {at(n['t0'])} {zn}" if n else f"ships:   {here}no call ahead")
        print(f"         {wallets} of {seats} passenger wallets made, kinds tried: {', '.join(tried)}, logbook https://node.tauhud.com/cruise/log")
    for e in (s.get("escrow") or [])[:1]:   # bookings ahead of the next call (relay/cruise.py escrow)
        c = ", ".join(f"{k} {x}" for k, x in (e.get("count") or {}).items()) or "none"
        off = f", called off: {e['called_off']['why']}" if e.get("called_off") else ""
        print(f"escrow:  {e.get('name')} {at(e['arrival'])}: {c}{off}")
# in sync with IDNI (alerts/devpulse.py, every 30 min): is our node on the newest tau-testnet main, does IDNI's build
# use our tau-lang commit, do our node patches still apply to the newest main
s = read(sys.argv[4], "idni:    ")
if s is not None:
    y = s.get("sync") or {}
    t, l, p = y.get("testnet") or {}, y.get("tau_lang") or {}, y.get("patches")
    short = lambda x: (x or "?")[:7]
    if not y:
        print("idni:    no sync check yet (devpulse is just starting; the next up shows it)")
    elif t.get("ahead") == 0:
        print(f"idni:    our node runs the newest tau-testnet main ({short(t.get('pin'))})")
    else:
        print(f"idni:    tau-testnet main is {t.get('ahead')} commits ahead of our node ({short(t.get('pin'))} -> {short(t.get('head'))}):")
        for b in (t.get("behind") or [])[:5]:
            print(f"         {short(b.get('sha'))} {b.get('text')}")
    ai = s.get("news_ai") or "not running yet"
    heads = [n.get("headline", {}).get("en") for n in s.get("news") or [] if n.get("headline")]
    print(f"         news line: {len(heads)} IDNI headlines in 14 days, writer {ai}" + (f"; newest: {heads[0]}" if heads else ""))
    dg = s.get("digest") or {}
    if dg:
        import datetime as dt2
        hm = lambda t: dt2.datetime.fromtimestamp(t, dt2.timezone.utc).strftime("%a %d.%m. %H:%M UTC") if t else "?"
        la = dg.get("last") or {}
        print(f"         daily post: {dg.get('state')}; next {hm(dg.get('next_at'))}, covering since {hm(dg.get('since'))}"
              + (f"; last: {la.get('status')} {la.get('title') or ''}".rstrip() if la else "") + " (up idni shows it)")
    if y and not l.get("same"):
        print(f"         tau-lang: IDNI's build uses {short(l.get('idni'))}, ours {short(l.get('ours'))}")
    if p:
        bad = [r for r in p.get("results") or [] if r.get("ok") is False]
        if bad:
            print(f"         patches on main {short(p.get('sha'))}: {bad[0]['name']} no longer applies ({bad[0].get('error') or 'see devpulse log'}); a pin bump needs it reworked")
        elif t.get("ahead"):
            print(f"         all {len(p.get('results') or [])} node patches apply to main {short(p.get('sha'))}: a pin bump can be built (then test it)")
PY
# the node following IDNI main by itself (follow/idni_follow.py): its timer (made anew by every up), what it follows, held back
python3 follow/idni_follow.py install >/dev/null 2>&1 || true
python3 follow/idni_follow.py status 2>/dev/null | tee -a "$NOTE" || true
# Tau today for AI assistants (alerts/knowledge.py): how many facts, which to check again because IDNI changed their source
python3 - <<'PY' | tee -a "$NOTE"
import json, time, urllib.request
try:
    d = json.load(urllib.request.urlopen("https://node.tauhud.com/tau-today.json", timeout=20)); f = d["facts"]; st = f.get("stale") or {}
    print(f"facts:   {len(f.get('items') or [])} for AI assistants (checked {f.get('checked')}), "
          + (f"{len(st)} to check again: {', '.join(sorted(st))}" if st else "none to check again") + ", written " + time.strftime("%d.%m. %H:%M UTC", time.gmtime(d.get("generated_at") or 0)))
except Exception as e:
    print(f"facts:   tau-today not written yet ({str(e)[:60]}); the build pulse writes it within a few minutes, up knowledge status shows it")
PY
# the channels: may the service post at all? (asks Telegram and X, posts nothing; a refused key or a bot without the
# right to post is named here, so the channel can never go quiet unnoticed), then what the running containers logged
# the blog: drafts written after a cruise visit wait here for a read and an up blog publish <id>
docker compose exec -T blog python blog.py drafts 2>/dev/null | tee -a "$NOTE" || true
# the HUD's news line (alerts/tickerwatch.py): how many new items it holds, what leaves soon, what is stale
docker compose exec -T alerts python tickerwatch.py status 2>/dev/null | tee -a "$NOTE" || true
echo "channels:" | tee -a "$NOTE"
docker compose run --rm --no-deps -T alerts python alerts.py --check 2>/dev/null | sed 's/^/         /' | tee -a "$NOTE"
echo "posts logged by the running containers (a rebuild starts the log afresh):" | tee -a "$NOTE"
docker compose logs --since 48h alerts agorzilla 2>/dev/null | grep -iE 'posted|failed|cannot post|silent|cap|lost' | tail -12 | sed 's/^/         /' | tee -a "$NOTE"
# White Rabbit Key's island: the places' names and click areas as the repo has them (plates/island-22.json), so a renamed
# or moved place goes live with the merge; only when the live island was laid out from that very file
python3 - <<'PY' | tee -a "$NOTE"
import json
try:
    path = "/opt/sites/rico/art/index.json"; idx = json.load(open(path)); lay = json.load(open("rabbit-art/plates/island-22.json"))
    old = idx.get("layout") or {}
    if set((old.get("places") or {})) == set(lay["places"]) and old != lay:
        idx["layout"] = lay; json.dump(idx, open(path, "w"), indent=1); print("island:  places updated from the repo (names, click areas, outlines)")
except Exception as e:
    print(f"island:  places not checked ({e})")
PY
# the drafts page (https://node.tauhud.com/rico/art/drafts/) as paint.py writes it now: the newest island versions
# large, two of them in one frame to compare
sh rabbit-art/paint.sh page >/dev/null 2>&1 || true
# Radio Coco and the islanders: speak any new voice lines (only lines without a clip cost credits; none new, nothing spent)
V=$(mktemp)
python3 rico/make.py make 2>&1 | tee "$V" || true
{ echo "voices:"; grep -E 'lines to make|credits left|wait\. Run|^Done:|No voice|GEMINI|ELEVEN|Error|error' "$V" | tail -4 | sed 's/^/         /'; } | tee -a "$NOTE"
# one room painted anew to match the island as it is, only when asked for: up room grotto (or several: up room grotto canoe)
if [ "${1:-}" = "room" ] && [ -n "${2:-}" ]; then
  shift
  ROOMS="$*"; KEEP=""; for r in $ROOMS; do KEEP="$KEEP $r=last"; done
  { sh rabbit-art/paint.sh draft $ROOMS --wide --n 1 --look 2 && sh rabbit-art/paint.sh keep $KEEP; } 2>&1 | tee "$V" || true
  { echo "room art:"; if grep -qE 'Traceback|Error|error|No place' "$V"; then grep -E 'Traceback|Error|error|No place' "$V" | tail -3 | sed 's/^/         /'; else echo "         $ROOMS painted anew and live (Ctrl+F5)"; fi; } | tee -a "$NOTE"
fi
# small changes to the island as it is (or to draft island N: up touch beach 28), painted twice to choose from
# (names in paint.py TOUCH_SETS);
# nothing goes live; then: up keep <number> <rooms to paint anew>, e.g. up keep 27 canoe camp
if [ "${1:-}" = "touch" ] && [ -n "${2:-}" ]; then
  FROM=""; [ -n "${3:-}" ] && FROM="--from island=$3"   # up touch beach 28: from island 28 instead of the live one
  sh rabbit-art/paint.sh touch "$2" $FROM --n 2 2>&1 | tee "$V" || true
  NEW=$(sed -n 's/^ *island=\([0-9][0-9]*\):.*/\1/p' "$V" | tr '\n' ' ')
  { echo "island art:"; if [ -n "$NEW" ]; then echo "         new islands (not live yet): $NEW  look: https://node.tauhud.com/rico/art/drafts/"; else grep -E 'Traceback|Error|error' "$V" | tail -3 | sed 's/^/         /'; fi; } | tee -a "$NOTE"
fi
if [ "${1:-}" = "keep" ] && [ -n "${2:-}" ]; then
  N="$2"; shift 2
  case "$N" in *[!0-9]*) echo "Usage: up keep <island number> [rooms]"; exit 1;; esac
  ROOMS="$*"; KEEP=""; for r in $ROOMS; do KEEP="$KEEP $r=last"; done
  # a new island can bring a new place: let GitHub Pages serve the merged game first (at most 15 minutes), so nobody
  # meets the new layout with the old game
  W=0; while [ "$W" -lt 45 ]; do
    [ "$(curl -s "https://tauhud.com/rabbit/game.js?up=$(date +%s)" | sha256sum | cut -c1-64)" = "$(sha256sum ../rabbit/game.js | cut -c1-64)" ] && break
    [ "$W" -eq 0 ] && echo "waiting for tauhud.com to serve the merged game (GitHub Pages, up to 15 minutes) ..."
    W=$((W + 1)); sleep 20
  done
  { sh rabbit-art/paint.sh keep island="$N" --layout island-22 && if [ -n "$ROOMS" ]; then sh rabbit-art/paint.sh draft $ROOMS --wide --n 1 --look 2 && sh rabbit-art/paint.sh keep $KEEP; fi; } 2>&1 | tee "$V" || true
  { echo "island art:"; if grep -qE 'Traceback|Error|error|No painting' "$V"; then grep -E 'Traceback|Error|error|No painting' "$V" | tail -3 | sed 's/^/         /'; else echo "         Island $N live${ROOMS:+, rooms painted anew: $ROOMS} (Ctrl+F5)"; fi; } | tee -a "$NOTE"
fi
# a portrait painted anew, only when asked for: up bust salado (or several: up bust salado rico); every painting is kept
# as it came, so a better cut later paints nothing: up bust --recut salado; pictures painted elsewhere and put in the
# repository: up bust --from infra/rabbit-art/imports/codex hana lola
if [ "${1:-}" = "bust" ] && [ -n "${2:-}" ]; then
  shift
  WHO=$(echo " $* " | sed 's/ --from [^ ]*//; s/ --[a-z]*//g; s/^ *//; s/ *$//')
  case " $* " in *" --recut "*) DID="cut out again from the kept painting";; *" --from "*) DID="taken from the pictures in the repository";; *) DID="painted anew";; esac
  sh rabbit-art/paint.sh busts "$@" 2>&1 | tee "$V" || true
  { echo "portraits:"; if grep -qE 'Traceback|Error|error|painter|No one called|No portrait|No bust|o painting kept|GEMINI|Keep an island' "$V"; then grep -E 'Traceback|Error|error|painter|No one called|No portrait|No bust|o painting kept|GEMINI|Keep an island' "$V" | tail -3 | sed 's/^/         /'; else echo "         $WHO $DID and live (Ctrl+F5)"; fi; } | tee -a "$NOTE"
fi
# the owner's private chat for the news line's watchtower, only when asked for: up owner (then up owner test)
if [ "${1:-}" = "owner" ]; then
  if [ "${2:-}" = "test" ]; then
    docker compose exec -T alerts python tickerwatch.py test 2>&1 | tee -a "$NOTE" || true
  else
    docker compose exec -T alerts python tickerwatch.py pair 2>&1 | tee -a "$NOTE" || true
  fi
fi
# every painted room's own lamps for the night: a room painted anew (up room, up keep, up island) is looked at once
# (paint.py lights --missing, one short text answer per new room, nothing when all are known)
{ echo "room lights:"; sh rabbit-art/paint.sh lights --missing 2>&1 | grep -E '^lights:|Error|error|GEMINI|painter' | tail -2 | sed 's/^/         /'; } | tee -a "$NOTE" || true
# what the Gemini API cost this month, measured by paint.py at every call (tokens x Google's list price; the bill itself:
# https://aistudio.google.com/usage); GEMINI_MONTH_CAP in .env stops painting at that many dollars a month (default 10)
python3 rabbit-art/paint.py usage 2>/dev/null | tee -a "$NOTE" || true
# what the Anthropic API cost this month (blog drafts, IDNI news and daily post, troll box check), measured at every
# answer by alerts/ai_meter.py (tokens x Anthropic's list price; the bill itself: platform.claude.com/settings/billing)
docker compose exec -T alerts python ai_meter.py line 2>/dev/null | tee -a "$NOTE" || true
# what the site's tools were paid, read from their receipts (alerts/receipts.py; up cost for more)
docker compose exec -T costs python receipts.py line 2>/dev/null | tee -a "$NOTE" || true
x_line | tee -a "$NOTE" || true
# Kling's clips this month (alerts/kling.py; KLING_MONTH_CAP in .env, default 30 clips)
docker compose exec -T blog python kling.py line 2>/dev/null | tee -a "$NOTE" || true
# a new painted island, only when asked for: up island
if [ "${1:-}" = "island" ]; then
  sh island.sh auto 2>&1 | tee "$V"
  { echo "island art:"; grep -E '^Island|to switch' "$V" | sed 's/^/         /'; } | tee -a "$NOTE"
fi
echo
echo "---------------- copy from here into the chat ----------------"
cat "$NOTE"
echo "---------------- to here --------------------------------------"
rm -f "$NOTE" "$NOTE.status" "$NOTE.isle" "$NOTE.cruise" "$NOTE.pulse" "$V"
echo "done. next time just type: up   (or: up follow, up idni, up report, up blog, up hack, up nomemo, up guardian, up services, up knowledge, up kling, up cost, up crewlog, up earnings, up owner, up island, up room <place>, up touch <change>, up keep <number> <rooms>, up bust <name>)"
