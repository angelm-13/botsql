from __future__ import annotations

from app.models.pac_config import PacConfig
from app.models.session import transaction_context
from app.services.pac_config_service import default_base_url, provider_credentials, save_config
from tests.conftest import BackendTestCase


class TestPacConfigBlindajeProdSandbox(BackendTestCase):
    def _seed_config(self, provider: str, base_url: str) -> None:
        with transaction_context() as db:
            db.add(PacConfig(id_pac_config=1, provider=provider, facturama_base_url=base_url))

    def test_base_url_ignores_stale_value_saved_in_db_for_prod(self):
        self._seed_config("facturama", "https://old-and-wrong.example")

        credentials = provider_credentials()

        self.assertEqual(credentials["base_url"], default_base_url("facturama"))
        self.assertEqual(credentials["base_url"], "https://api.facturama.mx")

    def test_base_url_ignores_stale_value_saved_in_db_for_sandbox(self):
        self._seed_config("facturama_sandbox", "https://also-wrong.example")

        credentials = provider_credentials()

        self.assertEqual(credentials["base_url"], "https://apisandbox.facturama.mx")

    def test_base_url_ignores_malicious_override(self):
        self._seed_config("facturama", "https://api.facturama.mx")

        credentials = provider_credentials({"facturama_base_url": "https://evil.example"})

        self.assertEqual(credentials["base_url"], "https://api.facturama.mx")

    def test_save_config_persists_the_canonical_url_even_if_a_different_one_is_sent(self):
        result = save_config({
            "provider": "facturama_sandbox",
            "facturama_base_url": "https://not-the-real-one.example",
        })

        self.assertEqual(result["facturama_base_url"], "https://apisandbox.facturama.mx")

    def test_fake_provider_never_persists_a_base_url(self):
        result = save_config({"provider": "fake", "facturama_base_url": "https://ignored.example"})

        self.assertEqual(result["facturama_base_url"], "")
