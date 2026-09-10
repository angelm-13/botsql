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


class TestCreditNoteRegressions(CreditNoteTestCase):
    """Tres defectos que solo salieron al recorrer el ciclo fiscal completo.

    Los tres vivian en la union entre piezas que si estaban probadas por
    separado, que es donde las pruebas de unidad no miran.
    """

    SEGUNDO_ALMACEN = 3

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(Location(id_location=self.SEGUNDO_ALMACEN, id_location_type=1,
                            location_description="Almacen Norte", created_by=1))
            db.flush()
            db.add(InventoryStock(id_product=PRODUCT, id_location=self.SEGUNDO_ALMACEN,
                                  quantity=5, created_by=1))

    def _despachar_desde(self, id_location, cantidad=2):
        """Registra la salida por la venta desde una ubicacion concreta."""
        from app.models.invoice_material_service import InvoiceMaterialService
        from app.services.inventory_service import apply_movement_in_session

        with transaction_context() as db:
            linea = InvoiceMaterialService(
                id_invoice=SALE, id_product=PRODUCT,
                invoice_material_service_description="Venta", quantity=cantidad,
                gross_price=Decimal("100.00"), authorization_status="authorized",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                line_type="product", tax_applicable=False,
                sat_product_key="01010101", sat_unit_key="H87", created_by=1,
            )
            db.add(linea)
            db.flush()
            apply_movement_in_session(
                db, PRODUCT, ACTOR, movement_type="issue", quantity_delta=-cantidad,
                idempotency_key=f"venta-{linea.id_invoice_material_service}",
                id_location=id_location, reference_type="invoice_line",
                reference_id=str(linea.id_invoice_material_service),
                reason="Salida por factura de venta",
            )

    def _stock_en(self, id_location):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(
                id_product=PRODUCT, id_location=id_location).first()
            return int(fila.quantity) if fila else None

    def test_returned_goods_go_back_to_the_warehouse_they_left_from(self):
        """Antes se acreditaba el almacen por omision, no el que despacho.

        Con un solo almacen daba igual. Con varios, el total cuadraba y la
        ubicacion no, que es la peor de las dos combinaciones: nadie audita un
        total correcto, y quien va por la mercancia la busca donde no esta.
        """
        self._despachar_desde(self.SEGUNDO_ALMACEN, cantidad=2)
        antes_norte = self._stock_en(self.SEGUNDO_ALMACEN)
        antes_central = self._stock_en(RACK)

        self.note(relation_type="03", quantity=1, product=PRODUCT, key="nc-devuelve")

        self.assertEqual(antes_norte + 1, self._stock_en(self.SEGUNDO_ALMACEN))
        self.assertEqual(antes_central, self._stock_en(RACK),
                         "el almacen que no despacho no debe recibir nada")

    def test_without_a_prior_movement_it_falls_back_to_the_default_warehouse(self):
        """Si la venta nunca se aplico al almacen, no hay origen que respetar."""
        antes = self.stock()

        resultado = self.note(relation_type="03", quantity=1, product=PRODUCT, key="nc-sin-origen")

        self.assertTrue(resultado["returns_goods"])
        self.assertEqual(antes + 1, self.stock())

    def test_the_note_inherits_the_payment_form_and_method(self):
        """Un CFDI de egreso los exige; sin ellos la nota no se podia timbrar.

        Nacia invalida: se creaba bien y luego no pasaba su propia revision
        previa. Las pruebas no lo veian porque el ayudante siempre los pasaba a
        mano, mas generoso que el llamador real.
        """
        nota = create_credit_note(SALE, {
            "relation_type": "01", "idempotency_key": "nc-hereda",
            "concepts": [{"description": "Descuento", "quantity": 1, "unit_price": "100",
                          "sat_product_key": "01010101", "sat_unit_key": "H87"}],
        }, ACTOR)["credit_note"]

        self.assertEqual("03", nota["forma_pago"])
        self.assertEqual("PUE", nota["metodo_pago"])

    def test_an_explicit_payment_form_still_wins(self):
        nota = self.note(relation_type="01", key="nc-explicita",
                         forma_pago="01", metodo_pago="PPD")["credit_note"]

        self.assertEqual("01", nota["forma_pago"])
        self.assertEqual("PPD", nota["metodo_pago"])

    def test_the_relation_reaches_the_stamped_xml(self):
        """La relacion se guardaba en la base pero no viajaba al XML.

        Ante el SAT la nota quedaba como un egreso suelto, sin decir que
        factura corrige: no corregia nada, y el enlace solo existia dentro del
        sistema. El generador si sabia emitir el nodo y habia pruebas de eso;
        lo que faltaba era que alguien le pasara las relaciones.
        """
        from app.services.stamping import _related_documents

        nota = self.note(relation_type="03", quantity=1, product=PRODUCT, key="nc-xml")["credit_note"]

        with transaction_context() as db:
            relacionados = _related_documents(db, db.get(Invoice, nota["id_invoice"]))

        self.assertEqual([{"relation_type": "03", "uuid": UUID_SALE}], relacionados)

    def test_the_draft_carries_the_relations_into_the_document(self):
        from app.services.invoice_builder import build_draft

        with transaction_context() as db:
            factura = db.get(Invoice, SALE)
            emisor = db.get(CustomerSupplier, PRINCIPAL)
            receptor = db.get(CustomerSupplier, CLIENT)
            borrador = build_draft(
                factura, emisor, receptor, [],
                [{"relation_type": "03", "uuid": UUID_SALE}],
            )

        self.assertEqual(
            [{"relation_type": "03", "uuid": UUID_SALE}],
            borrador.serialize()["related_documents"],
        )

    def test_an_invoice_without_relations_carries_an_empty_list(self):
        """Para que el nodo quede ausente, no vacio: un CfdiRelacionados sin
        folios dentro es un XML invalido."""
        from app.services.stamping import _related_documents

        with transaction_context() as db:
            relacionados = _related_documents(db, db.get(Invoice, SALE))

        self.assertEqual([], relacionados)

    def test_a_stamped_credit_note_declares_the_relation_in_its_xml(self):
        """La prueba que faltaba: la union, no cada pieza por separado.

        El generador sabia emitir CfdiRelacionados y tenia pruebas de eso. El
        servicio guardaba la relacion y tenia pruebas de eso. Nadie comprobaba
        que la relacion guardada llegara al XML timbrado, y no llegaba.
        """
        import xml.etree.ElementTree as ET
        from app.services.invoice_artifacts import invoice_xml_path
        from app.services.stamping import FakeStampingProvider, stamp_invoice

        nota = self.note(relation_type="03", quantity=1, product=PRODUCT,
                         key="nc-timbrada")["credit_note"]
        id_nota = nota["id_invoice"]

        stamp_invoice(id_nota, f"nc-{id_nota}", ACTOR, FakeStampingProvider())

        ruta = invoice_xml_path(id_nota, self.app.config.get("UPLOAD_ROOT"))
        self.assertTrue(ruta.is_file(), "la nota timbrada deja su XML en disco")
        root = ET.fromstring(ruta.read_bytes())
        nodos = root.findall("{http://www.sat.gob.mx/cfd/4}CfdiRelacionados")

        self.assertEqual(1, len(nodos), "sin este nodo la nota no corrige nada ante el SAT")
        self.assertEqual("03", nodos[0].attrib["TipoRelacion"])
        folios = nodos[0].findall("{http://www.sat.gob.mx/cfd/4}CfdiRelacionado")
        self.assertEqual([UUID_SALE], [f.attrib["UUID"] for f in folios])


class TestCreditNoteOriginalLineQuantity(CreditNoteTestCase):
    """Comparado contra cotizador_demo (el sistema anterior de un cliente
    real): alla una nota acredita por partida y por cantidad, no solo por
    monto total. Esto fija que tyakxa_tny ahora hace lo mismo cuando la nota
    cita `id_original_line`.
    """

    def _renglon_original(self, cantidad):
        from app.models.invoice_material_service import InvoiceMaterialService

        with transaction_context() as db:
            linea = InvoiceMaterialService(
                id_invoice=SALE, id_product=PRODUCT,
                invoice_material_service_description="Venta original", quantity=cantidad,
                gross_price=Decimal("100.00"), authorization_status="authorized",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                line_type="product", tax_applicable=False,
                sat_product_key="01010101", sat_unit_key="H87", created_by=1,
            )
            db.add(linea)
            db.flush()
            return linea.id_invoice_material_service

    def _nota_citando_renglon(self, id_original_line, cantidad, key):
        payload = {
            "relation_type": "01",
            "idempotency_key": key,
            "forma_pago": "03",
            "metodo_pago": "PUE",
            "lugar_expedicion": "37000",
            "concepts": [{
                "description": "Ajuste sobre la venta",
                "quantity": cantidad,
                "unit_price": "50",
                "sat_product_key": "01010101", "sat_unit_key": "H87",
                "id_original_line": id_original_line,
            }],
        }
        return create_credit_note(SALE, payload, ACTOR)

    def test_a_note_can_credit_up_to_the_original_quantity(self):
        id_linea = self._renglon_original(cantidad=5)

        resultado = self._nota_citando_renglon(id_linea, cantidad=5, key="nc-completa")

        self.assertTrue(resultado["created"])

    def test_a_second_note_cannot_exceed_what_the_first_already_credited(self):
        id_linea = self._renglon_original(cantidad=5)
        self._nota_citando_renglon(id_linea, cantidad=3, key="nc-1")

        with self.assertRaises(AppError) as raised:
            self._nota_citando_renglon(id_linea, cantidad=3, key="nc-2")

        self.assertEqual(
            "errors.credit_note_line_exceeds_creditable_quantity",
            raised.exception.message_key,
        )

    def test_two_notes_that_together_exactly_use_up_the_quantity_both_succeed(self):
        """El control es acumulado, no solo contra la primera nota."""
        id_linea = self._renglon_original(cantidad=5)
        self._nota_citando_renglon(id_linea, cantidad=3, key="nc-1")

        segunda = self._nota_citando_renglon(id_linea, cantidad=2, key="nc-2")

        self.assertTrue(segunda["created"])

    def test_citing_a_line_from_another_invoice_is_rejected(self):
        """No se puede acreditar contra un renglon que no es de esta factura."""
        with transaction_context() as db:
            db.add(Invoice(
                id_invoice=999, id_customer_supplier=CLIENT, id_issuer_customer_supplier=PRINCIPAL,
                id_proyect=30, id_status=40, invoice_status="timbrada",
                folio_fiscal="99999999-9999-9999-9999-999999999999",
                metodo_pago="PUE", forma_pago="03", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, total=Decimal("100.00"), currency="MXN", created_by=1,
            ))
        with transaction_context() as db:
            from app.models.invoice_material_service import InvoiceMaterialService
            linea_ajena = InvoiceMaterialService(
                id_invoice=999, id_product=PRODUCT,
                invoice_material_service_description="De otra factura", quantity=5,
                gross_price=Decimal("100.00"), authorization_status="authorized",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENT,
                line_type="product", tax_applicable=False,
                sat_product_key="01010101", sat_unit_key="H87", created_by=1,
            )
            db.add(linea_ajena)
            db.flush()
            id_linea_ajena = linea_ajena.id_invoice_material_service

        with self.assertRaises(AppError) as raised:
            self._nota_citando_renglon(id_linea_ajena, cantidad=1, key="nc-cruzada")

        self.assertEqual("errors.credit_note_original_line_mismatch", raised.exception.message_key)

    def test_summary_exposes_creditable_quantity_per_line(self):
        id_linea = self._renglon_original(cantidad=5)
        self._nota_citando_renglon(id_linea, cantidad=2, key="nc-1")

        resumen = credit_note_summary(SALE, ACTOR)
        disponibilidad = next(
            r for r in resumen["line_availability"] if r["id_invoice_material_service"] == id_linea
        )
        self.assertEqual("3.00", disponibilidad["creditable_quantity"])
        self.assertEqual("2.00", disponibilidad["credited_quantity"])


if __name__ == "__main__":
    unittest.main()
