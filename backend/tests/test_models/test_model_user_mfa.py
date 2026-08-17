from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.user_mfa import UserMfa


class TestUserMfaModel(BackendTestCase):
    def test_create_serialize_summary_delete_user_mfa(self):
        with transaction_context() as session:
            item = UserMfa(
            secret='test_user',
            secret_iv='test_user',
            enabled=True,
            failed_attempts=1,
            locked_until='test_user',
            last_used_at='test_user',
            backup_codes='{}'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
