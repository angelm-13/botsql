"""
Decorador de autorizacion por rol.

roles_required('mesero', 'cajero') exige que la request tenga un JWT
valido Y que el claim 'role' de ese token (puesto en auth.py al hacer
login) sea uno de los roles permitidos. Se usa en casi todas las rutas
para separar lo que puede hacer cada rol (mesero/cocina/cajero/admin).
"""
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from .errors import ApiError


def roles_required(*roles):
    """Decorador de ruta: solo permite el acceso a los roles listados.

    Ademas del claim 'role' del JWT, vuelve a leer is_active/role del User
    en la base de datos en cada request. Sin esto, desactivar una cuenta o
    bajarle el rol a alguien no tenia ningun efecto hasta que su token
    expirara solo (hasta JWT_ACCESS_HOURS horas despues): mientras tanto
    seguia entrando a todo lo que su rol original permitia, con el JWT ya
    emitido, sin importar lo que un admin acabara de cambiar."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in roles:
                raise ApiError('Insufficient permissions', 403, 'forbidden')
            from flask_jwt_extended import get_jwt_identity
            from app.restaurante.models import User
            user = User.query.get(int(get_jwt_identity()))
            if not user or not user.is_active or user.role != claims.get('role'):
                raise ApiError('Tu sesion ya no es valida, vuelve a iniciar sesion.', 401, 'session_invalid')
            return fn(*args, **kwargs)
        return decorator
    return wrapper
