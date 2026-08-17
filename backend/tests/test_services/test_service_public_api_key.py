from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.public_api_key_service import PublicApiKeyService


class TestPublicApiKeyService(BackendTestCase):
    def test_crud_service_public_api_key(self):
        created = PublicApiKeyService.create(build_payload(PublicApiKeyService, {'label': 'Web produccion', 'key_hash': 'disabled_seed_key_hash', 'key_prefix': 'disabled', 'allowed_domains': '[]', 'rate_limit_per_min': 1, 'is_active': True, 'last_used_at': '2026-01-15T12:00:00', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = PublicApiKeyService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
