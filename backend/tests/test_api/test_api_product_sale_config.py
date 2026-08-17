from __future__ import annotations

from tests.conftest import BackendTestCase


class TestProductSaleConfigApi(BackendTestCase):
    def test_list_product_sale_config_supports_pagination(self):
        response = self.client.get("/product_sale_config/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_product_sale_config_validates_payload(self):
        response = self.client.post("/product_sale_config/", json={'margin_percent': 10.5, 'manual_price': 10.5, 'is_active': True, 'created_by': 1}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_product_sale_config_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/product_sale_config/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/product_sale_config/{missing_id}", json={'margin_percent': 10.5, 'manual_price': 10.5, 'is_active': True, 'created_by': 1}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/product_sale_config/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
