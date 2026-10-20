"""Una entrada de existencia por la puerta publica no es un movimiento "normal".

Hallazgo de la auditoria de inventario (2026-10-19): `receive` y `return` por
`POST /product/<id>/inventory-movements` solo pedian el permiso de editar
productos. Sin motivo, sin documento y sin la capacidad `inventory_adjustment`
se podia inflar el saldo por cualquier cantidad -justo lo que el ajuste protege-.

Lo que estas pruebas fijan
--------------------------
* una entrada exige motivo, como el resto de los movimientos sin documento;
* sin la capacidad de ajustar, una entrada solo pasa si cita una orden de compra
  ya recibida con material de este producto, o un vale con una salida suya;
* con la capacidad, o siendo superusuario, pasa igual que siempre;
* el lote se nombra como objeto: un texto suelto se rechaza con el campo que falla.
"""
from __future__ import annotations

import jwt

from app.models import EntityPermission, Product
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.test_api import test_api_purchase_receive as recepcion
from tests.test_api.test_api_purchase_order import PROYECTO_A
from tests.test_services import test_vale_de_almacen as vale
from tests.test_services.test_vale_de_almacen import ACTOR, CEMENTO, NAVE

# Un rol que puede editar productos pero NO ajustar existencias.
SIN_CAPACIDAD = {"id_user": 2, "id_proyect": 30, "id_permission": 99}
CON_CAPACIDAD = {"id_user": 2, "id_proyect": 30, "id_permission": 98}


def _entrada(actor, *, clave, tipo="receive", cantidad=10, razon="Compra", **extra):
    carga = {"movement_type": tipo, "quantity": cantidad, "id_location": NAVE,
             "idempotency_key": clave}
    if razon is not None:
        carga["reason"] = razon
    carga.update(extra)
    return apply_inventory_movement(CEMENTO, carga, actor)


class BaseEntradas(vale.BaseVale):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=98, entity_name="inventory_adjustment",
                                    scope_read=4, scope_update=4, created_by=1))

    def _clave_de_error(self, funcion):
        with self.assertRaises(AppError) as caja:
            funcion()
        return caja.exception.message_key, caja.exception.status_code


class TestUnaEntradaExigeRespaldo(BaseEntradas):

    def test_without_the_capability_a_manual_entry_is_refused(self):
        clave, estado = self._clave_de_error(
            lambda: _entrada(SIN_CAPACIDAD, clave="e1", reference_type="manual"))
        self.assertEqual(("errors.inventory_entry_not_authorized", 403), (clave, estado))
        self.assertEqual(0, self._saldo(NAVE))

    def test_without_the_capability_a_return_is_refused_too(self):
        clave, estado = self._clave_de_error(
            lambda: _entrada(SIN_CAPACIDAD, clave="e2", tipo="return"))
        self.assertEqual(("errors.inventory_entry_not_authorized", 403), (clave, estado))

    def test_an_entry_needs_a_reason_even_with_the_capability(self):
        clave, estado = self._clave_de_error(
            lambda: _entrada(CON_CAPACIDAD, clave="e3", razon=None))
        self.assertEqual(("errors.inventory_reason_required", 400), (clave, estado))

    def test_with_the_capability_the_entry_goes_through(self):
        movimiento, creado = _entrada(CON_CAPACIDAD, clave="e4", reference_type="manual")
        self.assertTrue(creado)
        self.assertEqual(10, movimiento["quantity_delta"])
        self.assertEqual(10, self._saldo(NAVE))

    def test_a_superuser_is_not_blocked(self):
        _entrada(ACTOR, clave="e5")
        self.assertEqual(10, self._saldo(NAVE))

    def test_the_adjustment_still_needs_its_own_capability(self):
        clave, _ = self._clave_de_error(lambda: apply_inventory_movement(CEMENTO, {
            "movement_type": "adjustment", "quantity_delta": 5, "id_location": NAVE,
            "reason": "Conteo", "idempotency_key": "e6"}, SIN_CAPACIDAD))
        self.assertEqual("errors.inventory_adjustment_not_authorized", clave)


class TestElValeRespaldaLaEntrada(BaseEntradas):

    def test_a_return_citing_a_voucher_with_that_product_is_accepted(self):
        self.surtir(20, NAVE)
        r = self._vale([{"id_product": CEMENTO, "quantity": 5, "id_location_from": NAVE}])
        id_vale = r["voucher"]["id_incident"]

        movimiento, creado = _entrada(
            SIN_CAPACIDAD, clave="v1", tipo="return", cantidad=5,
            reference_type="incident", reference_id=id_vale)

        self.assertTrue(creado)
        self.assertEqual(5, movimiento["quantity_delta"])

    def test_a_voucher_that_does_not_exist_backs_nothing(self):
        clave, estado = self._clave_de_error(lambda: _entrada(
            SIN_CAPACIDAD, clave="v2", tipo="return",
            reference_type="incident", reference_id=999999))
        self.assertEqual(("errors.inventory_entry_not_authorized", 403), (clave, estado))

    def test_a_voucher_without_that_product_backs_nothing(self):
        # El vale existe, pero su unica salida es una herramienta serializada.
        pieza = self._pieza("DES-1")
        r = self._vale([self._linea_pieza(pieza)])
        clave, estado = self._clave_de_error(lambda: _entrada(
            SIN_CAPACIDAD, clave="v3", tipo="return",
            reference_type="incident", reference_id=r["voucher"]["id_incident"]))
        self.assertEqual(("errors.inventory_entry_not_authorized", 403), (clave, estado))

    def test_text_that_is_not_an_identifier_backs_nothing(self):
        clave, _ = self._clave_de_error(lambda: _entrada(
            SIN_CAPACIDAD, clave="v4", reference_type="purchase", reference_id="OC-1"))
        self.assertEqual("errors.inventory_entry_not_authorized", clave)


class TestLaCompraRespaldaLaEntrada(recepcion.BaseRecepcion):

    def _producto_de_la_orden(self, id_orden):
        # Un producto para el material 900 del primer renglon de la orden. Es la
        # misma preparacion de datos que usaban las pruebas de recepcion, copiada
        # aqui para no depender de ellas.
        from decimal import Decimal

        from sqlalchemy import select

        from app.models import (
            Brand, CustomerSupplier, Invoice, Location, LocationType, Material,
            ProductFamily, PurchaseOrderLine, Status, Unit,
        )
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(id_customer_supplier=900, name="Mi Empresa", tax_id="AAA010101AA1",
                                 postal_code="37000", fiscal_type="601", type="supplier",
                                 is_principal=True, id_user=1, created_by=1),
                LocationType(id_location_type=900, location_type_description="Almacen",
                             is_warehouse=True, created_by=1),
                Brand(id_brand=900, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=900, product_family_description="General", created_by=1),
                Unit(id_unit=900, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=1),
                Status(id_status=900, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
            ])
            db.flush()
            db.add_all([
                Location(id_location=900, id_location_type=900, location_description="Central", created_by=1),
                Material(id_material=900, material_description="Cemento", id_unit=900, id_brand=900,
                         id_product_family=900, created_by=1),
            ])
            db.flush()
            db.add(Invoice(id_invoice=900, id_customer_supplier=900, id_issuer_customer_supplier=900,
                           id_proyect=PROYECTO_A, id_status=900, invoice_status="pendiente",
                           tax_certification_supplier=900, apply_tax=False, total=Decimal("0"),
                           currency="MXN", created_by=1))
            db.flush()
            db.add(Product(id_product=900, id_invoice=900, id_location=900, id_material=900,
                           is_directly_related_to_product_service=False, cantidad=0, created_by=1))
            line = db.scalars(select(PurchaseOrderLine).where(
                PurchaseOrderLine.id_purchase_order == id_orden)).first()
            line.id_material = 900
            return line.id_purchase_order_line, int(line.quantity)

    def _entrada_manual(self, id_orden, clave):
        actor = {"id_user": 2, "id_proyect": PROYECTO_A, "id_permission": 99}
        return apply_inventory_movement(900, {
            "movement_type": "receive", "quantity": 3, "id_location": 900,
            "reason": "Llego", "idempotency_key": clave,
            "reference_type": "purchase", "reference_id": id_orden}, actor)

    def test_a_received_order_with_the_product_material_backs_the_entry(self):
        id_orden = self._comprada()
        self._producto_de_la_orden(id_orden)
        lineas = self._leer(id_orden)["lines"]
        self.assertEqual(200, self._recibir(id_orden, [
            {"id_purchase_order_line": l["id_purchase_order_line"], "quantity": l["quantity"]}
            for l in lineas]).status_code)

        movimiento, creado = self._entrada_manual(id_orden, "c1")

        self.assertTrue(creado)
        self.assertEqual(3, movimiento["quantity_delta"])

    def test_an_order_not_received_yet_backs_nothing(self):
        id_orden = self._comprada()
        self._producto_de_la_orden(id_orden)

        with self.assertRaises(AppError) as caja:
            self._entrada_manual(id_orden, "c2")

        self.assertEqual("errors.inventory_entry_not_authorized", caja.exception.message_key)


class TestElLoteSeNombraComoObjeto(BaseEntradas):

    def _con_lotes(self):
        with transaction_context() as db:
            db.get(Product, CEMENTO).lot_control = True

    def test_a_bare_string_is_refused_naming_the_field(self):
        self._con_lotes()
        with self.assertRaises(AppError) as caja:
            _entrada(ACTOR, clave="l1", lot="L-77")
        self.assertEqual("errors.invalid_field", caja.exception.message_key)
        self.assertEqual("lot", caja.exception.meta["field"])
        self.assertEqual(0, self._saldo(NAVE))

    def test_an_object_with_code_and_expiry_is_accepted(self):
        self._con_lotes()
        movimiento, creado = _entrada(
            ACTOR, clave="l2", lot={"lot_code": "L-77", "expiry_date": "2027-01-31"})
        self.assertTrue(creado)
        self.assertEqual(10, self._saldo(NAVE))

    def test_a_bare_string_is_refused_on_an_exit_too(self):
        self._con_lotes()
        _entrada(ACTOR, clave="l3", lot={"lot_code": "L-1"})
        with self.assertRaises(AppError) as caja:
            apply_inventory_movement(CEMENTO, {
                "movement_type": "issue", "quantity": 1, "id_location": NAVE,
                "reason": "Venta", "idempotency_key": "l4", "lot": "L-1"}, ACTOR)
        self.assertEqual("errors.invalid_field", caja.exception.message_key)


class TestPorLaRuta(BaseEntradas):

    def _cabeceras(self):
        self._otro_usuario(2)
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=1, entity_name="product",
                                    scope_read=4, scope_update=4, created_by=1))
        token = jwt.encode({"id_user": 2, "id_permission": 1, "id_proyect": 30},
                           SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def test_a_role_that_only_edits_products_cannot_inflate_the_balance(self):
        respuesta = self.client.post(
            "/product/%s/inventory-movements" % CEMENTO, headers=self._cabeceras(),
            json={"movement_type": "receive", "quantity": 1000, "id_location": NAVE,
                  "reason": "Sin respaldo", "reference_type": "manual",
                  "idempotency_key": "r1"})
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.inventory_entry_not_authorized",
                         self.json(respuesta)["error_key"])
        self.assertEqual(0, self._saldo(NAVE))
