# -*- coding: utf-8 -*-
"""
Servicio de Queue para BI - Gestión de requests asíncronos
Maneja concurrencia de consultas LLM sin bloquear el servidor
"""

from celery import Celery, Task
from celery.result import AsyncResult
from sqlalchemy.engine import Engine
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Configuración Celery (conecta a RabbitMQ que ya está en docker-compose)
celery_app = Celery(
    'bi_tasks',
    broker='amqp://guest:guest@rabbitmq:5672//',
    backend='redis://localhost:6379/0' if False else 'db+postgresql://tyakxa:tyakxa@db_bi:5432/tyakxa_celery'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min max (LLM timeout es 270s)
    task_soft_time_limit=280,  # 4m 40s soft limit
    result_expires=3600,  # Resultados expiran en 1h (si no se consultan)
    worker_prefetch_multiplier=1,  # Un request a la vez (por LLM)
    worker_max_tasks_per_child=100,  # Reciclar workers cada 100 tareas
)

class BiTask(Task):
    """Clase base para tareas BI con manejo de errores"""

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 2}
    retry_backoff = True
    retry_backoff_max = 60

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[BI Queue] Task {task_id} falló: {exc}")

    def on_success(self, result, task_id, args, kwargs):
        logger.info(f"[BI Queue] Task {task_id} completada exitosamente")

@celery_app.task(base=BiTask, bind=True, name='bi.query')
def ejecutar_query_bi(self, user_id: int, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una consulta BI en background

    Args:
        user_id: ID del usuario que hace la consulta
        question: Pregunta en lenguaje natural
        context: Contexto (BD connection info, etc.)

    Returns:
        {
            'task_id': str,
            'user_id': int,
            'status': 'processing|success|failed',
            'result': {...},
            'error': str,
            'started_at': ISO datetime,
            'completed_at': ISO datetime,
            'duration_ms': int
        }
    """
    from app.bi.service import BIService
    from app.bi.config import AjustesBI
    from app.bi.llm_provider import ProveedorOllama

    start_time = datetime.utcnow()

    try:
        # Actualizar estado en DB
        logger.info(f"[BI Queue {self.request.id}] Iniciando query para usuario {user_id}: '{question}'")

        # Crear servicio BI
        service = BIService(
            engine=context.get('engine'),
            ajustes=AjustesBI.desde_entorno(),
            proveedor=ProveedorOllama()
        )

        # Ejecutar
        result = service.responder(question)

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(f"[BI Queue {self.request.id}] Completada en {elapsed_ms}ms")

        return {
            'task_id': self.request.id,
            'user_id': user_id,
            'status': 'success',
            'result': result,
            'error': None,
            'started_at': start_time.isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
            'duration_ms': elapsed_ms
        }

    except Exception as e:
        logger.error(f"[BI Queue {self.request.id}] Error: {str(e)}")
        raise

class QueueManager:
    """Gestor de queue de requests BI"""

    def __init__(self):
        self.celery = celery_app

    def enviar_consulta(self, user_id: int, question: str, engine: Engine) -> str:
        """
        Envía una consulta a la queue y retorna task_id

        El cliente puede polling el resultado con:
            GET /api/v1/bi/task/{task_id}
        """
        task = ejecutar_query_bi.apply_async(
            args=[user_id, question, {'engine': engine}],
            queue='bi_queries',  # Queue dedicada para BI
            priority=5,  # Prioridad media (0-10)
        )
        return task.id

    def obtener_resultado(self, task_id: str) -> Dict[str, Any]:
        """
        Obtiene el resultado de una tarea (polling)

        Estados posibles:
            - PENDING: No iniciada
            - STARTED: En progreso
            - SUCCESS: Completada exitosamente
            - FAILURE: Error
            - RETRY: Reintentando
        """
        result = AsyncResult(task_id, app=celery_app)

        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.successful() else None,
            'error': str(result.info) if result.failed() else None,
            'ready': result.ready(),
            'successful': result.successful(),
        }

    def cancelar_tarea(self, task_id: str) -> bool:
        """Cancela una tarea en progreso"""
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"[BI Queue] Tarea {task_id} cancelada")
        return True

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del queue"""
        stats = celery_app.control.inspect().stats()
        active = celery_app.control.inspect().active()

        return {
            'workers': list(stats.keys()) if stats else [],
            'active_tasks': sum(len(tasks) for tasks in active.values()) if active else 0,
            'queue': 'bi_queries',
            'max_concurrent': 1,  # LLM solo maneja 1 a la vez
        }

# Instancia global
queue_manager = QueueManager()
