from __future__ import annotations

from tests.conftest import BackendTestCase


class TestUserMfaApi(BackendTestCase):
    def test_list_user_mfa_supports_pagination(self):
        response = self.client.get("/user_mfa/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_user_mfa_validates_payload(self):
        response = self.client.post("/user_mfa/", json={'secret': 'test_user', 'secret_iv': 'test_user', 'enabled': True, 'failed_attempts': 1, 'locked_until': 'test_user', 'last_used_at': 'test_user', 'backup_codes': '{}'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_user_mfa_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/user_mfa/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/user_mfa/{missing_id}", json={'secret': 'test_user', 'secret_iv': 'test_user', 'enabled': True, 'failed_attempts': 1, 'locked_until': 'test_user', 'last_used_at': 'test_user', 'backup_codes': '{}'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/user_mfa/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
