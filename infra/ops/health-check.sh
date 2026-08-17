#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .env 2>/dev/null || true
check_url() {
  local name="$1"; local url="$2"
  if curl -fsS "$url" >/dev/null 2>&1; then echo "OK  $name $url"; else echo "ERR $name $url"; fi
}
echo "== TYAKXA health check =="
docker compose ps
check_url "backend" "http://localhost:${BACKEND_PORT:-5001}/health"
check_url "frontend" "http://localhost:${FRONTEND_PORT:-3000}"
check_url "nginx" "http://localhost:${NGINX_HTTP_PORT:-8080}/health"
docker compose exec -T db pg_isready -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" || true
docker compose exec -T rabbitmq rabbitmq-diagnostics check_running || true
