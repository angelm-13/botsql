"""Rutas del vale de almacen.

Cuelgan de `/vouchers` y el permiso es la capacidad `warehouse_voucher`.
Capacidad y no entidad porque esta pantalla no es el CRUD de una tabla: escribe
en `incident` -el vale- y en `nm_incident_product` -sus renglones-, y esa
segunda esta fuera del menu a proposito, por ser tabla puente que se edita desde
su dueno. Es el mismo mecanismo de `inventory_adjustment`.

Cada accion es una ruta propia -abrir el vale, cerrar un renglon- en lugar de un
PUT que reciba el estado destino. El estado del vale se DERIVA de sus renglones
y no se puede capturar: es lo que evita un vale "terminado" con herramienta
todavia fuera. Una ruta que aceptara el estado abriria justo ese camino.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.warehouse_voucher_service import (
    autorizar_vale,
    buscar_vales,
    cerrar_renglon,
    consultar_vale,
    crear_vale,
    historial_del_producto,
    lo_que_ha_pedido,
    quien_tiene_que,
    vales_vencidos,
)
from app.utils.auth import require_entity_permission, token_required


bp_warehouse_voucher = Blueprint("warehouse_voucher", __name__)


def _cuerpo():
    return request.get_json(silent=True) or {}


@bp_warehouse_voucher.route("/vouchers", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher", "create")
def abrir_vale(user_data):
    """Abre un vale con sus renglones. Todo o nada."""
    return jsonify(crear_vale(_cuerpo(), user_data)), 201


@bp_warehouse_voucher.route("/prevouchers", methods=["POST"])
@token_required
@require_entity_permission("warehouse_prevoucher", "create")
def abrir_prevale(user_data):
    """Deja un PREVALE: el material pedido, en borrador, sin mover el almacen.

    Ruta aparte y no un campo en el cuerpo de `POST /vouchers` a proposito. Con
    un campo, la puerta seria la misma para pedir y para surtir -- habria que
    guardar la ruta con la capacidad mas permisiva de las dos -- y el permiso
    dejaria de decir nada. Asi cada camino lleva su llave: esta
    `warehouse_prevoucher`, la otra `warehouse_voucher`.
    """
    return jsonify(crear_vale(_cuerpo(), user_data, como_borrador=True)), 201


@bp_warehouse_voucher.route("/vouchers", methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def listar_vales(user_data):
    """La lista de vales, buscable por folio o por responsable.

    `q` busca por las dos cosas a la vez, porque son las dos formas en que
    alguien llega a un vale: con el papel en la mano -"vale 112"- o preguntando
    "que trae Maximino". El folio exacto gana sobre la coincidencia parcial.
    """
    return jsonify(buscar_vales(
        user_data,
        texto=request.args.get("q"),
        estado=request.args.get("status"),
        id_user=request.args.get("id_user"),
        solo_con_pendientes=str(
            request.args.get("only_open") or "").strip().lower()
        in ("1", "true", "si", "yes"),
        pagina=request.args.get("page"),
        por_pagina=request.args.get("per_page"),
    ))


@bp_warehouse_voucher.route("/vouchers/overdue", methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def vencidos(user_data):
    """Lo que ya debio volver y no ha vuelto. Es la razon de llevar vales."""
    return jsonify(vales_vencidos(user_data))


@bp_warehouse_voucher.route("/vouchers/<id_incident>", methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def leer_vale(user_data, id_incident):
    return jsonify(consultar_vale(id_incident, user_data))


@bp_warehouse_voucher.route("/vouchers/<id_incident>/authorize", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher_authorize", "create")
def autorizar(user_data, id_incident):
    """Convierte un borrador en vale: lo abre y saca el material.

    Se guarda con `warehouse_voucher_authorize` y no con `warehouse_voucher`
    porque son dos derechos distintos: escribir el prevale y soltar el
    material. El servicio lo vuelve a comprobar -- la ruta protege la puerta,
    pero la regla vive donde vive la operacion.
    """
    return jsonify(autorizar_vale(id_incident, _cuerpo(), user_data)), 200


@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/return", methods=["POST"])
@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/close", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher", "update")
def devolver_linea(user_data, id_line):
    """Recibe de vuelta lo que salio en ese renglon.

    Dos direcciones para una operacion porque no son dos operaciones: cerrar un
    renglon de prestamo ES devolver lo que salio. `/close` se conserva para lo
    que ya estaba escrito contra ella; `/return` es el nombre de lo que hace.

    El cuerpo acepta `id_location` -a donde vuelve, por omision de donde salio- y
    `note`.
    """
    return jsonify(cerrar_renglon(id_line, _cuerpo(), user_data))


# --- la trazabilidad, por la cosa y por la persona ---
#
# Las tres consultas existian como servicio desde que se cargo el sistema
# anterior -son las que contestan "quien tiene que", "que ha pedido cada uno" y
# "quien se ha llevado esto"- pero NINGUNA estaba expuesta: sin ruta, el front no
# tenia por donde preguntarlas, asi que el dato estaba en la base y no habia
# forma de verlo. Eran codigo muerto medido desde el navegador.
#
# Cuelgan de `/vouchers` y no de `/product` porque salen de `nm_incident_product`
# -los renglones del vale-, no del libro de inventario. Son cosas distintas y la
# ficha del producto ensena las dos por separado: el libro dice cuanto entro y
# salio; esto dice QUIEN se lo llevo.


@bp_warehouse_voucher.route("/vouchers/products/<id_product>/history",
                            methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def historial_de_producto(user_data, id_product):
    """Quien se ha llevado este producto, historico.

    Los renglones son de solo agregado -la devolucion ANADE una entrada en vez
    de reescribir la salida-, asi que esto puede contestar por todos los que se
    lo llevaron y no solo por el ultimo.
    """
    return jsonify(historial_del_producto(id_product, user_data))


@bp_warehouse_voucher.route("/vouchers/holders", methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def quien_tiene(user_data):
    """Quien tiene que, ahora mismo. Con `id_user`, solo el de esa persona."""
    return jsonify(quien_tiene_que(user_data,
                                   id_user=request.args.get("id_user")))


@bp_warehouse_voucher.route("/vouchers/requests", methods=["GET"])
@token_required
@require_entity_permission("warehouse_voucher", "read")
def lo_pedido(user_data):
    """Que ha pedido cada persona, historico."""
    return jsonify(lo_que_ha_pedido(user_data, request.args.get("id_user")))
