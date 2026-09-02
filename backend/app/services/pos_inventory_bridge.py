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


def reflejar_venta(venta, user_data, solicitud=None) -> dict:
    """Descuenta del inventario del nucleo lo que el POS acaba de vender.

    `venta` es la respuesta del POS al cobrar; `solicitud` es el cuerpo que se
    le mando.

    De donde salen las partidas y por que
    -------------------------------------
    La respuesta del POS es de pantalla: sus renglones traen `product_name`
    pero no `product_id`. Con solo el nombre habria que emparejar por texto,
    que es exactamente lo que este puente se prohibe -dos productos que se
    llaman casi igual y la venta descuenta del renglon equivocado sin que nada
    avise-. Asi que las partidas se toman de la peticion, que si lleva el
    `product_id` que el cajero cobro, y el folio se toma de la respuesta para
    que la llave de idempotencia siga siendo la de la venta real.

    Un 200 del POS significa que cobro esas partidas: la peticion es
    autoritativa sobre que salio del estante. Lo mas limpio a futuro seria que
    el POS incluyera `product_id` en su respuesta; mientras no lo haga, esto no
    depende de que lo haga.
    """
    partidas = (solicitud or {}).get("items") or venta.get("items") or venta.get("lines") or []
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
                    # 'sale' y no 'invoice': lo causo una venta cobrada, no un
                    # comprobante. Es lo que permite despues facturar esa venta
                    # sin descontar de nuevo -y lo que antes lo impedia-.
                    reference_type="sale",
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


def _ubicacion_del_pos(db, user_data, id_location=None):
    """La ubicacion donde vive la mercancia de mostrador.

    Si no se indica una, se usa -o se crea- una del modulo `pos`. Tener el
    mostrador como ubicacion propia es lo que permite despues preguntar "cuanto
    hay en el punto de venta" sin restar de memoria.
    """
    from app.models.location import Location

    if id_location:
        ubicacion = db.get(Location, int(id_location))
        if not ubicacion or ubicacion.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "location"})
        return ubicacion.id_location

    ubicacion = db.scalars(
        select(Location).where(
            Location.id_module == MODULO, Location.deletion_date.is_(None)
        ).order_by(Location.id_location)
    ).first()
    if ubicacion is not None:
        return ubicacion.id_location

    tipo = db.scalars(select(Location.id_location_type).limit(1)).first()
    if tipo is None:
        raise AppError("errors.resource_scope_missing", 409, {"entity": "location_type"})
    ubicacion = Location(
        id_location_type=tipo,
        location_description="Punto de venta - mostrador",
        id_module=MODULO,
        created_by=int(user_data.get("id_user") or 0),
    )
    db.add(ubicacion)
    db.flush()
    return ubicacion.id_location


def _existencia(db, id_product, id_location):
    """Lo que el libro del nucleo dice que hay, sumando su historico."""
    from sqlalchemy import func as sql_func

    from app.models.inventory_ledger import InventoryLedger

    total = db.scalar(
        select(sql_func.coalesce(sql_func.sum(InventoryLedger.quantity_delta), 0)).where(
            InventoryLedger.id_product == id_product,
            InventoryLedger.id_location == id_location,
        )
    )
    return int(total or 0)


def sincronizar_catalogo(payload, user_data) -> dict:
    """Da de alta en el nucleo los productos del POS que aun no tienen enlace.

    Es lo que hace cierto "un solo inventario": sin contraparte en el nucleo no
    hay nada de que descontar, y la venta se va sin dejar rastro en el almacen.

    Por que pide una factura y un material
    --------------------------------------
    En este esquema un producto existe porque una compra lo trajo
    (`product.id_invoice` es obligatorio y de ahi sale su proyecto) y porque es
    de algun tipo (`product.id_material`). El servicio no los inventa: fabricar
    una factura para cuadrar un requisito seria meter un documento inexistente
    en la contabilidad para poder guardar un renglon de almacen. Se piden, y
    quien sincroniza decide contra que compra entra la mercancia.

    Lo que hace y lo que deliberadamente no hace
    --------------------------------------------
    * **Reutiliza en vez de duplicar.** Si ya hay un producto con el mismo
      codigo, lo enlaza; crear un gemelo partiria el saldo en dos.
    * **Solo pone saldo de apertura a lo que acaba de crear**, que por
      definicion estaba en cero. A un producto que ya existia no le toca la
      existencia: si el POS y el nucleo no coinciden, eso es un descuadre que
      alguien tiene que mirar, no algo que se tape copiando una cifra encima.
      Las diferencias se devuelven en `discrepancies`.
    * **No adivina por nombre.** Empareja por codigo, que es lo unico que el
      operador controla a proposito.
    """
    from app.models.invoice import Invoice
    from app.models.material import Material
    from app.models.product import Product
    from app.services.inventory_service import _actor_project_id
    from app.services.pos_gateway import reenviar

    id_invoice = int(payload.get("id_invoice") or 0)
    id_material = int(payload.get("id_material") or 0)
    if not id_invoice:
        raise AppError("errors.required_field", 400, {"field": "id_invoice"})
    if not id_material:
        raise AppError("errors.required_field", 400, {"field": "id_material"})

    catalogo, codigo = reenviar("GET", "products", actor=user_data.get("id_user"))
    if codigo >= 400:
        raise AppError("errors.pos_unreachable", 502, {"status": codigo})
    if isinstance(catalogo, dict):
        catalogo = catalogo.get("items") or catalogo.get("results") or []

    creados, enlazados, omitidos, descuadres = [], [], [], []

    with transaction_context() as db:
        factura = db.get(Invoice, id_invoice)
        if not factura or factura.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "invoice"})
        proyecto = getattr(factura, "id_proyect", None)
        if not proyecto:
            raise AppError("errors.resource_scope_missing", 409, {"entity": "invoice"})
        sin_restriccion = bool(
            user_data.get("is_superuser") or user_data.get("is_bootstrap_admin")
        )
        if not sin_restriccion and _actor_project_id(user_data) != proyecto:
            raise AppError("errors.permission_denied", 403)

        material = db.get(Material, id_material)
        if not material or material.deletion_date is not None:
            raise AppError("errors.not_found", 404, {"entity": "material"})

        destino = _ubicacion_del_pos(db, user_data, payload.get("id_location"))
        ya_enlazados = _enlaces(db, [p.get("id") for p in catalogo if p.get("id")])

        for fila in catalogo:
            id_pos = str(fila.get("id") or "")
            nombre = str(fila.get("name") or "")[:200]
            if not id_pos:
                continue
            if id_pos in ya_enlazados:
                omitidos.append({"pos_product_id": id_pos, "name": nombre,
                                 "reason": "already_linked"})
                continue

            codigo_pos = str(fila.get("sku") or "").strip() or None
            producto = None
            if codigo_pos:
                producto = db.scalars(
                    select(Product).where(
                        Product.product_code == codigo_pos,
                        Product.deletion_date.is_(None),
                    ).order_by(Product.id_product)
                ).first()

            nuevo = producto is None
            if nuevo:
                producto = Product(
                    id_invoice=id_invoice,
                    id_location=destino,
                    id_material=id_material,
                    product_code=codigo_pos,
                    descripcion=nombre or None,
                    gross_price=fila.get("sale_price") or fila.get("price"),
                    is_directly_related_to_product_service=True,
                    tracking_mode="fungible",
                    stock_purpose="mercancia",
                    created_by=int(user_data.get("id_user") or 0),
                )
                db.add(producto)
                db.flush()

            enlace = PosProductLink(
                pos_product_id=id_pos,
                id_product=producto.id_product,
                pos_product_name=nombre or None,
                id_location=destino,
                created_by=int(user_data.get("id_user") or 0),
            )
            db.add(enlace)
            db.flush()

            existencia = _unidades(fila.get("current_stock"))
            if nuevo:
                if existencia:
                    apply_movement_in_session(
                        db, producto.id_product, user_data,
                        movement_type="receive",
                        quantity_delta=existencia,
                        idempotency_key=f"pos-apertura-{id_pos}"[:90],
                        id_location=destino,
                        reference_type="manual",
                        reference_id=id_pos,
                        reason=f"Saldo de apertura del punto de venta ({nombre})",
                        source_module=MODULO,
                    )
                creados.append({"pos_product_id": id_pos, "name": nombre,
                                "id_product": producto.id_product,
                                "opening_stock": existencia or 0})
            else:
                enlazados.append({"pos_product_id": id_pos, "name": nombre,
                                  "id_product": producto.id_product})
                # El saldo del nucleo manda: no se pisa con el del POS. Si no
                # coinciden alguien tiene que decidir cual es el bueno.
                del_nucleo = _existencia(db, producto.id_product, destino)
                if existencia is not None and del_nucleo != existencia:
                    descuadres.append({
                        "pos_product_id": id_pos, "name": nombre,
                        "id_product": producto.id_product,
                        "pos_stock": existencia, "core_stock": del_nucleo,
                    })

    return {
        "created": creados,
        "linked": enlazados,
        "skipped": omitidos,
        "discrepancies": descuadres,
        "id_location": destino,
    }
