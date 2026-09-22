#!/usr/bin/env bash
# Demostracion del modulo de BI: un comando, una URL.
#
# Instala lo necesario si falta, construye la interfaz la primera vez y
# levanta todo en http://localhost:5001
set -e
cd "$(dirname "$0")"

echo
echo "  === Modulo de BI -- demostracion ==="
echo

command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python
command -v "$PY" >/dev/null 2>&1 || {
  echo "  [!] No se encontro Python 3.11 o superior."; exit 1;
}

echo "  [1/3] Dependencias de Python..."
"$PY" -m pip install -q -r backend/requirements.txt

if [ -f frontend/dist/index.html ]; then
  echo "  [2/3] Interfaz ya construida."
elif command -v npm >/dev/null 2>&1; then
  echo "  [2/3] Construyendo la interfaz (tarda ~1 minuto la primera vez)..."
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
else
  echo "  [2/3] Sin Node.js: se arranca solo la API, sin interfaz."
  echo "        Para la interfaz, instale Node 20+ y vuelva a correr."
fi

echo "  [3/3] Arrancando..."
echo
cd backend
exec "$PY" demo.py
