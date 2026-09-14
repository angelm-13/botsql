"""La ubicacion general: lo que esta en el almacen sin sitio propio.

Como se encontro
----------------
Se reporto que "no salian los productos en localizar". Con la base recien
levantada, medido:

    inventory_stock                        0 filas
    product.cantidad > 0                   1 producto
    location_type con is_warehouse = true  ninguno

Hay existencia -en `product.cantidad`- y no hay ni una fila de existencia por
ubicacion. La pantalla de Localizar lee las ubicaciones de un producto SOLO de
`inventory_stock`, asi que el producto sale con `locations: []`: se ve, pero no
dice donde esta, y desaparece en cuanto alguien filtra por almacen.

La causa estaba en dos sitios:

  * `_ensure_stock_seeded` se rendia cuando el producto no tenia ubicacion, que
    es el caso del material que el sistema original entrega sin decir en que
    rack esta;
  * solo corria dentro de un movimiento, asi que un producto recien dado de alta
    no tenia fila hasta que alguien lo moviera.

Lo que estas pruebas fijan
--------------------------
* **un producto recien creado ya tiene sitio.** Sin esperar un movimiento, que
  es lo que lo dejaba invisible;
* **sin ubicacion propia, cae en la general.** Es lo que hace que el material
  entregado sin sitio deje de ser invisible;
* **con ubicacion propia, se respeta la suya.** La general es para los que no
  tienen ninguna, no un destino que pise lo que alguien ya dijo;
* **no se toca un producto que ya tiene existencia repartida**, aunque los
  numeros no cuadren con `cantidad`: cuadrar esa diferencia es un conteo fisico,
  no una decision que este codigo pueda tomar;
* **sin ubicacion general declarada no se inventa una.** Sembrar en una
  ubicacion cualquiera seria decir que el material esta en un sitio donde nadie
  lo dejo.
"""

from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import (
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
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services.inventory_service import (
    sembrar_existencia_inicial,
    ubicacion_general,
)
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

EMPRESA, CLIENTE, PROYECTO, ESTATUS, COMPRA = 10, 20, 30, 40, 50
RACK, GENERAL, RETIRADA = 60, 61, 62
FAMILIA, MARCA, MATERIAL = 70, 71, 72


class BaseUbicacionGeneral(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMPRESA, name="Mi Empresa",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Almacen",
                             is_warehouse=True, created_by=1),
                ProductFamily(id_product_family=FAMILIA,
                              product_family_description="Obra", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            from app.models import Brand
            db.add(Brand(id_brand=MARCA, brand_description="Truper", created_by=1))
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Obra", created_by=1),
                Location(id_location=RACK, id_location_type=1,
                         location_description="Rack A-1", created_by=1),
                # La general. Es la que contesta "esta en el almacen" cuando
                # nadie dijo en que rack.
                Location(id_location=GENERAL, id_location_type=1,
                         location_description="Almacen general",
                         is_general_stock=True, created_by=1),
                # Una ubicacion dada de baja: el caso del producto que apunta a
                # un sitio que ya no existe.
                Location(id_location=RETIRADA, id_location_type=1,
                         location_description="Bodega vieja", created_by=1,
                         deletion_date=datetime(2026, 1, 1)),
            ])
            db.flush()
            sembrar_actor(db, id_proyect=PROYECTO, id_status=ESTATUS)
            db.add(Material(id_material=MATERIAL, material_description="Cemento",
                            id_unit=1, id_brand=MARCA,
                            id_product_family=FAMILIA, created_by=1))
            db.flush()
            db.add(Invoice(
                id_invoice=COMPRA, id_customer_supplier=EMPRESA,
                id_issuer_customer_supplier=CLIENTE, id_proyect=PROYECTO,
                id_status=ESTATUS, invoice_status="timbrada",
                tax_certification_supplier=CLIENTE, apply_tax=False,
                total=Decimal("0"), currency="MXN", created_by=1))

    def alta(self, *, id_location, cantidad=10, codigo="PRD-001", por_servicio=True):
        """Da de alta un producto por la via normal, con su cantidad."""
        from app.services.product_service import ProductService

        return ProductService.create({
            "id_invoice": COMPRA,
            "id_location": id_location,
            "id_material": MATERIAL,
            "is_directly_related_to_product_service": por_servicio,
            "product_code": codigo,
            "descripcion": "Cemento 50kg",
            "cantidad": cantidad,
        }, user_id=1)

    def sitios(self, id_product):
        """[(id_location, cantidad)] de ese producto."""
        with transaction_context() as db:
            return [
                (int(f.id_location), int(f.quantity))
                for f in db.scalars(select(InventoryStock).where(
                    InventoryStock.id_product == int(id_product))).all()
            ]


class TestUnProductoNuevoYaTieneSitio(BaseUbicacionGeneral):

    def test_a_new_product_gets_its_stock_row_without_any_movement(self):
        """Era lo que lo dejaba invisible: la fila llegaba con el primer movimiento."""
        creado = self.alta(id_location=RACK, cantidad=10)
        self.assertEqual([(RACK, 10)], self.sitios(creado["id_product"]))

    def test_its_own_location_is_respected(self):
        """La general es para los que no tienen ninguna, no un destino que pise."""
        creado = self.alta(id_location=RACK, cantidad=4, codigo="PRD-002")
        sitios = self.sitios(creado["id_product"])
        self.assertEqual([(RACK, 4)], sitios)
        self.assertNotIn(GENERAL, [s[0] for s in sitios])

    def test_a_product_without_quantity_gets_no_row(self):
        """Una fila en cero no dice nada y ensucia el conteo de sitios."""
        creado = self.alta(id_location=RACK, cantidad=0, codigo="PRD-003")
        self.assertEqual([], self.sitios(creado["id_product"]))


class TestLoQueNoTieneSitioCaeEnLaGeneral(BaseUbicacionGeneral):

    def test_the_general_location_is_the_one_marked_as_such(self):
        with transaction_context() as db:
            general = ubicacion_general(db)
        self.assertIsNotNone(general)
        self.assertEqual(GENERAL, general.id_location)

    def test_a_product_pointing_at_a_deleted_location_lands_in_the_general_one(self):
        """El caso del material entregado sin sitio: antes no entraba nunca."""
        creado = self.alta(id_location=RETIRADA, cantidad=6, codigo="PRD-004")
        self.assertEqual([(GENERAL, 6)], self.sitios(creado["id_product"]))

    def test_a_product_without_any_location_lands_in_the_general_one(self):
        """`product.id_location` es NOT NULL, asi que se prueba por el servicio."""
        with transaction_context() as db:
            db.add(Product(
                id_product=900, id_invoice=COMPRA, id_location=RACK,
                id_material=MATERIAL,
                is_directly_related_to_product_service=True,
                product_code="PRD-905", descripcion="Sin sitio", cantidad=12,
                created_by=1))
        with transaction_context() as db:
            producto = db.get(Product, 900)
            # Se simula lo que llega del sistema original: la referencia apunta
            # a un sitio que no se puede usar.
            producto.id_location = RETIRADA
            db.flush()
            sembrar_existencia_inicial(db, producto)

        self.assertEqual([(GENERAL, 12)], self.sitios(900))

    def test_the_general_location_is_a_warehouse(self):
        """Si no lo fuera, el arbol de almacenes seguiria sin mostrarla."""
        with transaction_context() as db:
            general = ubicacion_general(db)
            tipo = db.get(LocationType, general.id_location_type)
        self.assertTrue(tipo.is_warehouse)


class TestNoSePisaLoQueYaEstaba(BaseUbicacionGeneral):

    def test_a_product_with_stock_already_spread_is_left_alone(self):
        """Cuadrar la diferencia con `cantidad` es un conteo fisico, no esto."""
        creado = self.alta(id_location=RACK, cantidad=10, codigo="PRD-006")
        id_producto = creado["id_product"]

        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            # Alguien reparte la existencia a mano y `cantidad` queda desfasada.
            db.add(InventoryStock(id_product=id_producto, id_location=GENERAL,
                                  quantity=3, created_by=1))
            producto.cantidad = 99
            db.flush()

        with transaction_context() as db:
            self.assertIsNone(
                sembrar_existencia_inicial(db, db.get(Product, id_producto)),
                "sembro sobre un producto que ya tenia existencia repartida")

        self.assertEqual({(RACK, 10), (GENERAL, 3)}, set(self.sitios(id_producto)))

    def test_without_a_general_location_nothing_is_invented(self):
        """Sembrar en una cualquiera seria decir que esta donde nadie lo dejo."""
        with transaction_context() as db:
            db.get(Location, GENERAL).is_general_stock = False
            db.add(Product(
                id_product=901, id_invoice=COMPRA, id_location=RETIRADA,
                id_material=MATERIAL,
                is_directly_related_to_product_service=True,
                product_code="PRD-907", descripcion="Sin general", cantidad=5,
                created_by=1))

        with transaction_context() as db:
            self.assertIsNone(ubicacion_general(db))
            self.assertIsNone(
                sembrar_existencia_inicial(db, db.get(Product, 901)))

        self.assertEqual([], self.sitios(901))


class TestElProductoAparoceEnLocalizar(BaseUbicacionGeneral):
    """La comprobacion de punta a punta: es lo que se reporto roto."""

    def test_a_new_product_says_where_it_is(self):
        from app.services.inventory_trace_service import localizar

        creado = self.alta(id_location=RACK, cantidad=8, codigo="PRD-LOC")
        r = localizar("PRD-LOC", ACTOR)

        item = next(x for x in r["items"]
                    if x["id_product"] == creado["id_product"])
        self.assertEqual(
            ["Rack A-1"],
            [s["location_description"] for s in item["locations"]],
            "el producto sale sin ubicacion: es el bug que se reporto")
        self.assertEqual(8, item["locations"][0]["quantity"])

    def test_a_product_delivered_without_a_place_says_the_general_one(self):
        from app.services.inventory_trace_service import localizar

        creado = self.alta(id_location=RETIRADA, cantidad=5, codigo="PRD-GEN")
        r = localizar("PRD-GEN", ACTOR)

        item = next(x for x in r["items"]
                    if x["id_product"] == creado["id_product"])
        self.assertEqual(["Almacen general"],
                         [s["location_description"] for s in item["locations"]])

    def test_the_general_location_shows_up_as_a_warehouse_to_filter_by(self):
        """Sin esto el desplegable de almacenes salia vacio."""
        from app.services.inventory_trace_service import localizar

        self.alta(id_location=RETIRADA, cantidad=5, codigo="PRD-CAT")
        r = localizar("PRD-CAT", ACTOR)

        self.assertIn("Almacen general",
                      [w["location_description"] for w in r["catalog"]["warehouses"]])


if __name__ == "__main__":
    unittest.main()
