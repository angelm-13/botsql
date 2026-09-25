from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete

from app.kpis.registry import (
    costo_promedio_reparacion_laboratorio_por_tecnico_query,
    ordenes_laboratorio_entregadas_por_tecnico_query,
    tiempo_promedio_reparacion_laboratorio_por_tecnico_query,
)
from app.models import LaboratoryEquipment, LaboratoryServiceOrder, Proyect, User
from app.models.session import engine, transaction_context

# Mismo criterio que test_kpi_desarrollo_por_empleado.py: PostgreSQL real,
# reutiliza el bootstrap de siempre (customer_supplier=1, status=1, user=1).
ADMIN_ID = 1
TECNICO_A = 980
TECNICO_B = 981
PROYECTO_ACTOR = 980
PROYECTO_OTRO = 981
EQUIPO_A = 980
EQUIPO_B = 981


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class KpiLaboratorioQueryTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        with transaction_context() as db:
            for user_id in (TECNICO_A, TECNICO_B):
                db.add(User(
                    id_user=user_id, created_by=ADMIN_ID, full_name=f"Tecnico {user_id}",
                    id_permission=1, id_proyect=1, id_status=1, supervisor=ADMIN_ID,
                    user_type="employee", is_employee=True, username=f"kpi-lab-test-{user_id}",
                ))
            db.flush()
            for proyect_id in (PROYECTO_ACTOR, PROYECTO_OTRO):
                db.add(Proyect(
                    id_proyect=proyect_id, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto KPI laboratorio {proyect_id}", created_by=ADMIN_ID,
                ))
            db.flush()
            db.add(LaboratoryEquipment(
                id_laboratory_equipment=EQUIPO_A, id_proyect=PROYECTO_ACTOR, id_customer_supplier=1,
                equipment_type="Multimetro", created_by=ADMIN_ID,
            ))
            db.add(LaboratoryEquipment(
                id_laboratory_equipment=EQUIPO_B, id_proyect=PROYECTO_OTRO, id_customer_supplier=1,
                equipment_type="Osciloscopio", created_by=ADMIN_ID,
            ))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            db.execute(delete(LaboratoryServiceOrder).where(LaboratoryServiceOrder.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(LaboratoryEquipment).where(LaboratoryEquipment.id_laboratory_equipment.in_([EQUIPO_A, EQUIPO_B])))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_([PROYECTO_ACTOR, PROYECTO_OTRO])))
            db.execute(delete(User).where(User.id_user.in_([TECNICO_A, TECNICO_B])))

    def _orden(self, folio, id_proyect, id_technician, status, reception_date,
               actual_delivery_date=None, final_cost=None, id_equipo=EQUIPO_A):
        return LaboratoryServiceOrder(
            id_proyect=id_proyect, folio=folio, id_laboratory_equipment=id_equipo,
            id_customer_supplier=1, contact_name="Cliente KPI", reported_failure="No enciende",
            id_technician=id_technician, status=status, final_cost=final_cost,
            reception_date=reception_date, actual_delivery_date=actual_delivery_date,
            created_by=ADMIN_ID,
        )

    # --- ordenes_laboratorio_entregadas_por_tecnico_query ---------------

    def test_solo_cuenta_entregadas_con_tecnico_asignado(self):
        with transaction_context() as db:
            db.add_all([
                self._orden("L-1", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 5)),
                # No entregada todavia: no cuenta.
                self._orden("L-2", PROYECTO_ACTOR, TECNICO_A, "repairing", datetime(2026, 9, 1)),
                # Entregada pero sin tecnico asignado: no cuenta.
                self._orden("L-3", PROYECTO_ACTOR, None, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 5)),
            ])

        with transaction_context() as db:
            filas = ordenes_laboratorio_entregadas_por_tecnico_query(
                db, date(2026, 9, 1), date(2026, 9, 10), {}, PROYECTO_ACTOR,
            )

        self.assertEqual([(TECNICO_A, date(2026, 9, 5), 1)], [tuple(f) for f in filas])

    def test_alcance_por_proyecto(self):
        with transaction_context() as db:
            db.add_all([
                self._orden("L-4", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 2), actual_delivery_date=datetime(2026, 9, 6)),
                self._orden("L-5", PROYECTO_OTRO, TECNICO_A, "delivered",
                            datetime(2026, 9, 2), actual_delivery_date=datetime(2026, 9, 6), id_equipo=EQUIPO_B),
            ])

        with transaction_context() as db:
            solo_actor = ordenes_laboratorio_entregadas_por_tecnico_query(
                db, date(2026, 9, 6), date(2026, 9, 6), {}, PROYECTO_ACTOR,
            )
            solo_otro = ordenes_laboratorio_entregadas_por_tecnico_query(
                db, date(2026, 9, 6), date(2026, 9, 6), {}, PROYECTO_OTRO,
            )

        self.assertEqual([(TECNICO_A, date(2026, 9, 6), 1)], [tuple(f) for f in solo_actor])
        self.assertEqual([(TECNICO_A, date(2026, 9, 6), 1)], [tuple(f) for f in solo_otro])

    # --- tiempo_promedio_reparacion_laboratorio_por_tecnico_query -------

    def test_tiempo_promedio_de_reparacion_en_dias(self):
        with transaction_context() as db:
            db.add_all([
                self._orden("L-6", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 5)),  # 4 dias
                self._orden("L-7", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 3), actual_delivery_date=datetime(2026, 9, 5)),  # 2 dias
            ])

        with transaction_context() as db:
            filas = tiempo_promedio_reparacion_laboratorio_por_tecnico_query(
                db, date(2026, 9, 5), date(2026, 9, 5), {}, PROYECTO_ACTOR,
            )

        self.assertEqual(1, len(filas))
        id_tecnico, periodo, promedio, peso = filas[0]
        self.assertEqual(TECNICO_A, id_tecnico)
        self.assertEqual(date(2026, 9, 5), periodo)
        self.assertAlmostEqual(3.0, float(promedio), places=2)
        self.assertEqual(2, peso)  # las 2 ordenes detras del promedio

    # --- costo_promedio_reparacion_laboratorio_por_tecnico_query --------

    def test_costo_promedio_excluye_ordenes_sin_costo_capturado(self):
        with transaction_context() as db:
            db.add_all([
                self._orden("L-8", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 8),
                            final_cost=Decimal("800.00")),
                self._orden("L-9", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 8),
                            final_cost=Decimal("1200.00")),
                # Entregada pero sin costo capturado: no debe promediar como 0.
                self._orden("L-10", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 1), actual_delivery_date=datetime(2026, 9, 8), final_cost=None),
            ])

        with transaction_context() as db:
            filas = costo_promedio_reparacion_laboratorio_por_tecnico_query(
                db, date(2026, 9, 8), date(2026, 9, 8), {}, PROYECTO_ACTOR,
            )

        self.assertEqual(1, len(filas))
        id_tecnico, periodo, promedio, peso = filas[0]
        self.assertEqual(TECNICO_A, id_tecnico)
        self.assertEqual(date(2026, 9, 8), periodo)
        self.assertEqual(Decimal("1000.00"), Decimal(promedio).quantize(Decimal("0.01")))
        # Peso = solo las ordenes CON costo: la de final_cost NULL no pesa.
        self.assertEqual(2, peso)

    def test_filtro_de_empleados(self):
        with transaction_context() as db:
            db.add_all([
                self._orden("L-11", PROYECTO_ACTOR, TECNICO_A, "delivered",
                            datetime(2026, 9, 9), actual_delivery_date=datetime(2026, 9, 9), final_cost=Decimal("500.00")),
                self._orden("L-12", PROYECTO_ACTOR, TECNICO_B, "delivered",
                            datetime(2026, 9, 9), actual_delivery_date=datetime(2026, 9, 9), final_cost=Decimal("700.00")),
            ])

        with transaction_context() as db:
            filas = ordenes_laboratorio_entregadas_por_tecnico_query(
                db, date(2026, 9, 9), date(2026, 9, 9), {"empleados": [TECNICO_B]}, PROYECTO_ACTOR,
            )

        self.assertEqual([(TECNICO_B, date(2026, 9, 9), 1)], [tuple(f) for f in filas])


if __name__ == "__main__":
    unittest.main()
