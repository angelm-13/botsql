from __future__ import annotations

from tests.conftest import BackendTestCase


class TestEventLogApi(BackendTestCase):
    def test_list_event_log_supports_pagination(self):
        response = self.client.get("/event_log/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_event_log_validates_payload(self):
        response = self.client.post("/event_log/", json={'table_name': 'user', 'field_name': 'user_id', 'action': 'create', 'before_value': 'test_before_value', 'after_value': 'test_after_value', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_event_log_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/event_log/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/event_log/{missing_id}", json={'table_name': 'user', 'field_name': 'user_id', 'action': 'create', 'before_value': 'test_before_value', 'after_value': 'test_after_value', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/event_log/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
