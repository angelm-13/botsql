from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_rate_service import LogisticsRateService
from app.utils.errors import AppError


class TestLogisticsRateService(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.client = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Cliente Tarifas', 'type': 'client',
        }))

    def rate_payload(self, overrides=None):
        return build_payload(LogisticsRateService, {
            'id_customer_supplier': self.client['id_customer_supplier'],
            'service_type': 'transporte',
            'origin': 'Monterrey',
            'destination': 'Querétaro',
            'amount': '12500.50',
            'currency': 'MXN',
            **(overrides or {}),
        })

    def test_creates_rate_for_client(self):
        rate = LogisticsRateService.create(self.rate_payload())

        self.assertEqual(self.client['id_customer_supplier'], rate['id_customer_supplier'])
        self.assertEqual(12500.5, rate['amount'])
        self.assertEqual('MXN', rate['currency'])

    def test_rejects_negative_amount(self):
        with self.assertRaises(AppError) as raised:
            LogisticsRateService.create(self.rate_payload({'amount': '-0.01'}))
        self.assertEqual('validations.logistics_rate.amount.invalid', raised.exception.message_key)

    def test_rejects_unsupported_currency(self):
        with self.assertRaises(AppError) as raised:
            LogisticsRateService.create(self.rate_payload({'currency': 'EUR'}))
        self.assertEqual('validations.logistics_rate.currency.invalid', raised.exception.message_key)

    def test_rejects_supplier_as_rate_client(self):
        supplier = CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': 'Proveedor Tarifas', 'type': 'supplier',
        }))
        with self.assertRaises(AppError) as raised:
            LogisticsRateService.create(self.rate_payload({'id_customer_supplier': supplier['id_customer_supplier']}))
        self.assertEqual('validations.logistics_rate.client.invalid', raised.exception.message_key)