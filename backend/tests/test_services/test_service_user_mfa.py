from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.user_mfa_service import UserMfaService


class TestUserMfaService(BackendTestCase):
    def test_crud_service_user_mfa(self):
        created = UserMfaService.create({'secret': 'test_user', 'secret_iv': 'test_user', 'enabled': True, 'failed_attempts': 1, 'locked_until': 'test_user', 'last_used_at': 'test_user', 'backup_codes': '{}'})
        self.assertIsNotNone(created)
        page = UserMfaService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
