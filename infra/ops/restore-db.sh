#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .env
BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then echo "Usage: infra/ops/restore-db.sh <backup.sql.gz|backup.sql>"; exit 1; fi
echo "Restoring $BACKUP_FILE into $DB_NAME"
if [[ "$BACKUP_FILE" == *.gz ]]; then gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"; else docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"; fi
echo "Restore complete"
