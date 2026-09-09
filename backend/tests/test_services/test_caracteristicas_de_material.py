"""Las caracteristicas del material: la familia las declara, el material las llena.

Que se venia a resolver
-----------------------
Con familia, tipo y marca se llega hasta "desarmador Truper plano". El resto -el
largo, el mango, el calibre, los litros- se escribia dentro de la descripcion:

    "Desarmador plano 6 pulgadas mango de goma"

Eso se puede leer y no se puede usar: nada de agrupar, filtrar, ni contestar
"cuantos de 6 pulgadas tengo", que es la pregunta que justifica todo esto.

Lo que estas pruebas fijan
--------------------------
* **una caracteristica pertenece a una familia.** Capturar en un desarmador un
  campo de otra familia se rechaza en vez de ignorarse: ignorarlo dejaria al
  usuario creyendo que se guardo;
* **el numero se guarda como numero.** Es la razon de la columna aparte:
  comparado como texto, "10" queda por debajo de "6", asi que "de 6 pulgadas o
  mas" daria la respuesta equivocada;
* **la lista solo acepta lo declarado.** Es lo que impide que "mate", "Mate" y
  "MATE" acaben siendo tres acabados, que es el fallo que ya tenia
  `product_status` cuando era texto libre;
* **lo obligatorio se comprueba sobre el juego completo**, no campo por campo:
  campo por campo, el orden de captura decidiria si pasa;
* **guardar es reemplazar.** Lo que no viene se retira, asi que quitar una
  caracteristica no necesita una segunda llamada que pueda quedar a medias;
* **el tipo de dato no se cambia.** Cambiarlo dejaria los valores ya capturados
  en la forma del tipo viejo y la comparacion numerica empezaria a mentir en
  silencio;
* **no se borra lo que se esta usando**, ni la caracteristica ni una opcion: esos
  valores quedarian apuntando a un campo que ya no existe;
* **se lee en lote.** Una consulta por material es el N+1 que ya costo 271
  consultas en el rastreo.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import (
    Brand,
    CustomerSupplier,
    Material,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.session import transaction_context
from app.services.material_attribute_service import (
    actualizar_atributo,
    agregar_opcion,
    atributos_de_la_familia,
    caracteristicas_de,
    crear_atributo,
    eliminar_atributo,
    eliminar_opcion,
    guardar_valores,
    materiales_que_cumplen,
    valores_de_materiales,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

CLIENTE, PROYECTO, ESTATUS = 20, 30, 40
FAM_DESARMADORES, FAM_CABLE = 60, 61
MARCA_TRUPER = 64
DESARMADOR_1, DESARMADOR_2, DESARMADOR_3 = 70, 71, 72
CABLE = 73


class BaseCaracteristicas(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
                ProductFamily(id_product_family=FAM_DESARMADORES,
                              product_family_description="Desarmadores",
                              type="tool", created_by=1),
                ProductFamily(id_product_family=FAM_CABLE,
                              product_family_description="Cable",
                              type="consumable", created_by=1),
                Brand(id_brand=MARCA_TRUPER, brand_description="Truper", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Obra", created_by=1),
            ])
            db.flush()
            sembrar_actor(db, id_proyect=PROYECTO, id_status=ESTATUS)
            db.add_all([
                Material(id_material=DESARMADOR_1,
                         material_description="Desarmador plano chico", id_unit=1,
                         id_brand=MARCA_TRUPER,
                         id_product_family=FAM_DESARMADORES, created_by=1),
                Material(id_material=DESARMADOR_2,
                         material_description="Desarmador plano grande", id_unit=1,
                         id_brand=MARCA_TRUPER,
                         id_product_family=FAM_DESARMADORES, created_by=1),
                Material(id_material=DESARMADOR_3,
                         material_description="Desarmador de cruz", id_unit=1,
                         id_brand=MARCA_TRUPER,
                         id_product_family=FAM_DESARMADORES, created_by=1),
                Material(id_material=CABLE,
                         material_description="Cable calibre 12", id_unit=1,
                         id_brand=MARCA_TRUPER,
                         id_product_family=FAM_CABLE, created_by=1),
            ])

    def declarar(self, nombre="Largo", tipo="numero", familia=FAM_DESARMADORES,
                 **extra):
        carga = {"id_product_family": familia, "attribute_name": nombre,
                 "data_type": tipo}
        carga.update(extra)
        return crear_atributo(carga, ACTOR)["attribute"]

    def largo(self, **extra):
        return self.declarar("Largo", "numero", unit_label="in", **extra)


class TestLaFamiliaDeclaraSusCaracteristicas(BaseCaracteristicas):

    def test_a_family_declares_a_characteristic(self):
        atributo = self.largo()
        self.assertEqual(FAM_DESARMADORES, atributo["id_product_family"])
        self.assertEqual("numero", atributo["data_type"])
        self.assertEqual("in", atributo["unit_label"])

    def test_the_same_name_twice_in_one_family_is_refused(self):
        """Con dos "Largo" vivos, la mitad de los materiales llena uno y la mitad el otro."""
        self.largo()
        with self.assertRaises(AppError) as caja:
            self.declarar("largo", "texto")
        self.assertEqual("errors.material_attribute_already_exists",
                         caja.exception.message_key)

    def test_the_same_name_in_another_family_is_fine(self):
        """"Largo" en desarmadores y "Largo" en cable son dos campos distintos."""
        self.largo()
        otro = self.declarar("Largo", "numero", familia=FAM_CABLE)
        self.assertEqual(FAM_CABLE, otro["id_product_family"])

    def test_a_characteristic_of_an_unknown_family_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self.declarar("Largo", "numero", familia=999999)
        self.assertEqual("errors.not_found", caja.exception.message_key)

    def test_a_data_type_outside_the_three_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self.declarar("Largo", "loquesea")
        self.assertEqual("errors.invalid_field", caja.exception.message_key)

    def test_a_list_without_values_is_refused(self):
        """Una lista sin valores es un campo de texto con otro nombre."""
        with self.assertRaises(AppError) as caja:
            self.declarar("Acabado", "lista")
        self.assertEqual("errors.material_attribute_options_required",
                         caja.exception.message_key)

    def test_values_on_something_that_is_not_a_list_are_refused(self):
        with self.assertRaises(AppError) as caja:
            self.declarar("Largo", "numero", options=["6", "8"])
        self.assertEqual("errors.material_attribute_options_not_applicable",
                         caja.exception.message_key)

    def test_a_list_keeps_its_declared_values(self):
        atributo = self.declarar("Mango", "lista", options=["Goma", "Plástico"])
        self.assertEqual(["Goma", "Plástico"],
                         [o["option_value"] for o in atributo["options"]])

    def test_the_data_type_cannot_be_changed(self):
        """Los valores ya capturados se quedarian en la forma del tipo viejo."""
        atributo = self.largo()
        with self.assertRaises(AppError) as caja:
            actualizar_atributo(atributo["id_material_attribute"],
                                {"data_type": "texto"}, ACTOR)
        self.assertEqual("errors.material_attribute_type_is_fixed",
                         caja.exception.message_key)

    def test_a_characteristic_can_be_renamed(self):
        atributo = self.largo()
        renombrado = actualizar_atributo(
            atributo["id_material_attribute"],
            {"attribute_name": "Longitud"}, ACTOR)["attribute"]
        self.assertEqual("Longitud", renombrado["attribute_name"])

    def test_the_family_lists_what_it_declares_in_order(self):
        self.declarar("Mango", "texto", sort_order=20)
        self.largo(sort_order=10)
        lista = atributos_de_la_familia(FAM_DESARMADORES, ACTOR)
        self.assertEqual(["Largo", "Mango"],
                         [a["attribute_name"] for a in lista["items"]])


class TestElMaterialLlenaLoQueSuFamiliaDeclara(BaseCaracteristicas):

    def test_a_material_fills_a_number(self):
        atributo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {atributo["id_material_attribute"]: "6"}}, ACTOR)

        valores = caracteristicas_de(DESARMADOR_1, ACTOR)["values"]
        self.assertEqual(1, len(valores))
        self.assertEqual("6", valores[0]["value_text"])
        # El numero aparte: es lo que hace que "6 o mas" sea una comparacion.
        self.assertEqual(6.0, valores[0]["value_number"])

    def test_six_point_zero_and_six_are_the_same_length(self):
        """Guardados distinto aparecerian como dos valores en cualquier agrupacion."""
        atributo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {atributo["id_material_attribute"]: "6.0"}}, ACTOR)
        guardar_valores(DESARMADOR_2,
                        {"values": {atributo["id_material_attribute"]: "6"}}, ACTOR)

        uno = caracteristicas_de(DESARMADOR_1, ACTOR)["values"][0]
        dos = caracteristicas_de(DESARMADOR_2, ACTOR)["values"][0]
        self.assertEqual(uno["value_text"], dos["value_text"])

    def test_something_that_is_not_a_number_is_refused(self):
        atributo = self.largo()
        with self.assertRaises(AppError) as caja:
            guardar_valores(
                DESARMADOR_1,
                {"values": {atributo["id_material_attribute"]: "seis pulgadas"}},
                ACTOR)
        self.assertEqual("errors.invalid_field", caja.exception.message_key)

    def test_a_list_value_outside_the_declared_ones_is_refused(self):
        """Es lo que impide que "mate", "Mate" y "MATE" sean tres acabados."""
        atributo = self.declarar("Mango", "lista", options=["Goma", "Plástico"])
        with self.assertRaises(AppError) as caja:
            guardar_valores(
                DESARMADOR_1,
                {"values": {atributo["id_material_attribute"]: "Madera"}}, ACTOR)
        self.assertEqual("errors.material_attribute_value_not_allowed",
                         caja.exception.message_key)
        self.assertEqual(["Goma", "Plástico"], caja.exception.meta["allowed"])

    def test_a_list_value_is_stored_as_the_declared_one_whatever_the_casing(self):
        """Se captura "goma" y queda "Goma": un solo valor, no dos."""
        atributo = self.declarar("Mango", "lista", options=["Goma", "Plástico"])
        guardar_valores(DESARMADOR_1,
                        {"values": {atributo["id_material_attribute"]: "goma"}},
                        ACTOR)

        valor = caracteristicas_de(DESARMADOR_1, ACTOR)["values"][0]
        self.assertEqual("Goma", valor["value_text"])
        self.assertIsNotNone(valor["id_material_attribute_option"])

    def test_a_characteristic_of_another_family_is_refused(self):
        """Ignorarlo dejaria al usuario creyendo que se guardo."""
        ajeno = self.declarar("Calibre", "numero", familia=FAM_CABLE)
        with self.assertRaises(AppError) as caja:
            guardar_valores(DESARMADOR_1,
                            {"values": {ajeno["id_material_attribute"]: "12"}},
                            ACTOR)
        self.assertEqual("errors.material_attribute_not_in_family",
                         caja.exception.message_key)

    def test_a_required_characteristic_left_empty_is_refused(self):
        atributo = self.largo(is_required=True)
        self.declarar("Mango", "texto")
        with self.assertRaises(AppError) as caja:
            guardar_valores(DESARMADOR_1, {"values": {}}, ACTOR)
        self.assertEqual("errors.material_attribute_required",
                         caja.exception.message_key)
        self.assertEqual(["Largo"], caja.exception.meta["missing"])
        self.assertTrue(atributo["is_required"])

    def test_saving_replaces_the_whole_set(self):
        """Lo que no viene se retira: quitar un campo no necesita otra llamada."""
        largo = self.largo()
        mango = self.declarar("Mango", "texto")
        guardar_valores(DESARMADOR_1, {"values": {
            largo["id_material_attribute"]: "6",
            mango["id_material_attribute"]: "Goma",
        }}, ACTOR)
        self.assertEqual(2, len(caracteristicas_de(DESARMADOR_1, ACTOR)["values"]))

        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "6"}}, ACTOR)

        quedan = caracteristicas_de(DESARMADOR_1, ACTOR)["values"]
        self.assertEqual(["Largo"], [v["attribute_name"] for v in quedan])

    def test_saving_twice_updates_instead_of_duplicating(self):
        """Dos filas de "Largo" para el mismo material: no habria cual vale."""
        largo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "6"}}, ACTOR)
        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "8"}}, ACTOR)

        valores = caracteristicas_de(DESARMADOR_1, ACTOR)["values"]
        self.assertEqual(1, len(valores))
        self.assertEqual(8.0, valores[0]["value_number"])

    def test_the_screen_gets_the_fields_and_the_values_together(self):
        """La pantalla necesita las dos: que preguntar, y que ya se contesto."""
        self.largo()
        self.declarar("Mango", "texto")
        todo = caracteristicas_de(DESARMADOR_1, ACTOR)
        self.assertEqual(2, len(todo["attributes"]))
        self.assertEqual([], todo["values"])


class TestNoSeBorraLoQueSeUsa(BaseCaracteristicas):

    def test_a_characteristic_in_use_is_not_deleted(self):
        largo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "6"}}, ACTOR)

        with self.assertRaises(AppError) as caja:
            eliminar_atributo(largo["id_material_attribute"], ACTOR)
        self.assertEqual("errors.material_attribute_in_use",
                         caja.exception.message_key)
        self.assertEqual(1, caja.exception.meta["materials_using_it"])

    def test_an_unused_characteristic_is_deleted(self):
        largo = self.largo()
        self.assertTrue(
            eliminar_atributo(largo["id_material_attribute"], ACTOR)["deleted"])
        self.assertEqual(0, atributos_de_la_familia(FAM_DESARMADORES,
                                                    ACTOR)["total"])

    def test_the_list_says_how_many_materials_use_each_one(self):
        """"Usada por 14 materiales" es una respuesta; "no se pudo eliminar" no."""
        largo = self.largo()
        for material in (DESARMADOR_1, DESARMADOR_2):
            guardar_valores(material,
                            {"values": {largo["id_material_attribute"]: "6"}},
                            ACTOR)

        lista = atributos_de_la_familia(FAM_DESARMADORES, ACTOR)
        self.assertEqual(2, lista["items"][0]["materials_using_it"])

    def test_an_option_in_use_is_not_deleted(self):
        mango = self.declarar("Mango", "lista", options=["Goma", "Plástico"])
        guardar_valores(DESARMADOR_1,
                        {"values": {mango["id_material_attribute"]: "Goma"}},
                        ACTOR)
        id_goma = mango["options"][0]["id_material_attribute_option"]

        with self.assertRaises(AppError) as caja:
            eliminar_opcion(id_goma, ACTOR)
        self.assertEqual("errors.material_attribute_option_in_use",
                         caja.exception.message_key)

    def test_an_option_can_be_added_later(self):
        mango = self.declarar("Mango", "lista", options=["Goma"])
        agregar_opcion(mango["id_material_attribute"],
                       {"option_value": "Madera"}, ACTOR)

        lista = atributos_de_la_familia(FAM_DESARMADORES, ACTOR)["items"][0]
        self.assertEqual(["Goma", "Madera"],
                         [o["option_value"] for o in lista["options"]])

    def test_an_option_on_something_that_is_not_a_list_is_refused(self):
        largo = self.largo()
        with self.assertRaises(AppError) as caja:
            agregar_opcion(largo["id_material_attribute"],
                           {"option_value": "6"}, ACTOR)
        self.assertEqual("errors.material_attribute_options_not_applicable",
                         caja.exception.message_key)


class TestLaPreguntaQueLoJustifica(BaseCaracteristicas):
    """"Cuantos desarmadores Truper planos de 6 pulgadas tengo."

    Es el motivo de todo lo anterior. Antes habia que abrir material por
    material y leer la descripcion.
    """

    def setUp(self):
        super().setUp()
        self.largo_id = self.largo()["id_material_attribute"]
        self.mango_id = self.declarar(
            "Mango", "lista", options=["Goma", "Plástico"])["id_material_attribute"]
        guardar_valores(DESARMADOR_1, {"values": {
            self.largo_id: "6", self.mango_id: "Goma"}}, ACTOR)
        guardar_valores(DESARMADOR_2, {"values": {
            self.largo_id: "10", self.mango_id: "Goma"}}, ACTOR)
        guardar_valores(DESARMADOR_3, {"values": {
            self.largo_id: "6", self.mango_id: "Plástico"}}, ACTOR)

    def test_it_finds_by_an_exact_value(self):
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [{"id_material_attribute": self.largo_id, "value": "6"}],
        }, ACTOR)
        self.assertEqual({DESARMADOR_1, DESARMADOR_3},
                         {x["id_material"] for x in r["items"]})

    def test_ten_is_greater_than_six_and_not_smaller(self):
        """Comparado como texto, "10" queda por debajo de "6" y la respuesta cambia."""
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [{"id_material_attribute": self.largo_id, "min": 7}],
        }, ACTOR)
        self.assertEqual([DESARMADOR_2], [x["id_material"] for x in r["items"]])

    def test_a_range_works_on_both_ends(self):
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [{"id_material_attribute": self.largo_id,
                          "min": 5, "max": 7}],
        }, ACTOR)
        self.assertEqual(2, r["total"])

    def test_two_criteria_are_an_intersection(self):
        """De 6 pulgadas Y de mango de goma: uno solo."""
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [
                {"id_material_attribute": self.largo_id, "value": "6"},
                {"id_material_attribute": self.mango_id, "value": "Goma"},
            ],
        }, ACTOR)
        self.assertEqual([DESARMADOR_1], [x["id_material"] for x in r["items"]])

    def test_the_family_narrows_it_even_with_no_criteria(self):
        r = materiales_que_cumplen({"id_product_family": FAM_CABLE}, ACTOR)
        self.assertEqual([CABLE], [x["id_material"] for x in r["items"]])

    def test_each_result_carries_its_characteristics(self):
        """Sin ellas habria que volver a preguntar por cada material encontrado."""
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [{"id_material_attribute": self.largo_id, "value": "6"}],
        }, ACTOR)
        uno = next(x for x in r["items"] if x["id_material"] == DESARMADOR_1)
        self.assertEqual({"Largo", "Mango"},
                         {a["attribute_name"] for a in uno["attributes"]})

    def test_nothing_matching_is_an_empty_answer_and_not_an_error(self):
        r = materiales_que_cumplen({
            "id_product_family": FAM_DESARMADORES,
            "criteria": [{"id_material_attribute": self.largo_id, "min": 100}],
        }, ACTOR)
        self.assertEqual(0, r["total"])
        self.assertEqual([], r["items"])


class TestSeLeeEnLote(BaseCaracteristicas):

    def test_the_characteristics_of_many_materials_come_in_two_queries(self):
        """Una consulta por material es el N+1 que ya costo 271 en el rastreo."""
        from sqlalchemy import event

        from app.models.session import engine

        largo = self.largo()
        mango = self.declarar("Mango", "texto")
        for material in (DESARMADOR_1, DESARMADOR_2, DESARMADOR_3):
            guardar_valores(material, {"values": {
                largo["id_material_attribute"]: "6",
                mango["id_material_attribute"]: "Goma",
            }}, ACTOR)

        with transaction_context() as db:
            valores_de_materiales(db, [DESARMADOR_1])  # calienta la compilacion

        cuenta = []
        registrar = lambda *a, **k: cuenta.append(1)  # noqa: E731
        event.listen(engine, "after_cursor_execute", registrar)
        try:
            with transaction_context() as db:
                todos = valores_de_materiales(
                    db, [DESARMADOR_1, DESARMADOR_2, DESARMADOR_3])
        finally:
            event.remove(engine, "after_cursor_execute", registrar)

        self.assertEqual(3, len(todos))
        self.assertLessEqual(
            len(cuenta), 4,
            "resolver tres materiales tomo %d consultas; una por material es el "
            "patron de N+1 que ya costo caro en el rastreo" % len(cuenta))

    def test_a_material_without_characteristics_is_simply_absent(self):
        """Y no una fila vacia: quien lee la respuesta no tiene que filtrarla."""
        largo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "6"}}, ACTOR)
        with transaction_context() as db:
            todos = valores_de_materiales(db, [DESARMADOR_1, DESARMADOR_2])
        self.assertEqual([DESARMADOR_1], list(todos))

    def test_the_number_keeps_its_precision(self):
        largo = self.largo()
        guardar_valores(DESARMADOR_1,
                        {"values": {largo["id_material_attribute"]: "6.5"}}, ACTOR)
        with transaction_context() as db:
            valor = valores_de_materiales(db, [DESARMADOR_1])[DESARMADOR_1][0]
        self.assertEqual(Decimal("6.5"), Decimal(str(valor["value_number"])))


if __name__ == "__main__":
    unittest.main()
