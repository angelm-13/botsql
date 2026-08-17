from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.invoice_material_service import InvoiceMaterialService


class TestInvoiceMaterialServiceModel(BackendTestCase):
    def test_create_serialize_summary_delete_invoice_material_service(self):
        with transaction_context() as session:
            item = InvoiceMaterialService(
            invoice_material_service_description='test description',
            max_requirement_date='datetime.now()',
            is_directly_related_to_product_service_creation=True,
            gross_price=10.5,
            quantity=10.5,
            created_by=1,
            line_type='custom',
            tax_applicable=True,
            line_tax=10.5,
            line_total=10.5,
            authorization_status='pending',
            authorization_note='Pendiente de revision.',
            authorization_date='datetime.now()'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
