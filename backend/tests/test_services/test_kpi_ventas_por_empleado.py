from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete

from app.kpis.registry import egresos_por_empleado_query, ventas_por_empleado_query
from app.models import Invoice, Proyect, User
from app.models.session import engine, transaction_context

# Los KPI de facturacion se prueban contra PostgreSQL real, no SQLite: el
# esquema de PostgreSQL ya trae, ademas del que declara el modelo, un
# `fk_invoice_created_by` agregado por `database/init.sql` (ver el reporte de
# la tarea), y esta prueba depende de que los bootstrap de siempre
# (customer_supplier=1, proyect=1, status=1, user=1) ya existan -- los mismos
# que siembra `init_db.py`. Igual que `test_document_laboratory_postgresql.py`,
# no hereda de `BackendTestCase`: `reset_test_database()` recrea el esquema
# solo con lo que declara el ORM (sin las FK diferibles que el propio init.sql
# agrega para poder sembrar el ciclo permission/user/proyect), asi que tirar el
# esquema aqui rompería esa siembra.
ADMIN_ID = 1
EMPLEADO_A = 950
EMPLEADO_B = 951
PROYECTO_ACTOR = 950
PROYECTO_OTRO = 951


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class VentasPorEmpleadoQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Empleado {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-test-{user_id}",
                ))
            db.flush()
            for proyect_id in (PROYECTO_ACTOR, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI {proyect_id}", created_by=ADMIN_ID,
                ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Invoice).where(Invoice.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _factura(self, created_by, id_proyect, fecha, subtotal, invoice_status, invoice_direction=None):
        return Invoice(
            id_customer_supplier=1, id_issuer_customer_supplier=1, id_status=1,
            tax_certification_supplier=1, apply_tax=False,
            created_by=created_by, id_proyect=id_proyect,
            date_emision=fecha, subtotal=Decimal(str(subtotal)),
            invoice_status=invoice_status, invoice_direction=invoice_direction,
        )

    def test_suma_por_empleado_y_dia_excluye_no_vigentes(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 1, 10, 10, 0), "1000.00", "timbrada"),
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 1, 10, 15, 30), "500.00", "pagada"),
                self._factura(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 1, 11, 9, 0), "800.00", "pendiente"),
                # No vigentes: una cancelada y una que sigue siendo cotizacion.
                # Si se contaran, el dia 2026-01-10 del empleado A daria 2500 o
                # 1800 en vez de 1500.
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 1, 10, 12, 0), "300.00", "cancelada"),
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 1, 10, 8, 0), "700.00", "cotizacion"),
            ])

        with transaction_context() as db:
            filas = ventas_por_empleado_query(
                db, date(2026, 1, 10), date(2026, 1, 11), {}, PROYECTO_ACTOR,
            )

        self.assertEqual([
            (EMPLEADO_A, date(2026, 1, 10), Decimal("1500.00")),
            (EMPLEADO_B, date(2026, 1, 11), Decimal("800.00")),
        ], [tuple(fila) for fila in filas])

    def test_actor_project_acota_el_resultado(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 2, 1, 9, 0), "1000.00", "timbrada"),
                self._factura(EMPLEADO_A, PROYECTO_OTRO, datetime(2026, 2, 1, 9, 0), "9999.00", "timbrada"),
            ])

        with transaction_context() as db:
            solo_actor = ventas_por_empleado_query(db, date(2026, 2, 1), date(2026, 2, 1), {}, PROYECTO_ACTOR)
            solo_otro = ventas_por_empleado_query(db, date(2026, 2, 1), date(2026, 2, 1), {}, PROYECTO_OTRO)
            sin_acotar = ventas_por_empleado_query(db, date(2026, 2, 1), date(2026, 2, 1), {}, None)

        self.assertEqual([(EMPLEADO_A, date(2026, 2, 1), Decimal("1000.00"))], [tuple(f) for f in solo_actor])
        self.assertEqual([(EMPLEADO_A, date(2026, 2, 1), Decimal("9999.00"))], [tuple(f) for f in solo_otro])
        self.assertEqual([(EMPLEADO_A, date(2026, 2, 1), Decimal("10999.00"))], [tuple(f) for f in sin_acotar])

    def test_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 3, 1, 9, 0), "100.00", "timbrada"),
                self._factura(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 3, 1, 9, 0), "200.00", "timbrada"),
            ])

        with transaction_context() as db:
            filas = ventas_por_empleado_query(
                db, date(2026, 3, 1), date(2026, 3, 1), {"empleados": [EMPLEADO_B]}, PROYECTO_ACTOR,
            )

        self.assertEqual([(EMPLEADO_B, date(2026, 3, 1), Decimal("200.00"))], [tuple(f) for f in filas])


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class EgresosPorEmpleadoQueryTest(unittest.TestCase):
    """Espejo de `VentasPorEmpleadoQueryTest`, pero exigiendo `invoice_direction
    == 'compra'` en vez de excluirlo -- ver el docstring de
    `egresos_por_empleado_query`.
    """

    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Empleado {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-egresos-test-{user_id}",
                ))
            db.flush()
            for proyect_id in (PROYECTO_ACTOR, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI egresos {proyect_id}", created_by=ADMIN_ID,
                ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Invoice).where(Invoice.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _factura(self, created_by, id_proyect, fecha, subtotal, invoice_status, invoice_direction=None):
        return Invoice(
            id_customer_supplier=1, id_issuer_customer_supplier=1, id_status=1,
            tax_certification_supplier=1, apply_tax=False,
            created_by=created_by, id_proyect=id_proyect,
            date_emision=fecha, subtotal=Decimal(str(subtotal)),
            invoice_status=invoice_status, invoice_direction=invoice_direction,
        )

    def test_solo_cuenta_direccion_compra(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 10, 10, 0), "600.00", "pagada", "compra"),
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 10, 15, 0), "400.00", "pagada", "compra"),
                # Venta normal capturada a mano (direccion NULL): no es egreso.
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 10, 9, 0), "9999.00", "pagada", None),
                # Compra pero no vigente: cancelada.
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 10, 8, 0), "300.00", "cancelada", "compra"),
                self._factura(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 4, 11, 9, 0), "150.00", "timbrada", "compra"),
            ])

        with transaction_context() as db:
            filas = egresos_por_empleado_query(
                db, date(2026, 4, 10), date(2026, 4, 11), {}, PROYECTO_ACTOR,
            )

        self.assertEqual([
            (EMPLEADO_A, date(2026, 4, 10), Decimal("1000.00")),
            (EMPLEADO_B, date(2026, 4, 11), Decimal("150.00")),
        ], [tuple(fila) for fila in filas])

    def test_actor_project_acota_el_resultado(self):
        with transaction_context() as db:
            db.add_all([
                self._factura(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 20, 9, 0), "500.00", "pagada", "compra"),
                self._factura(EMPLEADO_A, PROYECTO_OTRO, datetime(2026, 4, 20, 9, 0), "700.00", "pagada", "compra"),
            ])

        with transaction_context() as db:
            solo_actor = egresos_por_empleado_query(db, date(2026, 4, 20), date(2026, 4, 20), {}, PROYECTO_ACTOR)
            solo_otro = egresos_por_empleado_query(db, date(2026, 4, 20), date(2026, 4, 20), {}, PROYECTO_OTRO)

        self.assertEqual([(EMPLEADO_A, date(2026, 4, 20), Decimal("500.00"))], [tuple(f) for f in solo_actor])
        self.assertEqual([(EMPLEADO_A, date(2026, 4, 20), Decimal("700.00"))], [tuple(f) for f in solo_otro])


if __name__ == "__main__":
    unittest.main()
