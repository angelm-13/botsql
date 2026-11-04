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
(solicitados). Los dias de cada año salen de la tabla de la empresa si la hay
(Ajustes de nomina), nunca menos que la ley. Como se ganan (al aniversario o mes
a mes), si se pueden adelantar, cuanto duran y que pasa con lo no usado lo decide
la politica de la empresa (services/politica_de_vacaciones.py); sin capturarla,
lo no usado del año anterior no se acumula (decision de RH, 2026-10-21; la
revision contable confirma que es valido si esta en el contrato firmado).

Solicitudes (decisiones de RH, 2026-10-22): el empleado pide vacaciones o un
permiso; lo aprueba o rechaza su supervisor (`user.supervisor`) o RH (permiso de
editar `employee_leave`). Desde la revision contable (2026-10-28) tambien reporta
su incapacidad con la hoja del IMSS, y esa solo la revisa RH. Lo que registra RH
directamente queda aprobado. Al aprobar se vuelven a validar saldo, que no se
enciman y que no caigan en un periodo cerrado.

Dos pasos (decision de RH, 2026-11-04): primero la aprueba su jefe directo y
queda boss_approved ("pendiente de RH"); despues RH la aprueba o la rechaza, y
solo entonces cuenta. Sin jefe directo, o si es una incapacidad, va directo a RH.
Si su jefe tambien es RH, su aprobacion cierra los dos pasos.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import EmployeeLeave, EntityPermission, PayrollPeriod, User
from app.models.employee_leave import (APROBADA, CANCELADA, ESTADOS_PENDIENTES, ESTADOS_VIGENTES, JEFE_APROBO,
                                       RECHAZADA, SOLICITADA, TIPOS_DE_AUSENCIA, TIPOS_DE_INCAPACIDAD)
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError
from app.utils.tiempo import ahora_negocio, ahora_utc

VACACIONES = "vacation"
# El empleado tambien reporta su incapacidad (y sube la hoja del IMSS); solo
# cuenta cuando RH la aprueba, y solo RH la revisa: el supervisor no ve la hoja.
TIPOS_QUE_PIDE_EL_EMPLEADO = ("vacation", "paid_leave", "unpaid_leave", "disability")
# Columnas que solo mueve el flujo de solicitud; la captura generica no las escribe.
CAMPOS_DEL_FLUJO = ("leave_status", "requested_by", "reviewed_by", "reviewed_at", "review_note",
                    "boss_reviewed_by", "boss_reviewed_at", "boss_review_note")


def _aniversario(ingreso: date, anios: int) -> date:
    try:
        return ingreso.replace(year=ingreso.year + anios)
    except ValueError:  # 29 de febrero en un año no bisiesto
        return date(ingreso.year + anios, 2, 28)


def ano_de_servicio(ingreso: date, al_dia: date) -> tuple[int, date, date]:
    """(años cumplidos, inicio y fin del año de servicio en curso) `al_dia`."""
    anios = ley.anios_cumplidos(ingreso, al_dia)
    return anios, _aniversario(ingreso, anios), _aniversario(ingreso, anios + 1) - timedelta(days=1)


def _dias_de_vacaciones(db, rangos: dict, excluir_id=None) -> dict[int, list[tuple[date, bool]]]:
    """{id_user: [(dia laborable de vacaciones, aprobada)]} dentro del rango (desde, hasta) de cada uno.

    Antes se leia el calendario completo (horarios, festivos y checadas) una vez
    por cada ausencia de cada empleado: cientos de consultas para todo el saldo.
    Ahora se leen las vacaciones de todos y el calendario sin checadas, una vez.
    """
    dias = {id_user: [] for id_user in rangos}
    if not rangos:
        return dias
    desde, hasta = min(v[0] for v in rangos.values()), max(v[1] for v in rangos.values())
    tramos = []
    for v in db.scalars(select(EmployeeLeave)
                        .where(EmployeeLeave.id_user.in_(list(rangos)))
                        .where(EmployeeLeave.leave_type == VACACIONES)
                        .where(EmployeeLeave.leave_status.in_(ESTADOS_VIGENTES))
                        .where(EmployeeLeave.deletion_date.is_(None))
                        .where(EmployeeLeave.start_date <= hasta)
                        .where(EmployeeLeave.end_date >= desde)):
        inicio, fin = rangos[v.id_user]
        if (excluir_id is not None and str(v.id_employee_leave) == str(excluir_id))                 or v.start_date > fin or v.end_date < inicio:
            continue
        tramos.append((v.id_user, max(v.start_date, inicio), min(v.end_date, fin), v.leave_status == APROBADA))
    if not tramos:
        return dias
    from app.services.attendance_record_service import asistencia_por_empleado
    calendario = asistencia_por_empleado(db, min(t[1] for t in tramos), max(t[2] for t in tramos),
                                         ids=sorted({t[0] for t in tramos}), con_checadas=False)
    for id_user, inicio, fin, aprobada in tramos:
        dias[id_user] += [(d.fecha, aprobada) for d in calendario.get(id_user, []) if d.laboral and inicio <= d.fecha <= fin]
    return dias


def _bloques_y_rango(empleado: User, al_dia: date, tabla: dict, pol: dict):
    """(bloques, (desde, hasta) de las vacaciones que cuentan, (años, inicio, fin) del año de servicio)."""
    from app.services import politica_de_vacaciones as pv
    anios, inicio, fin = ano_de_servicio(empleado.hire_date, al_dia)
    lista = pv.bloques(empleado.hire_date, fin, tabla, pol)
    # Las vacaciones que pueden caer en un bloque todavia vigente: desde que empezo a
    # ganarse el mas viejo de ellos hasta el fin del año de servicio en curso.
    desde = min((b.desde for b in lista if b.vigente(al_dia)), default=inicio)
    return lista, (desde, fin), (anios, inicio, fin)


def _saldos(db, empleados, al_dia: date, excluir_id=None) -> list[dict]:
    from app.services import politica_de_vacaciones as pv
    from app.services.payroll_calculation_service import tabla_de_vacaciones
    pol = pv.politica(db, al_dia)
    tabla = tabla_de_vacaciones(db, al_dia)
    datos, rangos = [], {}
    for empleado in empleados:
        if not empleado.hire_date or empleado.hire_date > al_dia:
            datos.append((empleado, None))
            continue
        lista, rango, ano = _bloques_y_rango(empleado, al_dia, tabla, pol)
        rangos[empleado.id_user] = rango
        datos.append((empleado, (lista, ano)))
    dias = _dias_de_vacaciones(db, rangos, excluir_id)
    salida = []
    for empleado, calculo in datos:
        if calculo is None:
            salida.append({"id_user": empleado.id_user, "full_name": empleado.full_name or "", "hire_date": None,
                           "service_years": 0, "entitled": 0, "taken": 0, "pending": 0, "available": 0,
                           "advanced": 0, "can_advance": 0, "expiring": [], "monthly_accrual": bool(pol[pv.MENSUAL]),
                           "year_start": None, "year_end": None})
            continue
        lista, (anios, inicio, fin) = calculo
        tomados = dias.get(empleado.id_user, [])
        pv.cargar(lista, [d for d, _ in tomados], pol[pv.ADELANTO])
        saldo = pv.resumen(lista, al_dia, pol[pv.ADELANTO])
        en_el_ano = [aprobada for d, aprobada in tomados if inicio <= d <= fin]
        salida.append({"id_user": empleado.id_user, "full_name": empleado.full_name or "",
                       "hire_date": empleado.hire_date.isoformat(), "service_years": anios,
                       "entitled": saldo["earned"], "taken": sum(en_el_ano), "pending": len(en_el_ano) - sum(en_el_ano),
                       "available": saldo["available"], "advanced": saldo["advanced"],
                       "can_advance": saldo["can_advance"], "expiring": saldo["expiring"],
                       "monthly_accrual": bool(pol[pv.MENSUAL]),
                       "year_start": inicio.isoformat(), "year_end": fin.isoformat()})
    return salida


def vacaciones_no_usadas_que_vencen(db, empleados, desde: date, hasta: date) -> dict[int, int]:
    """{id_user: dias} de vacaciones sin usar cuyo plazo vence entre `desde` y
    `hasta`, si la politica vigente a `hasta` es pagarlas (las paga la nomina)."""
    from app.services import politica_de_vacaciones as pv
    from app.services.payroll_calculation_service import tabla_de_vacaciones
    pol = pv.politica(db, hasta)
    if pol[pv.NO_USADOS] != pv.SE_PAGAN:
        return {}
    tabla = tabla_de_vacaciones(db, hasta)
    listas, rangos = {}, {}
    for empleado in empleados:
        if not empleado.hire_date or empleado.hire_date > hasta:
            continue
        lista = pv.bloques(empleado.hire_date, hasta, tabla, pol)
        vencen = [b for b in lista if b.vence and desde <= b.vence <= hasta]
        if not vencen:
            continue
        # Las vacaciones que pudieron cargarse a esos bloques: desde que empezo a
        # ganarse el mas viejo vigente un dia antes del primer vencimiento.
        antes = min(b.vence for b in vencen) - timedelta(days=1)
        listas[empleado.id_user] = lista
        rangos[empleado.id_user] = (min(b.desde for b in lista if b.vigente(antes)), hasta)
    dias = _dias_de_vacaciones(db, rangos)
    salida = {}
    for id_user, lista in listas.items():
        pv.cargar(lista, [d for d, _ in dias.get(id_user, [])], pol[pv.ADELANTO])
        no_usados = sum(n for _, n in pv.no_usados_que_vencen(lista, desde, hasta))
        if no_usados:
            salida[id_user] = no_usados
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


def _con_tipo_de_incapacidad(payload: dict, actual: dict | None = None) -> dict:
    """El tipo de incapacidad solo lo lleva una incapacidad; vacio = sin capturar."""
    payload = dict(payload)
    tipo = payload.get("leave_type", (actual or {}).get("leave_type"))
    if payload.get("disability_type") == "":
        payload["disability_type"] = None
    if tipo != "disability" and (payload.get("disability_type") or (actual or {}).get("disability_type")):
        payload["disability_type"] = None
    return payload


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
        if datos.get("disability_type") not in (None, *TIPOS_DE_INCAPACIDAD):
            raise AppError("errors.invalid_field", 400, {"field": "disability_type",
                                                         "allowed": list(TIPOS_DE_INCAPACIDAD)})
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
        from app.services import politica_de_vacaciones as pv
        from app.services.payroll_calculation_service import tabla_de_vacaciones
        if not empleado.hire_date:
            raise AppError("errors.employee_leave_no_hire_date", 409, {"id_user": empleado.id_user})
        pol = pv.politica(db, desde)
        anios, _, fin = ano_de_servicio(empleado.hire_date, desde)
        # El primer año no hay vacaciones, salvo que la empresa las de mes a mes o permita adelantar.
        if empleado.hire_date > desde or (anios < 1 and not pol[pv.MENSUAL] and not pol[pv.ADELANTO]):
            raise AppError("errors.employee_leave_first_year", 409, {
                "first_anniversary": _aniversario(empleado.hire_date, 1).isoformat()})
        if hasta > fin:
            raise AppError("errors.employee_leave_crosses_anniversary", 409, {
                "anniversary": (fin + timedelta(days=1)).isoformat()})
        from app.services.attendance_record_service import asistencia_por_empleado
        calendario = asistencia_por_empleado(db, desde, hasta, ids=[empleado.id_user], con_checadas=False)
        dias = calendario.get(empleado.id_user, [])
        if not dias or not all(d.con_horario for d in dias):
            raise AppError("errors.employee_leave_needs_schedule", 409, {"id_user": empleado.id_user})
        pedidos = [d.fecha for d in dias if d.laboral]
        if not pedidos:
            raise AppError("errors.employee_leave_no_workdays", 400, {"field": "start_date"})
        # Se cargan a los bloques con y sin lo pedido: si lo pedido deja dias sin
        # cubrir (ni con el adelanto permitido), no alcanza.
        tabla = tabla_de_vacaciones(db, desde)
        lista, rango, _ = _bloques_y_rango(empleado, desde, tabla, pol)
        tomados = [d for d, _ in _dias_de_vacaciones(db, {empleado.id_user: rango}, excluir_id)[empleado.id_user]]
        sin_cubrir = pv.cargar(lista, tomados, pol[pv.ADELANTO])
        con_lo_pedido, _, _ = _bloques_y_rango(empleado, desde, tabla, pol)
        if pv.cargar(con_lo_pedido, tomados + pedidos, pol[pv.ADELANTO]) > sin_cubrir:
            saldo = pv.resumen(lista, desde, pol[pv.ADELANTO])
            raise AppError("errors.employee_leave_insufficient_balance", 409, {
                "available": saldo["available"], "requested": len(pedidos), "entitled": saldo["earned"],
                "can_advance": saldo["can_advance"]})

    @classmethod
    def _actual(cls, item_id) -> dict:
        actual = cls.get(item_id)
        if actual is None:
            raise AppError("errors.resource_not_found", 404)
        return actual

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        # Lo que registra RH queda aprobado de una vez; el estado no se escribe a mano.
        payload = _con_tipo_de_incapacidad(
            {k: v for k, v in dict(payload or {}).items() if k not in CAMPOS_DEL_FLUJO})
        cls._validar(payload)
        payload.update(leave_status=APROBADA, reviewed_by=user_id, reviewed_at=ahora_utc())
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = {k: v for k, v in dict(payload or {}).items() if k not in CAMPOS_DEL_FLUJO}
        actual = cls._actual(item_id)
        payload = _con_tipo_de_incapacidad(payload, actual)
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


def _jefe_directo(db, empleado: User) -> int | None:
    """Quien aprueba primero; None si no tiene jefe (o es el mismo, o ya no existe)."""
    if not empleado.supervisor or empleado.supervisor == empleado.id_user:
        return None
    jefe = db.get(User, empleado.supervisor)
    return jefe.id_user if jefe is not None and jefe.deletion_date is None else None


def _ausente(db, id_user: int, dia: date) -> bool:
    """Si tiene una ausencia ya aprobada que cubre ese dia (vacaciones, permiso o incapacidad)."""
    return db.scalar(select(EmployeeLeave.id_employee_leave)
                     .where(EmployeeLeave.id_user == id_user).where(EmployeeLeave.leave_status == APROBADA)
                     .where(EmployeeLeave.deletion_date.is_(None))
                     .where(EmployeeLeave.start_date <= dia).where(EmployeeLeave.end_date >= dia)
                     .limit(1)) is not None


def _aprueban_primero(db, empleado: User, hoy: date | None = None) -> tuple[set[int], bool]:
    """(quienes pueden dar el primer paso, si su jefe esta ausente).

    Su jefe directo; si hoy esta de vacaciones o con permiso, tambien el jefe de su
    jefe como suplente (decision de RH, 2026-11-04). Si el jefe esta ausente y no
    hay a quien suplir, el primer paso se salta y la solicitud va directo a RH.
    Vacio = sin jefe: va directo a RH.
    """
    jefe = _jefe_directo(db, empleado)
    if jefe is None:
        return set(), False
    if not _ausente(db, jefe, hoy or ahora_negocio().date()):
        return {jefe}, False
    suplente = _jefe_directo(db, db.get(User, jefe))
    if suplente is None or suplente == empleado.id_user:
        return set(), True
    return {jefe, suplente}, True


def _paso(db, ausencia: EmployeeLeave, empleado: User) -> str:
    """'boss' si le toca a su jefe directo (o a su suplente), 'hr' si ya le toca a RH."""
    if ausencia.leave_status == SOLICITADA and ausencia.leave_type != "disability" \
            and _aprueban_primero(db, empleado)[0]:
        return "boss"
    return "hr"


def _equipo_ausente(db, empleado: User, desde: date, hasta: date, sin_id: int) -> tuple[list[dict], int]:
    """Quienes de su equipo (el mismo jefe directo) faltan en esas fechas, y cuantos
    son en el equipo: RH lo ve antes de aprobar para que el area no se quede sin gente."""
    jefe = _jefe_directo(db, empleado)
    if jefe is None:
        return [], 0
    equipo = {u.id_user: u for u in db.scalars(select(User).where(User.supervisor == jefe)
                                               .where(User.deletion_date.is_(None))
                                               .where(User.is_employee.is_(True)))}
    otros = db.scalars(select(EmployeeLeave)
                       .where(EmployeeLeave.id_user.in_([i for i in equipo if i != empleado.id_user] or [0]))
                       .where(EmployeeLeave.leave_status.in_(ESTADOS_VIGENTES))
                       .where(EmployeeLeave.id_employee_leave != sin_id)
                       .where(EmployeeLeave.deletion_date.is_(None))
                       .where(EmployeeLeave.start_date <= hasta).where(EmployeeLeave.end_date >= desde)
                       .order_by(EmployeeLeave.start_date)).all()
    return [{"id_user": a.id_user, "full_name": equipo[a.id_user].full_name or f"#{a.id_user}",
             "start_date": a.start_date.isoformat(), "end_date": a.end_date.isoformat(),
             "leave_type": a.leave_type, "leave_status": a.leave_status} for a in otros], len(equipo)


def _usuarios_de_rh(db) -> list[int]:
    """Quienes revisan ausencias en el Gestor (editar employee_leave), para avisarles."""
    roles = (select(EntityPermission.id_permission).where(EntityPermission.entity_name == "employee_leave")
             .where(EntityPermission.scope_update != 0).where(EntityPermission.deletion_date.is_(None)))
    return list(db.scalars(select(User.id_user).where(User.id_permission.in_(roles))
                           .where(User.deletion_date.is_(None))))


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


def avisar_vacaciones_por_vencer(hoy: date | None = None) -> int:
    """Avisa (campana) al empleado y a su supervisor cuando le quedan dias de
    vacaciones que vencen justo dentro de los dias de aviso de la politica (60 y
    30 por omision). Lo corre el job diario de RH; como solo avisa el dia exacto,
    cada aviso sale una sola vez. Devuelve cuantos avisos mando."""
    from app.services import politica_de_vacaciones as pv
    from app.services.notification_service import create_notification
    hoy = hoy or ahora_negocio().date()
    with transaction_context() as db:
        pol = pv.politica(db, hoy)
        avisos_en = {pol[pv.AVISO_1], pol[pv.AVISO_2]} - {0}
        if not avisos_en or pol[pv.NO_USADOS] == pv.SE_ACUMULAN:
            return 0
        empleados = db.scalars(select(User).where(User.deletion_date.is_(None))
                               .where(User.is_employee.is_(True))).all()
        jefes = {e.id_user: e.supervisor for e in empleados}
        pendientes = []
        for saldo in _saldos(db, empleados, hoy):
            for bloque in saldo["expiring"]:
                faltan = (date.fromisoformat(bloque["expires_on"]) - hoy).days
                if faltan in avisos_en:
                    pendientes.append((saldo, bloque, faltan))
    enviados = 0
    for saldo, bloque, faltan in pendientes:
        que = "pagan" if pol[pv.NO_USADOS] == pv.SE_PAGAN else "pierden"
        mensaje = (f"{saldo['full_name']} tiene {bloque['days']} días de vacaciones que vencen el "
                   f"{bloque['expires_on']} (en {faltan} días). Si no se toman, se {que}.")
        for destinatario in {saldo["id_user"], jefes.get(saldo["id_user"])} - {None}:
            try:
                # created_by es llave a user: sin el, Postgres rechaza el aviso (SQLite no lo
                # revisa). Lo escribe el sistema; queda a nombre de quien lo recibe, como el
                # aviso de vales vencidos.
                create_notification(id_user_recipient=destinatario, notification_type="vacation_expiring",
                                    title="Vacaciones por vencer", message=mensaje, created_by=destinatario,
                                    target_entity="employee_leave", target_id=None)
                enviados += 1
            except Exception:
                pass
    return enviados


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
    datos = _con_tipo_de_incapacidad({
        "id_user": actor_id, "leave_type": payload["leave_type"], "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"), "notes": payload.get("notes") or None,
        "disability_type": payload.get("disability_type")})
    EmployeeLeaveService._validar(datos)
    with transaction_context() as db:
        empleado = db.get(User, actor_id)
        ausencia = EmployeeLeave(**{**datos, "start_date": _fecha(datos["start_date"], "start_date"),
                                    "end_date": _fecha(datos["end_date"], "end_date")},
                                 leave_status=SOLICITADA, requested_by=actor_id, created_by=actor_id)
        db.add(ausencia)
        db.flush()
        resultado = ausencia.serialize()
        if datos["leave_type"] == "disability":
            # La incapacidad la revisa RH, pero su jefe tambien debe saberlo.
            destinatarios = set(_usuarios_de_rh(db)) | ({_jefe_directo(db, empleado)} - {None})
        else:
            destinatarios = _aprueban_primero(db, empleado)[0] or set(_usuarios_de_rh(db))
    for destinatario in sorted(destinatarios):
        _notificar(destinatario, notification_type="leave_requested", titulo="Solicitud de ausencia por autorizar",
                   mensaje=f"{empleado.full_name} {'reportó una incapacidad' if resultado['leave_type'] == 'disability' else 'pidió'}"
                           f" del {resultado['start_date']} al {resultado['end_date']}.",
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
        if ausencia.leave_status not in ESTADOS_PENDIENTES:
            raise AppError("errors.employee_leave_not_pending", 409, {"leave_status": ausencia.leave_status})
        ausencia.leave_status = CANCELADA
        return ausencia.serialize()


def por_autorizar(user_data: dict) -> list[dict]:
    """Solicitudes que le toca revisar al actor: como jefe directo, las de su equipo
    en su primer paso; como RH, las que ya aprobo su jefe, las de quien no tiene
    jefe y las incapacidades. Cada fila dice su paso (`step`: boss o hr)."""
    actor_id = user_data.get("id_user")
    es_rh = _es_rh(user_data)
    with transaction_context() as db:
        todas = db.scalars(select(EmployeeLeave)
                           .where(EmployeeLeave.leave_status.in_(ESTADOS_PENDIENTES))
                           .where(EmployeeLeave.deletion_date.is_(None))
                           .order_by(EmployeeLeave.start_date)).all()
        empleados = {u.id_user: u for u in db.scalars(select(User).where(User.id_user.in_([a.id_user for a in todas] or [0])))}
        primeros = {a.id_employee_leave: _aprueban_primero(db, empleados[a.id_user]) for a in todas}
        pasos = {a.id_employee_leave: _paso(db, a, empleados[a.id_user]) for a in todas}
        pendientes = [a for a in todas
                      if (pasos[a.id_employee_leave] == "boss" and a.id_user != actor_id
                          and actor_id in primeros[a.id_employee_leave][0])
                      or (pasos[a.id_employee_leave] == "hr" and es_rh)]
        filas = _con_nombre(db, pendientes)
        hoy = ahora_negocio().date()
        saldos_de = {s["id_user"]: s for s in _saldos(db, [empleados[a.id_user] for a in pendientes], hoy)}
        for fila in filas:
            fila["available"] = (saldos_de.get(fila["id_user"]) or {}).get("available", 0)
            fila["step"] = pasos[fila["id_employee_leave"]]
            # Su jefe directo esta ausente: aprueba el suplente (el jefe de su jefe).
            fila["boss_absent"] = primeros[fila["id_employee_leave"]][1]
            ausencia = next(a for a in pendientes if a.id_employee_leave == fila["id_employee_leave"])
            fila["team_off"], fila["team_size"] = _equipo_ausente(
                db, empleados[fila["id_user"]], ausencia.start_date, ausencia.end_date, ausencia.id_employee_leave)
        return filas


def revisar(user_data: dict, id_ausencia, aprobar: bool, nota=None) -> dict:
    """Aprueba o rechaza una solicitud pendiente en el paso que le toca: su jefe
    directo primero y RH despues (ver el docstring del modulo)."""
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
        if ausencia.leave_status not in ESTADOS_PENDIENTES:
            raise AppError("errors.employee_leave_not_pending", 409, {"leave_status": ausencia.leave_status})
        paso = _paso(db, ausencia, empleado)
        if paso == "boss" and (propia or actor_id not in _aprueban_primero(db, empleado)[0]):
            if es_rh:
                raise AppError("errors.employee_leave_waiting_boss", 409, {"leave_status": ausencia.leave_status})
            raise AppError("errors.permission_denied", 403, {"entity": "employee_leave", "action": "update"})
        if paso == "hr" and not es_rh:
            raise AppError("errors.permission_denied", 403, {"entity": "employee_leave", "action": "update"})
        # El jefe que tambien es RH cierra los dos pasos de una vez.
        final = paso == "hr" or es_rh
        nombre = empleado.full_name or f"#{empleado.id_user}"
        datos = {"id_user": ausencia.id_user, "leave_type": ausencia.leave_type, "start_date": ausencia.start_date,
                 "end_date": ausencia.end_date, "notes": ausencia.notes, "disability_type": ausencia.disability_type}
    if aprobar:
        # Desde que se pidio pudo cambiar el saldo, otra ausencia o el cierre de un periodo.
        EmployeeLeaveService._validar(datos, excluir_id=id_ausencia)
    nota = (str(nota).strip() or None) if nota is not None else None
    with transaction_context() as db:
        ausencia = db.get(EmployeeLeave, int(id_ausencia))
        ahora = ahora_utc()
        if paso == "boss":
            ausencia.boss_reviewed_by, ausencia.boss_reviewed_at, ausencia.boss_review_note = actor_id, ahora, nota
        if final or not aprobar:
            ausencia.leave_status = APROBADA if aprobar else RECHAZADA
            ausencia.reviewed_by, ausencia.reviewed_at, ausencia.review_note = actor_id, ahora, nota
        else:
            ausencia.leave_status = JEFE_APROBO
        resultado = ausencia.serialize()
        rh = _usuarios_de_rh(db) if resultado["leave_status"] == JEFE_APROBO else []
    periodo = f"Del {resultado['start_date']} al {resultado['end_date']}."
    if resultado["leave_status"] == JEFE_APROBO:
        for destinatario in rh:
            _notificar(destinatario, notification_type="leave_requested", titulo="Solicitud por autorizar (RH)",
                       mensaje=f"Su jefe aprobó la solicitud de {nombre}. {periodo}",
                       actor_id=actor_id, id_ausencia=resultado["id_employee_leave"])
        _notificar(resultado["id_user"], notification_type="leave_reviewed", titulo="Tu jefe aprobó tu solicitud",
                   mensaje=f"{periodo} Falta la aprobación de RH.", actor_id=actor_id,
                   id_ausencia=resultado["id_employee_leave"])
        return resultado
    _notificar(resultado["id_user"], notification_type="leave_reviewed",
               titulo="Tu solicitud fue aprobada" if aprobar else "Tu solicitud fue rechazada",
               mensaje=periodo + (f" Nota: {nota}" if nota else ""),
               actor_id=actor_id, id_ausencia=resultado["id_employee_leave"])
    return resultado
