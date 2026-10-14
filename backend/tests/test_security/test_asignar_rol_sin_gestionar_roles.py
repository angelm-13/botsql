"""Quien da de alta usuarios elige un rol sin poder administrar el catalogo de roles.

Caso real (comala-prod): el administrador del cliente veia el desplegable
"Rol/perfil" vacio aunque el Gestor le daba permiso sobre `permission`. El
filtro de protecion trataba `id_level == 1` como "nivel de superusuario", pero
`permission.id_level` nace con DEFAULT 1 (el nivel 'General'): todos los roles
quedaban escondidos para quien no fuera el bootstrap.

Ahora solo el rol bootstrap (id 1) esta protegido, y `/permission/options`
permite elegir un rol sin permiso de entidad -- igual que `/user/options`.
"""
from __future__ import annotations

from datetime import datetime

import jwt

from app.models.entity_permission import EntityPermission
from app.models.permission import Permission
from app.models.session import transaction_context
from app.models.user import User
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

ADMINISTRATOR, OPERADOR, RETIRADO = 1, 2, 3
ROL_DEL_ACTOR = 501


def _rol(id_permission, descripcion, **extra):
    # Todos con id_level=1: es el DEFAULT con el que nace cualquier rol.
    return Permission(id_permission=id_permission, permission_description=descripcion,
                      created_by=1, authorized_by=1, id_department=1, id_subdepartment=1,
                      id_level=1, **extra)


def _usuario(id_user, id_permission):
    return User(id_user=id_user, created_by=1, id_permission=id_permission,
                full_name="Persona %d" % id_user, username="persona%d" % id_user,
                id_proyect=1, supervisor=1, id_status=1)


class TestAsignarRolSinGestionarRoles(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                _rol(ADMINISTRATOR, "Administrator"),
                _rol(OPERADOR, "Operador"),
                _rol(RETIRADO, "Retirado", deletion_date=datetime.utcnow()),
                # El administrador del cliente: opera usuarios y SOLO LEE roles.
                EntityPermission(id_permission=ROL_DEL_ACTOR, entity_name="user",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=ROL_DEL_ACTOR, entity_name="permission",
                                 scope_create=0, scope_read=4, scope_update=0, scope_delete=0,
                                 created_by=1),
                _usuario(71, OPERADOR),
                _usuario(72, ADMINISTRATOR),
            ])

    def _headers(self, **claims):
        claims.setdefault("id_user", 41)
        claims.setdefault("username", "cormur")
        claims.setdefault("id_permission", ROL_DEL_ACTOR)
        claims.setdefault("user_type", "admin")
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def _ids(self, respuesta):
        datos = self.json(respuesta)
        filas = datos["items"] if isinstance(datos, dict) else datos
        return [fila["id_permission"] for fila in filas]

    # --- /permission/options ---------------------------------------------------

    def test_a_role_without_permission_entity_can_list_the_options(self):
        headers = self._headers(id_permission=999)  # sin ninguna fila de entity_permission

        self.assertEqual(403, self.client.get("/permission/", headers=headers).status_code)

        respuesta = self.client.get("/permission/options", headers=headers)
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual([OPERADOR], self._ids(respuesta))

    def test_options_expose_only_id_and_description(self):
        for fila in self.json(self.client.get("/permission/options", headers=self._headers())):
            self.assertEqual({"id_permission", "permission_description"}, set(fila))

    def test_options_hide_the_bootstrap_role_and_retired_roles(self):
        ids = self._ids(self.client.get("/permission/options", headers=self._headers()))
        self.assertNotIn(ADMINISTRATOR, ids)
        self.assertNotIn(RETIRADO, ids)

    def test_the_bootstrap_actor_does_see_the_administrator_role(self):
        ids = self._ids(self.client.get("/permission/options", headers=self._headers(username="admin1")))
        self.assertIn(ADMINISTRATOR, ids)
        self.assertNotIn(RETIRADO, ids)

    def test_options_require_authentication(self):
        self.assertEqual(401, self.client.get("/permission/options").status_code)

    # --- el listado completo dejo de esconder todos los roles ------------------

    def test_a_reader_sees_roles_even_though_they_have_the_default_level(self):
        ids = self._ids(self.client.get("/permission/?per_page=100", headers=self._headers()))
        self.assertEqual([OPERADOR], ids)

    def test_a_reader_cannot_fetch_the_bootstrap_role(self):
        self.assertEqual(404, self.client.get("/permission/%d" % ADMINISTRATOR,
                                              headers=self._headers()).status_code)
        self.assertEqual(200, self.client.get("/permission/%d" % OPERADOR,
                                              headers=self._headers()).status_code)

    # --- ver el catalogo no es poder crear roles -------------------------------

    def test_reading_roles_does_not_allow_creating_updating_or_deleting_them(self):
        headers = self._headers()
        nuevo = {"created_by": 1, "authorized_by": 1, "permission_description": "Rol nuevo",
                 "id_department": 1, "id_subdepartment": 1, "id_level": 1}
        self.assertEqual(403, self.client.post("/permission/", json=nuevo, headers=headers).status_code)
        self.assertEqual(403, self.client.put("/permission/%d" % OPERADOR, json=nuevo,
                                              headers=headers).status_code)
        self.assertEqual(403, self.client.delete("/permission/%d" % OPERADOR,
                                                 headers=headers).status_code)

    # --- esconder el rol bootstrap en la pantalla no basta: la API tambien ------

    def test_a_non_bootstrap_actor_cannot_assign_the_bootstrap_role_to_a_new_user(self):
        respuesta = self.client.post(
            "/user/", headers=self._headers(),
            json={"username": "nuevo1", "full_name": "Nuevo Uno", "id_permission": ADMINISTRATOR,
                  "user_type": "employee"})
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.bootstrap_admin_protected", self.json(respuesta).get("error_key"))

    def test_a_non_bootstrap_actor_cannot_promote_an_existing_user_to_the_bootstrap_role(self):
        respuesta = self.client.put("/user/71", headers=self._headers(),
                                    json={"id_permission": ADMINISTRATOR})
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.bootstrap_admin_protected", self.json(respuesta).get("error_key"))

    def test_editing_a_user_who_already_has_the_role_does_not_trip_the_guard(self):
        # El formulario reenvia el mismo `id_permission` al editar otros campos.
        respuesta = self.client.put("/user/72", headers=self._headers(),
                                    json={"id_permission": ADMINISTRATOR, "puesto": "Direccion"})
        self.assertNotEqual("errors.bootstrap_admin_protected", self.json(respuesta).get("error_key"))

    def test_assigning_an_ordinary_role_is_not_blocked_by_the_guard(self):
        respuesta = self.client.put("/user/71", headers=self._headers(),
                                    json={"id_permission": OPERADOR, "puesto": "Operador de planta"})
        self.assertNotEqual("errors.bootstrap_admin_protected", self.json(respuesta).get("error_key"))
