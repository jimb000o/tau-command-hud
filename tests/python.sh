#!/usr/bin/env bash
# Runs every Python test of the server parts (infra/*/test_*.py), each in its own folder, no network.
# infra/checker/test_checker.py is left out: it needs a built tau-testnet engine (run it inside the node image).
set -u
cd "$(dirname "$0")/../infra"
failed=()
for t in */test_*.py; do
  [ "$t" = "checker/test_checker.py" ] && continue
  dir=$(dirname "$t"); file=$(basename "$t")
  start=$(date +%s)
  if out=$(cd "$dir" && timeout 300 python3 "$file" 2>&1); then
    echo "✅ $t ($(( $(date +%s) - start )) s)"
  else
    echo "❌ $t"; echo "$out" | grep -E "FAIL|Error|Traceback|assert" | head -20 | sed 's/^/     /'
    failed+=("$t")
  fi
done
[ ${#failed[@]} -eq 0 ] || { echo; echo "${#failed[@]} Python test file(s) failed: ${failed[*]}"; exit 1; }
