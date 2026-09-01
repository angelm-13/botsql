"""Refleja en el inventario del nucleo lo que el punto de venta vende.

Por que hace falta
------------------
La decision es que haya un solo inventario para todos los proyectos. El POS es
el unico que no puede compartir tabla, porque corre contra su propia base; para
los demas basta con anotar el modulo en el movimiento.

Asi que aqui el POS no comparte tabla pero si comparte saldo: cuando una venta
se cobra, se escribe el movimiento correspondiente en el libro del nucleo, con
`source_module = 'pos'`. Quien pregunte cuanto hay obtiene una sola respuesta, y
quien pregunte de donde salio tambien.

Lo que se decidio no hacer
--------------------------
**No se adivina la correspondencia entre productos.** Emparejar por nombre
parece comodo hasta que dos se llaman casi igual y las ventas descuentan del
renglon equivocado sin que nada avise. Hace falta un enlace explicito en
`pos_product_link`.

**Un producto sin enlace no descuenta, y se dice.** Un inventario que descuenta
del producto equivocado es peor que uno que no descuenta, porque el primero se
ve sano.

**Si el reflejo falla, la venta no se deshace.** La venta ya ocurrio en el POS y
el dinero ya se cobro; revertirla porque el nucleo no pudo anotar el movimiento
seria dejar al cliente sin su compra por un problema de registro. Lo que no se
pudo reflejar se devuelve en la respuesta para que quede a la vista, y el
descuadre se ve en la conciliacion.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.pos_product_link import PosProductLink
from app.models.session import transaction_context
from app.services.inventory_service import apply_movement_in_session
from app.utils.errors import AppError


MODULO = "pos"


def _enlaces(db, ids_del_pos):
    filas = db.scalars(
        select(PosProductLink).where(
            PosProductLink.pos_product_id.in_([str(i) for i in ids_del_pos]),
            PosProductLink.deletion_date.is_(None),
        )
    ).all()
    return {fila.pos_product_id: fila for fila in filas}


def _unidades(cantidad):
    """Piezas enteras. Lo fraccionario se reporta en lugar de redondearse."""
    try:
        numero = float(cantidad)
    except (TypeError, ValueError):
        return None
    if numero <= 0 or numero != int(numero):
        return None
    return int(numero)


def reflejar_venta(venta, user_data) -> dict:
    """Descuenta del inventario del nucleo lo que el POS acaba de vender.

    `venta` es la respuesta del POS al cobrar. Devuelve el detalle de lo
    reflejado y lo que quedo sin reflejar, con el motivo.
    """
    partidas = venta.get("items") or venta.get("lines") or []
    folio = str(venta.get("folio") or venta.get("id") or "").strip()
    if not partidas:
        return {"reflected": [], "skipped": [], "folio": folio}

    reflejadas, omitidas = [], []
    with transaction_context() as db:
        enlaces = _enlaces(db, [p.get("product_id") for p in partidas if p.get("product_id")])

        for partida in partidas:
            id_pos = str(partida.get("product_id") or "")
            enlace = enlaces.get(id_pos)
            if enlace is None:
                omitidas.append({
                    "pos_product_id": id_pos,
                    "name": partida.get("name"),
                    "reason": "product_not_linked",
                })
                continue

            unidades = _unidades(partida.get("quantity"))
            if unidades is None:
                omitidas.append({
                    "pos_product_id": id_pos,
                    "name": partida.get("name"),
                    "reason": "quantity_not_whole_units",
                })
                continue

            try:
                movimiento, creado = apply_movement_in_session(
                    db,
                    enlace.id_product,
                    user_data,
                    movement_type="issue",
                    quantity_delta=-unidades,
                    # La llave lleva el folio de la venta: reintentar el reflejo
                    # de la misma venta no descuenta dos veces.
                    idempotency_key=f"pos-{folio}-{id_pos}"[:90],
                    id_location=enlace.id_location,
                    reference_type="invoice",
                    reference_id=folio,
                    reason=f"Venta {folio} del punto de venta",
                    source_module=MODULO,
                )
            except AppError as error:
                # Falta de existencia, sobre todo. No se revierte la venta: ya
                # se cobro. Se deja constancia para que el descuadre se vea.
                omitidas.append({
                    "pos_product_id": id_pos,
                    "id_product": enlace.id_product,
                    "name": partida.get("name"),
                    "reason": error.message_key,
                })
                continue

            reflejadas.append({
                "pos_product_id": id_pos,
                "id_product": enlace.id_product,
                "units": unidades,
                "already_applied": not creado,
                "id_inventory_ledger": movimiento.get("id_inventory_ledger"),
            })

    return {"folio": folio, "reflected": reflejadas, "skipped": omitidas}


def enlazar(payload, user_data) -> dict:
    """Declara que producto del nucleo corresponde a uno del punto de venta."""
    from app.models.product import Product
    from app.services.inventory_service import _authorize

    id_pos = str(payload.get("pos_product_id") or "").strip()
    if not id_pos:
        raise AppError("errors.required_field", 400, {"field": "pos_product_id"})

    with transaction_context() as db:
        producto = db.get(Product, int(payload.get("id_product") or 0))
        if not producto or producto.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _authorize(db, producto, user_data)

        ya = db.scalars(
            select(PosProductLink).where(PosProductLink.pos_product_id == id_pos)
        ).first()
        if ya and ya.deletion_date is None:
            raise AppError("errors.pos_product_already_linked", 409,
                           {"pos_product_id": id_pos, "id_product": ya.id_product})

        enlace = ya or PosProductLink(pos_product_id=id_pos, created_by=int(user_data.get("id_user") or 0))
        enlace.id_product = producto.id_product
        enlace.pos_product_name = str(payload.get("pos_product_name") or "")[:200] or None
        enlace.id_location = int(payload.get("id_location") or producto.id_location)
        enlace.deletion_date = None
        db.add(enlace)
        db.flush()
        return enlace.serialize()


def enlaces(user_data) -> dict:
    """Los enlaces declarados, para ver que producto del POS descuenta de cual."""
    with transaction_context() as db:
        filas = db.scalars(
            select(PosProductLink).where(PosProductLink.deletion_date.is_(None))
            .order_by(PosProductLink.id_pos_product_link)
        ).all()
        return {"items": [f.serialize() for f in filas], "total": len(filas)}
