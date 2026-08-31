from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timedelta, UTC
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import time
from email.message import EmailMessage
import bcrypt
import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_, select
from app.middleware.public_jwt import require_public_jwt, public_user_payload
from app.models import User, PasswordResetToken
from app.models.session import transaction_context
from app.utils.startup_guard import is_production

try:
    from app.models import EventLog
except Exception:  # pragma: no cover
    EventLog = None

bp_public_auth = Blueprint('public_auth', __name__, url_prefix='/public/auth')
JWT_ALGORITHM = 'HS256'
SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-change-me')
PUBLIC_JWT_SCOPE = os.getenv('PUBLIC_JWT_SCOPE', 'web_shopper')
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_RE = re.compile(r'^[0-9+() .-]{7,25}$')
_rate_limit_hits = defaultdict(deque)
_failed_login_hits = defaultdict(deque)


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _public_jwt_ttl_hours() -> int:
    try:
        return max(int(os.getenv('PUBLIC_JWT_TTL_HOURS', '24')), 1)
    except (TypeError, ValueError):
        return 24


def _reset_ttl_minutes() -> int:
    try:
        return max(int(os.getenv('PASSWORD_RESET_TTL_MINUTES', '60')), 1)
    except (TypeError, ValueError):
        return 60


def _bool(value) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'y', 'si', 'sí', 'on'}


def _client_ip() -> str:
    forwarded = request.headers.get('X-Forwarded-For', '')
    return (forwarded.split(',')[0].strip() or request.remote_addr or '')[:45]


def _check_rate(bucket: str, limit: int, seconds: int) -> bool:
    now = time.time()
    hits = _rate_limit_hits[bucket]
    while hits and now - hits[0] >= seconds:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(now)
    return True


def _check_failed_login(email: str) -> bool:
    now = time.time()
    key = (email or '').strip().lower()
    hits = _failed_login_hits[key]
    while hits and now - hits[0] >= 900:
        hits.popleft()
    return len(hits) < 5


def _record_failed_login(email: str) -> None:
    _failed_login_hits[(email or '').strip().lower()].append(time.time())


def _verify_password(raw_password: str, stored_value: str) -> bool:
    """Comprueba la contrasena del portal publico.

    El respaldo en texto plano existia para cuentas antiguas sin cifrar. En
    produccion no se acepta: una cuenta guardada en claro es un problema que hay
    que arreglar, no uno que convenga tolerar en silencio. Se compara con
    `compare_digest` para no filtrar por el tiempo de respuesta cuantos
    caracteres coinciden.
    """
    if not raw_password or not stored_value:
        return False
    try:
        return bcrypt.checkpw(raw_password.encode('utf-8'), stored_value.encode('utf-8'))
    except Exception:
        if is_production():
            current_app.logger.error(
                'Cuenta del portal con contrasena sin cifrar; se rechaza el acceso.')
            return False
        current_app.logger.warning(
            'Contrasena sin cifrar aceptada fuera de produccion.')
        return hmac.compare_digest(raw_password, stored_value)


def _hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _issue_public_token(user: User) -> str:
    payload = public_user_payload(user)
    payload['exp'] = datetime.now(UTC) + timedelta(hours=_public_jwt_ttl_hours())
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def _sanitize_user(user: User) -> dict:
    return public_user_payload(user)


def _is_active_web_shopper(user: User) -> bool:
    if not user:
        return False
    if str(getattr(user, 'user_type', '') or '').strip().lower() != 'web_shopper':
        return False
    if getattr(user, 'deletion_date', None) is not None:
        return False
    status = getattr(user, 'id_status', 1)
    return str(status if status is not None else 1).strip() == '1'


def _validate_register_payload(data: dict) -> tuple[str, str, str, str, bool, dict | None]:
    email = str(data.get('email') or '').strip().lower()
    password = str(data.get('password') or '')
    full_name = str(data.get('full_name') or '').strip()
    phone = str(data.get('phone') or '').strip()
    accepts_marketing = _bool(data.get('accepts_marketing'))
    errors = {}
    if not EMAIL_RE.match(email):
        errors['email'] = 'invalid'
    if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        errors['password'] = 'weak'
    if len(full_name) < 2 or len(full_name) > 120:
        errors['full_name'] = 'invalid'
    if phone and not PHONE_RE.match(phone):
        errors['phone'] = 'invalid'
    return email, password, full_name, phone, accepts_marketing, (errors or None)


def _write_event(session, event_name: str, user_id=None, before=None, after=None) -> None:
    if EventLog is None:
        return
    try:
        session.add(EventLog(
            table_name='web_shopper',
            field_name=event_name,
            action='update' if before is not None else 'create',
            before_value=before or {},
            after_value=after or {},
            created_by=user_id or 1,
            creation_date=_now(),
            last_update_date=_now(),
        ))
    except Exception:
        pass


def _send_reset_email(to_email: str, token: str) -> None:
    base_url = (os.getenv('PUBLIC_FRONTEND_BASE_URL') or '').rstrip('/')
    reset_url = f'{base_url}/reset-password?token={token}' if base_url else token
    host = os.getenv('SMTP_HOST') or os.getenv('MAIL_SERVER') or ''
    if not host:
        # Sin correo configurado esto imprimia el enlace de restablecimiento en
        # la salida del proceso. En desarrollo es comodo -no hay buzon donde
        # mirar-, pero en produccion el enlace queda en la bitacora del
        # contenedor, y quien pueda leerla se apodera de cualquier cuenta sin
        # necesitar la contrasena.
        if is_production():
            current_app.logger.error(
                'No se pudo enviar el restablecimiento a %s: falta configurar SMTP_HOST. '
                'El enlace NO se registra por seguridad.', to_email)
            raise RuntimeError('SMTP no configurado')
        current_app.logger.warning(
            '[public-auth] Sin SMTP; enlace de restablecimiento para %s: %s '
            '(solo fuera de produccion)', to_email, reset_url)
        return
    port = int(os.getenv('SMTP_PORT') or os.getenv('MAIL_PORT') or '587')
    username = os.getenv('SMTP_USERNAME') or os.getenv('MAIL_USERNAME') or ''
    password = os.getenv('SMTP_PASSWORD') or os.getenv('MAIL_PASSWORD') or ''
    sender = os.getenv('SMTP_FROM_PUBLIC') or os.getenv('SMTP_FROM') or username or 'noreply@localhost'
    msg = EmailMessage()
    msg['Subject'] = 'Recuperacion de contrasena'
    msg['From'] = sender
    msg['To'] = to_email
    msg.set_content(f'Usa este enlace para cambiar tu contrasena: {reset_url}')
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if _bool(os.getenv('SMTP_TLS', 'true')):
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)


@bp_public_auth.route('/register', methods=['POST'])
def register():
    if not _check_rate(f'register:{_client_ip()}', 5, 60):
        return jsonify({'error_key': 'errors.rate_limit_exceeded'}), 429
    data = request.get_json() or {}
    email, password, full_name, phone, accepts_marketing, errors = _validate_register_payload(data)
    if errors:
        return jsonify({'error_key': 'errors.validation_failed', 'errors': errors}), 400
    with transaction_context() as db:
        existing = db.scalars(select(User).where(or_(User.username == email, User.email == email))).first()
        if existing:
            return jsonify({'error_key': 'errors.email_already_registered'}), 409
        now = _now()
        hashed = _hash_password(password)
        user = User(username=email, email=email, full_name=full_name, user_type='web_shopper')
        if hasattr(user, 'password'):
            user.password = hashed
        if hasattr(user, 'password_hash'):
            user.password_hash = hashed
        if hasattr(user, 'principal_phone'):
            user.principal_phone = phone or None
        if hasattr(user, 'accepts_marketing'):
            user.accepts_marketing = accepts_marketing
        if hasattr(user, 'first_name'):
            user.first_name = full_name.split(' ', 1)[0]
        for field, value in {
            'created_by': 1,
            'id_permission': 1,
            'id_proyect': 1,
            'id_status': 1,
            'supervisor': 1,
            'creation_date': now,
            'last_update_date': now,
        }.items():
            if hasattr(user, field) and getattr(user, field, None) in (None, ''):
                setattr(user, field, value)
        db.add(user)
        db.flush()
        _write_event(db, 'web_shopper.register', user.id_user, after={'email': email})
        token = _issue_public_token(user)
        return jsonify({'token': token, 'user': _sanitize_user(user), 'message_key': 'auth.web_shopper_registered'}), 201


@bp_public_auth.route('/login', methods=['POST'])
def login():
    if not _check_rate(f'login-ip:{_client_ip()}', 10, 60):
        return jsonify({'error_key': 'errors.rate_limit_exceeded'}), 429
    data = request.get_json() or {}
    email = str(data.get('email') or data.get('username') or '').strip().lower()
    password = str(data.get('password') or '')
    if not email or not password:
        return jsonify({'error_key': 'errors.auth_missing_credentials'}), 400
    if not _check_failed_login(email):
        return jsonify({'error_key': 'errors.rate_limit_exceeded'}), 429
    with transaction_context() as db:
        user = db.scalars(select(User).where(User.username == email)).first()
        stored = getattr(user, 'password', None) or getattr(user, 'password_hash', '')
        if not _is_active_web_shopper(user) or not _verify_password(password, stored):
            _record_failed_login(email)
            _write_event(db, 'web_shopper.login_failed', None, after={'email': email})
            return jsonify({'error_key': 'errors.auth_invalid_credentials'}), 401
        _write_event(db, 'web_shopper.login_success', user.id_user, after={'email': email})
        return jsonify({'token': _issue_public_token(user), 'user': _sanitize_user(user), 'message_key': 'auth.login_success'})


@bp_public_auth.route('/recover-password', methods=['POST'])
def recover_password():
    data = request.get_json() or {}
    email = str(data.get('email') or '').strip().lower()
    if email and not _check_rate(f'recover:{email}', 3, 3600):
        return jsonify({'error_key': 'errors.rate_limit_exceeded'}), 429
    if not email:
        return jsonify({'message_key': 'auth.password_reset_if_exists'})
    with transaction_context() as db:
        user = db.scalars(select(User).where(User.username == email)).first()
        if _is_active_web_shopper(user):
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
            now = _now()
            record = PasswordResetToken(
                id_user=user.id_user,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=_reset_ttl_minutes()),
                requested_ip=_client_ip(),
                created_at=now,
            )
            db.add(record)
            _write_event(db, 'web_shopper.password_reset_requested', user.id_user, after={'email': email})
            try:
                _send_reset_email(email, token)
            except Exception as exc:
                # La respuesta al cliente no cambia a proposito: decir "no se
                # pudo enviar" revelaria que la cuenta existe. Pero el fallo si
                # tiene que quedar en la bitacora, o nadie se entera de que el
                # correo lleva dias sin salir.
                current_app.logger.error(
                    'No se pudo enviar el correo de restablecimiento: %s', exc)
    return jsonify({'message_key': 'auth.password_reset_if_exists'})


@bp_public_auth.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    token = str(data.get('token') or '').strip()
    new_password = str(data.get('new_password') or '')
    if not token or len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'[0-9]', new_password):
        return jsonify({'error_key': 'errors.validation_failed'}), 400
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    with transaction_context() as db:
        record = db.scalars(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)).first()
        if not record or record.used_at is not None or record.expires_at < _now():
            return jsonify({'error_key': 'errors.invalid_token'}), 400
        user = db.get(User, record.id_user)
        if not _is_active_web_shopper(user):
            return jsonify({'error_key': 'errors.invalid_token'}), 400
        hashed = _hash_password(new_password)
        if hasattr(user, 'password'):
            user.password = hashed
        if hasattr(user, 'password_hash'):
            user.password_hash = hashed
        if hasattr(user, 'last_update_date'):
            user.last_update_date = _now()
        record.used_at = _now()
        _write_event(db, 'web_shopper.password_reset_completed', user.id_user)
    return jsonify({'message_key': 'auth.password_reset_completed'})


@bp_public_auth.route('/me', methods=['GET'])
@require_public_jwt
def me(public_user):
    return jsonify({'user': public_user})


@bp_public_auth.route('/profile', methods=['PATCH'])
@bp_public_auth.route('/me', methods=['PATCH', 'PUT'])
@require_public_jwt
def update_me(public_user):
    data = request.get_json() or {}
    with transaction_context() as db:
        user = db.get(User, public_user.get('id_user'))
        if not _is_active_web_shopper(user):
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        before = _sanitize_user(user)
        if 'full_name' in data:
            full_name = str(data.get('full_name') or '').strip()
            if len(full_name) < 2 or len(full_name) > 120:
                return jsonify({'error_key': 'errors.validation_failed', 'field': 'full_name'}), 400
            user.full_name = full_name
        if 'phone' in data and hasattr(user, 'principal_phone'):
            phone = str(data.get('phone') or '').strip()
            if phone and not PHONE_RE.match(phone):
                return jsonify({'error_key': 'errors.validation_failed', 'field': 'phone'}), 400
            user.principal_phone = phone or None
        if 'tax_id' in data and hasattr(user, 'tax_id'):
            tax_id = str(data.get('tax_id') or '').strip().upper()
            if tax_id and len(tax_id) > 50:
                return jsonify({'error_key': 'errors.validation_failed', 'field': 'tax_id'}), 400
            user.tax_id = tax_id or None
        if 'accepts_marketing' in data and hasattr(user, 'accepts_marketing'):
            user.accepts_marketing = _bool(data.get('accepts_marketing'))
        if hasattr(user, 'last_update_date'):
            user.last_update_date = _now()
        db.flush()
        after = _sanitize_user(user)
        _write_event(db, 'web_shopper.profile_updated', user.id_user, before=before, after=after)
        return jsonify({'user': after, 'message_key': 'auth.profile_updated'})


@bp_public_auth.route('/change-password', methods=['POST'])
@require_public_jwt
def change_password(public_user):
    data = request.get_json() or {}
    current_password = str(data.get('current_password') or '')
    new_password = str(data.get('new_password') or '')
    if len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'[0-9]', new_password):
        return jsonify({'error_key': 'errors.validation_failed'}), 400
    with transaction_context() as db:
        user = db.get(User, public_user.get('id_user'))
        stored = getattr(user, 'password', None) or getattr(user, 'password_hash', '')
        if not _is_active_web_shopper(user) or not _verify_password(current_password, stored):
            return jsonify({'error_key': 'errors.auth_invalid_credentials'}), 401
        hashed = _hash_password(new_password)
        if hasattr(user, 'password'):
            user.password = hashed
        if hasattr(user, 'password_hash'):
            user.password_hash = hashed
        if hasattr(user, 'last_update_date'):
            user.last_update_date = _now()
        _write_event(db, 'web_shopper.password_changed', user.id_user)
    return jsonify({'message_key': 'auth.password_changed'})


@bp_public_auth.route('/logout', methods=['POST'])
@require_public_jwt
def logout(public_user):
    return jsonify({'message_key': 'auth.logout_success'})
