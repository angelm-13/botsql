
from __future__ import annotations

import os


class CeleryConfig:
    broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"))
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "rpc://")
    timezone = os.getenv("CELERY_TIMEZONE", "UTC")
    enable_utc = True
    task_track_started = True
    task_time_limit = int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800"))
    task_soft_time_limit = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "1500"))
    worker_prefetch_multiplier = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
    task_acks_late = True
    task_reject_on_worker_lost = True
    result_expires = int(os.getenv("CELERY_RESULT_EXPIRES", "86400"))
    accept_content = ["json"]
    task_serializer = "json"
    result_serializer = "json"

    task_routes = {
        "app.jobs.tasks_entity.*": {"queue": "entity"},
        "app.jobs.tasks_erp.*": {"queue": "erp"},
        "app.jobs.tasks_crm.*": {"queue": "crm"},
        "app.jobs.tasks_scm.*": {"queue": "scm"},
        "app.jobs.tasks_documents.*": {"queue": "documents"},
        "app.jobs.tasks_maintenance.*": {"queue": "maintenance"},
    }
