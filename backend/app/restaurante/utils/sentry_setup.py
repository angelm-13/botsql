"""
Reporte de errores a Sentry (opcional, apagado por default).

Sin SENTRY_DSN definida no hace nada -- ni siquiera importa sentry_sdk --
para que un despliegue que no lo use (ej. desarrollo local, o un cliente
que todavia no contrata monitoreo) no dependa de un servicio externo para
arrancar. Con la DSN definida, cada excepcion no manejada llega a Sentry
con el mismo request_id que ya usan los logs (ver logging_setup.py), para
poder cruzar un evento de Sentry con sus lineas de log exactas.

Los errores de negocio esperados (ApiError -- "mesa ya ocupada", "caja ya
cerrada", etc.) se excluyen a proposito: son parte del flujo normal de la
app, reportarlos a Sentry solo generaria ruido y escondería los bugs
reales entre cientos de eventos que no ameritan ninguna accion.
"""
import os
from flask import g


def configure_sentry(app):
    dsn = os.getenv('SENTRY_DSN')
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from .errors import ApiError

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=os.getenv('SENTRY_ENVIRONMENT') or os.getenv('FLASK_ENV', 'production'),
        # 0 por default: las trazas de rendimiento tienen costo (y a veces
        # costo monetario en el plan de Sentry) que no todos los despliegues
        # necesitan -- se activan explicitamente subiendo esta variable.
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0')),
        ignore_errors=[ApiError],
    )

    @app.before_request
    def _tag_sentry_request_id():
        # g.request_id lo asigna logging_setup.py en su propio before_request;
        # el orden de antes_request no esta garantizado entre extensiones, asi
        # que esto solo agrega la etiqueta si ya existe -- en el peor caso
        # (el filtro de logging no corrio primero) el evento simplemente sale
        # sin este tag extra, nunca falla por su ausencia.
        request_id = getattr(g, 'request_id', None)
        if request_id:
            sentry_sdk.set_tag('request_id', request_id)
