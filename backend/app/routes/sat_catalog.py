"""Consulta del catalogo c_ClaveProdServ del SAT.

Da al frontend una forma de encontrar la clave correcta sobre el catalogo real
cargado en la base, en lugar de teclearla de memoria.
"""

from flask import Blueprint, jsonify, request

from app.services.sat_catalog_service import catalog_status, search_product_keys
from app.utils.auth import require_entity_permission, token_required


bp_sat_catalog = Blueprint("sat_catalog", __name__, url_prefix="/sat")


@bp_sat_catalog.route("/clave-prod-serv", methods=["GET"])
@token_required
@require_entity_permission("invoice", "read")
def search_clave_prod_serv(user_data):
    """Busca por texto o por prefijo de clave. Parametro `q`."""
    status = catalog_status()
    return jsonify({
        "items": search_product_keys(request.args.get("q", ""), request.args.get("limit")),
        "catalog_loaded": status["loaded"],
    })


@bp_sat_catalog.route("/clave-prod-serv/status", methods=["GET"])
@token_required
@require_entity_permission("invoice", "read")
def clave_prod_serv_status(user_data):
    """Cuantas claves hay cargadas, para avisar en la interfaz si falta importar."""
    return jsonify(catalog_status())
