"""
Rutas de autenticacion.

Login por usuario/contrasena (no hay registro publico: los usuarios se
crean por seed.py o a mano). El token JWT incluye el rol y el waiter_id
en additional_claims, que es lo que usa roles_required() para decidir
que puede hacer cada usuario en el resto de la API.
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
)
from app.extensions import db
from app.restaurante.models import User, LoginAttempt
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action
from app.restaurante.utils.rate_limit import rate_limited

auth_bp = Blueprint('auth', __name__)

# Minimo de la contrasena, igual que en admin_users.py al dar de alta o
# editar personal -- si aqui fuera mas laxo, un usuario podria degradar su
# propia contrasena por debajo de lo que el administrador puede ponerle.
MIN_PASSWORD_LENGTH = 6

# Freno anti fuerza-bruta: no habia NINGUN limite antes, asi que
# /auth/login se podia llamar sin restriccion para probar contrasenas de
# cualquier usuario conocido. Se guarda en la base de datos (tabla
# LoginAttempt), NO en un diccionario en memoria del proceso: en produccion
# gunicorn corre con varios workers (procesos independientes con memoria
# separada), asi que un contador en memoria solo veia una fraccion de los
# intentos reales -- con N workers el limite efectivo era N veces el
# configurado, y se reseteaba solo a que un worker reiniciara. La tabla es
# compartida por todos los workers (y cualquier replica futura), asi que el
# limite es real sin importar cuantos procesos corran. Se cuenta por
# username+IP para no bloquear a todo un restaurante detras de la misma IP
# si una sola cuenta esta bajo ataque.
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 10


def _login_rate_limit_key(username):
    return f'{request.remote_addr}:{(username or "").strip().lower()}'


def _enforce_login_rate_limit(username):
    key = _login_rate_limit_key(username)
    cutoff = datetime.utcnow() - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    # Limpia los intentos ya expirados de esta key de una vez (evita que la
    # tabla crezca sin limite con el tiempo; el volumen de login de un
    # restaurante es bajo, asi que este DELETE no es un problema de
    # rendimiento real).
    LoginAttempt.query.filter(LoginAttempt.key == key, LoginAttempt.attempted_at < cutoff).delete()
    attempts = LoginAttempt.query.filter(LoginAttempt.key == key, LoginAttempt.attempted_at >= cutoff).count()
    db.session.commit()
    if attempts >= LOGIN_MAX_ATTEMPTS:
        raise ApiError('Demasiados intentos fallidos. Intenta de nuevo en unos minutos.', 429, 'too_many_attempts')


@auth_bp.post('/login')
def login():
    """Valida usuario/contrasena y devuelve los datos del usuario. El JWT se
    manda en una cookie httpOnly (set_access_cookies, ver JWT_TOKEN_LOCATION
    en app/config.py) para que el navegador nunca lo exponga a JS -- ni
    siquiera al propio codigo de este frontend. Tambien se deja en el cuerpo
    de la respuesta como respaldo para clientes que no son el navegador (la
    suite de pruebas, un futuro cliente API/movil), que siguen autenticando
    con el header Authorization de siempre."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    _enforce_login_rate_limit(username)
    user = User.query.filter_by(username=username, is_active=True).first()
    if not user or not user.check_password(password):
        db.session.add(LoginAttempt(key=_login_rate_limit_key(username)))
        db.session.commit()
        raise ApiError('Invalid credentials', 401, 'invalid_credentials')
    LoginAttempt.query.filter(LoginAttempt.key == _login_rate_limit_key(username)).delete()
    db.session.commit()
    token = create_access_token(identity=str(user.id), additional_claims={
        'role': user.role, 'waiter_id': user.waiter_id
    })
    # El token de refresco NO lleva claims de rol a proposito: si el rol
    # cambiara despues (o la cuenta se desactivara), un refresco debe leer
    # el estado ACTUAL del usuario desde la base de datos, no reciclar el
    # que tenia al iniciar sesion -- ver /auth/refresh mas abajo.
    refresh = create_refresh_token(identity=str(user.id))
    response = jsonify({'access_token': token, 'user': user.to_dict()})
    set_access_cookies(response, token)
    set_refresh_cookies(response, refresh)
    return response


@auth_bp.post('/logout')
def logout():
    """Limpia la cookie del JWT (y su companera CSRF) en el navegador. Sin
    @jwt_required a proposito: cerrar sesion debe funcionar incluso si el
    token ya expiro o es invalido -- el unico objetivo es borrar las cookies
    del lado del cliente, no validar nada del lado del servidor."""
    response = jsonify({'message': 'logged out'})
    unset_jwt_cookies(response)
    return response


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    """Emite un token de acceso nuevo a partir del de refresco.

    Lo llama el propio frontend en segundo plano cuando una peticion falla
    con 'token_expired' (ver request() en frontend/src/services/api.ts), asi
    que para el usuario es invisible: no lo saca al login cada 30 minutos.

    Revalida el usuario contra la base de datos en vez de confiar en el
    token: una cuenta desactivada (o con el rol cambiado) despues de
    iniciar sesion no debe poder renovar su acceso, y los claims nuevos
    deben reflejar el rol ACTUAL, no el que tenia hace 30 dias.
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.is_active:
        raise ApiError('Tu sesion ya no es valida, vuelve a iniciar sesion.', 401, 'session_invalid')
    token = create_access_token(identity=str(user.id), additional_claims={
        'role': user.role, 'waiter_id': user.waiter_id
    })
    response = jsonify({'access_token': token, 'user': user.to_dict()})
    set_access_cookies(response, token)
    return response


@auth_bp.get('/me')
@jwt_required()
def me():
    """Devuelve el usuario actual (segun el token) y sus claims (rol, waiter_id)."""
    user = User.query.get(int(get_jwt_identity()))
    return jsonify({'user': user.to_dict(), 'claims': get_jwt()})


@auth_bp.post('/change-password')
@jwt_required()
@rate_limited('change_password', max_requests=5, window_seconds=300)
def change_password():
    """Permite a CUALQUIER usuario con sesion cambiar su PROPIA contrasena.

    Antes no existia ninguna forma de hacerlo: la unica manera de cambiar
    una contrasena era que un administrador editara la cuenta desde el panel
    de Usuarios (PATCH /api/admin/staff/<id>), lo que obliga a que el mesero
    o cocinero le dicte su contrasena nueva a otra persona -- o peor, que se
    quede con la que le pusieron al darla de alta para siempre.

    Se exige la contrasena ACTUAL a proposito: en un restaurante las
    tablets quedan desatendidas con la sesion abierta, y sin ese requisito
    cualquiera que pasara junto a una podria dejar al mesero fuera de su
    propia cuenta cambiandosela.

    @rate_limited es indispensable aqui, no decorativo: sin el, este
    endpoint seria un oraculo para adivinar la contrasena actual por fuerza
    bruta sin pasar por el freno de /auth/login (5 intentos por 5 minutos).

    Nota sobre sesiones abiertas: el JWT es sin estado, asi que las sesiones
    que YA estaban abiertas con la contrasena vieja siguen siendo validas
    hasta que expiren (12h por default). Cerrar sesion en todos los
    dispositivos requeriria una lista de revocacion de tokens -- ver
    PRODUCTION_CHECKLIST.md.
    """
    data = request.get_json() or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.is_active:
        raise ApiError('Tu sesion ya no es valida, vuelve a iniciar sesion.', 401, 'session_invalid')

    if not user.check_password(current_password):
        raise ApiError('La contrasena actual no es correcta.', 403, 'wrong_current_password')
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ApiError(
            f'La contrasena nueva debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.',
            422, 'validation_error',
        )
    if new_password == current_password:
        raise ApiError('La contrasena nueva debe ser distinta de la actual.', 422, 'validation_error')

    user.set_password(new_password)
    # Se registra el HECHO de que cambio su contrasena, nunca la contrasena
    # en si (ni la vieja ni la nueva) -- la bitacora la puede leer el
    # superadmin, y no tiene por que exponer credenciales de nadie.
    log_action('auth.change_password', 'user', user.id, f'{user.username} cambio su propia contrasena.')
    db.session.commit()
    return jsonify({'message': 'Contrasena actualizada.'})
