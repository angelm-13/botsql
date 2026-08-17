#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: ./restore_postgres.sh <backup.dump>"
  exit 1
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-tyakxa_erp}"
DB_USER="${DB_USER:-postgres}"
BACKUP_FILE="$1"

pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$BACKUP_FILE"
echo "Restore aplicado sobre $DB_NAME desde $BACKUP_FILE"
