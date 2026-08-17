
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-tyakxa_u_7f2c9d}"
DB_NAME="${DB_NAME:-tyakxa_test}"

cd "$PROJECT_DIR"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" < security-permissions/sql/01_create_security_tables.sql
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" < security-permissions/sql/02_seed_admin_entity_permissions.sql
