from __future__ import annotations

from datetime import date, timedelta

import jwt

from tests.conftest import BackendTestCase
from app.utils.auth import SECRET_KEY
from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status
from app.models.session import transaction_context


class QuotationConversionTestCase(BackendTestCase):
    """Convertir una cotizacion en factura via PATCH /invoice/convert-quotation/<id>.

    Antes de este fix, `moveQuotation()` en el frontend llamaba a
    `transitionQuotation` (un simple cambio de etiqueta) en vez de este
    endpoint -la cotizacion nunca se convertia de verdad en una factura
    lista para timbrar. Ver invoice.py::convert_quotation_invoice.
    """

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=910, name="Emisor Cotizacion", tax_id="QQQ010101QQQ", postal_code="37000", fiscal_type="601", type="supplier", id_user=1, created_by=1),
                CustomerSupplier(id_customer_supplier=920, name="Cliente Cotizacion", tax_id="WWW010101WWW", postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1),
                Proyect(id_proyect=930, id_customer_supplier=920, leader=1, proyect_description="Proyecto cotizacion", created_by=1),
                Status(id_status=940, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])

    def _token(self):
        return jwt.encode({"id_user": 1, "is_superuser": True}, SECRET_KEY, algorithm="HS256")

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}"}

    def _quotation(self, date_expiration=None, lines=(("pending", 1, "100"),), status="approved"):
        with transaction_context() as db:
            invoice = Invoice(
                id_customer_supplier=920,
                id_issuer_customer_supplier=910,
                id_proyect=930,
                tax_certification_supplier=910,
                id_status=940,
                created_by=1,
                apply_tax=False,
                tax_rate=0,
                invoice_status=status,
                date_expiration=date_expiration,
            )
            db.add(invoice)
            db.flush()
            invoice_id = invoice.id_invoice
            for authorization_status, quantity, gross_price in lines:
                db.add(InvoiceMaterialService(
                    id_invoice=invoice_id,
                    invoice_material_service_description="Servicio cotizado",
                    is_directly_related_to_product_service_creation=False,
                    id_authorized=1,
                    id_status=940,
                    id_buyer=1,
                    id_customer_supplier=920,
                    gross_price=gross_price,
                    quantity=quantity,
                    created_by=1,
                    line_type="custom",
                    tax_applicable=False,
                    authorization_status=authorization_status,
                ))
            return invoice_id

    def _invoice_status(self, invoice_id):
        with transaction_context() as db:
            return db.get(Invoice, invoice_id).invoice_status

    def _line_statuses(self, invoice_id):
        with transaction_context() as db:
            rows = db.query(InvoiceMaterialService).filter(InvoiceMaterialService.id_invoice == invoice_id).all()
            return [row.authorization_status for row in rows]

    def _convert(self, invoice_id):
        return self.client.patch(f"/invoice/convert-quotation/{invoice_id}", headers=self._headers())

    def test_pending_lines_are_authorized_automatically_on_conversion(self):
        invoice_id = self._quotation(lines=(("pending", 1, "100"), ("pending", 2, "50")))

        response = self._convert(invoice_id)

        self.assertEqual(200, response.status_code)
        body = self.json(response)
        self.assertEqual(2, body["authorized_lines_count"])
        self.assertEqual(0, body["excluded_lines_count"])
        self.assertEqual(["authorized", "authorized"], self._line_statuses(invoice_id))
        self.assertEqual("pendiente", self._invoice_status(invoice_id))

    def test_rejected_line_is_excluded_from_total_and_conversion(self):
        invoice_id = self._quotation(lines=(("pending", 1, "100"), ("rejected", 1, "500")))

        response = self._convert(invoice_id)

        self.assertEqual(200, response.status_code)
        body = self.json(response)
        self.assertEqual(1, body["authorized_lines_count"])
        self.assertEqual(1, body["excluded_lines_count"])
        self.assertEqual(100.0, float(body["total"]))

    def test_all_lines_rejected_blocks_conversion(self):
        invoice_id = self._quotation(lines=(("rejected", 1, "100"),))

        response = self._convert(invoice_id)

        self.assertEqual(400, response.status_code)
        self.assertEqual("validations.invoice.quotation_conversion.no_authorized_lines", self.json(response)["error_key"])
        self.assertEqual("approved", self._invoice_status(invoice_id))

    def test_converting_twice_fails_because_status_already_changed(self):
        invoice_id = self._quotation()
        first = self._convert(invoice_id)
        self.assertEqual(200, first.status_code)

        second = self._convert(invoice_id)

        self.assertEqual(400, second.status_code)
        self.assertEqual("validations.invoice.quotation_conversion.invalid_status", self.json(second)["error_key"])

    def test_expired_quotation_cannot_be_converted(self):
        invoice_id = self._quotation(date_expiration=date.today() - timedelta(days=1))

        response = self._convert(invoice_id)

        self.assertEqual(409, response.status_code)
        self.assertEqual("validations.invoice.quotation_expired", self.json(response)["error_key"])
        self.assertEqual("approved", self._invoice_status(invoice_id))

    def test_expiration_today_is_not_expired_yet(self):
        invoice_id = self._quotation(date_expiration=date.today())

        response = self._convert(invoice_id)

        self.assertEqual(200, response.status_code)

    def test_a_quotation_still_in_draft_cannot_be_converted(self):
        """Regresion real: el tablero (QuotationWorkflowBoard) solo deja pasar
        a "converted" desde "approved" -una cotizacion recien creada, en
        "draft", nunca debe poder saltarse la revision.
        """
        invoice_id = self._quotation(status="draft")

        response = self._convert(invoice_id)

        self.assertEqual(400, response.status_code)
        self.assertEqual("validations.invoice.quotation_conversion.invalid_status", self.json(response)["error_key"])

    def test_a_legacy_quotation_with_the_old_literal_status_can_still_convert(self):
        """Compatibilidad con datos de antes de que existiera el tablero,
        donde el estado se guardaba tal cual como 'Cotizacion'.
        """
        invoice_id = self._quotation(status="Cotizacion")

        response = self._convert(invoice_id)

        self.assertEqual(200, response.status_code)


class QuotationOptionsTestCase(BackendTestCase):
    """GET /invoice/quotation_options -- selector de "Cotizacion" al crear o
    editar un proyecto.

    Antes de este endpoint el formulario pedia el id interno de la factura a
    mano, sin lista: cualquier numero que no fuera el id real de una
    cotizacion existente respondia `errors.not_found` al guardar el
    proyecto.
    """

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=810, name="Cliente Selector", tax_id="SEL010101SEL", postal_code="37000", fiscal_type="601", type="client", id_user=1, created_by=1),
                Proyect(id_proyect=820, id_customer_supplier=810, leader=1, proyect_description="Proyecto selector", created_by=1),
                Status(id_status=950, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])
            comunes = dict(
                id_customer_supplier=810, id_issuer_customer_supplier=810,
                tax_certification_supplier=1, id_status=950,
                apply_tax=False, tax_rate=0, created_by=1,
            )
            db.add_all([
                Invoice(folio="COT-0001", invoice_status="draft", **comunes),
                Invoice(folio="COT-0002", invoice_status="converted", **comunes),
                # Una factura de verdad -no una cotizacion- no debe aparecer.
                Invoice(folio="FAC-0001", invoice_status="timbrada", **comunes),
            ])

    def _token(self, **claims):
        payload = {"id_user": 1, "id_proyect": 820, **claims}
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    def test_it_only_lists_quotations_not_regular_invoices(self):
        response = self.client.get(
            "/invoice/quotation_options",
            headers={"Authorization": f"Bearer {self._token(is_superuser=True)}"},
        )

        self.assertEqual(200, response.status_code)
        folios = {row["folio"] for row in self.json(response)}
        self.assertEqual({"COT-0001", "COT-0002"}, folios)

    def test_a_role_that_only_reads_proyect_can_use_it(self):
        """No exige el permiso completo de `invoice` -- ver el docstring de
        `list_quotation_options` en invoice.py."""
        from app.models.entity_permission import EntityPermission

        with transaction_context() as db:
            db.add(EntityPermission(id_permission=930, entity_name="proyect", scope_read=4, created_by=1))

        response = self.client.get(
            "/invoice/quotation_options",
            headers={"Authorization": f"Bearer {self._token(id_permission=930)}"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(self.json(response)))
