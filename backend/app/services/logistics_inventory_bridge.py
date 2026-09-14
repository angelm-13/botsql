"""Refleja en el inventario del nucleo la mercancia que logistica guarda.

Por que existe
--------------
Igual que el del restaurante y el del punto de venta: un solo inventario para
todos los proyectos, que es la decision escrita en `pos_inventory_bridge.py` y la
que el libro ya contemplaba con
`source_module IN ('nucleo','pos','restaurante','logistica')`.

Y aqui hacia mas falta que en ningun otro, porque `logistics_inventory` no lleva
libro: cada alta o edicion SOBRESCRIBE `quantity` y no queda rastro de como se
llego a ese numero. Una mercancia que aparece con 40 y manana con 12 no dice si
salieron 28 o si alguien tecleo mal.

Que hace
--------
Anota en el libro del nucleo la DIFERENCIA entre el saldo anterior y el nuevo,
con `source_module = 'logistica'`. La fila de logistica sigue siendo la verdad
sobre de quien es la mercancia y en que estante del almacen del cliente esta; el
libro del nucleo pasa a ser la verdad sobre cuanto hay y como se llego ahi.

Solo entradas y salidas, que es todo lo que pasa aqui
---------------------------------------------------
Logistica no presta ni ajusta: recibe mercancia de un cliente y la despacha. El
signo de la diferencia decide el verbo, y no hay un campo donde equivocarse:

    saldo sube  ->  receive  (+)
    saldo baja  ->  issue    (-)

Sin enlace, no se refleja
-------------------------
Una fila sin `id_product` sigue como hasta hoy. Es lo que permite adoptar esto
mercancia por mercancia, y no se adivina la correspondencia por nombre ni por
SKU: un SKU del cliente no es el codigo del producto en el almacen propio, y
emparejarlos porque se parecen descuenta del renglon equivocado.

Si el reflejo falla, la fila de logistica NO se revierte
-------------------------------------------------------
La mercancia ya entro o ya salio del almacen fisico. Revertir el registro porque
el nucleo no pudo anotarlo dejaria la fila mintiendo sobre lo que hay en el
estante. Lo que no se pudo reflejar se devuelve para que quede a la vista.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.inventory_service import apply_movement_in_session

MODULO = "logistica"


def _entero(valor):
    """La cantidad como entero, o None si es fraccionaria.

    El nucleo lleva piezas enteras. Lo fraccionario se reporta en lugar de
    redondearse: redondear esconde mercancia o la inventa.
    """
    try:
        numero = Decimal(str(valor or 0))
    except (TypeError, ValueError, ArithmeticError):
        return None
    if numero != numero.to_integral_value():
        return None
    return int(numero)


def reflejar_cambio(db, fila, cantidad_anterior, user_data, *, motivo=None) -> dict | None:
    """Anota la diferencia de saldo de una fila de logistica en el nucleo.

    `cantidad_anterior` es el saldo que tenia antes de la operacion; en un alta,
    cero. Devuelve None si no habia nada que reflejar y un diccionario con el
    motivo si se intento y no se pudo. Nunca lanza.
    """
    id_producto = getattr(fila, "id_product", None)
    if not id_producto:
        return None

    antes = _entero(cantidad_anterior)
    ahora = _entero(getattr(fila, "quantity", 0))
    if antes is None or ahora is None:
        return {"id_logistics_inventory": fila.id_logistics_inventory,
                "motivo": "cantidad fraccionaria, el nucleo lleva piezas"}

    delta = ahora - antes
    if delta == 0:
        return None

    # El signo decide el verbo. No hay campo que capturar, asi que no hay campo
    # donde equivocarse.
    tipo = "receive" if delta > 0 else "issue"

    try:
        apply_movement_in_session(
            db,
            id_producto,
            user_data,
            movement_type=tipo,
            quantity_delta=delta,
            # La llave lleva la fila Y el saldo resultante: reintentar la misma
            # operacion no vuelve a mover, pero una operacion posterior sobre la
            # misma fila si -- que es lo correcto, es otro movimiento.
            idempotency_key=(
                "logistica-%s-%s" % (fila.id_logistics_inventory, ahora))[:90],
            id_location=getattr(fila, "id_core_location", None),
            reference_type="logistics_inventory",
            reference_id=str(fila.id_logistics_inventory),
            reason=(motivo or "Mercancia en custodia de logistica")[:250],
            source_module=MODULO,
        )
    except Exception as fallo:  # noqa: BLE001 -- ver la cabecera del modulo
        return {"id_logistics_inventory": fila.id_logistics_inventory,
                "motivo": str(getattr(fallo, "message_key", None) or fallo)[:200]}
    return None
