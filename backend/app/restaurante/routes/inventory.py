"""
Rutas de inventario: catalogo de insumos (InventoryItem) y su bitacora de
movimientos (InventoryMovement) -- entradas (compras), salidas (consumo
manual), mermas (perdidas: caducidad, rotura, derrame...) y ajustes
(correccion tras un conteo fisico).

Cada movimiento queda registrado con quien lo hizo, cuando, el motivo, el
costo unitario vigente en ese momento, y una foto de la cantidad resultante
-- nunca se sobreescribe silenciosamente InventoryItem.quantity sin dejar
rastro de por que cambio.

Los movimientos que RESTAN stock (salida/merma, y un ajuste a la baja)
nunca dejan la cantidad en negativo: se rechazan con un error claro en vez
de guardar un inventario que no tiene sentido fisico.
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from app.extensions import db
from app.restaurante.models import InventoryItem, InventoryMovement, User, INVENTORY_MOVEMENT_TYPES
from app.restaurante.utils.pagination import paginate
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action

inventory_bp = Blueprint('inventory', __name__)

INVENTORY_ROLES = ('cajero', 'admin', 'superadmin')


def _validate_amount(value, field_name):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ApiError(f'{field_name} debe ser un numero', 422, 'validation_error') from None
    if amount < 0:
        raise ApiError(f'{field_name} no puede ser negativo', 422, 'validation_error')
    return amount


@inventory_bp.get('/items')
@roles_required(*INVENTORY_ROLES)
def list_items():
    """Lista los insumos de inventario en orden alfabetico. Por default solo
    los activos; ?include_inactive=1 tambien trae los dados de baja (para
    poder reactivarlos). ?search filtra por descripcion."""
    q = InventoryItem.query if request.args.get('include_inactive') else InventoryItem.query.filter_by(is_active=True)
    search = request.args.get('search')
    if search:
        q = q.filter(InventoryItem.description.ilike(f'%{search}%'))
    return jsonify(paginate(q.order_by(InventoryItem.description), request))


@inventory_bp.post('/items')
@roles_required(*INVENTORY_ROLES)
def create_item():
    """Crea un insumo de inventario nuevo. La cantidad inicial (quantity)
    es opcional -- si el insumo ya tiene existencias al momento de
    registrarlo, lo mas trazable es crearlo en 0 y despues capturar esa
    cantidad como una 'entrada' con motivo (ver POST /movements), pero se
    deja la opcion de capturar quantity aqui directo para no obligar ese
    paso extra en insumos nuevos que arrancan en cero de verdad."""
    data = request.get_json() or {}
    description = (data.get('description') or '').strip()
    unit = (data.get('unit') or '').strip()
    if not description or not unit:
        raise ApiError('description y unit son requeridos', 422, 'validation_error')
    if InventoryItem.query.filter(func.lower(InventoryItem.description) == description.lower()).first():
        raise ApiError('Ya existe un insumo con esa descripcion', 409, 'name_taken')
    quantity = _validate_amount(data.get('quantity', 0), 'quantity')
    cost_per_unit = _validate_amount(data.get('cost_per_unit', 0), 'cost_per_unit')
    min_stock = _validate_amount(data.get('min_stock', 0), 'min_stock')
    item = InventoryItem(description=description, unit=unit, quantity=quantity, cost_per_unit=cost_per_unit, min_stock=min_stock)
    db.session.add(item)
    db.session.flush()
    log_action('inventory_item.create', 'inventory_item', item.id, f'Creo el insumo "{item.description}".')
    db.session.commit()
    return jsonify(item.to_dict()), 201


@inventory_bp.put('/items/<int:item_id>')
@roles_required(*INVENTORY_ROLES)
def update_item(item_id):
    """Edita descripcion/unidad/costo/umbral de stock bajo/estatus de un
    insumo. NO edita quantity directamente -- eso solo cambia via
    movimientos (POST /movements), para que la bitacora siempre explique
    por que cambio el stock."""
    item = InventoryItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    if 'description' in data:
        description = (data.get('description') or '').strip()
        if not description:
            raise ApiError('description es requerido', 422, 'validation_error')
        dup = InventoryItem.query.filter(func.lower(InventoryItem.description) == description.lower(), InventoryItem.id != item.id).first()
        if dup:
            raise ApiError('Ya existe un insumo con esa descripcion', 409, 'name_taken')
        item.description = description
    if 'unit' in data:
        unit = (data.get('unit') or '').strip()
        if not unit:
            raise ApiError('unit es requerido', 422, 'validation_error')
        item.unit = unit
    if 'cost_per_unit' in data:
        item.cost_per_unit = _validate_amount(data['cost_per_unit'], 'cost_per_unit')
    if 'min_stock' in data:
        item.min_stock = _validate_amount(data['min_stock'], 'min_stock')
    if 'is_active' in data:
        item.is_active = bool(data['is_active'])
    log_action('inventory_item.update', 'inventory_item', item.id, f'Edito el insumo "{item.description}".')
    db.session.commit()
    return jsonify(item.to_dict())


@inventory_bp.delete('/items/<int:item_id>')
@roles_required(*INVENTORY_ROLES)
def delete_item(item_id):
    """Da de baja un insumo (is_active=False). No borra el registro ni su
    historial de movimientos."""
    item = InventoryItem.query.get_or_404(item_id)
    item.is_active = False
    log_action('inventory_item.delete', 'inventory_item', item.id, f'Dio de baja el insumo "{item.description}".')
    db.session.commit()
    return jsonify({'deleted': True})


@inventory_bp.get('/movements')
@roles_required(*INVENTORY_ROLES)
def list_movements():
    """Historial de movimientos (mas reciente primero), filtrable por
    insumo/tipo/rango de fechas -- para reportes de compras, consumo o
    mermas de un periodo."""
    q = InventoryMovement.query
    item_id = request.args.get('inventory_item_id')
    if item_id:
        q = q.filter(InventoryMovement.inventory_item_id == int(item_id))
    movement_type = request.args.get('type')
    if movement_type:
        if movement_type not in INVENTORY_MOVEMENT_TYPES:
            raise ApiError('Tipo de movimiento invalido', 422, 'validation_error')
        q = q.filter(InventoryMovement.type == movement_type)
    start = request.args.get('start')
    end = request.args.get('end')
    if start:
        q = q.filter(InventoryMovement.created_at >= datetime.strptime(start, '%Y-%m-%d'))
    if end:
        q = q.filter(InventoryMovement.created_at < datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1))
    result = paginate(q.order_by(InventoryMovement.created_at.desc()), request)
    user_cache = {}
    for row in result['items']:
        uid = row.get('created_by_id')
        if uid not in user_cache:
            u = User.query.get(uid) if uid else None
            user_cache[uid] = u.username if u else None
        row['created_by_username'] = user_cache[uid]
    return jsonify(result)


@inventory_bp.post('/movements')
@roles_required(*INVENTORY_ROLES)
def create_movement():
    """Registra un movimiento de inventario y actualiza InventoryItem.quantity
    en la MISMA transaccion.

    Payload:
      - inventory_item_id (requerido)
      - type: 'entrada' | 'salida' | 'merma' | 'ajuste' (requerido)
      - quantity: cantidad POSITIVA capturada por el usuario. Requerida
        para entrada/salida/merma (el signo lo decide el tipo, no el
        usuario). Ignorada para 'ajuste'.
      - new_quantity: SOLO para 'ajuste' -- la cantidad real que se conto
        fisicamente; el delta se calcula solo (new_quantity - la actual).
      - reason: motivo (opcional en entrada/salida, recomendado; se
        vuelve especialmente util en merma/ajuste para saber por que).
      - unit_cost: opcional. En 'entrada', si se manda, tambien actualiza
        InventoryItem.cost_per_unit (ultimo precio de compra) -- asi el
        valor de inventario reportado usa el costo mas reciente. En
        salida/merma/ajuste, si no se manda, se usa el costo actual del
        insumo para poder valuar la perdida/consumo.
    """
    data = request.get_json() or {}
    movement_type = data.get('type')
    if movement_type not in INVENTORY_MOVEMENT_TYPES:
        raise ApiError('Tipo de movimiento invalido', 422, 'validation_error')
    item_id = data.get('inventory_item_id')
    if not item_id:
        raise ApiError('inventory_item_id es requerido', 422, 'validation_error')
    # FOR UPDATE: bloquea la fila del insumo hasta el commit, para que dos
    # movimientos casi simultaneos sobre el MISMO insumo (ej. cocina
    # reportando una merma mientras el cajero registra una entrada) queden
    # serializados -- sin esto, ambos podian leer la misma quantity antes
    # de que el otro comiteara, y el segundo en escribir pisaba el cambio
    # del primero (lost update).
    item = InventoryItem.query.filter_by(id=item_id).with_for_update().first()
    if not item:
        raise ApiError('Insumo no encontrado', 404, 'inventory_item_not_found')

    reason = (data.get('reason') or '').strip()[:255] or None
    current_qty = float(item.quantity)

    if movement_type == 'ajuste':
        if data.get('new_quantity') is None:
            raise ApiError('new_quantity es requerido para un ajuste', 422, 'validation_error')
        new_quantity = _validate_amount(data['new_quantity'], 'new_quantity')
        delta = round(new_quantity - current_qty, 3)
        if delta == 0:
            raise ApiError('La cantidad nueva es igual a la actual; no hay nada que ajustar', 422, 'no_change')
        unit_cost = _validate_amount(data.get('unit_cost', item.cost_per_unit), 'unit_cost')
    else:
        quantity = data.get('quantity')
        if quantity is None:
            raise ApiError('quantity es requerido', 422, 'validation_error')
        quantity = _validate_amount(quantity, 'quantity')
        if quantity <= 0:
            raise ApiError('quantity debe ser mayor a cero', 422, 'validation_error')
        if movement_type == 'entrada':
            delta = quantity
            unit_cost = _validate_amount(data.get('unit_cost', item.cost_per_unit), 'unit_cost')
            # "Ultimo costo de compra": si se declara un costo unitario en
            # la entrada, se usa para actualizar el costo vigente del
            # insumo (no se promedia contra el costo anterior -- mantenerlo
            # simple es mas predecible que un costo promedio ponderado para
            # un restaurante chico).
            if data.get('unit_cost') is not None:
                item.cost_per_unit = unit_cost
        else:  # salida | merma
            delta = -quantity
            unit_cost = _validate_amount(data.get('unit_cost', item.cost_per_unit), 'unit_cost')
        if movement_type in ('merma',) and not reason:
            raise ApiError('Indica el motivo de la merma', 400, 'reason_required')

    resulting_quantity = round(current_qty + delta, 3)
    if resulting_quantity < 0:
        raise ApiError(
            f'No hay suficiente stock: quedarian {resulting_quantity} {item.unit} (negativo). '
            f'Stock actual: {current_qty} {item.unit}.',
            409, 'insufficient_stock',
        )

    item.quantity = resulting_quantity
    movement = InventoryMovement(
        inventory_item_id=item.id, type=movement_type, quantity_delta=delta,
        unit_cost=unit_cost, reason=reason, resulting_quantity=resulting_quantity,
        created_by_id=int(get_jwt_identity()),
    )
    db.session.add(movement)
    db.session.flush()
    log_action(
        'inventory.movement', 'inventory_movement', movement.id,
        f'{movement_type.capitalize()} de {abs(delta)} {item.unit} en "{item.description}" '
        f'(quedan {resulting_quantity} {item.unit})' + (f'. Motivo: {reason}' if reason else '') + '.',
    )
    db.session.commit()
    result = movement.to_dict()
    result['item'] = item.to_dict()
    return jsonify(result), 201


@inventory_bp.get('/summary')
@roles_required(*INVENTORY_ROLES)
def summary():
    """KPIs de inventario para el panel de admin/cajero: valor total del
    inventario activo, insumos en stock bajo, y mermas/entradas del mes en
    curso (cantidad de movimientos y costo)."""
    active_items = InventoryItem.query.filter_by(is_active=True).all()
    total_value = round(sum(float(i.quantity) * float(i.cost_per_unit) for i in active_items), 2)
    low_stock_items = [i for i in active_items if i.min_stock and float(i.quantity) < float(i.min_stock)]

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    def _month_totals(movement_type):
        rows = InventoryMovement.query.filter(
            InventoryMovement.type == movement_type, InventoryMovement.created_at >= month_start,
        ).all()
        qty = round(sum(abs(float(r.quantity_delta)) for r in rows), 3)
        cost = round(sum(abs(float(r.quantity_delta)) * float(r.unit_cost) for r in rows), 2)
        return {'count': len(rows), 'quantity': qty, 'cost': cost}

    return jsonify({
        'total_value': total_value,
        'active_items_count': len(active_items),
        'low_stock_items': [i.to_dict() for i in low_stock_items],
        'mermas_this_month': _month_totals('merma'),
        'entradas_this_month': _month_totals('entrada'),
        'salidas_this_month': _month_totals('salida'),
    })
