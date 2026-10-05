"""`GET /location/options`: el nombre de una ubicacion sin leer el modulo.

En el prevale de un Supervisor, el "Sale de" se llenaba con `GET /location/`,
que exige leer `location` (modulo de inventario). Al quitarle ese modulo -que es
lo correcto, no administra el almacen- la lista llegaba vacia y el campo se
quedaba en "-". `/location/options` da solo id y descripcion, como
`/user/options` y `/incident_type/options`, sin permiso de entidad.
"""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.location import Location
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestLocationOptions(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=201, entity_name="warehouse_prevoucher",
                                    scope_create=4, scope_read=4, created_by=1))

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def test_a_role_without_location_permission_can_still_read_the_options(self):
        # Sin fila de `location` para el rol: la lista completa le dice 403...
        sin_permiso = self.client.get(
            "/location/", headers=self._headers(id_user=11, id_permission=201))
        self.assertEqual(403, sin_permiso.status_code)
        # ...pero las opciones, que solo traen id y nombre, si le llegan.
        respuesta = self.client.get(
            "/location/options", headers=self._headers(id_user=11, id_permission=201))
        self.assertEqual(200, respuesta.status_code)
        self.assertIsInstance(respuesta.get_json(), list)

    def test_the_options_carry_only_id_and_description(self):
        with transaction_context() as db:
            db.add(Location(id_location=901, id_location_type=1,
                            location_description="Almacen de prueba", created_by=1))
        respuesta = self.client.get(
            "/location/options", headers=self._headers(id_user=11, id_permission=201))
        self.assertEqual(200, respuesta.status_code)
        filas = [f for f in respuesta.get_json() if f["id_location"] == 901]
        self.assertEqual([{"id_location": 901,
                           "location_description": "Almacen de prueba"}], filas)

    def test_without_a_session_the_options_are_rejected(self):
        self.assertEqual(401, self.client.get("/location/options").status_code)
