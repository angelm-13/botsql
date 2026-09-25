from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, desc

from app.models.notification import Notification
from app.models.session import transaction_context


def create_notification(
    id_user_recipient: int,
    notification_type: str,
    title: str,
    message: str = None,
    id_proyect: int = None,
    id_user_sender: int = None,
    created_by: int = None,
    metadata: dict = None,
) -> Notification:
    """
    Crea una notificación para un usuario.

    Args:
        id_user_recipient: ID del usuario que recibe la notificación
        notification_type: Tipo de notificación (project_status_change, project_modified, etc.)
        title: Título breve
        message: Mensaje detallado (opcional)
        id_proyect: ID del proyecto relacionado (opcional)
        id_user_sender: ID del usuario que genera la notificación (opcional)
        created_by: ID del usuario que registra la notificación en el sistema
        metadata: Datos adicionales en JSON (previous_status, new_status, reason, etc.)

    Returns:
        Notification: La notificación creada
    """
    if created_by is None:
        created_by = id_user_sender if id_user_sender else 0

    if metadata is None:
        metadata = {}

    with transaction_context() as db:
        notification = Notification(
            id_user_recipient=id_user_recipient,
            id_user_sender=id_user_sender,
            id_proyect=id_proyect,
            notification_type=notification_type,
            title=title,
            message=message,
            metadata_data=metadata,
            created_by=created_by,
        )
        db.add(notification)
        db.flush()
        db.refresh(notification)
        return notification


def get_user_notifications(
    id_user: int,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> List[Notification]:
    """
    Obtiene notificaciones de un usuario.

    Args:
        id_user: ID del usuario
        unread_only: Si True, solo retorna notificaciones no leídas
        limit: Cantidad máxima de resultados
        offset: Desplazamiento (para paginación)

    Returns:
        List[Notification]: Lista de notificaciones ordenadas por fecha descendente
    """
    with transaction_context() as db:
        query = select(Notification).where(
            (Notification.id_user_recipient == id_user) &
            (Notification.deletion_date.is_(None))
        )

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(desc(Notification.creation_date)).limit(limit).offset(offset)

        notifications = db.execute(query).scalars().all()
        return notifications


def get_notification_by_id(id_notification: int) -> Optional[Notification]:
    """Obtiene una notificación específica por ID."""
    with transaction_context() as db:
        notification = db.execute(
            select(Notification).where(
                (Notification.id_notification == id_notification) &
                (Notification.deletion_date.is_(None))
            )
        ).scalar()
        return notification


def mark_as_read(id_notification: int, id_user: int) -> bool:
    """
    Marca una notificación como leída.

    Args:
        id_notification: ID de la notificación
        id_user: ID del usuario que la lee (para validar que es el propietario)

    Returns:
        bool: True si se marcó exitosamente, False si la notificación no existe o no pertenece al usuario
    """
    with transaction_context() as db:
        notification = db.execute(
            select(Notification).where(
                (Notification.id_notification == id_notification) &
                (Notification.id_user_recipient == id_user) &
                (Notification.deletion_date.is_(None))
            )
        ).scalar()

        if not notification:
            return False

        notification.is_read = True
        notification.read_date = datetime.now()
        db.flush()
        return True


def mark_all_as_read(id_user: int) -> int:
    """
    Marca todas las notificaciones no leídas del usuario como leídas.

    Args:
        id_user: ID del usuario

    Returns:
        int: Cantidad de notificaciones marcadas como leídas
    """
    with transaction_context() as db:
        count = db.query(Notification).filter(
            (Notification.id_user_recipient == id_user) &
            (Notification.is_read == False) &
            (Notification.deletion_date.is_(None))
        ).update({
            Notification.is_read: True,
            Notification.read_date: datetime.now(),
        })
        db.flush()
        return count


def delete_notification(id_notification: int, id_user: int) -> bool:
    """
    Soft delete de una notificación (solo si pertenece al usuario).

    Args:
        id_notification: ID de la notificación
        id_user: ID del usuario que la elimina

    Returns:
        bool: True si se eliminó, False si no existe
    """
    with transaction_context() as db:
        notification = db.execute(
            select(Notification).where(
                (Notification.id_notification == id_notification) &
                (Notification.id_user_recipient == id_user) &
                (Notification.deletion_date.is_(None))
            )
        ).scalar()

        if not notification:
            return False

        notification.deletion_date = datetime.now()
        db.flush()
        return True


def get_unread_count(id_user: int) -> int:
    """Obtiene la cantidad de notificaciones no leídas de un usuario."""
    with transaction_context() as db:
        count = db.query(Notification).filter(
            (Notification.id_user_recipient == id_user) &
            (Notification.is_read == False) &
            (Notification.deletion_date.is_(None))
        ).count()
        return count
