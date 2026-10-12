import os
from unittest import mock

from app.models.session import transaction_context
from app.models.user import User
from app.utils import auth
from tests.conftest import BackendTestCase


class TestLaSesionSeRevalida(BackendTestCase):
    def setUp(self):
        super().setUp()
        auth.olvidar_vigencias()
        with transaction_context() as db:
            db.add(User(id_user=77, full_name="Op", username="op77", id_permission=6,
                        id_proyect=1, id_status=1, supervisor=1, created_by=1, email="o@x.mx"))

    def _sin_modo_de_pruebas(self):
        env = {k: v for k, v in os.environ.items() if k != "TESTING"}
        return mock.patch.dict(os.environ, env, clear=True)

    def test_a_live_user_with_the_same_role_keeps_the_session(self):
        with self._sin_modo_de_pruebas():
            self.assertTrue(auth.sesion_vigente({"id_user": 77, "id_permission": 6}))

    def test_a_deactivated_user_loses_the_session(self):
        with self._sin_modo_de_pruebas():
            self.assertTrue(auth.sesion_vigente({"id_user": 77, "id_permission": 6}))
            auth.olvidar_vigencias()
            with transaction_context() as db:
                from datetime import datetime
                db.get(User, 77).deletion_date = datetime.utcnow()
            self.assertFalse(auth.sesion_vigente({"id_user": 77, "id_permission": 6}))

    def test_a_changed_role_invalidates_the_old_token(self):
        with self._sin_modo_de_pruebas():
            self.assertFalse(auth.sesion_vigente({"id_user": 77, "id_permission": 1}))

    def test_a_user_that_does_not_exist_has_no_session(self):
        with self._sin_modo_de_pruebas():
            self.assertFalse(auth.sesion_vigente({"id_user": 9999, "id_permission": 1}))
