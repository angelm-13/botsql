from __future__ import annotations

from app.models import LocationType
from app.models.session import transaction_context
from app.services.location_service import LocationService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_payload


class TestLocationService(BackendTestCase):
    def setUp(self):
        super().setUp()
        # `build_payload` rellena id_location_type=1 sin crear el tipo. La
        # prueba pasaba solo porque SQLite no exige las llaves foraneas; contra
        # PostgreSQL la alta habria fallado. Se crea el tipo que la ubicacion
        # necesita para que el caso sea real.
        with transaction_context() as db:
            db.add(LocationType(
                id_location_type=1,
                location_type_description="Almacen",
                is_warehouse=True,
                created_by=1,
            ))

    def test_crud_service_location(self):
        created = LocationService.create(build_payload(LocationService, {'location_description': 'test description', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = LocationService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def test_a_location_type_that_does_not_exist_is_refused(self):
        with self.assertRaises(AppError) as raised:
            LocationService.create({
                'id_location_type': 9999,
                'location_description': 'Ubicacion sin tipo',
                'created_by': 1,
            })

        self.assertEqual('validations.location.id_location_type.invalid', raised.exception.message_key)
