"""Dos huecos del flujo de facturacion que se timbraban o se cobraban mal.

Por que existe este archivo
---------------------------
Los dos son silenciosos: no dan error, dan un resultado creible y equivocado.

**El tipo de cambio se suponia 1.** `create_manual_invoice` rellenaba
`type_exchange_rate` con 1 cuando no venia capturado, para cualquier moneda. Al
elegir USD y no tocar el campo salia una factura de 116 USD "a un peso por
dolar", y el validador solo lo marcaba como AVISO: medido, `can_stamp = True`.
El SAT habria leido 116 pesos por algo que cuesta unos dos mil.

El arreglo va a la causa y no al sintoma: en moneda extranjera sin capturar, el
tipo de cambio queda en cero, que es como el validador ya lee "no capturado", y
el mismo validador lo convierte en error y pide el dato. Un 1 explicito se
respeta, porque una moneda a la par es raro pero legal.

**Cancelar una factura dejaba sus abonos vivos.** Medido: factura de 1160 en
parcialidades, abono de 500, se cancela -sin una queja- y el estado de cuenta
seguia diciendo "saldo 660" de una factura que fiscalmente ya no existe. Las
cuentas por cobrar contaban dinero de facturas canceladas.

No se bloquea la cancelacion porque no hay forma de anular un abono por
separado -no existe la ruta- y bloquear dejaria al usuario sin salida. Los
abonos son de la factura: si ella se cancela, ellos se dan de baja. El estado
`cancelado` ya existia y el servicio de pagos ya lo excluia del saldo; lo que
faltaba era que alguien lo marcara.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import (
    CustomerSupplier,
    Invoice,
    InventoryStock,
    Location,
    LocationType,
    Material,
    Brand,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.session import transaction_context
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

EMISOR, CLIENTE, PROYECTO, ESTATUS = 10, 20, 30, 40
NAVE, MATERIAL = 50, 52


class BaseFacturacion(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMISOR, name="EMISOR DEMO SA DE CV",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="CLIENTE DEMO SA DE CV",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1,
                              product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto demo", created_by=1),
                Location(id_location=NAVE, id_location_type=1,
                         location_description="Nave A", created_by=1),
                Material(id_material=MATERIAL, material_description="Generico",
                         id_unit=1, id_brand=1, id_product_family=1, created_by=1),
            ])

    def factura(self, **extra):
        from app.services.manual_invoice_service import create_manual_invoice

        carga = {
            "id_proyect": PROYECTO, "id_customer_supplier": CLIENTE,
            "id_issuer_customer_supplier": EMISOR, "id_status": ESTATUS,
            "forma_pago": "03", "metodo_pago": "PUE", "uso_cfdi": "G03",
            "tipo_de_comprobante": "I",
            "concepts": [{"description": "Servicio", "quantity": "1",
                          "unit_price": "100", "sat_product_key": "81111500",
                          "sat_unit_key": "E48"}],
        }
        carga.update(extra)
        return create_manual_invoice(carga, ACTOR)


class TestElTipoDeCambioNoSeSupone(BaseFacturacion):

    def _preflight(self, **extra):
        from app.services.stamping import preflight_invoice

        r = self.factura(**extra)
        return preflight_invoice(r["invoice"]["id_invoice"], ACTOR)

    def test_a_foreign_currency_without_a_rate_cannot_be_stamped(self):
        """Antes: can_stamp True con un aviso. El SAT habria leido pesos."""
        v = self._preflight(moneda="USD")
        self.assertFalse(v["can_stamp"])
        self.assertIn("invoice.exchange_rate_required_for_foreign_currency",
                      v["errors"])

    def test_a_foreign_currency_with_a_real_rate_is_fine(self):
        v = self._preflight(moneda="USD", type_exchange_rate="17.85")
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")

    def test_pesos_still_default_to_one(self):
        """Lo normal no puede haberse roto: en MXN el 1 se sigue poniendo."""
        r = self.factura()
        self.assertEqual(Decimal("1"),
                         Decimal(str(r["invoice"]["type_exchange_rate"])))
        v = self._preflight()
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")

    def test_an_explicit_rate_of_one_on_a_foreign_currency_is_respected(self):
        """Una moneda a la par es raro pero legal: se avisa, no se bloquea."""
        v = self._preflight(moneda="USD", type_exchange_rate="1")
        self.assertTrue(v["can_stamp"], f"errores: {v['errors']}")
        self.assertIn("invoice.exchange_rate_one_for_foreign_currency",
                      v["warnings"])


class TestCancelarUnaFacturaCancelaSusAbonos(BaseFacturacion):

    def _en_parcialidades(self):
        from app.services.stamping import FakeStampingProvider, stamp_invoice

        # PPD con forma 99 es lo que el CFDI exige para parcialidades; sin eso
        # la factura no acepta abonos.
        r = self.factura(metodo_pago="PPD", forma_pago="99",
                         concepts=[{"description": "Servicio", "quantity": "1",
                                    "unit_price": "1000",
                                    "sat_product_key": "81111500",
                                    "sat_unit_key": "E48"}])
        id_factura = r["invoice"]["id_invoice"]
        # Timbrado simulado: la cancelacion y los abonos exigen factura
        # timbrada, y timbrar de verdad no entra aqui.
        stamp_invoice(id_factura, "st-1", ACTOR, FakeStampingProvider())
        return id_factura

    def _abonar(self, id_factura, monto, llave):
        from app.services.invoice_payment_service import register_payment

        return register_payment(id_factura, {
            "amount": monto, "payment_form": "03", "currency": "MXN",
            "idempotency_key": llave}, ACTOR)

    def _estado(self, id_factura):
        from app.services.invoice_payment_service import invoice_statement

        return invoice_statement(id_factura, ACTOR)

    def _cancelar(self, id_factura):
        from app.services.invoice_cancellation_service import request_cancellation
        from app.services.stamping import FakeStampingProvider

        return request_cancellation(
            id_factura, {"motive": "02", "idempotency_key": "cn-1"},
            ACTOR, FakeStampingProvider())

    def test_the_preview_says_how_many_payments_it_would_cancel(self):
        """Enterarse despues no sirve: es una decision contable."""
        from app.services.invoice_cancellation_service import preview_cancellation

        id_factura = self._en_parcialidades()
        self.assertEqual(
            0, preview_cancellation(id_factura, {}, ACTOR)["payments_to_cancel"])

        self._abonar(id_factura, "500", "p1")
        self.assertEqual(
            1, preview_cancellation(id_factura, {}, ACTOR)["payments_to_cancel"])

    def test_cancelling_the_invoice_cancels_its_payments(self):
        id_factura = self._en_parcialidades()
        self._abonar(id_factura, "500", "p1")
        self.assertEqual(1, len(self._estado(id_factura)["payments"]))

        resultado = self._cancelar(id_factura)
        self.assertEqual(1, len(resultado["payments_cancelled"]))

        # El servicio de pagos ya excluia lo cancelado; ahora hay algo marcado.
        self.assertEqual([], self._estado(id_factura)["payments"])

    def test_the_receivable_does_not_keep_counting_a_cancelled_invoice(self):
        """Medido antes: "saldo 660" de una factura que ya no existe."""
        id_factura = self._en_parcialidades()
        self._abonar(id_factura, "500", "p1")
        antes = self._estado(id_factura)
        self.assertEqual(Decimal("660.00"), Decimal(str(antes["outstanding"])))

        self._cancelar(id_factura)

        with transaction_context() as db:
            self.assertEqual("cancelada", db.get(Invoice, id_factura).invoice_status)
        # Sin abonos vigentes, el estado de cuenta ya no reparte saldo de una
        # factura cancelada entre las cuentas por cobrar.
        self.assertEqual([], self._estado(id_factura)["payments"])

    def test_the_payments_are_not_deleted_only_marked(self):
        """Un abono cancelado es historia contable: se cobro y se revirtio."""
        from app.models.invoice_payment import InvoicePayment
        from app.services.invoice_payment_service import CANCELLED

        id_factura = self._en_parcialidades()
        self._abonar(id_factura, "500", "p1")
        self._cancelar(id_factura)

        with transaction_context() as db:
            from sqlalchemy import select

            filas = db.scalars(select(InvoicePayment).where(
                InvoicePayment.id_invoice == id_factura)).all()
        self.assertEqual(1, len(filas), "la fila no puede haberse borrado")
        self.assertEqual(CANCELLED, filas[0].status)
        self.assertIsNone(filas[0].deletion_date)

    def test_an_invoice_without_payments_cancels_exactly_as_before(self):
        """El caso normal no puede haberse roto."""
        id_factura = self._en_parcialidades()
        resultado = self._cancelar(id_factura)
        self.assertEqual([], resultado["payments_cancelled"])
        with transaction_context() as db:
            self.assertEqual("cancelada", db.get(Invoice, id_factura).invoice_status)


if __name__ == "__main__":
    unittest.main()
