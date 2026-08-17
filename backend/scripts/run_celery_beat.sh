
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
celery -A celery_worker.celery beat --loglevel="${CELERY_LOG_LEVEL:-info}"
