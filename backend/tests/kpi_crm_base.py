"""Base comun de las pruebas de los KPIs de la pestana CRM (`test_kpi_crm*.py`): un admin y helpers de siembra.

`Siembra` va aparte de la clase de prueba para que un archivo de solo-PostgreSQL pueda declarar `class X(BackendTestCase)`
directamente: `backend/ci/run_postgres_tests.sh` clasifica el archivo por la clase base que lee en esa linea.
"""

from __future__ import annotations

from sqlalchemy import text

from app.models import CustomerSupplier, Department, Level, Permission, Proyect, Status, Subdepartment, User
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase


def sembrar_admin():
    """Lo minimo que piden las FK: estatus, departamento, nivel, permiso y un usuario admin (id 1)."""
    with transaction_context() as db:
        if engine.dialect.name != "sqlite":      # en Postgres las FK se difieren; SQLite no las aplica
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
        db.add(Department(id_department=1, department_description="General", created_by=1))
        db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
        db.add(Level(id_level=1, level_description="General", created_by=1))
        db.add(Permission(
            id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
            id_department=1, id_subdepartment=1, id_level=1,
        ))
        db.add(User(
            id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=1,
            id_status=1, supervisor=1, user_type="admin", username="crm-admin",
        ))
        # El proveedor y el proyecto internos de siempre (`user.id_proyect` apunta a uno): no son un cliente, asi que
        # ningun KPI de clientes los cuenta.
        db.add(CustomerSupplier(
            id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
            fiscal_type="601", type="supplier", id_user=1, created_by=1,
        ))
        db.add(Proyect(id_proyect=1, id_customer_supplier=1, leader=1, proyect_description="Interno", created_by=1))


class Siembra:
    """Clientes y proyectos de prueba con ids propios (desde 101), con nombres de coworking."""

    def __init__(self):
        self._siguiente = 100

    def cliente(self, nombre, tipo="client", creation_date=None, baja=None):
        self._siguiente += 1
        with transaction_context() as db:
            db.add(CustomerSupplier(
                id_customer_supplier=self._siguiente, name=nombre, tax_id=f"AAA0101{self._siguiente}", postal_code="37000",
                fiscal_type="601", type=tipo, id_user=1, created_by=1,
                creation_date=creation_date, deletion_date=baja,
            ))
        return self._siguiente

    def proyecto(self, id_cliente, estado="in_progress", comercial="autorizado", entrega=None, baja=None):
        self._siguiente += 1
        with transaction_context() as db:
            db.add(Proyect(
                id_proyect=self._siguiente, id_customer_supplier=id_cliente, leader=1, created_by=1,
                proyect_description=f"Oficina {self._siguiente}", proyect_status=estado, management_status=comercial,
                delivery_date=entrega, deletion_date=baja,
            ))
        return self._siguiente


class CrmBase(BackendTestCase):
    """Para pruebas que corren tambien en SQLite: cada prueba arranca de un esquema vacio, con el admin sembrado."""

    def setUp(self):
        super().setUp()
        sembrar_admin()
        self._siembra = Siembra()

    def _cliente(self, *args, **kwargs):
        return self._siembra.cliente(*args, **kwargs)

    def _proyecto(self, *args, **kwargs):
        return self._siembra.proyecto(*args, **kwargs)
