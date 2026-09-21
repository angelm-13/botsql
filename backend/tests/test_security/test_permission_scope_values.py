"""Cada valor de alcance (0/1/2/4), por separado, contra el guardia real.

`entity_permission` reemplazo el viejo `control_type` (mascara de un bit por
accion) por 4 columnas de alcance (`scope_create/read/update/delete`), cada
una 0 Sin acceso / 1 Propios / 2 Mis grupos / 4 Todos. Esta migracion (Fase 1)
NO conecta todavia un filtrado real por Propios/Mis grupos/Todos -- el guardia
de `require_entity_permission` sigue siendo booleano: 0 deniega, cualquier
otro valor permite.

Esta prueba documenta esa frontera a proposito: confirma que 0 deniega y que
1/2/4 hoy permiten POR IGUAL (todavia no distinguen el alcance real). Cuando
una fase futura conecte el filtrado, esta prueba es la que hay que revisar
primero -- si empieza a fallar porque 1/2/4 ya no se comportan igual, es la
senal de que el alcance real ya esta conectado.
"""

from __future__ import annotations

import unittest

import jwt

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

PERFIL = 501


class TestPermissionScopeValues(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=PERFIL, entity_name="team",
                scope_create=0, scope_read=0, scope_update=0, scope_delete=0,
                created_by=1,
            ))

    def token(self):
        return jwt.encode(
            {"id_user": 999, "id_permission": PERFIL, "user_type": "employee"},
            SECRET_KEY, algorithm="HS256",
        )

    def headers(self):
        return {"Authorization": f"Bearer {self.token()}"}

    def set_scope_read(self, value):
        with transaction_context() as db:
            row = (
                db.query(EntityPermission)
                .filter(EntityPermission.id_permission == PERFIL)
                .filter(EntityPermission.entity_name == "team")
                .first()
            )
            row.scope_read = value

    def test_scope_zero_denies_read(self):
        self.set_scope_read(0)
        response = self.client.get("/team/", headers=self.headers())
        self.assertEqual(403, response.status_code)

    def test_scope_own_permits_read_today(self):
        self.set_scope_read(1)
        response = self.client.get("/team/", headers=self.headers())
        self.assertEqual(200, response.status_code)

    def test_scope_groups_permits_read_today(self):
        self.set_scope_read(2)
        response = self.client.get("/team/", headers=self.headers())
        self.assertEqual(200, response.status_code)

    def test_scope_all_permits_read_today(self):
        self.set_scope_read(4)
        response = self.client.get("/team/", headers=self.headers())
        self.assertEqual(200, response.status_code)

    def test_the_four_actions_gate_independently(self):
        """Alcance en Leer no presta acceso a Crear/Actualizar/Eliminar."""
        with transaction_context() as db:
            row = (
                db.query(EntityPermission)
                .filter(EntityPermission.id_permission == PERFIL)
                .filter(EntityPermission.entity_name == "team")
                .first()
            )
            row.scope_read = 4
            row.scope_create = 0
            row.scope_update = 0
            row.scope_delete = 0

        self.assertEqual(200, self.client.get("/team/", headers=self.headers()).status_code)
        self.assertEqual(
            403,
            self.client.post("/team/", json={"team_description": "x"}, headers=self.headers()).status_code,
        )
        self.assertEqual(
            403,
            self.client.put("/team/1", json={"team_description": "x"}, headers=self.headers()).status_code,
        )
        self.assertEqual(403, self.client.delete("/team/1", headers=self.headers()).status_code)


if __name__ == "__main__":
    unittest.main()
