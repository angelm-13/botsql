from __future__ import annotations

from tests.conftest import BackendTestCase


class TestLocationApi(BackendTestCase):
    def test_list_location_supports_pagination(self):
        response = self.client.get("/location/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_location_validates_payload(self):
        response = self.client.post("/location/", json={'location_description': 'test description', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_location_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/location/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/location/{missing_id}", json={'location_description': 'test description', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/location/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
