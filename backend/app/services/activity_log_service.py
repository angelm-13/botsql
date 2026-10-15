from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, desc, and_

from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.activity_log_worker import ActivityLogWorker
from app.models.team import Team
from app.models.nm_team_user import NmTeamUser
from app.models.user import User
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.tiempo import ahora_utc


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

    with transaction_context() as db:
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
    with transaction_context() as db:
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
    ids_supervisor: list = None,
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
    with transaction_context() as db:
        query = select(SupervisorActivityLog).where(
            SupervisorActivityLog.deletion_date.is_(None)
        )

        # Filtros opcionales
        if id_proyect:
            query = query.where(SupervisorActivityLog.id_proyect == id_proyect)

        if id_supervisor:
            query = query.where(SupervisorActivityLog.id_supervisor == id_supervisor)

        # Con Mis grupos: las bitacoras de todo el equipo (ver routes/activity_logs).
        if ids_supervisor is not None:
            query = query.where(SupervisorActivityLog.id_supervisor.in_(list(ids_supervisor)))

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

    with transaction_context() as db:
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
    with transaction_context() as db:
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
    with transaction_context() as db:
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

        activity.deletion_date = ahora_utc()
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

    with transaction_context() as db:
        activities = db.execute(
            select(SupervisorActivityLog).where(
                (SupervisorActivityLog.id_proyect == id_proyect) &
                (SupervisorActivityLog.activity_date.between(start_date, end_date)) &
                (SupervisorActivityLog.deletion_date.is_(None))
            ).order_by(desc(SupervisorActivityLog.activity_date))
        ).scalars().all()
        return activities


def list_my_team_workers(id_jefe_taller: int) -> List[dict]:
    """La plantilla del Jefe de taller: los `user` de sus propios `team`.

    No se inventa un rol de "obrero" -- pedido explicito de negocio
    (2026-09-28): los obreros son usuarios sin ningun rol operativo,
    agrupados por el Jefe de taller en un equipo generico (`team`/
    `nm_team_user`), el mismo mecanismo que ya existe para otros usos. "Su"
    equipo es el que el mismo creo (`team.created_by`); no hay un campo de
    lider aparte todavia.
    """
    with transaction_context() as db:
        rows = db.execute(
            select(User.id_user, User.full_name, User.username)
            .join(NmTeamUser, NmTeamUser.id_user == User.id_user)
            .join(Team, Team.id_team == NmTeamUser.id_team)
            .where(
                (Team.created_by == id_jefe_taller) &
                (Team.deletion_date.is_(None)) &
                (NmTeamUser.deletion_date.is_(None)) &
                (User.deletion_date.is_(None))
            )
            .order_by(User.full_name)
        ).all()
        return [
            {"id_user": r.id_user, "full_name": r.full_name, "username": r.username}
            for r in rows
        ]


def set_activity_workers(id_activity: int, id_jefe_taller: int, worker_ids: List[int]) -> List[dict]:
    """Fija quien de la plantilla participo en esta bitacora (reemplaza).

    Cada `id_user` debe pertenecer a un `team` del propio Jefe de taller --
    sin este candado, cualquiera podria atribuirle la jornada de hoy a un
    obrero que ni siquiera es suyo.
    """
    with transaction_context() as db:
        propios = {
            r.id_user for r in db.execute(
                select(User.id_user)
                .join(NmTeamUser, NmTeamUser.id_user == User.id_user)
                .join(Team, Team.id_team == NmTeamUser.id_team)
                .where(
                    (Team.created_by == id_jefe_taller) &
                    (Team.deletion_date.is_(None)) &
                    (NmTeamUser.deletion_date.is_(None))
                )
            ).all()
        }
        ajenos = [w for w in worker_ids if int(w) not in propios]
        if ajenos:
            raise AppError("errors.worker_not_in_team", 400, {"worker_ids": ajenos})

        # Reemplaza: se borran (fisico, es tabla puente) los renglones que ya
        # no vienen y se agregan los nuevos -- una bitacora no acumula
        # obreros de intentos anteriores del mismo dia.
        db.query(ActivityLogWorker).filter(
            ActivityLogWorker.id_activity == id_activity
        ).delete()
        for id_user in worker_ids:
            db.add(ActivityLogWorker(
                id_activity=id_activity, id_user=id_user, created_by=id_jefe_taller,
            ))
        db.flush()

        rows = db.execute(
            select(User.id_user, User.full_name)
            .join(ActivityLogWorker, ActivityLogWorker.id_user == User.id_user)
            .where(ActivityLogWorker.id_activity == id_activity)
        ).all()
        return [{"id_user": r.id_user, "full_name": r.full_name} for r in rows]


def get_activity_workers(id_activity: int) -> List[dict]:
    with transaction_context() as db:
        rows = db.execute(
            select(User.id_user, User.full_name)
            .join(ActivityLogWorker, ActivityLogWorker.id_user == User.id_user)
            .where(ActivityLogWorker.id_activity == id_activity)
        ).all()
        return [{"id_user": r.id_user, "full_name": r.full_name} for r in rows]
