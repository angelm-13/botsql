"""Las membresias (`nm_team_user`) se rigen por el permiso de `team`, sin filtro de campos propio.

Un rol con `team` y sin ninguna fila de `nm_team_user` (el Gestor la oculta) lee, agrega y quita miembros.
"""

from __future__ import annotations

import jwt
from sqlalchemy.exc import IntegrityError

from app.models import EntityPermission, NmTeamUser, Team
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ROL_CON_EQUIPOS, ROL_SIN_EQUIPOS = 501, 502
ANA, BETO = 11, 12


def _headers(**claims):
    token = jwt.encode({"user_type": "employee", **claims}, SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


class MembresiasPorPermisoDeTeamTest(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=ROL_CON_EQUIPOS, entity_name="team",
                                 scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=ROL_SIN_EQUIPOS, entity_name="user",
                                 scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
            ])
            equipo = Team(team_description="Manzanillo 1", created_by=1)
            db.add(equipo)
            db.flush()
            self.id_team = equipo.id_team
        self.rol = _headers(id_user=21, id_permission=ROL_CON_EQUIPOS)
        self.otro = _headers(id_user=22, id_permission=ROL_SIN_EQUIPOS)
        self.admin = _headers(id_user=1, is_superuser=True)

    def _agrega(self, headers, **cuerpo):
        return self.client.post("/nm_team_user/", json={"id_team": self.id_team, "id_user": ANA, **cuerpo}, headers=headers)

    def _fila(self, id_):
        with transaction_context() as db:
            fila = db.get(NmTeamUser, id_)
            return None if fila is None else fila.serialize()

    def test_a_role_without_team_gets_403_on_every_route(self):
        creada = self.json(self._agrega(self.admin))["id_nm_team_user"]
        ruta = f"/nm_team_user/{creada}"
        self.assertEqual(403, self.client.get("/nm_team_user/", headers=self.otro).status_code)
        self.assertEqual(403, self.client.get(ruta, headers=self.otro).status_code)
        self.assertEqual(403, self._agrega(self.otro, id_user=BETO).status_code)
        self.assertEqual(403, self.client.put(ruta, json={"id_user": BETO}, headers=self.otro).status_code)
        self.assertEqual(403, self.client.delete(ruta, headers=self.otro).status_code)

    def test_a_role_with_team_reads_adds_and_removes_members(self):
        respuesta = self._agrega(self.rol)
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        creada = self.json(respuesta)
        self.assertEqual((self.id_team, ANA), (creada["id_team"], creada["id_user"]))

        lista = self.client.get("/nm_team_user/?per_page=100", headers=self.rol)
        self.assertEqual(200, lista.status_code)
        self.assertIn(creada["id_nm_team_user"], [f["id_nm_team_user"] for f in self.json(lista)["items"]])
        self.assertEqual(200, self.client.get(f"/nm_team_user/{creada['id_nm_team_user']}", headers=self.rol).status_code)

        self.assertEqual(200, self.client.delete(f"/nm_team_user/{creada['id_nm_team_user']}", headers=self.rol).status_code)

    def test_the_list_of_a_role_with_team_has_the_full_fields(self):
        self._agrega(self.rol)
        fila = self.json(self.client.get("/nm_team_user/?per_page=100", headers=self.rol))["items"][0]
        self.assertLessEqual({"id_nm_team_user", "id_team", "id_user", "creation_date"}, set(fila))
        self.assertEqual((self.id_team, ANA), (fila["id_team"], fila["id_user"]))

    def test_the_pair_is_written_whole_and_a_foreign_field_is_ignored(self):
        respuesta = self._agrega(self.rol, created_by=999, deletion_date="2020-01-01T00:00:00", campo_ajeno="x")
        self.assertEqual(201, respuesta.status_code, self.json(respuesta))
        fila = self._fila(self.json(respuesta)["id_nm_team_user"])
        self.assertEqual((self.id_team, ANA), (fila["id_team"], fila["id_user"]))
        self.assertNotIn("campo_ajeno", fila)
        self.assertNotEqual(999, fila["created_by"])
        self.assertIsNone(fila["deletion_date"])

    def test_deleting_is_a_soft_delete(self):
        id_ = self.json(self._agrega(self.rol))["id_nm_team_user"]
        self.assertEqual(200, self.client.delete(f"/nm_team_user/{id_}", headers=self.rol).status_code)
        fila = self._fila(id_)
        self.assertIsNotNone(fila, "la fila no debe borrarse fisicamente")
        self.assertIsNotNone(fila["deletion_date"])

    def test_an_active_membership_cannot_be_duplicated(self):
        self.assertEqual(201, self._agrega(self.rol).status_code)
        self.assertEqual(409, self._agrega(self.rol).status_code)
        # y el indice parcial unico lo impide aunque se salte el servicio
        with self.assertRaises(IntegrityError):
            with transaction_context() as db:
                db.add(NmTeamUser(id_team=self.id_team, id_user=ANA, created_by=1))

    def test_administrator_keeps_working(self):
        respuesta = self._agrega(self.admin)
        self.assertEqual(201, respuesta.status_code)
        self.assertEqual(200, self.client.get("/nm_team_user/", headers=self.admin).status_code)
        self.assertEqual(200, self.client.delete(f"/nm_team_user/{self.json(respuesta)['id_nm_team_user']}",
                                                 headers=self.admin).status_code)
