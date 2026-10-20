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
from app.services.inventory_trace_service import (
    _clasificar, estatus_efectivo, localizar,
)
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 70}
AJENO = {"id_user": 2, "id_proyect": 99}

EMPRESA = 10
CLIENTE = 20
ALMACEN = 1
COMPRA = 55
MERCANCIA = 80
HERRAMIENTA = 81
RESPONSABLE = 300


def _sembrar_lo_minimo(db, *, id_invoice, ubicaciones):
    """Los catalogos y la factura sin los que `product` no se puede insertar.

    `product.id_invoice` es NOT NULL y el alcance del actor se resuelve por el
    proyecto de esa factura, asi que hasta una prueba que solo quiere buscar
    texto tiene que montar la cadena completa: empresa, cliente, estatus,
    proyecto y factura.

    `ubicaciones` es {id: descripcion}; se crean todas con el mismo tipo.
    """
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
        ProductFamily(id_product_family=1, product_family_description="General",
                      created_by=1),
        Unit(id_unit=1, unit_name="Pieza", is_active=True,
             measurement_system="metric", created_by=1),
    ])
    db.flush()
    db.add_all([
        Status(id_status=40, status_description="Activo", category="invoice",
               is_terminal=False, sort_order="asc", created_by=1),
        Proyect(id_proyect=70, id_customer_supplier=CLIENTE, leader=1,
                proyect_description="Proyecto", created_by=1),
        Material(id_material=1, material_description="Generico", id_unit=1,
                 id_brand=1, id_product_family=1, created_by=1),
    ])
    db.add_all([
        Location(id_location=id_ubicacion, id_location_type=1,
                 location_description=descripcion, created_by=1)
        for id_ubicacion, descripcion in ubicaciones.items()
    ])
    db.flush()
    # El usuario 1 existe de verdad. Prestar una pieza ahora comprueba el
    # responsable contra la tabla, porque en produccion `inventory_asset.
    # id_holder` tiene llave ajena y un identificador inventado reventaba en el
    # COMMIT. `TestLocalizar` siembra ademas a RESPONSABLE, que es quien recibe.
    sembrar_actor(db, id_proyect=70, id_status=40)
    db.add(Invoice(
        id_invoice=id_invoice, id_customer_supplier=EMPRESA,
        id_issuer_customer_supplier=CLIENTE, id_proyect=70, id_status=40,
        invoice_status="timbrada", tax_certification_supplier=CLIENTE,
        apply_tax=False, created_by=1,
    ))
    db.flush()


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


class TestElEstatusQueSePinta(unittest.TestCase):
    """El verde de una tarjeta no puede contradecir lo que esta fuera."""

    SALIDAS = {"quantity": 1}

    def test_open_loans_and_nothing_in_stock_override_a_stale_entrada(self):
        self.assertEqual("SALIDA", estatus_efectivo("ENTRADA", self.SALIDAS, []))
        self.assertEqual("SALIDA", estatus_efectivo(None, self.SALIDAS, []))

    def test_stock_still_in_the_warehouse_keeps_the_stored_status(self):
        self.assertEqual("ENTRADA", estatus_efectivo(
            "ENTRADA", self.SALIDAS, [{"quantity": 3}]))

    def test_nothing_out_keeps_the_stored_status(self):
        self.assertEqual("ENTRADA", estatus_efectivo("ENTRADA", None, []))

    def test_a_decision_is_never_overridden(self):
        for estatus in ("EXTRAVIADO", "DESTRUCCION", "DAÑADO", "EN REPARACION"):
            self.assertEqual(estatus, estatus_efectivo(estatus, self.SALIDAS, []))

    def test_a_stale_salida_with_everything_back_is_shown_as_entrada(self):
        """Todas las salidas cerradas y existencia en el almacen: el azul de
        "salio del almacen" que dejo el sistema anterior es mentira."""
        self.assertEqual("ENTRADA", estatus_efectivo("SALIDA", None, [{"quantity": 1}]))

    def test_salida_stays_while_something_is_still_out(self):
        self.assertEqual("SALIDA", estatus_efectivo("SALIDA", self.SALIDAS, []))
        # Caso mixto: algo fuera y algo en el almacen. No se adivina.
        self.assertEqual("SALIDA", estatus_efectivo(
            "SALIDA", self.SALIDAS, [{"quantity": 3}]))

    def test_nuevo_and_usado_are_condition_not_location(self):
        """Quien marca "usado" desde el selector del producto no puede escoger
        ENTRADA (no esta en el catalogo): con existencia en el almacen se ve verde."""
        for estado in ("usado", "nuevo", "Usado"):
            with self.subTest(estado=estado):
                self.assertEqual("ENTRADA", estatus_efectivo(estado, None, [{"quantity": 1}]))
                self.assertEqual("ENTRADA", estatus_efectivo(
                    estado, self.SALIDAS, [{"quantity": 1}]))
                self.assertEqual("SALIDA", estatus_efectivo(estado, self.SALIDAS, []))
                # Sin existencia ni salidas no hay de donde concluir.
                self.assertEqual(estado, estatus_efectivo(estado, None, []))

    def test_salida_with_nothing_anywhere_is_left_alone(self):
        self.assertEqual("SALIDA", estatus_efectivo("SALIDA", None, []))


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



class TestLosDosNivelesDeBusqueda(BackendTestCase):
    """Buscar una pieza y buscar el producto son dos preguntas distintas.

    Antes se contestaban igual: buscar la etiqueta `TAL-CFG-C` devolvia el
    producto con sus tres piezas y sin decir cual era la que se pidio -medido-,
    asi que quien tenia el numero en la mano tenia que encontrarlo a ojo en la
    lista, que es justo lo que la busqueda venia a evitar.

    Ahora la respuesta dice por que salio -`match_kind`- y senala las piezas que
    coinciden. La distincion es fina a proposito: las etiquetas suelen empezar
    por el codigo del producto -`TAL-CFG-A`, `-B`, `-C`-, asi que "contiene el
    texto" marcaba las tres al buscar el producto y afirmaba que coincidian tres
    piezas cuando no coincidia ninguna.
    """

    ALMACEN2 = 8801
    HERRAMIENTA2 = 8802
    COMPRA2 = 8803

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            _sembrar_lo_minimo(db, id_invoice=self.COMPRA2,
                               ubicaciones={self.ALMACEN2: "Nave 2"})
            db.add(Product(
                id_product=self.HERRAMIENTA2, id_invoice=self.COMPRA2,
                id_location=self.ALMACEN2, id_material=1,
                is_directly_related_to_product_service=True, product_code="TAL-CFG",
                descripcion="Taladro percutor", stock_purpose="uso_interno",
                tracking_mode="serializado", gross_price=Decimal("3200.00"), created_by=1,
            ))

        from app.services.inventory_asset_service import register_asset

        for sufijo in ("A", "B", "C"):
            register_asset({
                "id_product": self.HERRAMIENTA2,
                "asset_tag": "TAL-CFG-" + sufijo,
                "id_location": self.ALMACEN2,
            }, ACTOR)

    def _pieza_llamada(self, etiqueta):
        from sqlalchemy import select as _select

        from app.models.inventory_asset import InventoryAsset

        with transaction_context() as db:
            return db.scalars(
                _select(InventoryAsset.id_inventory_asset)
                .where(InventoryAsset.asset_tag == etiqueta)
            ).first()

    def _item(self, consulta):
        resultado = localizar(consulta, ACTOR)
        self.assertEqual(1, resultado["total"], "'%s' no dio un solo producto" % consulta)
        return resultado["items"][0]

    def test_asking_for_one_piece_points_at_that_piece(self):
        item = self._item("TAL-CFG-C")
        self.assertEqual("asset_tag", item["match_kind"])
        self.assertEqual(["TAL-CFG-C"], item["matched_asset_tags"])
        # Las tres siguen ahi: la pieza vive en un producto y verlo entero es
        # util. Lo que cambia es que se sabe cual se pidio.
        self.assertEqual(3, len(item["assets"]))
        self.assertEqual("TAL-CFG-C", item["assets"][0]["asset_tag"],
                         "la pieza que se pidio tiene que venir primero")
        self.assertEqual([True, False, False], [p["matched"] for p in item["assets"]])

    def test_asking_for_the_product_marks_no_piece(self):
        """El codigo es prefijo de las etiquetas; sin cuidado marcaria las tres."""
        item = self._item("TAL-CFG")
        self.assertEqual("product_code", item["match_kind"])
        self.assertEqual([], item["matched_asset_tags"])
        self.assertEqual(3, len(item["assets"]))
        self.assertFalse(any(p["matched"] for p in item["assets"]))

    def test_it_says_how_many_units_there_are_and_how_many_are_usable(self):
        """Tres piezas de las que solo una sirve no es "tres" ni es "una"."""
        from app.services.inventory_asset_service import send_to_repair

        send_to_repair(self._pieza_llamada("TAL-CFG-B"), {"reason": "No enciende"}, ACTOR)

        item = self._item("TAL-CFG")
        self.assertEqual(3, item["unit_count"])
        self.assertEqual(2, item["available_units"])

    def test_the_matched_piece_carries_its_own_log(self):
        """La historia del producto no contesta donde esta ESTA pieza."""
        from app.services.inventory_asset_service import lend_asset

        # La fecha de regreso es obligatoria: un prestamo sin ella es una baja
        # disfrazada, porque nunca esta vencido y nadie lo reclama.
        lend_asset(self._pieza_llamada("TAL-CFG-A"),
                   {"id_holder": 1, "due_date": "2027-01-01",
                    "reason": "Obra Norte"}, ACTOR)

        pieza = self._item("TAL-CFG-A")["assets"][0]
        eventos = pieza["timeline"]
        # Del mas reciente al mas viejo: lo ultimo que le paso es la respuesta.
        self.assertEqual(["prestamo", "alta"], [e["event_type"] for e in eventos])
        self.assertEqual("se presto a", eventos[0]["etiqueta"])
        # Un nombre, no un identificador: "responsable 1" no dice quien lo tiene.
        self.assertIsNotNone(eventos[0]["holder_after_name"])
        self.assertNotEqual("1", eventos[0]["holder_after_name"])
        self.assertEqual("Nave 2", eventos[1]["location_after_description"])

    def test_the_unmatched_pieces_do_not_carry_a_log(self):
        """Traer la bitacora de las treinta piezas de un producto para ver una
        son treinta consultas desperdiciadas."""
        item = self._item("TAL-CFG-C")
        self.assertIn("timeline", item["assets"][0])
        for pieza in item["assets"][1:]:
            self.assertNotIn("timeline", pieza)


class TestElTrasladoNoCuentaDoble(BackendTestCase):
    """Un traslado escribe dos asientos; sumar valores absolutos los cuenta dos veces.

    Medido antes del arreglo: trasladar 10 unidades y la historia decia
    `trasladado 20`. El libro guarda la salida del origen y la entrada al
    destino con el mismo `transfer_group`, y las dos tienen 10 en valor
    absoluto. Se cuenta solo la salida, que es lo que se movio.

    Importa mas de lo que parece: el traslado es el movimiento que mas se hace
    en un almacen -reacomodos- y un numero inflado ahi hace creer que se mueve
    el doble de mercancia de la que se mueve.
    """

    ALMACEN_A = 8811
    ALMACEN_B = 8812
    PRODUCTO = 8813
    COMPRA3 = 8814

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            _sembrar_lo_minimo(db, id_invoice=self.COMPRA3, ubicaciones={
                self.ALMACEN_A: "Nave A", self.ALMACEN_B: "Nave B",
            })
            db.add(Product(
                id_product=self.PRODUCTO, id_invoice=self.COMPRA3,
                id_location=self.ALMACEN_A, id_material=1,
                is_directly_related_to_product_service=True, product_code="TOR-500",
                descripcion="Tornillo", stock_purpose="mercancia",
                gross_price=Decimal("2.00"), created_by=1,
            ))

        apply_inventory_movement(self.PRODUCTO, {
            "movement_type": "receive", "quantity": 30, "id_location": self.ALMACEN_A,
            "reference_type": "purchase", "reference_id": "1",
            "idempotency_key": "tor-compra",
        }, ACTOR)

    def _trasladar(self, llave):
        from app.services.inventory_service import transfer_inventory

        return transfer_inventory(self.PRODUCTO, {
            "quantity": 10, "id_location_from": self.ALMACEN_A,
            "id_location_to": self.ALMACEN_B, "reason": "Reacomodo",
            "idempotency_key": llave,
        }, ACTOR)

    def test_moving_ten_units_is_reported_as_ten(self):
        self._trasladar("tor-traslado")

        historia = localizar("TOR-500", ACTOR)["items"][0]["history"]
        self.assertEqual(10, historia["trasladado"]["unidades"])
        self.assertEqual(1, historia["trasladado"]["veces"],
                         "un traslado es un movimiento, no dos")

    def test_the_stock_still_adds_up_after_the_move(self):
        """El arreglo es de la cuenta de la historia; el saldo no se toca."""
        self._trasladar("tor-traslado-2")

        item = localizar("TOR-500", ACTOR)["items"][0]
        self.assertEqual(30, item["total"])
        self.assertEqual(
            {"Nave A": 20, "Nave B": 10},
            {u["location_description"]: u["quantity"] for u in item["locations"]},
        )



class TestLaCadenaDeClasificacionYElSitio(BackendTestCase):
    """A que familia pertenece, de que marca es y donde esta exactamente.

    Todo esto ya estaba en la base, a dos saltos: `product.id_material` lleva a
    `material`, y de ahi salen la familia, la marca y la unidad. El rastreo
    devolvia el codigo y la descripcion, asi que para saber la familia de lo que
    se acababa de encontrar habia que abrir la pantalla de Producto y desde ahi
    la de Material -dos pantallas para un dato que ya venia en la consulta-.

    Del sitio pasaba algo parecido: se devolvia el almacen y la ubicacion final.
    En un almacen de dos niveles alcanza; en uno de cuatro, "Rack A-1" no dice
    donde esta el rack, y con dos naves hay un Rack A-1 en cada una.

    Lo que estas pruebas fijan:

    * la familia, la marca, el material y la unidad salen resueltos por nombre;
    * la ubicacion trae su rama completa, del almacen a la balda;
    * filtrar por un almacen incluye lo que esta en sus racks. Sin eso el filtro
      por almacen devuelve casi nada y parece que el almacen esta vacio cuando
      lo que pasa es que todo esta un nivel mas abajo;
    * los desplegables no se encogen al aplicar un filtro. Calculados sobre el
      resultado ya filtrado, elegir una familia vaciaba las otras listas -y la
      propia cuando la eleccion no daba resultados, con lo que el filtro activo
      desaparecia del desplegable que lo mostraba-;
    * un filtro con basura se ignora en vez de reventar. Llegan de la barra de
      direcciones, y un 500 deja la pantalla en blanco sin decir por que.
    """

    NAVE_A = 8821
    RACK_A = 8822
    NAVE_B = 8823
    COMPRA = 8824
    TALADRO = 8825
    CEMENTO = 8826

    FAM_HERRAMIENTA = 8831
    FAM_OBRA = 8832
    MARCA_BOSCH = 8833
    MARCA_CEMEX = 8834
    MAT_TALADRO = 8835
    MAT_CEMENTO = 8836
    UNIDAD_PIEZA = 8837
    UNIDAD_SACO = 8838

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMPRESA, name="Mi Empresa",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client",
                    id_user=1, created_by=1,
                ),
                # Dos tipos: uno es almacen y el otro no. La distincion es la que
                # decide donde termina la rama al subir por el arbol.
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                LocationType(id_location_type=2, location_type_description="Rack",
                             is_warehouse=False, created_by=1),
                ProductFamily(id_product_family=self.FAM_HERRAMIENTA,
                              product_family_description="Herramienta", created_by=1),
                ProductFamily(id_product_family=self.FAM_OBRA,
                              product_family_description="Material de obra", created_by=1),
                Brand(id_brand=self.MARCA_BOSCH, brand_description="Bosch", created_by=1),
                Brand(id_brand=self.MARCA_CEMEX, brand_description="Cemex", created_by=1),
                Unit(id_unit=self.UNIDAD_PIEZA, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
                Unit(id_unit=self.UNIDAD_SACO, unit_name="Saco", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Proyect(id_proyect=70, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Location(id_location=self.NAVE_A, id_location_type=1,
                         location_description="Nave A", created_by=1),
                Location(id_location=self.NAVE_B, id_location_type=1,
                         location_description="Nave B", created_by=1),
                Material(id_material=self.MAT_TALADRO,
                         material_description="Herramienta electrica",
                         id_unit=self.UNIDAD_PIEZA, id_brand=self.MARCA_BOSCH,
                         id_product_family=self.FAM_HERRAMIENTA, created_by=1),
                Material(id_material=self.MAT_CEMENTO, material_description="Cemento gris",
                         id_unit=self.UNIDAD_SACO, id_brand=self.MARCA_CEMEX,
                         id_product_family=self.FAM_OBRA, created_by=1),
            ])
            db.flush()
            # El rack cuelga de la nave: es la jerarquia que la rama recorre.
            db.add(Location(id_location=self.RACK_A, id_location_type=2,
                            location_description="Rack A-1",
                            id_location_reference=self.NAVE_A, created_by=1))
            db.add(Invoice(
                id_invoice=self.COMPRA, id_customer_supplier=EMPRESA,
                id_issuer_customer_supplier=CLIENTE, id_proyect=70, id_status=40,
                invoice_status="timbrada", tax_certification_supplier=CLIENTE,
                apply_tax=False, created_by=1,
            ))
            db.flush()
            db.add_all([
                Product(id_product=self.TALADRO, id_invoice=self.COMPRA,
                        id_location=self.RACK_A, id_material=self.MAT_TALADRO,
                        is_directly_related_to_product_service=True,
                        product_code="TAL-900", descripcion="Taladro percutor",
                        stock_purpose="uso_interno", tracking_mode="serializado",
                        gross_price=Decimal("3200.00"), created_by=1),
                Product(id_product=self.CEMENTO, id_invoice=self.COMPRA,
                        id_location=self.NAVE_B, id_material=self.MAT_CEMENTO,
                        is_directly_related_to_product_service=True,
                        product_code="CEM-500", descripcion="Cemento gris 50kg",
                        stock_purpose="mercancia", gross_price=Decimal("210.00"),
                        created_by=1),
            ])

        # El taladro entra al rack -dentro de la Nave A- y el cemento a la Nave B.
        apply_inventory_movement(self.TALADRO, {
            "movement_type": "receive", "quantity": 4, "id_location": self.RACK_A,
            "reference_type": "purchase", "reference_id": str(self.COMPRA),
            "idempotency_key": "tal-compra",
        }, ACTOR)
        apply_inventory_movement(self.CEMENTO, {
            "movement_type": "receive", "quantity": 80, "id_location": self.NAVE_B,
            "reference_type": "purchase", "reference_id": str(self.COMPRA),
            "idempotency_key": "cem-compra",
        }, ACTOR)

    def _codigos(self, **kwargs):
        return sorted(i["product_code"] for i in localizar("", ACTOR, **kwargs)["items"])

    # --- la cadena ---------------------------------------------------------

    def test_it_says_which_family_brand_material_and_unit_it_belongs_to(self):
        item = [i for i in localizar("TAL-900", ACTOR)["items"]][0]
        self.assertEqual(
            {
                "family": "Herramienta", "brand": "Bosch",
                "material": "Herramienta electrica", "unit": "Pieza",
            },
            {c: item["classification"][c] for c in ("family", "brand", "material", "unit")},
        )
        # Los identificadores viajan junto al nombre: la pantalla filtra con
        # ellos al hacer clic en el eslabon.
        self.assertEqual(self.FAM_HERRAMIENTA, item["classification"]["id_product_family"])
        self.assertEqual(self.MARCA_BOSCH, item["classification"]["id_brand"])

    def test_a_disagreeing_public_catalogue_is_reported_not_hidden(self):
        """`product.id_familia` es la familia de la tienda, no la del material."""
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_familia = self.FAM_OBRA

        clasificacion = localizar("TAL-900", ACTOR)["items"][0]["classification"]
        # Manda la del material: es la que el almacen usa y la unica obligatoria.
        self.assertEqual("Herramienta", clasificacion["family"])
        # Y la otra se dice, en vez de elegir una en silencio.
        self.assertEqual("Material de obra",
                         clasificacion["catalog_mismatch"]["family"]["family"])

    def test_no_mismatch_is_reported_when_they_agree(self):
        """El aviso solo aparece cuando hay algo que avisar."""
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_familia = self.FAM_HERRAMIENTA

        self.assertIsNone(
            localizar("TAL-900", ACTOR)["items"][0]["classification"]["catalog_mismatch"])

    # Un material sin marca/familia ("no se sabe") y el producto que si la trae.
    SIN_MARCA, PRETUL, SIN_FAMILIA = 8861, 8862, 8863

    def _material_sin_clasificar(self):
        with transaction_context() as db:
            db.add_all([
                Brand(id_brand=self.SIN_MARCA, brand_description="Sin marca específica",
                      created_by=1),
                Brand(id_brand=self.PRETUL, brand_description="Pretul", created_by=1),
                ProductFamily(id_product_family=self.SIN_FAMILIA,
                              product_family_description="Sin categoría", created_by=1),
            ])
            db.flush()
            material = db.get(Material, self.MAT_TALADRO)
            material.id_brand = self.SIN_MARCA
            material.id_product_family = self.SIN_FAMILIA

    def test_an_unclassified_material_takes_the_brand_and_family_of_the_product(self):
        """La marca vive en el producto; el material es solo el tipo de pieza."""
        self._material_sin_clasificar()
        with transaction_context() as db:
            taladro = db.get(Product, self.TALADRO)
            taladro.id_marca = self.PRETUL
            taladro.id_familia = self.FAM_OBRA

        clasificacion = localizar("TAL-900", ACTOR)["items"][0]["classification"]
        self.assertEqual("Pretul", clasificacion["brand"])
        self.assertEqual(self.PRETUL, clasificacion["id_brand"])
        self.assertEqual("Material de obra", clasificacion["family"])
        self.assertIsNone(clasificacion["catalog_mismatch"])

    def test_an_unclassified_material_and_product_just_say_nothing(self):
        self._material_sin_clasificar()
        clasificacion = localizar("TAL-900", ACTOR)["items"][0]["classification"]
        self.assertEqual("Sin marca específica", clasificacion["brand"])
        self.assertIsNone(clasificacion["catalog_mismatch"])

    def test_two_real_brands_that_disagree_are_still_reported(self):
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_marca = self.MARCA_CEMEX

        clasificacion = localizar("TAL-900", ACTOR)["items"][0]["classification"]
        self.assertEqual("Bosch", clasificacion["brand"])
        self.assertEqual("Cemex", clasificacion["catalog_mismatch"]["brand"]["brand"])

    def test_an_id_that_no_longer_exists_is_reported_with_its_id(self):
        """Sin nombre que mostrar, el aviso tiene que dar al menos el id."""
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_familia = 987654

        mismatch = localizar("TAL-900", ACTOR)["items"][0]["classification"]["catalog_mismatch"]
        self.assertEqual(987654, mismatch["family"]["id_product_family"])
        self.assertIsNone(mismatch["family"]["family"])

    def test_an_orphan_id_does_not_replace_an_unclassified_material(self):
        self._material_sin_clasificar()
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_marca = 987654

        clasificacion = localizar("TAL-900", ACTOR)["items"][0]["classification"]
        self.assertEqual("Sin marca específica", clasificacion["brand"])
        self.assertEqual(987654, clasificacion["catalog_mismatch"]["brand"]["id_brand"])

    def test_filtering_by_a_brand_finds_it_on_the_product_when_the_material_has_none(self):
        self._material_sin_clasificar()
        with transaction_context() as db:
            db.get(Product, self.TALADRO).id_marca = self.PRETUL

        self.assertEqual(["TAL-900"], self._codigos(id_marca=self.PRETUL))

    # --- el sitio ----------------------------------------------------------

    def test_the_location_comes_with_its_full_branch(self):
        """"Rack A-1" no dice donde esta el rack."""
        ubicacion = localizar("TAL-900", ACTOR)["items"][0]["locations"][0]
        self.assertEqual("Nave A > Rack A-1", ubicacion["path_label"])
        self.assertEqual(
            [("Nave A", True), ("Rack A-1", False)],
            [(s["location_description"], s["is_warehouse"]) for s in ubicacion["path"]],
        )

    def test_the_piece_carries_its_branch_too(self):
        from app.services.inventory_asset_service import register_asset

        register_asset({"id_product": self.TALADRO, "asset_tag": "TAL-900-A",
                        "id_location": self.RACK_A}, ACTOR)

        pieza = localizar("TAL-900-A", ACTOR)["items"][0]["assets"][0]
        self.assertEqual("Nave A > Rack A-1", pieza["location_path_label"])

    # --- los filtros -------------------------------------------------------

    def test_filtering_by_a_warehouse_includes_what_is_in_its_racks(self):
        """El taladro esta en el rack, no en la nave; filtrar por la nave lo trae."""
        self.assertEqual(["TAL-900"], self._codigos(id_ubicacion=self.NAVE_A))
        self.assertEqual(["CEM-500"], self._codigos(id_ubicacion=self.NAVE_B))

    def test_filtering_by_family_and_by_brand_narrows_the_list(self):
        self.assertEqual(["TAL-900"], self._codigos(id_familia=self.FAM_HERRAMIENTA))
        self.assertEqual(["CEM-500"], self._codigos(id_marca=self.MARCA_CEMEX))

    def test_two_filters_are_applied_together_not_one_of_them(self):
        """Familia de herramienta en la Nave B: no hay nada, y eso es la respuesta."""
        self.assertEqual(
            [], self._codigos(id_familia=self.FAM_HERRAMIENTA, id_ubicacion=self.NAVE_B))

    def test_filtering_by_piece_status_keeps_only_products_that_have_one(self):
        from app.services.inventory_asset_service import register_asset, send_to_repair

        creada = register_asset({"id_product": self.TALADRO, "asset_tag": "TAL-900-B",
                                 "id_location": self.RACK_A}, ACTOR)
        send_to_repair(creada["asset"]["id_inventory_asset"], {"reason": "No enciende"}, ACTOR)

        self.assertEqual(["TAL-900"], self._codigos(estado_pieza="en_reparacion"))
        # El cemento no tiene piezas, asi que ningun estado lo alcanza.
        self.assertEqual([], self._codigos(estado_pieza="extraviada"))

    def test_a_garbage_filter_is_ignored_instead_of_failing(self):
        """Llegan de la barra de direcciones; un 500 deja la pantalla en blanco."""
        for basura in ("abc", "", "  ", None, "3.7"):
            with self.subTest(valor=basura):
                self.assertEqual(
                    ["CEM-500", "TAL-900"], self._codigos(id_familia=basura),
                    "un filtro ilegible tiene que no filtrar, no reventar",
                )

    def test_an_unknown_id_filters_everything_out_rather_than_nothing(self):
        """Un identificador valido que no existe da cero, no la lista entera."""
        self.assertEqual([], self._codigos(id_familia=999999))

    # --- los desplegables --------------------------------------------------

    def test_the_dropdowns_only_offer_options_with_something_behind_them(self):
        catalogo = localizar("", ACTOR)["catalog"]
        self.assertEqual(
            ["Herramienta", "Material de obra"], [f["family"] for f in catalogo["families"]])
        self.assertEqual(["Bosch", "Cemex"], [b["brand"] for b in catalogo["brands"]])
        # Solo las naves, no los racks: la rama sube hasta el almacen.
        self.assertEqual(
            ["Nave A", "Nave B"],
            [w["location_description"] for w in catalogo["warehouses"]])

    def test_the_dropdowns_do_not_shrink_when_a_filter_is_applied(self):
        """Calculados sobre el resultado filtrado, elegir una familia vaciaba el resto."""
        sin_filtro = localizar("", ACTOR)["catalog"]
        con_filtro = localizar("", ACTOR, id_familia=self.FAM_HERRAMIENTA)["catalog"]
        self.assertEqual(sin_filtro, con_filtro)

    def test_the_dropdowns_survive_a_filter_that_matches_nothing(self):
        """Si se vaciaran, el filtro activo desapareceria del desplegable que lo muestra."""
        vacio = localizar("", ACTOR, id_familia=999999)
        self.assertEqual([], vacio["items"])
        self.assertEqual(
            ["Herramienta", "Material de obra"],
            [f["family"] for f in vacio["catalog"]["families"]])

    def test_it_reports_what_was_applied_so_the_screen_can_show_it(self):
        respuesta = localizar("", ACTOR, id_familia=self.FAM_HERRAMIENTA,
                              id_ubicacion=self.NAVE_A)
        self.assertEqual(self.FAM_HERRAMIENTA, respuesta["filters"]["id_product_family"])
        self.assertEqual(self.NAVE_A, respuesta["filters"]["id_location"])
        self.assertIsNone(respuesta["filters"]["id_brand"])

    def test_it_counts_every_match_even_when_it_only_returns_the_first_ones(self):
        """Con tope de resultados, lo que se ve puede ser menos que lo que hay."""
        respuesta = localizar("", ACTOR)
        self.assertEqual(2, respuesta["matches"])
        self.assertEqual(len(respuesta["items"]), respuesta["total"])


if __name__ == "__main__":
    unittest.main()
