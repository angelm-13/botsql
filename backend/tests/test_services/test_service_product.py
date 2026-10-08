from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.product_service import ProductService
from app.utils.errors import AppError


class TestProductService(BackendTestCase):
    def test_crud_service_product(self):
        created = ProductService.create(build_payload(ProductService, {'gross_price': 10.5, 'color': 'test color', 'is_directly_related_to_product_service': True, 'product_status': 'test state', 'path_imagen': 'test path_imagen', 'product_code': 'test code', 'note': 'test note', 'created_by': 1, 'descripcion': 'test_descripcion', 'cantidad': 'test_cantidad'}))
        self.assertIsNotNone(created)
        page = ProductService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)


class TestLaCantidadNoSeEditaDirecto(BackendTestCase):
    """`product.cantidad` es la suma de `inventory_stock` -- mantenida
    EXCLUSIVAMENTE por los movimientos de inventario (entrada, salida,
    ajuste, traspaso), cada uno con su capacidad, su motivo obligatorio y
    su renglon en el ledger. `PUT /product/<id>` no puede ser un segundo
    camino que cambie el saldo sin ninguna de esas protecciones -- hallazgo
    de la auditoria de seguridad del 2026-10-06.
    """

    def _producto(self, cantidad=5):
        return ProductService.create(build_payload(
            ProductService, {'created_by': 1, 'descripcion': 'test', 'cantidad': cantidad}))

    def test_changing_the_quantity_through_update_is_rejected(self):
        creado = self._producto(cantidad=5)

        with self.assertRaises(AppError) as contexto:
            ProductService.update(creado['id_product'], {'cantidad': 999})

        self.assertEqual('errors.cantidad_no_se_edita_directo', contexto.exception.message_key)
        # Y el rechazo no deja el saldo a medias: sigue como nacio.
        actualizado = ProductService.list(
            page=1, per_page=1, filters={'id_product': creado['id_product']}, sort=None)
        self.assertEqual(5, actualizado['items'][0]['cantidad'])

    def test_resubmitting_the_same_quantity_is_a_no_op_that_does_not_block_the_rest_of_the_form(self):
        """El formulario de edicion manda el registro completo, cantidad
        incluida; si no cambio, no se esta pidiendo nada que el backend deba
        rechazar -- mismo trato que ya recibe `lot_control`."""
        creado = self._producto(cantidad=5)

        guardado = ProductService.update(
            creado['id_product'], {'cantidad': 5, 'descripcion': 'nueva descripcion'})

        self.assertEqual('nueva descripcion', guardado['descripcion'])
        self.assertEqual(5, guardado['cantidad'])

    def test_it_still_works_as_the_initial_seed_at_creation(self):
        """Solo `update` lo bloquea -- al CREAR, `cantidad` sigue siendo
        legitima: es con lo que nace el producto, y de ahi sale la existencia
        inicial (`sembrar_existencia_inicial`)."""
        creado = self._producto(cantidad=12)

        self.assertEqual(12, creado['cantidad'])


class TestProductoHeredaLaFotoDelMaterial(BackendTestCase):
    """La foto del material la heredan los productos sin foto propia (solo lectura)."""

    def test_a_product_without_photo_borrows_its_materials_and_its_own_wins(self):
        from app.models import Material
        from app.models.session import transaction_context
        from app.services.product_service import ProductService

        from app.services.material_service import MaterialService

        id_material = MaterialService.create(build_payload(
            MaterialService, {"material_description": "material con foto", "created_by": 1}
        ))["id_material"]
        with transaction_context() as db:
            db.get(Material, id_material).path_imagen = "uploads/products/m_test.png"

        sin_foto = {"id_product": 1, "id_material": id_material, "path_imagen": None}
        con_foto = {"id_product": 2, "id_material": id_material, "path_imagen": "uploads/products/p_2.png"}
        sin_material = {"id_product": 3, "id_material": None, "path_imagen": None}
        ProductService.heredar_foto_del_material([sin_foto, con_foto, sin_material])

        self.assertEqual("uploads/products/m_test.png", sin_foto["path_imagen"])
        self.assertEqual("uploads/products/p_2.png", con_foto["path_imagen"])
        self.assertIsNone(sin_material["path_imagen"])
