"""Avisos periodicos del almacen: hoy, solo "vale vencido".

`vales_vencidos` (`warehouse_voucher_service.py`) ya contesta "que no ha
vuelto", pero solo cuando alguien abre la pantalla de vales y la pregunta --
nunca empuja un aviso. Este job corre esa misma pregunta por su cuenta y la
convierte en una notificacion real (campanita), para quien de verdad tiene
que reclamarlo: el responsable del vale, o la persona a la que se le entrego
la herramienta si el vale la tiene delegada.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.models.incident import Incident
from app.models.nm_incident_product import NmIncidentProduct
from app.models.session import transaction_context
from app.services.notification_service import create_notification
from app.services.warehouse_voucher_service import SALIDA, _vales_de_baja


@celery.task(name="app.jobs.tasks_warehouse.notify_overdue_vouchers")
def notify_overdue_vouchers() -> dict:
    """Notifica una sola vez por renglon vencido.

    Deduplicado con `overdue_notified_date`: sin esta marca, cada corrida
    repetiria el mismo aviso mientras el renglon siga sin volver. La lectura
    y la escritura van en transacciones SEPARADAS -nunca anidadas con
    `create_notification`, que abre la suya propia- por el mismo motivo que
    `_notificar_proyecto` en `project_management_service.py`: anidarlas se
    queda esperando una conexion libre del pool para siempre.
    """
    ahora = datetime.now()
    with transaction_context() as db:
        filas = db.execute(
            select(
                NmIncidentProduct.id_nm_incident_product,
                NmIncidentProduct.id_user_delivered_to,
                Incident.id_user,
                Incident.external_folio,
                Incident.id_incident,
            )
            .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
            .where(
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.direction == SALIDA,
                NmIncidentProduct.close_date.is_(None),
                NmIncidentProduct.due_date.isnot(None),
                NmIncidentProduct.due_date < ahora,
                NmIncidentProduct.overdue_notified_date.is_(None),
                Incident.id_incident.notin_(_vales_de_baja()),
            )
        ).all()
        pendientes = [
            {
                "id_nm_incident_product": int(fila[0]),
                # A quien se le entrego, si se delego; si no, el responsable.
                "destinatario": int(fila[1] or fila[2]),
                # `create_notification` exige `created_by` con FK valida a
                # `user` -- no hay un actor humano en un job periodico, asi
                # que se usa el responsable del propio vale, que ya esta
                # garantizado valido (misma FK que `incident.id_user`).
                "id_responsable": int(fila[2]),
                "folio": fila[3] or str(fila[4]),
                "id_incident": int(fila[4]),
            }
            for fila in filas
        ]

    avisados = 0
    for item in pendientes:
        try:
            create_notification(
                id_user_recipient=item["destinatario"],
                notification_type="warehouse_voucher_overdue",
                title="Vale #%s vencido" % item["folio"],
                message=(
                    "El vale #%s tiene material que ya debió volver al "
                    "almacén y no ha vuelto."
                ) % item["folio"],
                metadata={
                    "id_incident": item["id_incident"],
                    "id_nm_incident_product": item["id_nm_incident_product"],
                },
                target_entity="voucher", target_id=item["id_incident"],
                created_by=item["id_responsable"],
            )
        except Exception:
            continue
        with transaction_context() as db:
            renglon = db.get(NmIncidentProduct, item["id_nm_incident_product"])
            if renglon is not None:
                renglon.overdue_notified_date = ahora
        avisados += 1

    return result_ok("jobs.warehouse.overdue_notified", count=avisados)
