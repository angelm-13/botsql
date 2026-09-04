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
    cerrar_renglon,
    consultar_vale,
    crear_vale,
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


@bp_warehouse_voucher.route("/vouchers/lines/<id_line>/close", methods=["POST"])
@token_required
@require_entity_permission("warehouse_voucher", "update")
def cerrar_linea(user_data, id_line):
    """Cierra un renglon. Si era el ultimo, el vale queda cerrado."""
    return jsonify(cerrar_renglon(id_line, _cuerpo(), user_data))
