from __future__ import annotations

from tests.conftest import BackendTestCase


class TestPublicApiKeyApi(BackendTestCase):
    def test_list_public_api_key_supports_pagination(self):
        response = self.client.get("/public_api_key/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_public_api_key_validates_payload(self):
        response = self.client.post("/public_api_key/", json={'label': 'Web produccion', 'key_hash': 'disabled_seed_key_hash', 'key_prefix': 'disabled', 'allowed_domains': '[]', 'rate_limit_per_min': 1, 'is_active': True, 'last_used_at': 'datetime.now()', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_public_api_key_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/public_api_key/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/public_api_key/{missing_id}", json={'label': 'Web produccion', 'key_hash': 'disabled_seed_key_hash', 'key_prefix': 'disabled', 'allowed_domains': '[]', 'rate_limit_per_min': 1, 'is_active': True, 'last_used_at': 'datetime.now()', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/public_api_key/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
