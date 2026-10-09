"""Movimientos de almacen: validacion, idempotencia, saldos y auditoria."""

from __future__ import annotations

import unittest

import jwt

from app.models import (
    Brand,
    CustomerSupplier,
    Invoice,
    Location,
    LocationType,
    Material,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.entity_permission import EntityPermission
from app.models.inventory_ledger import InventoryLedger
from app.models.session import transaction_context
from app.services.inventory_service import (
    _integer_quantity,
    apply_inventory_movement,
    list_inventory_movements,
    reconcile_product_stock,
)
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "id_permission": 900}
OUTSIDER = {"id_user": 2, "id_proyect": 99}


class TestQuantityValidation(unittest.TestCase):
    def test_accepts_positive_integer_quantity(self):
        self.assertEqual(_integer_quantity("3"), 3)

    def test_rejects_zero_negative_boolean_and_fractional_quantity(self):
        for value in (0, -1, True, "1.5", 1.5, None):
            with self.subTest(value=value), self.assertRaises(AppError):
                _integer_quantity(value)


class InventoryTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=20, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1,
                ),
                Proyect(id_proyect=30, id_customer_supplier=20, leader=1, proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
            ])
            db.flush()
            db.add_all([
                Invoice(
                    id_invoice=50, id_customer_supplier=20, id_issuer_customer_supplier=20,
                    id_proyect=30, id_status=40, invoice_status="pendiente",
                    tax_certification_supplier=20, apply_tax=False, created_by=1,
                ),
                LocationType(id_location_type=1, location_type_description="Almacen", created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Location(id_location=1, id_location_type=1, location_description="Almacen central", created_by=1),
                Material(
                    id_material=1, material_description="Insumo", id_unit=1, id_brand=1,
                    id_product_family=1, created_by=1,
                ),
            ])
            db.flush()
            db.add(self._product(60, 10))
            # Estas pruebas verifican las reglas del movimiento, no quien puede
            # hacerlo: se concede al actor la capacidad de ajustar para que el
            # caso bajo prueba sea la regla y no el permiso.
            db.add(EntityPermission(
                id_permission=900, entity_name="inventory_adjustment",
                scope_read=4, created_by=1,
            ))

    @staticmethod
    def _product(product_id, quantity):
        return Product(
            id_product=product_id, id_invoice=50, id_location=1, id_material=1,
            is_directly_related_to_product_service=False, cantidad=quantity, created_by=1,
        )

    def _move(self, **payload):
        return apply_inventory_movement(60, payload, ACTOR)

    def _balance(self):
        with transaction_context() as db:
            return db.get(Product, 60).cantidad


class TestInventoryMovements(InventoryTestCase):
    def test_receiving_and_issuing_move_the_balance_in_both_directions(self):
        movement, created = self._move(movement_type="receive", quantity=5, idempotency_key="in-1")
        self.assertTrue(created)
        self.assertEqual(movement["quantity_delta"], 5)
        self.assertEqual(movement["balance_after"], 15)
        self.assertEqual(self._balance(), 15)

        movement, _ = self._move(movement_type="issue", quantity=4, idempotency_key="out-1")
        self.assertEqual(movement["quantity_delta"], -4)
        self.assertEqual(movement["balance_after"], 11)
        self.assertEqual(self._balance(), 11)

    def test_repeating_an_idempotency_key_does_not_move_the_balance_again(self):
        first, created = self._move(movement_type="receive", quantity=5, idempotency_key="repeat")
        second, replayed = self._move(movement_type="receive", quantity=5, idempotency_key="repeat")

        self.assertTrue(created)
        self.assertFalse(replayed)
        self.assertEqual(first["id_inventory_ledger"], second["id_inventory_ledger"])
        self.assertEqual(self._balance(), 15)

    def test_reusing_a_key_on_another_product_is_a_conflict(self):
        with transaction_context() as db:
            db.add(self._product(61, 0))
        self._move(movement_type="receive", quantity=1, idempotency_key="shared")

        with self.assertRaises(AppError) as raised:
            apply_inventory_movement(61, {
                "movement_type": "receive", "quantity": 1, "idempotency_key": "shared",
            }, ACTOR)
        self.assertEqual(raised.exception.status_code, 409)

    def test_stock_cannot_go_negative(self):
        with self.assertRaises(AppError) as raised:
            self._move(movement_type="issue", quantity=11, idempotency_key="oversold")

        self.assertEqual(raised.exception.message_key, "errors.inventory_insufficient_stock")
        self.assertEqual(raised.exception.meta["available"], 10)
        self.assertEqual(self._balance(), 10)
        # Un movimiento rechazado no debe dejar rastro en el libro.
        with transaction_context() as db:
            self.assertEqual(db.query(InventoryLedger).count(), 0)

    def test_unknown_movement_type_is_rejected_with_the_allowed_list(self):
        with self.assertRaises(AppError) as raised:
            self._move(movement_type="teletransporte", quantity=1, idempotency_key="bad-type")
        self.assertIn("receive", raised.exception.meta["allowed"])

    def test_idempotency_key_is_mandatory(self):
        for key in ("", "   ", "x" * 101):
            with self.subTest(key=key), self.assertRaises(AppError):
                self._move(movement_type="receive", quantity=1, idempotency_key=key)

    def test_adjustment_requires_a_reason(self):
        with self.assertRaises(AppError) as raised:
            self._move(movement_type="adjustment", quantity_delta=-3, idempotency_key="adj-1")
        self.assertEqual(raised.exception.message_key, "errors.inventory_reason_required")

        movement, _ = self._move(
            movement_type="adjustment", quantity_delta=-3,
            reason="Conteo fisico de agosto", idempotency_key="adj-2",
        )
        self.assertEqual(movement["balance_after"], 7)
        self.assertEqual(movement["reason"], "Conteo fisico de agosto")

    def test_shrinkage_movements_also_require_a_reason(self):
        for movement_type in ("damage", "destroy", "loss"):
            with self.subTest(movement_type=movement_type), self.assertRaises(AppError):
                self._move(movement_type=movement_type, quantity=1, idempotency_key=f"no-reason-{movement_type}")

    def test_adjustment_of_zero_is_rejected(self):
        with self.assertRaises(AppError):
            self._move(movement_type="adjustment", quantity_delta=0, reason="Sin efecto", idempotency_key="adj-0")

    def test_reference_type_must_come_from_the_known_list(self):
        with self.assertRaises(AppError) as raised:
            self._move(
                movement_type="receive", quantity=1,
                reference_type="lo_que_sea", idempotency_key="ref-bad",
            )
        self.assertEqual(raised.exception.meta["field"], "reference_type")

        movement, _ = self._move(
            movement_type="receive", quantity=1,
            reference_type="Invoice", reference_id="50", idempotency_key="ref-ok",
        )
        self.assertEqual(movement["reference_type"], "invoice")
        self.assertEqual(movement["reference_id"], "50")

    def test_a_movement_outside_the_actor_project_is_denied(self):
        with self.assertRaises(AppError) as raised:
            apply_inventory_movement(60, {
                "movement_type": "receive", "quantity": 1, "idempotency_key": "foreign",
            }, OUTSIDER)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(self._balance(), 10)

    def test_the_ledger_is_append_only(self):
        self._move(movement_type="receive", quantity=1, idempotency_key="frozen")
        with self.assertRaises(ValueError):
            with transaction_context() as db:
                db.query(InventoryLedger).first().quantity_delta = 999
        with self.assertRaises(ValueError):
            with transaction_context() as db:
                db.delete(db.query(InventoryLedger).first())


class TestInventoryAudit(InventoryTestCase):
    def _seed(self):
        self._move(movement_type="receive", quantity=5, idempotency_key="a")
        self._move(movement_type="issue", quantity=2, idempotency_key="b")
        self._move(movement_type="loss", quantity=1, reason="Merma en traslado", idempotency_key="c")

    def test_movements_are_listed_newest_first_with_the_current_balance(self):
        self._seed()
        page = list_inventory_movements(60, ACTOR)

        self.assertEqual(page["total"], 3)
        self.assertEqual(page["balance"], 12)
        self.assertEqual([item["movement_type"] for item in page["items"]], ["loss", "issue", "receive"])
        self.assertEqual([item["balance_after"] for item in page["items"]], [12, 13, 15])

    def test_movements_can_be_filtered_and_paginated(self):
        self._seed()
        self.assertEqual(list_inventory_movements(60, ACTOR, movement_type="issue")["total"], 1)
        first_page = list_inventory_movements(60, ACTOR, per_page=2)
        self.assertEqual(len(first_page["items"]), 2)
        self.assertEqual(first_page["total"], 3)
        self.assertEqual(len(list_inventory_movements(60, ACTOR, page=2, per_page=2)["items"]), 1)

    def test_listing_is_scoped_to_the_actor_project(self):
        self._seed()
        with self.assertRaises(AppError) as raised:
            list_inventory_movements(60, OUTSIDER)
        self.assertEqual(raised.exception.status_code, 403)

    def test_reconciliation_confirms_the_balance_matches_the_ledger(self):
        self._seed()
        report = reconcile_product_stock(60, ACTOR)

        # El saldo inicial de 10 se cargo sin movimientos, asi que el libro
        # cuadra con la diferencia respecto a ese arranque.
        self.assertEqual(report["stock_balance"], 12)
        self.assertEqual(report["ledger_balance"], 2)
        self.assertEqual(report["difference"], 10)
        self.assertEqual(report["movements"], 3)
        self.assertEqual(report["last_movement_balance"], 12)

    def test_reconciliation_detects_a_balance_changed_outside_the_ledger(self):
        with transaction_context() as db:
            db.get(Product, 60).cantidad = 0
        self._move(movement_type="receive", quantity=4, idempotency_key="d")

        report = reconcile_product_stock(60, ACTOR)
        self.assertTrue(report["is_reconciled"])

        with transaction_context() as db:
            db.get(Product, 60).cantidad = 99
        report = reconcile_product_stock(60, ACTOR)
        self.assertFalse(report["is_reconciled"])
        self.assertEqual(report["difference"], 95)

    def test_audit_endpoints_are_reachable_over_http(self):
        self._seed()
        token = jwt.encode({"id_user": 1, "id_proyect": 30, "is_superuser": True}, SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        movements = self.client.get("/product/60/inventory-movements", headers=headers)
        self.assertEqual(movements.status_code, 200)
        self.assertEqual(movements.get_json()["total"], 3)

        reconciliation = self.client.get("/product/60/inventory-reconciliation", headers=headers)
        self.assertEqual(reconciliation.status_code, 200)
        self.assertEqual(reconciliation.get_json()["stock_balance"], 12)


if __name__ == "__main__":
    unittest.main()
