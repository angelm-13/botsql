from __future__ import annotations

import unittest

import jwt

from app.models import CustomerSupplier, Invoice, Proyect, Status
from app.models.session import transaction_context
from app.services.manual_invoice_service import create_manual_invoice
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_artifacts import invoice_xml_path
from app.services.stamping import FacturamaSandboxProvider, FakeStampingProvider, StampingResult
from app.services.stamping import stamp_invoice
from app.utils.auth import SECRET_KEY
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

    def test_facturama_maps_invoice_draft_to_cfdi_api(self):
        provider = FacturamaSandboxProvider(
            base_url="https://apisandbox.facturama.mx",
            username="demo",
            password="secret",
            expedition_place="37000",
            name_id="1",
        )

        body = provider.build_request_body({
            "issuer": {"rfc": "AAA010101AAA", "name": "Emisor", "tax_regime": "601", "postal_code": "37000"},
            "receiver": {"rfc": "BBB010101BBB", "name": "Cliente", "tax_regime": "601", "postal_code": "37100", "cfdi_use": "G03"},
            "payment_form": "03", "payment_method": "PUE", "currency": "MXN", "cfdi_type": "I",
            "concepts": [{
                "description": "Servicio", "quantity": "2", "unit_price": "100", "amount": "200",
                "discount": "20", "sat_product_key": "80101500", "sat_unit_key": "E48",
                "tax_object": "02", "iva_rate": "0.16", "isr_retention_rate": "0.10", "iva_retention_rate": "0",
            }],
        })

        self.assertEqual("37000", body["ExpeditionPlace"])
        self.assertEqual("03", body["PaymentForm"])
        self.assertEqual("BBB010101BBB", body["Receiver"]["Rfc"])
        self.assertEqual("80101500", body["Items"][0]["ProductCode"])
        self.assertEqual("190.80", body["Items"][0]["Total"])


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
        token = jwt.encode({"id_user": 1, "id_proyect": 30, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        xml_response = self.client.get(f"/invoice/{invoice_id}/xml", headers=headers)
        pdf_response = self.client.get(f"/invoice/{invoice_id}/pdf", headers=headers)
        quotation_response = self.client.get(f"/invoice/{invoice_id}/pdf?document=quotation", headers=headers)
        public_legacy_response = self.client.get(f"/documents/invoice_pdf/{invoice_id}?format=pdf")

        self.assertEqual(xml_response.status_code, 200)
        self.assertEqual(xml_response.mimetype, "application/xml")
        with transaction_context() as db:
            persisted_uuid = db.get(Invoice, invoice_id).folio_fiscal
        self.assertEqual(parse_cfdi(xml_response.data)["uuid"], persisted_uuid)
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.mimetype, "application/pdf")
        self.assertTrue(pdf_response.data.startswith(b"%PDF"))
        self.assertEqual(quotation_response.status_code, 200)
        self.assertEqual(quotation_response.mimetype, "application/pdf")
        self.assertTrue(quotation_response.data.startswith(b"%PDF"))
        self.assertEqual(public_legacy_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

class TestFacturamaPayloadMapping(unittest.TestCase):
    def _provider(self):
        return FacturamaSandboxProvider(
            base_url="https://apisandbox.facturama.mx", username="demo", password="secret",
            expedition_place="37000", name_id="1",
        )

    def _payload(self, **concept_overrides):
        concept = {
            "description": "Servicio", "quantity": "3", "unit_price": "33.333",
            "amount": "100.00", "discount": "0", "taxable_base": "100.00",
            "sat_product_key": "81111500", "sat_unit_key": "E48", "tax_object": "02",
            "breaks_down_taxes": True, "iva_exempt": False, "iva_rate": "0.160000",
            "transferred_iva": "16.00", "isr_retention_rate": "0", "retained_isr": "0.00",
            "iva_retention_rate": "0", "retained_iva": "0.00", "total": "116.00",
        }
        concept.update(concept_overrides)
        return {
            "issuer": {"rfc": "AAA010101AA1", "name": "Emisor", "tax_regime": "601", "postal_code": "37000"},
            "receiver": {"rfc": "BBB010101BB1", "name": "Cliente", "tax_regime": "601",
                         "postal_code": "37100", "cfdi_use": "G03"},
            "payment_form": "03", "payment_method": "PUE", "currency": "MXN", "cfdi_type": "I",
            "export_code": "01", "exchange_rate": "1", "concepts": [concept],
        }

    def test_precomputed_amounts_are_sent_verbatim(self):
        """Recalcularlos en el PAC reintroducia los descuadres de centavos."""
        item = self._provider().build_request_body(self._payload())["Items"][0]

        self.assertEqual(item["Subtotal"], "100.00")
        self.assertEqual(item["Total"], "116.00")
        # Unit es la etiqueta legible, UnitCode la ClaveUnidad del SAT.
        self.assertEqual(item["UnitCode"], "E48")
        self.assertEqual(item["Unit"], "Unidad de servicio")
        self.assertEqual(item["Taxes"][0]["Total"], "16.00")
        # ValorUnitario conserva los decimales que permite el SAT.
        self.assertEqual(item["UnitPrice"], "33.333")

    def test_concepts_without_breakdown_carry_no_taxes(self):
        item = self._provider().build_request_body(self._payload(
            tax_object="01", breaks_down_taxes=False, iva_rate="0", transferred_iva="0.00", total="100.00",
        ))["Items"][0]

        self.assertNotIn("Taxes", item)
        self.assertEqual(item["Total"], "100.00")

    def test_exempt_iva_is_sent_as_iva_exento_not_as_zero_rate(self):
        """Facturama traduce Name "IVA Exento" a TipoFactor="Exento" en el XML.

        Mandarlo como "IVA" con tasa 0 emitiria tasa cero, que el SAT trata
        como algo distinto del exento.
        """
        item = self._provider().build_request_body(self._payload(
            iva_exempt=True, iva_rate="0", transferred_iva="0.00", total="100.00",
        ))["Items"][0]
        tax = item["Taxes"][0]

        self.assertEqual(tax["Name"], "IVA Exento")
        self.assertEqual(tax["Total"], "0.00")
        self.assertEqual(tax["Base"], "100.00")
        self.assertEqual(item["Total"], "100.00")

    def test_zero_rate_is_sent_as_plain_iva(self):
        item = self._provider().build_request_body(self._payload(
            iva_rate="0.000000", transferred_iva="0.00", total="100.00",
        ))["Items"][0]

        self.assertEqual(item["Taxes"][0]["Name"], "IVA")
        self.assertEqual(item["Taxes"][0]["Rate"], "0.000000")

    def test_foreign_currency_sends_the_exchange_rate(self):
        body = self._provider().build_request_body({
            **self._payload(), "currency": "USD", "exchange_rate": "17.253400",
        })
        self.assertEqual(body["Currency"], "USD")
        self.assertEqual(body["ExchangeRate"], "17.253400")

    def test_mxn_does_not_send_an_exchange_rate(self):
        self.assertNotIn("ExchangeRate", self._provider().build_request_body(self._payload()))

    def test_export_code_is_taken_from_the_invoice(self):
        body = self._provider().build_request_body({**self._payload(), "export_code": "02"})
        self.assertEqual(body["Exportation"], "02")

    def test_missing_credentials_are_reported_without_calling_the_api(self):
        provider = FacturamaSandboxProvider(
            base_url="https://apisandbox.facturama.mx", username="", password="",
        )
        result = provider.stamp(self._payload(), "key-no-creds")

        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.error_code, "facturama_credentials_missing")

    def test_http_base_url_is_refused(self):
        with self.assertRaises(ValueError):
            FacturamaSandboxProvider(base_url="http://apisandbox.facturama.mx", username="a", password="b")


class TestStampingOperationDiagnostics(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=10, name="Emisor Demo", tax_id="AAA010101AAA", postal_code="37000", fiscal_type="601", type="supplier", id_user=1, created_by=1),
                CustomerSupplier(id_customer_supplier=20, name="Cliente Demo", tax_id="BBB010101BBB", postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1),
                Proyect(id_proyect=30, id_customer_supplier=20, leader=1, proyect_description="Proyecto demo", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])

    def _invoice(self):
        return create_manual_invoice({
            "id_proyect": 30, "id_customer_supplier": 20, "id_issuer_customer_supplier": 10,
            "id_status": 40, "forma_pago": "03", "metodo_pago": "PUE", "uso_cfdi": "G03",
            "concepts": [{"description": "Servicio", "quantity": 1, "unit_price": 100,
                          "sat_product_key": "80101500", "sat_unit_key": "E48"}],
        }, {"id_user": 1, "id_proyect": 30})["invoice"]["id_invoice"]

    def test_provider_diagnostics_reach_the_api_response(self):
        """Sin esto un rechazo solo mostraba el codigo, no el motivo del PAC."""
        invoice_id = self._invoice()
        provider = FakeStampingProvider(StampingResult(
            "rejected", error_code="http_401", metadata={"http_status": 401, "detail": "Unauthorized"},
        ))

        operation, _ = stamp_invoice(invoice_id, "diag-1", {"id_user": 1, "id_proyect": 30}, provider)

        self.assertEqual(operation["status"], "rejected")
        self.assertEqual(operation["error_code"], "http_401")
        self.assertEqual(operation["response_metadata"], {"http_status": 401, "detail": "Unauthorized"})

    def test_a_rejected_stamp_leaves_the_invoice_untouched(self):
        invoice_id = self._invoice()
        provider = FakeStampingProvider(StampingResult("rejected", error_code="http_401"))

        stamp_invoice(invoice_id, "diag-2", {"id_user": 1, "id_proyect": 30}, provider)

        with transaction_context() as db:
            invoice = db.get(Invoice, invoice_id)
            self.assertEqual(invoice.invoice_status, "pendiente")
            self.assertIsNone(invoice.folio_fiscal)

    def test_an_uncertain_stamp_is_not_treated_as_success(self):
        """Un timeout del PAC no debe dar la factura por timbrada."""
        invoice_id = self._invoice()
        provider = FakeStampingProvider(StampingResult("uncertain", error_code="provider_timeout"))

        operation, _ = stamp_invoice(invoice_id, "diag-3", {"id_user": 1, "id_proyect": 30}, provider)

        self.assertEqual(operation["status"], "uncertain")
        with transaction_context() as db:
            self.assertEqual(db.get(Invoice, invoice_id).invoice_status, "pendiente")
