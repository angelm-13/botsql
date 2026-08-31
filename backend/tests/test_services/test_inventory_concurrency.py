"""Concurrencia de almacen contra PostgreSQL real.

La auditoria externa dejo este control en rojo por falta de datos: "Smoke
inventario DB: bloqueado, no habia producto local asociado a factura con
proyecto". Aqui se monta ese dato y se ejecuta.

Corre solo contra PostgreSQL, y se omite con motivo en SQLite. No es una
comodidad: SQLite serializa las escrituras, asi que dos hilos nunca compiten
por la misma fila y los dos errores que se buscan no pueden reproducirse.
Ejecutarla en SQLite daria verde sin haber probado nada, que es peor que
omitirla.

Lo que se busca no es que "no truene", sino:

* **sobreventa**: dos salidas simultaneas que juntas superan la existencia y
  ambas pasan, dejando el saldo negativo;
* **actualizacion perdida**: dos movimientos que leen el mismo saldo y el
  segundo pisa al primero, de modo que una salida desaparece del saldo aunque
  siga en el libro;
* **doble aplicacion**: la misma llave de idempotencia aplicada dos veces
  porque las dos llamadas pasaron juntas por el hueco entre consultar y
  escribir.

Ninguno deja error en la bitacora. Se descubren contando el almacen.
"""

from __future__ import annotations

import threading
import unittest
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    Brand, CustomerSupplier, Invoice, Location, LocationType, Material,
    Product, ProductFamily, Proyect, Status, Unit,
)
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.session import engine, transaction_context
from app.services.inventory_service import (
    apply_inventory_movement,
    reconcile_product_stock,
)
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}
PRINCIPAL = 10
CLIENT = 20
ALMACEN = 2
PRODUCTO = 60
FACTURA = 50
EXISTENCIA = 12


def _motivo_de_omision() -> str:
    if engine.dialect.name != "postgresql":
        return (
            f"la concurrencia solo es medible en PostgreSQL; aqui corre "
            f"{engine.dialect.name}, que serializa las escrituras y daria verde "
            f"sin probar nada"
        )
    return ""


class TestInventarioConcurrente(BackendTestCase):
    def setUp(self):
        super().setUp()
        motivo = _motivo_de_omision()
        if motivo:
            self.skipTest(motivo)

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
                Location(id_location=ALMACEN, id_location_type=1,
                         location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Cemento", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(
                id_invoice=FACTURA, id_customer_supplier=CLIENT,
                id_issuer_customer_supplier=PRINCIPAL, id_proyect=30, id_status=40,
                invoice_status="pendiente", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, total=Decimal("0"), currency="MXN", created_by=1,
            ))
            db.flush()
            db.add(Product(
                id_product=PRODUCTO, id_invoice=FACTURA, id_location=ALMACEN, id_material=1,
                is_directly_related_to_product_service=False, cantidad=EXISTENCIA, created_by=1,
            ))
            db.flush()
            db.add(InventoryStock(id_product=PRODUCTO, id_location=ALMACEN,
                                  quantity=EXISTENCIA, created_by=1))

    def _a_la_vez(self, cuantos, trabajo):
        """Lanza `cuantos` hilos que arrancan al mismo tiempo.

        La barrera es lo que hace la prueba: sin ella los hilos se escalonan y
        se estaria midiendo una secuencia, no una carrera.
        """
        resultados = [None] * cuantos
        barrera = threading.Barrier(cuantos)

        def correr(indice):
            barrera.wait()
            try:
                trabajo(indice)
                resultados[indice] = "aplicado"
            except Exception as error:
                resultados[indice] = getattr(error, "message_key", type(error).__name__)

        hilos = [threading.Thread(target=correr, args=(i,)) for i in range(cuantos)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        return resultados

    def _existencia(self):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(
                id_product=PRODUCTO, id_location=ALMACEN).first()
            return int(fila.quantity) if fila else 0

    def test_simultaneous_issues_never_oversell(self):
        """Mas salidas que existencia, todas a la vez."""
        intentos = EXISTENCIA + 6

        resultados = self._a_la_vez(intentos, lambda i: apply_inventory_movement(PRODUCTO, {
            "movement_type": "issue", "quantity": 1,
            "idempotency_key": f"conc-{i}", "id_location": ALMACEN,
            "reason": "Prueba de concurrencia",
        }, ACTOR))

        aplicados = resultados.count("aplicado")
        self.assertEqual(EXISTENCIA, aplicados,
                         "se aplicaron exactamente las unidades que habia")
        self.assertEqual(0, self._existencia(), "la existencia queda en cero, no negativa")
        self.assertEqual(
            {"errors.inventory_insufficient_stock"},
            set(resultados) - {"aplicado"},
            "los rechazos son por falta de existencia, no por un error tecnico",
        )

    def test_no_applied_movement_is_lost_from_the_balance(self):
        """La actualizacion perdida: el libro y el saldo tienen que cuadrar."""
        self._a_la_vez(8, lambda i: apply_inventory_movement(PRODUCTO, {
            "movement_type": "issue", "quantity": 1,
            "idempotency_key": f"perdida-{i}", "id_location": ALMACEN,
            "reason": "Prueba de concurrencia",
        }, ACTOR))

        with transaction_context() as db:
            suma_libro = int(db.scalar(
                select(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
                .where(InventoryLedger.id_product == PRODUCTO)
                .where(InventoryLedger.id_location == ALMACEN)
            ) or 0)

        self.assertEqual(EXISTENCIA + suma_libro, self._existencia(),
                         "cada delta del libro se refleja en el saldo")
        self.assertTrue(reconcile_product_stock(PRODUCTO, ACTOR)["is_reconciled"])

    def test_the_same_key_applied_at_once_moves_stock_only_once(self):
        """Cinco llamadas simultaneas con la misma llave.

        Antes las cuatro que perdian la carrera recibian un IntegrityError en
        crudo: justo el cliente que reintenta -para quien existe la llave- veia
        fallar su reintento, aunque el movimiento si estuviera aplicado.
        """
        antes = self._existencia()

        resultados = self._a_la_vez(5, lambda i: apply_inventory_movement(PRODUCTO, {
            "movement_type": "receive", "quantity": 2,
            "idempotency_key": "misma-llave", "id_location": ALMACEN,
            "reason": "Prueba de idempotencia concurrente",
        }, ACTOR))

        self.assertEqual(["aplicado"] * 5, resultados,
                         "las cinco responden bien, ninguna con error de integridad")
        self.assertEqual(antes + 2, self._existencia(),
                         "pero el almacen se movio una sola vez")

    def test_a_reused_key_on_another_product_is_a_conflict(self):
        """La llave no puede saltar de producto: seria un movimiento distinto."""
        apply_inventory_movement(PRODUCTO, {
            "movement_type": "receive", "quantity": 1,
            "idempotency_key": "llave-compartida", "id_location": ALMACEN,
            "reason": "Primera",
        }, ACTOR)

        with transaction_context() as db:
            db.add(Product(
                id_product=PRODUCTO + 1, id_invoice=FACTURA, id_location=ALMACEN,
                id_material=1, is_directly_related_to_product_service=False,
                cantidad=0, created_by=1,
            ))

        from app.utils.errors import AppError
        with self.assertRaises(AppError) as raised:
            apply_inventory_movement(PRODUCTO + 1, {
                "movement_type": "receive", "quantity": 1,
                "idempotency_key": "llave-compartida", "id_location": ALMACEN,
                "reason": "Segunda",
            }, ACTOR)

        self.assertEqual("errors.idempotency_conflict", raised.exception.message_key)


if __name__ == "__main__":
    unittest.main()
