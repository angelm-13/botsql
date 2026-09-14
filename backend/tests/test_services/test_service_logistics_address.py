from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_address_service import LogisticsAddressService
from app.utils.errors import AppError


class TestLogisticsAddressService(BackendTestCase):
    def test_creates_address_for_client(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Direcciones', 'type': 'client',
        }))
        address = LogisticsAddressService.create(build_payload(LogisticsAddressService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'name': 'Planta Norte',
            'address_line': 'Av. Industria 100',
        }))

        self.assertEqual(client['id_customer_supplier'], address['id_customer_supplier'])
        self.assertEqual('Planta Norte', address['name'])

    def test_rejects_supplier_as_address_client(self):
        supplier = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Proveedor Direcciones', 'type': 'supplier',
        }))
        with self.assertRaises(AppError) as raised:
            LogisticsAddressService.create(build_payload(LogisticsAddressService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'name': 'Dirección inválida',
                'address_line': 'Calle 1',
            }))
        self.assertEqual('validations.logistics_address.client.invalid', raised.exception.message_key)