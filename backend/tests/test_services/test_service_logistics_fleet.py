from app.services.logistics_maintenance_service import LogisticsMaintenanceService
from app.services.logistics_operator_service import LogisticsOperatorService
from app.services.logistics_trailer_service import LogisticsTrailerService
from app.services.logistics_unit_service import LogisticsUnitService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestLogisticsFleetServices(BackendTestCase):
    def create_unit(self):
        return LogisticsUnitService.create(build_payload(LogisticsUnitService, {
            'plate': 'FLT-100', 'unit_type': 'tractocamion', 'mileage': '1000',
            'availability_status': 'disponible', 'status': 'activo',
        }))

    def test_creates_trailer(self):
        trailer = LogisticsTrailerService.create(build_payload(LogisticsTrailerService, {
            'plate': 'REM-200', 'trailer_type': 'caja seca', 'capacity': '25.5', 'status': 'activo',
        }))
        self.assertEqual(25.5, trailer['capacity'])

    def test_rejects_negative_trailer_capacity(self):
        with self.assertRaises(AppError) as raised:
            LogisticsTrailerService.create(build_payload(LogisticsTrailerService, {
                'plate': 'REM-201', 'trailer_type': 'plataforma', 'capacity': '-1', 'status': 'activo',
            }))
        self.assertEqual('validations.logistics_trailer.capacity.invalid', raised.exception.message_key)

    def test_creates_operator(self):
        operator = LogisticsOperatorService.create(build_payload(LogisticsOperatorService, {
            'full_name': 'Ana Operadora', 'license_number': 'LIC-100',
            'performance_score': '98.5', 'status': 'activo',
        }))
        self.assertEqual(98.5, operator['performance_score'])

    def test_rejects_negative_operator_performance(self):
        with self.assertRaises(AppError) as raised:
            LogisticsOperatorService.create(build_payload(LogisticsOperatorService, {
                'full_name': 'Operador Inválido', 'license_number': 'LIC-101',
                'performance_score': '-0.01', 'status': 'activo',
            }))
        self.assertEqual('validations.logistics_operator.performance_score.invalid', raised.exception.message_key)

    def test_creates_closed_maintenance_for_unit(self):
        unit = self.create_unit()
        maintenance = LogisticsMaintenanceService.create(build_payload(LogisticsMaintenanceService, {
            'id_logistics_unit': unit['id_logistics_unit'], 'maintenance_type': 'preventivo',
            'scheduled_at': '2026-08-20', 'closed_at': '2026-08-21',
            'cost': '8500', 'status': 'cerrada', 'description': 'Servicio mayor',
        }))
        self.assertEqual(unit['id_logistics_unit'], maintenance['id_logistics_unit'])
        self.assertEqual('cerrada', maintenance['status'])

    def test_rejects_unknown_maintenance_unit(self):
        with self.assertRaises(AppError) as raised:
            LogisticsMaintenanceService.create(build_payload(LogisticsMaintenanceService, {
                'id_logistics_unit': 999999, 'maintenance_type': 'preventivo',
                'cost': '0', 'status': 'abierta',
            }))
        self.assertEqual('validations.logistics_maintenance.unit.invalid', raised.exception.message_key)

    def test_rejects_negative_maintenance_cost(self):
        unit = self.create_unit()
        with self.assertRaises(AppError) as raised:
            LogisticsMaintenanceService.create(build_payload(LogisticsMaintenanceService, {
                'id_logistics_unit': unit['id_logistics_unit'], 'maintenance_type': 'correctivo',
                'cost': '-0.01', 'status': 'abierta',
            }))
        self.assertEqual('validations.logistics_maintenance.cost.invalid', raised.exception.message_key)

    def test_rejects_closed_maintenance_without_closed_date(self):
        unit = self.create_unit()
        payload = build_payload(LogisticsMaintenanceService, {
            'id_logistics_unit': unit['id_logistics_unit'], 'maintenance_type': 'preventivo',
            'scheduled_at': '2026-08-20', 'cost': '0', 'status': 'cerrada',
        })
        payload['closed_at'] = ''
        with self.assertRaises(AppError) as raised:
            LogisticsMaintenanceService.create(payload)
        self.assertEqual('validations.logistics_maintenance.closed_at.required', raised.exception.message_key)

    def test_rejects_closed_date_before_schedule(self):
        unit = self.create_unit()
        with self.assertRaises(AppError) as raised:
            LogisticsMaintenanceService.create(build_payload(LogisticsMaintenanceService, {
                'id_logistics_unit': unit['id_logistics_unit'], 'maintenance_type': 'preventivo',
                'scheduled_at': '2026-08-20', 'closed_at': '2026-08-19', 'cost': '0', 'status': 'cerrada',
            }))
        self.assertEqual('validations.logistics_maintenance.closed_at.invalid', raised.exception.message_key)