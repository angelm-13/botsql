from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.jobs.tasks_kpis import VENTANA_DIAS, _recalcular_kpi_snapshots_en_sesion
from app.kpis.registry import AGREGACION_POR_CLAVE, seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, KpiDefinition, KpiSnapshot, Level, Permission,
    Proyect, Status, Subdepartment, Task, User,
)
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase

# `_totales()` (app/routes/kpi.py) combina los snapshots segun la
# `agregacion` que declara cada KPI (AGREGACIONES en app/kpis/registry.py).
# Antes sumaba siempre: 30 noches de un 50 % daban 1500 %, 30 fotos de 10
# piezas daban 300. Estas pruebas fijan el numero correcto de cada regla.
ADMIN = {"id_user": 1, "is_superuser": True}
EMPLEADO_A = 950
EMPLEADO_B = 951
EMPLEADO_SIN_PESO = 952
PROYECTO_A = 960
PROYECTO_B = 961
D1, D2, D3 = date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestAgregacionDeKpis(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # Mismo ciclo user <-> customer_supplier <-> proyect que
            # test_api_kpi.py: sin aplazar las FK no hay orden de INSERT posible.
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            db.add(Permission(
                id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
                id_department=1, id_subdepartment=1, id_level=1,
            ))
            for id_user in (1, EMPLEADO_A, EMPLEADO_B):
                db.add(User(
                    id_user=id_user, created_by=1, full_name=f"Usuario {id_user}", id_permission=1,
                    id_proyect=PROYECTO_A, id_status=1, supervisor=1, user_type="admin" if id_user == 1 else "employee",
                    username=f"kpi-agregacion-{id_user}",
                ))
            db.add(CustomerSupplier(
                id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                fiscal_type="601", type="supplier", id_user=1, created_by=1,
            ))
            for id_proyect in (PROYECTO_A, PROYECTO_B):
                db.add(Proyect(
                    id_proyect=id_proyect, id_customer_supplier=1, leader=1,
                    proyect_description=f"Proyecto {id_proyect}", created_by=1,
                ))
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.ids = dict(db.execute(select(KpiDefinition.clave, KpiDefinition.id_kpi_definition)).all())

    def _consultar(self, clave, fecha_inicio=D1, fecha_fin=D3, **params):
        params.update(id_kpi_definition=self.ids[clave], fecha_inicio=fecha_inicio.isoformat(), fecha_fin=fecha_fin.isoformat())
        with patch("app.utils.auth.jwt.decode", return_value=ADMIN):
            respuesta = self.client.get(
                "/kpi_snapshot/query?" + "&".join(f"{k}={v}" for k, v in params.items()),
                headers={"Authorization": "Bearer kpi-agregacion-test"},
            )
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return self.json(respuesta)["rango_a"]

    def _snapshot(self, clave, dimension_key, periodo, valor, peso=None):
        return KpiSnapshot(
            id_kpi_definition=self.ids[clave], dimension_key=dimension_key,
            periodo=periodo, valor=Decimal(str(valor)), peso=None if peso is None else Decimal(str(peso)),
        )

    def test_las_reglas_declaradas_de_los_kpis_corregidos(self):
        self.assertEqual("promedio_ponderado", AGREGACION_POR_CLAVE["desarrollo_por_empleado"])
        self.assertEqual("promedio_ponderado", AGREGACION_POR_CLAVE["incidentes_resueltos_por_empleado"])
        self.assertEqual("promedio_ponderado", AGREGACION_POR_CLAVE["tiempo_promedio_reparacion_laboratorio_por_tecnico"])
        self.assertEqual("promedio_ponderado", AGREGACION_POR_CLAVE["costo_promedio_reparacion_laboratorio_por_tecnico"])
        self.assertEqual("ultimo", AGREGACION_POR_CLAVE["articulos_bajo_stock"])
        self.assertEqual("suma", AGREGACION_POR_CLAVE["ventas_por_empleado"])

    # --- promedio_ponderado -------------------------------------------------

    def _sembrar_ponderado(self):
        clave = "desarrollo_por_empleado"
        with transaction_context() as db:
            db.add_all([
                self._snapshot(clave, {"id_proyect": PROYECTO_A, "id_user": EMPLEADO_A}, D1, 100, peso=1),
                self._snapshot(clave, {"id_proyect": PROYECTO_A, "id_user": EMPLEADO_A}, D2, 25, peso=4),
                self._snapshot(clave, {"id_proyect": PROYECTO_B, "id_user": EMPLEADO_A}, D1, 50, peso=2),
                self._snapshot(clave, {"id_proyect": PROYECTO_A, "id_user": EMPLEADO_B}, D2, 0, peso=3),
                # Fila con la forma vieja (sin peso): no se puede ponderar y
                # se ignora, en vez de colarse como un 90 % mas.
                self._snapshot(clave, {"id_proyect": PROYECTO_A, "id_user": EMPLEADO_SIN_PESO}, D2, 90),
            ])
        return clave

    def test_promedio_ponderado_por_entidad_y_total(self):
        resultado = self._consultar(self._sembrar_ponderado())

        # A: (100*1 + 25*4 + 50*2) / (1+4+2) = 300/7; B: 0/3.
        self.assertAlmostEqual(300 / 7, resultado["por_empleado"][str(EMPLEADO_A)], places=6)
        self.assertEqual(0.0, resultado["por_empleado"][str(EMPLEADO_B)])
        self.assertNotIn(str(EMPLEADO_SIN_PESO), resultado["por_empleado"])
        # Total: se recombinan numeradores y pesos -- 300/10 = 30 %, no la
        # suma (300/7 + 0) ni el promedio simple de los empleados.
        self.assertAlmostEqual(30.0, resultado["total"], places=6)

    def test_promedio_ponderado_por_periodo(self):
        resultado = self._consultar(self._sembrar_ponderado(), agrupar_por="periodo")

        # D1: (100*1 + 50*2) / 3; D2: (25*4 + 0*3) / 7.
        self.assertAlmostEqual(200 / 3, resultado["por_periodo"][D1.isoformat()], places=6)
        self.assertAlmostEqual(100 / 7, resultado["por_periodo"][D2.isoformat()], places=6)
        self.assertAlmostEqual(30.0, resultado["total"], places=6)

    # --- ultimo -------------------------------------------------------------

    def _sembrar_fotos(self):
        clave = "articulos_bajo_stock"
        with transaction_context() as db:
            db.add_all([
                self._snapshot(clave, {"id_product": 1}, D1, 10),
                self._snapshot(clave, {"id_product": 2}, D1, 3),
                self._snapshot(clave, {"id_product": 3}, D1, 5),  # ya no aparece en la foto de D2
                self._snapshot(clave, {"id_product": 1}, D2, 8),
                self._snapshot(clave, {"id_product": 2}, D2, 3),
            ])
        return clave

    def test_ultimo_toma_la_foto_del_ultimo_dia_con_datos(self):
        resultado = self._consultar(self._sembrar_fotos())

        # D3 no tiene foto: vale la de D2. Sumar dias habria dado 18 y 6.
        self.assertEqual({"1": 8.0, "2": 3.0}, resultado["por_empleado"])
        self.assertEqual(11.0, resultado["total"])

    def test_ultimo_respeta_el_fin_del_rango(self):
        resultado = self._consultar(self._sembrar_fotos(), fecha_fin=D1)

        self.assertEqual({"1": 10.0, "2": 3.0, "3": 5.0}, resultado["por_empleado"])
        self.assertEqual(18.0, resultado["total"])

    def test_ultimo_por_periodo_muestra_cada_foto_y_el_total_es_la_ultima(self):
        resultado = self._consultar(self._sembrar_fotos(), agrupar_por="periodo")

        self.assertEqual({D1.isoformat(): 18.0, D2.isoformat(): 11.0}, resultado["por_periodo"])
        self.assertEqual(11.0, resultado["total"])

    def test_ultimo_sin_datos_en_el_rango_es_cero(self):
        resultado = self._consultar(self._sembrar_fotos(), fecha_inicio=D3, fecha_fin=D3)

        self.assertEqual(0.0, resultado["total"])
        self.assertEqual({}, resultado["por_empleado"])

    # --- de punta a punta: datos reales + corridas nocturnas ----------------

    def test_desarrollo_de_punta_a_punta_con_varias_noches(self):
        # A: D1 1 de 1 terminada, D2 1 de 4, D3 0 de 1 -> 2 de 6 = 33.33 %.
        tareas = [(D1, "terminada"), (D2, "terminada"), (D2, "pendiente"), (D2, "pendiente"),
                  (D2, "bloqueada"), (D3, "en_proceso")]
        with transaction_context() as db:
            for dia, estatus in tareas:
                db.add(Task(
                    owner=EMPLEADO_A, dependency=0, validation=1, task_description="agregacion",
                    task_status=estatus, id_proyect=PROYECTO_A, created_by=1,
                    creation_date=datetime.combine(dia, datetime.min.time()) + timedelta(hours=9),
                ))
        # Tres noches, cada una con su ventana de 7 dias, igual que
        # recalculate_kpi_snapshots en produccion.
        for noche in (D1, D2, D3):
            with transaction_context() as db:
                _recalcular_kpi_snapshots_en_sesion(db, noche - timedelta(days=VENTANA_DIAS - 1), noche)

        resultado = self._consultar("desarrollo_por_empleado")

        self.assertAlmostEqual(100 * 2 / 6, resultado["por_empleado"][str(EMPLEADO_A)], places=6)
        self.assertAlmostEqual(100 * 2 / 6, resultado["total"], places=6)
