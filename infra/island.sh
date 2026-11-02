#!/bin/sh
# White Rabbit Key's island, in two short steps on the server:
#   sh infra/island.sh       paints two touched versions of island 22 (places as inside: pond and water wheel,
#                            villa pool, wooden radio hut, intact palace); look at them, then pick one
#   sh infra/island.sh N     keeps island N and paints every room anew to match it (21:9, one each)
set -e
cd "$(dirname "$0")/.."
git pull -q
P=infra/rabbit-art/paint.sh
ROOMS="hall market radio north south bar book pier school dive works camp ship ama canoe stone drums circle grotto"
if [ -z "${1:-}" ]; then
  $P touch --from island=22 --n 2
  echo
  echo "The two new islands are the numbers just above. Look at them (Ctrl+F5): https://node.tauhud.com/rico/art/drafts/"
  echo "Then: sh infra/island.sh <number of the better one>"
  exit 0
fi
case "$1" in *[!0-9]*) echo "Usage: sh infra/island.sh [island number]"; exit 1;; esac
$P keep island="$1" --layout island-22
$P draft $ROOMS --wide --n 1 --look 2
KEEP=""; for r in $ROOMS; do KEEP="$KEEP $r=last"; done
$P keep $KEEP
echo
echo "Island $1 and its rooms are live: https://tauhud.com/rabbit/ (Ctrl+F5)"
