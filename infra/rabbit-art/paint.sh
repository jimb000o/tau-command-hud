#!/usr/bin/env bash
# Runs paint.py in the share container (it has Pillow, for small WebP files), with the repository and the
# pictures folder mounted: infra/rabbit-art/paint.sh draft all | keep island=2 hall=1 | drop hall
set -eu
cd "$(dirname "$0")/../.."
mkdir -p /opt/sites/rico/art
exec docker compose -f infra/docker-compose.yml run --rm --no-deps -T \
  -v "$PWD:/repo:ro" -v /opt/sites/rico/art:/art --entrypoint python3 share /repo/infra/rabbit-art/paint.py --out /art "$@"
