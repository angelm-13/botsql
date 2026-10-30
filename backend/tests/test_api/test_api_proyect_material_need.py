"""La lista de necesidades por proyecto, las sugerencias y la vista "Por comprar".

Tres preguntas distintas:

* El supervisor declara lo que necesita SU proyecto con sus propias palabras --el
  catalogo de Adser es de herramienta, no de lo que una obra consume--. Puede
  pedir mas de lo que hay, no toca proyectos ajenos y no duplica un renglon.
* Al escribir se le sugiere lo que el catalogo parece tener. Es solo ayuda: buscar
  por texto no decide nada.
* Quien compra ve las necesidades de TODOS los proyectos con la capacidad
  `purchase_planning`. Lo de texto libre sale "por revisar" hasta que alguien que
  conoce el almacen lo vincule (ya existe) o confirme la compra.
"""
from __future__ import annotations

import jwt

from app.models import (
    EntityPermission, InventoryStock, Material, Product, Proyect,
)
from app.models.session import transaction_context
from app.services.proyect_material_need_service import descripcion_sospechosa
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.model_factory import build_model

SUPERVISOR, COMPRAS, SOLO_VE, NADIE = 201, 301, 302, 401
USUARIO_SUPERVISOR, USUARIO_AJENO, USUARIO_COMPRAS = 11, 12, 21
PROYECTO_PROPIO, PROYECTO_AJENO = 10, 20
DISCO, TORNILLO, CABLE, TALADRO, ROTOMARTILLO, AMOLADORA = 1, 2, 3, 4, 5, 6


def _con_id(objeto, **ids):
    """`build_model` ignora las llaves autoincrementales: se asignan despues."""
    for campo, valor in ids.items():
        setattr(objeto, campo, valor)
    return objeto


class TestListaDeNecesidades(BackendTestCase):
    def setUp(self):
        super().setUp()
        catalogo = [
            (DISCO, "Disco de corte 4 1/2", 5), (TORNILLO, "Tornillo", 0),
            (CABLE, "Cable", 500), (TALADRO, "Taladro inalambrico", 3),
            (ROTOMARTILLO, "Taladro rotomartillo", 2), (AMOLADORA, "Amoladora angular", 1),
        ]
        with transaction_context() as db:
            db.add_all([
                # Supervisor: CAPTURA sobre la entidad, como la da `operaciones`.
                EntityPermission(id_permission=SUPERVISOR, entity_name="proyect_material_need",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Compras: ve y REVISA lo de todos (capacidad con lectura y edicion).
                EntityPermission(id_permission=COMPRAS, entity_name="purchase_planning",
                                 scope_read=4, scope_update=4, created_by=1),
                # Otro que solo VE lo que falta, sin poder revisar.
                EntityPermission(id_permission=SOLO_VE, entity_name="purchase_planning",
                                 scope_read=4, created_by=1),
                _con_id(build_model(
                    Proyect, created_by=USUARIO_SUPERVISOR, leader=USUARIO_SUPERVISOR,
                    proyect_status="authorized", folio="PRJ-10", title="Obra propia"),
                    id_proyect=PROYECTO_PROPIO),
                _con_id(build_model(
                    Proyect, created_by=USUARIO_AJENO, leader=USUARIO_AJENO,
                    proyect_status="authorized", folio="PRJ-20", title="Obra ajena"),
                    id_proyect=PROYECTO_AJENO),
            ] + [
                _con_id(build_model(Material, material_description=nombre), id_material=i)
                for i, nombre, _existencia in catalogo
            ] + [
                _con_id(build_model(Product, id_material=i), id_product=100 + i)
                for i, _nombre, _existencia in catalogo
            ])
            db.flush()
            db.add_all([
                build_model(InventoryStock, id_product=100 + i, id_location=1, quantity=existencia)
                for i, _nombre, existencia in catalogo if existencia
            ])

    # --- ayudas --------------------------------------------------------------

    def _headers(self, id_user, id_permission):
        token = jwt.encode({"id_user": id_user, "id_permission": id_permission},
                           SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def _supervisor(self):
        return self._headers(USUARIO_SUPERVISOR, SUPERVISOR)

    def _ajeno(self):
        return self._headers(USUARIO_AJENO, SUPERVISOR)

    def _compras(self):
        return self._headers(USUARIO_COMPRAS, COMPRAS)

    def _pedir(self, id_proyecto, cantidad=1, headers=None, **datos):
        return self.client.post(
            "/proyect/%s/material-needs" % id_proyecto,
            json={"quantity": cantidad, **datos}, headers=headers or self._supervisor())

    def _id(self, respuesta):
        return self.json(respuesta)["id_proyect_material_need"]

    # --- lo vinculado al catalogo --------------------------------------------

    def test_the_supervisor_declares_what_his_project_needs(self):
        respuesta = self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO, note="para la placa",
                                needed_by="2026-11-01")
        self.assertEqual(201, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual(3, cuerpo["quantity"])
        self.assertTrue(cuerpo["linked"])
        self.assertEqual("Disco de corte 4 1/2", cuerpo["display_name"])
        self.assertEqual("2026-11-01", cuerpo["needed_by"])
        self.assertFalse(cuerpo["needs_review"])

    def test_a_need_that_names_a_catalog_material_is_born_linked(self):
        """Si no, ni se podia ordenar (need_not_purchasable) ni confirmar la compra."""
        from app.models.proyect_material_need import ProyectMaterialNeed
        from app.models.session import transaction_context

        cuerpo = self.json(self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO))

        with transaction_context() as db:
            necesidad = db.get(ProyectMaterialNeed, cuerpo["id_proyect_material_need"])
            self.assertEqual("linked", necesidad.review_result)

    def test_it_may_ask_for_more_than_there_is(self):
        """A diferencia del prevale, esta lista sirve justo para avisar el faltante."""
        cuerpo = self.json(self._pedir(PROYECTO_PROPIO, 50, id_material=DISCO))
        self.assertEqual(5, cuerpo["in_stock"])
        self.assertFalse(cuerpo["covered_by_stock"])

    def test_it_says_when_the_stock_already_covers_it(self):
        cuerpo = self.json(self._pedir(PROYECTO_PROPIO, 5, id_material=DISCO))
        self.assertTrue(cuerpo["covered_by_stock"])

    def test_the_same_catalog_material_is_not_listed_twice_in_a_project(self):
        self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO)
        respuesta = self._pedir(PROYECTO_PROPIO, 4, id_material=DISCO)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_duplicate_material", self.json(respuesta)["error_key"])

    # --- el texto libre ------------------------------------------------------

    def test_the_supervisor_describes_what_he_needs_in_his_own_words(self):
        respuesta = self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013", unit="kg")
        self.assertEqual(201, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertFalse(cuerpo["linked"])
        self.assertEqual("Soldadura 6013", cuerpo["display_name"])
        self.assertEqual("kg", cuerpo["unit"])
        # No hay contra que comparar: no se inventa una existencia.
        self.assertIsNone(cuerpo["in_stock"])
        self.assertIsNone(cuerpo["covered_by_stock"])
        # Y nadie lo ha revisado.
        self.assertTrue(cuerpo["needs_review"])

    def test_it_needs_either_a_catalog_material_or_a_description(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 1).status_code)
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 1, description="   ").status_code)

    def test_linking_to_the_catalog_wins_over_the_text(self):
        cuerpo = self.json(self._pedir(PROYECTO_PROPIO, 1, id_material=DISCO,
                                       description="algo que escribio"))
        self.assertTrue(cuerpo["linked"])
        self.assertIsNone(cuerpo["description"])

    def test_the_same_text_is_not_listed_twice_even_with_other_spacing_or_case(self):
        self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013")
        respuesta = self._pedir(PROYECTO_PROPIO, 5, description="  soldadura   6013 ")
        self.assertEqual(409, respuesta.status_code)

    def test_a_description_that_is_too_long_is_rejected(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 1, description="x" * 201).status_code)

    def test_changing_the_words_of_a_reviewed_line_asks_the_question_again(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013"))
        self.client.post("/material-needs/%s/confirm-buy" % id_need, headers=self._compras())
        editada = self.client.put("/material-needs/%s" % id_need,
                                  json={"description": "Electrodo 7018"},
                                  headers=self._supervisor())
        self.assertEqual(200, editada.status_code)
        cuerpo = self.json(editada)
        self.assertTrue(cuerpo["needs_review"])
        self.assertIsNone(cuerpo["review_result"])

    # --- la visibilidad y los permisos ---------------------------------------

    def test_nobody_writes_in_a_project_they_cannot_see(self):
        self.assertEqual(404, self._pedir(PROYECTO_AJENO, 1, id_material=DISCO).status_code)

    def test_nor_reads_it(self):
        respuesta = self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_AJENO, headers=self._supervisor())
        self.assertEqual(404, respuesta.status_code)

    def test_an_invalid_quantity_or_unknown_material_is_rejected(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 0, id_material=DISCO).status_code)
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, "abc", id_material=DISCO).status_code)
        self.assertEqual(404, self._pedir(PROYECTO_PROPIO, 1, id_material=999).status_code)
        self.assertEqual(
            400, self._pedir(PROYECTO_PROPIO, 1, id_material=DISCO,
                             needed_by="mañana").status_code)

    def test_it_lists_the_needs_of_the_project(self):
        self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO)
        self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013")
        respuesta = self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_PROPIO, headers=self._supervisor())
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual({"Disco de corte 4 1/2", "Soldadura 6013"},
                         {i["display_name"] for i in self.json(respuesta)["items"]})

    def test_a_need_is_edited_and_then_cancelled_without_being_deleted(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO))

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

    def test_after_cancelling_the_same_thing_can_be_asked_again(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, id_material=DISCO))
        self.client.delete("/material-needs/%s" % id_need, headers=self._supervisor())
        self.assertEqual(201, self._pedir(PROYECTO_PROPIO, 2, id_material=DISCO).status_code)

    def test_a_role_without_the_entity_permission_cannot_use_the_list(self):
        sin_permiso = self._headers(USUARIO_SUPERVISOR, NADIE)
        self.assertEqual(
            403, self._pedir(PROYECTO_PROPIO, 1, id_material=DISCO, headers=sin_permiso).status_code)
        self.assertEqual(403, self.client.get(
            "/proyect/%s/material-needs" % PROYECTO_PROPIO, headers=sin_permiso).status_code)

    # --- las sugerencias al capturar -----------------------------------------

    def _sugerir(self, texto, headers=None):
        return self.client.get("/material-needs/suggestions", query_string={"q": texto},
                               headers=headers or self._supervisor())

    def test_it_suggests_what_the_catalog_seems_to_have_with_its_stock(self):
        respuesta = self._sugerir("taladro inalambrico")
        self.assertEqual(200, respuesta.status_code)
        sugerencias = self.json_list(respuesta)
        # El que coincide en todo va primero, con su existencia.
        self.assertEqual(TALADRO, sugerencias[0]["id_material"])
        self.assertTrue(sugerencias[0]["complete_match"])
        self.assertEqual(3, sugerencias[0]["in_stock"])
        # El que solo comparte "taladro" tambien se ofrece, pero despues y como parcial.
        rotomartillo = next(s for s in sugerencias if s["id_material"] == ROTOMARTILLO)
        self.assertFalse(rotomartillo["complete_match"])

    def test_a_plural_finds_the_singular(self):
        ids = {s["id_material"] for s in self.json_list(self._sugerir("taladros"))}
        self.assertEqual({TALADRO, ROTOMARTILLO}, ids)

    def test_accents_and_case_do_not_matter(self):
        ids = {s["id_material"] for s in self.json_list(self._sugerir("INALÁMBRICO"))}
        self.assertEqual({TALADRO}, ids)

    def test_a_word_only_matches_the_start_of_another_not_the_middle(self):
        """"arco" no es "marco"."""
        with transaction_context() as db:
            db.add(_con_id(build_model(Material, material_description="Marco metalico"),
                           id_material=50))
        self.assertEqual([], self.json_list(self._sugerir("arco")))

    def test_a_synonym_is_not_found_and_that_is_why_nothing_is_decided_by_text(self):
        """"esmeril angular" y "amoladora angular" son lo mismo para el almacen.

        Solo comparten "angular": se sugiere como PARCIAL, nunca como lo mismo.
        Y si el texto no comparte nada, no hay sugerencia: de ahi que lo de texto
        libre salga "por revisar" en vez de darse por cubierto o por comprado.
        """
        parcial = self.json_list(self._sugerir("esmeril angular"))
        self.assertEqual([AMOLADORA], [s["id_material"] for s in parcial])
        self.assertFalse(parcial[0]["complete_match"])
        self.assertEqual([], self.json_list(self._sugerir("esmeril")))

    def test_nothing_is_suggested_for_empty_or_meaningless_text(self):
        self.assertEqual([], self.json_list(self._sugerir("")))
        self.assertEqual([], self.json_list(self._sugerir("de la y")))
        self.assertEqual([], self.json_list(self._sugerir("zzzzzz")))

    def test_the_suggestions_need_the_list_permission(self):
        sin_permiso = self._headers(USUARIO_SUPERVISOR, NADIE)
        self.assertEqual(403, self._sugerir("taladro", headers=sin_permiso).status_code)

    def json_list(self, respuesta):
        return respuesta.get_json()["materials"]

    # --- por comprar ---------------------------------------------------------

    def _por_comprar(self, headers=None, query=""):
        return self.client.get("/material-needs/to-buy" + query,
                               headers=headers or self._compras())

    def _grupos(self, respuesta):
        return self.json(respuesta)["items"]

    def test_without_the_capability_to_buy_it_is_forbidden(self):
        self.assertEqual(403, self._por_comprar(headers=self._supervisor()).status_code)

    def test_the_buyer_sees_linked_needs_of_all_projects_against_the_stock(self):
        """Un mismo material pedido por dos proyectos es UNA compra."""
        self._pedir(PROYECTO_PROPIO, 8, id_material=DISCO, needed_by="2026-11-10")
        self._pedir(PROYECTO_AJENO, 4, id_material=DISCO, headers=self._ajeno(),
                    needed_by="2026-11-01")
        self._pedir(PROYECTO_PROPIO, 1, id_material=TORNILLO)

        grupos = {g["material"]["id_material"]: g for g in self._grupos(self._por_comprar())}
        disco = grupos[DISCO]
        self.assertEqual(12, disco["required"])
        self.assertEqual(5, disco["in_stock"])
        self.assertEqual(7, disco["missing"])
        self.assertEqual("2026-11-01", disco["needed_by"])  # la obra mas urgente
        self.assertEqual({PROYECTO_PROPIO, PROYECTO_AJENO},
                         {p["id_proyect"] for p in disco["projects"]})
        self.assertFalse(disco["needs_review"])
        self.assertEqual(1, grupos[TORNILLO]["missing"])

    def test_free_text_is_grouped_by_its_words_and_marked_for_review(self):
        self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013", unit="kg")
        self._pedir(PROYECTO_AJENO, 5, description="soldadura  6013", headers=self._ajeno())

        respuesta = self._por_comprar()
        grupos = self._grupos(respuesta)
        self.assertEqual(1, len(grupos))
        soldadura = grupos[0]
        self.assertFalse(soldadura["linked"])
        self.assertEqual(15, soldadura["required"])
        self.assertEqual(15, soldadura["missing"])      # no se compara con nada
        self.assertIsNone(soldadura["in_stock"])
        self.assertTrue(soldadura["needs_review"])
        self.assertEqual(2, len(soldadura["projects"]))
        self.assertEqual(1, self.json(respuesta)["to_review"])

    def test_text_that_resembles_the_catalog_shows_the_suggestions_but_is_not_hidden(self):
        """Aunque el almacen tenga 3, no se da por cubierto por parecerse."""
        self._pedir(PROYECTO_PROPIO, 2, description="Taladro inalambrico")
        grupos = self._grupos(self._por_comprar())
        self.assertEqual(1, len(grupos))
        self.assertTrue(grupos[0]["needs_review"])
        self.assertEqual(TALADRO, grupos[0]["suggestions"][0]["id_material"])
        self.assertEqual(3, grupos[0]["suggestions"][0]["in_stock"])

    def test_free_text_is_never_hidden_by_the_only_missing_filter(self):
        self._pedir(PROYECTO_PROPIO, 10, id_material=CABLE)          # hay 500: cubierto
        self._pedir(PROYECTO_PROPIO, 1, description="Pintura")       # texto libre

        solo_faltantes = [g["key"] for g in self._grupos(self._por_comprar())]
        self.assertEqual(["d:pintura"], solo_faltantes)
        todo = {g["key"] for g in self._grupos(self._por_comprar(query="?only_missing=0"))}
        self.assertEqual({"d:pintura", "m:%d" % CABLE}, todo)

    def test_the_most_urgent_comes_first(self):
        self._pedir(PROYECTO_PROPIO, 8, id_material=DISCO, needed_by="2026-12-01")
        self._pedir(PROYECTO_PROPIO, 1, id_material=TORNILLO, needed_by="2026-11-01")
        self.assertEqual(
            ["m:%d" % TORNILLO, "m:%d" % DISCO],
            [g["key"] for g in self._grupos(self._por_comprar())])

    def test_a_cancelled_need_does_not_count(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 1, id_material=TORNILLO))
        self.client.delete("/material-needs/%s" % id_need, headers=self._supervisor())
        self.assertEqual([], self._grupos(self._por_comprar()))

    def test_a_finished_project_no_longer_buys(self):
        """Sus necesidades abiertas son residuo: contarlas inflaria lo que falta."""
        self._pedir(PROYECTO_PROPIO, 1, id_material=TORNILLO)
        with transaction_context() as db:
            db.get(Proyect, PROYECTO_PROPIO).proyect_status = "completed"
        self.assertEqual([], self._grupos(self._por_comprar()))

    # --- revisar lo de texto libre -------------------------------------------

    def _vincular(self, id_need, id_material, headers=None):
        return self.client.post("/material-needs/%s/link" % id_need,
                                json={"id_material": id_material},
                                headers=headers or self._compras())

    def _confirmar(self, id_need, headers=None):
        return self.client.post("/material-needs/%s/confirm-buy" % id_need,
                                headers=headers or self._compras())

    def test_the_reviewer_links_text_that_already_exists_in_the_warehouse(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 2, description="Taladro inalambrico"))

        respuesta = self._vincular(id_need, TALADRO)
        self.assertEqual(200, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertTrue(cuerpo["linked"])
        self.assertEqual("linked", cuerpo["review_result"])
        self.assertEqual(USUARIO_COMPRAS, cuerpo["reviewed_by"])
        self.assertIsNotNone(cuerpo["reviewed_date"])
        self.assertFalse(cuerpo["needs_review"])

        # Ahora si se compara con la existencia: 2 pedidos contra 3 hay, no falta nada.
        self.assertEqual([], self._grupos(self._por_comprar()))
        grupos = self._grupos(self._por_comprar(query="?only_missing=0"))
        self.assertEqual(TALADRO, grupos[0]["material"]["id_material"])

    def test_the_reviewer_confirms_that_it_really_has_to_be_bought(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013"))

        respuesta = self._confirmar(id_need)
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual("buy", self.json(respuesta)["review_result"])

        grupos = self._grupos(self._por_comprar())
        self.assertEqual(1, len(grupos))
        # Sigue sin vincular y sigue por comprar, pero ya no esta por revisar.
        self.assertFalse(grupos[0]["linked"])
        self.assertFalse(grupos[0]["needs_review"])
        self.assertEqual(0, self.json(self._por_comprar())["to_review"])

    def test_reviewing_does_not_require_seeing_the_project(self):
        """Quien compra revisa lo de todas las obras sin poder abrirlas."""
        id_need = self._id(self._pedir(PROYECTO_AJENO, 1, description="Pintura",
                                       headers=self._ajeno()))
        self.assertEqual(200, self._confirmar(id_need).status_code)

    def test_only_seeing_the_purchase_list_does_not_allow_reviewing(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Pintura"))
        solo_ve = self._headers(USUARIO_COMPRAS, SOLO_VE)
        self.assertEqual(200, self._por_comprar(headers=solo_ve).status_code)
        self.assertEqual(403, self._confirmar(id_need, headers=solo_ve).status_code)
        self.assertEqual(403, self._vincular(id_need, TALADRO, headers=solo_ve).status_code)

    def test_the_supervisor_cannot_review_his_own_text(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Pintura"))
        self.assertEqual(403, self._confirmar(id_need, headers=self._supervisor()).status_code)

    def test_the_review_screen_says_whether_the_actor_can_review(self):
        self.assertTrue(self.json(self._por_comprar())["can_review"])
        solo_ve = self._headers(USUARIO_COMPRAS, SOLO_VE)
        self.assertFalse(self.json(self._por_comprar(headers=solo_ve))["can_review"])

    def test_it_cannot_link_to_a_material_the_project_already_lists(self):
        self._pedir(PROYECTO_PROPIO, 1, id_material=TALADRO)
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 2, description="Taladro inalambrico"))
        respuesta = self._vincular(id_need, TALADRO)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_duplicate_material", self.json(respuesta)["error_key"])

    def test_a_line_already_linked_or_cancelled_is_not_reviewed_again(self):
        vinculada = self._id(self._pedir(PROYECTO_PROPIO, 1, id_material=DISCO))
        respuesta = self._confirmar(vinculada)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_already_linked", self.json(respuesta)["error_key"])

        cancelada = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Pintura"))
        self.client.delete("/material-needs/%s" % cancelada, headers=self._supervisor())
        self.assertEqual("errors.need_not_open",
                         self.json(self._confirmar(cancelada))["error_key"])

    def test_linking_to_an_unknown_material_is_a_404(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Pintura"))
        self.assertEqual(404, self._vincular(id_need, 999).status_code)

    # --- proteger el texto libre ---------------------------------------------

    REALES = [
        "soldadura 6013", "tornillo 1/4 x 2", "Pintura esmalte blanca", "cable THW calibre 12",
        "electrodo E7018", "cemento gris", "lija 120", "varilla 3/8", "malla electrosoldada 6x6",
        "construcción", "tuerca M8x1.25", "brocha 4 pulgadas", "thinner", "disco de corte 4 1/2",
        "guantes de carnaza", "clavo 2 1/2", "cinta teflón", "pegamento PVC", "manguera 1/2 pulgada",
        "extensión eléctrica 15 m", "grasa multiusos", "WD-40", "tubo cuadrado 2x2",
        "perfil estructural IPR", "anclas expansivas 3/8", "cable THHN calibre 10",
    ]
    ABSURDOS = ["12o3pifsfjg", "asdfgh", "qwerty", "aaaaa", "xxxxx", "jjjjjjj", "123456",
                "....", "bcdfghjk", "pifsfjg", "ab", "  "]

    def test_the_rule_catches_nonsense_and_never_a_real_request(self):
        """Probada contra 26 pedidos reales de una obra: no rechaza ninguno."""
        self.assertEqual([], [t for t in self.REALES if descripcion_sospechosa(t)])
        self.assertEqual([], [t for t in self.ABSURDOS if not descripcion_sospechosa(t)])

    def test_nonsense_is_rejected_when_the_supervisor_types_it(self):
        for texto in ("12o3pifsfjg", "asdfgh", "aaaaa", "6013", "ab"):
            with self.subTest(texto=texto):
                respuesta = self._pedir(PROYECTO_PROPIO, 1, description=texto)
                self.assertEqual(400, respuesta.status_code)
                self.assertEqual("errors.need_description_invalid",
                                 self.json(respuesta)["error_key"])

    def test_real_requests_all_go_through(self):
        for texto in self.REALES:
            with self.subTest(texto=texto):
                self.assertEqual(201, self._pedir(PROYECTO_PROPIO, 1, description=texto).status_code)

    def test_nonsense_is_also_rejected_when_editing_the_words(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Pintura"))
        respuesta = self.client.put("/material-needs/%s" % id_need,
                                    json={"description": "12o3pifsfjg"},
                                    headers=self._supervisor())
        self.assertEqual(400, respuesta.status_code)

    def test_the_unit_has_to_be_one_of_the_list(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 1, description="Pintura",
                                          unit="kilos").status_code)
        cuerpo = self.json(self._pedir(PROYECTO_PROPIO, 1, description="Soldadura 6013", unit="KG"))
        self.assertEqual("kg", cuerpo["unit"])

    def test_a_linked_line_takes_its_unit_from_the_catalog_and_ignores_the_typed_one(self):
        respuesta = self._pedir(PROYECTO_PROPIO, 1, id_material=DISCO, unit="lo-que-sea")
        self.assertEqual(201, respuesta.status_code)
        self.assertIsNone(self.json(respuesta)["unit"])

    def test_an_absurd_quantity_is_rejected(self):
        self.assertEqual(400, self._pedir(PROYECTO_PROPIO, 100001, description="Pintura").status_code)
        self.assertEqual(201, self._pedir(PROYECTO_PROPIO, 100000, description="Cemento gris").status_code)

    # --- devolver lo que no se entiende --------------------------------------

    def _devolver(self, id_need, nota="No se entiende que material es", headers=None):
        return self.client.post("/material-needs/%s/return" % id_need, json={"note": nota},
                                headers=headers or self._compras())

    def test_the_reviewer_returns_what_does_not_make_sense_and_it_is_not_bought(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))

        respuesta = self._devolver(id_need, "Dime que material es exactamente")
        self.assertEqual(200, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual("returned", cuerpo["review_result"])
        self.assertEqual("Dime que material es exactamente", cuerpo["review_note"])
        self.assertTrue(cuerpo["returned"])
        self.assertFalse(cuerpo["needs_review"])
        self.assertEqual(USUARIO_COMPRAS, cuerpo["reviewed_by"])

        # Todavia no es una compra: espera al supervisor.
        self.assertEqual([], self._grupos(self._por_comprar()))
        self.assertEqual(0, self.json(self._por_comprar())["to_review"])

    def test_the_supervisor_sees_why_it_came_back(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self._devolver(id_need, "Dime que material es exactamente")
        lista = self.client.get("/proyect/%s/material-needs" % PROYECTO_PROPIO,
                                headers=self._supervisor())
        renglon = self.json(lista)["items"][0]
        self.assertTrue(renglon["returned"])
        self.assertEqual("Dime que material es exactamente", renglon["review_note"])

    def test_correcting_the_words_sends_it_back_to_review(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self._devolver(id_need)
        editada = self.client.put("/material-needs/%s" % id_need,
                                  json={"description": "Pintura esmalte blanca"},
                                  headers=self._supervisor())
        cuerpo = self.json(editada)
        self.assertTrue(cuerpo["needs_review"])
        self.assertFalse(cuerpo["returned"])
        self.assertIsNone(cuerpo["review_note"])
        self.assertEqual(1, len(self._grupos(self._por_comprar())))

    def test_the_supervisor_can_resubmit_without_changing_the_words(self):
        """Si el que reviso se equivoco, basta con explicarlo y reenviar."""
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self._devolver(id_need)
        editada = self.client.put("/material-needs/%s" % id_need, json={"resubmit": True},
                                  headers=self._supervisor())
        self.assertTrue(self.json(editada)["needs_review"])

    def test_a_returned_line_cannot_be_reviewed_until_it_is_resubmitted(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self._devolver(id_need)
        respuesta = self._confirmar(id_need)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_not_reviewable", self.json(respuesta)["error_key"])
        self.assertEqual(409, self._vincular(id_need, TALADRO).status_code)
        self.assertEqual(409, self._devolver(id_need).status_code)

    def test_a_reason_is_required_to_return(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self.assertEqual(400, self._devolver(id_need, nota="").status_code)
        self.assertEqual(400, self._devolver(id_need, nota="no").status_code)

    def test_only_a_reviewer_can_return(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 3, description="Material raro"))
        self.assertEqual(403, self._devolver(id_need, headers=self._supervisor()).status_code)
        solo_ve = self._headers(USUARIO_COMPRAS, SOLO_VE)
        self.assertEqual(403, self._devolver(id_need, headers=solo_ve).status_code)

    def test_a_confirmed_purchase_cannot_be_returned_but_can_still_be_linked(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 2, description="Taladro inalambrico"))
        self._confirmar(id_need)
        self.assertEqual(409, self._devolver(id_need).status_code)
        # Se descubrio despues que si habia: vincular sigue siendo posible.
        self.assertEqual(200, self._vincular(id_need, TALADRO).status_code)

    # --- el vocabulario que ya paso por una revision -------------------------

    def _previas(self, texto):
        return self._sugerir(texto).get_json()["previous"]

    def test_what_was_already_confirmed_as_a_purchase_is_suggested_again(self):
        id_need = self._id(self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013", unit="kg"))
        self._confirmar(id_need)
        # Otro proyecto la vuelve a pedir y se confirma tambien: ya son dos veces.
        otra = self._id(self._pedir(PROYECTO_AJENO, 5, description="soldadura  6013",
                                    headers=self._ajeno()))
        self._confirmar(otra)

        previas = self._previas("soldadura")
        self.assertEqual(1, len(previas))
        self.assertEqual("Soldadura 6013", previas[0]["description"])
        self.assertEqual("kg", previas[0]["unit"])
        self.assertEqual(2, previas[0]["times"])

    def test_text_nobody_has_reviewed_or_that_was_returned_is_not_suggested(self):
        self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013")           # sin revisar
        devuelto = self._id(self._pedir(PROYECTO_PROPIO, 1, description="Soldadura rara"))
        self._devolver(devuelto)
        self.assertEqual([], self._previas("soldadura"))

    def test_every_word_has_to_be_in_the_previous_text(self):
        self._confirmar(self._id(self._pedir(PROYECTO_PROPIO, 10, description="Soldadura 6013")))
        self.assertEqual(1, len(self._previas("soldadura 6013")))
        self.assertEqual([], self._previas("soldadura 7018"))
