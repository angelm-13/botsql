from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.nm_template_task_service import NmTemplateTaskService


class TestNmTemplateTaskService(BackendTestCase):
    def test_crud_service_nm_template_task(self):
        created = NmTemplateTaskService.create({'created_by': 1})
        self.assertIsNotNone(created)
        page = NmTemplateTaskService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
