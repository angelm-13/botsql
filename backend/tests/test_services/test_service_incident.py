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

    def _checada(self, **extra):
        return IncidentService.create({
            'incident_date': '2026-01-15T12:00:00',
            'incident_status': 'abierta',
            'id_incident_type': 1,
            'id_user': 7,
            'created_by': 1,
            **extra,
        })

    def test_the_check_in_keeps_latitude_longitude_and_distance_as_columns(self):
        # n8n manda numeros o texto; las tres quedan como numeros, no dentro de `note`.
        creada = self._checada(latitude='21.1161741', longitude=-101.6625754, distance_m=9)
        self.assertAlmostEqual(21.1161741, creada['latitude'], places=7)
        self.assertAlmostEqual(-101.6625754, creada['longitude'], places=7)
        self.assertEqual(9.0, creada['distance_m'])

    def test_an_incident_without_coordinates_leaves_them_empty(self):
        creada = self._checada()
        self.assertIsNone(creada['latitude'])
        self.assertIsNone(creada['longitude'])
        self.assertIsNone(creada['distance_m'])

    def test_coordinates_outside_their_real_range_are_rejected(self):
        for campo, valor in (
            ('latitude', 90.5), ('latitude', -91), ('longitude', 180.1),
            ('distance_m', -1), ('latitude', 'abc'), ('distance_m', 'NaN'),
        ):
            with self.subTest(campo=campo, valor=valor):
                with self.assertRaises(AppError) as contexto:
                    self._checada(**{campo: valor})
                self.assertEqual('errors.invalid_field', contexto.exception.message_key)

    def test_a_status_outside_the_catalog_no_longer_passes(self):
        with self.assertRaises(AppError):
            IncidentService.create({
                'incident_date': '2026-01-15T12:00:00',
                'incident_status': 'test state',
                'id_incident_type': 1,
                'id_user': 7,
                'created_by': 1,
            })
