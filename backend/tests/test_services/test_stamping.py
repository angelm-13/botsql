from __future__ import annotations

import unittest

from app.services.stamping import FakeStampingProvider, StampingResult


class TestStampingProviders(unittest.TestCase):
    def test_fake_provider_success_without_network(self):
        provider = FakeStampingProvider()
        result = provider.stamp({"total": "116.00"}, "key-1")

        self.assertEqual(result.status, "stamped")
        self.assertEqual(provider.calls, 1)

    def test_fake_provider_models_rejection_and_uncertain_timeout(self):
        rejected = FakeStampingProvider(StampingResult("rejected", error_code="invalid_cfdi"))
        uncertain = FakeStampingProvider(StampingResult("uncertain", error_code="provider_timeout"))

        self.assertEqual(rejected.stamp({}, "key-2").status, "rejected")
        self.assertEqual(uncertain.stamp({}, "key-3").status, "uncertain")

    def test_reconciliation_preserves_uncertain_state(self):
        provider = FakeStampingProvider(StampingResult("uncertain", "provider-ref", error_code="pending"))

        result = provider.reconcile("provider-ref")

        self.assertEqual(result.status, "uncertain")
        self.assertEqual(result.reference, "provider-ref")


if __name__ == "__main__":
    unittest.main()