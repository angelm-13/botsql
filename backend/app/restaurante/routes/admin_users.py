"""
Rutas de administracion de personal (rol admin, o superadmin) y de la
bitacora de auditoria (unicamente superadmin).

Antes de esto, los usuarios (meseros/cajeros/cocina/admin) solo se podian
crear editando variables de entorno y volviendo a correr seed.py, y el
nombre real de un mesero (Waiter.name/nickname) estaba fijo en el codigo
-- por eso una cuenta como 'mesero-marcos' podia terminar apuntando al
perfil de mesera equivocado ('Mariana Torres'), y el KPI de servicios por
mesero le daba credito a la persona equivocada.

Con estas rutas, el administrador puede dar de alta una cuenta nueva
(mesero, cajero, cocina o admin) desde la app: si el rol es 'mesero', se
crea junto con ella un perfil de Waiter nuevo con el nombre real de esa
persona, para que quede correctamente ligado desde el primer momento.

'superadmin' es un rol aparte, pensado para soporte/auditoria del
desarrollador de la plantilla, no para el dueno del restaurante: no esta
en VALID_ROLES a proposito, asi que nunca se puede crear ni asignar desde
esta API (solo existe si se siembra por variables de entorno en
seed.py). list_staff() ademas oculta esa cuenta de cualquier admin normal.

Desactivar (is_active=False) sigue siendo la forma recomendada de dar de
baja a alguien -- no borra nada del historial. delete_staff() SI borra el
registro de verdad, pero solo si no tiene historial ligado (pedidos,
cortes de caja, cancelaciones): si lo tiene, la base de datos rechaza el
borrado por las foreign keys y se le pide al admin que desactive en vez
de eliminar.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.restaurante.models import User, Waiter, AuditLog
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action
from app.restaurante.utils.rate_limit import rate_limited
from app import demo as demo_limits

admin_users_bp = Blueprint('admin_users', __name__)

VALID_ROLES = ['mesero', 'cajero', 'cocina', 'admin']

# Advisory lock fijo para serializar cualquier accion que pueda dejar al
# sistema sin ningun admin activo (desactivar o degradar de rol). La
# proteccion existente (nadie puede desactivarse/degradarse A SI MISMO)
# no cubre el caso de dos admins actuando el uno sobre el otro casi al
# mismo tiempo (Admin A desactiva a B mientras B desactiva a A): cada
# request individualmente pasa el chequeo de "target != yo mismo", y sin
# este lock ambos podian comitear, dejando 0 admins activos y sin ningun
# superadmin de emergencia si tampoco se sembro esa cuenta.
ADMIN_INVARIANT_LOCK_NAMESPACE = 918277
ADMIN_INVARIANT_LOCK_KEY = 1


def _ensure_active_admin_remains(excluding_user_id):
    """Bloquea la accion si, tras excluir a excluding_user_id, no queda
    ningun otro usuario con rol 'admin' activo. Debe llamarse DESPUES de
    tomar el advisory lock de arriba, para que dos requests concurrentes
    queden serializadas y la segunda vea ya aplicado el efecto de la
    primera."""
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :key)'), {'ns': ADMIN_INVARIANT_LOCK_NAMESPACE, 'key': ADMIN_INVARIANT_LOCK_KEY})
    remaining = User.query.filter(User.role == 'admin', User.is_active.is_(True), User.id != excluding_user_id).count()
    if remaining == 0:
        raise ApiError('Esta accion dejaria el sistema sin ningun administrador activo', 409, 'no_admins_left')


@admin_users_bp.get('/staff')
@roles_required('admin', 'superadmin')
def list_staff():
    """Lista todas las cuentas (activas e inactivas) con su perfil de mesero si aplica.
    Un admin normal nunca ve la cuenta 'superadmin' en esta lista."""
    is_superadmin = get_jwt().get('role') == 'superadmin'
    users = User.query.order_by(User.created_at.asc()).all()
    items = []
    for u in users:
        if u.role == 'superadmin' and not is_superadmin:
            continue
        data = u.to_dict()
        waiter = Waiter.query.get(u.waiter_id) if u.waiter_id else None
        data['waiter'] = waiter.to_dict() if waiter else None
        items.append(data)
    return jsonify({'items': items})


@admin_users_bp.post('/staff')
@roles_required('admin', 'superadmin')
@rate_limited('staff_create', max_requests=20, window_seconds=60)
def create_staff():
    """Crea una cuenta nueva. Si el rol es 'mesero', tambien crea su perfil de mesero
    (nombre real + apodo), para que el KPI de servicios por mesero lo atribuya bien
    desde el primer pedido que tome."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role')

    if not username or len(username) < 3:
        raise ApiError('El usuario debe tener al menos 3 caracteres', 422, 'validation_error')
    if not password or len(password) < 6:
        raise ApiError('La contrasena debe tener al menos 6 caracteres', 422, 'validation_error')
    if role not in VALID_ROLES:
        raise ApiError('Rol invalido', 422, 'validation_error')
    if User.query.filter_by(username=username).first():
        raise ApiError('Ese usuario ya existe', 409, 'username_taken')
    # Tope de personal de la version freemium (ver app/demo.py) -- sin
    # efecto si FREEMIUM_LIMITS_ENABLED esta apagado.
    if demo_limits.staff_limit_reached():
        raise ApiError(
            f'La version de prueba permite hasta {demo_limits.MAX_STAFF} cuentas de personal.',
            422, 'demo_staff_limit',
        )

    waiter_id = None
    if role == 'mesero':
        name = (data.get('name') or '').strip()
        nickname = (data.get('nickname') or '').strip() or (name.split(' ')[0] if name else '')
        if not name:
            raise ApiError('El nombre del mesero es requerido', 422, 'validation_error')
        waiter = Waiter(name=name, nickname=nickname or name, status='active')
        db.session.add(waiter)
        db.session.flush()
        waiter_id = waiter.id

    user = User(username=username, role=role, is_active=True, waiter_id=waiter_id)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        log_action('staff.create', 'user', user.id, f'Creo la cuenta "{username}" con rol {role}.')
        db.session.commit()
    except IntegrityError as e:
        # El chequeo de arriba (User.query.filter_by(username=...).first())
        # tiene una ventana de carrera: dos admins dando de alta el MISMO
        # username casi al mismo tiempo pueden pasar ambos ese chequeo antes
        # de que cualquiera de los dos haga commit. Sin este try/except, el
        # segundo terminaba en un 500 generico de base de datos en vez de un
        # 409 claro.
        db.session.rollback()
        raise ApiError('Ese usuario ya existe', 409, 'username_taken') from e

    result = user.to_dict()
    result['waiter'] = Waiter.query.get(waiter_id).to_dict() if waiter_id else None
    return jsonify(result), 201


@admin_users_bp.patch('/staff/<int:user_id>')
@roles_required('admin', 'superadmin')
def update_staff(user_id):
    """Edita una cuenta existente: usuario, contrasena (opcional), rol, y si es
    mesero, el nombre/apodo de su perfil de mesero (se crea uno nuevo si el
    usuario aun no tenia, por ejemplo si se le cambia el rol a 'mesero')."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    changes = []

    if 'username' in data:
        new_username = (data.get('username') or '').strip()
        if not new_username or len(new_username) < 3:
            raise ApiError('El usuario debe tener al menos 3 caracteres', 422, 'validation_error')
        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != user.id:
            raise ApiError('Ese usuario ya existe', 409, 'username_taken')
        if new_username != user.username:
            changes.append(f'usuario "{user.username}" -> "{new_username}"')
        user.username = new_username

    if data.get('password'):
        if len(data['password']) < 6:
            raise ApiError('La contrasena debe tener al menos 6 caracteres', 422, 'validation_error')
        user.set_password(data['password'])
        changes.append('contrasena')

    if 'role' in data:
        new_role = data.get('role')
        if new_role not in VALID_ROLES:
            raise ApiError('Rol invalido', 422, 'validation_error')
        if new_role != user.role:
            # Sin este chequeo, el unico admin de la cuenta se podia
            # degradar a si mismo (por ejemplo por error, o probando el
            # formulario) y quedarse sin acceso a admin_users_bp -- sin
            # ningun otro admin que pudiera revertirlo.
            if user.id == int(get_jwt_identity()):
                raise ApiError('No puedes cambiar el rol de tu propia cuenta', 409, 'cannot_change_own_role')
            # Esa proteccion no cubre a dos admins actuando el uno sobre el
            # otro: si el usuario que se esta degradando ES admin activo,
            # hay que garantizar que quede al menos otro admin activo.
            if user.role == 'admin' and user.is_active:
                _ensure_active_admin_remains(excluding_user_id=user.id)
            changes.append(f'rol "{user.role}" -> "{new_role}"')
        user.role = new_role

    if user.role == 'mesero':
        name = (data.get('name') or '').strip()
        nickname = (data.get('nickname') or '').strip()
        waiter = Waiter.query.get(user.waiter_id) if user.waiter_id else None
        if waiter:
            # Solo se actualiza si mandaron un valor nuevo (no se borra el nombre existente por accidente).
            if name:
                waiter.name = name
            if nickname:
                waiter.nickname = nickname
        elif name:
            # Antes no tenia perfil de mesero (por ejemplo se le acaba de cambiar el rol a 'mesero'): se crea uno.
            waiter = Waiter(name=name, nickname=nickname or name, status='active')
            db.session.add(waiter)
            db.session.flush()
            user.waiter_id = waiter.id

    if changes:
        log_action('staff.update', 'user', user.id, f'Edito la cuenta "{user.username}": {", ".join(changes)}.')
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise ApiError('Ese usuario ya existe', 409, 'username_taken') from e
    result = user.to_dict()
    waiter = Waiter.query.get(user.waiter_id) if user.waiter_id else None
    result['waiter'] = waiter.to_dict() if waiter else None
    return jsonify(result)


@admin_users_bp.post('/staff/<int:user_id>/deactivate')
@roles_required('admin', 'superadmin')
def deactivate_staff(user_id):
    """Desactiva una cuenta (ya no podra iniciar sesion). No borra nada del historial."""
    user = User.query.get_or_404(user_id)
    if user.id == int(get_jwt_identity()):
        raise ApiError('No puedes desactivar tu propia cuenta', 409, 'cannot_deactivate_self')
    if user.role == 'admin' and user.is_active:
        _ensure_active_admin_remains(excluding_user_id=user.id)
    user.is_active = False
    log_action('staff.deactivate', 'user', user.id, f'Desactivo la cuenta "{user.username}".')
    db.session.commit()
    return jsonify(user.to_dict())


@admin_users_bp.post('/staff/<int:user_id>/activate')
@roles_required('admin', 'superadmin')
def activate_staff(user_id):
    """Reactiva una cuenta previamente desactivada."""
    user = User.query.get_or_404(user_id)
    user.is_active = True
    log_action('staff.activate', 'user', user.id, f'Reactivo la cuenta "{user.username}".')
    db.session.commit()
    return jsonify(user.to_dict())


@admin_users_bp.delete('/staff/<int:user_id>')
@roles_required('admin', 'superadmin')
@rate_limited('staff_delete', max_requests=20, window_seconds=60)
def delete_staff(user_id):
    """Borra una cuenta de verdad (no solo is_active=False). Solo funciona si
    el usuario no tiene historial ligado (pedidos, cortes de caja,
    cancelaciones): las foreign keys hacen que la base de datos rechace el
    borrado en ese caso, y aqui se convierte ese rechazo en un mensaje claro
    en vez de un error generico de base de datos."""
    user = User.query.get_or_404(user_id)
    if user.id == int(get_jwt_identity()):
        raise ApiError('No puedes eliminar tu propia cuenta', 409, 'cannot_delete_self')
    username = user.username
    try:
        db.session.delete(user)
        log_action('staff.delete', 'user', user.id, f'Elimino la cuenta "{username}".')
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise ApiError(
            f'No se puede eliminar "{username}": tiene historial ligado a su cuenta '
            '(pedidos, cortes de caja, cancelaciones o registros en la bitacora de '
            'auditoria). Desactivala en su lugar.',
            409, 'has_history',
        ) from e
    return jsonify({'deleted': True})


@admin_users_bp.get('/audit')
@roles_required('superadmin')
def list_audit_log():
    """Bitacora de cambios administrativos, mas reciente primero. Oculto
    para cualquier rol que no sea superadmin (ver roles_required arriba)."""
    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    page = max(int(request.args.get('page', 1)), 1)
    per_page = min(max(int(request.args.get('per_page', 100)), 1), 200)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'items': [i.to_dict() for i in items],
        'pagination': {'page': page, 'per_page': per_page, 'total': total},
    })
