"""El vale de almacen: el rastro de quien se llevo que, y su cierre automatico.

Por que existe este archivo
---------------------------
El modelo que hay que sostener es este: un material se define por su familia,
su tipo y su marca -desarmadores / plano / Truper- y de ahi salen productos. Para
rastrear quien tiene que, se levanta un vale: un `incident` con tipo -prestamo-,
responsable, estado y renglones que unen el vale con el producto, la pieza y la
ubicacion.

Casi todo eso ya existia con otros nombres. Lo que faltaba, y lo que estas
pruebas fijan:

* **el tipo del material, colgando de su familia.** "Plano" no significa nada
  suelto: es un tipo de desarmador. Con una tabla plana de tipos se podria
  capturar "Cemento de tipo De cruz";
* **las dos formas de rastrear, cada una donde toca.** La herramienta se presta
  por PIEZA -devolver "un desarmador" no cierra el prestamo del desarmador que
  se llevaron- y la mercancia por CANTIDAD -nadie etiqueta trescientos
  tornillos-. El renglon exige pieza cuando el producto es serializado y la
  rechaza cuando no;
* **el cierre es automatico.** El estado del vale se deriva de sus renglones, no
  se captura. Es lo que evita el estado que mas duele: un vale "terminado" con
  dos herramientas todavia fuera, o uno "abierto" con todo devuelto;
* **lo vencido se puede preguntar.** Era la razon de llevar vales y no se podia:
  el renglon no tenia fecha de regreso.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models import (
    Brand,
    CustomerSupplier,
    Incident,
    IncidentType,
    Invoice,
    Location,
    LocationType,
    Material,
    MaterialType,
    Product,
    ProductFamily,
    Proyect,
    Status,
    Unit,
)
from app.models.session import transaction_context
from app.services.warehouse_voucher_service import (
    ABIERTO,
    CERRADO,
    cerrar_renglon,
    consultar_vale,
    crear_vale,
    vales_vencidos,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}

EMISOR, CLIENTE, PROYECTO, ESTATUS = 10, 20, 30, 40
NAVE, RACK, COMPRA = 50, 51, 52
FAM_DESARMADORES, FAM_OBRA = 60, 61
TIPO_PLANO, TIPO_CRUZ = 62, 63
MARCA_TRUPER, MARCA_CEMEX = 64, 65
MAT_DESARMADOR, MAT_CEMENTO = 66, 67
DESARMADOR, CEMENTO = 68, 69
TIPO_PRESTAMO = 70


class BaseVale(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                CustomerSupplier(
                    id_customer_supplier=EMISOR, name="Mi Empresa",
                    tax_id="AAA010101AA1", postal_code="37000", fiscal_type="601",
                    type="supplier", is_principal=True, id_user=1, created_by=1),
                CustomerSupplier(
                    id_customer_supplier=CLIENTE, name="Cliente",
                    tax_id="BBB010101BB1", postal_code="37100", fiscal_type="601",
                    type="client", id_user=1, created_by=1),
                LocationType(id_location_type=1, location_type_description="Nave",
                             is_warehouse=True, created_by=1),
                LocationType(id_location_type=2, location_type_description="Rack",
                             is_warehouse=False, created_by=1),
                # La familia y la marca, que ya existian.
                ProductFamily(id_product_family=FAM_DESARMADORES,
                              product_family_description="Desarmadores",
                              created_by=1),
                ProductFamily(id_product_family=FAM_OBRA,
                              product_family_description="Material de obra",
                              created_by=1),
                Brand(id_brand=MARCA_TRUPER, brand_description="Truper", created_by=1),
                Brand(id_brand=MARCA_CEMEX, brand_description="Cemex", created_by=1),
                Unit(id_unit=1, unit_name="Pieza", is_active=True,
                     measurement_system="metric", created_by=1),
                IncidentType(id_incident_type=TIPO_PRESTAMO,
                             incident_type_description="Prestamo", created_by=1),
            ])
            db.flush()
            db.add_all([
                # El tipo, que es lo nuevo, y cuelga de la familia.
                MaterialType(id_material_type=TIPO_PLANO,
                             id_product_family=FAM_DESARMADORES,
                             material_type_description="Plano", created_by=1),
                MaterialType(id_material_type=TIPO_CRUZ,
                             id_product_family=FAM_DESARMADORES,
                             material_type_description="De cruz", created_by=1),
                Status(id_status=ESTATUS, status_description="Activo",
                       category="invoice", is_terminal=False, sort_order="asc",
                       created_by=1),
                Proyect(id_proyect=PROYECTO, id_customer_supplier=CLIENTE, leader=1,
                        proyect_description="Obra Norte", created_by=1),
                Location(id_location=NAVE, id_location_type=1,
                         location_description="Nave A", created_by=1),
            ])
            db.flush()
            db.add_all([
                Location(id_location=RACK, id_location_type=2,
                         location_description="Rack A-1",
                         id_location_reference=NAVE, created_by=1),
                # Familia + tipo + marca = material.
                Material(id_material=MAT_DESARMADOR,
                         material_description="Desarmador",
                         id_unit=1, id_brand=MARCA_TRUPER,
                         id_product_family=FAM_DESARMADORES,
                         id_material_type=TIPO_PLANO, created_by=1),
                Material(id_material=MAT_CEMENTO, material_description="Cemento gris",
                         id_unit=1, id_brand=MARCA_CEMEX,
                         id_product_family=FAM_OBRA, created_by=1),
                Invoice(id_invoice=COMPRA, id_customer_supplier=EMISOR,
                        id_issuer_customer_supplier=CLIENTE, id_proyect=PROYECTO,
                        id_status=ESTATUS, invoice_status="borrador",
                        tax_certification_supplier=CLIENTE, apply_tax=False,
                        created_by=1),
            ])
            db.flush()
            db.add_all([
                # Herramienta: se rastrea pieza por pieza.
                Product(id_product=DESARMADOR, id_invoice=COMPRA, id_location=RACK,
                        id_material=MAT_DESARMADOR,
                        is_directly_related_to_product_service=True,
                        product_code="DES-PLA-TRU", descripcion="Desarmador plano Truper",
                        stock_purpose="uso_interno", tracking_mode="serializado",
                        gross_price=Decimal("85.00"), created_by=1),
                # Mercancia: se rastrea por saldo.
                Product(id_product=CEMENTO, id_invoice=COMPRA, id_location=NAVE,
                        id_material=MAT_CEMENTO,
                        is_directly_related_to_product_service=True,
                        product_code="CEM-50", descripcion="Cemento gris 50kg",
                        stock_purpose="mercancia", tracking_mode="fungible",
                        gross_price=Decimal("210.00"), created_by=1),
            ])

    def _pieza(self, etiqueta):
        from app.services.inventory_asset_service import register_asset

        r = register_asset({"id_product": DESARMADOR, "asset_tag": etiqueta,
                            "id_location": RACK}, ACTOR)
        return r["asset"]["id_inventory_asset"]

    def _vale(self, lineas, **extra):
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": 1,
                 "note": "Obra Norte", "lines": lineas}
        carga.update(extra)
        return crear_vale(carga, ACTOR)

    def _linea_pieza(self, id_pieza, **extra):
        base = {"id_product": DESARMADOR, "id_inventory_asset": id_pieza,
                "direction": "salida", "id_location_from": RACK}
        base.update(extra)
        return base

    def _linea_cantidad(self, cantidad=50, **extra):
        base = {"id_product": CEMENTO, "quantity": cantidad,
                "direction": "salida", "id_location_from": NAVE}
        base.update(extra)
        return base


class TestElTipoCuelgaDeLaFamilia(BaseVale):

    def test_a_material_is_family_plus_type_plus_brand(self):
        with transaction_context() as db:
            material = db.get(Material, MAT_DESARMADOR)
            tipo = db.get(MaterialType, material.id_material_type)
            self.assertEqual(FAM_DESARMADORES, material.id_product_family)
            self.assertEqual("Plano", tipo.material_type_description)
            self.assertEqual(MARCA_TRUPER, material.id_brand)

    def test_the_type_belongs_to_one_family(self):
        """"Plano" es un tipo de desarmador, no un tipo suelto."""
        with transaction_context() as db:
            self.assertEqual(
                FAM_DESARMADORES,
                db.get(MaterialType, TIPO_PLANO).id_product_family)

    def test_an_existing_material_may_have_no_type_yet(self):
        """Los materiales de antes no tienen tipo y no se les puede inventar uno."""
        with transaction_context() as db:
            self.assertIsNone(db.get(Material, MAT_CEMENTO).id_material_type)


class TestLasDosFormasDeRastrear(BaseVale):

    def test_a_tool_is_lent_by_the_piece(self):
        pieza = self._pieza("DES-001")
        r = self._vale([self._linea_pieza(pieza)])
        linea = r["lines"][0]
        self.assertEqual(pieza, linea["id_inventory_asset"])
        # Una pieza es una pieza: lo garantiza tambien un CHECK en la base.
        self.assertEqual(1, linea["quantity"])

    def test_merchandise_is_taken_by_quantity(self):
        r = self._vale([self._linea_cantidad(50)])
        linea = r["lines"][0]
        self.assertIsNone(linea["id_inventory_asset"])
        self.assertEqual(50, linea["quantity"])

    def test_a_serialized_product_without_a_piece_is_refused(self):
        """Un prestamo de herramienta sin decir cual es un vale que nadie cierra."""
        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": DESARMADOR, "quantity": 1,
                         "direction": "salida"}])
        self.assertEqual("errors.voucher_asset_required",
                         caja.exception.message_key)

    def test_a_fungible_product_with_a_piece_is_refused(self):
        """El cemento no tiene piezas: "una pieza de cemento" no existe."""
        pieza = self._pieza("DES-002")
        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": CEMENTO, "id_inventory_asset": pieza,
                         "direction": "salida"}])
        self.assertEqual("errors.voucher_asset_not_applicable",
                         caja.exception.message_key)

    def test_a_piece_of_another_product_is_refused(self):
        """Diria que se llevaron un desarmador cuando se llevaron otra cosa."""
        pieza = self._pieza("DES-003")
        with transaction_context() as db:
            # Se crea un tercer producto serializado y se le pide la pieza ajena.
            db.add(Product(
                id_product=900, id_invoice=COMPRA, id_location=RACK,
                id_material=MAT_DESARMADOR,
                is_directly_related_to_product_service=True,
                product_code="OTRO", descripcion="Otro desarmador",
                stock_purpose="uso_interno", tracking_mode="serializado",
                gross_price=Decimal("90.00"), created_by=1))

        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": 900, "id_inventory_asset": pieza,
                         "direction": "salida"}])
        self.assertEqual("errors.voucher_asset_product_mismatch",
                         caja.exception.message_key)

    def test_one_voucher_carries_both_kinds(self):
        """Es lo normal: la obra saca dos desarmadores y cincuenta de cemento."""
        r = self._vale([self._linea_pieza(self._pieza("DES-004")),
                        self._linea_cantidad(50)])
        self.assertEqual(2, len(r["lines"]))
        self.assertEqual({1, 50}, {l["quantity"] for l in r["lines"]})


class TestElCierreEsAutomatico(BaseVale):

    def test_a_new_voucher_is_open(self):
        r = self._vale([self._linea_pieza(self._pieza("DES-010"))])
        self.assertEqual(ABIERTO, r["voucher"]["incident_status"])
        self.assertIsNone(r["voucher"]["close_date"])

    def test_closing_the_last_line_closes_the_voucher(self):
        r = self._vale([self._linea_pieza(self._pieza("DES-011"))])
        cierre = cerrar_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        self.assertTrue(cierre["closed_the_voucher"])
        self.assertEqual(CERRADO, cierre["voucher"]["incident_status"])
        self.assertIsNotNone(cierre["voucher"]["close_date"])

    def test_a_voucher_with_one_line_open_stays_open(self):
        """Es el estado que mas duele si se captura a mano."""
        r = self._vale([self._linea_pieza(self._pieza("DES-012")),
                        self._linea_cantidad(20)])
        cierre = cerrar_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        self.assertFalse(cierre["closed_the_voucher"])
        self.assertEqual(ABIERTO, cierre["voucher"]["incident_status"])
        self.assertIsNone(cierre["voucher"]["close_date"])

        consulta = consultar_vale(r["voucher"]["id_incident"], ACTOR)
        self.assertEqual(1, consulta["open_lines"])
        self.assertEqual(2, consulta["total_lines"])

    def test_closing_both_lines_closes_the_voucher(self):
        r = self._vale([self._linea_pieza(self._pieza("DES-013")),
                        self._linea_cantidad(20)])
        for linea in r["lines"]:
            ultimo = cerrar_renglon(linea["id_nm_incident_product"], {}, ACTOR)

        self.assertTrue(ultimo["closed_the_voucher"])
        self.assertEqual(0, consultar_vale(r["voucher"]["id_incident"],
                                           ACTOR)["open_lines"])

    def test_a_line_cannot_be_closed_twice(self):
        """Cerrar dos veces refecharia el cierre y perderia cuando volvio."""
        r = self._vale([self._linea_pieza(self._pieza("DES-014"))])
        id_linea = r["lines"][0]["id_nm_incident_product"]
        cerrar_renglon(id_linea, {}, ACTOR)

        with self.assertRaises(AppError) as caja:
            cerrar_renglon(id_linea, {}, ACTOR)
        self.assertEqual("errors.voucher_line_already_closed",
                         caja.exception.message_key)

    def test_the_close_date_of_the_voucher_is_the_last_one(self):
        r = self._vale([self._linea_pieza(self._pieza("DES-015")),
                        self._linea_cantidad(20)])
        cierres = [cerrar_renglon(l["id_nm_incident_product"], {}, ACTOR)
                   for l in r["lines"]]

        with transaction_context() as db:
            vale = db.get(Incident, r["voucher"]["id_incident"])
            ultimo_renglon = max(
                datetime.fromisoformat(c["line"]["close_date"]) for c in cierres)
            self.assertEqual(ultimo_renglon, vale.close_date)


class TestLoVencido(BaseVale):

    def test_an_overdue_line_is_listed(self):
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        r = self._vale([self._linea_pieza(self._pieza("DES-020"))], due_date=ayer)

        vencidos = vales_vencidos(ACTOR)
        self.assertEqual(1, vencidos["total"])
        self.assertEqual(r["lines"][0]["id_nm_incident_product"],
                         vencidos["items"][0]["id_nm_incident_product"])

    def test_a_line_that_is_not_due_yet_is_not_listed(self):
        manana = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        self._vale([self._linea_pieza(self._pieza("DES-021"))], due_date=manana)
        self.assertEqual(0, vales_vencidos(ACTOR)["total"])

    def test_a_closed_line_stops_being_overdue(self):
        """Ya volvio: seguir reclamandola manda a buscar algo que esta en su sitio."""
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        r = self._vale([self._linea_pieza(self._pieza("DES-022"))], due_date=ayer)
        self.assertEqual(1, vales_vencidos(ACTOR)["total"])

        cerrar_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)
        self.assertEqual(0, vales_vencidos(ACTOR)["total"])

    def test_a_line_without_a_due_date_is_never_overdue(self):
        """Un prestamo sin fecha es una baja disfrazada; se ve en otra consulta."""
        self._vale([self._linea_pieza(self._pieza("DES-023"))])
        self.assertEqual(0, vales_vencidos(ACTOR)["total"])


class TestLoQueElValeExige(BaseVale):

    def test_a_voucher_without_lines_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self._vale([])
        self.assertEqual("errors.voucher_lines_required",
                         caja.exception.message_key)

    def test_an_unknown_incident_type_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_cantidad(1)], id_incident_type=999999)
        self.assertEqual("errors.not_found", caja.exception.message_key)

    def test_a_direction_outside_the_three_is_refused(self):
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_cantidad(1, direction="loquesea")])
        self.assertEqual("errors.invalid_field", caja.exception.message_key)

    def test_a_transfer_without_a_destination_is_refused(self):
        """Sin destino no es un traslado, es una salida sin registrar."""
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_cantidad(1, direction="traslado")])
        self.assertEqual("errors.required_field", caja.exception.message_key)

    def test_nothing_is_written_when_one_line_fails(self):
        """Un vale a medias dice que salio parte y nadie sabe que parte."""
        pieza = self._pieza("DES-030")
        with self.assertRaises(AppError):
            self._vale([self._linea_pieza(pieza),
                        {"id_product": DESARMADOR, "direction": "salida"}])

        with transaction_context() as db:
            from sqlalchemy import func, select

            from app.models.nm_incident_product import NmIncidentProduct

            self.assertEqual(0, db.scalar(select(func.count()).select_from(Incident)))
            self.assertEqual(0, db.scalar(
                select(func.count()).select_from(NmIncidentProduct)))


if __name__ == "__main__":
    unittest.main()
