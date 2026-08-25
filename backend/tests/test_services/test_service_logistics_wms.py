from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_inventory_service import LogisticsInventoryService
from app.services.logistics_location_service import LogisticsLocationService
from app.services.logistics_rack_service import LogisticsRackService
from app.services.logistics_warehouse_service import LogisticsWarehouseService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestLogisticsWmsServices(BackendTestCase):
    def create_warehouse(self):
        return LogisticsWarehouseService.create(build_payload(LogisticsWarehouseService, {
            'name': 'Almacén Norte', 'address': 'Parque Industrial', 'capacity': '1000', 'status': 'activo',
        }))

    def create_location(self):
        warehouse = self.create_warehouse()
        return LogisticsLocationService.create(build_payload(LogisticsLocationService, {
            'id_logistics_warehouse': warehouse['id_logistics_warehouse'], 'code': 'A-01-01',
            'zone': 'A', 'location_type': 'rack', 'capacity': '500', 'status': 'activo',
        }))

    def create_client(self, customer_type='client'):
        return CustomerSupplierService.create(build_payload(CustomerSupplierService, {
            'name': f'Cliente WMS {customer_type}', 'type': customer_type,
        }))

    def test_creates_warehouse_and_location(self):
        location = self.create_location()
        self.assertEqual('A-01-01', location['code'])
        self.assertEqual(500.0, location['capacity'])

    def test_rejects_negative_warehouse_capacity(self):
        with self.assertRaises(AppError) as raised:
            LogisticsWarehouseService.create(build_payload(LogisticsWarehouseService, {'name': 'Inválido', 'capacity': '-1'}))
        self.assertEqual('validations.logistics_warehouse.capacity.invalid', raised.exception.message_key)

    def test_rejects_unknown_location_warehouse(self):
        with self.assertRaises(AppError) as raised:
            LogisticsLocationService.create(build_payload(LogisticsLocationService, {
                'id_logistics_warehouse': 999999, 'code': 'X-01', 'capacity': '0',
            }))
        self.assertEqual('validations.logistics_location.warehouse.invalid', raised.exception.message_key)

    def test_rejects_negative_location_capacity(self):
        warehouse = self.create_warehouse()
        with self.assertRaises(AppError) as raised:
            LogisticsLocationService.create(build_payload(LogisticsLocationService, {
                'id_logistics_warehouse': warehouse['id_logistics_warehouse'], 'code': 'X-02', 'capacity': '-0.01',
            }))
        self.assertEqual('validations.logistics_location.capacity.invalid', raised.exception.message_key)

    def test_creates_inventory_for_client_and_location(self):
        client = self.create_client()
        location = self.create_location()
        inventory = LogisticsInventoryService.create(build_payload(LogisticsInventoryService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'id_logistics_location': location['id_logistics_location'],
            'sku': 'SKU-DEMO-001', 'quantity': '50.125', 'status': 'activo',
        }))
        self.assertEqual(50.125, inventory['quantity'])

    def test_rejects_supplier_as_inventory_client(self):
        supplier = self.create_client('supplier')
        location = self.create_location()
        with self.assertRaises(AppError) as raised:
            LogisticsInventoryService.create(build_payload(LogisticsInventoryService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'id_logistics_location': location['id_logistics_location'], 'sku': 'SKU-INVALID', 'quantity': '1',
            }))
        self.assertEqual('validations.logistics_inventory.client.invalid', raised.exception.message_key)

    def test_rejects_unknown_inventory_location(self):
        client = self.create_client()
        with self.assertRaises(AppError) as raised:
            LogisticsInventoryService.create(build_payload(LogisticsInventoryService, {
                'id_customer_supplier': client['id_customer_supplier'], 'id_logistics_location': 999999,
                'sku': 'SKU-NO-LOCATION', 'quantity': '1',
            }))
        self.assertEqual('validations.logistics_inventory.location.invalid', raised.exception.message_key)

    def test_rejects_negative_inventory_quantity(self):
        client = self.create_client()
        location = self.create_location()
        with self.assertRaises(AppError) as raised:
            LogisticsInventoryService.create(build_payload(LogisticsInventoryService, {
                'id_customer_supplier': client['id_customer_supplier'],
                'id_logistics_location': location['id_logistics_location'], 'sku': 'SKU-NEG', 'quantity': '-0.001',
            }))
        self.assertEqual('validations.logistics_inventory.quantity.invalid', raised.exception.message_key)

    def test_rejects_invalid_inventory_status(self):
        client = self.create_client()
        location = self.create_location()
        with self.assertRaises(AppError) as raised:
            LogisticsInventoryService.create(build_payload(LogisticsInventoryService, {
                'id_customer_supplier': client['id_customer_supplier'],
                'id_logistics_location': location['id_logistics_location'],
                'sku': 'SKU-STATUS', 'quantity': '1', 'status': 'reservado',
            }))
        self.assertEqual('validations.logistics_inventory.status.invalid', raised.exception.message_key)

    def test_creates_rack_for_client_and_location(self):
        client = self.create_client()
        location = self.create_location()
        rack = LogisticsRackService.create(build_payload(LogisticsRackService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'id_logistics_location': location['id_logistics_location'], 'code': 'RACK-DEMO-001',
            'status': 'pendiente_retorno', 'condition': 'bueno', 'quantity': 10,
        }))
        self.assertEqual(10, rack['quantity'])

    def test_rejects_unknown_rack_location(self):
        client = self.create_client()
        with self.assertRaises(AppError) as raised:
            LogisticsRackService.create(build_payload(LogisticsRackService, {
                'id_customer_supplier': client['id_customer_supplier'], 'id_logistics_location': 999999,
                'code': 'RACK-NO-LOCATION', 'quantity': 1,
            }))
        self.assertEqual('validations.logistics_rack.location.invalid', raised.exception.message_key)

    def test_rejects_supplier_as_rack_client(self):
        supplier = self.create_client('supplier')
        location = self.create_location()
        with self.assertRaises(AppError) as raised:
            LogisticsRackService.create(build_payload(LogisticsRackService, {
                'id_customer_supplier': supplier['id_customer_supplier'],
                'id_logistics_location': location['id_logistics_location'],
                'code': 'RACK-SUPPLIER', 'quantity': 1,
            }))
        self.assertEqual('validations.logistics_rack.client.invalid', raised.exception.message_key)

    def test_rejects_negative_rack_quantity(self):
        client = self.create_client()
        location = self.create_location()
        with self.assertRaises(AppError) as raised:
            LogisticsRackService.create(build_payload(LogisticsRackService, {
                'id_customer_supplier': client['id_customer_supplier'],
                'id_logistics_location': location['id_logistics_location'], 'code': 'RACK-NEG', 'quantity': -1,
            }))
        self.assertEqual('validations.logistics_rack.quantity.invalid', raised.exception.message_key)