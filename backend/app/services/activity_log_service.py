from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, desc, and_, or_

from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.session import get_session


def create_activity(
    id_proyect: int,
    id_supervisor: int,
    activity_date: date,
    description: str,
    status: str = 'pending',
    hours_spent: Decimal = None,
    notes: str = None,
    created_by: int = None,
) -> SupervisorActivityLog:
    """
    Crea un registro de actividad diaria.

    Args:
        id_proyect: ID del proyecto
        id_supervisor: ID del supervisor que registra
        activity_date: Fecha de la actividad (puede ser hoy o una fecha pasada)
        description: Descripción de la actividad realizada
        status: Estado del registro ('pending', 'in_progress', 'completed')
        hours_spent: Horas dedicadas (opcional)
        notes: Notas adicionales / problemas encontrados (opcional)
        created_by: ID del usuario que registra (default = id_supervisor)

    Returns:
        SupervisorActivityLog: El registro creado
    """
    if created_by is None:
        created_by = id_supervisor

    with get_session() as db:
        activity = SupervisorActivityLog(
            id_proyect=id_proyect,
            id_supervisor=id_supervisor,
            activity_date=activity_date,
            description=description,
            status=status,
            hours_spent=hours_spent,
            notes=notes,
            created_by=created_by,
        )
        db.add(activity)
        db.flush()
        db.refresh(activity)
        return activity


def get_activity_by_id(id_activity: int) -> Optional[SupervisorActivityLog]:
    """Obtiene un registro de actividad por ID."""
    with get_session() as db:
        activity = db.execute(
            select(SupervisorActivityLog).where(
                (SupervisorActivityLog.id_activity == id_activity) &
                (SupervisorActivityLog.deletion_date.is_(None))
            )
        ).scalar()
        return activity


def get_activities_by_range(
    id_proyect: int = None,
    id_supervisor: int = None,
    start_date: date = None,
    end_date: date = None,
    limit: int = 100,
    offset: int = 0,
) -> List[SupervisorActivityLog]:
    """
    Obtiene registros de actividades en un rango de fechas con filtros opcionales.

    Args:
        id_proyect: Filtrar por proyecto (opcional)
        id_supervisor: Filtrar por supervisor (opcional)
        start_date: Fecha de inicio (inclusive)
        end_date: Fecha de fin (inclusive)
        limit: Máximo de resultados
        offset: Desplazamiento (paginación)

    Returns:
        List[SupervisorActivityLog]: Lista de actividades ordenadas por fecha descendente
    """
    with get_session() as db:
        query = select(SupervisorActivityLog).where(
            SupervisorActivityLog.deletion_date.is_(None)
        )

        # Filtros opcionales
        if id_proyect:
            query = query.where(SupervisorActivityLog.id_proyect == id_proyect)

        if id_supervisor:
            query = query.where(SupervisorActivityLog.id_supervisor == id_supervisor)

        # Rango de fechas
        if start_date and end_date:
            query = query.where(
                SupervisorActivityLog.activity_date.between(start_date, end_date)
            )
        elif start_date:
            query = query.where(SupervisorActivityLog.activity_date >= start_date)
        elif end_date:
            query = query.where(SupervisorActivityLog.activity_date <= end_date)

        # Ordenamiento y paginación
        query = query.order_by(
            desc(SupervisorActivityLog.activity_date),
            desc(SupervisorActivityLog.creation_date)
        ).limit(limit).offset(offset)

        activities = db.execute(query).scalars().all()
        return activities


def get_supervisor_pending_activities(id_supervisor: int, days: int = 7) -> List[SupervisorActivityLog]:
    """
    Obtiene actividades pendientes o en progreso del supervisor en los últimos N días.
    Útil para recordarle qué bitácoras aún no está completas.

    Args:
        id_supervisor: ID del supervisor
        days: Número de días atrás a buscar (default 7)

    Returns:
        List[SupervisorActivityLog]: Actividades pendientes o en progreso
    """
    today = date.today()
    start_date = today - timedelta(days=days)

    with get_session() as db:
        activities = db.execute(
            select(SupervisorActivityLog).where(
                (SupervisorActivityLog.id_supervisor == id_supervisor) &
                (SupervisorActivityLog.activity_date >= start_date) &
                (SupervisorActivityLog.status.in_(['pending', 'in_progress'])) &
                (SupervisorActivityLog.deletion_date.is_(None))
            ).order_by(
                desc(SupervisorActivityLog.activity_date)
            )
        ).scalars().all()
        return activities


def update_activity(
    id_activity: int,
    id_supervisor: int = None,
    **fields,
) -> Optional[SupervisorActivityLog]:
    """
    Actualiza un registro de actividad.

    Args:
        id_activity: ID de la actividad
        id_supervisor: ID del supervisor (para validar que es el propietario)
        **fields: Campos a actualizar (description, status, hours_spent, notes, etc.)

    Returns:
        SupervisorActivityLog: La actividad actualizada, o None si no existe
    """
    with get_session() as db:
        query_filter = SupervisorActivityLog.id_activity == id_activity

        if id_supervisor:
            query_filter = and_(query_filter, SupervisorActivityLog.id_supervisor == id_supervisor)

        activity = db.execute(
            select(SupervisorActivityLog).where(
                (query_filter) &
                (SupervisorActivityLog.deletion_date.is_(None))
            )
        ).scalar()

        if not activity:
            return None

        # Actualizar solo los campos permitidos
        allowed_fields = {'description', 'status', 'hours_spent', 'notes'}
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(activity, key, value)

        db.flush()
        db.refresh(activity)
        return activity


def delete_activity(id_activity: int, id_supervisor: int = None) -> bool:
    """
    Soft delete de un registro de actividad.

    Args:
        id_activity: ID de la actividad
        id_supervisor: ID del supervisor que la elimina (para validar propiedad)

    Returns:
        bool: True si se eliminó, False si no existe
    """
    with get_session() as db:
        query_filter = SupervisorActivityLog.id_activity == id_activity

        if id_supervisor:
            query_filter = and_(query_filter, SupervisorActivityLog.id_supervisor == id_supervisor)

        activity = db.execute(
            select(SupervisorActivityLog).where(
                (query_filter) &
                (SupervisorActivityLog.deletion_date.is_(None))
            )
        ).scalar()

        if not activity:
            return False

        activity.deletion_date = datetime.now()
        db.flush()
        return True


def get_activities_by_project(
    id_proyect: int,
    start_date: date = None,
    end_date: date = None,
) -> List[SupervisorActivityLog]:
    """
    Obtiene todas las actividades de un proyecto en un rango de fechas.
    Útil para generar reportes de proyecto.

    Args:
        id_proyect: ID del proyecto
        start_date: Fecha de inicio (default: 30 días atrás)
        end_date: Fecha de fin (default: hoy)

    Returns:
        List[SupervisorActivityLog]: Todas las actividades del proyecto
    """
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today - timedelta(days=30)

    with get_session() as db:
        activities = db.execute(
            select(SupervisorActivityLog).where(
                (SupervisorActivityLog.id_proyect == id_proyect) &
                (SupervisorActivityLog.activity_date.between(start_date, end_date)) &
                (SupervisorActivityLog.deletion_date.is_(None))
            ).order_by(desc(SupervisorActivityLog.activity_date))
        ).scalars().all()
        return activities
