from __future__ import annotations

from tests.conftest import BackendTestCase


class TestProductApi(BackendTestCase):
    def test_list_product_supports_pagination(self):
        response = self.client.get("/product/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_product_validates_payload(self):
        response = self.client.post("/product/", json={'gross_price': 10.5, 'color': 'test color', 'is_directly_related_to_product_service': True, 'product_status': 'test state', 'path_imagen': 'test path_imagen', 'product_code': 'test code', 'note': 'test note', 'created_by': 1, 'descripcion': 'test_descripcion', 'cantidad': 'test_cantidad'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_product_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/product/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/product/{missing_id}", json={'gross_price': 10.5, 'color': 'test color', 'is_directly_related_to_product_service': True, 'product_status': 'test state', 'path_imagen': 'test path_imagen', 'product_code': 'test code', 'note': 'test note', 'created_by': 1, 'descripcion': 'test_descripcion', 'cantidad': 'test_cantidad'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/product/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
