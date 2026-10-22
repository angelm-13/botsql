"""Una llave de idempotencia repetida con OTROS datos es un conflicto.

Por que existe este archivo
---------------------------
Una llave de idempotencia promete una cosa: repetir la MISMA peticion no la
aplica dos veces. No promete nada sobre repetir la llave con datos distintos, y
eso era justo lo que pasaba: el guardia solo comparaba a que producto -o a que
factura- pertenecia el registro guardado.

Medido antes del arreglo, y es lo peor que puede pasar en cada modulo:

* **almacen** - entrada de 10 unidades con la llave "K"; despues 99 con la
  misma llave. Devolvia el asiento de 10 y contestaba que todo bien. El
  almacenista cree que entraron 99;
* **facturacion** - abono de 100 con la llave "K"; despues 900 con la misma
  llave. Devolvia el abono de 100 y contestaba que todo bien. El cliente cree
  que abono 900 y la cuenta tiene 100.

El caso no es raro. Es exactamente lo que pasa cuando la primera llamada llevaba
un error de captura y alguien reintenta con el dato corregido reusando la misma
llave, que es lo que hace un cliente que trata la llave como "identificador de
esta operacion" en vez de "huella de esta peticion".

Lo que estas pruebas fijan:

* **misma llave y misma peticion**: se devuelve lo guardado y no se aplica dos
  veces. Es la promesa de la idempotencia y ya funcionaba;
* **misma llave y otra peticion**: 409, y el error dice que se habia guardado
  con esa llave, para que quien reintento pueda ver que la estaba reusando;
* **el efecto no se duplica ni se pierde**: el saldo y el abono siguen siendo
  los de la primera peticion.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import (
    CustomerSupplier,
    Invoice,
    Location,
    LocationType,
    Material,
    Brand,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.session import transaction_context
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

EMISOR, CLIENTE, PROYECTO, ESTATUS = 10, 20, 30, 40
NAVE_A, NAVE_B, MATERIAL, COMPRA, PRODUCTO = 50, 51, 52, 53, 54


class BaseIdempotencia(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMISOR, name="EMISOR DEMO SA DE CV",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="CLIENTE DEMO SA DE CV",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1,
                              product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto demo", created_by=1),
                Location(id_location=NAVE_A, id_location_type=1,
                         location_description="Nave A", created_by=1),
                Location(id_location=NAVE_B, id_location_type=1,
                         location_description="Nave B", created_by=1),
                Material(id_material=MATERIAL, material_description="Generico",
                         id_unit=1, id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(
                id_invoice=COMPRA, id_customer_supplier=EMISOR,
                id_issuer_customer_supplier=CLIENTE, id_proyect=PROYECTO,
                id_status=ESTATUS, invoice_status="borrador",
                tax_certification_supplier=CLIENTE, apply_tax=False, created_by=1))
            db.flush()
            db.add(Product(
                id_product=PRODUCTO, id_invoice=COMPRA, id_location=NAVE_A,
                id_material=MATERIAL, is_directly_related_to_product_service=True,
                product_code="TOR-500", descripcion="Tornillo",
                stock_purpose="mercancia", tracking_mode="fungible",
                gross_price=Decimal("10.00"), created_by=1))

    def _conflicto(self, funcion, *args, **kwargs):
        with self.assertRaises(AppError) as caja:
            funcion(*args, **kwargs)
        self.assertEqual("errors.idempotency_conflict", caja.exception.message_key,
                         f"revento por `{caja.exception.message_key}`")
        self.assertEqual(409, caja.exception.status_code)
        return caja.exception


class TestLaLlaveDelAlmacen(BaseIdempotencia):

    def _entrada(self, cantidad, llave, **extra):
        from app.services.inventory_service import apply_inventory_movement

        carga = {"movement_type": "receive", "quantity": cantidad,
                 "id_location": NAVE_A, "reference_type": "purchase",
                 "reference_id": str(COMPRA), "idempotency_key": llave,
                 "reason": "Compra"}
        carga.update(extra)
        return apply_inventory_movement(PRODUCTO, carga, ACTOR)

    def _saldo(self):
        from app.services.inventory_service import product_stock

        return product_stock(PRODUCTO, ACTOR)["total"]

    def test_the_same_request_twice_is_applied_once(self):
        """La promesa de la idempotencia, que ya funcionaba."""
        primero, creado = self._entrada(10, "K")
        self.assertTrue(creado)
        segundo, recreado = self._entrada(10, "K")
        self.assertFalse(recreado)
        self.assertEqual(primero["id_inventory_ledger"],
                         segundo["id_inventory_ledger"])
        self.assertEqual(10, self._saldo())

    def test_the_same_key_with_another_quantity_is_a_conflict(self):
        """Devolvia el asiento de 10 y contestaba que habian entrado 99."""
        self._entrada(10, "K")
        error = self._conflicto(self._entrada, 99, "K")
        # El error dice que estaba guardado: sin eso, un 409 a secas no explica
        # que la llave se estaba reusando.
        self.assertEqual(10, error.meta["stored"]["quantity_delta"])
        self.assertEqual(10, self._saldo(), "el saldo no puede haber cambiado")

    def test_the_same_key_with_another_movement_type_is_a_conflict(self):
        self._entrada(10, "K")
        self._conflicto(self._entrada, 10, "K", movement_type="issue",
                        reference_type="sale")

    def test_the_same_key_in_another_location_is_a_conflict(self):
        """Recibir en Nave A y despues en Nave B no es la misma peticion."""
        self._entrada(10, "K")
        self._conflicto(self._entrada, 10, "K", id_location=NAVE_B)

    def test_the_same_key_against_another_document_is_a_conflict(self):
        """La referencia decide como se clasifica, asi que es parte de la peticion."""
        self._entrada(10, "K")
        self._conflicto(self._entrada, 10, "K", reference_id="999")

    def test_a_corrected_reason_is_not_another_request(self):
        """El motivo es texto libre: arreglar una falta no es otra peticion."""
        self._entrada(20, "entrada-previa")
        primero, _ = self._entrada(10, "K", movement_type="expiry",
                                   reason="Se pasaron de fexa")
        segundo, recreado = self._entrada(10, "K", movement_type="expiry",
                                          reason="Se pasaron de fecha")
        self.assertFalse(recreado)
        self.assertEqual(primero["id_inventory_ledger"],
                         segundo["id_inventory_ledger"])

    def test_the_same_key_on_another_product_is_still_a_conflict(self):
        """Ya funcionaba; se fija para que el arreglo no lo pierda."""
        with transaction_context() as db:
            db.add(Product(
                id_product=PRODUCTO + 1, id_invoice=COMPRA, id_location=NAVE_A,
                id_material=MATERIAL, is_directly_related_to_product_service=True,
                product_code="OTRO", descripcion="Otro",
                stock_purpose="mercancia", gross_price=Decimal("1.00"),
                created_by=1))

        from app.services.inventory_service import apply_inventory_movement

        self._entrada(10, "K")
        self._conflicto(apply_inventory_movement, PRODUCTO + 1, {
            "movement_type": "receive", "quantity": 10, "id_location": NAVE_A,
            "reference_type": "purchase", "reference_id": str(COMPRA),
            "reason": "Compra", "idempotency_key": "K"}, ACTOR)


class TestLaLlaveDelTraslado(BaseIdempotencia):

    def setUp(self):
        super().setUp()
        from app.services.inventory_service import apply_inventory_movement

        apply_inventory_movement(PRODUCTO, {
            "movement_type": "receive", "quantity": 40, "id_location": NAVE_A,
            "reference_type": "purchase", "reference_id": str(COMPRA),
            "reason": "Compra", "idempotency_key": "entrada"}, ACTOR)

    def _trasladar(self, cantidad, llave, **extra):
        from app.services.inventory_service import transfer_inventory

        carga = {"quantity": cantidad, "id_location_from": NAVE_A,
                 "id_location_to": NAVE_B, "reason": "Reacomodo",
                 "idempotency_key": llave}
        carga.update(extra)
        return transfer_inventory(PRODUCTO, carga, ACTOR)

    def _por_ubicacion(self):
        from app.services.inventory_service import product_stock

        return {u["id_location"]: u["quantity"]
                for u in product_stock(PRODUCTO, ACTOR)["items"]}

    def test_the_same_transfer_twice_moves_it_once(self):
        self._trasladar(10, "T")
        self._trasladar(10, "T")
        self.assertEqual({NAVE_A: 30, NAVE_B: 10}, self._por_ubicacion())

    def test_the_same_key_with_another_quantity_is_a_conflict(self):
        """Devolvia el par de 10 y contestaba que se habian movido 99."""
        self._trasladar(10, "T")
        error = self._conflicto(self._trasladar, 25, "T")
        self.assertEqual(10, error.meta["stored"]["quantity"])
        self.assertEqual({NAVE_A: 30, NAVE_B: 10}, self._por_ubicacion(),
                         "el reparto no puede haber cambiado")

    def test_the_same_key_from_another_origin_is_a_conflict(self):
        self._trasladar(10, "T")
        self._conflicto(self._trasladar, 10, "T",
                        id_location_from=NAVE_B, id_location_to=NAVE_A)


class TestLaLlaveDelAbono(BaseIdempotencia):

    def _factura_en_parcialidades(self):
        from app.services.manual_invoice_service import create_manual_invoice
        from app.services.stamping import FakeStampingProvider, stamp_invoice

        r = create_manual_invoice({
            "id_proyect": PROYECTO, "id_customer_supplier": CLIENTE,
            "id_issuer_customer_supplier": EMISOR, "id_status": ESTATUS,
            # PPD con forma 99: es lo que exige el CFDI para parcialidades, y
            # sin eso la factura no acepta abonos.
            "forma_pago": "99", "metodo_pago": "PPD", "uso_cfdi": "G03",
            "tipo_de_comprobante": "I",
            "concepts": [{"description": "Servicio", "quantity": "1",
                          "unit_price": "1000", "sat_product_key": "81111500",
                          "sat_unit_key": "E48"}],
        }, ACTOR)
        id_factura = r["invoice"]["id_invoice"]
        # Timbrado simulado: los abonos exigen factura timbrada, y timbrar de
        # verdad no entra aqui.
        stamp_invoice(id_factura, "st-parcialidades", ACTOR, FakeStampingProvider())
        return id_factura

    def _abonar(self, id_factura, monto, llave, **extra):
        from app.services.invoice_payment_service import register_payment

        carga = {"amount": monto, "payment_form": "03", "currency": "MXN",
                 "idempotency_key": llave}
        carga.update(extra)
        return register_payment(id_factura, carga, ACTOR)

    def _saldo(self, id_factura):
        from app.services.invoice_payment_service import invoice_statement

        return invoice_statement(id_factura, ACTOR)

    def test_the_same_payment_twice_is_charged_once(self):
        id_factura = self._factura_en_parcialidades()
        uno = self._abonar(id_factura, "100", "K")
        self.assertTrue(uno["created"])
        dos = self._abonar(id_factura, "100", "K")
        self.assertFalse(dos["created"])
        self.assertEqual(uno["payment"]["id_invoice_payment"],
                         dos["payment"]["id_invoice_payment"])
        self.assertEqual(1, len(self._saldo(id_factura)["payments"]))

    def test_the_same_key_with_another_amount_is_a_conflict(self):
        """Devolvia el abono de 100 y contestaba que se habian abonado 900."""
        id_factura = self._factura_en_parcialidades()
        self._abonar(id_factura, "100", "K")
        error = self._conflicto(self._abonar, id_factura, "900", "K")
        self.assertEqual(Decimal("100.00"), Decimal(error.meta["stored"]["amount"]))

        estado = self._saldo(id_factura)
        self.assertEqual(1, len(estado["payments"]), "no puede haber dos abonos")
        self.assertEqual(Decimal("100.00"),
                         Decimal(str(estado["payments"][0]["amount"])),
                         "el abono guardado sigue siendo el primero")

    def test_the_same_key_with_another_payment_form_is_a_conflict(self):
        id_factura = self._factura_en_parcialidades()
        self._abonar(id_factura, "100", "K")
        self._conflicto(self._abonar, id_factura, "100", "K", payment_form="04")

    def test_omitting_the_currency_is_not_another_request(self):
        """Sin moneda el abono hereda la de la factura; no es otra peticion."""
        id_factura = self._factura_en_parcialidades()
        uno = self._abonar(id_factura, "100", "K")
        from app.services.invoice_payment_service import register_payment

        dos = register_payment(id_factura, {
            "amount": "100", "payment_form": "03", "idempotency_key": "K"}, ACTOR)
        self.assertFalse(dos["created"])
        self.assertEqual(uno["payment"]["id_invoice_payment"],
                         dos["payment"]["id_invoice_payment"])


if __name__ == "__main__":
    unittest.main()
