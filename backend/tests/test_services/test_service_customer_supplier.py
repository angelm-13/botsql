from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.customer_supplier_service import CustomerSupplierService


class TestCustomerSupplierService(BackendTestCase):
    def test_crud_service_customer_supplier(self):
        created = CustomerSupplierService.create({'postal_code': '00000', 'name': 'test razon_social', 'title': 'test title', 'contact_name': 'test contact_name', 'phone': 'test phone', 'email': 'contacto@example.com', 'web_site': 'test web_site', 'street': 'test street', 'number_ext': '1', 'number_int': '1', 'neighborhood': 'test neighborhood', 'city': 'test city', 'geographic_state': 'test state', 'fiscal_type': 'test fiscal_type', 'last_fiscal_certification_date': 'datetime.now()', 'tax_id': 'test tax_id', 'type': 'client', 'created_by': 1, 'path_logo': 'uploads/customer_suppliers/logos/logo.png'})
        self.assertIsNotNone(created)
        page = CustomerSupplierService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
