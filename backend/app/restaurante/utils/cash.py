"""
Utilidades de caja compartidas entre las rutas de ordenes (orders.py) y
visitas/mesas (visits.py).

Regla de negocio: no se debe poder registrar ningun cobro (ni por orden
individual ni por mesa completa) si no hay una caja (CashSession) abierta
en ese momento. Esto evita que se cobre "fuera de turno" y que el corte de
caja no coincida con las ventas reales.
"""
import os
from datetime import datetime
from app.restaurante.models import CashSession
from app.restaurante.utils.errors import ApiError

# Aviso (no bloqueante) de que la caja lleva abierta mas de lo normal --
# un turno real rara vez pasa de este numero de horas, asi que casi
# siempre significa que alguien olvido cerrarla al terminar el dia, no que
# el turno de verdad sigue activo. Configurable por si algun restaurante
# opera turnos mas largos.
REGISTER_OPEN_ALERT_HOURS = float(os.getenv('REGISTER_OPEN_ALERT_HOURS', '16'))


def register_open_hours(session):
    """Cuantas horas lleva abierta esta CashSession, a partir de opened_at."""
    return (datetime.utcnow() - session.opened_at).total_seconds() / 3600


def register_open_too_long(session):
    return session is not None and register_open_hours(session) >= REGISTER_OPEN_ALERT_HOURS


def require_open_register():
    """
    Verifica que exista una caja abierta ahora mismo.

    Devuelve la CashSession abierta (la mas reciente, por si hubiera mas de
    una por error) si existe. Si no hay ninguna caja abierta, lanza un
    ApiError 409 'register_closed' que la ruta que llama deja propagar,
    para que el cajero/administrador vea un mensaje claro en pantalla en
    vez de que el cobro falle o quede en un estado inconsistente.
    """
    session = CashSession.query.filter_by(status='open').order_by(CashSession.opened_at.desc()).first()
    if not session:
        raise ApiError(
            'No se puede cobrar: la caja esta cerrada. Abre la caja antes de registrar un pago.',
            409, 'register_closed',
        )
    return session
