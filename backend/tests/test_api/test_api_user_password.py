from __future__ import annotations

import bcrypt
import jwt

from app.models import Proyect, Status, User
from app.models.session import transaction_context
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


class TestChangeOwnPassword(BackendTestCase):
    """POST /user/me/password -- cualquier usuario cambia SU PROPIA
    contrasena, sin importar su rol, porque antes no existia ningun camino
    para esto (`password` esta fuera del CRUD generico de usuarios).
    """

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                Proyect(id_proyect=700, id_customer_supplier=1, leader=1, proyect_description="Proyecto de pruebas", created_by=1),
                Status(id_status=700, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])
            db.flush()
            sembrar_actor(db, id_proyect=700, id_status=700, ids=(701,))
            usuario = db.get(User, 701)
            usuario.password = bcrypt.hashpw(b"ViejaClave1", bcrypt.gensalt()).decode("utf-8")

    def _token(self, id_user=701):
        return jwt.encode({"id_user": id_user, "id_permission": 1}, SECRET_KEY, algorithm="HS256")

    def _headers(self, id_user=701):
        return {"Authorization": f"Bearer {self._token(id_user)}"}

    def test_it_changes_the_password_with_the_right_current_one(self):
        response = self.client.post(
            "/user/me/password",
            json={"current_password": "ViejaClave1", "new_password": "NuevaClave2"},
            headers=self._headers(),
        )

        self.assertEqual(200, response.status_code)
        with transaction_context() as db:
            usuario = db.get(User, 701)
            self.assertTrue(bcrypt.checkpw(b"NuevaClave2", usuario.password.encode("utf-8")))
            self.assertFalse(bcrypt.checkpw(b"ViejaClave1", usuario.password.encode("utf-8")))

    def test_it_rejects_the_wrong_current_password(self):
        response = self.client.post(
            "/user/me/password",
            json={"current_password": "NoEsEsta", "new_password": "NuevaClave2"},
            headers=self._headers(),
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("errors.auth_invalid_credentials", self.json(response)["error_key"])
        with transaction_context() as db:
            usuario = db.get(User, 701)
            self.assertTrue(bcrypt.checkpw(b"ViejaClave1", usuario.password.encode("utf-8")))

    def test_it_rejects_a_weak_new_password(self):
        response = self.client.post(
            "/user/me/password",
            json={"current_password": "ViejaClave1", "new_password": "corta1"},
            headers=self._headers(),
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("errors.validation_failed", self.json(response)["error_key"])

    def test_it_can_only_change_its_own_password_never_someone_elses(self):
        """No hay id en la ruta a proposito -- siempre es `user_data['id_user']`."""
        with transaction_context() as db:
            db.add(User(
                id_user=702, full_name="Otro usuario", username="otro702",
                id_permission=1, id_proyect=700, id_status=700, supervisor=701,
                created_by=701,
                password=bcrypt.hashpw(b"OtraClave1", bcrypt.gensalt()).decode("utf-8"),
            ))

        response = self.client.post(
            "/user/me/password",
            json={"current_password": "OtraClave1", "new_password": "NuevaClave2"},
            headers=self._headers(id_user=701),
        )

        self.assertEqual(400, response.status_code)
        with transaction_context() as db:
            otro = db.get(User, 702)
            self.assertTrue(bcrypt.checkpw(b"OtraClave1", otro.password.encode("utf-8")))
