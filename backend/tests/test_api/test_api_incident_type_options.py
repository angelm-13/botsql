"""`/incident_type/options` alimenta el selector de tipo del vale de almacen.

Almacenista no tiene el modulo `operaciones` (al que pertenece `incident_type`),
asi que `GET /incident_type/` le da 403; con la lista vacia la pantalla de vales
dejaba "Levantar vale" deshabilitado. `/options` no exige permiso de entidad --
igual que `/user/options` y `/proyect/options`.
"""
from __future__ import annotations

import jwt

from app.models.entity_permission import EntityPermission
from app.models.incident_type import IncidentType
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestIncidentTypeOptions(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Almacenista: opera vales, pero sin ninguna fila de incident_type.
                EntityPermission(id_permission=401, entity_name="warehouse_voucher",
                                  scope_create=4, scope_read=4, scope_update=4, created_by=1),
                IncidentType(incident_type_description="Prestamo", created_by=1),
            ])

    def _headers(self, **claims):
        return {"Authorization": "Bearer %s" % jwt.encode(claims, SECRET_KEY, algorithm="HS256")}

    def test_a_role_without_incident_type_permission_can_list_the_options(self):
        headers = self._headers(id_user=41, id_permission=401)

        self.assertEqual(403, self.client.get("/incident_type/", headers=headers).status_code)

        respuesta = self.client.get("/incident_type/options", headers=headers)
        self.assertEqual(200, respuesta.status_code)
        descripciones = [x["incident_type_description"] for x in self.json(respuesta)]
        self.assertIn("Prestamo", descripciones)

    def test_options_expose_only_id_and_description(self):
        respuesta = self.client.get("/incident_type/options",
                                    headers=self._headers(id_user=41, id_permission=401))
        for fila in self.json(respuesta):
            self.assertEqual({"id_incident_type", "incident_type_description"}, set(fila))

    def test_options_require_authentication(self):
        self.assertEqual(401, self.client.get("/incident_type/options").status_code)
