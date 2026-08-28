"""Complemento de pago: abonos a una factura en parcialidades.

Lo que estas pruebas fijan:

* solo se abona una factura en parcialidades o diferida; en una de contado el
  cobro ya quedo acreditado con la factura misma;
* el saldo anterior y el insoluto los calcula el sistema, y encadenan bien
  entre parcialidades;
* un abono no puede exceder lo que se debe, ni repetirse;
* el comprobante de pago va en ceros, porque el importe vive en el complemento.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import CustomerSupplier, Invoice, Proyect, Status
from app.models.invoice_payment import InvoicePayment
from app.models.session import transaction_context
from app.services.invoice_payment_service import (
    build_payment_complement,
    invoice_statement,
    register_payment,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}
OUTSIDER = {"id_user": 2, "id_proyect": 99}

PRINCIPAL = 10
CLIENT = 20
PPD = 50   # factura en parcialidades
PUE = 51   # factura de contado
UUID_PPD = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


class PaymentTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=PRINCIPAL, name="Mi Empresa", tax_id="AAA010101AA1",
                    postal_code="37000", fiscal_type="601", type="supplier",
                    is_principal=True, id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=CLIENT, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1,
                ),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=30, id_customer_supplier=CLIENT, leader=1, proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])
            db.flush()
            db.add_all([
                Invoice(
                    id_invoice=PPD, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                    id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal=UUID_PPD,
                    metodo_pago="PPD", forma_pago="99", tax_certification_supplier=PRINCIPAL,
                    apply_tax=False, total=Decimal("1000.00"), currency="MXN", created_by=1,
                ),
                Invoice(
                    id_invoice=PUE, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                    id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal="11111111-1111-1111-1111-111111111111",
                    metodo_pago="PUE", forma_pago="03", tax_certification_supplier=PRINCIPAL,
                    apply_tax=False, total=Decimal("500.00"), currency="MXN", created_by=1,
                ),
            ])

    def pay(self, amount, key, **extra):
        payload = {
            "amount": amount,
            "payment_form": extra.pop("payment_form", "03"),
            "idempotency_key": key,
        }
        payload.update(extra)
        return register_payment(extra.pop("invoice", PPD) if "invoice" in extra else PPD, payload, ACTOR)

    def statement(self, invoice=PPD):
        return invoice_statement(invoice, ACTOR)

    def invoice_status(self, invoice=PPD):
        with transaction_context() as db:
            return db.get(Invoice, invoice).invoice_status


class TestPaymentRules(PaymentTestCase):
    def test_a_deferred_invoice_accepts_a_payment(self):
        resultado = self.pay("400.00", "p1")

        self.assertTrue(resultado["created"])
        abono = resultado["payment"]
        self.assertEqual(1, abono["instalment"])
        self.assertEqual("1000.00", abono["previous_balance"])
        self.assertEqual("400.00", abono["amount"])
        self.assertEqual("600.00", abono["outstanding_balance"])

    def test_a_cash_invoice_does_not_take_payments(self):
        """En PUE el cobro ya quedo acreditado con la factura misma."""
        with self.assertRaises(AppError) as raised:
            register_payment(PUE, {"amount": "100", "payment_form": "03", "idempotency_key": "x"}, ACTOR)

        self.assertEqual("errors.payment_requires_deferred_invoice", raised.exception.message_key)

    def test_the_balances_chain_between_instalments(self):
        self.pay("400.00", "p1")
        segundo = self.pay("350.00", "p2")

        self.assertEqual(2, segundo["payment"]["instalment"])
        self.assertEqual("600.00", segundo["payment"]["previous_balance"])
        self.assertEqual("250.00", segundo["payment"]["outstanding_balance"])

    def test_a_payment_cannot_exceed_what_is_owed(self):
        self.pay("900.00", "p1")

        with self.assertRaises(AppError) as raised:
            self.pay("200.00", "p2")

        self.assertEqual("errors.payment_exceeds_outstanding", raised.exception.message_key)
        self.assertEqual("100.00", raised.exception.meta["outstanding"])

    def test_a_settled_invoice_takes_no_more_payments(self):
        self.pay("1000.00", "p1")

        with self.assertRaises(AppError) as raised:
            self.pay("1.00", "p2")

        self.assertEqual("errors.payment_invoice_already_settled", raised.exception.message_key)

    def test_settling_it_marks_the_invoice_as_paid(self):
        self.pay("600.00", "p1")
        self.assertEqual("parcial", self.invoice_status())

        self.pay("400.00", "p2")

        self.assertEqual("pagada", self.invoice_status())

    def test_repeating_a_payment_does_not_charge_twice(self):
        primero = self.pay("400.00", "misma")
        segundo = self.pay("400.00", "misma")

        self.assertTrue(primero["created"])
        self.assertFalse(segundo["created"])
        self.assertEqual("600.00", self.statement()["outstanding"])

    def test_a_zero_or_negative_amount_is_refused(self):
        for amount in ("0", "-50"):
            with self.subTest(amount=amount), self.assertRaises(AppError) as raised:
                self.pay(amount, f"p-{amount}")
            self.assertEqual("errors.payment_amount_must_be_positive", raised.exception.message_key)

    def test_the_payment_form_must_be_in_the_catalog(self):
        with self.assertRaises(AppError) as raised:
            self.pay("100", "p1", payment_form="77")

        self.assertEqual("errors.payment_form_invalid", raised.exception.message_key)

    def test_a_payment_cannot_say_it_is_to_be_defined(self):
        """Un abono ya ocurrio; decir "por definir" seria contradecirlo."""
        with self.assertRaises(AppError) as raised:
            self.pay("100", "p1", payment_form="99")

        self.assertEqual("errors.payment_form_cannot_be_undefined", raised.exception.message_key)

    def test_project_isolation_is_respected(self):
        with self.assertRaises(AppError) as raised:
            register_payment(PPD, {"amount": "100", "payment_form": "03", "idempotency_key": "x"}, OUTSIDER)

        self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_the_instalment_number_is_unique_per_invoice(self):
        self.pay("100.00", "p1")
        self.pay("100.00", "p2")

        with transaction_context() as db:
            parcialidades = [
                fila.instalment for fila in
                db.query(InvoicePayment).filter_by(id_invoice=PPD).order_by(InvoicePayment.instalment).all()
            ]
        self.assertEqual([1, 2], parcialidades)


class TestStatement(PaymentTestCase):
    def test_it_reports_the_outstanding_balance(self):
        self.pay("300.00", "p1")

        estado = self.statement()

        self.assertEqual("1000.00", estado["total"])
        self.assertEqual("300.00", estado["paid"])
        self.assertEqual("700.00", estado["outstanding"])
        self.assertFalse(estado["is_settled"])
        self.assertEqual(2, estado["next_instalment"])
        self.assertTrue(estado["requires_payment_complement"])

    def test_a_cash_invoice_does_not_require_a_complement(self):
        estado = self.statement(PUE)

        self.assertFalse(estado["requires_payment_complement"])

    def test_it_lists_every_payment(self):
        self.pay("300.00", "p1")
        self.pay("200.00", "p2")

        estado = self.statement()

        self.assertEqual(2, len(estado["payments"]))
        self.assertEqual([1, 2], [p["instalment"] for p in estado["payments"]])


class TestPaymentComplement(PaymentTestCase):
    def test_the_payment_receipt_goes_in_zeros(self):
        """El importe vive en el complemento, no en el cuerpo del comprobante."""
        abono = self.pay("400.00", "p1")["payment"]

        complemento = build_payment_complement(abono["id_invoice_payment"], ACTOR)

        self.assertEqual("P", complemento["cfdi_type"])
        self.assertEqual("0", complemento["subtotal"])
        self.assertEqual("0", complemento["total"])
        self.assertEqual("CP01", complemento["cfdi_use"])

    def test_it_carries_the_related_document(self):
        abono = self.pay("400.00", "p1")["payment"]

        relacionado = build_payment_complement(abono["id_invoice_payment"], ACTOR)["related_document"]

        self.assertEqual(UUID_PPD, relacionado["uuid"])
        self.assertEqual(1, relacionado["instalment"])
        self.assertEqual("1000.00", relacionado["previous_balance"])
        self.assertEqual("400.00", relacionado["amount_paid"])
        self.assertEqual("600.00", relacionado["outstanding_balance"])
        self.assertEqual("PPD", relacionado["payment_method"])

    def test_it_carries_the_payment_data(self):
        abono = self.pay("400.00", "p1", operation_number="TRANSF-9911")["payment"]

        pago = build_payment_complement(abono["id_invoice_payment"], ACTOR)["payment"]

        self.assertEqual("03", pago["payment_form"])
        self.assertEqual("400.00", pago["amount"])
        self.assertEqual("TRANSF-9911", pago["operation_number"])

    def test_an_unstamped_invoice_has_no_complement(self):
        """El documento relacionado se identifica por su folio fiscal."""
        with transaction_context() as db:
            db.get(Invoice, PPD).folio_fiscal = None
        abono = self.pay("400.00", "p1")["payment"]

        with self.assertRaises(AppError) as raised:
            build_payment_complement(abono["id_invoice_payment"], ACTOR)

        self.assertEqual("errors.payment_requires_stamped_invoice", raised.exception.message_key)


if __name__ == "__main__":
    unittest.main()
