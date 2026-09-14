"""Cancelacion de CFDI.

Lo que estas pruebas fijan:

* solo se cancela un comprobante timbrado;
* el motivo 01 exige el folio del comprobante que lo sustituye, y los demas
  motivos lo prohiben;
* una cancelacion no se pide dos veces, pero una rechazada si se puede volver
  a intentar;
* cancelar una venta devuelve al almacen lo que descontó, y solo despues de
  que el SAT confirma.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

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
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services.invoice_cancellation_service import (
    CANCELLATION_MOTIVES,
    preview_cancellation,
    refresh_cancellation,
    request_cancellation,
)
from app.services.invoice_inventory_service import apply_invoice_to_inventory
from app.services.stamping import CancellationResult, FakeStampingProvider
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}
OUTSIDER = {"id_user": 2, "id_proyect": 99}

PRINCIPAL = 10
CLIENT = 20
WAREHOUSE = 1
RACK = 2
PRODUCT = 60
SALE = 50
REPLACEMENT = 52
UUID_SALE = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
UUID_REPLACEMENT = "11111111-2222-3333-4444-555555555555"


class CancellationTestCase(BackendTestCase):
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
                LocationType(id_location_type=1, location_type_description="Almacen", is_warehouse=True, created_by=1),
                LocationType(id_location_type=2, location_type_description="Rack", is_warehouse=False, created_by=1),
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
            db.add(Location(id_location=RACK, id_location_type=2, location_description="Rack A-1", id_location_reference=WAREHOUSE, created_by=1))
            db.flush()
            db.add_all([
                Invoice(
                    id_invoice=SALE, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                    id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal=UUID_SALE,
                    tax_certification_supplier=PRINCIPAL, apply_tax=False, total=Decimal("1160.00"), created_by=1,
                ),
                Invoice(
                    id_invoice=REPLACEMENT, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                    id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal=UUID_REPLACEMENT,
                    tax_certification_supplier=PRINCIPAL, apply_tax=False, total=Decimal("1160.00"), created_by=1,
                ),
            ])
            db.flush()
            db.add(Product(
                id_product=PRODUCT, id_invoice=SALE, id_location=RACK, id_material=1,
                is_directly_related_to_product_service=False, cantidad=0, created_by=1,
            ))
            db.flush()
            db.add(InventoryStock(id_product=PRODUCT, id_location=RACK, quantity=50, created_by=1))

    def add_line(self, quantity="10", invoice=SALE):
        with transaction_context() as db:
            linea = InvoiceMaterialService(
                id_invoice=invoice,
                invoice_material_service_description="Cemento vendido",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                gross_price=Decimal("120"), quantity=Decimal(str(quantity)),
                line_type="product", tax_applicable=False, authorization_status="authorized",
                id_product=PRODUCT, created_by=1,
            )
            db.add(linea)
            db.flush()
            return linea.id_invoice_material_service

    def cancel(self, **payload):
        payload.setdefault("motive", "02")
        payload.setdefault("idempotency_key", "cancel-1")
        provider = payload.pop("provider", None) or FakeStampingProvider()
        return request_cancellation(SALE, payload, ACTOR, provider)

    def stock(self, location=RACK):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(id_product=PRODUCT, id_location=location).first()
            return int(fila.quantity) if fila else None

    def invoice_status(self, invoice=SALE):
        with transaction_context() as db:
            return db.get(Invoice, invoice).invoice_status


class TestCancellationRules(CancellationTestCase):
    def test_a_stamped_invoice_can_be_cancelled(self):
        resultado = self.cancel()

        self.assertTrue(resultado["created"])
        self.assertEqual("cancelado", resultado["cancellation"]["status"])
        self.assertEqual("02", resultado["cancellation"]["motive"])
        self.assertEqual("cancelada", self.invoice_status())

    def test_the_acknowledgement_is_kept(self):
        """Sin acuse no hay como demostrar ante una revision que se pidio."""
        resultado = self.cancel()

        self.assertIn(UUID_SALE, resultado["cancellation"]["acknowledgement"])

    def test_an_invoice_without_a_fiscal_folio_cannot_be_cancelled(self):
        with transaction_context() as db:
            db.get(Invoice, SALE).folio_fiscal = None

        with self.assertRaises(AppError) as raised:
            self.cancel()

        self.assertEqual("errors.cancellation_requires_stamped_invoice", raised.exception.message_key)

    def test_a_motive_outside_the_catalog_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.cancel(motive="99")

        self.assertEqual("errors.cancellation_motive_invalid", raised.exception.message_key)

    def test_motive_01_requires_the_replacement_folio(self):
        with self.assertRaises(AppError) as raised:
            self.cancel(motive="01")

        self.assertEqual("errors.cancellation_substitution_required", raised.exception.message_key)

    def test_motive_01_accepts_an_existing_replacement(self):
        resultado = self.cancel(motive="01", substitution_uuid=UUID_REPLACEMENT)

        self.assertEqual("cancelado", resultado["cancellation"]["status"])
        self.assertEqual(UUID_REPLACEMENT, resultado["cancellation"]["substitution_uuid"])

    def test_a_replacement_that_does_not_exist_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.cancel(motive="01", substitution_uuid="99999999-9999-9999-9999-999999999999")

        self.assertEqual("errors.cancellation_substitution_not_found", raised.exception.message_key)

    def test_an_invoice_cannot_replace_itself(self):
        with self.assertRaises(AppError) as raised:
            self.cancel(motive="01", substitution_uuid=UUID_SALE)

        self.assertEqual("errors.cancellation_substitution_is_same_invoice", raised.exception.message_key)

    def test_the_other_motives_reject_a_replacement(self):
        for motive in ("02", "03", "04"):
            with self.subTest(motive=motive), self.assertRaises(AppError) as raised:
                self.cancel(motive=motive, substitution_uuid=UUID_REPLACEMENT)
            self.assertEqual("errors.cancellation_substitution_not_allowed", raised.exception.message_key)

    def test_every_catalog_motive_is_accepted(self):
        self.assertEqual({"01", "02", "03", "04"}, set(CANCELLATION_MOTIVES))

    def test_a_cancelled_invoice_is_not_cancelled_again(self):
        self.cancel(idempotency_key="uno")

        with self.assertRaises(AppError) as raised:
            self.cancel(idempotency_key="dos")

        self.assertEqual("errors.cancellation_already_requested", raised.exception.message_key)

    def test_repeating_the_same_request_returns_the_first_one(self):
        primera = self.cancel(idempotency_key="misma")
        segunda = self.cancel(idempotency_key="misma")

        self.assertTrue(primera["created"])
        self.assertFalse(segunda["created"])
        self.assertEqual(
            primera["cancellation"]["id_invoice_cancellation"],
            segunda["cancellation"]["id_invoice_cancellation"],
        )

    def test_a_rejected_request_can_be_tried_again(self):
        """El SAT puede rechazar; entonces hay que poder volver a pedirlo."""
        rechazo = FakeStampingProvider(cancellation_result=CancellationResult("rechazado", error_code="receptor_no_acepto"))
        primera = request_cancellation(SALE, {"motive": "02", "idempotency_key": "r1"}, ACTOR, rechazo)
        self.assertEqual("rechazado", primera["cancellation"]["status"])
        self.assertEqual("timbrada", self.invoice_status())

        segunda = self.cancel(idempotency_key="r2", motive="03")

        self.assertEqual("cancelado", segunda["cancellation"]["status"])
        self.assertEqual("cancelada", self.invoice_status())

    def test_project_isolation_is_respected(self):
        with self.assertRaises(AppError) as raised:
            request_cancellation(SALE, {"motive": "02", "idempotency_key": "x"}, OUTSIDER, FakeStampingProvider())

        self.assertEqual("errors.permission_denied", raised.exception.message_key)


class TestCancellationReturnsStock(CancellationTestCase):
    def test_cancelling_a_sale_returns_what_it_took(self):
        self.add_line(quantity="10")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)
        self.assertEqual(40, self.stock())

        resultado = self.cancel()

        self.assertEqual(50, self.stock(), "lo vendido vuelve al almacen")
        self.assertEqual(1, len(resultado["inventory"]))
        self.assertEqual(10, resultado["inventory"][0]["quantity_delta"])
        self.assertEqual("return", resultado["inventory"][0]["movement_type"])

    def test_a_rejected_cancellation_does_not_return_stock(self):
        """Devolver antes de la confirmacion inflaria el inventario."""
        self.add_line(quantity="10")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)
        rechazo = FakeStampingProvider(cancellation_result=CancellationResult("rechazado"))

        resultado = request_cancellation(SALE, {"motive": "02", "idempotency_key": "r"}, ACTOR, rechazo)

        self.assertEqual([], resultado["inventory"])
        self.assertEqual(40, self.stock())

    def test_a_cancellation_in_progress_does_not_return_stock_either(self):
        self.add_line(quantity="10")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)
        espera = FakeStampingProvider(cancellation_result=CancellationResult("en_proceso"))

        resultado = request_cancellation(SALE, {"motive": "02", "idempotency_key": "p"}, ACTOR, espera)

        self.assertEqual("en_proceso", resultado["cancellation"]["status"])
        self.assertEqual(40, self.stock())
        self.assertEqual("timbrada", self.invoice_status())

    def test_stock_returns_when_the_sat_finally_confirms(self):
        self.add_line(quantity="10")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)
        espera = FakeStampingProvider(cancellation_result=CancellationResult("en_proceso"))
        pendiente = request_cancellation(SALE, {"motive": "02", "idempotency_key": "p"}, ACTOR, espera)

        confirma = FakeStampingProvider(cancellation_result=CancellationResult("cancelado", acknowledgement="ACUSE-OK"))
        resultado = refresh_cancellation(
            pendiente["cancellation"]["id_invoice_cancellation"], ACTOR, confirma
        )

        self.assertTrue(resultado["changed"])
        self.assertEqual("cancelado", resultado["cancellation"]["status"])
        self.assertEqual(50, self.stock())
        self.assertEqual("cancelada", self.invoice_status())

    def test_refreshing_a_resolved_request_changes_nothing(self):
        self.cancel()
        with transaction_context() as db:
            from app.models.invoice_cancellation import InvoiceCancellation
            solicitud = db.query(InvoiceCancellation).first()
            solicitud_id = solicitud.id_invoice_cancellation

        resultado = refresh_cancellation(solicitud_id, ACTOR, FakeStampingProvider())

        self.assertFalse(resultado["changed"])

    def test_an_invoice_without_inventory_movements_cancels_cleanly(self):
        resultado = self.cancel()

        self.assertEqual([], resultado["inventory"])
        self.assertEqual("cancelado", resultado["cancellation"]["status"])


class TestCancellationPreview(CancellationTestCase):
    def test_it_reports_what_would_be_returned(self):
        self.add_line(quantity="10")
        apply_invoice_to_inventory(SALE, {"id_location": RACK}, ACTOR)

        reporte = preview_cancellation(SALE, {}, ACTOR)

        self.assertTrue(reporte["can_request"])
        self.assertTrue(reporte["is_stamped"])
        self.assertEqual(1, reporte["inventory_movements_to_reverse"])
        self.assertEqual(["01"], reporte["requires_substitution"])

    def test_it_reports_an_invoice_that_cannot_be_cancelled(self):
        with transaction_context() as db:
            db.get(Invoice, SALE).folio_fiscal = None

        reporte = preview_cancellation(SALE, {}, ACTOR)

        self.assertFalse(reporte["can_request"])
        self.assertFalse(reporte["is_stamped"])

    def test_the_history_keeps_every_attempt(self):
        rechazo = FakeStampingProvider(cancellation_result=CancellationResult("rechazado"))
        request_cancellation(SALE, {"motive": "02", "idempotency_key": "r1"}, ACTOR, rechazo)
        self.cancel(idempotency_key="r2", motive="03")

        reporte = preview_cancellation(SALE, {}, ACTOR)

        self.assertEqual(2, len(reporte["history"]))
        self.assertFalse(reporte["can_request"])


if __name__ == "__main__":
    unittest.main()
