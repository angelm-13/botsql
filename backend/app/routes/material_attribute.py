"""Rutas de las caracteristicas del material.

Dos grupos, con dos permisos distintos y a proposito:

  * el CATALOGO -que caracteristicas declara una familia- se guarda con la
    entidad `material_attribute`. Es configuracion: declarar "largo" en
    desarmadores cambia el alta de todos los desarmadores;
  * los VALORES de un material se guardan con `material`, "update". Llenar el
    largo de un desarmador es editar ese desarmador, y quien puede editar
    materiales tiene que poder hacerlo sin que le concedan un permiso aparte.

Sin esa separacion, el almacenista que captura materiales necesitaria permiso de
configuracion para llenar un campo, o el que configura podria editar materiales.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.material_attribute_service import (
    actualizar_atributo,
    agregar_opcion,
    atributos_de_la_familia,
    caracteristicas_de,
    crear_atributo,
    eliminar_atributo,
    eliminar_opcion,
    guardar_valores,
    materiales_que_cumplen,
)
from app.utils.auth import require_entity_permission, token_required


bp_material_attribute = Blueprint("material_attribute", __name__)


def _cuerpo():
    return request.get_json(silent=True) or {}


# --- el catalogo que declara la familia ----------------------------------

@bp_material_attribute.route(
    "/material-attributes/by-family/<id_product_family>", methods=["GET"])
@token_required
@require_entity_permission("material_attribute", "read")
def atributos_por_familia(user_data, id_product_family):
    """Lo que esta familia declara, con sus opciones y cuantos la usan."""
    return jsonify(atributos_de_la_familia(id_product_family, user_data))


@bp_material_attribute.route("/material-attributes", methods=["POST"])
@token_required
@require_entity_permission("material_attribute", "create")
def declarar_atributo(user_data):
    """Declara una caracteristica en una familia."""
    return jsonify(crear_atributo(_cuerpo(), user_data)), 201


@bp_material_attribute.route("/material-attributes/<id_attribute>", methods=["PUT"])
@token_required
@require_entity_permission("material_attribute", "update")
def editar_atributo(user_data, id_attribute):
    """Renombra o reordena. El tipo de dato no se cambia."""
    return jsonify(actualizar_atributo(id_attribute, _cuerpo(), user_data))


@bp_material_attribute.route("/material-attributes/<id_attribute>", methods=["DELETE"])
@token_required
@require_entity_permission("material_attribute", "delete")
def retirar_atributo(user_data, id_attribute):
    """Retira una caracteristica, si ningun material la usa."""
    return jsonify(eliminar_atributo(id_attribute, user_data))


@bp_material_attribute.route(
    "/material-attributes/<id_attribute>/options", methods=["POST"])
@token_required
@require_entity_permission("material_attribute", "update")
def agregar_valor_permitido(user_data, id_attribute):
    """Agrega un valor permitido a una caracteristica de lista."""
    return jsonify(agregar_opcion(id_attribute, _cuerpo(), user_data)), 201


@bp_material_attribute.route(
    "/material-attributes/options/<id_option>", methods=["DELETE"])
@token_required
@require_entity_permission("material_attribute", "delete")
def retirar_valor_permitido(user_data, id_option):
    """Retira un valor permitido, si ningun material lo eligio."""
    return jsonify(eliminar_opcion(id_option, user_data))


# --- los valores de un material -----------------------------------------

@bp_material_attribute.route(
    "/material/<id_material>/attributes", methods=["GET"])
@token_required
@require_entity_permission("material", "read")
def leer_caracteristicas(user_data, id_material):
    """Lo que el material tiene, junto a lo que su familia declara."""
    return jsonify(caracteristicas_de(id_material, user_data))


@bp_material_attribute.route(
    "/material/<id_material>/attributes", methods=["PUT"])
@token_required
@require_entity_permission("material", "update")
def escribir_caracteristicas(user_data, id_material):
    """Guarda el juego completo: lo que no venga se retira."""
    return jsonify(guardar_valores(id_material, _cuerpo(), user_data))


@bp_material_attribute.route("/material-attributes/search", methods=["POST"])
@token_required
@require_entity_permission("material", "read")
def buscar_por_caracteristicas(user_data):
    """"Cuantos desarmadores Truper planos de 6 pulgadas tengo."

    Es POST y no GET porque los criterios son una lista de objetos con rangos, y
    eso metido en la direccion sale ilegible y con el limite de longitud encima.
    """
    return jsonify(materiales_que_cumplen(_cuerpo(), user_data))
