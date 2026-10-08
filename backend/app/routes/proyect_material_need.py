"""Rutas de la lista de necesidades de un proyecto.

Tres puertas, porque son tres preguntas:

* `/proyect/<id>/material-needs` y `/material-needs/<id>` -- lo de UN proyecto. Lo
  guarda el permiso de la entidad `proyect_material_need` (que el Supervisor ya
  tiene desde `operaciones`) y ademas la visibilidad del proyecto: nadie lee ni
  escribe la lista de un proyecto que no puede ver.
* `/material-needs/suggestions` -- lo que el catalogo sugiere para lo que el
  supervisor esta escribiendo. Solo ayuda a capturar.
* `/material-needs/to-buy`, `/link` y `/confirm-buy` -- lo de TODOS los proyectos.
  Lo guarda la capacidad `purchase_planning` (verla para leer, editarla para
  revisar); no es una lectura de la tabla sino un cruce con el almacen, y quien
  compra no tiene por que poder abrir cada proyecto.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.proyect_material_need_service import (
    cancel_need, confirm_buy, create_need, link_need, list_needs, return_need,
    suggest_materials, to_buy, update_need,
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


@bp_proyect_material_need.route("/material-needs/suggestions", methods=["GET"])
@token_required
@require_entity_permission(ENTITY, "read")
def sugerencias(user_data):
    """Lo del catalogo que parece lo que el supervisor esta escribiendo."""
    return jsonify(suggest_materials(request.args.get("q"), user_data))


@bp_proyect_material_need.route("/material-needs/to-buy", methods=["GET"])
@token_required
def por_comprar(user_data):
    # Sin decorador de entidad a proposito: la capacidad se comprueba en el
    # servicio, porque esta vista cruza necesidades con existencias.
    solo_faltantes = request.args.get("only_missing", "1")
    return jsonify(to_buy(user_data, solo_faltantes=_verdadero(solo_faltantes)))


@bp_proyect_material_need.route("/material-needs/<id_need>/link", methods=["POST"])
@token_required
def vincular(user_data, id_need):
    """"Ya existe en el almacen": se vincula al catalogo. Pide EDITAR la capacidad."""
    return jsonify(link_need(id_need, _cuerpo().get("id_material"), user_data))


@bp_proyect_material_need.route("/material-needs/<id_need>/return", methods=["POST"])
@token_required
def devolver(user_data, id_need):
    """"No se entiende": vuelve al supervisor con un motivo. Pide EDITAR la capacidad."""
    return jsonify(return_need(id_need, _cuerpo().get("note"), user_data))


@bp_proyect_material_need.route("/material-needs/<id_need>/confirm-buy", methods=["POST"])
@token_required
def confirmar_compra(user_data, id_need):
    """"Si hay que comprarlo": se confirma. Pide EDITAR la capacidad."""
    return jsonify(confirm_buy(id_need, user_data))
