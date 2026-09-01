"""Puerta del punto de venta desde la sesion de TYAKXA.

Un solo inicio de sesion: el usuario entra en TYAKXA y el nucleo habla con el
POS por detras. Aqui se comprueban dos cosas antes de reenviar nada:

1. Que la ruta este declarada como reenviable. Un proxy que pasa cualquier ruta
   da acceso a todo el POS -incluida su administracion- a cualquiera que tenga
   la capacidad mas basica.
2. Que el rol del actor tenga la capacidad que esa ruta exige. Las de caja piden
   `pos_terminal`; las de configuracion y reportes, `pos_admin`.

La comprobacion es contra `entity_permission`, el mismo mecanismo que gobierna
el resto del sistema, para que conceder el punto de venta a un rol se haga en el
mismo lugar que todo lo demas.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.session import transaction_context
from app.services.inventory_service import has_capability
from app.services.pos_gateway import capacidad_para, estado, reenviar
from app.utils.auth import token_required
from app.utils.errors import AppError


bp_pos = Blueprint("pos", __name__, url_prefix="/pos")


@bp_pos.route("/status", methods=["GET"])
@token_required
def estado_del_puente(user_data):
    """Si el puente esta configurado y el POS responde.

    Sin esto, un puente mal configurado se manifiesta como pantallas vacias y
    hay que ir a leer bitacoras para saber por que.
    """
    with transaction_context() as db:
        alcanza = (
            has_capability(db, user_data, "pos_terminal")
            or has_capability(db, user_data, "pos_admin")
        )
    if not alcanza:
        raise AppError("errors.permission_denied", 403, {"capability": "pos_terminal"})
    return jsonify(estado())


@bp_pos.route("/api/<path:ruta>", methods=["GET", "POST", "PUT", "PATCH"])
@token_required
def puerta(user_data, ruta):
    capacidad = capacidad_para(request.method, ruta)
    if capacidad is None:
        # Se responde 404 y no 403: decir "esa ruta existe pero no la puedes
        # usar" describiria el POS a quien no tiene por que conocerlo.
        raise AppError("errors.resource_not_found", 404)

    with transaction_context() as db:
        if not has_capability(db, user_data, capacidad):
            raise AppError("errors.permission_denied", 403, {"capability": capacidad})

    datos, codigo = reenviar(
        request.method,
        ruta,
        actor=user_data.get("id_user"),
        params=request.args.to_dict(flat=True),
        cuerpo=request.get_json(silent=True),
    )
    return jsonify(datos), codigo
