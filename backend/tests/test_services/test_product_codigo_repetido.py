"""Un codigo identifica a un solo producto vivo (caso ESC-06: ids 2132 y 2516)."""

from __future__ import annotations

from app.models import Product
from app.models.session import transaction_context
from app.services.product_service import ProductService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestElCodigoNoSeRepite(BackendTestCase):

    def _crear(self, codigo):
        return ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "escalera", "cantidad": 0,
                             "product_code": codigo}))["id_product"]

    def test_no_se_da_de_alta_otro_con_el_mismo_codigo_aunque_cambie_mayuscula_o_espacios(self):
        self._crear("ESC-06")
        for repetido in ("ESC-06", "esc-06", "  Esc-06 "):
            with self.subTest(codigo=repetido), self.assertRaises(AppError) as raised:
                self._crear(repetido)
            self.assertEqual("errors.product_code_duplicate", raised.exception.message_key)
            self.assertEqual(409, raised.exception.status_code)

    def test_un_codigo_dado_de_baja_se_puede_volver_a_usar(self):
        id_producto = self._crear("ESC-07")
        with transaction_context() as db:
            from datetime import datetime
            db.get(Product, id_producto).deletion_date = datetime.utcnow()
        self.assertTrue(self._crear("ESC-07"))

    def test_editar_otro_campo_de_un_producto_con_codigo_repetido_de_antes_sigue_funcionando(self):
        a = self._crear("DUP-1")
        with transaction_context() as db:
            db.get(Product, a).product_code = "DUP-2"
        b = self._crear("DUP-3")
        with transaction_context() as db:
            db.get(Product, b).product_code = "DUP-2"  # repetido heredado de la migracion
        ProductService.update(b, {"product_code": "DUP-2", "color": "rojo"}, user_id=1)

    def test_cambiar_el_codigo_a_uno_ocupado_se_rechaza(self):
        self._crear("OCU-1")
        otro = self._crear("OCU-2")
        with self.assertRaises(AppError) as raised:
            ProductService.update(otro, {"product_code": "ocu-1"}, user_id=1)
        self.assertEqual("errors.product_code_duplicate", raised.exception.message_key)

    def test_entrada_es_un_estado_valido_y_limpia_el_del_catalogo(self):
        id_producto = self._crear("BRS-9")
        with transaction_context() as db:
            db.get(Product, id_producto).product_status = "EXTRAVIADO"
        ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            self.assertEqual("ENTRADA", producto.product_status)
            self.assertIsNone(producto.id_inventory_status)
