#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

ensure_db_running

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/${BACKUP_PREFIX}_${DB_NAME}_${TS}.dump"
META="$OUT.meta.json"

log "Creando backup PostgreSQL: $OUT"
compose exec -T "$DB_SERVICE" pg_dump \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --format=custom \
  --blobs \
  --verbose \
  > "$OUT"

SHA="$(sha256sum "$OUT" | awk '{print $1}')"
SIZE="$(wc -c < "$OUT")"
cat > "$META" <<JSON
{
  "database": "$DB_NAME",
  "user": "$DB_USER",
  "created_at": "$(date -Iseconds)",
  "file": "$(basename "$OUT")",
  "sha256": "$SHA",
  "size_bytes": $SIZE
}
JSON

ok "Backup creado: $OUT"
ok "Checksum: $SHA"
