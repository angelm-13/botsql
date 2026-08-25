"""
Limites de la version freemium/de prueba: numero de personal, facturas por
mes y duracion total del periodo de prueba. Todo configurable por variables
de entorno para poder ajustar los limites sin tocar codigo.

Ojo: esto NO tiene relacion con DEMO_MODE de app/config.py -- esa bandera
controla como se SIEMBRA una replica (solo superadmin vs. todo el personal
de ejemplo, ver backend/seed.py), no los limites del producto. Este modulo
es el sistema real de limites de la version freemium (free-restaurant):
expira, limita personal y facturas timbradas, y bloquea el PAC real. Se
deja separado de DEMO_MODE a proposito, con variables DEMO_* propias, para
no mezclar los dos significados de "demo" -- las dos banderas son
independientes y se pueden combinar segun el despliegue.

Esta version existe para que un restaurante interesado pruebe el flujo real
de la plantilla y decida contratar la version completa (sin estos limites)
-- por eso los limites se reportan de forma clara (ver demo_status()) en
vez de fallar en silencio.
"""
import os
from datetime import datetime

# Apagado por default a proposito: este mismo codigo se publica en DOS
# repositorios (ver PRODUCTION_CHECKLIST.md) -- demo_restaurante (la demo
# completa a produccion, sin limites) y free-restaurant (la version
# freemium/de prueba). Una sola base de codigo, un solo interruptor: en
# vez de mantener dos codebases que puedan divergir, free-restaurant
# simplemente define FREEMIUM_LIMITS_ENABLED=1 en su .env; demo_restaurante
# no la define y se comporta como la version completa sin cambiar una
# linea de codigo.
FREEMIUM_LIMITS_ENABLED = os.getenv('FREEMIUM_LIMITS_ENABLED', '0') == '1'

MAX_STAFF = int(os.getenv('DEMO_MAX_STAFF', '5'))
MAX_INVOICES_PER_MONTH = int(os.getenv('DEMO_MAX_INVOICES_PER_MONTH', '5'))
DEMO_MONTHS = int(os.getenv('DEMO_MONTHS', '4'))

_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _add_months(dt, months):
    """Suma `months` meses a `dt` sin depender de python-dateutil, ajustando
    el dia si el mes destino es mas corto (ej. 31 de enero + 1 mes -> 28/29
    de febrero, no un error)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    max_day = 29 if (month == 2 and _is_leap(year)) else _DAYS_IN_MONTH[month - 1]
    return dt.replace(year=year, month=month, day=min(dt.day, max_day))


def demo_expires_at():
    from app.models import DemoConfig
    return _add_months(DemoConfig.get_singleton().started_at, DEMO_MONTHS)


def demo_is_expired():
    if not FREEMIUM_LIMITS_ENABLED:
        return False
    return datetime.utcnow() >= demo_expires_at()


def staff_limit_reached():
    return FREEMIUM_LIMITS_ENABLED and staff_count() >= MAX_STAFF


def invoice_limit_reached():
    return FREEMIUM_LIMITS_ENABLED and invoices_stamped_this_month() >= MAX_INVOICES_PER_MONTH


def pac_provider_locked(requested_provider):
    """El PAC real (Facturama) queda bloqueado en la version freemium -- solo
    se puede timbrar con el proveedor simulado ('mock'), para que probar el
    flujo de facturacion no requiera credenciales reales de un PAC."""
    return FREEMIUM_LIMITS_ENABLED and (requested_provider or 'mock') != 'mock'


def invoices_stamped_this_month():
    from app.models import Invoice
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return Invoice.query.filter(Invoice.status == 'stamped', Invoice.stamped_at >= month_start).count()


def staff_count():
    from app.models import User
    return User.query.filter(User.role != 'superadmin').count()


def demo_status():
    """Resumen publico del estado de la version de prueba (ver
    routes/demo.py) -- lo consume tanto la pantalla de login/banner (sin
    sesion) como cada pantalla que necesita saber si ya se llego a un tope
    antes de intentar la accion (alta de personal, timbrar una factura).

    'enabled': False en cuanto FREEMIUM_LIMITS_ENABLED este apagado (el caso
    de demo_restaurante, la version completa) -- el frontend no debe mostrar
    ningun banner ni bloqueo si esto viene en False, sin importar los demas
    campos."""
    if not FREEMIUM_LIMITS_ENABLED:
        return {'enabled': False}
    from app.models import DemoConfig
    started_at = DemoConfig.get_singleton().started_at
    expires_at = _add_months(started_at, DEMO_MONTHS)
    now = datetime.utcnow()
    remaining = expires_at - now

    return {
        'enabled': True,
        'expired': remaining.total_seconds() <= 0,
        'expires_at': expires_at.isoformat() + 'Z',
        'days_remaining': max(0, remaining.days),
        'max_staff': MAX_STAFF,
        'staff_count': staff_count(),
        'max_invoices_per_month': MAX_INVOICES_PER_MONTH,
        'invoices_used_this_month': invoices_stamped_this_month(),
    }
