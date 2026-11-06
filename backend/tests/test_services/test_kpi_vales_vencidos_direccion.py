"""`vales_vencidos_por_responsable` solo cuenta renglones de SALIDA.

Una ENTRADA (material que vuelve al almacen) con fecha de regreso pasada no es un prestamo que haya que
reclamar. `prestamos_vencidos_por_responsable` ya exigia la salida; este KPI no. Requiere PostgreSQL.
"""

from __future__ import annotations

import unittest
from datetime import timedelta

from sqlalchemy import delete

from app.kpis.registry import vales_vencidos_por_responsable_query
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType, Material, NmIncidentProduct, Product,
    ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_negocio

ADMIN_ID = 1
EMPLEADO = 986
TIPO = 986
LOCATION_TYPE = BRAND = PRODUCT_FAMILY = UNIT = MATERIAL = INVOICE = PRODUCT = LOCATION = 986
VALE_SALIDA, VALE_ENTRADA = 9861, 9862
AHORA = ahora_negocio().replace(hour=10, minute=0, second=0, microsecond=0)
VENCIO = AHORA - timedelta(days=2)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class ValesVencidosDireccionTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add(User(
                id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado vencidos",
                id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                user_type="employee", is_employee=True, username="kpi-vales-vencidos-direccion-test",
            ))
            db.add(IncidentType(id_incident_type=TIPO, incident_type_description="Vale prestamo", created_by=ADMIN_ID))
            db.add(LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI vencidos", is_warehouse=True, created_by=ADMIN_ID))
            db.add(Brand(id_brand=BRAND, brand_description="KPI vencidos", created_by=ADMIN_ID))
            db.add(ProductFamily(id_product_family=PRODUCT_FAMILY, product_family_description="KPI vencidos", created_by=ADMIN_ID))
            db.add(Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID))
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI vencidos", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI vencidos", id_unit=UNIT, id_brand=BRAND,
                            id_product_family=PRODUCT_FAMILY, created_by=ADMIN_ID))
            db.add(Invoice(
                id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1, id_proyect=1, id_status=1,
                tax_certification_supplier=1, apply_tax=False, invoice_status="pendiente", created_by=ADMIN_ID,
            ))
            db.flush()
            db.add(Product(id_product=PRODUCT, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                           is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID))
            db.flush()
            for id_vale in (VALE_SALIDA, VALE_ENTRADA):
                db.add(Incident(id_incident=id_vale, id_incident_type=TIPO, id_user=EMPLEADO, incident_status="abierto",
                                incident_date=VENCIO, creation_date=VENCIO, created_by=EMPLEADO))
            db.flush()
            for id_renglon, id_vale, direccion in ((98610, VALE_SALIDA, "salida"), (98620, VALE_ENTRADA, "entrada")):
                db.add(NmIncidentProduct(id_nm_incident_product=id_renglon, id_incident=id_vale, id_product=PRODUCT,
                                         quantity=1, direction=direccion, due_date=VENCIO, created_by=ADMIN_ID))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product == PRODUCT))
            db.execute(delete(Incident).where(Incident.id_incident_type == TIPO))
            db.execute(delete(Product).where(Product.id_product == PRODUCT))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type == TIPO))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _filas(self):
        dia = VENCIO.date()
        with transaction_context() as db:
            return [tuple(f) for f in vales_vencidos_por_responsable_query(db, dia, dia, {}, None) if f[0] == EMPLEADO]

    def test_la_entrada_vencida_no_cuenta_y_la_salida_si(self):
        self.assertEqual([(EMPLEADO, VENCIO.date(), 1)], self._filas())
