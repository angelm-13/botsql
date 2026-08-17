#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-db}"; PORT="${2:-5432}"; TIMEOUT="${3:-60}"
for i in $(seq 1 "$TIMEOUT"); do if nc -z "$HOST" "$PORT" >/dev/null 2>&1; then exit 0; fi; sleep 1; done
echo "Timeout waiting for $HOST:$PORT"
exit 1
