"""Simulador de nomina (services/payroll_simulator_service.py).

Todo lo guarda la capacidad `payroll_simulator` del Gestor. Pasar los bonos a un
periodo real escribe movimientos de nomina: pide ademas el alta de
`payroll_movement`, igual que capturarlos a mano.
"""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.services import payroll_simulator_service as simulador
from app.utils.auth import require_entity_permission, token_required

bp_payroll_simulator = Blueprint('payroll_simulator', __name__, url_prefix='/payroll_simulator')


@bp_payroll_simulator.route('/employee/<id_user>', methods=['GET'])
@token_required
@require_entity_permission('payroll_simulator', 'read')
def simulator_employee(user_data, id_user):
    """Forma de salario, grupo, ingreso, jornada y periodos abiertos de un empleado."""
    return jsonify(simulador.datos_del_empleado(id_user))


@bp_payroll_simulator.route('/calculate', methods=['POST'])
@token_required
@require_entity_permission('payroll_simulator', 'read')
def simulator_calculate(user_data):
    return jsonify(simulador.simular(request.get_json(silent=True) or {}))


@bp_payroll_simulator.route('/pdf', methods=['POST'])
@token_required
@require_entity_permission('payroll_simulator', 'read')
def simulator_pdf(user_data):
    pdf, nombre = simulador.pdf_de_simulacion(request.get_json(silent=True) or {})
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename="{nombre}"'})


@bp_payroll_simulator.route('/bonuses', methods=['POST'])
@token_required
@require_entity_permission('payroll_simulator', 'read')
@require_entity_permission('payroll_movement', 'create')
def simulator_bonuses(user_data):
    """Deja los bonos de la simulacion en el periodo real del empleado."""
    return jsonify(simulador.pasar_bonos(request.get_json(silent=True) or {}, user_data.get('id_user'))), 201
