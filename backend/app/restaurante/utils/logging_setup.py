"""
Logging estructurado + correlation ID.

Cada linea de log sale como un objeto JSON (timestamp, nivel, logger,
mensaje, request_id) en vez de texto plano -- facilita mandar los logs a
un agregador (Loki, CloudWatch, Datadog, etc.) sin tener que parsear texto
libre con regex. En DevelopmentConfig se usa un formato legible en su
lugar (mas comodo para leer directo en la terminal durante desarrollo).

request_id: cada request recibe un id (el que traiga el header
X-Request-ID si el proxy/cliente ya mando uno, o uno nuevo generado aqui)
que viaja en CADA linea de log de esa request Y se regresa en la
respuesta con ese mismo header -- asi se puede rastrear una request
especifica de punta a punta (nginx -> backend -> logs) sin tener que
adivinar cual linea de log pertenece a cual peticion cuando hay trafico
concurrente de varias mesas/usuarios a la vez.
"""
import json
import logging
import uuid
from flask import g, request


class RequestIdFilter(logging.Filter):
    """Agrega record.request_id a cada log record, para que el formatter
    (JSON o texto) lo pueda incluir sin que cada logger.info(...) tenga
    que pasarlo a mano. Fuera de una request activa (ej. un log durante el
    arranque de la app) no hay g.request_id -- se usa '-' en su lugar."""
    def filter(self, record):
        try:
            record.request_id = g.request_id
        except RuntimeError:  # fuera de un contexto de aplicacion/request
            record.request_id = '-'
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            'timestamp': self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    """Reemplaza los handlers default de Flask/root logger por uno solo,
    con el formato elegido segun LOG_JSON (ver app/config.py), y agrega el
    correlation id a cada request via before_request/after_request."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    if app.config.get('LOG_JSON', True):
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s'
        ))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())

    @app.after_request
    def _add_request_id_header(response):
        request_id = getattr(g, 'request_id', None)
        if request_id:
            response.headers['X-Request-ID'] = request_id
        return response
