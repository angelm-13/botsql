from app.services.logistics_unit_service import LogisticsUnitService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestLogisticsUnitService(BackendTestCase):
    def unit_payload(self, overrides=None):
        return build_payload(LogisticsUnitService, {
            'plate': 'NKP-100',
            'unit_type': 'tractocamion',
            'mileage': '125000.50',
            'availability_status': 'disponible',
            'fuel_efficiency': '4.25',
            'status': 'activo',
            **(overrides or {}),
        })

    def test_creates_unit(self):
        unit = LogisticsUnitService.create(self.unit_payload())

        self.assertEqual('NKP-100', unit['plate'])
        self.assertEqual(125000.5, unit['mileage'])
        self.assertEqual('disponible', unit['availability_status'])

    def test_rejects_negative_mileage(self):
        with self.assertRaises(AppError) as raised:
            LogisticsUnitService.create(self.unit_payload({'mileage': '-0.01'}))
        self.assertEqual('validations.logistics_unit.mileage.invalid', raised.exception.message_key)

    def test_rejects_unknown_availability(self):
        with self.assertRaises(AppError) as raised:
            LogisticsUnitService.create(self.unit_payload({'availability_status': 'taller externo'}))
        self.assertEqual('validations.logistics_unit.availability_status.invalid', raised.exception.message_key)