"""Localizar cualquier cosa del almacen.

Lo que estas pruebas fijan, en orden de importancia:

* **se encuentra por la etiqueta de la pieza**, no solo por el codigo del
  producto. Es lo que esta pegado en la herramienta y lo que lee quien la tiene
  en la mano; sin eso hay que saber de antemano de que producto es la pieza que
  se busca, que es justo lo que no se sabe;
* **comprado y vendido se cuentan aparte** de recibido y entregado. Una entrada
  con una compra detras no es lo mismo que una devolucion de cliente, y en el
  mismo saco no hay forma de saber que se compro;
* **la merma, la caducidad y lo extraviado no se juntan.** Cada una se reduce
  haciendo algo distinto, asi que sumadas no dicen nada;
* **lo que el alcance esconde se cuenta**, en vez de callarlo: quien busca algo
  que existe y no lo ve merece saber que el filtro es el alcance;
* el nombre del responsable se resuelve, y si ya no existe se dice.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

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
    User,
)
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement
from app.services.inventory_trace_service import _clasificar, localizar
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 70}
AJENO = {"id_user": 2, "id_proyect": 99}

EMPRESA = 10
CLIENTE = 20
ALMACEN = 1
COMPRA = 55
MERCANCIA = 80
HERRAMIENTA = 81
RESPONSABLE = 300


class TestComoSeClasificaCadaMovimiento(unittest.TestCase):
    """La lectura del libro, sin tocar la base."""

    def test_an_entry_with_a_purchase_behind_it_is_a_purchase(self):
        self.assertEqual("comprado", _clasificar("receive", "purchase"))
        self.assertEqual("comprado", _clasificar("receive", "invoice_line"))

    def test_an_entry_without_a_document_is_only_a_receipt(self):
        """Un saldo de apertura no es una compra.

        Contarlo como compra inflaria lo comprado con mercancia que nunca se
        pago, que es justo el numero que se usa para negociar con proveedores.
        """
        self.assertEqual("recibido", _clasificar("receive", "manual"))
        self.assertEqual("recibido", _clasificar("receive", None))

    def test_an_exit_with_a_sale_behind_it_is_a_sale(self):
        self.assertEqual("vendido", _clasificar("issue", "sale"))
        self.assertEqual("vendido", _clasificar("issue", "invoice_line"))

    def test_an_exit_to_a_project_is_not_a_sale(self):
        """Sacar material para una obra no es venderlo."""
        self.assertEqual("entregado", _clasificar("issue", "project"))

    def test_losses_are_never_lumped_together(self):
        """Cada perdida se reduce haciendo algo distinto."""
        nombres = {
            _clasificar("damage", None),
            _clasificar("expiry", None),
            _clasificar("loss", None),
            _clasificar("destroy", None),
        }
        self.assertEqual(4, len(nombres), f"se solaparon: {nombres}")


class TestLocalizar(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMPRESA, name="Mi Empresa", tax_id="AAA010101AA1",
                    postal_code="37000", fiscal_type="601", type="supplier",
                    is_principal=True, id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente", tax_id="BBB010101BB1",
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
                Proyect(id_proyect=70, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=ALMACEN, id_location_type=1,
                         location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Generico", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
                User(id_user=RESPONSABLE, username="ana", full_name="Ana Almacenista",
                     email="ana@example.com", password="x", user_type="employee",
                     id_permission=1, id_proyect=70, id_status=40, supervisor=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(
                id_invoice=COMPRA, id_customer_supplier=EMPRESA,
                id_issuer_customer_supplier=CLIENTE, id_proyect=70, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=CLIENTE,
                apply_tax=False, created_by=1,
            ))
            db.flush()
            db.add_all([
                Product(id_product=MERCANCIA, id_invoice=COMPRA, id_location=ALMACEN,
                        id_material=1, is_directly_related_to_product_service=True,
                        product_code="AGU-001", descripcion="Agua embotellada",
                        stock_purpose="mercancia", gross_price=Decimal("18.00"), created_by=1),
                Product(id_product=HERRAMIENTA, id_invoice=COMPRA, id_location=ALMACEN,
                        id_material=1, is_directly_related_to_product_service=True,
                        product_code="TAL-CFG", descripcion="Taladro percutor",
                        stock_purpose="uso_interno", tracking_mode="serializado",
                        gross_price=Decimal("3200.00"), created_by=1),
            ])

        apply_inventory_movement(MERCANCIA, {
            "movement_type": "receive", "quantity": 50, "id_location": ALMACEN,
            "reference_type": "purchase", "reference_id": str(COMPRA),
            "idempotency_key": "compra-inicial",
        }, ACTOR)
        apply_inventory_movement(MERCANCIA, {
            "movement_type": "issue", "quantity": 6, "id_location": ALMACEN,
            "reference_type": "sale", "reference_id": "V-1",
            "idempotency_key": "venta-1",
        }, ACTOR)
        apply_inventory_movement(MERCANCIA, {
            "movement_type": "expiry", "quantity": 2, "id_location": ALMACEN,
            "reason": "Se pasaron de fecha", "idempotency_key": "caducidad-1",
        }, ACTOR)

    def test_it_finds_by_code_and_by_description(self):
        por_codigo = localizar("AGU-001", ACTOR)
        self.assertEqual(1, por_codigo["total"])
        por_texto = localizar("embotellada", ACTOR)
        self.assertEqual([MERCANCIA], [i["id_product"] for i in por_texto["items"]])

    def test_it_finds_a_product_by_the_tag_on_its_piece(self):
        """La etiqueta es lo que esta pegado en la herramienta.

        Sin esto hay que saber de antemano de que producto es la pieza que se
        busca, que es exactamente lo que no se sabe cuando se tiene el numero
        en la mano.
        """
        from app.services.inventory_asset_service import register_asset

        register_asset({
            "id_product": HERRAMIENTA, "asset_tag": "TAL-777",
            "id_location": ALMACEN,
        }, ACTOR)

        encontrado = localizar("TAL-777", ACTOR)
        self.assertEqual([HERRAMIENTA], [i["id_product"] for i in encontrado["items"]])

    def test_the_history_separates_bought_sold_and_expired(self):
        historia = localizar("AGU-001", ACTOR)["items"][0]["history"]
        self.assertEqual(50, historia["comprado"]["unidades"])
        self.assertEqual(6, historia["vendido"]["unidades"])
        self.assertEqual(2, historia["caducado"]["unidades"])
        # Lo que caduco no se cuenta como vendido en ningun sitio.
        self.assertNotIn("entregado", historia)

    def test_it_says_where_the_stock_is(self):
        item = localizar("AGU-001", ACTOR)["items"][0]
        self.assertEqual(1, len(item["locations"]))
        self.assertEqual(42, item["locations"][0]["quantity"])
        self.assertEqual("Almacen Central", item["locations"][0]["location_description"])

    def test_empty_locations_are_not_listed(self):
        """Una ubicacion sin existencia solo alarga la lista."""
        apply_inventory_movement(MERCANCIA, {
            "movement_type": "issue", "quantity": 42, "id_location": ALMACEN,
            "reference_type": "sale", "reference_id": "V-2",
            "idempotency_key": "venta-todo",
        }, ACTOR)
        item = localizar("AGU-001", ACTOR)["items"][0]
        self.assertEqual([], item["locations"])
        self.assertEqual(0, item["total"])

    def test_the_holder_is_named_and_a_missing_one_is_flagged(self):
        """"Quien lo tiene" con un numero no le dice nada a nadie.

        Y una pieza asignada a alguien que ya no existe es justo la que hay que
        ir a buscar, asi que no se deja el hueco en blanco.
        """
        from app.services.inventory_asset_service import lend_asset, register_asset

        alta = register_asset({
            "id_product": HERRAMIENTA, "asset_tag": "TAL-888",
            "id_location": ALMACEN,
        }, ACTOR)
        id_pieza = alta["asset"]["id_inventory_asset"]
        lend_asset(id_pieza, {
            "id_holder": RESPONSABLE, "due_date": "2027-01-01", "reason": "Obra",
        }, ACTOR)

        piezas = localizar("TAL-888", ACTOR)["items"][0]["assets"]
        prestada = next(p for p in piezas if p["asset_tag"] == "TAL-888")
        self.assertEqual("Ana Almacenista", prestada["holder_name"])

        with transaction_context() as db:
            from app.models.inventory_asset import InventoryAsset
            db.get(InventoryAsset, id_pieza).id_holder = 99999

        piezas = localizar("TAL-888", ACTOR)["items"][0]["assets"]
        huerfana = next(p for p in piezas if p["asset_tag"] == "TAL-888")
        self.assertEqual("#99999", huerfana["holder_name"])

    def test_it_counts_what_the_scope_hides_instead_of_staying_silent(self):
        """Buscar algo que existe y no verlo, sin explicacion, se lee como un fallo."""
        resultado = localizar("AGU-001", AJENO)
        self.assertEqual(0, resultado["total"])
        self.assertEqual(1, resultado["hidden_by_scope"])

    def test_it_can_be_narrowed_to_internal_use(self):
        """Herramienta y mercancia se buscan distinto y por motivos distintos."""
        solo_interno = localizar("", ACTOR, proposito="uso_interno")
        self.assertEqual([HERRAMIENTA], [i["id_product"] for i in solo_interno["items"]])

    def test_the_photo_travels_with_the_result(self):
        with transaction_context() as db:
            db.get(Product, MERCANCIA).path_imagen = "uploads/products/p_80.png"
        item = localizar("AGU-001", ACTOR)["items"][0]
        self.assertEqual("uploads/products/p_80.png", item["path_imagen"])


if __name__ == "__main__":
    unittest.main()
