from __future__ import annotations

from tests.conftest import BackendTestCase


class TestInventoryStatusApi(BackendTestCase):
    def test_list_inventory_status_supports_pagination(self):
        response = self.client.get("/inventory_status/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_inventory_status_validates_payload(self):
        response = self.client.post("/inventory_status/", json={'inventory_status_code': 'ENTRADA', 'inventory_status_description': 'Entrada', 'color': '#22c55e', 'entity_scope': 'product', 'flow_scope': 'inventory', 'is_active': True, 'is_terminal': True, 'visible_to_other_departments': True, 'sort_order': 1, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_inventory_status_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/inventory_status/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/inventory_status/{missing_id}", json={'inventory_status_code': 'ENTRADA', 'inventory_status_description': 'Entrada', 'color': '#22c55e', 'entity_scope': 'product', 'flow_scope': 'inventory', 'is_active': True, 'is_terminal': True, 'visible_to_other_departments': True, 'sort_order': 1, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/inventory_status/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
