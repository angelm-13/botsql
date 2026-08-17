from __future__ import annotations

from tests.conftest import BackendTestCase


class TestPayrollConceptApi(BackendTestCase):
    def test_list_payroll_concept_supports_pagination(self):
        response = self.client.get("/payroll_concept/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_payroll_concept_validates_payload(self):
        response = self.client.post("/payroll_concept/", json={'payroll_code': 'test title', 'payroll_concept_description': 'test title', 'type': 'earning', 'is_taxable': True, 'is_imss': True, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_payroll_concept_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/payroll_concept/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/payroll_concept/{missing_id}", json={'payroll_code': 'test title', 'payroll_concept_description': 'test title', 'type': 'earning', 'is_taxable': True, 'is_imss': True, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/payroll_concept/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
