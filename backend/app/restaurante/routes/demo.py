"""
Endpoint publico del estado de la version freemium/de prueba.

A proposito SIN @jwt_required: la pantalla de login necesita mostrar el
banner de cuota/expiracion (ver frontend/src/main.tsx) ANTES de que exista
cualquier sesion, y el gate de expiracion global (ver
block_if_demo_expired en app/__init__.py) exime esta ruta explicitamente
para que el frontend pueda seguir preguntando el estado incluso despues de
que la prueba ya vencio.
"""
from flask import Blueprint, jsonify
from app.restaurante import demo as demo_limits

demo_bp = Blueprint('demo', __name__)


@demo_bp.get('/status')
def status():
    return jsonify(demo_limits.demo_status())
