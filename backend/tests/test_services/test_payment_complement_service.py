"""Timbrado real del complemento de pago (REP) de un abono.

Lo que estas pruebas fijan:

* un timbrado exitoso crea el comprobante tipo P, lo deja timbrado, y marca
  el abono como pagado -- con `id_payment_invoice` apuntando al nuevo;
* un rechazo definitivo del PAC revierte todo -- no debe quedar ni el
  comprobante tipo P ni la operacion de timbrado, a diferencia de
  `stamp_invoice` (que no crea la factura, solo la timbra);
* la misma llave de idempotencia no timbra dos veces;
* un abono con forma de pago '99' nunca deberia llegar aqui (register_payment
  ya lo rechaza), pero si llegara, se rechaza tambien en esta capa.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import CustomerSupplier, Invoice, Proyect, Status
from app.models.invoice_payment import InvoicePayment
from app.models.session import transaction_context
from app.models.stamping_operation import StampingOperation
from app.services.invoice_payment_service import register_payment
from app.services.payment_complement_service import stamp_payment_complement
from app.services.stamping import FakeStampingProvider, StampingResult
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}

PRINCIPAL = 10
CLIENT = 20
PPD = 50
UUID_PPD = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


class PaymentComplementTestCase(BackendTestCase):
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
            db.add(Invoice(
                id_invoice=PPD, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal=UUID_PPD,
                metodo_pago="PPD", forma_pago="99", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, total=Decimal("1000.00"), currency="MXN", created_by=1,
                rfc_receptor="BBB010101BB1", nombre_receptor="Cliente",
                regimen_fiscal_receptor="601", domicilio_fiscal_receptor="37100",
            ))

    def pay(self, amount, key):
        return register_payment(PPD, {"amount": amount, "payment_form": "03", "idempotency_key": key}, ACTOR)

    def payment_count(self):
        with transaction_context() as db:
            return db.query(InvoicePayment).count()

    def invoice_count(self):
        with transaction_context() as db:
            return db.query(Invoice).count()

    def operation_count(self):
        with transaction_context() as db:
            return db.query(StampingOperation).count()


class TestSuccessfulStamping(PaymentComplementTestCase):
    def test_stamps_the_complement_and_settles_the_payment(self):
        abono = self.pay("400.00", "pay-1")["payment"]
        operacion, created = stamp_payment_complement(
            abono["id_invoice_payment"], "stamp-1", ACTOR, provider=FakeStampingProvider(),
        )

        self.assertTrue(created)
        self.assertEqual("stamped", operacion["status"])

        with transaction_context() as db:
            renglon = db.get(InvoicePayment, abono["id_invoice_payment"])
            self.assertEqual("timbrado", renglon.status)
            self.assertIsNotNone(renglon.id_payment_invoice)

            complemento = db.get(Invoice, renglon.id_payment_invoice)
            self.assertEqual("P", complemento.tipo_de_comprobante)
            self.assertEqual("CP01", complemento.uso_cfdi)
            self.assertEqual(Decimal("0.00"), Decimal(str(complemento.total)))
            self.assertIsNotNone(complemento.folio_fiscal)
            self.assertEqual("timbrada", complemento.invoice_status)
            # El emisor viaja en vivo (mismo criterio que _load_draft).
            self.assertEqual("Mi Empresa", complemento.nombre_emisor)
            self.assertEqual("BBB010101BB1", complemento.rfc_receptor)

    def test_replaying_the_same_idempotency_key_does_not_stamp_twice(self):
        abono = self.pay("400.00", "pay-2")["payment"]
        stamp_payment_complement(abono["id_invoice_payment"], "stamp-2", ACTOR, provider=FakeStampingProvider())
        invoices_antes = self.invoice_count()

        operacion, created = stamp_payment_complement(
            abono["id_invoice_payment"], "stamp-2", ACTOR, provider=FakeStampingProvider(),
        )

        self.assertFalse(created)
        self.assertEqual(invoices_antes, self.invoice_count())


class TestRejectionRollsBackCompletely(PaymentComplementTestCase):
    def test_a_definitive_rejection_leaves_nothing_behind(self):
        """A diferencia de stamp_invoice: aqui la factura tipo P se crea
        especificamente para el intento, asi que un rechazo del PAC no debe
        dejar ni esa factura ni la operacion -- todo o nada."""
        abono = self.pay("400.00", "pay-3")["payment"]
        invoices_antes = self.invoice_count()
        operaciones_antes = self.operation_count()

        provider = FakeStampingProvider(result=StampingResult("rejected", error_code="rfc_invalido"))
        with self.assertRaises(AppError) as raised:
            stamp_payment_complement(abono["id_invoice_payment"], "stamp-3", ACTOR, provider=provider)

        self.assertEqual("invoice.payment_complement_rejected", raised.exception.message_key)
        self.assertEqual(invoices_antes, self.invoice_count())
        self.assertEqual(operaciones_antes, self.operation_count())
        with transaction_context() as db:
            renglon = db.get(InvoicePayment, abono["id_invoice_payment"])
            self.assertEqual("pendiente", renglon.status)
            self.assertIsNone(renglon.id_payment_invoice)


class TestUncertainResultIsKeptForReconciliation(PaymentComplementTestCase):
    def test_a_timeout_persists_the_attempt_without_settling_the_payment(self):
        abono = self.pay("400.00", "pay-4")["payment"]
        provider = FakeStampingProvider(result=StampingResult("uncertain", error_code="provider_timeout"))

        operacion, created = stamp_payment_complement(
            abono["id_invoice_payment"], "stamp-4", ACTOR, provider=provider,
        )

        self.assertTrue(created)
        self.assertEqual("uncertain", operacion["status"])
        with transaction_context() as db:
            renglon = db.get(InvoicePayment, abono["id_invoice_payment"])
            self.assertEqual("pendiente", renglon.status)
            self.assertIsNone(renglon.id_payment_invoice)
            complemento = db.get(Invoice, operacion["id_invoice"])
            self.assertIsNotNone(complemento)
            self.assertIsNone(complemento.folio_fiscal)


class TestGuards(PaymentComplementTestCase):
    def test_cannot_stamp_a_payment_whose_invoice_never_stamped(self):
        # Un abono ya no se registra sobre una factura sin timbrar: se simula uno anterior a
        # ese control, registrado con la factura timbrada y despues sin su folio.
        abono = self.pay("400.00", "pay-5")["payment"]
        with transaction_context() as db:
            db.query(Invoice).filter(Invoice.id_invoice == PPD).update({"folio_fiscal": None, "invoice_status": "pendiente"})

        with self.assertRaises(AppError) as raised:
            stamp_payment_complement(abono["id_invoice_payment"], "stamp-5", ACTOR, provider=FakeStampingProvider())

        self.assertEqual("errors.payment_requires_stamped_invoice", raised.exception.message_key)

    def test_cannot_stamp_the_same_payment_twice(self):
        abono = self.pay("400.00", "pay-6")["payment"]
        stamp_payment_complement(abono["id_invoice_payment"], "stamp-6", ACTOR, provider=FakeStampingProvider())

        with self.assertRaises(AppError) as raised:
            stamp_payment_complement(abono["id_invoice_payment"], "stamp-6-otra", ACTOR, provider=FakeStampingProvider())

        self.assertEqual("errors.payment_already_stamped", raised.exception.message_key)

    def test_rejects_an_undefined_payment_form_as_defense_in_depth(self):
        """register_payment ya rechaza forma_pago=99 al capturar -- este es
        un segundo cinturon, por si un abono llegara aqui sin haber pasado
        por ese guardia (ej. datos migrados de otro lado)."""
        abono = self.pay("400.00", "pay-7")["payment"]
        with transaction_context() as db:
            db.query(InvoicePayment).filter(
                InvoicePayment.id_invoice_payment == abono["id_invoice_payment"]
            ).update({"payment_form": "99"})

        with self.assertRaises(AppError) as raised:
            stamp_payment_complement(abono["id_invoice_payment"], "stamp-7", ACTOR, provider=FakeStampingProvider())

        self.assertEqual("errors.payment_form_cannot_be_undefined", raised.exception.message_key)


if __name__ == "__main__":
    unittest.main()
