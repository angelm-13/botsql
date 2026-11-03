"""POST /kpi_dashboard/<id>/recalcular: recalculo bajo demanda de los indicadores de un tablero.

Postgres: usa el candado de asesoria y `kpi_snapshot`, que en SQLite no existen (mismo criterio que test_api_kpi.py).
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, KpiDefinition, KpiSnapshot, Level, NmPermissionKpi, Permission,
    Proyect, Status, Subdepartment, User,
)
from app.models.session import engine, transaction_context
from app.utils.tiempo import ahora_utc, hoy_negocio
from tests.conftest import BackendTestCase

ACTOR_A = {"id_user": 980, "id_permission": 980, "id_proyect": 980}
ACTOR_B = {"id_user": 981, "id_permission": 981, "id_proyect": 981}
LLAVE_DEL_CANDADO = 7_210_000


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestRecalculoDeTablero(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            db.add(Permission(id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
                              id_department=1, id_subdepartment=1, id_level=1))
            db.add(User(id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=1, id_status=1,
                        supervisor=1, user_type="admin", username="kpi-recalculo-admin"))
            db.add(CustomerSupplier(id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                                    fiscal_type="601", type="supplier", id_user=1, created_by=1))
            db.add(Proyect(id_proyect=1, id_customer_supplier=1, leader=1, proyect_description="Default", created_by=1))
            for rol in (980, 981):
                for entidad in ("kpi_dashboard", "kpi_dashboard_widget"):
                    db.add(EntityPermission(id_permission=rol, entity_name=entidad, scope_create=4, scope_read=4,
                                            scope_update=4, scope_delete=4, created_by=1))
        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.id_kpi = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado"))
            self.id_kpi_otro = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "egresos_por_empleado"))
            db.add(NmPermissionKpi(id_permission=980, id_kpi_definition=self.id_kpi, puede_ver=True, created_by=1))
        self.id_tablero = self._crear_tablero(ACTOR_A)
        self._crear_widget(ACTOR_A, self.id_tablero, [self.id_kpi])

    def _request(self, actor, method, path, payload=None):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(path, method=method, json=payload, headers={"Authorization": "Bearer kpi-recalculo-test"})

    def _crear_tablero(self, actor):
        respuesta = self._request(actor, "POST", "/kpi_dashboard/", {"nombre": "Tablero"})
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        return self.json(respuesta)["id_kpi_dashboard"]

    def _crear_widget(self, actor, id_tablero, ids):
        respuesta = self._request(actor, "POST", f"/kpi_dashboard/{id_tablero}/widgets/", {"ids_kpi_definition": ids, "tipo_grafica": "barras"})
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))

    def _recalcular(self, actor, items, id_tablero=None):
        return self._request(actor, "POST", f"/kpi_dashboard/{id_tablero or self.id_tablero}/recalcular", {"items": items})

    @staticmethod
    def _item(id_kpi, inicio, fin):
        return {"id_kpi_definition": id_kpi, "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()}

    def _snapshot_con_computed_at(self, computed_at):
        with transaction_context() as db:
            db.add(KpiSnapshot(id_kpi_definition=self.id_kpi, dimension_key={"id_user": 950, "id_proyect": 1},
                               periodo=hoy_negocio(), valor=Decimal("1.00"), computed_at=computed_at))

    def test_the_owner_recalculates_a_visible_indicator_over_the_range_asked_even_when_older_than_seven_days(self):
        hoy = hoy_negocio()
        inicio = hoy - timedelta(days=40)
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves", return_value=3) as recalculo:
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, inicio, hoy)])
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        cuerpo = self.json(respuesta)
        self.assertEqual([self.id_kpi], cuerpo["actualizados"])
        self.assertEqual([], cuerpo["ya_al_dia"] + cuerpo["omitidos"])
        self.assertTrue(cuerpo["recalculado_en"].endswith("Z"))
        _, inicio_usado, fin_usado, claves = recalculo.call_args.args
        self.assertEqual((inicio, hoy, ["ventas_por_empleado"]), (inicio_usado, fin_usado, claves))

    def test_an_end_date_in_the_future_is_clipped_to_today(self):
        hoy = hoy_negocio()
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves", return_value=0) as recalculo:
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy, hoy + timedelta(days=5))])
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        self.assertEqual(hoy, recalculo.call_args.args[2])

    def test_it_really_writes_through_the_job_logic(self):
        hoy = hoy_negocio()
        respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy - timedelta(days=3), hoy)])
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        self.assertEqual([self.id_kpi], self.json(respuesta)["actualizados"])

    def test_an_indicator_calculated_less_than_a_minute_ago_is_already_up_to_date(self):
        self._snapshot_con_computed_at(ahora_utc() - timedelta(seconds=10))
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves") as recalculo:
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy_negocio() - timedelta(days=5), hoy_negocio())])
        self.assertEqual([self.id_kpi], self.json(respuesta)["ya_al_dia"])
        self.assertEqual([], self.json(respuesta)["actualizados"])
        recalculo.assert_not_called()

    def test_an_indicator_calculated_ten_minutes_ago_is_recalculated(self):
        self._snapshot_con_computed_at(ahora_utc() - timedelta(minutes=10))
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves", return_value=1):
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy_negocio() - timedelta(days=5), hoy_negocio())])
        self.assertEqual([self.id_kpi], self.json(respuesta)["actualizados"])

    def test_someone_elses_dashboard_is_a_404(self):
        respuesta = self._recalcular(ACTOR_B, [self._item(self.id_kpi, hoy_negocio(), hoy_negocio())])
        self.assertEqual(404, respuesta.status_code)

    def test_an_indicator_that_is_not_on_the_dashboard_is_skipped(self):
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves") as recalculo:
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi_otro, hoy_negocio(), hoy_negocio())])
        self.assertEqual([{"id_kpi_definition": self.id_kpi_otro, "motivo": "no_esta_en_el_tablero"}], self.json(respuesta)["omitidos"])
        recalculo.assert_not_called()

    def test_an_indicator_the_actor_can_no_longer_see_is_skipped(self):
        with transaction_context() as db:
            db.execute(text("DELETE FROM nm_permission_kpi WHERE id_kpi_definition = :i"), {"i": self.id_kpi})
        with patch("app.jobs.tasks_kpis.recalcular_kpi_snapshots_de_claves") as recalculo:
            respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy_negocio(), hoy_negocio())])
        self.assertEqual("sin_permiso", self.json(respuesta)["omitidos"][0]["motivo"])
        recalculo.assert_not_called()

    def test_a_range_longer_than_a_year_is_rejected(self):
        hoy = hoy_negocio()
        respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy - timedelta(days=400), hoy)])
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.rango_excede_limite", self.json(respuesta)["error_key"])

    def test_invalid_bodies_are_400(self):
        for items in (None, [], "x", [{"id_kpi_definition": "a", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-02"}],
                      [{"id_kpi_definition": self.id_kpi, "fecha_inicio": "no", "fecha_fin": "2026-01-02"}],
                      [self._item(self.id_kpi, date(2026, 2, 1), date(2026, 1, 1))]):
            with self.subTest(items=items):
                self.assertEqual(400, self._recalcular(ACTOR_A, items).status_code)

    def test_a_second_recalculation_at_the_same_time_gets_409(self):
        with engine.connect() as otra_conexion:
            otra_conexion.execute(text("SELECT pg_advisory_lock(:k)"), {"k": LLAVE_DEL_CANDADO + self.id_tablero})
            try:
                respuesta = self._recalcular(ACTOR_A, [self._item(self.id_kpi, hoy_negocio(), hoy_negocio())])
            finally:
                otra_conexion.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LLAVE_DEL_CANDADO + self.id_tablero})
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("kpis.recalculation_in_progress", self.json(respuesta)["error_key"])
