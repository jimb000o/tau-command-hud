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
#              up blog       the blog drafts waiting (nothing rebuilt); up blog publish <id>  puts one on tauhud.com/blog/
#                            and posts it once to Telegram and X; up blog draft <visit>  writes that visit's draft anew
#              up bust salado  the same, then that portrait (or several) painted anew, talking and blinking too (1 min each);
#                            up bust --recut salado  cuts the kept painting out again, paints nothing;
#                            up bust --from infra/rabbit-art/imports/codex hana  takes pictures painted elsewhere
#              up idni       what the next daily IDNI progress post would say now (nothing rebuilt, nothing posted);
#                            up idni send  posts it now, up idni hold  keeps the next one back, up idni release  undoes that
#              up cruise     a cruise ship's last visit in numbers and the node's timeouts per hour (nothing rebuilt)
#                            up cruise next  the next call's announcement as it goes out by itself (posts nothing);
#                            announcements and reports run by themselves every week (alerts/cruise_crier.py)
#              up report     the weekly report for IDNI as it stands (nothing rebuilt, nothing filed): its text, a page
#                            and a pre-filled GitHub issue link; up report last  last week's; up report send  also to
#                            your Telegram (it comes there by itself every Sunday 18:00)
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
# a cruise ship's visit in numbers, nothing rebuilt, nothing sent (cruise-report.py): up cruise  the last visit,
# up cruise 2026-11-07-queen  that one; then the relay's sendtx timeouts per hour of the last 3 days
if [ "${1:-}" = "cruise" ]; then
  # up cruise next: the next call's announcement as it will go out by itself (texts and picture), posts nothing
  if [ "${2:-}" = "next" ]; then
    docker compose up -d blog >/dev/null 2>&1 || true
    docker compose exec -T blog python cruise_crier.py preview ${3:-}
    docker compose cp blog:/tmp/cruise-dryrun.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 || true
    docker compose cp blog:/tmp/cruise-queen.jpg /opt/sites/rico/art/drafts/ >/dev/null 2>&1 || true
    echo "look: https://node.tauhud.com/rico/art/drafts/cruise-queen.jpg (or cruise-dryrun.jpg)"
    exit 0
  fi
  docker compose cp cruise-report.py relay:/tmp/cruise-report.py >/dev/null
  docker compose exec -T relay python /tmp/cruise-report.py ${2:-}
  echo "sendtx timeouts per hour (UTC), last 3 days:"
  docker compose logs -t --since 72h relay 2>&1 | grep -E "(upstream|sender) sendtx failed" | awk '{print substr($3,1,13)}' | sort | uniq -c | sed 's/^/  /'
  exit 0
fi
# IDNI's progress of the day as ONE post, nothing rebuilt (alerts/idni_digest.py): up idni  the last ones and what the
# next would say now (one model call, posts nothing), up idni send  writes it now and the alerts service posts it within a
# minute (up idni send --force: also when the check marked numbers or wording), up idni hold / up idni release
if [ "${1:-}" = "idni" ]; then
  shift
  docker compose up -d devpulse >/dev/null 2>&1 || true
  docker compose exec -T devpulse python devpulse.py --digest "$@"
  exit $?
fi
# the weekly report for IDNI, nothing rebuilt, nothing filed (alerts/idni_report.py): up report  this week so far,
# up report last  last week, up report send  the page link to the owner's Telegram as well
if [ "${1:-}" = "report" ]; then
  shift
  docker compose up -d blog >/dev/null 2>&1 || true
  docker compose exec -T blog python idni_report.py "$@"
  exit $?
fi
# the blog by hand, nothing rebuilt (alerts/blog.py): up blog  lists the drafts waiting and where to read them,
# up blog publish <id>  puts one on the blog and posts it once, up blog draft <visit-id>  writes one anew,
# up blog unpublish <id>  takes one off again, up blog pictures  makes every article's hero picture and link preview anew
if [ "${1:-}" = "blog" ]; then
  shift
  [ -n "${1:-}" ] || set -- drafts
  docker compose up -d blog >/dev/null 2>&1 || true
  docker compose exec -T blog python blog.py "$@"
  exit $?
fi
cp sites/agorzilla.caddy /opt/sites/ 2>/dev/null || true
# The pinned tau-testnet commit follows the repo, not the server's old .env (as in setup.sh); a new pin
# rebuilds and restarts the node (a few minutes, tau-lang itself stays cached).
REF=$(grep '^TAU_TESTNET_REF=' .env.example | cut -d= -f2)
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
echo "done. next time just type: up   (or: up idni, up report, up blog, up owner, up island, up room <place>, up touch <change>, up keep <number> <rooms>, up bust <name>)"
