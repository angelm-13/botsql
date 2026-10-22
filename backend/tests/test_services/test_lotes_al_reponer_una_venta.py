"""Cancelar una factura o acreditar una devolucion repone en los lotes de los que salio.

Hallazgo de la auditoria de inventario (2026-10-19), pendiente despues de corregir los
traspasos y las devoluciones de vale: la cancelacion de una factura y la nota de
credito por devolucion (relacion 03) reponen la existencia con un `return` sin lote, y
una entrada a un producto con lotes lo exige. La venta se sirve del lote que vence
primero; el regreso fallaba con `required_field lot_code`.

Lo que estas pruebas fijan
--------------------------
* cancelar una venta repone cada lote con lo que dio la venta;
* una nota de credito por devolucion repone en los lotes de los que salio la venta, y
  una segunda nota sobre la misma venta no vuelve a contar lo que la primera ya repuso;
* lo que la venta no explica -no tiene desglose- entra al lote de apertura;
* sin lotes, nada cambia.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models import InvoiceMaterialService
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_lot import NmInventoryLedgerLot
from app.models.session import transaction_context
from app.services.inventory_lot_service import (
    cuadre_de_lotes, encender_control_de_lotes, lotes_del_producto,
)
from app.services.inventory_service import apply_inventory_movement, apply_movement_in_session
from tests.test_services import test_invoice_cancellation as canc
from tests.test_services import test_invoice_credit_notes as notas

PRODUCT, RACK, SALE, CLIENT = canc.PRODUCT, canc.RACK, canc.SALE, canc.CLIENT
SUPER = {"id_user": 1, "id_proyect": 30, "is_superuser": True}


class ConLotes:
    """Un producto con lotes: la apertura (lo que ya habia) y L-A, que vence antes."""

    def preparar_lotes(self):
        encender_control_de_lotes(PRODUCT, {}, SUPER)
        apply_inventory_movement(PRODUCT, {
            "movement_type": "receive", "quantity": 20, "id_location": RACK,
            "reason": "Compra", "idempotency_key": "in-L-A",
            "lot": {"lot_code": "L-A", "expiry_date": "2027-03-01"}}, SUPER)

    def en_lotes(self):
        salida = {}
        for lote in lotes_del_producto(PRODUCT, SUPER)["items"]:
            for sitio in lote["locations"]:
                salida[(lote["lot_code"], sitio["id_location"])] = sitio["quantity"]
        return salida

    def assertCuadra(self):
        cuadre = cuadre_de_lotes(PRODUCT, SUPER)
        self.assertTrue(cuadre["balanced"], cuadre["differences"])


class TestLaCancelacionReponeEnSusLotes(ConLotes, canc.CancellationTestCase):

    def setUp(self):
        super().setUp()
        self.preparar_lotes()      # 50 de apertura + 20 de L-A

    def vender_y_aplicar(self, cantidad):
        self.add_line(quantity=str(cantidad))
        canc.apply_invoice_to_inventory(SALE, {"id_location": RACK}, canc.ACTOR)

    def test_cancelling_a_sale_puts_each_lot_back(self):
        # La venta de 25 toma 20 de L-A -vence antes- y 5 de la apertura.
        self.vender_y_aplicar(25)
        self.assertEqual({("APERTURA", RACK): 45}, self.en_lotes())

        resultado = self.cancel()

        self.assertEqual({("L-A", RACK): 20, ("APERTURA", RACK): 50}, self.en_lotes())
        self.assertEqual(70, self.stock())
        self.assertEqual(25, sum(m["quantity_delta"] for m in resultado["inventory"]))
        self.assertCuadra()

    def test_a_sale_without_breakdown_returns_to_the_opening_lot(self):
        self.vender_y_aplicar(25)
        with transaction_context() as db:
            # Se simula una salida anterior al control por lote: sin desglose.
            salida = db.scalars(select(InventoryLedger).where(
                InventoryLedger.movement_type == "issue")).first()
            for fila in db.scalars(select(NmInventoryLedgerLot).where(
                    NmInventoryLedgerLot.id_inventory_ledger == salida.id_inventory_ledger)):
                db.delete(fila)

        self.cancel()

        # Todo lo que no se pudo ligar a un lote entra a la apertura.
        self.assertEqual(70, self.stock())
        self.assertEqual({("APERTURA", RACK): 70}, self.en_lotes())
        self.assertCuadra()


class TestUnaNotaDeCreditoReponeEnSusLotes(ConLotes, notas.CreditNoteTestCase):

    def setUp(self):
        super().setUp()
        self.preparar_lotes()      # 30 de apertura + 20 de L-A

    def vender(self, cantidad):
        """La salida por la venta, como la escribe la factura: lleva su desglose por lote."""
        with transaction_context() as db:
            linea = InvoiceMaterialService(
                id_invoice=SALE, id_product=PRODUCT,
                invoice_material_service_description="Venta", quantity=cantidad,
                gross_price=Decimal("100.00"), authorization_status="authorized",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                line_type="product", tax_applicable=False,
                sat_product_key="01010101", sat_unit_key="H87", created_by=1)
            db.add(linea)
            db.flush()
            apply_movement_in_session(
                db, PRODUCT, notas.ACTOR, movement_type="issue", quantity_delta=-cantidad,
                idempotency_key=f"venta-{linea.id_invoice_material_service}",
                id_location=RACK, reference_type="invoice_line",
                reference_id=str(linea.id_invoice_material_service),
                reason="Salida por factura de venta")

    def devolver(self, cantidad, clave):
        return self.note(relation_type="03", quantity=cantidad, unit_price="10",
                         product=PRODUCT, key=clave)

    def test_a_return_goes_back_to_the_lots_the_sale_took_from(self):
        self.vender(25)     # 20 de L-A y 5 de la apertura
        self.assertEqual({("APERTURA", RACK): 25}, self.en_lotes())

        self.devolver(25, "nc-completa")

        self.assertEqual({("L-A", RACK): 20, ("APERTURA", RACK): 30}, self.en_lotes())
        self.assertCuadra()

    def test_a_second_note_does_not_count_again_what_the_first_one_returned(self):
        self.vender(10)     # todo de L-A
        self.assertEqual({("L-A", RACK): 10, ("APERTURA", RACK): 30}, self.en_lotes())

        self.devolver(4, "nc-1")
        self.devolver(6, "nc-2")

        self.assertEqual({("L-A", RACK): 20, ("APERTURA", RACK): 30}, self.en_lotes())
        self.assertCuadra()

    def test_a_discount_note_does_not_touch_the_lots(self):
        self.vender(10)
        antes = self.en_lotes()

        self.note(relation_type="01", quantity=10, unit_price="50", product=PRODUCT,
                  key="nc-desc")

        self.assertEqual(antes, self.en_lotes())

    def test_the_same_key_does_not_return_twice(self):
        self.vender(10)

        self.devolver(4, "misma")
        self.devolver(4, "misma")

        self.assertEqual({("L-A", RACK): 14, ("APERTURA", RACK): 30}, self.en_lotes())


class TestSinLotesTodoSigueIgual(notas.CreditNoteTestCase):

    def test_a_return_without_lots_is_a_single_movement_as_before(self):
        resultado = self.note(relation_type="03", quantity=5, unit_price="100", product=PRODUCT)

        self.assertEqual(1, len(resultado["inventory"]))
        self.assertEqual(35, self.stock())
        with transaction_context() as db:
            self.assertEqual([], db.scalars(select(NmInventoryLedgerLot)).all())
