"""El job nocturno con los KPIs de la pestana CRM: sin alcance de proyecto, no multiplica por el numero de proyectos.

Solo PostgreSQL: el upsert de snapshots usa INSERT ... ON CONFLICT.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.jobs import tasks_kpis
from app.kpis.registry import seed_kpi_definitions
from app.models import KpiDefinition, KpiSnapshot, Task
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase
from tests.kpi_crm_base import Siembra, sembrar_admin
from tests.reloj import ahora_local

HOY = date(2026, 10, 28)
AHORA = datetime(2026, 10, 28, 12, 0)


@unittest.skipUnless(engine.dialect.name == "postgresql", "El upsert de snapshots usa INSERT ... ON CONFLICT de PostgreSQL")
class JobDeCrmTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        sembrar_admin()
        siembra = Siembra()
        self._cliente, self._proyecto = siembra.cliente, siembra.proyecto
        self._usuario, self._tarea = siembra.usuario, siembra.tarea
        seed_kpi_definitions(engine)

    def _correr(self, claves):
        with ahora_local(AHORA), transaction_context() as db:
            tasks_kpis._recalcular_kpi_snapshots_en_sesion(db, HOY - timedelta(days=6), HOY, claves=claves)

    def _snapshots(self, clave):
        with transaction_context() as db:
            return db.execute(
                select(KpiSnapshot.periodo, KpiSnapshot.dimension_key, KpiSnapshot.valor)
                .join(KpiDefinition, KpiDefinition.id_kpi_definition == KpiSnapshot.id_kpi_definition)
                .where(KpiDefinition.clave == clave)
                .order_by(KpiSnapshot.periodo)
            ).all()

    def test_clientes_activos_se_escribe_una_sola_vez_aunque_haya_muchos_proyectos(self):
        # Tres proyectos vivos del mismo cliente y uno de otro: son 2 clientes, no 4 ni 3 x N.
        inquilino = self._cliente("Inquilino 4")
        for _ in range(3):
            self._proyecto(inquilino)
        self._proyecto(self._cliente("Inquilino 5"))
        self._correr(("clientes_activos",))
        filas = self._snapshots("clientes_activos")
        self.assertEqual([(HOY, {}, Decimal("2"))], [tuple(f) for f in filas], "una fila, sin id_proyect en la llave")

    def test_clientes_nuevos_no_lleva_id_proyect_ni_se_repite_por_proyecto(self):
        self._proyecto(self._cliente("Inquilino 1", creation_date=datetime(2026, 10, 27, 15, 0)))
        self._proyecto(self._cliente("Inquilino 2", creation_date=datetime(2026, 10, 27, 16, 0)))
        self._correr(("clientes_nuevos",))
        filas = self._snapshots("clientes_nuevos")
        self.assertEqual([(date(2026, 10, 27), {}, Decimal("2"))], [tuple(f) for f in filas])

    def test_correr_dos_veces_el_mismo_dia_no_duplica_ni_suma(self):
        self._proyecto(self._cliente("Inquilino 1"))
        self._correr(("clientes_activos",))
        self._correr(("clientes_activos",))
        self.assertEqual([(HOY, {}, Decimal("1"))], [tuple(f) for f in self._snapshots("clientes_activos")])

    def test_proyectos_por_estado_comercial_escribe_una_fila_por_categoria_sin_multiplicar_por_proyecto(self):
        inquilino = self._cliente("Inquilino 4")
        for _ in range(3):
            self._proyecto(inquilino, comercial="autorizado")
        self._proyecto(inquilino, comercial="cobrado", estado="completed")
        self._correr(("proyectos_por_estado_comercial",))
        filas = {tuple(f[1].items())[0][1]: (f[0], f[2]) for f in self._snapshots("proyectos_por_estado_comercial")}
        # El proyecto interno del admin (id 1) esta pendiente de orden de compra por omision.
        self.assertEqual({
            "pendiente_orden_compra": (HOY, Decimal("1")), "autorizado": (HOY, Decimal("3")),
            "cancelado": (HOY, Decimal("0")), "cobrado": (HOY, Decimal("1")),
        }, filas, "una fila por categoria, con la llave 'estado' y sin id_proyect: 3 autorizados, no 3 x N")

    def test_proyectos_con_entrega_vencida_se_escribe_una_sola_vez(self):
        inquilino = self._cliente("Inquilino 4")
        for _ in range(3):
            self._proyecto(inquilino, entrega=date(2026, 10, 1))
        self._correr(("proyectos_con_entrega_vencida",))
        self.assertEqual([(HOY, {}, Decimal("3"))], [tuple(f) for f in self._snapshots("proyectos_con_entrega_vencida")])

    def test_tareas_por_estado_cuenta_cada_tarea_una_vez_aunque_haya_muchos_proyectos(self):
        ana = self._usuario("Ana")
        proyectos = [self._proyecto(self._cliente(f"Inquilino {n}")) for n in range(3)]
        for proyecto in proyectos:
            self._tarea(ana, proyecto, "bloqueada")
        self._correr(("tareas_por_estado",))
        filas = {tuple(f[1].items())[0][1]: (f[0], f[2]) for f in self._snapshots("tareas_por_estado")}
        self.assertEqual((HOY, Decimal("3")), filas["bloqueada"], "3 tareas, no 3 x N proyectos")
        self.assertEqual({"pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada"}, set(filas))

    def test_tareas_bloqueadas_por_responsable_suma_los_proyectos_y_deja_en_cero_al_que_se_desbloquea(self):
        ana, beto = self._usuario("Ana"), self._usuario("Beto")
        proyectos = [self._proyecto(self._cliente(f"Inquilino {n}")) for n in range(3)]
        for proyecto in proyectos:
            self._tarea(ana, proyecto, "bloqueada")
        id_beto = self._tarea(beto, proyectos[0], "bloqueada")
        self._correr(("tareas_bloqueadas_por_responsable",))
        por_responsable = {f[1]["id_user"]: f[2] for f in self._snapshots("tareas_bloqueadas_por_responsable")}
        self.assertEqual({ana: Decimal("3"), beto: Decimal("1")}, por_responsable)
        # Beto desbloquea su tarea: la corrida siguiente lo deja en 0, no en el 1 de antes.
        with transaction_context() as db:
            db.get(Task, id_beto).task_status = "en_proceso"
        self._correr(("tareas_bloqueadas_por_responsable",))
        por_responsable = {f[1]["id_user"]: f[2] for f in self._snapshots("tareas_bloqueadas_por_responsable")}
        self.assertEqual({ana: Decimal("3"), beto: Decimal("0")}, por_responsable)


if __name__ == "__main__":
    unittest.main()
