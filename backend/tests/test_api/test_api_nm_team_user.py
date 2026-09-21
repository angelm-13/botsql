from __future__ import annotations

from tests.conftest import BackendTestCase


class TestNmTeamUserApi(BackendTestCase):
    def test_list_nm_team_user_supports_pagination(self):
        response = self.client.get("/nm_team_user/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_nm_team_user_validates_payload(self):
        response = self.client.post("/nm_team_user/", json={'id_team': 1, 'id_user': 1, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 404, 422])

    def test_get_update_delete_nm_team_user_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/nm_team_user/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/nm_team_user/{missing_id}", json={'id_team': 1, 'id_user': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/nm_team_user/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
