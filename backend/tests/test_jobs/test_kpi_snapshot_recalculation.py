from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import cast, delete, select
from sqlalchemy.dialects.postgresql import JSONB

from app.jobs.tasks_kpis import recalculate_kpi_snapshots
from app.kpis.registry import seed_kpi_definitions
from app.models import Invoice, KpiDefinition, KpiSnapshot, Proyect, User
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


if __name__ == "__main__":
    unittest.main()
