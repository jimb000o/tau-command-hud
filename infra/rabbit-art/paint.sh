#!/usr/bin/env bash
# Runs paint.py on the server: infra/rabbit-art/paint.sh draft all | keep island=2 hall=1 | drop hall
# Pillow (apt-get install -y python3-pil) makes the paintings small WebP files; without it they stay as they came.
set -eu
cd "$(dirname "$0")/../.."
python3 -c "import PIL" 2>/dev/null || echo "Tip: apt-get install -y python3-pil makes the pictures much smaller."
exec python3 -u infra/rabbit-art/paint.py "$@"
