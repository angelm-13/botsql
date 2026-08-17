#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

ensure_docker

log "Limpiando recursos Docker no usados. No elimina volúmenes por seguridad."
docker system prune -f
ok "Limpieza Docker completada."

warn "Para limpiar volúmenes huérfanos manualmente usa: docker volume prune"
