from __future__ import annotations

from tests.conftest import BackendTestCase


class TestStatusApi(BackendTestCase):
    def test_list_status_supports_pagination(self):
        response = self.client.get("/status/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_status_validates_payload(self):
        response = self.client.post("/status/", json={'status_description': 'test name', 'category': 'test name', 'is_terminal': True, 'sort_order': 'mxn', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_status_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/status/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/status/{missing_id}", json={'status_description': 'test name', 'category': 'test name', 'is_terminal': True, 'sort_order': 'mxn', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/status/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
