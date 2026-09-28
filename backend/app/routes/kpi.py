from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.kpis.registry import (
    AGREGACION_POR_CLAVE, ALCANCE_PROYECTO_POR_CLAVE, DIMENSION_JSON_KEY, DIMENSION_POR_CLAVE, KPI_POR_CLAVE,
)
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


def _optional_entidades(value):
    # Generico, dimension-agnostico: filtra por la entidad que el KPI
    # desglosa de verdad (empleado o producto). "empleados" (arriba) se
    # conserva como sinonimo por compatibilidad -- es el nombre que ya manda
    # el frontend para los KPIs por empleado.
    return _optional_int_list(value, 'entidades')


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


def _dimension_entity_expr(campo_json):
    # `.contains()`/`[]` sobre `dimension_key` necesitan `cast(..., JSONB)`:
    # el tipo declarado en el modelo es el JSON generico con variante, y
    # `with_variant` solo cambia el DDL/bind, no el comparador de Python. Ver
    # el comentario en app/models/kpi_snapshot.py.
    #
    # `campo_json` viene de `DIMENSION_JSON_KEY` (app/kpis/registry.py):
    # "id_user" para KPIs por empleado, "id_product" para KPIs por producto.
    # Antes esta funcion asumia siempre "id_user" -- ahora la llama cada KPI
    # con la llave que de verdad le corresponde.
    return cast(KpiSnapshot.dimension_key, JSONB)[campo_json].astext


def _totales(db, id_kpi_definition, fecha_inicio, fecha_fin, actor_project, entidades, campo_json, agregacion, agrupar_por_periodo=False):
    """Combina `kpi_snapshot` en el rango, en uno de tres modos:

    * `campo_json` es None (dimension "global", ej. ingresos/egresos
      totales): no hay entidad que desglosar -- un solo total.
    * `agrupar_por_periodo=True`: se combina entre TODAS las entidades por
      `periodo` (dia) -- la serie de tendencia en el tiempo que pidio Aurora
      ("Ambas, seleccionable": por empleado/producto O por periodo).
    * si no, el comportamiento de siempre: un valor por entidad
      (`por_empleado`, el nombre historico del campo -- se conserva tal cual
      aunque ahora tambien puede traer productos, para no romper el resto del
      frontend que ya lo lee).

    COMO se combina lo decide `agregacion`, declarada por cada KPI (ver
    AGREGACIONES en app/kpis/registry.py). Antes aqui se sumaba siempre, y
    eso inflaba porcentajes, promedios y fotos de existencia:

    * "suma": SUM(valor).
    * "promedio_ponderado": SUM(valor * peso) / SUM(peso), tanto por grupo
      como en el total -- el total NO es la suma ni el promedio simple de los
      grupos. Las filas sin peso (escritas antes de que existiera la columna)
      se ignoran: no hay forma correcta de combinarlas.
    * "ultimo": la foto del ultimo dia del rango que tenga datos. Por periodo
      se muestra la foto de cada dia, y el total es la del ultimo.
    """
    condiciones = [
        KpiSnapshot.id_kpi_definition == id_kpi_definition,
        KpiSnapshot.periodo >= fecha_inicio,
        KpiSnapshot.periodo <= fecha_fin,
    ]
    if actor_project is not None:
        condiciones.append(cast(KpiSnapshot.dimension_key, JSONB).contains({'id_proyect': actor_project}))

    entidad_expr = _dimension_entity_expr(campo_json) if campo_json else None
    # `is not None`, no truthy: una lista vacia (departamento sin empleados,
    # ver `_empleados_de_departamentos`) tiene que filtrar a "nadie", no
    # saltarse el filtro por completo. SQLAlchemy compila `IN (())` como una
    # condicion siempre falsa, asi que es seguro.
    if entidad_expr is not None and entidades is not None:
        condiciones.append(entidad_expr.in_([str(entidad) for entidad in entidades]))

    base = {'inicio': fecha_inicio.isoformat(), 'fin': fecha_fin.isoformat()}

    if agregacion == 'ultimo':
        ultimo = db.execute(select(func.max(KpiSnapshot.periodo)).where(*condiciones)).scalar()
        if ultimo is None:
            return {**base, 'total': 0.0, 'por_empleado': {}, 'por_periodo': {}}
        if agrupar_por_periodo:
            filas = db.execute(
                select(KpiSnapshot.periodo, func.sum(KpiSnapshot.valor))
                .where(*condiciones)
                .group_by(KpiSnapshot.periodo)
                .order_by(KpiSnapshot.periodo)
            ).all()
            por_periodo = {periodo.isoformat(): float(valor) for periodo, valor in filas}
            return {**base, 'total': por_periodo[ultimo.isoformat()], 'por_empleado': {}, 'por_periodo': por_periodo}
        # Acotado a un solo dia, sumar entre entidades y proyectos ya es
        # correcto: es la existencia total de esa foto.
        condiciones.append(KpiSnapshot.periodo == ultimo)

    ponderado = agregacion == 'promedio_ponderado'
    if ponderado:
        condiciones.extend([KpiSnapshot.peso.isnot(None), KpiSnapshot.peso > 0])
        columnas = (func.sum(KpiSnapshot.valor * KpiSnapshot.peso), func.sum(KpiSnapshot.peso))
    else:
        columnas = (func.sum(KpiSnapshot.valor),)

    def valor_de(numerador, denominador=None):
        if not ponderado:
            return float(numerador or 0)
        return float(numerador) / float(denominador) if denominador else 0.0

    def total_de(agregados):
        # `agregados`: lista de (numerador,) o (numerador, denominador) por
        # grupo. Ponderado: se recombinan numeradores y denominadores, nunca
        # los valores ya divididos.
        if not ponderado:
            return float(sum(numerador or 0 for numerador, in agregados))
        numerador = sum(n or 0 for n, _ in agregados)
        denominador = sum(d or 0 for _, d in agregados)
        return float(numerador) / float(denominador) if denominador else 0.0

    if agrupar_por_periodo:
        filas = db.execute(
            select(KpiSnapshot.periodo, *columnas)
            .where(*condiciones)
            .group_by(KpiSnapshot.periodo)
            .order_by(KpiSnapshot.periodo)
        ).all()
        por_periodo = {periodo.isoformat(): valor_de(*agregados) for periodo, *agregados in filas}
        total = total_de([tuple(agregados) for _, *agregados in filas])
        return {**base, 'total': total, 'por_empleado': {}, 'por_periodo': por_periodo}

    if entidad_expr is None:
        fila = db.execute(select(*columnas).where(*condiciones)).one()
        return {**base, 'total': valor_de(*fila), 'por_empleado': {}, 'por_periodo': {}}

    filas = [
        (entidad, *agregados)
        for entidad, *agregados in db.execute(
            select(entidad_expr, *columnas)
            .where(*condiciones)
            .group_by(entidad_expr)
        ).all()
        if entidad is not None
    ]
    por_entidad = {entidad: valor_de(*agregados) for entidad, *agregados in filas}
    total = total_de([tuple(agregados) for _, *agregados in filas])
    return {**base, 'total': total, 'por_empleado': por_entidad, 'por_periodo': {}}


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
            if has_kpi_permission(db, user_data, kpi.id_kpi_definition)
        ]
    return jsonify({'items': items})


@bp_kpi.route('/kpi_definition/all', methods=['GET'])
@token_required
@require_entity_permission('nm_permission_kpi', 'read')
def list_all_kpi_definitions(user_data):
    """Catalogo completo de KPIs, sin filtrar por `has_kpi_permission`.

    Distinto de `list_kpi_definitions` (`/kpi_definition/`, usado por el
    propio dashboard: cada quien ve solo lo que tiene permitido). Este es
    para poblar el selector de la pantalla que administra
    `nm_permission_kpi` -- quien reparte permisos necesita ver los 16 KPIs
    completos para poder asignarlos, no solo los que ya tiene concedidos a
    si mismo. Protegido con el permiso de administrar `nm_permission_kpi`,
    no con el de `kpi_definition`.
    """
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
    # "empleados" sigue siendo el nombre que manda el frontend hoy para
    # cualquier KPI por empleado; "entidades" es el nombre nuevo,
    # dimension-agnostico (para KPIs por producto). Si llega el primero se
    # usa ese; si no, se acepta el segundo.
    entidades = empleados if empleados is not None else _optional_entidades(request.args.get('entidades'))
    agrupar_por = request.args.get('agrupar_por') or 'entidad'
    if agrupar_por not in ('entidad', 'periodo'):
        raise AppError('errors.invalid_field', 400, {'field': 'agrupar_por'})

    # Salvo que el plan del cliente declare otro valor, un rango no puede
    # pedir mas de un anio de una sola vez (ver el comentario junto a
    # KPI_RANGO_DIAS_MAX_POR_OMISION).
    dias_maximo = limite('kpi_rango_dias_max', KPI_RANGO_DIAS_MAX_POR_OMISION)
    _validar_rango(fecha_inicio, fecha_fin, dias_maximo, 'fecha_fin')
    if fecha_inicio_b and fecha_fin_b:
        _validar_rango(fecha_inicio_b, fecha_fin_b, dias_maximo, 'fecha_fin_b')

    with transaction_context() as db:
        if not has_kpi_permission(db, user_data, id_kpi_definition):
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
        dimension = DIMENSION_POR_CLAVE.get(kpi_row.clave, 'empleado') if kpi_row else 'empleado'
        campo_json = DIMENSION_JSON_KEY.get(dimension, 'id_user')
        # Sin regla no se combina nada: una fila de kpi_definition que ya no
        # esta en KPI_REGISTRY no tiene quien la calcule, y sumarla "por si
        # acaso" es exactamente el error que motivo `agregacion`.
        agregacion = AGREGACION_POR_CLAVE.get(kpi_row.clave) if kpi_row else None
        if agregacion is None:
            raise AppError('errors.resource_not_found', 404, {'kpi': id_kpi_definition})

        # id_departments se resuelve a id_user (via Permission.id_department)
        # y se combina con "entidades": si vienen los dos, interseccion; si
        # solo viene el departamento, esa lista completa hace de filtro de
        # empleados. Una lista vacia (departamento sin nadie) filtra a
        # "nadie" -- ver el comentario en `_totales`. Solo aplica a KPIs por
        # empleado -- un producto no tiene departamento.
        if id_departments and dimension == 'empleado':
            usuarios_del_departamento = _empleados_de_departamentos(db, id_departments)
            if entidades is not None:
                entidades = [id_empleado for id_empleado in entidades if id_empleado in usuarios_del_departamento]
            else:
                entidades = list(usuarios_del_departamento)

        agrupar_por_periodo = agrupar_por == 'periodo'
        rango_a = _totales(db, id_kpi_definition, fecha_inicio, fecha_fin, actor_project, entidades, campo_json, agregacion, agrupar_por_periodo)
        rango_b = None
        if fecha_inicio_b and fecha_fin_b:
            rango_b = _totales(db, id_kpi_definition, fecha_inicio_b, fecha_fin_b, actor_project, entidades, campo_json, agregacion, agrupar_por_periodo)

    return jsonify({'rango_a': rango_a, 'rango_b': rango_b})


# Igual que KPI_RANGO_DIAS_MAX_POR_OMISION arriba, pero para el tamano de
# pagina de un KPI "vivo" -- sin tope, una pagina sin fin es una tabla
# completa escaneada por peticion (ver material_prestado_actual_query).
KPI_VIVO_LIMIT_MAX_POR_OMISION = 100
KPI_VIVO_LIMIT_POR_OMISION = 25


@bp_kpi.route('/kpi_definition/<int:id_kpi_definition>/vivo', methods=['GET'])
@token_required
@require_entity_permission('kpi_definition', 'read')
def query_kpi_vivo(user_data, id_kpi_definition):
    """Datos de un KPI "vivo" (`KpiDefinition.modo == "vivo"`, ver el registry).

    Distinto de `query_kpi_snapshot`: no hay rango de fechas (siempre es
    "ahora") ni combinacion de `kpi_snapshot` -- se llama al `query_builder`
    del KPI directo, con limit/offset, cada vez que se pide. Mismos dos
    chequeos que el resto de los KPIs (`has_kpi_permission`, que ya cubre
    tanto el permiso del rol como el plan/modulo del cliente -- ver su propio
    docstring en app/utils/auth.py) para que un KPI "vivo" no sea una
    puerta trasera que se salte esas dos capas.
    """
    limit_maximo = limite('kpi_vivo_limit_max', KPI_VIVO_LIMIT_MAX_POR_OMISION)
    limit = min(_required_int(request.args.get('limit', KPI_VIVO_LIMIT_POR_OMISION), 'limit'), limit_maximo)
    if limit < 1:
        raise AppError('errors.invalid_field', 400, {'field': 'limit'})
    offset = _required_int(request.args.get('offset', 0), 'offset')
    if offset < 0:
        raise AppError('errors.invalid_field', 400, {'field': 'offset'})

    with transaction_context() as db:
        if not has_kpi_permission(db, user_data, id_kpi_definition):
            raise AppError('errors.permission_denied', 403, {'kpi': id_kpi_definition})

        kpi_row = db.get(KpiDefinition, id_kpi_definition)
        kpi_def = KPI_POR_CLAVE.get(kpi_row.clave) if kpi_row else None
        if kpi_def is None or kpi_def.modo != 'vivo':
            raise AppError('errors.resource_not_found', 404, {'kpi': id_kpi_definition})

        actor_project = InvoiceService.actor_project(user_data) if kpi_def.alcance_proyecto else None
        items, total = kpi_def.query_builder(db, limit=limit, offset=offset, actor_project=actor_project)

    return jsonify({'items': items, 'total': total, 'limit': limit, 'offset': offset})


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
