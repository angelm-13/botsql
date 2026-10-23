from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.notification import Notification
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class NotificationService(CrudService):
    model = Notification
    primary_key = 'id_notification'
    entity_name = 'notification'

    @classmethod
    def create_for_user(cls, db, id_user: int, notification_type: str, title: str, *,
                         content: str | None = None, id_proyect: int | None = None,
                         id_proyect_event: int | None = None) -> Notification:
        """Crea una notificacion dentro de una transaccion que ya esta abierta.

        No usa `CrudService.create()` -- ese helper abre su propia
        `transaction_context()`, y esto se llama siempre desde dentro de otra
        (el alta del `ProyectEvent` que la origina), donde tiene que quedar en
        el mismo commit/rollback que el hecho que la genera.
        """
        notification = Notification(
            id_user=id_user,
            id_proyect=id_proyect,
            id_proyect_event=id_proyect_event,
            notification_type=notification_type,
            title=title,
            content=content,
            created_by=1,
        )
        db.add(notification)
        return notification

    @classmethod
    def unread_count(cls, id_user: int) -> int:
        with transaction_context() as db:
            return db.scalar(
                select(func.count()).select_from(Notification)
                .where(Notification.id_user == id_user)
                .where(Notification.read_at.is_(None))
            ) or 0

    @classmethod
    def mark_read(cls, id_notification, id_user: int) -> dict:
        with transaction_context() as db:
            item = db.get(Notification, id_notification)
            if not item or item.id_user != id_user:
                raise AppError('errors.resource_not_found', status_code=404)
            if item.read_at is None:
                item.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.flush()
            return item.serialize()

    @classmethod
    def mark_all_read(cls, id_user: int) -> dict:
        with transaction_context() as db:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            (
                db.query(Notification)
                .filter(Notification.id_user == id_user)
                .filter(Notification.read_at.is_(None))
                .update({Notification.read_at: now}, synchronize_session=False)
            )
            return {'message_key': 'success.notifications_marked_read'}
