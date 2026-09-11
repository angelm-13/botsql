from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_

from app.models.entity_permission import EntityPermission
from app.models.permission import Permission
from app.models.proyect import Proyect
from app.models.proyect_event import ProyectEvent
from app.models.proyect_payment import ProyectPayment
from app.models.session import transaction_context
from app.models.task import Task
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
    "draft": {"submitted"},
    "submitted": {"authorized", "denied", "blocked"},
    "blocked": {"submitted", "authorized", "denied"},
    "authorized": {"in_progress"},
    "in_progress": {"waiting_material", "stopped", "completed"},
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
    "id_customer_supplier", "leader", "proyect_description", "title",
    # Los de la orden de trabajo. El estado NO esta aqui: se mueve por
    # `transition`, que valida la transicion y deja constancia en `proyect_event`.
    "folio", "requested_by", "id_quotation", "purchase_order",
    "purchase_order_item", "id_supervisor", "delivery_date",
    "id_drawing_document",
}

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


def transition_management(project_id, payload: dict, user_data: dict) -> dict:
    """Mueve el proyecto por el recorrido de GERENCIA, no por el de taller.

    Son dos vidas del mismo proyecto y avanzan por separado: uno entregado
    puede seguir sin cobrar. Por eso hay dos rutas y no una con un parametro.
    """
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
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
    return bool(record and int(record.control_type) & 2)


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
        payload["incidents"] = [i.serialize() for i in incidencias]
        payload["appointments"] = [c.serialize() for c in citas]
        payload["payments"] = [p.serialize() for p in pagos]
        payload["payment_summary"] = _resumen_de_pagos(pagos)
        return payload


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


def create_project(payload: dict, user_data: dict) -> dict:
    actor_id = _actor_id(user_data)
    values = {key: value for key, value in (payload or {}).items() if key in PROJECT_MUTABLE_FIELDS}
    for field in ("id_customer_supplier", "proyect_description"):
        if values.get(field) in (None, ""):
            raise AppError("errors.required_field", 400, {"field": field})
    values["created_by"] = actor_id
    values["leader"] = _safe_int(values.get("leader")) or actor_id
    values["proyect_status"] = "draft"
    with transaction_context() as db:
        project = Proyect(**values)
        db.add(project)
        db.flush()
        _append_event(db, project, user_data, "created", new_status="draft")
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

        # Quien envia a revision: el que lo creo o su lider.
        puede_enviar = scope in {"ownership", "unrestricted"} or leads_it
        # Quien autoriza, deniega o bloquea: solo la capacidad de autorizacion.
        # El lider NO entra aqui a proposito: quien ejecuta el trabajo no debe
        # aprobarlo. Es la separacion que evita que una sola persona levante,
        # apruebe y cierre su propio proyecto.
        puede_autorizar = scope in {"authorization", "unrestricted"}
        # Quien lo ejecuta: el taller, o el lider sobre el proyecto que lidera.
        puede_ejecutar = scope in {"execution", "unrestricted"} or leads_it

        allowed_scope = (
            (current in {"draft", "blocked"} and validated_target == "submitted" and puede_enviar)
            or (validated_target in {"authorized", "denied", "blocked"} and puede_autorizar)
            or (validated_target in {"in_progress", "stopped", "completed"} and puede_ejecutar)
        )
        if not allowed_scope:
            raise AppError(
                "errors.permission_denied",
                403,
                {"target_status": validated_target, "scope": scope, "is_leader": leads_it},
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
    """
    carga = payload or {}
    with transaction_context() as db:
        project = _get_visible_project(db, project_id, user_data, for_update=True)
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
        pago.deletion_date = datetime.now()
        db.flush()
        return {"id_proyect_payment": pago.id_proyect_payment}
