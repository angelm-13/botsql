"""Quien es el "dueno" de un vale para quien solo pide material, y "Mis grupos".

Dueno = su responsable (`id_user`), quien lo capturo (`created_by`) o quien recoge
la herramienta de algun renglon (`id_user_delivered_to`). Con Mis grupos en
`warehouse_prevoucher`, tambien los vales de los companeros de equipo. Con
Propios (o el 4 de siempre), solo los suyos. Quien opera el almacen ve todo.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import jwt

from app.models import Incident
from app.models.entity_permission import EntityPermission
from app.models.nm_incident_product import NmIncidentProduct
from app.models.nm_team_user import NmTeamUser
from app.models.session import transaction_context
from app.models.team import Team
from app.models.user import User
from app.services.entity_permission_service import EntityPermissionService
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.conftest import BackendTestCase

SOLICITANTE = 11
COMPANERO = 12
EXTRANO = 13
ROL_SOLICITANTE = 201
ROL_ALMACEN = 401


def _headers(**claims):
    return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}


class BaseDuenoDelVale(BackendTestCase):
    SCOPE_PREVALE = 4

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=ROL_SOLICITANTE, entity_name="warehouse_prevoucher",
                                 scope_create=4, scope_read=self.SCOPE_PREVALE, scope_update=4, created_by=1),
                EntityPermission(id_permission=ROL_ALMACEN, entity_name="warehouse_voucher",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
            ])
            # Responsable distinto de quien lo capturo, y viceversa.
            self.propio = self._vale(id_user=SOLICITANTE, created_by=1, folio="9101", db=db)
            self.capturado_por_mi = self._vale(id_user=EXTRANO, created_by=SOLICITANTE, folio="9102", db=db)
            self.del_companero = self._vale(id_user=COMPANERO, created_by=1, folio="9103", db=db)
            self.ajeno = self._vale(id_user=EXTRANO, created_by=1, folio="9104", db=db)
            self.recogido_por_mi = self._vale(id_user=EXTRANO, created_by=1, folio="9105", db=db)
            db.add(NmIncidentProduct(
                id_incident=self.recogido_por_mi, id_product=1, quantity=1, created_by=1,
                id_user_delivered_to=SOLICITANTE,
            ))

    @staticmethod
    def _vale(*, id_user, created_by, folio, db):
        vale = Incident(id_incident_type=1, id_user=id_user, created_by=created_by, external_folio=folio)
        db.add(vale)
        db.flush()
        return vale.id_incident

    def _equipo(self, *miembros):
        with transaction_context() as db:
            equipo = Team(team_description="Taller", created_by=1)
            db.add(equipo)
            db.flush()
            for id_user in miembros:
                db.add(NmTeamUser(id_team=equipo.id_team, id_user=id_user, created_by=1))

    def _abre(self, id_incident, **claims):
        claims.setdefault("id_user", SOLICITANTE)
        claims.setdefault("id_permission", ROL_SOLICITANTE)
        return self.client.get("/vouchers/%s" % id_incident, headers=_headers(**claims)).status_code


class TestDuenoDelVale(BaseDuenoDelVale):
    def test_the_responsible_opens_the_voucher(self):
        self.assertEqual(200, self._abre(self.propio))

    def test_whoever_captured_it_opens_it_even_when_it_is_in_someone_elses_name(self):
        self.assertEqual(200, self._abre(self.capturado_por_mi))

    def test_whoever_picks_up_a_line_opens_it(self):
        self.assertEqual(200, self._abre(self.recogido_por_mi))

    def test_a_stranger_voucher_is_not_found(self):
        self.assertEqual(404, self._abre(self.ajeno))

    def test_a_teammates_voucher_is_not_visible_without_mis_grupos(self):
        self._equipo(SOLICITANTE, COMPANERO)
        self.assertEqual(404, self._abre(self.del_companero))

    def test_the_warehouse_operator_opens_any_voucher(self):
        self.assertEqual(200, self._abre(self.ajeno, id_user=31, id_permission=ROL_ALMACEN))

    def test_the_list_only_shows_the_actors_vouchers(self):
        r = self.client.get("/vouchers", headers=_headers(id_user=SOLICITANTE, id_permission=ROL_SOLICITANTE))
        self.assertEqual(200, r.status_code)
        self.assertTrue(self.json(r).get("scoped_to_actor"))


class TestMisGruposEnElPrevale(BaseDuenoDelVale):
    SCOPE_PREVALE = 2

    def test_a_teammates_voucher_is_visible(self):
        self._equipo(SOLICITANTE, COMPANERO)
        self.assertEqual(200, self._abre(self.del_companero))

    def test_a_voucher_of_someone_outside_the_team_is_not(self):
        self._equipo(SOLICITANTE, COMPANERO)
        self.assertEqual(404, self._abre(self.ajeno))

    def test_without_a_team_it_is_the_same_as_propios(self):
        self.assertEqual(404, self._abre(self.del_companero))
        self.assertEqual(200, self._abre(self.propio))

    def test_a_user_in_two_teams_sees_both_teams(self):
        self._equipo(SOLICITANTE, COMPANERO)
        self._equipo(SOLICITANTE, EXTRANO)
        self.assertEqual(200, self._abre(self.del_companero))
        self.assertEqual(200, self._abre(self.ajeno))

    def test_a_removed_team_stops_sharing(self):
        self._equipo(SOLICITANTE, COMPANERO)
        with transaction_context() as db:
            db.query(Team).update({"deletion_date": datetime.utcnow()})
        self.assertEqual(404, self._abre(self.del_companero))


class TestPropiosEnElPrevale(BaseDuenoDelVale):
    SCOPE_PREVALE = 1

    def test_propios_never_shares_with_the_team(self):
        self._equipo(SOLICITANTE, COMPANERO)
        self.assertEqual(404, self._abre(self.del_companero))
        self.assertEqual(200, self._abre(self.propio))


class TestVencidosPorDueno(BaseDuenoDelVale):
    def setUp(self):
        super().setUp()
        ayer = datetime.now() - timedelta(days=2)
        with transaction_context() as db:
            for id_vale in (self.propio, self.ajeno):
                db.add(NmIncidentProduct(
                    id_incident=id_vale, id_product=1, quantity=1, created_by=1,
                    direction="salida", due_date=ayer,
                ))

    def _vencidos(self, **claims):
        r = self.client.get("/vouchers/overdue", headers=_headers(**claims))
        self.assertEqual(200, r.status_code)
        return {i["id_incident"] for i in self.json(r)["items"]}

    def test_a_requester_only_sees_his_overdue_lines(self):
        vistos = self._vencidos(id_user=SOLICITANTE, id_permission=ROL_SOLICITANTE)
        self.assertIn(self.propio, vistos)
        self.assertNotIn(self.ajeno, vistos)

    def test_the_warehouse_operator_sees_all_of_them(self):
        vistos = self._vencidos(id_user=31, id_permission=ROL_ALMACEN)
        self.assertLessEqual({self.propio, self.ajeno}, vistos)


class TestAntiBloqueoDelGestor(BackendTestCase):
    ROL_ADMIN = 701
    ROL_OTRO = 702

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(User(
                id_user=51, created_by=1, id_permission=self.ROL_ADMIN, full_name="Admin Gestor",
                id_proyect=1, supervisor=1, id_status=1,
            ))
            propio = EntityPermission(id_permission=self.ROL_ADMIN, entity_name="entity_permission",
                                      scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1)
            ajeno = EntityPermission(id_permission=self.ROL_OTRO, entity_name="entity_permission",
                                     scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1)
            db.add_all([propio, ajeno])
            db.flush()
            self.id_propio, self.id_ajeno = propio.id_entity_permission, ajeno.id_entity_permission

    def test_an_admin_cannot_remove_their_own_access_to_the_manager(self):
        for columna in ("scope_read", "scope_update"):
            with self.subTest(columna=columna):
                with self.assertRaises(AppError) as caja:
                    EntityPermissionService.update(self.id_propio, {columna: 0}, user_id=51)
                self.assertEqual("errors.permission_manager_lockout", caja.exception.message_key)

    def test_an_admin_can_narrow_another_role_on_the_manager(self):
        EntityPermissionService.update(self.id_ajeno, {"scope_read": 0}, user_id=51)
        with transaction_context() as db:
            self.assertEqual(0, db.get(EntityPermission, self.id_ajeno).scope_read)

    def test_an_admin_can_still_change_other_actions_of_their_own_role(self):
        EntityPermissionService.update(self.id_propio, {"scope_delete": 0}, user_id=51)
        with transaction_context() as db:
            self.assertEqual(0, db.get(EntityPermission, self.id_propio).scope_delete)
