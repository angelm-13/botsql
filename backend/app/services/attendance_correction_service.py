"""Correcciones de checadas (revision contable, 2026-10-28).

Para que nadie "acomode" sus horas despues (llegar tarde y pedir que no se
marque, o decir que no tomo su hora completa de comida) y para que cada quien se
haga responsable de checar:

* Corrige el supervisor del empleado (`user.supervisor`) o RH (quien puede
  editar `attendance_record`). Nadie corrige las suyas, salvo RH.
* La correccion cambia la checada MISMA: el calculo usa una sola hora. Lo que
  decia antes, quien la cambio, cuando y el motivo (obligatorio) quedan en
  `attendance_correction`. Una checada que faltaba (la salida que no se marco)
  se agrega como checada `manual` y tambien cuenta.
* Limite por empleado y mes calendario (el de la checada): cada hora corregida
  o agregada cuenta 1; corregir entrada y salida del mismo dia son 2. Por
  omision SIN limite (0; decision de RH, 2026-11-04: el supervisor corrige las
  veces que haga falta y RH vigila con la bitacora del reporte de asistencia).
  Una empresa que quiera tope lo captura en `attendance_correction_limit`
  (Ajustes de nomina): al llegar a el, el supervisor ya no puede; RH si, con
  motivo, y queda marcada como excepcion.
* El contador lo ven el supervisor y RH, nunca el empleado.
* No se corrige nada dentro de un periodo de nomina cerrado.
"""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime

from sqlalchemy import func, select

from app.models import AttendanceCorrection, AttendanceEmployeeLink, AttendanceRecord, User
from app.models.session import transaction_context
from app.utils.errors import AppError

LIMITE = "attendance_correction_limit"
# Tipo de incidente de cada correccion (respuestas de RH, 2026-11-04). "Fallo el
# checador" no es mala practica del empleado: no cuenta para la alerta de checadas a mano.
TIPOS_DE_INCIDENTE = ("forgot", "device_failure", "field_work", "hourly_leave")
# clave -> (valor por omision, valores permitidos), igual que POLITICA de vacaciones.
# 0 = sin limite (lo de omision desde 2026-11-04).
POLITICA_DE_CHECADAS = {LIMITE: (0, range(0, 32))}


MIN_MOTIVO = 5

def limite(db, al_dia: date) -> int:
    from app.services.payroll_calculation_service import _vigentes
    return int(_vigentes(db, (LIMITE,), al_dia).get(LIMITE, POLITICA_DE_CHECADAS[LIMITE][0]))


def _es_rh(user_data: dict) -> bool:
    from app.utils.auth import _has_entity_permission
    return _has_entity_permission(user_data, "attendance_record", "update")


def exigir_acceso_a_asistencias(user_data: dict) -> None:
    """Correcciones y horas extra pasan por el Gestor (pedido de Alan, 2026-11-05): sin
    leer `attendance_record` (RH apagado para ese rol o esa empresa) no se usan, aunque
    el actor sea jefe del empleado."""
    from app.utils.auth import _has_entity_permission
    if not _has_entity_permission(user_data, "attendance_record", "read"):
        raise AppError("errors.permission_denied", 403, {"entity": "attendance_record", "action": "read"})


def _exigir_que_pueda(db, user_data: dict, id_empleado: int) -> tuple[User, bool]:
    """(empleado, es_rh). Su supervisor o RH; nadie las suyas salvo RH."""
    exigir_acceso_a_asistencias(user_data)
    empleado = db.get(User, id_empleado)
    if empleado is None or empleado.deletion_date is not None:
        raise AppError("errors.invalid_field", 400, {"field": "id_user"})
    es_rh = _es_rh(user_data)
    actor = user_data.get("id_user")
    if not es_rh and (empleado.id_user == actor or empleado.supervisor != actor):
        raise AppError("errors.permission_denied", 403, {"entity": "attendance_record", "action": "update"})
    return empleado, es_rh


def _mes(dia: date) -> tuple[date, date]:
    return dia.replace(day=1), dia.replace(day=calendar.monthrange(dia.year, dia.month)[1])


def _usadas(db, id_user: int, dia: date) -> int:
    inicio, fin = _mes(dia)
    return db.scalar(select(func.count(AttendanceCorrection.id_attendance_correction))
                     .where(AttendanceCorrection.id_user == id_user)
                     .where(AttendanceCorrection.deletion_date.is_(None))
                     .where(AttendanceCorrection.check_date >= inicio)
                     .where(AttendanceCorrection.check_date <= fin)) or 0


def _hora(valor) -> datetime:
    try:
        return datetime.fromisoformat(str(valor).strip()[:16])
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": "new_time"}) from exc


def corregir(user_data: dict, payload: dict) -> dict:
    """Corrige una checada (`id_attendance_record`) o agrega la que falta (`id_user`)."""
    from app.services.employee_leave_service import _exigir_fuera_de_periodo_cerrado
    payload = dict(payload or {})
    motivo = str(payload.get("reason") or "").strip()
    # Minimo 5 letras: en la revision del tester se guardo un motivo de una sola letra ("p").
    if len(motivo) < MIN_MOTIVO or len(motivo) > 300:
        raise AppError("errors.invalid_field", 400, {"field": "reason", "min": MIN_MOTIVO})
    nueva = _hora(payload.get("new_time"))
    tipo = payload.get("incident_kind") or None
    if tipo is not None and tipo not in TIPOS_DE_INCIDENTE:
        raise AppError("errors.invalid_field", 400, {"field": "incident_kind", "allowed": list(TIPOS_DE_INCIDENTE)})
    actor = user_data.get("id_user")
    with transaction_context() as db:
        checada = None
        if payload.get("id_attendance_record") not in (None, ""):
            try:
                checada = db.get(AttendanceRecord, int(payload["id_attendance_record"]))
            except (TypeError, ValueError):
                checada = None
            if checada is None or checada.deletion_date is not None or checada.id_user is None:
                raise AppError("errors.resource_not_found", 404)
            # Se corrige la hora, no el dia: mover una checada a otro dia seria otra cosa.
            if nueva.date() != checada.check_time.date():
                raise AppError("errors.invalid_field", 400, {"field": "new_time", "reason": "same_day"})
            id_empleado = checada.id_user
        else:
            try:
                id_empleado = int(payload.get("id_user"))
            except (TypeError, ValueError) as exc:
                raise AppError("errors.invalid_field", 400, {"field": "id_user"}) from exc
        empleado, es_rh = _exigir_que_pueda(db, user_data, id_empleado)
        _exigir_fuera_de_periodo_cerrado(db, nueva.date(), nueva.date())
        tope, usadas = limite(db, nueva.date()), _usadas(db, id_empleado, nueva.date())
        excepcion = bool(tope) and usadas >= tope
        if excepcion and not es_rh:
            raise AppError("errors.attendance_correction_limit_reached", 409, {"limit": tope, "used": usadas})
        anterior = checada.check_time if checada else None
        if checada is not None:
            checada.check_time = nueva
        else:
            numero = db.scalar(select(AttendanceEmployeeLink.employee_no)
                               .where(AttendanceEmployeeLink.id_user == id_empleado)
                               .where(AttendanceEmployeeLink.deletion_date.is_(None))) or str(id_empleado)
            checada = AttendanceRecord(id_user=id_empleado, employee_no=numero, employee_name=empleado.full_name,
                                       check_time=nueva, source="manual",
                                       source_ref=f"correccion:{uuid.uuid4().hex}", created_by=actor)
            db.add(checada)
            db.flush()
        correccion = AttendanceCorrection(
            id_attendance_record=checada.id_attendance_record, id_user=id_empleado, check_date=nueva.date(),
            previous_time=anterior, new_time=nueva, reason=motivo, incident_kind=tipo, is_exception=excepcion,
            created_by=actor)
        db.add(correccion)
        db.flush()
        return {**correccion.serialize(), "limit": tope, "used": usadas + 1,
                "remaining": max(tope - usadas - 1, 0) if tope else None}


def del_mes(user_data: dict, id_user, mes: str) -> dict:
    """Contador y correcciones de un empleado en un mes ("AAAA-MM"): solo su supervisor o RH."""
    try:
        dia = date.fromisoformat(f"{str(mes)[:7]}-01")
        id_user = int(id_user)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": "month"}) from exc
    inicio, fin = _mes(dia)
    with transaction_context() as db:
        _exigir_que_pueda(db, user_data, id_user)
        filas = db.scalars(select(AttendanceCorrection)
                           .where(AttendanceCorrection.id_user == id_user)
                           .where(AttendanceCorrection.deletion_date.is_(None))
                           .where(AttendanceCorrection.check_date >= inicio)
                           .where(AttendanceCorrection.check_date <= fin)
                           .order_by(AttendanceCorrection.creation_date)).all()
        nombres = dict(db.execute(select(User.id_user, User.full_name)
                                  .where(User.id_user.in_([f.created_by for f in filas] or [0]))).all())
        tope = limite(db, dia)
        return {"id_user": id_user, "month": dia.strftime("%Y-%m"), "limit": tope, "used": len(filas),
                "remaining": max(tope - len(filas), 0) if tope else None,
                "corrections": [{**f.serialize(), "created_by_name": nombres.get(f.created_by) or ""} for f in filas]}
