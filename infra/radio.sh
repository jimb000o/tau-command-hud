#!/bin/sh
# Radio Coco's new voices: speaks every line that has no clip yet (the show's opener, the phone-in conversations,
# the chain news) with the ElevenLabs key in infra/.env. Safe to run again any time: it only makes what is missing,
# and with too few credits left it makes what fits and the rest after the monthly renewal.
#   cd /opt/tau-command-hud && git pull && sh infra/radio.sh
set -e
cd "$(dirname "$0")/.."
python3 infra/rico/make.py make
echo "Radio Coco: done. The new lines play in the game as soon as their clips are listed."
