"""Notas de credito: el CFDI de egreso que corrige una factura.

Lo que estas pruebas fijan, y en particular la distincion que mas cuesta cara:

* una nota por descuento (relacion 01) NO toca el almacen, porque el cliente se
  queda con la mercancia;
* una por devolucion (relacion 03) SI la devuelve;
* no se acredita mas de lo que queda por acreditar;
* la nota sale de tipo Egreso y relacionada al folio de la factura original.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from app.models import (
    Brand,
    CfdiRelation,
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
from app.services.invoice_credit_note_service import (
    create_credit_note,
    credit_note_relations,
    credit_note_summary,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30}
OUTSIDER = {"id_user": 2, "id_proyect": 99}

PRINCIPAL = 10
CLIENT = 20
RACK = 2
PRODUCT = 60
SALE = 50
UUID_SALE = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


class CreditNoteTestCase(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=PRINCIPAL, name="Mi Empresa", tax_id="AAA010101AA1",
                    postal_code="37000", fiscal_type="601", type="supplier",
                    is_principal=True, id_user=1, created_by=1,
                ),
                CustomerSupplier(
                    id_customer_supplier=CLIENT, name="Cliente", tax_id="BBB010101BB1",
                    postal_code="37100", fiscal_type="601", type="client", id_user=1, created_by=1,
                ),
                LocationType(id_location_type=1, location_type_description="Almacen", is_warehouse=True, created_by=1),
                Brand(id_brand=1, brand_description="Generica", created_by=1),
                ProductFamily(id_product_family=1, product_family_description="General", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True, measurement_system="metric", created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=30, id_customer_supplier=CLIENT, leader=1, proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice", is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=RACK, id_location_type=1, location_description="Almacen Central", created_by=1),
                Material(id_material=1, material_description="Cemento", id_unit=1, id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            db.add(Invoice(
                id_invoice=SALE, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                id_proyect=30, id_status=40, invoice_status="timbrada", folio_fiscal=UUID_SALE,
                metodo_pago="PUE", forma_pago="03", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, total=Decimal("1160.00"), currency="MXN", created_by=1,
            ))
            db.flush()
            db.add(Product(
                id_product=PRODUCT, id_invoice=SALE, id_location=RACK, id_material=1,
                is_directly_related_to_product_service=False, cantidad=0, created_by=1,
            ))
            db.flush()
            db.add(InventoryStock(id_product=PRODUCT, id_location=RACK, quantity=30, created_by=1))

    def note(self, *, relation_type="01", quantity=1, unit_price="100", key="nc-1", product=None, **extra):
        payload = {
            "relation_type": relation_type,
            "idempotency_key": key,
            "forma_pago": "03",
            "metodo_pago": "PUE",
            "lugar_expedicion": "37000",
            "concepts": [{
                "description": "Ajuste sobre la venta",
                "quantity": quantity,
                "unit_price": unit_price,
                "sat_product_key": "01010101",
                "sat_unit_key": "H87",
                **({"id_product": product} if product else {}),
            }],
        }
        payload.update(extra)
        return create_credit_note(SALE, payload, ACTOR)

    def stock(self):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(id_product=PRODUCT, id_location=RACK).first()
            return int(fila.quantity) if fila else None


class TestCreditNoteBasics(CreditNoteTestCase):
    def test_it_is_issued_as_an_expense_document(self):
        """Una nota de credito es un CFDI de egreso, no una factura negativa."""
        resultado = self.note(unit_price="100")

        nota = resultado["credit_note"]
        self.assertTrue(resultado["created"])
        self.assertEqual("E", nota["tipo_de_comprobante"])
        self.assertEqual("G02", nota["uso_cfdi"])

    def test_its_amounts_are_positive(self):
        nota = self.note(unit_price="100")["credit_note"]

        self.assertGreater(Decimal(str(nota["total"])), 0)

    def test_it_is_related_to_the_original_invoice(self):
        resultado = self.note(relation_type="01")

        relacion = resultado["relation"]
        self.assertEqual("01", relacion["relation_type"])
        self.assertEqual(UUID_SALE, relacion["related_uuid"])
        self.assertEqual(SALE, relacion["id_related_invoice"])

    def test_the_relations_are_exposed_for_the_xml(self):
        nota = self.note()["credit_note"]

        relacionados = credit_note_relations(nota["id_invoice"], ACTOR)["related_documents"]

        self.assertEqual([{"relation_type": "01", "uuid": UUID_SALE}], relacionados)

    def test_it_inherits_the_parties_and_currency_of_the_original(self):
        nota = self.note()["credit_note"]

        self.assertEqual(CLIENT, nota["id_customer_supplier"])
        self.assertEqual(PRINCIPAL, nota["id_issuer_customer_supplier"])
        self.assertEqual("MXN", nota["currency"])

    def test_repeating_the_call_does_not_issue_a_second_note(self):
        primera = self.note(key="misma")
        segunda = self.note(key="misma")

        self.assertTrue(primera["created"])
        self.assertFalse(segunda["created"])
        self.assertEqual(
            primera["credit_note"]["id_invoice"], segunda["credit_note"]["id_invoice"]
        )

    def test_project_isolation_is_respected(self):
        with self.assertRaises(AppError) as raised:
            create_credit_note(SALE, {
                "relation_type": "01", "idempotency_key": "x",
                "concepts": [{"description": "X", "quantity": 1, "unit_price": "10",
                              "sat_product_key": "01010101", "sat_unit_key": "H87"}],
            }, OUTSIDER)

        self.assertEqual("errors.permission_denied", raised.exception.message_key)


class TestCreditNoteLimits(CreditNoteTestCase):
    def test_it_cannot_credit_more_than_the_invoice(self):
        with self.assertRaises(AppError) as raised:
            self.note(unit_price="2000")

        self.assertEqual("errors.credit_note_exceeds_creditable", raised.exception.message_key)

    def test_the_creditable_amount_shrinks_with_each_note(self):
        self.note(unit_price="500", key="n1")

        resumen = credit_note_summary(SALE, ACTOR)

        self.assertEqual("1160.00", resumen["total"])
        self.assertEqual("580.00", resumen["credited"])
        self.assertEqual("580.00", resumen["creditable"])

    def test_a_second_note_that_fits_is_accepted(self):
        self.note(unit_price="500", key="n1")

        segunda = self.note(unit_price="400", key="n2")

        self.assertTrue(segunda["created"])
        self.assertEqual("116.00", credit_note_summary(SALE, ACTOR)["creditable"])

    def test_a_second_note_that_does_not_fit_is_refused(self):
        self.note(unit_price="900", key="n1")

        with self.assertRaises(AppError) as raised:
            self.note(unit_price="200", key="n2")

        self.assertEqual("errors.credit_note_exceeds_creditable", raised.exception.message_key)

    def test_an_unstamped_invoice_cannot_be_credited(self):
        with transaction_context() as db:
            db.get(Invoice, SALE).folio_fiscal = None

        with self.assertRaises(AppError) as raised:
            self.note()

        self.assertEqual("errors.credit_note_requires_stamped_invoice", raised.exception.message_key)

    def test_a_cancelled_invoice_cannot_be_credited(self):
        with transaction_context() as db:
            db.get(Invoice, SALE).invoice_status = "cancelada"

        with self.assertRaises(AppError) as raised:
            self.note()

        self.assertEqual("errors.credit_note_invoice_cancelled", raised.exception.message_key)

    def test_a_relation_type_outside_the_two_valid_ones_is_refused(self):
        for tipo in ("02", "04", "07", "99"):
            with self.subTest(tipo=tipo), self.assertRaises(AppError) as raised:
                self.note(relation_type=tipo, key=f"n-{tipo}")
            self.assertEqual("errors.credit_note_relation_type_invalid", raised.exception.message_key)

    def test_a_note_without_concepts_is_refused(self):
        with self.assertRaises(AppError) as raised:
            create_credit_note(SALE, {"relation_type": "01", "idempotency_key": "x", "concepts": []}, ACTOR)

        self.assertEqual("errors.credit_note_concepts_required", raised.exception.message_key)


class TestCreditNoteAndInventory(CreditNoteTestCase):
    """La distincion que mas cuesta cara si se confunde."""

    def test_a_discount_does_not_touch_the_warehouse(self):
        """Relacion 01: el cliente se queda con la mercancia."""
        resultado = self.note(relation_type="01", quantity=5, unit_price="100", product=PRODUCT)

        self.assertFalse(resultado["returns_goods"])
        self.assertEqual([], resultado["inventory"])
        self.assertEqual(30, self.stock(), "un descuento no devuelve producto")

    def test_a_return_puts_the_goods_back(self):
        """Relacion 03: el cliente regresa lo que compro."""
        resultado = self.note(relation_type="03", quantity=5, unit_price="100", product=PRODUCT)

        self.assertTrue(resultado["returns_goods"])
        self.assertEqual(1, len(resultado["inventory"]))
        self.assertEqual(5, resultado["inventory"][0]["quantity_delta"])
        self.assertEqual("return", resultado["inventory"][0]["movement_type"])
        self.assertEqual(35, self.stock())

    def test_a_return_without_a_product_moves_nothing(self):
        """Un servicio devuelto no vive en el almacen."""
        resultado = self.note(relation_type="03", quantity=1, unit_price="100")

        self.assertTrue(resultado["returns_goods"])
        self.assertEqual([], resultado["inventory"])
        self.assertEqual(30, self.stock())

    def test_the_ledger_says_it_came_from_a_credit_note(self):
        resultado = self.note(relation_type="03", quantity=2, unit_price="100", product=PRODUCT)

        movimiento = resultado["inventory"][0]
        self.assertEqual("invoice_line", movimiento["reference_type"])
        self.assertIn("nota de credito", movimiento["reason"])

    def test_returning_twice_with_the_same_key_does_not_double_the_stock(self):
        self.note(relation_type="03", quantity=5, unit_price="100", product=PRODUCT, key="misma")
        self.note(relation_type="03", quantity=5, unit_price="100", product=PRODUCT, key="misma")

        self.assertEqual(35, self.stock())


class TestCreditNoteSummary(CreditNoteTestCase):
    def test_it_reports_what_can_still_be_credited(self):
        resumen = credit_note_summary(SALE, ACTOR)

        self.assertTrue(resumen["can_credit"])
        self.assertEqual("1160.00", resumen["creditable"])
        self.assertEqual(["01", "03"], resumen["relation_types"])
        self.assertEqual("03", resumen["returns_goods_relation"])
        self.assertEqual([], resumen["credit_notes"])

    def test_it_lists_the_notes_already_issued(self):
        self.note(unit_price="100", key="n1")
        self.note(unit_price="200", key="n2")

        resumen = credit_note_summary(SALE, ACTOR)

        self.assertEqual(2, len(resumen["credit_notes"]))

    def test_a_cancelled_note_stops_counting(self):
        """Si la nota se cancela, su importe vuelve a estar disponible."""
        primera = self.note(unit_price="500", key="n1")["credit_note"]
        with transaction_context() as db:
            db.get(Invoice, primera["id_invoice"]).invoice_status = "cancelada"

        resumen = credit_note_summary(SALE, ACTOR)

        self.assertEqual("0.00", resumen["credited"])
        self.assertEqual("1160.00", resumen["creditable"])

    def test_a_fully_credited_invoice_takes_no_more(self):
        self.note(unit_price="1000", key="n1")

        resumen = credit_note_summary(SALE, ACTOR)

        self.assertEqual("0.00", resumen["creditable"])
        self.assertFalse(resumen["can_credit"])


class TestRelationsInTheXml(unittest.TestCase):
    """El nodo CfdiRelacionados, sin el cual la nota no dice a que corrige."""

    def test_related_documents_are_grouped_by_type(self):
        from app.services.cfdi_document import build_cfdi_xml
        import xml.etree.ElementTree as ET

        xml = build_cfdi_xml(
            {
                "issuer": {"rfc": "AAA010101AA1", "name": "E", "tax_regime": "601", "postal_code": "37000"},
                "receiver": {"rfc": "BBB010101BB1", "name": "C", "tax_regime": "601",
                             "postal_code": "37100", "cfdi_use": "G02"},
                "cfdi_type": "E", "currency": "MXN", "payment_form": "03", "payment_method": "PUE",
                "concepts": [], "totals": {"subtotal": "100.00", "discount": "0", "total": "100.00"},
                "related_documents": [
                    {"relation_type": "01", "uuid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"},
                    {"relation_type": "01", "uuid": "11111111-2222-3333-4444-555555555555"},
                    {"relation_type": "03", "uuid": "99999999-8888-7777-6666-555555555555"},
                ],
            },
            issued_at="2026-08-28T10:00:00", certificate_number="30001000000400000001", seal="X",
        )
        root = ET.fromstring(xml)
        NS = "{http://www.sat.gob.mx/cfd/4}"
        nodos = root.findall(NS + "CfdiRelacionados")

        # Un nodo por tipo, con sus folios dentro.
        self.assertEqual(2, len(nodos))
        self.assertEqual(["01", "03"], [n.attrib["TipoRelacion"] for n in nodos])
        self.assertEqual(2, len(nodos[0].findall(NS + "CfdiRelacionado")))
        # Va antes del emisor, como lo ordena el esquema.
        self.assertEqual("CfdiRelacionados", root[0].tag.split("}")[-1])

    def test_without_relations_the_node_is_absent(self):
        from app.services.cfdi_document import build_cfdi_xml
        import xml.etree.ElementTree as ET

        xml = build_cfdi_xml(
            {
                "issuer": {"rfc": "AAA010101AA1", "name": "E", "tax_regime": "601", "postal_code": "37000"},
                "receiver": {"rfc": "BBB010101BB1", "name": "C", "tax_regime": "601",
                             "postal_code": "37100", "cfdi_use": "G03"},
                "cfdi_type": "I", "currency": "MXN", "payment_form": "03", "payment_method": "PUE",
                "concepts": [], "totals": {"subtotal": "0", "discount": "0", "total": "0"},
            },
            issued_at="2026-08-28T10:00:00", certificate_number="30001000000400000001", seal="X",
        )
        root = ET.fromstring(xml)

        self.assertEqual([], root.findall("{http://www.sat.gob.mx/cfd/4}CfdiRelacionados"))


if __name__ == "__main__":
    unittest.main()
