from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import cast, delete, select
from sqlalchemy.dialects.postgresql import JSONB

from app.jobs.tasks_kpis import recalculate_kpi_snapshots
from app.kpis.registry import seed_kpi_definitions
from app.models import (
    Brand, Incident, IncidentType, Invoice, KpiDefinition, KpiSnapshot,
    Location, LocationType, Material, NmIncidentProduct, Product,
    ProductFamily, Proyect, Unit, User,
)
from app.models.session import engine, transaction_context

# Se prueba contra PostgreSQL real, no SQLite: el UNIQUE de `kpi_snapshot` es
# sobre una columna JSONB (`dimension_key`) y el upsert de la tarea usa
# `on_conflict_do_update`, exclusivo del dialecto de Postgres. Mismo patron
# que `test_kpi_ventas_por_empleado.py`: no hereda de `BackendTestCase`
# porque `reset_test_database()` no trae las FK diferibles que `init.sql`
# agrega para poder sembrar el ciclo permission/user/proyect.
ADMIN_ID = 1
EMPLEADO_A = 960
EMPLEADO_B = 961
PROYECTO_A = 960
PROYECTO_B = 961
PROYECTO_BAJA = 962

HOY = date.today()
FECHA_RECIENTE = HOY - timedelta(days=2)     # dentro de la ventana de 7 dias
FECHA_FUERA = HOY - timedelta(days=10)       # fuera de la ventana


def _por_proyecto(id_proyect):
    """`dimension_key` es JSON portable con variante JSONB en Postgres (ver
    `kpi_snapshot.py`): `.contains()` sobre el tipo generico compila como
    `LIKE`, no como `@>`. El cast fuerza el comparador de JSONB."""
    return cast(KpiSnapshot.dimension_key, JSONB).contains({"id_proyect": id_proyect})


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class RecalculateKpiSnapshotsTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        # La tarea salta cualquier KPI cuya clave no este en kpi_definition
        # (ver el comentario en tasks_kpis.py); sembrarlo aqui reproduce lo
        # que init_db.py hace en un arranque real.
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            for user_id in (EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Empleado {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-snap-test-{user_id}",
                ))
            db.flush()
            for proyect_id in (PROYECTO_A, PROYECTO_B):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI snapshot {proyect_id}", created_by=ADMIN_ID,
                ))
            db.add(Proyect(
                id_proyect=PROYECTO_BAJA, id_customer_supplier=1, leader=ADMIN_ID,
                proyect_description="Proyecto dado de baja", created_by=ADMIN_ID,
                deletion_date=datetime(2026, 1, 1),
            ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        proyectos = [PROYECTO_A, PROYECTO_B, PROYECTO_BAJA]
        with transaction_context() as db:
            for proyecto_id in proyectos:
                db.execute(delete(KpiSnapshot).where(_por_proyecto(proyecto_id)))
            db.execute(delete(Invoice).where(Invoice.id_proyect.in_(proyectos)))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_(proyectos)))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _factura(self, created_by, id_proyect, fecha, subtotal, invoice_status="timbrada"):
        return Invoice(
            id_customer_supplier=1, id_issuer_customer_supplier=1, id_status=1,
            tax_certification_supplier=1, apply_tax=False,
            created_by=created_by, id_proyect=id_proyect,
            date_emision=datetime(fecha.year, fecha.month, fecha.day, 10, 0),
            subtotal=Decimal(str(subtotal)), invoice_status=invoice_status,
        )

    def _snapshots(self, id_proyect):
        with transaction_context() as db:
            id_kpi_definition = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )
            filas = db.execute(
                select(KpiSnapshot.dimension_key, KpiSnapshot.periodo, KpiSnapshot.valor)
                .where(
                    KpiSnapshot.id_kpi_definition == id_kpi_definition,
                    _por_proyecto(id_proyect),
                )
                .order_by(KpiSnapshot.periodo)
            ).all()
        return [(dimension_key["id_user"], periodo, valor) for dimension_key, periodo, valor in filas]

    def test_puebla_kpi_snapshot_separado_por_proyecto(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_A, FECHA_RECIENTE, "1000.00"),
                self._factura(EMPLEADO_B, PROYECTO_B, FECHA_RECIENTE, "500.00"),
                # Fuera de la ventana de 7 dias: no debe generar snapshot.
                self._factura(EMPLEADO_A, PROYECTO_A, FECHA_FUERA, "99999.00"),
            ])

        resultado = recalculate_kpi_snapshots()

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            [(EMPLEADO_A, FECHA_RECIENTE, Decimal("1000.00"))], self._snapshots(PROYECTO_A),
        )
        self.assertEqual(
            [(EMPLEADO_B, FECHA_RECIENTE, Decimal("500.00"))], self._snapshots(PROYECTO_B),
        )

    def test_correr_dos_veces_actualiza_en_vez_de_duplicar(self):
        with transaction_context() as db:
            db.add(self._factura(EMPLEADO_A, PROYECTO_A, FECHA_RECIENTE, "1000.00"))

        recalculate_kpi_snapshots()
        recalculate_kpi_snapshots()

        self.assertEqual(
            [(EMPLEADO_A, FECHA_RECIENTE, Decimal("1000.00"))], self._snapshots(PROYECTO_A),
            "un segundo corrido no debe duplicar la fila",
        )

    def test_un_cambio_de_valor_en_la_ventana_actualiza_el_snapshot(self):
        with transaction_context() as db:
            db.add(self._factura(EMPLEADO_A, PROYECTO_A, FECHA_RECIENTE, "1000.00"))
        recalculate_kpi_snapshots()
        self.assertEqual(
            [(EMPLEADO_A, FECHA_RECIENTE, Decimal("1000.00"))], self._snapshots(PROYECTO_A),
        )

        with transaction_context() as db:
            factura = db.scalar(
                select(Invoice).where(
                    Invoice.id_proyect == PROYECTO_A, Invoice.created_by == EMPLEADO_A,
                )
            )
            factura.subtotal = Decimal("1500.00")

        recalculate_kpi_snapshots()

        self.assertEqual(
            [(EMPLEADO_A, FECHA_RECIENTE, Decimal("1500.00"))], self._snapshots(PROYECTO_A),
            "el snapshot debe reflejar el valor corregido, no acumularlo ni quedarse con el viejo",
        )

    def test_no_incluye_proyectos_dados_de_baja(self):
        with transaction_context() as db:
            db.add(self._factura(EMPLEADO_A, PROYECTO_BAJA, FECHA_RECIENTE, "1000.00"))

        recalculate_kpi_snapshots()

        self.assertEqual([], self._snapshots(PROYECTO_BAJA))


# IDs propios (965-969), distintos de los de arriba (960-962) y de los de
# test_kpi_incidentes.py (970+): esta clase recorre su propio setUp/tearDown
# y no deben pisarse entre corridas.
EMPLEADO_SIN_PROYECTO = 965
PROYECTO_UNO = 966
PROYECTO_DOS = 967
INCIDENT_TYPE_JOB = 965
LOCATION_TYPE_JOB = 965
LOCATION_JOB = 965
BRAND_JOB = 965
PRODUCT_FAMILY_JOB = 965
UNIT_JOB = 965
MATERIAL_JOB = 965
INVOICE_JOB = 965
PRODUCT_JOB = 965
INCIDENT_JOB = 965
VALE_JOB = 965


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class RecalculateKpiSnapshotsSinAlcanceDeProyectoTest(unittest.TestCase):
    """Un KPI con `alcance_proyecto=False` (ver `KpiDefinition` en
    `app/kpis/registry.py`) no debe calcularse una vez por proyecto activo --
    a diferencia de `ventas_por_empleado`, que SI tiene alcance de proyecto y
    ya prueba esa parte en `RecalculateKpiSnapshotsTest` de arriba."""

    def setUp(self):
        self._limpiar()
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            db.add(User(
                id_user=EMPLEADO_SIN_PROYECTO, created_by=ADMIN_ID, full_name="Empleado sin proyecto KPI",
                id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                user_type="employee", is_employee=True, username="kpi-snap-sin-proyecto",
            ))
            db.add(IncidentType(id_incident_type=INCIDENT_TYPE_JOB, incident_type_description="KPI job test", created_by=ADMIN_ID))
            db.add(LocationType(id_location_type=LOCATION_TYPE_JOB, location_type_description="KPI job test", is_warehouse=True, created_by=ADMIN_ID))
            db.add(Brand(id_brand=BRAND_JOB, brand_description="KPI job test", created_by=ADMIN_ID))
            db.add(ProductFamily(id_product_family=PRODUCT_FAMILY_JOB, product_family_description="KPI job test", created_by=ADMIN_ID))
            db.add(Unit(id_unit=UNIT_JOB, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=ADMIN_ID))
            db.flush()
            for proyect_id in (PROYECTO_UNO, PROYECTO_DOS):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI job {proyect_id}", created_by=ADMIN_ID,
                ))
            db.add(Location(id_location=LOCATION_JOB, id_location_type=LOCATION_TYPE_JOB, location_description="KPI job test", created_by=ADMIN_ID))
            db.add(Material(id_material=MATERIAL_JOB, material_description="KPI job test", id_unit=UNIT_JOB, id_brand=BRAND_JOB, id_product_family=PRODUCT_FAMILY_JOB, created_by=ADMIN_ID))
            db.flush()
            db.add(Invoice(
                id_invoice=INVOICE_JOB, id_customer_supplier=1, id_issuer_customer_supplier=1,
                id_proyect=1, id_status=1, tax_certification_supplier=1, apply_tax=False,
                invoice_status="pendiente", created_by=ADMIN_ID,
            ))
            db.flush()
            db.add(Product(
                id_product=PRODUCT_JOB, id_invoice=INVOICE_JOB, id_location=LOCATION_JOB, id_material=MATERIAL_JOB,
                is_directly_related_to_product_service=False, cantidad=5, created_by=ADMIN_ID,
            ))
            db.flush()
            db.add(Incident(
                id_incident=INCIDENT_JOB, id_incident_type=INCIDENT_TYPE_JOB, id_user=EMPLEADO_SIN_PROYECTO,
                incident_status="abierta", creation_date=FECHA_RECIENTE, created_by=EMPLEADO_SIN_PROYECTO,
            ))
            db.flush()
            db.add(NmIncidentProduct(
                id_nm_incident_product=VALE_JOB, id_incident=INCIDENT_JOB, id_product=PRODUCT_JOB,
                quantity=1, due_date=datetime.now() - timedelta(days=1), created_by=ADMIN_ID,
            ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(NmIncidentProduct).where(NmIncidentProduct.id_nm_incident_product == VALE_JOB))
            db.execute(delete(Incident).where(Incident.id_incident == INCIDENT_JOB))
            db.execute(delete(Product).where(Product.id_product == PRODUCT_JOB))
            db.execute(delete(Invoice).where(Invoice.id_invoice == INVOICE_JOB))
            db.execute(delete(Material).where(Material.id_material == MATERIAL_JOB))
            db.execute(delete(Location).where(Location.id_location == LOCATION_JOB))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_UNO, PROYECTO_DOS])))
            db.execute(delete(Unit).where(Unit.id_unit == UNIT_JOB))
            db.execute(delete(ProductFamily).where(ProductFamily.id_product_family == PRODUCT_FAMILY_JOB))
            db.execute(delete(Brand).where(Brand.id_brand == BRAND_JOB))
            db.execute(delete(LocationType).where(LocationType.id_location_type == LOCATION_TYPE_JOB))
            db.execute(delete(IncidentType).where(IncidentType.id_incident_type == INCIDENT_TYPE_JOB))
            db.execute(delete(KpiSnapshot).where(
                cast(KpiSnapshot.dimension_key, JSONB).contains({"id_user": EMPLEADO_SIN_PROYECTO})
            ))
            db.execute(delete(User).where(User.id_user == EMPLEADO_SIN_PROYECTO))

    def test_kpi_sin_alcance_de_proyecto_no_se_duplica_por_proyecto_activo(self):
        # Dos proyectos activos (PROYECTO_UNO, PROYECTO_DOS) + el bootstrap
        # (id_proyect=1): si vales_vencidos_por_responsable ignorara
        # `alcance_proyecto=False` y se recorriera igual que
        # ventas_por_empleado, sembraria una fila IDENTICA por cada uno.
        recalculate_kpi_snapshots()

        with transaction_context() as db:
            id_kpi_definition = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "vales_vencidos_por_responsable")
            )
            filas = db.execute(
                select(KpiSnapshot.dimension_key, KpiSnapshot.valor)
                .where(KpiSnapshot.id_kpi_definition == id_kpi_definition)
            ).all()

        self.assertEqual(1, len(filas), "un KPI sin alcance de proyecto debe sembrar una sola fila, no una por proyecto activo")
        dimension_key, valor = filas[0]
        self.assertNotIn("id_proyect", dimension_key, "un KPI sin alcance de proyecto no debe traer id_proyect en su dimension_key")
        self.assertEqual({"id_user": EMPLEADO_SIN_PROYECTO}, dimension_key)
        self.assertEqual(1, int(valor))


if __name__ == "__main__":
    unittest.main()
