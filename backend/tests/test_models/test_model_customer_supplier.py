from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.customer_supplier import CustomerSupplier


class TestCustomerSupplierModel(BackendTestCase):
    def test_create_serialize_summary_delete_customer_supplier(self):
        with transaction_context() as session:
            item = build_model(CustomerSupplier,
            postal_code='00000',
            name='test razon_social',
            title='test title',
            contact_name='test contact_name',
            phone='test phone',
            email='contacto@example.com',
            web_site='test web_site',
            street='test street',
            number_ext='1',
            number_int='1',
            neighborhood='test neighborhood',
            city='test city',
            geographic_state='test state',
            fiscal_type='test fiscal_type',
            last_fiscal_certification_date='2026-01-15T12:00:00',
            tax_id='test tax_id',
            type='client',
            created_by=1,
            path_logo='uploads/customer_suppliers/logos/logo.png'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
