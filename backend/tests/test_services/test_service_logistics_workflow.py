from app.services.customer_supplier_service import CustomerSupplierService
from app.services.logistics_operator_service import LogisticsOperatorService
from app.services.logistics_trailer_service import LogisticsTrailerService
from app.services.logistics_unit_service import LogisticsUnitService
from app.services.logistics_workflow_service import (
    LogisticsEvidenceService,
    LogisticsIncidentService,
    LogisticsQuotationService,
    LogisticsServiceRequestService,
    LogisticsTripService,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestLogisticsWorkflowServices(BackendTestCase):
    def create_client(self, name='Cliente Flujo'):
        return CustomerSupplierService.create(build_payload(CustomerSupplierService, {'name': name, 'type': 'client'}))

    def create_chain(self):
        client = self.create_client()
        quotation = LogisticsQuotationService.create(build_payload(LogisticsQuotationService, {
            'id_customer_supplier': client['id_customer_supplier'], 'folio': 'COT-0001',
            'service_type': 'carga completa', 'origin': 'León', 'destination': 'Monterrey',
            'kilometers': '710.50', 'maneuvers': '1200', 'storage': '0',
            'additional_services': {'custodia': 1500}, 'total': '12700', 'status': 'aceptada',
        }))
        service_request = LogisticsServiceRequestService.create(build_payload(LogisticsServiceRequestService, {
            'id_customer_supplier': client['id_customer_supplier'],
            'id_logistics_quotation': quotation['id_logistics_quotation'], 'request_number': 'SOL-0001',
            'request_type': 'carga completa', 'origin': 'León', 'destination': 'Monterrey',
            'requested_pickup_at': '2026-08-23T08:00:00', 'requested_delivery_at': '2026-08-24T18:00:00',
            'status': 'aprobado', 'priority': 'alta',
        }))
        unit = LogisticsUnitService.create(build_payload(LogisticsUnitService, {
            'plate': 'TYX-101', 'unit_type': 'tractocamión', 'status': 'activo',
        }))
        trailer = LogisticsTrailerService.create(build_payload(LogisticsTrailerService, {
            'plate': 'TYX-R01', 'trailer_type': 'caja seca', 'capacity': '25', 'status': 'activo',
        }))
        operator = LogisticsOperatorService.create(build_payload(LogisticsOperatorService, {
            'full_name': 'Operador Demo', 'license_number': 'LIC-TYX-01', 'status': 'activo',
        }))
        trip = LogisticsTripService.create(build_payload(LogisticsTripService, {
            'id_logistics_service_request': service_request['id_logistics_service_request'],
            'id_customer_supplier': client['id_customer_supplier'], 'folio': 'VIA-0001',
            'id_logistics_unit': unit['id_logistics_unit'],
            'id_logistics_trailer': trailer['id_logistics_trailer'],
            'id_logistics_operator': operator['id_logistics_operator'],
            'status': 'asignado', 'planned_pickup_at': '2026-08-23T08:00:00',
            'planned_delivery_at': '2026-08-24T18:00:00', 'planned_cost': '8500',
            'actual_cost': '0', 'revenue': '12700', 'kilometers': '710.50',
        }))
        return client, quotation, service_request, trip

    def test_creates_quotation_request_trip_evidence_and_incident(self):
        _, quotation, service_request, trip = self.create_chain()
        evidence = LogisticsEvidenceService.create(build_payload(LogisticsEvidenceService, {
            'id_logistics_trip': trip['id_logistics_trip'], 'evidence_type': 'recoleccion',
            'latitude': '21.1221000', 'longitude': '-101.6821000', 'comments': 'Carga completa',
        }))
        incident = LogisticsIncidentService.create(build_payload(LogisticsIncidentService, {
            'id_logistics_trip': trip['id_logistics_trip'], 'incident_type': 'demora',
            'severity': 'media', 'description': 'Tráfico en carretera', 'status': 'abierta',
        }))
        self.assertEqual({'custodia': 1500}, quotation['additional_services'])
        self.assertEqual(quotation['id_logistics_quotation'], service_request['id_logistics_quotation'])
        self.assertEqual(trip['id_logistics_trip'], evidence['id_logistics_trip'])
        self.assertEqual(trip['id_logistics_trip'], incident['id_logistics_trip'])

    def test_rejects_invalid_foreign_keys(self):
        client = self.create_client()
        with self.assertRaises(AppError) as raised:
            LogisticsServiceRequestService.create(build_payload(LogisticsServiceRequestService, {
                'id_customer_supplier': client['id_customer_supplier'], 'id_logistics_quotation': 999999,
                'request_number': 'SOL-BAD-FK', 'request_type': 'carga',
            }))
        self.assertEqual('validations.logistics_service_request.quotation.invalid', raised.exception.message_key)

    def test_rejects_negative_cost_and_invalid_status(self):
        client, _, service_request, trip = self.create_chain()
        with self.assertRaises(AppError) as negative:
            LogisticsTripService.create(build_payload(LogisticsTripService, {
                'id_logistics_service_request': service_request['id_logistics_service_request'],
                'id_customer_supplier': client['id_customer_supplier'], 'folio': 'VIA-NEG',
                'planned_cost': '-0.01',
            }))
        self.assertEqual('validations.logistics_trip.planned_cost.invalid', negative.exception.message_key)
        with self.assertRaises(AppError) as invalid_status:
            LogisticsIncidentService.create(build_payload(LogisticsIncidentService, {
                'id_logistics_trip': trip['id_logistics_trip'], 'incident_type': 'demora',
                'description': 'No válido', 'status': 'desconocida',
            }))
        self.assertEqual('validations.logistics_incident.status.invalid', invalid_status.exception.message_key)