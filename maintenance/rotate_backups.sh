#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

log "Rotando backups mayores a $BACKUP_RETENTION_DAYS días en $BACKUP_DIR"
find "$BACKUP_DIR" -type f \
  \( -name "${BACKUP_PREFIX}_*.dump" -o -name "${BACKUP_PREFIX}_*.dump.meta.json" \) \
  -mtime "+$BACKUP_RETENTION_DAYS" \
  -print \
  -delete
ok "Rotación completada."
