from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete

from app.kpis.registry import desarrollo_por_empleado_query
from app.models import Proyect, Task, User
from app.models.session import engine, transaction_context

# Mismo criterio que test_kpi_ventas_por_empleado.py: se corre solo contra
# PostgreSQL real y reutiliza los bootstrap de siempre (customer_supplier=1,
# proyect=1, status=1, user=1) que siembra init_db.py.
ADMIN_ID = 1
EMPLEADO_A = 952
EMPLEADO_B = 953
PROYECTO_ACTOR = 952
PROYECTO_OTRO = 953


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class DesarrolloPorEmpleadoQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Empleado {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-desarrollo-test-{user_id}",
                ))
            db.flush()
            for proyect_id in (PROYECTO_ACTOR, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI desarrollo {proyect_id}", created_by=ADMIN_ID,
                ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(Task).where(Task.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(User).where(User.id_user.in_([EMPLEADO_A, EMPLEADO_B])))

    def _tarea(self, owner, id_proyect, creation_date, task_status, descripcion="Tarea KPI"):
        return Task(
            owner=owner, dependency=0, validation=ADMIN_ID,
            task_description=descripcion, task_status=task_status,
            id_proyect=id_proyect, created_by=ADMIN_ID, creation_date=creation_date,
        )

    def test_porcentaje_por_empleado_excluye_fuera_de_rango(self):
        with transaction_context() as db:
            db.add_all([
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 5, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 5, 2, 9, 0), "terminada"),
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 5, 3, 9, 0), "en_proceso"),
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 5, 4, 9, 0), "bloqueada"),
                # Fuera de rango: no debe contarse ni en numerador ni denominador.
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 4, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 5, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 5, 2, 9, 0), "cancelada"),
            ])

        with transaction_context() as db:
            filas = desarrollo_por_empleado_query(
                db, date(2026, 5, 1), date(2026, 5, 4), {}, PROYECTO_ACTOR,
            )

        # A: 2 de 4 terminadas = 50.00%. B: 1 de 2 terminadas = 50.00%.
        self.assertEqual([
            (EMPLEADO_A, date(2026, 5, 4), Decimal("50.00")),
            (EMPLEADO_B, date(2026, 5, 4), Decimal("50.00")),
        ], [tuple(fila) for fila in filas])

    def test_status_null_o_desconocido_cuenta_como_no_terminada(self):
        with transaction_context() as db:
            db.add_all([
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 6, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 6, 1, 10, 0), None),
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 6, 1, 11, 0), "estatus_viejo"),
            ])

        with transaction_context() as db:
            filas = desarrollo_por_empleado_query(
                db, date(2026, 6, 1), date(2026, 6, 1), {}, PROYECTO_ACTOR,
            )

        # 1 de 3 terminadas = 33.33%; NULL y el estatus desconocido no suman
        # al numerador, pero si al denominador.
        self.assertEqual([(EMPLEADO_A, date(2026, 6, 1), Decimal("33.33"))], [tuple(f) for f in filas])

    def test_actor_project_acota_el_resultado(self):
        with transaction_context() as db:
            db.add_all([
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 7, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_A, PROYECTO_OTRO, datetime(2026, 7, 1, 9, 0), "en_proceso"),
            ])

        with transaction_context() as db:
            solo_actor = desarrollo_por_empleado_query(db, date(2026, 7, 1), date(2026, 7, 1), {}, PROYECTO_ACTOR)
            solo_otro = desarrollo_por_empleado_query(db, date(2026, 7, 1), date(2026, 7, 1), {}, PROYECTO_OTRO)

        self.assertEqual([(EMPLEADO_A, date(2026, 7, 1), Decimal("100.00"))], [tuple(f) for f in solo_actor])
        self.assertEqual([(EMPLEADO_A, date(2026, 7, 1), Decimal("0.00"))], [tuple(f) for f in solo_otro])

    def test_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._tarea(EMPLEADO_A, PROYECTO_ACTOR, datetime(2026, 8, 1, 9, 0), "terminada"),
                self._tarea(EMPLEADO_B, PROYECTO_ACTOR, datetime(2026, 8, 1, 9, 0), "en_proceso"),
            ])

        with transaction_context() as db:
            filas = desarrollo_por_empleado_query(
                db, date(2026, 8, 1), date(2026, 8, 1), {"empleados": [EMPLEADO_B]}, PROYECTO_ACTOR,
            )

        self.assertEqual([(EMPLEADO_B, date(2026, 8, 1), Decimal("0.00"))], [tuple(f) for f in filas])


if __name__ == "__main__":
    unittest.main()
