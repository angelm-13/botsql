#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_common.sh"

ensure_docker

STATUS=0

echo ""
echo "TYAKXA healthcheck"
echo "=================="

log "Contenedores"
compose ps || STATUS=1

echo ""
log "PostgreSQL"
if compose exec -T "$DB_SERVICE" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
  ok "PostgreSQL disponible"
else
  warn "PostgreSQL no disponible"
  STATUS=1
fi

echo ""
log "Backend"
if command -v curl >/dev/null 2>&1 && curl -fsS "$BACKEND_HEALTH_URL" >/dev/null 2>&1; then
  ok "Backend responde: $BACKEND_HEALTH_URL"
else
  warn "Backend no responde: $BACKEND_HEALTH_URL"
  STATUS=1
fi

echo ""
log "Frontend"
if command -v curl >/dev/null 2>&1 && curl -fsS "$FRONTEND_URL" >/dev/null 2>&1; then
  ok "Frontend responde: $FRONTEND_URL"
else
  warn "Frontend no responde: $FRONTEND_URL"
  STATUS=1
fi

echo ""
log "RabbitMQ AMQP"
if command -v nc >/dev/null 2>&1 && nc -z "$RABBITMQ_AMQP_HOST" "$RABBITMQ_AMQP_PORT" >/dev/null 2>&1; then
  ok "RabbitMQ AMQP disponible"
else
  warn "RabbitMQ AMQP no disponible"
  STATUS=1
fi

exit "$STATUS"
