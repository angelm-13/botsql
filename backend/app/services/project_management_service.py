from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import case, func, or_, select

from app.models.entity_permission import EntityPermission
from app.models.permission import Permission
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.proyect_payment import ProyectPayment
from app.models.session import transaction_context
from app.models.task import Task
from app.services.operations_workflow import TASK_CLOSED_STATUSES
from app.utils.errors import AppError


# El recorrido del TALLER. Los dos ultimos se agregaron con la orden de trabajo
# (migracion 20260911180000): faltaban "en espera de material" y "entregado",
# que el taller si distingue.
#
# `waiting_material` NO es lo mismo que `stopped`: parado es que alguien lo
# detuvo y hay que explicar por que; en espera de material es que el trabajo
# esta bien y falta que llegue algo. Mezclarlos haria que la unica lista de
# "por que no avanza esto" tuviera un motivo escrito a mano en cada renglon.
PROJECT_STATUSES = (
    "draft",
    "submitted",
    "authorized",
    "denied",
    "blocked",
    "in_progress",
    "waiting_material",
    "stopped",
    "completed",
    "delivered",
)

PROJECT_TRANSITIONS = {
    # Gerente mueve el proyecto directo desde Borrador -- al recibir la
    # orden de compra del cliente -- sin que Supervisor tenga que "enviarlo
    # a revision" primero. `submitted` se deja alcanzable por compatibilidad
    # con lo que ya se hubiera capturado antes de este cambio, pero ya nadie
    # tiene permiso para pedirlo (ver `transition_project`).
    "draft": {"submitted", "authorized", "denied", "blocked"},
    "submitted": {"authorized", "denied", "blocked"},
    "blocked": {"submitted", "authorized", "denied"},
    "authorized": {"in_progress"},
    # `blocked` tambien es destino valido desde aqui: Jefe de taller puede
    # bloquear un proyecto que ya esta en curso, no solo Gerente rechazandolo
    # antes de iniciar (desde `submitted`). Ver el candado de rol en
    # `transition_project`. Volver de un bloqueo en curso pasa por Gerente
    # (blocked -> authorized -> in_progress), a proposito: quien bloquea no
    # se autoriza solo de vuelta.
    "in_progress": {"waiting_material", "stopped", "completed", "blocked"},
    # De la espera se vuelve al trabajo: el material llego. No se salta a
    # terminado porque lo que faltaba era justo para poder terminarlo.
    "waiting_material": {"in_progress", "stopped"},
    "stopped": {"in_progress"},
    # Terminado es que el taller acabo; entregado, que salio hacia el cliente.
    # Son dos hechos con dias de diferencia y alguien pregunta por los dos.
    "completed": {"delivered"},
    "denied": set(),
    "delivered": set(),
}

REASON_REQUIRED_TARGETS = {"denied", "blocked", "stopped"}
# Estatus en los que el proyecto ya no admite trabajo nuevo.
#
# Se DERIVABA de `PROJECT_TRANSITIONS` -- "los que no tienen salida" -- y
# funcionaba mientras terminar fuera el final. Dejo de funcionar al agregar
# `delivered`: `completed` paso a tener salida y, con la regla vieja, un
# proyecto terminado volvia a aceptar tareas nuevas. Lo detecto
# `test_no_new_task_in_a_closed_project`.
#
# La leccion es que eran dos cosas distintas que coincidian: "no avanza mas" y
# "no acepta mas trabajo". Un proyecto TERMINADO todavia avanza -- falta
# entregarlo -- pero el trabajo ya se hizo. Asi que se declara, y el aviso
# original sigue vigente: una sola lista, aqui, no una copia en `task_service`.
PROJECT_CLOSED_STATUSES = frozenset({"completed", "delivered", "denied"})
WORKSHOP_VISIBLE_STATUSES = {"authorized", "in_progress", "waiting_material",
                             "stopped", "completed", "delivered"}
PROJECT_MUTABLE_FIELDS = {
    "id_customer_supplier", "id_customer_contact", "proyect_description", "title",
    # Los de la orden de trabajo. El estado NO esta aqui: se mueve por
    # `transition`, que valida la transicion y deja constancia en `proyect_event`.
    #
    # `leader` (responsable) tampoco esta aqui a proposito: siempre es quien
    # crea el proyecto, sin excepcion de rol ni siquiera al editar despues
    # (decision de negocio). `id_supervisor` se quito del formulario -- es el
    # mismo concepto que `leader` -- y la columna se deja inerte en la base,
    # sin migracion de borrado.
    #
    # `id_quotation`/`quotation_reference` tampoco estan aqui a proposito: el
    # formulario manda un solo valor crudo bajo `id_quotation` y
    # `_resolver_cotizacion` decide a cual de las dos columnas va -- dejarlas
    # en este set permitiria que alguien mandara `quotation_reference`
    # directo, sin pasar por esa resolucion.
    "folio", "purchase_order",
    "purchase_order_item", "delivery_date",
    "id_drawing_document",
}

# Campos de `proyect` que existen en la tabla y que el formulario YA NO escribe.
# Se dejan documentados aqui porque su ausencia de `PROJECT_MUTABLE_FIELDS` es
# una decision, no un olvido:
#
#   * `leader`    -- el responsable es SIEMPRE quien crea el proyecto. Elegirlo
#                    de una lista permitia levantar un proyecto a nombre de otra
#                    persona, y el responsable dejaba de ser quien respondia.
#   * `id_supervisor` -- ya no se ASIGNA: el supervisor TOMA el proyecto
#                    (`take_project`). Asignarlo desde el formulario hacia que
#                    quien captura repartiera el trabajo del taller.

# El recorrido COMERCIAL, que corre en paralelo al de taller: un proyecto puede
# estar entregado y sin cobrar.
MANAGEMENT_STATUSES = (
    "pendiente_orden_compra",
    "autorizado",
    "cancelado",
    "cobrado",
)

MANAGEMENT_TRANSITIONS = {
    "pendiente_orden_compra": {"autorizado", "cancelado"},
    "autorizado": {"cobrado", "cancelado"},
    "cobrado": set(),
    "cancelado": set(),
}


def normalize_project_status(value) -> str:
    status = str(value or "").strip().lower()
    return {"active": "draft", "activo": "draft", "borrador": "draft"}.get(status, status)


def validate_project_transition(current_status, target_status, reason=None) -> str:
    current = normalize_project_status(current_status)
    target = normalize_project_status(target_status)
    if current not in PROJECT_TRANSITIONS or target not in PROJECT_TRANSITIONS[current]:
        raise AppError(
            "errors.project_invalid_transition",
            409,
            {"current_status": current, "target_status": target},
        )
    if target in REASON_REQUIRED_TARGETS and not str(reason or "").strip():
        raise AppError(
            "errors.project_transition_reason_required",
            400,
            {"target_status": target, "field": "reason"},
        )
    return target


def validate_management_transition(current_status, target_status) -> str:
    """La misma disciplina que el recorrido de taller, para el comercial.

    Sin motivo obligatorio: cancelar un proyecto por gerencia ya se explica en
    el mensaje del evento, y exigir dos textos para el mismo hecho hace que uno
    de los dos se rellene con un punto.
    """
    actual = str(current_status or "").strip().lower() or "pendiente_orden_compra"
    destino = str(target_status or "").strip().lower()
    if actual not in MANAGEMENT_TRANSITIONS or destino not in MANAGEMENT_TRANSITIONS[actual]:
        raise AppError(
            "errors.project_invalid_management_transition",
            409,
            {"current_status": actual, "target_status": destino},
        )
    return destino


def _require_management_scope(db, user_data: dict) -> None:
    """Candado de rol compartido por todo el recorrido de GERENCIA.

    Exclusivo de quien autoriza (Gerente) o de un actor sin restriccion. Vive
    aqui -no en la ruta- para que ninguna operacion comercial (el recorrido
    en si o las parcialidades que cuelgan de el) se quede sin el candado por
    accidente, como paso antes con `transition_management`.
    """
    scope = _scope_name(db, user_data)
    if scope not in {"authorization", "unrestricted"}:
        raise AppError("errors.permission_denied", 403, {"scope": scope})


def transition_management(project_id, payload: dict, user_data: dict) -> dict:
    """Mueve el proyecto por el recorrido de GERENCIA, no por el de taller.

    Son dos vidas del mismo proyecto y avanzan por separado: uno entregado
    puede seguir sin cobrar. Por eso hay dos rutas y no una con un parametro.
    """
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        _require_management_scope(db, user_data)
        destino = validate_management_transition(
            project.management_status, (payload or {}).get("management_status"))
        anterior = project.management_status
        project.management_status = destino
        # Queda en la MISMA bitacora que el recorrido de taller: quien mira la
        # historia de un proyecto quiere los dos hilos en orden, no dos listas.
        _append_event(db, project, user_data, "management_transition",
                      new_status=destino, previous_status=anterior,
                      reason=(payload or {}).get("reason"))
        db.flush()
        return _project_payload(project)


def project_options(*, id_leader: int | None = None) -> list[dict]:
    """Solo id+folio+titulo, para selectores como "Obra" en un vale de almacen.

    Sin permiso de entidad de por medio, igual que `UserService.options()`: un
    Almacenista puede levantar un vale y ligarlo a una obra sin tener acceso al
    modulo de Operaciones completo -- solo necesita saber CUALES obras existen,
    no su cotizacion, su orden de compra ni su historial. Sin esto, el selector
    de proyecto en el vale seria un 403 para el rol que mas lo usa: el propio
    Almacenista no tiene el modulo `operaciones`.

    `id_leader` es OPCIONAL y lo pide quien llama, no un alcance que este
    modulo adivine: el Supervisor de un prevale solo debe ver SUS proyectos
    -es el unico que pide material, y el responsable del vale ya es el mismo
    actor-, pero el Almacenista que autoriza necesita la lista completa para
    reconocer cualquier obra que le mencionen. No es el filtrado de Fase 2
    (Propios/Mis grupos/Todos) que sigue pendiente en el resto del sistema;
    es un filtro puntual de este selector, pedido por quien lo consume.
    """
    with transaction_context() as db:
        consulta = db.query(Proyect.id_proyect, Proyect.folio, Proyect.title,
                            Proyect.proyect_description)
        if id_leader is not None:
            consulta = consulta.filter(Proyect.leader == id_leader)
        filas = (
            consulta.filter(Proyect.deletion_date.is_(None))
            .order_by(Proyect.id_proyect.desc())
            .all()
        )
        return [
            {"id_proyect": f[0], "folio": f[1], "title": f[2], "description": f[3]}
            for f in filas
        ]


def project_catalog() -> dict:
    """Las maquinas de estados de proyecto, tal como las valida el servidor.

    La pantalla de proyectos llevaba su propia copia de PROJECT_TRANSITIONS en
    JavaScript. Dos copias de una maquina de estados divergen: la interfaz
    ofrecia un cambio que el servidor rechazaba, o escondia uno que si era
    valido. Se sirve la del servidor y se acaba la copia.
    """
    return {
        "statuses": list(PROJECT_STATUSES),
        "transitions": {key: sorted(value) for key, value in PROJECT_TRANSITIONS.items()},
        "reason_required": sorted(REASON_REQUIRED_TARGETS),
        "closed_statuses": sorted(PROJECT_CLOSED_STATUSES),
        # El recorrido comercial viaja por el mismo sitio y por el mismo motivo:
        # si la pantalla se escribiera su propia copia, ofreceria transiciones
        # que el servidor rechaza.
        "management_statuses": list(MANAGEMENT_STATUSES),
        "management_transitions": {
            key: sorted(value) for key, value in MANAGEMENT_TRANSITIONS.items()
        },
    }


def _safe_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _actor_id(user_data: dict) -> int:
    actor_id = _safe_int(user_data.get("id_user") or user_data.get("user_id"))
    if not actor_id:
        raise AppError("errors.auth_required", 401)
    return actor_id


def _is_unrestricted(user_data: dict) -> bool:
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))


def _permission_id(user_data: dict) -> int | None:
    return _safe_int(user_data.get("id_permission") or user_data.get("permission_id"))


def _has_capability(db, user_data: dict, capability: str) -> bool:
    if _is_unrestricted(user_data):
        return True
    permission_id = _permission_id(user_data)
    if not permission_id:
        return False
    record = (
        db.query(EntityPermission)
        .filter(EntityPermission.id_permission == permission_id)
        .filter(EntityPermission.entity_name == capability)
        .filter(EntityPermission.deletion_date.is_(None))
        .first()
    )
    return bool(record and int(record.scope_read) != 0)


def _actor_role(db, user_data: dict) -> str | None:
    permission_id = _permission_id(user_data)
    permission = db.get(Permission, permission_id) if permission_id else None
    return permission.permission_description if permission else None


def _scope_name(db, user_data: dict) -> str:
    if _is_unrestricted(user_data):
        return "unrestricted"
    if _has_capability(db, user_data, "project_authorization"):
        return "authorization"
    if _has_capability(db, user_data, "project_execution"):
        return "execution"
    return "ownership"


def is_project_leader(project, user_data: dict) -> bool:
    """El lider designado del proyecto.

    Se distingue de quien lo creo: un supervisor puede levantar el proyecto y
    asignarlo a otra persona, y esa persona es la responsable de sacarlo.
    """
    leader = _safe_int(getattr(project, "leader", None))
    return leader is not None and leader == _safe_int(user_data.get("id_user") or user_data.get("user_id"))


def _scoped_query(db, user_data: dict):
    query = db.query(Proyect).filter(Proyect.deletion_date.is_(None))
    scope = _scope_name(db, user_data)
    actor_id = _actor_id(user_data)
    if scope == "ownership":
        # El lider ve su proyecto aunque no lo haya creado. Sin esto, un
        # proyecto asignado a alguien mas quedaba invisible para su propio
        # responsable, que no podia ni consultarlo.
        query = query.filter(or_(Proyect.created_by == actor_id, Proyect.leader == actor_id))
    elif scope == "execution":
        query = query.filter(
            or_(
                Proyect.proyect_status.in_(WORKSHOP_VISIBLE_STATUSES),
                Proyect.leader == actor_id,
            )
        )
    elif scope == "authorization":
        # Quien autoriza ve todo, y ademas lo que lidera.
        return query
    return query


def _project_payload(project: Proyect, events=None) -> dict:
    payload = project.serialize()
    # Solo se INVENTA un folio cuando el proyecto no trae el suyo. Antes se
    # sobreescribia siempre: un proyecto capturado con folio "OT-2026-0042" -el
    # de la orden de trabajo, migracion 20260911180000- se veia como
    # "PRJ-000006" en cuanto alguien abria su detalle, porque esta funcion lo
    # pisaba sin mirar si ya tenia uno. El folio de PRJ- sigue existiendo para
    # los proyectos viejos que nunca tuvieron folio propio.
    if not payload.get("folio"):
        payload["folio"] = f"PRJ-{project.id_proyect:06d}"
    submitted_event = next(
        (event for event in (events or []) if event.event_type == "status_changed" and event.new_status == "submitted"),
        None,
    )
    payload["submitted_date"] = submitted_event.creation_date.isoformat() if submitted_event else None
    return payload


def _get_visible_project(db, project_id, user_data: dict, *, for_update=False) -> Proyect:
    query = _scoped_query(db, user_data).filter(Proyect.id_proyect == project_id)
    if for_update:
        query = query.with_for_update()
    project = query.first()
    if not project:
        raise AppError("errors.resource_not_found", 404)
    return project


def visible_project_ids(user_data: dict) -> list[int] | None:
    with transaction_context() as db:
        if _scope_name(db, user_data) in {"unrestricted", "authorization"}:
            return None
        return [row[0] for row in _scoped_query(db, user_data).with_entities(Proyect.id_proyect).all()]


def require_project_access(project_id, user_data: dict) -> None:
    with transaction_context() as db:
        _get_visible_project(db, project_id, user_data)


def require_task_access(task_id, user_data: dict) -> None:
    with transaction_context() as db:
        task = db.get(Task, task_id)
        if not task or task.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        _get_visible_project(db, task.id_proyect, user_data)


def _parse_review_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": "review_date"}) from exc


def _parse_filter_date(value, field):
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=None)
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _append_event(
    db,
    project: Proyect,
    user_data: dict,
    event_type: str,
    *,
    task: Task | None = None,
    previous_status=None,
    new_status=None,
    content=None,
    reason=None,
    review_date=None,
) -> ProyectEvent:
    """Anota un hecho en el expediente del proyecto.

    `task` cuelga el evento de una tarea concreta. La columna
    `proyect_event.id_task` existe desde el principio, con indice, y nadie la
    escribia: el historial solo contaba lo que le pasaba al proyecto, asi que
    una tarea bloqueada o cancelada no aparecia en ningun sitio y el motivo se
    perdia. Ahora el expediente cuenta las dos cosas en una sola linea de
    tiempo, que es donde se busca "por que se paro esto".
    """
    event = ProyectEvent(
        id_proyect=project.id_proyect,
        id_task=task.id_task if task is not None else None,
        created_by=_actor_id(user_data),
        author_role=_actor_role(db, user_data),
        event_type=event_type,
        previous_status=previous_status,
        new_status=new_status,
        content=str(content).strip() if content else None,
        reason=str(reason).strip() if reason else None,
        review_date=_parse_review_date(review_date),
    )
    db.add(event)
    return event


def list_projects(user_data: dict, *, page=1, per_page=20, filters=None, sort=None) -> dict:
    page = max(_safe_int(page) or 1, 1)
    per_page = min(max(_safe_int(per_page) or 20, 1), 100)
    filters = filters or {}
    with transaction_context() as db:
        query = _scoped_query(db, user_data)
        status = normalize_project_status(filters.get("proyect_status"))
        if status:
            if status not in PROJECT_STATUSES:
                raise AppError("errors.invalid_field", 400, {"field": "proyect_status"})
            query = query.filter(Proyect.proyect_status == status)
        owner = _safe_int(filters.get("created_by"))
        if owner and _scope_name(db, user_data) in {"unrestricted", "authorization"}:
            query = query.filter(Proyect.created_by == owner)
        customer = _safe_int(filters.get("id_customer_supplier"))
        if customer:
            query = query.filter(Proyect.id_customer_supplier == customer)
        search = str(filters.get("search") or "").strip()
        if search:
            query = query.filter(or_(Proyect.title.ilike(f"%{search}%"), Proyect.proyect_description.ilike(f"%{search}%")))
        creation_date_from = _parse_filter_date(filters.get("creation_date_from"), "creation_date_from")
        creation_date_to = _parse_filter_date(filters.get("creation_date_to"), "creation_date_to")
        if creation_date_from:
            query = query.filter(Proyect.creation_date >= creation_date_from)
        if creation_date_to:
            query = query.filter(Proyect.creation_date < creation_date_to + timedelta(days=1))

        sort_columns = {
            "title": Proyect.title,
            "proyect_status": Proyect.proyect_status,
            "creation_date": Proyect.creation_date,
            "last_update_date": Proyect.last_update_date,
        }
        descending = str(sort or "").startswith("-")
        sort_column = sort_columns.get(str(sort or "").lstrip("-"), Proyect.creation_date)
        query = query.order_by(sort_column.desc() if descending else sort_column.asc(), Proyect.id_proyect.asc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        project_ids = [item.id_proyect for item in items]
        submitted_events = {}
        if project_ids:
            rows = (
                db.query(ProyectEvent)
                .filter(ProyectEvent.id_proyect.in_(project_ids))
                .filter(ProyectEvent.event_type == "status_changed")
                .filter(ProyectEvent.new_status == "submitted")
                .order_by(ProyectEvent.creation_date.asc(), ProyectEvent.id_proyect_event.asc())
                .all()
            )
            for event in rows:
                submitted_events.setdefault(event.id_proyect, event)
        payloads = [
            _project_payload(item, [submitted_events[item.id_proyect]] if item.id_proyect in submitted_events else [])
            for item in items
        ]
        return {"items": payloads, "page": page, "per_page": per_page, "total": total}


def get_project_detail(project_id, user_data: dict) -> dict:
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data)
        tasks = (
            db.query(Task)
            .filter(Task.id_proyect == project.id_proyect)
            .filter(Task.deletion_date.is_(None))
            .order_by(Task.creation_date.asc(), Task.id_task.asc())
            .all()
        )
        events = (
            db.query(ProyectEvent)
            .filter(ProyectEvent.id_proyect == project.id_proyect)
            .order_by(ProyectEvent.creation_date.asc(), ProyectEvent.id_proyect_event.asc())
            .all()
        )
        # Lo que cuelga del proyecto, en el mismo viaje. Las tres cosas se
        # preguntan juntas -- "como va este trabajo" -- y pedirlas en tres
        # llamadas dejaba la pantalla armando el expediente a mano.
        from app.models.appointment import Appointment
        from app.models.incident import Incident

        incidencias = (
            db.query(Incident)
            .filter(Incident.id_proyect == project.id_proyect)
            .filter(Incident.deletion_date.is_(None))
            .order_by(Incident.incident_date.desc().nullslast(),
                      Incident.id_incident.desc())
            .all()
        )
        citas = (
            db.query(Appointment)
            .filter(Appointment.id_proyect == project.id_proyect)
            .order_by(Appointment.starts_at.asc())
            .all()
        )
        pagos = (
            db.query(ProyectPayment)
            .filter(ProyectPayment.id_proyect == project.id_proyect)
            .filter(ProyectPayment.deletion_date.is_(None))
            .order_by(ProyectPayment.payment_date.asc(),
                      ProyectPayment.id_proyect_payment.asc())
            .all()
        )

        payload = _project_payload(project, events)
        payload["tasks"] = [task.serialize() for task in tasks]
        payload["events"] = [event.serialize() for event in events]
        payload["incidents"] = _vales_con_material(db, incidencias)
        payload["material_summary"] = _material_del_proyecto(db, project.id_proyect)
        payload["appointments"] = [c.serialize() for c in citas]
        payload["payments"] = [p.serialize() for p in pagos]
        payload["payment_summary"] = _resumen_de_pagos(pagos)
        return payload


def _vales_con_material(db, incidencias) -> list[dict]:
    """Los vales del proyecto, cada uno con cuanto se llevo y cuanto falta.

    Un vale sin esas dos cifras obliga a abrirlo para saber si todavia debe
    algo, y en una obra con veinte vales eso es abrir veinte pantallas.
    """
    from app.models.nm_incident_product import NmIncidentProduct

    if not incidencias:
        return []
    ids = [i.id_incident for i in incidencias]
    cuenta = dict(db.execute(
        select(NmIncidentProduct.id_incident, func.count())
        .where(NmIncidentProduct.id_incident.in_(ids),
               NmIncidentProduct.deletion_date.is_(None))
        .group_by(NmIncidentProduct.id_incident)
    ).all())
    abiertos = dict(db.execute(
        select(NmIncidentProduct.id_incident, func.count())
        .where(NmIncidentProduct.id_incident.in_(ids),
               NmIncidentProduct.close_date.is_(None),
               NmIncidentProduct.deletion_date.is_(None))
        .group_by(NmIncidentProduct.id_incident)
    ).all())
    salida = []
    for i in incidencias:
        fila = i.serialize()
        # El folio es el numero con el que la gente conoce el vale: el del
        # sistema anterior cuando lo trae, y el id cuando no.
        fila["folio"] = i.external_folio or str(i.id_incident)
        fila["total_lines"] = int(cuenta.get(i.id_incident, 0))
        fila["open_lines"] = int(abiertos.get(i.id_incident, 0))
        salida.append(fila)
    return salida


def _material_del_proyecto(db, id_proyect) -> dict:
    """Que se llevo esta obra y que sigue fuera, por producto.

    Se cuenta desde los RENGLONES del vale y no desde `inventory_ledger`, aunque
    el libro tambien tenga `id_proyect`: el del libro es el INQUILINO -- lo toma
    del actor -- y no la obra. Contarlo de ahi daria todo el almacen de la
    empresa como si fuera de este proyecto.
    """
    from app.models.incident import Incident
    from app.models.nm_incident_product import NmIncidentProduct
    from app.models.product import Product

    filas = db.execute(
        select(
            Product.id_product,
            Product.descripcion,
            Product.product_code,
            func.sum(NmIncidentProduct.quantity),
            func.sum(case((NmIncidentProduct.close_date.is_(None),
                           NmIncidentProduct.quantity), else_=0)),
        )
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .join(Product, Product.id_product == NmIncidentProduct.id_product)
        .where(Incident.id_proyect == id_proyect,
               Incident.deletion_date.is_(None),
               NmIncidentProduct.deletion_date.is_(None),
               NmIncidentProduct.direction == "salida")
        .group_by(Product.id_product, Product.descripcion, Product.product_code)
        .order_by(Product.descripcion)
    ).all()

    articulos = [
        {"id_product": f[0], "descripcion": f[1], "product_code": f[2],
         "taken": int(f[3] or 0), "still_out": int(f[4] or 0)}
        for f in filas
    ]
    return {
        "items": articulos,
        "products": len(articulos),
        "taken_total": sum(a["taken"] for a in articulos),
        "still_out_total": sum(a["still_out"] for a in articulos),
    }


def _resumen_de_pagos(pagos) -> dict:
    """Lo acordado, lo cobrado y lo que falta.

    Se cuenta aqui y no en la pantalla porque la misma cifra la quieren el
    detalle del proyecto y cualquier reporte de cobranza que venga despues, y
    dos sumas escritas en dos sitios acaban dando numeros distintos.
    """
    acordado = sum(Decimal(str(p.amount or 0)) for p in pagos)
    cobrado = sum(Decimal(str(p.amount or 0)) for p in pagos if p.paid_at)
    porcentaje = sum(Decimal(str(p.agreed_percent or 0)) for p in pagos)
    return {
        "agreed_total": float(acordado),
        "collected_total": float(cobrado),
        "pending_total": float(acordado - cobrado),
        # La suma de los porcentajes pactados. Se devuelve tal cual, sin
        # forzarla a 100: que no sumen es un dato -- falta acordar una
        # parcialidad -- y corregirlo aqui lo escondería.
        "agreed_percent_total": float(porcentaje),
        "installments": len(pagos),
        "collected_installments": sum(1 for p in pagos if p.paid_at),
    }


def _parsear_fecha_de_la_orden(values: dict) -> None:
    """`delivery_date` como objeto `date`, no como texto.

    SQLite -donde corre la suite- exige un `date` de verdad para una columna
    `Date` y revienta con un texto ISO; Postgres lo tolera por el driver, asi
    que el mismo codigo se veia bien contra la base real y fallaba solo en la
    suite. Se normaliza aqui, una vez, para las dos rutas que escriben el
    proyecto -crear y actualizar.
    """
    valor = values.get("delivery_date")
    if valor and isinstance(valor, str):
        try:
            values["delivery_date"] = date.fromisoformat(valor[:10])
        except ValueError as fallo:
            raise AppError("errors.invalid_field", 400,
                           {"field": "delivery_date"}) from fallo


def _resolver_cotizacion(db, valor_bruto) -> tuple:
    """Un solo campo de captura, dos destinos posibles.

    El formulario manda un solo valor bajo `id_quotation`. Si coincide con un
    `invoice` real de esta base, se liga ahi (FK protegida). Si no -- el
    folio de un sistema externo, como el de adser, que nunca genera una fila
    de invoice aqui y puede traer letras/guiones -- se guarda tal cual en
    `quotation_reference`, sin exigir que exista nada.
    """
    from app.models.invoice import Invoice

    if valor_bruto in (None, ""):
        return None, None
    texto = str(valor_bruto).strip()
    if texto.isdigit() and db.get(Invoice, int(texto)) is not None:
        return int(texto), None
    return None, texto[:80]


def _validar_referencias_de_la_orden(db, values: dict, id_proyecto_actual=None) -> None:
    """Que la cotizacion no este duplicada, y que el contacto y el dibujo existan de verdad.

    `id_customer_contact` e `id_drawing_document` son llaves ajenas normales
    -no diferidas, como las de `incident`-, asi que un id inventado revienta
    en el INSERT/UPDATE como un IntegrityError crudo y le llega al usuario
    como un 500 en vez del 404 que le toca. Se comprueba antes, igual que ya
    hace `crear_vale` con `id_proyect`.

    `id_quotation` ya llega resuelto por `_resolver_cotizacion` -- aqui solo
    se comprueba que, si es un `invoice` real, no este ya ligado a OTRO
    proyecto activo: dos proyectos con la misma cotizacion no se pueden
    distinguir al facturar.
    """
    from app.models.customer_contact import CustomerContact

    if values.get("id_quotation") is not None:
        conflicto = db.scalars(
            select(Proyect.id_proyect).where(
                Proyect.id_quotation == values["id_quotation"],
                Proyect.deletion_date.is_(None),
                Proyect.id_proyect != (id_proyecto_actual or -1),
            ).limit(1)
        ).first()
        if conflicto is not None:
            raise AppError("errors.quotation_already_linked", 409,
                           {"id_quotation": values["id_quotation"], "id_proyect": conflicto})
    if values.get("id_customer_contact"):
        contacto = db.get(CustomerContact, int(values["id_customer_contact"]))
        if contacto is None or contacto.deletion_date is not None:
            raise AppError("errors.not_found", 404,
                           {"entity": "customer_contact", "field": "id_customer_contact"})
        # El "Cliente" del proyecto se elige como contacto -"Empresa -
        # Persona"-, y de ahi salen la empresa y quien lo pidio. No son dos
        # capturas sueltas: si se cambia el contacto, cambian juntas.
        values["id_customer_supplier"] = contacto.id_customer_supplier
        values["requested_by"] = contacto.full_name
    if values.get("id_drawing_document"):
        from app.models.document import Document
        if db.get(Document, int(values["id_drawing_document"])) is None:
            raise AppError("errors.not_found", 404,
                           {"entity": "document", "field": "id_drawing_document"})


def create_project(payload: dict, user_data: dict) -> dict:
    """Levanta el proyecto a nombre de quien lo esta creando.

    **El responsable.** Es siempre el actor. Antes el formulario ofrecia la
    lista completa de usuarios y `leader` solo caia en el actor cuando venia
    vacio, asi que se podia levantar un proyecto a nombre de otra persona --
    y esa persona aparecia como responsable de algo que no sabia que existia.
    """
    actor_id = _actor_id(user_data)
    values = {key: value for key, value in (payload or {}).items() if key in PROJECT_MUTABLE_FIELDS}
    if values.get("id_customer_contact") in (None, "") and values.get("id_customer_supplier") in (None, ""):
        raise AppError("errors.required_field", 400, {"field": "id_customer_contact"})
    if values.get("proyect_description") in (None, ""):
        raise AppError("errors.required_field", 400, {"field": "proyect_description"})
    values["created_by"] = actor_id
    # El responsable es siempre quien crea el proyecto -- solo Supervisor (y
    # roles sin restriccion) pueden crear, y no hace falta que nadie elija a
    # otro responsable. Ignora cualquier `leader` que venga en el payload
    # (ya no llega: no esta en PROJECT_MUTABLE_FIELDS).
    values["leader"] = actor_id
    values["proyect_status"] = "draft"
    _parsear_fecha_de_la_orden(values)
    with transaction_context() as db:
        values["id_quotation"], values["quotation_reference"] = _resolver_cotizacion(
            db, (payload or {}).get("id_quotation"))
        _validar_referencias_de_la_orden(db, values)
        project = Proyect(**values)
        db.add(project)
        db.flush()
        _append_event(db, project, user_data, "created", new_status="draft")
        db.flush()
        return project.serialize()


def take_project(project_id, user_data: dict) -> dict:
    """El supervisor TOMA el proyecto; nadie se lo asigna.

    Antes `id_supervisor` era un desplegable del formulario, o sea que quien
    captura la orden repartia el trabajo del taller desde su escritorio. Se
    invierte: el proyecto sale sin supervisor y lo toma quien lo va a sacar.

    Quien puede tomarlo es quien tiene la capacidad `project_execution` -- hoy
    el rol Supervisor -- y no se comprueba por NOMBRE de rol: los roles se
    renombran y se crean desde el gestor, y un permiso amarrado a la cadena
    "Supervisor" deja de funcionar el dia que alguien escriba "Supervisor de
    obra". La capacidad es lo que el registro declara y lo que el gestor
    concede.

    Solo se toma lo que esta libre. Quitarle el proyecto a otro supervisor
    seria una reasignacion, y eso no es tomar: el que lo tiene lo suelta
    (`release_project`) o lo mueve la administracion.
    """
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        scope = _scope_name(db, user_data)
        if scope not in {"execution", "unrestricted"}:
            raise AppError("errors.permission_denied", 403,
                           {"action": "take_project", "scope": scope})
        actual = _safe_int(project.id_supervisor)
        actor_id = _actor_id(user_data)
        if actual is not None and actual != actor_id:
            raise AppError("errors.project_already_taken", 409,
                           {"id_supervisor": actual})
        project.id_supervisor = actor_id
        _append_event(db, project, user_data, "taken")
        db.flush()
        return project.serialize()


def release_project(project_id, user_data: dict) -> dict:
    """Soltarlo, para que otro lo tome.

    Existe porque tomar es irreversible sin esto: quien se equivoco de proyecto
    lo dejaria ocupado para siempre. Lo suelta el que lo tiene, o la
    administracion; nadie mas, porque entonces "tomar" no reservaria nada.
    """
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        actual = _safe_int(project.id_supervisor)
        if actual is None:
            return project.serialize()
        es_suyo = actual == _actor_id(user_data)
        if not es_suyo and _scope_name(db, user_data) != "unrestricted":
            raise AppError("errors.permission_denied", 403,
                           {"action": "release_project"})
        project.id_supervisor = None
        _append_event(db, project, user_data, "released")
        db.flush()
        return project.serialize()


def update_project(project_id, payload: dict, user_data: dict) -> dict:
    if "proyect_status" in (payload or {}):
        raise AppError("errors.project_status_requires_transition", 409)
    values = {key: value for key, value in (payload or {}).items() if key in PROJECT_MUTABLE_FIELDS}
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        scope = _scope_name(db, user_data)
        leads_it = is_project_leader(project, user_data)
        if scope == "execution" and not leads_it:
            raise AppError("errors.permission_denied", 403)
        if (scope == "ownership" or leads_it) and normalize_project_status(project.proyect_status) not in {"draft", "blocked"}:
            raise AppError("errors.project_not_editable", 409, {"status": project.proyect_status})
        _parsear_fecha_de_la_orden(values)
        if payload and "id_quotation" in payload:
            values["id_quotation"], values["quotation_reference"] = _resolver_cotizacion(
                db, payload.get("id_quotation"))
        _validar_referencias_de_la_orden(db, values, id_proyecto_actual=project.id_proyect)
        for field, value in values.items():
            setattr(project, field, value)
        db.flush()
        return project.serialize()


def delete_project(project_id, user_data: dict) -> dict:
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        scope = _scope_name(db, user_data)
        # Borrar queda con quien lo creo: el lider saca el proyecto adelante,
        # pero no lo elimina.
        if scope not in {"ownership", "unrestricted"} or (
            scope == "ownership" and _safe_int(project.created_by) != _actor_id(user_data)
        ):
            raise AppError("errors.permission_denied", 403)
        if normalize_project_status(project.proyect_status) != "draft":
            raise AppError("errors.project_not_editable", 409, {"status": project.proyect_status})
        project.deletion_date = datetime.utcnow()
        db.flush()
        return {"deleted": True, "id_proyect": project.id_proyect}


def transition_project(project_id, payload: dict, user_data: dict) -> dict:
    target = normalize_project_status((payload or {}).get("status"))
    reason = (payload or {}).get("reason")
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        current = normalize_project_status(project.proyect_status)
        validated_target = validate_project_transition(current, target, reason)
        scope = _scope_name(db, user_data)
        leads_it = is_project_leader(project, user_data)

        # Enviar a revision ya no lo pide nadie a proposito: Gerente mueve el
        # proyecto directo desde Borrador (al recibir la orden de compra), y
        # ni Supervisor ni el lider tienen esta puerta -- decision de negocio.
        # `submitted` se queda en PROJECT_TRANSITIONS por compatibilidad con
        # lo que ya se hubiera capturado antes, pero nadie puede pedirlo.
        #
        # Quien autoriza, deniega o bloquea: solo la capacidad de autorizacion.
        # El lider NO entra aqui a proposito: quien ejecuta el trabajo no debe
        # aprobarlo. Es la separacion que evita que una sola persona levante,
        # apruebe y cierre su propio proyecto.
        puede_autorizar = scope in {"authorization", "unrestricted"}
        # Quien lo ejecuta: el taller, o el lider sobre el proyecto que lidera.
        puede_ejecutar = scope in {"execution", "unrestricted"} or leads_it
        # Entregar al cliente es responsabilidad de quien lidera el proyecto
        # (normalmente Supervisor, quien lo crea), no del taller: "completado"
        # es que el trabajo esta hecho, "entregado" es un hecho comercial
        # aparte, con el cliente de por medio.
        puede_entregar = leads_it or scope == "unrestricted"

        allowed_scope = (
            (validated_target in {"authorized", "denied", "blocked"} and puede_autorizar)
            or (validated_target in {"in_progress", "stopped", "completed"} and puede_ejecutar)
            # Bloquear un proyecto que ya esta en curso tambien lo puede
            # pedir quien lo ejecuta (taller), no solo quien autoriza -- a
            # diferencia de bloquear ANTES de iniciar (desde `submitted`),
            # que sigue siendo exclusivo de `puede_autorizar` en la regla de
            # arriba.
            or (validated_target == "blocked" and current == "in_progress" and puede_ejecutar)
            or (validated_target == "delivered" and puede_entregar)
        )
        if not allowed_scope:
            raise AppError(
                "errors.permission_denied",
                403,
                {"target_status": validated_target, "scope": scope, "is_leader": leads_it},
            )

        if validated_target == "delivered":
            # No se entrega con tareas todavia abiertas -- "completado" es el
            # estatus del proyecto, no garantiza que cada tarea individual ya
            # se haya cerrado en el taller.
            tareas_abiertas = (
                db.query(Task)
                .filter(Task.id_proyect == project.id_proyect, Task.deletion_date.is_(None))
                # `NOT IN` con NULL nunca es verdadero en SQL -- una tarea sin
                # estatus capturado quedaria fuera del conteo, como si ya
                # estuviera cerrada, sin estarlo.
                .filter(or_(Task.task_status.is_(None), Task.task_status.notin_(TASK_CLOSED_STATUSES)))
                .count()
            )
            if tareas_abiertas:
                raise AppError(
                    "errors.project_open_tasks",
                    409,
                    {"open_tasks": tareas_abiertas},
                )

        project.proyect_status = validated_target
        _append_event(
            db,
            project,
            user_data,
            "status_changed",
            previous_status=current,
            new_status=validated_target,
            reason=reason,
            content=(payload or {}).get("content"),
            review_date=(payload or {}).get("review_date"),
        )
        db.flush()
        return project.serialize()


def add_project_message(project_id, payload: dict, user_data: dict) -> dict:
    content = str((payload or {}).get("content") or "").strip()
    if not content:
        raise AppError("errors.required_field", 400, {"field": "content"})
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data)
        event = _append_event(db, project, user_data, "message", content=content)
        db.flush()
        return event.serialize()


# --- adjuntos de requerimientos (PDF/DOCX) -------------------------------
#
# Tabla propia, `proyect_document`, y no el modulo /document generico: ese
# usa `user.id_proyect` del JWT -el tenant/instalacion del actor, la MISMA
# tabla `proyect` pero otro significado- y no el proyecto de taller que se
# esta editando en el formulario. Ver el comentario de la migracion
# 20260921100000.

def list_project_documents(project_id, user_data: dict) -> dict:
    from app.models.proyect_document import ProyectDocument

    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data)
        filas = (
            db.query(ProyectDocument)
            .filter(ProyectDocument.id_proyect == project.id_proyect)
            .filter(ProyectDocument.deletion_date.is_(None))
            .order_by(ProyectDocument.creation_date.desc())
            .all()
        )
        return {"items": [d.serialize_summary() for d in filas]}


def add_project_document(project_id, payload, raw, original_filename, user_data, storage) -> dict:
    from app.models.proyect_document import ProyectDocument
    import hashlib

    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        from app.services.document_service import PROJECT_ATTACHMENT_FILE_TYPES
        extension, mime_type = storage.validate(raw, original_filename, allowed_types=PROJECT_ATTACHMENT_FILE_TYPES)
        documento = ProyectDocument(
            id_proyect=project.id_proyect,
            title=(str((payload or {}).get("title") or "").strip() or None),
            original_filename=str(original_filename or "")[:255],
            extension=extension,
            mime_type=mime_type,
            file_size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            file_path="",
            created_by=_actor_id(user_data),
        )
        db.add(documento)
        db.flush()
        documento.file_path = storage.write(
            raw, project.id_proyect, documento.id_proyect_document, 1, extension,
            subfolder="proyecto_adjuntos",
        )
        db.flush()
        _append_event(db, project, user_data, "document_attached",
                      content=documento.original_filename)
        return documento.serialize_summary()


def delete_project_document(document_id, user_data: dict) -> dict:
    from app.models.proyect_document import ProyectDocument

    with transaction_context() as db:
        documento = db.get(ProyectDocument, int(document_id))
        if documento is None or documento.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "proyect_document"})
        project = _get_visible_project(db, documento.id_proyect, user_data, for_update=True)
        documento.deletion_date = datetime.utcnow()
        _append_event(db, project, user_data, "document_removed",
                      content=documento.original_filename)
        db.flush()
        return {"deleted": True, "id_proyect_document": documento.id_proyect_document}


def project_document_content(document_id, user_data: dict, storage):
    from app.models.proyect_document import ProyectDocument

    with transaction_context() as db:
        documento = db.get(ProyectDocument, int(document_id))
        if documento is None or documento.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "proyect_document"})
        _get_visible_project(db, documento.id_proyect, user_data)
        return storage.resolve(documento.file_path), documento.mime_type, documento.original_filename


# --- parcialidades de pago ----------------------------------------------

def _fecha(valor, campo):
    if valor in (None, ""):
        raise AppError("errors.required_field", 400, {"field": campo})
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError as fallo:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from fallo


def _monto(valor, campo, *, obligatorio=True):
    if valor in (None, ""):
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as fallo:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from fallo


def list_project_payments(project_id, user_data: dict) -> dict:
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data)
        filas = (
            db.query(ProyectPayment)
            .filter(ProyectPayment.id_proyect == project.id_proyect)
            .filter(ProyectPayment.deletion_date.is_(None))
            .order_by(ProyectPayment.payment_date.asc(),
                      ProyectPayment.id_proyect_payment.asc())
            .all()
        )
        return {"items": [p.serialize() for p in filas],
                "summary": _resumen_de_pagos(filas)}


def add_project_payment(project_id, payload: dict, user_data: dict) -> dict:
    """Acuerda una parcialidad: fecha, monto y el porcentaje pactado.

    El porcentaje es opcional porque no siempre se pacta asi -- a veces se
    acuerda una cifra redonda y no una fraccion --, pero cuando viene se guarda
    tal cual. Ver la cabecera del modelo para por que no se deduce del total.

    Exclusivo de Gerente, igual que `transition_management`: las
    parcialidades son parte del mismo recorrido comercial.
    """
    carga = payload or {}
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
        _require_management_scope(db, user_data)
        pago = ProyectPayment(
            id_proyect=project.id_proyect,
            payment_date=_fecha(carga.get("payment_date"), "payment_date"),
            amount=_monto(carga.get("amount"), "amount"),
            agreed_percent=_monto(carga.get("agreed_percent"), "agreed_percent",
                                  obligatorio=False),
            paid_at=(_fecha(carga.get("paid_at"), "paid_at")
                     if carga.get("paid_at") else None),
            notes=(str(carga.get("notes") or "").strip() or None),
            created_by=_actor_id(user_data),
        )
        if pago.amount <= 0:
            raise AppError("errors.invalid_field", 400, {"field": "amount"})
        db.add(pago)
        db.flush()
        _append_event(db, project, user_data, "payment_agreed",
                      content="%s el %s" % (pago.amount, pago.payment_date))
        return pago.serialize()


def settle_project_payment(payment_id, payload: dict, user_data: dict) -> dict:
    """Marca una parcialidad como cobrada, con la fecha en que entro de verdad.

    La fecha de cobro es aparte de la acordada a proposito: un pago que cae dos
    semanas tarde sigue siendo el pago de su fecha, y guardar una sola borraria
    el retraso, que es justo lo que alguien quiere ver.
    """
    with transaction_context() as db:
        pago = db.get(ProyectPayment, int(payment_id))
        if pago is None or pago.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "proyect_payment"})
        # Pasa por la misma comprobacion de alcance que el proyecto: quien no ve
        # el proyecto no cobra sus parcialidades.
        project = _get_visible_project(db, pago.id_proyect, user_data, for_update=True)
        _require_management_scope(db, user_data)

        carga = payload or {}
        if carga.get("paid_at") in (None, ""):
            # Desmarcar tambien es valido: alguien se adelanto al registrarlo.
            pago.paid_at = None
        else:
            pago.paid_at = _fecha(carga.get("paid_at"), "paid_at")
        if carga.get("notes") is not None:
            pago.notes = str(carga.get("notes") or "").strip() or None
        db.flush()
        _append_event(db, project, user_data, "payment_settled",
                      content="%s cobrado el %s" % (pago.amount, pago.paid_at)
                      if pago.paid_at else "%s sin cobrar" % pago.amount)
        return pago.serialize()


def delete_project_payment(payment_id, user_data: dict) -> dict:
    with transaction_context() as db:
        pago = db.get(ProyectPayment, int(payment_id))
        if pago is None or pago.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "proyect_payment"})
        _get_visible_project(db, pago.id_proyect, user_data, for_update=True)
        _require_management_scope(db, user_data)
        pago.deletion_date = datetime.now()
        db.flush()
        return {"id_proyect_payment": pago.id_proyect_payment}
