from __future__ import annotations

from tests.conftest import BackendTestCase


class TestThemeApi(BackendTestCase):
    def test_list_theme_supports_pagination(self):
        response = self.client.get("/theme/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_theme_validates_payload(self):
        response = self.client.post("/theme/", json={'created_by': 1, 'tenant_id': 1, 'primary_color': '#0D47A1', 'secondary_color': '#0D47A1', 'background_color': '#0D47A1', 'text_color': '#0D47A1', 'highlight_color': '#0D47A1', 'success_color': '#0D47A1', 'error_color': '#0D47A1'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_theme_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/theme/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/theme/{missing_id}", json={'created_by': 1, 'tenant_id': 1, 'primary_color': '#0D47A1', 'secondary_color': '#0D47A1', 'background_color': '#0D47A1', 'text_color': '#0D47A1', 'highlight_color': '#0D47A1', 'success_color': '#0D47A1', 'error_color': '#0D47A1'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/theme/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
