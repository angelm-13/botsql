"""Proyectos, incidencias y bitacora: Mis grupos SUMA al equipo; Propios y Todos dejan la regla como estaba.

Estos modulos ya tenian su propia regla de dueno (por capacidad). La celda del
Gestor solo la amplia: un Supervisor sembrado en Todos NO pasa a ver todos los
proyectos.
"""
from __future__ import annotations

from datetime import date

from app.models import Incident
from app.models.entity_permission import EntityPermission
from app.models.nm_team_user import NmTeamUser
from app.models.proyect import Proyect
from app.models.session import transaction_context
from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.team import Team
from app.services.activity_log_service import get_activities_by_range
from app.services.incident_service import require_incident_access, scoped_incident_query
from app.services.project_management_service import visible_project_ids
from app.utils.errors import AppError
from app.utils.scope import companeros
from tests.conftest import BackendTestCase

YO, COMPANERO, EXTRANO = 11, 12, 13
ROL = 801


class Base(BackendTestCase):
    CELDA = 4  # alcance de lectura en proyect / incident / daily_activity_log

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for entidad in ("proyect", "incident", "daily_activity_log"):
                db.add(EntityPermission(id_permission=ROL, entity_name=entidad,
                                        scope_create=4, scope_read=self.CELDA, scope_update=4, created_by=1))
            self.p_yo = self._proyecto(db, YO)
            self.p_companero = self._proyecto(db, COMPANERO)
            self.p_extrano = self._proyecto(db, EXTRANO)
            self.i_yo = self._incidencia(db, YO)
            self.i_companero = self._incidencia(db, COMPANERO)
            self.i_extrano = self._incidencia(db, EXTRANO)
            for id_proyect, id_user in ((self.p_yo, YO), (self.p_companero, COMPANERO), (self.p_extrano, EXTRANO)):
                db.add(SupervisorActivityLog(id_proyect=id_proyect, id_supervisor=id_user,
                                             activity_date=date(2026, 10, 1), description="x", created_by=id_user))

    @staticmethod
    def _proyecto(db, dueno):
        p = Proyect(id_customer_supplier=1, leader=dueno, proyect_description="P%s" % dueno, created_by=dueno)
        db.add(p)
        db.flush()
        return p.id_proyect

    @staticmethod
    def _incidencia(db, dueno):
        i = Incident(id_incident_type=1, id_user=dueno, created_by=dueno)
        db.add(i)
        db.flush()
        return i.id_incident

    def _equipo(self, *miembros):
        with transaction_context() as db:
            equipo = Team(team_description="Taller", created_by=1)
            db.add(equipo)
            db.flush()
            for id_user in miembros:
                db.add(NmTeamUser(id_team=equipo.id_team, id_user=id_user, created_by=1))

    @property
    def actor(self):
        return {"id_user": YO, "id_permission": ROL, "user_type": "employee"}

    def proyectos(self):
        return set(visible_project_ids(self.actor))

    def incidencias(self):
        with transaction_context() as db:
            return {i.id_incident for i in scoped_incident_query(db, self.actor).all()}

    def bitacoras(self):
        with transaction_context() as db:
            gente = companeros(db, self.actor, "daily_activity_log")
        return {a.id_proyect for a in get_activities_by_range(ids_supervisor=sorted(gente))}


class TestMisGrupos(Base):
    CELDA = 2

    def test_projects_include_the_teammates(self):
        self._equipo(YO, COMPANERO)
        self.assertEqual({self.p_yo, self.p_companero}, self.proyectos())

    def test_incidents_include_the_teammates(self):
        self._equipo(YO, COMPANERO)
        self.assertEqual({self.i_yo, self.i_companero}, self.incidencias())

    def test_the_activity_log_includes_the_teammates(self):
        self._equipo(YO, COMPANERO)
        self.assertEqual({self.p_yo, self.p_companero}, self.bitacoras())

    def test_a_teammates_incident_can_be_opened(self):
        self._equipo(YO, COMPANERO)
        self.assertEqual(self.i_companero, require_incident_access(self.i_companero, self.actor).id_incident)

    def test_someone_outside_the_team_stays_hidden(self):
        self._equipo(YO, COMPANERO)
        self.assertNotIn(self.p_extrano, self.proyectos())
        self.assertNotIn(self.i_extrano, self.incidencias())
        with self.assertRaises(AppError):
            require_incident_access(self.i_extrano, self.actor)

    def test_without_a_team_it_is_the_same_as_before(self):
        self.assertEqual({self.p_yo}, self.proyectos())
        self.assertEqual({self.i_yo}, self.incidencias())
        self.assertEqual({self.p_yo}, self.bitacoras())

    def test_two_teams_add_up(self):
        self._equipo(YO, COMPANERO)
        self._equipo(YO, EXTRANO)
        self.assertEqual({self.p_yo, self.p_companero, self.p_extrano}, self.proyectos())


class TestPropiosYTodosNoCambianLaReglaDeAntes(Base):
    def test_todos_widens_projects_but_not_incidents_or_the_log(self):
        """Proyectos: la celda `scope_read` manda (desde 2026-10-16), asi que
        Todos ve todos. Incidencias y bitacora conservan su regla de antes."""
        self._equipo(YO, COMPANERO)
        self.assertEqual({self.p_yo, self.p_companero, self.p_extrano}, self.proyectos())
        self.assertEqual({self.i_yo}, self.incidencias())
        self.assertEqual({self.p_yo}, self.bitacoras())

    def test_propios_is_the_same(self):
        with transaction_context() as db:
            db.query(EntityPermission).filter(EntityPermission.id_permission == ROL).update({"scope_read": 1})
        self._equipo(YO, COMPANERO)
        self.assertEqual({self.p_yo}, self.proyectos())
        self.assertEqual({self.i_yo}, self.incidencias())
