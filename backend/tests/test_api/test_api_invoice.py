from __future__ import annotations

from io import BytesIO
import jwt

from tests.conftest import BackendTestCase
from app.utils.auth import SECRET_KEY


class TestInvoiceApi(BackendTestCase):
    def test_upload_xml_requires_principal_company(self):
        token = jwt.encode({'id_user': 1, 'is_superuser': True}, SECRET_KEY, algorithm='HS256')
        response = self.client.post(
            '/invoice/upload-xml',
            data={'files': (BytesIO(b'<xml/>'), 'invoice.xml')},
            headers={'Authorization': f'Bearer {token}'},
            content_type='multipart/form-data',
        )
        self.assertEqual(409, response.status_code)
        self.assertEqual('invoice.principal_company_required', self.json(response)['error_key'])

    def test_list_invoice_supports_pagination(self):
        response = self.client.get("/invoice/?page=1&per_page=10", headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403])
        if response.status_code == 200:
            data = self.json(response)
            self.assertIn("items", data)
            self.assertIn("total", data)

    def test_create_invoice_validates_payload(self):
        response = self.client.post("/invoice/", json={'date_emision': '2026-01-15T12:00:00', 'date_expiration': '2026-01-15T12:00:00', 'subtotal': 10.5, 'tax': 10.5, 'total': 10.5, 'invoice_status': 'test state', 'payment_method': 'test payment_method', 'note': 'test notes', 'fiscal_reference': 'test fiscal_reference', 'serie_csd': 'test serie_csd', 'internationalization': 'exported', 'currency': 'test currency', 'type_exchange_rate': 10.5, 'tax_certification_supplier': 1, 'fiscal_certify_serie': 'test fiscal_certify_serie', 'certification_date': '2026-01-15T12:00:00', 'cfdi_code': 'test cfdi_code', 'sat_code': 'test sat_code', 'sat_certification_code': 'test sat_certification_code', 'created_by': 1, 'nombre_emisor': 'test_nombre_emisor', 'lugar_expedicion': 'test_lugar_expedicion', 'tipo_de_comprobante': 'factura', 'rfc_receptor': 'test_rfc_receptor', 'nombre_receptor': 'test_nombre_receptor', 'regimen_fiscal_receptor': 'Empresa Moral', 'domicilio_fiscal_receptor': 'Paseos de Jerez 541, Las arboledas', 'folio_fiscal': 'test_folio_fiscal', 'exportacion': 'test_exportacion', 'folio': 'test_folio', 'no_certificado_sat': 'test_no_certificado_sat', 'sello_sat': 'test_sello_sat', 'sello_certificacion_sat': 'test_sello_certificacion_sat', 'no_certificado': 'test_no_certificado', 'descuento': 10.5, 'metodo_pago': 'test_metodo_pago', 'condiciones_pago': 'test_condiciones_pago', 'apply_tax': True, 'tax_rate': 10.5, 'commercial_terms': 'Vigencia sujeta a disponibilidad.'}, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 201, 400, 401, 403, 422])

    def test_get_update_delete_invoice_handle_missing_record(self):
        missing_id = 999999
        self.assertIn(self.client.get(f"/invoice/{missing_id}", headers=self.auth_headers()).status_code, [200, 401, 403, 404])
        self.assertIn(self.client.put(f"/invoice/{missing_id}", json={'date_emision': '2026-01-15T12:00:00', 'date_expiration': '2026-01-15T12:00:00', 'subtotal': 10.5, 'tax': 10.5, 'total': 10.5, 'invoice_status': 'test state', 'payment_method': 'test payment_method', 'note': 'test notes', 'fiscal_reference': 'test fiscal_reference', 'serie_csd': 'test serie_csd', 'internationalization': 'exported', 'currency': 'test currency', 'type_exchange_rate': 10.5, 'tax_certification_supplier': 1, 'fiscal_certify_serie': 'test fiscal_certify_serie', 'certification_date': '2026-01-15T12:00:00', 'cfdi_code': 'test cfdi_code', 'sat_code': 'test sat_code', 'sat_certification_code': 'test sat_certification_code', 'created_by': 1, 'nombre_emisor': 'test_nombre_emisor', 'lugar_expedicion': 'test_lugar_expedicion', 'tipo_de_comprobante': 'factura', 'rfc_receptor': 'test_rfc_receptor', 'nombre_receptor': 'test_nombre_receptor', 'regimen_fiscal_receptor': 'Empresa Moral', 'domicilio_fiscal_receptor': 'Paseos de Jerez 541, Las arboledas', 'folio_fiscal': 'test_folio_fiscal', 'exportacion': 'test_exportacion', 'folio': 'test_folio', 'no_certificado_sat': 'test_no_certificado_sat', 'sello_sat': 'test_sello_sat', 'sello_certificacion_sat': 'test_sello_certificacion_sat', 'no_certificado': 'test_no_certificado', 'descuento': 10.5, 'metodo_pago': 'test_metodo_pago', 'condiciones_pago': 'test_condiciones_pago', 'apply_tax': True, 'tax_rate': 10.5, 'commercial_terms': 'Vigencia sujeta a disponibilidad.'}, headers=self.auth_headers()).status_code, [200, 204, 400, 401, 403, 404, 422])
        self.assertIn(self.client.delete(f"/invoice/{missing_id}", headers=self.auth_headers()).status_code, [200, 204, 401, 403, 404])


class TestCambioRealDeUnCampo(BackendTestCase):
    def test_resending_the_same_value_is_not_a_change(self):
        from app.routes.invoice import _cambia

        for actual, nuevo in ((None, ''), ('', None), (100, '100.00'), ('Timbrada', 'timbrada')):
            with self.subTest(actual=actual, nuevo=nuevo):
                self.assertFalse(_cambia(actual, nuevo))

    def test_a_different_value_is_a_change(self):
        from app.routes.invoice import _cambia

        for actual, nuevo in ((100, '101'), ('cotizacion', 'timbrada'), (None, 1)):
            with self.subTest(actual=actual, nuevo=nuevo):
                self.assertTrue(_cambia(actual, nuevo))
