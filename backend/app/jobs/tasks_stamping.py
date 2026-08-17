from __future__ import annotations

from app.jobs.celery_app import celery
from app.services.stamping import configured_provider


@celery.task(
    bind=True,
    name="app.jobs.tasks_stamping.reconcile_stamping",
    autoretry_for=(),
    soft_time_limit=30,
    time_limit=45,
)
def reconcile_stamping(self, provider_reference):
    result = configured_provider().reconcile(provider_reference)
    return {"status": result.status, "reference": result.reference, "error_code": result.error_code}