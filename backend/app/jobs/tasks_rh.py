"""Avisos periodicos de RH: hoy, solo "vacaciones por vencer".

La regla de cuando avisar (los dias de aviso de la politica de vacaciones de la
empresa) vive en employee_leave_service.avisar_vacaciones_por_vencer; este job
solo la corre una vez al dia.
"""

from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.services.employee_leave_service import avisar_vacaciones_por_vencer


@celery.task(name="app.jobs.tasks_rh.notify_expiring_vacations")
def notify_expiring_vacations() -> dict:
    return result_ok("jobs.rh.expiring_vacations_notified", sent=avisar_vacaciones_por_vencer())
