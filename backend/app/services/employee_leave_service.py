"""Vacaciones, permisos e incapacidades (employee_leave) y el saldo de vacaciones.

Que dia de una ausencia es falta y cual se paga lo decide
services/attendance_rules.py. Aqui viven las reglas de captura, validadas en
el backend para que valgan igual por la API:

* Las ausencias de un mismo empleado no se enciman.
* No se registra, edita ni borra una ausencia cuyas fechas caigan en un periodo
  de nomina cerrado: el recibo ya pagado no debe quedar distinto de lo
  registrado (decision de RH, 2026-10-21).
* Vacaciones (LFT art. 76): necesitan fecha de ingreso, no hay antes del primer
  año, no cruzan el aniversario y no pasan del saldo. Solo se descuentan los
  dias laborables del horario del empleado, asi que necesita horario asignado
  en todo el rango.

Saldo de vacaciones: al cumplir cada año de servicio le tocan los dias de ese
año; disponibles = los que le tocan - los tomados (aprobados) - los pendientes
(solicitados), desde su ultimo aniversario. Los dias no usados del año anterior
no se acumulan (decision de RH, 2026-10-21).

Solicitudes (decisiones de RH, 2026-10-22): el empleado pide vacaciones o un
permiso (la incapacidad la registra RH); lo aprueba o rechaza su supervisor
(`user.supervisor`) o RH (permiso de editar `employee_leave`). Lo que registra RH
directamente queda aprobado. Al aprobar se vuelven a validar saldo, que no se
enciman y que no caigan en un periodo cerrado.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import EmployeeLeave, PayrollPeriod, User
from app.models.employee_leave import (APROBADA, CANCELADA, ESTADOS_VIGENTES, RECHAZADA, SOLICITADA,
                                       TIPOS_DE_AUSENCIA)
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError
from app.utils.tiempo import ahora_negocio, ahora_utc

VACACIONES = "vacation"
# Lo que el propio empleado puede pedir; la incapacidad la registra RH (folio del IMSS).
TIPOS_QUE_PIDE_EL_EMPLEADO = ("vacation", "paid_leave", "unpaid_leave")
# Columnas que solo mueve el flujo de solicitud; la captura generica no las escribe.
CAMPOS_DEL_FLUJO = ("leave_status", "requested_by", "reviewed_by", "reviewed_at", "review_note")


def _aniversario(ingreso: date, anios: int) -> date:
    try:
        return ingreso.replace(year=ingreso.year + anios)
    except ValueError:  # 29 de febrero en un año no bisiesto
        return date(ingreso.year + anios, 2, 28)


def ano_de_servicio(ingreso: date, al_dia: date) -> tuple[int, date, date]:
    """(años cumplidos, inicio y fin del año de servicio en curso) `al_dia`."""
    anios = ley.anios_cumplidos(ingreso, al_dia)
    return anios, _aniversario(ingreso, anios), _aniversario(ingreso, anios + 1) - timedelta(days=1)


def dias_laborables(db, id_user: int, desde: date, hasta: date) -> tuple[int, bool]:
    """(dias laborables de su horario en el rango, si todo el rango tiene horario)."""
    from app.services.attendance_record_service import asistencia_por_empleado
    dias = asistencia_por_empleado(db, desde, hasta, ids=[id_user], con_checadas=False).get(id_user, [])
    return sum(d.laboral for d in dias), bool(dias) and all(d.con_horario for d in dias)


def _vacaciones_tomadas(db, ventanas: dict, excluir_id=None) -> dict[int, tuple[int, int]]:
    """{id_user: (aprobados, pendientes)} en dias laborables de vacaciones, dentro de la
    ventana (inicio, fin) de cada uno.

    Antes se leia el calendario completo (horarios, festivos y checadas) una vez
    por cada ausencia de cada empleado: cientos de consultas para todo el saldo.
    Ahora se leen las vacaciones de todos y el calendario sin checadas, una vez.
    """
    tomadas = {id_user: [0, 0] for id_user in ventanas}
    if not ventanas:
        return {k: tuple(v) for k, v in tomadas.items()}
    desde, hasta = min(v[0] for v in ventanas.values()), max(v[1] for v in ventanas.values())
    tramos = []
    for v in db.scalars(select(EmployeeLeave)
                        .where(EmployeeLeave.id_user.in_(list(ventanas)))
                        .where(EmployeeLeave.leave_type == VACACIONES)
                        .where(EmployeeLeave.leave_status.in_(ESTADOS_VIGENTES))
                        .where(EmployeeLeave.deletion_date.is_(None))
                        .where(EmployeeLeave.start_date <= hasta)
                        .where(EmployeeLeave.end_date >= desde)):
        inicio, fin = ventanas[v.id_user]
        if (excluir_id is not None and str(v.id_employee_leave) == str(excluir_id)) \
                or v.start_date > fin or v.end_date < inicio:
            continue
        tramos.append((v.id_user, max(v.start_date, inicio), min(v.end_date, fin), v.leave_status == APROBADA))
    if not tramos:
        return {k: tuple(v) for k, v in tomadas.items()}
    from app.services.attendance_record_service import asistencia_por_empleado
    calendario = asistencia_por_empleado(db, min(t[1] for t in tramos), max(t[2] for t in tramos),
                                         ids=sorted({t[0] for t in tramos}), con_checadas=False)
    for id_user, inicio, fin, aprobada in tramos:
        tomadas[id_user][0 if aprobada else 1] += sum(
            d.laboral for d in calendario.get(id_user, []) if inicio <= d.fecha <= fin)
    return {k: tuple(v) for k, v in tomadas.items()}


def _saldos(db, empleados, al_dia: date, excluir_id=None) -> list[dict]:
    ventanas, datos = {}, []
    for empleado in empleados:
        ingreso = empleado.hire_date
        if not ingreso or ingreso > al_dia:
            datos.append((empleado, None))
            continue
        anios, inicio, fin = ano_de_servicio(ingreso, al_dia)
        if anios >= 1:
            ventanas[empleado.id_user] = (inicio, fin)
        datos.append((empleado, (anios, inicio, fin)))
    tomadas = _vacaciones_tomadas(db, ventanas, excluir_id)
    salida = []
    for empleado, ano in datos:
        if ano is None:
            salida.append({"id_user": empleado.id_user, "full_name": empleado.full_name or "", "hire_date": None,
                           "service_years": 0, "entitled": 0, "taken": 0, "pending": 0, "available": 0,
                           "year_start": None, "year_end": None})
            continue
        anios, inicio, fin = ano
        derecho = ley.dias_de_vacaciones(anios - 1) if anios >= 1 else 0
        tomados, pendientes = tomadas.get(empleado.id_user, (0, 0))
        salida.append({"id_user": empleado.id_user, "full_name": empleado.full_name or "",
                       "hire_date": empleado.hire_date.isoformat(), "service_years": anios, "entitled": derecho,
                       "taken": tomados, "pending": pendientes,
                       "available": max(derecho - tomados - pendientes, 0),
                       "year_start": inicio.isoformat(), "year_end": fin.isoformat()})
    return salida


def saldo_de_vacaciones(db, empleado: User, al_dia: date, excluir_id=None) -> dict:
    return _saldos(db, [empleado], al_dia, excluir_id)[0]


def saldos() -> list[dict]:
    """Saldo de vacaciones de cada empleado al dia de hoy (hora del negocio)."""
    hoy = ahora_negocio().date()
    with transaction_context() as db:
        empleados = db.scalars(select(User)
                               .where(User.deletion_date.is_(None))
                               .where(User.is_employee.is_(True))
                               .order_by(User.full_name)).all()
        return _saldos(db, empleados, hoy)


def _exigir_fuera_de_periodo_cerrado(db, desde: date, hasta: date) -> None:
    cerrado = db.scalars(select(PayrollPeriod)
                         .where(PayrollPeriod.deletion_date.is_(None))
                         .where(PayrollPeriod.period_state == "closed")
                         .where(PayrollPeriod.period_start <= hasta)
                         .where(PayrollPeriod.period_end >= desde)).first()
    if cerrado is not None:
        raise AppError("errors.payroll_period_closed", 409, {"id_payroll_period": cerrado.id_payroll_period})


class EmployeeLeaveService(CrudService):
    model = EmployeeLeave
    primary_key = 'id_employee_leave'
    entity_name = 'employee_leave'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        id_user = _entero(datos.get("id_user"), "id_user")
        tipo = str(datos.get("leave_type") or "")
        if tipo not in TIPOS_DE_AUSENCIA:
            raise AppError("errors.invalid_field", 400, {"field": "leave_type", "allowed": list(TIPOS_DE_AUSENCIA)})
        desde = _fecha(datos.get("start_date"), "start_date")
        hasta = _fecha(datos.get("end_date"), "end_date")
        if hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "end_date"})
        if len(str(datos.get("notes") or "")) > 300:
            raise AppError("errors.invalid_field", 400, {"field": "notes"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            _exigir_fuera_de_periodo_cerrado(db, desde, hasta)
            for otra in db.scalars(select(EmployeeLeave)
                                   .where(EmployeeLeave.id_user == id_user)
                                   .where(EmployeeLeave.leave_status.in_(ESTADOS_VIGENTES))
                                   .where(EmployeeLeave.deletion_date.is_(None))
                                   .where(EmployeeLeave.start_date <= hasta)
                                   .where(EmployeeLeave.end_date >= desde)):
                if excluir_id is None or str(otra.id_employee_leave) != str(excluir_id):
                    raise AppError("errors.employee_leave_overlap", 409, {
                        "id_employee_leave": otra.id_employee_leave, "leave_type": otra.leave_type,
                        "start_date": otra.start_date.isoformat(), "end_date": otra.end_date.isoformat()})
            if tipo == VACACIONES:
                cls._validar_vacaciones(db, empleado, desde, hasta, excluir_id)

    @staticmethod
    def _validar_vacaciones(db, empleado: User, desde: date, hasta: date, excluir_id) -> None:
        if not empleado.hire_date:
            raise AppError("errors.employee_leave_no_hire_date", 409, {"id_user": empleado.id_user})
        anios, _, fin = ano_de_servicio(empleado.hire_date, desde)
        if empleado.hire_date > desde or anios < 1:
            raise AppError("errors.employee_leave_first_year", 409, {
                "first_anniversary": _aniversario(empleado.hire_date, 1).isoformat()})
        if hasta > fin:
            raise AppError("errors.employee_leave_crosses_anniversary", 409, {
                "anniversary": (fin + timedelta(days=1)).isoformat()})
        pedidos, con_horario = dias_laborables(db, empleado.id_user, desde, hasta)
        if not con_horario:
            raise AppError("errors.employee_leave_needs_schedule", 409, {"id_user": empleado.id_user})
        if pedidos == 0:
            raise AppError("errors.employee_leave_no_workdays", 400, {"field": "start_date"})
        saldo = saldo_de_vacaciones(db, empleado, desde, excluir_id)
        if pedidos > saldo["available"]:
            raise AppError("errors.employee_leave_insufficient_balance", 409, {
                "available": saldo["available"], "requested": pedidos, "entitled": saldo["entitled"]})

    @classmethod
    def _actual(cls, item_id) -> dict:
        actual = cls.get(item_id)
        if actual is None:
            raise AppError("errors.resource_not_found", 404)
        return actual

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        # Lo que registra RH queda aprobado de una vez; el estado no se escribe a mano.
        payload = {k: v for k, v in dict(payload or {}).items() if k not in CAMPOS_DEL_FLUJO}
        cls._validar(payload)
        payload.update(leave_status=APROBADA, reviewed_by=user_id, reviewed_at=ahora_utc())
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = {k: v for k, v in dict(payload or {}).items() if k not in CAMPOS_DEL_FLUJO}
        actual = cls._actual(item_id)
        with transaction_context() as db:
            _exigir_fuera_de_periodo_cerrado(db, _fecha(actual["start_date"], "start_date"),
                                             _fecha(actual["end_date"], "end_date"))
        cls._validar({**actual, **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        actual = cls._actual(item_id)
        with transaction_context() as db:
            _exigir_fuera_de_periodo_cerrado(db, _fecha(actual["start_date"], "start_date"),
                                             _fecha(actual["end_date"], "end_date"))
        return super().delete(item_id, user_id=user_id)


# ------------------------------------------------------------------ solicitudes del empleado

def _es_rh(user_data: dict) -> bool:
    from app.utils.auth import _has_entity_permission
    return _has_entity_permission(user_data, "employee_leave", "update")


def _notificar(destinatario, notification_type: str, titulo: str, mensaje: str, actor_id: int,
               id_ausencia: int) -> None:
    """Avisa (campana) al jefe o al empleado. Se llama ya cerrada la transaccion y es
    "best effort", igual que los avisos de compras y vales: un fallo al avisar nunca
    revierte la solicitud. Quien hizo la accion no se avisa a si mismo. Cada tipo debe
    estar en notification_type_check (20261007100000); por eso las llamadas lo escriben
    tal cual, para que la prueba test_notification_types_constraint lo vea.
    """
    if not destinatario or destinatario == actor_id:
        return
    from app.services.notification_service import create_notification
    try:
        create_notification(id_user_recipient=destinatario, notification_type=notification_type, title=titulo,
                            message=mensaje, id_user_sender=actor_id, created_by=actor_id,
                            target_entity="employee_leave", target_id=id_ausencia)
    except Exception:
        pass


def _con_nombre(db, ausencias) -> list[dict]:
    ids = {a.id_user for a in ausencias}
    nombres = dict(db.execute(select(User.id_user, User.full_name).where(User.id_user.in_(list(ids) or [0]))).all())
    return [{**a.serialize(), "full_name": nombres.get(a.id_user) or f"#{a.id_user}"} for a in ausencias]


def mis_ausencias(actor_id: int) -> dict:
    """Saldo y ausencias del propio empleado (nunca las de otros)."""
    with transaction_context() as db:
        empleado = db.get(User, actor_id)
        if empleado is None or not empleado.is_employee:
            return {"is_employee": False, "balance": None, "leaves": []}
        propias = db.scalars(select(EmployeeLeave)
                             .where(EmployeeLeave.id_user == actor_id)
                             .where(EmployeeLeave.deletion_date.is_(None))
                             .order_by(EmployeeLeave.start_date.desc())).all()
        return {"is_employee": True, "balance": saldo_de_vacaciones(db, empleado, ahora_negocio().date()),
                "leaves": [a.serialize() for a in propias]}


def solicitar(actor_id: int, payload: dict) -> dict:
    """El empleado pide vacaciones o un permiso para si mismo; queda pendiente."""
    payload = dict(payload or {})
    if str(payload.get("leave_type") or "") not in TIPOS_QUE_PIDE_EL_EMPLEADO:
        raise AppError("errors.invalid_field", 400, {"field": "leave_type", "allowed": list(TIPOS_QUE_PIDE_EL_EMPLEADO)})
    datos = {"id_user": actor_id, "leave_type": payload["leave_type"], "start_date": payload.get("start_date"),
             "end_date": payload.get("end_date"), "notes": payload.get("notes") or None}
    EmployeeLeaveService._validar(datos)
    with transaction_context() as db:
        empleado = db.get(User, actor_id)
        ausencia = EmployeeLeave(**{**datos, "start_date": _fecha(datos["start_date"], "start_date"),
                                    "end_date": _fecha(datos["end_date"], "end_date")},
                                 leave_status=SOLICITADA, requested_by=actor_id, created_by=actor_id)
        db.add(ausencia)
        db.flush()
        resultado = ausencia.serialize()
        jefe = empleado.supervisor
    _notificar(jefe, notification_type="leave_requested", titulo="Solicitud de ausencia por autorizar",
               mensaje=f"{empleado.full_name} pidió del {resultado['start_date']} al {resultado['end_date']}.",
               actor_id=actor_id, id_ausencia=resultado["id_employee_leave"])
    return resultado


def cancelar(actor_id: int, id_ausencia) -> dict:
    """El empleado cancela su propia solicitud mientras siga pendiente."""
    with transaction_context() as db:
        ausencia = db.get(EmployeeLeave, _entero(id_ausencia, "id_employee_leave"))
        if ausencia is None or ausencia.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        if ausencia.id_user != actor_id:
            raise AppError("errors.permission_denied", 403, {"entity": "employee_leave", "action": "update"})
        if ausencia.leave_status != SOLICITADA:
            raise AppError("errors.employee_leave_not_pending", 409, {"leave_status": ausencia.leave_status})
        ausencia.leave_status = CANCELADA
        return ausencia.serialize()


def por_autorizar(user_data: dict) -> list[dict]:
    """Solicitudes pendientes que el actor puede revisar: las de su equipo, o todas si es RH."""
    actor_id = user_data.get("id_user")
    with transaction_context() as db:
        consulta = (select(EmployeeLeave)
                    .where(EmployeeLeave.leave_status == SOLICITADA)
                    .where(EmployeeLeave.deletion_date.is_(None))
                    .order_by(EmployeeLeave.start_date))
        if not _es_rh(user_data):
            equipo = select(User.id_user).where(User.supervisor == actor_id).where(User.id_user != actor_id)
            consulta = consulta.where(EmployeeLeave.id_user.in_(equipo))
        pendientes = db.scalars(consulta).all()
        filas = _con_nombre(db, pendientes)
        empleados = {u.id_user: u for u in db.scalars(select(User).where(User.id_user.in_([a.id_user for a in pendientes] or [0])))}
        hoy = ahora_negocio().date()
        saldos_de = {s["id_user"]: s for s in _saldos(db, list(empleados.values()), hoy)}
        for fila in filas:
            fila["available"] = (saldos_de.get(fila["id_user"]) or {}).get("available", 0)
        return filas


def revisar(user_data: dict, id_ausencia, aprobar: bool, nota=None) -> dict:
    """Aprueba o rechaza una solicitud pendiente. Puede su supervisor o RH, nunca el propio empleado."""
    actor_id = user_data.get("id_user")
    if nota is not None and len(str(nota)) > 300:
        raise AppError("errors.invalid_field", 400, {"field": "review_note"})
    with transaction_context() as db:
        ausencia = db.get(EmployeeLeave, _entero(id_ausencia, "id_employee_leave"))
        if ausencia is None or ausencia.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        empleado = db.get(User, ausencia.id_user)
        es_rh = _es_rh(user_data)
        propia = ausencia.id_user == actor_id
        if not es_rh and (propia or empleado.supervisor != actor_id):
            raise AppError("errors.permission_denied", 403, {"entity": "employee_leave", "action": "update"})
        if ausencia.leave_status != SOLICITADA:
            raise AppError("errors.employee_leave_not_pending", 409, {"leave_status": ausencia.leave_status})
        datos = {"id_user": ausencia.id_user, "leave_type": ausencia.leave_type, "start_date": ausencia.start_date,
                 "end_date": ausencia.end_date, "notes": ausencia.notes}
    if aprobar:
        # Desde que se pidio pudo cambiar el saldo, otra ausencia o el cierre de un periodo.
        EmployeeLeaveService._validar(datos, excluir_id=id_ausencia)
    with transaction_context() as db:
        ausencia = db.get(EmployeeLeave, int(id_ausencia))
        ausencia.leave_status = APROBADA if aprobar else RECHAZADA
        ausencia.reviewed_by = actor_id
        ausencia.reviewed_at = ahora_utc()
        ausencia.review_note = (str(nota).strip() or None) if nota is not None else None
        resultado = ausencia.serialize()
    _notificar(resultado["id_user"], notification_type="leave_reviewed",
               titulo="Tu solicitud fue aprobada" if aprobar else "Tu solicitud fue rechazada",
               mensaje=f"Del {resultado['start_date']} al {resultado['end_date']}."
               + (f" Nota: {resultado['review_note']}" if resultado["review_note"] else ""),
               actor_id=actor_id, id_ausencia=resultado["id_employee_leave"])
    return resultado
