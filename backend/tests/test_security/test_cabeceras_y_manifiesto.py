import jwt

from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase


class TestCabecerasYManifiesto(BackendTestCase):
    def test_every_response_carries_the_basic_security_headers(self):
        r = self.client.get("/health")

        self.assertEqual("nosniff", r.headers.get("X-Content-Type-Options"))
        self.assertEqual("SAMEORIGIN", r.headers.get("X-Frame-Options"))
        self.assertIn("strict-origin", r.headers.get("Referrer-Policy"))

    def test_hsts_is_not_sent_outside_production(self):
        self.assertIsNone(self.client.get("/health").headers.get("Strict-Transport-Security"))

    def test_the_document_manifest_needs_a_session(self):
        self.assertEqual(401, self.client.get("/documents/manifest").status_code)

    def test_with_a_session_the_manifest_still_answers(self):
        token = jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        r = self.client.get("/documents/manifest", headers={"Authorization": "Bearer " + token})

        self.assertEqual(200, r.status_code)
        self.assertIn("documents", self.json(r))
