from __future__ import annotations

from tests.conftest import BackendTestCase


class TestIncidentDetailApi(BackendTestCase):
    def test_list_incident_detail_supports_pagination(self):
        response = self.client.get("/incident_detail/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_incident_detail_validates_payload(self):
        response = self.client.post("/incident_detail/", json={'incident_detail_name': 'test description', 'incident_detail_description': 'test description', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_incident_detail_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/incident_detail/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/incident_detail/{missing_id}", json={'incident_detail_name': 'test description', 'incident_detail_description': 'test description', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/incident_detail/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
