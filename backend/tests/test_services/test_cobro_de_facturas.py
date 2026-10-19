"""El cobro de una factura PPD: tres controles que la auditoria de ventas (2026-10-19) encontro abiertos.

Lo que estas pruebas fijan
--------------------------
* **no se abona una factura sin timbrar.** Antes se aceptaba el abono sobre una factura
  `pendiente`, que quedaba `pagada` sin folio fiscal: `stamp_invoice` no timbra una
  `pagada`, asi que el cobro quedaba registrado contra un CFDI que ya no podia existir;
* **el saldo descuenta las notas de credito vigentes.** Antes se podia cobrar el total de
  una factura ya acreditada por completo. La cadena fiscal de los abonos (saldo anterior
  e insoluto del complemento de pago) NO cambia: sigue siendo el total del CFDI menos
  lo pagado, que es lo que el SAT valida;
* **la fecha del pago no puede ser futura** (con un dia de holgura por el huso horario):
  va al complemento de pago.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Invoice
from app.models.invoice_payment import InvoicePayment
from app.models.session import transaction_context
from app.services.invoice_payment_service import invoice_statement, register_payment
from app.utils.errors import AppError
from tests.test_services import test_invoice_credit_notes as notas
from tests.test_services import test_invoice_payments as pagos


def _sin_timbrar(id_invoice):
    with transaction_context() as db:
        factura = db.get(Invoice, id_invoice)
        factura.folio_fiscal = None
        factura.invoice_status = "pendiente"


def _a_plazos(id_invoice):
    with transaction_context() as db:
        db.get(Invoice, id_invoice).metodo_pago = "PPD"


class TestSoloSeAbonaLoTimbrado(pagos.PaymentTestCase):

    def test_an_unstamped_deferred_invoice_does_not_take_payments(self):
        _sin_timbrar(pagos.PPD)

        with self.assertRaises(AppError) as caja:
            self.pay("400.00", "p-sin-timbre")

        self.assertEqual("errors.payment_requires_stamped_invoice", caja.exception.message_key)
        self.assertEqual(409, caja.exception.status_code)
        # La factura sigue como estaba: se puede timbrar, que es lo que le falta.
        self.assertEqual("pendiente", self.invoice_status())
        with transaction_context() as db:
            self.assertEqual([], db.query(InvoicePayment).all())

    def test_a_stamped_one_still_takes_them(self):
        resultado = self.pay("400.00", "p-timbrada")

        self.assertTrue(resultado["created"])


class TestElSaldoDescuentaLasNotasDeCredito(notas.CreditNoteTestCase):

    def setUp(self):
        super().setUp()
        _a_plazos(notas.SALE)

    def pagar(self, monto, clave):
        return register_payment(notas.SALE, {
            "amount": monto, "payment_form": "03", "idempotency_key": clave}, notas.ACTOR)

    def estado(self):
        return invoice_statement(notas.SALE, notas.ACTOR)

    def test_the_statement_shows_what_was_credited_and_the_net_balance(self):
        self.note(relation_type="01", unit_price="1000", quantity=1, key="nc-total")

        estado = self.estado()

        self.assertEqual("1160.00", estado["total"])
        self.assertEqual("1160.00", estado["credited"])
        self.assertEqual("0.00", estado["outstanding"])
        self.assertTrue(estado["is_settled"])

    def test_a_fully_credited_invoice_takes_no_payment(self):
        self.note(relation_type="01", unit_price="1000", quantity=1, key="nc-total")

        with self.assertRaises(AppError) as caja:
            self.pagar("1160.00", "p-total")

        self.assertEqual("errors.payment_invoice_already_settled", caja.exception.message_key)

    def test_a_partial_credit_limits_the_payment(self):
        nota = self.note(relation_type="01", unit_price="500", quantity=1, key="nc-medio")
        acreditado = nota["credit_note"]["total"]
        self.assertEqual(580.0, float(acreditado))

        with self.assertRaises(AppError) as caja:
            self.pagar("600.00", "p-de-mas")
        self.assertEqual("errors.payment_exceeds_outstanding", caja.exception.message_key)
        self.assertEqual("580.00", caja.exception.meta["outstanding"])

        resultado = self.pagar("580.00", "p-justo")
        self.assertTrue(resultado["created"])

    def test_the_invoice_is_settled_when_the_net_balance_reaches_zero(self):
        self.note(relation_type="01", unit_price="500", quantity=1, key="nc-medio")

        self.pagar("580.00", "p-justo")

        with transaction_context() as db:
            self.assertEqual("pagada", db.get(Invoice, notas.SALE).invoice_status)
        self.assertTrue(self.estado()["is_settled"])

    def test_the_fiscal_chain_of_the_payment_complement_is_not_changed(self):
        """El saldo anterior del complemento es el del CFDI, no el neto: eso lo valida el SAT."""
        self.note(relation_type="01", unit_price="500", quantity=1, key="nc-medio")

        abono = self.pagar("100.00", "p-uno")["payment"]

        self.assertEqual("1160.00", abono["previous_balance"])
        self.assertEqual("1060.00", abono["outstanding_balance"])


class TestLaFechaDelPago(pagos.PaymentTestCase):

    def test_a_payment_dated_in_the_future_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self.pay("100.00", "p-futuro", paid_at="2099-01-01T00:00:00")

        self.assertEqual("errors.invalid_field", caja.exception.message_key)
        self.assertEqual("paid_at", caja.exception.meta["field"])
        with transaction_context() as db:
            self.assertEqual([], db.query(InvoicePayment).all())

    def test_a_few_hours_ahead_is_tolerated_for_the_time_zone(self):
        manana = (datetime.now(timezone.utc) + timedelta(hours=12)).replace(tzinfo=None)

        resultado = self.pay("100.00", "p-huso", paid_at=manana.isoformat())

        self.assertTrue(resultado["created"])

    def test_a_past_date_is_accepted(self):
        resultado = self.pay("100.00", "p-pasado", paid_at="2026-01-15T10:00:00")

        self.assertTrue(resultado["created"])
