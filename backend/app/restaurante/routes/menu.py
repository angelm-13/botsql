"""
Rutas del menu: platillos (Dish), categorias (Category) y guisados (Guisado).

Lectura (GET) esta disponible para cualquier rol autenticado que la use
(el mesero la usa para armar la carta). Altas, ediciones y bajas
(POST/PUT/DELETE) son exclusivas de los roles 'admin'/'superadmin': el
cajero puede cobrar y ver reportes, pero no puede tocar el catalogo.

Las bajas son "soft delete" (is_active=False), nunca se borra el
renglon de la base de datos, para no perder el historial de ordenes que
ya referencian ese platillo o guisado.
"""
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt
from app.extensions import db
from app.restaurante.models import Dish, Guisado, Category
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action

menu_bp = Blueprint('menu', __name__)

VALID_SCHEDULES = {'all', 'weekday', 'weekend', '0', '1', '2', '3', '4', '5', '6'}
# Cualquier cuenta con sesion (todos los roles) puede LEER el menu; solo
# admin/superadmin pueden escribirlo (ver docstring del modulo).
ANY_STAFF_ROLE = ('mesero', 'cocina', 'cajero', 'admin', 'superadmin')


def _validate_price(value, field_name='precio'):
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise ApiError(f'El {field_name} debe ser un numero', 422, 'validation_error') from None
    if price < 0:
        raise ApiError(f'El {field_name} no puede ser negativo', 422, 'validation_error')
    return price


def _validate_schedule(value):
    if value not in VALID_SCHEDULES:
        raise ApiError('Horario invalido', 422, 'validation_error')
    return value


def active_category_slugs():
    return {c.slug for c in Category.query.filter_by(is_active=True).all()}


def slugify(name):
    """Convierte un nombre de categoria en un slug estable: minusculas, sin
    acentos, espacios/puntuacion a '_'. Se calcula una sola vez al crear la
    categoria (ver create_category) -- Dish.category guarda este slug, asi
    que nunca vuelve a cambiar aunque despues se edite el nombre."""
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '_', normalized.lower()).strip('_')
    return slug or 'categoria'


@menu_bp.get('/dishes')
@roles_required(*ANY_STAFF_ROLE)
def list_dishes():
    """Lista platillos, con filtros opcionales de categoria/busqueda/paginacion.

    Por default solo trae platillos activos; `include_inactive=1` tambien
    trae los dados de baja (usado por el panel de admin para poder
    reactivarlos, por eso queda restringido a admin/superadmin/cajero mas
    abajo). El parametro `today=1` filtra ademas por
    Dish.is_available_today(), que respeta el campo `schedule` de cada
    platillo (todos los dias, entre semana, fin de semana, o un dia
    especifico de la semana) -- asi el mesero solo ve el platillo del dia
    y las aguas frescas que realmente aplican hoy.
    """
    include_inactive = request.args.get('include_inactive')
    if include_inactive and get_jwt().get('role') not in ('admin', 'superadmin', 'cajero'):
        raise ApiError('Insufficient permissions', 403, 'forbidden')
    q = Dish.query if include_inactive else Dish.query.filter_by(is_active=True)
    category = request.args.get('category')
    search = request.args.get('search')
    only_today = request.args.get('today')
    if category:
        q = q.filter(Dish.category == category)
    if search:
        q = q.filter(Dish.title.ilike(f'%{search}%'))
    dishes = q.order_by(Dish.category, Dish.title).all()
    if only_today:
        # 'Hoy' se calcula en la hora LOCAL real del dispositivo
        # (tz_offset_minutes), igual que /cashier/dashboard -- usar
        # date.today() (reloj del servidor, tipicamente UTC dentro del
        # contenedor) hacia que un platillo de fin de semana desapareciera o
        # apareciera varias horas antes/despues de la medianoche real del
        # restaurante para cualquier zona horaria distinta de UTC+0.
        try:
            tz_offset_minutes = int(request.args.get('tz_offset_minutes', 0))
        except (TypeError, ValueError):
            tz_offset_minutes = 0
        tz_offset_minutes = max(-840, min(720, tz_offset_minutes))
        local_today = (datetime.utcnow() - timedelta(minutes=tz_offset_minutes)).date()
        dishes = [d for d in dishes if d.is_available_today(local_today)]
    page = max(int(request.args.get('page', 1)), 1)
    per_page = min(max(int(request.args.get('per_page', 100)), 1), 200)
    start = (page - 1) * per_page
    items = dishes[start:start + per_page]
    return jsonify({
        'items': [d.to_dict() for d in items],
        'pagination': {'page': page, 'per_page': per_page, 'total': len(dishes)}
    })


@menu_bp.post('/dishes')
@roles_required('admin', 'superadmin')
def create_dish():
    """Crea un platillo nuevo en el catalogo. Solo administrador."""
    data = request.get_json() or {}
    for field in ['title', 'category']:
        if not data.get(field):
            raise ApiError('Missing field: ' + field, 422, 'validation_error')
    # 'price' se valida aparte de 'title'/'category': un platillo con precio
    # $0 (ej. agua de cortesia, staff meal) es un valor legitimo, pero
    # `not data.get('price')` lo trataba igual que si el campo no viniera
    # en absoluto, porque `not 0` es True en Python.
    if data.get('price') is None:
        raise ApiError('Missing field: price', 422, 'validation_error')
    price = _validate_price(data['price'])
    # 'production_cost' es opcional, pero si viene explicito como null (la
    # clave SI existe en el JSON) hay que tratarlo igual que "no vino" en
    # vez de pasar None a una columna NOT NULL -- el mismo bug que ya se
    # arreglo arriba para 'price'.
    production_cost = _validate_price(data['production_cost'], 'costo de produccion') if data.get('production_cost') is not None else 0
    if data['category'] not in active_category_slugs():
        raise ApiError('Invalid category', 422, 'validation_error')
    schedule = _validate_schedule(data.get('schedule', 'all'))
    dish = Dish(
        title=data['title'],
        description=data.get('description'),
        image_url=(data.get('image_url') or '').strip() or None,
        size_label=(data.get('size_label') or '').strip() or None,
        icon=data.get('icon') or 'plate',
        category=data['category'],
        price=price,
        production_cost=production_cost,
        requires_guisado=bool(data.get('requires_guisado', False)),
        schedule=schedule,
    )
    db.session.add(dish)
    db.session.flush()
    log_action('dish.create', 'dish', dish.id, f'Creo el platillo "{dish.title}" en la categoria "{dish.category}".')
    db.session.commit()
    return jsonify(dish.to_dict()), 201


@menu_bp.put('/dishes/<int:dish_id>')
@roles_required('admin', 'superadmin')
def update_dish(dish_id):
    """Edita cualquier campo de un platillo existente. Solo administrador."""
    dish = Dish.query.get_or_404(dish_id)
    data = request.get_json() or {}
    if 'category' in data and data['category'] not in active_category_slugs():
        raise ApiError('Invalid category', 422, 'validation_error')
    if 'price' in data:
        if data['price'] is None:
            raise ApiError('El precio es requerido', 422, 'validation_error')
        data['price'] = _validate_price(data['price'])
    if 'production_cost' in data:
        if data['production_cost'] is None:
            raise ApiError('El costo de produccion es requerido', 422, 'validation_error')
        data['production_cost'] = _validate_price(data['production_cost'], 'costo de produccion')
    if 'schedule' in data:
        data['schedule'] = _validate_schedule(data['schedule'])
    for field in ['title', 'description', 'image_url', 'size_label', 'icon', 'category', 'price', 'production_cost', 'requires_guisado', 'schedule', 'is_active']:
        if field in data:
            value = data[field]
            if field in ('image_url', 'size_label') and isinstance(value, str):
                value = value.strip() or None
            setattr(dish, field, value)
    log_action('dish.update', 'dish', dish.id, f'Edito el platillo "{dish.title}".')
    db.session.commit()
    return jsonify(dish.to_dict())


@menu_bp.delete('/dishes/<int:dish_id>')
@roles_required('admin', 'superadmin')
def delete_dish(dish_id):
    """Da de baja un platillo (is_active=False). No borra el registro ni su historial."""
    dish = Dish.query.get_or_404(dish_id)
    dish.is_active = False
    log_action('dish.delete', 'dish', dish.id, f'Dio de baja el platillo "{dish.title}".')
    db.session.commit()
    return jsonify({'deleted': True})


@menu_bp.get('/categories')
@roles_required(*ANY_STAFF_ROLE)
def list_categories():
    """Lista las categorias activas, en el orden que definio el admin."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    return jsonify({'items': [c.to_dict() for c in categories]})


@menu_bp.post('/categories')
@roles_required('admin', 'superadmin')
def create_category():
    """Crea una categoria nueva. El slug se genera del nombre y no se
    vuelve a exponer para edicion (ver slugify): es lo que queda guardado
    en Dish.category para siempre. Solo administrador."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        raise ApiError('Missing field: name', 422, 'validation_error')
    slug = slugify(name)
    existing = Category.query.filter_by(slug=slug).first()
    if existing:
        if existing.is_active:
            raise ApiError('A category with that name already exists', 422, 'validation_error')
        # El slug pertenece a una categoria dada de baja: reactivarla en vez
        # de dejar el nombre "atorado" para siempre (antes, borrar una
        # categoria por error volvia su nombre irrecuperable).
        existing.is_active = True
        existing.icon = data.get('icon') or existing.icon
        existing.color = data.get('color') or existing.color
        log_action('category.create', 'category', existing.id, f'Reactivo la categoria "{existing.name}".')
        db.session.commit()
        return jsonify(existing.to_dict()), 201
    max_order = db.session.query(db.func.max(Category.sort_order)).scalar() or 0
    category = Category(
        slug=slug, name=name,
        icon=data.get('icon') or 'utensils',
        color=data.get('color') or '#71717a',
        sort_order=max_order + 1,
    )
    db.session.add(category)
    db.session.flush()
    log_action('category.create', 'category', category.id, f'Creo la categoria "{category.name}".')
    db.session.commit()
    return jsonify(category.to_dict()), 201


@menu_bp.put('/categories/<int:category_id>')
@roles_required('admin', 'superadmin')
def update_category(category_id):
    """Edita nombre/icono/color/orden de una categoria existente. El slug
    nunca se toca aqui (ver slugify): los platillos ya guardados siguen
    apuntando al mismo Dish.category aunque el nombre visible cambie."""
    category = Category.query.get_or_404(category_id)
    data = request.get_json() or {}
    for field in ['name', 'icon', 'color', 'sort_order', 'is_active']:
        if field in data:
            setattr(category, field, data[field])
    log_action('category.update', 'category', category.id, f'Edito la categoria "{category.name}".')
    db.session.commit()
    return jsonify(category.to_dict())


@menu_bp.delete('/categories/<int:category_id>')
@roles_required('admin', 'superadmin')
def delete_category(category_id):
    """Da de baja una categoria (is_active=False). Solo administrador. Los
    platillos que ya la usaban conservan su Dish.category tal cual (no se
    reasignan ni se borran) -- simplemente dejan de poder elegirse para
    platillos nuevos."""
    category = Category.query.get_or_404(category_id)
    category.is_active = False
    log_action('category.delete', 'category', category.id, f'Dio de baja la categoria "{category.name}".')
    db.session.commit()
    return jsonify({'deleted': True})


@menu_bp.get('/guisados')
@roles_required(*ANY_STAFF_ROLE)
def list_guisados():
    """Lista los guisados activos, en orden alfabetico."""
    guisados = Guisado.query.filter_by(is_active=True).order_by(Guisado.name).all()
    return jsonify({'items': [g.to_dict() for g in guisados]})


@menu_bp.post('/guisados')
@roles_required('admin', 'superadmin')
def create_guisado():
    """Agrega un guisado nuevo al catalogo. Solo administrador."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        raise ApiError('Missing field: name', 422, 'validation_error')
    if Guisado.query.filter(db.func.lower(Guisado.name) == name.lower()).first():
        raise ApiError('Ya existe un guisado con ese nombre', 409, 'name_taken')
    guisado = Guisado(name=name)
    db.session.add(guisado)
    db.session.flush()
    log_action('guisado.create', 'guisado', guisado.id, f'Agrego el guisado "{guisado.name}".')
    db.session.commit()
    return jsonify(guisado.to_dict()), 201


@menu_bp.put('/guisados/<int:guisado_id>')
@roles_required('admin', 'superadmin')
def update_guisado(guisado_id):
    """Edita el nombre y/o reactiva un guisado existente. Antes no habia
    forma de corregir un typo ni de reactivar uno dado de baja sin perder
    la baja logica sobre pedidos historicos que ya lo usaban."""
    guisado = Guisado.query.get_or_404(guisado_id)
    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            raise ApiError('Missing field: name', 422, 'validation_error')
        dup = Guisado.query.filter(db.func.lower(Guisado.name) == name.lower(), Guisado.id != guisado.id).first()
        if dup:
            raise ApiError('Ya existe un guisado con ese nombre', 409, 'name_taken')
        guisado.name = name
    if 'is_active' in data:
        guisado.is_active = bool(data['is_active'])
    log_action('guisado.update', 'guisado', guisado.id, f'Edito el guisado "{guisado.name}".')
    db.session.commit()
    return jsonify(guisado.to_dict())


@menu_bp.delete('/guisados/<int:guisado_id>')
@roles_required('admin', 'superadmin')
def delete_guisado(guisado_id):
    """Da de baja un guisado (is_active=False). Solo administrador."""
    guisado = Guisado.query.get_or_404(guisado_id)
    guisado.is_active = False
    log_action('guisado.delete', 'guisado', guisado.id, f'Dio de baja el guisado "{guisado.name}".')
    db.session.commit()
    return jsonify({'deleted': True})
