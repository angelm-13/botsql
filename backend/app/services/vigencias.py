"""Cambiar una asignacion con vigencia "a partir de" una fecha (2026-11-02).

Lo usa el apartado "Nomina y asistencia" del perfil del usuario para el
horario (employee_schedule), el grupo de pago (employee_payroll_group) y la
forma de salario (employee_salary): RH elige el valor nuevo y desde cuando, y
no tiene que cerrar antes a mano la asignacion que estaba vigente.

* La asignacion vigente ese dia se cierra el dia anterior, y la nueva sigue
  hasta donde llegaba aquella (o sin fin). Las dos cosas van en una sola
  transaccion: nunca queda la persona sin asignacion ni con dos encimadas.
* Si la vigente empieza ese mismo dia, se corrige en su lugar (capturaron mal).
* Cualquier otro encime -una asignacion futura ya capturada- lo sigue
  rechazando el `_validar` de cada servicio, con su 409 de siempre.

Cada paso deja su asiento en el registro de eventos, igual que el CRUD.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from app.models.session import transaction_context
from app.services.work_schedule_service import _entero, _fecha


def cambiar_desde(servicio, payload: dict, user_id: int | None = None) -> dict:
    """Asigna los valores de `payload` a `id_user` desde `valid_from`; devuelve la fila que queda."""
    modelo, llave = servicio.model, servicio.primary_key
    # La vigencia final la decide este cambio, no quien lo pide.
    datos = {k: v for k, v in dict(payload or {}).items() if k not in (llave, "valid_to", "created_by")}
    id_user = _entero(datos.get("id_user"), "id_user")
    desde = _fecha(datos.get("valid_from"), "valid_from")
    with transaction_context() as db:
        filas = db.scalars(select(modelo).where(modelo.id_user == id_user)
                           .where(modelo.deletion_date.is_(None))).all()
        del_dia = next((f for f in filas if f.valid_from == desde), None)
        anterior = next((f for f in filas if f.valid_from < desde
                         and (f.valid_to is None or f.valid_to >= desde)), None)
        id_del_dia = getattr(del_dia, llave) if del_dia else None
        id_anterior = getattr(anterior, llave) if anterior else None
        hasta = anterior.valid_to if anterior else None

    if id_del_dia is not None:
        return servicio.update(id_del_dia, datos, user_id=user_id)

    datos["valid_to"] = hasta.isoformat() if hasta else None
    datos.update(servicio._validar(datos, excluir_id=id_anterior) or {})
    nuevo = servicio._coerce_payload({**datos, "created_by": user_id or 1})
    try:
        with transaction_context() as db:
            if id_anterior is not None:
                fila = db.get(modelo, id_anterior)
                antes = fila.valid_to
                fila.valid_to = desde - timedelta(days=1)
                servicio._write_event_log(db, action="update", actor_id=user_id, field_name="valid_to",
                                          before=antes.isoformat() if antes else "",
                                          after=fila.valid_to.isoformat())
            item = modelo(**nuevo)
            db.add(item)
            db.flush()
            creado = item.serialize()
            servicio._write_event_log(db, action="create", actor_id=user_id, before="",
                                      after=servicio._format_audit_create_after(creado), field_name="*")
            return creado
    except (IntegrityError, StatementError) as error:
        servicio._raise_database_constraint_error(error, action="create")
