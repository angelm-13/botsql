"""Almacenes en el inventario: existencia por ubicacion y traspasos.

El almacen es una ubicacion cuyo tipo esta marcado como almacen, y las demas
ubicaciones cuelgan de el. Estas pruebas fijan las tres invariantes del
modulo:

* la existencia de una ubicacion nunca queda negativa;
* `product.cantidad` es siempre la suma de las existencias por ubicacion;
* un traspaso mueve las dos puntas o ninguna.
"""

from __future__ import annotations

import unittest

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
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services.inventory_service import (
    apply_inventory_movement,
    list_inventory_movements,
    product_stock,
    reconcile_product_stock,
    resolve_warehouse,
    transfer_inventory,
    warehouse_stock,
)
from app.services.location_service import LocationService, location_tree
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}
OUTSIDER = {"id_user": 2, "id_proyect": 99}

# Tipos de ubicacion
TYPE_WAREHOUSE = 1
TYPE_ZONE = 2

# Ubicaciones: dos almacenes, y una zona con un rack dentro del primero.
CENTRAL = 1
NORTE = 2
ZONA_A = 3
RACK_A1 = 4

PRODUCT = 60


class WarehouseTestCase(BackendTestCase):
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
                LocationType(
                    id_location_type=TYPE_WAREHOUSE, location_type_description="Almacen",
                    is_warehouse=True, created_by=1,
                ),
                LocationType(
                    id_location_type=TYPE_ZONE, location_type_description="Zona",
                    is_warehouse=False, created_by=1,
                ),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Location(id_location=CENTRAL, id_location_type=TYPE_WAREHOUSE, location_description="Almacen Central", created_by=1),
                Location(id_location=NORTE, id_location_type=TYPE_WAREHOUSE, location_description="Almacen Norte", created_by=1),
                Material(id_material=1, material_description="Insumo", id_unit=1, id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add_all([
                Location(id_location=ZONA_A, id_location_type=TYPE_ZONE, location_description="Zona A", id_location_reference=CENTRAL, created_by=1),
            ])
            db.flush()
            db.add(Location(id_location=RACK_A1, id_location_type=TYPE_ZONE, location_description="Rack A-1", id_location_reference=ZONA_A, created_by=1))
            db.flush()
            db.add(Product(
                id_product=PRODUCT, id_invoice=50, id_location=CENTRAL, id_material=1,
                is_directly_related_to_product_service=False, cantidad=0, created_by=1,
            ))

    def receive(self, quantity, location, key, **extra):
        return apply_inventory_movement(PRODUCT, {
            "movement_type": "receive", "quantity": quantity,
            "id_location": location, "idempotency_key": key, **extra,
        }, ACTOR)

    def transfer(self, quantity, origin, target, key, **extra):
        payload = {
            "id_location_from": origin, "id_location_to": target,
            "quantity": quantity, "idempotency_key": key,
            "reason": extra.pop("reason", "Reabasto"),
            **extra,
        }
        return transfer_inventory(PRODUCT, payload, ACTOR)

    def stock_at(self, location):
        with transaction_context() as db:
            row = db.query(InventoryStock).filter_by(id_product=PRODUCT, id_location=location).first()
            return int(row.quantity) if row else None

    def product_total(self):
        with transaction_context() as db:
            return int(db.get(Product, PRODUCT).cantidad or 0)


class TestStockPerLocation(WarehouseTestCase):
    def test_the_same_product_holds_stock_in_two_warehouses(self):
        """El punto de toda la funcionalidad: antes solo cabia en un lugar."""
        self.receive(40, RACK_A1, "in-central")
        self.receive(15, NORTE, "in-norte")

        self.assertEqual(40, self.stock_at(RACK_A1))
        self.assertEqual(15, self.stock_at(NORTE))
        self.assertEqual(55, self.product_total())

    def test_product_total_is_always_the_sum_of_its_locations(self):
        self.receive(7, CENTRAL, "a")
        self.receive(3, NORTE, "b")
        self.receive(5, RACK_A1, "c")

        report = product_stock(PRODUCT, ACTOR)
        self.assertEqual(15, report["total"])
        self.assertEqual(15, report["stock_balance"])
        self.assertEqual(15, self.product_total())

    def test_movement_without_location_uses_the_product_location(self):
        """Compatibilidad: las llamadas anteriores no indicaban ubicacion."""
        movement, _ = apply_inventory_movement(PRODUCT, {
            "movement_type": "receive", "quantity": 9, "idempotency_key": "sin-ubicacion",
        }, ACTOR)

        self.assertEqual(CENTRAL, movement["id_location"])
        self.assertEqual(9, self.stock_at(CENTRAL))

    def test_issue_beyond_what_the_location_holds_is_refused(self):
        self.receive(5, RACK_A1, "in")

        with self.assertRaises(AppError) as raised:
            apply_inventory_movement(PRODUCT, {
                "movement_type": "issue", "quantity": 6,
                "id_location": RACK_A1, "idempotency_key": "out",
            }, ACTOR)

        self.assertEqual("errors.inventory_insufficient_stock", raised.exception.message_key)
        self.assertEqual(5, raised.exception.meta["available"])
        self.assertEqual(RACK_A1, raised.exception.meta["id_location"])
        self.assertEqual(5, self.stock_at(RACK_A1))

    def test_stock_in_one_warehouse_does_not_cover_an_issue_from_another(self):
        """Es el error que el saldo global unico ocultaba."""
        self.receive(50, NORTE, "in-norte")

        with self.assertRaises(AppError):
            apply_inventory_movement(PRODUCT, {
                "movement_type": "issue", "quantity": 1,
                "id_location": RACK_A1, "idempotency_key": "out-central",
            }, ACTOR)

    def test_ledger_records_where_the_movement_happened(self):
        movement, _ = self.receive(12, RACK_A1, "in")

        self.assertEqual(RACK_A1, movement["id_location"])
        self.assertEqual(12, movement["location_balance_after"])
        self.assertEqual(12, movement["balance_after"])

    def test_movement_in_a_missing_location_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.receive(1, 9999, "in-fantasma")

        self.assertEqual("errors.not_found", raised.exception.message_key)

    def test_seeds_existing_quantity_on_first_use(self):
        """Un producto dado de alta con cantidad y sin filas de existencia.

        La migracion sembro los que existian; uno creado despues por el alta
        normal llega con `cantidad` y sin existencia por ubicacion. Si no se
        sembrara, el primer movimiento perderia lo que ya habia.
        """
        with transaction_context() as db:
            db.get(Product, PRODUCT).cantidad = 30

        self.receive(5, CENTRAL, "in")

        self.assertEqual(35, self.stock_at(CENTRAL))
        self.assertEqual(35, self.product_total())


class TestTransfers(WarehouseTestCase):
    def test_transfer_moves_stock_between_warehouses(self):
        self.receive(40, RACK_A1, "in")

        result, created = self.transfer(25, RACK_A1, NORTE, "t1")

        self.assertTrue(created)
        self.assertEqual(15, self.stock_at(RACK_A1))
        self.assertEqual(25, self.stock_at(NORTE))
        # Un traspaso no crea ni destruye existencia.
        self.assertEqual(40, self.product_total())
        self.assertEqual(2, len(result["movements"]))

    def test_transfer_writes_a_paired_entry_in_the_ledger(self):
        self.receive(10, RACK_A1, "in")

        result, _ = self.transfer(4, RACK_A1, NORTE, "t1")
        outbound, inbound = result["movements"]

        self.assertEqual(-4, outbound["quantity_delta"])
        self.assertEqual(4, inbound["quantity_delta"])
        self.assertEqual(outbound["transfer_group"], inbound["transfer_group"])
        self.assertIsNotNone(outbound["transfer_group"])
        # Cada renglon apunta a la punta contraria.
        self.assertEqual(NORTE, outbound["id_location_target"])
        self.assertEqual(RACK_A1, inbound["id_location_target"])

    def test_transfer_beyond_available_stock_moves_nothing(self):
        self.receive(10, RACK_A1, "in")

        with self.assertRaises(AppError) as raised:
            self.transfer(11, RACK_A1, NORTE, "t1")

        self.assertEqual("errors.inventory_insufficient_stock", raised.exception.message_key)
        self.assertEqual(10, self.stock_at(RACK_A1))
        self.assertIsNone(self.stock_at(NORTE))
        with transaction_context() as db:
            self.assertEqual(0, db.query(InventoryLedger).filter_by(movement_type="transfer").count())

    def test_transfer_to_the_same_location_is_refused(self):
        self.receive(10, RACK_A1, "in")

        with self.assertRaises(AppError) as raised:
            self.transfer(1, RACK_A1, RACK_A1, "t1")

        self.assertEqual("errors.inventory_transfer_same_location", raised.exception.message_key)

    def test_transfer_requires_a_reason(self):
        self.receive(10, RACK_A1, "in")

        with self.assertRaises(AppError) as raised:
            self.transfer(1, RACK_A1, NORTE, "t1", reason="")

        self.assertEqual("errors.inventory_reason_required", raised.exception.message_key)

    def test_repeating_a_transfer_returns_the_same_pair(self):
        self.receive(10, RACK_A1, "in")
        first, created = self.transfer(4, RACK_A1, NORTE, "t1")
        second, repeated = self.transfer(4, RACK_A1, NORTE, "t1")

        self.assertTrue(created)
        self.assertFalse(repeated)
        self.assertEqual(
            [m["id_inventory_ledger"] for m in first["movements"]],
            [m["id_inventory_ledger"] for m in second["movements"]],
        )
        # No se movio dos veces.
        self.assertEqual(6, self.stock_at(RACK_A1))
        self.assertEqual(4, self.stock_at(NORTE))

    def test_transfer_cannot_be_requested_through_the_movement_endpoint(self):
        """Un traspaso por la via de movimientos dejaria media operacion."""
        with self.assertRaises(AppError) as raised:
            apply_inventory_movement(PRODUCT, {
                "movement_type": "transfer", "quantity": 1, "idempotency_key": "t",
            }, ACTOR)

        self.assertEqual("errors.inventory_transfer_requires_endpoint", raised.exception.message_key)

    def test_transfer_respects_project_isolation(self):
        self.receive(10, RACK_A1, "in")

        with self.assertRaises(AppError) as raised:
            transfer_inventory(PRODUCT, {
                "id_location_from": RACK_A1, "id_location_to": NORTE,
                "quantity": 1, "reason": "Ajeno", "idempotency_key": "t-ajeno",
            }, OUTSIDER)

        self.assertEqual("errors.permission_denied", raised.exception.message_key)


class TestWarehouseResolution(WarehouseTestCase):
    def test_walks_up_the_tree_to_find_the_warehouse(self):
        with transaction_context() as db:
            rack = db.get(Location, RACK_A1)
            self.assertEqual(CENTRAL, resolve_warehouse(db, rack).id_location)

    def test_a_warehouse_resolves_to_itself(self):
        with transaction_context() as db:
            self.assertEqual(NORTE, resolve_warehouse(db, db.get(Location, NORTE)).id_location)

    def test_a_branch_without_a_warehouse_resolves_to_nothing(self):
        """Datos anteriores a esta funcionalidad: ningun tipo era almacen."""
        with transaction_context() as db:
            db.get(LocationType, TYPE_WAREHOUSE).is_warehouse = False
        with transaction_context() as db:
            self.assertIsNone(resolve_warehouse(db, db.get(Location, RACK_A1)))

    def test_product_stock_reports_the_warehouse_of_each_location(self):
        self.receive(5, RACK_A1, "a")
        self.receive(3, NORTE, "b")

        by_location = {item["id_location"]: item for item in product_stock(PRODUCT, ACTOR)["items"]}

        self.assertEqual("Almacen Central", by_location[RACK_A1]["warehouse_description"])
        self.assertEqual("Almacen Norte", by_location[NORTE]["warehouse_description"])


class TestWarehouseQueries(WarehouseTestCase):
    def test_warehouse_stock_sums_every_location_beneath_it(self):
        self.receive(4, CENTRAL, "a")
        self.receive(6, ZONA_A, "b")
        self.receive(10, RACK_A1, "c")
        self.receive(99, NORTE, "d")

        central = warehouse_stock(CENTRAL, ACTOR)

        self.assertEqual(20, central["total"])
        self.assertTrue(central["is_warehouse"])
        self.assertEqual(3, central["locations_included"])

    def test_warehouse_stock_of_a_leaf_covers_only_itself(self):
        self.receive(10, RACK_A1, "a")
        self.receive(6, ZONA_A, "b")

        self.assertEqual(10, warehouse_stock(RACK_A1, ACTOR)["total"])

    def test_warehouse_stock_hides_other_projects_goods(self):
        """Un almacen puede guardar mercancia de varios proyectos."""
        self.receive(10, NORTE, "a")

        self.assertEqual(0, warehouse_stock(NORTE, OUTSIDER)["total"])

    def test_empty_locations_are_left_out(self):
        self.receive(5, RACK_A1, "a")

        items = warehouse_stock(CENTRAL, ACTOR)["items"]

        self.assertEqual([RACK_A1], [item["id_location"] for item in items])

    def test_movements_can_be_filtered_by_location(self):
        self.receive(5, RACK_A1, "a")
        self.receive(7, NORTE, "b")

        report = list_inventory_movements(PRODUCT, ACTOR, location_id=NORTE)

        self.assertEqual(1, report["total"])
        self.assertEqual(NORTE, report["items"][0]["id_location"])


class TestLocationTree(WarehouseTestCase):
    def test_tree_nests_locations_and_rolls_up_quantities(self):
        self.receive(4, CENTRAL, "a")
        self.receive(10, RACK_A1, "b")

        tree = location_tree(ACTOR)
        central = next(node for node in tree["items"] if node["id_location"] == CENTRAL)
        zona = central["children"][0]

        self.assertEqual(4, central["quantity"])
        self.assertEqual(14, central["total_quantity"])
        self.assertEqual(10, zona["total_quantity"])
        self.assertEqual("Rack A-1", zona["children"][0]["location_description"])

    def test_tree_marks_which_locations_are_warehouses(self):
        tree = location_tree(ACTOR)

        self.assertEqual(
            ["Almacen Central", "Almacen Norte"],
            sorted(node["location_description"] for node in tree["warehouses"]),
        )


class TestLocationHierarchyIntegrity(WarehouseTestCase):
    def test_a_location_cannot_be_its_own_parent(self):
        with self.assertRaises(AppError) as raised:
            LocationService.update(ZONA_A, {"id_location_reference": ZONA_A}, user_id=1)

        self.assertIn("self_reference", raised.exception.message_key)

    def test_a_cycle_is_refused(self):
        """Sin este guardian, recorrer el arbol se colgaba."""
        with self.assertRaises(AppError) as raised:
            LocationService.update(CENTRAL, {"id_location_reference": RACK_A1}, user_id=1)

        self.assertIn("cycle", raised.exception.message_key)

    def test_a_missing_parent_is_refused(self):
        with self.assertRaises(AppError):
            LocationService.update(ZONA_A, {"id_location_reference": 9999}, user_id=1)

    def test_moving_a_subtree_to_another_warehouse_is_allowed(self):
        LocationService.update(ZONA_A, {"id_location_reference": NORTE}, user_id=1)

        with transaction_context() as db:
            self.assertEqual(NORTE, resolve_warehouse(db, db.get(Location, RACK_A1)).id_location)

    def test_a_location_holding_stock_cannot_be_deleted(self):
        self.receive(3, RACK_A1, "a")

        with self.assertRaises(AppError) as raised:
            LocationService.delete(RACK_A1, user_id=1)

        self.assertEqual("errors.location_has_stock", raised.exception.message_key)

    def test_a_location_with_children_cannot_be_deleted(self):
        with self.assertRaises(AppError) as raised:
            LocationService.delete(ZONA_A, user_id=1)

        self.assertEqual("errors.location_has_children", raised.exception.message_key)

    def test_an_empty_leaf_can_be_deleted(self):
        self.assertTrue(LocationService.delete(RACK_A1, user_id=1))


class TestReconciliation(WarehouseTestCase):
    def test_reconciles_ledger_stock_and_product_total(self):
        self.receive(10, RACK_A1, "a")
        self.receive(5, NORTE, "b")
        self.transfer(4, RACK_A1, NORTE, "t")

        report = reconcile_product_stock(PRODUCT, ACTOR)

        self.assertTrue(report["is_reconciled"])
        self.assertEqual(15, report["ledger_balance"])
        self.assertEqual(15, report["stock_balance"])
        self.assertEqual(15, report["product_balance"])
        self.assertTrue(all(row["is_reconciled"] for row in report["by_location"]))

    def test_detects_a_location_altered_outside_the_flow(self):
        self.receive(10, RACK_A1, "a")
        with transaction_context() as db:
            db.query(InventoryStock).filter_by(id_product=PRODUCT, id_location=RACK_A1).first().quantity = 999

        report = reconcile_product_stock(PRODUCT, ACTOR)

        self.assertFalse(report["is_reconciled"])
        broken = [row for row in report["by_location"] if not row["is_reconciled"]]
        self.assertEqual([RACK_A1], [row["id_location"] for row in broken])
        self.assertEqual(989, broken[0]["difference"])


if __name__ == "__main__":
    unittest.main()
