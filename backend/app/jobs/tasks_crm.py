
from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok


@celery.task(name="app.jobs.tasks_crm.score_customer_health")
def score_customer_health(customer_supplier_id: int | str | None = None) -> dict:
    return result_ok("jobs.crm.customer_health_scored", customer_supplier_id=customer_supplier_id)


@celery.task(name="app.jobs.tasks_crm.sync_customer_segments")
def sync_customer_segments() -> dict:
    return result_ok("jobs.crm.customer_segments_synced")


@celery.task(name="app.jobs.tasks_crm.schedule_followups")
def schedule_followups(owner_user_id: int | str | None = None) -> dict:
    return result_ok("jobs.crm.followups_scheduled", owner_user_id=owner_user_id)
