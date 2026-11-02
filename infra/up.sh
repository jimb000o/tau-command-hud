#!/bin/sh
# One short command for the server after any merge: pull, rebuild whatever changed, recreate caddy once, speak any new
# voice lines, then print one block to paste into the chat. Safe to rerun; containers whose code did not change keep running.
# First time:  cd /opt/tau-command-hud && git pull && sh infra/up.sh
# After that:  up            everything above
#              up island     the same, then a new painted island with every room to match (a few minutes, see island.sh)
set -e
cd "$(dirname "$(readlink -f "$0")")"
ln -sf "$(pwd)/up.sh" /usr/local/bin/up 2>/dev/null && chmod +x up.sh 2>/dev/null || true
if [ "$1" != "--pulled" ]; then
  git -C .. pull --ff-only
  exec sh "$(pwd)/up.sh" --pulled "$@"
fi
shift
cp sites/agorzilla.caddy /opt/sites/ 2>/dev/null || true
docker compose up -d --build
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
        idx["layout"] = lay; json.dump(idx, open(path, "w"), indent=1); print("island:  places updated from the repo (names, click areas)")
except Exception as e:
    print(f"island:  places not checked ({e})")
PY
# Radio Coco and the islanders: speak any new voice lines (only lines without a clip cost credits; none new, nothing spent)
V=$(mktemp)
python3 rico/make.py make 2>&1 | tee "$V" || true
{ echo "voices:"; grep -E 'lines to make|credits left|wait\. Run|^Done:|No voice|GEMINI|ELEVEN|Error|error' "$V" | tail -4 | sed 's/^/         /'; } | tee -a "$NOTE"
# a new painted island, only when asked for: up island
if [ "$1" = "island" ]; then
  sh island.sh auto 2>&1 | tee "$V"
  { echo "island art:"; grep -E '^Island|to switch' "$V" | sed 's/^/         /'; } | tee -a "$NOTE"
fi
echo
echo "---------------- copy from here into the chat ----------------"
cat "$NOTE"
echo "---------------- to here --------------------------------------"
rm -f "$NOTE" "$NOTE.status" "$NOTE.isle" "$V"
echo "done. next time just type: up   (or: up island)"
