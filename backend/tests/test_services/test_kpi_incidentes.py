from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.kpis.registry import (
    cancelaciones_por_empleado_query,
    incidentes_resueltos_por_empleado_query,
    vales_vencidos_por_responsable_query,
)
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context
from app.services.warehouse_voucher_service import CIERRE_SENTINELA

# Mismo criterio que test_kpi_ventas_por_empleado.py: se corre solo contra
# PostgreSQL real y reutiliza el bootstrap de siempre (customer_supplier=1,
# proyect=1, status=1, user=1) que siembra init_db.py -- NmIncidentProduct
# exige un Product real (FK NOT NULL), y Product exige Invoice/Location/
# Material reales, asi que el fixture arma esa cadena minima con ids propios
# para no chocar con otros archivos de prueba.
ADMIN_ID = 1
EMPLEADO_A = 970
EMPLEADO_B = 971
INCIDENT_TYPE = 970
LOCATION_TYPE = 970
LOCATION = 970
BRAND = 970
PRODUCT_FAMILY = 970
UNIT = 970
MATERIAL = 970
INVOICE = 970
PRODUCT = 970

AHORA = datetime.now()
HOY = AHORA.date()


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class KpiIncidentesTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Empleado {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-incidente-test-{user_id}",
                ))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE, incident_type_description="KPI test", created_by=ADMIN_ID))
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
            db.add(Product(
                id_product=PRODUCT, id_invoice=INVOICE, id_location=LOCATION, id_material=MATERIAL,
                is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
            ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_product == PRODUCT))
            db.execute(delete(Incident).where(Incident.id_incident_type == INCIDENT_TYPE))
            db.execute(delete(Product).where(Product.id_product == PRODUCT))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type == INCIDENT_TYPE))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _incidente(self, id_incident, id_user, incident_status, creation_date, close_date=None):
        return Incident(
            id_incident=id_incident, id_incident_type=INCIDENT_TYPE, id_user=id_user,
            incident_status=incident_status, creation_date=creation_date, close_date=close_date,
            created_by=id_user,
        )

    def _vale(self, id_nm_incident_product, id_incident, due_date=None, close_date=None):
        return NmIncidentProduct(
            id_nm_incident_product=id_nm_incident_product, id_incident=id_incident, id_product=PRODUCT,
            quantity=1, due_date=due_date, close_date=close_date, created_by=ADMIN_ID,
        )

    # --- vales_vencidos_por_responsable_query ---------------------------

    def test_vales_vencidos_solo_cuenta_abiertos_y_vencidos(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9701, EMPLEADO_A, "abierta", datetime(2026, 6, 1)),
                self._incidente(9702, EMPLEADO_B, "abierta", datetime(2026, 6, 1)),
                self._incidente(9703, EMPLEADO_B, "abierta", datetime(2026, 6, 1)),
            ])
            db.flush()
            db.add_all([
                # A: vencido y sin cerrar -- cuenta.
                self._vale(97001, 9701, due_date=AHORA - timedelta(days=2)),
                # B: vencido pero YA cerrado -- no cuenta.
                self._vale(97002, 9702, due_date=AHORA - timedelta(days=2), close_date=AHORA - timedelta(days=1)),
                # B: due_date en el futuro -- todavia no vence, no cuenta.
                self._vale(97003, 9703, due_date=AHORA + timedelta(days=5)),
            ])

        with transaction_context() as db:
            filas = vales_vencidos_por_responsable_query(
                db, HOY - timedelta(days=10), HOY + timedelta(days=10), {}, None,
            )

        self.assertEqual([(EMPLEADO_A, (AHORA - timedelta(days=2)).date(), 1)], [tuple(f) for f in filas])

    def test_vales_vencidos_cuenta_el_sentinel_legacy_como_abierto(self):
        # Renglones migrados de Adser: close_date quedo en CIERRE_SENTINELA
        # (1990-01-01), no NULL, para un vale que en realidad sigue abierto.
        # Mismo criterio que warehouse_voucher_service._renglones_de_reporte
        # -- antes de este fix, close_date.is_(None) solo no lo contaba.
        with transaction_context() as db:
            db.add(self._incidente(9708, EMPLEADO_A, "abierta", datetime(2026, 6, 1)))
            db.flush()
            db.add(self._vale(97008, 9708, due_date=AHORA - timedelta(days=2), close_date=CIERRE_SENTINELA))

        with transaction_context() as db:
            filas = vales_vencidos_por_responsable_query(
                db, HOY - timedelta(days=10), HOY + timedelta(days=10), {}, None,
            )

        self.assertEqual([(EMPLEADO_A, (AHORA - timedelta(days=2)).date(), 1)], [tuple(f) for f in filas])

    def test_vales_vencidos_agrupa_por_dia_de_vencimiento(self):
        with transaction_context() as db:
            db.add(self._incidente(9704, EMPLEADO_A, "abierta", datetime(2026, 6, 1)))
            db.flush()
            db.add_all([
                self._vale(97004, 9704, due_date=datetime(2026, 6, 1, 9, 0)),
                self._vale(97005, 9704, due_date=datetime(2026, 6, 3, 9, 0)),
            ])

        with transaction_context() as db:
            filas = vales_vencidos_por_responsable_query(db, date(2026, 6, 1), date(2026, 6, 3), {}, None)

        self.assertEqual(
            [(EMPLEADO_A, date(2026, 6, 1), 1), (EMPLEADO_A, date(2026, 6, 3), 1)],
            [tuple(f) for f in filas],
        )

    def test_vales_vencidos_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9706, EMPLEADO_A, "abierta", datetime(2026, 6, 5)),
                self._incidente(9707, EMPLEADO_B, "abierta", datetime(2026, 6, 5)),
            ])
            db.flush()
            db.add_all([
                self._vale(97006, 9706, due_date=datetime(2026, 6, 5, 9, 0)),
                self._vale(97007, 9707, due_date=datetime(2026, 6, 5, 9, 0)),
            ])

        with transaction_context() as db:
            filas = vales_vencidos_por_responsable_query(
                db, date(2026, 6, 5), date(2026, 6, 5), {"empleados": [EMPLEADO_B]}, None,
            )

        self.assertEqual([(EMPLEADO_B, date(2026, 6, 5), 1)], [tuple(f) for f in filas])

    # --- incidentes_resueltos_por_empleado_query ------------------------

    def test_resuelta_y_cerrada_cuentan_cancelada_no(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9710, EMPLEADO_A, "resuelta", datetime(2026, 7, 1, 9, 0), close_date=datetime(2026, 7, 2)),
                self._incidente(9711, EMPLEADO_A, "cerrada", datetime(2026, 7, 1, 9, 0), close_date=datetime(2026, 7, 2)),
                self._incidente(9712, EMPLEADO_A, "cancelada", datetime(2026, 7, 1, 9, 0), close_date=datetime(2026, 7, 2)),
                self._incidente(9713, EMPLEADO_A, "abierta", datetime(2026, 7, 1, 9, 0)),
            ])

        with transaction_context() as db:
            filas = incidentes_resueltos_por_empleado_query(db, date(2026, 7, 1), date(2026, 7, 1), {}, None)

        # 2 de 4 (resuelta + cerrada) = 50.00%; cancelada NO cuenta como resuelta.
        self.assertEqual([(EMPLEADO_A, date(2026, 7, 1), Decimal("50.00"))], [tuple(f) for f in filas])

    def test_incidentes_resueltos_excluye_fuera_de_rango_de_creacion(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9714, EMPLEADO_A, "resuelta", datetime(2026, 7, 10, 9, 0)),
                # Creado fuera del rango: no cuenta ni en numerador ni denominador.
                self._incidente(9715, EMPLEADO_A, "abierta", datetime(2026, 6, 1, 9, 0)),
            ])

        with transaction_context() as db:
            filas = incidentes_resueltos_por_empleado_query(db, date(2026, 7, 10), date(2026, 7, 10), {}, None)

        self.assertEqual([(EMPLEADO_A, date(2026, 7, 10), Decimal("100.00"))], [tuple(f) for f in filas])

    def test_incidentes_resueltos_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9716, EMPLEADO_A, "resuelta", datetime(2026, 7, 15, 9, 0)),
                self._incidente(9717, EMPLEADO_B, "abierta", datetime(2026, 7, 15, 9, 0)),
            ])

        with transaction_context() as db:
            filas = incidentes_resueltos_por_empleado_query(
                db, date(2026, 7, 15), date(2026, 7, 15), {"empleados": [EMPLEADO_B]}, None,
            )

        self.assertEqual([(EMPLEADO_B, date(2026, 7, 15), Decimal("0.00"))], [tuple(f) for f in filas])

    # --- cancelaciones_por_empleado_query --------------------------------

    def test_cancelaciones_cuenta_por_dia_de_cierre_no_de_creacion(self):
        with transaction_context() as db:
            db.add(self._incidente(
                9720, EMPLEADO_A, "cancelada",
                creation_date=datetime(2026, 5, 1, 9, 0),  # creado MUCHO antes
                close_date=datetime(2026, 8, 1, 9, 0),     # cancelado dentro del rango
            ))

        with transaction_context() as db:
            dentro = cancelaciones_por_empleado_query(db, date(2026, 8, 1), date(2026, 8, 1), {}, None)
            fuera = cancelaciones_por_empleado_query(db, date(2026, 5, 1), date(2026, 5, 1), {}, None)

        self.assertEqual([(EMPLEADO_A, date(2026, 8, 1), 1)], [tuple(f) for f in dentro])
        self.assertEqual([], [tuple(f) for f in fuera], "debe agrupar por close_date, no por creation_date")

    def test_cancelaciones_solo_cuenta_estatus_cancelada(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9721, EMPLEADO_A, "cancelada", datetime(2026, 8, 5, 9, 0), close_date=datetime(2026, 8, 5, 10, 0)),
                self._incidente(9722, EMPLEADO_A, "resuelta", datetime(2026, 8, 5, 9, 0), close_date=datetime(2026, 8, 5, 10, 0)),
                self._incidente(9723, EMPLEADO_A, "cerrada", datetime(2026, 8, 5, 9, 0), close_date=datetime(2026, 8, 5, 10, 0)),
            ])

        with transaction_context() as db:
            filas = cancelaciones_por_empleado_query(db, date(2026, 8, 5), date(2026, 8, 5), {}, None)

        self.assertEqual([(EMPLEADO_A, date(2026, 8, 5), 1)], [tuple(f) for f in filas])

    def test_cancelaciones_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9724, EMPLEADO_A, "cancelada", datetime(2026, 8, 10, 9, 0), close_date=datetime(2026, 8, 10, 10, 0)),
                self._incidente(9725, EMPLEADO_B, "cancelada", datetime(2026, 8, 10, 9, 0), close_date=datetime(2026, 8, 10, 10, 0)),
            ])

        with transaction_context() as db:
            filas = cancelaciones_por_empleado_query(
                db, date(2026, 8, 10), date(2026, 8, 10), {"empleados": [EMPLEADO_B]}, None,
            )

        self.assertEqual([(EMPLEADO_B, date(2026, 8, 10), 1)], [tuple(f) for f in filas])


if __name__ == "__main__":
    unittest.main()
