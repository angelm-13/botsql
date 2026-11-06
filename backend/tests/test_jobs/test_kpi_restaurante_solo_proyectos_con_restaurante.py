"""Los KPIs de restaurante solo se calculan para los proyectos que tienen restaurante.

Antes el job los iteraba por TODOS los proyectos activos: `mesas_ocupadas`, `pedidos_del_dia` y
`cuentas_sin_cobrar` devuelven filas aunque no haya nada (categorias en cero), asi que cada proyecto de
cualquier otro modulo recibia filas en cero. Requiere PostgreSQL (upsert de `kpi_snapshot`).
"""

from __future__ import annotations

import unittest
from datetime import datetime

from sqlalchemy import cast, delete, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.jobs.tasks_kpis import recalculate_kpi_snapshots
from app.kpis.registry import seed_kpi_definitions
from app.models import KpiDefinition, KpiSnapshot, Proyect
from app.models.restaurant import RestaurantWaiter
from app.models.session import engine, transaction_context

ADMIN_ID = 1
CON_RESTAURANTE = 970
SIN_RESTAURANTE = 971
PROYECTOS = (CON_RESTAURANTE, SIN_RESTAURANTE)


def _por_proyecto(id_proyect):
    return cast(KpiSnapshot.dimension_key, JSONB).contains({"id_proyect": id_proyect})


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class KpisDeRestauranteSoloConRestauranteTest(unittest.TestCase):
    def setUp(self):
        self._limpiar()
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            for id_proyect in PROYECTOS:
                db.add(Proyect(
                    id_proyect=id_proyect, id_customer_supplier=1, leader=ADMIN_ID,
                    proyect_description=f"Proyecto restaurante {id_proyect}", created_by=ADMIN_ID,
                ))
            db.flush()
            db.add(RestaurantWaiter(id_proyect=CON_RESTAURANTE, name="Mesero de prueba", nickname="mp970", created_by=ADMIN_ID))

    def tearDown(self):
        self._limpiar()

    def _limpiar(self):
        with transaction_context() as db:
            for id_proyect in PROYECTOS:
                db.execute(delete(KpiSnapshot).where(_por_proyecto(id_proyect)))
            db.execute(delete(RestaurantWaiter).where(RestaurantWaiter.id_proyect.in_(PROYECTOS)))
            db.execute(delete(Proyect).where(Proyect.id_proyect.in_(PROYECTOS)))

    def _filas_de_restaurante(self, id_proyect):
        with transaction_context() as db:
            return db.scalar(
                select(func.count()).select_from(KpiSnapshot)
                .join(KpiDefinition, KpiDefinition.id_kpi_definition == KpiSnapshot.id_kpi_definition)
                .where(KpiDefinition.modulo == "restaurante", _por_proyecto(id_proyect))
            )

    def test_un_proyecto_sin_restaurante_no_recibe_filas_en_cero(self):
        recalculate_kpi_snapshots()
        self.assertEqual(0, self._filas_de_restaurante(SIN_RESTAURANTE))

    def test_un_proyecto_con_restaurante_si_se_calcula(self):
        recalculate_kpi_snapshots()
        # mesas_ocupadas (3 categorias) + pedidos_del_dia (3) + cuentas_sin_cobrar (1), del dia de hoy.
        self.assertGreaterEqual(self._filas_de_restaurante(CON_RESTAURANTE), 7)


if __name__ == "__main__":
    unittest.main()
