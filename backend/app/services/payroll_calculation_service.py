"""Calculo de la nomina de un periodo a partir de las checadas guardadas.

Antes las tablas `payroll_*` solo tenian altas y bajas: nadie calculaba nada y
el sueldo se escribia a mano. Aqui vive la primera regla de calculo:

* Dias pagados (services/attendance_rules.py): con horario asignado, todos los
  dias del periodo -descansos y festivos incluidos- menos las faltas; sin
  horario, solo los dias con al menos una checada ligada (como antes de que
  existieran los horarios). Los retardos no afectan la nomina. Vacaciones,
  permisos e incapacidades (employee_leave) no son falta; cuales se pagan lo
  decide la misma regla.
* Sueldo del periodo: `user.base_salary` (salario DIARIO) x dias pagados.
  Se guarda como un movimiento con el concepto SUELDO.
* ISR (con el subsidio para el empleo ya restado) e IMSS (cuota del
  trabajador): dos movimientos de deduccion, ISR e IMSS. Las reglas estan en
  payroll_tax_rules.py y las cifras oficiales en `payroll_isr_bracket` y
  `payroll_parameter`. La base del ISR son las percepciones marcadas como
  gravables (`is_taxable`), las capturadas a mano incluidas.
* Totales del detalle: percepciones y deducciones salen de TODOS sus
  movimientos -los que genera este calculo y los que alguien capturo a mano
  (un bono, un descuento)-; el neto es percepciones menos deducciones. Las
  aportaciones patronales (`employer_contribution`) no le tocan al empleado y
  no entran al neto.
* Aguinaldo (si el periodo tiene marcada `includes_aguinaldo`) y prima
  vacacional (si en el periodo cae el aniversario de ingreso): movimientos
  AGUINALDO y PRIMA_VAC. Sus conceptos no se marcan gravables porque solo
  grava lo que pasa del tope exento; esa parte la suma este calculo a la base
  del ISR. Reglas en payroll_tax_rules.py.

Recalcular no duplica: el detalle del empleado en el periodo se reusa y solo
se reemplazan los movimientos que escribe este calculo (SUELDO, AGUINALDO,
PRIMA_VAC, ISR e IMSS). Lo capturado a mano no se toca.

Estados del periodo (columna `period_state`):

* 'open'        recien creado.
* 'calculated'  ya se calculo; se puede recalcular.
* 'closed'      pagado: congelado. No se recalcula ni se edita nada de el
                -fechas, detalles, movimientos-, ni desde la pantalla ni por la
                API. Solo quien administra nomina (permiso de borrar periodos,
                que el registro solo le da a Administrator) lo puede reabrir, y
                queda registro de quien y cuando.

"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.models import (PayrollConcept, PayrollDetail, PayrollIsrBracket, PayrollMovement,
                        PayrollParameter, PayrollPeriod, User)
from app.services import payroll_tax_rules as ley
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.tiempo import ahora_utc

CODIGO_SUELDO = "SUELDO"
CODIGO_AGUINALDO, CODIGO_PRIMA = "AGUINALDO", "PRIMA_VAC"
ABIERTO, CALCULADO, CERRADO = "open", "calculated", "closed"
# Columnas que solo mueven calcular/cerrar/reabrir; la captura generica no.
CAMPOS_DEL_ESTADO = ("period_state", "closed_at", "closed_by", "reopened_at", "reopened_by")
CENTAVOS = Decimal("0.01")
# Dias de ausencia justificada que se guardan en el detalle (attendance_rules.resumen).
CAMPOS_DE_AUSENCIA = ("vacation_days", "paid_leave_days", "unpaid_leave_days", "disability_days")


def _dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


# Conceptos que escribe el calculo: codigo -> (descripcion, tipo, grava ISR, integra IMSS).
CONCEPTOS_DEL_CALCULO = {
    CODIGO_SUELDO: ("Sueldo", "earning", True, True),
    CODIGO_AGUINALDO: ("Aguinaldo", "earning", False, False),
    CODIGO_PRIMA: ("Prima vacacional", "earning", False, False),
    "ISR": ("ISR retenido (subsidio para el empleo aplicado)", "deduction", False, False),
    "IMSS": ("Cuota obrera IMSS", "deduction", False, False),
}

# Valores que el calculo necesita de payroll_parameter.
PARAMETROS_REQUERIDOS = (
    "uma_daily", "uma_monthly", "minimum_wage_daily", "subsidy_pct", "subsidy_income_limit",
    "imss_em_surplus_pct", "imss_em_cash_pct", "imss_em_pensioners_pct", "imss_iv_pct", "imss_cv_pct",
    "imss_surplus_umas", "sbc_cap_umas", "aguinaldo_days", "vacation_premium_pct",
    "aguinaldo_exempt_umas", "vacation_premium_exempt_umas",
)


def _concepto(db, codigo: str, user_id: int) -> PayrollConcept:
    """Un concepto del calculo; se crea la primera vez que se calcula una nomina."""
    concepto = db.scalars(
        select(PayrollConcept)
        .where(PayrollConcept.payroll_code == codigo)
        .where(PayrollConcept.deletion_date.is_(None))
    ).first()
    if concepto is None:
        descripcion, tipo, gravable, imss = CONCEPTOS_DEL_CALCULO[codigo]
        concepto = PayrollConcept(
            payroll_code=codigo, payroll_concept_description=descripcion,
            type=tipo, is_taxable=gravable, is_imss=imss, created_by=user_id)
        db.add(concepto)
        db.flush()
    return concepto


def _concepto_sueldo(db, user_id: int) -> PayrollConcept:
    return _concepto(db, CODIGO_SUELDO, user_id)


def _parametros(db, al_dia) -> dict:
    """Los parametros vigentes `al_dia`; si falta alguno, no se calcula a ciegas.

    Una sola consulta para todas las claves; si una clave tiene dos vigencias que
    cubren el dia, gana la que empezo despues.
    """
    valores = {}
    for fila in db.scalars(
        select(PayrollParameter)
        .where(PayrollParameter.parameter_key.in_(PARAMETROS_REQUERIDOS))
        .where(PayrollParameter.deletion_date.is_(None))
        .where(PayrollParameter.valid_from <= al_dia)
        .where((PayrollParameter.valid_to.is_(None)) | (PayrollParameter.valid_to >= al_dia))
        .order_by(PayrollParameter.valid_from.desc())
    ):
        valores.setdefault(fila.parameter_key, Decimal(str(fila.value)))
    faltan = [clave for clave in PARAMETROS_REQUERIDOS if clave not in valores]
    if faltan:
        raise AppError("errors.payroll_parameters_missing", 409, {"date": al_dia.isoformat(), "keys": faltan})
    return valores


def _tarifa_isr(db, anio: int, dias: int):
    tabla, factor = ley.tabla_para_dias(dias)
    tramos = [
        (t.lower_limit, t.upper_limit, t.fixed_fee, t.rate_pct)
        for t in db.scalars(
            select(PayrollIsrBracket)
            .where(PayrollIsrBracket.valid_year == anio)
            .where(PayrollIsrBracket.period_days == tabla)
            .where(PayrollIsrBracket.deletion_date.is_(None))
        )
    ]
    if not tramos:
        raise AppError("errors.payroll_isr_table_missing", 409, {"year": anio, "period_days": tabla})
    return tramos, factor


class _MovimientosDelPeriodo:
    """Los movimientos vivos de los detalles de un periodo, leidos en UNA consulta.

    Antes, por cada empleado se buscaba y reemplazaba cada movimiento por separado
    y se sumaban percepciones y totales con otra consulta: unas 14 consultas por
    empleado (1,462 con 100 empleados). Aqui se leen todos juntos, se reemplazan
    en memoria y se guardan de una vez al cerrar la transaccion. Las sumas son las
    mismas que hacian las consultas: lo capturado a mano tambien cuenta.
    """

    def __init__(self, db, ids_detalle):
        self._db = db
        self._vivos: dict[int, list] = {i: [] for i in ids_detalle}
        if ids_detalle:
            for movimiento, concepto in db.execute(
                select(PayrollMovement, PayrollConcept)
                .join(PayrollConcept, PayrollConcept.id_payroll_concept == PayrollMovement.id_payroll_concept)
                .where(PayrollMovement.id_payroll_detail.in_(list(ids_detalle)))
                .where(PayrollMovement.deletion_date.is_(None))
            ):
                self._vivos[movimiento.id_payroll_detail].append((movimiento, concepto))

    def reemplazar(self, detalle: PayrollDetail, concepto: PayrollConcept, monto: Decimal, user_id: int) -> None:
        """Cierra el movimiento anterior de este concepto y escribe el nuevo (si no es cero)."""
        vivos = self._vivos.setdefault(detalle.id_payroll_detail, [])
        for par in [par for par in vivos if par[1].id_payroll_concept == concepto.id_payroll_concept]:
            par[0].deletion_date = ahora_utc()
            vivos.remove(par)
        if monto > 0:
            nuevo = PayrollMovement(id_payroll_detail=detalle.id_payroll_detail,
                                    id_payroll_concept=concepto.id_payroll_concept,
                                    amount=monto, created_by=user_id)
            self._db.add(nuevo)
            vivos.append((nuevo, concepto))

    def percepciones_gravables(self, detalle: PayrollDetail) -> Decimal:
        """Percepciones gravables completas. AGUINALDO y PRIMA_VAC quedan fuera
        aunque alguien marque su concepto como gravable: de ellos solo grava lo que
        pasa del tope exento, y eso lo suma el calculo."""
        return _dinero(sum((Decimal(str(m.amount)) for m, c in self._vivos.get(detalle.id_payroll_detail, [])
                            if c.type == "earning" and c.is_taxable is True
                            and c.payroll_code not in (CODIGO_AGUINALDO, CODIGO_PRIMA)), Decimal(0)))

    def totales(self, detalle: PayrollDetail) -> tuple[Decimal, Decimal]:
        por_tipo: dict[str, Decimal] = {}
        for m, c in self._vivos.get(detalle.id_payroll_detail, []):
            por_tipo[c.type] = por_tipo.get(c.type, Decimal(0)) + Decimal(str(m.amount))
        return _dinero(por_tipo.get("earning")), _dinero(por_tipo.get("deduction"))


def _periodo(db, id_payroll_period) -> PayrollPeriod:
    try:
        id_payroll_period = int(id_payroll_period)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.resource_not_found", 404) from exc
    periodo = db.get(PayrollPeriod, id_payroll_period)
    if periodo is None or periodo.deletion_date is not None:
        raise AppError("errors.resource_not_found", 404)
    return periodo


def exigir_periodo_no_cerrado(db, id_payroll_period) -> None:
    """La unica puerta: nada de un periodo cerrado se escribe."""
    if id_payroll_period in (None, ""):
        return
    try:
        periodo = db.get(PayrollPeriod, int(id_payroll_period))
    except (TypeError, ValueError):
        return
    if periodo is not None and periodo.period_state == CERRADO:
        raise AppError("errors.payroll_period_closed", 409, {"id_payroll_period": periodo.id_payroll_period})


def _registrar(db, antes: str, despues: str, user_id: int) -> None:
    """Deja el cambio de estado en la bitacora del sistema (event_log)."""
    from app.services.payroll_period_service import PayrollPeriodService
    PayrollPeriodService._write_event_log(
        db, action="update", actor_id=user_id, before=antes, after=despues, field_name="period_state")


def calcular_periodo(id_payroll_period, user_id: int) -> dict:
    """Calcula (o recalcula) la nomina de todos los empleados con sueldo."""
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        id_payroll_period = periodo.id_payroll_period
        if periodo.period_state == CERRADO:
            raise AppError("errors.payroll_period_closed", 409, {"id_payroll_period": id_payroll_period})
        if not periodo.period_start or not periodo.period_end or periodo.period_start > periodo.period_end:
            raise AppError("errors.invalid_field", 400, {"field": "period_start", "reason": "invalid_period"})

        empleados = db.scalars(
            select(User)
            .where(User.deletion_date.is_(None))
            .where(User.is_employee.is_(True))
            .order_by(User.full_name)
        ).all()
        from app.services.attendance_record_service import asistencia_por_empleado
        from app.services.attendance_rules import resumen as resumen_de_asistencia
        asistencia = asistencia_por_empleado(db, periodo.period_start, periodo.period_end,
                                             ids=[e.id_user for e in empleados])
        conceptos = {codigo: _concepto(db, codigo, user_id) for codigo in CONCEPTOS_DEL_CALCULO}
        # Las cifras oficiales son las vigentes al ultimo dia del periodo.
        al_dia = periodo.period_end
        dias_del_periodo = (periodo.period_end - periodo.period_start).days + 1
        parametros = _parametros(db, al_dia)
        tramos, factor_tarifa = _tarifa_isr(db, al_dia.year, dias_del_periodo)

        # Los detalles del periodo (y los que falten) y sus movimientos, de una vez.
        detalles: dict[int, PayrollDetail] = {}
        for d in db.scalars(select(PayrollDetail)
                            .where(PayrollDetail.id_payroll_period == periodo.id_payroll_period)
                            .where(PayrollDetail.deletion_date.is_(None))
                            .order_by(PayrollDetail.id_payroll_detail)):
            detalles.setdefault(d.id_user, d)
        nuevos = [PayrollDetail(id_payroll_period=periodo.id_payroll_period, id_user=e.id_user, created_by=user_id)
                  for e in empleados if _dinero(e.base_salary) > 0 and e.id_user not in detalles]
        if nuevos:
            db.add_all(nuevos)
            db.flush()
            detalles.update({d.id_user: d for d in nuevos})
        movimientos = _MovimientosDelPeriodo(db, [d.id_payroll_detail for d in detalles.values()])

        calculados, sin_sueldo, sin_ingreso = [], [], []
        for empleado in empleados:
            diario = _dinero(empleado.base_salary)
            if diario <= 0:
                sin_sueldo.append({"id_user": empleado.id_user, "full_name": empleado.full_name or ""})
                continue
            totales = resumen_de_asistencia(asistencia.get(empleado.id_user, []))
            trabajados, faltas = totales["paid_days"], totales["absences"]
            ausencias = {k: totales[k] for k in CAMPOS_DE_AUSENCIA}
            sueldo = _dinero(diario * trabajados)

            detalle = detalles[empleado.id_user]

            # Solo se reemplaza lo que escribe este calculo: SUELDO, AGUINALDO,
            # PRIMA_VAC, ISR e IMSS.
            movimientos.reemplazar(detalle, conceptos[CODIGO_SUELDO], sueldo, user_id)

            if not empleado.hire_date:
                sin_ingreso.append({"id_user": empleado.id_user, "full_name": empleado.full_name or ""})
            monto_aguinaldo = _dinero(0)
            if periodo.includes_aguinaldo:
                monto_aguinaldo = ley.aguinaldo(diario, parametros["aguinaldo_days"], empleado.hire_date, al_dia.year)
            movimientos.reemplazar(detalle, conceptos[CODIGO_AGUINALDO], monto_aguinaldo, user_id)

            dias_vacaciones, prima = 0, _dinero(0)
            aniversario = ley.aniversario_en(empleado.hire_date, periodo.period_start, periodo.period_end)
            if aniversario:
                dias_vacaciones, prima = ley.prima_vacacional(
                    diario, ley.anios_cumplidos(empleado.hire_date, aniversario), parametros["vacation_premium_pct"])
            movimientos.reemplazar(detalle, conceptos[CODIGO_PRIMA], prima, user_id)

            aguinaldo_gravado = ley.parte_gravada(monto_aguinaldo, parametros["uma_daily"],
                                                  parametros["aguinaldo_exempt_umas"])
            prima_gravada = ley.parte_gravada(prima, parametros["uma_daily"],
                                              parametros["vacation_premium_exempt_umas"])
            gravable = movimientos.percepciones_gravables(detalle) + aguinaldo_gravado + prima_gravada
            isr_tarifa = ley.isr_por_tarifa(gravable, tramos, factor_tarifa)
            subsidio = ley.subsidio_para_el_empleo(
                gravable, dias_del_periodo, parametros["uma_monthly"], parametros["subsidy_pct"],
                parametros["subsidy_income_limit"])
            isr = max(isr_tarifa - subsidio, _dinero(0))
            movimientos.reemplazar(detalle, conceptos["ISR"], isr, user_id)

            vacaciones = ley.dias_de_vacaciones(ley.anios_cumplidos(empleado.hire_date, al_dia))
            factor = ley.factor_de_integracion(parametros["aguinaldo_days"], vacaciones,
                                               parametros["vacation_premium_pct"])
            sbc = ley.salario_base_de_cotizacion(diario, factor, parametros["minimum_wage_daily"],
                                                 parametros["uma_daily"], parametros["sbc_cap_umas"])
            imss = ley.cuota_obrera_imss(sbc, trabajados, diario, parametros["minimum_wage_daily"],
                                         parametros["uma_daily"], parametros)
            movimientos.reemplazar(detalle, conceptos["IMSS"], imss, user_id)

            percepciones, deducciones = movimientos.totales(detalle)
            detalle.gross_salary = sueldo
            detalle.total_earnings = percepciones
            detalle.total_deductions = deducciones
            detalle.net_pay = percepciones - deducciones
            detalle.days_worked = trabajados
            detalle.absences = faltas
            for campo, dias in ausencias.items():
                setattr(detalle, campo, dias)
            calculados.append({
                "id_user": empleado.id_user,
                "full_name": empleado.full_name or "",
                "days_worked": trabajados,
                "absences": faltas,
                **ausencias,
                "daily_salary": float(diario),
                "salary": float(sueldo),
                "aguinaldo": float(monto_aguinaldo),
                "aguinaldo_taxable": float(aguinaldo_gravado),
                "vacation_premium": float(prima),
                "vacation_premium_taxable": float(prima_gravada),
                "vacation_premium_days": dias_vacaciones,
                "taxable_income": float(gravable),
                "isr_before_subsidy": float(isr_tarifa),
                "employment_subsidy": float(subsidio),
                "isr": float(isr),
                "integration_factor": float(factor),
                "sbc": float(sbc),
                "imss": float(imss),
                "total_earnings": float(percepciones),
                "total_deductions": float(deducciones),
                "net_pay": float(percepciones - deducciones),
            })

        periodo.period_state = CALCULADO

    return {
        "id_payroll_period": id_payroll_period,
        "period_state": CALCULADO,
        "employees": calculados,
        "without_salary": sin_sueldo,
        "without_hire_date": sin_ingreso,
        "total_net_pay": float(sum((_dinero(e["net_pay"]) for e in calculados), _dinero(0))),
    }


def cerrar_periodo(id_payroll_period, user_id: int) -> dict:
    """Congela un periodo ya calculado."""
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        if periodo.period_state != CALCULADO:
            raise AppError("errors.payroll_period_not_calculated", 409,
                           {"id_payroll_period": periodo.id_payroll_period, "period_state": periodo.period_state})
        periodo.period_state = CERRADO
        periodo.closed_at = ahora_utc()
        periodo.closed_by = user_id
        _registrar(db, CALCULADO, CERRADO, user_id)
        return periodo.serialize()


def reabrir_periodo(id_payroll_period, user_id: int) -> dict:
    """Regresa un periodo cerrado a 'calculado'. La ruta exige administrar nomina."""
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        if periodo.period_state != CERRADO:
            raise AppError("errors.payroll_period_not_closed", 409,
                           {"id_payroll_period": periodo.id_payroll_period, "period_state": periodo.period_state})
        periodo.period_state = CALCULADO
        periodo.reopened_at = ahora_utc()
        periodo.reopened_by = user_id
        _registrar(db, CERRADO, CALCULADO, user_id)
        return periodo.serialize()


def _movimientos_por_detalle(db, ids_detalle) -> dict[int, list[dict]]:
    """Movimientos vivos de varios detalles en una sola consulta (antes era una por empleado)."""
    salida: dict[int, list[dict]] = {i: [] for i in ids_detalle}
    if not ids_detalle:
        return salida
    for id_detalle, codigo, descripcion, tipo, monto in db.execute(
        select(PayrollMovement.id_payroll_detail, PayrollConcept.payroll_code,
               PayrollConcept.payroll_concept_description, PayrollConcept.type, PayrollMovement.amount)
        .join(PayrollConcept, PayrollConcept.id_payroll_concept == PayrollMovement.id_payroll_concept)
        .where(PayrollMovement.id_payroll_detail.in_(list(ids_detalle)))
        .where(PayrollMovement.deletion_date.is_(None))
        .order_by(PayrollConcept.type, PayrollConcept.payroll_concept_description)
    ):
        salida[id_detalle].append({"code": codigo or "", "description": descripcion or "", "type": tipo,
                                   "amount": float(_dinero(monto))})
    return salida


def _movimientos(db, detalle: PayrollDetail) -> list[dict]:
    return _movimientos_por_detalle(db, [detalle.id_payroll_detail])[detalle.id_payroll_detail]


def resumen_periodo(id_payroll_period) -> dict:
    """Lo ya calculado del periodo, sin recalcular (sirve tambien si esta cerrado)."""
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        filas = db.execute(
            select(PayrollDetail, User)
            .join(User, User.id_user == PayrollDetail.id_user)
            .where(PayrollDetail.id_payroll_period == periodo.id_payroll_period)
            .where(PayrollDetail.deletion_date.is_(None))
            .order_by(User.full_name)
        ).all()
        empleados = []
        de_cada_uno = _movimientos_por_detalle(db, [detalle.id_payroll_detail for detalle, _ in filas])
        for detalle, empleado in filas:
            por_codigo = {m["code"]: m["amount"] for m in de_cada_uno[detalle.id_payroll_detail]}
            empleados.append({
                "id_user": empleado.id_user,
                "full_name": empleado.full_name or "",
                "days_worked": detalle.days_worked or 0,
                "absences": detalle.absences or 0,
                **{campo: getattr(detalle, campo) or 0 for campo in CAMPOS_DE_AUSENCIA},
                "daily_salary": float(_dinero(empleado.base_salary)),
                "salary": float(_dinero(detalle.gross_salary)),
                "aguinaldo": por_codigo.get(CODIGO_AGUINALDO, 0.0),
                "vacation_premium": por_codigo.get(CODIGO_PRIMA, 0.0),
                "isr": por_codigo.get("ISR", 0.0),
                "imss": por_codigo.get("IMSS", 0.0),
                "total_earnings": float(_dinero(detalle.total_earnings)),
                "total_deductions": float(_dinero(detalle.total_deductions)),
                "net_pay": float(_dinero(detalle.net_pay)),
            })
        return {
            "id_payroll_period": periodo.id_payroll_period,
            "period_state": periodo.period_state,
            "employees": empleados,
            "without_salary": [],
            "without_hire_date": [],
            "total_net_pay": float(sum((_dinero(e["net_pay"]) for e in empleados), _dinero(0))),
        }


def datos_del_recibo(id_payroll_period, id_user) -> dict:
    """Todo lo que imprime el recibo de un empleado en un periodo ya calculado."""
    from app.models import CustomerSupplier
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        if periodo.period_state == ABIERTO:
            raise AppError("errors.payroll_period_not_calculated", 409,
                           {"id_payroll_period": periodo.id_payroll_period, "period_state": periodo.period_state})
        try:
            id_user = int(id_user)
        except (TypeError, ValueError) as exc:
            raise AppError("errors.resource_not_found", 404) from exc
        detalle = db.scalars(
            select(PayrollDetail)
            .where(PayrollDetail.id_payroll_period == periodo.id_payroll_period)
            .where(PayrollDetail.id_user == id_user)
            .where(PayrollDetail.deletion_date.is_(None))
        ).first()
        empleado = db.get(User, id_user)
        if detalle is None or empleado is None:
            raise AppError("errors.resource_not_found", 404)
        empresa = db.scalars(
            select(CustomerSupplier)
            .where(CustomerSupplier.is_principal.is_(True))
            .where(CustomerSupplier.deletion_date.is_(None))
            .order_by(CustomerSupplier.id_customer_supplier)
        ).first()
        movimientos = _movimientos(db, detalle)
        return {
            "company": (empresa.name if empresa else "") or "",
            "company_tax_id": (empresa.tax_id if empresa else "") or "",
            "id_payroll_period": periodo.id_payroll_period,
            "period_start": periodo.period_start.isoformat() if periodo.period_start else "",
            "period_end": periodo.period_end.isoformat() if periodo.period_end else "",
            "payment_date": periodo.payment_date.isoformat() if periodo.payment_date else "",
            "period_state": periodo.period_state,
            "employee": empleado.full_name or empleado.username or "",
            "position": empleado.puesto or "",
            "days_worked": detalle.days_worked or 0,
            "absences": detalle.absences or 0,
            **{campo: getattr(detalle, campo) or 0 for campo in CAMPOS_DE_AUSENCIA},
            "daily_salary": float(_dinero(empleado.base_salary)),
            "earnings": [m for m in movimientos if m["type"] == "earning"],
            "deductions": [m for m in movimientos if m["type"] == "deduction"],
            "total_earnings": float(_dinero(detalle.total_earnings)),
            "total_deductions": float(_dinero(detalle.total_deductions)),
            "net_pay": float(_dinero(detalle.net_pay)),
        }


def pdf_del_recibo(id_payroll_period, id_user) -> tuple[bytes, str]:
    """El recibo en PDF y su nombre de archivo.

    Se dibuja con el mismo motor de documentos que el vale y el laboratorio
    (plantilla documents-reports/templates/payroll_period_receipt.html), pero sin
    registrarlo en el catalogo generico: asi la ruta /documents/<clave>/<id> no
    puede abrirlo con datos que no son los suyos.
    """
    import os
    import sys
    datos = datos_del_recibo(id_payroll_period, id_user)
    app_path = os.getenv("DOCUMENTS_REPORTS_APP_PATH", "/documents-reports/app")
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    from documents.service import DocumentService
    plantillas = os.getenv("DOCUMENTS_TEMPLATES_DIR", "/documents-reports/templates")
    html = DocumentService(plantillas).env.get_template("payroll_period_receipt.html").render(record=datos)
    from weasyprint import HTML
    pdf = HTML(string=html, base_url=plantillas).write_pdf()
    return pdf, f"recibo_periodo_{datos['id_payroll_period']}_empleado_{int(id_user)}.pdf"
