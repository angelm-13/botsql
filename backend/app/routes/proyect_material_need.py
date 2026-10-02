"""Rutas de la lista de necesidades de material de un proyecto.

Dos puertas, porque son dos preguntas:

* `/proyect/<id>/material-needs` -- lo de UN proyecto. Lo guarda el permiso de la
  entidad `proyect_material_need` (que el Supervisor ya tiene desde
  `operaciones`) y ademas la visibilidad del proyecto: nadie lee ni escribe la
  lista de un proyecto que no puede ver.
* `/material-needs/to-buy` -- lo de TODOS los proyectos contra la existencia. Lo
  guarda la capacidad `purchase_planning`; no es una lectura de la tabla sino un
  cruce con el almacen, y quien compra no tiene por que poder abrir cada proyecto.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.proyect_material_need_service import (
    cancel_need, create_need, list_needs, material_options, to_buy, update_need,
)
from app.utils.auth import require_entity_permission, token_required

bp_proyect_material_need = Blueprint("proyect_material_need", __name__)

ENTITY = "proyect_material_need"


def _cuerpo():
    return request.get_json(silent=True) or {}


def _verdadero(valor) -> bool:
    return str(valor or "").strip().lower() in ("1", "true", "si", "yes")


@bp_proyect_material_need.route("/proyect/<id_proyect>/material-needs", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def listar_necesidades(user_data, id_proyect):
    return jsonify(list_needs(
        id_proyect, user_data,
        incluir_canceladas=_verdadero(request.args.get("include_cancelled"))))


@bp_proyect_material_need.route("/proyect/<id_proyect>/material-needs", methods=["POST"])
@token_required
@require_entity_permission(ENTITY, "create")
def crear_necesidad(user_data, id_proyect):
    return jsonify(create_need(id_proyect, _cuerpo(), user_data)), 201


@bp_proyect_material_need.route("/material-needs/<id_need>", methods=["PUT"])
@token_required
@require_entity_permission(ENTITY, "update")
def editar_necesidad(user_data, id_need):
    return jsonify(update_need(id_need, _cuerpo(), user_data))


@bp_proyect_material_need.route("/material-needs/<id_need>", methods=["DELETE"])
@token_required
@require_entity_permission(ENTITY, "update")
def cancelar_necesidad(user_data, id_need):
    """Cancelar, no borrar: el permiso que se pide es el de ACTUALIZAR."""
    return jsonify(cancel_need(id_need, user_data))


@bp_proyect_material_need.route("/material-needs/materials", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def opciones_de_material(user_data):
    """Id, nombre y unidad: el desplegable de "que material necesito"."""
    return jsonify(material_options())


@bp_proyect_material_need.route("/material-needs/to-buy", methods=["GET"])
@token_required
def por_comprar(user_data):
    # Sin decorador de entidad a proposito: la capacidad se comprueba en el
    # servicio, porque esta vista cruza necesidades con existencias.
    solo_faltantes = request.args.get("only_missing", "1")
    return jsonify(to_buy(user_data, solo_faltantes=_verdadero(solo_faltantes)))
