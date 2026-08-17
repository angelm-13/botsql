
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
celery -A app.jobs.celery_app.celery worker --loglevel="${CELERY_LOG_LEVEL:-info}" -Q entity,erp,crm,scm,documents,maintenance
