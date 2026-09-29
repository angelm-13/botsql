from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from app.kpis.registry import material_prestado_actual_query
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context
from app.services.warehouse_voucher_service import CIERRE_SENTINELA

# Mismo criterio que los demas archivos de KPI sobre Incident/NmIncidentProduct:
# solo PostgreSQL real, IDs propios (990+) para no chocar con otros fixtures.
ADMIN_ID = 1
EMPLEADO_A = 990
EMPLEADO_B = 991
INCIDENT_TYPE_NORMAL = 990
INCIDENT_TYPE_DESTRUCCION = 991
INCIDENT_TYPE_EXTRAVIADO = 992
INCIDENT_TYPE_DANADO = 993
LOCATION_TYPE = 990
LOCATION = 990
BRAND = 990
PRODUCT_FAMILY = 990
UNIT = 990
MATERIAL = 990
INVOICE = 990
PRODUCT_A = 990
PRODUCT_B = 991

HOY = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class MaterialPrestadoActualQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add_all([
                User(id_user=EMPLEADO_A, created_by=ADMIN_ID, full_name="Empleado 990",
                     id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                     user_type="employee", is_employee=True, username="kpi-material-prestado-test-a"),
                User(id_user=EMPLEADO_B, created_by=ADMIN_ID, full_name="Empleado 991",
                     id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                     user_type="employee", is_employee=True, username="kpi-material-prestado-test-b"),
            ])
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_NORMAL, incident_type_description="Vale normal", created_by=ADMIN_ID))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_DESTRUCCION, incident_type_description="Destruccion", created_by=ADMIN_ID))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_EXTRAVIADO, incident_type_description="Extraviado", created_by=ADMIN_ID))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_DANADO, incident_type_description="Dañado", created_by=ADMIN_ID))
            db.add(LocationType(id_location_type=LOCATION_TYPE, location_type_description="KPI test", is_warehouse=True, created_by=ADMIN_ID))
            db.add(Brand(id_brand=BRAND, brand_description="KPI test", created_by=ADMIN_ID))
            db.add(ProductFamily(id_product_family=PRODUCT_FAMILY, product_family_description="KPI test", created_by=ADMIN_ID))
            db.add(Unit(id_unit=UNIT, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID))
            db.flush()
            db.add(Location(id_location=LOCATION, id_location_type=LOCATION_TYPE, location_description="KPI test", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL, material_description="KPI test", id_unit=UNIT, id_brand=BRAND, id_product_family=PRODUCT_FAMILY, created_by=ADMIN_ID))
            db.add(Invoice(
                id_invoice=INVOICE, id_customer_supplier=1, id_issuer_customer_supplier=1,
                id_proyect=1, id_status=1, tax_certification_supplier=1, apply_tax=False,
                invoice_status="pendiente", created_by=ADMIN_ID,
            ))
            db.flush()
            db.add_all([
                Product(id_product=PRODUCT_A, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                        is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
                        descripcion="Taladro Bosch", product_code="TAL-001"),
                Product(id_product=PRODUCT_B, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                        is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
                        descripcion="Esmeriladora", product_code="ESM-001"),
            ])

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product.in_([PRODUCT_A, PRODUCT_B])))
            db.execute(delete(Incident).where(Incident.id_incident_type.in_([INCIDENT_TYPE_NORMAL, INCIDENT_TYPE_DESTRUCCION, INCIDENT_TYPE_EXTRAVIADO, INCIDENT_TYPE_DANADO])))
            db.execute(delete(Product).where(Product.id_product.in_([PRODUCT_A, PRODUCT_B])))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_([INCIDENT_TYPE_NORMAL, INCIDENT_TYPE_DESTRUCCION, INCIDENT_TYPE_EXTRAVIADO, INCIDENT_TYPE_DANADO])))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _incidente(self, id_incident, id_user, incident_date, id_incident_type=INCIDENT_TYPE_NORMAL):
        return Incident(
            id_incident=id_incident, id_incident_type=id_incident_type, id_user=id_user,
            incident_status="abierta", incident_date=incident_date, created_by=id_user,
        )

    def _renglon(self, id_nm_incident_product, id_incident, id_product, direction, close_date=None):
        return NmIncidentProduct(
            id_nm_incident_product=id_nm_incident_product, id_incident=id_incident, id_product=id_product,
            quantity=1, direction=direction, close_date=close_date, created_by=ADMIN_ID,
        )

    def test_solo_salida_sin_cerrar_cuenta_como_prestado(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9900, EMPLEADO_A, HOY - timedelta(days=5)),
                self._incidente(9901, EMPLEADO_A, HOY - timedelta(days=3)),
            ])
            db.flush()
            db.add_all([
                self._renglon(99000, 9900, PRODUCT_A, "salida"),        # prestado
                self._renglon(99001, 9901, PRODUCT_B, "entrada"),       # entrada, no cuenta
            ])

        with transaction_context() as db:
            items, total = material_prestado_actual_query(db, limit=25, offset=0)

        self.assertEqual(1, total)
        self.assertEqual(1, len(items))
        self.assertEqual("Taladro Bosch", items[0]["articulo"])
        self.assertEqual(EMPLEADO_A, items[0]["id_user"])
        self.assertEqual("Empleado 990", items[0]["responsable"])
        self.assertEqual((HOY - timedelta(days=5)).date().isoformat(), items[0]["fecha_prestamo"])
        self.assertEqual(5, items[0]["dias_prestado"])

    def test_cerrado_con_fecha_real_no_cuenta(self):
        with transaction_context() as db:
            db.add(self._incidente(9902, EMPLEADO_A, HOY - timedelta(days=10)))
            db.flush()
            db.add(self._renglon(99002, 9902, PRODUCT_A, "salida", close_date=HOY - timedelta(days=2)))

        with transaction_context() as db:
            items, total = material_prestado_actual_query(db, limit=25, offset=0)

        self.assertEqual(0, total)
        self.assertEqual([], items)

    def test_sentinel_legacy_sigue_contando_como_prestado(self):
        with transaction_context() as db:
            db.add(self._incidente(9903, EMPLEADO_A, HOY - timedelta(days=20)))
            db.flush()
            db.add(self._renglon(99003, 9903, PRODUCT_A, "salida", close_date=CIERRE_SENTINELA))

        with transaction_context() as db:
            items, total = material_prestado_actual_query(db, limit=25, offset=0)

        self.assertEqual(1, total)
        self.assertEqual(20, items[0]["dias_prestado"])

    def test_una_baja_no_cuenta_aunque_la_direccion_sea_salida(self):
        # Un vale de Destruccion o de Extraviado registra que la herramienta ya
        # no esta con nadie: nunca es un prestamo pendiente, sin importar que su
        # direction sea 'salida' y siga sin cerrar.
        for id_incident, id_renglon, tipo in (
            (9904, 99004, INCIDENT_TYPE_DESTRUCCION),
            (9907, 99007, INCIDENT_TYPE_EXTRAVIADO),
        ):
            with self.subTest(tipo=tipo):
                with transaction_context() as db:
                    db.add(self._incidente(id_incident, EMPLEADO_A, HOY - timedelta(days=1), id_incident_type=tipo))
                    db.flush()
                    db.add(self._renglon(id_renglon, id_incident, PRODUCT_A, "salida"))

                with transaction_context() as db:
                    items, total = material_prestado_actual_query(db, limit=25, offset=0)

                self.assertEqual(0, total)

    def test_lo_danado_sigue_contando_como_prestado(self):
        # Decision del 2026-09-29: no se sabe si quien lo daño todavia lo tiene o
        # ya lo entrego roto, y es mejor verlo de mas que esconderlo.
        with transaction_context() as db:
            db.add(self._incidente(9908, EMPLEADO_A, HOY - timedelta(days=4), id_incident_type=INCIDENT_TYPE_DANADO))
            db.flush()
            db.add(self._renglon(99008, 9908, PRODUCT_A, "salida"))

        with transaction_context() as db:
            items, total = material_prestado_actual_query(db, limit=25, offset=0)

        self.assertEqual(1, total)
        self.assertEqual(4, items[0]["dias_prestado"])

    def test_orden_por_mas_dias_prestado_primero(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9905, EMPLEADO_A, HOY - timedelta(days=2)),
                self._incidente(9906, EMPLEADO_B, HOY - timedelta(days=30)),
            ])
            db.flush()
            db.add_all([
                self._renglon(99005, 9905, PRODUCT_A, "salida"),
                self._renglon(99006, 9906, PRODUCT_B, "salida"),
            ])

        with transaction_context() as db:
            items, total = material_prestado_actual_query(db, limit=25, offset=0)

        self.assertEqual(2, total)
        self.assertEqual([30, 2], [item["dias_prestado"] for item in items])

    def test_limit_y_offset_paginan_sin_perder_el_total(self):
        with transaction_context() as db:
            incidentes = [self._incidente(9910 + i, EMPLEADO_A, HOY - timedelta(days=i + 1)) for i in range(5)]
            db.add_all(incidentes)
            db.flush()
            db.add_all([
                self._renglon(99010 + i, 9910 + i, PRODUCT_A, "salida") for i in range(5)
            ])

        with transaction_context() as db:
            pagina_1, total_1 = material_prestado_actual_query(db, limit=2, offset=0)
            pagina_2, total_2 = material_prestado_actual_query(db, limit=2, offset=2)

        self.assertEqual(5, total_1)
        self.assertEqual(5, total_2)
        self.assertEqual(2, len(pagina_1))
        self.assertEqual(2, len(pagina_2))
        ids_pagina_1 = {item["id_nm_incident_product"] for item in pagina_1}
        ids_pagina_2 = {item["id_nm_incident_product"] for item in pagina_2}
        self.assertEqual(set(), ids_pagina_1 & ids_pagina_2)


if __name__ == "__main__":
    unittest.main()
