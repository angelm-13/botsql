"""Tareas: catalogo de estatus, fase de taller, responsables reales y proyecto
abierto.

Antes era un CRUD sin reglas y aceptaba, entre otras cosas, un estatus
inventado, una duracion negativa, responsables que no existen (las columnas
dependency y validation son enteros sueltos, sin llave foranea) y tareas
nuevas en un proyecto ya cerrado. `analyst` y `leader` -las mismas fallas, un
entero suelto sin llave foranea- se retiraron para simplificar la pantalla:
en produccion real nunca sirvieron para distinguir usuarios (las 13 tareas de
torredigital-prod comparten un solo valor en las tres, el default de
instalacion). `owner` SI se queda, aunque tenga el mismo defecto de fondo:
`desarrollo_por_empleado_query` (app/kpis/registry.py) ya lo usa como
responsable real para el KPI "Desarrollo por empleado".
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.models import Proyect, Task, User
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.services.operations_workflow import (
    FASE_TO_TASK_STATUS,
    TASK_CLOSED_STATUSES,
    TASK_FASES,
    TASK_REASON_REQUIRED,
    TASK_TRANSITIONS,
    normalize_task_fase,
    normalize_task_status,
    validate_transition,
)
from app.services.project_management_service import (
    PROJECT_CLOSED_STATUSES,
    normalize_project_status,
)
from app.utils.errors import AppError


DEFAULT_STATUS = "pendiente"
DEFAULT_FASE = "en_espera"

# Columnas de responsables: enteros sin llave foranea en la tabla (salvo
# `owner`, que si tiene FK a `user`), asi que la existencia del usuario se
# comprueba aqui de todas formas para tratarlas igual.
RESPONSIBLE_FIELDS = ("owner", "validation")

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
        # Se guarda ANTES de que 'fase' pueda inyectar 'task_status' mas
        # abajo: si quien llama ya mando un task_status explicito (el flujo
        # dedicado, /task/<id>/transition), esa intencion manda y no se
        # pisa con lo que la fase sugeriria.
        explicit_task_status = 'task_status' in payload

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

        if 'fase' in payload:
            payload['fase'] = cls._fase(payload['fase'])
            if not explicit_task_status and payload['fase']:
                derived = FASE_TO_TASK_STATUS.get(payload['fase'])
                origin = normalize_task_status(current.task_status) if current else None
                if derived and derived != origin:
                    payload['task_status'] = derived

        if 'task_status' in payload:
            if explicit_task_status:
                payload['task_status'] = cls._resolve_status(payload, current)
            # Si no fue explicito (lo puso la fase, arriba), se deja tal
            # cual: a proposito NO pasa por `validate_transition` -- Jefe de
            # taller pidio que cambiar la fase cierre la tarea sin repetir
            # la adyacencia formal de TASK_TRANSITIONS ni exigir motivo. Ver
            # el comentario de FASE_TO_TASK_STATUS (operations_workflow.py).

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

    @staticmethod
    def _fase(value):
        if value in (None, ''):
            return None
        normalized = normalize_task_fase(value)
        if normalized not in TASK_FASES:
            raise AppError(
                "errors.task_fase_invalid",
                400,
                {"field": "fase", "allowed": list(TASK_FASES)},
            )
        return normalized

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
        payload.setdefault('fase', DEFAULT_FASE)
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


def transition_task(task_id, payload: dict, user_data: dict) -> dict:
    """Mueve una tarea de estatus y lo anota en el expediente del proyecto.

    Existe por simetria con el flujo de proyectos, que ya tenia su
    `/transition`. Sin este endpoint la unica forma de cambiar el estatus de
    una tarea era un PUT con el campo suelto, asi que la pantalla lo pintaba
    como texto libre: quien escribia "En Proceso " creaba una columna nueva en
    el tablero y la tarea desaparecia de donde su responsable la buscaba. El
    motivo tampoco tenia donde guardarse.
    """
    from app.services.project_management_service import _append_event, require_task_access

    require_task_access(task_id, user_data)
    target = normalize_task_status((payload or {}).get("status"))
    reason = (payload or {}).get("reason")
    content = (payload or {}).get("content")

    with transaction_context() as db:
        task = db.get(Task, int(task_id))
        if not task or task.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        origin = normalize_task_status(task.task_status) or DEFAULT_STATUS
        validated = validate_transition(
            origin,
            target,
            transitions=TASK_TRANSITIONS,
            reason_required=TASK_REASON_REQUIRED,
            reason=reason,
            entity="task",
        )
        project = db.get(Proyect, task.id_proyect)
        if not project or project.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404, {"field": "id_proyect"})

        task.task_status = validated
        _append_event(
            db,
            project,
            user_data,
            "task_status_changed",
            task=task,
            previous_status=origin,
            new_status=validated,
            reason=reason,
            content=content,
        )
        db.flush()
        return task.serialize()


def add_task_note(task_id, payload: dict, user_data: dict) -> dict:
    """Escribe una nota de tarea y la deja visible en la linea de tiempo.

    La nota sigue viviendo en `task_note`, que es su tabla; lo que se agrega es
    el reflejo en `proyect_event` para que el expediente del proyecto cuente lo
    que pasa en sus tareas sin tener que abrirlas una por una.
    """
    from app.services.project_management_service import _append_event, require_task_access
    from app.services.task_note_service import TaskNoteService

    require_task_access(task_id, user_data)
    description = str((payload or {}).get("task_note_description") or "").strip()
    if not description:
        raise AppError("errors.required_field", 400, {"field": "task_note_description"})

    nota = {"id_task": int(task_id), "task_note_description": description}
    fecha = (payload or {}).get("date")
    if fecha not in (None, ""):
        nota["date"] = fecha
    note = TaskNoteService.create(nota, user_id=user_data.get("id_user"))
    with transaction_context() as db:
        task = db.get(Task, int(task_id))
        project = db.get(Proyect, task.id_proyect) if task else None
        if project is not None:
            _append_event(db, project, user_data, "task_note", task=task, content=description)
            db.flush()
    return note
