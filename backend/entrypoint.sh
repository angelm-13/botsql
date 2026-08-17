#!/usr/bin/env bash
set -euo pipefail
python - <<'PYWAIT'
import os, socket, time, sys
host=os.getenv('DB_HOST','db'); port=int(os.getenv('DB_PORT','5432'))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2): sys.exit(0)
    except OSError: time.sleep(1)
print(f"Database not reachable: {host}:{port}"); sys.exit(1)
PYWAIT

echo "🚀 Initializing database..."
python init_db.py

if [ "${FLASK_ENV:-development}" = "development" ]; then
  flask --app app run --host=0.0.0.0 --port=${BACKEND_PORT:-5001} --debug
else
  gunicorn "app:create_app()" --bind 0.0.0.0:${BACKEND_PORT:-5001} --workers 3 --timeout 120
fi
