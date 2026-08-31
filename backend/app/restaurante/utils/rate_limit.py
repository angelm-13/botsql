"""
Rate limiting general de API para endpoints de escritura sensible (caja,
facturacion, personal) -- antes el UNICO limite en toda la API era el de
/auth/login (ver routes/auth.py). Mismo patron ya probado ahi: una tabla
en la base de datos (RateLimitHit), no un contador en memoria del proceso,
porque gunicorn en produccion corre con varios workers (procesos
independientes, cada uno con su propia memoria) y un contador en memoria
solo veria una fraccion de las llamadas reales.

Se llama con verify_jwt_in_request(optional=True) en vez de depender de
que @roles_required ya haya corrido antes -- asi funciona sin importar el
orden de los decoradores, y sigue limitando por IP aunque el token falte
o sea invalido.
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.extensions import db
from app.restaurante.models import RateLimitHit
from app.restaurante.utils.errors import ApiError


def rate_limited(action, max_requests=30, window_seconds=60):
    """Limita cuantas veces se puede llamar la ruta decorada, por
    usuario+IP, en una ventana de tiempo. `action` distingue el limite de
    esta ruta del de cualquier otra (dos endpoints no comparten contador)."""
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
            except Exception:
                identity = None
            key = f'{action}:{request.remote_addr}:{identity or "anon"}'
            cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
            # Limpia los hits ya expirados de esta key de una vez (evita que
            # la tabla crezca sin limite; el volumen de estas rutas en un
            # restaurante es bajo, este DELETE no es un problema de rendimiento).
            RateLimitHit.query.filter(RateLimitHit.key == key, RateLimitHit.created_at < cutoff).delete()
            count = RateLimitHit.query.filter(RateLimitHit.key == key, RateLimitHit.created_at >= cutoff).count()
            if count >= max_requests:
                db.session.commit()
                raise ApiError(
                    'Demasiadas solicitudes, intenta de nuevo en unos momentos.',
                    429, 'rate_limited',
                )
            db.session.add(RateLimitHit(key=key))
            db.session.commit()
            return fn(*args, **kwargs)
        return wrapped
    return decorator
