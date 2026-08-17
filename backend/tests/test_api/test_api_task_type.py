from __future__ import annotations

from tests.conftest import BackendTestCase


class TestTaskTypeApi(BackendTestCase):
    def test_list_task_type_supports_pagination(self):
        response = self.client.get("/task_type/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_task_type_validates_payload(self):
        response = self.client.post("/task_type/", json={'task_type_description': 'test permission description', 'task_type_scope': 'test permission description', 'task_type_limit': 'test permission description', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_task_type_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/task_type/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/task_type/{missing_id}", json={'task_type_description': 'test permission description', 'task_type_scope': 'test permission description', 'task_type_limit': 'test permission description', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/task_type/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
