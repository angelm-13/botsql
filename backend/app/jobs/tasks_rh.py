"""Avisos periodicos de RH: "vacaciones por vencer" y "no has checado".

La regla de cuando avisar (los dias de aviso de la politica de vacaciones de la
empresa) vive en employee_leave_service.avisar_vacaciones_por_vencer; este job
solo la corre una vez al dia. La de las checadas que faltan vive en
services/avisos_de_checada.py y corre cada 5 minutos.
"""

from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.services.avisos_de_checada import avisar_checadas_faltantes
from app.services.employee_leave_service import avisar_vacaciones_por_vencer


@celery.task(name="app.jobs.tasks_rh.notify_expiring_vacations")
def notify_expiring_vacations() -> dict:
    return result_ok("jobs.rh.expiring_vacations_notified", sent=avisar_vacaciones_por_vencer())


@celery.task(name="app.jobs.tasks_rh.notify_missing_checks")
def notify_missing_checks() -> dict:
    return result_ok("jobs.rh.missing_checks_notified", sent=avisar_checadas_faltantes())
