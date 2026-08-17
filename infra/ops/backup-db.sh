#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .env
mkdir -p infra/backups
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="infra/backups/${DB_NAME}_${STAMP}.sql.gz"
echo "Creating backup: $OUT"
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$OUT"
find infra/backups -type f -name "*.sql.gz" -mtime +"${BACKUP_RETENTION_DAYS:-14}" -delete
echo "Backup complete: $OUT"
