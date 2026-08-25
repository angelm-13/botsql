"""
Rutas de mesas.

Solo expone una consulta: el estado actual de las 15 mesas del salon
(libre u ocupada, y si esta ocupada, cuantos comensales tiene). No hay
endpoint para crear/eliminar mesas: el catalogo de mesas se siembra una
sola vez con seed.py: agregar mesas fisicas nuevas es un cambio de
catalogo, no una operacion de uso diario.
"""
from flask import Blueprint, jsonify
from app.restaurante.models import Table, Visit
from app.restaurante.utils.security import roles_required

tables_bp = Blueprint('tables', __name__)


@tables_bp.get('')
@roles_required('cajero', 'admin', 'mesero', 'cocina')
def list_tables():
    """Devuelve todas las mesas con su estado en tiempo real (libre/ocupada).

    Para cada mesa se busca si tiene una Visit con status='active'; si la
    tiene, se anota cuantos comensales trae esa visita. El mesero usa esto
    para pintar el tablero de mesas (verde=libre, naranja=ocupada).
    """
    tables = Table.query.order_by(Table.number).all()
    active_visits = Visit.query.filter_by(status='active').all()
    occupied = {v.table_number: v for v in active_visits}
    result = []
    for t in tables:
        data = t.to_dict()
        visit = occupied.get(t.number)
        data['occupied'] = visit is not None
        data['visit_id'] = visit.id if visit else None
        data['diners_count'] = visit.diners_count if visit else 0
        result.append(data)
    return jsonify({'items': result})
