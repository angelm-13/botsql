from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.utils.auth import require_entity_permission, token_required

# Horas extra: solo exigen sesion; quien puede registrarlas o verlas (el
# supervisor del empleado o RH; la captura a mano solo RH) lo decide
# services/overtime_service.py.
bp_overtime = Blueprint('overtime', __name__, url_prefix='/overtime')


@bp_overtime.route('/', methods=['GET'])
@token_required
def list_overtime(user_data):
    """Horas extra y tiempo no autorizado de un rango (?from=&to=)."""
    from app.services.overtime_service import del_rango
    return jsonify(del_rango(user_data, request.args.get('from'), request.args.get('to')))


@bp_overtime.route('/', methods=['POST'])
@token_required
def create_overtime(user_data):
    """Autoriza, aprueba lo no autorizado o captura horas extra."""
    from app.services.overtime_service import registrar
    return jsonify(registrar(user_data, request.get_json() or {})), 201


# El segundo paso (jefe y luego RH, 2026-11-04): solo RH, que en el Gestor es
# quien edita las checadas (attendance_record), igual que en las correcciones.
@bp_overtime.route('/<int:id_overtime>/review', methods=['POST'])
@token_required
@require_entity_permission('attendance_record', 'update')
def review_overtime(user_data, id_overtime):
    """RH confirma ({approve: true}) o rechaza lo que registro el jefe."""
    from app.services.overtime_service import confirmar
    datos = request.get_json(silent=True) or {}
    return jsonify(confirmar(user_data, id_overtime, bool(datos.get('approve')), datos.get('notes')))


@bp_overtime.route('/<int:id_overtime>', methods=['DELETE'])
@token_required
def delete_overtime(user_data, id_overtime):
    """Quita un registro que todavia no se paga."""
    from app.services.overtime_service import borrar
    return jsonify(borrar(user_data, id_overtime))
