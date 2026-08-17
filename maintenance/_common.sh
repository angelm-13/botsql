#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/maintenance.env"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
elif [ -f "$SCRIPT_DIR/maintenance.env.example" ]; then
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/maintenance.env.example"
fi

DB_SERVICE="${DB_SERVICE:-db}"
DB_NAME="${DB_NAME:-tyakxa_erp}"
DB_USER="${DB_USER:-tyakxa_user}"
DB_PASSWORD="${DB_PASSWORD:-change_me}"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_PREFIX="${BACKUP_PREFIX:-tyakxa_pg}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://localhost:5001/health}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
RABBITMQ_AMQP_HOST="${RABBITMQ_AMQP_HOST:-localhost}"
RABBITMQ_AMQP_PORT="${RABBITMQ_AMQP_PORT:-5672}"

mkdir -p "$BACKUP_DIR"

log() { printf '\033[0;34m[INFO]\033[0m %s\n' "$*"; }
ok() { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
fail() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

compose_file_args() {
  if [ -n "${COMPOSE_FILE:-}" ]; then
    printf -- '-f\n%s\n' "$COMPOSE_FILE"
    return
  fi

  if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    printf -- '-f\n%s\n' "$PROJECT_DIR/docker-compose.yml"
    return
  fi

  if [ -f "$PROJECT_DIR/infra/docker-compose.yml" ]; then
    printf -- '-f\n%s\n' "$PROJECT_DIR/infra/docker-compose.yml"
    return
  fi
}

compose() {
  mapfile -t args < <(compose_file_args)
  docker compose "${args[@]}" "$@"
}

ensure_docker() {
  command -v docker >/dev/null 2>&1 || fail "Docker no está instalado o no está en PATH."
  docker ps >/dev/null 2>&1 || fail "Docker no está ejecutándose."
}

ensure_db_running() {
  ensure_docker
  compose ps "$DB_SERVICE" >/dev/null 2>&1 || fail "No encuentro el servicio PostgreSQL: $DB_SERVICE"
}
