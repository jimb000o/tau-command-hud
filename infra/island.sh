#!/bin/sh
# White Rabbit Key's island, painted anew on the server. Three ways:
#   sh infra/island.sh auto  paints two touched versions of island 22 (places as inside: pond and water wheel, villa pool,
#                            wooden radio hut, intact palace), keeps the first, and paints every room anew to match it
#                            (21:9, one each). Nothing to choose; a few minutes. Also runs as the last step of: up island
#   sh infra/island.sh       paints the two versions only; look at them, then pick one with the next line
#   sh infra/island.sh N     keeps island N and paints every room anew to match it
# Switching later costs the rooms again (19 pictures), the islands themselves stay in the drafts.
set -e
cd "$(dirname "$0")/.."
git pull -q
P=infra/rabbit-art/paint.sh
ROOMS="hall market radio north south bar book pier school dive works camp ship ama canoe stone drums circle grotto"
OTHER=""
if [ -z "${1:-}" ] || [ "$1" = "auto" ]; then
  NEW=$($P touch --from island=22 --n 2 | tee /dev/stderr | sed -n 's/^ *island=\([0-9][0-9]*\):.*/\1/p')
  if [ "${1:-}" != "auto" ]; then
    echo
    echo "The two new islands are the numbers just above. Look at them (Ctrl+F5): https://node.tauhud.com/rico/art/drafts/"
    echo "Then: sh infra/island.sh <number of the better one>"
    exit 0
  fi
  set -- $NEW
  [ -n "${1:-}" ] || { echo "No new island was painted (see above)."; exit 1; }
  OTHER="${2:-}"
fi
case "$1" in *[!0-9]*) echo "Usage: sh infra/island.sh [auto | island number]"; exit 1;; esac
$P keep island="$1" --layout island-22
$P draft $ROOMS --wide --n 1 --look 2
KEEP=""; for r in $ROOMS; do KEEP="$KEEP $r=last"; done
$P keep $KEEP
echo
echo "Island $1 and its rooms are live: https://tauhud.com/rabbit/ (Ctrl+F5)"
[ -n "$OTHER" ] && echo "The other new one is island $OTHER; to switch: sh infra/island.sh $OTHER" || true
