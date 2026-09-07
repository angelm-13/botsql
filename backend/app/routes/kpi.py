from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.session import transaction_context
from app.services.invoice_service import InvoiceService
from app.utils.auth import has_kpi_permission, require_entity_permission, token_required
from app.utils.errors import AppError

bp_kpi = Blueprint('kpi', __name__)


def _required_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise AppError('errors.invalid_field', 400, {'field': field})


def _required_date(value, field):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise AppError('errors.invalid_field', 400, {'field': field})


def _optional_date(value, field):
    return _required_date(value, field) if value else None


def _optional_empleados(value):
    if not value:
        return None
    ids = [_required_int(chunk.strip(), 'empleados') for chunk in str(value).split(',') if chunk.strip()]
    return ids or None


def _dimension_user_text():
    # `.contains()`/`[]` sobre `dimension_key` necesitan `cast(..., JSONB)`:
    # el tipo declarado en el modelo es el JSON generico con variante, y
    # `with_variant` solo cambia el DDL/bind, no el comparador de Python. Ver
    # el comentario en app/models/kpi_snapshot.py.
    return cast(KpiSnapshot.dimension_key, JSONB)['id_user'].astext


def _totales(db, id_kpi_definition, fecha_inicio, fecha_fin, actor_project, empleados):
    id_user_expr = _dimension_user_text()
    condiciones = [
        KpiSnapshot.id_kpi_definition == id_kpi_definition,
        KpiSnapshot.periodo >= fecha_inicio,
        KpiSnapshot.periodo <= fecha_fin,
    ]
    if actor_project is not None:
        condiciones.append(cast(KpiSnapshot.dimension_key, JSONB).contains({'id_proyect': actor_project}))
    if empleados:
        condiciones.append(id_user_expr.in_([str(id_empleado) for id_empleado in empleados]))

    filas = db.execute(
        select(id_user_expr, func.sum(KpiSnapshot.valor))
        .where(*condiciones)
        .group_by(id_user_expr)
    ).all()

    por_empleado = {id_user: float(valor) for id_user, valor in filas if id_user is not None}
    return {
        'inicio': fecha_inicio.isoformat(),
        'fin': fecha_fin.isoformat(),
        'total': sum(por_empleado.values()),
        'por_empleado': por_empleado,
    }


@bp_kpi.route('/kpi_definition/', methods=['GET'])
@token_required
@require_entity_permission('kpi_definition', 'read')
def list_kpi_definitions(user_data):
    with transaction_context() as db:
        kpis = db.scalars(
            select(KpiDefinition).where(KpiDefinition.deletion_date.is_(None))
        ).all()
        items = [
            {
                'clave': kpi.clave,
                'etiqueta': kpi.etiqueta,
                'modulo': kpi.modulo,
                'dimensiones': kpi.dimensiones,
                'unidad': kpi.unidad,
            }
            for kpi in kpis
            if has_kpi_permission(db, user_data, kpi.id_kpi_definition, 'read')
        ]
    return jsonify({'items': items})


@bp_kpi.route('/kpi_snapshot/query', methods=['GET'])
@token_required
@require_entity_permission('kpi_definition', 'read')
def query_kpi_snapshot(user_data):
    id_kpi_definition = _required_int(request.args.get('id_kpi_definition'), 'id_kpi_definition')
    fecha_inicio = _required_date(request.args.get('fecha_inicio'), 'fecha_inicio')
    fecha_fin = _required_date(request.args.get('fecha_fin'), 'fecha_fin')
    fecha_inicio_b = _optional_date(request.args.get('fecha_inicio_b'), 'fecha_inicio_b')
    fecha_fin_b = _optional_date(request.args.get('fecha_fin_b'), 'fecha_fin_b')
    empleados = _optional_empleados(request.args.get('empleados'))

    with transaction_context() as db:
        if not has_kpi_permission(db, user_data, id_kpi_definition, 'read'):
            raise AppError('errors.permission_denied', 403, {'kpi': id_kpi_definition})

        # Alcance del actor. KPI_REGISTRY hoy solo tiene "ventas_por_empleado",
        # de facturacion, cuyo alcance natural -igual que las facturas que
        # suma- es el proyecto. Se reutiliza tal cual
        # InvoiceService.actor_project (es un @staticmethod que no toca nada
        # de Invoice, solo user_data) en vez de duplicar el criterio de
        # "superusuario ve todo, el resto exige id_proyect". Cuando exista un
        # KPI de otro modulo con otra convencion de alcance -RRHH por
        # departamento, por ejemplo, no por proyecto- este punto tendra que
        # generalizarse a un alcance por-modulo en vez de seguir atado a
        # InvoiceService.
        actor_project = InvoiceService.actor_project(user_data)

        rango_a = _totales(db, id_kpi_definition, fecha_inicio, fecha_fin, actor_project, empleados)
        rango_b = None
        if fecha_inicio_b and fecha_fin_b:
            rango_b = _totales(db, id_kpi_definition, fecha_inicio_b, fecha_fin_b, actor_project, empleados)

    return jsonify({'rango_a': rango_a, 'rango_b': rango_b})
