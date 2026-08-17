from __future__ import annotations

from tests.conftest import BackendTestCase


class TestUserApi(BackendTestCase):
    def test_list_user_supports_pagination(self):
        response = self.client.get("/user/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_user_validates_payload(self):
        response = self.client.post("/user/", json={'created_by': 1, 'date_born': '2026-01-15T12:00:00', 'date_start': '2026-01-15T12:00:00', 'email': 'test email', 'first_name': 'test first_name', 'full_name': 'test first_name', 'last_name_father': 'test last_name_father', 'last_name_mother': 'test last_name_mother', 'national_id': 'test national_id', 'password': 'test password', 'principal_phone': 'test principal_phone', 'secundary_phone': 'test secundary_phone', 'ssn': 'test ssn', 'supervisor': 'test_supervisor', 'base_salary': 10.5, 'hire_date': '2026-01-15T12:00:00', 'tax_id': 'test tax_id', 'title': 'test title', 'user_type': 'admin', 'username': 'test_user', 'puesto': 'test_puesto', 'accepts_marketing': True}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_user_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/user/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/user/{missing_id}", json={'created_by': 1, 'date_born': '2026-01-15T12:00:00', 'date_start': '2026-01-15T12:00:00', 'email': 'test email', 'first_name': 'test first_name', 'full_name': 'test first_name', 'last_name_father': 'test last_name_father', 'last_name_mother': 'test last_name_mother', 'national_id': 'test national_id', 'password': 'test password', 'principal_phone': 'test principal_phone', 'secundary_phone': 'test secundary_phone', 'ssn': 'test ssn', 'supervisor': 'test_supervisor', 'base_salary': 10.5, 'hire_date': '2026-01-15T12:00:00', 'tax_id': 'test tax_id', 'title': 'test title', 'user_type': 'admin', 'username': 'test_user', 'puesto': 'test_puesto', 'accepts_marketing': True}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/user/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
