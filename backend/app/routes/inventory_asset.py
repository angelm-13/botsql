"""Rutas para rastrear piezas una por una.

Cuelgan de `/product/<id>/assets` cuando se habla de las piezas de un producto,
y de `/assets/<id>` cuando se habla de una pieza concreta. El permiso se apoya
en la entidad `product`, que es la que ya gobierna el inventario: dar acceso al
almacen da acceso a sus piezas, sin un permiso nuevo que alguien tenga que
acordarse de conceder.

Cada accion es una ruta propia -prestar, devolver, mandar a reparacion- en lugar
de un PUT que reciba el estado destino. Asi la bitacora del servidor dice que se
intento hacer, y no se puede llegar a un estado por un camino que nadie penso.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.inventory_asset_service import (
    asset_history, assign_asset, back_from_repair, find_asset_by_tag,
    lend_asset, list_assets, move_asset, overdue_loans, product_asset_summary,
    register_asset, report_lost, resumen_de_estatus, retire_asset, return_asset,
    send_to_repair,
)
from functools import wraps

from app.utils.auth import _has_entity_permission, require_entity_permission, token_required


bp_inventory_asset = Blueprint("inventory_asset", __name__)


def _cuerpo():
    return request.get_json(silent=True) or {}


def _puede_buscar_en_almacen(fn):
    """Busca en el almacen quien lee `product` O quien levanta vales/prevales.

    El buscador del prevale (`inventoryTrace`) es lo que deja a un Supervisor
    teclear "taladro" y elegir la pieza. Con solo `require_entity_permission(
    "product", "read")`, quitarle el modulo Productos al Supervisor -que es
    lo correcto: no administra el almacen- le apagaba tambien el buscador, y
    el desplegable de sugerencias se quedaba vacio sin decir por que (el 403
    se atrapa en la pantalla). Quien puede pedir material tiene que poder
    buscarlo, sin que eso le abra el modulo de Productos ni su menu.
    """
    from app.models.session import transaction_context
    from app.services.inventory_service import has_capability

    @wraps(fn)
    def wrapper(user_data, *args, **kwargs):
        if not _has_entity_permission(user_data, "product", "read"):
            with transaction_context() as db:
                permitido = (
                    has_capability(db, user_data, "warehouse_voucher")
                    or has_capability(db, user_data, "warehouse_prevoucher")
                )
            if not permitido:
                return jsonify({
                    "error_key": "errors.permission_denied",
                    "meta": {"entity": "product", "action": "read"},
                }), 403
        return fn(user_data, *args, **kwargs)
    return wrapper


# --- consultas ----------------------------------------------------------

@bp_inventory_asset.route("/inventory/trace", methods=["GET"])
@token_required
@_puede_buscar_en_almacen
def localizar_en_almacen(user_data):
    """Buscar cualquier cosa del almacen y ver donde esta y que le paso.

    Es la pregunta que se hace primero en un almacen -"donde esta el
    taladro"- y la que no se podia hacer: habia que saber de antemano el
    producto o el almacen para consultar. Busca por codigo, descripcion y
    etiqueta de pieza, porque la etiqueta es lo que esta pegado en la
    herramienta y lo que lee quien la tiene en la mano.
    """
    from app.services.inventory_trace_service import localizar

    return jsonify(localizar(
        request.args.get("q"),
        user_data,
        proposito=(request.args.get("stock_purpose") or "").strip() or None,
        con_piezas=str(request.args.get("assets") or "1").strip().lower() not in {"0", "false", "no"},
        # Los filtros de la barra lateral. Se recortan en el servidor y no en la
        # pantalla para que el conteo, el aviso de "hay mas" y los desplegables
        # hablen del mismo conjunto que se ve.
        id_familia=request.args.get("id_product_family"),
        id_marca=request.args.get("id_brand"),
        id_material=request.args.get("id_material"),
        id_ubicacion=request.args.get("id_location"),
        estado_pieza=request.args.get("asset_status"),
        clase=request.args.get("item_class"),
        # Paginado. Antes se cortaba en cuarenta resultados y se avisaba "afina
        # la busqueda", que no es una respuesta cuando el filtro ya esta puesto
        # y aun quedan doscientas coincidencias.
        pagina=request.args.get("page"),
        por_pagina=request.args.get("per_page"),
    ))


@bp_inventory_asset.route("/assets", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def listar_piezas(user_data):
    return jsonify(list_assets(
        user_data,
        id_product=request.args.get("id_product"),
        status=request.args.get("status"),
        id_holder=request.args.get("id_holder"),
        id_location=request.args.get("id_location"),
        overdue_only=str(request.args.get("overdue") or "").strip().lower() in {"1", "true", "si"},
        page=request.args.get("page", 1),
        per_page=request.args.get("per_page", 50),
    ))


@bp_inventory_asset.route("/assets/summary", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def resumen_de_piezas(user_data):
    """Cuantas piezas hay en cada estado, ahora mismo.

    Es la pregunta de la manana en un almacen de herramienta: de lo mio, cuanto
    esta prestado, cuanto en reparacion y cuanto no aparece. Antes habia que
    abrir producto por producto.

    `stock_purpose` acota a mercancia o a uso interno, porque son dos preguntas
    distintas: de la herramienta importa quien la tiene y de la mercancia el
    saldo.
    """
    return jsonify(resumen_de_estatus(
        user_data,
        proposito=(request.args.get("stock_purpose") or "").strip() or None,
    ))


@bp_inventory_asset.route("/assets/overdue", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def prestamos_vencidos(user_data):
    """Lo que ya debio volver y no ha vuelto."""
    return jsonify(overdue_loans(user_data))


@bp_inventory_asset.route("/assets/by-tag/<asset_tag>", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def buscar_por_etiqueta(user_data, asset_tag):
    """Busca por la etiqueta pegada en la pieza, que es la que se tiene a mano."""
    return jsonify(find_asset_by_tag(asset_tag, user_data))


@bp_inventory_asset.route("/assets/<id_asset>", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def historia_de_la_pieza(user_data, id_asset):
    return jsonify(asset_history(id_asset, user_data))


@bp_inventory_asset.route("/product/<id_product>/asset-summary", methods=["GET"])
@token_required
@require_entity_permission("product", "read")
def resumen_por_producto(user_data, id_product):
    """Cuantas piezas hay en cada estado, y si cuadran con la existencia."""
    return jsonify(product_asset_summary(id_product, user_data))


# --- alta ---------------------------------------------------------------

@bp_inventory_asset.route("/assets", methods=["POST"])
@token_required
@require_entity_permission("product", "create")
def dar_de_alta(user_data):
    return jsonify(register_asset(_cuerpo(), user_data)), 201


# --- movimientos de la pieza -------------------------------------------

def _accion(nombre, funcion):
    """Registra una ruta por accion.

    Se generan asi porque las nueve comparten forma exacta; escribirlas a mano
    invitaba a que una se quedara sin el decorador de permiso.
    """
    def manejador(user_data, id_asset):
        return jsonify(funcion(id_asset, _cuerpo(), user_data))

    manejador.__name__ = f"accion_{nombre}"
    ruta = bp_inventory_asset.route(f"/assets/<id_asset>/{nombre}", methods=["POST"])
    return ruta(token_required(require_entity_permission("product", "update")(manejador)))


_accion("assign", assign_asset)
_accion("lend", lend_asset)
_accion("return", return_asset)
_accion("send-to-repair", send_to_repair)
_accion("back-from-repair", back_from_repair)
_accion("report-lost", report_lost)
_accion("retire", retire_asset)
_accion("move", move_asset)
