#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

ensure_db_running

log "Ejecutando VACUUM ANALYZE en $DB_NAME"
compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" -c "VACUUM ANALYZE;"
ok "VACUUM ANALYZE completado."
