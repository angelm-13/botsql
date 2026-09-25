#!/usr/bin/env bash
# Demostracion del modulo de BI: un comando, una URL.
#
# Instala lo necesario si falta, construye la interfaz la primera vez y
# levanta todo en http://localhost:8500 (o $BI_PORT, si ya esta exportada).
set -e
cd "$(dirname "$0")"

export BI_PORT="${BI_PORT:-8500}"

echo
echo "  === Modulo de BI -- demostracion ==="
echo

command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python
command -v "$PY" >/dev/null 2>&1 || {
  echo "  [!] No se encontro Python 3.11 o superior."; exit 1;
}

echo "  [1/4] Dependencias de Python..."
"$PY" -m pip install -q -r backend/requirements.txt

if [ -f frontend/dist/index.html ]; then
  echo "  [2/4] Interfaz ya construida."
elif command -v npm >/dev/null 2>&1; then
  echo "  [2/4] Construyendo la interfaz (tarda ~1 minuto la primera vez)..."
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
else
  echo "  [2/4] Sin Node.js: se arranca solo la API, sin interfaz."
  echo "        Para la interfaz, instale Node 20+ y vuelva a correr."
fi

# Aviso temprano si el puerto ya esta ocupado por otro programa -- en mas de
# una maquina de prueba, Docker reenviaba ahi un contenedor de OTRO proyecto,
# y el navegador terminaba hablando con esa otra aplicacion sin ningun aviso,
# dando la impresion de que la demostracion fallaba.
echo "  [3/4] Revisando el puerto $BI_PORT..."
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$BI_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo
  echo "  [!] El puerto $BI_PORT ya esta en uso por otro programa."
  echo "      No es esta demostracion la que va a fallar -- es que el"
  echo "      navegador terminaria hablando con lo que sea que ya esta ahi."
  echo "      Revise que lo ocupa, o corra con otro puerto:"
  echo "        BI_PORT=8501 ./demo.sh"
  echo
  exit 1
fi

echo "  [4/4] Arrancando en el puerto $BI_PORT..."
echo
cd backend
exec "$PY" demo.py
