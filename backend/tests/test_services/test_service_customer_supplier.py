from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_supplier_service import CustomerSupplierService
from app.utils.errors import AppError


class TestCustomerSupplierService(BackendTestCase):
    def test_crud_service_customer_supplier(self):
        created = CustomerSupplierService.create(build_payload(CustomerSupplierService, {'postal_code': '00000', 'name': 'test razon_social', 'title': 'test title', 'contact_name': 'test contact_name', 'phone': '5551234567', 'email': 'contacto@example.com', 'web_site': 'test web_site', 'street': 'test street', 'number_ext': '1', 'number_int': '1', 'neighborhood': 'test neighborhood', 'city': 'test city', 'geographic_state': 'test state', 'fiscal_type': 'test fiscal_type', 'last_fiscal_certification_date': '2026-01-15T12:00:00', 'tax_id': 'AAA010101AAA', 'type': 'client', 'created_by': 1, 'path_logo': 'uploads/customer_suppliers/logos/logo.png'}))
        self.assertIsNotNone(created)
        page = CustomerSupplierService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def test_setting_principal_clears_previous_company(self):
        first = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Empresa Uno', 'tax_id': 'AAA010101AAA', 'type': 'client', 'is_principal': True,
        }))
        second = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Empresa Dos', 'tax_id': 'BBB010101BBB', 'type': 'client', 'is_principal': True,
        }))

        page = CustomerSupplierService.list(page=1, per_page=10, filters={}, sort=None)
        principals = [item for item in page['items'] if item['is_principal']]
        self.assertEqual([second['id_customer_supplier']], [item['id_customer_supplier'] for item in principals])
        self.assertNotEqual(first['id_customer_supplier'], second['id_customer_supplier'])

    def test_principal_company_requires_tax_id(self):
        payload = build_payload(CustomerSupplierService, {
            'name': 'Empresa sin RFC', 'tax_id': '', 'type': 'client', 'is_principal': True,
        })
        with self.assertRaises(AppError) as raised:
            CustomerSupplierService.create(payload)
        self.assertEqual('validations.customer_supplier.principal_tax_id.required', raised.exception.message_key)
