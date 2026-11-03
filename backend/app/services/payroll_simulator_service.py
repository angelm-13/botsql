"""Simulador de nomina (diseño aprobado por RH el 2026-11-03).

RH escribe (o toma de un empleado real) el sueldo, la periodicidad y lo que paso
en el periodo -faltas, horas extra, domingos, descansos trabajados- mas los
bonos y premios que quiera dar (disfraz de Halloween, navidad, cumpleaños...), y
ve el recibo que saldria: percepciones, ISR con subsidio, IMSS y neto. No guarda
nada ni toca ningun periodo.

Las reglas son las del calculo real (payroll_tax_rules.py y las cifras
vigentes a la fecha elegida), no una copia:

* Diario: por dia = el monto; por hora = el monto x las horas de la jornada;
  fijo = el monto / 7, 14, 15 o 30.
* Sueldo: dias pagados (los del periodo menos las faltas) x diario; un fijo de
  la misma periodicidad del periodo paga el monto menos las faltas a diario.
* Horas extra: la hora = diario / horas de la jornada (o el monto, si gana por
  hora); dobles x2 y triples x3. Exento: la mitad de lo doble, hasta 5 UMA por
  semana del periodo (todo lo doble si gana el minimo); lo triple grava.
* Descanso o festivo trabajado: el doble del dia, en la misma bolsa exenta.
* Prima dominical: % del diario por domingo (Opciones de calculo); exenta 1 UMA
  por domingo.
* Bonos y premios: gravan completos para el ISR (gratificaciones) y no cambian la
  cuota del IMSS del periodo, por ser pagos eventuales. Pendiente de confirmar
  con la contadora; la regla vive en el concepto BONO (is_taxable, no is_imss).

`pasar_bonos` es lo unico que escribe: deja los bonos como movimientos del
empleado en un periodo real no cerrado, con un concepto por nombre de bono, para
que salgan en su recibo al calcular. Lo demas de la nomina real sigue saliendo de
las checadas.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.models import (EmployeePayrollGroup, PayrollConcept, PayrollDetail, PayrollGroup, PayrollMovement,
                        PayrollPeriod, User)
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.utils.errors import AppError

PERIODICIDADES = {"weekly": 7, "biweekly": 14, "semimonthly": 15, "monthly": 30}
FORMAS = ("daily", "hourly", "fixed")
CODIGO_BONO = "BONO"
MAX_BONOS = 20
ETIQUETAS = {
    "SUELDO": "Sueldo", "HORAS_EXTRA": "Horas extra", "DESCANSO_TRAB": "Descanso o festivo trabajado",
    "PRIMA_DOM": "Prima dominical", "ISR": "ISR retenido (subsidio para el empleo aplicado)",
    "IMSS": "Cuota obrera IMSS",
}


def _numero(valor, campo, minimo=Decimal(0), maximo=None, entero=False) -> Decimal:
    try:
        numero = Decimal(str(valor if valor not in (None, "") else 0))
    except (InvalidOperation, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc
    if not numero.is_finite() or numero < minimo or (maximo is not None and numero > maximo) \
            or (entero and numero != numero.to_integral_value()):
        raise AppError("errors.invalid_field", 400, {"field": campo})
    return numero


def _fecha(valor, campo) -> date:
    try:
        return date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _bonos(lista) -> list[dict]:
    if not isinstance(lista or [], list) or len(lista or []) > MAX_BONOS:
        raise AppError("errors.invalid_field", 400, {"field": "bonuses"})
    bonos = []
    for i, b in enumerate(lista or []):
        nombre = str((b or {}).get("name") or "").strip()
        if not nombre or len(nombre) > 120:
            raise AppError("errors.invalid_field", 400, {"field": f"bonuses.{i}.name"})
        monto = ley.dinero(_numero((b or {}).get("amount"), f"bonuses.{i}.amount", maximo=Decimal("9999999")))
        if monto > 0:
            bonos.append({"name": nombre, "amount": monto})
    return bonos


def _entrada(datos: dict) -> dict:
    """Valida y normaliza lo que capturo RH."""
    datos = dict(datos or {})
    periodicidad = datos.get("pay_frequency")
    if periodicidad not in PERIODICIDADES:
        raise AppError("errors.invalid_field", 400, {"field": "pay_frequency", "allowed": list(PERIODICIDADES)})
    forma = datos.get("salary_type") or "daily"
    if forma not in FORMAS:
        raise AppError("errors.invalid_field", 400, {"field": "salary_type", "allowed": list(FORMAS)})
    frecuencia = datos.get("fixed_frequency") or periodicidad
    if forma == "fixed" and frecuencia not in PERIODICIDADES:
        raise AppError("errors.invalid_field", 400, {"field": "fixed_frequency", "allowed": list(PERIODICIDADES)})
    dias = PERIODICIDADES[periodicidad]
    monto = _numero(datos.get("amount"), "amount", maximo=Decimal("9999999"))
    if monto <= 0:
        raise AppError("errors.invalid_field", 400, {"field": "amount"})
    return {
        "date": _fecha(datos.get("date") or date.today().isoformat(), "date"),
        "pay_frequency": periodicidad, "period_days": dias,
        "salary_type": forma, "amount": monto, "fixed_frequency": frecuencia if forma == "fixed" else None,
        "hire_date": _fecha(datos["hire_date"], "hire_date") if datos.get("hire_date") else None,
        "day_hours": _numero(datos.get("day_hours") or 8, "day_hours", Decimal(1), Decimal(24)),
        "absences": int(_numero(datos.get("absences"), "absences", maximo=Decimal(dias), entero=True)),
        "overtime_double_hours": _numero(datos.get("overtime_double_hours"), "overtime_double_hours", maximo=Decimal(500)),
        "overtime_triple_hours": _numero(datos.get("overtime_triple_hours"), "overtime_triple_hours", maximo=Decimal(500)),
        "sundays_worked": int(_numero(datos.get("sundays_worked"), "sundays_worked", maximo=Decimal(5), entero=True)),
        "rest_days_worked": int(_numero(datos.get("rest_days_worked"), "rest_days_worked", maximo=Decimal(dias), entero=True)),
        "bonuses": _bonos(datos.get("bonuses")),
    }


def simular(datos: dict) -> dict:
    """El recibo que saldria con `datos`, sin guardar nada."""
    from app.services.payroll_calculation_service import (OPCION_IMSS_EN_FALTAS, OPCION_SUBSIDIO_DIAS_DEL_MES,
                                                          _parametros, _tarifa_isr, _vigentes)
    import calendar
    e = _entrada(datos)
    al_dia, dias = e["date"], e["period_days"]
    with transaction_context() as db:
        p = _parametros(db, al_dia)
        tramos, factor_tarifa = _tarifa_isr(db, al_dia.year, dias, e["pay_frequency"])
        prima_dom_pct = Decimal(str(_vigentes(db, ("sunday_premium_pct",), al_dia).get("sunday_premium_pct", 25)))
    uma, minimo = Decimal(str(p["uma_daily"])), Decimal(str(p["minimum_wage_daily"]))

    if e["salary_type"] == "hourly":
        diario = ley.dinero(e["amount"] * e["day_hours"])
    elif e["salary_type"] == "fixed":
        diario = ley.dinero(e["amount"] / PERIODICIDADES[e["fixed_frequency"]])
    else:
        diario = ley.dinero(e["amount"])
    pagados = dias - e["absences"]
    if e["salary_type"] == "fixed" and e["fixed_frequency"] == e["pay_frequency"]:
        sueldo = ley.dinero(max(e["amount"] - diario * e["absences"], Decimal(0)))
    else:
        sueldo = ley.dinero(diario * pagados)

    hora = e["amount"] if e["salary_type"] == "hourly" else diario / e["day_hours"]
    dobles = ley.dinero(hora * 2 * e["overtime_double_hours"])
    triples = ley.dinero(hora * 3 * e["overtime_triple_hours"])
    descanso = ley.dinero(diario * 2 * e["rest_days_worked"])
    semanas = math.ceil(dias / 7)
    bolsa = dobles + descanso
    exento = bolsa if diario <= minimo else min(bolsa / 2, uma * 5 * semanas)
    exento_extra = exento * dobles / bolsa if bolsa else Decimal(0)
    extra_gravado = ley.dinero(dobles - exento_extra + triples)
    descanso_gravado = ley.dinero(descanso - (exento - exento_extra))
    por_domingo = ley.dinero(diario * prima_dom_pct / 100)
    dominical = ley.dinero(por_domingo * e["sundays_worked"])
    dominical_gravado = ley.dinero(max(por_domingo - uma, Decimal(0)) * e["sundays_worked"])
    bonos = sum((b["amount"] for b in e["bonuses"]), Decimal(0))

    gravable = sueldo + extra_gravado + descanso_gravado + dominical_gravado + bonos
    isr_tarifa = ley.isr_por_tarifa(gravable, tramos, factor_tarifa)
    dias_del_mes = calendar.monthrange(al_dia.year, al_dia.month)[1] if p[OPCION_SUBSIDIO_DIAS_DEL_MES] else None
    subsidio = ley.subsidio_para_el_empleo(gravable, dias, p["uma_monthly"], p["subsidy_pct"],
                                           p["subsidy_income_limit"], dias_del_mes)
    isr = max(isr_tarifa - subsidio, ley.dinero(0))

    anios = ley.anios_cumplidos(e["hire_date"], al_dia)
    factor = ley.factor_de_integracion(p["aguinaldo_days"], ley.dias_de_vacaciones(anios, p["vacation_table"]),
                                       p["vacation_premium_pct"])
    sbc = ley.salario_base_de_cotizacion(diario, factor, minimo, uma, p["sbc_cap_umas"])
    dias_imss = pagados + (e["absences"] if p[OPCION_IMSS_EN_FALTAS] else 0)
    imss = ley.cuota_obrera_imss(sbc, dias_imss, diario, minimo, uma, p)

    percepciones = [{"code": c, "description": ETIQUETAS[c], "amount": m} for c, m in (
        ("SUELDO", sueldo), ("HORAS_EXTRA", dobles + triples), ("DESCANSO_TRAB", descanso),
        ("PRIMA_DOM", dominical)) if m > 0]
    percepciones += [{"code": CODIGO_BONO, "description": b["name"], "amount": b["amount"]} for b in e["bonuses"]]
    deducciones = [{"code": c, "description": ETIQUETAS[c], "amount": m} for c, m in (("ISR", isr), ("IMSS", imss))
                   if m > 0]
    total_p = sum((x["amount"] for x in percepciones), Decimal(0))
    total_d = sum((x["amount"] for x in deducciones), Decimal(0))
    numero = lambda v: float(ley.dinero(v))
    return {
        "date": al_dia.isoformat(), "pay_frequency": e["pay_frequency"], "period_days": dias,
        "salary_type": e["salary_type"], "amount": numero(e["amount"]), "fixed_frequency": e["fixed_frequency"],
        "daily_salary": numero(diario), "hour_price": numero(hora), "paid_days": pagados,
        "absences": e["absences"], "years_of_service": anios,
        "earnings": [{**x, "amount": numero(x["amount"])} for x in percepciones],
        "deductions": [{**x, "amount": numero(x["amount"])} for x in deducciones],
        "taxable_income": numero(gravable), "isr_before_subsidy": numero(isr_tarifa),
        "employment_subsidy": numero(subsidio), "integration_factor": float(factor), "sbc": numero(sbc),
        "imss_days": dias_imss, "total_earnings": numero(total_p), "total_deductions": numero(total_d),
        "net_pay": numero(total_p - total_d),
    }


def datos_del_empleado(id_user) -> dict:
    """Lo que el simulador toma de un empleado real: forma de salario, grupo,
    ingreso y horas de su jornada (las de la politica si no tiene horario)."""
    from app.services import salary_service as salarios
    from app.services.overtime_service import _minutos_de_jornada, _politica, JORNADA
    from app.services.work_schedule_service import _entero
    id_user = _entero(id_user, "id_user")
    hoy = date.today()
    with transaction_context() as db:
        empleado = db.get(User, id_user)
        if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
            raise AppError("errors.resource_not_found", 404)
        sueldo = salarios.sueldos_vigentes(db, [id_user], hoy).get(id_user)
        fila = db.scalars(select(EmployeePayrollGroup).where(EmployeePayrollGroup.id_user == id_user)
                          .where(EmployeePayrollGroup.deletion_date.is_(None))
                          .where(EmployeePayrollGroup.valid_from <= hoy)
                          .where((EmployeePayrollGroup.valid_to.is_(None)) | (EmployeePayrollGroup.valid_to >= hoy))).first()
        grupo = db.get(PayrollGroup, fila.id_payroll_group) if fila else db.scalars(
            select(PayrollGroup).where(PayrollGroup.is_default.is_(True)).where(PayrollGroup.deletion_date.is_(None))).first()
        # Promedio de las jornadas de su horario en la semana que empieza hoy.
        jornadas = list(_minutos_de_jornada(db, [id_user], hoy, hoy + timedelta(days=6)).values())
        horas = round(sum(jornadas) / len(jornadas) / 60, 2) if jornadas else _politica(db, hoy)[JORNADA]
        return {
            "id_user": id_user, "full_name": empleado.full_name or "",
            "salary_type": sueldo.salary_type if sueldo else "daily",
            "amount": float(sueldo.amount) if sueldo else float(empleado.base_salary or 0),
            "fixed_frequency": sueldo.fixed_frequency if sueldo else None,
            "pay_frequency": grupo.pay_frequency if grupo else "semimonthly",
            "payroll_group": grupo.group_name if grupo else None,
            "hire_date": empleado.hire_date.isoformat() if empleado.hire_date else None,
            "day_hours": horas,
            "open_periods": periodos_abiertos(db, empleado),
        }


def periodos_abiertos(db, empleado: User) -> list[dict]:
    """Los periodos no cerrados que calculan a este empleado (los de su grupo)."""
    from app.services.payroll_calculation_service import CERRADO
    from app.services.payroll_group_service import empleados_del_grupo, grupo_del_periodo
    salida = []
    for periodo in db.scalars(select(PayrollPeriod).where(PayrollPeriod.deletion_date.is_(None))
                              .where(PayrollPeriod.period_state != CERRADO)
                              .order_by(PayrollPeriod.period_start.desc())):
        grupo = grupo_del_periodo(db, periodo)
        if grupo is not None and not empleados_del_grupo(db, grupo, periodo.period_end, [empleado]):
            continue
        salida.append({"id_payroll_period": periodo.id_payroll_period,
                       "period_start": periodo.period_start.isoformat() if periodo.period_start else None,
                       "period_end": periodo.period_end.isoformat() if periodo.period_end else None,
                       "period_state": periodo.period_state})
    return salida


def _concepto_de_bono(db, nombre: str, user_id: int) -> PayrollConcept:
    """Un concepto por nombre de bono, para que el recibo diga "Premio disfraz"."""
    concepto = db.scalars(select(PayrollConcept).where(PayrollConcept.payroll_code == CODIGO_BONO)
                          .where(PayrollConcept.payroll_concept_description == nombre)
                          .where(PayrollConcept.deletion_date.is_(None))).first()
    if concepto is None:
        concepto = PayrollConcept(payroll_code=CODIGO_BONO, payroll_concept_description=nombre, type="earning",
                                  is_taxable=True, is_imss=False, created_by=user_id)
        db.add(concepto)
        db.flush()
    return concepto


def pasar_bonos(payload: dict, user_id: int) -> dict:
    """Deja los bonos de la simulacion en el periodo real del empleado."""
    from app.services.payroll_calculation_service import exigir_periodo_no_cerrado
    from app.services.work_schedule_service import _entero
    payload = dict(payload or {})
    id_user = _entero(payload.get("id_user"), "id_user")
    id_periodo = _entero(payload.get("id_payroll_period"), "id_payroll_period")
    bonos = _bonos(payload.get("bonuses"))
    if not bonos:
        raise AppError("errors.invalid_field", 400, {"field": "bonuses"})
    with transaction_context() as db:
        empleado = db.get(User, id_user)
        if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
            raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
        periodo = db.get(PayrollPeriod, id_periodo)
        if periodo is None or periodo.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        exigir_periodo_no_cerrado(db, id_periodo)
        if id_periodo not in {p["id_payroll_period"] for p in periodos_abiertos(db, empleado)}:
            raise AppError("errors.payroll_simulator_not_in_period", 409, {"id_payroll_period": id_periodo})
        detalle = db.scalars(select(PayrollDetail).where(PayrollDetail.id_payroll_period == id_periodo)
                             .where(PayrollDetail.id_user == id_user)
                             .where(PayrollDetail.deletion_date.is_(None))
                             .order_by(PayrollDetail.id_payroll_detail)).first()
        if detalle is None:
            detalle = PayrollDetail(id_payroll_period=id_periodo, id_user=id_user, created_by=user_id)
            db.add(detalle)
            db.flush()
        from app.services.payroll_movement_service import PayrollMovementService
        for b in bonos:
            movimiento = PayrollMovement(id_payroll_detail=detalle.id_payroll_detail,
                                         id_payroll_concept=_concepto_de_bono(db, b["name"], user_id).id_payroll_concept,
                                         amount=b["amount"], created_by=user_id)
            db.add(movimiento)
            db.flush()
            PayrollMovementService._write_event_log(db, action="create", actor_id=user_id, before="",
                                                    after=PayrollMovementService._format_audit_create_after(
                                                        movimiento.serialize()), field_name="*")
        return {"id_payroll_period": id_periodo, "id_payroll_detail": detalle.id_payroll_detail,
                "bonuses": [{"name": b["name"], "amount": float(b["amount"])} for b in bonos]}


def pdf_de_simulacion(datos: dict) -> tuple[bytes, str]:
    """La simulacion en PDF, marcada como tal: no es recibo de nomina."""
    import os
    import sys
    from app.models import CustomerSupplier
    resultado = simular(datos)
    nombre = str((datos or {}).get("full_name") or "").strip()[:120]
    with transaction_context() as db:
        empresa = db.scalars(select(CustomerSupplier).where(CustomerSupplier.is_principal.is_(True))
                             .where(CustomerSupplier.deletion_date.is_(None))
                             .order_by(CustomerSupplier.id_customer_supplier)).first()
        registro = {**resultado, "employee": nombre, "company": (empresa.name if empresa else "") or "",
                    "company_tax_id": (empresa.tax_id if empresa else "") or ""}
    app_path = os.getenv("DOCUMENTS_REPORTS_APP_PATH", "/documents-reports/app")
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    from documents.service import DocumentService
    plantillas = os.getenv("DOCUMENTS_TEMPLATES_DIR", "/documents-reports/templates")
    html = DocumentService(plantillas).env.get_template("payroll_simulation.html").render(record=registro)
    from weasyprint import HTML
    return HTML(string=html, base_url=plantillas).write_pdf(), "simulacion_de_nomina.pdf"
