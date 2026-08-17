
from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok


@celery.task(name="app.jobs.tasks_scm.recalculate_inventory")
def recalculate_inventory(location_id: int | str | None = None, material_id: int | str | None = None) -> dict:
    return result_ok("jobs.scm.inventory_recalculated", location_id=location_id, material_id=material_id)


@celery.task(name="app.jobs.tasks_scm.detect_stock_risk")
def detect_stock_risk() -> dict:
    return result_ok("jobs.scm.stock_risk_detected")


@celery.task(name="app.jobs.tasks_scm.plan_replenishment")
def plan_replenishment(location_id: int | str | None = None) -> dict:
    return result_ok("jobs.scm.replenishment_planned", location_id=location_id)


@celery.task(name="app.jobs.tasks_scm.sync_supplier_scorecards")
def sync_supplier_scorecards() -> dict:
    return result_ok("jobs.scm.supplier_scorecards_synced")
