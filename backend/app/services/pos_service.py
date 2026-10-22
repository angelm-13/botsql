"""El punto de venta, ya nativo: cobrar, abrir caja y cortarla.

Que sustituye
-------------
A `pos_gateway` + `pos_inventory_bridge`, que mandaban la venta por HTTP a otra
base y luego REFLEJABAN aqui lo que aquella ya habia cobrado. Ahora la venta se
escribe en esta base, contra las mismas tablas que el almacen.

El cambio de comportamiento que eso trae, y por que es una mejora
----------------------------------------------------------------
El puente no podia deshacer una venta sin existencia: cuando llegaba el reflejo,
el dinero ya estaba cobrado en el otro sistema. Por eso apuntaba el descuadre en
`skipped` y seguia -- era lo unico honesto que podia hacer.

Aqui la venta y el movimiento de almacen se escriben en la MISMA transaccion, de
modo que una falta de existencia detiene el cobro en lugar de dejar un
descuadre. Es mas estricto que antes a proposito: es lo que hace el resto de
TYAKXA -- un vale tampoco sale sin existencia -- y es exactamente lo que se gana
al tener una sola base. Si al cajero le sobra mercancia fisica que el sistema no
tiene, lo que falta es una entrada, no una venta a ciegas.

La existencia sale por la puerta de siempre
-------------------------------------------
`apply_movement_in_session`, con `source_module='pos'` y `reference_type='sale'`.
No se toca `inventory_stock` a mano. Y `reference_type` es 'sale' y no 'invoice'
porque lo causo una venta cobrada, no un comprobante: es lo que permite facturar
despues esa venta sin volver a descontar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from app.models.location import Location
from app.models.pos import (
    ESTADOS_DE_TURNO, FORMAS_DE_PAGO, TIPOS_DE_VENTA,
    PosCashSession, PosCashWithdrawal, PosPayment, PosSale, PosSaleItem,
)
from app.models.product import Product
from app.models.session import transaction_context
from app.services.inventory_service import apply_movement_in_session
from app.utils.errors import AppError

MODULO = "pos"


def _ahora():
    """La hora en UTC, sin zona.

    Las columnas son `TIMESTAMP` sin zona -- se comprobo --, asi que una fecha
    con zona se guardaria convertida y la comparacion de un corte contra sus
    ventas dejaria de cuadrar por unas horas. `utcnow()` haria lo mismo pero
    esta marcada como obsoleta.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- ayudas -------------------------------------------------------------

def _actor(user_data) -> tuple[int, int]:
    """El usuario y su proyecto, que es como se acota todo en TYAKXA."""
    id_user = user_data.get("id_user") or user_data.get("user_id")
    id_proyect = user_data.get("id_proyect") or user_data.get("project_id")
    if not id_user or not id_proyect:
        raise AppError("errors.resource_scope_missing", 409, {"entity": "user"})
    return int(id_user), int(id_proyect)


def _decimal(valor, campo, *, por_omision=None):
    if valor is None or valor == "":
        if por_omision is not None:
            return Decimal(str(por_omision))
        raise AppError("errors.validation", 422, {"field": campo})
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise AppError("errors.validation", 422, {"field": campo})
    if not numero.is_finite():  # NaN/Infinity daban 500 o ventas con cambio infinito
        raise AppError("errors.validation", 422, {"field": campo})
    return numero


def _unidades(cantidad):
    """La cantidad como entero, o None si es fraccionaria.

    El libro del nucleo lleva piezas enteras. Se reporta en lugar de redondear,
    por lo mismo que en los puentes de restaurante y logistica: redondear a cero
    esconde una salida y redondear a uno inventa existencia.
    """
    try:
        numero = Decimal(str(cantidad))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if numero != numero.to_integral_value():
        return None
    return int(numero)


def ubicacion_del_mostrador(db, id_user, id_location=None):
    """Donde vive la mercancia de mostrador.

    Se conserva tal cual estaba en `pos_inventory_bridge`: el mostrador es una
    ubicacion propia, y eso es lo que permite preguntar "cuanto hay en el punto
    de venta" sin restar de memoria.
    """
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
        created_by=id_user,
    )
    db.add(ubicacion)
    db.flush()
    return ubicacion.id_location


def _siguiente_folio(db, id_proyect) -> str:
    """El folio corre DENTRO del proyecto, no global.

    Dos negocios en la misma instalacion llevan su propia numeracion; una comun
    haria que el ticket de uno saltara numeros por las ventas del otro.
    """
    ultimo = db.scalars(
        select(func.count(PosSale.id_pos_sale)).where(PosSale.id_proyect == id_proyect)
    ).first() or 0
    return "V%06d" % (int(ultimo) + 1)


def _turno_abierto(db, id_proyect):
    return db.scalars(
        select(PosCashSession).where(
            PosCashSession.id_proyect == id_proyect,
            PosCashSession.session_status == "open",
            PosCashSession.deletion_date.is_(None),
        ).order_by(PosCashSession.id_pos_cash_session.desc())
    ).first()


# --- la caja ------------------------------------------------------------

def abrir_turno(payload, user_data) -> dict:
    id_user, id_proyect = _actor(user_data)
    nombre = (payload.get("register_name") or "").strip()
    if not nombre:
        raise AppError("errors.validation", 422, {"field": "register_name"})

    with transaction_context() as db:
        # Un segundo turno abierto en la misma caja haria que el corte no
        # supiera contra que comparar.
        if _turno_abierto(db, id_proyect) is not None:
            raise AppError("errors.pos_session_already_open", 409)

        turno = PosCashSession(
            id_proyect=id_proyect,
            register_name=nombre[:120],
            id_user_opened=id_user,
            opening_amount=_decimal(payload.get("opening_amount"), "opening_amount",
                                    por_omision=0),
            opened_at=_ahora(),
            session_status="open",
            notes=(payload.get("notes") or None),
            created_by=id_user,
        )
        db.add(turno)
        db.flush()
        return turno.serialize()


def cerrar_turno(id_pos_cash_session, payload, user_data) -> dict:
    """El corte: se declara a ciegas y el sistema dice cuanto esperaba.

    Se guardan las tres cifras -- lo declarado, lo esperado y la diferencia -- y
    no solo el descuadre, porque un corte con diferencia cero no distingue
    "cuadro" de "nadie conto".
    """
    id_user, id_proyect = _actor(user_data)

    with transaction_context() as db:
        turno = db.get(PosCashSession, int(id_pos_cash_session))
        if not turno or turno.deletion_date is not None or turno.id_proyect != id_proyect:
            raise AppError("errors.not_found", 404, {"entity": "pos_cash_session"})
        if turno.session_status != "open":
            raise AppError("errors.pos_session_not_open", 409)

        declarado = payload.get("declared_amounts") or {}
        if not isinstance(declarado, dict):
            raise AppError("errors.validation", 422, {"field": "declared_amounts"})

        esperado = _esperado_del_turno(db, turno)
        diferencia = {
            forma: float(_decimal(declarado.get(forma), forma, por_omision=0)
                         - Decimal(str(esperado.get(forma, 0))))
            for forma in set(esperado) | set(declarado)
        }

        tipo = (payload.get("close_type") or "closed_z").strip()
        if tipo not in ("closed_x", "closed_z"):
            raise AppError("errors.validation", 422, {"field": "close_type"})

        turno.session_status = tipo
        turno.id_user_closed = id_user
        turno.closed_at = _ahora()
        turno.blind_declared_amounts = {k: float(_decimal(v, k, por_omision=0))
                                        for k, v in declarado.items()}
        turno.system_expected_amounts = esperado
        turno.discrepancy_amounts = diferencia
        if payload.get("notes"):
            turno.notes = payload["notes"]
        db.flush()
        return turno.serialize()


def _esperado_del_turno(db, turno) -> dict:
    """Lo cobrado por forma de pago, mas el fondo, menos los retiros.

    Se calcula de los pagos del turno y no de un acumulado que alguien fuera
    sumando: un acumulado se puede desfasar sin que nada avise, y entonces el
    corte compara contra una cifra que ya mentia.
    """
    # Lo que entro MENOS el vuelto que salio. Sumar solo `amount` daba de mas
    # justo por el importe del cambio devuelto.
    filas = db.execute(
        select(PosPayment.payment_method,
               func.coalesce(func.sum(PosPayment.amount), 0)
               - func.coalesce(func.sum(PosPayment.change_amount), 0))
        .join(PosSale, PosSale.id_pos_sale == PosPayment.id_pos_sale)
        .where(
            PosSale.id_pos_cash_session == turno.id_pos_cash_session,
            PosSale.sale_status == "paid",
            PosPayment.deletion_date.is_(None),
        )
        .group_by(PosPayment.payment_method)
    ).all()
    esperado = {forma: float(total) for forma, total in filas}

    retirado = db.scalars(
        select(func.coalesce(func.sum(PosCashWithdrawal.amount), 0)).where(
            PosCashWithdrawal.id_pos_cash_session == turno.id_pos_cash_session,
            PosCashWithdrawal.deletion_date.is_(None),
        )
    ).first() or 0

    # El fondo y los retiros solo tocan el efectivo: una tarjeta no se retira
    # del cajon.
    esperado["cash"] = float(
        Decimal(str(esperado.get("cash", 0)))
        + Decimal(str(turno.opening_amount or 0))
        - Decimal(str(retirado))
    )
    return esperado


def retirar_efectivo(id_pos_cash_session, payload, user_data) -> dict:
    id_user, id_proyect = _actor(user_data)
    with transaction_context() as db:
        turno = db.get(PosCashSession, int(id_pos_cash_session))
        if not turno or turno.deletion_date is not None or turno.id_proyect != id_proyect:
            raise AppError("errors.not_found", 404, {"entity": "pos_cash_session"})
        if turno.session_status != "open":
            raise AppError("errors.pos_session_not_open", 409)

        monto = _decimal(payload.get("amount"), "amount")
        if monto <= 0:
            raise AppError("errors.validation", 422, {"field": "amount"})
        motivo = (payload.get("reason") or "").strip()
        if not motivo:
            raise AppError("errors.validation", 422, {"field": "reason"})

        retiro = PosCashWithdrawal(
            id_proyect=id_proyect,
            id_pos_cash_session=turno.id_pos_cash_session,
            amount=monto,
            reason=motivo[:250],
            id_user_authorized=int(payload.get("id_user_authorized") or id_user),
            created_by=id_user,
        )
        db.add(retiro)
        db.flush()
        return retiro.serialize()


def turnos(user_data, *, limite=50) -> dict:
    _, id_proyect = _actor(user_data)
    with transaction_context() as db:
        filas = db.scalars(
            select(PosCashSession).where(
                PosCashSession.id_proyect == id_proyect,
                PosCashSession.deletion_date.is_(None),
            ).order_by(PosCashSession.id_pos_cash_session.desc()).limit(int(limite))
        ).all()
        return {"data": [t.serialize() for t in filas]}


# --- el cobro -----------------------------------------------------------

def cobrar(payload, user_data) -> dict:
    """Escribe la venta, sus renglones, sus pagos y el movimiento de almacen.

    Todo en una transaccion: si un renglon no tiene existencia, no queda ni la
    venta ni el descuento a medias. Ver la cabecera del modulo.
    """
    id_user, id_proyect = _actor(user_data)

    renglones = payload.get("items") or []
    if not isinstance(renglones, list) or not renglones:
        raise AppError("errors.validation", 422, {"field": "items"})

    pagos = payload.get("payments") or []
    if not isinstance(pagos, list) or not pagos:
        raise AppError("errors.validation", 422, {"field": "payments"})

    tipo = (payload.get("sale_type") or "takeout").strip()
    if tipo not in TIPOS_DE_VENTA:
        raise AppError("errors.validation", 422, {"field": "sale_type"})

    with transaction_context() as db:
        turno = _turno_abierto(db, id_proyect)
        if turno is None:
            # Cobrar sin turno abierto deja dinero que ningun corte reclama.
            raise AppError("errors.pos_session_required", 409)

        id_location = ubicacion_del_mostrador(db, id_user, payload.get("id_location"))
        folio = _siguiente_folio(db, id_proyect)

        venta = PosSale(
            id_proyect=id_proyect,
            folio=folio,
            sale_type=tipo,
            sale_status="open",
            table_number=(payload.get("table_number") or None),
            id_customer_supplier=payload.get("id_customer_supplier") or None,
            id_user_cashier=id_user,
            id_user_waiter=payload.get("id_user_waiter") or None,
            id_pos_cash_session=turno.id_pos_cash_session,
            notes=(payload.get("notes") or None),
            created_by=id_user,
        )
        db.add(venta)
        db.flush()

        subtotal = Decimal("0")
        descuento = Decimal("0")
        impuesto = Decimal("0")
        coste = Decimal("0")

        for indice, renglon in enumerate(renglones):
            id_product = renglon.get("id_product")
            if not id_product:
                raise AppError("errors.validation", 422,
                               {"field": "items[%d].id_product" % indice})
            producto = db.get(Product, int(id_product))
            if not producto or producto.deletion_date is not None:
                raise AppError("errors.not_found", 404, {"entity": "product"})

            cantidad = _decimal(renglon.get("quantity"), "items[%d].quantity" % indice)
            if cantidad <= 0:
                raise AppError("errors.validation", 422,
                               {"field": "items[%d].quantity" % indice})
            # El precio lo pone el SERVIDOR cuando el cliente no lo manda, que
            # es lo que hace la pantalla de caja. Aceptar sin mas el precio que
            # llega del navegador dejaria cobrar lo que el comprador quisiera.
            precio = _decimal(
                renglon.get("unit_price") if renglon.get("unit_price") not in (None, "")
                else producto.gross_price,
                "items[%d].unit_price" % indice, por_omision=0)
            desc_linea = _decimal(renglon.get("discount_amount"),
                                  "items[%d].discount_amount" % indice, por_omision=0)
            imp_linea = _decimal(renglon.get("tax_amount"),
                                 "items[%d].tax_amount" % indice, por_omision=0)
            # El coste se COPIA al vender. Recalcularlo despues con el coste de
            # hoy mentiria sobre el margen de la venta de ayer. `product` no
            # tiene columna de coste -- se comprobo --, asi que si nadie lo manda
            # queda en cero y el margen se lee como "sin coste capturado", que es
            # verdad, en vez de como un margen del 100%.
            coste_unitario = _decimal(renglon.get("unit_cost"),
                                      "items[%d].unit_cost" % indice, por_omision=0)

            total_linea = (precio * cantidad) - desc_linea + imp_linea
            subtotal += precio * cantidad
            descuento += desc_linea
            impuesto += imp_linea
            coste += coste_unitario * cantidad

            db.add(PosSaleItem(
                id_proyect=id_proyect,
                id_pos_sale=venta.id_pos_sale,
                id_product=int(id_product),
                id_pos_product_variant=renglon.get("id_pos_product_variant") or None,
                quantity=cantidad,
                unit_price=precio,
                unit_cost=coste_unitario,
                discount_amount=desc_linea,
                tax_amount=imp_linea,
                line_total=total_linea,
                id_pos_promotion=renglon.get("id_pos_promotion") or None,
                kitchen_zone=(renglon.get("kitchen_zone") or None),
                special_instructions=(renglon.get("special_instructions") or None),
                created_by=id_user,
            ))

            unidades = _unidades(cantidad)
            if unidades is None:
                raise AppError("errors.pos_fractional_quantity", 422,
                               {"field": "items[%d].quantity" % indice})

            # La puerta de siempre. Si no hay existencia esto lanza, y como
            # estamos dentro de la transaccion se cae la venta entera.
            apply_movement_in_session(
                db,
                int(id_product),
                user_data,
                movement_type="issue",
                quantity_delta=-unidades,
                # El folio de la venta en la llave: reintentar el mismo cobro no
                # descuenta dos veces.
                # El renglon en la llave: dos renglones del mismo producto en una
                # venta no pueden compartirla (el segundo se tomaba por replay y
                # el saldo bajaba una sola vez).
                idempotency_key=("pos-%s-%s-%d" % (folio, id_product, indice))[:90],
                id_location=id_location,
                reference_type="sale",
                reference_id=folio,
                reason="Venta %s del punto de venta" % folio,
                source_module=MODULO,
            )

        total = subtotal - descuento + impuesto

        cobrado = Decimal("0")
        renglones_de_pago = []
        for indice, pago in enumerate(pagos):
            forma = (pago.get("method") or "").strip()
            if forma not in FORMAS_DE_PAGO:
                raise AppError("errors.validation", 422,
                               {"field": "payments[%d].method" % indice})
            monto = _decimal(pago.get("amount"), "payments[%d].amount" % indice)
            entregado = pago.get("tendered_amount")
            entregado = (_decimal(entregado, "payments[%d].tendered_amount" % indice)
                         if entregado not in (None, "") else None)
            cobrado += monto
            renglones_de_pago.append(PosPayment(
                id_proyect=id_proyect,
                id_pos_sale=venta.id_pos_sale,
                payment_method=forma,
                amount=monto,
                tendered_amount=entregado,
                change_amount=Decimal("0"),
                reference=(pago.get("reference") or None),
                id_user_received=id_user,
                created_by=id_user,
            ))

        if cobrado < total:
            # Se compara despues de armar todo para poder decir cuanto falta.
            raise AppError("errors.pos_payment_insufficient", 422,
                           {"total": float(total), "paid": float(cobrado)})

        # El vuelto queda ASENTADO en el renglon de pago, no solo devuelto en la
        # respuesta. Sin esto el corte creia que en el cajon habia todo lo que
        # entro y no descontaba lo que salio como cambio: una venta de 100
        # pagada con 200 daba 300 de efectivo esperado cuando en el cajon habia
        # 200. Se encontro probando el cobro contra la base real.
        #
        # Se carga al ultimo pago en efectivo, que es de donde sale el vuelto de
        # verdad -- de una tarjeta no se da cambio.
        vuelto = cobrado - total
        if vuelto > 0:
            en_efectivo = [p for p in renglones_de_pago if p.payment_method == "cash"]
            if en_efectivo:
                en_efectivo[-1].change_amount = vuelto

        for renglon_de_pago in renglones_de_pago:
            db.add(renglon_de_pago)

        venta.subtotal = subtotal
        venta.discount_total = descuento
        venta.tax_total = impuesto
        venta.total = total
        venta.total_cost = coste
        venta.sale_status = "paid"
        venta.paid_at = _ahora()
        db.flush()

        return {
            "sale": venta.serialize(),
            "change": float(cobrado - total),
        }


def venta(id_pos_sale, user_data) -> dict:
    _, id_proyect = _actor(user_data)
    with transaction_context() as db:
        fila = db.get(PosSale, int(id_pos_sale))
        if not fila or fila.deletion_date is not None or fila.id_proyect != id_proyect:
            raise AppError("errors.not_found", 404, {"entity": "pos_sale"})
        renglones = db.scalars(
            select(PosSaleItem).where(
                PosSaleItem.id_pos_sale == fila.id_pos_sale,
                PosSaleItem.deletion_date.is_(None),
            )
        ).all()
        pagos = db.scalars(
            select(PosPayment).where(
                PosPayment.id_pos_sale == fila.id_pos_sale,
                PosPayment.deletion_date.is_(None),
            )
        ).all()
        datos = fila.serialize()
        datos["items"] = [r.serialize() for r in renglones]
        datos["payments"] = [p.serialize() for p in pagos]
        return datos


def ventas(user_data, *, limite=100) -> dict:
    _, id_proyect = _actor(user_data)
    with transaction_context() as db:
        filas = db.scalars(
            select(PosSale).where(
                PosSale.id_proyect == id_proyect,
                PosSale.deletion_date.is_(None),
            ).order_by(PosSale.id_pos_sale.desc()).limit(int(limite))
        ).all()
        return {"data": [v.serialize() for v in filas]}


# --- tablero ------------------------------------------------------------

def resumen_del_dia(user_data) -> dict:
    """Lo que la pantalla de caja muestra arriba.

    Sale de las ventas del turno abierto, que es lo que el cajero tiene delante.
    Sin turno abierto no hay resumen que dar, y eso es un dato, no un error.
    """
    _, id_proyect = _actor(user_data)
    with transaction_context() as db:
        turno = _turno_abierto(db, id_proyect)
        if turno is None:
            return {"open_session": None, "sales_count": 0, "total": 0.0,
                    "by_payment_method": {}}

        total, cuenta = db.execute(
            select(func.coalesce(func.sum(PosSale.total), 0),
                   func.count(PosSale.id_pos_sale))
            .where(PosSale.id_pos_cash_session == turno.id_pos_cash_session,
                   PosSale.sale_status == "paid",
                   PosSale.deletion_date.is_(None))
        ).one()

        return {
            "open_session": turno.serialize(),
            "sales_count": int(cuenta or 0),
            "total": float(total or 0),
            "by_payment_method": _esperado_del_turno(db, turno),
        }
