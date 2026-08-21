from __future__ import annotations

import unittest

import jwt

from app.models import CustomerSupplier, Invoice, Proyect, Status
from app.models.session import transaction_context
from app.services.manual_invoice_service import create_manual_invoice
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_artifacts import invoice_xml_path
from app.services.stamping import FakeStampingProvider, StampingResult
from app.services.stamping import stamp_invoice
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


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


class CapturingProvider(FakeStampingProvider):
    def stamp(self, payload, idempotency_key):
        self.payload = payload
        return super().stamp(payload, idempotency_key)


class TestStampInvoice(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=10, name="Emisor Demo", tax_id="AAA010101AAA", postal_code="37000", fiscal_type="601", type="supplier", id_user=1, created_by=1),
                CustomerSupplier(id_customer_supplier=20, name="Cliente Demo", tax_id="BBB010101BBB", postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1),
                Proyect(id_proyect=30, id_customer_supplier=20, leader=1, proyect_description="Proyecto demo", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])

    def _create_invoice(self):
        result = create_manual_invoice({
            "id_proyect": 30,
            "id_customer_supplier": 20,
            "id_issuer_customer_supplier": 10,
            "id_status": 40,
            "forma_pago": "03",
            "metodo_pago": "PUE",
            "uso_cfdi": "G03",
            "concepts": [{
                "description": "Servicio demo",
                "quantity": 1,
                "unit_price": 100,
                "sat_product_key": "80101500",
                "sat_unit_key": "E48",
            }],
        }, {"id_user": 1, "id_proyect": 30})
        return result["invoice"]["id_invoice"]

    def test_manual_invoice_builds_full_payload_and_persists_stamp(self):
        invoice_id = self._create_invoice()
        provider = CapturingProvider()

        operation, created = stamp_invoice(invoice_id, "manual-demo-1", {"id_user": 1, "id_proyect": 30}, provider)

        self.assertTrue(created)
        self.assertEqual(operation["status"], "stamped")
        self.assertEqual(provider.payload["issuer"]["rfc"], "AAA010101AAA")
        self.assertEqual(provider.payload["receiver"]["rfc"], "BBB010101BBB")
        self.assertEqual(provider.payload["concepts"][0]["sat_product_key"], "80101500")
        stored_cfdi = parse_cfdi(invoice_xml_path(invoice_id).read_bytes())
        with transaction_context() as db:
            invoice = db.get(Invoice, invoice_id)
            self.assertEqual(invoice.invoice_status, "timbrada")
            self.assertEqual(invoice.folio_fiscal, stored_cfdi["uuid"])
            self.assertEqual(invoice.no_certificado_sat, "30001000000400000002")
            self.assertIsNotNone(invoice.certification_date)

    def test_invalid_fiscal_data_does_not_call_provider(self):
        invoice_id = self._create_invoice()
        provider = CapturingProvider()
        with transaction_context() as db:
            db.get(Invoice, invoice_id).domicilio_fiscal_receptor = None
            db.get(CustomerSupplier, 20).postal_code = None

        with self.assertRaises(AppError) as raised:
            stamp_invoice(invoice_id, "manual-demo-2", {"id_user": 1, "id_proyect": 30}, provider)

        self.assertEqual(raised.exception.message_key, "invoice.stamping_validation_failed")
        self.assertEqual(provider.calls, 0)
        with transaction_context() as db:
            self.assertEqual(db.get(Invoice, invoice_id).invoice_status, "pendiente")

    def test_stamped_documents_download_through_authenticated_routes(self):
        invoice_id = self._create_invoice()
        stamp_invoice(invoice_id, "manual-demo-http", {"id_user": 1, "id_proyect": 30}, FakeStampingProvider())
        token = jwt.encode({"id_user": 1, "id_proyect": 30, "is_superuser": True}, "test-secret", algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        xml_response = self.client.get(f"/invoice/{invoice_id}/xml", headers=headers)
        pdf_response = self.client.get(f"/invoice/{invoice_id}/pdf", headers=headers)
        public_legacy_response = self.client.get(f"/documents/invoice_pdf/{invoice_id}?format=pdf")

        self.assertEqual(xml_response.status_code, 200)
        self.assertEqual(xml_response.mimetype, "application/xml")
        with transaction_context() as db:
            persisted_uuid = db.get(Invoice, invoice_id).folio_fiscal
        self.assertEqual(parse_cfdi(xml_response.data)["uuid"], persisted_uuid)
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.mimetype, "application/pdf")
        self.assertTrue(pdf_response.data.startswith(b"%PDF"))
        self.assertEqual(public_legacy_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()