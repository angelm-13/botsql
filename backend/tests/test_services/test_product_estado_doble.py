"""El estado del producto se escribe en sus dos columnas a la vez.

`product_status` (texto del sistema anterior, que el formulario escribe con el codigo
del catalogo) e `id_inventory_status` (catalogo) se guardaban por separado y el producto
quedaba diciendo dos cosas: MARR4 "usado" con el catalogo en "extraviado".
"""

from __future__ import annotations

import unittest

from app.models import Product
from app.models.inventory_status import InventoryStatus
from app.models.session import transaction_context
from app.services.product_service import ProductService
from app.utils.product_status import clave, codigo_de_catalogo
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload

CATALOGO = ("nuevo", "usado", "en_reparacion", "danado", "retirado", "extraviado")


class TestLaTraduccionDelTexto(unittest.TestCase):

    def test_cada_texto_historico_dice_su_codigo(self):
        casos = {
            "DAÑADO": "danado", "danado": "danado", "EQ. DAÑADOS": "danado",
            "DESTRUCCION": "retirado", "EXTRAVIADO": "extraviado",
            "EN REPARACION": "en_reparacion", "en_reparacion": "en_reparacion",
            "usado": "usado", " Nuevo ": "nuevo",
        }
        for texto, codigo in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(codigo, codigo_de_catalogo(texto))

    def test_entrada_y_salida_no_son_estados(self):
        for texto in ("ENTRADA", "SALIDA", "", None, "algo raro"):
            with self.subTest(texto=texto):
                self.assertIsNone(codigo_de_catalogo(texto))

    def test_la_clave_ignora_acentos_y_mayusculas(self):
        self.assertEqual("danado", clave("  DAÑADO "))


class BaseEstadoDoble(BackendTestCase):

    sembrar_catalogo = True

    def setUp(self):
        super().setUp()
        if self.sembrar_catalogo:
            with transaction_context() as db:
                db.add_all([
                    InventoryStatus(
                        inventory_status_code=codigo, inventory_status_description=codigo,
                        color="#000000", entity_scope="product", flow_scope="inventory",
                        id_department=1, id_minimum_level=1, is_active=True,
                        is_terminal=codigo == "retirado",
                        visible_to_other_departments=False, sort_order=10, created_by=1)
                    for codigo in CATALOGO
                ])

    def _producto(self, product_status=None, id_inventory_status=None):
        """Un producto con el estado dado. Se escribe directo en la base: el alta
        pasa por la fabrica de pruebas, que rellena ambos campos con basura."""
        id_producto = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "herramienta", "cantidad": 0}
        ))["id_product"]
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            producto.product_status = product_status
            producto.id_inventory_status = id_inventory_status
        return id_producto

    def _id_de(self, codigo):
        with transaction_context() as db:
            return db.query(InventoryStatus).filter_by(
                inventory_status_code=codigo).one().id_inventory_status

    def _estado(self, id_producto):
        """(codigo del catalogo o None, texto)."""
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            codigo = None
            if producto.id_inventory_status is not None:
                codigo = db.get(InventoryStatus, producto.id_inventory_status).inventory_status_code
            return codigo, producto.product_status


class TestElEstadoSeEscribeEnLasDosColumnas(BaseEstadoDoble):

    def test_cambiar_el_texto_pone_el_catalogo(self):
        id_producto = self._producto()
        ProductService.update(id_producto, {"product_status": "usado"}, user_id=1)
        self.assertEqual(("usado", "usado"), self._estado(id_producto))

    def test_el_caso_de_marr4_el_texto_corrige_un_catalogo_extraviado(self):
        id_producto = self._producto(
            product_status="EXTRAVIADO", id_inventory_status=self._id_de("extraviado"))
        self.assertEqual(("extraviado", "EXTRAVIADO"), self._estado(id_producto))

        # Lo que manda el formulario: el registro completo, con el id viejo.
        ProductService.update(id_producto, {
            "product_status": "usado", "id_inventory_status": self._id_de("extraviado"),
        }, user_id=1)

        self.assertEqual(("usado", "usado"), self._estado(id_producto))

    def test_un_texto_que_no_es_estado_limpia_el_catalogo(self):
        id_producto = self._producto(
            product_status="EXTRAVIADO", id_inventory_status=self._id_de("extraviado"))
        # Volver a En almacen exige existencia (ver test_product_estado_exige_existencia).
        with transaction_context() as db:
            db.get(Product, id_producto).cantidad = 1
        ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)
        self.assertEqual((None, "ENTRADA"), self._estado(id_producto))

    def test_cambiar_el_catalogo_pone_el_texto(self):
        id_producto = self._producto(product_status="ENTRADA")
        ProductService.update(
            id_producto, {"id_inventory_status": self._id_de("en_reparacion")}, user_id=1)
        self.assertEqual(("en_reparacion", "en_reparacion"), self._estado(id_producto))

    def test_quitar_el_catalogo_quita_un_texto_que_decia_un_estado(self):
        id_producto = self._producto(
            product_status="danado", id_inventory_status=self._id_de("danado"))
        ProductService.update(id_producto, {"id_inventory_status": None}, user_id=1)
        self.assertEqual((None, None), self._estado(id_producto))

    def test_si_cambian_los_dos_manda_el_catalogo(self):
        id_producto = self._producto(
            product_status="usado", id_inventory_status=self._id_de("usado"))
        ProductService.update(id_producto, {
            "product_status": "nuevo", "id_inventory_status": self._id_de("danado"),
        }, user_id=1)
        self.assertEqual(("danado", "danado"), self._estado(id_producto))

    def test_guardar_el_registro_completo_sin_tocar_el_estado_no_lo_mueve(self):
        id_producto = self._producto(
            product_status="DAÑADO", id_inventory_status=self._id_de("danado"))
        ProductService.update(id_producto, {
            "product_status": "DAÑADO", "id_inventory_status": self._id_de("danado"),
            "note": "editada",
        }, user_id=1)
        # El texto historico no se reescribe si solo cambio otra cosa.
        self.assertEqual(("danado", "DAÑADO"), self._estado(id_producto))

    def test_el_alta_con_solo_el_texto_trae_el_catalogo(self):
        payload = ProductService._sincronizar_estado(None, {"product_status": "usado"})
        self.assertEqual(self._id_de("usado"), payload["id_inventory_status"])


class TestSinCatalogoSembrado(BaseEstadoDoble):

    sembrar_catalogo = False

    def test_un_catalogo_vacio_no_tumba_el_guardado(self):
        id_producto = self._producto()
        ProductService.update(id_producto, {"product_status": "usado"}, user_id=1)
        self.assertEqual((None, "usado"), self._estado(id_producto))


if __name__ == "__main__":
    unittest.main()
