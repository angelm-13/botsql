from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, KpiDefinition, KpiSnapshot, Level, NmPermissionKpi, Permission,
    Proyect, RestaurantWaiter, Status, Subdepartment, User,
)
from app.models.session import engine, transaction_context
from app.modules.plan import reiniciar_plan
from app.services.nm_permission_kpi_service import NmPermissionKpiService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase

# Dimensiones del Dashboard: catalogo, nombres que manda el backend, "Sin asignar" y la regla de
# que un KPI sin eje de proyecto no se le asigna a un rol acotado. Solo PostgreSQL, igual que
# test_api_kpi.py (el filtro de snapshots usa JSONB).
ADMIN = {"id_user": 1, "is_superuser": True}
ACTOR_TODOS = {"id_user": 970, "id_permission": 970, "id_proyect": 970}
ACTOR_PROPIOS = {"id_user": 971, "id_permission": 971, "id_proyect": 970}
ACTOR_SIN_MODULO = {"id_user": 973, "id_permission": 973, "id_proyect": 970}

PROYECTO_A = 970
MESERO_ROSA = 9701
MESERO_LUIS = 9702
ROL_TODOS = 970        # scope_read = 4 sobre kpi_definition
ROL_PROPIOS = 971      # scope_read = 1
ROL_SIN_FILA = 972     # sin fila de kpi_definition


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestKpiDimensionesApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        reiniciar_plan()
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
                id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=PROYECTO_A,
                id_status=1, supervisor=1, user_type="admin", username="kpi-dim-admin",
            ))
            for id_user, nombre in ((950, "Ana Torres"), (951, "Luis Medina")):
                db.add(User(
                    id_user=id_user, created_by=1, full_name=nombre, id_permission=1, id_proyect=PROYECTO_A,
                    id_status=1, supervisor=1, user_type="employee", username=f"kpi-dim-{id_user}",
                ))
            db.add(CustomerSupplier(
                id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                fiscal_type="601", type="supplier", id_user=1, created_by=1,
            ))
            db.add(Proyect(
                id_proyect=PROYECTO_A, id_customer_supplier=1, leader=1, proyect_description="Restaurante", created_by=1,
            ))
            db.flush()
            for id_mesero, nombre in ((MESERO_ROSA, "Rosa"), (MESERO_LUIS, "Luis")):
                db.add(RestaurantWaiter(
                    id_restaurant_waiter=id_mesero, id_proyect=PROYECTO_A, name=nombre, nickname=nombre, created_by=1,
                ))
            db.add_all([
                EntityPermission(id_permission=ROL_TODOS, entity_name="kpi_definition", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=ROL_PROPIOS, entity_name="kpi_definition", scope_create=1, scope_read=1, scope_update=1, scope_delete=1, created_by=1),
            ])

        seed_kpi_definitions(engine)
        with transaction_context() as db:
            ids = dict(db.execute(select(KpiDefinition.clave, KpiDefinition.id_kpi_definition)).all())
            self.id_mesero = ids["ventas_por_mesero"]
            self.id_empleado = ids["ventas_por_empleado"]
            self.id_sin_eje = ids["incidencias_pendientes"]
            for id_kpi in (self.id_mesero, self.id_empleado):
                for rol in (ROL_TODOS, ROL_PROPIOS):
                    db.add(NmPermissionKpi(id_permission=rol, id_kpi_definition=id_kpi, puede_ver=True, created_by=1))
            db.add_all([
                KpiSnapshot(id_kpi_definition=self.id_mesero, dimension_key={"id_restaurant_waiter": MESERO_ROSA, "id_proyect": PROYECTO_A}, periodo=date(2026, 9, 1), valor=Decimal("250.00")),
                KpiSnapshot(id_kpi_definition=self.id_mesero, dimension_key={"id_restaurant_waiter": MESERO_LUIS, "id_proyect": PROYECTO_A}, periodo=date(2026, 9, 2), valor=Decimal("60.00")),
                # Una orden sin mesero: el job guarda la llave con valor nulo.
                KpiSnapshot(id_kpi_definition=self.id_mesero, dimension_key={"id_restaurant_waiter": None, "id_proyect": PROYECTO_A}, periodo=date(2026, 9, 2), valor=Decimal("40.00")),
                KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": 950, "id_proyect": PROYECTO_A}, periodo=date(2026, 9, 1), valor=Decimal("1000.00")),
                KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": None, "id_proyect": PROYECTO_A}, periodo=date(2026, 9, 1), valor=Decimal("5.00")),
            ])

    def _get(self, actor, path):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.get(path, headers={"Authorization": "Bearer kpi-dim-test"})

    def _post(self, actor, path, cuerpo):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.post(path, json=cuerpo, headers={"Authorization": "Bearer kpi-dim-test"})

    def _consulta(self, id_kpi, **params):
        params.setdefault("fecha_inicio", "2026-09-01")
        params.setdefault("fecha_fin", "2026-09-30")
        return f"/kpi_snapshot/query?id_kpi_definition={id_kpi}&" + "&".join(f"{k}={v}" for k, v in params.items())

    # --- catalogo de dimensiones ---------------------------------------------

    def test_el_catalogo_de_dimensiones_trae_las_de_siempre_y_las_nuevas(self):
        respuesta = self._get(ACTOR_TODOS, "/kpi_dimension/")
        self.assertEqual(200, respuesta.status_code)
        porclave = {d["clave"]: d for d in self.json(respuesta)["items"]}
        self.assertEqual(
            ["empleado", "producto", "global", "estado", "familia", "mesero", "platillo", "mesa", "cliente", "unidad", "operador"],
            list(porclave),
        )
        # Solo el empleado son ids de usuario: la unica "persona".
        self.assertEqual(["empleado"], [c for c, d in porclave.items() if d["tipo"] == "persona"])
        self.assertEqual("categoria", porclave["estado"]["tipo"])
        self.assertEqual("global", porclave["global"]["tipo"])
        self.assertFalse(porclave["estado"]["abierta"])
        self.assertTrue(porclave["mesero"]["abierta"])
        self.assertEqual("id_restaurant_waiter", porclave["mesero"]["json_key"])

    def test_el_catalogo_de_dimensiones_exige_el_modulo_de_kpis(self):
        self.assertEqual(403, self._get(ACTOR_SIN_MODULO, "/kpi_dimension/").status_code)

    # --- nombres que manda el backend y "Sin asignar" -------------------------

    def test_ventas_por_mesero_trae_los_nombres_y_la_fila_sin_asignar(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_mesero)))["rango_a"]
        self.assertEqual({str(MESERO_ROSA): 250.0, str(MESERO_LUIS): 60.0, "sin_asignar": 40.0}, rango["por_empleado"])
        self.assertEqual(350.0, rango["total"], "la fila sin mesero cuenta en el total")
        self.assertEqual("Rosa", rango["etiquetas"][str(MESERO_ROSA)])
        self.assertEqual("Luis", rango["etiquetas"][str(MESERO_LUIS)])
        self.assertEqual("Sin asignar", rango["etiquetas"]["sin_asignar"])

    def test_un_kpi_de_siempre_sigue_descartando_la_fila_sin_entidad_y_no_la_etiqueta(self):
        # "Sin asignar" es opt-in por KPI: ventas_por_empleado (uno de los 24 originales) no la muestra.
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_empleado)))["rango_a"]
        self.assertEqual({"950": 1000.0}, rango["por_empleado"])
        self.assertEqual(1000.0, rango["total"], "la fila sin empleado no entra al total")
        self.assertEqual({"950": "Ana Torres"}, rango["etiquetas"])

    def test_pedir_entidades_concretas_deja_fuera_la_fila_sin_asignar(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_mesero, entidades=MESERO_ROSA)))["rango_a"]
        self.assertEqual({str(MESERO_ROSA): 250.0}, rango["por_empleado"])

    def test_agrupado_por_periodo_suma_todo_y_no_trae_nombres_de_nadie(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_mesero, agrupar_por="periodo")))["rango_a"]
        self.assertEqual({"2026-09-01": 250.0, "2026-09-02": 100.0}, rango["por_periodo"])
        self.assertEqual(350.0, rango["total"])
        self.assertEqual({"sin_asignar": "Sin asignar"}, rango["etiquetas"])

    def test_un_kpi_de_estado_no_lleva_etiquetas(self):
        with transaction_context() as db:
            id_estado = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "material_por_estado"))
        rango = self.json(self._get(ADMIN, self._consulta(id_estado)))["rango_a"]
        self.assertNotIn("etiquetas", rango)

    def test_un_kpi_de_categorias_con_nombres_propios_los_manda_como_etiquetas(self):
        with transaction_context() as db:
            id_mesas = db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == "mesas_ocupadas"))
            db.add(KpiSnapshot(id_kpi_definition=id_mesas, dimension_key={"estado": "por_liberar", "id_proyect": PROYECTO_A},
                               periodo=date(2026, 9, 2), valor=Decimal("3")))
        rango = self.json(self._get(ADMIN, self._consulta(id_mesas)))["rango_a"]
        self.assertEqual({"por_liberar": 3.0}, rango["por_empleado"])
        self.assertEqual("Pagada, aún ocupada", rango["etiquetas"]["por_liberar"])
        self.assertEqual("Libre", rango["etiquetas"]["libre"])

    def test_sin_datos_no_hay_filas_y_el_total_es_cero(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_mesero, fecha_inicio="2025-01-01", fecha_fin="2025-01-31")))["rango_a"]
        self.assertEqual({}, rango["por_empleado"])
        self.assertEqual(0.0, rango["total"])
        self.assertEqual({"sin_asignar": "Sin asignar"}, rango["etiquetas"])

    # --- alcance de lectura ---------------------------------------------------

    def test_un_kpi_por_mesero_no_se_puede_recortar_por_persona_y_exige_todos(self):
        # Propios/Mis grupos recortan por id de usuario; un mesero no lo es.
        self.assertEqual(403, self._get(ACTOR_PROPIOS, self._consulta(self.id_mesero)).status_code)
        self.assertEqual(200, self._get(ACTOR_TODOS, self._consulta(self.id_mesero)).status_code)

    def test_un_kpi_por_empleado_sigue_recortandose_con_propios(self):
        rango = self.json(self._get(ACTOR_PROPIOS, self._consulta(self.id_empleado)))["rango_a"]
        self.assertEqual({}, rango["por_empleado"])

    # --- un KPI sin eje de proyecto no se asigna a un rol acotado -----------------

    def _asignar(self, id_permission, id_kpi, **extra):
        return self._post(ADMIN, "/permission_kpi/", {"id_permission": id_permission, "id_kpi_definition": id_kpi, **extra})

    def test_se_rechaza_asignar_un_kpi_sin_proyecto_a_un_rol_que_no_ve_todos(self):
        respuesta = self._asignar(ROL_PROPIOS, self.id_sin_eje)
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.kpi_sin_eje_de_proyecto", self.json(respuesta)["error_key"])
        with transaction_context() as db:
            self.assertIsNone(db.scalar(select(NmPermissionKpi).where(
                NmPermissionKpi.id_permission == ROL_PROPIOS, NmPermissionKpi.id_kpi_definition == self.id_sin_eje)))

    def test_un_rol_sin_fila_de_alcance_tampoco_recibe_un_kpi_sin_proyecto(self):
        self.assertEqual(400, self._asignar(ROL_SIN_FILA, self.id_sin_eje).status_code)

    def test_un_rol_con_todos_si_recibe_un_kpi_sin_proyecto(self):
        self.assertEqual(201, self._asignar(ROL_TODOS, self.id_sin_eje).status_code)

    def test_un_kpi_con_proyecto_se_asigna_a_cualquier_rol(self):
        with transaction_context() as db:
            db.execute(NmPermissionKpi.__table__.delete())
        self.assertEqual(201, self._asignar(ROL_PROPIOS, self.id_empleado).status_code)
        self.assertEqual(201, self._asignar(ROL_SIN_FILA, self.id_mesero).status_code)

    def test_quitar_la_visibilidad_no_se_bloquea(self):
        self.assertEqual(201, self._asignar(ROL_PROPIOS, self.id_sin_eje, puede_ver=False).status_code)

    def test_actualizar_una_fila_tambien_valida_la_combinacion_resultante(self):
        with transaction_context() as db:
            fila = db.scalar(select(NmPermissionKpi).where(
                NmPermissionKpi.id_permission == ROL_PROPIOS, NmPermissionKpi.id_kpi_definition == self.id_empleado))
            id_fila = fila.id_nm_permission_kpi
        with self.assertRaises(AppError) as contexto:
            NmPermissionKpiService.update(id_fila, {"id_kpi_definition": self.id_sin_eje}, user_id=1)
        self.assertEqual("errors.kpi_sin_eje_de_proyecto", contexto.exception.message_key)
        # Cambiar otra cosa de la misma fila no la bloquea.
        NmPermissionKpiService.update(id_fila, {"puede_ver": True}, user_id=1)


if __name__ == "__main__":
    unittest.main()
