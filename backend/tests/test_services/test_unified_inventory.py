"""Un solo inventario para todos los proyectos.

El criterio anterior era un almacen por modulo, en tablas separadas. Ahora es
uno solo, y lo que distingue el origen de cada movimiento es una columna y no
una tabla.

Se eligio columna por lo que ya pasaba con tres cadenas de tablas: una consulta
que olvidaba una devolvia un saldo incompleto sin avisar. Con una sola tabla,
"cuanto hay" y "de donde vino" se contestan las dos, y ninguna se puede
responder a medias por descuido.

El punto de venta es el unico que no comparte tabla, porque corre contra su
propia base. Comparte saldo: su venta escribe el movimiento en el libro del
nucleo.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import (
    Brand, CustomerSupplier, Invoice, Location, LocationType, Material,
    PosProductLink, Product, ProductFamily, Proyect, Status, Unit,
)
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services import inventory_service as inventario
from app.services.pos_inventory_bridge import enlazar, reflejar_venta
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}
PRINCIPAL, CLIENTE, PROYECTO, FACTURA = 10, 20, 30, 50
ALMACEN = 2
PRODUCTO = 60
POS_UUID = "045d0d68-d3ed-438b-9d86-89b2ccd6ca85"


class InventarioUnicoTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=PRINCIPAL, name="Mi Empresa",
                                 tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                                 type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(id_customer_supplier=CLIENTE, name="Cliente",
                                 tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                                 type="client", id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Almacen",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=ALMACEN, id_location_type=1,
                         location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Agua", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(id_invoice=FACTURA, id_customer_supplier=CLIENTE,
                           id_issuer_customer_supplier=PRINCIPAL, id_proyect=PROYECTO,
                           id_status=40, invoice_status="pendiente",
                           tax_certification_supplier=PRINCIPAL, apply_tax=False,
                           total=Decimal("0"), currency="MXN", created_by=1))
            db.flush()
            db.add(Product(id_product=PRODUCTO, id_invoice=FACTURA, id_location=ALMACEN,
                           id_material=1, is_directly_related_to_product_service=False,
                           cantidad=20, created_by=1))
            db.flush()
            db.add(InventoryStock(id_product=PRODUCTO, id_location=ALMACEN,
                                  quantity=20, created_by=1))

    def existencia(self):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(
                id_product=PRODUCTO, id_location=ALMACEN).first()
            return int(fila.quantity) if fila else 0

    def movimiento(self, tipo, cantidad, **extra):
        return inventario.apply_inventory_movement(PRODUCTO, {
            "movement_type": tipo, "quantity": cantidad,
            "id_location": ALMACEN,
            "idempotency_key": extra.pop("key", f"{tipo}-{cantidad}-{len(extra)}"),
            "reason": extra.pop("reason", "Prueba"),
            **extra,
        }, ACTOR)


class TestCaducidad(InventarioUnicoTestCase):
    """Lo que se vence no es lo mismo que lo que se merma.

    Se registraba todo como merma, y con las dos en el mismo saco no hay forma
    de saber cual de los dos problemas se tiene: la merma se reduce operando
    mejor y la caducidad se reduce comprando mejor.
    """

    def test_expiry_is_a_movement_of_its_own(self):
        self.assertIn("expiry", inventario.MOVEMENT_SIGNS)
        self.assertEqual(-1, inventario.MOVEMENT_SIGNS["expiry"])

    def test_it_discounts_like_any_other_exit(self):
        self.movimiento("expiry", 3, reason="Se vencio el lote")

        self.assertEqual(17, self.existencia())

    def test_it_demands_a_written_reason(self):
        """Cambia la existencia sin documento detras: sin motivo no se audita."""
        with self.assertRaises(AppError) as raised:
            inventario.apply_inventory_movement(PRODUCTO, {
                "movement_type": "expiry", "quantity": 1,
                "id_location": ALMACEN, "idempotency_key": "sin-motivo",
            }, ACTOR)

        self.assertEqual("errors.inventory_reason_required", raised.exception.message_key)


class TestOrigenDelMovimiento(InventarioUnicoTestCase):
    def test_a_movement_says_which_project_caused_it(self):
        self.movimiento("receive", 5, key="entrada-nucleo")

        with transaction_context() as db:
            ultimo = db.query(InventoryLedger).order_by(
                InventoryLedger.id_inventory_ledger.desc()).first()

        self.assertEqual("nucleo", ultimo.source_module,
                         "por omision el movimiento es del nucleo")

    def test_an_unknown_project_is_refused(self):
        """La lista es cerrada: un origen inventado no se puede consultar."""
        with transaction_context() as db:
            with self.assertRaises(AppError) as raised:
                inventario.apply_movement_in_session(
                    db, PRODUCTO, ACTOR, movement_type="receive", quantity_delta=1,
                    idempotency_key="origen-malo", id_location=ALMACEN,
                    source_module="inventado",
                )

        self.assertEqual("errors.invalid_field", raised.exception.message_key)

    def test_the_declared_projects_are_the_four_that_exist(self):
        self.assertEqual(
            {"nucleo", "pos", "restaurante", "logistica"},
            set(inventario.SOURCE_MODULES),
        )


class TestVentaDelPuntoDeVenta(InventarioUnicoTestCase):
    """El POS no comparte tabla -corre contra su base- pero si comparte saldo."""

    def enlace(self):
        return enlazar({
            "id_product": PRODUCTO,
            "pos_product_id": POS_UUID,
            "pos_product_name": "Agua embotellada 1L",
            "id_location": ALMACEN,
        }, ACTOR)

    def venta(self, cantidad=2, folio="V-20260901-00001", uuid=POS_UUID):
        return {
            "folio": folio,
            "items": [{"product_id": uuid, "name": "Agua embotellada 1L",
                       "quantity": cantidad}],
        }

    def test_a_linked_sale_discounts_the_core_inventory(self):
        self.enlace()

        resultado = reflejar_venta(self.venta(2), ACTOR)

        self.assertEqual(1, len(resultado["reflected"]))
        self.assertEqual([], resultado["skipped"])
        self.assertEqual(18, self.existencia())

    def test_the_movement_is_recorded_as_coming_from_the_pos(self):
        """Un solo saldo, y el origen sigue siendo legible."""
        self.enlace()
        reflejar_venta(self.venta(1), ACTOR)

        with transaction_context() as db:
            ultimo = db.query(InventoryLedger).order_by(
                InventoryLedger.id_inventory_ledger.desc()).first()

        self.assertEqual("pos", ultimo.source_module)
        self.assertEqual("issue", ultimo.movement_type)
        self.assertEqual("V-20260901-00001", ultimo.reference_id)

    def test_an_unlinked_product_does_not_discount_and_says_so(self):
        """Descontar del producto equivocado es peor que no descontar.

        Lo primero se ve sano; lo segundo se nota. Por eso no se adivina la
        correspondencia por nombre.
        """
        resultado = reflejar_venta(self.venta(2, uuid="otro-uuid-sin-enlace"), ACTOR)

        self.assertEqual([], resultado["reflected"])
        self.assertEqual("product_not_linked", resultado["skipped"][0]["reason"])
        self.assertEqual(20, self.existencia(), "no se toco nada")

    def test_reflecting_the_same_sale_twice_does_not_discount_twice(self):
        """La llave lleva el folio: un reintento no cobra dos veces al almacen."""
        self.enlace()
        reflejar_venta(self.venta(3), ACTOR)

        segunda = reflejar_venta(self.venta(3), ACTOR)

        self.assertEqual(17, self.existencia())
        self.assertTrue(segunda["reflected"][0]["already_applied"])

    def test_a_sale_without_stock_is_reported_and_not_reverted(self):
        """La venta ya se cobro: revertirla dejaria al cliente sin su compra."""
        self.enlace()

        resultado = reflejar_venta(self.venta(500), ACTOR)

        self.assertEqual([], resultado["reflected"])
        self.assertEqual("errors.inventory_insufficient_stock",
                         resultado["skipped"][0]["reason"])
        self.assertEqual(20, self.existencia())

    def test_a_fractional_quantity_is_reported_instead_of_rounded(self):
        self.enlace()

        resultado = reflejar_venta(self.venta("1.5"), ACTOR)

        self.assertEqual("quantity_not_whole_units", resultado["skipped"][0]["reason"])

    def test_a_pos_product_cannot_be_linked_twice(self):
        """Dos enlaces dejarian la venta descontando dos veces."""
        self.enlace()

        with self.assertRaises(AppError) as raised:
            self.enlace()

        self.assertEqual("errors.pos_product_already_linked", raised.exception.message_key)


class TestQueSigueSiendoUnSoloSaldo(InventarioUnicoTestCase):
    def test_movements_from_every_project_land_in_the_same_ledger(self):
        """Es lo que hace que "cuanto hay" tenga una sola respuesta."""
        self.movimiento("receive", 5, key="del-nucleo")
        with transaction_context() as db:
            inventario.apply_movement_in_session(
                db, PRODUCTO, ACTOR, movement_type="issue", quantity_delta=-2,
                idempotency_key="del-restaurante", id_location=ALMACEN,
                source_module="restaurante", reason="Consumo de cocina")

        with transaction_context() as db:
            origenes = {
                fila.source_module for fila in
                db.query(InventoryLedger).filter_by(id_product=PRODUCTO).all()
            }

        self.assertEqual({"nucleo", "restaurante"}, origenes)
        self.assertEqual(23, self.existencia(), "un solo saldo para los dos")


class TestInsumosDelRestaurante(InventarioUnicoTestCase):
    """El restaurante lleva su libro y ademas anota en el del nucleo.

    Los dos, no uno: el suyo guarda el coste unitario y el saldo por insumo,
    que son cosas del restaurante; el del nucleo contesta cuanta existencia hay
    en la empresa. Antes eran dos respuestas distintas a "cuanto aceite hay".
    """

    def insumo(self, *, enlazado=True, cantidad="10"):
        from decimal import Decimal

        from app.models.restaurant import RestaurantInventoryItem

        with transaction_context() as db:
            item = RestaurantInventoryItem(
                id_proyect=PROYECTO, description="Aceite vegetal",
                quantity=Decimal(cantidad), unit="L", cost_per_unit=Decimal("0"),
                id_product=PRODUCTO if enlazado else None,
                id_location=ALMACEN if enlazado else None,
                created_by=1)
            db.add(item)
            db.flush()
            return item.id_restaurant_inventory_item

    def movimiento_de_insumo(self, id_item, tipo, cantidad, previo, nuevo):
        from decimal import Decimal

        from app.models.restaurant import (
            RestaurantInventoryItem, RestaurantInventoryMovement,
        )
        from app.services.restaurant_inventory_bridge import reflejar_movimiento

        with transaction_context() as db:
            item = db.get(RestaurantInventoryItem, id_item)
            mov = RestaurantInventoryMovement(
                id_proyect=PROYECTO, id_restaurant_inventory_item=id_item,
                movement_type=tipo, quantity=Decimal(str(cantidad)),
                previous_quantity=Decimal(str(previo)),
                new_quantity=Decimal(str(nuevo)),
                reason="prueba", created_by=1)
            db.add(mov)
            db.flush()
            return reflejar_movimiento(db, item, mov, ACTOR)

    def test_a_consumption_discounts_the_core_inventory(self):
        id_item = self.insumo()

        fallo = self.movimiento_de_insumo(id_item, "salida", 2, 10, 8)

        self.assertIsNone(fallo)
        self.assertEqual(18, self.existencia())

    def test_the_movement_says_it_came_from_the_restaurant(self):
        id_item = self.insumo()
        self.movimiento_de_insumo(id_item, "salida", 1, 10, 9)

        with transaction_context() as db:
            ultimo = db.query(InventoryLedger).order_by(
                InventoryLedger.id_inventory_ledger.desc()).first()

        self.assertEqual("restaurante", ultimo.source_module)
        self.assertEqual("issue", ultimo.movement_type)

    def test_waste_leaves_as_an_exit_like_any_other(self):
        """Para el almacen una merma es existencia que se fue.

        Lo que la distingue -que se perdio en lugar de venderse- vive en el
        libro del restaurante, que es donde alguien va a preguntarlo.
        """
        id_item = self.insumo()

        self.movimiento_de_insumo(id_item, "merma", 3, 10, 7)

        self.assertEqual(17, self.existencia())

    def test_an_entry_adds_to_the_core_inventory(self):
        id_item = self.insumo()

        self.movimiento_de_insumo(id_item, "entrada", 5, 10, 15)

        self.assertEqual(25, self.existencia())

    def test_an_adjustment_moves_only_the_difference(self):
        """El ajuste FIJA el saldo, no lo suma: al nucleo va la diferencia."""
        id_item = self.insumo()

        self.movimiento_de_insumo(id_item, "ajuste", 7, 10, 7)

        self.assertEqual(17, self.existencia(), "de 10 a 7 son -3")

    def test_an_unlinked_item_does_not_touch_the_core(self):
        """Sin enlace no se refleja, y eso permite adoptarlo insumo a insumo."""
        id_item = self.insumo(enlazado=False)

        fallo = self.movimiento_de_insumo(id_item, "salida", 2, 10, 8)

        self.assertIsNone(fallo)
        self.assertEqual(20, self.existencia(), "no se toco nada")

    def test_a_fractional_quantity_is_reported_not_rounded(self):
        """0.75 kg de harina no son 0 ni 1 piezas.

        Redondear a 0 esconde un consumo y redondear a 1 inventa existencia que
        salio. Se reporta y el descuadre queda a la vista.
        """
        id_item = self.insumo()

        fallo = self.movimiento_de_insumo(id_item, "salida", "0.75", 10, "9.25")

        self.assertIsNotNone(fallo)
        self.assertIn("fraccionaria", fallo["motivo"])
        self.assertEqual(20, self.existencia(), "no se movio nada")

    def test_reflecting_the_same_movement_twice_does_not_discount_twice(self):
        """La llave lleva el identificador del movimiento del restaurante."""
        from app.models.restaurant import RestaurantInventoryItem
        from app.services.restaurant_inventory_bridge import reflejar_movimiento
        from app.models.restaurant import RestaurantInventoryMovement
        from decimal import Decimal

        id_item = self.insumo()
        with transaction_context() as db:
            item = db.get(RestaurantInventoryItem, id_item)
            mov = RestaurantInventoryMovement(
                id_proyect=PROYECTO, id_restaurant_inventory_item=id_item,
                movement_type="salida", quantity=Decimal("3"),
                previous_quantity=Decimal("10"), new_quantity=Decimal("7"),
                reason="prueba", created_by=1)
            db.add(mov)
            db.flush()
            reflejar_movimiento(db, item, mov, ACTOR)
            reflejar_movimiento(db, item, mov, ACTOR)

        self.assertEqual(17, self.existencia(), "un reintento no descuenta dos veces")


class TestMercanciaDeLogistica(InventarioUnicoTestCase):
    """Logistica no llevaba libro: cada edicion pisaba el saldo sin rastro.

    Aqui el signo de la DIFERENCIA decide el verbo, asi que no hay un campo de
    tipo que capturar y por tanto no hay donde equivocarse.
    """

    class Fila:
        """Lo unico que el puente lee de una fila de logistica."""

        def __init__(self, id_, cantidad, *, enlazada=True):
            self.id_logistics_inventory = id_
            self.quantity = cantidad
            self.id_product = PRODUCTO if enlazada else None
            self.id_core_location = ALMACEN if enlazada else None

    def reflejar(self, fila, anterior):
        from app.services.logistics_inventory_bridge import reflejar_cambio

        with transaction_context() as db:
            return reflejar_cambio(db, fila, anterior, ACTOR, motivo="prueba")

    def test_stock_going_up_enters_the_core_inventory(self):
        from decimal import Decimal

        fallo = self.reflejar(self.Fila(1, Decimal("4")), Decimal("0"))

        self.assertIsNone(fallo)
        self.assertEqual(24, self.existencia())

    def test_stock_going_down_leaves_the_core_inventory(self):
        from decimal import Decimal

        fallo = self.reflejar(self.Fila(2, Decimal("1")), Decimal("4"))

        self.assertIsNone(fallo)
        self.assertEqual(17, self.existencia(), "de 4 a 1 son -3")

    def test_the_movement_says_it_came_from_logistics(self):
        from decimal import Decimal

        self.reflejar(self.Fila(3, Decimal("2")), Decimal("0"))

        with transaction_context() as db:
            ultimo = db.query(InventoryLedger).order_by(
                InventoryLedger.id_inventory_ledger.desc()).first()

        self.assertEqual("logistica", ultimo.source_module)
        self.assertEqual("receive", ultimo.movement_type)
        self.assertEqual("logistics_inventory", ultimo.reference_type)

    def test_no_change_writes_nothing(self):
        """Guardar una fila sin tocar la cantidad no es un movimiento."""
        from decimal import Decimal

        with transaction_context() as db:
            antes = db.query(InventoryLedger).count()

        fallo = self.reflejar(self.Fila(4, Decimal("5")), Decimal("5"))

        with transaction_context() as db:
            despues = db.query(InventoryLedger).count()

        self.assertIsNone(fallo)
        self.assertEqual(antes, despues)
        self.assertEqual(20, self.existencia())

    def test_an_unlinked_row_does_not_touch_the_core(self):
        from decimal import Decimal

        fallo = self.reflejar(self.Fila(5, Decimal("9"), enlazada=False), Decimal("0"))

        self.assertIsNone(fallo)
        self.assertEqual(20, self.existencia())

    def test_a_fractional_quantity_is_reported_not_rounded(self):
        from decimal import Decimal

        fallo = self.reflejar(self.Fila(6, Decimal("2.5")), Decimal("0"))

        self.assertIsNotNone(fallo)
        self.assertIn("fraccionaria", fallo["motivo"])
        self.assertEqual(20, self.existencia())

    def test_the_same_resulting_balance_is_not_applied_twice(self):
        """La llave lleva la fila Y el saldo resultante.

        Reintentar la misma operacion no vuelve a mover; una operacion POSTERIOR
        sobre la misma fila si, que es lo correcto -- es otro movimiento.
        """
        from decimal import Decimal

        self.reflejar(self.Fila(7, Decimal("3")), Decimal("0"))
        self.reflejar(self.Fila(7, Decimal("3")), Decimal("0"))

        self.assertEqual(23, self.existencia(), "el reintento no entro dos veces")


if __name__ == "__main__":
    unittest.main()
