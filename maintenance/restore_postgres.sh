#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

BACKUP_FILE="${1:-}"
[ -n "$BACKUP_FILE" ] || fail "Uso: ./restore_postgres.sh /ruta/al/backup.dump"
[ -f "$BACKUP_FILE" ] || fail "Backup no encontrado: $BACKUP_FILE"

ensure_db_running

cat <<EOF
Vas a restaurar este backup sobre la base de datos actual.

  DB:      $DB_NAME
  Usuario: $DB_USER
  Backup:  $BACKUP_FILE

Esto puede sobrescribir datos existentes.
EOF

read -r -p "Escribe RESTORE para continuar: " CONFIRM
[ "$CONFIRM" = "RESTORE" ] || fail "Restore cancelado."

log "Creando backup de seguridad antes del restore..."
"$SCRIPT_DIR/backup_postgres.sh"

log "Restaurando $BACKUP_FILE en $DB_NAME"
cat "$BACKUP_FILE" | compose exec -T "$DB_SERVICE" pg_restore \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --clean \
  --if-exists \
  --no-owner \
  --verbose

ok "Restore completado."
