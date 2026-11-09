from __future__ import annotations

from flask import Blueprint, jsonify

from app.utils.auth import require_entity_permission, token_required

# Primeros pasos de RH: lo controla la capacidad `rh_setup` del Gestor.
bp_rh_setup = Blueprint('rh_setup', __name__, url_prefix='/rh_setup')


@bp_rh_setup.route('/', methods=['GET'])
@token_required
@require_entity_permission('rh_setup', 'read')
def rh_setup_steps(user_data):
    """Cuantos de los 9 pasos de la puesta en marcha de RH estan listos (services/primeros_pasos_rh.py)."""
    from app.services.primeros_pasos_rh import pasos
    return jsonify(pasos())
