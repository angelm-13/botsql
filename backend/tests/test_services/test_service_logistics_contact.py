from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_contact_service import LogisticsContactService
from app.utils.errors import AppError


class TestLogisticsContactService(BackendTestCase):
    def test_creates_contact_for_client(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Contactos', 'type': 'client',
        }))
        contact = LogisticsContactService.create(build_payload(LogisticsContactService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'full_name': 'Ana Operaciones',
            'email': 'ana@example.com',
            'status': 'activo',
        }))

        self.assertEqual(client['id_customer_supplier'], contact['id_customer_supplier'])
        self.assertEqual('Ana Operaciones', contact['full_name'])

    def test_rejects_supplier_as_contact_client(self):
        supplier = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Proveedor', 'type': 'supplier',
        }))
        with self.assertRaises(AppError) as raised:
            LogisticsContactService.create(build_payload(LogisticsContactService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'full_name': 'Contacto inválido',
            }))
        self.assertEqual('validations.logistics_contact.client.invalid', raised.exception.message_key)