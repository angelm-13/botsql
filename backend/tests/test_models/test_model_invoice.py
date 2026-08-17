from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.invoice import Invoice


class TestInvoiceModel(BackendTestCase):
    def test_create_serialize_summary_delete_invoice(self):
        with transaction_context() as session:
            item = build_model(Invoice,
            date_emision='2026-01-15T12:00:00',
            date_expiration='2026-01-15T12:00:00',
            subtotal=10.5,
            tax=10.5,
            total=10.5,
            invoice_status='test state',
            payment_method='test payment_method',
            note='test notes',
            fiscal_reference='test fiscal_reference',
            serie_csd='test serie_csd',
            internationalization='exported',
            currency='test currency',
            type_exchange_rate=10.5,
            tax_certification_supplier=1,
            fiscal_certify_serie='test fiscal_certify_serie',
            certification_date='2026-01-15T12:00:00',
            cfdi_code='test cfdi_code',
            sat_code='test sat_code',
            sat_certification_code='test sat_certification_code',
            created_by=1,
            nombre_emisor='test_nombre_emisor',
            lugar_expedicion='test_lugar_expedicion',
            tipo_de_comprobante='factura',
            rfc_receptor='test_rfc_receptor',
            nombre_receptor='test_nombre_receptor',
            regimen_fiscal_receptor='Empresa Moral',
            domicilio_fiscal_receptor='Paseos de Jerez 541, Las arboledas',
            folio_fiscal='test_folio_fiscal',
            exportacion='test_exportacion',
            folio='test_folio',
            no_certificado_sat='test_no_certificado_sat',
            sello_sat='test_sello_sat',
            sello_certificacion_sat='test_sello_certificacion_sat',
            no_certificado='test_no_certificado',
            descuento=10.5,
            metodo_pago='test_metodo_pago',
            condiciones_pago='test_condiciones_pago',
            apply_tax=True,
            tax_rate=10.5,
            commercial_terms='Vigencia sujeta a disponibilidad.'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
