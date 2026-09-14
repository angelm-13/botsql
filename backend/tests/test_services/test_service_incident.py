from __future__ import annotations

from app.models import IncidentType, User
from app.models.session import transaction_context
from app.services.incident_service import IncidentService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.test_services.test_operations_workflow import OperationsTestCase


class TestIncidentService(OperationsTestCase):
    """CRUD basico de incidencias.

    Antes esta prueba capturaba `incident_status='test state'` y una fecha de
    cierre en una incidencia abierta, y pasaba porque el servicio no validaba
    nada. Ahora usa datos validos, que es lo que la prueba deberia haber
    afirmado desde el principio.
    """

    def test_crud_service_incident(self):
        created = IncidentService.create({
            'incident_date': '2026-01-15T12:00:00',
            'note': 'test note',
            'incident_status': 'abierta',
            'id_incident_type': 1,
            'id_user': 7,
            'created_by': 1,
        })
        self.assertIsNotNone(created)
        self.assertEqual('abierta', created['incident_status'])

        page = IncidentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def test_a_status_outside_the_catalog_no_longer_passes(self):
        with self.assertRaises(AppError):
            IncidentService.create({
                'incident_date': '2026-01-15T12:00:00',
                'incident_status': 'test state',
                'id_incident_type': 1,
                'id_user': 7,
                'created_by': 1,
            })
