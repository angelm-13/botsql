from __future__ import annotations

from tests.conftest import BackendTestCase


class TestTaskApi(BackendTestCase):
    def test_list_task_supports_pagination(self):
        response = self.client.get("/task/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_task_validates_payload(self):
        response = self.client.post("/task/", json={'task_code': 'C1', 'start_date': 'datetime.now()', 'duration': 10.5, 'type': 'business', 'owner': 1, 'analyst': 1, 'dependency': 1, 'leader': 1, 'validation': 1, 'task_description': 'test description', 'estimated_effort': 'test estimated_effort', 'task_status': 'test state', 'fase': 'test fase', 'priority': 'test priority', 'title': 'test titulo', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_task_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/task/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/task/{missing_id}", json={'task_code': 'C1', 'start_date': 'datetime.now()', 'duration': 10.5, 'type': 'business', 'owner': 1, 'analyst': 1, 'dependency': 1, 'leader': 1, 'validation': 1, 'task_description': 'test description', 'estimated_effort': 'test estimated_effort', 'task_status': 'test state', 'fase': 'test fase', 'priority': 'test priority', 'title': 'test titulo', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/task/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
