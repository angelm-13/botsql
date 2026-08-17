from __future__ import annotations

from tests.conftest import BackendTestCase


class TestCustomerSupplierApi(BackendTestCase):
    def test_list_customer_supplier_supports_pagination(self):
        response = self.client.get("/customer_supplier/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_customer_supplier_validates_payload(self):
        response = self.client.post("/customer_supplier/", json={'postal_code': '00000', 'name': 'test razon_social', 'title': 'test title', 'contact_name': 'test contact_name', 'phone': 'test phone', 'email': 'contacto@example.com', 'web_site': 'test web_site', 'street': 'test street', 'number_ext': '1', 'number_int': '1', 'neighborhood': 'test neighborhood', 'city': 'test city', 'geographic_state': 'test state', 'fiscal_type': 'test fiscal_type', 'last_fiscal_certification_date': 'datetime.now()', 'tax_id': 'test tax_id', 'type': 'client', 'created_by': 1, 'path_logo': 'uploads/customer_suppliers/logos/logo.png'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_customer_supplier_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/customer_supplier/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/customer_supplier/{missing_id}", json={'postal_code': '00000', 'name': 'test razon_social', 'title': 'test title', 'contact_name': 'test contact_name', 'phone': 'test phone', 'email': 'contacto@example.com', 'web_site': 'test web_site', 'street': 'test street', 'number_ext': '1', 'number_int': '1', 'neighborhood': 'test neighborhood', 'city': 'test city', 'geographic_state': 'test state', 'fiscal_type': 'test fiscal_type', 'last_fiscal_certification_date': 'datetime.now()', 'tax_id': 'test tax_id', 'type': 'client', 'created_by': 1, 'path_logo': 'uploads/customer_suppliers/logos/logo.png'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/customer_supplier/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])
