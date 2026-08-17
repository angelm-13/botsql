from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.template_service import TemplateService


class TestTemplateService(BackendTestCase):
    def test_crud_service_template(self):
        created = TemplateService.create({'template_description': 'test permission description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = TemplateService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
