"""Facturar una venta que ya ocurrio en otro modulo.

Por que existe
--------------
La decision es que haya un solo modulo de facturacion. El punto de venta y el
restaurante cobran, pero no timbran: cuando un cliente pide factura de su
compra, el CFDI lo emite TYAKXA.

Lo que este servicio hace es traducir: toma una venta ya cobrada en su modulo y
la convierte en el borrador de una factura del nucleo, con sus partidas y sus
importes. De ahi en adelante es una factura como cualquier otra -se timbra, se
cancela, se le hace nota de credito- con una sola diferencia, que es la
importante.

La diferencia: no vuelve a mover el almacen
-------------------------------------------
La venta ya descontó del inventario al cobrarse. La factura nace con
`source_module` y `source_reference`, y con eso `invoice_inventory_service` sabe
que esta factura DOCUMENTA un movimiento en vez de causarlo. Sin esa marca, el
producto saldria dos veces del almacen por haberse vendido una vez, y el
descuadre no avisaria: las dos operaciones son correctas por separado.

Las claves del SAT
------------------
Un CFDI necesita ClaveProdServ y ClaveUnidad por concepto, y los productos del
punto de venta no las traen. No se inventan: se piden a quien factura, con una
pareja por omision para toda la venta y la posibilidad de fijarlas por producto.
Rellenarlas con un valor cualquiera produciria comprobantes que el PAC acepta y
la autoridad objeta despues, que es la peor forma de fallar.

Una venta se factura una sola vez
---------------------------------
Antes de crear nada se busca si ya existe una factura viva de esa venta. Dos
CFDI de la misma venta es un problema fiscal, no un duplicado cosmetico.

Identificador contra folio
--------------------------
La venta se pide por su identificador, que es como la direcciona la API del
modulo, pero se guarda por su FOLIO. El folio es lo que el libro de inventario
anoto al descontar y lo que el cliente tiene impreso en su ticket; el
identificador solo existe dentro de la base del modulo. Guardar el identificador
dejaria la factura sin forma de llegar a los movimientos que documenta.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.models.invoice import Invoice
from app.models.session import transaction_context
from app.utils.errors import AppError


MODULOS = ("pos", "restaurante")

# Claves genericas del catalogo del SAT, para cuando quien factura no fija otras.
# `01010101` es "No existe en el catalogo" y `H87` es Pieza: son validas y
# honestas para una venta de mostrador, y se pueden precisar por producto.
CLAVE_PRODUCTO_POR_OMISION = "01010101"
CLAVE_UNIDAD_POR_OMISION = "H87"


def _decimal(valor, campo: str) -> Decimal:
    try:
        return Decimal(str(valor))
    except (TypeError, ValueError, InvalidOperation):
        raise AppError("errors.invalid_field", 400, {"field": campo})


def factura_de_la_venta(db, modulo: str, referencia: str):
    """La factura viva de esa venta, si ya se facturo."""
    return db.scalars(
        select(Invoice).where(
            Invoice.source_module == modulo,
            Invoice.source_reference == str(referencia),
            Invoice.deletion_date.is_(None),
        ).order_by(Invoice.id_invoice)
    ).first()


def _venta_del_pos(referencia: str, user_data: dict) -> dict:
    """La venta y sus renglones, ahora leidos de esta misma base.

    Antes se pedian al otro sistema por HTTP (`GET sales/<id>/receipt`), y esa
    llamada podia fallar por red, por token caducado o porque el POS estuviera
    apagado -- de ahi el `errors.pos_unreachable` que ya no hace falta. Con la
    venta en esta base es una consulta mas, dentro de la misma transaccion que
    despues escribe la factura.

    Se leen los renglones y no solo el resumen porque una factura necesita las
    partidas, y se toman los importes tal como se cobraron: la factura debe
    decir exactamente lo que el cliente tiene impreso en la mano.
    """
    from app.models.pos import PosSale, PosSaleItem
    from app.models.product import Product
    from app.models.session import transaction_context

    with transaction_context() as db:
        venta = db.get(PosSale, int(referencia)) if str(referencia).isdigit() else None
        if venta is None:
            venta = db.scalars(
                select(PosSale).where(
                    PosSale.folio == str(referencia),
                    PosSale.deletion_date.is_(None),
                )
            ).first()
        if venta is None or venta.deletion_date is not None:
            raise AppError("errors.not_found", 404,
                           {"entity": "sale", "reference": referencia})

        renglones = db.execute(
            select(PosSaleItem, Product.descripcion)
            .join(Product, Product.id_product == PosSaleItem.id_product)
            .where(PosSaleItem.id_pos_sale == venta.id_pos_sale,
                   PosSaleItem.deletion_date.is_(None))
            .order_by(PosSaleItem.id_pos_sale_item)
        ).all()

        return {
            "folio": venta.folio,
            "total": float(venta.total or 0),
            "items": [
                {
                    "product_name": descripcion,
                    "quantity": str(fila.quantity),
                    "unit_price": str(fila.unit_price),
                    "discount_amount": str(fila.discount_amount or 0),
                }
                for fila, descripcion in renglones
            ],
        }


def _partidas_del_pos(venta: dict, payload: dict) -> list[dict]:
    """Traduce los renglones de la venta a conceptos de factura.

    El importe unitario sale de la venta y no se recalcula: el POS ya decidio
    cuanto cobro, descuentos y promociones incluidos, y recalcular aqui produce
    una factura que no coincide con el ticket que el cliente tiene en la mano.
    """
    renglones = venta.get("items") or venta.get("lines") or []
    if not renglones:
        raise AppError("errors.sale_without_lines", 409, {"reference": venta.get("folio")})

    claves = payload.get("sat_keys") or {}
    clave_producto = str(payload.get("sat_product_key") or CLAVE_PRODUCTO_POR_OMISION)
    clave_unidad = str(payload.get("sat_unit_key") or CLAVE_UNIDAD_POR_OMISION)

    conceptos = []
    for indice, renglon in enumerate(renglones):
        nombre = str(renglon.get("product_name") or renglon.get("name") or "").strip()
        if not nombre:
            raise AppError("errors.sale_line_without_description", 409, {"index": indice})
        por_producto = claves.get(nombre) or {}
        conceptos.append({
            "description": nombre[:200],
            "sat_product_key": str(por_producto.get("sat_product_key") or clave_producto),
            "sat_unit_key": str(por_producto.get("sat_unit_key") or clave_unidad),
            "quantity": str(_decimal(renglon.get("quantity"), f"items.{indice}.quantity")),
            "unit_price": str(_decimal(renglon.get("unit_price"), f"items.{indice}.unit_price")),
            "discount": str(_decimal(renglon.get("discount_amount") or 0, f"items.{indice}.discount")),
            # El enum de la partida solo acepta product, service o custom. Un
            # renglon de mostrador es un producto; de donde viene la venta lo
            # dice `source_module` en la factura, no el tipo de la partida.
            "line_type": "product",
        })
    return conceptos


def preparar(modulo: str, id_venta: str, payload: dict, user_data: dict) -> dict:
    """Lo que se facturaria de esa venta, sin crear nada.

    Sirve para que la pantalla pueda mostrar las partidas y los importes antes
    de emitir, y para avisar si esa venta ya tiene factura.
    """
    if modulo not in MODULOS:
        raise AppError("errors.invalid_field", 400,
                       {"field": "source_module", "allowed": list(MODULOS)})
    if modulo == "restaurante":
        # El restaurante todavia no expone sus ventas por aqui. Se dice en vez
        # de devolver una lista vacia, que se leeria como "no hay nada que
        # facturar".
        raise AppError("errors.not_implemented", 501, {"source_module": modulo})

    venta = _venta_del_pos(id_venta, user_data)
    conceptos = _partidas_del_pos(venta, payload or {})

    # El folio, no el identificador: es lo que el libro anoto al descontar.
    referencia = str(venta.get("folio") or "").strip()
    if not referencia:
        raise AppError("errors.sale_without_folio", 409, {"sale_id": id_venta})

    with transaction_context() as db:
        existente = factura_de_la_venta(db, modulo, referencia)
        ya_facturada = existente.id_invoice if existente else None

    return {
        "source_module": modulo,
        "source_reference": referencia,
        "sale_id": id_venta,
        "sale": {
            "folio": venta.get("folio"),
            "total": venta.get("total"),
            "paid_at": venta.get("paid_at"),
            "customer_name": venta.get("customer_name"),
        },
        "concepts": conceptos,
        "already_invoiced": ya_facturada,
        "can_invoice": ya_facturada is None,
        # Se dice en la respuesta y no solo en el codigo: quien factura tiene
        # que saber que esta factura no va a mover el almacen, y por que.
        "moves_inventory": False,
        "inventory_note": "sale_already_moved_inventory",
    }


def facturar(modulo: str, id_venta: str, payload: dict, user_data: dict) -> dict:
    """Crea la factura del nucleo que documenta esa venta.

    Los datos fiscales del receptor los pone quien factura: el punto de venta no
    los tiene, porque una venta de mostrador se cobra sin pedirlos y la factura
    se pide despues.
    """
    from app.services.manual_invoice_service import create_manual_invoice

    preparado = preparar(modulo, id_venta, payload, user_data)
    referencia = preparado["source_reference"]
    if not preparado["can_invoice"]:
        raise AppError("errors.sale_already_invoiced", 409, {
            "source_reference": referencia,
            "id_invoice": preparado["already_invoiced"],
        })

    cuerpo = dict(payload or {})
    cuerpo["concepts"] = preparado["concepts"]
    cuerpo["source_module"] = modulo
    cuerpo["source_reference"] = referencia
    # El folio del comprobante lo asigna la facturacion; el de la venta viaja
    # como referencia, no como folio fiscal.
    cuerpo.pop("folio", None)

    creada = create_manual_invoice(cuerpo, user_data)
    creada["source_module"] = modulo
    creada["source_reference"] = referencia
    creada["moves_inventory"] = False
    creada["inventory_note"] = "sale_already_moved_inventory"
    return creada
