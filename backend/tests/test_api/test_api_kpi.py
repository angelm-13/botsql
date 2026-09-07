from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, KpiDefinition, KpiSnapshot, Level, NmPermissionKpi,
    Permission, Proyect, Status, Subdepartment, User,
)
from app.models.session import engine, transaction_context
from tests.conftest import BackendTestCase

# Se prueba contra PostgreSQL real, no SQLite: `/kpi_snapshot/query` filtra
# `dimension_key` con `cast(..., JSONB).contains(...)`, exclusivo del
# dialecto de Postgres (ver el comentario en app/models/kpi_snapshot.py).
ADMIN = {"id_user": 1, "is_superuser": True}
ACTOR_CON_KPI = {"id_user": 970, "id_permission": 970, "id_proyect": 970}
ACTOR_SIN_KPI_ESPECIFICO = {"id_user": 972, "id_permission": 972, "id_proyect": 972}
ACTOR_SIN_MODULO = {"id_user": 971, "id_permission": 971, "id_proyect": 971}

PROYECTO_A = 970
PROYECTO_B = 972


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestKpiApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            # user <-> customer_supplier <-> proyect se referencian en circulo
            # (User.id_proyect, CustomerSupplier.id_user, Proyect.leader/
            # id_customer_supplier), y las FK de app/models/__init__.py son
            # DEFERRABLE INITIALLY IMMEDIATE -- se comprueban en cada
            # sentencia salvo que la transaccion pida aplazarlas, que es
            # justo lo que hace `seed.sql` para poder sembrar este mismo
            # ciclo. Sin esto, cualquier orden de INSERT revienta.
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Status(id_status=1, status_description="Activo", category="general", is_terminal=False, sort_order="asc", created_by=1))
            db.add(Department(id_department=1, department_description="General", created_by=1))
            db.add(Subdepartment(id_subdepartment=1, subdepartment_description="General", id_department=1, created_by=1))
            db.add(Level(id_level=1, level_description="General", created_by=1))
            db.add(Permission(
                id_permission=1, permission_description="Admin", created_by=1, authorized_by=1,
                id_department=1, id_subdepartment=1, id_level=1,
            ))
            db.add(User(
                id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="admin", username="kpi-api-admin",
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
            # `kpi_definition` concedido (el guardia de modulo) a los
            # permisos 970 y 972; 971 se queda sin el, a proposito.
            db.add_all([
                EntityPermission(id_permission=970, entity_name="kpi_definition", control_type=15, created_by=1),
                EntityPermission(id_permission=972, entity_name="kpi_definition", control_type=15, created_by=1),
            ])

        seed_kpi_definitions(engine)

        with transaction_context() as db:
            self.id_kpi = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )
            # Solo 970 recibe el permiso puntual sobre el KPI (nm_permission_kpi):
            # 972 tiene el modulo pero no este KPI en particular.
            db.add(NmPermissionKpi(id_permission=970, id_kpi_definition=self.id_kpi, control_type=15, created_by=1))
            db.add_all([
                KpiSnapshot(
                    id_kpi_definition=self.id_kpi, dimension_key={"id_user": 950, "id_proyect": PROYECTO_A},
                    periodo=date(2026, 4, 1), valor=Decimal("1000.00"),
                ),
                KpiSnapshot(
                    id_kpi_definition=self.id_kpi, dimension_key={"id_user": 951, "id_proyect": PROYECTO_A},
                    periodo=date(2026, 4, 2), valor=Decimal("500.00"),
                ),
                # Mismo empleado y mismo dia, pero en OTRO proyecto: no debe
                # mezclarse con el total de PROYECTO_A.
                KpiSnapshot(
                    id_kpi_definition=self.id_kpi, dimension_key={"id_user": 950, "id_proyect": PROYECTO_B},
                    periodo=date(2026, 4, 1), valor=Decimal("9999.00"),
                ),
            ])

    def _request(self, actor, path):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.get(path, headers={"Authorization": "Bearer kpi-api-test"})

    def _query_url(self, **params):
        params.setdefault("id_kpi_definition", self.id_kpi)
        params.setdefault("fecha_inicio", "2026-04-01")
        params.setdefault("fecha_fin", "2026-04-02")
        return "/kpi_snapshot/query?" + "&".join(f"{k}={v}" for k, v in params.items())

    def test_catalog_only_shows_kpis_with_permission_granted(self):
        con_permiso = self._request(ACTOR_CON_KPI, "/kpi_definition/")
        self.assertEqual(200, con_permiso.status_code)
        claves = [item["clave"] for item in self.json(con_permiso)["items"]]
        self.assertIn("ventas_por_empleado", claves)

        sin_permiso_puntual = self._request(ACTOR_SIN_KPI_ESPECIFICO, "/kpi_definition/")
        self.assertEqual(200, sin_permiso_puntual.status_code)
        self.assertEqual([], self.json(sin_permiso_puntual)["items"], "tiene el modulo pero no el KPI")

    def test_query_snapshot_respects_actor_project(self):
        response = self._request(ACTOR_CON_KPI, self._query_url())

        self.assertEqual(200, response.status_code)
        payload = self.json(response)
        self.assertIsNone(payload["rango_b"])
        self.assertEqual(1500.0, payload["rango_a"]["total"])
        self.assertEqual({"950": 1000.0, "951": 500.0}, payload["rango_a"]["por_empleado"])

    def test_query_snapshot_empleados_filter(self):
        response = self._request(ACTOR_CON_KPI, self._query_url(empleados="950"))

        payload = self.json(response)["rango_a"]
        self.assertEqual({"950": 1000.0}, payload["por_empleado"])
        self.assertEqual(1000.0, payload["total"])

    def test_query_snapshot_denied_without_specific_kpi_permission(self):
        response = self._request(ACTOR_SIN_KPI_ESPECIFICO, self._query_url())

        self.assertEqual(403, response.status_code)

    def test_actor_without_module_gets_403_on_both_routes(self):
        for path in ("/kpi_definition/", self._query_url()):
            with self.subTest(path=path):
                self.assertEqual(403, self._request(ACTOR_SIN_MODULO, path).status_code)

    def test_superuser_without_project_scope_sees_every_project(self):
        response = self._request(ADMIN, self._query_url())

        payload = self.json(response)["rango_a"]
        self.assertEqual(11499.0, payload["total"])
        self.assertEqual({"950": 10999.0, "951": 500.0}, payload["por_empleado"])


if __name__ == "__main__":
    unittest.main()
