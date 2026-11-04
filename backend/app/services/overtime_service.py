"""Horas extra (revision contable, Etapa C; decisiones de RH 2026-10-30).

Como entran
-----------
* Autorizadas antes por el supervisor del empleado o RH (`authorized`).
* Tiempo no autorizado: lo que alguien se quedo despues de su salida segun
  sus checadas, pasada la tolerancia (`overtime_tolerance_minutes`, 15). No se
  paga solo: el supervisor o RH lo aprueba como horas extra (`detected`).
* Capturadas a mano por RH, con motivo, cuando no hay checadas (`manual`).
El empleado no las pide. Cada registro guarda quien y el comentario.

Que se paga
-----------
Lo autorizado con tope en lo que marcan las checadas ese dia (de la hora de
salida de su horario a su ultima checada): autorizar no es pagar a ciegas. Si la
salida esta mal checada, RH la corrige (attendance_correction_service) y se
paga lo real. Las manuales se pagan como se capturaron. Estado de cada
registro: verified, partial, not_worked o manual. Las de `compensate` (tiempo
libre) se verifican igual pero no se pagan: queda el comentario.

Cuanto (LFT arts. 67 y 68)
--------------------------
Hora = salario diario / horas de su jornada ese dia (entrada a salida menos
los minutos de comida del horario; sin horario, `overtime_day_hours`, 8). Las
primeras 9 horas de la semana (lunes a domingo) se pagan dobles; las demas,
triples.

ISR (LISR art. 93 fr. I)
------------------------
Quien gana el salario minimo: lo doble no grava. Los demas: la mitad de lo
doble no grava, con tope de 5 UMA por semana. Lo triple grava completo.

Descanso o festivo trabajado (LFT arts. 73 y 75)
------------------------------------------------
Mismo registro con `kind` = rest_day y el mismo flujo de autorizacion: si
checo en su dia de descanso o en un festivo y nadie lo autorizo, aparece como
"descanso trabajado sin autorizar". Verificado = checo ese dia. Se paga el
doble de su diario ademas del dia (que ya se paga). Exento igual que lo doble
de las horas extra y en la misma bolsa semanal de 5 UMA (LISR art. 93 fr. I);
no cuenta para las 9 horas dobles.

Cuando
------
En el periodo donde cae el dia, o en el siguiente que se calcule si se aprobo
despues de cerrar aquel (nunca dos veces: al cerrar, cada registro queda con
el periodo que lo pago; al reabrir se libera).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import EmployeeSchedule, Overtime, User, WorkSchedule, WorkScheduleDay
from app.models.overtime import (AUTORIZADA, COMPENSAR, CONFIRMADA, DESCANSO, DETECTADA, HORA_EXTRA, MANUAL, PAGAR,
                                 PENDIENTE_RH, RECHAZADA)
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.utils.errors import AppError

TOLERANCIA = "overtime_tolerance_minutes"
JORNADA = "overtime_day_hours"
# clave -> (valor por omision, valores permitidos), igual que las demas politicas.
PRIMA_DOMINICAL = "sunday_premium_pct"
POLITICA_DE_HORAS_EXTRA = {TOLERANCIA: (15, range(0, 241)), JORNADA: (8, range(1, 13)),
                           PRIMA_DOMINICAL: (25, range(25, 101))}
LIMITE_DOBLES = 9 * 60   # minutos dobles por semana (LFT art. 68)
UMAS_EXENTAS_POR_SEMANA = 5


def _politica(db, al_dia) -> dict:
    from app.services.payroll_calculation_service import _vigentes
    capturados = _vigentes(db, tuple(POLITICA_DE_HORAS_EXTRA), al_dia)
    return {clave: int(capturados.get(clave, defecto)) for clave, (defecto, _) in POLITICA_DE_HORAS_EXTRA.items()}


def _minutos_de_jornada(db, ids, desde: date, hasta: date) -> dict:
    """{(id_user, dia): minutos de la jornada de su horario} (entrada a salida menos comida)."""
    asignaciones = db.scalars(select(EmployeeSchedule)
                              .where(EmployeeSchedule.id_user.in_(list(ids) or [0]))
                              .where(EmployeeSchedule.deletion_date.is_(None))
                              .where(EmployeeSchedule.valid_from <= hasta)
                              .where((EmployeeSchedule.valid_to.is_(None)) | (EmployeeSchedule.valid_to >= desde))).all()
    horarios = {h.id_work_schedule: h for h in db.scalars(select(WorkSchedule))}
    dias = defaultdict(dict)
    for d in db.scalars(select(WorkScheduleDay).where(WorkScheduleDay.deletion_date.is_(None))):
        dias[d.id_work_schedule][d.weekday] = (d.start_time, d.end_time)
    salida = {}
    dia = desde
    while dia <= hasta:
        for a in asignaciones:
            if a.valid_from <= dia and (a.valid_to is None or a.valid_to >= dia) and dia.weekday() in dias[a.id_work_schedule]:
                inicio, fin = dias[a.id_work_schedule][dia.weekday()]
                bruto = (datetime.combine(dia, fin) - datetime.combine(dia, inicio)).seconds // 60
                salida[(a.id_user, dia)] = max(bruto - (horarios[a.id_work_schedule].meal_minutes or 0), 60)
        dia += timedelta(days=1)
    return salida


def _lo_checado(db, ids, desde: date, hasta: date) -> tuple[dict, dict]:
    """({(id_user, dia): minutos despues de su hora de salida segun su ultima checada},
        {(id_user, dia): es_festivo} de los dias de descanso o festivos en que checo)."""
    from app.services.attendance_record_service import asistencia_por_empleado
    extra, descansos = {}, {}
    for id_user, lista in asistencia_por_empleado(db, desde, hasta, ids=list(ids)).items():
        for d in lista:
            if d.laboral and d.salida and len(d.marcas) >= 2:
                minutos = int((datetime.combine(d.fecha, d.marcas[-1]) - datetime.combine(d.fecha, d.salida))
                              .total_seconds() // 60)
                extra[(id_user, d.fecha)] = max(minutos, 0)
            if d.trabajo_en_descanso and d.ausencia is None:
                descansos[(id_user, d.fecha)] = d.festivo
    return extra, descansos


def _verificar(registros, extra: dict, descansos: dict) -> dict:
    """{id_overtime: (minutos pagables, estado)}. Las de un mismo dia comparten lo checado.
    Un descanso trabajado esta verificado si checo ese dia."""
    salida, restante = {}, dict(extra)
    for r in sorted(registros, key=lambda r: (r.work_date, r.id_overtime)):
        if r.origin == MANUAL:
            salida[r.id_overtime] = (r.minutes, "manual")
            continue
        if r.kind == DESCANSO:
            trabajado = (r.id_user, r.work_date) in descansos
            salida[r.id_overtime] = (r.minutes if trabajado else 0, "verified" if trabajado else "not_worked")
            continue
        clave = (r.id_user, r.work_date)
        pagables = min(r.minutes, restante.get(clave, 0))
        restante[clave] = restante.get(clave, 0) - pagables
        estado = "verified" if pagables == r.minutes else "partial" if pagables else "not_worked"
        salida[r.id_overtime] = (pagables, estado)
    return salida


def _semana(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def _registros(db, ids, desde: date, hasta: date):
    return db.scalars(select(Overtime).where(Overtime.id_user.in_(list(ids) or [0]))
                      .where(Overtime.deletion_date.is_(None))
                      .where(Overtime.work_date >= desde).where(Overtime.work_date <= hasta)).all()


def horas_extra_del_periodo(db, empleados, periodo, parametros, diarios=None, horas=None) -> dict:
    """{id_user: {double_minutes, triple_minutes, amount, taxable, ids}} de lo que paga este periodo.

    Entran las horas extra a pagar con dia hasta el fin del periodo que no pago
    otro periodo cerrado. Dobles y triples se cuentan por semana con TODAS las
    pagadas de esa semana, aunque otra parte se haya pagado en otro periodo.
    `diarios`: diario equivalente de cada uno (salary_service); `horas`: la hora
    de quien gana por hora. Sin ellos, `user.base_salary` / su jornada.
    """
    ids = [e.id_user for e in empleados]
    if not ids:
        return {}
    candidatas = [r for r in db.scalars(
        select(Overtime).where(Overtime.id_user.in_(ids)).where(Overtime.deletion_date.is_(None))
        .where(Overtime.settlement == PAGAR).where(Overtime.approval_status == CONFIRMADA)
        .where(Overtime.work_date <= periodo.period_end)
        .where((Overtime.id_payroll_period.is_(None)) | (Overtime.id_payroll_period == periodo.id_payroll_period)))]
    if not candidatas:
        return {}
    desde = _semana(min(r.work_date for r in candidatas))
    hasta = max(_semana(max(r.work_date for r in candidatas)) + timedelta(days=6), periodo.period_end)
    todas = [r for r in _registros(db, ids, desde, hasta) if r.settlement == PAGAR and r.approval_status == CONFIRMADA]
    pagables = _verificar(todas, *_lo_checado(db, ids, desde, hasta))
    jornada = _minutos_de_jornada(db, ids, desde, hasta)
    politica = _politica(db, periodo.period_end)
    diarios = diarios or {e.id_user: Decimal(str(e.base_salary or 0)) for e in empleados}
    horas = horas or {}
    de_este = {r.id_overtime for r in candidatas}
    resultado = {}
    por_semana = defaultdict(list)
    for r in sorted(todas, key=lambda r: (r.work_date, r.id_overtime)):
        por_semana[(r.id_user, _semana(r.work_date))].append(r)
    uma, minimo = Decimal(str(parametros["uma_daily"])), Decimal(str(parametros["minimum_wage_daily"]))
    for (id_user, _), lista in por_semana.items():
        diario = diarios.get(id_user, Decimal(0))
        acumulado, dobles_semana, filas = 0, Decimal(0), []
        for r in lista:
            minutos = pagables[r.id_overtime][0]
            if r.kind == DESCANSO:
                # El doble del dia, ademas del dia que ya se paga; no cuenta para las 9 h.
                monto_doble = diario * 2 if minutos else Decimal(0)
                dobles_semana += monto_doble
                filas.append((r, 0, 0, monto_doble, monto_doble))
                continue
            dobles = max(min(minutos, LIMITE_DOBLES - acumulado), 0)
            triples = minutos - dobles
            acumulado += minutos
            hora = horas.get(id_user) or diario / (Decimal(jornada.get((id_user, r.work_date), politica[JORNADA] * 60)) / 60)
            monto_doble = hora * 2 * dobles / 60
            dobles_semana += monto_doble
            filas.append((r, dobles, triples, monto_doble + hora * 3 * triples / 60, monto_doble))
        # Exento de la semana, repartido entre sus registros por lo doble de cada uno.
        exento_semana = dobles_semana if diario <= minimo else min(dobles_semana / 2, uma * UMAS_EXENTAS_POR_SEMANA)
        for r, dobles, triples, monto, monto_doble in filas:
            if r.id_overtime not in de_este:
                continue
            exento = exento_semana * monto_doble / dobles_semana if dobles_semana else Decimal(0)
            fila = resultado.setdefault(id_user, {"double_minutes": 0, "triple_minutes": 0, "amount": Decimal(0),
                                                  "taxable": Decimal(0), "rest_days": 0,
                                                  "rest_day_amount": Decimal(0), "rest_day_taxable": Decimal(0),
                                                  "ids": []})
            if r.kind == DESCANSO:
                fila["rest_days"] += 1 if monto else 0
                fila["rest_day_amount"] += monto
                fila["rest_day_taxable"] += monto - exento
            else:
                fila["double_minutes"] += dobles
                fila["triple_minutes"] += triples
                fila["amount"] += monto
                fila["taxable"] += monto - exento
            fila["ids"].append(r.id_overtime)
    for fila in resultado.values():
        for clave in ("amount", "taxable", "rest_day_amount", "rest_day_taxable"):
            fila[clave] = ley.dinero(fila[clave])
    return resultado


# ------------------------------------------------------------------ registro y consulta

def _fecha(valor, campo) -> date:
    try:
        return date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def registrar(user_data: dict, payload: dict) -> dict:
    """Autoriza, aprueba lo no autorizado o captura (RH) horas extra de un empleado."""
    from app.services.attendance_correction_service import _exigir_que_pueda
    payload = dict(payload or {})
    origen = payload.get("origin") or AUTORIZADA
    liquidacion = payload.get("settlement") or PAGAR
    tipo = payload.get("kind") or HORA_EXTRA
    if tipo not in (HORA_EXTRA, DESCANSO):
        raise AppError("errors.invalid_field", 400, {"field": "kind"})
    if tipo == DESCANSO and not payload.get("minutes"):
        payload["minutes"] = 8 * 60   # informativo: el descanso se paga por dia
    if origen not in (AUTORIZADA, DETECTADA, MANUAL):
        raise AppError("errors.invalid_field", 400, {"field": "origin"})
    if liquidacion not in (PAGAR, COMPENSAR):
        raise AppError("errors.invalid_field", 400, {"field": "settlement"})
    try:
        minutos = int(payload.get("minutes"))
        id_user = int(payload.get("id_user"))
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": "minutes"}) from exc
    if not 0 < minutos <= 16 * 60:
        raise AppError("errors.invalid_field", 400, {"field": "minutes"})
    notas = str(payload.get("notes") or "").strip()
    # La captura a mano y el tiempo libre llevan siempre su porque.
    if (origen == MANUAL or liquidacion == COMPENSAR) and not notas or len(notas) > 300:
        raise AppError("errors.invalid_field", 400, {"field": "notes"})
    dia = _fecha(payload.get("work_date"), "work_date")
    with transaction_context() as db:
        _, es_rh = _exigir_que_pueda(db, user_data, id_user)
        if origen == MANUAL and not es_rh:
            raise AppError("errors.permission_denied", 403, {"entity": "overtime", "action": "manual"})
        # Jefe y luego RH (2026-11-04): lo que registra RH ya queda confirmado.
        registro = Overtime(id_user=id_user, work_date=dia, minutes=minutos, kind=tipo, origin=origen,
                            settlement=liquidacion, approval_status=CONFIRMADA if es_rh else PENDIENTE_RH,
                            notes=notas or None, created_by=user_data.get("id_user"))
        db.add(registro)
        db.flush()
        return registro.serialize()


def confirmar(user_data: dict, id_overtime, confirmar_: bool, notas=None) -> dict:
    """RH confirma (se paga) o rechaza (no se paga) lo que registro el jefe."""
    notas = str(notas or "").strip()
    if len(notas) > 300:
        raise AppError("errors.invalid_field", 400, {"field": "notes"})
    with transaction_context() as db:
        registro = db.get(Overtime, int(id_overtime))
        if registro is None or registro.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        if registro.approval_status != PENDIENTE_RH:
            raise AppError("errors.overtime_not_pending", 409, {"approval_status": registro.approval_status})
        registro.approval_status = CONFIRMADA if confirmar_ else RECHAZADA
        if notas:
            registro.notes = (f"{registro.notes} · RH: {notas}" if registro.notes else f"RH: {notas}")[:300]
        return registro.serialize()


def borrar(user_data: dict, id_overtime) -> dict:
    """Quita un registro que todavia no se paga en un periodo cerrado."""
    from app.services.attendance_correction_service import _exigir_que_pueda
    from app.utils.tiempo import ahora_utc
    with transaction_context() as db:
        registro = db.get(Overtime, int(id_overtime))
        if registro is None or registro.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        _exigir_que_pueda(db, user_data, registro.id_user)
        if registro.id_payroll_period is not None:
            raise AppError("errors.overtime_already_paid", 409, {"id_payroll_period": registro.id_payroll_period})
        registro.deletion_date = ahora_utc()
        return registro.serialize()


def del_rango(user_data: dict, desde, hasta) -> dict:
    """Horas extra registradas (con lo checado y su estado) y tiempo no autorizado del
    rango: de todos para RH, de su equipo para un supervisor."""
    from app.services.attendance_correction_service import _es_rh
    desde, hasta = _fecha(desde, "from"), _fecha(hasta, "to")
    if hasta < desde or (hasta - desde).days > 62:
        raise AppError("errors.invalid_field", 400, {"field": "to"})
    actor = user_data.get("id_user")
    with transaction_context() as db:
        consulta = select(User).where(User.deletion_date.is_(None)).where(User.is_employee.is_(True))
        if not _es_rh(user_data):
            consulta = consulta.where(User.supervisor == actor).where(User.id_user != actor)
        empleados = {u.id_user: u.full_name or f"#{u.id_user}" for u in db.scalars(consulta)}
        ids = list(empleados)
        registros = _registros(db, ids, desde, hasta)
        extra, descansos = _lo_checado(db, ids, desde, hasta)
        pagables = _verificar(registros, extra, descansos)
        politica = _politica(db, hasta)
        cubierto = defaultdict(int)
        descansos_registrados = {(r.id_user, r.work_date) for r in registros if r.kind == DESCANSO}
        for r in registros:
            if r.origin != MANUAL and r.kind == HORA_EXTRA:
                cubierto[(r.id_user, r.work_date)] += pagables[r.id_overtime][0]
        filas = [{**r.serialize(), "full_name": empleados[r.id_user],
                  "checked_minutes": extra.get((r.id_user, r.work_date), 0),
                  "payable_minutes": pagables[r.id_overtime][0], "status": pagables[r.id_overtime][1]}
                 for r in sorted(registros, key=lambda r: (r.work_date, empleados[r.id_user]))]
        sin_autorizar = [{"id_user": u, "full_name": empleados[u], "work_date": d.isoformat(),
                          "minutes": m - cubierto[(u, d)]}
                         for (u, d), m in sorted(extra.items(), key=lambda x: (x[0][1], empleados[x[0][0]]))
                         if m - cubierto[(u, d)] > politica[TOLERANCIA]]
        descansos_sin_autorizar = [{"id_user": u, "full_name": empleados[u], "work_date": d.isoformat(), "holiday": festivo}
                                   for (u, d), festivo in sorted(descansos.items(), key=lambda x: (x[0][1], empleados[x[0][0]]))
                                   if (u, d) not in descansos_registrados]
        return {"overtime": filas, "unauthorized": sin_autorizar, "unauthorized_rest_days": descansos_sin_autorizar,
                "tolerance_minutes": politica[TOLERANCIA]}
