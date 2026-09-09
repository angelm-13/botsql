"""Tableros de KPIs: SIEMPRE privados por dueno, sin excepcion de rol.

Por que no es list_scoped/require_scope de InvoiceService
-----------------------------------------------------------
InvoiceService acota por proyecto y deja pasar sin filtro al superusuario
(`actor_project()` devuelve `None` para el bootstrap admin): un
administrador SI puede ver la factura de cualquier proyecto. Aqui la regla
es otra, decidida desde el diseno original de este modulo: un tablero es
del usuario que lo armo, punto, sin excepcion de rol. Ni Administrator ve
el tablero de otra persona. Por eso el filtro `id_user == actor` se aplica
siempre -- superusuario incluido-- y no hay un `None` que lo desactive.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.kpi_dashboard import KpiDashboard
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError


class KpiDashboardService(CrudService):
    model = KpiDashboard
    primary_key = 'id_kpi_dashboard'
    entity_name = 'kpi_dashboard'

    @staticmethod
    def actor_id(user_data: dict) -> int:
        try:
            return int(user_data.get('id_user'))
        except (TypeError, ValueError):
            raise AppError('errors.auth_required', 401)

    @staticmethod
    def owned_or_404(session, id_kpi_dashboard, actor_id: int) -> KpiDashboard:
        """El tablero, si es del actor. 404 -no 403- si no.

        Mismo criterio que InvoiceService.require_scope: quien no es dueno
        no debe ni enterarse de que el tablero existe.
        """
        try:
            id_kpi_dashboard = int(id_kpi_dashboard)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.resource_not_found', 404) from exc

        dashboard = session.get(KpiDashboard, id_kpi_dashboard)
        if dashboard is None or dashboard.deletion_date is not None or dashboard.id_user != actor_id:
            raise AppError('errors.resource_not_found', 404)
        return dashboard

    @classmethod
    def list_own(cls, user_data: dict, page: int = 1, per_page: int = 20) -> dict:
        actor_id = cls.actor_id(user_data)
        with transaction_context() as session:
            stmt = (
                select(KpiDashboard)
                .where(KpiDashboard.id_user == actor_id, KpiDashboard.deletion_date.is_(None))
                .order_by(KpiDashboard.orden, KpiDashboard.id_kpi_dashboard)
            )
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            items = session.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
            return {
                'items': [item.serialize() for item in items],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
            }

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        """Baja logica (`deletion_date`), no `session.delete`.

        El CRUD generico borra fisico. Mismo criterio que ya usa
        `EntityPermissionService.delete`: la fila queda para consulta y el
        registro de quien la borro y cuando no se pierde.
        """
        from datetime import datetime, timezone

        with transaction_context() as session:
            item = session.get(cls.model, item_id)
            if not item:
                raise AppError('errors.resource_not_found', status_code=404)
            if item.deletion_date is not None:
                return {'message_key': 'success.deleted'}
            before = item.serialize()
            item.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
            cls._write_event_log(
                session, action='delete', actor_id=user_id,
                before=cls._format_audit_delete_before(before), after='Tablero eliminado', field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}

    @classmethod
    def create_own(cls, user_data: dict, payload: dict) -> dict:
        actor_id = cls.actor_id(user_data)
        nombre = str((payload or {}).get('nombre') or '').strip()
        if not nombre:
            raise AppError('errors.required_field', 400, {'field': 'nombre'})

        data = {'nombre': nombre, 'id_user': actor_id, 'created_by': actor_id}
        if (payload or {}).get('orden') not in (None, ''):
            data['orden'] = payload['orden']
        return cls.create(data, user_id=actor_id)

    @classmethod
    def update_own(cls, user_data: dict, id_kpi_dashboard, payload: dict) -> dict:
        actor_id = cls.actor_id(user_data)
        with transaction_context() as session:
            cls.owned_or_404(session, id_kpi_dashboard, actor_id)

        # El dueno ya esta confirmado; se delega en el CRUD generico para
        # coercion/validacion/auditoria, sin dejar que el payload reasigne
        # el dueno ni la llave primaria.
        payload = dict(payload or {})
        payload.pop('id_user', None)
        payload.pop('id_kpi_dashboard', None)
        return cls.update(id_kpi_dashboard, payload, user_id=actor_id)

    @classmethod
    def delete_own(cls, user_data: dict, id_kpi_dashboard) -> dict:
        actor_id = cls.actor_id(user_data)
        with transaction_context() as session:
            cls.owned_or_404(session, id_kpi_dashboard, actor_id)
        # Baja logica simple. Si es la ultima pestana del usuario, no se crea
        # una de repuesto aqui: la pantalla vacia y el boton de "+" son
        # responsabilidad del frontend, no de este servicio.
        return cls.delete(id_kpi_dashboard, user_id=actor_id)
