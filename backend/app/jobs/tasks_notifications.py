from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.models.notification import Notification
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.user import User
from app.services.notification_service import NotificationService


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _last_business_day(today):
    # Sabado (5) y domingo (6) no cuentan como dia habil -- un supervisor que
    # no captura nada en fin de semana no tiene nada que reclamar el lunes.
    anterior = today - timedelta(days=1)
    while anterior.weekday() >= 5:
        anterior -= timedelta(days=1)
    return anterior


@celery.task(name="app.jobs.tasks_notifications.check_missing_activity_logs")
def check_missing_activity_logs() -> dict:
    """Recordatorio diario: quien tiene rol Supervisor y no capturo su bitacora.

    Corre una vez al dia (ver BEAT_SCHEDULE). Revisa el ultimo dia habil, no
    "ayer" a secas: un lunes reclama el viernes, no el domingo.
    """
    target_date = _last_business_day(_now_naive().date())
    with transaction_context() as db:
        supervisor_ids = [
            row[0]
            for row in db.query(User.id_user)
            .join(Permission, Permission.id_permission == User.id_permission)
            .filter(Permission.permission_description.ilike("supervisor"))
            .filter(Permission.deletion_date.is_(None))
            .filter(User.deletion_date.is_(None))
            .all()
        ]
        if not supervisor_ids:
            return result_ok("jobs.notifications.no_supervisors", target_date=target_date.isoformat())

        logged_ids = {
            row[0]
            for row in db.query(SupervisorActivityLog.id_user)
            .filter(SupervisorActivityLog.id_user.in_(supervisor_ids))
            .filter(SupervisorActivityLog.activity_date == target_date)
            .filter(SupervisorActivityLog.deletion_date.is_(None))
            .all()
        }
        missing_ids = [id_user for id_user in supervisor_ids if id_user not in logged_ids]
        content = f"No registraste actividad el {target_date.isoformat()}."
        # El job corre una vez al dia por `BEAT_SCHEDULE`, pero nada impide
        # que alguien lo dispare a mano dos veces el mismo dia (o que un
        # reintento de Celery lo repita) -- sin esta comprobacion, cada
        # corrida de mas duplicaria el recordatorio para todo el que siga sin
        # capturar. El contenido ya trae la fecha exacta, asi que sirve de
        # llave natural sin agregar una columna solo para esto.
        already_notified = {
            row[0]
            for row in db.query(Notification.id_user)
            .filter(Notification.id_user.in_(missing_ids))
            .filter(Notification.notification_type == "activity_log_missing")
            .filter(Notification.content == content)
            .all()
        }
        for id_user in missing_ids:
            if id_user in already_notified:
                continue
            NotificationService.create_for_user(
                db, id_user, "activity_log_missing",
                "Bitacora de actividades pendiente",
                content=content,
            )
    return result_ok(
        "jobs.notifications.missing_activity_logs_checked",
        target_date=target_date.isoformat(),
        supervisors=len(supervisor_ids),
        missing=len(missing_ids),
    )
