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
#              up bust salado  the same, then that portrait (or several) painted anew, talking and blinking too (1 min each);
#                            up bust --recut salado  cuts the kept painting out again, paints nothing
set -e
cd "$(dirname "$(readlink -f "$0")")"
ln -sf "$(pwd)/up.sh" /usr/local/bin/up 2>/dev/null && chmod +x up.sh 2>/dev/null || true
if [ "$1" != "--pulled" ]; then
  git -C .. pull --ff-only
  exec sh "$(pwd)/up.sh" --pulled "$@"
fi
shift
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
python3 - "$NOTE.status" "$NOTE.isle" <<'PY' | tee -a "$NOTE"
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
s = read(sys.argv[2], "island:  ")
if s:
    w = s.get("week") or {}; l = s.get("last") or {}
    print(f"island:  day {s.get('day')}, {len(s.get('players') or [])} players, week {w.get('id')}: {w.get('campaigns', 0)} campaigns, "
          f"{w.get('finished', 0)} finished, wins {w.get('wins') or {}}")
    print(f"         last week: governor {l.get('governor') or 'none yet'}, laws {l.get('laws') or []}")
PY
# the channels: may the service post at all? (asks Telegram and X, posts nothing; a refused key or a bot without the
# right to post is named here, so the channel can never go quiet unnoticed), then what the running containers logged
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
# as it came, so a better cut later paints nothing: up bust --recut salado
if [ "${1:-}" = "bust" ] && [ -n "${2:-}" ]; then
  shift
  WHO=$(echo " $* " | sed 's/ --[a-z]*//g; s/^ *//; s/ *$//')
  case " $* " in *" --recut "*) DID="cut out again from the kept painting";; *) DID="painted anew";; esac
  sh rabbit-art/paint.sh busts "$@" 2>&1 | tee "$V" || true
  { echo "portraits:"; if grep -qE 'Traceback|Error|error|painter|No one called|No portrait|o painting kept|GEMINI|Keep an island' "$V"; then grep -E 'Traceback|Error|error|painter|No one called|No portrait|o painting kept|GEMINI|Keep an island' "$V" | tail -3 | sed 's/^/         /'; else echo "         $WHO $DID and live (Ctrl+F5)"; fi; } | tee -a "$NOTE"
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
rm -f "$NOTE" "$NOTE.status" "$NOTE.isle" "$V"
echo "done. next time just type: up   (or: up island, up room <place>, up touch <change>, up keep <number> <rooms>, up bust <name>)"
