"""
Rutas de reservaciones.

Modulo basico de reservaciones (nombre, fecha, hora, numero de
comensales). Existe en el backend pero, a la fecha, no esta conectado a
ninguna pantalla del frontend nuevo -- queda disponible por API para
quien quiera integrarlo o para llamarlo por fuera de la app.
"""
from datetime import date, datetime
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.restaurante.models import Reservation, Table
from app.restaurante.utils.pagination import paginate
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.get('')
@roles_required('cajero', 'mesero', 'admin', 'superadmin')
def list_reservations():
    """Lista las reservaciones, de la mas reciente a la mas antigua (por fecha y hora)."""
    return jsonify(paginate(Reservation.query.order_by(Reservation.date.desc(), Reservation.time.desc()), request))


@reservations_bp.post('')
@roles_required('cajero', 'mesero', 'admin', 'superadmin')
def create_reservation():
    """Crea una reservacion nueva. Requiere nombre, fecha, hora y numero de comensales."""
    data = request.get_json() or {}
    required = ['name', 'date', 'time', 'guests']
    if any(not data.get(f) for f in required):
        raise ApiError('Missing reservation data', 422, 'validation_error')
    try:
        reservation_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        reservation_time = datetime.strptime(data['time'], '%H:%M').time()
    except (ValueError, TypeError):
        raise ApiError('Fecha u hora invalida (usa YYYY-MM-DD y HH:MM)', 422, 'validation_error') from None
    if reservation_date < date.today():
        raise ApiError('No se puede reservar en una fecha pasada', 422, 'validation_error')
    guests = data.get('guests')
    try:
        guests = int(guests)
    except (TypeError, ValueError):
        raise ApiError('guests debe ser un numero', 422, 'validation_error') from None
    if guests < 1:
        raise ApiError('guests debe ser al menos 1', 422, 'validation_error')
    table_number = data.get('table_number')
    if table_number is not None:
        table = Table.query.filter_by(number=int(table_number)).first()
        if not table:
            raise ApiError('Table not found', 404, 'table_not_found')
        if table.capacity and guests > table.capacity:
            raise ApiError(f'La mesa {table.number} tiene capacidad para {table.capacity} comensales', 422, 'over_capacity')
        # Sin este chequeo se podian crear dos reservaciones para la MISMA
        # mesa, fecha y hora sin ningun aviso -- ambas quedaban "pending" y
        # ninguna de las dos sabia de la otra hasta que alguien ya estaba
        # ahi para la misma mesa a la misma hora.
        clash = Reservation.query.filter_by(
            table_number=table.number, date=reservation_date, time=reservation_time,
        ).filter(Reservation.status != 'cancelled').first()
        if clash:
            raise ApiError('Esa mesa ya tiene una reservacion a esa fecha y hora', 409, 'reservation_conflict')
    reservation = Reservation(
        table_number=table_number, name=data['name'], date=reservation_date,
        time=reservation_time, guests=guests, event_type=data.get('event_type'),
    )
    db.session.add(reservation)
    db.session.commit()
    return jsonify(reservation.to_dict()), 201
