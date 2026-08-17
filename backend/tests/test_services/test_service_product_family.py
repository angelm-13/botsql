from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.product_family_service import ProductFamilyService


class TestProductFamilyService(BackendTestCase):
    def test_crud_service_product_family(self):
        created = ProductFamilyService.create({'product_family_description': 'test description', 'type': 'tool', 'created_by': 1})
        self.assertIsNotNone(created)
        page = ProductFamilyService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
