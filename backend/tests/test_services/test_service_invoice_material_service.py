from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.invoice_material_service_service import InvoiceMaterialServiceService


class TestInvoiceMaterialServiceService(BackendTestCase):
    def test_crud_service_invoice_material_service(self):
        created = InvoiceMaterialServiceService.create({'invoice_material_service_description': 'test description', 'max_requirement_date': 'datetime.now()', 'is_directly_related_to_product_service_creation': True, 'gross_price': 10.5, 'quantity': 10.5, 'created_by': 1, 'line_type': 'custom', 'tax_applicable': True, 'line_tax': 10.5, 'line_total': 10.5, 'authorization_status': 'pending', 'authorization_note': 'Pendiente de revision.', 'authorization_date': 'datetime.now()'})
        self.assertIsNotNone(created)
        page = InvoiceMaterialServiceService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
