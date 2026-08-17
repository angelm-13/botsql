from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.product_sale_config_service import ProductSaleConfigService


class TestProductSaleConfigService(BackendTestCase):
    def test_crud_service_product_sale_config(self):
        created = ProductSaleConfigService.create(build_payload(ProductSaleConfigService, {'margin_percent': 10.5, 'manual_price': 10.5, 'is_active': True, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = ProductSaleConfigService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
