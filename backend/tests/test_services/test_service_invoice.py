from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.invoice_service import InvoiceService


class TestInvoiceService(BackendTestCase):
    def test_crud_service_invoice(self):
        created = InvoiceService.create({'date_emision': 'datetime.now()', 'date_expiration': 'datetime.now()', 'subtotal': 10.5, 'tax': 10.5, 'total': 10.5, 'invoice_status': 'test state', 'payment_method': 'test payment_method', 'note': 'test notes', 'fiscal_reference': 'test fiscal_reference', 'serie_csd': 'test serie_csd', 'internationalization': 'exported', 'currency': 'test currency', 'type_exchange_rate': 10.5, 'tax_certification_supplier': 1, 'fiscal_certify_serie': 'test fiscal_certify_serie', 'certification_date': 'datetime.now()', 'cfdi_code': 'test cfdi_code', 'sat_code': 'test sat_code', 'sat_certification_code': 'test sat_certification_code', 'created_by': 1, 'nombre_emisor': 'test_nombre_emisor', 'lugar_expedicion': 'test_lugar_expedicion', 'tipo_de_comprobante': 'factura', 'rfc_receptor': 'test_rfc_receptor', 'nombre_receptor': 'test_nombre_receptor', 'regimen_fiscal_receptor': 'Empresa Moral', 'domicilio_fiscal_receptor': 'Paseos de Jerez 541, Las arboledas', 'folio_fiscal': 'test_folio_fiscal', 'exportacion': 'test_exportacion', 'folio': 'test_folio', 'no_certificado_sat': 'test_no_certificado_sat', 'sello_sat': 'test_sello_sat', 'sello_certificacion_sat': 'test_sello_certificacion_sat', 'no_certificado': 'test_no_certificado', 'descuento': 10.5, 'metodo_pago': 'test_metodo_pago', 'condiciones_pago': 'test_condiciones_pago', 'apply_tax': True, 'tax_rate': 10.5, 'commercial_terms': 'Vigencia sujeta a disponibilidad.'})
        self.assertIsNotNone(created)
        page = InvoiceService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
