"""Avisos periodicos de compras: hoy, solo la renta de maquinaria por vencer o vencida.

La regla (a quien, cuando, sin repetir) vive en `avisar_rentas_por_vencer`
(`purchase_order_service.py`); este job solo la dispara. Sin ruta propia en
`task_routes`: va a la cola `celery`, la unica que consume el worker de k8s.
"""

from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.services.purchase_order_service import avisar_rentas_por_vencer


@celery.task(name="app.jobs.tasks_purchases.notify_rentals_due")
def notify_rentals_due() -> dict:
    return result_ok("jobs.purchases.rentals_notified", count=avisar_rentas_por_vencer())
