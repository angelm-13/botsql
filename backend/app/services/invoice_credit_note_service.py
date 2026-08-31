"""Notas de credito: el CFDI de egreso que corrige una factura.

Una nota de credito no es una factura negativa ni una cancelacion parcial. Es
un comprobante propio, de tipo Egreso, con sus importes en positivo, que se
relaciona con la factura que corrige. La factura original se queda como esta;
lo que cambia es el neto entre ambas.

Dos usos, que el SAT distingue por el tipo de relacion, y que aqui se tratan
distinto a proposito:

* **01, nota de credito.** Un descuento o una bonificacion posterior. El
  cliente se queda con la mercancia, asi que el almacen NO se toca.
* **03, devolucion de mercancia.** El cliente regresa lo que compro. Ahi si
  vuelve al almacen, con la misma mecanica del reverso por cancelacion.

Confundirlas es el error caro: aplicar un descuento y ademas devolver la
mercancia al almacen infla la existencia con producto que nunca regreso.

Reglas que se aplican:

* La factura original tiene que estar timbrada y no cancelada.
* No se acredita mas de lo que queda por acreditar: total de la factura menos
  lo ya acreditado por notas anteriores.
* Misma moneda y mismo receptor que la factura original.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select

from app.models.cfdi_relation import CfdiRelation
from app.models.invoice import Invoice
from app.models.inventory_ledger import InventoryLedger
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.session import transaction_context
from app.services.inventory_service import apply_movement_in_session
from app.services.invoice_catalogs import (
    TIPO_RELACION_DEVUELVE_MERCANCIA,
    TIPO_RELACION_NOTA_CREDITO,
)
from app.utils.errors import AppError


MONEY = Decimal("0.01")

# Tipo de comprobante de una nota de credito.
CREDIT_NOTE_TYPE = "E"
# Uso de CFDI que le corresponde: devoluciones, descuentos o bonificaciones.
CREDIT_NOTE_CFDI_USE = "G02"

# Estatus de factura sobre los que tiene sentido acreditar.
CREDITABLE_STATUSES = {"timbrada", "pendiente", "parcial", "pagada"}


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def _authorize(invoice, user_data):
    if not invoice.id_proyect:
        raise AppError("errors.resource_scope_missing", 409)
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    if not unrestricted and str(actor_project) != str(invoice.id_proyect):
        raise AppError("errors.permission_denied", 403)


def _load_invoice(db, invoice_id, user_data) -> Invoice:
    invoice = db.get(Invoice, int(invoice_id))
    if not invoice or invoice.deletion_date is not None:
        raise AppError("errors.resource_not_found", 404)
    _authorize(invoice, user_data)
    return invoice


def _credit_notes(db, invoice):
    """Notas de credito ya emitidas contra esta factura."""
    if not str(invoice.folio_fiscal or "").strip():
        return []
    relaciones = db.scalars(
        select(CfdiRelation)
        .where(CfdiRelation.related_uuid == invoice.folio_fiscal)
        .where(CfdiRelation.relation_type.in_(TIPO_RELACION_NOTA_CREDITO))
    ).all()
    ids = [relacion.id_invoice for relacion in relaciones]
    if not ids:
        return []
    return db.scalars(
        select(Invoice)
        .where(Invoice.id_invoice.in_(ids))
        .where(Invoice.deletion_date.is_(None))
        .where(Invoice.invoice_status != "cancelada")
        .order_by(Invoice.id_invoice)
    ).all()


def _credited_so_far(db, invoice) -> Decimal:
    return _money(sum((_money(nota.total) for nota in _credit_notes(db, invoice)), Decimal("0")))


def _validate_relation_type(value) -> str:
    tipo = str(value or "").strip()
    if tipo not in TIPO_RELACION_NOTA_CREDITO:
        raise AppError(
            "errors.credit_note_relation_type_invalid",
            400,
            {"field": "relation_type", "allowed": sorted(TIPO_RELACION_NOTA_CREDITO)},
        )
    return tipo


def _require_creditable(invoice):
    if not str(invoice.folio_fiscal or "").strip():
        raise AppError(
            "errors.credit_note_requires_stamped_invoice",
            409,
            {"invoice_status": invoice.invoice_status},
        )
    estatus = str(invoice.invoice_status or "").strip().lower()
    if estatus == "cancelada":
        raise AppError("errors.credit_note_invoice_cancelled", 409, {"invoice_status": estatus})
    if estatus not in CREDITABLE_STATUSES:
        raise AppError(
            "errors.credit_note_invoice_status_not_allowed",
            409,
            {"invoice_status": invoice.invoice_status, "allowed": sorted(CREDITABLE_STATUSES)},
        )


def credit_note_summary(invoice_id, user_data) -> dict:
    """Cuanto se puede acreditar de esta factura y que notas ya tiene."""
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        total = _money(invoice.total)
        acreditado = _credited_so_far(db, invoice)
        timbrada = bool(str(invoice.folio_fiscal or "").strip())
        cancelada = str(invoice.invoice_status or "").strip().lower() == "cancelada"
        return {
            "id_invoice": invoice.id_invoice,
            "folio_fiscal": invoice.folio_fiscal,
            "invoice_status": invoice.invoice_status,
            "currency": invoice.currency,
            "total": format(total, "f"),
            "credited": format(acreditado, "f"),
            "creditable": format(max(total - acreditado, Decimal("0")), "f"),
            "relation_types": sorted(TIPO_RELACION_NOTA_CREDITO),
            "returns_goods_relation": TIPO_RELACION_DEVUELVE_MERCANCIA,
            "credit_notes": [
                {
                    "id_invoice": nota.id_invoice,
                    "folio_fiscal": nota.folio_fiscal,
                    "total": format(_money(nota.total), "f"),
                    "invoice_status": nota.invoice_status,
                }
                for nota in _credit_notes(db, invoice)
            ],
            "can_credit": timbrada and not cancelada and (total - acreditado) > 0,
        }


def _build_concepts(payload) -> list[dict]:
    conceptos = payload.get("concepts") or payload.get("conceptos") or []
    if not conceptos:
        raise AppError("errors.credit_note_concepts_required", 400, {"field": "concepts"})
    return conceptos


def _origin_locations(db, original) -> dict[int, int]:
    """Producto -> ubicacion de la que salio al facturar.

    La mercancia devuelta tiene que volver al almacen del que salio. Antes se
    pasaba `id_location=None`, que resuelve el almacen por omision: con un solo
    almacen daba igual, pero con varios la devolucion acreditaba uno distinto
    del que despacho. El total cuadraba y la ubicacion no, que es la peor de
    las dos: nadie revisa un total correcto, y quien va por la mercancia la
    busca en un almacen que no la tiene mientras otro carga un sobrante que
    nunca recibio.

    Se lee del libro de inventario, igual que hace el reverso por cancelacion.
    """
    lineas = [
        str(linea.id_invoice_material_service)
        for linea in db.scalars(
            select(InvoiceMaterialService)
            .where(InvoiceMaterialService.id_invoice == original.id_invoice)
            .where(InvoiceMaterialService.deletion_date.is_(None))
        ).all()
    ]
    if not lineas:
        return {}

    salidas = db.scalars(
        select(InventoryLedger)
        .where(InventoryLedger.reference_type == "invoice_line")
        .where(InventoryLedger.reference_id.in_(lineas))
        .where(InventoryLedger.quantity_delta < 0)
        .order_by(InventoryLedger.id_inventory_ledger)
    ).all()
    # El ultimo gana si un producto salio de varias ubicaciones en la misma
    # factura: no hay forma de saber de que caja venia cada pieza devuelta, y
    # elegir siempre la misma al menos es predecible.
    return {int(salida.id_product): int(salida.id_location) for salida in salidas}


def _return_goods(db, credit_note, original, user_data, conceptos_creados):
    """Devuelve al almacen la mercancia que el cliente regresa.

    Solo con relacion 03. Se apoya en las partidas de la propia nota, no en las
    de la factura original: el cliente puede regresar una parte.
    """
    origenes = _origin_locations(db, original)
    movimientos = []
    for linea in conceptos_creados:
        if not linea.id_product:
            continue
        cantidad = _money(linea.quantity)
        if cantidad <= 0 or cantidad != cantidad.to_integral_value():
            # La existencia se lleva en piezas enteras; lo fraccionario se
            # reporta en lugar de redondearse a la callada.
            movimientos.append({
                "id_invoice_material_service": linea.id_invoice_material_service,
                "skipped": "quantity_not_whole_units",
            })
            continue
        movimiento, _ = apply_movement_in_session(
            db,
            linea.id_product,
            user_data,
            movement_type="return",
            quantity_delta=int(cantidad),
            idempotency_key=f"credit-{credit_note.id_invoice}-line-{linea.id_invoice_material_service}",
            # Si la factura original nunca se aplico al almacen no hay origen
            # que respetar, y entonces si toca el almacen por omision.
            id_location=origenes.get(int(linea.id_product)),
            reference_type="invoice_line",
            reference_id=str(linea.id_invoice_material_service),
            reason=f"Devolucion por nota de credito de la factura {original.id_invoice}",
        )
        movimientos.append(movimiento)
    return movimientos


def create_credit_note(invoice_id, payload, user_data) -> dict:
    """Emite una nota de credito contra una factura timbrada."""
    from app.services.manual_invoice_service import create_manual_invoice, preview_manual_invoice

    payload = dict(payload or {})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key or len(key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})

    relation_type = _validate_relation_type(payload.get("relation_type"))

    with transaction_context() as db:
        # Repetir la llamada no emite una segunda nota: se devuelve la que ya
        # se creo con esa llave.
        previa = db.scalars(
            select(CfdiRelation).where(CfdiRelation.idempotency_key == key)
        ).first()
        if previa:
            nota = db.get(Invoice, previa.id_invoice)
            return {
                "credit_note": nota.serialize(),
                "relation": previa.serialize(),
                "inventory": [],
                "returns_goods": previa.relation_type == TIPO_RELACION_DEVUELVE_MERCANCIA,
                "created": False,
            }

        original = _load_invoice(db, invoice_id, user_data)
        _require_creditable(original)
        total_factura = _money(original.total)
        acreditado = _credited_so_far(db, original)
        disponible = total_factura - acreditado
        if disponible <= 0:
            raise AppError(
                "errors.credit_note_nothing_left_to_credit",
                409,
                {"total": format(total_factura, "f"), "credited": format(acreditado, "f")},
            )
        datos_originales = {
            "id_proyect": original.id_proyect,
            "id_customer_supplier": original.id_customer_supplier,
            "id_issuer_customer_supplier": original.id_issuer_customer_supplier,
            "id_status": original.id_status,
            "currency": original.currency or "MXN",
            "folio_fiscal": original.folio_fiscal,
            "id_invoice": original.id_invoice,
            # Un CFDI de egreso exige forma y metodo de pago igual que uno de
            # ingreso. Sin ellos la nota se creaba pero no pasaba su propia
            # revision previa, asi que no se podia timbrar: un documento que
            # nace invalido. Se heredan de la factura que corrige, que es la
            # practica habitual, y quien lo necesite los puede sobreescribir.
            "forma_pago": original.forma_pago,
            "metodo_pago": original.metodo_pago,
        }

    conceptos = _build_concepts(payload)

    # El importe se calcula con la misma maquinaria que una factura normal, de
    # modo que impuestos y redondeos salgan identicos.
    vista = preview_manual_invoice({**payload, "concepts": conceptos})
    if not vista["can_create"]:
        raise AppError("errors.credit_note_validation_failed", 400, {"errors": vista["errors"]})
    total_nota = _money(vista["total"])
    if total_nota <= 0:
        raise AppError("errors.credit_note_amount_must_be_positive", 400, {"total": vista["total"]})
    if total_nota > disponible:
        raise AppError(
            "errors.credit_note_exceeds_creditable",
            409,
            {"amount": format(total_nota, "f"), "creditable": format(disponible, "f")},
        )

    creacion = {
        **payload,
        "id_proyect": datos_originales["id_proyect"],
        "id_customer_supplier": datos_originales["id_customer_supplier"],
        "id_issuer_customer_supplier": datos_originales["id_issuer_customer_supplier"],
        "id_status": datos_originales["id_status"],
        "currency": datos_originales["currency"],
        "concepts": conceptos,
        "tipo_de_comprobante": CREDIT_NOTE_TYPE,
        "uso_cfdi": payload.get("uso_cfdi") or CREDIT_NOTE_CFDI_USE,
        "forma_pago": payload.get("forma_pago") or datos_originales["forma_pago"],
        "metodo_pago": payload.get("metodo_pago") or datos_originales["metodo_pago"],
        "note": (payload.get("note") or f"Nota de credito de la factura {invoice_id}")[:300],
    }
    creacion.pop("idempotency_key", None)
    creacion.pop("relation_type", None)
    resultado = create_manual_invoice(creacion, user_data)
    nota_id = resultado["invoice"]["id_invoice"]

    with transaction_context() as db:
        nota = db.get(Invoice, nota_id)
        original = db.get(Invoice, datos_originales["id_invoice"])
        relacion = CfdiRelation(
            id_invoice=nota.id_invoice,
            relation_type=relation_type,
            related_uuid=datos_originales["folio_fiscal"],
            id_related_invoice=original.id_invoice,
            idempotency_key=key,
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(relacion)
        db.flush()

        movimientos = []
        if relation_type == TIPO_RELACION_DEVUELVE_MERCANCIA:
            lineas = db.scalars(
                select(InvoiceMaterialService)
                .where(InvoiceMaterialService.id_invoice == nota.id_invoice)
                .where(InvoiceMaterialService.deletion_date.is_(None))
            ).all()
            movimientos = _return_goods(db, nota, original, user_data, lineas)

        return {
            "credit_note": nota.serialize(),
            "relation": relacion.serialize(),
            "inventory": movimientos,
            "returns_goods": relation_type == TIPO_RELACION_DEVUELVE_MERCANCIA,
            "created": True,
        }


def credit_note_relations(invoice_id, user_data) -> dict:
    """Con que comprobantes se relaciona esta nota, para armar el XML."""
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        relaciones = db.scalars(
            select(CfdiRelation)
            .where(CfdiRelation.id_invoice == invoice.id_invoice)
            .order_by(CfdiRelation.id_cfdi_relation)
        ).all()
        return {
            "id_invoice": invoice.id_invoice,
            "related_documents": [
                {"relation_type": r.relation_type, "uuid": r.related_uuid}
                for r in relaciones
            ],
        }
