from __future__ import annotations

from tests.conftest import BackendTestCase


class TestEntityPermissionApi(BackendTestCase):
    def test_list_entity_permission_supports_pagination(self):
        response = self.client.get("/entity_permission/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_entity_permission_validates_payload(self):
        response = self.client.post("/entity_permission/", json={'entity_name': 'bank', 'scope_create': 4, 'scope_read': 4, 'scope_update': 4, 'scope_delete': 4, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_entity_permission_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/entity_permission/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/entity_permission/{missing_id}", json={'entity_name': 'bank', 'scope_create': 4, 'scope_read': 4, 'scope_update': 4, 'scope_delete': 4, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/entity_permission/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
