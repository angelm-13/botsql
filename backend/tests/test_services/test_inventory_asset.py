"""Rastreo de piezas: herramienta, equipo, activo de uso.

Lo que estas pruebas fijan es la diferencia entre un inventario que sirve para
herramienta y uno que solo cuenta:

* una pieza tiene identidad, estado y responsable, asi que se puede contestar
  donde esta el taladro A-014 y quien se lo llevo;
* el saldo por cantidad y las piezas no se pueden separar: cada cambio de estado
  que la saca del almacen escribe su movimiento en el libro;
* un prestamo exige responsable y fecha, porque un prestamo sin fecha nunca esta
  vencido y se vuelve una baja disfrazada;
* declarar una pieza perdida exige la misma capacidad que un ajuste, que es la
  que separa a quien mueve la mercancia de quien puede tapar un faltante.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import (
    Brand, CustomerSupplier, EntityPermission, Invoice, Location, LocationType,
    Material, Product, ProductFamily, Proyect, Status, Unit,
)
from app.models.inventory_asset import (
    DISPONIBLE, EN_REPARACION, EN_USO, EXTRAVIADA, PRESTADA, RETIRADA,
)
from app.models.inventory_asset_event import InventoryAssetEvent
from app.models.inventory_stock import InventoryStock
from app.models.session import transaction_context
from app.services import inventory_asset_service as piezas
from app.services.inventory_service import ADJUSTMENT_CAPABILITY
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 30, "id_permission": 1}
QUIEN_AJUSTA = {"id_user": 1, "id_proyect": 30, "id_permission": 1}
QUIEN_NO_AJUSTA = {"id_user": 2, "id_proyect": 30, "id_permission": 2}

PRINCIPAL, CLIENTE = 10, 20
PROYECTO, FACTURA = 30, 50
ALMACEN, OTRO_ALMACEN = 2, 3
HERRAMIENTA, INSUMO = 60, 61
RESPONSABLE = 77


class PiezasTestCase(BackendTestCase):
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
                # Solo el perfil 1 puede ajustar: es la separacion de funciones
                # que ya existia para el ajuste de existencias.
                EntityPermission(id_permission=1, entity_name=ADJUSTMENT_CAPABILITY,
                                 scope_read=4, created_by=1),
            ])
            db.flush()
            db.add_all([
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Proyecto", created_by=1),
                Status(id_status=40, status_description="Activo", category="invoice",
                       is_terminal=False, sort_order="asc", created_by=1),
                Location(id_location=ALMACEN, id_location_type=1,
                         location_description="Almacen Central", created_by=1),
                Location(id_location=OTRO_ALMACEN, id_location_type=1,
                         location_description="Almacen Norte", created_by=1),
                Material(id_material=1, material_description="Taladro", id_unit=1,
                         id_brand=1, id_product_family=1, created_by=1),
            ])
            db.flush()
            # El usuario 1 existe de verdad. Las piezas se prestan y se asignan
            # a un responsable, y eso ahora se comprueba contra la tabla: la
            # llave ajena de `inventory_asset.id_holder` esta en el esquema, y
            # antes un prestamo a un usuario inventado se guardaba tal cual.
            sembrar_actor(db, id_proyect=PROYECTO, id_status=40,
                          ids=(1, RESPONSABLE))
            db.add(Invoice(
                id_invoice=FACTURA, id_customer_supplier=CLIENTE,
                id_issuer_customer_supplier=PRINCIPAL, id_proyect=PROYECTO, id_status=40,
                invoice_status="pendiente", tax_certification_supplier=PRINCIPAL,
                apply_tax=False, total=Decimal("0"), currency="MXN", created_by=1,
            ))
            db.flush()
            db.add_all([
                Product(id_product=HERRAMIENTA, id_invoice=FACTURA, id_location=ALMACEN,
                        id_material=1, is_directly_related_to_product_service=False,
                        cantidad=0, tracking_mode=piezas.SERIALIZADO, created_by=1),
                # Un producto fungible, para comprobar que no se le pueden dar
                # de alta piezas: contar cemento por numero de serie no tiene
                # sentido y el sistema lo debe decir.
                Product(id_product=INSUMO, id_invoice=FACTURA, id_location=ALMACEN,
                        id_material=1, is_directly_related_to_product_service=False,
                        cantidad=0, tracking_mode=piezas.FUNGIBLE, created_by=1),
            ])

    def alta(self, etiqueta="A-014", **extra):
        return piezas.register_asset({
            "id_product": HERRAMIENTA,
            "asset_tag": etiqueta,
            "id_location": ALMACEN,
            **extra,
        }, ACTOR)["asset"]

    def existencia(self, id_location=ALMACEN):
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(
                id_product=HERRAMIENTA, id_location=id_location).first()
            return int(fila.quantity) if fila else 0

    def estado(self, id_asset):
        return piezas.asset_history(id_asset, ACTOR)["asset"]["status"]


class TestAlta(PiezasTestCase):
    def test_a_new_asset_lands_available_and_counts_as_stock(self):
        pieza = self.alta()

        self.assertEqual(DISPONIBLE, pieza["status"])
        self.assertEqual(ALMACEN, pieza["id_location"])
        self.assertTrue(pieza["counts_as_stock"])
        self.assertEqual(1, self.existencia(), "el alta suma al saldo por cantidad")

    def test_the_tag_cannot_be_reused(self):
        """Dos herramientas con la misma etiqueta vuelven inutil el rastreo."""
        self.alta("A-014")

        with self.assertRaises(AppError) as raised:
            self.alta("A-014")

        self.assertEqual("errors.inventory_asset_tag_already_used", raised.exception.message_key)

    def test_a_fungible_product_takes_no_assets(self):
        """Contar cemento por numero de serie no tiene sentido."""
        with self.assertRaises(AppError) as raised:
            piezas.register_asset({
                "id_product": INSUMO, "asset_tag": "X-1", "id_location": ALMACEN,
            }, ACTOR)

        self.assertEqual(
            "errors.inventory_product_is_not_serialized", raised.exception.message_key)

    def test_the_acquisition_cost_arrives_as_text_and_survives(self):
        """Salio al recorrer el ciclo contra la base real, no en estas pruebas.

        El importe llega del cuerpo de la peticion como cadena. Se guardaba tal
        cual, y el modelo no reventaba al asignarlo sino al serializarlo, lejos
        del origen. Estas pruebas no lo veian porque nunca pasaban el importe:
        una fijacion que omite un campo opcional deja ese camino sin recorrer.
        """
        pieza = self.alta(acquisition_cost="4250.5")

        self.assertEqual("4250.50", pieza["acquisition_cost"],
                         "se guarda como decimal y viaja como cadena, no como flotante")

    def test_a_negative_acquisition_cost_is_refused(self):
        with self.assertRaises(AppError) as raised:
            self.alta("A-999", acquisition_cost="-10")

        self.assertEqual("errors.invalid_field", raised.exception.message_key)

    def test_the_registration_is_recorded_in_its_history(self):
        pieza = self.alta()

        historia = piezas.asset_history(pieza["id_inventory_asset"], ACTOR)

        self.assertEqual(1, historia["total"])
        self.assertEqual("alta", historia["events"][0]["event_type"])
        self.assertEqual(DISPONIBLE, historia["events"][0]["status_after"])


class TestPrestamo(PiezasTestCase):
    def test_lending_records_who_took_it_and_when_it_is_due(self):
        """Lo que el movimiento `loan` no podia contestar."""
        pieza = self.alta()
        vence = (date.today() + timedelta(days=7)).isoformat()

        resultado = piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE, "due_date": vence,
        }, ACTOR)

        self.assertEqual(PRESTADA, resultado["asset"]["status"])
        self.assertEqual(RESPONSABLE, resultado["asset"]["id_holder"])
        self.assertEqual(vence, resultado["asset"]["due_date"])
        self.assertIsNone(resultado["asset"]["id_location"],
                          "no esta en la empresa, asi que no esta en una ubicacion")
        self.assertEqual(0, self.existencia(), "sale del saldo por cantidad")

    def test_a_loan_without_a_holder_is_refused(self):
        pieza = self.alta()

        with self.assertRaises(AppError) as raised:
            piezas.lend_asset(pieza["id_inventory_asset"], {
                "due_date": (date.today() + timedelta(days=3)).isoformat(),
            }, ACTOR)

        self.assertEqual("errors.required_field", raised.exception.message_key)

    def test_a_loan_without_a_due_date_is_refused(self):
        """Sin fecha nunca esta vencido, y nadie lo reclama."""
        pieza = self.alta()

        with self.assertRaises(AppError) as raised:
            piezas.lend_asset(pieza["id_inventory_asset"], {"id_holder": RESPONSABLE}, ACTOR)

        self.assertEqual("errors.required_field", raised.exception.message_key)

    def test_a_due_date_already_past_is_refused(self):
        pieza = self.alta()

        with self.assertRaises(AppError) as raised:
            piezas.lend_asset(pieza["id_inventory_asset"], {
                "id_holder": RESPONSABLE,
                "due_date": (date.today() - timedelta(days=1)).isoformat(),
            }, ACTOR)

        self.assertEqual(
            "errors.inventory_asset_due_date_in_the_past", raised.exception.message_key)

    def test_returning_it_puts_it_back_in_stock_and_clears_the_holder(self):
        pieza = self.alta()
        piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        resultado = piezas.return_asset(pieza["id_inventory_asset"],
                                        {"id_location": ALMACEN}, ACTOR)

        self.assertEqual(DISPONIBLE, resultado["asset"]["status"])
        self.assertIsNone(resultado["asset"]["id_holder"])
        self.assertIsNone(resultado["asset"]["due_date"])
        self.assertEqual(1, self.existencia())

    def test_overdue_loans_are_listed_on_their_own(self):
        """Sin esta consulta un prestamo se vuelve permanente por olvido."""
        a_tiempo = self.alta("A-001")
        vencida = self.alta("A-002")
        piezas.lend_asset(a_tiempo["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
        }, ACTOR)
        piezas.lend_asset(vencida["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=1)).isoformat(),
        }, ACTOR)
        # Se atrasa despues de prestarla: al prestarla la fecha tenia que ser
        # futura, que es justo lo que la otra prueba exige.
        with transaction_context() as db:
            from app.models.inventory_asset import InventoryAsset
            db.get(InventoryAsset, vencida["id_inventory_asset"]).due_date = (
                date.today() - timedelta(days=3))

        resultado = piezas.overdue_loans(ACTOR)

        etiquetas = {fila["asset_tag"] for fila in resultado["items"]}
        self.assertEqual({"A-002"}, etiquetas)
        self.assertEqual(3, resultado["items"][0]["days_overdue"])


class TestAsignacionInterna(PiezasTestCase):
    def test_assigning_it_internally_does_not_move_the_balance(self):
        """Sigue siendo de la empresa: el saldo no cambia, el responsable si."""
        pieza = self.alta()

        resultado = piezas.assign_asset(pieza["id_inventory_asset"],
                                        {"id_holder": RESPONSABLE}, ACTOR)

        self.assertEqual(EN_USO, resultado["asset"]["status"])
        self.assertEqual(RESPONSABLE, resultado["asset"]["id_holder"])
        self.assertEqual(1, self.existencia(),
                         "una asignacion interna no saca la pieza de la empresa")


class TestReparacionYMerma(PiezasTestCase):
    def test_sending_it_to_repair_takes_it_out_of_stock(self):
        pieza = self.alta()

        resultado = piezas.send_to_repair(pieza["id_inventory_asset"],
                                          {"reason": "No enciende"}, ACTOR)

        self.assertEqual(EN_REPARACION, resultado["asset"]["status"])
        self.assertEqual(0, self.existencia(), "existe pero no se puede usar")

    def test_repair_requires_a_written_reason(self):
        pieza = self.alta()

        with self.assertRaises(AppError) as raised:
            piezas.send_to_repair(pieza["id_inventory_asset"], {}, ACTOR)

        self.assertEqual("errors.required_field", raised.exception.message_key)

    def test_it_comes_back_from_repair_available(self):
        pieza = self.alta()
        piezas.send_to_repair(pieza["id_inventory_asset"], {"reason": "No enciende"}, ACTOR)

        resultado = piezas.back_from_repair(pieza["id_inventory_asset"],
                                            {"id_location": ALMACEN}, ACTOR)

        self.assertEqual(DISPONIBLE, resultado["asset"]["status"])
        self.assertEqual(1, self.existencia())

    def test_reporting_it_lost_needs_the_adjustment_capability(self):
        """Declararla perdida destruye existencia sin documento detras."""
        pieza = self.alta()

        with self.assertRaises(AppError) as raised:
            piezas.report_lost(pieza["id_inventory_asset"],
                               {"reason": "No aparece"}, QUIEN_NO_AJUSTA)

        self.assertEqual(
            "errors.inventory_adjustment_not_authorized", raised.exception.message_key)

    def test_whoever_may_adjust_may_report_it_lost(self):
        pieza = self.alta()

        resultado = piezas.report_lost(pieza["id_inventory_asset"],
                                       {"reason": "No aparece"}, QUIEN_AJUSTA)

        self.assertEqual(EXTRAVIADA, resultado["asset"]["status"])
        self.assertIsNone(resultado["asset"]["id_location"])
        self.assertEqual(0, self.existencia())

    def test_a_retired_asset_does_not_come_back(self):
        pieza = self.alta()
        piezas.retire_asset(pieza["id_inventory_asset"], {"reason": "Fin de vida"}, QUIEN_AJUSTA)

        with self.assertRaises(AppError) as raised:
            piezas.assign_asset(pieza["id_inventory_asset"], {"id_holder": RESPONSABLE}, ACTOR)

        self.assertEqual("errors.inventory_asset_is_retired", raised.exception.message_key)


class TestMaquinaDeEstados(PiezasTestCase):
    def test_a_lent_asset_cannot_be_lent_again(self):
        """Dos responsables y un solo taladro."""
        pieza = self.alta()
        piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        with self.assertRaises(AppError) as raised:
            piezas.lend_asset(pieza["id_inventory_asset"], {
                "id_holder": 99,
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            }, ACTOR)

        self.assertEqual(
            "errors.inventory_asset_transition_not_allowed", raised.exception.message_key)

    def test_a_lent_asset_cannot_be_retired_without_coming_back(self):
        """Dar de baja lo que no se tiene enfrente tapa un faltante."""
        pieza = self.alta()
        piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        with self.assertRaises(AppError) as raised:
            piezas.retire_asset(pieza["id_inventory_asset"], {"reason": "x"}, QUIEN_AJUSTA)

        self.assertEqual(
            "errors.inventory_asset_transition_not_allowed", raised.exception.message_key)


class TestTraslado(PiezasTestCase):
    def test_moving_it_changes_location_without_changing_status(self):
        pieza = self.alta()

        resultado = piezas.move_asset(pieza["id_inventory_asset"], {
            "id_location": OTRO_ALMACEN, "reason": "Se ocupa en la otra obra",
        }, ACTOR)

        self.assertEqual(OTRO_ALMACEN, resultado["asset"]["id_location"])
        self.assertEqual(DISPONIBLE, resultado["asset"]["status"])
        self.assertEqual(0, self.existencia(ALMACEN))
        self.assertEqual(1, self.existencia(OTRO_ALMACEN),
                         "el saldo sigue a la pieza de una ubicacion a la otra")

    def test_a_lent_asset_cannot_be_moved(self):
        """No esta en la empresa: moverla de estante seria inventar un dato."""
        pieza = self.alta()
        piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        with self.assertRaises(AppError) as raised:
            piezas.move_asset(pieza["id_inventory_asset"],
                              {"id_location": OTRO_ALMACEN, "reason": "x"}, ACTOR)

        self.assertEqual("errors.inventory_asset_not_in_stock", raised.exception.message_key)

    def test_a_failure_after_the_stock_moves_rolls_back_the_stock_too(self):
        """`move_asset` escribe el traspaso de existencia Y el evento de la
        pieza en la MISMA transaccion (`transfer_in_session`, no
        `transfer_inventory`) -- si algo falla despues de que el saldo ya se
        movio, el rollback tiene que deshacer las DOS cosas juntas, no solo
        la pieza. Hallazgo de la auditoria de seguridad del 2026-10-06: antes
        de este arreglo, `transfer_inventory` abria su propia transaccion y
        ya habia hecho COMMIT del traspaso cuando esto fallaba -el saldo se
        quedaba movido con la pieza todavia en la ubicacion vieja.
        """
        from unittest.mock import patch

        pieza = self.alta()

        with patch("app.services.inventory_asset_service._asentar",
                   side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                piezas.move_asset(pieza["id_inventory_asset"], {
                    "id_location": OTRO_ALMACEN, "reason": "x",
                }, ACTOR)

        actual = piezas.asset_history(pieza["id_inventory_asset"], ACTOR)["asset"]
        self.assertEqual(ALMACEN, actual["id_location"],
                         "la pieza no se movio: el fallo fue despues")
        self.assertEqual(1, self.existencia(ALMACEN),
                         "el saldo de origen no debe quedar movido si la pieza no se movio")
        self.assertEqual(0, self.existencia(OTRO_ALMACEN),
                         "ni el destino debe quedar con existencia fantasma")


class TestRastreo(PiezasTestCase):
    def test_the_whole_life_of_a_tool_reads_in_order(self):
        """La pregunta que motivo todo esto: que le ha pasado a esta pieza."""
        pieza = self.alta("A-014")
        id_asset = pieza["id_inventory_asset"]
        piezas.lend_asset(id_asset, {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)
        piezas.return_asset(id_asset, {"id_location": ALMACEN}, ACTOR)
        piezas.send_to_repair(id_asset, {"reason": "Cable danado"}, ACTOR)
        piezas.back_from_repair(id_asset, {"id_location": ALMACEN}, ACTOR)

        historia = piezas.asset_history(id_asset, ACTOR)

        self.assertEqual(
            ["alta", "prestamo", "devolucion", "envio_reparacion", "regreso_reparacion"],
            [evento["event_type"] for evento in historia["events"]],
        )
        self.assertEqual(DISPONIBLE, historia["asset"]["status"])

    def test_it_is_found_by_the_tag_stuck_on_it(self):
        """Es la consulta que se hace con la herramienta en la mano."""
        self.alta("A-014")

        historia = piezas.find_asset_by_tag("A-014", ACTOR)

        self.assertEqual("A-014", historia["asset"]["asset_tag"])

    def test_each_stock_movement_is_linked_to_its_event(self):
        """Para ir de 'quien se la llevo' a 'que renglon la descontó'."""
        pieza = self.alta()
        piezas.lend_asset(pieza["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        with transaction_context() as db:
            eventos = db.query(InventoryAssetEvent).filter_by(
                id_inventory_asset=pieza["id_inventory_asset"]).all()
            prestamo = next(e for e in eventos if e.event_type == "prestamo")
            asignacion_interna = [e for e in eventos if e.event_type == "asignacion"]

        self.assertIsNotNone(prestamo.id_inventory_ledger,
                             "un prestamo mueve el saldo, asi que apunta a su renglon")
        self.assertEqual([], asignacion_interna)

    def test_the_summary_says_how_many_are_where(self):
        """"Tengo diez taladros" con el detalle de cuantos estan prestados."""
        for i in range(3):
            self.alta(f"A-00{i}")
        prestada = self.alta("A-100")
        piezas.lend_asset(prestada["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        resumen = piezas.product_asset_summary(HERRAMIENTA, ACTOR)

        self.assertEqual(4, resumen["total_assets"])
        self.assertEqual(3, resumen["by_status"][DISPONIBLE])
        self.assertEqual(1, resumen["by_status"][PRESTADA])
        self.assertEqual(3, resumen["assets_in_stock"])
        self.assertEqual(3, resumen["stock_balance"])
        self.assertTrue(resumen["is_reconciled"],
                        "las piezas disponibles y el saldo por cantidad cuadran")

    def test_the_summary_reports_a_mismatch_instead_of_hiding_it(self):
        """Si alguien movio existencia por fuera del rastreo, se dice."""
        self.alta("A-001")
        with transaction_context() as db:
            fila = db.query(InventoryStock).filter_by(
                id_product=HERRAMIENTA, id_location=ALMACEN).first()
            fila.quantity = 5

        resumen = piezas.product_asset_summary(HERRAMIENTA, ACTOR)

        self.assertFalse(resumen["is_reconciled"])
        self.assertEqual(-4, resumen["difference"])

    def test_assets_can_be_listed_by_who_holds_them(self):
        """Que tiene esta persona: lo que se pregunta cuando alguien se va."""
        primera = self.alta("A-001")
        self.alta("A-002")
        piezas.lend_asset(primera["id_inventory_asset"], {
            "id_holder": RESPONSABLE,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
        }, ACTOR)

        resultado = piezas.list_assets(ACTOR, id_holder=RESPONSABLE)

        self.assertEqual(1, resultado["total"])
        self.assertEqual("A-001", resultado["items"][0]["asset_tag"])


class TestPropositoDelAlmacen(PiezasTestCase):
    """El almacen guarda dos cosas y no son intercambiables.

    Mercancia se compra para venderse; un activo de uso interno -herramienta,
    equipo- no se vende nunca. Sin la distincion, una herramienta prestada y un
    producto vendido se veian igual en el saldo, y nada impedia facturar la venta
    de un taladro propio.
    """

    def test_an_internal_use_product_is_not_applied_to_a_sale(self):
        from app.services.invoice_inventory_service import preview_invoice_inventory
        from app.models.invoice_material_service import InvoiceMaterialService

        with transaction_context() as db:
            db.get(Product, HERRAMIENTA).stock_purpose = "uso_interno"
            db.get(Invoice, FACTURA).invoice_direction = "venta"
            db.add(InvoiceMaterialService(
                id_invoice=FACTURA, id_product=HERRAMIENTA,
                invoice_material_service_description="Taladro", quantity=1,
                gross_price=Decimal("100.00"), authorization_status="authorized",
                is_directly_related_to_product_service_creation=False,
                id_authorized=1, id_status=40, id_buyer=1, id_customer_supplier=CLIENTE,
                line_type="product", tax_applicable=False,
                sat_product_key="01010101", sat_unit_key="H87", created_by=1,
            ))

        vista = preview_invoice_inventory(FACTURA, {}, ACTOR)

        partida = next(l for l in vista["lines"] if l["id_product"] == HERRAMIENTA)
        self.assertEqual("product_is_for_internal_use", partida["skip_reason"])
        self.assertFalse(partida["applicable"])

    def test_merchandise_is_the_default_so_nothing_existing_changes(self):
        with transaction_context() as db:
            insumo = db.get(Product, INSUMO)

        self.assertEqual("mercancia", insumo.stock_purpose)


if __name__ == "__main__":
    unittest.main()


class TestElPanoramaDeEstatus(PiezasTestCase):
    """De mis herramientas: cuantas prestadas, cuantas en reparacion, cuantas no aparecen.

    Es la pregunta de la manana en un almacen de herramienta, y no se podia
    hacer: habia resumen POR PRODUCTO y la lista de prestamos vencidos, pero
    para el panorama habia que abrir producto por producto.

    Lo que estas pruebas fijan:

    * **los estados se cuentan todos**, incluidos los que estan en cero: un
      desplegable que solo ofrece los estados con piezas cambia de opciones
      segun el dia;
    * **lo vencido va aparte y no como un estado mas.** Una pieza vencida esta
      PRESTADA: contarla como estado propio la sumaria dos veces y el total
      dejaria de cuadrar con el numero de piezas;
    * **`stock_purpose` acota**, porque de la herramienta importa quien la tiene
      y de la mercancia el saldo;
    * **una consulta agrupada, no una por estado.** Seis idas a la base cada vez
      que alguien abre la pantalla es el patron que ya costo caro en el rastreo.
    """

    def _pieza(self, etiqueta):
        return self.alta(etiqueta)["id_inventory_asset"]

    def _resumen(self, **kwargs):
        from app.services.inventory_asset_service import resumen_de_estatus

        return resumen_de_estatus(ACTOR, **kwargs)

    def test_it_counts_every_status_including_the_empty_ones(self):
        from app.services.inventory_asset_service import ESTADOS

        self._pieza("PAN-001")
        resumen = self._resumen()

        self.assertEqual(set(ESTADOS), set(resumen["by_status"]),
                         "faltan estados: el desplegable cambiaria de opciones "
                         "segun cuantas piezas haya ese dia")
        self.assertEqual(1, resumen["by_status"]["disponible"])
        self.assertEqual(0, resumen["by_status"]["prestada"])
        self.assertEqual(1, resumen["total"])

    def test_the_total_matches_the_number_of_pieces(self):
        from app.services.inventory_asset_service import lend_asset, send_to_repair

        uno, dos, tres = (self._pieza("PAN-01%d" % i) for i in range(3))
        lend_asset(uno, {"id_holder": 1, "due_date": "2027-01-31",
                         "reason": "Obra"}, ACTOR)
        send_to_repair(dos, {"reason": "No enciende"}, ACTOR)

        resumen = self._resumen()
        self.assertEqual(3, resumen["total"])
        self.assertEqual(1, resumen["by_status"]["prestada"])
        self.assertEqual(1, resumen["by_status"]["en_reparacion"])
        self.assertEqual(1, resumen["by_status"]["disponible"])

    def test_an_overdue_loan_is_reported_apart_and_not_double_counted(self):
        from datetime import date, timedelta

        from app.models.inventory_asset import InventoryAsset
        from app.models.session import transaction_context
        from app.services.inventory_asset_service import lend_asset

        pieza = self._pieza("PAN-020")
        lend_asset(pieza, {"id_holder": 1, "due_date": "2027-01-31",
                           "reason": "Obra"}, ACTOR)
        # La fecha se atrasa a mano: el servicio rechaza prestar con una fecha
        # ya pasada, que es el guardia haciendo su trabajo.
        with transaction_context() as db:
            db.get(InventoryAsset, pieza).due_date = date.today() - timedelta(days=1)

        resumen = self._resumen()
        self.assertEqual(1, resumen["overdue"])
        # Sigue siendo UNA pieza, y sigue estando prestada.
        self.assertEqual(1, resumen["total"])
        self.assertEqual(1, resumen["by_status"]["prestada"])

    def test_it_narrows_to_internal_use_or_to_merchandise(self):
        """Son dos preguntas: quien tiene la herramienta, y cuanto hay de la mercancia."""
        self._pieza("PAN-030")

        # El producto serializado del montaje no declara `stock_purpose`, asi
        # que toma el valor por omision: mercancia. Se prueba contra lo que el
        # montaje dice, no contra lo que su nombre sugiere.
        mercancia = self._resumen(proposito="mercancia")
        interno = self._resumen(proposito="uso_interno")

        self.assertEqual(1, mercancia["total"])
        self.assertEqual("mercancia", mercancia["stock_purpose"])
        self.assertEqual(0, interno["total"],
                         "acotar por el otro proposito no puede traer nada")

    def test_it_asks_the_database_once_per_question(self):
        """Seis consultas -una por estado- en cada carga de la pantalla, no."""
        from sqlalchemy import event

        from app.models.session import engine

        for i in range(4):
            self._pieza("PAN-04%d" % i)

        self._resumen()  # calienta la compilacion de sentencias
        cuenta = []
        registrar = lambda *a, **k: cuenta.append(1)
        event.listen(engine, "after_cursor_execute", registrar)
        try:
            self._resumen()
        finally:
            event.remove(engine, "after_cursor_execute", registrar)

        self.assertLessEqual(
            len(cuenta), 4,
            "el resumen hizo %d consultas; con seis estados, una por estado "
            "seria el patron que ya costo caro en el rastreo" % len(cuenta))


class TestElResponsableExiste(PiezasTestCase):
    """Una pieza no se puede prestar a un usuario que no existe.

    Que estaba pasando
    ------------------
    `inventory_asset.id_holder` no tenia llave ajena y el servicio solo
    comprobaba que el valor fuera un entero. Un prestamo a `id_holder = 9999`
    se guardaba tal cual y la pieza quedaba PRESTADA a nadie: no sale en lo que
    debe ningun usuario, no se le puede reclamar, y el unico modo de notarla es
    ver que falta.

    La llave ajena esta ahora en el esquema
    -`20260907090000_el_responsable_de_la_pieza_es_un_usuario.sql`-, pero la
    base sola no basta para estas pruebas: SQLite no aplica llaves ajenas, asi
    que sin la comprobacion en el servicio esto seguiria pasando aqui y
    reventaria en produccion como un 500 en el COMMIT en lugar de un 404.
    """

    def _pieza_disponible(self):
        return self.alta("RES-001")["id_inventory_asset"]

    def test_lending_to_a_user_that_does_not_exist_is_refused(self):
        from app.services import inventory_asset_service as piezas

        with self.assertRaises(AppError) as saltó:
            piezas.lend_asset(self._pieza_disponible(), {
                "id_holder": 9999,
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            }, ACTOR)

        self.assertEqual("errors.not_found", saltó.exception.message_key)
        self.assertEqual("id_holder", saltó.exception.meta.get("field"))

    def test_assigning_to_a_user_that_does_not_exist_is_refused(self):
        """Lo mismo en la asignacion interna, que pasa por la misma puerta."""
        from app.services import inventory_asset_service as piezas

        with self.assertRaises(AppError) as saltó:
            piezas.assign_asset(self._pieza_disponible(), {"id_holder": 9999}, ACTOR)

        self.assertEqual("errors.not_found", saltó.exception.message_key)

    def test_a_deleted_user_cannot_receive_a_tool(self):
        """Un usuario dado de baja tampoco: ya no esta para devolverla."""
        from app.models.session import transaction_context
        from app.models.user import User
        from app.services import inventory_asset_service as piezas

        with transaction_context() as db:
            db.get(User, RESPONSABLE).deletion_date = datetime.now()

        with self.assertRaises(AppError) as saltó:
            piezas.lend_asset(self._pieza_disponible(), {
                "id_holder": RESPONSABLE,
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            }, ACTOR)

        self.assertEqual("errors.not_found", saltó.exception.message_key)

    def test_the_piece_is_not_left_lent_when_the_holder_is_refused(self):
        """Y la pieza se queda como estaba: ni PRESTADA ni descontada.

        Es la parte que importa. Si la transicion escribiera el estado y
        reventara despues, la pieza quedaria prestada a un usuario inexistente,
        que es justo lo que se venia a evitar.
        """
        from app.services import inventory_asset_service as piezas

        id_pieza = self._pieza_disponible()
        with self.assertRaises(AppError):
            piezas.lend_asset(id_pieza, {
                "id_holder": 9999,
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            }, ACTOR)

        pieza = piezas.find_asset_by_tag("RES-001", ACTOR)["asset"]
        self.assertEqual(id_pieza, pieza["id_inventory_asset"])
        self.assertEqual("disponible", pieza["status"])
        self.assertIsNone(pieza["id_holder"])
