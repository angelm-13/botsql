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
    BORRADOR,
    CERRADO,
    EN_ESPERA,
    EN_TRANSITO,
    autorizar_vale,
    buscar_vales,
    cerrar_renglon,
    devolver_renglon,
    consultar_vale,
    crear_vale,
    documento_del_historial_de_persona,
    documento_del_vale,
    notificar_material_entregado,
    notificar_prevale_creado,
    pdf_del_historial_de_persona,
    reporte_por_almacen,
    reporte_por_persona,
    reporte_por_producto,
    reporte_vales_pendientes,
    vales_vencidos,
)
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import sembrar_actor


ACTOR = {"id_user": 1, "id_proyect": 30, "is_superuser": True}
# El que autoriza no es el que pide, que es el control entero. Superusuario para
# no tener que sembrar la matriz de permisos en cada prueba: lo que se comprueba
# aqui es el flujo del borrador, y el permiso tiene sus propias pruebas.
OTRO_ACTOR = {"id_user": 2, "id_proyect": 30, "is_superuser": True}
JEFE_DE_ALMACEN = 6

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
            # El responsable del vale existe de verdad. `incident.id_user` tiene
            # llave ajena, y un vale a nombre de un usuario inventado no se le
            # puede reclamar a nadie.
            sembrar_actor(db, id_proyect=PROYECTO, id_status=ESTATUS)
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

    def surtir(self, cantidad=500, id_location=NAVE):
        """Existencia de cemento en la nave.

        Hace falta porque el vale ahora DESCUENTA: antes escribia sus renglones
        sin tocar el almacen, asi que las pruebas podian prestar cemento que no
        existia. Que eso funcionara era el fallo.
        """
        from app.services.inventory_service import apply_inventory_movement

        return apply_inventory_movement(CEMENTO, {
            "movement_type": "receive",
            "quantity": cantidad,
            "id_location": id_location,
            "reason": "Surtido inicial",
            "idempotency_key": "surtido:%s:%s" % (id_location, cantidad),
        }, ACTOR)

    def _saldo(self, id_location=NAVE, id_product=None):
        from sqlalchemy import select as _select

        from app.models.inventory_stock import InventoryStock

        with transaction_context() as db:
            fila = db.scalars(_select(InventoryStock).where(
                InventoryStock.id_product == (id_product or CEMENTO),
                InventoryStock.id_location == id_location,
            )).first()
            return int(fila.quantity) if fila else 0

    def _pieza(self, etiqueta):
        from app.services.inventory_asset_service import register_asset

        r = register_asset({"id_product": DESARMADOR, "asset_tag": etiqueta,
                            "id_location": RACK}, ACTOR)
        return r["asset"]["id_inventory_asset"]

    def _vale(self, lineas, **extra):
        # La fecha de regreso va siempre: sin ella el vale no se acepta.
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": 1,
                 "note": "Obra Norte", "lines": lineas,
                 "due_date": (datetime.now() + timedelta(days=30)).strftime(
                     "%Y-%m-%d %H:%M:%S")}
        carga.update(extra)
        return crear_vale(carga, ACTOR)

    def vencer(self, id_linea):
        """Atrasa la fecha de regreso de un renglon ya escrito.

        No se puede crear un vale vencido -una fecha pasada se rechaza al
        capturarla, que casi siempre es un dedazo en el ano-, asi que para
        probar lo vencido hay que dejar pasar el tiempo, y aqui se simula
        moviendo la fecha en la base.
        """
        from app.models.nm_incident_product import NmIncidentProduct

        with transaction_context() as db:
            db.get(NmIncidentProduct, id_linea).due_date = (
                datetime.now() - timedelta(days=1))
        return id_linea

    def _linea_pieza(self, id_pieza, **extra):
        base = {"id_product": DESARMADOR, "id_inventory_asset": id_pieza,
                "id_location_from": RACK}
        base.update(extra)
        return base

    def _linea_cantidad(self, cantidad=50, **extra):
        base = {"id_product": CEMENTO, "quantity": cantidad,
                "id_location_from": NAVE}
        base.update(extra)
        return base

    def _prevale(self, lineas, **extra):
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": 1,
                 "note": "Obra Norte", "lines": lineas,
                 "due_date": (datetime.now() + timedelta(days=30)).strftime(
                     "%Y-%m-%d %H:%M:%S")}
        carga.update(extra)
        return crear_vale(carga, ACTOR, como_borrador=True)

    def _otro_usuario(self, id_user):
        """Un segundo usuario real -- quien recoge, cuando no es el
        responsable -- con la misma llave ajena que `sembrar_actor` ya
        garantiza para el primero."""
        from app.models.user import User

        with transaction_context() as db:
            db.add(User(
                id_user=id_user, full_name="Operador %d" % id_user,
                username="operador%d" % id_user, id_permission=1,
                id_proyect=PROYECTO, id_status=ESTATUS, supervisor=1,
                created_by=1))
        return id_user

    def _autorizacion_completa(self, id_incident, actor=OTRO_ACTOR):
        """Helper: autoriza + marca salido + confirma (flujo completo).

        Para compatibilidad con tests que esperaban ABIERTO después de autorizar.
        El nuevo flujo es: BORRADOR -> EN_ESPERA -> EN_TRANSITO -> ABIERTO.
        """
        # Paso 1: Autorizar (BORRADOR -> EN_ESPERA)
        resultado = autorizar_vale(id_incident, {}, actor)

        # Paso 2: Marcar entregado (EN_ESPERA -> EN_TRANSITO, saca del almacén)
        entregar_vale(id_incident, {}, actor)

        # Paso 3: El responsable confirma que lo recibió (-> ABIERTO)
        resultado = confirmar_recibido_del_vale(id_incident, {}, ACTOR)

        return resultado


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
        self.surtir()
        r = self._vale([self._linea_cantidad(50)])
        linea = r["lines"][0]
        self.assertIsNone(linea["id_inventory_asset"])
        self.assertEqual(50, linea["quantity"])

    def test_a_serialized_product_without_a_piece_is_refused(self):
        """Un prestamo de herramienta sin decir cual es un vale que nadie cierra."""
        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": DESARMADOR, "quantity": 1}])
        self.assertEqual("errors.voucher_asset_required",
                         caja.exception.message_key)

    def test_a_fungible_product_with_a_piece_is_refused(self):
        """El cemento no tiene piezas: "una pieza de cemento" no existe."""
        pieza = self._pieza("DES-002")
        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": CEMENTO, "id_inventory_asset": pieza}])
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
            self._vale([{"id_product": 900, "id_inventory_asset": pieza}])
        self.assertEqual("errors.voucher_asset_product_mismatch",
                         caja.exception.message_key)

    def test_one_voucher_carries_both_kinds(self):
        """Es lo normal: la obra saca dos desarmadores y cincuenta de cemento."""
        self.surtir()
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
        self.surtir()
        r = self._vale([self._linea_pieza(self._pieza("DES-012")),
                        self._linea_cantidad(20)])
        cierre = cerrar_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        self.assertFalse(cierre["closed_the_voucher"])
        self.assertEqual(ABIERTO, cierre["voucher"]["incident_status"])
        self.assertIsNone(cierre["voucher"]["close_date"])

        consulta = consultar_vale(r["voucher"]["id_incident"], ACTOR)
        self.assertEqual(1, consulta["open_lines"])
        # Dos salidas, y una entrada por la que ya volvio. La devolucion agrega
        # renglon en vez de reescribir la salida: el papel se lee entero
        # despues, sin adivinar que paso con cada cosa.
        self.assertEqual(2, consulta["exit_lines"])
        self.assertEqual(1, consulta["entry_lines"])
        self.assertEqual(3, consulta["total_lines"])

    def test_closing_both_lines_closes_the_voucher(self):
        self.surtir()
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
        self.surtir()
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
        r = self._vale([self._linea_pieza(self._pieza("DES-020"))])

        self.vencer(r["lines"][0]["id_nm_incident_product"])

        vencidos = vales_vencidos(ACTOR)
        self.assertEqual(1, vencidos["total"])
        self.assertEqual(r["lines"][0]["id_nm_incident_product"],
                         vencidos["items"][0]["id_nm_incident_product"])

    def test_a_line_that_is_not_due_yet_is_not_listed(self):
        self._vale([self._linea_pieza(self._pieza("DES-021"))])
        self.assertEqual(0, vales_vencidos(ACTOR)["total"])

    def test_a_returned_line_stops_being_overdue(self):
        """Ya volvio: seguir reclamandola manda a buscar algo que esta en su sitio."""
        r = self._vale([self._linea_pieza(self._pieza("DES-022"))])
        self.vencer(r["lines"][0]["id_nm_incident_product"])
        self.assertEqual(1, vales_vencidos(ACTOR)["total"])

        devolver_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)
        self.assertEqual(0, vales_vencidos(ACTOR)["total"])

    def test_an_overdue_line_says_the_stock_of_its_product(self):
        """Reclamar sin saber si queda mas del mismo producto es media respuesta."""
        r = self._vale([self._linea_pieza(self._pieza("DES-024"))])
        self.vencer(r["lines"][0]["id_nm_incident_product"])

        vencidos = vales_vencidos(ACTOR)
        self.assertIn("stock_on_hand", vencidos["items"][0])


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

    def test_a_line_is_always_an_exit_whatever_was_asked_for(self):
        """Un vale es una salida en calidad de prestamo. No hay otra clase.

        La direccion se podia capturar, asi que un traspaso entre racks se
        podia guardar como si fuera un vale, y entonces la lista de lo que esta
        fuera contaba cosas que nunca salieron del almacen.
        """
        self.surtir()
        r = self._vale([self._linea_cantidad(1, direction="traslado")])
        self.assertEqual("salida", r["lines"][0]["direction"])

    def test_a_voucher_without_a_return_date_is_refused(self):
        """Un prestamo sin fecha de regreso nunca esta vencido, asi que nadie lo pide."""
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_pieza(self._pieza("DES-031"))], due_date=None)
        self.assertEqual("errors.required_field", caja.exception.message_key)
        self.assertEqual("due_date", caja.exception.meta.get("field"))

    def test_a_return_date_already_past_is_refused(self):
        """Nace vencido, y casi siempre es un dedazo en el ano."""
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_pieza(self._pieza("DES-032"))], due_date=ayer)
        self.assertEqual("errors.voucher_due_date_in_the_past",
                         caja.exception.message_key)

    def test_a_voucher_without_a_reason_is_refused(self):
        """El motivo es lo que contesta "y esto por que salio" tres meses despues."""
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_pieza(self._pieza("DES-033"))], note="")
        self.assertEqual("errors.required_field", caja.exception.message_key)

    def test_a_fungible_line_must_say_where_it_comes_out_of(self):
        """Descontar "del almacen" sin decir de cual deja el saldo por sitio mintiendo."""
        self.surtir()
        with self.assertRaises(AppError) as caja:
            self._vale([{"id_product": CEMENTO, "quantity": 1}])
        self.assertEqual("errors.required_field", caja.exception.message_key)
        self.assertEqual("id_location_from", caja.exception.meta.get("field"))

    def test_nothing_is_written_when_one_line_fails(self):
        """Un vale a medias dice que salio parte y nadie sabe que parte."""
        pieza = self._pieza("DES-030")
        with self.assertRaises(AppError):
            self._vale([self._linea_pieza(pieza),
                        {"id_product": DESARMADOR}])

        with transaction_context() as db:
            from sqlalchemy import func, select

            from app.models.nm_incident_product import NmIncidentProduct

            self.assertEqual(0, db.scalar(select(func.count()).select_from(Incident)))
            self.assertEqual(0, db.scalar(
                select(func.count()).select_from(NmIncidentProduct)))



class TestElResponsableDelValeExiste(BaseVale):
    """Un vale a nombre de un usuario que no existe no se le puede reclamar a nadie.

    `incident.id_user` si tiene llave ajena, y DIFERIDA: el identificador
    inventado no falla al asignarlo, falla en el COMMIT, fuera de todo manejo de
    errores. Al usuario le llegaba un 500 sin decir que campo estaba mal.
    """

    def test_a_voucher_for_a_user_that_does_not_exist_is_refused(self):
        with self.assertRaises(AppError) as saltó:
            self._vale([{"id_product": CEMENTO, "quantity": 5,
                         "direction": "salida", "id_location_from": NAVE}],
                       id_user=9999)

        self.assertEqual("errors.not_found", saltó.exception.message_key)
        self.assertEqual("id_user", saltó.exception.meta.get("field"))

    def test_nothing_is_written_when_the_holder_is_refused(self):
        """Y no queda medio vale escrito: o entra entero o no entra."""
        from sqlalchemy import func, select

        from app.models.nm_incident_product import NmIncidentProduct
        from app.models.session import transaction_context

        with self.assertRaises(AppError):
            self._vale([{"id_product": CEMENTO, "quantity": 5,
                         "direction": "salida", "id_location_from": NAVE}],
                       id_user=9999)

        with transaction_context() as db:
            self.assertEqual(0, db.scalar(select(func.count()).select_from(Incident)))
            self.assertEqual(
                0, db.scalar(select(func.count()).select_from(NmIncidentProduct)))

class TestElValeMueveElAlmacen(BaseVale):
    """Un vale que no descuenta es un papel.

    Que estaba pasando
    ------------------
    `crear_vale` escribia sus renglones y no tocaba nada mas. La pieza seguia
    diciendo "disponible" mientras estaba en la camioneta de alguien, y el saldo
    seguia contando cinco sacos que ya no estaban. Dos vistas del mismo hecho,
    en desacuerdo, y ninguna forma de saber cual creer.

    Lo que estas pruebas fijan:

    * **la pieza queda PRESTADA, con responsable y con fecha de regreso.** Es lo
      que hace que salga en "que trae Juan" y en la lista de vencidos;
    * **lo fungible se descuenta de la ubicacion de la que salio**, no "del
      almacen" en general;
    * **la devolucion repone**, y agrega su renglon de entrada en vez de
      reescribir la salida;
    * **no se puede prestar lo que no hay.** El vale pasa por la misma puerta
      que todo lo demas, asi que hereda el guardia que impide el saldo negativo;
    * **todo o nada.** Si el tercer renglon falla, los dos primeros no se
      llevaron nada: ni saldo descontado ni piezas marcadas.
    """

    def _saldo(self, id_location=NAVE, id_product=None):
        from sqlalchemy import select as _select

        from app.models.inventory_stock import InventoryStock

        with transaction_context() as db:
            fila = db.scalars(_select(InventoryStock).where(
                InventoryStock.id_product == (id_product or CEMENTO),
                InventoryStock.id_location == id_location,
            )).first()
            return int(fila.quantity) if fila else 0

    def _pieza_en_la_base(self, id_pieza):
        from app.models.inventory_asset import InventoryAsset

        with transaction_context() as db:
            pieza = db.get(InventoryAsset, id_pieza)
            return {"status": pieza.status, "id_holder": pieza.id_holder,
                    "due_date": pieza.due_date, "id_location": pieza.id_location}

    def test_lending_a_piece_marks_it_as_lent_with_a_holder_and_a_date(self):
        id_pieza = self._pieza("MOV-001")
        self.assertEqual("disponible", self._pieza_en_la_base(id_pieza)["status"])

        self._vale([self._linea_pieza(id_pieza)])

        despues = self._pieza_en_la_base(id_pieza)
        self.assertEqual("prestada", despues["status"])
        self.assertEqual(1, despues["id_holder"])
        self.assertIsNotNone(despues["due_date"])
        # Deja de estar en una ubicacion: decir que sigue en el rack seria falso,
        # y es el dato que hace que nadie la busque donde de verdad esta.
        self.assertIsNone(despues["id_location"])

    def test_the_piece_history_records_the_loan_with_the_voucher_behind_it(self):
        """Desde la bitacora de la pieza se llega al papel que la justifica."""
        from app.services.inventory_asset_service import asset_history

        id_pieza = self._pieza("MOV-002")
        r = self._vale([self._linea_pieza(id_pieza)])

        eventos = asset_history(id_pieza, ACTOR)["events"]
        prestamo = [e for e in eventos if e["event_type"] == "prestamo"]
        self.assertEqual(1, len(prestamo))
        self.assertEqual("incident", prestamo[0]["reference_type"])
        self.assertEqual(str(r["voucher"]["id_incident"]),
                         prestamo[0]["reference_id"])

    def test_taking_merchandise_discounts_the_location_it_came_out_of(self):
        self.surtir(100)
        self.assertEqual(100, self._saldo())

        self._vale([self._linea_cantidad(30)])

        self.assertEqual(70, self._saldo())

    def test_a_voucher_cannot_take_more_than_there_is(self):
        """Hereda el guardia del saldo negativo, porque usa la misma puerta."""
        self.surtir(10)
        with self.assertRaises(AppError) as caja:
            self._vale([self._linea_cantidad(11)])
        self.assertEqual("errors.inventory_insufficient_stock",
                         caja.exception.message_key)
        self.assertEqual(10, self._saldo())

    def test_returning_a_piece_puts_it_back_available_and_frees_the_holder(self):
        id_pieza = self._pieza("MOV-003")
        r = self._vale([self._linea_pieza(id_pieza)])

        devolver_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        despues = self._pieza_en_la_base(id_pieza)
        self.assertEqual("disponible", despues["status"])
        self.assertIsNone(despues["id_holder"])
        # Vuelve al sitio del que salio.
        self.assertEqual(RACK, despues["id_location"])

    def test_returning_merchandise_puts_the_quantity_back(self):
        self.surtir(100)
        r = self._vale([self._linea_cantidad(30)])
        self.assertEqual(70, self._saldo())

        devolver_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        self.assertEqual(100, self._saldo())

    def test_the_return_adds_an_entry_line_instead_of_rewriting_the_exit(self):
        """Salio un registro, volvio otro. La historia no se corrige, se continua."""
        id_pieza = self._pieza("MOV-004")
        r = self._vale([self._linea_pieza(id_pieza)])
        id_salida = r["lines"][0]["id_nm_incident_product"]

        devolucion = devolver_renglon(id_salida, {}, ACTOR)

        self.assertEqual("entrada", devolucion["entry"]["direction"])
        self.assertNotEqual(id_salida, devolucion["entry"]["id_nm_incident_product"])
        # Y la salida sigue ahi, con su fecha de cierre: es lo que hace que
        # "que sigue fuera" sea una consulta con indice.
        self.assertEqual("salida", devolucion["line"]["direction"])
        self.assertIsNotNone(devolucion["line"]["close_date"])

        consulta = consultar_vale(r["voucher"]["id_incident"], ACTOR)
        self.assertEqual(1, consulta["exit_lines"])
        self.assertEqual(1, consulta["entry_lines"])
        self.assertEqual(0, consulta["open_lines"])

    def test_an_entry_line_cannot_be_returned(self):
        """Una entrada nace saldada: no hay nada que devolver de una devolucion."""
        r = self._vale([self._linea_pieza(self._pieza("MOV-005"))])
        devolucion = devolver_renglon(
            r["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        with self.assertRaises(AppError) as caja:
            devolver_renglon(devolucion["entry"]["id_nm_incident_product"], {}, ACTOR)
        self.assertEqual("errors.voucher_line_not_a_loan",
                         caja.exception.message_key)

    def test_a_returned_piece_can_go_out_again_on_another_voucher(self):
        """Es el ciclo normal, y solo funciona si la devolucion la libero de verdad."""
        id_pieza = self._pieza("MOV-006")
        primero = self._vale([self._linea_pieza(id_pieza)])
        devolver_renglon(primero["lines"][0]["id_nm_incident_product"], {}, ACTOR)

        segundo = self._vale([self._linea_pieza(id_pieza)])

        self.assertEqual("prestada", self._pieza_en_la_base(id_pieza)["status"])
        self.assertNotEqual(primero["voucher"]["id_incident"],
                            segundo["voucher"]["id_incident"])

    def test_nothing_moves_when_one_line_fails(self):
        """El almacen queda intacto: ni saldo descontado ni piezas marcadas."""
        self.surtir(100)
        id_pieza = self._pieza("MOV-007")

        with self.assertRaises(AppError):
            self._vale([
                self._linea_pieza(id_pieza),
                self._linea_cantidad(30),
                # Serializado sin decir cual: el vale entero se cae.
                {"id_product": DESARMADOR, "quantity": 1},
            ])

        self.assertEqual(100, self._saldo())
        self.assertEqual("disponible", self._pieza_en_la_base(id_pieza)["status"])

    def test_a_line_says_the_stock_of_its_product(self):
        """"Salen 5 de 40" y "salen 5 de 5" son la misma linea con otra consecuencia."""
        self.surtir(40)
        r = self._vale([self._linea_cantidad(5)])

        linea = r["lines"][0]
        # Lo que queda despues de la salida: es la cifra con la que se firma.
        self.assertEqual(35, linea["stock_on_hand"])


class TestElFolioSeBusca(BaseVale):
    """El folio es el numero con el que la gente conoce el vale.

    Como se encontro
    ----------------
    Revisando el flujo con los datos importados: el vale 112 del sistema
    anterior es nuestro `id_incident = 530`, y la unica forma de consultarlo era
    saberse el 530. El folio se guardaba y no servia para nada, que era justo lo
    contrario de lo que se pidio al traerlo.

    Lo que estas pruebas fijan:

    * **el vale se encuentra por su folio**, no solo por su identificador;
    * **el identificador gana**: es lo que usan los enlaces internos y es unico
      sin discusion, asi que se prueba primero;
    * **la lista busca por folio Y por responsable a la vez**, porque son las
      dos formas de llegar a un vale: con el papel en la mano o preguntando que
      trae alguien;
    * **un texto que no es numero no revienta.** Buscar "MAXIMINO" no es un
      error de captura: `_entero` tiraba 400 con cualquier texto y por eso la
      busqueda por nombre fallaba.
    """

    def _con_folio(self, folio, **extra):
        from app.models.incident import Incident

        r = self._vale([self._linea_pieza(self._pieza("FOL-%s" % folio))], **extra)
        with transaction_context() as db:
            vale = db.get(Incident, r["voucher"]["id_incident"])
            vale.external_folio = str(folio)
            vale.external_source = "adser_prod"
        return r["voucher"]["id_incident"]

    def test_a_voucher_is_found_by_its_folio(self):
        id_nuestro = self._con_folio(112)
        r = consultar_vale("112", ACTOR)
        self.assertEqual(id_nuestro, r["voucher"]["id_incident"])
        self.assertEqual("112", r["voucher"]["external_folio"])

    def test_the_identifier_still_works(self):
        id_nuestro = self._con_folio(113)
        r = consultar_vale(id_nuestro, ACTOR)
        self.assertEqual(id_nuestro, r["voucher"]["id_incident"])

    def test_the_identifier_wins_over_a_folio_that_collides(self):
        """Si un folio coincide con el id de OTRO vale, manda el id."""
        primero = self._con_folio(500)
        # Al segundo se le pone como folio el identificador del primero.
        segundo = self._con_folio(primero)

        r = consultar_vale(primero, ACTOR)
        self.assertEqual(primero, r["voucher"]["id_incident"],
                         "el folio ajeno gano sobre el identificador")
        self.assertNotEqual(segundo, r["voucher"]["id_incident"])

    def test_something_that_is_neither_is_a_404(self):
        with self.assertRaises(AppError) as caja:
            consultar_vale("no-existe-este-folio", ACTOR)
        self.assertEqual("errors.not_found", caja.exception.message_key)

    def test_the_list_finds_by_folio(self):
        from app.services.warehouse_voucher_service import buscar_vales

        self._con_folio(221)
        r = buscar_vales(ACTOR, texto="221")
        self.assertEqual(1, r["total"])
        self.assertEqual("221", r["items"][0]["folio"])

    def test_the_list_finds_by_holder_name(self):
        """Y un texto que no es numero no revienta: era el fallo de `_entero`."""
        from app.services.warehouse_voucher_service import buscar_vales

        self._con_folio(222)
        r = buscar_vales(ACTOR, texto="Usuario de pruebas")
        self.assertGreaterEqual(r["total"], 1)
        self.assertTrue(all(x["holder_name"] for x in r["items"]))

    def test_the_list_says_the_folio_even_without_one(self):
        """Un vale del sistema nuevo no tiene folio: se usa su identificador."""
        from app.services.warehouse_voucher_service import buscar_vales

        r = self._vale([self._linea_pieza(self._pieza("FOL-SIN"))])
        lista = buscar_vales(ACTOR, texto=str(r["voucher"]["id_incident"]))
        self.assertEqual(1, lista["total"])
        self.assertEqual(str(r["voucher"]["id_incident"]), lista["items"][0]["folio"])

    def test_only_open_leaves_out_what_came_back(self):
        from app.services.warehouse_voucher_service import buscar_vales

        r = self._vale([self._linea_pieza(self._pieza("FOL-CERRAR"))])
        self.assertEqual(1, buscar_vales(ACTOR, solo_con_pendientes=True)["total"])

        devolver_renglon(r["lines"][0]["id_nm_incident_product"], {}, ACTOR)
        self.assertEqual(0, buscar_vales(ACTOR, solo_con_pendientes=True)["total"])

    def test_the_list_counts_what_is_still_out(self):
        from app.services.warehouse_voucher_service import buscar_vales

        self._vale([self._linea_pieza(self._pieza("FOL-A")),
                    self._linea_pieza(self._pieza("FOL-B"))])
        fila = buscar_vales(ACTOR, solo_con_pendientes=True)["items"][0]
        self.assertEqual(2, fila["open_lines"])
        self.assertEqual(2, fila["total_lines"])


class TestElPrevaleNoMueveElAlmacen(BaseVale):
    """El borrador es lo PEDIDO, no lo entregado.

    Es el control entero: quien pide material deja un borrador y no saca nada;
    quien surte lo autoriza, y ese acto es el que mueve la existencia. Con las
    dos cosas en la misma operacion, pedir era llevarse.
    """

    def _prevale(self, lineas, **extra):
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": 1,
                 "note": "Obra Norte", "lines": lineas,
                 "due_date": (datetime.now() + timedelta(days=30)).strftime(
                     "%Y-%m-%d %H:%M:%S")}
        carga.update(extra)
        return crear_vale(carga, ACTOR, como_borrador=True)

    def test_a_draft_leaves_the_stock_untouched(self):
        self.surtir(5, RACK)
        antes = self._saldo(RACK)

        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])

        self.assertEqual(BORRADOR, r["voucher"]["incident_status"])
        self.assertEqual(antes, self._saldo(RACK),
                         "un borrador no puede descontar")

    def test_authorising_opens_it_and_moves_the_stock(self):
        self.surtir(5, RACK)
        antes = self._saldo(RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])

        # Otro actor: el que pidio no autoriza.
        # Flujo completo: autorizar -> marcar-salido -> confirmar
        abierto = self._autorizacion_completa(r["voucher"]["id_incident"], OTRO_ACTOR)

        self.assertEqual(ABIERTO, abierto["voucher"]["incident_status"])
        self.assertEqual(antes - 2, self._saldo(RACK),
                         "al marcar-salido SI sale el material")

    def test_it_cannot_be_authorised_twice(self):
        """Autorizar dos veces sacaria el material dos veces."""
        self.surtir(5, RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])
        id_vale = r["voucher"]["id_incident"]
        autorizar_vale(id_vale, {}, OTRO_ACTOR)
        despues = self._saldo(RACK)

        with self.assertRaises(AppError) as cm:
            autorizar_vale(id_vale, {}, OTRO_ACTOR)
        self.assertEqual("errors.voucher_not_a_draft", cm.exception.message_key)
        self.assertEqual(despues, self._saldo(RACK),
                         "el intento fallido no puede haber movido nada")

    def test_an_already_open_voucher_is_not_a_draft(self):
        self.surtir(5, RACK)
        r = self._vale([{"id_product": CEMENTO, "quantity": 1,
                         "id_location_from": RACK}])
        with self.assertRaises(AppError) as cm:
            autorizar_vale(r["voucher"]["id_incident"], {}, OTRO_ACTOR)
        self.assertEqual("errors.voucher_not_a_draft", cm.exception.message_key)

    def test_without_the_capability_it_cannot_be_authorised(self):
        """Sin `warehouse_voucher_authorize`, no se autoriza.

        Es el permiso que se le quito al rol Administrator: puede dejar el
        borrador y no puede soltar el material.
        """
        self.surtir(5, RACK)
        antes = self._saldo(RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])

        sin_permiso = {"id_user": 2, "id_proyect": PROYECTO, "id_permission": 999}
        with self.assertRaises(AppError) as cm:
            autorizar_vale(r["voucher"]["id_incident"], {}, sin_permiso)
        self.assertEqual("errors.forbidden", cm.exception.message_key)
        self.assertEqual(antes, self._saldo(RACK))

    def test_the_one_who_asked_cannot_authorise_it(self):
        """Separacion de deberes: si el que pide autoriza, no separa nada.

        Hace falta sembrar la fila de permiso: sin ella salta primero la
        comprobacion de capacidad y la prueba no llegaria a mirar lo que
        pretende mirar -- que TENIENDO el permiso, el que pidio sigue sin poder
        autorizar lo suyo.
        """
        from app.models.entity_permission import EntityPermission

        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=JEFE_DE_ALMACEN,
                entity_name="warehouse_voucher_authorize",
                scope_create=4, scope_read=4, scope_update=4, scope_delete=4,
                created_by=1))

        self.surtir(5, RACK)
        antes = self._saldo(RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])

        # El mismo usuario que lo creo, pero SIN el atajo de superusuario.
        el_mismo = {"id_user": ACTOR["id_user"], "id_proyect": PROYECTO,
                    "id_permission": JEFE_DE_ALMACEN}
        with self.assertRaises(AppError) as cm:
            autorizar_vale(r["voucher"]["id_incident"], {}, el_mismo)
        self.assertEqual("errors.voucher_self_authorization",
                         cm.exception.message_key)
        self.assertEqual(antes, self._saldo(RACK),
                         "el intento rechazado no puede haber movido nada")

    def test_with_the_capability_someone_else_can_authorise_it(self):
        """Y la otra mitad: TENIENDO el permiso y siendo otro, si se autoriza.

        Sin esta, la prueba de arriba pasaria igual si `autorizar_vale`
        rechazara a todo el mundo.
        """
        from app.models.entity_permission import EntityPermission

        with transaction_context() as db:
            db.add(EntityPermission(
                id_permission=JEFE_DE_ALMACEN,
                entity_name="warehouse_voucher_authorize",
                scope_create=4, scope_read=4, scope_update=4, scope_delete=4,
                created_by=1))

        self.surtir(5, RACK)
        antes = self._saldo(RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])

        otro = {"id_user": 2, "id_proyect": PROYECTO,
                "id_permission": JEFE_DE_ALMACEN}
        autorizado = autorizar_vale(r["voucher"]["id_incident"], {}, otro)

        # Autorizar aparta: el material sigue en el almacen hasta entregarlo.
        self.assertEqual(EN_ESPERA, autorizado["voucher"]["incident_status"])
        self.assertEqual(antes, self._saldo(RACK))
        entregar_vale(r["voucher"]["id_incident"], {}, ACTOR)
        self.assertEqual(antes - 2, self._saldo(RACK))


class TestElPrevaleNoPideMasDeLoQueHay(BaseVale):
    """Pedir 5 de lo que tiene 1 no es una peticion que alguien pueda surtir.

    El borrador no mueve el almacen, pero antes tampoco miraba cuanto habia: la
    cantidad solo tenia que ser mayor que cero, y el rechazo llegaba hasta que el
    almacen intentaba autorizar. Ahora el prevale nace comprobado contra la
    existencia de SU ubicacion (la autorizacion la vuelve a comprobar).
    """

    def _prevale(self, lineas):
        carga = {"id_incident_type": TIPO_PRESTAMO, "id_user": 1,
                 "note": "Obra Norte", "lines": lineas,
                 "due_date": (datetime.now() + timedelta(days=30)).strftime(
                     "%Y-%m-%d %H:%M:%S")}
        return crear_vale(carga, ACTOR, como_borrador=True)

    def _renglon(self, cantidad, ubicacion=RACK):
        return {"id_product": CEMENTO, "quantity": cantidad,
                "id_location_from": ubicacion}

    def test_asking_for_more_than_there_is_is_rejected_with_the_numbers(self):
        self.surtir(1, RACK)
        with self.assertRaises(AppError) as cm:
            self._prevale([self._renglon(5)])
        self.assertEqual("errors.voucher_quantity_exceeds_stock",
                         cm.exception.message_key)
        self.assertEqual(5, cm.exception.meta["requested"])
        self.assertEqual(1, cm.exception.meta["available"])

    def test_asking_for_exactly_what_there_is_passes(self):
        self.surtir(3, RACK)
        r = self._prevale([self._renglon(3)])
        self.assertEqual(BORRADOR, r["voucher"]["incident_status"])

    def test_two_lines_of_the_same_product_are_added_before_comparing(self):
        """Dos de 3 contra 4 son 6 pedidos: por separado, los dos pasarian."""
        self.surtir(4, RACK)
        with self.assertRaises(AppError) as cm:
            self._prevale([self._renglon(3), self._renglon(3)])
        self.assertEqual("errors.voucher_quantity_exceeds_stock",
                         cm.exception.message_key)
        self.assertEqual(6, cm.exception.meta["requested"])

    def test_stock_in_another_location_does_not_cover_this_one(self):
        self.surtir(10, NAVE)
        with self.assertRaises(AppError) as cm:
            self._prevale([self._renglon(2, RACK)])
        self.assertEqual("errors.voucher_quantity_exceeds_stock",
                         cm.exception.message_key)
        self.assertEqual(0, cm.exception.meta["available"])

    def test_a_rejected_draft_leaves_no_voucher_behind(self):
        from sqlalchemy import func as _func, select as _select
        from app.models.incident import Incident
        self.surtir(1, RACK)
        with self.assertRaises(AppError):
            self._prevale([self._renglon(5)])
        with transaction_context() as db:
            self.assertEqual(
                0, db.scalar(_select(_func.count()).select_from(Incident)))


class TestLaDevolucionEsPorRenglon(BaseVale):
    """Se piden dos y se devuelve uno primero y el otro despues.

    Cada renglon del vale se cierra por su cuenta: el vale no queda cerrado
    hasta que vuelve el ultimo. Sin esto, devolver una de dos cosas obligaria a
    dejar el vale entero abierto o a cerrarlo con material fuera.
    """

    def test_returning_one_of_two_leaves_the_other_out(self):
        self.surtir(10, RACK)
        r = self._vale([
            {"id_product": CEMENTO, "quantity": 2, "id_location_from": RACK},
            {"id_product": CEMENTO, "quantity": 3, "id_location_from": RACK},
        ])
        id_vale = r["voucher"]["id_incident"]
        primero, segundo = r["lines"][0], r["lines"][1]
        tras_salir = self._saldo(RACK)

        devolver_renglon(primero["id_nm_incident_product"], {}, ACTOR)

        consulta = consultar_vale(id_vale, ACTOR)
        self.assertEqual(ABIERTO, consulta["voucher"]["incident_status"],
                         "con un renglon fuera, el vale sigue abierto")
        self.assertEqual(tras_salir + 2, self._saldo(RACK),
                         "solo vuelve lo del renglon devuelto")

        devolver_renglon(segundo["id_nm_incident_product"], {}, ACTOR)

        consulta = consultar_vale(id_vale, ACTOR)
        self.assertEqual(CERRADO, consulta["voucher"]["incident_status"],
                         "cuando vuelve el ultimo, el vale se cierra")
        self.assertEqual(tras_salir + 5, self._saldo(RACK))


if __name__ == "__main__":
    unittest.main()


class TestElValeSeArchivaComoDocumento(BaseVale):
    """El vale en papel se guarda, no solo se genera al vuelo.

    Un vale es un documento que alguien FIRMA, y cambia: los renglones se
    devuelven uno a uno. Si solo existiera mientras dura la descarga, nadie
    podria ver despues que decia el que se firmo.
    """

    class AlmacenDePrueba:
        """Escribe en memoria, para no tocar el disco en la suite."""

        def __init__(self):
            self.archivos = {}

        def write(self, raw, project_id, document_id, version, extension):
            ruta = "documents/%s/%s/v%s.%s" % (project_id, document_id, version, extension)
            self.archivos[ruta] = raw
            return ruta

        def resolve(self, ruta):
            from pathlib import Path

            class _Falso(Path().__class__):
                pass

            datos = self.archivos[ruta]

            class _Archivo:
                def read_bytes(self_):
                    return datos

            return _Archivo()

    def setUp(self):
        super().setUp()
        from unittest.mock import patch

        from app.models.document import DocumentCategory

        with transaction_context() as db:
            db.add(DocumentCategory(code="warehouse_voucher", name="Vale de almacen",
                                    active=True, created_by=1))
        self.surtir()
        self.almacen = self.AlmacenDePrueba()
        # El PDF de verdad lo arma WeasyPrint, que necesita bibliotecas nativas
        # y tarda; aqui interesa el ARCHIVADO, no el dibujo. Se sustituye el
        # renderizador por uno que devuelve la ficha serializada, que cambia
        # cuando cambia el vale -- que es justo lo que se esta probando.
        self.render = patch(
            "app.services.warehouse_voucher_service._motor_de_documentos")
        motor = self.render.start()
        self.addCleanup(self.render.stop)
        motor.return_value.render_pdf_bytes.side_effect = (
            lambda clave, ficha, *a, **k: repr(sorted(ficha.items())).encode())

    def descargar(self, id_incident):
        from app.services.warehouse_voucher_service import pdf_del_vale

        return pdf_del_vale(id_incident, ACTOR, storage=self.almacen)

    def versiones(self, id_incident):
        from sqlalchemy import select

        from app.models.document import Document, DocumentVersion

        with transaction_context() as db:
            doc = db.scalars(select(Document).where(
                Document.business_reference_type == "incident",
                Document.business_reference_value == str(id_incident))).first()
            if doc is None:
                return []
            return db.scalars(select(DocumentVersion).where(
                DocumentVersion.id_document == doc.id_document
            ).order_by(DocumentVersion.version)).all()

    def test_downloading_it_files_the_document(self):
        vale = self._vale([self._linea_cantidad(10)])

        self.descargar(vale["voucher"]["id_incident"])

        versiones = self.versiones(vale["voucher"]["id_incident"])
        self.assertEqual(1, len(versiones))
        self.assertEqual("pdf", versiones[0].extension)
        self.assertEqual("generated", versiones[0].source)

    def test_downloading_it_again_does_not_file_a_second_copy(self):
        """El mismo papel no se archiva dos veces."""
        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]

        primero = self.descargar(id_vale)
        segundo = self.descargar(id_vale)

        self.assertEqual(primero, segundo)
        self.assertEqual(1, len(self.versiones(id_vale)))

    def test_a_change_in_the_voucher_files_a_new_version(self):
        """Devolver un renglon cambia el papel, y eso si es otra version."""
        from app.services.warehouse_voucher_service import devolver_renglon

        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]
        self.descargar(id_vale)

        devolver_renglon(vale["lines"][0]["id_nm_incident_product"],
                         {"id_location_to": NAVE}, ACTOR)
        self.descargar(id_vale)

        versiones = self.versiones(id_vale)
        self.assertEqual(2, len(versiones))
        self.assertEqual([1, 2], [v.version for v in versiones])

    def test_touching_the_voucher_without_changing_it_files_nothing(self):
        """Lo que decide es el CONTENIDO, no la fecha de modificacion.

        El primer intento comparaba `last_update_date` contra la fecha de la
        version archivada. Dos motivos para abandonarlo, los dos reales:

        * los 141 vales que vinieron del sistema anterior tienen `creation_date`
          y `last_update_date` NULAS -- comprobado en la base --, asi que sin
          fecha con que comparar se archivaba una version nueva en CADA
          descarga, justo de los vales viejos, que son los que mas se consultan;
        * y al reves, cualquier escritura que no cambie el papel -- como esta --
          archivaba una copia identica.
        """
        from datetime import timedelta

        from app.models.incident import Incident

        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]
        self.descargar(id_vale)

        with transaction_context() as db:
            db.get(Incident, id_vale).last_update_date = (
                datetime.now() + timedelta(days=1))

        self.descargar(id_vale)

        self.assertEqual(1, len(self.versiones(id_vale)),
                         "el papel dice lo mismo: no hay nada que archivar")

    def test_the_filed_copy_keeps_what_the_voucher_said(self):
        """La ficha se guarda con la version: se puede leer sin abrir el PDF."""
        vale = self._vale([self._linea_cantidad(10)])

        self.descargar(vale["voucher"]["id_incident"])

        ficha = self.versiones(vale["voucher"]["id_incident"])[0].source_snapshot
        self.assertEqual(1, len(ficha["salidas"]))
        self.assertEqual("Obra Norte", ficha["nota"])


class TestElValeSeLigaAUnaObra(BaseVale):
    """El material se relaciona con el proyecto que lo pidio.

    `id_proyect` en el vale NO es el mismo `id_proyect` que acota quien puede
    ver que -eso es el inquilino, y toda esta suite corre bajo el 30-. Es la
    OBRA a la que va el material, una fila mas de `proyect` como cualquier
    otra orden de trabajo. Se prueba con una fila distinta (OBRA) para que
    quede claro que son dos preguntas distintas sobre la misma tabla.
    """

    def setUp(self):
        super().setUp()
        self.OBRA = 31
        self.surtir()
        with transaction_context() as db:
            db.add(Proyect(id_proyect=self.OBRA, id_customer_supplier=CLIENTE,
                           leader=1, proyect_description="Mantenimiento de puerta",
                           title="MEXINOX", created_by=1))

    def _vale_de_la_obra(self, **extra):
        return self._vale([self._linea_cantidad(5)], id_proyect=self.OBRA, **extra)

    def test_a_voucher_can_be_tied_to_a_project(self):
        vale = self._vale_de_la_obra()

        self.assertEqual(self.OBRA, vale["voucher"]["id_proyect"])

    def test_a_voucher_is_not_forced_into_a_project(self):
        """Un prestamo para el propio taller no pertenece a ninguna obra."""
        vale = self._vale([self._linea_cantidad(5)])

        self.assertIsNone(vale["voucher"]["id_proyect"])

    def test_an_inexistent_project_is_rejected(self):
        with self.assertRaises(AppError) as fallo:
            self._vale([self._linea_cantidad(5)], id_proyect=999999)

        self.assertEqual("errors.not_found", fallo.exception.message_key)

    def test_consulting_the_voucher_names_its_project(self):
        """El detalle del vale trae el proyecto CON nombre, no solo el id."""
        vale = self._vale_de_la_obra()

        detalle = consultar_vale(vale["voucher"]["id_incident"], ACTOR)

        self.assertEqual(self.OBRA, detalle["proyect"]["id_proyect"])
        self.assertEqual("MEXINOX", detalle["proyect"]["title"])

    def test_a_voucher_without_project_names_none(self):
        vale = self._vale([self._linea_cantidad(5)])

        detalle = consultar_vale(vale["voucher"]["id_incident"], ACTOR)

        self.assertIsNone(detalle["proyect"])

    def test_the_voucher_list_is_filtered_by_project(self):
        """Es la pregunta del jefe de obra: que se llevo ESTA obra."""
        self._vale_de_la_obra()
        self._vale([self._linea_cantidad(5)])  # otro vale, sin obra

        resultado = buscar_vales(ACTOR, id_proyect=self.OBRA)

        self.assertEqual(1, resultado["total"])
        self.assertEqual(self.OBRA, resultado["items"][0]["id_proyect"])


class TestLosReportesDeAlmacen(BaseVale):
    """Los 4 reportes que ya existian en el sistema anterior (Adser).

    El caso real que motiva `_sin_cerrar()`: los vales migrados de Adser no
    traen `close_date` en NULL cuando siguen abiertos, traen el sentinela
    `1990-01-01` que la migracion no limpio (a diferencia de
    `product.fecha_baja`, que si paso por `normalizar_fecha()`). Estas pruebas
    fijan que un renglon con ESE valor se lea como abierto, igual que uno con
    NULL de verdad -- y que uno con una fecha real se lea como cerrado.
    """

    def setUp(self):
        super().setUp()
        self.surtir(100)

    def _cerrar_con_sentinela(self, id_linea):
        """Simula un renglon migrado de Adser: cerrado con el sentinela
        heredado del sistema anterior, no con NULL."""
        from app.models.nm_incident_product import NmIncidentProduct

        with transaction_context() as db:
            db.get(NmIncidentProduct, id_linea).close_date = datetime(1990, 1, 1)

    def test_a_line_with_the_inherited_sentinel_counts_as_open(self):
        vale = self._vale([self._linea_cantidad(10)])
        linea = vale["lines"][0]["id_nm_incident_product"]
        self._cerrar_con_sentinela(linea)

        pendientes = reporte_vales_pendientes(ACTOR)

        self.assertEqual(1, pendientes["total"])
        self.assertIsNone(pendientes["items"][0]["close_date"])

    def test_a_line_actually_returned_does_not_count_as_pending(self):
        vale = self._vale([self._linea_cantidad(10)])
        linea = vale["lines"][0]["id_nm_incident_product"]
        devolver_renglon(linea, {}, ACTOR)

        pendientes = reporte_vales_pendientes(ACTOR)

        self.assertEqual(0, pendientes["total"])

    def test_a_line_still_open_with_null_close_date_is_pending(self):
        self._vale([self._linea_cantidad(10)])

        pendientes = reporte_vales_pendientes(ACTOR)

        self.assertEqual(1, pendientes["total"])

    def test_grouped_by_product_uses_the_product_code(self):
        self._vale([self._linea_cantidad(10)])
        self._vale([self._linea_cantidad(20)])

        reporte = reporte_por_producto(ACTOR)

        self.assertEqual(1, len(reporte["groups"]))
        self.assertEqual("CEM-50", reporte["groups"][0]["group"])
        self.assertEqual(2, reporte["groups"][0]["total"])

    def test_grouped_by_project_uses_the_trimmed_note(self):
        """`incident.note` es donde vive el proyecto/sitio para lo migrado de
        Adser -- `id_proyect` y `id_location_*` estan en NULL ahi. Un valor
        sin recortar (como puede traer lo migrado, escrito directo en la
        base y no via `crear_vale`, que ya recorta al capturar) tiene que
        agruparse igual que el ya limpio.
        """
        limpio = self._vale([self._linea_cantidad(10)], note="APELSA")
        sucio = self._vale([self._linea_cantidad(10)], note="APELSA")
        with transaction_context() as db:
            db.get(Incident, sucio["voucher"]["id_incident"]).note = "  APELSA  "

        reporte = reporte_por_almacen(ACTOR)

        self.assertEqual(1, len(reporte["groups"]))
        self.assertEqual("APELSA", reporte["groups"][0]["group"])
        self.assertEqual(2, reporte["groups"][0]["total"])

    def test_a_voucher_without_a_project_note_falls_into_its_own_group(self):
        vale = self._vale([self._linea_cantidad(10)])
        with transaction_context() as db:
            db.get(Incident, vale["voucher"]["id_incident"]).note = "   "

        reporte = reporte_por_almacen(ACTOR)

        self.assertEqual("(sin proyecto)", reporte["groups"][0]["group"])

    def test_grouped_by_requester_uses_the_holder_name(self):
        self._vale([self._linea_cantidad(10)])

        reporte = reporte_por_persona(ACTOR)

        self.assertEqual(1, len(reporte["groups"]))
        self.assertEqual(1, reporte["groups"][0]["total"])

    def test_status_is_entrada_or_salida_by_direction(self):
        vale = self._vale([self._linea_cantidad(10)])
        linea = vale["lines"][0]["id_nm_incident_product"]
        devolver_renglon(linea, {}, ACTOR)

        reporte = reporte_por_producto(ACTOR)
        estados = {r["status"] for r in reporte["groups"][0]["items"]}

        self.assertEqual({"Salida", "Entrada"}, estados)

    def test_status_is_the_incident_type_for_danado_and_destruccion(self):
        with transaction_context() as db:
            db.add(IncidentType(id_incident_type=999,
                                incident_type_description="Dañado",
                                created_by=1))
        self._vale([self._linea_cantidad(10)], id_incident_type=999)

        reporte = reporte_por_producto(ACTOR)

        self.assertEqual("Dañado", reporte["groups"][0]["items"][0]["status"])

    def test_date_range_filters_by_incident_date(self):
        vale = self._vale([self._linea_cantidad(10)])
        with transaction_context() as db:
            db.get(Incident, vale["voucher"]["id_incident"]).incident_date = (
                datetime(2020, 1, 1))

        dentro = reporte_por_producto(ACTOR, fecha_inicio="2019-12-01",
                                      fecha_fin="2020-02-01")
        fuera = reporte_por_producto(ACTOR, fecha_inicio="2021-01-01",
                                     fecha_fin="2021-12-31")

        self.assertEqual(1, dentro["total_items"])
        self.assertEqual(0, fuera["total_items"])

    def test_filtered_by_requester(self):
        self._vale([self._linea_cantidad(10)])

        propio = reporte_por_producto(ACTOR, id_user=1)
        ajeno = reporte_por_producto(ACTOR, id_user=999999)

        self.assertEqual(1, propio["total_items"])
        self.assertEqual(0, ajeno["total_items"])

    def test_a_requester_without_the_warehouse_capability_only_sees_their_own(self):
        """Mismo alcance que el resto del modulo: quien no opera el almacen
        ve lo suyo, aunque pida ver todo con `id_user`."""
        self._vale([self._linea_cantidad(10)])

        sin_permiso = {"id_user": 999999, "is_superuser": False}
        reporte = reporte_por_producto(sin_permiso)

        self.assertEqual(0, reporte["total_items"])


class TestElHistorialDeUnaPersonaEnPdf(BaseVale):
    """El boton nuevo: el historial de una persona -el mismo dato que pinta
    `EmployeeVoucherHistory` en pantalla- descargable en PDF, como lo tenia
    el sistema anterior.

    No se archiva como version de `document` -a diferencia del vale, que se
    firma-, asi que aqui no hace falta un almacen de prueba: solo que la
    ficha que arma el servicio diga lo mismo que `lo_que_ha_pedido`, y que el
    renderizador se llame con la plantilla correcta.
    """

    def setUp(self):
        super().setUp()
        from unittest.mock import patch

        self.surtir(100)
        self.render = patch(
            "app.services.warehouse_voucher_service._motor_de_documentos")
        motor = self.render.start()
        self.addCleanup(self.render.stop)
        motor.return_value.render_pdf_bytes.side_effect = (
            lambda clave, ficha, *a, **k: repr((clave, sorted(ficha.items()))).encode())

    def test_the_fiche_matches_what_the_screen_shows(self):
        from app.services.warehouse_voucher_service import lo_que_ha_pedido

        self._vale([self._linea_cantidad(10)])

        pantalla = lo_que_ha_pedido(ACTOR, 1)
        ficha = documento_del_historial_de_persona(ACTOR, 1)

        self.assertEqual(pantalla["total"], ficha["total"])
        self.assertEqual(pantalla["still_out"], ficha["still_out"])
        self.assertEqual(pantalla["overdue"], ficha["overdue"])
        self.assertEqual(1, len(ficha["grupos"]))
        self.assertEqual("Obra Norte", ficha["grupos"][0]["titulo"])
        renglon = ficha["grupos"][0]["renglones"][0]
        self.assertEqual("Cemento gris 50kg", renglon["descripcion"])
        self.assertEqual("CEM-50", renglon["codigo"])
        self.assertFalse(renglon["devuelto"])

    def test_a_returned_line_is_marked_as_such(self):
        vale = self._vale([self._linea_cantidad(10)])
        linea = vale["lines"][0]["id_nm_incident_product"]
        devolver_renglon(linea, {}, ACTOR)

        ficha = documento_del_historial_de_persona(ACTOR, 1)

        renglon = ficha["grupos"][0]["renglones"][0]
        self.assertTrue(renglon["devuelto"])
        self.assertIsNotNone(renglon["cierre"])

    def test_grouped_by_project_like_the_screen_does(self):
        """Dos vales con nota distinta caen en dos grupos, en el orden en
        que aparece cada uno por primera vez -- `lo_que_ha_pedido` ya
        ordena por fecha descendente, asi que el vale mas reciente (Obra
        Norte, creado segundo) encabeza."""
        self._vale([self._linea_cantidad(10)], note="Obra Sur")
        self._vale([self._linea_cantidad(5)], note="Obra Norte")

        ficha = documento_del_historial_de_persona(ACTOR, 1)

        self.assertEqual(2, len(ficha["grupos"]))
        self.assertEqual(["Obra Norte", "Obra Sur"],
                         [g["titulo"] for g in ficha["grupos"]])

    def test_a_blank_note_falls_into_sin_proyecto(self):
        """`crear_vale` exige nota -- un blanco solo llega por datos
        migrados, escritos directo en la base y no via el servicio."""
        vale = self._vale([self._linea_cantidad(10)])
        with transaction_context() as db:
            db.get(Incident, vale["voucher"]["id_incident"]).note = "   "

        ficha = documento_del_historial_de_persona(ACTOR, 1)

        self.assertEqual("(sin proyecto)", ficha["grupos"][0]["titulo"])

    def test_downloading_it_renders_the_history_template(self):
        self._vale([self._linea_cantidad(10)])

        pdf = pdf_del_historial_de_persona(ACTOR, 1)

        self.assertIn(b"warehouse_voucher_history", pdf)

    def test_someone_without_the_warehouse_capability_only_sees_their_own(self):
        """Mismo alcance que `lo_que_ha_pedido`: quien no opera el almacen ve
        lo suyo, aunque pida el historial de otro `id_user`."""
        self._vale([self._linea_cantidad(10)])

        sin_permiso = {"id_user": 1, "is_superuser": False}
        ficha = documento_del_historial_de_persona(sin_permiso, 999999)

        self.assertEqual(1, ficha["id_user"])
        self.assertEqual(1, ficha["total"])


OPERADOR = 2


ALMACEN = 90


class TestLasNotificacionesDelCicloDelVale(BaseVale):
    """Las tres notificaciones del ciclo prevale -> autorizado -> recibido,
    pedidas aparte de la custodia (2026-10-05): avisar a quien puede
    autorizar (Almacen) cuando nace un prevale, avisar al responsable (y a
    quien recoja) cuando el material sale del almacen -- directo o recien
    autorizado, son el mismo evento en este sistema -- y avisar de vuelta a
    Almacen cuando el responsable confirma que ya lo recibio.
    """

    def setUp(self):
        super().setUp()
        from app.models.entity_permission import EntityPermission
        from app.models.permission import Permission
        from app.models.user import User

        self._otro_usuario(OPERADOR)
        with transaction_context() as db:
            db.add(Permission(
                id_permission=2, permission_description="Almacen",
                authorized_by=1, id_department=1, id_subdepartment=1,
                id_level=1, created_by=1))
            db.flush()
            db.add_all([
                EntityPermission(id_permission=2,
                                 entity_name="warehouse_voucher_authorize",
                                 scope_read=1, created_by=1),
                EntityPermission(id_permission=2, entity_name="warehouse_voucher",
                                 scope_read=1, created_by=1),
            ])
            db.add(User(
                id_user=ALMACEN, full_name="Almacen de pruebas",
                username="almacendepruebas", id_permission=2,
                id_proyect=PROYECTO, id_status=ESTATUS, supervisor=1,
                created_by=1))
        self.surtir(100)

    def _no_leidas(self, id_user):
        from app.services.notification_service import get_user_notifications

        return get_user_notifications(id_user, unread_only=True)

    def test_a_new_prevoucher_notifies_whoever_can_authorize(self):
        vale = self._prevale([self._linea_cantidad(10)])

        notificar_prevale_creado(vale["voucher"]["id_incident"], actor_id=1)

        avisos = self._no_leidas(ALMACEN)
        self.assertEqual(1, len(avisos))
        self.assertEqual("warehouse_voucher_prevoucher_pending",
                         avisos[0].notification_type)

    def test_authorizing_notifies_the_holder(self):
        """El responsable (OPERADOR) es distinto de quien autoriza (ACTOR,
        id_user=1) -- si fueran la misma persona, el aviso se excluiria a
        si mismo (ver `test_it_excludes_the_actor_from_their_own_action`),
        que no es lo que esta prueba quiere comprobar.

        Nota: la notificación se envía desde la RUTA después de que la
        transacción cierra, no desde el servicio, así que este test (que
        llama al servicio directamente) no verifica la notificación.
        """
        vale = self._prevale([self._linea_cantidad(10)], id_user=OPERADOR)
        resultado = autorizar_vale(vale["voucher"]["id_incident"], {}, ACTOR)

        # Verificar que el estado cambió a EN_ESPERA correctamente
        from app.services.warehouse_voucher_service import EN_ESPERA
        self.assertEqual(EN_ESPERA, resultado["voucher"]["incident_status"])

    def test_opening_a_direct_voucher_notifies_the_holder_too(self):
        """Un vale directo ya saca el material al crearse -- no hay un
        "autorizar" aparte -- asi que el mismo aviso aplica aqui."""
        vale = self._vale([self._linea_cantidad(10)], id_user=OPERADOR)

        notificar_material_entregado(vale["voucher"]["id_incident"], actor_id=1)

        avisos = self._no_leidas(OPERADOR)
        self.assertEqual(1, len(avisos))
        self.assertEqual("warehouse_voucher_delivered", avisos[0].notification_type)

    def test_it_excludes_the_actor_from_their_own_action(self):
        vale = self._vale([self._linea_cantidad(10)])  # id_user=1, mismo actor

        notificar_material_entregado(vale["voucher"]["id_incident"], actor_id=1)

        self.assertEqual(0, len(self._no_leidas(1)))

    def test_a_write_off_voucher_is_not_notified(self):
        """Una baja (destruccion/extraviado) no se reclama -- avisar "pasa
        por el" ahi confundiria. Ver `TIPOS_DE_BAJA`."""
        with transaction_context() as db:
            db.add(IncidentType(id_incident_type=90,
                                incident_type_description="Destruccion",
                                created_by=1))
        vale = self._vale([self._linea_cantidad(10)], id_incident_type=90,
                          id_user=OPERADOR)

        notificar_material_entregado(vale["voucher"]["id_incident"], actor_id=1)

        self.assertEqual(0, len(self._no_leidas(OPERADOR)))


class TestElJobDeValesVencidos(BaseVale):
    """`notify_overdue_vouchers` -- el mismo criterio que `vales_vencidos`,
    convertido en una notificacion real (campanita) en vez de una pregunta
    bajo demanda."""

    def setUp(self):
        super().setUp()
        self.surtir(100)

    def _correr_job(self):
        from app.jobs.tasks_warehouse import notify_overdue_vouchers

        return notify_overdue_vouchers()

    def _no_leidas(self, id_user):
        from app.services.notification_service import get_user_notifications

        return get_user_notifications(id_user, unread_only=True)

    def test_it_notifies_the_holder_of_an_overdue_line(self):
        vale = self._vale([self._linea_cantidad(10)])
        self.vencer(vale["lines"][0]["id_nm_incident_product"])

        resultado = self._correr_job()

        self.assertEqual(1, resultado["count"])
        avisos = self._no_leidas(1)
        self.assertEqual(1, len(avisos))
        self.assertEqual("warehouse_voucher_overdue", avisos[0].notification_type)

    def test_it_never_repeats_the_same_notification(self):
        """Sin `overdue_notified_date` esto avisaria de nuevo cada corrida
        mientras el renglon siga vencido -- ver el docstring del job."""
        vale = self._vale([self._linea_cantidad(10)])
        self.vencer(vale["lines"][0]["id_nm_incident_product"])

        primera = self._correr_job()
        segunda = self._correr_job()

        self.assertEqual(1, primera["count"])
        self.assertEqual(0, segunda["count"])
        self.assertEqual(1, len(self._no_leidas(1)))

    def test_it_ignores_lines_that_are_not_due_yet(self):
        self._vale([self._linea_cantidad(10)])

        resultado = self._correr_job()

        self.assertEqual(0, resultado["count"])

    def test_it_ignores_closed_lines(self):
        vale = self._vale([self._linea_cantidad(10)])
        linea = vale["lines"][0]["id_nm_incident_product"]
        self.vencer(linea)
        devolver_renglon(linea, {}, ACTOR)

        resultado = self._correr_job()

        self.assertEqual(0, resultado["count"])


# --- entrega separada de la autorizacion, recibido y complementario -----------

from app.services.warehouse_voucher_service import (  # noqa: E402
    PROYECTO_ACTIVO,
    confirmar_recibido_del_vale,
    entregar_vale,
    estado_de_entrega,
)

# El responsable actuando como el supervisor que es: sin el pase de
# superusuario, para que los candados de verdad se ejerzan.
SUPERVISOR = {"id_user": 1}
ALMACEN_SIN_PASE = {"id_user": OPERADOR}


class BaseEntrega(BaseVale):
    def setUp(self):
        super().setUp()
        self._otro_usuario(OPERADOR)
        self.surtir(100)

    def _proyecto_en(self, estado, id_proyect=PROYECTO):
        with transaction_context() as db:
            db.get(Proyect, id_proyect).proyect_status = estado

    def _estado(self, vale):
        with transaction_context() as db:
            return estado_de_entrega(db.get(Incident, vale["voucher"]["id_incident"]))

    def _borrador(self, lineas):
        """Un prevale de verdad. `_vale(..., como_borrador=True)` NO lo es:
        mete la bandera en el cuerpo y `crear_vale` la lee como argumento."""
        return crear_vale({
            "id_incident_type": TIPO_PRESTAMO, "id_user": 1, "note": "Obra Norte",
            "lines": lineas,
            "due_date": (datetime.now() + timedelta(days=30)).strftime(
                "%Y-%m-%d %H:%M:%S")}, ACTOR, como_borrador=True)

    def _error(self, funcion, *args, **kwargs):
        with self.assertRaises(AppError) as caja:
            funcion(*args, **kwargs)
        return caja.exception


class TestElSeguimientoDeEntrega(BaseEntrega):

    def test_a_new_voucher_is_waiting_to_be_delivered(self):
        vale = self._vale([self._linea_cantidad(10)])
        self.assertEqual("por_entregar", self._estado(vale))

    def test_a_draft_is_waiting_to_be_authorized(self):
        vale = self._borrador([self._linea_cantidad(10)])
        self.assertEqual("por_autorizar", self._estado(vale))

    def test_a_voucher_from_before_has_no_delivery_tracking(self):
        """Ni se espera una entrega ni se le inventa una confirmacion."""
        vale = self._vale([self._linea_cantidad(10)])
        with transaction_context() as db:
            db.get(Incident, vale["voucher"]["id_incident"]).tracks_delivery = False
        self.assertIsNone(self._estado(vale))
        detalle = consultar_vale(vale["voucher"]["id_incident"], ACTOR)
        self.assertIsNone(detalle["delivery_status"])

    def test_delivering_to_someone_else_demands_a_note(self):
        vale = self._vale([self._linea_cantidad(10)])
        self._otro_usuario(3)

        e = self._error(entregar_vale, vale["voucher"]["id_incident"],
                        {"id_user": 3}, ACTOR)

        self.assertEqual("errors.voucher_delivery_note_required", e.message_key)

    def test_a_draft_cannot_be_delivered(self):
        vale = self._borrador([self._linea_cantidad(10)])

        e = self._error(entregar_vale, vale["voucher"]["id_incident"], {}, ACTOR)

        self.assertEqual("errors.voucher_not_authorized", e.message_key)

    def test_it_cannot_be_delivered_twice(self):
        vale = self._vale([self._linea_cantidad(10)])
        entregar_vale(vale["voucher"]["id_incident"], {}, ACTOR)

        e = self._error(entregar_vale, vale["voucher"]["id_incident"], {}, ACTOR)

        self.assertEqual("errors.voucher_already_delivered", e.message_key)

    def test_only_the_warehouse_can_mark_a_delivery(self):
        vale = self._vale([self._linea_cantidad(10)])

        e = self._error(entregar_vale, vale["voucher"]["id_incident"], {},
                        ALMACEN_SIN_PASE)

        self.assertEqual(403, e.status_code)

    def test_the_queues_filter_by_delivery_state(self):
        a = self._vale([self._linea_cantidad(5)])
        b = self._vale([self._linea_cantidad(5)])
        entregar_vale(b["voucher"]["id_incident"], {}, ACTOR)

        por_entregar = buscar_vales(ACTOR, entrega="por_entregar")
        por_confirmar = buscar_vales(ACTOR, entrega="por_confirmar")

        self.assertEqual([a["voucher"]["id_incident"]],
                         [v["id_incident"] for v in por_entregar["items"]])
        self.assertEqual([b["voucher"]["id_incident"]],
                         [v["id_incident"] for v in por_confirmar["items"]])
        self.assertEqual(400, self._error(buscar_vales, ACTOR,
                                          entrega="inventada").status_code)


class TestLaConfirmacionDeRecibido(BaseEntrega):

    def _entregado(self, **extra):
        vale = self._vale([self._linea_cantidad(10)], **extra)
        entregar_vale(vale["voucher"]["id_incident"], {}, ACTOR)
        return vale["voucher"]["id_incident"]

    def test_it_cannot_be_confirmed_before_the_delivery(self):
        vale = self._vale([self._linea_cantidad(10)])

        e = self._error(confirmar_recibido_del_vale,
                        vale["voucher"]["id_incident"], {}, SUPERVISOR)

        self.assertEqual("errors.voucher_not_delivered", e.message_key)

    def test_the_holder_confirms_it(self):
        id_vale = self._entregado()

        r = confirmar_recibido_del_vale(id_vale, {}, SUPERVISOR)

        self.assertEqual("recibido", r["delivery_status"])
        self.assertEqual(1, r["voucher"]["received_confirmed_by"])

    def test_nobody_else_confirms_for_the_holder(self):
        """Ni quien recogio ni el almacen confirman por el supervisor."""
        id_vale = self._entregado()

        e = self._error(confirmar_recibido_del_vale, id_vale, {}, ALMACEN_SIN_PASE)

        self.assertEqual(403, e.status_code)

    def test_observations_demand_a_note(self):
        id_vale = self._entregado()

        e = self._error(confirmar_recibido_del_vale, id_vale, {"ok": False},
                        SUPERVISOR)
        self.assertEqual("errors.required_field", e.message_key)

        r = confirmar_recibido_del_vale(
            id_vale, {"ok": False, "note": "Falto un desarmador"}, SUPERVISOR)
        self.assertEqual("recibido_con_observaciones", r["delivery_status"])

    def test_it_cannot_be_confirmed_twice(self):
        id_vale = self._entregado()
        confirmar_recibido_del_vale(id_vale, {}, SUPERVISOR)

        e = self._error(confirmar_recibido_del_vale, id_vale, {}, SUPERVISOR)

        self.assertEqual("errors.voucher_already_received", e.message_key)

    def test_a_voucher_from_before_cannot_be_confirmed(self):
        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]
        with transaction_context() as db:
            db.get(Incident, id_vale).tracks_delivery = False

        e = self._error(confirmar_recibido_del_vale, id_vale, {}, SUPERVISOR)

        self.assertEqual("errors.voucher_without_delivery_tracking", e.message_key)


class TestQuienRecogeSinUsuario(BaseEntrega):

    def test_delivering_defaults_to_the_designated_external(self):
        vale = self._vale([self._linea_cantidad(10)], pickup_name="Juan Perez")

        r = entregar_vale(vale["voucher"]["id_incident"], {}, ACTOR)

        self.assertEqual("Juan Perez", r["voucher"]["delivered_to_name"])


class TestElValeComplementario(BaseEntrega):

    def setUp(self):
        super().setUp()
        self._proyecto_en("in_progress")
        self.padre = self._vale([self._linea_cantidad(10)], id_proyect=PROYECTO)

    def _complementario(self, **extra):
        carga = {"id_proyect": PROYECTO,
                 "id_incident_parent": self.padre["voucher"]["id_incident"]}
        carga.update(extra)
        return self._vale([self._linea_cantidad(5)], **carga)

    def test_it_is_linked_to_the_original(self):
        hijo = self._complementario()

        self.assertEqual(self.padre["voucher"]["id_incident"],
                         hijo["voucher"]["id_incident_parent"])

    def test_every_active_status_allows_it(self):
        for estado in PROYECTO_ACTIVO:
            self._proyecto_en(estado)
            self._complementario()

    def test_a_project_that_is_not_active_rejects_it(self):
        for estado in ("draft", "submitted", "blocked", "denied",
                       "completed", "delivered", "cancelled"):
            self._proyecto_en(estado)
            e = self._error(self._complementario)
            self.assertEqual("errors.voucher_project_not_active", e.message_key,
                             estado)

    def test_it_must_be_of_the_same_project(self):
        with transaction_context() as db:
            db.add(Proyect(id_proyect=31, id_customer_supplier=CLIENTE, leader=1,
                           proyect_description="Obra Sur", proyect_status="in_progress",
                           created_by=1))

        e = self._error(self._complementario, id_proyect=31)

        self.assertEqual("errors.voucher_parent_other_project", e.message_key)

    def test_it_demands_a_project(self):
        e = self._error(self._vale, [self._linea_cantidad(5)],
                        id_incident_parent=self.padre["voucher"]["id_incident"])

        self.assertEqual("errors.voucher_parent_other_project", e.message_key)

    def test_an_unknown_parent_is_a_404(self):
        e = self._error(self._complementario, id_incident_parent=99999)

        self.assertEqual(404, e.status_code)

    def test_whoever_only_requests_cannot_hang_from_someone_elses_voucher(self):
        """Mismo alcance que abrir un vale ajeno por su numero: 404."""
        e = self._error(
            crear_vale,
            {"id_incident_type": TIPO_PRESTAMO, "id_user": OPERADOR,
             "note": "x", "id_proyect": PROYECTO,
             "id_incident_parent": self.padre["voucher"]["id_incident"],
             "lines": [self._linea_cantidad(5)],
             "due_date": (datetime.now() + timedelta(days=30)).strftime(
                 "%Y-%m-%d %H:%M:%S")},
            ALMACEN_SIN_PASE)

        self.assertEqual(404, e.status_code)

    def test_it_inherits_the_delivery_tracking(self):
        hijo = self._complementario()

        self.assertEqual("por_entregar", self._estado(hijo))


# --- notificaciones con destino ----------------------------------------------

from app.services.warehouse_voucher_service import (  # noqa: E402
    notificar_entrega_registrada,
)


class TestLasNotificacionesLlevanAUnDestino(BaseEntrega):
    """Un clic en la campana abre el registro que origino el aviso: cada
    notificacion trae `target_entity` + `target_id`."""

    def _no_leidas(self, id_user):
        from app.services.notification_service import get_user_notifications

        return get_user_notifications(id_user, unread_only=True)

    def _crear(self, **extra):
        from app.services.notification_service import create_notification

        base = {"id_user_recipient": 1, "notification_type": "custom",
                "title": "x", "created_by": 1}
        base.update(extra)
        return create_notification(**base).serialize()

    def test_an_explicit_target_is_kept(self):
        n = self._crear(target_entity="voucher", target_id=7)

        self.assertEqual("voucher", n["target_entity"])
        self.assertEqual(7, n["target_id"])

    def test_a_project_notification_without_target_points_at_its_project(self):
        """Un productor viejo, que solo pasa `id_proyect`, sigue llevando al
        proyecto sin tocar su codigo."""
        n = self._crear(id_proyect=PROYECTO)

        self.assertEqual("proyect", n["target_entity"])
        self.assertEqual(PROYECTO, n["target_id"])

    def test_half_a_target_is_no_target(self):
        """O es un par completo o no hay destino: medio destino no abre nada."""
        n = self._crear(target_entity="voucher")

        self.assertIsNone(n["target_entity"])
        self.assertIsNone(n["target_id"])

    def test_a_notification_with_nothing_has_no_target(self):
        n = self._crear()

        self.assertIsNone(n["target_entity"])
        self.assertIsNone(n["target_id"])

    def test_the_overdue_job_points_at_the_voucher(self):
        from app.jobs.tasks_warehouse import notify_overdue_vouchers

        vale = self._vale([self._linea_cantidad(10)])
        self.vencer(vale["lines"][0]["id_nm_incident_product"])

        notify_overdue_vouchers.run() if hasattr(notify_overdue_vouchers, "run") \
            else notify_overdue_vouchers()

        aviso = self._no_leidas(1)[0].serialize()
        self.assertEqual("voucher", aviso["target_entity"])
        self.assertEqual(vale["voucher"]["id_incident"], aviso["target_id"])

    def test_the_holder_is_told_when_the_warehouse_delivers(self):
        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]

        notificar_entrega_registrada(id_vale, actor_id=OPERADOR)

        avisos = self._no_leidas(1)
        self.assertEqual(1, len(avisos))
        self.assertEqual("warehouse_voucher_delivered", avisos[0].notification_type)
        self.assertEqual("voucher", avisos[0].serialize()["target_entity"])
        self.assertEqual(id_vale, avisos[0].serialize()["target_id"])

    def test_nobody_is_told_about_their_own_delivery(self):
        vale = self._vale([self._linea_cantidad(10)])

        notificar_entrega_registrada(vale["voucher"]["id_incident"], actor_id=1)

        self.assertEqual(0, len(self._no_leidas(1)))

    def test_a_failure_to_notify_the_delivery_never_raises(self):
        from unittest.mock import patch

        vale = self._vale([self._linea_cantidad(10)])

        with patch("app.services.notification_service.create_notification",
                   side_effect=RuntimeError("boom")):
            notificar_entrega_registrada(
                vale["voucher"]["id_incident"], actor_id=OPERADOR)


# --- el PDF dice quien recoge, a quien se entrego y quien recibio -------------

class TestElPdfDiceLaEntrega(BaseEntrega):
    """El papel firmado tiene que decir lo mismo que la pantalla: quien recoge,
    a quien se la dio almacen de verdad y si el responsable ya confirmo."""

    def _ficha(self, vale):
        return documento_del_vale(vale["voucher"]["id_incident"], ACTOR)

    def _html(self, ficha):
        """La plantilla REAL renderizada con la ficha: lo que se imprime."""
        import os

        from jinja2 import Environment, FileSystemLoader

        carpeta = os.path.join(os.environ.get("DOCUMENTS_REPORTS_ROOT", "/documents-reports"),
                               "templates")
        if not os.path.isdir(carpeta):
            self.skipTest("la plantilla no esta montada en este entorno")
        plantilla = Environment(loader=FileSystemLoader(carpeta)).get_template(
            "warehouse_voucher.html")
        return plantilla.render(record=ficha)

    def test_it_says_when_an_external_picks_it_up(self):
        vale = self._vale([self._linea_cantidad(10)], pickup_name="Juan Perez")

        ficha = self._ficha(vale)

        self.assertEqual({"nombre": "Juan Perez", "externo": True,
                          "es_responsable": False}, ficha["recoge"])
        html = self._html(ficha)
        self.assertIn("Juan Perez", html)
        self.assertIn("persona externa", html)

    def test_without_a_designated_pickup_the_holder_picks_it_up(self):
        vale = self._vale([self._linea_cantidad(10)])

        ficha = self._ficha(vale)

        self.assertTrue(ficha["recoge"]["es_responsable"])
        self.assertIn("el responsable", self._html(ficha))

    def test_it_says_to_whom_the_warehouse_really_delivered(self):
        vale = self._vale([self._linea_cantidad(10)])
        self._otro_usuario(3)
        entregar_vale(vale["voucher"]["id_incident"],
                      {"id_user": 3, "note": "Fue otro por el"}, ACTOR)

        ficha = self._ficha(vale)

        self.assertEqual("Operador 3", ficha["entrega"]["recibio"])
        self.assertEqual("Fue otro por el", ficha["entrega"]["nota"])
        html = self._html(ficha)
        self.assertIn("Fue otro por el", html)
        # La firma de quien recibe lleva el nombre de quien SI recibio.
        self.assertIn("Recibe: Operador 3", html)

    def test_the_signature_box_names_an_external_who_receives(self):
        vale = self._vale([self._linea_cantidad(10)], pickup_name="Juan Perez")
        entregar_vale(vale["voucher"]["id_incident"], {}, ACTOR)

        html = self._html(self._ficha(vale))

        self.assertIn("Recibe: Juan Perez (persona externa)", html)

    def test_a_pending_receipt_is_said_so(self):
        vale = self._vale([self._linea_cantidad(10)])
        entregar_vale(vale["voucher"]["id_incident"], {}, ACTOR)

        html = self._html(self._ficha(vale))

        self.assertIn("Pendiente de confirmar el recibido", html)

    def test_a_confirmed_receipt_with_observations_is_printed(self):
        vale = self._vale([self._linea_cantidad(10)])
        id_vale = vale["voucher"]["id_incident"]
        entregar_vale(id_vale, {}, ACTOR)
        confirmar_recibido_del_vale(
            id_vale, {"ok": False, "note": "Falto la caja de brocas"}, SUPERVISOR)

        ficha = self._ficha(vale)

        self.assertFalse(ficha["recibido"]["ok"])
        self.assertIn("Recibido con observaciones: Falto la caja de brocas",
                      self._html(ficha))

    def test_a_voucher_not_yet_delivered_says_so(self):
        vale = self._vale([self._linea_cantidad(10)])

        html = self._html(self._ficha(vale))

        self.assertIn("Pendiente de entrega", html)

    def test_a_complementary_voucher_names_its_original(self):
        self._proyecto_en("in_progress")
        padre = self._vale([self._linea_cantidad(10)], id_proyect=PROYECTO)
        hijo = self._vale([self._linea_cantidad(5)], id_proyect=PROYECTO,
                          id_incident_parent=padre["voucher"]["id_incident"])

        ficha = self._ficha(hijo)

        self.assertEqual(str(padre["voucher"]["id_incident"]),
                         ficha["complementario_de"])
        self.assertIn("Complementario del vale", self._html(ficha))

    def test_a_voucher_from_before_prints_exactly_as_it_always_did(self):
        """Sin seguimiento no se agrega nada: ni 'Recoge' ni 'Pendiente de'."""
        vale = self._vale([self._linea_cantidad(10)])
        with transaction_context() as db:
            db.get(Incident, vale["voucher"]["id_incident"]).tracks_delivery = False

        ficha = self._ficha(vale)
        html = self._html(ficha)

        self.assertFalse(ficha["con_seguimiento"])
        self.assertIsNone(ficha["recoge"])
        self.assertNotIn("Pendiente de entrega", html)
        self.assertNotIn("Recoge:", html)
        self.assertNotIn("Recibe:", html)


class TestElMaterialDelProyectoNoCuentaLoQueNoSalio(BaseEntrega):
    """El proyecto dice lo que la obra se llevo: un prevale es una peticion."""

    def _material(self):
        from app.services.project_management_service import _material_del_proyecto

        with transaction_context() as db:
            return _material_del_proyecto(db, PROYECTO)

    def _para_el_proyecto(self, lineas):
        return crear_vale({
            "id_incident_type": TIPO_PRESTAMO, "id_user": 1, "note": "Obra Norte",
            "id_proyect": PROYECTO, "lines": lineas,
            "due_date": (datetime.now() + timedelta(days=30)).strftime(
                "%Y-%m-%d %H:%M:%S")}, ACTOR, como_borrador=True)

    def test_a_draft_is_not_material_taken_by_the_project(self):
        self._para_el_proyecto([self._linea_cantidad(2)])

        self.assertEqual(0, self._material()["taken_total"])

    def test_an_authorized_voucher_is_reserved_not_taken(self):
        borrador = self._para_el_proyecto([self._linea_cantidad(2)])

        autorizar_vale(borrador["voucher"]["id_incident"], {}, OTRO_ACTOR)

        self.assertEqual(0, self._material()["taken_total"])

    def test_a_shipped_voucher_counts_for_the_project(self):
        borrador = self._para_el_proyecto([self._linea_cantidad(2)])
        id_vale = borrador["voucher"]["id_incident"]

        autorizar_vale(id_vale, {}, OTRO_ACTOR)
        entregar_vale(id_vale, {}, OTRO_ACTOR)

        resumen = self._material()
        self.assertEqual(2, resumen["taken_total"])
        self.assertEqual(2, resumen["still_out_total"])

    def test_a_cancelled_voucher_does_not_count(self):
        borrador = self._para_el_proyecto([self._linea_cantidad(2)])
        with transaction_context() as db:
            db.get(Incident, borrador["voucher"]["id_incident"]).incident_status = "cancelado"

        self.assertEqual(0, self._material()["taken_total"])

    def test_a_voucher_from_before_without_status_still_counts(self):
        borrador = self._para_el_proyecto([self._linea_cantidad(2)])
        with transaction_context() as db:
            db.get(Incident, borrador["voucher"]["id_incident"]).incident_status = None

        self.assertEqual(2, self._material()["taken_total"])


class TestLosTiposDeValePorRol(BaseVale):
    """Gerencia levanta cualquier tipo; Almacen solo los de herramienta;
    Supervisor solo prestamo, danado, extraviado y reparacion (y como prevale)."""

    P_ALMACEN, P_SUPERVISOR, P_GERENCIA = 71, 72, 73
    T_JORNADA, T_REPARACION, T_DESTRUCCION = 191, 192, 193

    def setUp(self):
        super().setUp()
        from app.models.entity_permission import EntityPermission

        with transaction_context() as db:
            db.add_all([
                IncidentType(id_incident_type=self.T_JORNADA,
                             incident_type_description="Jornada", created_by=1),
                IncidentType(id_incident_type=self.T_REPARACION,
                             incident_type_description="Reparación", created_by=1),
                IncidentType(id_incident_type=self.T_DESTRUCCION,
                             incident_type_description="Destruccion", created_by=1),
            ])
            for permiso, entidad in (
                    (self.P_ALMACEN, "warehouse_voucher"),
                    (self.P_SUPERVISOR, "warehouse_prevoucher"),
                    (self.P_GERENCIA, "project_authorization")):
                db.add(EntityPermission(
                    id_permission=permiso, entity_name=entidad,
                    scope_create=4, scope_read=4, scope_update=4, scope_delete=4,
                    created_by=1))

    def _error(self, funcion, *args, **kwargs):
        with self.assertRaises(AppError) as caja:
            funcion(*args, **kwargs)
        return caja.exception

    def _levantar(self, permiso, tipo, borrador):
        self.surtir(5, RACK)
        actor = {"id_user": 1, "id_proyect": PROYECTO, "id_permission": permiso}
        return crear_vale(
            {"id_incident_type": tipo, "id_user": 1, "note": "x",
             "due_date": (datetime.now() + timedelta(days=7)).strftime(
                 "%Y-%m-%d %H:%M:%S"),
             "lines": [{"id_product": CEMENTO, "quantity": 1,
                        "id_location_from": RACK}]},
            actor, como_borrador=borrador)

    def test_management_can_raise_any_type(self):
        r = self._levantar(self.P_GERENCIA, self.T_JORNADA, False)

        self.assertEqual("abierto", r["voucher"]["incident_status"])

    def test_the_warehouse_cannot_raise_a_non_tool_type(self):
        e = self._error(self._levantar, self.P_ALMACEN, self.T_JORNADA, False)

        self.assertEqual(403, e.status_code)

    def test_the_warehouse_can_raise_destruction(self):
        self._levantar(self.P_ALMACEN, self.T_DESTRUCCION, False)

    def test_a_supervisor_can_request_a_repair(self):
        r = self._levantar(self.P_SUPERVISOR, self.T_REPARACION, True)

        self.assertEqual(BORRADOR, r["voucher"]["incident_status"])

    def test_a_supervisor_cannot_request_destruction(self):
        e = self._error(self._levantar, self.P_SUPERVISOR, self.T_DESTRUCCION, True)

        self.assertEqual(403, e.status_code)

    def test_a_supervisor_cannot_open_a_voucher_directly(self):
        e = self._error(self._levantar, self.P_SUPERVISOR, TIPO_PRESTAMO, False)

        self.assertEqual(403, e.status_code)

    def test_the_selector_only_offers_what_the_role_can_raise(self):
        from app.services.warehouse_voucher_service import filtrar_tipos_de_vale

        todos = [{"incident_type_description": d}
                 for d in ("Prestamo", "Jornada", "Destruccion", "Reparación")]
        actor = {"id_user": OPERADOR, "id_permission": self.P_SUPERVISOR}

        ofrecidos = [o["incident_type_description"]
                     for o in filtrar_tipos_de_vale(todos, actor)]

        self.assertEqual(["Prestamo", "Reparación"], ofrecidos)

    def test_delivering_moves_the_stock_and_confirming_opens_it(self):
        self.surtir(5, RACK)
        antes = self._saldo(RACK)
        r = self._prevale([{"id_product": CEMENTO, "quantity": 2,
                            "id_location_from": RACK}])
        id_vale = r["voucher"]["id_incident"]

        autorizar_vale(id_vale, {}, OTRO_ACTOR)
        self.assertEqual(antes, self._saldo(RACK))
        entregado = entregar_vale(id_vale, {}, OTRO_ACTOR)
        self.assertEqual(EN_TRANSITO, entregado["voucher"]["incident_status"])
        self.assertEqual(antes - 2, self._saldo(RACK))
        confirmado = confirmar_recibido_del_vale(id_vale, {}, ACTOR)

        self.assertEqual(ABIERTO, confirmado["voucher"]["incident_status"])


class TestLoApartadoNoSeVuelveAPedir(BaseVale):
    def test_a_second_prevoucher_cannot_ask_for_the_only_unit(self):
        self.surtir(1, RACK)
        linea = {"id_product": CEMENTO, "quantity": 1, "id_location_from": RACK}
        self._prevale([linea])

        with self.assertRaises(AppError) as caja:
            self._prevale([dict(linea)])

        self.assertEqual("errors.voucher_quantity_exceeds_stock", caja.exception.message_key)

    def test_the_trace_offers_only_what_is_not_reserved(self):
        from app.services.inventory_trace_service import localizar

        self.surtir(3, RACK)
        self._prevale([{"id_product": CEMENTO, "quantity": 2, "id_location_from": RACK}])

        sitio = localizar("cemento", ACTOR)["items"][0]["locations"][0]

        self.assertEqual((3, 2, 1), (sitio["quantity"], sitio["reserved"], sitio["available"]))


class TestQuienResponde(TestLosTiposDeValePorRol):
    """El supervisor del proyecto responde solo cuando GERENCIA levanta el vale;
    `proyect.id_supervisor` (Jefe de taller que lo tomo) nunca pisa a nadie."""

    def _en_proyecto(self, permiso, id_user, tipo=TIPO_PRESTAMO, borrador=False):
        self.surtir(5, RACK)
        actor = {"id_user": 1, "id_proyect": PROYECTO, "id_permission": permiso}
        return crear_vale(
            {"id_incident_type": tipo, "id_user": id_user, "note": "x", "id_proyect": PROYECTO,
             "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
             "lines": [{"id_product": CEMENTO, "quantity": 1, "id_location_from": RACK}]},
            actor, como_borrador=borrador)

    def _proyecto_con_lider_y_jefe_de_taller(self, lider, jefe):
        with transaction_context() as db:
            p = db.get(Proyect, PROYECTO)
            p.leader, p.id_supervisor = lider, jefe

    def test_management_assigns_the_project_supervisor_as_responsible(self):
        lider = self._otro_usuario(7)
        self._proyecto_con_lider_y_jefe_de_taller(lider, 1)

        r = self._en_proyecto(self.P_GERENCIA, id_user=1)

        self.assertEqual(lider, r["voucher"]["id_user"])

    def test_a_supervisor_keeps_whoever_they_chose_even_if_a_workshop_head_took_the_project(self):
        jefe = self._otro_usuario(8)
        self._proyecto_con_lider_y_jefe_de_taller(1, jefe)

        r = self._en_proyecto(self.P_SUPERVISOR, id_user=1, borrador=True)

        self.assertEqual(1, r["voucher"]["id_user"])


class TestUnProyectoNoSeCierraConMaterialPendiente(BaseVale):
    def test_cancelling_the_project_is_refused_while_a_voucher_holds_material(self):
        from app.services.project_management_service import transition_management

        self.surtir(5, RACK)
        self._prevale([{"id_product": CEMENTO, "quantity": 1, "id_location_from": RACK}],
                      id_proyect=PROYECTO)

        with self.assertRaises(AppError) as caja:
            transition_management(PROYECTO, {"management_status": "cancelado"}, ACTOR)

        self.assertEqual("errors.project_open_vouchers", caja.exception.message_key)


class TestCancelarUnVale(BaseVale):
    def _prevale_con_stock(self, **extra):
        self.surtir(2, RACK)
        return self._prevale([{"id_product": CEMENTO, "quantity": 2, "id_location_from": RACK}], **extra)

    def test_cancelling_a_draft_releases_what_it_reserved(self):
        from app.services.warehouse_voucher_service import cancelar_vale

        r = self._prevale_con_stock()
        with self.assertRaises(AppError):
            self._prevale([{"id_product": CEMENTO, "quantity": 1, "id_location_from": RACK}])

        cancelado = cancelar_vale(r["voucher"]["id_incident"], {"note": "ya no se necesita"}, ACTOR)

        self.assertEqual("cancelado", cancelado["voucher"]["incident_status"])
        self._prevale([{"id_product": CEMENTO, "quantity": 2, "id_location_from": RACK}])

    def test_a_cancelled_vale_leaves_no_open_lines(self):
        from app.services.warehouse_voucher_service import cancelar_vale, vales_vencidos

        r = self._prevale_con_stock()
        cancelar_vale(r["voucher"]["id_incident"], {"note": "error de captura"}, ACTOR)

        self.assertEqual([], [x for x in vales_vencidos(ACTOR)["items"]
                              if x.get("id_incident") == r["voucher"]["id_incident"]])

    def test_the_reason_is_required(self):
        from app.services.warehouse_voucher_service import cancelar_vale

        r = self._prevale_con_stock()
        with self.assertRaises(AppError) as caja:
            cancelar_vale(r["voucher"]["id_incident"], {}, ACTOR)

        self.assertEqual(400, caja.exception.status_code)

    def test_a_vale_that_already_gave_out_material_cannot_be_cancelled(self):
        from app.services.warehouse_voucher_service import cancelar_vale

        r = self._prevale_con_stock()
        id_vale = r["voucher"]["id_incident"]
        autorizar_vale(id_vale, {}, OTRO_ACTOR)
        entregar_vale(id_vale, {}, OTRO_ACTOR)

        with self.assertRaises(AppError) as caja:
            cancelar_vale(id_vale, {"note": "tarde"}, ACTOR)

        self.assertEqual("errors.voucher_not_cancellable", caja.exception.message_key)

    def test_a_stranger_without_warehouse_rights_cannot_cancel_it(self):
        from app.services.warehouse_voucher_service import cancelar_vale

        r = self._prevale_con_stock()
        extrano = {"id_user": 2, "id_permission": 999}
        with self.assertRaises(AppError) as caja:
            cancelar_vale(r["voucher"]["id_incident"], {"note": "x"}, extrano)

        self.assertEqual(404, caja.exception.status_code)

    def test_a_destruction_vale_needs_no_return_date(self):
        self.surtir(3, RACK)
        with transaction_context() as db:
            db.add(IncidentType(id_incident_type=555, incident_type_description="Destruccion",
                                created_by=1))
        crear_vale({"id_incident_type": 555, "id_user": 1, "note": "se rompio",
                    "lines": [{"id_product": CEMENTO, "quantity": 1, "id_location_from": RACK}]},
                   ACTOR)
