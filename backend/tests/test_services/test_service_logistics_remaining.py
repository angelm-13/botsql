from app.services.customer_supplier_service import CustomerSupplierService
from app.services.invoice_service import InvoiceService
from app.services.logistics_workflow_service import (
    LogisticsBranchService,
    LogisticsFileService,
    LogisticsReceivableService,
    LogisticsShipmentService,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestRemainingLogisticsServices(BackendTestCase):
    def create_client(self, name='Cliente Entidades'):
        return CustomerSupplierService.create(build_payload(CustomerSupplierService, {'name': name, 'type': 'client'}))

    def create_invoice(self, client):
        return InvoiceService.create(build_payload(InvoiceService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'id_issuer_customer_supplier': client['id_customer_supplier'],
            'internationalization': 'local',
            'tax_certification_supplier': client['id_customer_supplier'],
            'id_status': 1,
            'apply_tax': False,
            'folio': f"FAC-{client['id_customer_supplier']}",
        }))

    def test_creates_shipment_branch_receivable_and_file(self):
        client = self.create_client()
        invoice = self.create_invoice(client)
        branch = LogisticsBranchService.create(build_payload(LogisticsBranchService, {
            'name': 'Sucursal Bajío', 'postal_code': '37000', 'series': 'BJ', 'status': 'activo',
        }))
        shipment = LogisticsShipmentService.create(build_payload(LogisticsShipmentService, {
            'id_customer_supplier': client['id_customer_supplier'], 'shipment_number': 'EMB-0001',
            'bl_number': 'BL-9001', 'transport_mode': 'marítimo', 'origin_port': 'Manzanillo',
            'destination_port': 'Yokohama', 'status': 'en tránsito',
        }))
        receivable = LogisticsReceivableService.create(build_payload(LogisticsReceivableService, {
            'id_invoice': invoice['id_invoice'], 'id_customer_supplier': client['id_customer_supplier'],
            'amount': '12500.50', 'due_at': '2026-09-30', 'status': 'pendiente',
        }))
        logistics_file = LogisticsFileService.create(build_payload(LogisticsFileService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'id_logistics_branch': branch['id_logistics_branch'], 'id_invoice': invoice['id_invoice'],
            'folio': 'EXP-0001', 'origin': 'León', 'destination': 'Monterrey',
            'payment_form': '99', 'payment_method': 'PUE', 'cfdi_use': 'G03', 'status': 'abierto',
        }))

        self.assertEqual(client['id_customer_supplier'], shipment['id_customer_supplier'])
        self.assertEqual(invoice['id_invoice'], receivable['id_invoice'])
        self.assertEqual(branch['id_logistics_branch'], logistics_file['id_logistics_branch'])

    def test_rejects_invalid_constraints(self):
        client = self.create_client()
        invoice = self.create_invoice(client)
        other_client = self.create_client('Cliente Diferente')

        with self.assertRaises(AppError) as invalid_fk:
            LogisticsShipmentService.create(build_payload(LogisticsShipmentService, {
                'id_customer_supplier': 999999, 'shipment_number': 'EMB-BAD-FK',
            }))
        self.assertEqual('validations.logistics_shipment.client.invalid', invalid_fk.exception.message_key)

        with self.assertRaises(AppError) as negative_amount:
            LogisticsReceivableService.create(build_payload(LogisticsReceivableService, {
                'id_invoice': invoice['id_invoice'], 'id_customer_supplier': client['id_customer_supplier'],
                'amount': '-0.01', 'due_at': '2026-09-30',
            }))
        self.assertEqual('validations.logistics_receivable.amount.invalid', negative_amount.exception.message_key)

        with self.assertRaises(AppError) as mismatched_invoice:
            LogisticsFileService.create(build_payload(LogisticsFileService, {
                'id_customer_supplier': other_client['id_customer_supplier'], 'id_invoice': invoice['id_invoice'],
                'folio': 'EXP-BAD-INVOICE', 'origin': 'León', 'destination': 'Monterrey',
            }))
        self.assertEqual('validations.logistics_file.id_invoice.invalid', mismatched_invoice.exception.message_key)

        with self.assertRaises(AppError) as invalid_status:
            LogisticsBranchService.create(build_payload(LogisticsBranchService, {
                'name': 'Sucursal inválida', 'status': 'cerrada',
            }))
        self.assertEqual('validations.logistics_branch.status.invalid', invalid_status.exception.message_key)