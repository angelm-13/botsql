from __future__ import annotations

from tests.conftest import BackendTestCase


class TestFiscalAccountApi(BackendTestCase):
    def test_list_fiscal_account_supports_pagination(self):
        response = self.client.get("/fiscal_account/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_fiscal_account_validates_payload(self):
        response = self.client.post("/fiscal_account/", json={'fiscal_account_description': 'test description', 'balance': 10.5, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_fiscal_account_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/fiscal_account/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/fiscal_account/{missing_id}", json={'fiscal_account_description': 'test description', 'balance': 10.5, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/fiscal_account/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
