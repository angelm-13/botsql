"""Enlace entre facturar y mover existencias.

Lo que estas pruebas fijan, en orden de importancia:

* una venta saca del almacen y una compra lo surte, y el sentido lo decide la
  direccion de la factura, no quien llama;
* repetir la operacion no vuelve a mover;
* si una partida no alcanza en una venta, ninguna se aplica;
* una factura sin clasificar no mueve nada;
* lo que no se puede mover se reporta, nunca se redondea a la callada;
* **una factura que documenta una venta ya cobrada no vuelve a mover.** Es la
  unica de la lista que no protege contra un error de captura sino contra un
  descuadre silencioso: la venta de mostrador descuenta al cobrarse y la factura
  descontaria otra vez, sacando el producto dos veces por haberse vendido una.
  Las dos operaciones son correctas por separado, asi que nada avisaria.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from sqlalchemy import select

from app.models import (
    Brand,
    CustomerSupplier,
    Invoice,
    InvoiceMaterialService,
    Location,
    LocationType,
    Material,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement, reconcile_product_stock
from app.services.invoice_inventory_service import (
    _movement_key,
    _whole_units,
    apply_invoice_to_inventory,
    preview_invoice_inventory,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}
OUTSIDER = {"id_user": 2, "id_proyect": 99}

PRINCIPAL = 10   # la empresa que emite: sus facturas son ventas
CLIENT = 20
WAREHOUSE = 1
RACK = 2
PRODUCT = 60
SALE = 50        # factura de venta
PURCHASE = 51    # factura de compra


class TestLaFacturaQueDocumentaUnaVenta(BackendTestCase):
    """Una partida CAUSA un movimiento o lo DOCUMENTA, nunca las dos.

    Una venta de mostrador ya movio el almacen cuando se cobro. La factura que
    se emite despues solo la respalda ante el SAT.
    """

    VENTA_DEL_POS = "V-20260101-00007"

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
                    postal_code="37100", fiscal_type="601", type="client",
                    id_user=1, created_by=1,
                ),
                LocationType(id_location_type=1, location_type_description="Almacen",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=30, id_customer_supplier=CLIENT, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=WAREHOUSE, id_location_type=1,
                         location_description="Mostrador", id_module="pos", created_by=1),
                Material(id_material=1, material_description="Agua", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(
                id_invoice=PURCHASE, id_customer_supplier=PRINCIPAL,
                id_issuer_customer_supplier=CLIENT, id_proyect=30, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=CLIENT,
                apply_tax=False, created_by=1,
            ))
            db.flush()
            db.add(Product(
                id_product=PRODUCT, id_invoice=PURCHASE, id_location=WAREHOUSE,
                id_material=1, is_directly_related_to_product_service=True,
                gross_price=Decimal("15.00"), created_by=1,
            ))
            db.flush()

        # Existencia inicial y la venta que la descuenta, tal como la escribe el
        # punto de venta al cobrar: reference_type 'sale' con el folio.
        apply_inventory_movement(PRODUCT, {
            "movement_type": "receive", "quantity": 10,
            "id_location": WAREHOUSE, "reference_type": "purchase",
            "reference_id": str(PURCHASE), "idempotency_key": "alta-inicial",
        }, ACTOR)
        with transaction_context() as db:
            from app.services.inventory_service import apply_movement_in_session
            apply_movement_in_session(
                db, PRODUCT, ACTOR, movement_type="issue", quantity_delta=-3,
                idempotency_key=f"pos-{self.VENTA_DEL_POS}",
                id_location=WAREHOUSE, reference_type="sale",
                reference_id=self.VENTA_DEL_POS,
                reason="Venta de mostrador", source_module="pos",
            )

    def _factura_de_la_venta(self, modulo="pos", referencia=None):
        with transaction_context() as db:
            db.add(Invoice(
                id_invoice=SALE, id_customer_supplier=CLIENT,
                id_issuer_customer_supplier=PRINCIPAL, id_proyect=30, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, created_by=1,
                source_module=modulo,
                source_reference=referencia if referencia is not None else self.VENTA_DEL_POS,
            ))
            db.flush()
            db.add(InvoiceMaterialService(
                id_invoice=SALE, id_product=PRODUCT, id_unit=1,
                invoice_material_service_description="Agua mineral",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1,
                id_customer_supplier=CLIENT, gross_price=Decimal("15.00"),
                quantity=Decimal("3"), created_by=1, line_type="product",
                tax_applicable=False, authorization_status="authorized",
            ))

    def _saldo(self):
        with transaction_context() as db:
            from sqlalchemy import func as f
            return int(db.scalar(
                select(f.coalesce(f.sum(InventoryLedger.quantity_delta), 0))
                .where(InventoryLedger.id_product == PRODUCT)
            ) or 0)

    def test_applying_it_does_not_discount_again(self):
        """La prueba central: el saldo no se mueve.

        Sin esto, el producto sale dos veces del almacen por haberse vendido una
        vez, y nada lo reporta porque las dos operaciones son correctas por
        separado.
        """
        self._factura_de_la_venta()
        antes = self._saldo()
        self.assertEqual(7, antes, "la venta ya descontó 3 de 10")

        resultado = apply_invoice_to_inventory(SALE, {}, ACTOR)

        self.assertEqual(antes, self._saldo(), "la factura volvio a descontar")
        self.assertTrue(resultado["documents_sale"])
        self.assertEqual("sale_already_moved_inventory", resultado["reason"])
        self.assertEqual(0, resultado["applied_lines"])

    def test_it_points_at_the_movement_the_sale_already_made(self):
        """No basta con no mover: hay que poder decir de donde salio la mercancia.

        Una factura que no puede senalar el movimiento que documenta obliga a
        buscarlo a mano el dia que alguien pregunte.
        """
        self._factura_de_la_venta()
        vista = preview_invoice_inventory(SALE, {}, ACTOR)

        self.assertEqual(1, vista["sale_movement_count"])
        movimiento = vista["sale_movements"][0]
        self.assertEqual(PRODUCT, movimiento["id_product"])
        self.assertEqual(-3, movimiento["quantity_delta"])
        self.assertEqual("issue", movimiento["movement_type"])
        self.assertFalse(vista["sale_movements_missing"])
        self.assertFalse(vista["can_apply"])

    def test_a_sale_without_a_trace_in_the_ledger_is_reported(self):
        """Si la venta no descontó, no se calla.

        Pasa de verdad: un producto del punto de venta sin enlace al almacen se
        vende sin descontar. Entonces la factura no mueve -por la regla- y el
        movimiento tampoco existe, asi que la mercancia salio del estante sin
        dejar rastro en ningun sitio. Eso hay que verlo.
        """
        self._factura_de_la_venta(referencia="V-20260101-99999")
        vista = preview_invoice_inventory(SALE, {}, ACTOR)

        self.assertEqual(0, vista["sale_movement_count"])
        self.assertTrue(vista["sale_movements_missing"])

    def test_an_invoice_without_an_origin_still_moves(self):
        """La regla no puede haber roto el caso normal.

        Una venta capturada en facturacion, sin modulo de origen, sigue siendo
        la causa del movimiento y tiene que descontar.
        """
        with transaction_context() as db:
            db.add(Invoice(
                id_invoice=SALE, id_customer_supplier=CLIENT,
                id_issuer_customer_supplier=PRINCIPAL, id_proyect=30, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, created_by=1,
            ))
            db.flush()
            db.add(InvoiceMaterialService(
                id_invoice=SALE, id_product=PRODUCT, id_unit=1,
                invoice_material_service_description="Agua mineral",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1,
                id_customer_supplier=CLIENT, gross_price=Decimal("15.00"),
                quantity=Decimal("2"), created_by=1, line_type="product",
                tax_applicable=False, authorization_status="authorized",
            ))

        antes = self._saldo()
        apply_invoice_to_inventory(SALE, {}, ACTOR)
        self.assertEqual(antes - 2, self._saldo(),
                         "una factura sin origen tiene que descontar")


class InvoiceInventoryTestCase(BackendTestCase):
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
                LocationType(
                    id_location_type=1, location_type_description="Almacen",
                    is_warehouse=True, created_by=1,
                ),
                LocationType(
                    id_location_type=2, location_type_description="Rack",
                    is_warehouse=False, created_by=1,
                ),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=30, id_customer_supplier=CLIENT, leader=1, proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=WAREHOUSE, id_location_type=1, location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Cemento", id_unit=1, id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Location(
                id_location=RACK, id_location_type=2, location_description="Rack A-1",
                id_location_reference=WAREHOUSE, created_by=1,
            ))
            db.flush()
            db.add_all([
                # La factura de compra que trajo el producto.
                Invoice(
                    id_invoice=PURCHASE, id_customer_supplier=PRINCIPAL,
                    id_issuer_customer_supplier=CLIENT, id_proyect=30, id_status=40,
                    invoice_status="timbrada", tax_certification_supplier=CLIENT,
                    apply_tax=False, created_by=1,
                ),
                # La factura de venta que se va a descargar.
                Invoice(
                    id_invoice=SALE, id_customer_supplier=CLIENT,
                    id_issuer_customer_supplier=PRINCIPAL, id_proyect=30, id_status=40,
                    invoice_status="timbrada", tax_certification_supplier=PRINCIPAL,
                    apply_tax=False, created_by=1,
                ),
            ])
            db.flush()
            db.add(Product(
                id_product=PRODUCT, id_invoice=PURCHASE, id_location=RACK, id_material=1,
                is_directly_related_to_product_service=False, cantidad=0, created_by=1,
            ))
            db.flush()
            db.add(InventoryStock(
                id_product=PRODUCT, id_location=RACK, quantity=20, created_by=1,
            ))

    def add_line(self, *, invoice=SALE, quantity="4", product=PRODUCT, authorized=True, line_id=None):
        with transaction_context() as db:
            line = InvoiceMaterialService(
                id_invoice_material_service=line_id,
                id_invoice=invoice,
                invoice_material_service_description="Cemento vendido",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                gross_price=Decimal("120"), quantity=Decimal(str(quantity)),
                line_type="product", tax_applicable=False,
                authorization_status="authorized" if authorized else "pending",
                id_product=product, created_by=1,
            )
            db.add(line)
            db.flush()
            return line.id_invoice_material_service

    def stock(self, location=RACK):
        with transaction_context() as db:
            row = db.query(InventoryStock).filter_by(id_product=PRODUCT, id_location=location).first()
            return int(row.quantity) if row else None

    def product_total(self):
        with transaction_context() as db:
            return int(db.get(Product, PRODUCT).cantidad or 0)


class TestDischarge(InvoiceInventoryTestCase):
    def test_selling_decrements_the_warehouse(self):
        """El enlace que faltaba: se facturaba y el almacen quedaba igual."""
        line = self.add_line(quantity="4")

        result = apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(1, result["applied_lines"])
        self.assertEqual(16, self.stock())
        self.assertEqual(16, self.product_total())
        movement = result["movements"][0]
        self.assertEqual(-4, movement["quantity_delta"])
        self.assertEqual("issue", movement["movement_type"])
        # El libro queda con el origen, que es lo que permite auditar la salida.
        self.assertEqual("invoice_line", movement["reference_type"])
        self.assertEqual(str(line), movement["reference_id"])

    def test_discharging_twice_does_not_decrement_twice(self):
        self.add_line(quantity="4")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        again = apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(0, again["applied_lines"])
        self.assertEqual(
            ["already_applied"], [row["skip_reason"] for row in again["skipped_lines"]]
        )
        self.assertEqual(16, self.stock())

    def test_a_line_that_does_not_fit_blocks_the_whole_invoice(self):
        """Descargar solo lo que alcanza dejaria la factura a medias."""
        self.add_line(quantity="2")
        self.add_line(quantity="9999")

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual("errors.inventory_insufficient_stock", raised.exception.message_key)
        # Ni la partida que si alcanzaba se aplico.
        self.assertEqual(20, self.stock())
        with transaction_context() as db:
            self.assertEqual(0, db.query(InventoryLedger).count())

    def test_a_purchase_invoice_increments_instead(self):
        """Una compra es el documento con el que la mercancia entra."""
        self.add_line(invoice=PURCHASE, quantity="4")

        result = apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)

        self.assertEqual(1, result["applied_lines"])
        self.assertEqual("compra", result["invoice_direction"])
        self.assertEqual("receive", result["movement_type"])
        self.assertEqual(24, self.stock())
        self.assertEqual(4, result["movements"][0]["quantity_delta"])

    def test_a_quotation_cannot_be_discharged(self):
        self.add_line(quantity="4")
        with transaction_context() as db:
            db.get(Invoice, SALE).invoice_status = "cotizacion"

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(
            "errors.invoice_inventory_status_not_allowed", raised.exception.message_key
        )

    def test_an_invoice_without_lines_is_reported(self):
        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {}, ACTOR)

        self.assertEqual("errors.invoice_inventory_no_lines", raised.exception.message_key)

    def test_lines_without_a_product_are_skipped(self):
        """Un servicio facturado no vive en el almacen."""
        self.add_line(quantity="1", product=None)

        result = apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(0, result["applied_lines"])
        self.assertEqual(
            ["line_without_product"], [row["skip_reason"] for row in result["skipped_lines"]]
        )
        self.assertEqual(20, self.stock())

    def test_a_fractional_quantity_is_reported_not_rounded(self):
        """La existencia se lleva en piezas; 2.5 kilos no se puede descontar.

        Redondear a la callada descuadraria el almacen sin dejar rastro.
        """
        self.add_line(quantity="2.5")

        result = apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(0, result["applied_lines"])
        self.assertEqual(
            ["quantity_not_whole_units"], [row["skip_reason"] for row in result["skipped_lines"]]
        )
        self.assertEqual(20, self.stock())

    def test_unauthorized_lines_are_left_out(self):
        self.add_line(quantity="4", authorized=False)

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {}, ACTOR)

        self.assertEqual("errors.invoice_inventory_no_lines", raised.exception.message_key)

    def test_the_discharge_location_can_be_chosen(self):
        self.add_line(quantity="4")
        with transaction_context() as db:
            db.add(InventoryStock(id_product=PRODUCT, id_location=WAREHOUSE, quantity=7, created_by=1))

        apply_invoice_to_inventory(SALE, {"id_location": WAREHOUSE}, ACTOR)

        self.assertEqual(3, self.stock(WAREHOUSE))
        self.assertEqual(20, self.stock(RACK))

    def test_without_a_location_it_uses_the_product_location(self):
        self.add_line(quantity="4")

        apply_invoice_to_inventory(SALE, {}, ACTOR)

        self.assertEqual(16, self.stock(RACK))

    def test_a_location_per_line_can_be_given(self):
        first = self.add_line(quantity="3")
        with transaction_context() as db:
            db.add(InventoryStock(id_product=PRODUCT, id_location=WAREHOUSE, quantity=9, created_by=1))

        apply_invoice_to_inventory(
            SALE, {"locations_by_line": {str(first): WAREHOUSE}}, ACTOR
        )

        self.assertEqual(6, self.stock(WAREHOUSE))
        self.assertEqual(20, self.stock(RACK))

    def test_project_isolation_is_respected(self):
        self.add_line(quantity="4")

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {"id_location": RACK}, OUTSIDER)

        self.assertEqual("errors.permission_denied", raised.exception.message_key)

    def test_a_missing_invoice_is_reported(self):
        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(9999, {}, ACTOR)

        self.assertEqual("errors.resource_not_found", raised.exception.message_key)


class TestPreview(InvoiceInventoryTestCase):
    def test_preview_reports_what_would_happen_without_touching_stock(self):
        self.add_line(quantity="4")

        report = preview_invoice_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual("venta", report["invoice_direction"])
        self.assertEqual("decrementa", report["effect"])
        self.assertTrue(report["can_apply"])
        self.assertEqual(1, report["pending_lines"])
        self.assertEqual(0, report["blocked_lines"])
        self.assertEqual(4, report["lines"][0]["units"])
        self.assertEqual(20, report["lines"][0]["available"])
        # Nada se movio.
        self.assertEqual(20, self.stock())

    def test_preview_flags_a_line_that_does_not_fit(self):
        self.add_line(quantity="9999")

        report = preview_invoice_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertFalse(report["can_apply"])
        self.assertEqual(1, report["blocked_lines"])
        self.assertEqual("insufficient_stock", report["lines"][0]["skip_reason"])

    def test_preview_of_a_purchase_says_it_increments(self):
        self.add_line(invoice=PURCHASE, quantity="4")

        report = preview_invoice_inventory(PURCHASE, {}, ACTOR)

        self.assertEqual("compra", report["invoice_direction"])
        self.assertEqual("incrementa", report["effect"])
        self.assertEqual("receive", report["movement_type"])
        self.assertTrue(report["can_apply"])

    def test_preview_reports_an_already_discharged_invoice(self):
        self.add_line(quantity="4")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        report = preview_invoice_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertTrue(report["fully_applied"])
        self.assertFalse(report["can_apply"])
        self.assertEqual(1, report["already_applied_lines"])


class TestHelpers(unittest.TestCase):
    def test_the_movement_key_is_stable_per_invoice_and_line(self):
        """De aqui sale la idempotencia: misma factura y partida, misma llave."""
        self.assertEqual("invoice-50-line-7", _movement_key(50, 7))
        self.assertEqual(_movement_key("50", "7"), _movement_key(50, 7))
        self.assertNotEqual(_movement_key(50, 7), _movement_key(50, 8))

    def test_whole_units_accepts_only_positive_integers(self):
        self.assertEqual(3, _whole_units("3"))
        self.assertEqual(3, _whole_units(Decimal("3.000000")))
        for value in ("2.5", "0", "-1", None, "abc", ""):
            with self.subTest(value=value):
                self.assertIsNone(_whole_units(value))


if __name__ == "__main__":
    unittest.main()


class TestPurchaseReceives(InvoiceInventoryTestCase):
    """El lado que faltaba: la compra surte el almacen."""

    def purchase(self, **overrides):
        return apply_invoice_to_inventory(PURCHASE, overrides, ACTOR)

    def test_a_purchase_does_not_need_existing_stock(self):
        """Es lo contrario de una venta: la mercancia esta entrando."""
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT).delete()
        self.add_line(invoice=PURCHASE, quantity="30")

        result = self.purchase(id_location=RACK)

        self.assertEqual(1, result["applied_lines"])
        self.assertEqual(30, self.stock())

    def test_a_huge_purchase_is_not_blocked(self):
        """En una compra no hay existencia que pueda faltar."""
        self.add_line(invoice=PURCHASE, quantity="9999")

        result = self.purchase(id_location=RACK)

        self.assertEqual(1, result["applied_lines"])
        self.assertEqual(10019, self.stock())

    def test_receiving_twice_does_not_increment_twice(self):
        self.add_line(invoice=PURCHASE, quantity="5")
        self.purchase(id_location=RACK)

        again = self.purchase(id_location=RACK)

        self.assertEqual(0, again["applied_lines"])
        self.assertEqual(25, self.stock())

    def test_a_purchase_can_receive_into_another_warehouse(self):
        self.add_line(invoice=PURCHASE, quantity="6")

        self.purchase(id_location=WAREHOUSE)

        self.assertEqual(6, self.stock(WAREHOUSE))
        self.assertEqual(20, self.stock(RACK))

    def test_the_ledger_says_it_came_from_a_purchase(self):
        line = self.add_line(invoice=PURCHASE, quantity="6")

        movement = self.purchase(id_location=RACK)["movements"][0]

        self.assertEqual("receive", movement["movement_type"])
        self.assertEqual("invoice_line", movement["reference_type"])
        self.assertEqual(str(line), movement["reference_id"])
        self.assertIn("compra", movement["reason"])

    def test_a_fractional_purchase_is_reported_not_rounded(self):
        self.add_line(invoice=PURCHASE, quantity="2.5")

        result = self.purchase(id_location=RACK)

        self.assertEqual(0, result["applied_lines"])
        self.assertEqual(
            ["quantity_not_whole_units"], [row["skip_reason"] for row in result["skipped_lines"]]
        )
        self.assertEqual(20, self.stock())

    def test_an_unclassified_invoice_moves_nothing(self):
        """Sin saber si entra o sale, moverlo seria una adivinanza."""
        with transaction_context() as db:
            # Emisor y receptor distintos de la empresa principal.
            db.get(Invoice, SALE).id_issuer_customer_supplier = CLIENT
            db.get(Invoice, SALE).id_customer_supplier = CLIENT
        self.add_line(quantity="4")

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual(
            "errors.invoice_inventory_direction_unknown", raised.exception.message_key
        )
        self.assertEqual(20, self.stock())

    def test_a_declared_direction_wins_over_the_deduced_one(self):
        """Las facturas cargadas por XML ya traen su direccion clasificada."""
        with transaction_context() as db:
            db.get(Invoice, SALE).invoice_direction = "compra"
        self.add_line(quantity="4")

        result = apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual("compra", result["invoice_direction"])
        self.assertEqual(24, self.stock())


class TestEndToEndProjectFlow(InvoiceInventoryTestCase):
    """El recorrido completo de un proyecto real, en un solo caso.

    Compra 100, se consumen 30 en la obra, se venden 40. Al final deben quedar
    30 en el almacen y el libro debe explicar de donde salio cada movimiento.
    Es la comprobacion que responde a la pregunta practica: al facturar, se
    actualiza el inventario solo?
    """

    def test_purchase_consumption_and_sale_leave_the_right_balance(self):
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT).delete()

        # 1) La compra surte el almacen.
        compra = self.add_line(invoice=PURCHASE, quantity="100")
        apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)
        self.assertEqual(100, self.stock(), "la compra debe sumar al almacen")

        # 2) Consumo en obra: salida directa, sin factura de por medio.
        apply_inventory_movement(PRODUCT, {
            "movement_type": "issue", "quantity": 30, "id_location": RACK,
            "idempotency_key": "obra-1", "reference_type": "project", "reference_id": "30",
        }, ACTOR)
        self.assertEqual(70, self.stock())

        # 3) La venta descuenta.
        venta = self.add_line(invoice=SALE, quantity="40")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)
        self.assertEqual(30, self.stock(), "100 - 30 - 40 = 30")

        # 4) El libro explica cada movimiento.
        with transaction_context() as db:
            movimientos = db.query(InventoryLedger).order_by(InventoryLedger.id_inventory_ledger).all()
            resumen = [(m.movement_type, m.quantity_delta, m.reference_type, m.reference_id) for m in movimientos]

        self.assertEqual([
            ("receive", 100, "invoice_line", str(compra)),
            ("issue", -30, "project", "30"),
            ("issue", -40, "invoice_line", str(venta)),
        ], resumen)

    def test_the_ledger_and_the_stock_agree_after_the_whole_flow(self):
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT).delete()
        self.add_line(invoice=PURCHASE, quantity="100")
        apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)
        self.add_line(invoice=SALE, quantity="40")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        report = reconcile_product_stock(PRODUCT, ACTOR)

        self.assertTrue(report["is_reconciled"])
        self.assertEqual(60, report["stock_balance"])
        self.assertEqual(60, report["ledger_balance"])

    def test_a_sale_cannot_take_more_than_the_purchase_brought_in(self):
        """El caso que el saldo global unico dejaba pasar."""
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT).delete()
        self.add_line(invoice=PURCHASE, quantity="10")
        apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)
        self.add_line(invoice=SALE, quantity="11")

        with self.assertRaises(AppError) as raised:
            apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        self.assertEqual("errors.inventory_insufficient_stock", raised.exception.message_key)
        self.assertEqual(10, self.stock(), "la existencia no se toca si la venta no cabe")

    def test_applying_a_purchase_twice_does_not_double_the_stock(self):
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT).delete()
        self.add_line(invoice=PURCHASE, quantity="100")

        apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)
        apply_invoice_to_inventory(PURCHASE, {"id_location": RACK}, ACTOR)

        self.assertEqual(100, self.stock())
