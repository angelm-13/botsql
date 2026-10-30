from __future__ import annotations

from tests.conftest import BackendTestCase


class TestAuthMfaFlow(BackendTestCase):
    def test_login_rejects_invalid_credentials_with_i18n_key(self):
        response = self.client.post("/auth/login", json={"username": "missing", "password": "wrong"})
        self.assertIn(response.status_code, [400, 401, 404])
        data = self.json(response)
        self.assertTrue("error" in data or "message" in data or "code" in data)

    def test_mfa_verify_requires_temp_token_and_code(self):
        response = self.client.post("/auth/mfa/verify-login", json={"temp_token": "bad", "code": "000000"})
        self.assertIn(response.status_code, [400, 401, 403, 422])

    def test_mfa_setup_requires_authentication(self):
        response = self.client.post("/auth/mfa/setup", headers={})
        self.assertIn(response.status_code, [401, 403])

    def test_mfa_enable_requires_code(self):
        response = self.client.post("/auth/mfa/enable", json={}, headers=self.auth_headers())
        self.assertIn(response.status_code, [400, 401, 403, 422])

    def test_mfa_verify_is_throttled_after_repeated_failures(self):
        import jwt
        from app.utils import login_throttle
        from app.utils.auth import SECRET_KEY

        login_throttle.reiniciar()
        temp = jwt.encode({"id_user": 5, "mfa_step": True}, SECRET_KEY, algorithm="HS256")
        # Los fallos que el propio endpoint registra al equivocarse de codigo.
        for _ in range(login_throttle.max_intentos_por_usuario()):
            login_throttle.registrar_fallo("mfa:5", "127.0.0.1")
        response = self.client.post("/auth/mfa/verify-login",
                                    json={"temp_token": temp, "code": "000000"})
        self.assertEqual(429, response.status_code)
        self.assertIn("Retry-After", response.headers)
        login_throttle.reiniciar()
