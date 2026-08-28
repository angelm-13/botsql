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

# Las migraciones se venian aplicando a mano, sin registro de cuales. Una base
# nueva no tenia camino definido hasta el esquema actual, y sobre una existente
# nadie podia decir cual faltaba. El aplicador lleva ese registro y solo corre
# lo pendiente; si una falla, se detiene aqui en lugar de levantar el servidor
# contra un esquema a medias.
echo "📜 Applying pending migrations..."
python scripts/apply_migrations.py

if [ "${FLASK_ENV:-development}" = "development" ]; then
  flask --app app run --host=0.0.0.0 --port=${BACKEND_PORT:-5001} --debug
else
  gunicorn "app:create_app()" --bind 0.0.0.0:${BACKEND_PORT:-5001} --workers 3 --timeout 120
fi
