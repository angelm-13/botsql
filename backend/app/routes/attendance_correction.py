from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.utils.auth import token_required

# Correcciones de checadas: solo exigen sesion; quien puede corregir o ver el
# contador (el supervisor del empleado o RH) lo decide
# services/attendance_correction_service.py.
bp_attendance_correction = Blueprint('attendance_correction', __name__, url_prefix='/attendance_correction')


@bp_attendance_correction.route('/', methods=['GET'])
@token_required
def month_attendance_corrections(user_data):
    """Contador y correcciones de un empleado en un mes (?id_user=&month=AAAA-MM)."""
    from app.services.attendance_correction_service import del_mes
    return jsonify(del_mes(user_data, request.args.get('id_user'), request.args.get('month')))


@bp_attendance_correction.route('/', methods=['POST'])
@token_required
def correct_attendance_record(user_data):
    """Corrige una checada ({id_attendance_record, new_time, reason}) o agrega la que
    falta ({id_user, new_time, reason})."""
    from app.services.attendance_correction_service import corregir
    return jsonify(corregir(user_data, request.get_json() or {})), 201
