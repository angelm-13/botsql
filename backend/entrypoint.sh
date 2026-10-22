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

# scripts/apply_migrations.py (con su propio tracking por checksum) NO se
# llama aqui: requiere DATABASE_URL, que nunca ha existido ni en el Secret de
# k8s (DB_HOST/DB_NAME/DB_USER/DB_PASSWORD/DB_PORT por separado) ni en
# docker-compose.yml, asi que esta linea jamas llego a ejecutarse con exito en
# ningun ambiente donde corre la app -- siempre se cayo antes el
# initContainer de k8s (database/migrations/*.sql via psql -f, ver
# k8s/base/backend.yaml), que es el mecanismo real y ya corre antes de que
# este contenedor arranque. Es una herramienta de desarrollo aparte, para
# correr a mano con su propio DATABASE_URL.

# El servidor de desarrollo (con el depurador de Werkzeug, que ejecuta codigo desde
# el navegador) solo si se pide EXPLICITAMENTE. Sin variable -- o en cualquier otro
# valor -- se arranca gunicorn: olvidar la variable no debe abrir el depurador.
if [ "${FLASK_ENV:-}" = "development" ] || [ "${APP_ENV:-}" = "development" ]; then
  flask --app app run --host=0.0.0.0 --port=${BACKEND_PORT:-5001} --debug
else
  gunicorn "app:create_app()" --bind 0.0.0.0:${BACKEND_PORT:-5001} --workers 3 --timeout 120
fi
