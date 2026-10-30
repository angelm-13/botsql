"""La clase de un articulo: herramienta, consumible, sobrante o recargable.

* Una sola lista de clases y un 400 que nombra el campo si llega otra.
* El material la trae por omision, el producto la hereda y puede cambiarla.
* El renglon de una orden de compra la lleva (por omision, la de su material) y al recibir
  el producto que aun no tiene clase la toma de ahi, sin pisar la que ya tenia.
* "Localizar" filtra por clase, contando la del producto o, sin ella, la de su material.
"""
from __future__ import annotations

import unittest

from app.models import Material, Product
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.item_class import ITEM_CLASSES, effective_item_class, normalize_item_class
from app.services.inventory_trace_service import localizar
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from tests.test_api.test_api_purchase_receive import BaseRecepcion


class TestLaListaDeClases(unittest.TestCase):
    def test_the_four_classes_are_known(self):
        self.assertEqual(("herramienta", "consumible", "sobrante", "recargable"), ITEM_CLASSES)

    def test_blank_means_no_class_and_case_is_ignored(self):
        self.assertIsNone(normalize_item_class(None))
        self.assertIsNone(normalize_item_class("  "))
        self.assertEqual("recargable", normalize_item_class(" Recargable "))

    def test_an_unknown_class_is_a_400_that_names_the_field(self):
        with self.assertRaises(AppError) as e:
            normalize_item_class("chatarra", "item_class")
        self.assertEqual(400, e.exception.status_code)
        self.assertEqual("item_class", e.exception.meta["field"])

    def test_the_material_class_wins_over_the_product(self):
        material = type("M", (), {"item_class": "consumible"})()
        sin_clase = type("M", (), {"item_class": None})()
        self.assertEqual("consumible", effective_item_class(type("P", (), {"item_class": None})(), material))
        self.assertEqual("consumible", effective_item_class(type("P", (), {"item_class": "herramienta"})(), material))
        self.assertEqual("herramienta", effective_item_class(type("P", (), {"item_class": "herramienta"})(), sin_clase))
        self.assertIsNone(effective_item_class(type("P", (), {"item_class": None})(), None))


class TestLaClaseEnLosModelos(unittest.TestCase):
    def test_a_material_and_a_product_reject_an_unknown_class(self):
        with self.assertRaises(AppError):
            Material(item_class="chatarra")
        with self.assertRaises(AppError):
            Product(item_class="chatarra")

    def test_the_class_is_serialized(self):
        self.assertEqual("recargable", Material(item_class="recargable").serialize()["item_class"])
        self.assertEqual("sobrante", Product(item_class="sobrante").serialize()["item_class"])


class TestLaClaseEnLaOrdenDeCompra(BaseRecepcion):
    def _renglon_libre(self, **extra):
        return {"description": "Extintor 6 kg PQS", "quantity": 2, "unit_cost": 800, **extra}

    def _crear_libre(self, **extra):
        return self._crear(lineas=[self._renglon_libre(**extra)])

    def test_a_free_line_carries_the_class_it_was_given(self):
        respuesta = self._crear_libre(item_class="recargable")
        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        self.assertEqual("recargable", self.json(respuesta)["lines"][0]["item_class"])

    def test_a_line_without_class_has_none(self):
        self.assertIsNone(self.json(self._crear_libre())["lines"][0]["item_class"])

    def test_an_unknown_class_on_a_line_is_rejected(self):
        respuesta = self._crear_libre(item_class="chatarra")
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("item_class", self.json(respuesta)["meta"]["field"])

    def test_a_line_of_a_material_takes_the_class_of_the_material(self):
        with transaction_context() as db:
            material = build_model(Material, material_description="Tanque de gas")
            material.id_material = 800
            material.item_class = "recargable"
            db.add(material)
        respuesta = self._crear_libre(id_material=800)
        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        self.assertEqual("recargable", self.json(respuesta)["lines"][0]["item_class"])

    def _comprada_de_un_material(self, clase_del_material, clase_del_renglon):
        """Una orden comprada con un solo renglon de un material; devuelve (orden, renglon, material)."""
        with transaction_context() as db:
            material = build_model(Material, material_description="Tanque de gas")
            material.id_material = 810
            material.item_class = clase_del_material
            db.add(material)
        id_orden = self._orden_completa(lineas=[{
            "description": "Tanque de gas", "quantity": 2, "unit_cost": 5000,
            "id_material": 810, "item_class": clase_del_renglon}])
        self.assertEqual(200, self._comprar(id_orden).status_code)
        linea = self._leer(id_orden)["lines"][0]
        return id_orden, linea, 810

    def _recibir_todo(self, id_orden, linea):
        return self._recibir(id_orden, [{
            "id_purchase_order_line": linea["id_purchase_order_line"],
            "quantity": linea["quantity"]}])

    def test_receiving_classifies_a_material_that_has_no_class(self):
        id_orden, linea, id_material = self._comprada_de_un_material(None, "recargable")

        self.assertEqual(200, self._recibir_todo(id_orden, linea).status_code)

        with transaction_context() as db:
            self.assertEqual("recargable", db.get(Material, id_material).item_class)

    def test_receiving_does_not_overwrite_the_class_a_material_already_has(self):
        id_orden, linea, id_material = self._comprada_de_un_material("herramienta", "consumible")

        self.assertEqual(200, self._recibir_todo(id_orden, linea).status_code)

        with transaction_context() as db:
            self.assertEqual("herramienta", db.get(Material, id_material).item_class)


class TestFiltrarPorClase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for id_material, clase in ((801, "herramienta"), (802, None)):
                # `build_model` inventa un valor para cualquier campo que se le pase, aun
                # `None`: la clase se pone aparte.
                material = build_model(Material, material_description="Mat %d" % id_material)
                material.id_material = id_material
                material.item_class = clase
                db.add(material)
            db.flush()
            for id_product, id_material, clase, descripcion in (
                    (1, 801, None, "Taladro (hereda del material)"),
                    (2, 802, "recargable", "Extintor (propio)"),
                    (3, 802, "consumible", "Disco de corte (propio)"),
                    (4, 802, None, "Tornillo (sin clase)")):
                producto = build_model(Product, id_material=id_material,
                                       descripcion=descripcion, product_code="C%d" % id_product)
                producto.id_product = id_product
                producto.item_class = clase
                db.add(producto)

    def _buscar(self, **filtros):
        return localizar("", {"is_superuser": True}, con_piezas=False, **filtros)

    def _descripciones(self, resultado):
        return {i["descripcion"].split(" (")[0] for i in resultado["items"]}

    def test_a_product_of_a_material_without_class_uses_its_own(self):
        self.assertEqual({"Extintor"}, self._descripciones(self._buscar(clase="recargable")))
        self.assertEqual({"Disco de corte"}, self._descripciones(self._buscar(clase="consumible")))

    def test_the_class_of_the_material_wins_over_the_product(self):
        with transaction_context() as db:
            producto = db.get(Product, 1)
            producto.item_class = "consumible"
        self.assertEqual({"Taladro"}, self._descripciones(self._buscar(clase="herramienta")))
        self.assertNotIn("Taladro", self._descripciones(self._buscar(clase="consumible")))

    def test_without_a_filter_everything_is_listed_with_its_effective_class(self):
        resultado = self._buscar()
        clases = {i["descripcion"].split(" (")[0]: i["item_class"] for i in resultado["items"]}
        self.assertEqual({"Taladro": "herramienta", "Extintor": "recargable",
                          "Disco de corte": "consumible", "Tornillo": None}, clases)

    def test_an_unknown_class_is_rejected(self):
        with self.assertRaises(AppError):
            self._buscar(clase="chatarra")

    def test_the_applied_filter_is_echoed(self):
        self.assertEqual("sobrante", self._buscar(clase="sobrante")["filters"]["item_class"])
