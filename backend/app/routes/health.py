from flask import Blueprint, jsonify

bp_health = Blueprint('health', __name__)

@bp_health.route('/health')
def health():
    return jsonify({'status': 'ok', 'message_key': 'success.health_ok'})
