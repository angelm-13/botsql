"""Rutas de la orden de compra.

Todo se guarda con el permiso de la entidad `purchase_order` (la politica, con el de
`purchase_policy`): leer para ver, crear para armar una orden, actualizar para
todo lo demas. Lo que ademas exige una capacidad -autorizar, rechazar, comprar lo
que la politica reserva a gerencia- lo comprueba el servicio, que es donde vive la
regla: la ruta cuida la puerta, no la decision.

Los comprobantes suben como `multipart/form-data` (campo `file`) y se descargan por
su propia ruta. La ruta en disco no sale nunca en una respuesta.
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.document_service import SecureDocumentStorage
from app.services.purchase_order_service import (
    add_voucher, authorize_order, cancel_order, create_order, get_order, get_policy,
    list_orders, notificar_orden, purchase_order, receive_order, reject_order,
    remove_voucher, submit_order, supplier_options, update_order, update_policy,
    voucher_content,
)
from app.utils.auth import require_entity_permission, token_required

bp_purchase_order = Blueprint("purchase_order", __name__)

ENTITY = "purchase_order"
POLICY_ENTITY = "purchase_policy"


def _cuerpo():
    return request.get_json(silent=True) or {}


def _almacen():
    return SecureDocumentStorage(current_app.config["UPLOAD_ROOT"])


@bp_purchase_order.route("/purchase-orders", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def listar(user_data):
    return jsonify(list_orders(
        user_data, status=request.args.get("status"),
        id_supplier=request.args.get("supplier"), q=request.args.get("q"),
        limit=request.args.get("limit", 100), offset=request.args.get("offset", 0)))


@bp_purchase_order.route("/purchase-orders", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "create")
def crear(user_data):
    return jsonify(create_order(_cuerpo(), user_data)), 201


@bp_purchase_order.route("/purchase-orders/suppliers", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def proveedores(user_data):
    """Los proveedores dados de alta, para elegir uno. No abre el modulo de CRM."""
    return jsonify(supplier_options(user_data, request.args.get("q")))


@bp_purchase_order.route("/purchase-orders/<id_order>", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def leer(user_data, id_order):
    return jsonify(get_order(id_order, user_data))


@bp_purchase_order.route("/purchase-orders/<id_order>", methods=["PUT"])
@token_required
@require_entity_permission(ENTITY, "update")
def editar(user_data, id_order):
    return jsonify(update_order(id_order, _cuerpo(), user_data))


@bp_purchase_order.route("/purchase-orders/<id_order>/submit", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def enviar(user_data, id_order):
    ficha = submit_order(id_order, user_data)
    if ficha.get("order_status") == "pending_authorization":
        notificar_orden("por_autorizar", ficha, user_data["id_user"])
    return jsonify(ficha)


@bp_purchase_order.route("/purchase-orders/<id_order>/authorize", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def autorizar(user_data, id_order):
    """Pide ademas la capacidad `purchase_authorize`: la comprueba el servicio."""
    ficha = authorize_order(id_order, _cuerpo(), user_data)
    notificar_orden("autorizada", ficha, user_data["id_user"])
    return jsonify(ficha)


@bp_purchase_order.route("/purchase-orders/<id_order>/reject", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def rechazar(user_data, id_order):
    ficha = reject_order(id_order, _cuerpo(), user_data)
    notificar_orden("rechazada", ficha, user_data["id_user"])
    return jsonify(ficha)


@bp_purchase_order.route("/purchase-orders/<id_order>/purchase", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def comprar(user_data, id_order):
    ficha = purchase_order(id_order, _cuerpo(), user_data)
    # Si el comprobante salio mas caro, la orden volvio a autorizacion: eso es lo que
    # le toca saber a quien autoriza, no que "se compro".
    notificar_orden("por_autorizar" if ficha.get("reauthorization_required") else "comprada",
                    ficha, user_data["id_user"])
    return jsonify(ficha)


@bp_purchase_order.route("/purchase-orders/<id_order>/receive", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "read")
def recibir(user_data, id_order):
    """Se guarda con LEER y no con actualizar: recibir es del almacen, que solo consulta
    las ordenes. Lo que lo limita es la capacidad `purchase_receive`, que comprueba el
    servicio."""
    ficha = receive_order(id_order, _cuerpo(), user_data)
    notificar_orden("recibida" if ficha.get("order_status") == "received"
                    else "recibida_en_parte", ficha, user_data["id_user"])
    return jsonify(ficha)


@bp_purchase_order.route("/purchase-orders/<id_order>/cancel", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def cancelar(user_data, id_order):
    return jsonify(cancel_order(id_order, _cuerpo(), user_data))


@bp_purchase_order.route("/purchase-orders/<id_order>/vouchers", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def subir_comprobante(user_data, id_order):
    archivo = request.files.get("file")
    if not archivo or not archivo.filename:
        return jsonify({"error_key": "errors.invalid_field", "meta": {"field": "file"}}), 400
    return jsonify(add_voucher(
        id_order, request.form, archivo.read(), archivo.filename, user_data,
        _almacen())), 201


@bp_purchase_order.route("/purchase-vouchers/<id_voucher>/remove", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "update")
def quitar_comprobante(user_data, id_voucher):
    return jsonify(remove_voucher(id_voucher, _cuerpo(), user_data))


@bp_purchase_order.route("/purchase-vouchers/<id_voucher>/content", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def descargar_comprobante(user_data, id_voucher):
    ruta, mime, nombre = voucher_content(id_voucher, user_data, _almacen())
    return send_file(ruta, mimetype=mime, as_attachment=False, download_name=nombre)


@bp_purchase_order.route("/purchase-policy", methods=["GET"])
@token_required
@require_entity_permission(POLICY_ENTITY, "read")
def leer_politica(user_data):
    return jsonify(get_policy(user_data))


@bp_purchase_order.route("/purchase-policy", methods=["PUT"])
@token_required
@require_entity_permission(POLICY_ENTITY, "update")
def fijar_politica(user_data):
    return jsonify(update_policy(_cuerpo(), user_data))
