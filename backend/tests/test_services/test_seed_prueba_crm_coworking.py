"""El script de datos de prueba de la pestana CRM deja a cada KPI exactamente lo que dice (`DATOS_DE_PRUEBA`) y se deshace sin tocar nada mas.

Solo PostgreSQL: el script usa `RETURNING` y `= ANY(...)`. No corre el script contra ninguna base real: llama a `insertar` y `borrar`
(sin la guardia de base) sobre la base de prueba que arma cada test.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import func, select, text

from app.kpis.modulos.crm import (
    clientes_activos_query, clientes_nuevos_query, proyectos_con_entrega_vencida_query, proyectos_por_estado_comercial_query,
    tareas_bloqueadas_por_responsable_query, tareas_por_estado_query,
)
from app.models import CustomerSupplier, Proyect, Task
from app.models.session import engine, transaction_context
from scripts import seed_prueba_crm_coworking as seed
from tests.conftest import BackendTestCase
from tests.kpi_crm_base import Siembra, sembrar_admin
from tests.reloj import ahora_local

HOY = date(2026, 10, 28)
AHORA = datetime(2026, 10, 28, 12, 0)


@unittest.skipUnless(engine.dialect.name == "postgresql", "El script usa RETURNING y = ANY(...) de PostgreSQL")
class SeedPruebaCrmCoworkingTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        sembrar_admin()
        self.siembra = Siembra()
        self.responsables = [(self.siembra.usuario(f"PRUEBA Persona {n}"), f"PRUEBA Persona {n}") for n in (1, 2, 3)]

    def _sembrar(self):
        with transaction_context() as db:
            # Los datos de base se sembraron con ids explicitos: las secuencias siguen en 1 y el script (que deja que la base asigne
            # el id, como en la base real) chocaria con el cliente 1. Se alinean, como en una base con ids migrados.
            for tabla, columna in (("customer_supplier", "id_customer_supplier"), ("proyect", "id_proyect"), ("task", "id_task")):
                db.execute(text(f"select setval(pg_get_serial_sequence('{tabla}', '{columna}'), (select coalesce(max({columna}), 1) from {tabla}))"))
            return seed.insertar(db, self.responsables, HOY)

    def _kpi(self, consulta, *argumentos):
        with ahora_local(AHORA), transaction_context() as db:
            return [tuple(fila) for fila in consulta(db, *argumentos)]

    def _cuentas(self):
        with transaction_context() as db:
            return seed._cuentas_marcadas(db)

    def test_siembra_lo_que_dice_y_es_idempotente_en_su_marca(self):
        clientes, proyectos, tareas = self._sembrar()
        self.assertEqual((len(seed.CLIENTES), len(seed.PROYECTOS), len(seed.TAREAS)), (len(clientes), len(proyectos), len(tareas)))
        self.assertEqual({"clientes": 9, "proyectos": 12, "tareas": 24}, self._cuentas())

    def test_los_kpis_de_clientes_y_proyectos_dan_lo_que_promete_el_script(self):
        self._sembrar()
        esperado = seed.DATOS_DE_PRUEBA
        self.assertEqual([(None, HOY, esperado["clientes_activos"])], self._kpi(clientes_activos_query, HOY, HOY, {}, None))
        self.assertEqual([(None, HOY, esperado["proyectos_con_entrega_vencida"])],
                         self._kpi(proyectos_con_entrega_vencida_query, HOY, HOY, {}, None))
        por_estado = {estado: total for estado, _, total in self._kpi(proyectos_por_estado_comercial_query, HOY, HOY, {}, None)}
        # El proyecto interno del admin (id 1) esta pendiente de orden de compra por omision: uno mas.
        esperado_comercial = {**esperado["proyectos_por_estado_comercial"]}
        esperado_comercial["pendiente_orden_compra"] += 1
        self.assertEqual(esperado_comercial, por_estado)

    def test_los_kpis_de_tareas_dan_lo_que_promete_el_script(self):
        self._sembrar()
        por_estado = {estado: total for estado, _, total in self._kpi(tareas_por_estado_query, HOY, HOY, {}, None)}
        self.assertEqual(seed.DATOS_DE_PRUEBA["tareas_por_estado"], por_estado)
        ids = [i for i, _ in self.responsables]
        bloqueadas = {owner: total for owner, _, total in self._kpi(tareas_bloqueadas_por_responsable_query, HOY, HOY, {}, None)}
        self.assertEqual({ids[0]: 2, ids[1]: 1, ids[2]: 1}, bloqueadas)

    def test_los_ocho_clientes_nuevos_caen_dentro_de_los_ultimos_60_dias(self):
        self._sembrar()
        filas = self._kpi(clientes_nuevos_query, HOY - timedelta(days=60), HOY, {}, None)
        self.assertEqual(8, sum(total for _, _, total in filas), "los 8 clientes; el proveedor no cuenta")
        self.assertTrue(all(HOY - timedelta(days=60) <= fecha <= HOY for _, fecha, _ in filas))

    def test_deshacer_borra_solo_lo_marcado_y_deja_lo_demas(self):
        propio = self.siembra.cliente("Cliente real", creation_date=datetime(2026, 5, 1, 12, 0))
        proyecto_propio = self.siembra.proyecto(propio)
        self.siembra.tarea(self.responsables[0][0], proyecto_propio, "pendiente")
        self._sembrar()
        with transaction_context() as db:
            borradas = seed.borrar(db)
        self.assertEqual({"tareas": 24, "proyectos": 12, "clientes": 9}, borradas)
        self.assertEqual({"clientes": 0, "proyectos": 0, "tareas": 0}, self._cuentas())
        with transaction_context() as db:
            self.assertEqual(2, db.scalar(select(func.count()).select_from(CustomerSupplier)), "el interno (id 1) y el cliente real")
            self.assertEqual(2, db.scalar(select(func.count()).select_from(Proyect)), "el interno (id 1) y el del cliente real")
            self.assertEqual(1, db.scalar(select(func.count()).select_from(Task)), "la tarea real")
        with transaction_context() as db:
            self.assertEqual({"tareas": 0, "proyectos": 0, "clientes": 0}, seed.borrar(db), "borrar dos veces no falla ni borra mas")

    def test_los_numeros_del_script_coinciden_con_sus_datos(self):
        # Si alguien cambia `CLIENTES`, `PROYECTOS` o `TAREAS` sin actualizar `DATOS_DE_PRUEBA`, esto lo dice antes que el KPI.
        estados = {}
        for _, estado, _, _ in seed.TAREAS:
            estados[estado or "sin_estado"] = estados.get(estado or "sin_estado", 0) + 1
        self.assertEqual(seed.DATOS_DE_PRUEBA["tareas_por_estado"], estados)
        comercial = {}
        for _, _, _, estado, _ in seed.PROYECTOS:
            comercial[estado] = comercial.get(estado, 0) + 1
        self.assertEqual(seed.DATOS_DE_PRUEBA["proyectos_por_estado_comercial"], comercial)


if __name__ == "__main__":
    unittest.main()
