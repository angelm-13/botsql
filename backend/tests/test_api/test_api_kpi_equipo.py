from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select, text

from app.kpis.registry import seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, KpiDefinition, KpiSnapshot, Level, NmPermissionKpi, NmTeamUser,
    Permission, Proyect, Status, Subdepartment, Team, User,
)
from app.models.session import engine, transaction_context
from app.modules.plan import reiniciar_plan
from tests.conftest import BackendTestCase

# Filtro `id_teams` de GET /kpi_snapshot/query y la dimension `equipo`. Solo PostgreSQL, como el resto de las pruebas
# de la API de KPIs: el filtro de snapshots usa JSONB.
ACTOR_TODOS = {"id_user": 970, "id_permission": 970, "id_proyect": 970}
ACTOR_PROPIOS = {"id_user": 951, "id_permission": 971, "id_proyect": 970}
ACTOR_MIS_GRUPOS = {"id_user": 950, "id_permission": 972, "id_proyect": 970}

PROYECTO = 970
ANA, BETO, CARLA = 950, 951, 952
T1, T2, T3 = 9701, 9702, 9703       # T1 = {Ana, Beto}; T2 = {Beto, Carla}; T3 = sin miembros
ROL_TODOS, ROL_PROPIOS, ROL_MIS_GRUPOS = 970, 971, 972


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class TestKpiFiltroPorEquipoApi(BackendTestCase):
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
                id_user=1, created_by=1, full_name="Admin", id_permission=1, id_proyect=PROYECTO,
                id_status=1, supervisor=1, user_type="admin", username="kpi-eq-admin",
            ))
            for id_user, nombre in ((ANA, "Ana Torres"), (BETO, "Beto Luna"), (CARLA, "Carla Rios")):
                db.add(User(
                    id_user=id_user, created_by=1, full_name=nombre, id_permission=1, id_proyect=PROYECTO,
                    id_status=1, supervisor=1, user_type="employee", username=f"kpi-eq-{id_user}",
                ))
            db.add(CustomerSupplier(
                id_customer_supplier=1, name="Interno", tax_id="AAA010101AA1", postal_code="37000",
                fiscal_type="601", type="supplier", id_user=1, created_by=1,
            ))
            db.add(Proyect(id_proyect=PROYECTO, id_customer_supplier=1, leader=1, proyect_description="Parques", created_by=1))
            db.flush()
            for id_team, nombre in ((T1, "Parque Norte"), (T2, "Parque Sur"), (T3, "Parque Vacio")):
                db.add(Team(id_team=id_team, team_description=nombre, created_by=1))
            db.flush()
            # Beto esta en los dos equipos con miembros.
            for id_team, id_user in ((T1, ANA), (T1, BETO), (T2, BETO), (T2, CARLA)):
                db.add(NmTeamUser(id_team=id_team, id_user=id_user, created_by=1))
            db.add_all([
                EntityPermission(id_permission=ROL_TODOS, entity_name="kpi_definition", scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=ROL_PROPIOS, entity_name="kpi_definition", scope_create=1, scope_read=1, scope_update=1, scope_delete=1, created_by=1),
                EntityPermission(id_permission=ROL_MIS_GRUPOS, entity_name="kpi_definition", scope_create=2, scope_read=2, scope_update=2, scope_delete=2, created_by=1),
            ])

        seed_kpi_definitions(engine)
        with transaction_context() as db:
            ids = dict(db.execute(select(KpiDefinition.clave, KpiDefinition.id_kpi_definition)).all())
            self.id_empleado = ids["ventas_por_empleado"]
            self.id_equipo = ids["checadas_en_turno_por_equipo"]
            self.id_global = ids["incidencias_pendientes"]
            for id_kpi in (self.id_empleado, self.id_equipo, self.id_global):
                for rol in (ROL_TODOS, ROL_PROPIOS, ROL_MIS_GRUPOS):
                    db.add(NmPermissionKpi(id_permission=rol, id_kpi_definition=id_kpi, puede_ver=True, created_by=1))
            db.add_all([
                KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": ANA, "id_proyect": PROYECTO}, periodo=date(2026, 9, 1), valor=Decimal("100.00")),
                KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": BETO, "id_proyect": PROYECTO}, periodo=date(2026, 9, 1), valor=Decimal("200.00")),
                KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": CARLA, "id_proyect": PROYECTO}, periodo=date(2026, 9, 1), valor=Decimal("300.00")),
                # Un KPI por equipo no lleva id_proyect (alcance_proyecto=False).
                KpiSnapshot(id_kpi_definition=self.id_equipo, dimension_key={"id_team": T1}, periodo=date(2026, 9, 2), valor=Decimal("2")),
                KpiSnapshot(id_kpi_definition=self.id_equipo, dimension_key={"id_team": T2}, periodo=date(2026, 9, 2), valor=Decimal("3")),
                KpiSnapshot(id_kpi_definition=self.id_equipo, dimension_key={"id_team": T3}, periodo=date(2026, 9, 2), valor=Decimal("0")),
                KpiSnapshot(id_kpi_definition=self.id_global, dimension_key={}, periodo=date(2026, 9, 2), valor=Decimal("4")),
            ])

    def _get(self, actor, path):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.get(path, headers={"Authorization": "Bearer kpi-eq-test"})

    def _consulta(self, id_kpi, **params):
        params.setdefault("fecha_inicio", "2026-09-01")
        params.setdefault("fecha_fin", "2026-09-30")
        return f"/kpi_snapshot/query?id_kpi_definition={id_kpi}&" + "&".join(f"{k}={v}" for k, v in params.items())

    def _por_empleado(self, actor, id_kpi, **params):
        respuesta = self._get(actor, self._consulta(id_kpi, **params))
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        return {int(k): v for k, v in self.json(respuesta)["rango_a"]["por_empleado"].items()}

    # --- KPI por empleado: id_teams deja a los miembros ---------------------------------------------

    def test_sin_id_teams_se_ve_a_todos(self):
        self.assertEqual({ANA: 100.0, BETO: 200.0, CARLA: 300.0}, self._por_empleado(ACTOR_TODOS, self.id_empleado))

    def test_un_equipo_deja_solo_a_sus_miembros(self):
        self.assertEqual({ANA: 100.0, BETO: 200.0}, self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=T1))
        self.assertEqual({BETO: 200.0, CARLA: 300.0}, self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=T2))

    def test_varios_equipos_son_la_union_y_quien_esta_en_dos_sale_una_vez(self):
        self.assertEqual(
            {ANA: 100.0, BETO: 200.0, CARLA: 300.0},
            self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=f"{T1},{T2}"),
        )

    def test_un_equipo_sin_miembros_filtra_a_nadie_y_no_se_salta_el_filtro(self):
        self.assertEqual({}, self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=T3))

    def test_id_teams_se_combina_con_empleados_por_interseccion(self):
        self.assertEqual({BETO: 200.0}, self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=T1, empleados=BETO))
        self.assertEqual({}, self._por_empleado(ACTOR_TODOS, self.id_empleado, id_teams=T1, empleados=CARLA))

    # --- el alcance de lectura manda: id_teams recorta, nunca amplia ------------------------------------

    def test_mis_grupos_ve_a_su_equipo_y_un_equipo_ajeno_no_lo_amplia(self):
        # Ana (Mis grupos) esta en T1: cubre a Ana y Beto.
        self.assertEqual({ANA: 100.0, BETO: 200.0}, self._por_empleado(ACTOR_MIS_GRUPOS, self.id_empleado))
        # Pedir T2 (Beto y Carla) no le suma a Carla: solo queda lo que ya cubria.
        self.assertEqual({BETO: 200.0}, self._por_empleado(ACTOR_MIS_GRUPOS, self.id_empleado, id_teams=T2))
        self.assertEqual({}, self._por_empleado(ACTOR_MIS_GRUPOS, self.id_empleado, id_teams=T3))

    def test_propios_con_un_equipo_solo_ve_lo_suyo(self):
        # Beto (Propios) solo se cubre a si mismo, este o no en el equipo pedido.
        self.assertEqual({BETO: 200.0}, self._por_empleado(ACTOR_PROPIOS, self.id_empleado, id_teams=T1))
        self.assertEqual({BETO: 200.0}, self._por_empleado(ACTOR_PROPIOS, self.id_empleado, id_teams=T2))

    # --- KPI por equipo --------------------------------------------------------------------------------------

    def test_un_kpi_por_equipo_trae_el_nombre_de_cada_equipo(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_equipo)))["rango_a"]
        self.assertEqual({str(T1): 2.0, str(T2): 3.0, str(T3): 0.0}, rango["por_empleado"])
        self.assertEqual("Parque Norte", rango["etiquetas"][str(T1)])
        self.assertEqual("Parque Sur", rango["etiquetas"][str(T2)])

    def test_id_teams_deja_solo_esos_equipos_en_un_kpi_por_equipo(self):
        self.assertEqual({T1: 2.0}, self._por_empleado(ACTOR_TODOS, self.id_equipo, id_teams=T1))
        self.assertEqual({T1: 2.0, T2: 3.0}, self._por_empleado(ACTOR_TODOS, self.id_equipo, id_teams=f"{T1},{T2}"))
        # Un equipo sin snapshots (o que no existe) no inventa filas.
        self.assertEqual({}, self._por_empleado(ACTOR_TODOS, self.id_equipo, id_teams=99999))

    def test_id_teams_y_entidades_se_intersectan_en_un_kpi_por_equipo(self):
        self.assertEqual({T2: 3.0}, self._por_empleado(ACTOR_TODOS, self.id_equipo, id_teams=f"{T1},{T2}", entidades=T2))
        self.assertEqual({}, self._por_empleado(ACTOR_TODOS, self.id_equipo, id_teams=T1, entidades=T2))

    def test_un_kpi_por_equipo_exige_todos_como_cualquiera_que_no_es_por_persona(self):
        # Un equipo no es una persona: no se puede recortar por persona, asi que Propios y Mis grupos no lo ven.
        for actor in (ACTOR_PROPIOS, ACTOR_MIS_GRUPOS):
            respuesta = self._get(actor, self._consulta(self.id_equipo))
            self.assertEqual(403, respuesta.status_code, actor)
            self.assertEqual("scope", self.json(respuesta)["meta"]["reason"])

    # --- lo que id_teams no toca -----------------------------------------------------------------------------

    def test_un_kpi_sin_dimension_de_persona_ni_de_equipo_ignora_id_teams(self):
        sin = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_global)))["rango_a"]["total"]
        con = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_global, id_teams=T1)))["rango_a"]["total"]
        self.assertEqual(4.0, sin)
        self.assertEqual(sin, con)

    def test_un_id_teams_que_no_es_numero_es_un_error_400(self):
        respuesta = self._get(ACTOR_TODOS, self._consulta(self.id_empleado, id_teams="abc"))
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("id_teams", self.json(respuesta)["meta"]["field"])
