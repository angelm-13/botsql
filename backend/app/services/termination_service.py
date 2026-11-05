"""Finiquito y liquidacion (Etapa E; diseño aprobado por RH el 2026-11-02).

RH registra la baja (fecha = ultimo dia trabajado, motivo) y el sistema calcula
lo que se le debe, con los datos de ese dia. No se guarda el resultado: si se
corrige una checada o una ausencia, el calculo cambia con ella.

Que se paga (LFT)
-----------------
* Dias trabajados no pagados: del dia siguiente al ultimo periodo de nomina que
  ya lo incluyo hasta la fecha de baja, con su forma de salario (salary_service).
* Aguinaldo proporcional (art. 87): lo del año hasta la baja, menos el
  aguinaldo que ya se le pago ese año.
* Vacaciones (arts. 76, 79 y 80): las que tiene disponibles mas las
  proporcionales del año de servicio en curso (si la empresa las da al
  aniversario), con prima vacacional solo sobre las proporcionales (la de las
  disponibles ya se pago al cumplir el año). Las adelantadas no se descuentan
  (decision de RH, 2026-10-28).
* Prima de antigüedad (art. 162): 12 dias por año, con el salario topado en 2
  salarios minimos; en despido (justificado o no) siempre, en renuncia o mutuo
  acuerdo solo con 15 años o mas.
* Despido injustificado (art. 50): 3 meses de salario integrado y, si RH lo
  marca, 20 dias por año.

ISR (LISR)
----------
Aguinaldo y prima con sus exentos (30 y 15 UMA). Prima de antigüedad e
indemnizaciones: exentas hasta 90 UMA por cada año de servicio (art. 93 fr. XIII;
mas de seis meses cuenta como año); lo demas grava con la tasa de su ultimo
sueldo mensual ordinario (art. 96). Lo ordinario (dias y vacaciones mas lo
gravado del aguinaldo y la prima) con la tarifa mensual. IMSS del trabajador
sobre los dias pendientes.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (EmployeeTermination, EmployeeTerminationLine, PayrollConcept, PayrollDetail, PayrollMovement, PayrollPeriod,
                        User)
from app.models.employee_termination import DESPIDO_INJUSTIFICADO, DESPIDO_JUSTIFICADO, MOTIVOS
from app.models.employee_termination_line import OTRO_PAGO, TIPOS_DE_RENGLON
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError

ANIOS_PARA_PRIMA_EN_RENUNCIA = 15
DIAS_PRIMA_ANTIGUEDAD = 12
DIAS_INDEMNIZACION = 90          # 3 meses
DIAS_POR_ANIO_INDEMNIZACION = 20
UMAS_EXENTAS_POR_ANIO = 90


class EmployeeTerminationService(CrudService):
    """La baja de un empleado; una sola viva por persona."""

    model = EmployeeTermination
    primary_key = 'id_employee_termination'
    entity_name = 'employee_termination'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        id_user = _entero(datos.get("id_user"), "id_user")
        if datos.get("reason") not in MOTIVOS:
            raise AppError("errors.invalid_field", 400, {"field": "reason", "allowed": list(MOTIVOS)})
        fecha = _fecha(datos.get("termination_date"), "termination_date")
        if len(str(datos.get("notes") or "")) > 300:
            raise AppError("errors.invalid_field", 400, {"field": "notes"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            if not empleado.hire_date or fecha < empleado.hire_date:
                raise AppError("errors.termination_before_hire_date", 409, {
                    "hire_date": empleado.hire_date.isoformat() if empleado.hire_date else None})
            for otra in db.scalars(select(EmployeeTermination).where(EmployeeTermination.id_user == id_user)
                                   .where(EmployeeTermination.deletion_date.is_(None))):
                if excluir_id is None or str(otra.id_employee_termination) != str(excluir_id):
                    raise AppError("errors.termination_duplicate", 409,
                                   {"id_employee_termination": otra.id_employee_termination})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        cls._validar(payload)
        payload["pay_twenty_days"] = bool(payload.get("pay_twenty_days")) and payload["reason"] == DESPIDO_INJUSTIFICADO
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        datos = {**cls.get(item_id), **payload}
        cls._validar(datos, excluir_id=item_id)
        payload["pay_twenty_days"] = bool(datos.get("pay_twenty_days")) and datos["reason"] == DESPIDO_INJUSTIFICADO
        return super().update(item_id, payload, user_id=user_id)


# ------------------------------------------------- otros pagos y descuentos

MONTO_MAXIMO = Decimal("9999999.99")


def _baja_viva(db, id_employee_termination) -> EmployeeTermination:
    baja = db.get(EmployeeTermination, _entero(id_employee_termination, "id_employee_termination"))
    if baja is None or baja.deletion_date is not None:
        raise AppError("errors.resource_not_found", 404)
    return baja


def agregar_renglon(id_employee_termination, payload: dict, user_id: int | None = None) -> dict:
    """Un bono o pago pendiente (se suma) o un descuento como Infonavit, Fonacot o una
    deuda (se resta), capturado por RH como en el Excel de la contadora (2026-11-05)."""
    payload = dict(payload or {})
    tipo = payload.get("line_kind")
    if tipo not in TIPOS_DE_RENGLON:
        raise AppError("errors.invalid_field", 400, {"field": "line_kind", "allowed": list(TIPOS_DE_RENGLON)})
    concepto = str(payload.get("description") or "").strip()
    if not concepto or len(concepto) > 120:
        raise AppError("errors.invalid_field", 400, {"field": "description"})
    try:
        monto = Decimal(str(payload.get("amount")))
    except Exception as exc:
        raise AppError("errors.invalid_field", 400, {"field": "amount"}) from exc
    if not monto.is_finite() or monto <= 0 or monto > MONTO_MAXIMO:
        raise AppError("errors.invalid_field", 400, {"field": "amount"})
    with transaction_context() as db:
        baja = _baja_viva(db, id_employee_termination)
        # Un descuento no cambia el ISR; solo un pago puede gravar.
        renglon = EmployeeTerminationLine(id_employee_termination=baja.id_employee_termination, line_kind=tipo,
                                          description=concepto, amount=_d(monto),
                                          taxable=tipo == OTRO_PAGO and payload.get("taxable", True) is not False,
                                          created_by=user_id or 1)
        db.add(renglon)
        db.flush()
        return renglon.serialize()


def quitar_renglon(id_employee_termination, id_line, user_id: int | None = None) -> dict:
    from app.utils.tiempo import ahora_utc
    with transaction_context() as db:
        baja = _baja_viva(db, id_employee_termination)
        renglon = db.get(EmployeeTerminationLine, _entero(id_line, "id_employee_termination_line"))
        if (renglon is None or renglon.deletion_date is not None
                or renglon.id_employee_termination != baja.id_employee_termination):
            raise AppError("errors.resource_not_found", 404)
        renglon.deletion_date = ahora_utc()
        return {"id_employee_termination_line": renglon.id_employee_termination_line, "deleted": True}


def _renglones(db, id_employee_termination) -> list:
    return list(db.scalars(select(EmployeeTerminationLine)
                           .where(EmployeeTerminationLine.id_employee_termination == id_employee_termination)
                           .where(EmployeeTerminationLine.deletion_date.is_(None))
                           .order_by(EmployeeTerminationLine.id_employee_termination_line)))


# ------------------------------------------------------------------ calculo

def _d(valor) -> Decimal:
    return ley.dinero(valor)


def _desde_dias_pendientes(db, empleado: User, fecha: date) -> date:
    """El dia siguiente al ultimo periodo de nomina que ya le pago."""
    ultimo = db.scalar(select(func.max(PayrollPeriod.period_end))
                       .join(PayrollDetail, PayrollDetail.id_payroll_period == PayrollPeriod.id_payroll_period)
                       .where(PayrollDetail.id_user == empleado.id_user)
                       .where(PayrollDetail.deletion_date.is_(None)).where(PayrollPeriod.deletion_date.is_(None))
                       .where(PayrollPeriod.period_state.in_(("calculated", "closed")))
                       .where(PayrollPeriod.period_end < fecha))
    if ultimo:
        return ultimo + timedelta(days=1)
    return max(empleado.hire_date, fecha.replace(day=1))


def _aguinaldo_pagado(db, id_user: int, anio: int) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(PayrollMovement.amount), 0))
                      .join(PayrollConcept, PayrollConcept.id_payroll_concept == PayrollMovement.id_payroll_concept)
                      .join(PayrollDetail, PayrollDetail.id_payroll_detail == PayrollMovement.id_payroll_detail)
                      .join(PayrollPeriod, PayrollPeriod.id_payroll_period == PayrollDetail.id_payroll_period)
                      .where(PayrollConcept.payroll_code == "AGUINALDO")
                      .where(PayrollDetail.id_user == id_user)
                      .where(PayrollMovement.deletion_date.is_(None)).where(PayrollDetail.deletion_date.is_(None))
                      .where(PayrollPeriod.deletion_date.is_(None))
                      .where(PayrollPeriod.period_state.in_(("calculated", "closed")))
                      .where(func.extract("year", PayrollPeriod.period_end) == anio))
    return Decimal(str(total or 0))


def calcular(id_employee_termination) -> dict:
    """El finiquito (o liquidacion) de una baja, concepto por concepto."""
    from app.services import politica_de_vacaciones as pv
    from app.services import salary_service as salarios
    from app.services.attendance_record_service import asistencia_por_empleado
    from app.services.attendance_rules import resumen as resumen_de_asistencia
    from app.services.employee_leave_service import saldo_de_vacaciones
    from app.services.payroll_calculation_service import _parametros, _tarifa_isr, _vigentes, tabla_de_vacaciones
    with transaction_context() as db:
        baja = db.get(EmployeeTermination, _entero(id_employee_termination, "id_employee_termination"))
        if baja is None or baja.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        empleado = db.get(User, baja.id_user)
        fecha, ingreso = baja.termination_date, empleado.hire_date
        p = _parametros(db, fecha)
        uma, minimo = Decimal(str(p["uma_daily"])), Decimal(str(p["minimum_wage_daily"]))

        # Dias pendientes y diario (con su forma de salario).
        desde = _desde_dias_pendientes(db, empleado, fecha)
        dias = asistencia_por_empleado(db, desde, fecha, ids=[empleado.id_user]).get(empleado.id_user, []) \
            if desde <= fecha else []
        sueldo = salarios.sueldos_vigentes(db, [empleado.id_user], fecha).get(empleado.id_user)
        horas = int(_vigentes(db, ("overtime_day_hours",), fecha).get("overtime_day_hours", 8))
        diario = salarios.diario_equivalente(sueldo, dias, horas) if sueldo else _d(empleado.base_salary)
        if diario <= 0:
            raise AppError("errors.termination_without_salary", 409, {"id_user": empleado.id_user})
        salario = salarios.sueldo_del_periodo(sueldo, diario, dias, None)
        pagados = resumen_de_asistencia(dias)["paid_days"]

        # Aguinaldo proporcional menos lo ya pagado en el año.
        inicio_anio = max(date(fecha.year, 1, 1), ingreso)
        dias_del_anio = (date(fecha.year, 12, 31) - date(fecha.year, 1, 1)).days + 1
        proporcional = diario * Decimal(str(p["aguinaldo_days"])) * ((fecha - inicio_anio).days + 1) / dias_del_anio
        aguinaldo = _d(max(proporcional - _aguinaldo_pagado(db, empleado.id_user, fecha.year), Decimal(0)))

        # Vacaciones disponibles mas proporcionales del año de servicio en curso.
        politica = pv.politica(db, fecha)
        tabla = tabla_de_vacaciones(db, fecha)
        anios = ley.anios_cumplidos(ingreso, fecha)
        disponibles = Decimal(saldo_de_vacaciones(db, empleado, fecha)["available"])
        proporcionales = Decimal(0)
        if not politica[pv.MENSUAL]:
            del_anio = (fecha - pv.aniversario(ingreso, anios)).days + 1
            proporcionales = (Decimal(ley.dias_de_vacaciones(anios, tabla)) * del_anio / 365).quantize(Decimal("0.01"))
        vacaciones = _d(diario * (disponibles + proporcionales))
        prima_vacacional = _d(diario * proporcionales * Decimal(str(p["vacation_premium_pct"])) / 100)

        # Prima de antigüedad e indemnizaciones.
        anios_exactos = Decimal((fecha - ingreso).days + 1) / 365
        despido = baja.reason in (DESPIDO_JUSTIFICADO, DESPIDO_INJUSTIFICADO)
        prima_antiguedad = _d(DIAS_PRIMA_ANTIGUEDAD * min(diario, minimo * 2) * anios_exactos) \
            if despido or anios_exactos >= ANIOS_PARA_PRIMA_EN_RENUNCIA else _d(0)
        factor = ley.factor_de_integracion(p["aguinaldo_days"], ley.dias_de_vacaciones(anios, tabla),
                                           p["vacation_premium_pct"])
        integrado = diario * factor
        tres_meses = _d(integrado * DIAS_INDEMNIZACION) if baja.reason == DESPIDO_INJUSTIFICADO else _d(0)
        veinte_dias = _d(integrado * DIAS_POR_ANIO_INDEMNIZACION * anios_exactos) \
            if baja.reason == DESPIDO_INJUSTIFICADO and baja.pay_twenty_days else _d(0)

        # ISR: lo ordinario con la tarifa mensual; la separacion con la tasa del ultimo sueldo mensual.
        aguinaldo_gravado = ley.parte_gravada(aguinaldo, uma, p["aguinaldo_exempt_umas"])
        prima_gravada = ley.parte_gravada(prima_vacacional, uma, p["vacation_premium_exempt_umas"])
        renglones = _renglones(db, baja.id_employee_termination)
        otros_pagos = [x for x in renglones if x.line_kind == OTRO_PAGO]
        otros_descuentos = [x for x in renglones if x.line_kind != OTRO_PAGO]
        otros_gravados = sum((Decimal(str(x.amount)) for x in otros_pagos if x.taxable), Decimal(0))
        tramos, _ = _tarifa_isr(db, fecha.year, 30, "monthly")
        isr_ordinario = ley.isr_por_tarifa(salario + vacaciones + aguinaldo_gravado + prima_gravada + otros_gravados,
                                           tramos)
        separacion = prima_antiguedad + tres_meses + veinte_dias
        resto = (fecha - pv.aniversario(ingreso, anios)).days
        anios_exentos = anios + (1 if resto > 182 else 0)
        separacion_gravada = _d(max(separacion - uma * UMAS_EXENTAS_POR_ANIO * max(anios_exentos, 1), Decimal(0)))
        mensual = diario * 30
        tasa = ley.isr_por_tarifa(mensual, tramos) / mensual if mensual else Decimal(0)
        isr_separacion = _d(separacion_gravada * tasa)
        sbc = ley.salario_base_de_cotizacion(diario, factor, minimo, uma, p["sbc_cap_umas"])
        imss = ley.cuota_obrera_imss(sbc, pagados, diario, minimo, uma, p)

        percepciones = [(codigo, monto, None) for codigo, monto in (
            ("pending_days", salario), ("aguinaldo", aguinaldo), ("vacations", vacaciones),
            ("vacation_premium", prima_vacacional), ("seniority_premium", prima_antiguedad),
            ("severance_three_months", tres_meses), ("severance_twenty_days", veinte_dias)) if monto > 0]
        percepciones += [("extra", _d(x.amount), x.description) for x in otros_pagos]
        deducciones = [(codigo, monto, None) for codigo, monto in (
            ("isr", isr_ordinario), ("isr_severance", isr_separacion), ("imss", imss)) if monto > 0]
        deducciones += [("extra", _d(x.amount), x.description) for x in otros_descuentos]
        total = sum((m for _, m, _ in percepciones), Decimal(0))
        descuentos = sum((m for _, m, _ in deducciones), Decimal(0))

        def concepto(codigo, monto, descripcion):
            return {"code": codigo, "amount": float(monto), **({"description": descripcion} if descripcion else {})}
        return {
            **baja.serialize(), "full_name": empleado.full_name or "", "hire_date": ingreso.isoformat(),
            "daily_salary": float(diario), "integrated_daily_salary": float(_d(integrado)),
            "years_of_service": float(round(anios_exactos, 2)),
            "pending_from": desde.isoformat(), "pending_paid_days": pagados,
            "vacation_days_available": float(disponibles), "vacation_days_proportional": float(proporcionales),
            "earnings": [concepto(*x) for x in percepciones],
            "deductions": [concepto(*x) for x in deducciones],
            "extra_lines": [x.serialize() for x in renglones],
            "taxable_severance": float(separacion_gravada), "severance_tax_rate": float(round(tasa * 100, 2)),
            "total_earnings": float(_d(total)), "total_deductions": float(_d(descuentos)),
            "net_pay": float(_d(total - descuentos)),
        }


ETIQUETAS = {
    "pending_days": "Días trabajados pendientes de pago", "aguinaldo": "Aguinaldo proporcional",
    "vacations": "Vacaciones (disponibles y proporcionales)", "vacation_premium": "Prima vacacional proporcional",
    "seniority_premium": "Prima de antigüedad (LFT art. 162)",
    "severance_three_months": "Indemnización: 3 meses de salario (LFT art. 50)",
    "severance_twenty_days": "Indemnización: 20 días por año (LFT art. 50)",
    "isr": "ISR (sueldo, vacaciones y prestaciones)", "isr_severance": "ISR de la separación (LISR art. 96)",
    "imss": "Cuota obrera IMSS",
}
MOTIVOS_TEXTO = {"resignation": "Renuncia voluntaria", "mutual_agreement": "Mutuo acuerdo",
                 "justified_dismissal": "Despido justificado", "unjustified_dismissal": "Despido injustificado"}


def pdf_del_finiquito(id_employee_termination) -> tuple[bytes, str]:
    """El recibo de finiquito en PDF, con el mismo motor que el recibo de nomina."""
    import os
    import sys
    from app.models import CustomerSupplier
    datos = calcular(id_employee_termination)
    with transaction_context() as db:
        empresa = db.scalars(select(CustomerSupplier).where(CustomerSupplier.is_principal.is_(True))
                             .where(CustomerSupplier.deletion_date.is_(None))
                             .order_by(CustomerSupplier.id_customer_supplier)).first()
        registro = {
            **datos, "employee": datos["full_name"],
            "title": "Liquidación" if datos["reason"] == DESPIDO_INJUSTIFICADO else "Finiquito",
            "reason_label": MOTIVOS_TEXTO[datos["reason"]],
            "company": (empresa.name if empresa else "") or "", "company_tax_id": (empresa.tax_id if empresa else "") or "",
            "earnings": [{**m, "description": m.get("description") or ETIQUETAS[m["code"]]} for m in datos["earnings"]],
            "deductions": [{**m, "description": m.get("description") or ETIQUETAS[m["code"]]}
                           for m in datos["deductions"]],
        }
    app_path = os.getenv("DOCUMENTS_REPORTS_APP_PATH", "/documents-reports/app")
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    from documents.service import DocumentService
    plantillas = os.getenv("DOCUMENTS_TEMPLATES_DIR", "/documents-reports/templates")
    html = DocumentService(plantillas).env.get_template("termination_settlement.html").render(record=registro)
    from weasyprint import HTML
    pdf = HTML(string=html, base_url=plantillas).write_pdf()
    return pdf, f"finiquito_baja_{datos['id_employee_termination']}.pdf"
