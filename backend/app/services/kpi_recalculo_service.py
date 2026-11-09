"""Recalculo de indicadores bajo demanda, desde el boton "Actualizar datos" de un tablero.

El job nocturno solo recalcula una ventana de `VENTANA_DIAS` y ningun flujo recalcula al crear o cerrar una incidencia:
sin esto, un dato capturado con fecha vieja nunca llega a `kpi_snapshot`. Aqui se recalcula UN indicador por llamada, con
el rango que el widget muestra, y se reusa la misma logica del job (`recalcular_kpi_snapshots_de_claves`).

Reglas (el actor debe ser el DUENO del tablero, como en el resto del modulo):
  * solo indicadores que estan en un widget de ese tablero y que el actor puede ver (`has_kpi_permission`);
  * los KPIs "vivos" y los que ya no estan en el registry no se calculan: se reportan como omitidos;
  * el rango no pasa del tope del plan (365 dias por omision) y nunca llega al futuro;
  * si el indicador se calculo hace menos de `SEGUNDOS_MINIMOS_ENTRE_RECALCULOS`, responde "ya al dia" sin recalcular;
  * un candado de Postgres por tablero impide dos recalculos a la vez (409). En SQLite, que no lo tiene, se omite.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select, text

from app.kpis.registry import KPI_POR_CLAVE
from app.models.kpi_dashboard_widget import KpiDashboardWidget
from app.models.kpi_dashboard_widget_kpi import KpiDashboardWidgetKpi
from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.session import engine, transaction_context
from app.modules.plan import limite
from app.services.kpi_dashboard_service import KpiDashboardService
from app.utils.auth import has_kpi_permission
from app.utils.errors import AppError
from app.utils.tiempo import a_iso_utc, ahora_utc, hoy_negocio

SEGUNDOS_MINIMOS_ENTRE_RECALCULOS = 60
RANGO_DIAS_MAX_POR_OMISION = 365
MAXIMO_DE_ITEMS = 50
# Espacio de llaves del candado: una por tablero. Constante propia para no chocar con otros candados de la app.
LLAVE_BASE_DEL_CANDADO = 7_210_000


def _fecha(valor, campo) -> date:
    try:
        return date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        raise AppError('errors.invalid_field', 400, {'field': campo})


def _entero(valor, campo) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise AppError('errors.invalid_field', 400, {'field': campo})


def _items_validados(items) -> list[dict]:
    if not isinstance(items, list) or not items or len(items) > MAXIMO_DE_ITEMS:
        raise AppError('errors.invalid_field', 400, {'field': 'items'})
    dias_maximo = limite('kpi_rango_dias_max', RANGO_DIAS_MAX_POR_OMISION)
    hoy = hoy_negocio()
    validados = []
    for item in items:
        if not isinstance(item, dict):
            raise AppError('errors.invalid_field', 400, {'field': 'items'})
        inicio = _fecha(item.get('fecha_inicio'), 'fecha_inicio')
        fin = _fecha(item.get('fecha_fin'), 'fecha_fin')
        if fin < inicio:
            raise AppError('errors.invalid_field', 400, {'field': 'fecha_fin'})
        if (fin - inicio).days > dias_maximo:
            raise AppError('errors.rango_excede_limite', 400, {'field': 'fecha_fin', 'dias_maximo': dias_maximo})
        # Nunca se calcula el futuro: un rango que termina despues de hoy se recorta a hoy.
        fin = min(fin, hoy)
        inicio = min(inicio, fin)
        validados.append({'id_kpi_definition': _entero(item.get('id_kpi_definition'), 'id_kpi_definition'), 'inicio': inicio, 'fin': fin})
    return validados


class KpiRecalculoService:
    @classmethod
    def recalcular(cls, user_data: dict, id_kpi_dashboard, items) -> dict:
        from app.jobs.tasks_kpis import recalcular_kpi_snapshots_de_claves

        actor_id = KpiDashboardService.actor_id(user_data)
        validados = _items_validados(items)
        actualizados, ya_al_dia, omitidos = [], [], []

        with transaction_context() as db:
            tablero = KpiDashboardService.owned_or_404(db, id_kpi_dashboard, actor_id)
            if engine.dialect.name == 'postgresql':
                libre = db.execute(
                    text('SELECT pg_try_advisory_xact_lock(:llave)'),
                    {'llave': LLAVE_BASE_DEL_CANDADO + tablero.id_kpi_dashboard},
                ).scalar()
                if not libre:
                    raise AppError('kpis.recalculation_in_progress', 409)

            en_el_tablero = set(db.scalars(
                select(KpiDashboardWidgetKpi.id_kpi_definition)
                .join(KpiDashboardWidget, KpiDashboardWidget.id_kpi_dashboard_widget == KpiDashboardWidgetKpi.id_kpi_dashboard_widget)
                .where(KpiDashboardWidget.id_kpi_dashboard == tablero.id_kpi_dashboard, KpiDashboardWidget.deletion_date.is_(None))
            ).all())
            ahora = ahora_utc()

            for item in validados:
                id_kpi = item['id_kpi_definition']
                if id_kpi not in en_el_tablero:
                    omitidos.append({'id_kpi_definition': id_kpi, 'motivo': 'no_esta_en_el_tablero'})
                    continue
                if not has_kpi_permission(db, user_data, id_kpi):
                    omitidos.append({'id_kpi_definition': id_kpi, 'motivo': 'sin_permiso'})
                    continue
                definicion = db.get(KpiDefinition, id_kpi)
                kpi = KPI_POR_CLAVE.get(definicion.clave) if definicion else None
                if kpi is None or kpi.modo != 'snapshot':
                    omitidos.append({'id_kpi_definition': id_kpi, 'motivo': 'no_se_calcula'})
                    continue
                ultimo = db.scalar(select(func.max(KpiSnapshot.computed_at)).where(KpiSnapshot.id_kpi_definition == id_kpi))
                if ultimo is not None and ahora - ultimo < timedelta(seconds=SEGUNDOS_MINIMOS_ENTRE_RECALCULOS):
                    ya_al_dia.append(id_kpi)
                    continue
                recalcular_kpi_snapshots_de_claves(db, item['inicio'], item['fin'], [definicion.clave])
                actualizados.append(id_kpi)

        return {
            'actualizados': actualizados,
            'ya_al_dia': ya_al_dia,
            'omitidos': omitidos,
            'recalculado_en': a_iso_utc(ahora),
        }
