"""Registrar en la bitacora algo que no es un alta, un cambio ni una baja.

Por que ya no hay una tabla propia
----------------------------------
Esto escribia en `audit_log`, una segunda bitacora paralela a `event_log`. La
razon de que existiera no era de diseno sino una restriccion: `event_log.action`
solo admitia `create`, `update` y `delete`, asi que un permiso denegado o el
cambio de estatus de un vale no cabian, y quien necesito registrarlos creo otra
tabla.

La migracion 20260911120000 ensancho esa restriccion, asi que el motivo
desaparecio y `audit_log` con el. Todo asiento -- CRUD o no -- vive ahora en
`event_log`, que es lo que hace que "que paso con esto" tenga una sola consulta
y no dos que alguien pueda olvidar cruzar.

Como encaja lo que no es CRUD
-----------------------------
`action` pasa a ser la CATEGORIA y `event_detail` el verbo concreto:

    permiso denegado    action='denied'      event_detail='read'
    cambio de estatus   action='transition'  event_detail='cerrado'
    algo del restaurante action='custom'     event_detail='mesa_cobrada'

Asi se puede contar "cuantos permisos se negaron" sin conocer de antemano todos
los verbos, y seguir viendo cual fue cada uno.
"""
from __future__ import annotations

from typing import Any

# De donde viene el asiento -> que categoria le toca en `action`. Lo que no
# este aqui cae en 'custom', que existe para que un caso nuevo no rompa nada ni
# obligue a otra migracion.
CATEGORIA = {
    "permission_denied": "denied",
    "incident_transition": "transition",
    "voucher_transition": "transition",
}


def audit_event(
    db_session: Any,
    user_data: dict[str, Any] | None,
    event_type: str,
    entity_name: str | None = None,
    action: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Deja constancia de un hecho en `event_log`.

    La firma no cambio a proposito: los tres llamadores siguen escribiendo lo
    mismo y es la funcion la que decide donde cae cada campo. Cambiarla habria
    mezclado la union de las dos bitacoras con una revision de sus llamadores.
    """
    from app.models.event_log import EventLog

    user_data = user_data or {}
    datos = dict(metadata or {})
    # El proyecto sube a columna: filtrar por el era la unica consulta que la
    # bitacora del restaurante hacia, y hacerla contra el JSON obligaba a
    # abrirlo fila por fila.
    id_proyect = datos.pop("id_proyect", None) or user_data.get("id_proyect")
    # Se conserva el origen dentro del asiento: es lo que distingue un evento
    # del restaurante de uno de almacen cuando los dos comparten tabla.
    datos["event_type"] = event_type

    db_session.add(EventLog(
        table_name=(entity_name or event_type)[:50],
        field_name="*",
        action=CATEGORIA.get(event_type, "custom"),
        event_detail=(str(action)[:80] if action else None),
        # Los dos explicitos: son NOT NULL y un hecho que no es un cambio de
        # fila no tiene "antes". Vacio dice eso; nulo no se puede guardar.
        before_value={},
        after_value=datos,
        id_proyect=int(id_proyect) if id_proyect else None,
        created_by=int(user_data.get("id_user") or 1),
    ))
