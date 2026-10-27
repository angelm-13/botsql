from __future__ import annotations
from datetime import datetime, timedelta, UTC
import hashlib
import os
import hmac

import bcrypt

from app.utils import login_throttle
from app.utils.startup_guard import is_production
import jwt
import pyotp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import select
from app.models.session import transaction_context
from app.models import User, UserMfa
from app.utils.auth import SECRET_KEY, _has_entity_permission, token_required
from app.utils.user_access import can_manage_user

bp_auth = Blueprint('auth', __name__, url_prefix='/auth')
JWT_ALGORITHM = 'HS256'
MFA_TEMP_MINUTES = int(os.getenv('MFA_TEMP_TOKEN_MINUTES', '5'))
ACCESS_TOKEN_MINUTES = int(os.getenv('ACCESS_TOKEN_MINUTES', '480'))
ISSUER_NAME = os.getenv('MFA_ISSUER_NAME') or os.getenv('MFA_ISSUER') or 'TYAKXA ERP CRM SCM'


def _mfa_encryption_key() -> bytes:
    key_source = os.getenv('MFA_ENCRYPTION_KEY') or os.getenv('SECRET_KEY') or SECRET_KEY
    return hashlib.sha256(str(key_source).encode('utf-8')).digest()


def _mfa_to_bytes(value) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode('utf-8')
    try:
        return bytes(value)
    except Exception:
        return None


def _mfa_encrypt_secret(secret_text: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    encrypted = AESGCM(_mfa_encryption_key()).encrypt(nonce, secret_text.encode('utf-8'), None)
    return encrypted, nonce


def _mfa_decrypt_secret(mfa: UserMfa) -> str:
    encrypted = _mfa_to_bytes(getattr(mfa, 'secret', None))
    nonce = _mfa_to_bytes(getattr(mfa, 'secret_iv', None))
    if not encrypted:
        return ''
    if nonce:
        try:
            return AESGCM(_mfa_encryption_key()).decrypt(nonce, encrypted, None).decode('utf-8')
        except Exception:
            # Backward compatibility: existing databases may contain a plain text
            # secret in the VARBINARY column from older generated projects.
            pass
    try:
        return encrypted.decode('utf-8')
    except Exception:
        return ''


def _mfa_apply_defaults(mfa: UserMfa, *, reset_attempts: bool = False) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    if hasattr(mfa, 'failed_attempts') and (reset_attempts or getattr(mfa, 'failed_attempts', None) is None):
        mfa.failed_attempts = 0
    if hasattr(mfa, 'backup_codes') and getattr(mfa, 'backup_codes', None) is None:
        mfa.backup_codes = {}
    if hasattr(mfa, 'created_at') and getattr(mfa, 'created_at', None) is None:
        mfa.created_at = now
    if hasattr(mfa, 'updated_at'):
        mfa.updated_at = now


def _issue_token(payload: dict, minutes: int) -> str:
    data = dict(payload)
    data['exp'] = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode(data, SECRET_KEY, algorithm=JWT_ALGORITHM)


def _truthy(value: str | None) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'y', 'si', 'sí', 'on'}


def _bootstrap_admin_username() -> str:
    return (os.getenv('BOOTSTRAP_ADMIN_USERNAME') or 'admin1').strip() or 'admin1'


def _is_bootstrap_admin(user: User) -> bool:
    if not _truthy(os.getenv('BOOTSTRAP_ADMIN_ENABLED', 'true')):
        return False
    return (
        str(getattr(user, 'username', '') or '') == _bootstrap_admin_username()
        and str(getattr(user, 'user_type', '') or '').lower() == 'admin'
    )


def _user_payload(user: User, *, mfa_enabled: bool = False) -> dict:
    bootstrap_admin = _is_bootstrap_admin(user)
    return {
        'id_user': getattr(user, 'id_user', None),
        'id_proyect': getattr(user, 'id_proyect', None),
        'username': getattr(user, 'username', ''),
        'user_type': getattr(user, 'user_type', 'user'),
        'id_permission': getattr(user, 'id_permission', None),
        # Computed from BOOTSTRAP_ADMIN_* configuration; not a database column.
        'is_bootstrap_admin': bootstrap_admin,
        'is_superuser': bootstrap_admin,
        # Computed from user_mfa.enabled; not a column on user.
        'mfa_enabled': bool(mfa_enabled),
    }


def _request_is_bootstrap_admin(user_data: dict) -> bool:
    return bool(user_data.get('is_bootstrap_admin') or user_data.get('is_superuser'))


def _normalize_user_type(value) -> str:
    return str(value or '').strip().lower()


def _request_can_manage_target_user(user_data: dict, target: User) -> bool:
    """Mismas protecciones que `routes/user.py`: ver `app/utils/user_access.py`."""
    if _request_is_bootstrap_admin(user_data):
        return True
    if not target or _is_bootstrap_admin(target):
        return False
    return can_manage_user(user_data, getattr(target, 'id_permission', None),
                           actor_is_bootstrap=False, target_is_bootstrap=False)


def _verify_password(raw_password: str, stored_value: str) -> bool:
    """Comprueba la contrasena contra el valor guardado.

    El respaldo en texto plano existe por las semillas antiguas, pero significa
    que una contrasena guardada sin cifrar entra tal cual. En produccion eso no
    se tolera: si el valor guardado no es un hash, la cuenta simplemente no
    entra, y queda en la bitacora para que se pueda corregir.
    """
    if not raw_password or not stored_value:
        return False
    try:
        return bcrypt.checkpw(raw_password.encode('utf-8'), stored_value.encode('utf-8'))
    except Exception:
        pass

    if is_production():
        current_app.logger.error(
            'Cuenta con contrasena sin cifrar; se rechaza el acceso. '
            'Restablecela para que se guarde con hash.'
        )
        return False
    current_app.logger.warning(
        'Contrasena sin cifrar aceptada fuera de produccion. Restablecela antes de desplegar.'
    )
    return hmac.compare_digest(raw_password, stored_value)


def _login_error(error_key: str, status_code: int):
    return jsonify({'error': error_key, 'error_key': error_key}), status_code


def _client_ip() -> str:
    from app.utils.client_ip import client_ip
    return client_ip()


@bp_auth.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _login_error('errors.auth_missing_credentials', 400)
    username = str(data.get('username') or '').strip()
    password = str(data.get('password') or '')
    if not username or not password:
        return _login_error('errors.auth_missing_credentials', 400)

    origen = _client_ip()
    # Sin freno se podian probar contrasenas sin limite: con un diccionario y
    # unos minutos, cualquier cuenta con contrasena debil cae.
    if login_throttle.esta_bloqueado(username, origen):
        espera = login_throttle.segundos_para_reintentar(username, origen)
        respuesta = jsonify({
            'error': 'errors.auth_too_many_attempts',
            'error_key': 'errors.auth_too_many_attempts',
            'meta': {'retry_after_seconds': espera},
        })
        respuesta.headers['Retry-After'] = str(espera)
        return respuesta, 429

    with transaction_context() as db:
        user = db.scalars(select(User).where(
            User.username == username, User.deletion_date.is_(None))).first()
        if user and _normalize_user_type(getattr(user, 'user_type', None)) == 'web_shopper':
            login_throttle.registrar_fallo(username, origen)
            return _login_error('errors.auth_invalid_credentials', 401)
        stored_password = getattr(user, 'password', None) or getattr(user, 'password_hash', '')
        # Un usuario dado de baja no entra: misma respuesta que una contrasena
        # mala, para no revelar que la cuenta existio.
        if not user or user.deletion_date is not None or not _verify_password(password, stored_password):
            login_throttle.registrar_fallo(username, origen)
            return _login_error('errors.auth_invalid_credentials', 401)

        login_throttle.registrar_exito(username)

        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == user.id_user, UserMfa.enabled == True)).first()
        if mfa:
            user_payload = _user_payload(user, mfa_enabled=True)
            temp_token = _issue_token({**user_payload, 'mfa_step': True}, MFA_TEMP_MINUTES)
            return jsonify({'mfa_required': True, 'temp_token': temp_token, 'message_key': 'auth.mfa_required'})

        user_payload = _user_payload(user, mfa_enabled=False)
        access_token = _issue_token(user_payload, ACCESS_TOKEN_MINUTES)
        return jsonify({'mfa_required': False, 'token': access_token, 'user': user_payload, 'message_key': 'auth.login_success'})


@bp_auth.route('/mfa/verify-login', methods=['POST'])
def verify_login_mfa():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error_key': 'errors.mfa_missing_code'}), 400
    temp_token = str(data.get('temp_token') or '')
    code = str(data.get('code') or '').replace(' ', '')
    if not temp_token or not code:
        return jsonify({'error_key': 'errors.mfa_missing_code'}), 400

    try:
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        return jsonify({'error_key': 'errors.invalid_token'}), 401
    if not payload.get('mfa_step'):
        return jsonify({'error_key': 'errors.invalid_token'}), 401

    # Con la contrasena ya dada, 10^6 codigos son pocos: mismo freno que el login,
    # por usuario y por origen, para que el segundo factor no se pueda adivinar.
    llave_mfa = 'mfa:%s' % payload.get('id_user')
    origen = _client_ip()
    if login_throttle.esta_bloqueado(llave_mfa, origen):
        espera = login_throttle.segundos_para_reintentar(llave_mfa, origen)
        respuesta = jsonify({'error_key': 'errors.auth_too_many_attempts',
                             'meta': {'retry_after_seconds': espera}})
        respuesta.headers['Retry-After'] = str(espera)
        return respuesta, 429

    with transaction_context() as db:
        user = db.get(User, payload.get('id_user'))
        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == payload.get('id_user'), UserMfa.enabled == True)).first()
        if not user or user.deletion_date is not None or not mfa:
            return jsonify({'error_key': 'errors.mfa_not_enabled'}), 404
        secret = _mfa_decrypt_secret(mfa)
        if not secret:
            return jsonify({'error_key': 'errors.mfa_not_configured'}), 404
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            login_throttle.registrar_fallo(llave_mfa, origen)
            return jsonify({'error_key': 'errors.mfa_invalid_code'}), 401
        login_throttle.registrar_exito(llave_mfa)
        user_payload = _user_payload(user, mfa_enabled=True)
        access_token = _issue_token(user_payload, ACCESS_TOKEN_MINUTES)
        return jsonify({'token': access_token, 'user': user_payload, 'message_key': 'auth.login_success'})


@bp_auth.route('/mfa/setup', methods=['POST'])
@token_required
def setup_mfa(user_data):
    is_bootstrap = _request_is_bootstrap_admin(user_data)
    with transaction_context() as db:
        existing_mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == user_data.get('id_user'))).first()
        if existing_mfa and existing_mfa.enabled and not is_bootstrap:
            return jsonify({'error_key': 'auth.mfa_already_enabled'}), 409

    secret = pyotp.random_base32()
    encrypted_secret, secret_iv = _mfa_encrypt_secret(secret)
    username = user_data.get('username') or f"user-{user_data.get('id_user')}"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER_NAME)
    with transaction_context() as db:
        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == user_data.get('id_user'))).first()
        if not mfa:
            mfa = UserMfa(id_user=user_data.get('id_user'), secret=encrypted_secret, secret_iv=secret_iv, enabled=False)
            _mfa_apply_defaults(mfa, reset_attempts=True)
            db.add(mfa)
        else:
            mfa.secret = encrypted_secret
            mfa.secret_iv = secret_iv
            mfa.enabled = False
            _mfa_apply_defaults(mfa, reset_attempts=True)
        db.flush()
    return jsonify({'secret': secret, 'otpauth_uri': uri, 'message_key': 'auth.mfa_setup_created'})


@bp_auth.route('/mfa/enable', methods=['POST'])
@token_required
def enable_mfa(user_data):
    data = request.get_json() or {}
    code = str(data.get('code') or '').replace(' ', '')
    is_bootstrap = _request_is_bootstrap_admin(user_data)
    with transaction_context() as db:
        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == user_data.get('id_user'))).first()
        if not mfa:
            return jsonify({'error_key': 'errors.mfa_not_configured'}), 404
        if mfa.enabled and not is_bootstrap:
            return jsonify({'error_key': 'auth.mfa_already_enabled'}), 409
        secret = _mfa_decrypt_secret(mfa)
        if not secret:
            return jsonify({'error_key': 'errors.mfa_not_configured'}), 404
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            return jsonify({'error_key': 'errors.mfa_invalid_code'}), 401
        mfa.enabled = True
        _mfa_apply_defaults(mfa)
        db.flush()
    return jsonify({'message_key': 'auth.mfa_enabled'})


@bp_auth.route('/mfa/reset/<int:target_user_id>', methods=['POST'])
@token_required
def reset_user_mfa(user_data, target_user_id):
    # Reiniciar el MFA de otra persona es administrar usuarios: lo concede el
    # Gestor (editar `user`), no el tipo de cuenta.
    if not _has_entity_permission(user_data, 'user', 'update'):
        return jsonify({'error_key': 'errors.forbidden'}), 403
    with transaction_context() as db:
        target = db.get(User, target_user_id)
        if not target:
            return jsonify({'error_key': 'errors.resource_not_found'}), 404
        if _is_bootstrap_admin(target) and not _request_is_bootstrap_admin(user_data):
            return jsonify({'error_key': 'errors.resource_not_found'}), 404
        if not _request_can_manage_target_user(user_data, target):
            return jsonify({'error_key': 'errors.user_hierarchy_denied'}), 403
        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == target_user_id)).first()
        if mfa:
            mfa.enabled = False
            if hasattr(mfa, 'secret'):
                mfa.secret = b''
            if hasattr(mfa, 'secret_iv'):
                mfa.secret_iv = b''
            if hasattr(mfa, 'failed_attempts'):
                mfa.failed_attempts = 0
            if hasattr(mfa, 'locked_until'):
                mfa.locked_until = None
            if hasattr(mfa, 'last_used_at'):
                mfa.last_used_at = None
            if hasattr(mfa, 'backup_codes'):
                mfa.backup_codes = {}
            _mfa_apply_defaults(mfa, reset_attempts=True)
        db.flush()
    return jsonify({'message_key': 'auth.mfa_reset_success'})


@bp_auth.route('/mfa/disable', methods=['POST'])
@token_required
def disable_mfa(user_data):
    if not _request_is_bootstrap_admin(user_data):
        return jsonify({'error_key': 'errors.forbidden'}), 403
    with transaction_context() as db:
        mfa = db.scalars(select(UserMfa).where(UserMfa.id_user == user_data.get('id_user'))).first()
        if mfa:
            mfa.enabled = False
            _mfa_apply_defaults(mfa)
            db.flush()
    return jsonify({'message_key': 'auth.mfa_disabled'})
