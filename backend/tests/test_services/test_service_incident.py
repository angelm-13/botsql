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

    # Un JPEG minimo en base64 (firma "/9j/"): lo que n8n manda, sin "data:".
    FOTO = '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/'

    def test_the_photo_is_kept_whole_even_when_it_is_megabytes_long(self):
        # TEXT, no VARCHAR(n): una foto de telefono en base64 pasa de 1 MB.
        grande = 'A' * (3 * 1024 * 1024)
        creada = self._checada(photo_base64=grande)
        self.assertEqual(len(grande), len(creada['photo_base64']))
        self.assertEqual(grande, IncidentService.get(creada['id_incident'])['photo_base64'])

    def test_the_photo_drops_line_breaks_and_accepts_a_data_uri(self):
        partida = self.FOTO[:40] + '\r\n' + self.FOTO[40:] + '\n'
        self.assertEqual(self.FOTO, self._checada(photo_base64=partida)['photo_base64'])
        con_prefijo = 'data:image/jpeg;base64,' + self.FOTO
        self.assertEqual(con_prefijo, self._checada(photo_base64=con_prefijo)['photo_base64'])

    def test_an_empty_photo_is_stored_as_null(self):
        self.assertIsNone(self._checada(photo_base64='')['photo_base64'])
        self.assertIsNone(self._checada()['photo_base64'])

    def test_text_that_is_not_base64_is_rejected_as_a_photo(self):
        for valor in ('esto no es base64!', '<script>alert(1)</script>', 'data:text/html;base64,AAAA', 12345):
            with self.subTest(valor=valor):
                with self.assertRaises(AppError) as contexto:
                    self._checada(photo_base64=valor)
                self.assertEqual('errors.invalid_field', contexto.exception.message_key)
                self.assertEqual('photo_base64', contexto.exception.meta['field'])

    def test_a_photo_over_the_limit_is_rejected(self):
        from unittest import mock
        with mock.patch('app.services.incident_service.FOTO_MAX_CARACTERES', 100):
            with self.assertRaises(AppError):
                self._checada(photo_base64='A' * 101)
            self._checada(photo_base64='A' * 100)

    def test_the_list_does_not_carry_the_photo_only_whether_there_is_one(self):
        from app.services.incident_service import list_incidents
        con = self._checada(photo_base64=self.FOTO)['id_incident']
        sin = self._checada()['id_incident']
        filas = {f['id_incident']: f for f in list_incidents({'is_superuser': True}, per_page=100)['items']}
        self.assertNotIn('photo_base64', filas[con])
        self.assertTrue(filas[con]['has_photo'])
        self.assertFalse(filas[sin]['has_photo'])

    def test_the_event_log_records_the_photo_change_without_copying_the_image(self):
        from app.models import EventLog
        creada = self._checada()
        IncidentService.update(creada['id_incident'], {'photo_base64': self.FOTO}, user_id=1)
        with transaction_context() as db:
            asientos = db.query(EventLog).filter_by(table_name='incident', field_name='photo_base64').all()
            valores = [str(a.after_value) for a in asientos]
        self.assertEqual(1, len(valores))
        self.assertNotIn(self.FOTO, valores[0])
        self.assertIn(str(len(self.FOTO)), valores[0])

    def test_a_status_outside_the_catalog_no_longer_passes(self):
        with self.assertRaises(AppError):
            IncidentService.create({
                'incident_date': '2026-01-15T12:00:00',
                'incident_status': 'test state',
                'id_incident_type': 1,
                'id_user': 7,
                'created_by': 1,
            })
