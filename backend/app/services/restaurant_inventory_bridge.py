"""Refleja en el inventario del nucleo lo que el restaurante consume.

Por que existe
--------------
La decision es que haya un solo inventario para todos los proyectos --
`pos_inventory_bridge.py` lo dice en su cabecera y el libro lo contempla desde
20260901140000, con `source_module IN ('nucleo','pos','restaurante','logistica')`.

El restaurante llevaba el suyo aparte: `restaurant_inventory_item` con su saldo y
`restaurant_inventory_movement` con su propio libro. Funciona, y por si solo esta
bien hecho -- guarda el saldo antes y despues de cada movimiento --, pero deja
dos respuestas distintas a "cuanto aceite hay": la del restaurante y la del
almacen. Y cuando dos vistas del mismo hecho discrepan, no hay forma de saber
cual creer.

Que hace, y que no
------------------
Anota en el libro del nucleo el mismo movimiento que el restaurante acaba de
registrar, con `source_module = 'restaurante'`. NO sustituye su libro: el suyo
guarda el saldo por insumo y el coste unitario, que son cosas del restaurante; el
del nucleo contesta cuanta existencia hay en la empresa. Cada uno responde lo
suyo, y ahora concuerdan.

El vocabulario se reduce a entrada y salida
------------------------------------------
El restaurante maneja cuatro tipos y el nucleo no necesita esa distincion:

    entrada          ->  receive     (+)
    salida, merma    ->  issue       (-)
    ajuste           ->  adjustment  (delta = nuevo - anterior)

`merma` entra como salida y no como su propio tipo a proposito: para el almacen
una merma es existencia que se fue, igual que un consumo. Lo que la distingue --
que se perdio en lugar de venderse -- vive en el libro del restaurante, que es
donde alguien va a preguntarlo.

Sin enlace, no se refleja
-------------------------
Un insumo sin `id_product` sigue como hasta hoy: su saldo propio y nada en el
nucleo. Es lo que permite adoptar esto insumo por insumo. Y no se adivina la
correspondencia por nombre, por el mismo motivo que el POS: emparejar "ACEITE" con
"ACEITE VEGETAL 1L" descuenta del renglon equivocado sin que nada avise.

Si el reflejo falla, el movimiento del restaurante NO se deshace
---------------------------------------------------------------
El consumo ya ocurrio -- el platillo salio de la cocina -- y revertirlo porque el
nucleo no pudo anotarlo dejaria el saldo del restaurante mintiendo sobre lo que
hay en la despensa. Lo que no se pudo reflejar se devuelve para que quede a la
vista, y el descuadre se ve en la conciliacion. Es la misma regla que el POS
aplica con una venta ya cobrada.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.inventory_service import apply_movement_in_session

MODULO = "restaurante"

# Como se traduce cada tipo del restaurante al vocabulario del nucleo, y con que
# signo. `ajuste` no esta aqui: su delta se calcula, no se declara.
TRADUCCION = {
    "entrada": ("receive", 1),
    "salida": ("issue", -1),
    "merma": ("issue", -1),
}


def _unidades(cantidad):
    """La cantidad como entero, o None si no se puede.

    El nucleo lleva piezas enteras y el restaurante decimales -- 0.750 kg de
    harina --. Lo fraccionario se REPORTA en lugar de redondearse: redondear
    0.4 a 0 esconde un consumo, y redondear a 1 inventa existencia que salio.
    """
    try:
        numero = Decimal(str(cantidad))
    except (TypeError, ValueError, ArithmeticError):
        return None
    if numero != numero.to_integral_value():
        return None
    return int(numero)


def reflejar_movimiento(db, item, movimiento, user_data) -> dict | None:
    """Anota en el libro del nucleo el movimiento que el restaurante registro.

    Devuelve None si no habia nada que reflejar -- insumo sin enlace -- y un
    diccionario con el motivo si se intento y no se pudo. Nunca lanza: el
    movimiento del restaurante ya esta escrito y no se deshace por esto.
    """
    id_producto = getattr(item, "id_product", None)
    if not id_producto:
        return None

    tipo = str(getattr(movimiento, "movement_type", "") or "").strip().lower()
    if tipo == "ajuste":
        # El ajuste fija el saldo, no lo suma: el delta es la diferencia.
        try:
            delta = int(Decimal(str(movimiento.new_quantity))
                        - Decimal(str(movimiento.previous_quantity)))
        except (TypeError, ValueError, ArithmeticError):
            return {"id_restaurant_inventory_item": item.id_restaurant_inventory_item,
                    "motivo": "cantidad no entera"}
        if delta == 0:
            return None
        movimiento_nucleo, signo = "adjustment", 1
        unidades = delta
    else:
        par = TRADUCCION.get(tipo)
        if par is None:
            return {"id_restaurant_inventory_item": item.id_restaurant_inventory_item,
                    "motivo": "tipo de movimiento sin traduccion: %s" % tipo}
        movimiento_nucleo, signo = par
        unidades = _unidades(movimiento.quantity)
        if unidades is None:
            return {"id_restaurant_inventory_item": item.id_restaurant_inventory_item,
                    "motivo": "cantidad fraccionaria, el nucleo lleva piezas"}
        if unidades == 0:
            return None
        unidades = signo * abs(unidades)

    try:
        apply_movement_in_session(
            db,
            id_producto,
            user_data,
            movement_type=movimiento_nucleo,
            quantity_delta=unidades,
            # La llave lleva el identificador del movimiento del restaurante:
            # reintentar el reflejo del mismo movimiento no descuenta dos veces.
            idempotency_key=(
                "restaurante-mov-%s" % movimiento.id_restaurant_inventory_movement)[:90],
            id_location=getattr(item, "id_location", None),
            reference_type="restaurant_inventory_movement",
            reference_id=str(movimiento.id_restaurant_inventory_movement),
            reason=(getattr(movimiento, "reason", None)
                    or "Movimiento de insumos del restaurante")[:250],
            source_module=MODULO,
        )
    except Exception as fallo:  # noqa: BLE001 -- ver la cabecera del modulo
        return {"id_restaurant_inventory_item": item.id_restaurant_inventory_item,
                "motivo": str(getattr(fallo, "message_key", None) or fallo)[:200]}
    return None
