from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.brand_service import BrandService


class TestBrandService(BackendTestCase):
    def test_crud_service_brand(self):
        created = BrandService.create({'brand_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = BrandService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
