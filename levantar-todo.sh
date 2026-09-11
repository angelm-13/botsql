#!/usr/bin/env bash
#
# Levanta TYAKXA y todo lo que necesita, de una vez.
#
# Por que un script y no un solo docker-compose
# ---------------------------------------------
# La idea original era meter los demas proyectos en el compose de TYAKXA para
# que un `docker compose up` levantara todo. No se puede sin romper algo, por
# dos motivos medidos:
#
#   1. **Los nombres chocan.** TYAKXA tiene `db`, `backend` y `frontend`; el POS
#      tiene `db`, `backend`, `frontend`, `redis`, `celery_worker` y
#      `celery_beat`. Fundir los dos archivos exige renombrar los del POS, y
#      entonces este repositorio tendria una COPIA de los servicios del POS que
#      se queda vieja en cuanto alguien toca el POS de verdad.
#
#   2. **Los volumenes son del otro proyecto.** La base del POS vive en
#      `pos-enterprise_pos_db_data`. Redeclararla aqui como volumen propio
#      arrancaria el POS con la base VACIA -- casi paso: el primer intento leia
#      `C:\Users\TDW3\pos-system\docker-compose.yml`, que es OTRO proyecto con
#      otras credenciales, y habria creado una base nueva sin darse cuenta.
#
# Asi que cada proyecto conserva su compose, sus volumenes y sus datos, y esto
# solo es el boton que los arranca en orden.
#
# Que NO hace falta levantar
# --------------------------
# Restaurante y logistica NO son proyectos aparte: su codigo vive dentro de este
# repositorio (`backend/app/models/restaurant.py`,
# `backend/app/services/logistics_*.py`). Los directorios `restaurante`,
# `demo_restaurante`, `demo_pos`, `nkpm*` y `cotizador_demo` de esta maquina son
# otros productos, no servicios que TYAKXA llame.
#
# La unica dependencia externa de TYAKXA es el POS, y esta declarada en el .env:
#
#     POS_API_URL=http://host.docker.internal:5000
#
set -euo pipefail

TYAKXA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POS="${POS_PROJECT_DIR:-$(dirname "$TYAKXA")/pos-enterprise}"

# Del POS solo lo que la pantalla de Caja necesita: su API, su base y su redis.
# El frontend del POS y sus dos celery se quedan apagados a proposito -- TYAKXA
# habla con la API, no con su interfaz, y son cuatro contenedores de memoria
# que nadie mira. Con `--completo` se levantan tambien.
SERVICIOS_POS=(db redis backend)
if [[ "${1:-}" == "--completo" ]]; then
  SERVICIOS_POS=()
fi

echo "==> TYAKXA  ($TYAKXA)"
docker compose -f "$TYAKXA/docker-compose.yml" up -d

if [[ -f "$POS/docker-compose.yml" ]]; then
  echo
  echo "==> Punto de venta  ($POS)"
  docker compose --project-directory "$POS" up -d "${SERVICIOS_POS[@]}"
else
  echo
  echo "!! No se encontro el POS en $POS"
  echo "   La pantalla de Caja dira 'El punto de venta no responde'."
  echo "   Si esta en otro sitio: POS_PROJECT_DIR=/ruta/al/pos ./levantar-todo.sh"
fi

# Y comprobar que responde, que es la parte que de verdad importa: un
# contenedor 'Up' no significa que su API contesta.
echo
echo "==> Comprobando"
for intento in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://localhost:5001/health" 2>/dev/null; then
    echo "   TYAKXA        ok  http://localhost:5001/health"
    break
  fi
  [[ $intento -eq 30 ]] && echo "   TYAKXA        NO responde en el 5001"
  sleep 2
done

for intento in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://localhost:3001/" 2>/dev/null; then
    echo "   Interfaz      ok  http://localhost:3001"
    break
  fi
  [[ $intento -eq 30 ]] && echo "   Interfaz      NO responde en el 3001"
  sleep 2
done

for intento in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://localhost:5000/health" 2>/dev/null; then
    echo "   Punto de venta ok  http://localhost:5000/health"
    break
  fi
  [[ $intento -eq 30 ]] && echo "   Punto de venta NO responde en el 5000"
  sleep 2
done
