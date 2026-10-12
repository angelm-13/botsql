# -*- coding: utf-8 -*-
"""
Endpoints REST para Queue de BI
Maneja requests asíncronos sin bloquear el servidor
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

bp_bi_queue = Blueprint('bi_queue', __name__)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar JWT (simplificado, usar el de tyakxa)
        from flask import request
        auth = request.headers.get('Authorization')
        if not auth:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@bp_bi_queue.route('/query/async', methods=['POST'])
@require_auth
def query_async() -> Tuple[dict, int]:
    """
    POST /api/v1/bi/query/async

    Envía una pregunta a la queue (sin bloquear)

    Body:
        {
            "prompt": "¿Cuántas facturas hay?",
            "priority": 5  # 0-10, default 5
        }

    Response:
        {
            "task_id": "abc-123-xyz",
            "status": "queued",
            "message": "Consulta encolada. Usa GET /task/{task_id} para monitorear",
            "check_url": "/api/v1/bi/task/abc-123-xyz"
        }
    """
    from app.bi.queue_service import queue_manager
    from app.utils.auth import current_user
    from app.database import db

    try:
        data = request.get_json()
        question = data.get('prompt', '').strip()
        priority = data.get('priority', 5)

        if not question:
            return {'error': 'Pregunta vacía'}, 400

        user = current_user()

        # Enviar a queue
        task_id = queue_manager.enviar_consulta(
            user_id=user.id,
            question=question,
            engine=db.engine
        )

        logger.info(f"[BI Queue] Query encolada: {task_id} (usuario {user.id})")

        return {
            'task_id': task_id,
            'status': 'queued',
            'message': 'Consulta encolada. Polling con GET /task/{task_id}',
            'check_url': f'/api/v1/bi/task/{task_id}',
            'priority': priority,
        }, 202  # 202 Accepted

    except Exception as e:
        logger.error(f"[BI Queue] Error encolando: {e}")
        return {'error': str(e)}, 500

@bp_bi_queue.route('/task/<task_id>', methods=['GET'])
@require_auth
def get_task_status(task_id: str) -> Tuple[dict, int]:
    """
    GET /api/v1/bi/task/{task_id}

    Obtiene el estado de una tarea

    Response:
        {
            "task_id": "abc-123-xyz",
            "status": "STARTED|SUCCESS|FAILURE|PENDING",
            "result": {...},
            "error": null,
            "ready": false,
            "progress_percent": 0
        }
    """
    from app.bi.queue_service import queue_manager

    try:
        result = queue_manager.obtener_resultado(task_id)

        # Agregar progreso estimado
        if result['status'] == 'STARTED':
            result['progress_percent'] = 50  # LLM en progreso
            result['message'] = 'Generando SQL (60-100s)...'
        elif result['status'] == 'PENDING':
            result['progress_percent'] = 0
            result['message'] = 'En cola, esperando disponibilidad...'
        elif result['status'] == 'SUCCESS':
            result['progress_percent'] = 100
            result['message'] = 'Completada'
        elif result['status'] == 'FAILURE':
            result['progress_percent'] = 0
            result['message'] = f"Error: {result.get('error', 'Desconocido')}"

        return result, 200

    except Exception as e:
        logger.error(f"[BI Queue] Error obteniendo status: {e}")
        return {'error': str(e)}, 500

@bp_bi_queue.route('/task/<task_id>', methods=['DELETE'])
@require_auth
def cancel_task(task_id: str) -> Tuple[dict, int]:
    """
    DELETE /api/v1/bi/task/{task_id}

    Cancela una tarea en progreso
    """
    from app.bi.queue_service import queue_manager

    try:
        cancelled = queue_manager.cancelar_tarea(task_id)

        return {
            'task_id': task_id,
            'cancelled': cancelled,
            'message': 'Tarea cancelada'
        }, 200

    except Exception as e:
        logger.error(f"[BI Queue] Error cancelando: {e}")
        return {'error': str(e)}, 500

@bp_bi_queue.route('/stats', methods=['GET'])
@require_auth
def queue_stats() -> Tuple[dict, int]:
    """
    GET /api/v1/bi/stats

    Obtiene estadísticas del queue

    Response:
        {
            "workers": ["worker1", "worker2"],
            "active_tasks": 1,
            "queue": "bi_queries",
            "max_concurrent": 1
        }
    """
    from app.bi.queue_service import queue_manager

    try:
        stats = queue_manager.obtener_estadisticas()
        return stats, 200

    except Exception as e:
        logger.error(f"[BI Queue] Error obteniendo stats: {e}")
        return {'error': str(e)}, 500
