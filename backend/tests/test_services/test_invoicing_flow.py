"""Flujo completo de facturacion: captura, revision previa y timbrado.

Recorre el camino real (`create_manual_invoice` -> `preflight_invoice` ->
`stamp_invoice`) y comprueba lo que importa fiscalmente: que los importes
guardados en la factura sean exactamente los del CFDI timbrado y que el XML
resultante pase todas las reglas del SAT.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

import jwt

from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status
from app.models.session import transaction_context
from app.services.cfdi_validation import inspect_cfdi_xml, validate_cfdi_xml
from app.services.invoice_artifacts import invoice_xml_path
from app.services.manual_invoice_service import create_manual_invoice, preview_manual_invoice
from app.services.stamping import FakeStampingProvider, preflight_invoice, stamp_invoice
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}


class InvoicingFlowTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=10, name="EMISOR DEMO SA DE CV", tax_id="AAA010101AA1",
                    postal_code="37000", fiscal_type="601", type="supplier", id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=20, name="CLIENTE DEMO SA DE CV", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1,
                ),
                Proyect(id_proyect=30, id_customer_supplier=20, leader=1, proyect_description="Proyecto demo", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])

    def _create(self, concepts, **overrides):
        payload = {
            "id_proyect": 30,
            "id_customer_supplier": 20,
            "id_issuer_customer_supplier": 10,
            "id_status": 40,
            "forma_pago": "03",
            "metodo_pago": "PUE",
            "uso_cfdi": "G03",
            "concepts": concepts,
        }
        payload.update(overrides)
        return create_manual_invoice(payload, ACTOR)


class TestInvoicingFlow(InvoicingFlowTestCase):
    def test_stamped_invoice_totals_match_the_cfdi_exactly(self):
        """Los precios con decimales solian dejar la factura y el XML descuadrados."""
        result = self._create([
            {"description": "Servicio A", "quantity": 3, "unit_price": "33.333",
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
            {"description": "Servicio B", "quantity": 7, "unit_price": "1.115",
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])
        invoice_id = result["invoice"]["id_invoice"]

        operation, created = stamp_invoice(invoice_id, "flow-decimales", ACTOR, FakeStampingProvider())
        self.assertTrue(created)
        self.assertEqual(operation["status"], "stamped")

        xml = invoice_xml_path(invoice_id).read_bytes()
        self.assertEqual(inspect_cfdi_xml(xml), {"errors": [], "warnings": []})

        import xml.etree.ElementTree as ET

        attributes = ET.fromstring(xml).attrib
        with transaction_context() as db:
            invoice = db.get(Invoice, invoice_id)
            self.assertEqual(Decimal(attributes["SubTotal"]), Decimal(str(invoice.subtotal)))
            self.assertEqual(Decimal(attributes["Total"]), Decimal(str(invoice.total)))
            self.assertEqual(invoice.invoice_status, "timbrada")

    def test_invoice_is_stored_with_the_sat_comprobante_code(self):
        result = self._create([
            {"description": "Servicio", "quantity": 1, "unit_price": 100,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])
        with transaction_context() as db:
            invoice = db.get(Invoice, result["invoice"]["id_invoice"])
            # Antes se guardaba la etiqueta 'factura', fuera del catalogo.
            self.assertEqual(invoice.tipo_de_comprobante, "I")
            self.assertEqual(invoice.uso_cfdi, "G03")

    def test_exempt_concept_is_stamped_as_exento_not_as_zero_rate(self):
        result = self._create(
            [{"description": "Alimento exento", "quantity": 2, "unit_price": "50",
              "sat_product_key": "50192700", "sat_unit_key": "H87"}],
            iva_tipo="exento",
        )
        invoice_id = result["invoice"]["id_invoice"]
        with transaction_context() as db:
            line = db.query(InvoiceMaterialService).filter_by(id_invoice=invoice_id).one()
            self.assertTrue(line.iva_exempt)

        stamp_invoice(invoice_id, "flow-exento", ACTOR, FakeStampingProvider())
        xml = invoice_xml_path(invoice_id).read_text(encoding="utf-8")
        self.assertIn('TipoFactor="Exento"', xml)
        self.assertNotIn('TasaOCuota="0.000000"', xml)
        self.assertEqual(validate_cfdi_xml(xml), [])

    def test_zero_rate_concept_keeps_the_tasa_breakdown(self):
        result = self._create(
            [{"description": "Producto tasa cero", "quantity": 1, "unit_price": "100",
              "sat_product_key": "50192700", "sat_unit_key": "H87"}],
            iva_tipo="0",
        )
        invoice_id = result["invoice"]["id_invoice"]
        stamp_invoice(invoice_id, "flow-tasa-cero", ACTOR, FakeStampingProvider())
        xml = invoice_xml_path(invoice_id).read_text(encoding="utf-8")
        self.assertIn('TasaOCuota="0.000000"', xml)
        self.assertNotIn('TipoFactor="Exento"', xml)
        self.assertEqual(validate_cfdi_xml(xml), [])

    def test_retentions_are_declared_per_concept_and_in_the_summary(self):
        result = self._create(
            [{"description": "Honorarios", "quantity": 1, "unit_price": "10000",
              "sat_product_key": "84111500", "sat_unit_key": "E48"}],
            isr_ret_rate="10", iva_ret_rate="10.6667",
        )
        invoice_id = result["invoice"]["id_invoice"]
        stamp_invoice(invoice_id, "flow-retenciones", ACTOR, FakeStampingProvider())
        xml = invoice_xml_path(invoice_id).read_bytes()
        self.assertEqual(validate_cfdi_xml(xml), [])

        import xml.etree.ElementTree as ET

        namespace = "{http://www.sat.gob.mx/cfd/4}"
        summary = ET.fromstring(xml).find(f"{namespace}Impuestos")
        # 10000 * 0.10 = 1000 de ISR y 10000 * 0.106667 = 1066.67 de IVA.
        self.assertEqual(summary.attrib["TotalImpuestosRetenidos"], "2066.67")
        self.assertEqual(summary.attrib["TotalImpuestosTrasladados"], "1600.00")
        attributes = ET.fromstring(xml).attrib
        self.assertEqual(attributes["Total"], "9533.33")


class TestStampingPreflight(InvoicingFlowTestCase):
    def _invoice(self):
        return self._create([
            {"description": "Servicio", "quantity": 1, "unit_price": 1000,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])["invoice"]["id_invoice"]

    def test_preflight_reports_a_stampable_invoice_without_calling_the_pac(self):
        invoice_id = self._invoice()
        report = preflight_invoice(invoice_id, ACTOR)

        self.assertTrue(report["can_stamp"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["authorized_lines"], 1)
        self.assertEqual(report["totals"]["total"], "1160.00")
        self.assertEqual(validate_cfdi_xml(report["preview_xml"]), [])
        with transaction_context() as db:
            self.assertEqual(db.get(Invoice, invoice_id).invoice_status, "pendiente")

    def test_preflight_explains_why_an_invoice_cannot_be_stamped(self):
        invoice_id = self._invoice()
        with transaction_context() as db:
            invoice = db.get(Invoice, invoice_id)
            invoice.rfc_receptor = "XAXX010101000"
            invoice.regimen_fiscal_receptor = "612"

        report = preflight_invoice(invoice_id, ACTOR)
        self.assertFalse(report["can_stamp"])
        self.assertIn("invoice.generic_receiver_tax_regime_must_be_616", report["errors"])
        self.assertIn("invoice.generic_receiver_cfdi_use_must_be_s01", report["errors"])
        self.assertIsNone(report["preview_xml"])

    def test_preflight_warns_when_the_stored_total_drifted_from_the_lines(self):
        invoice_id = self._invoice()
        with transaction_context() as db:
            db.get(Invoice, invoice_id).total = Decimal("1159.99")

        report = preflight_invoice(invoice_id, ACTOR)
        # No impide timbrar, pero queda visible: el timbrado corrige el importe.
        self.assertIn("invoice.stored_total_differs_from_cfdi_total", report["warnings"])
        self.assertTrue(report["can_stamp"])
        self.assertEqual(report["stored_total"], "1159.99")
        self.assertEqual(report["totals"]["total"], "1160.00")

        stamp_invoice(invoice_id, "flow-drift", ACTOR, FakeStampingProvider())
        with transaction_context() as db:
            self.assertEqual(Decimal(str(db.get(Invoice, invoice_id).total)), Decimal("1160.00"))

    def test_preflight_is_reachable_over_http_and_scoped_to_the_project(self):
        invoice_id = self._invoice()
        token = jwt.encode({"id_user": 1, "id_proyect": 30, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        response = self.client.get(
            f"/stamping/invoices/{invoice_id}/preflight",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["can_stamp"])
        # El XML solo viaja si se pide expresamente.
        self.assertNotIn("preview_xml", body)

        outsider = jwt.encode({"id_user": 2, "id_proyect": 99}, SECRET_KEY, algorithm="HS256")
        denied = self.client.get(
            f"/stamping/invoices/{invoice_id}/preflight",
            headers={"Authorization": f"Bearer {outsider}"},
        )
        self.assertEqual(denied.status_code, 403)


class TestInvoicingGuardrails(InvoicingFlowTestCase):
    def test_stamping_is_blocked_when_the_receiver_data_is_not_sat_compliant(self):
        invoice_id = self._create([
            {"description": "Servicio", "quantity": 1, "unit_price": 100,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])["invoice"]["id_invoice"]
        with transaction_context() as db:
            db.get(Invoice, invoice_id).regimen_fiscal_receptor = "999"

        provider = FakeStampingProvider()
        with self.assertRaises(AppError) as raised:
            stamp_invoice(invoice_id, "guard-regimen", ACTOR, provider)

        self.assertEqual(raised.exception.message_key, "invoice.stamping_validation_failed")
        self.assertIn("invoice.receiver_tax_regime_not_in_catalog", raised.exception.meta["errors"])
        self.assertEqual(provider.calls, 0)

    def test_an_invalid_document_from_the_pac_does_not_mark_the_invoice_as_stamped(self):
        """Si el PAC devuelve un CFDI que no cumple, no lo damos por bueno."""
        from app.services.stamping import StampingResult

        invoice_id = self._create([
            {"description": "Servicio", "quantity": 1, "unit_price": 100,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])["invoice"]["id_invoice"]

        broken_xml = (
            '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"'
            ' xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"'
            ' Version="4.0" Fecha="2026-08-26T10:00:00" SubTotal="100.00" Total="500.00"'
            ' Moneda="MXN" TipoDeComprobante="I" Exportacion="01" MetodoPago="PUE"'
            ' FormaPago="03" LugarExpedicion="37000" Sello="S" Certificado="C"'
            ' NoCertificado="30001000000400000001">'
            '<cfdi:Emisor Rfc="AAA010101AA1" Nombre="EMISOR" RegimenFiscal="601"/>'
            '<cfdi:Receptor Rfc="BBB010101BB1" Nombre="CLIENTE" DomicilioFiscalReceptor="37100"'
            ' RegimenFiscalReceptor="601" UsoCFDI="G03"/>'
            '<cfdi:Conceptos><cfdi:Concepto ClaveProdServ="81111500" Cantidad="1" ClaveUnidad="E48"'
            ' Descripcion="Servicio" ValorUnitario="100" Importe="100.00" ObjetoImp="01"/>'
            '</cfdi:Conceptos><cfdi:Complemento>'
            '<tfd:TimbreFiscalDigital Version="1.1" UUID="3F2C9A1B-4D5E-4F60-8A71-B2C3D4E5F607"'
            ' FechaTimbrado="2026-08-26T10:00:05" RfcProvCertif="MOC010101AAA" SelloCFD="X"'
            ' NoCertificadoSAT="30001000000400000002" SelloSAT="Y"/>'
            '</cfdi:Complemento></cfdi:Comprobante>'
        )
        provider = FakeStampingProvider(StampingResult(
            "stamped", "3F2C9A1B-4D5E-4F60-8A71-B2C3D4E5F607", {"http_status": 200}, xml=broken_xml,
        ))

        with self.assertRaises(AppError) as raised:
            stamp_invoice(invoice_id, "guard-pac", ACTOR, provider)

        self.assertEqual(raised.exception.message_key, "invoice.stamped_document_invalid")
        self.assertIn(
            "cfdi.total_no_cuadra_con_subtotal_menos_descuento_mas_impuestos",
            raised.exception.meta["errors"],
        )
        with transaction_context() as db:
            self.assertEqual(db.get(Invoice, invoice_id).invoice_status, "pendiente")

    def test_only_authorized_lines_reach_the_cfdi(self):
        invoice_id = self._create([
            {"description": "Partida autorizada", "quantity": 1, "unit_price": 100,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
            {"description": "Partida por revisar", "quantity": 1, "unit_price": 900,
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ])["invoice"]["id_invoice"]
        with transaction_context() as db:
            second = db.query(InvoiceMaterialService).filter_by(
                id_invoice=invoice_id, invoice_material_service_description="Partida por revisar",
            ).one()
            second.authorization_status = "pending"

        report = preflight_invoice(invoice_id, ACTOR)
        self.assertEqual(report["authorized_lines"], 1)
        self.assertEqual(report["totals"]["subtotal"], "100.00")

    def test_preview_matches_what_gets_persisted(self):
        concepts = [
            {"description": "Servicio A", "quantity": 3, "unit_price": "33.333",
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
            {"description": "Servicio B", "quantity": "2.5", "unit_price": "19.99",
             "sat_product_key": "81111500", "sat_unit_key": "E48"},
        ]
        preview = preview_manual_invoice({"metodo_pago": "PUE", "forma_pago": "03", "concepts": concepts})
        invoice = self._create(concepts)["invoice"]

        self.assertTrue(preview["can_create"])
        self.assertEqual(Decimal(preview["subtotal"]), Decimal(str(invoice["subtotal"])))
        self.assertEqual(Decimal(preview["total"]), Decimal(str(invoice["total"])))


if __name__ == "__main__":
    unittest.main()
