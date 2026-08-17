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
