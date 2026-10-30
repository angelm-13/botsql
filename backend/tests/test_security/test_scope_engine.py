"""El motor de alcance (app/utils/scope.py) y las reglas de que alcance admite cada fila.

Cubre: cada valor de alcance por separado (0/1/2/4) y su suma (3, 5), un usuario
en varios equipos, un usuario sin equipo, membresias y equipos dados de baja, y
que las capacidades y las pantallas de administracion no admitan Propios/Mis
grupos.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from app.models.entity_permission import EntityPermission
from app.models.nm_team_user import NmTeamUser
from app.models.session import transaction_context
from app.models.team import Team
from app.services.entity_permission_service import EntityPermissionService
from app.utils.errors import AppError
from app.utils.scope import (
    SCOPE_ALL, SCOPE_GROUPS, SCOPE_NONE, SCOPE_OWN,
    owner_ids, scope_bits, team_member_ids,
)
from tests.conftest import BackendTestCase

ROL = 601


def _equipo(db, nombre, miembros, baja=False):
    equipo = Team(team_description=nombre, created_by=1)
    if baja:
        equipo.deletion_date = datetime.utcnow()
    db.add(equipo)
    db.flush()
    for id_user in miembros:
        db.add(NmTeamUser(id_team=equipo.id_team, id_user=id_user, created_by=1))
    return equipo


class TestEquipos(BackendTestCase):
    def test_a_user_without_team_only_has_themselves(self):
        with transaction_context() as db:
            self.assertEqual({7}, team_member_ids(db, 7))

    def test_a_user_in_two_teams_gets_the_union_of_both(self):
        with transaction_context() as db:
            _equipo(db, "Taller A", [1, 2])
            _equipo(db, "Taller B", [1, 3])
        with transaction_context() as db:
            self.assertEqual({1, 2, 3}, team_member_ids(db, 1))
            # Quien solo esta en A no ve a quien solo esta en B.
            self.assertEqual({1, 2}, team_member_ids(db, 2))
            self.assertEqual({1, 3}, team_member_ids(db, 3))

    def test_a_deleted_team_does_not_count(self):
        with transaction_context() as db:
            _equipo(db, "Viejo", [1, 2], baja=True)
        with transaction_context() as db:
            self.assertEqual({1}, team_member_ids(db, 1))

    def test_a_deleted_membership_does_not_count(self):
        with transaction_context() as db:
            equipo = _equipo(db, "Taller", [1, 2])
            fila = (
                db.query(NmTeamUser)
                .filter(NmTeamUser.id_team == equipo.id_team, NmTeamUser.id_user == 2)
                .first()
            )
            fila.deletion_date = datetime.utcnow()
        with transaction_context() as db:
            self.assertEqual({1}, team_member_ids(db, 1))


class TestOwnerIds(BackendTestCase):
    ACTOR = {"id_user": 1, "id_permission": ROL}

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            _equipo(db, "Taller", [1, 2])

    def test_sin_acceso_covers_nobody(self):
        with transaction_context() as db:
            self.assertEqual(set(), owner_ids(db, self.ACTOR, SCOPE_NONE))

    def test_propios_covers_only_the_actor(self):
        with transaction_context() as db:
            self.assertEqual({1}, owner_ids(db, self.ACTOR, SCOPE_OWN))

    def test_mis_grupos_covers_the_team(self):
        with transaction_context() as db:
            self.assertEqual({1, 2}, owner_ids(db, self.ACTOR, SCOPE_GROUPS))

    def test_todos_means_no_filter(self):
        with transaction_context() as db:
            self.assertIsNone(owner_ids(db, self.ACTOR, SCOPE_ALL))

    def test_a_sum_of_bits_is_the_union(self):
        """3 = Propios + Mis grupos; cualquier valor con el bit 4 ve todo."""
        with transaction_context() as db:
            self.assertEqual({1, 2}, owner_ids(db, self.ACTOR, SCOPE_OWN | SCOPE_GROUPS))
            self.assertIsNone(owner_ids(db, self.ACTOR, SCOPE_OWN | SCOPE_ALL))
            self.assertIsNone(owner_ids(db, self.ACTOR, SCOPE_GROUPS | SCOPE_ALL))

    def test_an_actor_without_id_covers_nobody(self):
        with transaction_context() as db:
            self.assertEqual(set(), owner_ids(db, {"id_permission": ROL}, SCOPE_OWN))


class TestScopeBits(BackendTestCase):
    def test_reads_the_scope_of_each_action_independently(self):
        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=ROL, entity_name="incident",
                scope_create=1, scope_read=2, scope_update=4, scope_delete=0,
                created_by=1,
            ))
        actor = {"id_user": 1, "id_permission": ROL}
        with transaction_context() as db:
            self.assertEqual(1, scope_bits(db, actor, "incident", "create"))
            self.assertEqual(2, scope_bits(db, actor, "incident", "read"))
            self.assertEqual(4, scope_bits(db, actor, "incident", "update"))
            self.assertEqual(0, scope_bits(db, actor, "incident", "delete"))

    def test_a_role_without_the_row_has_no_access(self):
        with transaction_context() as db:
            self.assertEqual(0, scope_bits(db, {"id_user": 1, "id_permission": ROL}, "incident", "read"))

    def test_a_superuser_sees_everything(self):
        with transaction_context() as db:
            self.assertEqual(SCOPE_ALL, scope_bits(db, {"id_user": 1, "is_superuser": True}, "incident", "read"))


class TestQueAlcanceAdmiteCadaFila(BackendTestCase):
    def _crear(self, entidad, **escopes):
        payload = {"id_permission": ROL, "entity_name": entidad,
                   "scope_create": 0, "scope_read": 0, "scope_update": 0, "scope_delete": 0}
        payload.update(escopes)
        return EntityPermissionService.create(payload, user_id=1)

    def test_a_capability_rejects_propios_and_mis_grupos(self):
        for valor in (SCOPE_OWN, SCOPE_GROUPS):
            with self.subTest(valor=valor):
                with self.assertRaises(AppError) as caja:
                    self._crear("warehouse_voucher_authorize", scope_read=valor)
                self.assertEqual("errors.permission_scope_only_all", caja.exception.message_key)

    def test_a_capability_accepts_sin_acceso_and_todos(self):
        self._crear("warehouse_voucher_authorize", scope_read=SCOPE_ALL)
        with transaction_context() as db:
            self.assertEqual(SCOPE_ALL, scope_bits(db, {"id_user": 1, "id_permission": ROL}, "warehouse_voucher_authorize", "read"))

    def test_the_admin_screens_cannot_be_narrowed(self):
        for entidad in ("entity_permission", "permission", "team", "nm_team_user"):
            with self.subTest(entidad=entidad):
                with self.assertRaises(AppError):
                    self._crear(entidad, scope_read=SCOPE_OWN)

    def test_an_ordinary_entity_accepts_every_level_and_sums(self):
        for valor in (0, 1, 2, 3, 4):
            with self.subTest(valor=valor):
                fila = self._crear("incident", scope_read=valor)
                self.assertEqual(valor, fila["scope_read"])
                with transaction_context() as db:
                    db.query(EntityPermission).filter(
                        EntityPermission.id_permission == ROL,
                        EntityPermission.entity_name == "incident",
                    ).delete()


class TestQueModulosSoportanPropios(BackendTestCase):
    def test_the_catalog_flags_only_the_modules_that_really_filter(self):
        from app.modules.catalogo import catalogo_base
        from app.utils.scope import ENTIDADES_CON_ALCANCE_DE_DUENO

        entidades = {e["entity_name"]: e for e in catalogo_base()["entities"]}
        con_alcance = {n for n, e in entidades.items() if e["supports_owner_scope"]}
        self.assertEqual(set(ENTIDADES_CON_ALCANCE_DE_DUENO), con_alcance)
        self.assertIn("warehouse_prevoucher", con_alcance)

    def test_a_capability_is_only_flagged_when_it_really_filters(self):
        from app.modules.catalogo import catalogo_base
        from app.utils.scope import ENTIDADES_CON_ALCANCE_DE_DUENO

        for e in catalogo_base()["entities"]:
            if e["permission_scope"] == "actions_only" and e["entity_name"] not in ENTIDADES_CON_ALCANCE_DE_DUENO:
                self.assertFalse(e["supports_owner_scope"], e["entity_name"])

    def test_the_prevoucher_capability_accepts_mis_grupos(self):
        EntityPermissionService.create({"id_permission": ROL, "entity_name": "warehouse_prevoucher",
                                        "scope_create": 4, "scope_read": SCOPE_GROUPS,
                                        "scope_update": 0, "scope_delete": 0}, user_id=1)

    def test_saving_a_role_keeps_a_legacy_value_that_was_already_stored(self):
        """Un 1 o 2 puesto antes de esta regla no impide guardar el resto del rol."""
        with transaction_context() as db:
            fila = EntityPermission(id_permission=ROL, entity_name="warehouse_voucher_authorize",
                                    scope_create=0, scope_read=1, scope_update=0, scope_delete=0, created_by=1)
            db.add(fila)
            db.flush()
            id_fila = fila.id_entity_permission
        EntityPermissionService.update(id_fila, {"scope_read": 1, "scope_update": 4}, user_id=1)
        with transaction_context() as db:
            self.assertEqual(4, db.get(EntityPermission, id_fila).scope_update)
        with self.assertRaises(AppError):
            EntityPermissionService.update(id_fila, {"scope_read": 2}, user_id=1)


if __name__ == "__main__":
    unittest.main()
