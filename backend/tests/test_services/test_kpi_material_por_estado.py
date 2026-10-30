from __future__ import annotations

import unittest
from datetime import date, datetime

from sqlalchemy import delete

from app.kpis.registry import material_por_estado_query
from app.models import (
    Brand, Incident, IncidentType, Invoice, Location, LocationType,
    Material, NmIncidentProduct, Product, ProductFamily, Unit, User,
)
from app.models.session import engine, transaction_context

# Mismo criterio que test_kpi_incidentes.py: solo PostgreSQL real, reusa el
# bootstrap de siempre (user=1, proyect=1, status=1, customer_supplier=1).
# IDs propios (980+) para no chocar si corre en la misma base que ese archivo.
ADMIN_ID = 1
EMPLEADO = 980
INCIDENT_TYPE_NORMAL = 980
INCIDENT_TYPE_DESTRUCCION = 981
INCIDENT_TYPE_EXTRAVIADO = 982
LOCATION_TYPE = 980
LOCATION = 980
BRAND = 980
PRODUCT_FAMILY = 980
UNIT = 980
MATERIAL = 980
INVOICE = 980
PRODUCT = 980


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class MaterialPorEstadoQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            db.add(User(
                id_user=EMPLEADO, created_by=ADMIN_ID, full_name="Empleado 980",
                id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                user_type="employee", is_employee=True, username="kpi-material-estado-test",
            ))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_NORMAL, incident_type_description="Vale normal", created_by=ADMIN_ID))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_DESTRUCCION, incident_type_description="Destruccion", created_by=ADMIN_ID))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_EXTRAVIADO, incident_type_description="Extraviado", created_by=ADMIN_ID))
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
            db.execute(delete(Incident).where(Incident.id_incident_type.in_(
                [INCIDENT_TYPE_NORMAL, INCIDENT_TYPE_DESTRUCCION, INCIDENT_TYPE_EXTRAVIADO])))
            db.execute(delete(Product).where(Product.id_product == PRODUCT))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE))
            db.execute(delete(Material).where(Material.id_material == MATERIAL))
            db.execute(delete(Location).where(Location.id_location == LOCATION))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type.in_(
                [INCIDENT_TYPE_NORMAL, INCIDENT_TYPE_DESTRUCCION, INCIDENT_TYPE_EXTRAVIADO])))
            db.execute(delete(User).where(User.id_user == EMPLEADO))

    def _incidente(self, id_incident, id_incident_type, incident_date):
        return Incident(
            id_incident=id_incident, id_incident_type=id_incident_type, id_user=EMPLEADO,
            incident_status="abierta", creation_date=incident_date, incident_date=incident_date,
            created_by=EMPLEADO,
        )

    def _renglon(self, id_nm_incident_product, id_incident, direction):
        return NmIncidentProduct(
            id_nm_incident_product=id_nm_incident_product, id_incident=id_incident, id_product=PRODUCT,
            quantity=1, direction=direction, created_by=ADMIN_ID,
        )

    def test_entrada_y_salida_por_direction(self):
        with transaction_context() as db:
            db.add_all([
                self._incidente(9800, INCIDENT_TYPE_NORMAL, datetime(2031, 9, 1)),
                self._incidente(9801, INCIDENT_TYPE_NORMAL, datetime(2031, 9, 1)),
            ])
            db.flush()
            db.add_all([
                self._renglon(98000, 9800, "entrada"),
                self._renglon(98001, 9801, "salida"),
            ])

        with transaction_context() as db:
            filas = material_por_estado_query(db, date(2031, 9, 1), date(2031, 9, 1), {}, None)

        self.assertEqual(
            [("Entrada", date(2031, 9, 1), 1), ("Salida", date(2031, 9, 1), 1)],
            sorted([tuple(f) for f in filas]),
        )

    def test_tipo_especial_pisa_a_la_direccion(self):
        with transaction_context() as db:
            db.add(self._incidente(9802, INCIDENT_TYPE_DESTRUCCION, datetime(2031, 9, 2)))
            db.flush()
            # direction="entrada", pero el TIPO es Destruccion -- debe ganar
            # el tipo, no la direccion (ver _estado_del_renglon).
            db.add(self._renglon(98002, 9802, "entrada"))

        with transaction_context() as db:
            filas = material_por_estado_query(db, date(2031, 9, 2), date(2031, 9, 2), {}, None)

        self.assertEqual([("Destruccion", date(2031, 9, 2), 1)], [tuple(f) for f in filas])

    def test_extraviado_reconocido_igual_que_destruccion_y_danado(self):
        with transaction_context() as db:
            db.add(self._incidente(9803, INCIDENT_TYPE_EXTRAVIADO, datetime(2031, 9, 3)))
            db.flush()
            db.add(self._renglon(98003, 9803, "salida"))

        with transaction_context() as db:
            filas = material_por_estado_query(db, date(2031, 9, 3), date(2031, 9, 3), {}, None)

        self.assertEqual([("Extraviado", date(2031, 9, 3), 1)], [tuple(f) for f in filas])

    def test_combina_en_python_categorias_repetidas_del_mismo_dia(self):
        # Dos vales NORMALES distintos (mismo tipo de incidencia, pero podria
        # ser cualquier tipo no especial) con direction="salida" el mismo dia
        # deben sumarse en una sola fila "Salida", no llegar sueltos -- si
        # llegaran sueltos, el upsert de tasks_kpis.py pisaria el primero.
        with transaction_context() as db:
            db.add_all([
                self._incidente(9804, INCIDENT_TYPE_NORMAL, datetime(2031, 9, 4)),
                self._incidente(9805, INCIDENT_TYPE_NORMAL, datetime(2031, 9, 4)),
            ])
            db.flush()
            db.add_all([
                self._renglon(98004, 9804, "salida"),
                self._renglon(98005, 9805, "salida"),
            ])

        with transaction_context() as db:
            filas = material_por_estado_query(db, date(2031, 9, 4), date(2031, 9, 4), {}, None)

        self.assertEqual([("Salida", date(2031, 9, 4), 2)], [tuple(f) for f in filas])

    def test_usa_incident_date_no_creation_date_del_renglon(self):
        # NmIncidentProduct.creation_date trae server_default=func.now() y no
        # se pasa aqui a proposito -- la query debe ignorarlo y agrupar por
        # Incident.incident_date, igual que hace migrate_adser.py para lo
        # real (creation_date del renglon queda en la fecha de migracion).
        with transaction_context() as db:
            db.add(self._incidente(9806, INCIDENT_TYPE_NORMAL, datetime(2031, 9, 5)))
            db.flush()
            db.add(self._renglon(98006, 9806, "entrada"))

        with transaction_context() as db:
            filas = material_por_estado_query(db, date(2031, 9, 5), date(2031, 9, 5), {}, None)

        self.assertEqual([("Entrada", date(2031, 9, 5), 1)], [tuple(f) for f in filas])


if __name__ == "__main__":
    unittest.main()
