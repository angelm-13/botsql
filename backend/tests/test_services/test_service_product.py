from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.product_service import ProductService


class TestProductService(BackendTestCase):
    def test_crud_service_product(self):
        created = ProductService.create(build_payload(ProductService, {'gross_price': 10.5, 'color': 'test color', 'is_directly_related_to_product_service': True, 'product_status': 'test state', 'path_imagen': 'test path_imagen', 'product_code': 'test code', 'note': 'test note', 'created_by': 1, 'descripcion': 'test_descripcion', 'cantidad': 'test_cantidad'}))
        self.assertIsNotNone(created)
        page = ProductService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)


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
