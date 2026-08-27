"""Incidencias: catalogo de estatus, coherencia de fechas y cierre.

Antes era un CRUD sin reglas: aceptaba cualquier estatus, una incidencia
cerrada antes de haber ocurrido, y el estatus "cerrada" sin fecha de cierre.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Incident, IncidentType, User
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


DEFAULT_STATUS = "abierta"


def _as_datetime(value, field):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        return payload

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
