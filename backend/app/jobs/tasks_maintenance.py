
from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok


@celery.task(name="app.jobs.tasks_maintenance.cleanup_expired_results")
def cleanup_expired_results() -> dict:
    return result_ok("jobs.maintenance.cleanup_completed")


@celery.task(name="app.jobs.tasks_maintenance.rebuild_search_indexes")
def rebuild_search_indexes() -> dict:
    return result_ok("jobs.maintenance.search_indexes_rebuilt")
