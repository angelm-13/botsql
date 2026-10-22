"""Los lotes viajan con la existencia: en un traspaso y en la devolucion de un vale.

Hallazgos de la auditoria de inventario (2026-10-19), reproducidos antes de corregirse:

* un traspaso movia `inventory_stock` y dejaba los saldos por lote en el origen: el
  stock decia 40 en el destino y los lotes 0, y la primera salida desde ahi fallaba
  con `lot_insufficient_stock`;
* devolver un vale de un producto con lotes daba `required_field lot_code` y se
  revertia todo: la salida se sirve del lote que vence primero, pero la entrada de
  regreso exigia un lote que nadie escribio.

Lo que estas pruebas fijan
--------------------------
* un traspaso saca de los lotes del origen -por fecha, o el que se nombre- y los
  MISMOS lotes entran al destino, con su desglose en el libro de las dos puntas;
* una devolucion repone cada lote con lo que dio la salida, y lo que la salida no
  explica entra al lote de apertura;
* en ambos casos el desglose por lote cuadra con el stock, y lo que no tiene lotes
  no cambia.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import Product
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_lot import NmInventoryLedgerLot
from app.models.session import transaction_context
from app.services.inventory_lot_service import cuadre_de_lotes, lotes_del_producto
from app.services.inventory_service import apply_inventory_movement, transfer_inventory
from app.services.warehouse_voucher_service import CERRADO, devolver_renglon
from app.utils.errors import AppError
from tests.test_services import test_vale_de_almacen as vale
from tests.test_services.test_vale_de_almacen import ACTOR, CEMENTO, NAVE, RACK


def _dias(n):
    return (date.today() + timedelta(days=n)).isoformat()


class BaseLotesViajan(vale.BaseVale):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.get(Product, CEMENTO).lot_control = True

    def recibir(self, cantidad, codigo, vence=None, ubicacion=NAVE):
        lote = {"lot_code": codigo}
        if vence:
            lote["expiry_date"] = vence
        return apply_inventory_movement(CEMENTO, {
            "movement_type": "receive", "quantity": cantidad, "id_location": ubicacion,
            "reason": "Compra", "idempotency_key": f"in:{codigo}:{ubicacion}:{cantidad}",
            "lot": lote}, ACTOR)

    def trasladar(self, cantidad, clave="t1", origen=NAVE, destino=RACK, **extra):
        return transfer_inventory(CEMENTO, {
            "quantity": cantidad, "id_location_from": origen, "id_location_to": destino,
            "reason": "Reabasto", "idempotency_key": clave, **extra}, ACTOR)

    def en_lotes(self):
        """{(codigo del lote, ubicacion): cantidad}, sin saldos en cero."""
        salida = {}
        for lote in lotes_del_producto(CEMENTO, ACTOR)["items"]:
            for sitio in lote["locations"]:
                salida[(lote["lot_code"], sitio["id_location"])] = sitio["quantity"]
        return salida

    def id_del_lote(self, codigo):
        return next(l["id_inventory_lot"] for l in lotes_del_producto(CEMENTO, ACTOR)["items"]
                    if l["lot_code"] == codigo)

    def assertCuadra(self):
        cuadre = cuadre_de_lotes(CEMENTO, ACTOR)
        self.assertTrue(cuadre["balanced"], cuadre["differences"])


class TestElTraspasoMueveLosLotes(BaseLotesViajan):

    def test_the_lots_move_with_the_stock_and_the_exit_at_the_destination_works(self):
        self.recibir(100, "L-1")

        self.trasladar(40)

        self.assertEqual({("L-1", NAVE): 60, ("L-1", RACK): 40}, self.en_lotes())
        self.assertCuadra()
        # El caso que antes fallaba con `lot_insufficient_stock`.
        apply_inventory_movement(CEMENTO, {
            "movement_type": "issue", "quantity": 10, "id_location": RACK,
            "reason": "Venta", "idempotency_key": "out-1"}, ACTOR)
        self.assertEqual(30, self.en_lotes()[("L-1", RACK)])
        self.assertCuadra()

    def test_a_transfer_takes_first_what_expires_first_and_the_same_lots_arrive(self):
        self.recibir(30, "L-A", _dias(30))
        self.recibir(50, "L-B", _dias(100))

        self.trasladar(40)

        # L-A vence antes: viaja completo (30) y L-B aporta los 10 que faltan.
        self.assertEqual(
            {("L-B", NAVE): 40, ("L-A", RACK): 30, ("L-B", RACK): 10}, self.en_lotes())
        self.assertCuadra()

    def test_a_named_lot_is_the_one_that_travels(self):
        self.recibir(30, "L-A", _dias(30))
        self.recibir(50, "L-B", _dias(100))

        self.trasladar(20, lot={"id_inventory_lot": self.id_del_lote("L-B")})

        self.assertEqual(
            {("L-A", NAVE): 30, ("L-B", NAVE): 30, ("L-B", RACK): 20}, self.en_lotes())
        self.assertCuadra()

    def test_both_ledger_rows_carry_their_lot_breakdown(self):
        self.recibir(30, "L-A", _dias(30))
        self.recibir(50, "L-B", _dias(100))

        movimientos = self.trasladar(40)[0]["movements"]
        salida, entrada = movimientos

        with transaction_context() as db:
            def desglose(id_ledger):
                filas = db.execute(
                    select(NmInventoryLedgerLot.id_inventory_lot,
                           NmInventoryLedgerLot.quantity_delta)
                    .where(NmInventoryLedgerLot.id_inventory_ledger == id_ledger)
                    .order_by(NmInventoryLedgerLot.id_inventory_lot)).all()
                return [(int(l), int(q)) for l, q in filas]

            a, b = self.id_del_lote("L-A"), self.id_del_lote("L-B")
            self.assertEqual([(a, -30), (b, -10)], desglose(salida["id_inventory_ledger"]))
            self.assertEqual([(a, 30), (b, 10)], desglose(entrada["id_inventory_ledger"]))

    def test_repeating_the_same_key_does_not_move_the_lots_twice(self):
        self.recibir(100, "L-1")
        self.trasladar(40, clave="K")
        antes = self.en_lotes()

        _, creado = self.trasladar(40, clave="K")

        self.assertFalse(creado)
        self.assertEqual(antes, self.en_lotes())

    def test_a_transfer_the_lots_do_not_cover_is_refused_whole(self):
        """Existencia sin lote -el control se encendio despues- no se puede mover a medias."""
        with transaction_context() as db:
            db.get(Product, CEMENTO).lot_control = False
        self.surtir(10, NAVE)
        with transaction_context() as db:
            db.get(Product, CEMENTO).lot_control = True

        with self.assertRaises(AppError) as caja:
            self.trasladar(5)

        self.assertEqual("errors.lot_insufficient_stock", caja.exception.message_key)
        self.assertEqual(10, self._saldo(NAVE))
        self.assertEqual(0, self._saldo(RACK))


class TestElTraspasoDeLoQueNoLlevaLotes(vale.BaseVale):

    def test_a_product_without_lots_transfers_exactly_as_before(self):
        self.surtir(20, NAVE)

        transfer_inventory(CEMENTO, {
            "quantity": 5, "id_location_from": NAVE, "id_location_to": RACK,
            "reason": "Reabasto", "idempotency_key": "t-sin-lotes"}, ACTOR)

        self.assertEqual(15, self._saldo(NAVE))
        self.assertEqual(5, self._saldo(RACK))
        with transaction_context() as db:
            self.assertEqual(0, len(db.scalars(select(NmInventoryLedgerLot)).all()))

    def test_naming_a_lot_on_a_product_without_lots_is_refused(self):
        self.surtir(20, NAVE)

        with self.assertRaises(AppError) as caja:
            transfer_inventory(CEMENTO, {
                "quantity": 5, "id_location_from": NAVE, "id_location_to": RACK,
                "reason": "Reabasto", "idempotency_key": "t-lote",
                "lot": {"lot_code": "L-1"}}, ACTOR)

        self.assertEqual("errors.lot_not_applicable", caja.exception.message_key)
        self.assertEqual(20, self._saldo(NAVE))


class TestLaDevolucionDelValeVuelveASuLote(BaseLotesViajan):

    def _prestar(self, cantidad, ubicacion=RACK):
        r = self._vale([{"id_product": CEMENTO, "quantity": cantidad,
                         "id_location_from": ubicacion}])
        return r["lines"][0]["id_nm_incident_product"]

    def test_the_return_goes_back_to_the_lot_it_came_from(self):
        self.recibir(50, "L-9", ubicacion=RACK)
        id_linea = self._prestar(5)
        self.assertEqual({("L-9", RACK): 45}, self.en_lotes())

        devolver_renglon(id_linea, {}, ACTOR)

        self.assertEqual({("L-9", RACK): 50}, self.en_lotes())
        self.assertEqual(50, self._saldo(RACK))
        self.assertCuadra()

    def test_a_loan_that_spanned_two_lots_returns_to_each_of_them(self):
        self.recibir(3, "L-A", _dias(30), ubicacion=RACK)
        self.recibir(10, "L-B", _dias(90), ubicacion=RACK)
        id_linea = self._prestar(5)
        # Salieron 3 de L-A y 2 de L-B.
        self.assertEqual({("L-B", RACK): 8}, self.en_lotes())

        devolver_renglon(id_linea, {}, ACTOR)

        self.assertEqual({("L-A", RACK): 3, ("L-B", RACK): 10}, self.en_lotes())
        self.assertCuadra()

    def test_a_loan_without_breakdown_returns_to_the_opening_lot(self):
        """Lo migrado -o anterior al control por lote- no dice de que lote salio."""
        self.recibir(50, "L-9", ubicacion=RACK)
        id_linea = self._prestar(5)
        with transaction_context() as db:
            # Se simula un renglon sin desglose: el de la salida del vale.
            salida = db.scalars(select(InventoryLedger).where(
                InventoryLedger.movement_type == "loan")).first()
            for fila in db.scalars(select(NmInventoryLedgerLot).where(
                    NmInventoryLedgerLot.id_inventory_ledger == salida.id_inventory_ledger)):
                db.delete(fila)

        devolver_renglon(id_linea, {}, ACTOR)

        # El saldo del producto vuelve completo; lo que no se pudo ligar va a APERTURA.
        self.assertEqual(50, self._saldo(RACK))
        self.assertEqual({("L-9", RACK): 45, ("APERTURA", RACK): 5}, self.en_lotes())

    def test_the_voucher_closes_and_the_ledger_has_one_return_per_lot(self):
        self.recibir(3, "L-A", _dias(30), ubicacion=RACK)
        self.recibir(10, "L-B", _dias(90), ubicacion=RACK)
        id_linea = self._prestar(5)

        resultado = devolver_renglon(id_linea, {}, ACTOR)

        self.assertEqual(CERRADO, str(resultado["voucher"]["incident_status"]).lower())
        with transaction_context() as db:
            regresos = db.scalars(select(InventoryLedger).where(
                InventoryLedger.movement_type == "return")).all()
            self.assertEqual([3, 2], sorted((int(r.quantity_delta) for r in regresos),
                                            reverse=True))
