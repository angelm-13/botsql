"""Widgets de un tablero de KPIs: heredan el dueno del tablero padre.

El widget no tiene `id_user` propio, asi que toda operacion pasa primero
por confirmar que el tablero (`kpi_dashboard`) es del actor -reusando
`KpiDashboardService.owned_or_404`, mismo criterio de "404 y no 403" para
no delatar que el tablero ajeno existe- antes de tocar el widget.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.models.kpi_dashboard_widget import KpiDashboardWidget
from app.models.kpi_dashboard_widget_kpi import KpiDashboardWidgetKpi
from app.models.kpi_definition import KpiDefinition
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.services.kpi_dashboard_service import KpiDashboardService
from app.utils.auth import has_kpi_permission
from app.utils.errors import AppError

# "dona" y no "pastel": el mockup original mostraba un donut con hueco en el
# centro, no un pastel completo. El nombre tiene que ser el mismo en modelo,
# API y frontend -- se elige aqui porque es donde nace el contrato.
TIPOS_GRAFICA = {'numero', 'barras', 'linea', 'area', 'dona'}


class KpiDashboardWidgetService(CrudService):
    model = KpiDashboardWidget
    primary_key = 'id_kpi_dashboard_widget'
    entity_name = 'kpi_dashboard_widget'

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        """Baja logica, igual que KpiDashboardService.delete."""
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
                before=cls._format_audit_delete_before(before), after='Widget eliminado', field_name='*',
            )
            session.flush()
            return {'message_key': 'success.deleted'}

    @classmethod
    def _widget_owned_or_404(cls, session, id_kpi_dashboard_widget, actor_id: int) -> KpiDashboardWidget:
        try:
            id_kpi_dashboard_widget = int(id_kpi_dashboard_widget)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.resource_not_found', 404) from exc

        widget = session.get(KpiDashboardWidget, id_kpi_dashboard_widget)
        if widget is None or widget.deletion_date is not None:
            raise AppError('errors.resource_not_found', 404)
        # El widget hereda el dueno de su tablero: si el tablero no es del
        # actor, el widget tampoco existe para el.
        KpiDashboardService.owned_or_404(session, widget.id_kpi_dashboard, actor_id)
        return widget

    @classmethod
    def _validar_kpi_o_falla(cls, session, user_data: dict, id_kpi_definition) -> int:
        try:
            id_kpi_definition = int(id_kpi_definition)
        except (TypeError, ValueError) as exc:
            raise AppError('errors.required_field', 400, {'field': 'id_kpi_definition'}) from exc

        kpi = session.get(KpiDefinition, id_kpi_definition)
        if kpi is None or kpi.deletion_date is not None:
            raise AppError('errors.invalid_field', 400, {'field': 'id_kpi_definition'})
        # Sin esto un usuario podria guardar un widget apuntando a un KPI que
        # no le corresponde: `/kpi_snapshot/query` se lo negaria al leerlo,
        # pero mejor no dejar guardar la referencia rota desde el alta.
        if not has_kpi_permission(session, user_data, id_kpi_definition, 'read'):
            raise AppError('errors.permission_denied', 403, {'kpi': id_kpi_definition})
        return id_kpi_definition

    @classmethod
    def _validar_kpis_o_falla(cls, session, user_data: dict, ids_kpi_definition) -> list[int]:
        """Valida la lista completa antes de tocar nada: todo o nada.

        Se llama SIEMPRE dentro de una transaccion que todavia no escribio
        ningun cambio de `create_widget`/`update_widget` -- si cualquier id de
        la lista falla (no existe, o el actor no tiene permiso sobre el),
        esto revienta antes de que se cree o edite una sola fila.
        """
        if not isinstance(ids_kpi_definition, (list, tuple)) or not ids_kpi_definition:
            raise AppError('errors.required_field', 400, {'field': 'ids_kpi_definition'})

        vistos = set()
        validados = []
        for id_kpi_definition in ids_kpi_definition:
            id_validado = cls._validar_kpi_o_falla(session, user_data, id_kpi_definition)
            if id_validado in vistos:
                # El mismo KPI repetido en la lista: se ignora la repeticion en
                # vez de reventar contra el UNIQUE de kpi_dashboard_widget_kpi.
                continue
            vistos.add(id_validado)
            validados.append(id_validado)
        return validados

    @classmethod
    def _reemplazar_kpis(cls, session, id_kpi_dashboard_widget: int, ids_kpi_definition: list[int]) -> None:
        """Sustituye por completo los KPIs de un widget por esta lista.

        El orden que se guarda es la posicion dentro de la lista recibida
        (100, 200, 300...), el mismo criterio de espaciado que ya usa
        `posicion_orden` en `kpi_dashboard_widget` -- deja hueco para
        reordenar despues sin tener que recorrer toda la lista.
        """
        session.execute(
            delete(KpiDashboardWidgetKpi).where(
                KpiDashboardWidgetKpi.id_kpi_dashboard_widget == id_kpi_dashboard_widget,
            )
        )
        for indice, id_kpi_definition in enumerate(ids_kpi_definition):
            session.add(KpiDashboardWidgetKpi(
                id_kpi_dashboard_widget=id_kpi_dashboard_widget,
                id_kpi_definition=id_kpi_definition,
                orden=(indice + 1) * 100,
            ))
        session.flush()

    @classmethod
    def _ids_kpi_definition_de(cls, session, id_kpi_dashboard_widget: int) -> list[int]:
        return list(session.scalars(
            select(KpiDashboardWidgetKpi.id_kpi_definition)
            .where(KpiDashboardWidgetKpi.id_kpi_dashboard_widget == id_kpi_dashboard_widget)
            .order_by(KpiDashboardWidgetKpi.orden, KpiDashboardWidgetKpi.id_kpi_dashboard_widget_kpi)
        ))

    @classmethod
    def _kpis_de_widgets(cls, session, ids_kpi_dashboard_widget: list[int]) -> dict[int, list[int]]:
        """`id_kpi_dashboard_widget -> [id_kpi_definition, ...]` ordenado.

        Una sola consulta para todos los widgets del tablero, en vez de una
        por widget -- `list_by_dashboard` la usa para no volver N+1.
        """
        resultado = {id_widget: [] for id_widget in ids_kpi_dashboard_widget}
        if not ids_kpi_dashboard_widget:
            return resultado
        filas = session.execute(
            select(KpiDashboardWidgetKpi.id_kpi_dashboard_widget, KpiDashboardWidgetKpi.id_kpi_definition)
            .where(KpiDashboardWidgetKpi.id_kpi_dashboard_widget.in_(ids_kpi_dashboard_widget))
            .order_by(
                KpiDashboardWidgetKpi.id_kpi_dashboard_widget,
                KpiDashboardWidgetKpi.orden,
                KpiDashboardWidgetKpi.id_kpi_dashboard_widget_kpi,
            )
        ).all()
        for id_widget, id_kpi_definition in filas:
            resultado[id_widget].append(id_kpi_definition)
        return resultado

    @staticmethod
    def _validar_tipo_grafica(payload: dict) -> str:
        tipo_grafica = str((payload or {}).get('tipo_grafica') or '').strip().lower()
        if tipo_grafica not in TIPOS_GRAFICA:
            raise AppError('errors.invalid_field', 400, {'field': 'tipo_grafica', 'allowed': sorted(TIPOS_GRAFICA)})
        return tipo_grafica

    @classmethod
    def list_by_dashboard(cls, user_data: dict, id_kpi_dashboard) -> dict:
        actor_id = KpiDashboardService.actor_id(user_data)
        with transaction_context() as session:
            KpiDashboardService.owned_or_404(session, id_kpi_dashboard, actor_id)
            items = session.scalars(
                select(KpiDashboardWidget)
                .where(
                    KpiDashboardWidget.id_kpi_dashboard == int(id_kpi_dashboard),
                    KpiDashboardWidget.deletion_date.is_(None),
                )
                .order_by(KpiDashboardWidget.posicion_orden, KpiDashboardWidget.id_kpi_dashboard_widget)
            ).all()
            kpis_por_widget = cls._kpis_de_widgets(session, [item.id_kpi_dashboard_widget for item in items])
            serializados = []
            for item in items:
                fila = item.serialize()
                fila['ids_kpi_definition'] = kpis_por_widget[item.id_kpi_dashboard_widget]
                serializados.append(fila)
            return {'items': serializados}

    @classmethod
    def create_widget(cls, user_data: dict, id_kpi_dashboard, payload: dict) -> dict:
        actor_id = KpiDashboardService.actor_id(user_data)
        payload = dict(payload or {})
        tipo_grafica = cls._validar_tipo_grafica(payload)

        with transaction_context() as session:
            KpiDashboardService.owned_or_404(session, id_kpi_dashboard, actor_id)
            ids_kpi_definition = cls._validar_kpis_o_falla(session, user_data, payload.get('ids_kpi_definition'))

        data = {
            'id_kpi_dashboard': int(id_kpi_dashboard),
            'tipo_grafica': tipo_grafica,
        }
        if payload.get('parametros') is not None:
            data['parametros'] = payload['parametros']
        if payload.get('posicion_orden') not in (None, ''):
            data['posicion_orden'] = payload['posicion_orden']

        creado = cls.create(data, user_id=actor_id)
        with transaction_context() as session:
            cls._reemplazar_kpis(session, creado['id_kpi_dashboard_widget'], ids_kpi_definition)
        creado['ids_kpi_definition'] = ids_kpi_definition
        return creado

    @classmethod
    def update_widget(cls, user_data: dict, id_kpi_dashboard_widget, payload: dict) -> dict:
        actor_id = KpiDashboardService.actor_id(user_data)
        payload = dict(payload or {})
        if 'tipo_grafica' in payload:
            payload['tipo_grafica'] = cls._validar_tipo_grafica(payload)
        # Ni el tablero ni la llave primaria se reasignan desde un update de
        # widget. La lista de KPIs se maneja aparte (tabla puente, no columna
        # de este modelo), asi que tambien se saca del payload que llega al
        # CRUD generico.
        payload.pop('id_kpi_dashboard', None)
        payload.pop('id_kpi_dashboard_widget', None)
        hay_lista_nueva = 'ids_kpi_definition' in payload
        ids_kpi_definition_crudo = payload.pop('ids_kpi_definition', None)

        with transaction_context() as session:
            cls._widget_owned_or_404(session, id_kpi_dashboard_widget, actor_id)
            ids_kpi_definition = (
                cls._validar_kpis_o_falla(session, user_data, ids_kpi_definition_crudo)
                if hay_lista_nueva else None
            )

        resultado = cls.update(id_kpi_dashboard_widget, payload, user_id=actor_id)

        with transaction_context() as session:
            if hay_lista_nueva:
                cls._reemplazar_kpis(session, int(id_kpi_dashboard_widget), ids_kpi_definition)
                resultado['ids_kpi_definition'] = ids_kpi_definition
            else:
                resultado['ids_kpi_definition'] = cls._ids_kpi_definition_de(session, int(id_kpi_dashboard_widget))

        return resultado

    @classmethod
    def delete_widget(cls, user_data: dict, id_kpi_dashboard_widget) -> dict:
        actor_id = KpiDashboardService.actor_id(user_data)
        with transaction_context() as session:
            cls._widget_owned_or_404(session, id_kpi_dashboard_widget, actor_id)
        return cls.delete(id_kpi_dashboard_widget, user_id=actor_id)
