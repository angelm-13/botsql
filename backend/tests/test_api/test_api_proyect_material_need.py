"""La lista de necesidades de material por proyecto y la vista "Por comprar".

Dos preguntas distintas:

* El supervisor declara lo que necesita SU proyecto. Puede pedir mas de lo que hay
  -- para eso sirve la lista: avisar el faltante --, no puede tocar proyectos
  ajenos, y no se duplica el mismo material en un proyecto.
* Quien compra ve las necesidades de TODOS los proyectos contra la existencia, con
  la capacidad `purchase_planning` y sin necesidad de abrir cada proyecto.
"""
from __future__ import annotations

import jwt

from app.models import (
    EntityPermission, InventoryStock, Material, Product, Proyect,
)
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.model_factory import build_model

SUPERVISOR, COMPRAS, NADIE = 201, 301, 401
USUARIO_SUPERVISOR, USUARIO_AJENO, USUARIO_COMPRAS = 11, 12, 21
PROYECTO_PROPIO, PROYECTO_AJENO = 10, 20
DISCO, TORNILLO, CABLE = 1, 2, 3


def _con_id(objeto, **ids):
    """`build_model` ignora las llaves autoincrementales: se asignan despues."""
    for campo, valor in ids.items():
        setattr(objeto, campo, valor)
    return objeto


class TestListaDeNecesidades(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Supervisor: CAPTURA sobre la entidad, como la da `operaciones`.
                EntityPermission(id_permission=SUPERVISOR, entity_name="proyect_material_need",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Compras: solo lee la entidad y tiene la capacidad de "Por comprar".
                EntityPermission(id_permission=COMPRAS, entity_name="proyect_material_need",
                                 scope_read=4, created_by=1),
                EntityPermission(id_permission=COMPRAS, entity_name="purchase_planning",
                                 scope_read=4, created_by=1),
                _con_id(build_model(
                    Proyect, created_by=USUARIO_SUPERVISOR, leader=USUARIO_SUPERVISOR,
                    proyect_status="authorized", folio="PRJ-10", title="Obra propia"),
                    id_proyect=PROYECTO_PROPIO),
                _con_id(build_model(
                    Proyect, created_by=USUARIO_AJENO, leader=USUARIO_AJENO,
                    proyect_status="authorized", folio="PRJ-20", title="Obra ajena"),
                    id_proyect=PROYECTO_AJENO),
                _con_id(build_model(Material, material_description="Disco de corte 4 1/2"),
                        id_material=DISCO),
                _con_id(build_model(Material, material_description="Tornillo"),
                        id_material=TORNILLO),
                _con_id(build_model(Material, material_description="Cable"),
                        id_material=CABLE),
                _con_id(build_model(Product, id_material=DISCO), id_product=100),
                _con_id(build_model(Product, id_material=CABLE), id_product=300),
            ])
            db.flush()
            db.add_all([
                build_model(InventoryStock, id_product=100, id_location=1, quantity=5),
                build_model(InventoryStock, id_product=300, id_location=1, quantity=500),
            ])

    # --- ayudas --------------------------------------------------------------

    def _headers(self, id_user, id_permission):
        token = jwt.encode({"id_user": id_user, "id_permission": id_permission},
                           SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def _supervisor(self):
        return self._headers(USUARIO_SUPERVISOR, SUPERVISOR)

    def _pedir(self, id_proyecto, id_material, cantidad, headers=None, **extra):
        return self.client.post(
            "/proyect/%s/material-needs" % id_proyecto,
            json={"id_material": id_material, "quantity": cantidad, **extra},
            headers=headers or self._supervisor())

    # --- el supervisor y su proyecto -----------------------------------------

    def test_the_supervisor_declares_what_his_project_needs(self):
        respuesta = self._pedir(PROYECTO_PROPIO, DISCO, 3, note="para la placa",
                                needed_by="2026-11-01")
        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        cuerpo = self.json(respuesta)
        self.assertEqual(3, cuerpo["quantity"])
        self.assertEqual("open", cuerpo["need_status"])
        self.assertEqual("2026-11-01", cuerpo["needed_by"])
        self.assertEqual("Disco de corte 4 1/2", cuerpo["material"]["material_description"])

    def test_it_may_ask_for_more_than_there_is(self):
        """A diferencia del prevale, esta lista sirve justo para avisar el faltante."""
        respuesta = self._pedir(PROYECTO_PROPIO, DISCO, 50)
        self.assertEqual(201, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual(5, cuerpo["in_stock"])
        self.assertFalse(cuerpo["covered_by_stock"])

    def test_it_says_when_the_stock_already_covers_it(self):
        respuesta = self._pedir(PROYECTO_PROPIO, DISCO, 5)
        self.assertTrue(self.json(respuesta)["covered_by_stock"])

    def test_nobody_writes_in_a_project_they_cannot_see(self):
        respuesta = self._pedir(PROYECTO_AJENO, DISCO, 1)
        self.assertEqual(404, respuesta.status_code)

    def test_nor_reads_it(self):
        respuesta = self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_AJENO, headers=self._supervisor())
        self.assertEqual(404, respuesta.status_code)

    def test_the_same_material_is_not_listed_twice_in_a_project(self):
        self._pedir(PROYECTO_PROPIO, DISCO, 3)
        respuesta = self._pedir(PROYECTO_PROPIO, DISCO, 4)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_duplicate_material", self.json(respuesta)["error_key"])

    def test_an_invalid_quantity_or_unknown_material_is_rejected(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, DISCO, 0).status_code)
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, DISCO, "abc").status_code)
        self.assertEqual(404, self._pedir(PROYECTO_PROPIO, 999, 1).status_code)
        self.assertEqual(
            400, self._pedir(PROYECTO_PROPIO, DISCO, 1, needed_by="mañana").status_code)

    def test_it_lists_the_needs_of_the_project(self):
        self._pedir(PROYECTO_PROPIO, DISCO, 3)
        self._pedir(PROYECTO_PROPIO, TORNILLO, 10)
        respuesta = self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_PROPIO, headers=self._supervisor())
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual({DISCO, TORNILLO},
                         {i["id_material"] for i in self.json(respuesta)["items"]})

    def test_a_need_is_edited_and_then_cancelled_without_being_deleted(self):
        id_need = self.json(self._pedir(PROYECTO_PROPIO, DISCO, 3))["id_proyect_material_need"]

        editada = self.client.put("/material-needs/%s" % id_need,
                                  json={"quantity": 8}, headers=self._supervisor())
        self.assertEqual(200, editada.status_code)
        self.assertEqual(8, self.json(editada)["quantity"])

        cancelada = self.client.delete("/material-needs/%s" % id_need,
                                       headers=self._supervisor())
        self.assertEqual("cancelled", self.json(cancelada)["need_status"])

        # Ya no sale en la lista... pero no se perdio.
        lista = self.client.get("/proyect/%s/material-needs" % PROYECTO_PROPIO,
                                headers=self._supervisor())
        self.assertEqual([], self.json(lista)["items"])
        con_canceladas = self.client.get(
            "/proyect/%s/material-needs?include_cancelled=1" % PROYECTO_PROPIO,
            headers=self._supervisor())
        self.assertEqual(1, len(self.json(con_canceladas)["items"]))

        # Y una cancelada no se edita.
        otra = self.client.put("/material-needs/%s" % id_need,
                               json={"quantity": 2}, headers=self._supervisor())
        self.assertEqual(409, otra.status_code)
        self.assertEqual("errors.need_not_open", self.json(otra)["error_key"])

    def test_after_cancelling_the_material_can_be_asked_again(self):
        id_need = self.json(self._pedir(PROYECTO_PROPIO, DISCO, 3))["id_proyect_material_need"]
        self.client.delete("/material-needs/%s" % id_need, headers=self._supervisor())
        self.assertEqual(201, self._pedir(PROYECTO_PROPIO, DISCO, 2).status_code)

    def test_a_role_without_the_entity_permission_cannot_use_the_list(self):
        sin_permiso = self._headers(USUARIO_SUPERVISOR, NADIE)
        self.assertEqual(403, self._pedir(PROYECTO_PROPIO, DISCO, 1, headers=sin_permiso).status_code)
        self.assertEqual(403, self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_PROPIO, headers=sin_permiso).status_code)

    def test_read_only_cannot_create(self):
        solo_lee = self._headers(USUARIO_COMPRAS, COMPRAS)
        self.assertEqual(403, self._pedir(PROYECTO_PROPIO, DISCO, 1, headers=solo_lee).status_code)

    # --- por comprar ---------------------------------------------------------

    def _por_comprar(self, headers=None, query=""):
        return self.client.get(
            "/material-needs/to-buy" + query,
            headers=headers or self._headers(USUARIO_COMPRAS, COMPRAS))

    def test_without_the_capability_to_buy_it_is_forbidden(self):
        respuesta = self._por_comprar(headers=self._supervisor())
        self.assertEqual(403, respuesta.status_code)

    def test_the_buyer_sees_all_projects_against_the_stock(self):
        """Un mismo material pedido por dos proyectos es UNA compra."""
        self._pedir(PROYECTO_PROPIO, DISCO, 8, needed_by="2026-11-10")
        self._pedir(PROYECTO_AJENO, DISCO, 4, headers=self._headers(USUARIO_AJENO, SUPERVISOR),
                    needed_by="2026-11-01")
        self._pedir(PROYECTO_PROPIO, TORNILLO, 1)

        respuesta = self._por_comprar()
        self.assertEqual(200, respuesta.status_code)
        por_material = {i["material"]["id_material"]: i for i in self.json(respuesta)["items"]}

        disco = por_material[DISCO]
        self.assertEqual(12, disco["required"])
        self.assertEqual(5, disco["in_stock"])
        self.assertEqual(7, disco["missing"])
        # La fecha mas urgente de las dos obras.
        self.assertEqual("2026-11-01", disco["needed_by"])
        self.assertEqual({PROYECTO_PROPIO, PROYECTO_AJENO},
                         {p["id_proyect"] for p in disco["projects"]})

        tornillo = por_material[TORNILLO]
        self.assertEqual(0, tornillo["in_stock"])
        self.assertEqual(1, tornillo["missing"])

    def test_what_the_stock_already_covers_is_hidden_unless_asked(self):
        self._pedir(PROYECTO_PROPIO, CABLE, 10)  # hay 500
        self._pedir(PROYECTO_PROPIO, TORNILLO, 1)

        solo_faltantes = {i["material"]["id_material"]
                          for i in self.json(self._por_comprar())["items"]}
        self.assertEqual({TORNILLO}, solo_faltantes)

        todo = {i["material"]["id_material"]
                for i in self.json(self._por_comprar(query="?only_missing=0"))["items"]}
        self.assertEqual({CABLE, TORNILLO}, todo)

    def test_the_most_urgent_comes_first(self):
        self._pedir(PROYECTO_PROPIO, DISCO, 8, needed_by="2026-12-01")
        self._pedir(PROYECTO_PROPIO, TORNILLO, 1, needed_by="2026-11-01")
        orden = [i["material"]["id_material"] for i in self.json(self._por_comprar())["items"]]
        self.assertEqual([TORNILLO, DISCO], orden)

    def test_a_cancelled_need_does_not_count(self):
        id_need = self.json(self._pedir(PROYECTO_PROPIO, TORNILLO, 1))["id_proyect_material_need"]
        self.client.delete("/material-needs/%s" % id_need, headers=self._supervisor())
        self.assertEqual([], self.json(self._por_comprar())["items"])

    def test_a_finished_project_no_longer_buys(self):
        """Sus necesidades abiertas son residuo: contarlas inflaria lo que falta."""
        self._pedir(PROYECTO_PROPIO, TORNILLO, 1)
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_PROPIO).proyect_status = "completed"
        self.assertEqual([], self.json(self._por_comprar())["items"])

    # --- el desplegable de material ------------------------------------------

    def test_the_supervisor_can_pick_a_material_without_the_material_permission(self):
        """Solo id, nombre y unidad, sin leer el catalogo de inventario."""
        respuesta = self.client.get("/material-needs/materials", headers=self._supervisor())
        self.assertEqual(200, respuesta.status_code)
        nombres = {m["material_description"] for m in respuesta.get_json()}
        self.assertEqual({"Disco de corte 4 1/2", "Tornillo", "Cable"}, nombres)
        self.assertEqual({"id_material", "material_description", "unit"},
                         set(respuesta.get_json()[0]))

    def test_the_material_options_need_the_list_permission(self):
        sin_permiso = self._headers(USUARIO_SUPERVISOR, NADIE)
        self.assertEqual(
            403, self.client.get("/material-needs/materials", headers=sin_permiso).status_code)
