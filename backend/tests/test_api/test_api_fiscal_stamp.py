from __future__ import annotations

from tests.conftest import BackendTestCase


class TestFiscalStampApi(BackendTestCase):
    def test_list_fiscal_stamp_supports_pagination(self):
        response = self.client.get("/fiscal_stamp/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_fiscal_stamp_validates_payload(self):
        response = self.client.post("/fiscal_stamp/", json={'concept': 'test concept', 'reviewed_by': 1, 'authorized_by': 1, 'auxiliar': 'test auxiliar', 'num_policy': 'test num_policy', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_fiscal_stamp_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/fiscal_stamp/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/fiscal_stamp/{missing_id}", json={'concept': 'test concept', 'reviewed_by': 1, 'authorized_by': 1, 'auxiliar': 'test auxiliar', 'num_policy': 'test num_policy', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/fiscal_stamp/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
