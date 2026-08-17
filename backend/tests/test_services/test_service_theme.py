from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.theme_service import ThemeService


class TestThemeService(BackendTestCase):
    def test_crud_service_theme(self):
        created = ThemeService.create(build_payload(ThemeService, {'created_by': 1, 'tenant_id': 1, 'primary_color': '#0D47A1', 'secondary_color': '#0D47A1', 'background_color': '#0D47A1', 'text_color': '#0D47A1', 'highlight_color': '#0D47A1', 'success_color': '#0D47A1', 'error_color': '#0D47A1'}))
        self.assertIsNotNone(created)
        page = ThemeService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
