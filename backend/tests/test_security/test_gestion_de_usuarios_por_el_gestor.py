"""Quien gestiona usuarios lo decide el Gestor; el codigo solo protege al Administrator.

Antes una jerarquia por `user_type` (admin 80 > client/supplier 50 > employee 40)
dejaba a un Gerente (`employee`) sin poder gestionar a otro `employee` aunque el
Gestor le concediera `user`. Ahora: con `user` en el Gestor, un Gerente da de alta,
edita y borra a Supervisor, Almacenista y a otro Gerente; lo unico fijo es que a
quien tiene el rol Administrator solo lo gestionan otro Administrator o el
superusuario, y que nadie se cambia a si mismo el rol.
Ver `docs/propuestas/2026-10-15_quien_gestiona_a_quien_sin_user_type.md`.
"""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.field import Field
from app.models.nm_field_permission import NmFieldPermission
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.user import User
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ADMINISTRATOR, OPERADOR, GERENTE, SUPERVISOR, SIN_PERMISO = 1, 2, 3, 4, 5
ACTOR = 41          # el Gerente que actua
OTRO_GERENTE, UN_SUPERVISOR, UN_ADMINISTRATOR, UN_OPERADOR = 42, 43, 44, 45
CAMPOS = ("id_permission", "username", "full_name", "user_type", "email", "password",
          "id_proyect", "supervisor", "id_status")


def _rol(id_permission, descripcion):
    return Permission(id_permission=id_permission, permission_description=descripcion,
                      created_by=1, authorized_by=1, id_department=1, id_subdepartment=1, id_level=1)


def _usuario(id_user, id_permission, user_type="employee"):
    return User(id_user=id_user, created_by=1, id_permission=id_permission, user_type=user_type,
                full_name="Persona %d" % id_user, username="persona%d" % id_user,
                id_proyect=1, supervisor=1, id_status=1)


def _permisos_de_usuarios(id_permission, c=4, r=4, u=4, d=4):
    return [
        EntityPermission(id_permission=id_permission, entity_name="user", scope_create=c,
                         scope_read=r, scope_update=u, scope_delete=d, created_by=1),
        EntityPermission(id_permission=id_permission, entity_name="permission", scope_read=4, created_by=1),
    ]


class TestGestionDeUsuariosPorElGestor(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                _rol(ADMINISTRATOR, "Administrator"), _rol(OPERADOR, "Operador"),
                _rol(GERENTE, "Gerente"), _rol(SUPERVISOR, "Supervisor"), _rol(SIN_PERMISO, "Sin permiso"),
                *_permisos_de_usuarios(GERENTE),
                *_permisos_de_usuarios(ADMINISTRATOR),
                _usuario(ACTOR, GERENTE), _usuario(OTRO_GERENTE, GERENTE),
                _usuario(UN_SUPERVISOR, SUPERVISOR), _usuario(UN_OPERADOR, OPERADOR),
                _usuario(UN_ADMINISTRATOR, ADMINISTRATOR, user_type="admin"),
            ])
            campos = [Field(table_name="user", field_name=nombre, created_by=1) for nombre in CAMPOS]
            db.add_all(campos)
            db.flush()
            for rol in (GERENTE, ADMINISTRATOR):
                db.add_all([NmFieldPermission(id_field=campo.id_field, id_permission=rol,
                                              control_type="7", created_by=1) for campo in campos])

    def _headers(self, id_permission=GERENTE, id_user=ACTOR, **claims):
        claims = {"id_user": id_user, "username": "persona%d" % id_user, "user_type": "employee",
                  "id_permission": id_permission, **claims}
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def _editar(self, id_user, headers=None, **cambios):
        return self.client.put("/user/%d" % id_user, headers=headers or self._headers(),
                               json=cambios or {"full_name": "Editado"})

    # --- el Gestor decide, sin importar el tipo de cuenta ---------------------

    def test_a_manager_edits_a_supervisor_and_another_manager(self):
        self.assertEqual(200, self._editar(UN_SUPERVISOR).status_code)
        self.assertEqual(200, self._editar(OTRO_GERENTE).status_code)

    def test_the_account_type_changes_nothing(self):
        for tipo in ("employee", "admin", "client", None):
            with self.subTest(user_type=tipo):
                respuesta = self._editar(UN_SUPERVISOR, headers=self._headers(user_type=tipo))
                self.assertEqual(200, respuesta.status_code)

    def test_a_manager_deletes_a_supervisor(self):
        respuesta = self.client.delete("/user/%d" % UN_OPERADOR, headers=self._headers())

        self.assertEqual(200, respuesta.status_code)

    def test_a_manager_creates_an_operator(self):
        respuesta = self.client.post("/user/", headers=self._headers(), json={
            "username": "nuevo1", "full_name": "Nuevo Uno", "id_permission": OPERADOR, "user_type": "employee",
            "password": "Cambiar123", "id_proyect": 1, "supervisor": 1, "id_status": 1})

        self.assertIn(respuesta.status_code, (200, 201), respuesta.get_data(as_text=True))

    def test_without_user_in_the_role_manager_even_an_admin_type_is_denied(self):
        headers = self._headers(id_permission=SIN_PERMISO, user_type="admin")

        self.assertEqual(403, self._editar(UN_SUPERVISOR, headers=headers).status_code)
        self.assertEqual(403, self.client.delete("/user/%d" % UN_OPERADOR, headers=headers).status_code)

    # --- lo unico fijo: el rol Administrator ----------------------------------

    def test_a_manager_cannot_touch_an_administrator(self):
        self.assertEqual(403, self._editar(UN_ADMINISTRATOR).status_code)
        self.assertEqual(403, self.client.delete("/user/%d" % UN_ADMINISTRATOR, headers=self._headers()).status_code)
        self.assertEqual(403, self.client.post("/auth/mfa/reset/%d" % UN_ADMINISTRATOR,
                                               headers=self._headers()).status_code)

    def test_a_manager_cannot_create_an_administrator(self):
        respuesta = self.client.post("/user/", headers=self._headers(), json={
            "username": "nuevo2", "full_name": "Nuevo Dos", "id_permission": ADMINISTRATOR,
            "user_type": "employee"})

        self.assertEqual(403, respuesta.status_code)

    def test_an_administrator_still_manages_other_administrators(self):
        headers = self._headers(id_permission=ADMINISTRATOR, id_user=1, user_type="admin")

        self.assertEqual(200, self._editar(UN_ADMINISTRATOR, headers=headers).status_code)
        self.assertEqual(200, self._editar(UN_SUPERVISOR, headers=headers).status_code)

    def test_nobody_changes_their_own_role(self):
        respuesta = self._editar(ACTOR, id_permission=OPERADOR)

        self.assertEqual(403, respuesta.status_code)
        # Editar otros datos propios, en cambio, esta bien.
        self.assertEqual(200, self._editar(ACTOR, full_name="Yo mismo").status_code)
