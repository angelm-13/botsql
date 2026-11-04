"""Hoja de nomina tipo Excel (puntos 6 y 7 de RH, diseño aprobado el 2026-11-04).

Una fila por empleado del periodo y una columna por concepto: ingresos a un lado,
egresos al otro, cada bloque con su total y al final el neto.

* Lo que escribe el calculo (SUELDO, ISR, IMSS, horas extra...) no se escribe a
  mano: se recalcula. Lo demas (bonos, premios, prestamos, descuentos) se escribe
  en la celda y queda como un movimiento de nomina del empleado.
* Guardar una celda reemplaza el movimiento de ese concepto y recalcula el periodo
  en la MISMA transaccion: si el calculo falla, la celda no se guarda.
* Simular hace lo mismo y al final deshace todo (rollback): se ve como quedaria
  la nomina sin tocar nada. "Pasar a la nomina" es guardar esas mismas celdas.
* Periodo cerrado: solo se ve. Periodo sin calcular: primero se calcula.
"""
from __future__ import annotations

import io
import zipfile
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from sqlalchemy import select

from app.models import PayrollConcept, PayrollDetail, PayrollMovement, User
from app.models.session import transaction_context
from app.services.payroll_calculation_service import (ABIERTO, CERRADO, CONCEPTOS_DEL_CALCULO, _dinero, _periodo,
                                                      calcular_en)
from app.services.payroll_movement_service import PayrollMovementService
from app.utils.errors import AppError
from app.utils.tiempo import ahora_utc

TIPOS = ("earning", "deduction")
SIEMPRE = ("SUELDO", "ISR", "IMSS")
MAX_CAMBIOS = 500
TOPE = Decimal("9999999999.99")  # Numeric(12,2)


def _editable(concepto: PayrollConcept) -> bool:
    return concepto.type in TIPOS and (concepto.payroll_code or "") not in CONCEPTOS_DEL_CALCULO


def _columna(c: PayrollConcept) -> dict:
    return {"id_payroll_concept": c.id_payroll_concept, "code": c.payroll_code or "",
            "description": c.payroll_concept_description or "", "type": c.type, "editable": _editable(c)}


def _orden(c: PayrollConcept):
    # Ingresos antes que egresos; dentro de cada bloque, lo calculado primero (en el orden del calculo).
    calculados = list(CONCEPTOS_DEL_CALCULO)
    codigo = c.payroll_code or ""
    return (TIPOS.index(c.type), 0 if codigo in calculados else 1,
            calculados.index(codigo) if codigo in calculados else 0, c.payroll_concept_description or "")


def hoja_en(db, periodo) -> dict:
    filas = db.execute(
        select(PayrollDetail, User).join(User, User.id_user == PayrollDetail.id_user)
        .where(PayrollDetail.id_payroll_period == periodo.id_payroll_period)
        .where(PayrollDetail.deletion_date.is_(None)).order_by(User.full_name)
    ).all()
    ids = [d.id_payroll_detail for d, _ in filas]
    montos: dict[int, dict[int, Decimal]] = {i: {} for i in ids}
    en_uso: dict[int, PayrollConcept] = {}
    if ids:
        for m, c in db.execute(
            select(PayrollMovement, PayrollConcept)
            .join(PayrollConcept, PayrollConcept.id_payroll_concept == PayrollMovement.id_payroll_concept)
            .where(PayrollMovement.id_payroll_detail.in_(ids)).where(PayrollMovement.deletion_date.is_(None))
            .where(PayrollConcept.type.in_(TIPOS))
        ):
            en_uso[c.id_payroll_concept] = c
            fila = montos[m.id_payroll_detail]
            fila[c.id_payroll_concept] = fila.get(c.id_payroll_concept, Decimal(0)) + Decimal(str(m.amount or 0))
    catalogo = db.scalars(select(PayrollConcept).where(PayrollConcept.deletion_date.is_(None))
                          .where(PayrollConcept.type.in_(TIPOS))).all()
    # Sueldo, ISR e IMSS siempre se ven, aunque en este periodo salgan en cero.
    en_uso.update({c.id_payroll_concept: c for c in catalogo if c.payroll_code in SIEMPRE})
    columnas = sorted(en_uso.values(), key=_orden)
    renglones = []
    for detalle, empleado in filas:
        renglones.append({
            "id_user": empleado.id_user, "full_name": empleado.full_name or empleado.username or "",
            "days_worked": detalle.days_worked or 0, "absences": detalle.absences or 0,
            "amounts": {str(k): float(_dinero(v)) for k, v in montos[detalle.id_payroll_detail].items()},
            "total_earnings": float(_dinero(detalle.total_earnings)),
            "total_deductions": float(_dinero(detalle.total_deductions)),
            "net_pay": float(_dinero(detalle.net_pay)),
        })
    totales = {str(c.id_payroll_concept): float(_dinero(sum((f[c.id_payroll_concept] for f in montos.values()
                                                             if c.id_payroll_concept in f), Decimal(0))))
               for c in columnas}
    for campo in ("total_earnings", "total_deductions", "net_pay"):
        totales[campo] = float(sum((_dinero(r[campo]) for r in renglones), _dinero(0)))
    return {
        "id_payroll_period": periodo.id_payroll_period,
        "period_state": periodo.period_state,
        "period_start": periodo.period_start.isoformat() if periodo.period_start else "",
        "period_end": periodo.period_end.isoformat() if periodo.period_end else "",
        "columns": [_columna(c) for c in columnas],
        "available": [_columna(c) for c in sorted(catalogo, key=_orden)
                      if _editable(c) and c.id_payroll_concept not in en_uso],
        "rows": renglones,
        "totals": totales,
    }


def hoja(id_payroll_period) -> dict:
    with transaction_context() as db:
        return hoja_en(db, _periodo(db, id_payroll_period))


def _cambios(lista) -> list[tuple[int, int, Decimal]]:
    if not isinstance(lista, list) or not lista:
        raise AppError("errors.invalid_field", 400, {"field": "changes"})
    if len(lista) > MAX_CAMBIOS:
        raise AppError("errors.invalid_field", 400, {"field": "changes", "reason": "too_many"})
    salida = {}
    for c in lista:
        try:
            clave = (int(c["id_user"]), int(c["id_payroll_concept"]))
            monto = _dinero(c.get("amount") if c.get("amount") not in (None, "") else 0)
        except (TypeError, ValueError, KeyError, InvalidOperation) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "changes"}) from exc
        if monto < 0 or monto > TOPE:
            raise AppError("errors.invalid_field", 400, {"field": "amount"})
        salida[clave] = monto  # la ultima escritura de la misma celda gana
    return [(u, c, m) for (u, c), m in salida.items()]


def _aplicar(db, periodo, cambios, user_id: int) -> None:
    if periodo.period_state == CERRADO:
        raise AppError("errors.payroll_period_closed", 409, {"id_payroll_period": periodo.id_payroll_period})
    if periodo.period_state == ABIERTO:
        raise AppError("errors.payroll_period_not_calculated", 409,
                       {"id_payroll_period": periodo.id_payroll_period, "period_state": periodo.period_state})
    for id_user, id_concepto, monto in cambios:
        concepto = db.get(PayrollConcept, id_concepto)
        if concepto is None or concepto.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        if not _editable(concepto):
            raise AppError("errors.payroll_sheet_concept_calculated", 409, {"code": concepto.payroll_code or ""})
        detalle = db.scalars(select(PayrollDetail).where(PayrollDetail.id_payroll_period == periodo.id_payroll_period)
                             .where(PayrollDetail.id_user == id_user)
                             .where(PayrollDetail.deletion_date.is_(None))).first()
        if detalle is None:
            raise AppError("errors.resource_not_found", 404)
        antes = Decimal(0)
        for m in db.scalars(select(PayrollMovement).where(PayrollMovement.id_payroll_detail == detalle.id_payroll_detail)
                            .where(PayrollMovement.id_payroll_concept == id_concepto)
                            .where(PayrollMovement.deletion_date.is_(None))):
            antes += Decimal(str(m.amount or 0))
            m.deletion_date = ahora_utc()
        if monto > 0:
            db.add(PayrollMovement(id_payroll_detail=detalle.id_payroll_detail, id_payroll_concept=id_concepto,
                                   amount=monto, created_by=user_id))
        PayrollMovementService._write_event_log(
            db, action="update", actor_id=user_id, field_name="amount",
            before=f"periodo {periodo.id_payroll_period}, usuario {id_user}, concepto {id_concepto}: {_dinero(antes)}",
            after=f"periodo {periodo.id_payroll_period}, usuario {id_user}, concepto {id_concepto}: {monto}")
    db.flush()


def guardar(id_payroll_period, lista, user_id: int) -> dict:
    """Guarda las celdas y recalcula el periodo, todo o nada."""
    cambios = _cambios(lista)
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        _aplicar(db, periodo, cambios, user_id)
        calcular_en(db, periodo.id_payroll_period, user_id)
        return hoja_en(db, periodo)


def simular(id_payroll_period, lista, user_id: int) -> dict:
    """Como quedaria con esas celdas, sin guardar nada."""
    cambios = _cambios(lista)
    with transaction_context() as db:
        periodo = _periodo(db, id_payroll_period)
        _aplicar(db, periodo, cambios, user_id)
        calcular_en(db, periodo.id_payroll_period, user_id)
        resultado = hoja_en(db, periodo)
        db.rollback()
        return {**resultado, "simulated": True}


def _celda(ref: str, valor) -> str:
    if isinstance(valor, (int, float)):
        return f'<c r="{ref}"><v>{valor}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(valor))}</t></is></c>'


def _ref(col: int, fila: int) -> str:
    letras = ""
    col += 1
    while col:
        col, resto = divmod(col - 1, 26)
        letras = chr(65 + resto) + letras
    return f"{letras}{fila}"


def xlsx(id_payroll_period, titulos: dict) -> tuple[bytes, str]:
    """La hoja en un .xlsx minimo (sin dependencias: un .xlsx es un zip de XML)."""
    datos = hoja(id_payroll_period)
    ingresos = [c for c in datos["columns"] if c["type"] == "earning"]
    egresos = [c for c in datos["columns"] if c["type"] == "deduction"]
    encabezado = ([titulos["employee"], titulos["days"]] + [c["description"] for c in ingresos]
                  + [titulos["earnings"]] + [c["description"] for c in egresos]
                  + [titulos["deductions"], titulos["net"]])

    def renglon(nombre, dias, montos, tot):
        return ([nombre, dias] + [montos.get(str(c["id_payroll_concept"]), 0) for c in ingresos]
                + [tot["total_earnings"]] + [montos.get(str(c["id_payroll_concept"]), 0) for c in egresos]
                + [tot["total_deductions"], tot["net_pay"]])

    tabla = [encabezado] + [renglon(r["full_name"], r["days_worked"], r["amounts"], r) for r in datos["rows"]]
    tabla.append(renglon(titulos["totals"], "", datos["totals"], datos["totals"]))
    filas = "".join(f'<row r="{i + 1}">' + "".join(_celda(_ref(j, i + 1), v) for j, v in enumerate(f)) + "</row>"
                    for i, f in enumerate(tabla))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    archivos = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<?xml version="1.0" encoding="UTF-8"?><workbook {ns} {rel}><sheets>'
        f'<sheet name="Nomina {datos["id_payroll_period"]}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": f'<?xml version="1.0" encoding="UTF-8"?><worksheet {ns}><sheetData>{filas}</sheetData></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos.items():
            z.writestr(nombre, contenido)
    return buffer.getvalue(), f"nomina_periodo_{datos['id_payroll_period']}.xlsx"
