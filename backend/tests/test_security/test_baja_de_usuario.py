"""Un usuario dado de baja no entra y su token vigente deja de servir."""
from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import patch

import bcrypt
import jwt

from app.models.session import transaction_context
from app.models.user import User
from app.utils import auth as auth_utils
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

CLAVE = "Clave-de-prueba-1"


class TestBajaDeUsuario(BackendTestCase):
    def setUp(self):
        super().setUp()
        hash_ = bcrypt.hashpw(CLAVE.encode(), bcrypt.gensalt()).decode()
        with transaction_context() as db:
            db.add(User(
                id_user=61, created_by=1, id_permission=1, full_name="Persona de prueba",
                username="persona61", password=hash_, id_proyect=1, supervisor=1, id_status=1,
            ))

    def _baja(self):
        with transaction_context() as db:
            db.get(User, 61).deletion_date = datetime.utcnow()

    def _login(self):
        return self.client.post("/auth/login", json={"username": "persona61", "password": CLAVE})

    def _token(self, id_user=61):
        return jwt.encode({"id_user": id_user, "id_permission": 1, "user_type": "employee"}, SECRET_KEY, algorithm="HS256")

    def _pide(self, id_user=61):
        # `sesion_vigente` se salta la revision con TESTING=1: aqui se prueba justo
        # esa revision, asi que se apaga la bandera solo durante la peticion y se
        # vacia la copia de vigencias.
        auth_utils.olvidar_vigencias()
        with patch.dict(os.environ, {"TESTING": "0"}):
            respuesta = self.client.get("/vouchers", headers={"Authorization": "Bearer %s" % self._token(id_user)})
        auth_utils.olvidar_vigencias()
        return respuesta

    def test_an_active_user_logs_in(self):
        self.assertEqual(200, self._login().status_code)

    def test_a_removed_user_cannot_log_in_and_gets_the_same_answer_as_a_bad_password(self):
        self._baja()
        r = self._login()
        mala = self.client.post("/auth/login", json={"username": "persona61", "password": "otra"})
        self.assertEqual(401, r.status_code)
        self.assertEqual(mala.status_code, r.status_code)
        self.assertEqual(self.json(mala).get("error_key"), self.json(r).get("error_key"))

    def test_a_live_token_of_a_removed_user_is_rejected(self):
        self.assertNotEqual(401, self._pide().status_code)
        self._baja()
        self.assertEqual(401, self._pide().status_code)
