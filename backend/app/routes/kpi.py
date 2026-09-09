from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.kpis.registry import ALCANCE_PROYECTO_POR_CLAVE
from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.user import User
from app.modules.plan import limite
from app.services.invoice_service import InvoiceService
from app.services.kpi_dashboard_service import KpiDashboardService
from app.services.kpi_dashboard_widget_service import KpiDashboardWidgetService
from app.utils.auth import has_kpi_permission, require_entity_permission, token_required
from app.utils.errors import AppError

# Salvo que el plan del cliente declare otro valor en `limites.kpi_rango_dias_max`
# (ver `app/modules/plan.py`), una consulta no puede pedir mas de un anio de
# historico de una sola vez: sin tope, un rango sin fin es una tabla completa
# escaneada por peticion.
KPI_RANGO_DIAS_MAX_POR_OMISION = 365

bp_kpi = Blueprint('kpi', __name__)
bp_kpi_dashboard = Blueprint('kpi_dashboard', __name__, url_prefix='/kpi_dashboard')
bp_kpi_dashboard_widget = Blueprint('kpi_dashboard_widget', __name__, url_prefix='/kpi_dashboard_widget')


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


def _optional_int_list(value, field):
    if not value:
        return None
    ids = [_required_int(chunk.strip(), field) for chunk in str(value).split(',') if chunk.strip()]
    return ids or None


def _optional_empleados(value):
    return _optional_int_list(value, 'empleados')


def _optional_id_departments(value):
    return _optional_int_list(value, 'id_departments')


def _validar_rango(fecha_inicio, fecha_fin, dias_maximo, field):
    dias = (fecha_fin - fecha_inicio).days
    if dias > dias_maximo:
        raise AppError('errors.rango_excede_limite', 400, {'field': field, 'dias_maximo': dias_maximo})


def _empleados_de_departamentos(db, id_departments):
    """`id_user` de todos los empleados cuyo `Permission.id_department` este
    en `id_departments`. `User.id_department` no existe -- la pertenencia
    pasa por `Permission` (ver `app/models/permission.py`)."""
    permisos_del_departamento = select(Permission.id_permission).where(
        Permission.id_department.in_(id_departments),
        Permission.deletion_date.is_(None),
    )
    return db.scalars(
        select(User.id_user).where(
            User.id_permission.in_(permisos_del_departamento),
            User.deletion_date.is_(None),
        )
    ).all()


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
    # `is not None`, no truthy: una lista vacia (departamento sin empleados,
    # ver `_empleados_de_departamentos`) tiene que filtrar a "nadie", no
    # saltarse el filtro por completo. SQLAlchemy compila `IN (())` como una
    # condicion siempre falsa, asi que es seguro.
    if empleados is not None:
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
                'id_kpi_definition': kpi.id_kpi_definition,
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
    id_departments = _optional_id_departments(request.args.get('id_departments'))

    # Salvo que el plan del cliente declare otro valor, un rango no puede
    # pedir mas de un anio de una sola vez (ver el comentario junto a
    # KPI_RANGO_DIAS_MAX_POR_OMISION).
    dias_maximo = limite('kpi_rango_dias_max', KPI_RANGO_DIAS_MAX_POR_OMISION)
    _validar_rango(fecha_inicio, fecha_fin, dias_maximo, 'fecha_fin')
    if fecha_inicio_b and fecha_fin_b:
        _validar_rango(fecha_inicio_b, fecha_fin_b, dias_maximo, 'fecha_fin_b')

    with transaction_context() as db:
        if not has_kpi_permission(db, user_data, id_kpi_definition, 'read'):
            raise AppError('errors.permission_denied', 403, {'kpi': id_kpi_definition})

        # Alcance del actor. Los primeros 3 KPIs de KPI_REGISTRY (facturacion,
        # operaciones/tareas) miden entidades con id_proyect real, cuyo
        # alcance natural es el proyecto -- se reutiliza tal cual
        # InvoiceService.actor_project (es un @staticmethod que no toca nada
        # de Invoice, solo user_data) en vez de duplicar el criterio de
        # "superusuario ve todo, el resto exige id_proyect". Pero KPIs como
        # "vales_vencidos_por_responsable" o "incidentes_resueltos_por_empleado"
        # miden Incident/NmIncidentProduct, que no tienen id_proyect en NINGUN
        # punto de la cadena -- exigirles un alcance de proyecto los dejaria
        # sin una sola fila para cualquier no-superusuario (ver
        # KpiDefinition.alcance_proyecto en app/kpis/registry.py, y
        # tasks_kpis.py, que por el mismo motivo los calcula una sola vez en
        # vez de una vez por proyecto activo). Por eso se resuelve el alcance
        # por KPI (via su `clave`) antes de decidir si aplica algun filtro de
        # proyecto: la generalizacion que este comentario ya anticipaba.
        kpi_row = db.get(KpiDefinition, id_kpi_definition)
        alcance_proyecto = ALCANCE_PROYECTO_POR_CLAVE.get(kpi_row.clave, True) if kpi_row else True
        actor_project = InvoiceService.actor_project(user_data) if alcance_proyecto else None

        # id_departments se resuelve a id_user (via Permission.id_department)
        # y se combina con "empleados": si vienen los dos, interseccion; si
        # solo viene el departamento, esa lista completa hace de filtro de
        # empleados. Una lista vacia (departamento sin nadie) filtra a
        # "nadie" -- ver el comentario en `_totales`.
        if id_departments:
            usuarios_del_departamento = _empleados_de_departamentos(db, id_departments)
            if empleados is not None:
                empleados = [id_empleado for id_empleado in empleados if id_empleado in usuarios_del_departamento]
            else:
                empleados = list(usuarios_del_departamento)

        rango_a = _totales(db, id_kpi_definition, fecha_inicio, fecha_fin, actor_project, empleados)
        rango_b = None
        if fecha_inicio_b and fecha_fin_b:
            rango_b = _totales(db, id_kpi_definition, fecha_inicio_b, fecha_fin_b, actor_project, empleados)

    return jsonify({'rango_a': rango_a, 'rango_b': rango_b})


# --- kpi_dashboard: tableros del usuario, siempre privados por dueno -------
#
# No se construye con `create_crud_blueprint`
# (app/routes/logistics_workflow.py): ese generico llama a `service.list`/
# `get`/`create`/`update`/`delete` sin ningun filtro de propiedad -- su
# supuesto es "cualquier actor con el bit de la entidad ve/edita cualquier
# fila", que es exactamente correcto para logistica (acotada por proyecto,
# no por usuario) y exactamente incorrecto aqui: expondria el tablero de
# cualquier usuario a cualquier otro con el modulo "kpis" concedido, sin
# siquiera la excepcion de superusuario que si existe en otros modulos. Por
# eso las rutas llaman a los metodos `_own`/`_widget` del servicio, que
# resuelven el alcance por dueno antes de tocar el CRUD generico.

@bp_kpi_dashboard.route('/', methods=['GET'])
@token_required
@require_entity_permission('kpi_dashboard', 'read')
def list_kpi_dashboards(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    return jsonify(KpiDashboardService.list_own(user_data, page=page, per_page=per_page))


@bp_kpi_dashboard.route('/', methods=['POST'])
@token_required
@require_entity_permission('kpi_dashboard', 'create')
def create_kpi_dashboard(user_data):
    return jsonify(KpiDashboardService.create_own(user_data, request.get_json(silent=True) or {})), 201


@bp_kpi_dashboard.route('/<id_kpi_dashboard>', methods=['PUT'])
@token_required
@require_entity_permission('kpi_dashboard', 'update')
def update_kpi_dashboard(user_data, id_kpi_dashboard):
    return jsonify(KpiDashboardService.update_own(user_data, id_kpi_dashboard, request.get_json(silent=True) or {}))


@bp_kpi_dashboard.route('/<id_kpi_dashboard>', methods=['DELETE'])
@token_required
@require_entity_permission('kpi_dashboard', 'delete')
def delete_kpi_dashboard(user_data, id_kpi_dashboard):
    return jsonify(KpiDashboardService.delete_own(user_data, id_kpi_dashboard))


@bp_kpi_dashboard.route('/<id_kpi_dashboard>/widgets/', methods=['GET'])
@token_required
@require_entity_permission('kpi_dashboard_widget', 'read')
def list_kpi_dashboard_widgets(user_data, id_kpi_dashboard):
    return jsonify(KpiDashboardWidgetService.list_by_dashboard(user_data, id_kpi_dashboard))


@bp_kpi_dashboard.route('/<id_kpi_dashboard>/widgets/', methods=['POST'])
@token_required
@require_entity_permission('kpi_dashboard_widget', 'create')
def create_kpi_dashboard_widget(user_data, id_kpi_dashboard):
    payload = request.get_json(silent=True) or {}
    return jsonify(KpiDashboardWidgetService.create_widget(user_data, id_kpi_dashboard, payload)), 201


@bp_kpi_dashboard_widget.route('/<id_kpi_dashboard_widget>', methods=['PUT'])
@token_required
@require_entity_permission('kpi_dashboard_widget', 'update')
def update_kpi_dashboard_widget(user_data, id_kpi_dashboard_widget):
    payload = request.get_json(silent=True) or {}
    return jsonify(KpiDashboardWidgetService.update_widget(user_data, id_kpi_dashboard_widget, payload))


@bp_kpi_dashboard_widget.route('/<id_kpi_dashboard_widget>', methods=['DELETE'])
@token_required
@require_entity_permission('kpi_dashboard_widget', 'delete')
def delete_kpi_dashboard_widget(user_data, id_kpi_dashboard_widget):
    return jsonify(KpiDashboardWidgetService.delete_widget(user_data, id_kpi_dashboard_widget))
