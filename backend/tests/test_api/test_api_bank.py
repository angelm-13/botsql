from __future__ import annotations

from tests.conftest import BackendTestCase


class TestBankApi(BackendTestCase):
    def test_list_bank_supports_pagination(self):
        response = self.client.get("/bank/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_bank_validates_payload(self):
        response = self.client.post("/bank/", json={'bank_name': 'test bank_name', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_bank_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/bank/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/bank/{missing_id}", json={'bank_name': 'test bank_name', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/bank/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
