from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_contact_service import CustomerContactService
from app.services.customer_supplier_service import CustomerSupplierService
from app.utils.errors import AppError


class TestCustomerContactService(BackendTestCase):
    def test_creates_contact_for_client(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Contactos', 'type': 'client',
        }))
        contact = CustomerContactService.create(build_payload(CustomerContactService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'full_name': 'Ana Operaciones',
            'email': 'ana@example.com',
            'status': 'activo',
        }))

        self.assertEqual(client['id_customer_supplier'], contact['id_customer_supplier'])
        self.assertEqual('Ana Operaciones', contact['full_name'])

    def test_rejects_supplier_as_contact_customer(self):
        supplier = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Proveedor', 'type': 'supplier',
        }))
        with self.assertRaises(AppError) as raised:
            CustomerContactService.create(build_payload(CustomerContactService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'full_name': 'Contacto inválido',
            }))
        self.assertEqual('validations.customer_contact.customer.invalid', raised.exception.message_key)

    def test_options_builds_the_company_dash_contact_label(self):
        client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Constructora ABC', 'type': 'client',
        }))
        CustomerContactService.create(build_payload(CustomerContactService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'full_name': 'Ing. Juan Pérez',
            'status': 'activo',
        }))
        # Un contacto inactivo no debe ofrecerse en el selector del proyecto.
        CustomerContactService.create(build_payload(CustomerContactService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'full_name': 'Contacto dado de baja',
            'status': 'inactivo',
        }))

        opciones = CustomerContactService.options()

        self.assertEqual(1, len(opciones))
        self.assertEqual('Constructora ABC — Ing. Juan Pérez', opciones[0]['label'])
