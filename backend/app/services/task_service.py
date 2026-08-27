"""Tareas: catalogo de estatus, responsables reales y proyecto abierto.

Antes era un CRUD sin reglas y aceptaba, entre otras cosas, un estatus
inventado, una duracion negativa, responsables que no existen (las columnas
analyst, dependency, leader y validation son enteros sueltos, sin llave
foranea) y tareas nuevas en un proyecto ya cerrado.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.models import Proyect, Task, User
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.services.operations_workflow import (
    TASK_CLOSED_STATUSES,
    TASK_REASON_REQUIRED,
    TASK_TRANSITIONS,
    normalize_task_status,
    validate_transition,
)
from app.services.project_management_service import normalize_project_status
from app.utils.errors import AppError


DEFAULT_STATUS = "pendiente"

# Estatus de proyecto que ya no admiten trabajo nuevo.
PROJECT_CLOSED_STATUSES = {"completed", "denied"}

# Columnas de responsables: enteros sin llave foranea en la tabla, asi que la
# existencia del usuario se comprueba aqui.
RESPONSIBLE_FIELDS = ("owner", "analyst", "leader", "validation")

VALID_PRIORITIES = {"baja", "media", "alta", "urgente"}

PRIORITY_ALIASES = {
    "low": "baja",
    "normal": "media",
    "medium": "media",
    "high": "alta",
    "urgent": "urgente",
    "critica": "urgente",
    "muy alta": "urgente",
}


class TaskService(CrudService):
    model = Task
    primary_key = 'id_task'
    entity_name = 'task'

    @classmethod
    def _validate(cls, payload: dict, *, current: Task | None = None) -> dict:
        payload = dict(payload or {})

        if 'id_proyect' in payload and payload['id_proyect'] not in (None, ''):
            payload['id_proyect'] = cls._open_project(payload['id_proyect'], creating=current is None)
        elif current is None:
            raise AppError("errors.required_field", 400, {"field": "id_proyect"})

        for field in RESPONSIBLE_FIELDS:
            if field in payload and payload[field] not in (None, ''):
                payload[field] = cls._existing_user(payload[field], field)

        if 'duration' in payload and payload['duration'] not in (None, ''):
            payload['duration'] = cls._non_negative(payload['duration'], 'duration')

        if 'priority' in payload and payload['priority'] not in (None, ''):
            payload['priority'] = cls._priority(payload['priority'])

        if 'task_status' in payload:
            payload['task_status'] = cls._resolve_status(payload, current)

        return payload

    @staticmethod
    def _as_int(value, field):
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": field}) from exc

    @classmethod
    def _existing_user(cls, value, field):
        parsed = cls._as_int(value, field)
        with transaction_context() as db:
            user = db.get(User, parsed)
            if not user or getattr(user, 'deletion_date', None) is not None:
                raise AppError(
                    "errors.task_responsible_not_found",
                    400,
                    {"field": field, "id_user": parsed},
                )
        return parsed

    @classmethod
    def _open_project(cls, value, *, creating):
        parsed = cls._as_int(value, 'id_proyect')
        with transaction_context() as db:
            project = db.get(Proyect, parsed)
            if not project or project.deletion_date is not None:
                raise AppError("errors.resource_not_found", 404, {"field": "id_proyect"})
            status = normalize_project_status(project.proyect_status)
            # Solo se bloquea al dar de alta: una tarea que ya existe debe
            # poder cerrarse aunque el proyecto se haya cerrado antes.
            if creating and status in PROJECT_CLOSED_STATUSES:
                raise AppError(
                    "errors.task_project_closed",
                    409,
                    {"field": "id_proyect", "proyect_status": status},
                )
        return parsed

    @staticmethod
    def _non_negative(value, field):
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": field}) from exc
        if parsed < 0:
            raise AppError("errors.invalid_field", 400, {"field": field})
        return parsed

    @staticmethod
    def _priority(value):
        text = " ".join(str(value or "").strip().lower().split())
        resolved = PRIORITY_ALIASES.get(text, text)
        if resolved not in VALID_PRIORITIES:
            raise AppError(
                "errors.task_priority_invalid",
                400,
                {"field": "priority", "allowed": sorted(VALID_PRIORITIES)},
            )
        return resolved

    @classmethod
    def _resolve_status(cls, payload, current):
        target = normalize_task_status(payload.get('task_status'))
        if not target:
            return DEFAULT_STATUS if current is None else current.task_status

        if current is None:
            if target not in TASK_TRANSITIONS:
                raise AppError(
                    "errors.task_status_invalid",
                    400,
                    {"field": "task_status", "allowed": sorted(TASK_TRANSITIONS)},
                )
            return target

        origin = normalize_task_status(current.task_status) or DEFAULT_STATUS
        if origin == target:
            return target
        return validate_transition(
            origin,
            target,
            transitions=TASK_TRANSITIONS,
            reason_required=TASK_REASON_REQUIRED,
            reason=payload.get('reason') or payload.get('note'),
            entity="task",
        )

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.setdefault('task_status', DEFAULT_STATUS)
        return super().create(cls._validate(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        with transaction_context() as db:
            current = db.get(Task, int(item_id))
            if not current:
                raise AppError("errors.resource_not_found", 404)
            db.expunge(current)
        return super().update(item_id, cls._validate(payload, current=current), user_id=user_id)


def task_is_closed(task) -> bool:
    return normalize_task_status(getattr(task, 'task_status', None)) in TASK_CLOSED_STATUSES
