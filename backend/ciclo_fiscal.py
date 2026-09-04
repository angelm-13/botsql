"""Ciclo fiscal completo contra la base real, con timbrado simulado.

Recorre lo que hace una empresa con una venta: emitir, timbrar, descontar del
almacen, cobrar en parcialidades con su complemento de pago, devolver mercancia
con nota de credito y finalmente cancelar. En cada paso se comprueba el efecto,
no solo que la llamada no reviente.

El PAC es simulado a proposito. Lo que se prueba aqui es la logica propia -el
XML, los catalogos, la aritmetica, el efecto en existencias, las transiciones de
estado-; el proveedor real solo cambia de donde sale el timbre.
"""

from __future__ import annotations

import sys
import traceback
from decimal import Decimal


ACTOR = {"id_user": 1, "id_proyect": 8, "is_superuser": True}
fallos = []
paso_num = 0


def paso(titulo):
    global paso_num
    paso_num += 1
    print(f"\n{'=' * 72}\n{paso_num}. {titulo}\n{'=' * 72}")


def check(descripcion, condicion, detalle=""):
    """Imprime el detalle solo al fallar: al lado de un `ok` se lee como error."""
    if condicion:
        print(f"  ok  {descripcion}")
        return
    fallos.append(descripcion)
    print(f"  XX  {descripcion}{('  -> ' + str(detalle)) if detalle else ''}")


def main():
    from app import create_app
    app = create_app()

    from app.models.session import transaction_context
    from app.models import CustomerSupplier, Invoice, Product
    from app.models.inventory_stock import InventoryStock
    from app.services.manual_invoice_service import create_manual_invoice
    from app.services.stamping import FakeStampingProvider, stamp_invoice, preflight_invoice
    from app.services.cfdi_validation import validate_cfdi_xml
    from app.services.invoice_artifacts import invoice_xml_path
    from app.services.invoice_inventory_service import (
        apply_invoice_to_inventory, preview_invoice_inventory)
    from app.services.invoice_payment_service import (
        register_payment, invoice_statement, build_payment_complement)
    from app.services.invoice_credit_note_service import (
        create_credit_note, credit_note_summary, credit_note_relations)
    from app.services.invoice_cancellation_service import (
        preview_cancellation, request_cancellation, refresh_cancellation)

    with app.app_context():
        # ---------------------------------------------------------------
        paso("Datos de partida")
        with transaction_context() as db:
            emisor = db.query(CustomerSupplier).filter_by(is_principal=True).first()
            cliente = (db.query(CustomerSupplier)
                       .filter(CustomerSupplier.is_principal.is_(False))
                       .filter(CustomerSupplier.tax_id.notlike("XAXX%"))
                       .first())
            producto = db.get(Product, 100)
            existencia = (db.query(InventoryStock)
                          .filter_by(id_product=100)
                          .order_by(InventoryStock.quantity.desc()).first())
            id_location = existencia.id_location
            stock_inicial = int(existencia.quantity)
            clave_sat = getattr(producto, "clave_prod_serv", None) or getattr(
                producto, "sat_product_key", None) or "01010101"
            unidad_sat = getattr(producto, "clave_unidad", None) or "H87"
            print(f"  emisor      {emisor.id_customer_supplier} {emisor.name} ({emisor.tax_id})")
            print(f"  cliente     {cliente.id_customer_supplier} {cliente.name} ({cliente.tax_id})")
            print(f"  producto    {producto.id_product} clave SAT {clave_sat} unidad {unidad_sat}")
            print(f"  almacen     ubicacion {id_location}, existencia inicial {stock_inicial}")
            id_emisor = emisor.id_customer_supplier
            id_cliente = cliente.id_customer_supplier
            id_status = db.query(Invoice).order_by(Invoice.id_invoice.desc()).first().id_status

        CANTIDAD = 3
        PRECIO = Decimal("250.00")

        # ---------------------------------------------------------------
        paso("Emitir la factura de venta")
        resultado = create_manual_invoice({
            "id_proyect": 8,
            "id_customer_supplier": id_cliente,
            "id_issuer_customer_supplier": id_emisor,
            "id_status": id_status,
            "forma_pago": "99",          # por definir: se paga en parcialidades
            "metodo_pago": "PPD",        # parcialidades o diferido
            "uso_cfdi": "G03",
            "concepts": [{
                "description": "Prueba de ciclo fiscal completo",
                "quantity": CANTIDAD,
                "unit_price": str(PRECIO),
                "sat_product_key": clave_sat,
                "sat_unit_key": unidad_sat,
                "id_product": 100,
            }],
        }, ACTOR)
        id_factura = resultado["invoice"]["id_invoice"]
        total = Decimal(str(resultado["invoice"]["total"]))
        esperado = (PRECIO * CANTIDAD * Decimal("1.16")).quantize(Decimal("0.01"))
        print(f"  factura {id_factura}, total {total}")
        check("el total cuadra con el IVA del 16 por ciento", total == esperado,
              f"{total} vs {esperado}")
        check("metodo PPD acepta forma de pago 99 (por definir)", True)

        # ---------------------------------------------------------------
        paso("Revision previa antes de timbrar")
        previo = preflight_invoice(id_factura, ACTOR)
        errores = previo.get("errors") or []
        check("la factura pasa la revision previa sin errores", not errores, errores)
        for aviso in (previo.get("warnings") or []):
            print(f"      aviso: {aviso}")

        # ---------------------------------------------------------------
        paso("Timbrar con PAC simulado")
        timbre = stamp_invoice(id_factura, f"ciclo-{id_factura}", ACTOR, FakeStampingProvider())
        with transaction_context() as db:
            factura = db.get(Invoice, id_factura)
            uuid = factura.folio_fiscal
            estado = factura.invoice_status
        print(f"  UUID {uuid}, estado {estado}")
        check("la factura queda timbrada", estado == "timbrada", estado)
        check("guarda el folio fiscal (UUID)", bool(uuid))

        # ---------------------------------------------------------------
        paso("Validar el CFDI contra el Anexo 20")
        ruta = invoice_xml_path(id_factura, app.config.get("UPLOAD_ROOT"))
        check("el XML timbrado queda en disco", ruta.is_file(), ruta)
        if ruta.is_file():
            problemas = validate_cfdi_xml(ruta.read_bytes())
            check("el XML no tiene observaciones del Anexo 20", not problemas, problemas)

        # ---------------------------------------------------------------
        paso("Descontar del almacen (salida por venta)")
        vista = preview_invoice_inventory(id_factura, {}, ACTOR)
        print(f"  direccion {vista.get('invoice_direction')}, "
              f"movimiento {vista.get('movement_type')}, efecto {vista.get('effect')}")
        check("una venta se interpreta como salida",
              vista.get("invoice_direction") == "venta", vista.get("invoice_direction"))
        check("el efecto en el almacen es decrementar",
              vista.get("effect") == "decrementa", vista.get("effect"))
        check("el estado de la factura permite aplicarla",
              vista.get("can_apply") is True, vista.get("can_apply"))
        apply_invoice_to_inventory(id_factura, {"id_location": id_location}, ACTOR)
        with transaction_context() as db:
            tras_venta = int(db.query(InventoryStock)
                             .filter_by(id_product=100, id_location=id_location).first().quantity)
        print(f"  existencia {stock_inicial} -> {tras_venta}")
        check(f"descuenta exactamente {CANTIDAD} unidades",
              tras_venta == stock_inicial - CANTIDAD,
              f"{stock_inicial} - {CANTIDAD} != {tras_venta}")

        # ---------------------------------------------------------------
        paso("Cobrar en dos parcialidades con complemento de pago")
        primera = (total / 2).quantize(Decimal("0.01"))
        pago1 = register_payment(id_factura, {
            "idempotency_key": f"ciclo-pago1-{id_factura}",
            "amount": str(primera), "payment_form": "03", "paid_at": "2026-08-31",
        }, ACTOR)
        estado_cuenta = invoice_statement(id_factura, ACTOR)
        print(f"  primer pago {primera}, saldo {estado_cuenta.get('outstanding')}")
        check("el saldo baja a la mitad",
              Decimal(str(estado_cuenta["outstanding"])) == total - primera,
              estado_cuenta.get("outstanding"))

        complemento = build_payment_complement(pago1["payment"]["id_invoice_payment"], ACTOR)
        relacionado = complemento["related_document"]
        print(f"  complemento tipo {complemento['cfdi_type']}, uso {complemento['cfdi_use']}, "
              f"total {complemento['total']}")
        check("el complemento es un CFDI de tipo P", complemento["cfdi_type"] == "P")
        check("el cuerpo va en ceros: el importe vive en el complemento",
              complemento["subtotal"] == "0" and complemento["total"] == "0")
        check("usa el uso CFDI de pagos (CP01)", complemento["cfdi_use"] == "CP01")
        check("relaciona el documento original por UUID",
              relacionado["uuid"] == uuid, relacionado["uuid"])
        check("declara metodo de pago diferido (PPD)",
              relacionado["payment_method"] == "PPD", relacionado["payment_method"])
        check("es la parcialidad numero 1", int(relacionado["instalment"]) == 1,
              relacionado["instalment"])
        check("el saldo anterior es el total de la factura",
              Decimal(relacionado["previous_balance"]) == total, relacionado["previous_balance"])
        check("saldo anterior menos abono da el insoluto",
              Decimal(relacionado["previous_balance"]) - Decimal(relacionado["amount_paid"])
              == Decimal(relacionado["outstanding_balance"]),
              f"{relacionado['previous_balance']} - {relacionado['amount_paid']} "
              f"!= {relacionado['outstanding_balance']}")

        segunda = total - primera
        register_payment(id_factura, {
            "idempotency_key": f"ciclo-pago2-{id_factura}",
            "amount": str(segunda), "payment_form": "03", "paid_at": "2026-08-31",
        }, ACTOR)
        estado_cuenta = invoice_statement(id_factura, ACTOR)
        print(f"  segundo pago {segunda}, saldo {estado_cuenta.get('outstanding')}")
        check("queda saldada", Decimal(str(estado_cuenta["outstanding"])) == 0,
              estado_cuenta.get("outstanding"))

        try:
            register_payment(id_factura, {
                "idempotency_key": f"ciclo-pago3-{id_factura}",
                "amount": "1.00", "payment_form": "03", "paid_at": "2026-08-31",
            }, ACTOR)
            check("una factura saldada no acepta mas pagos", False, "acepto un pago de mas")
        except Exception as error:
            check("una factura saldada no acepta mas pagos", True,
                  getattr(error, "message_key", type(error).__name__))

        # ---------------------------------------------------------------
        paso("Nota de credito por devolucion de mercancia (relacion 03)")
        resumen = credit_note_summary(id_factura, ACTOR)
        print(f"  acreditable: {resumen.get('creditable')}")
        nota = create_credit_note(id_factura, {
            "idempotency_key": f"ciclo-nota-{id_factura}",
            "relation_type": "03",
            "id_status": id_status,
            "concepts": [{
                "description": "Devolucion de una unidad",
                "quantity": 1,
                "unit_price": str(PRECIO),
                "sat_product_key": clave_sat,
                "sat_unit_key": unidad_sat,
                "id_product": 100,
            }],
        }, ACTOR)
        id_nota = nota["credit_note"]["id_invoice"]
        print(f"  nota de credito {id_nota}, total {nota['credit_note']['total']}")
        check("la nota se marca como devolucion de mercancia",
              nota.get("returns_goods") is True, nota.get("returns_goods"))
        check("la relacion declara el tipo 03",
              nota["relation"]["relation_type"] == "03", nota["relation"]["relation_type"])
        check("la relacion apunta al UUID de la factura original",
              nota["relation"]["related_uuid"] == uuid, nota["relation"]["related_uuid"])

        # El almacen lo mueve el propio servicio al crear la nota: la devolucion
        # de mercancia es parte de la nota, no un paso aparte que alguien pueda
        # olvidar.
        movimientos = nota.get("inventory") or []
        check("la nota genera el movimiento de entrada al almacen",
              len(movimientos) > 0, movimientos)
        with transaction_context() as db:
            tras_nota = int(db.query(InventoryStock)
                            .filter_by(id_product=100, id_location=id_location).first().quantity)
        print(f"  existencia {tras_venta} -> {tras_nota}")
        check("la devolucion regresa 1 unidad al almacen",
              tras_nota == tras_venta + 1, f"{tras_venta} + 1 != {tras_nota}")

        stamp_invoice(id_nota, f"ciclo-nota-{id_nota}", ACTOR, FakeStampingProvider())

        ruta_nota = invoice_xml_path(id_nota, app.config.get("UPLOAD_ROOT"))
        if ruta_nota.is_file():
            xml_nota = ruta_nota.read_bytes()
            texto = xml_nota.decode("utf-8", errors="ignore")
            check("la nota es un CFDI de egreso (tipo E)", 'TipoDeComprobante="E"' in texto)
            check("declara la relacion 03 (devolucion de mercancia)",
                  'TipoRelacion="03"' in texto)
            check("apunta al UUID de la factura original", uuid in texto)
            obs = validate_cfdi_xml(xml_nota)
            check("la nota pasa la validacion del Anexo 20", not obs, obs)

        # credit_note_relations responde por la NOTA (con que se relaciona);
        # que la factura conozca sus notas se consulta en su resumen.
        relaciones = credit_note_relations(id_nota, ACTOR)
        check("la nota declara su relacion con la factura",
              any(r["uuid"] == uuid and r["relation_type"] == "03"
                  for r in relaciones["related_documents"]),
              relaciones)

        resumen2 = credit_note_summary(id_factura, ACTOR)
        check("la factura conoce su nota de credito",
              any(str(n["id_invoice"]) == str(id_nota) for n in resumen2["credit_notes"]),
              resumen2["credit_notes"])
        check("lo acreditable baja en el importe de la nota",
              Decimal(resumen2["creditable"]) == total - Decimal(resumen2["credited"]),
              f"{resumen2['creditable']} vs {total} - {resumen2['credited']}")

        # ---------------------------------------------------------------
        paso("Cancelar el CFDI ante el SAT")
        try:
            request_cancellation(
                id_factura,
                {"idempotency_key": f"ciclo-cancel-malo-{id_factura}", "motive": "01"},
                ACTOR, FakeStampingProvider())
            check("el motivo 01 exige el UUID que sustituye", False, "acepto 01 sin sustitucion")
        except Exception as error:
            check("el motivo 01 exige el UUID que sustituye", True,
                  getattr(error, "message_key", type(error).__name__))

        vista_cancel = preview_cancellation(id_factura, {"motive": "02"}, ACTOR)
        print(f"  timbrada {vista_cancel['is_stamped']}, "
              f"puede solicitar {vista_cancel['can_request']}, "
              f"movimientos a revertir {vista_cancel['inventory_movements_to_reverse']}")
        check("la vista previa la reconoce como timbrada y cancelable",
              vista_cancel["is_stamped"] and vista_cancel["can_request"])
        check("anticipa que hay movimientos de almacen que revertir",
              vista_cancel["inventory_movements_to_reverse"] > 0,
              vista_cancel["inventory_movements_to_reverse"])
        cancelacion = request_cancellation(
            id_factura,
            {"idempotency_key": f"ciclo-cancel-{id_factura}", "motive": "02"},
            ACTOR, FakeStampingProvider())
        registro = cancelacion.get("cancellation", cancelacion)
        print(f"  estado de la cancelacion: {registro.get('status')}")
        check("la cancelacion queda solicitada o en proceso",
              registro.get("status") in {"solicitada", "en_proceso", "cancelado"},
              registro.get("status"))

        actualizada = refresh_cancellation(registro["id_invoice_cancellation"], ACTOR,
                                          FakeStampingProvider())
        reg2 = actualizada.get("cancellation", actualizada)
        with transaction_context() as db:
            estado_final = db.get(Invoice, id_factura).invoice_status
            tras_cancel = int(db.query(InventoryStock)
                              .filter_by(id_product=100, id_location=id_location).first().quantity)
        print(f"  tras consultar al SAT: {reg2.get('status')}, factura {estado_final}")
        print(f"  existencia {tras_nota} -> {tras_cancel}")
        if reg2.get("status") in {"cancelado"}:
            check("cancelada, el almacen recibe de vuelta lo facturado",
                  tras_cancel == tras_nota + CANTIDAD,
                  f"{tras_nota} + {CANTIDAD} != {tras_cancel}")
            check("la factura queda cancelada", estado_final == "cancelada", estado_final)
        else:
            check("mientras el SAT no confirma, el almacen NO se toca",
                  tras_cancel == tras_nota, f"{tras_nota} != {tras_cancel}")

        # ---------------------------------------------------------------
        paso("Resumen")
        print(f"  factura {id_factura}  nota de credito {id_nota}")
        print(f"  existencia del producto 100 en ubicacion {id_location}: "
              f"{stock_inicial} -> {tras_cancel}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        fallos.append("el ciclo se interrumpio con una excepcion")

    print(f"\n{'=' * 72}")
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones:")
        for f in fallos:
            print(f"  - {f}")
        sys.exit(1)
    print("Todas las comprobaciones del ciclo fiscal pasaron.")
