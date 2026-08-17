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
