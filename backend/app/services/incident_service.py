"""Incidencias: catalogo de estatus, coherencia de fechas y cierre.

Antes era un CRUD sin reglas: aceptaba cualquier estatus, una incidencia
cerrada antes de haber ocurrido, y el estatus "cerrada" sin fecha de cierre.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_

from app.models import Incident, IncidentType, User
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.services.operations_workflow import (
    INCIDENT_CLOSED_STATUSES,
    INCIDENT_REASON_REQUIRED,
    INCIDENT_TRANSITIONS,
    normalize_incident_status,
    validate_transition,
)
from app.utils.errors import AppError
from app.utils.tiempo import ZONA_NEGOCIO, ahora_negocio


DEFAULT_STATUS = "abierta"

# Quien supervisa incidencias las ve todas. Sin esta capacidad, una persona
# solo alcanza las suyas: las que reporto, las que atiende y las que lidera.
# Antes cualquiera con permiso de lectura veia las de toda la empresa.
SUPERVISION_CAPABILITY = "incident_supervision"
READ_BIT = 2


def _is_unrestricted(user_data) -> bool:
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))


def _actor_id(user_data):
    try:
        return int(user_data.get("id_user") or user_data.get("user_id") or 0) or None
    except (TypeError, ValueError):
        return None


def supervises_incidents(db, user_data) -> bool:
    if _is_unrestricted(user_data):
        return True
    try:
        permission_id = int(user_data.get("id_permission") or user_data.get("permission_id") or 0)
    except (TypeError, ValueError):
        return False
    if not permission_id:
        return False
    record = (
        db.query(EntityPermission)
        .filter(EntityPermission.id_permission == permission_id)
        .filter(EntityPermission.entity_name == SUPERVISION_CAPABILITY)
        .filter(EntityPermission.deletion_date.is_(None))
        .first()
    )
    try:
        return bool(record and int(record.scope_read) != 0)
    except (TypeError, ValueError):
        return False


def _involves_actor(incident, user_data, gente=None) -> bool:
    """La incidencia es de quien la reporto, la atiende o la lidera.

    `gente` son las personas cubiertas (el actor y, con Mis grupos, su equipo).
    """
    actor = _actor_id(user_data)
    if actor is None:
        return False
    return bool({
        _safe(incident.id_user),
        _safe(incident.id_lider),
        _safe(incident.created_by),
    } & (set(gente) if gente else {actor}))


def _safe(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def scoped_incident_query(db, user_data):
    """Consulta acotada a lo que el actor tiene derecho a ver."""
    query = db.query(Incident).filter(Incident.deletion_date.is_(None))
    if supervises_incidents(db, user_data):
        return query
    actor = _actor_id(user_data)
    if actor is None:
        # Sin identidad no se devuelve nada, en lugar de devolverlo todo.
        return query.filter(Incident.id_incident.is_(None))
    from app.utils.scope import companeros

    gente = companeros(db, user_data, "incident") or {actor}
    return query.filter(or_(
        Incident.id_user.in_(gente),
        Incident.id_lider.in_(gente),
        Incident.created_by.in_(gente),
    ))


def require_incident_access(incident_id, user_data) -> Incident:
    with transaction_context() as db:
        incident = db.get(Incident, int(incident_id))
        if not incident or incident.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        from app.utils.scope import companeros

        if not supervises_incidents(db, user_data) and not _involves_actor(
                incident, user_data, companeros(db, user_data, "incident")):
            # Se responde "no existe" y no "no puedes": quien no participa
            # tampoco debe enterarse de que la incidencia existe.
            raise AppError("errors.resource_not_found", 404)
        db.expunge(incident)
        return incident


def _as_datetime(value, field):
    """La fecha como hora de pared del negocio, sin zona.

    `incident_date` y los cierres son fechas de negocio: se guardan en la hora
    local del cliente. Si el llamador manda una con zona -n8n con `-06:00`, un
    `...Z`- se convierte a esa hora; antes se le quitaba la zona sin convertir,
    y una hora en UTC quedaba guardada como si fuera local.
    """
    if value in (None, ""):
        return None
    try:
        fecha = value if isinstance(value, datetime) else datetime.fromisoformat(
            str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(ZONA_NEGOCIO)
    return fecha.replace(tzinfo=None)


def _now():
    # Contra esta hora se compara `incident_date` y con ella se completa un
    # cierre, y ambas son hora de pared del negocio: con la hora UTC, una
    # incidencia podia fecharse hasta 6 horas en el futuro sin rechazarse.
    return ahora_negocio()


class IncidentService(CrudService):
    model = Incident
    primary_key = 'id_incident'
    entity_name = 'incident'

    @classmethod
    def _validate(cls, payload: dict, *, current: Incident | None = None) -> dict:
        payload = dict(payload or {})

        if 'id_incident_type' in payload and payload['id_incident_type'] not in (None, ''):
            payload['id_incident_type'] = cls._existing_id(
                payload['id_incident_type'], IncidentType, 'id_incident_type'
            )
        for field in ('id_user', 'id_lider'):
            if field in payload and payload[field] not in (None, ''):
                payload[field] = cls._existing_id(payload[field], User, field)

        if 'incident_status' in payload:
            payload['incident_status'] = cls._resolve_status(payload, current)

        cls._validate_dates(payload, current)
        cls._validate_geo(payload)
        return payload

    @staticmethod
    def _validate_geo(payload):
        """Latitud, longitud y distancia: numeros dentro de su rango real.

        Llegan de n8n como texto o numero; un valor fuera de rango (latitud 200,
        distancia negativa) es un error del flujo que conviene rechazar aqui y
        no guardarlo para que el reporte lo muestre como si fuera cierto.
        """
        limites = {'latitude': (-90, 90), 'longitude': (-180, 180), 'distance_m': (0, None)}
        for campo, (minimo, maximo) in limites.items():
            valor = payload.get(campo)
            if valor in (None, ''):
                continue
            try:
                numero = Decimal(str(valor).strip())
            except InvalidOperation as exc:
                raise AppError("errors.invalid_field", 400, {"field": campo}) from exc
            if not numero.is_finite() or numero < minimo or (maximo is not None and numero > maximo):
                raise AppError("errors.invalid_field", 400, {"field": campo})

    @staticmethod
    def _existing_id(value, model, field):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": field}) from exc
        with transaction_context() as db:
            record = db.get(model, parsed)
            if not record or getattr(record, 'deletion_date', None) is not None:
                raise AppError(
                    f"validations.incident.{field}.invalid", 400, {"field": field}
                )
        return parsed

    @classmethod
    def _resolve_status(cls, payload, current):
        target = normalize_incident_status(payload.get('incident_status'))
        if not target:
            return DEFAULT_STATUS if current is None else current.incident_status

        if current is None:
            # Al crear no hay transicion: basta que el estatus exista.
            if target not in INCIDENT_TRANSITIONS:
                raise AppError(
                    "errors.incident_status_invalid",
                    400,
                    {"field": "incident_status", "allowed": sorted(INCIDENT_TRANSITIONS)},
                )
            return target

        origin = normalize_incident_status(current.incident_status) or DEFAULT_STATUS
        if origin == target:
            return target
        return validate_transition(
            origin,
            target,
            transitions=INCIDENT_TRANSITIONS,
            reason_required=INCIDENT_REASON_REQUIRED,
            reason=payload.get('reason') or payload.get('note'),
            entity="incident",
        )

    @classmethod
    def _validate_dates(cls, payload, current):
        incident_date = _as_datetime(
            payload.get('incident_date', getattr(current, 'incident_date', None)), 'incident_date'
        )
        close_date = _as_datetime(
            payload.get('close_date', getattr(current, 'close_date', None)), 'close_date'
        )
        status = payload.get('incident_status') or normalize_incident_status(
            getattr(current, 'incident_status', None)
        )
        # Lo que se guarda es la hora de pared ya normalizada, no el texto que
        # mando el llamador (que puede traer zona).
        for campo, valor in (('incident_date', incident_date), ('close_date', close_date)):
            if campo in payload and payload[campo] not in (None, ''):
                payload[campo] = valor

        if incident_date and incident_date > _now():
            raise AppError(
                "errors.incident_date_in_the_future", 400, {"field": "incident_date"}
            )
        if close_date and incident_date and close_date < incident_date:
            raise AppError(
                "errors.incident_close_date_before_incident_date",
                400,
                {"field": "close_date"},
            )
        if status in INCIDENT_CLOSED_STATUSES:
            # Cerrar sin fecha dejaba la incidencia sin cuando se resolvio; se
            # completa con el momento del cambio en lugar de rechazar.
            if close_date is None:
                payload['close_date'] = _now()
        elif status and close_date is not None:
            if 'close_date' in payload:
                # El llamador pidio explicitamente una fecha de cierre en una
                # incidencia que no esta cerrada: eso no tiene sentido.
                raise AppError(
                    "errors.incident_close_date_requires_closed_status",
                    400,
                    {"field": "close_date", "incident_status": status},
                )
            # La fecha viene del cierre anterior y la incidencia se esta
            # reabriendo: se limpia, porque ya no esta cerrada.
            payload['close_date'] = None

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.setdefault('incident_status', DEFAULT_STATUS)
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        with transaction_context() as db:
            current = db.get(Incident, int(item_id))
            if not current:
                raise AppError("errors.resource_not_found", 404)
            db.expunge(current)
        return super().update(item_id, cls._validate(payload, current=current), user_id=user_id)


def transition_incident(incident_id, payload: dict, user_data: dict) -> dict:
    """Mueve una incidencia de estatus, con motivo cuando el catalogo lo exige.

    Existe por simetria con proyectos y tareas: las tres son procesos con
    maquina de estados y ahora las tres se mueven por el mismo camino. Sin
    esto, cambiar el estatus era un PUT con el campo suelto y la pantalla lo
    pintaba como texto libre, que es como el tablero acababa con una columna
    por variante escrita a mano.

    El motivo se anota en `event_log`, la bitacora unica que usa el modulo de
    restaurante para lo mismo: `incident` no tiene tabla de eventos propia y
    `note` es el texto de la incidencia, no el del cambio.
    """
    from app.security.audit import audit_event

    incident = require_incident_access(incident_id, user_data)
    target = normalize_incident_status((payload or {}).get("status"))
    reason = (payload or {}).get("reason")
    origin = normalize_incident_status(incident.incident_status) or DEFAULT_STATUS
    validated = validate_transition(
        origin,
        target,
        transitions=INCIDENT_TRANSITIONS,
        reason_required=INCIDENT_REASON_REQUIRED,
        reason=reason,
        entity="incident",
    )

    # El motivo viaja en el payload aunque no sea columna: `_resolve_status`
    # lo lee para validar de nuevo la transicion, y `_coerce_payload` descarta
    # lo que no sea columna antes de escribir. Sin el, cancelar fallaba aqui
    # -en la segunda validacion- despues de haberse aceptado arriba.
    actualizado = IncidentService.update(
        incident_id,
        {"incident_status": validated, "reason": reason},
        user_id=user_data.get("id_user"),
    )
    with transaction_context() as db:
        audit_event(
            db,
            user_data,
            event_type="incident_transition",
            entity_name="incident",
            action=validated,
            metadata={
                "id_incident": int(incident_id),
                "previous_status": origin,
                "new_status": validated,
                "reason": str(reason or "").strip() or None,
            },
        )
    return actualizado


def list_incidents(user_data, *, page=1, per_page=20, filters=None, sort=None) -> dict:
    """Listado acotado a lo que el actor tiene derecho a ver."""
    try:
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 20), 1), 100)
    except (TypeError, ValueError):
        page, per_page = 1, 20

    with transaction_context() as db:
        query = scoped_incident_query(db, user_data)
        for campo, valor in (filters or {}).items():
            columna = getattr(Incident, campo, None)
            if columna is not None and valor not in (None, ""):
                if campo == "incident_status":
                    valor = normalize_incident_status(valor) or valor
                query = query.filter(columna == valor)

        columnas = {
            "incident_date": Incident.incident_date,
            "close_date": Incident.close_date,
            "creation_date": Incident.creation_date,
            "incident_status": Incident.incident_status,
        }
        descendente = str(sort or "").startswith("-")
        columna = columnas.get(str(sort or "").lstrip("-"), Incident.creation_date)
        query = query.order_by(columna.desc() if descendente else columna.asc(), Incident.id_incident.desc())

        total = query.count()
        filas = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [fila.serialize() for fila in filas],
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
