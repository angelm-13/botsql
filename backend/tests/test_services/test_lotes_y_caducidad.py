"""Lotes y caducidad: primero sale lo que vence primero.

Que se venia a resolver
-----------------------
Un saldo de 300 sacos no dice cuando caduca ninguno. Con eso, lo que se vence se
descubre en el anaquel, y quien lo descubre ya no puede hacer nada: ni devolverlo
al proveedor, ni sacarlo antes, ni dejar de comprar tanto.

Lo que estas pruebas fijan
--------------------------
* **la salida se sirve del lote que vence primero.** Es lo unico que reduce la
  merma por caducidad; dejarlo a criterio de quien despacha ordena el anaquel por
  comodidad -lo de enfrente- en lugar de por fecha;
* **un lote sin fecha va al final.** No es que dure para siempre: es que uno con
  fecha siempre es mas urgente;
* **una salida puede tocar varios lotes**, y queda escrito de cuales. El libro
  escribe un renglon por movimiento, asi que sin el desglose el renglon diria que
  salieron 30 sin decir de donde;
* **el desglose por lote y el saldo del producto cuadran siempre.** Los dos los
  escribe la misma funcion, dentro de la misma transaccion: si hubiera dos
  caminos, empezarian a discrepar y no habria forma de saber cual creer;
* **el mismo lote que llega dos veces es un solo lote.** Con dos vivos, la mitad
  de las salidas descontaria de uno y la mitad del otro;
* **nada cambia para lo que no lleva lotes**, que hoy es todo: `lot_control`
  nace apagado.
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta
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
)
from app.models.session import transaction_context
from app.services.inventory_lot_service import (
    cuadre_de_lotes,
    lotes_del_producto,
    por_caducar,
)
from app.services.inventory_service import apply_inventory_movement
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

EMPRESA, CLIENTE, PROYECTO, ESTATUS = 10, 20, 30, 40
NAVE, RACK, COMPRA = 50, 51, 52
FAMILIA, MARCA, MATERIAL = 60, 61, 62
CEMENTO, TORNILLO = 70, 71


class BaseLotes(BackendTestCase):

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
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                ProductFamily(id_product_family=FAMILIA,
                              product_family_description="Obra", created_by=1),
                Brand(id_brand=MARCA, brand_description="Cemex", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Obra", created_by=1),
                Location(id_location=NAVE, id_location_type=1,
                         location_description="Nave A", created_by=1),
                Location(id_location=RACK, id_location_type=1,
                         location_description="Rack B", created_by=1),
                Material(id_material=MATERIAL, material_description="Cemento",
                         id_unit=1, id_brand=MARCA, id_product_family=FAMILIA,
                         created_by=1),
            ])
            db.flush()
            sembrar_actor(db, id_proyect=PROYECTO, id_status=ESTATUS)
            db.add(Invoice(
                id_invoice=COMPRA, id_customer_supplier=EMPRESA,
                id_issuer_customer_supplier=CLIENTE, id_proyect=PROYECTO,
                id_status=ESTATUS, invoice_status="timbrada",
                tax_certification_supplier=CLIENTE, apply_tax=False,
                total=Decimal("0"), currency="MXN", created_by=1))
            db.flush()
            db.add_all([
                # Con control por lote: es lo que caduca.
                Product(id_product=CEMENTO, id_invoice=COMPRA, id_location=NAVE,
                        id_material=MATERIAL,
                        is_directly_related_to_product_service=True,
                        product_code="CEM-50", descripcion="Cemento 50kg",
                        stock_purpose="mercancia", tracking_mode="fungible",
                        lot_control=True, gross_price=Decimal("210.00"),
                        created_by=1),
                # Sin control: es lo que no caduca, y tiene que seguir igual que
                # siempre.
                Product(id_product=TORNILLO, id_invoice=COMPRA, id_location=NAVE,
                        id_material=MATERIAL,
                        is_directly_related_to_product_service=True,
                        product_code="TOR-14", descripcion="Tornillo 1/4",
                        stock_purpose="mercancia", tracking_mode="fungible",
                        gross_price=Decimal("2.00"), created_by=1),
            ])

    def recibir(self, cantidad, *, codigo, vence=None, id_location=NAVE,
                id_product=CEMENTO, clave=None):
        carga = {
            "movement_type": "receive",
            "quantity": cantidad,
            "id_location": id_location,
            "reason": "Compra",
            "idempotency_key": clave or f"in:{id_product}:{codigo}:{id_location}:{cantidad}",
        }
        if codigo is not None:
            carga["lot"] = {"lot_code": codigo}
            if vence is not None:
                carga["lot"]["expiry_date"] = vence
        return apply_inventory_movement(id_product, carga, ACTOR)

    def sacar(self, cantidad, *, id_location=NAVE, id_product=CEMENTO,
              lote=None, clave=None):
        carga = {
            "movement_type": "issue",
            "quantity": cantidad,
            "id_location": id_location,
            "reason": "Venta",
            "idempotency_key": clave or f"out:{id_product}:{id_location}:{cantidad}",
        }
        if lote is not None:
            carga["lot"] = {"id_inventory_lot": lote}
        return apply_inventory_movement(id_product, carga, ACTOR)

    def saldos(self, id_product=CEMENTO):
        """{codigo del lote: cuanto queda}."""
        r = lotes_del_producto(id_product, ACTOR)
        return {x["lot_code"]: x["quantity"] for x in r["items"]}

    def en_dias(self, dias):
        return (date.today() + timedelta(days=dias)).isoformat()


class TestPrimeroLoQueVencePrimero(BaseLotes):

    def test_an_entry_creates_its_lot(self):
        self.recibir(100, codigo="L-441", vence=self.en_dias(120))
        self.assertEqual({"L-441": 100}, self.saldos())

    def test_the_exit_takes_from_the_lot_that_expires_first(self):
        """Es lo unico que reduce la merma por caducidad."""
        self.recibir(100, codigo="L-508", vence=self.en_dias(200))
        self.recibir(100, codigo="L-441", vence=self.en_dias(30))

        self.sacar(60)

        # Sale del que vence en 30 dias, aunque llego despues.
        self.assertEqual({"L-441": 40, "L-508": 100}, self.saldos())

    def test_an_exit_can_span_several_lots(self):
        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        self.recibir(50, codigo="L-508", vence=self.en_dias(60))
        self.recibir(50, codigo="L-600", vence=self.en_dias(90))

        self.sacar(120)

        self.assertEqual({"L-441": 0, "L-508": 0, "L-600": 30}, self.saldos())

    def test_a_lot_without_a_date_goes_last(self):
        """No es que dure para siempre: uno con fecha siempre es mas urgente."""
        self.recibir(50, codigo="SIN-FECHA")
        self.recibir(50, codigo="L-441", vence=self.en_dias(300))

        self.sacar(50)

        self.assertEqual({"L-441": 0, "SIN-FECHA": 50}, self.saldos())

    def test_a_named_lot_is_respected(self):
        """A veces hay que sacar ESE: el que el cliente devolvio, el que reclaman."""
        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        self.recibir(50, codigo="L-508", vence=self.en_dias(200))
        id_508 = next(x["id_inventory_lot"] for x in
                      lotes_del_producto(CEMENTO, ACTOR)["items"]
                      if x["lot_code"] == "L-508")

        self.sacar(20, lote=id_508)

        self.assertEqual({"L-441": 50, "L-508": 30}, self.saldos())

    def test_lots_are_kept_apart_by_location(self):
        """Sacar primero lo que vence antes manda al sitio equivocado sin esto."""
        self.recibir(40, codigo="L-441", vence=self.en_dias(30), id_location=NAVE)
        self.recibir(40, codigo="L-441", vence=self.en_dias(30), id_location=RACK,
                     clave="in:rack")

        self.sacar(30, id_location=RACK, clave="out:rack")

        lote = lotes_del_producto(CEMENTO, ACTOR)["items"][0]
        por_sitio = {x["id_location"]: x["quantity"] for x in lote["locations"]}
        self.assertEqual({NAVE: 40, RACK: 10}, por_sitio)


class TestElMismoLoteQueLlegaDosVeces(BaseLotes):

    def test_receiving_the_same_code_twice_adds_to_the_same_lot(self):
        """Con dos vivos, la mitad de las salidas descontaria de uno y la mitad del otro."""
        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        self.recibir(30, codigo="L-441", vence=self.en_dias(30), clave="in:2")

        r = lotes_del_producto(CEMENTO, ACTOR)
        self.assertEqual(1, r["total"])
        self.assertEqual(80, r["items"][0]["quantity"])

    def test_the_code_is_the_same_lot_whatever_the_casing(self):
        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        self.recibir(30, codigo="l-441", vence=self.en_dias(30), clave="in:2")
        self.assertEqual(1, lotes_del_producto(CEMENTO, ACTOR)["total"])

    def test_a_different_date_for_the_same_code_is_refused(self):
        """Casi siempre es un dedazo, y cambia en silencio el orden de salida."""
        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        with self.assertRaises(AppError) as caja:
            self.recibir(30, codigo="L-441", vence=self.en_dias(90), clave="in:2")
        self.assertEqual("errors.lot_expiry_mismatch", caja.exception.message_key)

    def test_an_entry_without_a_lot_is_refused_when_the_product_tracks_them(self):
        with self.assertRaises(AppError) as caja:
            self.recibir(50, codigo=None)
        self.assertEqual("errors.required_field", caja.exception.message_key)
        self.assertEqual("lot_code", caja.exception.meta.get("field"))


class TestElDesgloseCuadraConElSaldo(BaseLotes):

    def test_the_ledger_row_says_which_lots_it_moved(self):
        """El libro escribe un renglon por movimiento; sin esto no dice de donde salio."""
        from sqlalchemy import select

        from app.models.inventory_lot import NmInventoryLedgerLot

        self.recibir(50, codigo="L-441", vence=self.en_dias(30))
        self.recibir(50, codigo="L-508", vence=self.en_dias(60))
        movimiento, _ = self.sacar(70)

        with transaction_context() as db:
            desglose = db.scalars(select(NmInventoryLedgerLot).where(
                NmInventoryLedgerLot.id_inventory_ledger
                == movimiento["id_inventory_ledger"]
            )).all()

        self.assertEqual(2, len(desglose))
        self.assertEqual(-70, sum(x.quantity_delta for x in desglose))

    def test_the_lot_breakdown_matches_the_product_balance(self):
        self.recibir(100, codigo="L-441", vence=self.en_dias(30))
        self.recibir(50, codigo="L-508", vence=self.en_dias(60))
        self.sacar(120)

        cuadre = cuadre_de_lotes(CEMENTO, ACTOR)
        self.assertTrue(cuadre["balanced"], cuadre["differences"])

    def test_taking_more_than_the_lots_hold_is_refused(self):
        self.recibir(20, codigo="L-441", vence=self.en_dias(30))
        with self.assertRaises(AppError) as caja:
            self.sacar(30)
        # El guardia del saldo salta primero, que es el que ya existia.
        self.assertEqual("errors.inventory_insufficient_stock",
                         caja.exception.message_key)

    def test_nothing_is_written_when_the_exit_is_refused(self):
        self.recibir(20, codigo="L-441", vence=self.en_dias(30))
        with self.assertRaises(AppError):
            self.sacar(30)
        self.assertEqual({"L-441": 20}, self.saldos())
        self.assertTrue(cuadre_de_lotes(CEMENTO, ACTOR)["balanced"])


class TestLoQueNoLlevaLotes(BaseLotes):
    """`lot_control` nace apagado, asi que nada de lo que ya existe cambia."""

    def test_a_product_without_lot_control_moves_as_always(self):
        self.recibir(100, codigo=None, id_product=TORNILLO)
        self.sacar(30, id_product=TORNILLO)
        self.assertEqual(0, lotes_del_producto(TORNILLO, ACTOR)["total"])

    def test_naming_a_lot_on_something_that_does_not_track_them_is_refused(self):
        """Casi siempre es el producto equivocado; ignorarlo lo dejaria pasar."""
        with self.assertRaises(AppError) as caja:
            self.recibir(10, codigo="L-441", id_product=TORNILLO)
        self.assertEqual("errors.lot_not_applicable", caja.exception.message_key)


class TestLoQueVence(BaseLotes):

    def test_what_already_expired_is_reported_apart(self):
        """Se da de baja; lo que esta por vencer se saca antes. Dos acciones."""
        self.recibir(40, codigo="L-VIEJO", vence=self.en_dias(10))
        self.recibir(40, codigo="L-NUEVO", vence=self.en_dias(300), clave="in:2")

        # Se atrasa la fecha: no se puede recibir algo ya vencido, asi que para
        # probarlo hay que dejar pasar el tiempo, y aqui se simula.
        from app.models.inventory_lot import InventoryLot
        from sqlalchemy import select
        with transaction_context() as db:
            viejo = db.scalars(select(InventoryLot).where(
                InventoryLot.lot_code == "L-VIEJO")).first()
            viejo.expiry_date = date.today() - timedelta(days=2)

        r = por_caducar(ACTOR, dias=30)
        self.assertEqual(["L-VIEJO"], [x["lot_code"] for x in r["expired"]])
        self.assertEqual(40, r["expired_quantity"])
        self.assertEqual([], r["expiring_soon"])

    def test_what_expires_within_the_window_is_listed(self):
        self.recibir(40, codigo="L-PRONTO", vence=self.en_dias(10))
        self.recibir(40, codigo="L-LEJOS", vence=self.en_dias(300), clave="in:2")

        r = por_caducar(ACTOR, dias=30)
        self.assertEqual(["L-PRONTO"], [x["lot_code"] for x in r["expiring_soon"]])

    def test_a_lot_with_nothing_left_is_not_reported(self):
        """Un lote agotado no hay que sacarlo antes: ya salio."""
        self.recibir(40, codigo="L-PRONTO", vence=self.en_dias(10))
        self.sacar(40)
        r = por_caducar(ACTOR, dias=30)
        self.assertEqual([], r["expiring_soon"])
        self.assertEqual([], r["expired"])

    def test_each_row_says_how_many_days_are_left(self):
        self.recibir(40, codigo="L-PRONTO", vence=self.en_dias(10))
        r = por_caducar(ACTOR, dias=30)
        self.assertEqual(10, r["expiring_soon"][0]["days_to_expiry"])


class TestEncenderElControlNoDejaExistenciaFuera(BaseLotes):
    """Encender el control por lote no es escribir una columna.

    Como se encontro
    ----------------
    Probando contra Postgres se encendio `lot_control` en un producto que YA
    tenia una unidad, y el cuadre salio en falso:

        {'balanced': False, 'differences':
         [{'id_location': 1, 'stock': 1, 'in_lots': 0, 'difference': 1}]}

    Esa unidad queda fuera de todo lote. Y como la salida se sirve de los lotes,
    no se puede despachar: el saldo dice que esta y los lotes dicen que no. El
    almacen se queda con existencia que solo sale con un ajuste, que es la
    operacion que tapa faltantes.

    Lo que estas pruebas fijan:

    * **encender crea un lote de APERTURA** con lo que ya habia en cada
      ubicacion, y el cuadre sigue cuadrando;
    * **ese lote no lleva fecha**, porque nadie la sabe -es justo la informacion
      que no se llevaba-, y sin fecha va al final del orden de salida: primero se
      despacha lo que si tiene fecha conocida;
    * **la columna no se escribe por el CRUD.** Es el camino por el que el fallo
      entraba.
    """

    def _encender(self, id_product=TORNILLO, **extra):
        from app.services.inventory_lot_service import encender_control_de_lotes

        return encender_control_de_lotes(id_product, extra, ACTOR)

    def test_turning_it_on_with_stock_creates_an_opening_lot(self):
        self.recibir(40, codigo=None, id_product=TORNILLO)

        r = self._encender()

        self.assertIsNotNone(r["opening_lot"])
        self.assertEqual({"APERTURA": 40}, self.saldos(TORNILLO))

    def test_the_balance_still_reconciles_after_turning_it_on(self):
        """Es la comprobacion que salio en falso y motivo todo esto."""
        self.recibir(40, codigo=None, id_product=TORNILLO)
        self._encender()
        self.assertTrue(cuadre_de_lotes(TORNILLO, ACTOR)["balanced"])

    def test_the_opening_stock_can_still_be_taken_out(self):
        """Sin el lote de apertura, esas unidades solo salian con un ajuste."""
        self.recibir(40, codigo=None, id_product=TORNILLO)
        self._encender()

        self.sacar(15, id_product=TORNILLO, clave="out:apertura")

        self.assertEqual({"APERTURA": 25}, self.saldos(TORNILLO))

    def test_the_opening_lot_has_no_date_and_goes_last(self):
        """Nadie sabe cuando caduca: primero sale lo que si tiene fecha."""
        self.recibir(40, codigo=None, id_product=TORNILLO)
        self._encender()
        self.recibir(40, codigo="L-NUEVO", vence=self.en_dias(20),
                     id_product=TORNILLO, clave="in:nuevo")

        self.sacar(40, id_product=TORNILLO, clave="out:orden")

        self.assertEqual({"APERTURA": 40, "L-NUEVO": 0}, self.saldos(TORNILLO))

    def test_turning_it_on_without_stock_creates_nothing(self):
        r = self._encender()
        self.assertIsNone(r["opening_lot"])
        self.assertEqual(0, lotes_del_producto(TORNILLO, ACTOR)["total"])

    def test_turning_it_on_twice_is_harmless(self):
        self.recibir(40, codigo=None, id_product=TORNILLO)
        self._encender()
        segunda = self._encender()
        self.assertTrue(segunda["already_on"])
        self.assertEqual({"APERTURA": 40}, self.saldos(TORNILLO))

    def test_it_cannot_be_turned_on_for_a_serialized_product(self):
        """Ya hay una fila por unidad: seria la misma cosa por dos caminos."""
        with transaction_context() as db:
            db.get(Product, TORNILLO).tracking_mode = "serializado"

        with self.assertRaises(AppError) as caja:
            self._encender()
        self.assertEqual("errors.lot_control_not_for_serialized",
                         caja.exception.message_key)

    def test_the_column_cannot_be_written_through_the_crud(self):
        """Es el camino por el que la existencia se quedaba fuera de todo lote."""
        from app.services.product_service import ProductService

        with self.assertRaises(AppError) as caja:
            ProductService.update(TORNILLO, {"lot_control": True}, user_id=1)
        self.assertEqual("errors.lot_control_needs_its_own_endpoint",
                         caja.exception.message_key)

    def test_an_edit_that_sends_the_unchanged_flag_back_still_saves(self):
        """El formulario de edicion devuelve el registro completo, `lot_control` incluido.

        Rechazarlo aunque no cambiara hacia imposible guardar CUALQUIER edicion
        de un producto (se veia como un cuadro rojo al editar una herramienta).
        """
        from app.services.product_service import ProductService

        ProductService.update(
            TORNILLO, {"lot_control": False, "note": "editado desde el formulario"},
            user_id=1)
        with transaction_context() as db:
            producto = db.get(Product, TORNILLO)
            self.assertEqual("editado desde el formulario", producto.note)
            self.assertFalse(producto.lot_control)

    def test_turning_it_off_keeps_the_lots(self):
        """Un lote es el rastro que liga el anaquel con la factura de compra."""
        from app.services.inventory_lot_service import apagar_control_de_lotes

        self.recibir(40, codigo=None, id_product=TORNILLO)
        self._encender()
        apagar_control_de_lotes(TORNILLO, ACTOR)

        self.assertEqual(1, lotes_del_producto(TORNILLO, ACTOR)["total"])

    def test_turning_it_off_and_on_again_does_not_double_the_lots(self):
        """Apagar, recibir sin lote y volver a encender sumaba la existencia otra vez."""
        from app.services.inventory_lot_service import apagar_control_de_lotes

        self.recibir(15, codigo=None, id_product=TORNILLO)
        self._encender()
        apagar_control_de_lotes(TORNILLO, ACTOR)
        self.recibir(5, codigo=None, id_product=TORNILLO, clave="in:sin-lote")

        self._encender()

        self.assertEqual({"APERTURA": 20}, self.saldos(TORNILLO))
        self.assertTrue(cuadre_de_lotes(TORNILLO, ACTOR)["balanced"])


if __name__ == "__main__":
    unittest.main()
