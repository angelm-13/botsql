"""Un producto no se marca "En almacen" (ENTRADA) sin existencia.

Hueco funcional que se cerro a proposito: el estado es un texto, asi que marcar En
almacen una pieza con existencia 0 la dejaba diciendo "esta aqui" sin que el libro lo
respaldara. Primero se registra la entrada (al menos 1 pieza) y despues se cambia el
estado. Nuevo y Usado ya no son estados: sus productos pasan a En almacen.
"""

from __future__ import annotations

from app.models import InventoryStock, Product
from app.models.session import transaction_context
from app.services.product_service import ProductService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_model, build_payload


class TestEnAlmacenExigeExistencia(BackendTestCase):

    def _crear(self, codigo, cantidad=0, estado=None):
        id_producto = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "broca", "cantidad": cantidad,
                             "product_code": codigo}))["id_product"]
        with transaction_context() as db:
            db.get(Product, id_producto).product_status = estado
        return id_producto

    def _estado(self, id_producto):
        with transaction_context() as db:
            return db.get(Product, id_producto).product_status

    def test_sin_existencia_no_se_marca_en_almacen(self):
        id_producto = self._crear("BRO-1", estado="EXTRAVIADO")
        for texto in ("ENTRADA", "entrada", "  Entrada "):
            with self.subTest(estado=texto), self.assertRaises(AppError) as raised:
                ProductService.update(id_producto, {"product_status": texto}, user_id=1)
            self.assertEqual("errors.product_status_needs_stock", raised.exception.message_key)
            self.assertEqual(409, raised.exception.status_code)
        self.assertEqual("EXTRAVIADO", self._estado(id_producto))

    def test_con_existencia_si_se_marca(self):
        id_producto = self._crear("BRO-2", cantidad=3, estado="SALIDA")

        ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)

        self.assertEqual("ENTRADA", self._estado(id_producto))

    def test_el_saldo_en_una_ubicacion_destraba_el_cambio(self):
        # Lo que la guarda lee es el saldo por ubicacion, el mismo que sube la entrada
        # de existencia; se pone directo para no armar aqui la cadena factura-proyecto
        # que exige el libro.
        id_producto = self._crear("BRO-3", estado="EXTRAVIADO")
        with self.assertRaises(AppError):
            ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)

        with transaction_context() as db:
            ubicacion = db.get(Product, id_producto).id_location
            db.add(build_model(InventoryStock, id_product=id_producto,
                               id_location=ubicacion, quantity=1))

        ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)
        self.assertEqual("ENTRADA", self._estado(id_producto))

    def test_otros_estados_ya_no_se_ponen_a_mano(self):
        id_producto = self._crear("BRO-4", estado="ENTRADA")

        with self.assertRaises(AppError) as raised:
            ProductService.update(id_producto, {"product_status": "DAÑADO"}, user_id=1)

        self.assertEqual("errors.product_status_via_voucher", raised.exception.message_key)
        self.assertEqual("ENTRADA", self._estado(id_producto))

    def test_guardar_otro_campo_de_un_producto_que_ya_esta_en_almacen_en_cero_sigue_funcionando(self):
        # Una pieza En almacen sin existencia (heredada, o con todo prestado): editarle
        # el color no cambia su estado, asi que no se le exige nada.
        id_producto = self._crear("BRO-5", estado="ENTRADA")

        ProductService.update(id_producto, {"product_status": "ENTRADA", "color": "rojo"}, user_id=1)

        self.assertEqual("ENTRADA", self._estado(id_producto))

    def test_el_alta_en_almacen_sin_cantidad_no_se_rechaza(self):
        self.assertTrue(ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "broca", "cantidad": 0,
                             "product_code": "BRO-6", "product_status": "ENTRADA"})))
