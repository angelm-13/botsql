"""
Módulo de Restaurante integrado en la plataforma Tyakxa.

Componentes:
- Models: Entidades de negocio (mesas, ordenes, inventario, etc.)
- Routes: Blueprints de API (/api/restaurante/*)
- Services: Lógica de facturación, PDF, etc.
- Utils: Utilidades compartidas (auditoria, seguridad, etc.)
"""

from app.restaurante.routes import (
    admin_users,
    auth,
    cashier,
    demo,
    inventory,
    invoices,
    kitchen,
    menu,
    orders,
    reservations,
    tables,
    visits,
)

URL_PREFIX = '/restaurante'

# (blueprint, nombre de registro, sufijo de ruta).
#
# El nombre lleva prefijo 'restaurante_' porque Flask exige nombres unicos
# por app y el core ya registra un blueprint llamado 'auth'
# (app/routes/auth.py) -- sin el prefijo, el arranque aborta con ValueError.
#
# El sufijo replica el url_prefix que cada blueprint tenia en la app original
# del restaurante. Sin el, los 12 blueprints colapsan sobre la misma ruta
# base y las rutas se pisan entre si.
blueprints_restaurante = [
    (admin_users.admin_users_bp, 'restaurante_admin_users', '/admin'),
    (auth.auth_bp, 'restaurante_auth', '/auth'),
    (cashier.cashier_bp, 'restaurante_cashier', '/cashier'),
    (demo.demo_bp, 'restaurante_demo', '/demo'),
    (inventory.inventory_bp, 'restaurante_inventory', '/inventory'),
    (invoices.invoices_bp, 'restaurante_invoices', '/invoices'),
    (kitchen.kitchen_bp, 'restaurante_kitchen', '/kitchen'),
    (menu.menu_bp, 'restaurante_menu', '/menu'),
    (orders.orders_bp, 'restaurante_orders', '/orders'),
    (reservations.reservations_bp, 'restaurante_reservations', '/reservations'),
    (tables.tables_bp, 'restaurante_tables', '/tables'),
    (visits.visits_bp, 'restaurante_visits', '/visits'),
]

__all__ = ['blueprints_restaurante', 'URL_PREFIX']
