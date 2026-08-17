from __future__ import annotations

from sqlalchemy import func, select

from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status
from app.models.session import transaction_context
from app.services.manual_invoice_service import create_manual_invoice
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


class TestManualInvoicePersistence(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=10, name='Emisor', tax_id='AAA010101AAA', postal_code='37000', type='supplier', id_user=1, created_by=1),
                CustomerSupplier(id_customer_supplier=20, name='Cliente', tax_id='BBB010101BBB', postal_code='37100', fiscal_type='601', type='client', id_user=1, created_by=1),
                Proyect(id_proyect=30, id_customer_supplier=20, leader=1, proyect_description='Proyecto cliente', created_by=1),
                Status(id_status=40, status_description='Activo', category='invoice', is_terminal=False, sort_order='asc', created_by=1),
            ])

    def payload(self):
        return {
            'id_proyect': 30,
            'id_customer_supplier': 20,
            'id_issuer_customer_supplier': 10,
            'id_status': 40,
            'date_emision': '2026-08-16',
            'date_expiration': '2026-08-31',
            'forma_pago': '03',
            'metodo_pago': 'PUE',
            'uso_cfdi': 'G03',
            'concepts': [{
                'description': 'Servicio manual',
                'quantity': 1,
                'unit_price': 100,
                'sat_product_key': '80101500',
                'sat_unit_key': 'E48',
            }],
        }

    def test_creates_invoice_and_lines_atomically(self):
        result = create_manual_invoice(self.payload(), {'id_user': 1, 'id_proyect': 30})

        self.assertTrue(result['invoice']['manual_capture'])
        self.assertEqual(result['invoice']['total'], 116.0)
        with transaction_context() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Invoice)), 1)
            line = db.scalars(select(InvoiceMaterialService)).one()
            self.assertEqual(line.sat_product_key, '80101500')
            self.assertEqual(line.authorization_status, 'authorized')

    def test_invalid_preview_does_not_persist_partial_rows(self):
        payload = self.payload()
        payload['concepts'][0].pop('sat_product_key')

        with self.assertRaises(AppError):
            create_manual_invoice(payload, {'id_user': 1, 'id_proyect': 30})

        with transaction_context() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Invoice)), 0)