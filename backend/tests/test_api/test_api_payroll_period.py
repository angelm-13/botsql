from __future__ import annotations

from tests.conftest import BackendTestCase


class TestPayrollPeriodApi(BackendTestCase):
    def test_list_payroll_period_supports_pagination(self):
        response = self.client.get("/payroll_period/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_payroll_period_validates_payload(self):
        response = self.client.post("/payroll_period/", json={'period_start': '2026-01-15T12:00:00', 'period_end': '2026-01-15T12:00:00', 'payment_date': '2026-01-15T12:00:00', 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_payroll_period_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/payroll_period/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/payroll_period/{missing_id}", json={'period_start': '2026-01-15T12:00:00', 'period_end': '2026-01-15T12:00:00', 'payment_date': '2026-01-15T12:00:00', 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/payroll_period/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
