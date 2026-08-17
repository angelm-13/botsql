from __future__ import annotations

from flask import Blueprint, jsonify, request
from app.graphql.schema import schema

bp_graphql = Blueprint('graphql', __name__, url_prefix='/graphql')


@bp_graphql.route('', methods=['GET'])
def graphql_health():
    return jsonify({'status': 'ok', 'service': 'graphql', 'message_key': 'graphql.health_ok'})


@bp_graphql.route('', methods=['POST'])
def graphql_execute():
    payload = request.get_json(silent=True) or {}
    result = schema.execute(
        payload.get('query'),
        variable_values=payload.get('variables'),
        operation_name=payload.get('operationName'),
        context_value={'request': request},
    )
    response = {}
    if result.errors:
        response['errors'] = [{'message': str(error)} for error in result.errors]
    if result.data is not None:
        response['data'] = result.data
    return jsonify(response), 400 if result.errors else 200
