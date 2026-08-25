from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_contract_service import LogisticsContractService
from app.utils.errors import AppError


class TestLogisticsContractService(BackendTestCase):
    def test_creates_contract_for_client(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Contratos', 'type': 'client',
        }))
        contract = LogisticsContractService.create(build_payload(LogisticsContractService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'contract_number': 'CTR-2026-001',
            'start_date': '2026-08-01',
            'end_date': '2027-07-31',
        }))

        self.assertEqual(client['id_customer_supplier'], contract['id_customer_supplier'])
        self.assertEqual('CTR-2026-001', contract['contract_number'])

    def test_rejects_end_date_before_start_date(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Fechas', 'type': 'client',
        }))
        with self.assertRaises(AppError) as raised:
            LogisticsContractService.create(build_payload(LogisticsContractService, {
                'id_customer_supplier': client['id_customer_supplier'],
                'contract_number': 'CTR-INVALID',
                'start_date': '2026-08-02',
                'end_date': '2026-08-01',
            }))
        self.assertEqual('validations.logistics_contract.end_date.invalid', raised.exception.message_key)

    def test_rejects_supplier_as_contract_client(self):
        supplier = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Proveedor Contratos', 'type': 'supplier',
        }))
        with self.assertRaises(AppError) as raised:
            LogisticsContractService.create(build_payload(LogisticsContractService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'contract_number': 'CTR-SUPPLIER',
                'start_date': '2026-08-01',
            }))
        self.assertEqual('validations.logistics_contract.client.invalid', raised.exception.message_key)