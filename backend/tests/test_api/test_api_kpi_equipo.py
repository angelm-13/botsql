from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest import mock
from unittest.mock import patch

from sqlalchemy import select, text

from app.jobs import tasks_kpis
from app.kpis import frecuencia
from app.kpis.registry import KPI_POR_CLAVE, seed_kpi_definitions
from app.models import (
    CustomerSupplier, Department, EntityPermission, Incident, IncidentType, KpiDefinition, KpiSnapshot, Level,
    NmPermissionKpi, NmTeamUser, Permission, Proyect, Status, Subdepartment, Team, User,
)
from app.models.session import engine, transaction_context
from app.modules.plan import reiniciar_plan
from app.routes.kpi import _totales
from tests.conftest import BackendTestCase
from app.utils.tiempo import pared_a_utc
from tests.reloj import ahora_local

# Filtro `id_teams` de GET /kpi_snapshot/query y la dimension `equipo`. Solo PostgreSQL, como el resto de las pruebas
# de la API de KPIs: el filtro de snapshots usa JSONB.
ADMIN = {"id_user": 1, "is_superuser": True}
ACTOR_TODOS = {"id_user": 970, "id_permission": 970, "id_proyect": 970}
ACTOR_PROPIOS = {"id_user": 951, "id_permission": 971, "id_proyect": 970}
ACTOR_MIS_GRUPOS = {"id_user": 950, "id_permission": 972, "id_proyect": 970}

PROYECTO = 970
ANA, BETO, CARLA, DIEGO = 950, 951, 952, 953      # Diego no esta en ningun equipo
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
            for id_user, nombre in ((ANA, "Ana Torres"), (BETO, "Beto Luna"), (CARLA, "Carla Rios"), (DIEGO, "Diego Paz")):
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
            # Desde antes de cualquier dia de las pruebas: cada fila cuenta en el equipo que la persona tenia ese dia.
            for id_team, id_user in ((T1, ANA), (T1, BETO), (T2, BETO), (T2, CARLA)):
                db.add(NmTeamUser(id_team=id_team, id_user=id_user, created_by=1, creation_date=datetime(2026, 8, 1)))
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
                # Gente sin equipo: el job guarda la llave con valor nulo.
                KpiSnapshot(id_kpi_definition=self.id_equipo, dimension_key={"id_team": None}, periodo=date(2026, 9, 2), valor=Decimal("4")),
                KpiSnapshot(id_kpi_definition=self.id_global, dimension_key={}, periodo=date(2026, 9, 2), valor=Decimal("4")),
            ])

    def _get(self, actor, path):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.get(path, headers={"Authorization": "Bearer kpi-eq-test"})

    def _delete(self, actor, path):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.delete(path, headers={"Authorization": "Bearer kpi-eq-test"})

    def _consulta(self, id_kpi, **params):
        params.setdefault("fecha_inicio", "2026-09-01")
        params.setdefault("fecha_fin", "2026-09-30")
        return f"/kpi_snapshot/query?id_kpi_definition={id_kpi}&" + "&".join(f"{k}={v}" for k, v in params.items())

    def _por_empleado(self, actor, id_kpi, **params):
        respuesta = self._get(actor, self._consulta(id_kpi, **params))
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))
        return {(int(k) if k.isdigit() else k): v for k, v in self.json(respuesta)["rango_a"]["por_empleado"].items()}

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

    # --- id_teams atribuye cada DIA al equipo que la persona tenia ese dia ---------------------------------

    def _diego(self, *, snapshots, membresias):
        """Diego (sin equipo en el fixture) con `membresias` [(equipo, desde, hasta)] en hora de pared, y un snapshot por dia."""
        with transaction_context() as db:
            for id_team, desde, hasta in membresias:
                db.add(NmTeamUser(
                    id_team=id_team, id_user=DIEGO, created_by=1, creation_date=pared_a_utc(desde),
                    deletion_date=None if hasta is None else pared_a_utc(hasta),
                ))
            for dia, valor in snapshots.items():
                db.add(KpiSnapshot(
                    id_kpi_definition=self.id_empleado, dimension_key={"id_user": DIEGO, "id_proyect": PROYECTO},
                    periodo=dia, valor=Decimal(valor),
                ))

    def _de_diego(self, **params):
        params.setdefault("fecha_inicio", "2026-10-01")
        params.setdefault("fecha_fin", "2026-10-31")
        return self._por_empleado(ACTOR_TODOS, self.id_empleado, **params).get(DIEGO)

    def test_quien_pasa_de_t1_a_t2_el_miercoles_conserva_en_t1_los_dias_de_antes(self):
        self._diego(
            snapshots={date(2026, 10, 5): "10", date(2026, 10, 6): "20", date(2026, 10, 7): "30", date(2026, 10, 8): "40"},
            membresias=[
                (T1, datetime(2026, 10, 5, 0, 0), datetime(2026, 10, 7, 9, 0)),
                (T2, datetime(2026, 10, 7, 9, 0), None),
            ],
        )

        self.assertEqual(30.0, self._de_diego(id_teams=T1), "lunes y martes")
        self.assertEqual(70.0, self._de_diego(id_teams=T2), "el miercoles (se movio a las 9:00) y el jueves")
        self.assertEqual(100.0, self._de_diego(id_teams=f"{T1},{T2}"), "la union; un dia nunca cuenta dos veces")
        self.assertEqual(100.0, self._de_diego(), "sin filtro, todo")
        self.assertIsNone(self._de_diego(id_teams=T3))

    def test_un_dia_anterior_al_alta_en_el_equipo_no_cuenta(self):
        self._diego(
            snapshots={date(2026, 10, 5): "10", date(2026, 10, 6): "20"},
            membresias=[(T1, datetime(2026, 10, 6, 0, 0), None)],
        )

        self.assertEqual(20.0, self._de_diego(id_teams=T1), "el dia 5 la persona todavia no estaba en el equipo")

    def test_un_equipo_dado_de_baja_conserva_a_sus_integrantes_en_los_dias_en_que_existio(self):
        self._diego(
            snapshots={date(2026, 10, 5): "10", date(2026, 10, 6): "20", date(2026, 10, 7): "30", date(2026, 10, 8): "40"},
            membresias=[(T1, datetime(2026, 10, 5, 0, 0), None)],
        )
        with transaction_context() as db:
            db.get(Team, T1).deletion_date = pared_a_utc(datetime(2026, 10, 7, 12, 0))

        self.assertEqual(30.0, self._de_diego(id_teams=T1), "los dias 5 y 6; el 7 ya termino sin el equipo")

    def test_la_medianoche_utc_no_mueve_a_la_persona_un_dia(self):
        # Alta a las 19:00 locales del dia 6 = 01:00 UTC del dia 7. El dia local 6 termina con la persona en T1.
        self._diego(
            snapshots={date(2026, 10, 5): "10", date(2026, 10, 6): "20", date(2026, 10, 7): "30"},
            membresias=[(T1, datetime(2026, 10, 6, 19, 0), None)],
        )

        self.assertEqual(50.0, self._de_diego(id_teams=T1), "los dias 6 y 7, no el 5")

    def test_la_persona_dada_de_baja_del_sistema_no_cuenta_igual_que_antes(self):
        self._diego(snapshots={date(2026, 10, 5): "10"}, membresias=[(T1, datetime(2026, 10, 1, 0, 0), None)])
        with transaction_context() as db:
            db.get(User, DIEGO).deletion_date = datetime(2026, 10, 20)

        self.assertIsNone(self._de_diego(id_teams=T1))

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

    def test_un_kpi_por_equipo_trae_el_nombre_de_cada_equipo_y_la_fila_sin_equipo(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_equipo)))["rango_a"]
        self.assertEqual({str(T1): 2.0, str(T2): 3.0, str(T3): 0.0, "sin_asignar": 4.0}, rango["por_empleado"])
        self.assertEqual("Parque Norte", rango["etiquetas"][str(T1)])
        self.assertEqual("Parque Sur", rango["etiquetas"][str(T2)])
        # La fila sin entidad se llama "Sin equipo" (y no "Sin asignar") y cuenta en el total.
        self.assertEqual("Sin equipo", rango["etiquetas"]["sin_asignar"])
        self.assertEqual(9.0, rango["total"])

    def test_un_equipo_dado_de_baja_por_la_api_conserva_su_nombre_y_sus_cifras_en_el_historico(self):
        # Los snapshots guardan el id del equipo: si la baja lo borrara, esas cifras quedarian sin nombre ("#9701").
        respuesta = self._delete(ADMIN, f"/team/{T1}")
        self.assertEqual(200, respuesta.status_code, self.json(respuesta))

        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_equipo)))["rango_a"]

        self.assertEqual(2.0, rango["por_empleado"][str(T1)], "lo que ya se midio no se pierde")
        self.assertEqual("Parque Norte", rango["etiquetas"][str(T1)], "sigue con su nombre")
        with transaction_context() as db:
            self.assertIsNotNone(db.get(Team, T1).deletion_date, "la fila sigue ahi, de baja")

    def test_con_id_teams_la_fila_sin_equipo_no_aparece(self):
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_equipo, id_teams=f"{T1},{T2}")))["rango_a"]
        self.assertEqual({str(T1): 2.0, str(T2): 3.0}, rango["por_empleado"])
        self.assertNotIn("sin_asignar", rango["por_empleado"], "pedir equipos concretos deja fuera a quien no tiene equipo")
        # Tampoco con `entidades`, el filtro generico de siempre.
        rango = self.json(self._get(ACTOR_TODOS, self._consulta(self.id_equipo, entidades=T1)))["rango_a"]
        self.assertEqual({str(T1): 2.0}, rango["por_empleado"])

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

    # --- de punta a punta: checada -> corrida frecuente -> /kpi_snapshot/query ----------------------------

    def _checada_abierta(self, id_incident, id_user, hora):
        with transaction_context() as db:
            if db.get(IncidentType, 1) is None:
                db.add(IncidentType(id_incident_type=1, incident_type_description="Checador", created_by=1))
                db.flush()
            db.add(Incident(
                id_incident=id_incident, id_incident_type=1, id_user=id_user, created_by=id_user, incident_status="abierta",
                incident_date=datetime(2026, 10, 15, hora, 0), latitude=Decimal("21.1161741"),
            ))

    def _correr_frecuente(self, hora_local, minuto=0):
        fotos = tuple(KPI_POR_CLAVE[clave] for clave in frecuencia.KPIS_FRECUENTES)
        with mock.patch.object(tasks_kpis, "KPI_REGISTRY", fotos), ahora_local(datetime(2026, 10, 15, hora_local, minuto)):
            tasks_kpis.recalculate_kpi_snapshots_frecuentes()

    def test_de_punta_a_punta_la_checada_llega_al_dashboard_por_equipo_y_se_actualiza(self):
        with transaction_context() as db:
            id_sin_salida = db.scalar(select(KpiDefinition.id_kpi_definition).where(
                KpiDefinition.clave == "checadas_sin_salida_por_equipo"))
        self._checada_abierta(1, ANA, 10)          # Ana: Norte
        self._checada_abierta(2, BETO, 11)         # Beto: Norte y Sur
        self._checada_abierta(3, DIEGO, 11)        # Diego: ningun equipo
        self._correr_frecuente(15)

        rango = self.json(self._get(ADMIN, self._consulta(self.id_equipo, fecha_inicio="2026-10-09", fecha_fin="2026-10-15")))["rango_a"]
        # Beto cuenta en cada uno de sus dos equipos; el equipo sin nadie sale con su cero, no desaparece.
        self.assertEqual({str(T1): 2.0, str(T2): 1.0, str(T3): 0.0, "sin_asignar": 1.0}, rango["por_empleado"])
        self.assertEqual("Parque Norte", rango["etiquetas"][str(T1)])
        self.assertEqual("Parque Vacio", rango["etiquetas"][str(T3)])
        self.assertEqual("Sin equipo", rango["etiquetas"]["sin_asignar"], "Diego no tiene equipo")
        nadie = self.json(self._get(ADMIN, self._consulta(id_sin_salida, fecha_inicio="2026-10-09", fecha_fin="2026-10-15")))["rango_a"]
        self.assertEqual({str(T1): 0.0, str(T2): 0.0, str(T3): 0.0, "sin_asignar": 0.0}, nadie["por_empleado"])

        # Pasan las horas: a las 22:30 la entrada de las 10:00 lleva 12 h 30 min abierta ("sin salida") y la de las
        # 11:00 solo 11 h 30 min. Lo que era "en turno" se actualiza en el mismo dia, no queda el valor anterior.
        self._correr_frecuente(22, 30)
        en_turno = self.json(self._get(ADMIN, self._consulta(self.id_equipo, fecha_inicio="2026-10-09", fecha_fin="2026-10-15")))["rango_a"]
        self.assertEqual({str(T1): 1.0, str(T2): 1.0, str(T3): 0.0, "sin_asignar": 1.0}, en_turno["por_empleado"],
                         "quedan Beto y Diego (11:00)")
        sin_salida = self.json(self._get(ADMIN, self._consulta(id_sin_salida, fecha_inicio="2026-10-09", fecha_fin="2026-10-15")))["rango_a"]
        self.assertEqual({str(T1): 1.0, str(T2): 0.0, str(T3): 0.0, "sin_asignar": 0.0}, sin_salida["por_empleado"],
                         "Ana (10:00) ya paso de 12 h")

    # --- de punta a punta: entradas, salidas y minutos por persona -----------------------------------------

    def _id_de(self, clave):
        with transaction_context() as db:
            return db.scalar(select(KpiDefinition.id_kpi_definition).where(KpiDefinition.clave == clave))

    def _rango(self, clave):
        consulta = self._consulta(self._id_de(clave), fecha_inicio="2026-10-09", fecha_fin="2026-10-15")
        return self.json(self._get(ADMIN, consulta))["rango_a"]

    def test_de_punta_a_punta_entradas_salidas_y_quien_esta_en_turno(self):
        self._checada_abierta(1, ANA, 10)          # Norte
        self._checada_abierta(2, BETO, 11)         # Norte y Sur
        self._checada_abierta(3, DIEGO, 11)        # ningun equipo
        self._correr_frecuente(15)

        entradas = self._rango("checadas_entradas_por_equipo")
        self.assertEqual({str(T1): 2.0, str(T2): 1.0, str(T3): 0.0, "sin_asignar": 1.0}, entradas["por_empleado"])
        self.assertEqual("Sin equipo", entradas["etiquetas"]["sin_asignar"])
        salidas = self._rango("checadas_salidas_por_equipo")
        self.assertEqual({str(T1): 0.0, str(T2): 0.0, str(T3): 0.0, "sin_asignar": 0.0}, salidas["por_empleado"])
        # Minutos por persona (a las 15:00): Ana lleva 5 h, Beto y Diego 4 h; con su nombre.
        en_turno = self._rango("checadas_en_turno_por_empleado")
        self.assertEqual({str(ANA): 300.0, str(BETO): 240.0, str(DIEGO): 240.0}, en_turno["por_empleado"])
        self.assertEqual("Ana Torres", en_turno["etiquetas"][str(ANA)])

        # A las 16:30: Ana sale (resuelta, 16:00) y la entrada de Beto se anula. Lo que se habia contado se corrige
        # en el mismo dia: el equipo Sur baja de 1 a 0 (el cero pisa el valor viejo) y quien salio deja de aparecer.
        with transaction_context() as db:
            ana = db.get(Incident, 1)
            ana.incident_status, ana.close_date = "resuelta", datetime(2026, 10, 15, 16, 0)
            beto = db.get(Incident, 2)
            beto.incident_status, beto.close_date = "cancelada", datetime(2026, 10, 15, 16, 5)
        self._correr_frecuente(16, 30)

        entradas = self._rango("checadas_entradas_por_equipo")
        self.assertEqual({str(T1): 1.0, str(T2): 0.0, str(T3): 0.0, "sin_asignar": 1.0}, entradas["por_empleado"],
                         "la entrada anulada de Beto ya no cuenta: ni en Norte ni en Sur")
        salidas = self._rango("checadas_salidas_por_equipo")
        self.assertEqual({str(T1): 1.0, str(T2): 0.0, str(T3): 0.0, "sin_asignar": 0.0}, salidas["por_empleado"],
                         "la salida de Ana cuenta; la anulacion de Beto no es una salida")
        en_turno = self._rango("checadas_en_turno_por_empleado")
        self.assertEqual({str(DIEGO): 330.0}, en_turno["por_empleado"],
                         "Ana (salio) y Beto (anulada) quedan en cero y la API no los pinta; Diego lleva 5 h 30 min")
        self.assertEqual({str(DIEGO)}, set(en_turno["etiquetas"]), "tampoco viaja el nombre de quien no se pinta")

    # --- ocultar_ceros ---------------------------------------------------------------------------------------

    def _sembrar_un_cero(self):
        with transaction_context() as db:
            db.add(KpiSnapshot(id_kpi_definition=self.id_empleado, dimension_key={"id_user": DIEGO, "id_proyect": PROYECTO},
                               periodo=date(2026, 9, 1), valor=Decimal("0")))

    def _totales_de_empleados(self, **extra):
        with transaction_context() as db:
            return _totales(db, self.id_empleado, date(2026, 9, 1), date(2026, 9, 30), PROYECTO, None, "id_user", "suma", **extra)

    def test_ocultar_ceros_quita_las_entidades_en_cero_y_no_cambia_el_total(self):
        self._sembrar_un_cero()
        con = self._totales_de_empleados()
        sin = self._totales_de_empleados(ocultar_ceros=True)
        self.assertEqual({str(ANA), str(BETO), str(CARLA), str(DIEGO)}, set(con["por_empleado"]), "por omision se ven todas")
        self.assertEqual({str(ANA), str(BETO), str(CARLA)}, set(sin["por_empleado"]), "Diego (0) ya no sale")
        self.assertEqual(con["total"], sin["total"], "un cero no suma")

    def test_ocultar_ceros_va_antes_del_limite(self):
        # Con limite 4 y cuatro entidades (una en cero) salen tres: el cero no ocupa un lugar del top.
        self._sembrar_un_cero()
        self.assertEqual(4, len(self._totales_de_empleados(limite=4)["por_empleado"]))
        self.assertEqual(3, len(self._totales_de_empleados(ocultar_ceros=True, limite=4)["por_empleado"]))
