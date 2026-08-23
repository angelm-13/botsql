
from __future__ import annotations

from celery import Celery

from app.config.celery_config import CeleryConfig


celery = Celery("tyakxa_erp")
celery.config_from_object(CeleryConfig)

celery.autodiscover_tasks([
    "app.jobs.tasks_entity",
    "app.jobs.tasks_erp",
    "app.jobs.tasks_crm",
    "app.jobs.tasks_scm",
    "app.jobs.tasks_documents",
    "app.jobs.tasks_maintenance",
    "app.jobs.tasks_stamping",
    "app.jobs.tasks_appointments",
])


@celery.task(name="app.jobs.health.ping")
def ping() -> dict:
    return {"ok": True, "service": "celery", "message_key": "jobs.health.ok"}
