from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.invoice_service import InvoiceService


class TestInvoiceService(BackendTestCase):
    def test_crud_service_invoice(self):
        created = InvoiceService.create(build_payload(InvoiceService, {'date_emision': '2026-01-15T12:00:00', 'date_expiration': '2026-01-15T12:00:00', 'subtotal': 10.5, 'tax': 10.5, 'total': 21, 'invoice_status': 'test state', 'payment_method': 'test_payment_method', 'note': 'test notes', 'fiscal_reference': 'test_fiscal_reference', 'serie_csd': 'test_serie_csd', 'internationalization': 'exported', 'currency': 'MXN', 'type_exchange_rate': 1, 'tax_certification_supplier': 1, 'fiscal_certify_serie': 'test_serie_csd', 'certification_date': '2026-01-15T12:00:00', 'cfdi_code': 'test_cfdi_code', 'sat_code': 'test_sat_code', 'sat_certification_code': 'test_sat_certification_code', 'created_by': 1, 'nombre_emisor': 'test_nombre_emisor', 'lugar_expedicion': '37000', 'tipo_de_comprobante': 'factura', 'rfc_receptor': 'AAA010101AAA', 'nombre_receptor': 'test_nombre_receptor', 'regimen_fiscal_receptor': '601', 'domicilio_fiscal_receptor': '37000', 'folio_fiscal': '11111111-2222-3333-4444-555555555555', 'exportacion': '01', 'folio': '1', 'no_certificado_sat': '1', 'sello_sat': 'test_sello_sat', 'sello_certificacion_sat': 'test_sello_certificacion_sat', 'no_certificado': '1', 'descuento': 0, 'metodo_pago': 'PUE', 'condiciones_pago': 'contado', 'apply_tax': True, 'tax_rate': 100, 'commercial_terms': 'Vigencia sujeta a disponibilidad.'}))
        self.assertIsNotNone(created)
        page = InvoiceService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
