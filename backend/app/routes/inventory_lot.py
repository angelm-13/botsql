"""Rutas de lotes y caducidad.

Cuelgan del permiso de `product`, no de una entidad propia. Un lote no es un
catalogo que alguien administre: es una parte del saldo, y quien puede ver el
almacen tiene que poder ver de que lotes esta hecho. Crear lotes tampoco es una
operacion aparte -los crea la entrada de mercancia, al nombrarlos-, asi que no
hay un POST de lotes que guardar.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.inventory_lot_service import (
    apagar_control_de_lotes,
    cuadre_de_lotes,
    encender_control_de_lotes,
    lotes_del_producto,
    por_caducar,
)
from app.services.product_service import ProductService
from app.utils.auth import require_entity_permission, token_required


bp_inventory_lot = Blueprint("inventory_lot", __name__)


@bp_inventory_lot.route("/product/<id_product>/lots", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def lotes_de_un_producto(user_data, id_product):
    """Los lotes vivos, con lo que queda de cada uno y en que sitio."""
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(lotes_del_producto(id_product, user_data))


@bp_inventory_lot.route("/inventory/expiring", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def lo_que_vence(user_data):
    """Lo que vence dentro de N dias, y lo que ya vencio.

    Van separados porque son dos acciones distintas: lo vencido se da de baja
    -con el movimiento `expiry`, que existe aparte de la merma a proposito- y lo
    que esta por vencer se saca antes.
    """
    return jsonify(por_caducar(user_data, dias=request.args.get("days")))


@bp_inventory_lot.route("/product/<id_product>/lots/reconciliation", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def cuadre(user_data, id_product):
    """Si el desglose por lote cuadra con el saldo del producto.

    Que no cuadre significa que algo movio existencia sin pasar por la puerta de
    siempre, y eso es lo que hay que ir a buscar.
    """
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(cuadre_de_lotes(id_product, user_data))


@bp_inventory_lot.route("/product/<id_product>/lot-control", methods=["POST"])
@token_required
@require_entity_permission("product", "update")
def encender(user_data, id_product):
    """Enciende el control por lote, con su lote de apertura.

    No es escribir una columna: si el producto ya tiene existencia, esa
    existencia quedaria fuera de todo lote y no se podria despachar -la salida se
    sirve de los lotes-. Aqui se crea el lote de APERTURA con lo que ya habia, en
    la misma transaccion.
    """
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(encender_control_de_lotes(
        id_product, request.get_json(silent=True) or {}, user_data))


@bp_inventory_lot.route("/product/<id_product>/lot-control", methods=["DELETE"])
@token_required
@require_entity_permission("product", "update")
def apagar(user_data, id_product):
    """Apaga el control. Los lotes se conservan: son el rastro de lo que paso."""
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(apagar_control_de_lotes(id_product, user_data))
