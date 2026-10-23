from __future__ import annotations

from sqlalchemy import select

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.models.supervisor_activity_log import SupervisorActivityLog
from app.services.base_service import CrudService


def _safe_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def sees_every_log(user_data: dict) -> bool:
    """Si el rol tiene alcance Todos sobre `supervisor_activity_log`.

    La Fase 2 general (filtrado real por Propios/Mis grupos/Todos) sigue sin
    conectar en el guardia comun -- ver `ARQUITECTURA_TYAKXA_TNY.md` seccion
    3.5 --, pero esta entidad SI tiene un dueno natural (`created_by`), asi
    que el filtro se implementa aqui mismo en vez de esperar a esa fase
    general. "Propios" es el default; solo `scope_read = 4` (Todos) ve la
    bitacora de todo el equipo.
    """
    if user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'):
        return True
    permission_id = _safe_int(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return False
    with transaction_context() as db:
        record = (
            db.query(EntityPermission)
            .filter(EntityPermission.id_permission == permission_id)
            .filter(EntityPermission.entity_name == 'supervisor_activity_log')
            .filter(EntityPermission.deletion_date.is_(None))
            .first()
        )
        return bool(record and int(record.scope_read) == 4)


class SupervisorActivityLogService(CrudService):
    model = SupervisorActivityLog
    primary_key = 'id_supervisor_activity_log'
    entity_name = 'supervisor_activity_log'
    solo_vigentes = True

    @classmethod
    def missing_dates(cls, id_user: int, dates: list) -> list:
        """De la lista de fechas dadas, cuales no tienen fila para ese usuario."""
        if not dates:
            return []
        with transaction_context() as db:
            existentes = set(
                db.scalars(
                    select(SupervisorActivityLog.activity_date)
                    .where(SupervisorActivityLog.id_user == id_user)
                    .where(SupervisorActivityLog.deletion_date.is_(None))
                    .where(SupervisorActivityLog.activity_date.in_(dates))
                ).all()
            )
        return [fecha for fecha in dates if fecha not in existentes]
