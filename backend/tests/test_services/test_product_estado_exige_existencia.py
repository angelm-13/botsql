"""Un producto no pasa a Nuevo o Usado sin existencia.

Hueco funcional que se cerro a proposito: el estado es un texto, asi que marcar como
Nuevo o Usado un producto con existencia 0 lo dejaba diciendo "esta en el almacen" sin
que el libro lo respaldara. Primero se registra la entrada (al menos 1 pieza) y despues
se cambia el estado.
"""

from __future__ import annotations

from app.models import Product
from app.models.session import transaction_context
from app.services.product_service import ProductService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestNuevoOUsadoExigeExistencia(BackendTestCase):

    def _crear(self, codigo, cantidad=0, **extra):
        return ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "broca", "cantidad": cantidad,
                             "product_code": codigo, **extra}))["id_product"]

    def _estado(self, id_producto):
        with transaction_context() as db:
            return db.get(Product, id_producto).product_status

    def test_sin_existencia_no_se_marca_como_nuevo_ni_como_usado(self):
        id_producto = self._crear("BRO-1")
        for estado in ("NUEVO", "usado", "  Usado "):
            with self.subTest(estado=estado), self.assertRaises(AppError) as raised:
                ProductService.update(id_producto, {"product_status": estado}, user_id=1)
            self.assertEqual("errors.product_status_needs_stock", raised.exception.message_key)
            self.assertEqual(409, raised.exception.status_code)
        self.assertNotIn(self._estado(id_producto), ("NUEVO", "usado"))

    def test_con_existencia_si_se_marca(self):
        id_producto = self._crear("BRO-2", cantidad=3)

        ProductService.update(id_producto, {"product_status": "USADO"}, user_id=1)

        self.assertEqual("USADO", self._estado(id_producto))

    def test_el_saldo_en_una_ubicacion_destraba_el_cambio(self):
        # Lo que la guarda lee es el saldo por ubicacion, el mismo que sube la entrada
        # de existencia; se pone directo para no armar aqui la cadena factura-proyecto
        # que exige el libro.
        from app.models import InventoryStock
        from tests.model_factory import build_model

        id_producto = self._crear("BRO-3")
        with self.assertRaises(AppError):
            ProductService.update(id_producto, {"product_status": "NUEVO"}, user_id=1)

        with transaction_context() as db:
            ubicacion = db.get(Product, id_producto).id_location
            db.add(build_model(InventoryStock, id_product=id_producto,
                               id_location=ubicacion, quantity=1))

        ProductService.update(id_producto, {"product_status": "NUEVO"}, user_id=1)
        self.assertEqual("NUEVO", self._estado(id_producto))

    def test_otros_estados_no_piden_existencia(self):
        id_producto = self._crear("BRO-4")

        ProductService.update(id_producto, {"product_status": "DAÑADO"}, user_id=1)

        self.assertEqual("DAÑADO", self._estado(id_producto))

    def test_guardar_otro_campo_de_un_producto_que_ya_es_nuevo_en_cero_sigue_funcionando(self):
        # Una pieza nueva que esta prestada tiene existencia 0: editarle el color no
        # cambia su estado, asi que no se le exige nada.
        id_producto = self._crear("BRO-5", cantidad=2)
        ProductService.update(id_producto, {"product_status": "NUEVO"}, user_id=1)
        with transaction_context() as db:
            db.get(Product, id_producto).cantidad = 0

        ProductService.update(id_producto, {"product_status": "NUEVO", "color": "rojo"}, user_id=1)

        self.assertEqual("NUEVO", self._estado(id_producto))

    def test_en_el_alta_la_cantidad_declarada_cuenta(self):
        with self.assertRaises(AppError) as raised:
            self._crear("BRO-6", cantidad=0, product_status="NUEVO")
        self.assertEqual("errors.product_status_needs_stock", raised.exception.message_key)

        self.assertTrue(self._crear("BRO-7", cantidad=2, product_status="NUEVO"))
