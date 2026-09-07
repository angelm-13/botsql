from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, KpiDashboard, KpiDefinition, KpiSnapshot, Level,
    NmPermissionKpi, Permission, Proyect, Status, Subdepartment, User,
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


ACTOR_A = {"id_user": 980, "id_permission": 980, "id_proyect": 980}
ACTOR_B = {"id_user": 981, "id_permission": 981, "id_proyect": 981}


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestKpiDashboardApi(BackendTestCase):
    """kpi_dashboard / kpi_dashboard_widget: privados por dueno, sin excepcion.

    A diferencia de invoice (donde el superusuario ve todos los proyectos),
    aqui ni Administrator ve el tablero de otra persona -- es la regla de
    diseno del modulo, y `test_superuser_cannot_see_a_foreign_dashboard` la
    confirma explicitamente porque es la excepcion al resto del sistema.
    """

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
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
                id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=1,
                id_status=1, supervisor=1, user_type="admin", username="kpi-dash-admin",
            ))
            db.add(CustomerSupplier(
                id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                fiscal_type="601", type="supplier", id_user=1, created_by=1,
            ))
            db.add(Proyect(id_proyect=1, id_customer_supplier=1, leader=1, proyect_description="Default", created_by=1))
            # El modulo "kpis" (guardia de kpi_dashboard/kpi_dashboard_widget)
            # concedido a los dos actores no-admin: la propiedad, no el
            # modulo, es lo que se prueba aqui.
            db.add_all([
                EntityPermission(id_permission=980, entity_name="kpi_dashboard", control_type=15, created_by=1),
                EntityPermission(id_permission=980, entity_name="kpi_dashboard_widget", control_type=15, created_by=1),
                EntityPermission(id_permission=981, entity_name="kpi_dashboard", control_type=15, created_by=1),
                EntityPermission(id_permission=981, entity_name="kpi_dashboard_widget", control_type=15, created_by=1),
            ])

        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.id_kpi = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )
            # Solo ACTOR_A tiene permiso puntual sobre el KPI. ACTOR_B tiene
            # el modulo de tableros pero no este KPI -- y ADMIN nunca lo
            # necesita, por ser superusuario.
            db.add(NmPermissionKpi(id_permission=980, id_kpi_definition=self.id_kpi, control_type=15, created_by=1))

    def _request(self, actor, method, path, payload=None):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(
                path, method=method, json=payload, headers={"Authorization": "Bearer kpi-dash-test"},
            )

    def _crear_tablero(self, actor, nombre="Mi tablero"):
        response = self._request(actor, "POST", "/kpi_dashboard/", {"nombre": nombre})
        self.assertEqual(201, response.status_code, self.json(response))
        return self.json(response)["id_kpi_dashboard"]

    def test_actor_can_create_own_dashboard_and_widget(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        listado = self._request(ACTOR_A, "GET", "/kpi_dashboard/")
        self.assertEqual(200, listado.status_code)
        self.assertEqual([id_dashboard], [d["id_kpi_dashboard"] for d in self.json(listado)["items"]])

        widget = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "id_kpi_definition": self.id_kpi, "tipo_grafica": "barras",
        })
        self.assertEqual(201, widget.status_code, self.json(widget))
        id_widget = self.json(widget)["id_kpi_dashboard_widget"]

        widgets = self._request(ACTOR_A, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/")
        self.assertEqual([id_widget], [w["id_kpi_dashboard_widget"] for w in self.json(widgets)["items"]])

    def test_another_actor_with_the_module_cannot_reach_a_foreign_dashboard(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        self.assertEqual(
            404, self._request(ACTOR_B, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/").status_code,
        )
        self.assertEqual(
            404, self._request(ACTOR_B, "PUT", f"/kpi_dashboard/{id_dashboard}", {"nombre": "Intrusion"}).status_code,
        )
        self.assertEqual(
            404, self._request(ACTOR_B, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
                "id_kpi_definition": self.id_kpi, "tipo_grafica": "barras",
            }).status_code,
        )
        self.assertEqual(404, self._request(ACTOR_B, "DELETE", f"/kpi_dashboard/{id_dashboard}").status_code)

    def test_superuser_cannot_see_a_foreign_dashboard(self):
        """La excepcion a como se comporta el resto del sistema.

        InvoiceService.actor_project regresa None para el superusuario, que
        entonces ve todos los proyectos. kpi_dashboard NO tiene ese `None`:
        el filtro `id_user == actor` se aplica siempre, y para Administrator
        `actor` es su propio id_user (1), no un comodin.
        """
        id_dashboard = self._crear_tablero(ACTOR_A)

        self.assertEqual(
            404, self._request(ADMIN, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/").status_code,
        )
        self.assertEqual(
            404, self._request(ADMIN, "PUT", f"/kpi_dashboard/{id_dashboard}", {"nombre": "Intrusion"}).status_code,
        )
        self.assertEqual(404, self._request(ADMIN, "DELETE", f"/kpi_dashboard/{id_dashboard}").status_code)
        # Y el propio tablero de ADMIN sigue vacio: no hereda ni ve el de A.
        propio = self._request(ADMIN, "GET", "/kpi_dashboard/")
        self.assertEqual([], self.json(propio)["items"])

    def test_creating_widget_without_kpi_permission_fails(self):
        id_dashboard = self._crear_tablero(ACTOR_B)

        response = self._request(ACTOR_B, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "id_kpi_definition": self.id_kpi, "tipo_grafica": "barras",
        })

        self.assertEqual(403, response.status_code)

    def test_invalid_chart_type_is_rejected(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        response = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "id_kpi_definition": self.id_kpi, "tipo_grafica": "pastel",
        })

        self.assertEqual(400, response.status_code)

    def test_delete_dashboard_is_a_soft_delete(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        self.assertEqual(200, self._request(ACTOR_A, "DELETE", f"/kpi_dashboard/{id_dashboard}").status_code)

        listado = self._request(ACTOR_A, "GET", "/kpi_dashboard/")
        self.assertEqual([], self.json(listado)["items"])
        with transaction_context() as db:
            fila = db.get(KpiDashboard, id_dashboard)
            self.assertIsNotNone(fila, "la fila sigue existiendo: es baja logica, no fisica")
            self.assertIsNotNone(fila.deletion_date)


if __name__ == "__main__":
    unittest.main()
