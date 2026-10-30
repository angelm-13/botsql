"""`/documents/<doc>/<id>` lee el token por su cuenta (el modulo de documentos es
ajeno a `token_required`) y debe aplicar la MISMA regla de sesion: ni el token del
paso 1 del login con MFA ni el de un usuario dado de baja sirven para descargar."""
from __future__ import annotations

import os
from unittest import mock

import jwt

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.utils import auth
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

RUTA = "/documents/invoice_pdf/1?format=xml"


class TestDocumentosSesion(BackendTestCase):
    def setUp(self):
        super().setUp()
        if not any(r.rule == "/documents/<document_key>/<record_id>" for r in self.app.url_map.iter_rules()):
            self.skipTest("el modulo de documentos no esta registrado (falta el motor de PDF)")
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=401, entity_name="invoice", scope_read=4, created_by=1))
        auth.olvidar_vigencias()

    def tearDown(self):
        auth.olvidar_vigencias()
        super().tearDown()

    def _get(self, **claims):
        token = jwt.encode(claims, SECRET_KEY, algorithm="HS256")
        return self.client.get(RUTA, headers={"Authorization": "Bearer " + token}).status_code

    def test_the_half_finished_mfa_token_is_not_a_session(self):
        self.assertEqual(401, self._get(id_user=41, id_permission=401, mfa_step=True))

    def test_the_same_token_without_the_mfa_flag_is_a_session(self):
        # No 401: pasa la sesion y la autorizacion/registro dicen otra cosa (403/404).
        self.assertNotEqual(401, self._get(id_user=41, id_permission=401))

    def test_a_token_of_a_user_that_no_longer_exists_is_revoked(self):
        with mock.patch.dict(os.environ, {"TESTING": "0"}):
            self.assertEqual(401, self._get(id_user=999999, id_permission=401))
