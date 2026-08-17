#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
COMMAND="${1:-help}"
case "$COMMAND" in
  start) docker compose up -d --build ;;
  stop) docker compose down ;;
  restart) docker compose restart ;;
  logs) docker compose logs -f --tail=200 "${2:-}" ;;
  status) docker compose ps; bash infra/ops/health-check.sh ;;
  build) docker compose build --no-cache ;;
  clean)
    echo "This removes containers and volumes, including the database. Type YES to continue:"
    read -r answer
    if [ "$answer" = "YES" ]; then docker compose down -v --remove-orphans; else echo "Cancelled."; fi
    ;;
  prod) docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build ;;
  *)
    cat <<'HELP'
Usage: infra/ops/deploy.sh <command>
Commands: start, stop, restart, logs [svc], status, build, clean, prod
HELP
    ;;
esac
