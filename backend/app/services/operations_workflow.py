"""Maquinas de estado compartidas por los modulos de Operaciones.

Incidencias y tareas guardaban su estatus como texto libre, asi que cualquier
valor entraba. El da~no practico se ve en las pantallas: ambas arman su tablero
agrupando por ese campo, de modo que un dedazo creaba una columna nueva y la
incidencia dejaba de aparecer donde su responsable la buscaba.

Aqui viven el catalogo de estatus, las transiciones permitidas y los motivos
obligatorios, con la misma forma que ya usaba el flujo de proyectos para que
los tres modulos se comporten igual.

Los valores anteriores a este catalogo no se rechazan al leer: se normalizan
cuando se reconocen y, si no, se conserva lo que hubiera. Rechazarlos dejaria
sin poder editar los registros ya capturados.
"""

from __future__ import annotations

from app.utils.errors import AppError


# --- Incidencias -----------------------------------------------------------
INCIDENT_STATUSES = ("abierta", "en_proceso", "resuelta", "cerrada", "cancelada")

INCIDENT_TRANSITIONS = {
    "abierta": {"en_proceso", "resuelta", "cancelada"},
    "en_proceso": {"resuelta", "cancelada"},
    # Una incidencia resuelta puede reabrirse si el problema volvio.
    "resuelta": {"cerrada", "en_proceso"},
    "cerrada": set(),
    "cancelada": set(),
}

INCIDENT_REASON_REQUIRED = {"cancelada"}
INCIDENT_CLOSED_STATUSES = {"resuelta", "cerrada", "cancelada"}

INCIDENT_ALIASES = {
    "abierto": "abierta",
    "nueva": "abierta",
    "open": "abierta",
    "pendiente": "abierta",
    "proceso": "en_proceso",
    "en proceso": "en_proceso",
    "en curso": "en_proceso",
    "atendiendo": "en_proceso",
    "resuelto": "resuelta",
    "solucionada": "resuelta",
    "cerrado": "cerrada",
    "closed": "cerrada",
    "cancelado": "cancelada",
}


# --- Tareas ----------------------------------------------------------------
TASK_STATUSES = ("pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada")

TASK_TRANSITIONS = {
    "pendiente": {"en_proceso", "cancelada"},
    "en_proceso": {"en_revision", "bloqueada", "terminada", "cancelada"},
    "bloqueada": {"en_proceso", "cancelada"},
    # De revision puede regresar a proceso si algo hay que corregir.
    "en_revision": {"terminada", "en_proceso"},
    "terminada": set(),
    "cancelada": set(),
}

TASK_REASON_REQUIRED = {"bloqueada", "cancelada"}
TASK_CLOSED_STATUSES = {"terminada", "cancelada"}

TASK_ALIASES = {
    "nueva": "pendiente",
    "por hacer": "pendiente",
    "todo": "pendiente",
    "abierta": "pendiente",
    "proceso": "en_proceso",
    "en proceso": "en_proceso",
    "en curso": "en_proceso",
    "haciendo": "en_proceso",
    "doing": "en_proceso",
    "revision": "en_revision",
    "en revision": "en_revision",
    "revisando": "en_revision",
    "bloqueado": "bloqueada",
    "detenida": "bloqueada",
    "terminado": "terminada",
    "completada": "terminada",
    "hecha": "terminada",
    "done": "terminada",
    "cancelado": "cancelada",
}


def normalize_status(value, statuses, aliases) -> str:
    """Lleva el valor capturado al catalogo, si se reconoce.

    Acepta las variantes que la gente escribe (mayusculas, espacios en vez de
    guion bajo, masculino o femenino) y devuelve el codigo del catalogo. Lo
    que no se reconoce se devuelve tal cual para que el llamador decida.
    """
    text = str(value or "").strip().lower().replace("-", " ")
    if not text:
        return ""
    collapsed = " ".join(text.split())
    underscored = collapsed.replace(" ", "_")
    if underscored in statuses:
        return underscored
    return aliases.get(collapsed, aliases.get(underscored, underscored))


def validate_transition(current, target, *, transitions, reason_required, reason, entity) -> str:
    """Valida un cambio de estatus contra la maquina de estados.

    `entity` solo sirve para nombrar la clave de error, de modo que la interfaz
    pueda dar un mensaje propio de incidencias o de tareas.
    """
    if current not in transitions:
        # Un registro con estatus anterior al catalogo puede moverse a
        # cualquier estatus valido: es la unica forma de regularizarlo.
        if target not in transitions:
            raise AppError(
                f"errors.{entity}_status_invalid",
                400,
                {"field": "status", "allowed": sorted(transitions)},
            )
    elif target not in transitions[current]:
        raise AppError(
            f"errors.{entity}_invalid_transition",
            409,
            {
                "current_status": current,
                "target_status": target,
                "allowed": sorted(transitions[current]),
            },
        )

    if target in reason_required and not str(reason or "").strip():
        raise AppError(
            f"errors.{entity}_transition_reason_required",
            400,
            {"field": "reason", "target_status": target},
        )
    return target


def normalize_incident_status(value) -> str:
    return normalize_status(value, INCIDENT_STATUSES, INCIDENT_ALIASES)


def normalize_task_status(value) -> str:
    return normalize_status(value, TASK_STATUSES, TASK_ALIASES)


def incident_catalog() -> dict:
    return {
        "statuses": list(INCIDENT_STATUSES),
        "transitions": {key: sorted(value) for key, value in INCIDENT_TRANSITIONS.items()},
        "reason_required": sorted(INCIDENT_REASON_REQUIRED),
        "closed_statuses": sorted(INCIDENT_CLOSED_STATUSES),
    }


def task_catalog() -> dict:
    return {
        "statuses": list(TASK_STATUSES),
        "transitions": {key: sorted(value) for key, value in TASK_TRANSITIONS.items()},
        "reason_required": sorted(TASK_REASON_REQUIRED),
        "closed_statuses": sorted(TASK_CLOSED_STATUSES),
    }


# --- Fase de tarea (tablero del taller) -------------------------------------
# Independiente de TASK_STATUSES: task_status es el flujo formal de la tarea
# (con motivo obligatorio al bloquear/cancelar); fase es la ubicacion visual en
# el tablero que pidio Jefe de taller. Antes "fase" era texto libre sin
# catalogo -cualquiera escribia lo que quisiera- y el tablero terminaba con una
# columna nueva por cada dedazo, igual que le pasaba a task_status antes de
# este archivo. Sin maquina de transiciones a proposito: no se pidio un flujo
# formal para la fase, solo que viniera de una lista fija.
TASK_FASES = ("en_espera", "en_proceso", "bloqueado", "terminado", "entregado")

TASK_FASE_ALIASES = {
    "ejecucion": "en_proceso",
    "ejecución": "en_proceso",
    "cierre": "terminado",
}


def normalize_task_fase(value) -> str:
    return normalize_status(value, TASK_FASES, TASK_FASE_ALIASES)


def task_fase_catalog() -> dict:
    return {"fases": list(TASK_FASES)}
