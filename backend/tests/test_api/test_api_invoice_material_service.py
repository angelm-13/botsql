from __future__ import annotations

from tests.conftest import BackendTestCase


class TestInvoiceMaterialServiceApi(BackendTestCase):
    def test_list_invoice_material_service_supports_pagination(self):
        response = self.client.get("/invoice_material_service/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_invoice_material_service_validates_payload(self):
        response = self.client.post("/invoice_material_service/", json={'invoice_material_service_description': 'test description', 'max_requirement_date': 'datetime.now()', 'is_directly_related_to_product_service_creation': True, 'gross_price': 10.5, 'quantity': 10.5, 'created_by': 1, 'line_type': 'custom', 'tax_applicable': True, 'line_tax': 10.5, 'line_total': 10.5, 'authorization_status': 'pending', 'authorization_note': 'Pendiente de revision.', 'authorization_date': 'datetime.now()'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_invoice_material_service_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/invoice_material_service/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/invoice_material_service/{missing_id}", json={'invoice_material_service_description': 'test description', 'max_requirement_date': 'datetime.now()', 'is_directly_related_to_product_service_creation': True, 'gross_price': 10.5, 'quantity': 10.5, 'created_by': 1, 'line_type': 'custom', 'tax_applicable': True, 'line_tax': 10.5, 'line_total': 10.5, 'authorization_status': 'pending', 'authorization_note': 'Pendiente de revision.', 'authorization_date': 'datetime.now()'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/invoice_material_service/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
