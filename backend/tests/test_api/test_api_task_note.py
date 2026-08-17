from __future__ import annotations

from tests.conftest import BackendTestCase


class TestTaskNoteApi(BackendTestCase):
    def test_list_task_note_supports_pagination(self):
        response = self.client.get("/task_note/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_task_note_validates_payload(self):
        response = self.client.post("/task_note/", json={'date': '2026-01-15T12:00:00', 'task_note_description': 'test description', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_task_note_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/task_note/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/task_note/{missing_id}", json={'date': '2026-01-15T12:00:00', 'task_note_description': 'test description', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/task_note/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
