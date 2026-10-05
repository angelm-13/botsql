from __future__ import annotations

import os
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
from app.modules.plan import reiniciar_plan
from app.utils.auth import has_kpi_permission
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
                EntityPermission(id_permission=970, entity_name="kpi_definition", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=972, entity_name="kpi_definition", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
            ])

        seed_kpi_definitions(engine)

        with transaction_context() as db:
            self.id_kpi = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )
            # Solo 970 recibe el permiso puntual sobre el KPI (nm_permission_kpi):
            # 972 tiene el modulo pero no este KPI en particular.
            db.add(NmPermissionKpi(id_permission=970, id_kpi_definition=self.id_kpi, puede_ver=True, created_by=1))
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
        items = self.json(con_permiso)["items"]
        claves = [item["clave"] for item in items]
        self.assertIn("ventas_por_empleado", claves)
        # El front necesita el id (no solo la clave) para armar el payload
        # de creacion de widget: `POST .../widgets/` exige `id_kpi_definition`.
        fila = next(item for item in items if item["clave"] == "ventas_por_empleado")
        self.assertEqual(self.id_kpi, fila["id_kpi_definition"])
        # Metadatos que solo viven en KPI_REGISTRY (en memoria, nunca
        # migrados a la tabla kpi_definition) -- el frontend los necesita
        # para el rediseno del dashboard, sin que haga falta ninguna
        # migracion para exponerlos.
        self.assertEqual("alto_es_mejor", fila["direccion"])
        self.assertEqual("snapshot", fila["modo"])
        self.assertIn(fila["grafica_default"], fila["graficas_permitidas"])
        self.assertIsNone(fila["colores_categoria"])

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

    def test_has_kpi_permission_denies_without_a_row(self):
        # 972 tiene el modulo (kpi_definition) pero ninguna fila en
        # nm_permission_kpi para este KPI puntual -- fail-closed.
        with transaction_context() as db:
            self.assertFalse(has_kpi_permission(db, ACTOR_SIN_KPI_ESPECIFICO, self.id_kpi))

    def test_has_kpi_permission_allows_with_puede_ver_true(self):
        # 970 (setUp) ya tiene una fila con puede_ver=True para este KPI.
        with transaction_context() as db:
            self.assertTrue(has_kpi_permission(db, ACTOR_CON_KPI, self.id_kpi))

    def test_has_kpi_permission_denies_with_puede_ver_false(self):
        actor = {"id_user": 973, "id_permission": 973, "id_proyect": 973}
        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=973, entity_name="kpi_definition",
                scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1,
            ))
            db.add(NmPermissionKpi(id_permission=973, id_kpi_definition=self.id_kpi, puede_ver=False, created_by=1))

        with transaction_context() as db:
            self.assertFalse(has_kpi_permission(db, actor, self.id_kpi))

    def test_superuser_without_project_scope_sees_every_project(self):
        response = self._request(ADMIN, self._query_url())

        payload = self.json(response)["rango_a"]
        self.assertEqual(11499.0, payload["total"])
        self.assertEqual({"950": 10999.0, "951": 500.0}, payload["por_empleado"])

    def test_query_snapshot_rejects_range_over_one_year(self):
        response = self._request(
            ACTOR_CON_KPI, self._query_url(fecha_inicio="2025-01-01", fecha_fin="2026-06-01"),
        )

        self.assertEqual(400, response.status_code)
        payload = self.json(response)
        self.assertEqual("errors.rango_excede_limite", payload["error_key"])
        self.assertEqual(365, payload["meta"]["dias_maximo"])

    def test_query_snapshot_respects_plan_configured_range_limit(self):
        # Un limite mas estricto que el default (30 dias en vez de 365): si la
        # ruta siguiera usando el 365 fijo, el rango de 40 dias pasaria.
        with patch.dict(os.environ, {"TYAKXA_PLAN": '{"limites": {"kpi_rango_dias_max": 30}}'}):
            reiniciar_plan()
            try:
                dentro_del_limite = self._request(
                    ACTOR_CON_KPI, self._query_url(fecha_inicio="2026-01-01", fecha_fin="2026-01-20"),
                )
                fuera_del_limite = self._request(
                    ACTOR_CON_KPI, self._query_url(fecha_inicio="2026-01-01", fecha_fin="2026-03-01"),
                )
            finally:
                reiniciar_plan()

        self.assertEqual(200, dentro_del_limite.status_code)
        self.assertEqual(400, fuera_del_limite.status_code)
        self.assertEqual("errors.rango_excede_limite", self.json(fuera_del_limite)["error_key"])
        self.assertEqual(30, self.json(fuera_del_limite)["meta"]["dias_maximo"])

    def test_query_snapshot_filtra_por_departamento(self):
        # 950 y 951 (con snapshots ya sembrados en setUp) quedan en
        # departamentos distintos: 950 en uno nuevo ("Ventas"), 951 en el
        # mismo departamento que el admin ("General", id_department=1).
        with transaction_context() as db:
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Department(id_department=2, department_description="Ventas", created_by=1))
            db.add(Subdepartment(id_subdepartment=2, subdepartment_description="Ventas", id_department=2, created_by=1))
            db.add(Permission(
                id_permission=2, permission_description="Vendedor", created_by=1, authorized_by=1,
                id_department=2, id_subdepartment=2, id_level=1,
            ))
            db.add(User(
                id_user=950, created_by=1, full_name="Empleado 950", id_permission=2, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="employee", is_employee=True, username="kpi-dept-950",
            ))
            db.add(User(
                id_user=951, created_by=1, full_name="Empleado 951", id_permission=1, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="employee", is_employee=True, username="kpi-dept-951",
            ))

        response = self._request(ACTOR_CON_KPI, self._query_url(id_departments=2))

        payload = self.json(response)["rango_a"]
        self.assertEqual({"950": 1000.0}, payload["por_empleado"])
        self.assertEqual(1000.0, payload["total"])

    def test_query_snapshot_departamento_sin_empleados_no_trae_a_nadie(self):
        with transaction_context() as db:
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Department(id_department=3, department_description="Vacio", created_by=1))

        response = self._request(ACTOR_CON_KPI, self._query_url(id_departments=3))

        payload = self.json(response)["rango_a"]
        self.assertEqual({}, payload["por_empleado"])
        self.assertEqual(0, payload["total"])

    def test_query_snapshot_departamento_y_empleados_se_intersectan(self):
        # El departamento 2 tiene a 950 y 951, pero "empleados" solo pide 951:
        # el resultado debe ser la interseccion (solo 951), no la union.
        with transaction_context() as db:
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            db.add(Department(id_department=2, department_description="Ventas", created_by=1))
            db.add(Subdepartment(id_subdepartment=2, subdepartment_description="Ventas", id_department=2, created_by=1))
            db.add(Permission(
                id_permission=2, permission_description="Vendedor", created_by=1, authorized_by=1,
                id_department=2, id_subdepartment=2, id_level=1,
            ))
            db.add(User(
                id_user=950, created_by=1, full_name="Empleado 950", id_permission=2, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="employee", is_employee=True, username="kpi-dept-inter-950",
            ))
            db.add(User(
                id_user=951, created_by=1, full_name="Empleado 951", id_permission=2, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="employee", is_employee=True, username="kpi-dept-inter-951",
            ))

        response = self._request(ACTOR_CON_KPI, self._query_url(id_departments=2, empleados=951))

        payload = self.json(response)["rango_a"]
        self.assertEqual({"951": 500.0}, payload["por_empleado"])

    # --- KPI vivo: filtro, busqueda y orden en el servidor (ver test_kpi_material_prestado_actual_servidor) ---
    def _url_vivo(self, **params):
        with transaction_context() as db:
            id_vivo = db.scalar(select(KpiDefinition.id_kpi_definition)
                                .where(KpiDefinition.clave == "material_prestado_actual"))
        consulta = "&".join(f"{k}={v}" for k, v in params.items())
        return f"/kpi_definition/{id_vivo}/vivo" + (f"?{consulta}" if consulta else "")

    def test_vivo_responde_con_resumen_y_conteo_por_responsable(self):
        response = self._request(ADMIN, self._url_vivo(limit=5, q="zz-no-existe", orden="articulo", direccion="asc"))

        self.assertEqual(200, response.status_code, self.json(response))
        cuerpo = self.json(response)
        self.assertEqual(0, cuerpo["total"])
        self.assertEqual(0, cuerpo["resumen"]["renglones"])
        self.assertIsNone(cuerpo["resumen"]["mas_antiguo"])
        self.assertIsInstance(cuerpo["responsables"], list)

    def test_vivo_rechaza_parametros_invalidos(self):
        for parametros, campo in (
            ({"orden": "contrasena"}, "orden"),
            ({"direccion": "de_lado"}, "direccion"),
            ({"id_user": "abc"}, "id_user"),
            ({"id_user_ambito": "x"}, "id_user_ambito"),
        ):
            with self.subTest(parametros=parametros):
                response = self._request(ADMIN, self._url_vivo(**parametros))
                self.assertEqual(400, response.status_code)
                self.assertEqual(campo, self.json(response)["meta"]["field"])



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
                EntityPermission(id_permission=980, entity_name="kpi_dashboard", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=980, entity_name="kpi_dashboard_widget", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=981, entity_name="kpi_dashboard", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=981, entity_name="kpi_dashboard_widget", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
            ])

        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.id_kpi = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )
            self.id_kpi_egresos = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "egresos_por_empleado")
            )
            # Un tercer KPI real que existe en el catalogo pero sobre el que
            # ACTOR_A NUNCA recibe permiso puntual -- para probar que un
            # widget con varios KPIs se rechaza si cualquiera de la lista
            # falla, no solo si todos fallan.
            self.id_kpi_sin_permiso = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "desarrollo_por_empleado")
            )
            # Solo ACTOR_A tiene permiso puntual sobre estos dos KPIs. ACTOR_B
            # tiene el modulo de tableros pero ningun KPI -- y ADMIN nunca lo
            # necesita, por ser superusuario.
            db.add_all([
                NmPermissionKpi(id_permission=980, id_kpi_definition=self.id_kpi, puede_ver=True, created_by=1),
                NmPermissionKpi(id_permission=980, id_kpi_definition=self.id_kpi_egresos, puede_ver=True, created_by=1),
            ])

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

        # Un widget con DOS KPIs a la vez, no solo uno.
        widget = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi, self.id_kpi_egresos], "tipo_grafica": "barras",
        })
        self.assertEqual(201, widget.status_code, self.json(widget))
        cuerpo_creado = self.json(widget)
        id_widget = cuerpo_creado["id_kpi_dashboard_widget"]
        self.assertEqual([self.id_kpi, self.id_kpi_egresos], cuerpo_creado["ids_kpi_definition"])

        widgets = self._request(ACTOR_A, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/")
        items = self.json(widgets)["items"]
        self.assertEqual([id_widget], [w["id_kpi_dashboard_widget"] for w in items])
        self.assertEqual([self.id_kpi, self.id_kpi_egresos], items[0]["ids_kpi_definition"])

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
                "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "barras",
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
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "barras",
        })

        self.assertEqual(403, response.status_code)

    def test_creating_widget_fails_if_any_kpi_in_the_list_lacks_permission(self):
        """Todo o nada: un solo KPI sin permiso en la lista tira todo el alta.

        ACTOR_A si tiene permiso sobre `self.id_kpi`, pero no sobre
        `self.id_kpi_sin_permiso` -- mezclados en la misma lista, la
        respuesta debe ser 403 y no debe quedar ningun widget creado.
        """
        id_dashboard = self._crear_tablero(ACTOR_A)

        response = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi, self.id_kpi_sin_permiso], "tipo_grafica": "barras",
        })

        self.assertEqual(403, response.status_code)
        widgets = self._request(ACTOR_A, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/")
        self.assertEqual([], self.json(widgets)["items"], "no debio quedar ningun widget a medias")

    def test_invalid_chart_type_is_rejected(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        response = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "pastel",
        })

        self.assertEqual(400, response.status_code)

    def test_a_table_widget_can_be_saved(self):
        # "tabla" es el tipo del KPI "vivo" (material_prestado_actual). Sin
        # aceptarlo aqui el editor del Dashboard no podia guardar ese widget.
        id_dashboard = self._crear_tablero(ACTOR_A)

        response = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "tabla",
        })

        self.assertEqual(201, response.status_code, self.json(response))
        self.assertEqual("tabla", self.json(response)["tipo_grafica"])

    def test_update_widget_replaces_the_full_kpi_list_and_keeps_order(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        creado = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "numero",
        })
        id_widget = self.json(creado)["id_kpi_dashboard_widget"]

        # Agregar un KPI y reordenar: el segundo pasa a ir primero.
        actualizado = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {
            "ids_kpi_definition": [self.id_kpi_egresos, self.id_kpi],
        })
        self.assertEqual(200, actualizado.status_code, self.json(actualizado))
        self.assertEqual([self.id_kpi_egresos, self.id_kpi], self.json(actualizado)["ids_kpi_definition"])

        widgets = self._request(ACTOR_A, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/")
        self.assertEqual(
            [self.id_kpi_egresos, self.id_kpi], self.json(widgets)["items"][0]["ids_kpi_definition"],
        )

        # Quitar uno: la lista se reemplaza por completo, no se acumula.
        recortado = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {
            "ids_kpi_definition": [self.id_kpi],
        })
        self.assertEqual(200, recortado.status_code, self.json(recortado))
        self.assertEqual([self.id_kpi], self.json(recortado)["ids_kpi_definition"])

    def test_update_widget_without_touching_kpis_keeps_the_existing_list(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        creado = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi, self.id_kpi_egresos], "tipo_grafica": "numero",
        })
        id_widget = self.json(creado)["id_kpi_dashboard_widget"]

        actualizado = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {
            "tipo_grafica": "barras",
        })

        self.assertEqual(200, actualizado.status_code, self.json(actualizado))
        self.assertEqual("barras", self.json(actualizado)["tipo_grafica"])
        self.assertEqual([self.id_kpi, self.id_kpi_egresos], self.json(actualizado)["ids_kpi_definition"])

    # --- orden de la tabla de "Material prestado ahora": parametros.orden_tabla ---
    def _crear_widget_tabla(self, actor, id_dashboard, parametros=None):
        cuerpo = {"ids_kpi_definition": [self.id_kpi], "tipo_grafica": "tabla"}
        if parametros is not None:
            cuerpo["parametros"] = parametros
        respuesta = self._request(actor, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", cuerpo)
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        return self.json(respuesta)["id_kpi_dashboard_widget"]

    def _parametros_de(self, actor, id_dashboard, id_widget):
        items = self.json(self._request(actor, "GET", f"/kpi_dashboard/{id_dashboard}/widgets/"))["items"]
        return next(w for w in items if w["id_kpi_dashboard_widget"] == id_widget)["parametros"]

    def test_el_orden_de_la_tabla_se_guarda_y_se_fusiona_sin_pisar_el_resto_de_parametros(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        id_widget = self._crear_widget_tabla(ACTOR_A, id_dashboard, {"columnas": 2, "filas": 2})

        respuesta = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla",
                                  {"campo": "fecha_prestamo", "direccion": "asc"})

        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        self.assertEqual(
            {"columnas": 2, "filas": 2, "orden_tabla": {"campo": "fecha_prestamo", "direccion": "asc"}},
            self._parametros_de(ACTOR_A, id_dashboard, id_widget),
        )
        # Un segundo guardado reemplaza solo el orden.
        self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla",
                      {"campo": "dias_prestado", "direccion": "desc"})
        self.assertEqual(
            {"columnas": 2, "filas": 2, "orden_tabla": {"campo": "dias_prestado", "direccion": "desc"}},
            self._parametros_de(ACTOR_A, id_dashboard, id_widget),
        )

    def test_un_cambio_hecho_en_otra_pestana_no_se_pisa_al_guardar_el_orden(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        id_widget = self._crear_widget_tabla(ACTOR_A, id_dashboard, {"columnas": 1})
        # "Otra pestana" cambia el tamano despues de que esta ya cargo el widget...
        self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {"parametros": {"columnas": 2, "filas": 2}})
        # ...y esta guarda SOLO el orden: el servidor fusiona con lo que hay ahora, no con lo que esta leyo.
        self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla",
                      {"campo": "articulo", "direccion": "asc"})
        self.assertEqual(
            {"columnas": 2, "filas": 2, "orden_tabla": {"campo": "articulo", "direccion": "asc"}},
            self._parametros_de(ACTOR_A, id_dashboard, id_widget),
        )

    def test_un_orden_invalido_se_rechaza_y_no_cambia_lo_guardado(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        id_widget = self._crear_widget_tabla(ACTOR_A, id_dashboard, {"orden_tabla": {"campo": "articulo", "direccion": "asc"}})
        invalidos = [
            {"campo": "id_user", "direccion": "asc"},          # fuera de PRESTADO_ORDENES
            {"campo": "articulo", "direccion": "arriba"},      # direccion que no es asc/desc
            {"campo": "articulo"},                             # incompleto
            {"campo": "articulo", "direccion": "asc", "x": 1}, # clave de mas
            {"campo": ["articulo"], "direccion": "asc"},
            "articulo", None, [], 7,
        ]
        for valor in invalidos:
            with self.subTest(valor=valor):
                respuesta = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla", valor)
                self.assertEqual(400, respuesta.status_code, self.json(respuesta))
        self.assertEqual(
            {"orden_tabla": {"campo": "articulo", "direccion": "asc"}},
            self._parametros_de(ACTOR_A, id_dashboard, id_widget),
        )

    def test_orden_tabla_invalido_tambien_se_rechaza_al_crear_o_editar_el_widget(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        malo = {"orden_tabla": {"campo": "nada", "direccion": "asc"}}
        creado = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "tabla", "parametros": malo,
        })
        self.assertEqual(400, creado.status_code)
        id_widget = self._crear_widget_tabla(ACTOR_A, id_dashboard)
        self.assertEqual(400, self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {"parametros": malo}).status_code)
        # Y uno valido pasa por el editor sin problema.
        bueno = {"orden_tabla": {"campo": "responsable", "direccion": "desc"}}
        self.assertEqual(200, self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}", {"parametros": bueno}).status_code)
        self.assertEqual(bueno, self._parametros_de(ACTOR_A, id_dashboard, id_widget))

    def test_el_orden_solo_aplica_a_widgets_de_tabla(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        creado = self._request(ACTOR_A, "POST", f"/kpi_dashboard/{id_dashboard}/widgets/", {
            "ids_kpi_definition": [self.id_kpi], "tipo_grafica": "barras",
        })
        id_widget = self.json(creado)["id_kpi_dashboard_widget"]
        respuesta = self._request(ACTOR_A, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla",
                                  {"campo": "articulo", "direccion": "asc"})
        self.assertEqual(400, respuesta.status_code)

    def test_el_orden_de_un_widget_ajeno_es_404_y_sin_permiso_de_actualizar_es_403(self):
        id_dashboard = self._crear_tablero(ACTOR_A)
        id_widget = self._crear_widget_tabla(ACTOR_A, id_dashboard)
        orden = {"campo": "articulo", "direccion": "asc"}
        self.assertEqual(404, self._request(ACTOR_B, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla", orden).status_code)
        sin_permiso = {"id_user": 982, "id_permission": 982, "id_proyect": 982}
        self.assertEqual(403, self._request(sin_permiso, "PUT", f"/kpi_dashboard_widget/{id_widget}/orden_tabla", orden).status_code)
        self.assertEqual({}, self._parametros_de(ACTOR_A, id_dashboard, id_widget))

    def test_delete_dashboard_is_a_soft_delete(self):
        id_dashboard = self._crear_tablero(ACTOR_A)

        self.assertEqual(200, self._request(ACTOR_A, "DELETE", f"/kpi_dashboard/{id_dashboard}").status_code)

        listado = self._request(ACTOR_A, "GET", "/kpi_dashboard/")
        self.assertEqual([], self.json(listado)["items"])
        with transaction_context() as db:
            fila = db.get(KpiDashboard, id_dashboard)
            self.assertIsNotNone(fila, "la fila sigue existiendo: es baja logica, no fisica")
            self.assertIsNotNone(fila.deletion_date)


ACTOR_ADMINISTRA_PERMISOS_KPI = {"id_user": 990, "id_permission": 990, "user_type": "admin"}
ACTOR_SIN_PERMISO_DE_ADMINISTRAR_KPI = {"id_user": 991, "id_permission": 991}


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestPermissionKpiAdminApi(BackendTestCase):
    """`/kpi_definition/all` y `/permission_kpi`: la pantalla que reparte que
    rol ve que KPI. Protegidas con el permiso de administrar
    `nm_permission_kpi` como entidad -- el mismo criterio que ya protege la
    administracion de `entity_permission`/`nm_field_permission` -- y no con
    el permiso puntual de cada KPI (`has_kpi_permission`), que es el que
    filtra el catalogo para un usuario comun en `/kpi_definition/`.
    """

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=990, entity_name="nm_permission_kpi",
                scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1,
            ))
            # 991 no recibe nada sobre nm_permission_kpi -- solo existe para
            # probar el 403.

        seed_kpi_definitions(engine)
        with transaction_context() as db:
            self.id_kpi = db.scalar(
                select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "ventas_por_empleado")
            )

    def _request(self, actor, method, path, payload=None):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(
                path, method=method, json=payload, headers={"Authorization": "Bearer permission-kpi-test"},
            )

    def test_list_all_kpi_definitions_is_not_filtered_by_has_kpi_permission(self):
        # ACTOR_ADMINISTRA_PERMISOS_KPI no tiene ninguna fila propia en
        # nm_permission_kpi -- si /all estuviera filtrando por
        # has_kpi_permission (como /kpi_definition/ si lo hace), vendria
        # vacio. El catalogo completo debe verse igual.
        response = self._request(ACTOR_ADMINISTRA_PERMISOS_KPI, "GET", "/kpi_definition/all")

        self.assertEqual(200, response.status_code)
        claves = [item["clave"] for item in self.json(response)["items"]]
        self.assertIn("ventas_por_empleado", claves)

    def test_list_all_kpi_definitions_denied_without_admin_permission(self):
        response = self._request(ACTOR_SIN_PERMISO_DE_ADMINISTRAR_KPI, "GET", "/kpi_definition/all")

        self.assertEqual(403, response.status_code)

    def test_create_list_and_delete_permission_kpi(self):
        creado = self._request(ACTOR_ADMINISTRA_PERMISOS_KPI, "POST", "/permission_kpi/", {
            "id_permission": 500, "id_kpi_definition": self.id_kpi,
        })
        self.assertEqual(201, creado.status_code, self.json(creado))
        cuerpo = self.json(creado)
        self.assertTrue(cuerpo["puede_ver"], "puede_ver=True es el default")
        id_nm_permission_kpi = cuerpo["id_nm_permission_kpi"]

        listado = self._request(ACTOR_ADMINISTRA_PERMISOS_KPI, "GET", "/permission_kpi/?id_permission=500")
        self.assertEqual(200, listado.status_code)
        self.assertEqual([self.id_kpi], [item["id_kpi_definition"] for item in self.json(listado)["items"]])

        with transaction_context() as db:
            self.assertTrue(has_kpi_permission(db, {"id_permission": 500}, self.id_kpi))

        borrado = self._request(ACTOR_ADMINISTRA_PERMISOS_KPI, "DELETE", f"/permission_kpi/{id_nm_permission_kpi}")
        self.assertEqual(200, borrado.status_code)

        listado_tras_borrar = self._request(ACTOR_ADMINISTRA_PERMISOS_KPI, "GET", "/permission_kpi/?id_permission=500")
        self.assertEqual([], self.json(listado_tras_borrar)["items"])
        with transaction_context() as db:
            self.assertFalse(has_kpi_permission(db, {"id_permission": 500}, self.id_kpi))

    def test_permission_kpi_endpoints_denied_without_admin_permission(self):
        for method, path, payload in (
            ("GET", "/permission_kpi/?id_permission=500", None),
            ("POST", "/permission_kpi/", {"id_permission": 500, "id_kpi_definition": self.id_kpi}),
            ("DELETE", "/permission_kpi/1", None),
        ):
            with self.subTest(method=method, path=path):
                response = self._request(ACTOR_SIN_PERMISO_DE_ADMINISTRAR_KPI, method, path, payload)
                self.assertEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
