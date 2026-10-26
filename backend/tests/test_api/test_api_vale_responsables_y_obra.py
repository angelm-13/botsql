"""El responsable de un vale sale de una designacion, y la obra dice quien la lleva.

* `GET /user/options?para=vale_responsable` solo ofrece a quien el Gestor de roles y
  permisos designo con `warehouse_voucher_holder`: un vale puede levantarse a nombre
  de un gerente, un jefe de taller o Compras, no solo del supervisor del proyecto.
* `GET /proyect/options` trae el nombre de quien esta a cargo de cada obra, para
  verlo en el desplegable "Proyecto" del vale.
"""
from __future__ import annotations

import jwt

from app.models import EntityPermission, Proyect, User
from app.models.session import transaction_context
from app.modules import registry
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.model_factory import build_model

DESIGNADO, SIN_DESIGNAR = 201, 202
ANA, BETO, CARLA, DANIEL = 11, 12, 13, 14


def _con_id(objeto, **ids):
    for campo, valor in ids.items():
        setattr(objeto, campo, valor)
    return objeto


class TestResponsablesDeVale(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=DESIGNADO, entity_name="warehouse_voucher_holder",
                                    scope_read=4, created_by=1))
            for id_user, nombre, permiso in ((ANA, "Ana Gerente", DESIGNADO),
                                             (BETO, "Beto Jefe", DESIGNADO),
                                             (CARLA, "Carla Chofer", SIN_DESIGNAR)):
                db.add(_con_id(build_model(User, username="u%d" % id_user, email="u%d@x.mx" % id_user,
                                           full_name=nombre, id_permission=permiso,
                                           user_type="user"), id_user=id_user))

    def _h(self, id_user=ANA):
        token = jwt.encode({"id_user": id_user, "id_permission": DESIGNADO}, SECRET_KEY,
                           algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def _nombres(self, ruta):
        respuesta = self.client.get(ruta, headers=self._h())
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return {u["full_name"] for u in self.json(respuesta)}

    def test_only_designated_users_are_offered_as_voucher_holders(self):
        nombres = self._nombres("/user/options?para=vale_responsable")
        self.assertEqual({"Ana Gerente", "Beto Jefe"}, nombres & {"Ana Gerente", "Beto Jefe", "Carla Chofer"})
        self.assertNotIn("Carla Chofer", nombres)

    def test_without_the_filter_everyone_is_listed_as_before(self):
        nombres = self._nombres("/user/options")
        self.assertTrue({"Ana Gerente", "Beto Jefe", "Carla Chofer"} <= nombres)

    def test_taking_the_designation_away_removes_the_user_from_the_list(self):
        with transaction_context() as db:
            fila = db.query(EntityPermission).filter_by(
                id_permission=DESIGNADO, entity_name="warehouse_voucher_holder").one()
            fila.scope_read = 0
        self.assertNotIn("Ana Gerente", self._nombres("/user/options?para=vale_responsable"))

    def test_the_designation_is_a_capability_the_role_manager_can_grant(self):
        claves = {c.clave for c in registry.CAPACIDADES}
        self.assertIn("warehouse_voucher_holder", claves)
        por_rol = {r.nombre: set(r.capacidades) for r in registry.ROLES}
        for rol in ("Supervisor", "Gerente Comercial", "Gerente Tecnico", "Jefe de taller", "Compras"):
            self.assertIn("warehouse_voucher_holder", por_rol[rol], rol)
        # Almacen opera los vales y Administrator administra: ninguno responde por ellos.
        for rol in ("Almacenista", "Administrator"):
            self.assertNotIn("warehouse_voucher_holder", por_rol[rol], rol)


class TestObraConQuienLaLleva(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for id_user, nombre in ((ANA, "Ana Supervisora"), (BETO, "Beto Lider"), (DANIEL, "Daniel Taller")):
                db.add(_con_id(build_model(User, username="u%d" % id_user, email="u%d@x.mx" % id_user,
                                           full_name=nombre, id_permission=DESIGNADO, user_type="user"),
                               id_user=id_user))
            db.flush()
            db.add_all([
                # Con quien la lleva (id_supervisor): ese es el que esta a cargo.
                _con_id(build_model(Proyect, created_by=BETO, leader=BETO, id_supervisor=DANIEL,
                                    proyect_status="in_progress", folio="PRJ-1", title="Con taller"),
                        id_proyect=101),
                # Sin nadie que la lleve: el que la lidera.
                _con_id(build_model(Proyect, created_by=ANA, leader=ANA,
                                    proyect_status="authorized", folio="PRJ-2", title="Sin taller"),
                        id_proyect=102),
            ])

    def _opciones(self):
        token = jwt.encode({"id_user": ANA, "id_permission": DESIGNADO}, SECRET_KEY, algorithm="HS256")
        respuesta = self.client.get("/proyect/options", headers={"Authorization": "Bearer %s" % token})
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return {p["id_proyect"]: p for p in self.json(respuesta)}

    def test_the_project_says_who_is_in_charge(self):
        obras = self._opciones()
        self.assertEqual("Daniel Taller", obras[101]["in_charge_name"])
        self.assertEqual(DANIEL, obras[101]["id_in_charge"])

    def test_without_a_runner_the_leader_is_in_charge(self):
        obras = self._opciones()
        self.assertEqual("Ana Supervisora", obras[102]["in_charge_name"])
        self.assertEqual(ANA, obras[102]["id_in_charge"])

