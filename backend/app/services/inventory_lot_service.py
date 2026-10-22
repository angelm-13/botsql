"""Lotes y caducidad: lo que le pone fecha a una parte del saldo.

Que resuelve
------------
Un saldo de 300 sacos no dice cuando caduca ninguno. Con eso, lo que se vence se
descubre en el anaquel, y quien lo descubre ya no puede hacer nada: ni devolverlo
al proveedor, ni sacarlo antes, ni dejar de comprar tanto.

La regla de salida: PRIMERO LO QUE VENCE PRIMERO
------------------------------------------------
Cuando un producto se lleva por lotes, una salida no elige lote: se sirve del
que vence antes. Es lo unico que reduce la merma por caducidad, y dejarlo a
criterio de quien despacha es dejar que el anaquel se ordene por comodidad -lo
de enfrente- en lugar de por fecha.

Un lote sin fecha va al final. No es que dure para siempre: es que uno con fecha
siempre es mas urgente que uno sin ella.

Como se engancha con el resto
-----------------------------
Todo pasa por `apply_movement_in_session`, que es la unica puerta que mueve
existencias en el sistema. Este modulo NO escribe saldos por su cuenta: le dice a
esa puerta de que lotes salio o entro lo que ella ya decidio mover. Si tuviera su
propio camino, el saldo del producto y el desglose por lote empezarian a
discrepar y no habria forma de saber cual creer.

El control por lote se enciende producto por producto -`product.lot_control`- y
nace apagado. Encenderlo obliga a nombrar el lote en cada entrada, y eso solo
vale la pena en lo que caduca; en lo demas seria un campo mas que llenar sin
nada que contestar a cambio.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select

from app.models.inventory_lot import (
    InventoryLot, InventoryLotBalance, NmInventoryLedgerLot,
)
from app.models.inventory_stock import InventoryStock
from app.models.location import Location
from app.models.product import Product
from app.models.session import transaction_context
from app.utils.errors import AppError


def _actor(user_data: dict) -> int:
    id_usuario = (user_data or {}).get("id_user")
    if not id_usuario:
        raise AppError("errors.auth_required", 401)
    return int(id_usuario)


def _entero(valor, campo, *, obligatorio=True):
    if valor in (None, ""):
        if obligatorio:
            raise AppError("errors.required_field", 400, {"field": campo})
        return None
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _fecha(valor, campo):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def lleva_lotes(product) -> bool:
    """Si este producto se lleva por lotes.

    Un producto serializado no: ya tiene una fila por unidad, y ponerle lotes
    encima seria llevar la misma cosa por dos caminos.
    """
    return bool(getattr(product, "lot_control", False)) and \
        str(getattr(product, "tracking_mode", "") or "") != "serializado"


# --- el lote --------------------------------------------------------------

def _lote_como_objeto(valor) -> dict:
    """El lote que nombra la captura, siempre como objeto.

    Es `{"lot_code": ..., "expiry_date": ...}` o `{"id_inventory_lot": ...}`. Un
    texto suelto ("L-441") no dice si es codigo o identificador, y antes reventaba
    al leerlo como diccionario: se rechaza con el campo que falla.
    """
    if valor in (None, ""):
        return {}
    if not isinstance(valor, dict):
        raise AppError("errors.invalid_field", 400, {"field": "lot"})
    return valor


def _lote(db, id_lote, *, para_escribir=False) -> InventoryLot:
    consulta = select(InventoryLot).where(
        InventoryLot.id_inventory_lot == _entero(id_lote, "id_inventory_lot"),
        InventoryLot.deletion_date.is_(None),
    )
    if para_escribir:
        consulta = consulta.with_for_update()
    lote = db.scalars(consulta).first()
    if lote is None:
        raise AppError("errors.not_found", 404, {"entity": "inventory_lot"})
    return lote


def lote_en_sesion(db, id_product, datos: dict, actor: int) -> InventoryLot:
    """El lote que nombra una entrada, creandolo si es la primera vez que llega.

    Se acepta `id_inventory_lot` -un lote que ya existe- o `lot_code` mas
    `expiry_date`. Lo segundo es lo normal al recibir mercancia: quien captura
    tiene el codigo del proveedor delante, no un identificador del sistema.

    El par (producto, codigo) es unico: dos lotes L-441 del mismo producto son
    el mismo lote capturado dos veces, y con los dos vivos la mitad de las
    salidas descontaria de uno y la mitad del otro.
    """
    datos = _lote_como_objeto(datos)
    id_lote = _entero(datos.get("id_inventory_lot"), "id_inventory_lot",
                      obligatorio=False)
    if id_lote is not None:
        lote = _lote(db, id_lote)
        if int(lote.id_product) != int(id_product):
            raise AppError("errors.lot_product_mismatch", 409,
                           {"id_inventory_lot": id_lote,
                            "id_product": int(id_product),
                            "lot_id_product": int(lote.id_product)})
        return lote

    codigo = str(datos.get("lot_code") or "").strip()[:60]
    if not codigo:
        raise AppError("errors.required_field", 400, {"field": "lot_code"})

    existente = db.scalars(
        select(InventoryLot).where(
            InventoryLot.id_product == int(id_product),
            func.lower(InventoryLot.lot_code) == codigo.lower(),
            InventoryLot.deletion_date.is_(None),
        ).limit(1)
    ).first()
    if existente is not None:
        # Llega mas del mismo lote. La fecha ya la trae el lote; si la que viene
        # ahora no coincide, es un dedazo en una de las dos y hay que decirlo:
        # una fecha silenciosamente distinta cambia el orden de salida.
        vence = _fecha(datos.get("expiry_date"), "expiry_date")
        if vence is not None and existente.expiry_date is not None \
                and vence != existente.expiry_date:
            raise AppError(
                "errors.lot_expiry_mismatch", 409,
                {"lot_code": existente.lot_code,
                 "stored_expiry_date": existente.expiry_date.isoformat(),
                 "expiry_date": vence.isoformat()},
            )
        if vence is not None and existente.expiry_date is None:
            existente.expiry_date = vence
        return existente

    lote = InventoryLot(
        id_product=int(id_product),
        lot_code=codigo,
        expiry_date=_fecha(datos.get("expiry_date"), "expiry_date"),
        received_on=_fecha(datos.get("received_on"), "received_on") or date.today(),
        note=(str(datos.get("note") or "").strip()[:250] or None),
        created_by=actor,
    )
    db.add(lote)
    db.flush()
    return lote


def _saldo_de_lote(db, id_lote, id_location, actor, *, para_escribir=False):
    consulta = select(InventoryLotBalance).where(
        InventoryLotBalance.id_inventory_lot == int(id_lote),
        InventoryLotBalance.id_location == int(id_location),
    )
    if para_escribir:
        consulta = consulta.with_for_update()
    fila = db.scalars(consulta).first()
    if fila is None:
        fila = InventoryLotBalance(
            id_inventory_lot=int(id_lote), id_location=int(id_location),
            quantity=0, created_by=actor,
        )
        db.add(fila)
        db.flush()
    return fila


# --- lo que la puerta de movimientos llama -------------------------------

def entrada_en_sesion(db, *, product, id_location, cantidad, lote_pedido, actor):
    """Suma al lote lo que entro. Devuelve [(lote, cantidad)] para el desglose."""
    lote = lote_en_sesion(db, product.id_product, lote_pedido, actor)
    saldo = _saldo_de_lote(db, lote.id_inventory_lot, id_location, actor,
                           para_escribir=True)
    saldo.quantity = int(saldo.quantity or 0) + int(cantidad)
    db.flush()
    return [(lote, int(cantidad))]


def salida_en_sesion(db, *, product, id_location, cantidad, lote_pedido, actor):
    """Descuenta primero lo que vence primero.

    Si la salida nombra un lote, se respeta: a veces hay que sacar ESE -el que
    el cliente devolvio, el que el proveedor reclama- y negarlo obligaria a
    hacerlo con un ajuste, que es peor porque no deja dicho por que.

    Sin lote nombrado se sirve por fecha: los que vencen antes primero, y los sin
    fecha al final. Una salida puede tocar varios lotes, y por eso el desglose es
    una lista y no un lote.
    """
    pedido = int(cantidad)
    pedido_lote = _entero(_lote_como_objeto(lote_pedido).get("id_inventory_lot"),
                          "id_inventory_lot", obligatorio=False)

    consulta = (
        select(InventoryLotBalance, InventoryLot)
        .join(InventoryLot,
              InventoryLot.id_inventory_lot == InventoryLotBalance.id_inventory_lot)
        .where(
            InventoryLot.id_product == int(product.id_product),
            InventoryLot.deletion_date.is_(None),
            InventoryLotBalance.id_location == int(id_location),
            InventoryLotBalance.quantity > 0,
        )
    )
    if pedido_lote is not None:
        consulta = consulta.where(
            InventoryLotBalance.id_inventory_lot == pedido_lote)
    else:
        # NULLS LAST a mano: un lote sin fecha no es eterno, es menos urgente
        # que cualquiera que si la tenga. `nulls_last()` no viaja igual entre
        # motores, y esto se lee igual en los dos.
        consulta = consulta.order_by(
            InventoryLot.expiry_date.is_(None),
            InventoryLot.expiry_date,
            InventoryLot.id_inventory_lot,
        )

    filas = db.execute(consulta.with_for_update(of=InventoryLotBalance)).all()

    tomado = []
    restante = pedido
    for saldo, lote in filas:
        if restante <= 0:
            break
        toma = min(int(saldo.quantity or 0), restante)
        saldo.quantity = int(saldo.quantity or 0) - toma
        restante -= toma
        tomado.append((lote, -toma))

    if restante > 0:
        # El saldo del producto y el desglose por lote tienen que cuadrar. Que no
        # cuadren significa que algo movio existencia sin pasar por aqui, y
        # dejarlo pasar convertiria el desglose en decoracion.
        raise AppError(
            "errors.lot_insufficient_stock", 409,
            {"id_product": int(product.id_product),
             "id_location": int(id_location),
             "requested": pedido,
             "available_in_lots": pedido - restante,
             "id_inventory_lot": pedido_lote},
        )
    db.flush()
    return tomado


def lotes_de_un_movimiento(db, *, llave=None, id_ledger=None) -> list[tuple[int, int]]:
    """De que lotes vivos salio (o entro) un movimiento: `[(id_lote, cantidad)]`, cantidades positivas.

    Se busca por la llave de idempotencia del renglon del libro o por su identificador.
    Sirve para devolver lo que salio a los lotes de los que salio: una devolucion que no
    sabe de donde vino no puede decir que lote le corresponde. Un movimiento sin desglose
    -anterior al control por lote, o migrado- devuelve una lista vacia.
    """
    if id_ledger is None:
        from app.models.inventory_ledger import InventoryLedger

        id_ledger = db.scalar(select(InventoryLedger.id_inventory_ledger)
                              .where(InventoryLedger.idempotency_key == llave))
        if id_ledger is None:
            return []
    filas = db.execute(
        select(NmInventoryLedgerLot.id_inventory_lot,
               func.sum(NmInventoryLedgerLot.quantity_delta))
        .join(InventoryLot,
              InventoryLot.id_inventory_lot == NmInventoryLedgerLot.id_inventory_lot)
        .where(NmInventoryLedgerLot.id_inventory_ledger == int(id_ledger),
               InventoryLot.deletion_date.is_(None))
        .group_by(NmInventoryLedgerLot.id_inventory_lot)
        .order_by(NmInventoryLedgerLot.id_inventory_lot)
    ).all()
    return [(int(lote), abs(int(cantidad))) for lote, cantidad in filas if cantidad]


def lotes_por_regresar(db, ids_ledger) -> list[tuple[int, int]]:
    """De que lotes vivos salio lo que esos renglones del libro sacaron y aun no ha vuelto.

    Suma el desglose con su signo -las salidas restan, las reposiciones suman- y deja lo
    que sigue fuera: `[(id_lote, cantidad)]`. Es lo que permite que una segunda nota de
    credito sobre la misma venta no vuelva a contar lo que la primera ya repuso.
    """
    ids_ledger = [int(i) for i in ids_ledger]
    if not ids_ledger:
        return []
    filas = db.execute(
        select(NmInventoryLedgerLot.id_inventory_lot,
               func.sum(NmInventoryLedgerLot.quantity_delta))
        .join(InventoryLot,
              InventoryLot.id_inventory_lot == NmInventoryLedgerLot.id_inventory_lot)
        .where(NmInventoryLedgerLot.id_inventory_ledger.in_(ids_ledger),
               InventoryLot.deletion_date.is_(None))
        .group_by(NmInventoryLedgerLot.id_inventory_lot)
        .having(func.sum(NmInventoryLedgerLot.quantity_delta) < 0)
        .order_by(NmInventoryLedgerLot.id_inventory_lot)
    ).all()
    return [(int(lote), -int(cantidad)) for lote, cantidad in filas]


def asentar_desglose(db, ledger, movidos, actor) -> None:
    """Deja escrito de que lotes fue el movimiento.

    El libro escribe un renglon por movimiento, y una salida puede cubrirse con
    tres lotes: sin esto el renglon diria que salieron 30 sin decir de donde, y
    el rastro se corta justo donde el proveedor pregunta.
    """
    for lote, delta in movidos:
        db.add(NmInventoryLedgerLot(
            id_inventory_ledger=ledger.id_inventory_ledger,
            id_inventory_lot=lote.id_inventory_lot,
            quantity_delta=int(delta),
            created_by=actor,
        ))
    db.flush()


# --- consultas ------------------------------------------------------------

def lotes_del_producto(id_product, user_data) -> dict:
    """Los lotes vivos de un producto, con lo que queda en cada ubicacion."""
    _actor(user_data)
    with transaction_context() as db:
        id_producto = _entero(id_product, "id_product")
        lotes = db.scalars(
            select(InventoryLot).where(
                InventoryLot.id_product == id_producto,
                InventoryLot.deletion_date.is_(None),
            ).order_by(
                InventoryLot.expiry_date.is_(None),
                InventoryLot.expiry_date,
                InventoryLot.lot_code,
            )
        ).all()
        if not lotes:
            return {"id_product": id_producto, "items": [], "total": 0,
                    "total_quantity": 0}

        ids = [int(x.id_inventory_lot) for x in lotes]
        saldos = db.execute(
            select(InventoryLotBalance.id_inventory_lot,
                   InventoryLotBalance.id_location,
                   InventoryLotBalance.quantity,
                   Location.location_description)
            .join(Location,
                  Location.id_location == InventoryLotBalance.id_location)
            .where(InventoryLotBalance.id_inventory_lot.in_(ids),
                   InventoryLotBalance.quantity != 0)
        ).all()

        por_lote: dict[int, list] = {}
        for id_lote, id_ubicacion, cantidad, descripcion in saldos:
            por_lote.setdefault(int(id_lote), []).append({
                "id_location": int(id_ubicacion),
                "location_description": descripcion,
                "quantity": int(cantidad or 0),
            })

        hoy = date.today()
        items = []
        for lote in lotes:
            sitios = por_lote.get(int(lote.id_inventory_lot), [])
            cantidad = sum(x["quantity"] for x in sitios)
            fila = lote.serialize()
            fila["locations"] = sitios
            fila["quantity"] = cantidad
            fila["days_to_expiry"] = (
                (lote.expiry_date - hoy).days if lote.expiry_date else None
            )
            fila["expired"] = bool(lote.expiry_date and lote.expiry_date < hoy)
            items.append(fila)

        return {
            "id_product": id_producto,
            "items": items,
            "total": len(items),
            "total_quantity": sum(x["quantity"] for x in items),
        }


def por_caducar(user_data, *, dias=30) -> dict:
    """Lo que vence dentro de N dias, y lo que ya vencio.

    Es la razon de llevar lotes. Lo vencido va aparte de lo que esta por vencer
    porque son dos acciones distintas: lo vencido se da de baja -con el
    movimiento `expiry`, que existe separado de la merma a proposito- y lo que
    esta por vencer se saca antes.
    """
    _actor(user_data)
    dias = _entero(dias, "days", obligatorio=False) or 30
    hoy = date.today()
    with transaction_context() as db:
        filas = db.execute(
            select(InventoryLot,
                   func.sum(InventoryLotBalance.quantity),
                   Product.product_code,
                   Product.descripcion)
            .join(InventoryLotBalance,
                  InventoryLotBalance.id_inventory_lot == InventoryLot.id_inventory_lot)
            .join(Product, Product.id_product == InventoryLot.id_product)
            .where(
                InventoryLot.deletion_date.is_(None),
                InventoryLot.expiry_date.isnot(None),
                InventoryLotBalance.quantity > 0,
            )
            .group_by(InventoryLot.id_inventory_lot, Product.product_code,
                      Product.descripcion)
            .having(func.sum(InventoryLotBalance.quantity) > 0)
            .order_by(InventoryLot.expiry_date)
        ).all()

        vencidos, proximos = [], []
        for lote, cantidad, codigo, descripcion in filas:
            faltan = (lote.expiry_date - hoy).days
            fila = lote.serialize()
            fila["quantity"] = int(cantidad or 0)
            fila["days_to_expiry"] = faltan
            fila["product_code"] = codigo
            fila["product_description"] = descripcion
            if faltan < 0:
                vencidos.append(fila)
            elif faltan <= dias:
                proximos.append(fila)

        return {
            "days": dias,
            "expired": vencidos,
            "expiring_soon": proximos,
            "expired_quantity": sum(x["quantity"] for x in vencidos),
            "expiring_quantity": sum(x["quantity"] for x in proximos),
        }


def cuadre_de_lotes(id_product, user_data) -> dict:
    """Si el desglose por lote cuadra con el saldo del producto.

    Existe para poder contestar la pregunta con una consulta en lugar de con una
    revision a mano. Si no cuadra, alguien movio existencia sin pasar por la
    puerta de siempre, y eso es lo que hay que ir a buscar.
    """
    _actor(user_data)
    with transaction_context() as db:
        id_producto = _entero(id_product, "id_product")
        por_sitio = dict(db.execute(
            select(InventoryStock.id_location, func.sum(InventoryStock.quantity))
            .where(InventoryStock.id_product == id_producto)
            .group_by(InventoryStock.id_location)
        ).all())
        en_lotes = dict(db.execute(
            select(InventoryLotBalance.id_location,
                   func.sum(InventoryLotBalance.quantity))
            .join(InventoryLot,
                  InventoryLot.id_inventory_lot == InventoryLotBalance.id_inventory_lot)
            .where(InventoryLot.id_product == id_producto)
            .group_by(InventoryLotBalance.id_location)
        ).all())

        diferencias = []
        for id_ubicacion in sorted(set(por_sitio) | set(en_lotes)):
            saldo = int(por_sitio.get(id_ubicacion, 0) or 0)
            lotes = int(en_lotes.get(id_ubicacion, 0) or 0)
            if saldo != lotes:
                diferencias.append({
                    "id_location": int(id_ubicacion),
                    "stock": saldo,
                    "in_lots": lotes,
                    "difference": saldo - lotes,
                })
        return {"id_product": id_producto, "balanced": not diferencias,
                "differences": diferencias}

# --- encender y apagar el control por lote -------------------------------

LOTE_DE_APERTURA = "APERTURA"


def encender_control_de_lotes(id_product, payload: dict, user_data) -> dict:
    """Enciende el control por lote y no deja existencia fuera de ningun lote.

    Por que no es solo escribir la columna
    --------------------------------------
    Medido al probar contra Postgres: encendiendola en un producto que ya tenia
    una unidad, el cuadre salio en falso -saldo 1, en lotes 0-. Esa unidad queda
    fuera de todo lote, y como la salida se sirve de los lotes, no se puede
    despachar: el saldo dice que esta y los lotes dicen que no.

    Asi que al encender se crea un lote de APERTURA con lo que ya habia en cada
    ubicacion. Sin fecha de caducidad, porque nadie la sabe -esa es justamente la
    informacion que no se llevaba- y un lote sin fecha va al final del orden de
    salida, que es lo prudente: primero sale lo que si tiene fecha conocida.

    En lo serializado no se enciende: ya hay una fila por unidad, y ponerle lotes
    encima seria llevar la misma cosa por dos caminos. Lo impide tambien un CHECK
    en la base.
    """
    actor = _actor(user_data)
    codigo = str((payload or {}).get("lot_code") or LOTE_DE_APERTURA).strip()[:60]

    with transaction_context() as db:
        producto = db.scalars(
            select(Product).where(
                Product.id_product == _entero(id_product, "id_product"),
                Product.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if producto is None:
            raise AppError("errors.not_found", 404, {"entity": "product"})

        if str(producto.tracking_mode or "") == "serializado":
            raise AppError("errors.lot_control_not_for_serialized", 409,
                           {"id_product": producto.id_product,
                            "tracking_mode": producto.tracking_mode})

        if producto.lot_control:
            return {"id_product": producto.id_product, "lot_control": True,
                    "opening_lot": None, "already_on": True}

        existencias = db.execute(
            select(InventoryStock.id_location, InventoryStock.quantity)
            .where(InventoryStock.id_product == producto.id_product,
                   InventoryStock.quantity > 0)
        ).all()

        apertura = None
        if existencias:
            apertura = lote_en_sesion(db, producto.id_product, {
                "lot_code": codigo,
                "note": "Existencia anterior al control por lote. Sin fecha "
                        "porque no se llevaba.",
            }, actor)
            for id_ubicacion, cantidad in existencias:
                # Solo lo que ningun lote lleva ya: tras apagar y volver a encender,
                # los saldos de lote quedan viejos y sumar la existencia entera otra
                # vez los duplicaba (lotes 35 contra existencia 20).
                en_lotes = int(db.scalar(
                    select(func.coalesce(func.sum(InventoryLotBalance.quantity), 0))
                    .join(InventoryLot, InventoryLot.id_inventory_lot == InventoryLotBalance.id_inventory_lot)
                    .where(InventoryLot.id_product == producto.id_product,
                           InventoryLot.deletion_date.is_(None),
                           InventoryLotBalance.id_location == int(id_ubicacion))
                ) or 0)
                faltante = int(cantidad or 0) - en_lotes
                if faltante <= 0:
                    continue
                saldo = _saldo_de_lote(db, apertura.id_inventory_lot,
                                       id_ubicacion, actor, para_escribir=True)
                saldo.quantity = int(saldo.quantity or 0) + faltante

        producto.lot_control = True
        db.flush()
        return {
            "id_product": producto.id_product,
            "lot_control": True,
            "opening_lot": apertura.serialize() if apertura else None,
            "already_on": False,
        }


def apagar_control_de_lotes(id_product, user_data) -> dict:
    """Apaga el control. Los lotes se conservan: son el rastro de lo que paso.

    No se borran ni se vacian. Un lote con saldo dice donde esta esa parte de la
    existencia, y borrarlo para "dejar limpio" perderia el unico dato que liga lo
    del anaquel con la factura de compra cuando hay un reclamo.
    """
    _actor(user_data)
    with transaction_context() as db:
        producto = db.scalars(
            select(Product).where(
                Product.id_product == _entero(id_product, "id_product"),
                Product.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if producto is None:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        producto.lot_control = False
        db.flush()
        return {"id_product": producto.id_product, "lot_control": False}
