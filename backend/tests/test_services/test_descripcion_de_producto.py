from __future__ import annotations

import unittest

from app.services.product_service import ProductService
from app.utils.errors import AppError
from app.utils.product_description import es_valida, sugerir
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestFormatoDeOracion(unittest.TestCase):
    def test_accepts_sentence_case_with_numbers_and_fractions(self):
        for texto in ("Pulidor chico 3/4", "Cemento gris 50kg", "Broca 1/4 - larga",
                      "Tornillo hexagonal", "Codo PVC 90", "PVC codo 90", "Foco LED 9w"):
            self.assertTrue(es_valida(texto), texto)

    def test_rejects_what_is_not_sentence_case(self):
        for texto in ("pulidor chico", "PULIDOR CHICO 3/4", "Pulidor Chico",
                      "Pulidor  chico", " Pulidor chico", "3/4 pulidor", "Pulidor_chico"):
            self.assertFalse(es_valida(texto), texto)

    def test_blank_is_accepted_because_the_field_is_optional(self):
        self.assertTrue(es_valida(None))
        self.assertTrue(es_valida("  "))

    def test_suggestion_fixes_the_common_mistakes(self):
        self.assertEqual("Pulidor chico 3/4", sugerir("pulidor chico 3/4"))
        self.assertEqual("Pulidor chico 3/4", sugerir("PULIDOR CHICO 3/4"))
        self.assertEqual("Pulidor chico", sugerir("  Pulidor   Chico "))

    def test_acronyms_survive_unless_the_whole_text_is_shouting(self):
        self.assertEqual("Codo PVC 90", sugerir("codo PVC 90"))
        self.assertEqual("Codo PVC 90", sugerir("CODO PVC 90"))
        # En un texto todo en mayusculas solo se conservan las siglas conocidas.
        self.assertEqual("Taladro xyz", sugerir("TALADRO XYZ"))

    def test_single_letters_and_model_codes_keep_their_capitals(self):
        self.assertEqual('Prensa C 3"', sugerir('PRENSA C 3"'))
        self.assertEqual("Pistola cafetateadora B26T600", sugerir("PISTOLA CAFETATEADORA B26T600"))
        self.assertEqual("Rompedor 18kg", sugerir("ROMPEDOR 18KG"))
        self.assertEqual("Tuerca y tornillo", sugerir("TUERCA Y TORNILLO"))
        self.assertTrue(es_valida('Prensa C 3"'))

    def test_a_suggestion_is_always_valid(self):
        for texto in ("PULIDOR CHICO 3/4", "pulidor Chico", "CODO PVC 90", "broca HSS 1/4"):
            self.assertTrue(es_valida(sugerir(texto)), texto)


class TestLaRutaExigeElFormato(BackendTestCase):
    def test_a_new_description_is_checked_and_the_error_carries_the_suggestion(self):
        with self.assertRaises(AppError) as ctx:
            ProductService.exigir_descripcion_en_oracion({"descripcion": "PULIDOR CHICO 3/4"})
        self.assertEqual("descripcion", ctx.exception.meta["field"])
        self.assertEqual("Pulidor chico 3/4", ctx.exception.meta["suggestion"])
        ProductService.exigir_descripcion_en_oracion({"descripcion": "Pulidor chico 3/4"})
        ProductService.exigir_descripcion_en_oracion({"cantidad": 3})

    def test_editing_a_migrated_product_does_not_trip_on_its_untouched_description(self):
        creado = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "PULIDOR CHICO 3/4", "cantidad": 0}))
        id_product = creado["id_product"]
        # Mismo texto (el formulario devuelve el registro completo): pasa.
        ProductService.exigir_descripcion_en_oracion(
            {"descripcion": "PULIDOR CHICO 3/4"}, item_id=id_product)
        # Si lo cambia, ya debe cumplir.
        with self.assertRaises(AppError):
            ProductService.exigir_descripcion_en_oracion(
                {"descripcion": "PULIDOR GRANDE"}, item_id=id_product)
        ProductService.exigir_descripcion_en_oracion(
            {"descripcion": "Pulidor grande"}, item_id=id_product)


class TestLaExistenciaNoSeEditaAMano(BackendTestCase):
    def test_writing_cantidad_on_update_is_refused_unless_it_is_unchanged(self):
        creado = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "Tornillo", "cantidad": 5}))
        id_product = creado["id_product"]
        # El formulario devuelve el registro completo: mismo valor, no mueve nada.
        ProductService.update(id_product, {"cantidad": "5", "note": "editado"}, user_id=1)
        with self.assertRaises(AppError) as ctx:
            ProductService.update(id_product, {"cantidad": 50}, user_id=1)
        self.assertEqual("cantidad", ctx.exception.meta["field"])
        self.assertEqual(5, ProductService.get(id_product)["cantidad"])
