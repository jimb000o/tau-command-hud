#!/bin/sh
# One short command for the server after any merge: pull, rebuild whatever changed, recreate caddy once,
# then show that the node and the relay answer. Safe to rerun; containers whose code did not change keep running.
# First time:  cd /opt/tau-command-hud && git pull && sh infra/up.sh
# After that:  up
set -e
cd "$(dirname "$(readlink -f "$0")")"
ln -sf "$(pwd)/up.sh" /usr/local/bin/up 2>/dev/null && chmod +x up.sh 2>/dev/null || true
if [ "$1" != "--pulled" ]; then
  git -C .. pull --ff-only
  exec sh "$(pwd)/up.sh" --pulled
fi
cp sites/agorzilla.caddy /opt/sites/ 2>/dev/null || true
docker compose up -d --build
docker compose up -d --force-recreate caddy
echo "waiting 20 s…"
sleep 20
curl -s https://node.tauhud.com/status | head -c 200; echo
curl -s https://node.tauhud.com/isle | head -c 200; echo
# the channel and X: what the posting services did in the last two days (a failed send names its cause)
echo "posts, last 48 h:"; docker compose logs --since 48h alerts agorzilla 2>/dev/null | grep -iE 'posted|failed|cap|off \(|lost' | tail -12
# voice lines that have no clip yet (spends credits only on new lines)
# Radio Coco and the islanders: speak any new voice lines (only lines without a clip cost credits; none new, nothing spent)
python3 rico/make.py make || echo "voices: skipped (see the message above); run again later with: up"
echo "done. next time just type: up"
