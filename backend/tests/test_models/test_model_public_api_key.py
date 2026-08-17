from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.public_api_key import PublicApiKey


class TestPublicApiKeyModel(BackendTestCase):
    def test_create_serialize_summary_delete_public_api_key(self):
        with transaction_context() as session:
            item = build_model(PublicApiKey,
            label='Web produccion',
            key_hash='disabled_seed_key_hash',
            key_prefix='disabled',
            allowed_domains='[]',
            rate_limit_per_min=1,
            is_active=True,
            last_used_at='2026-01-15T12:00:00',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
