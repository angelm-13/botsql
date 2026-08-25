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

# Blueprints del restaurante con prefijo
blueprints_restaurante = [
    (admin_users.admin_users_bp, '/restaurante'),
    (auth.auth_bp, '/restaurante'),
    (cashier.cashier_bp, '/restaurante'),
    (demo.demo_bp, '/restaurante'),
    (inventory.inventory_bp, '/restaurante'),
    (invoices.invoices_bp, '/restaurante'),
    (kitchen.kitchen_bp, '/restaurante'),
    (menu.menu_bp, '/restaurante'),
    (orders.orders_bp, '/restaurante'),
    (reservations.reservations_bp, '/restaurante'),
    (tables.tables_bp, '/restaurante'),
    (visits.visits_bp, '/restaurante'),
]

__all__ = ['blueprints_restaurante']
