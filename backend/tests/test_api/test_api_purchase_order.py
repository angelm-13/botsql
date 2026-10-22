"""La orden de compra y la evidencia de que se compro.

Lo que estas pruebas sostienen, en el orden en que protege:

* una orden se arma con proveedor dado de alta y renglones que salen de necesidades
  YA revisadas -nunca de texto que nadie confirmo-, y una necesidad no esta en dos
  ordenes a la vez;
* quien pide el dinero no lo autoriza, y quien autoriza no compra -salvo lo que la
  politica reserva a gerencia-;
* comprar exige el comprobante, y el monto y el folio salen DEL comprobante;
* el mismo papel no justifica dos compras (huella, folio del proveedor, UUID), pero
  una orden SI surte a varios proyectos;
* si lo comprado sale mas caro de lo autorizado mas la tolerancia, la orden vuelve a
  autorizacion con el monto real;
* los montos viven en la politica, que quien compra no puede tocar.
"""
from __future__ import annotations

import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import jwt

from app.models import (
    CustomerSupplier, EntityPermission, Material, Proyect, ProyectMaterialNeed,
    PurchasePolicy,
)
from app.models.session import transaction_context
from app.modules import registry
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.model_factory import build_model

COMPRAS, GERENTE, ALMACEN, NADIE, SUPERVISOR = 301, 302, 303, 401, 201
COMPRAS_1, COMPRAS_2, GERENTE_1, GERENTE_2, ALMACEN_1, NADIE_1 = 21, 22, 31, 32, 41, 51
USUARIO_SUPERVISOR = 11
PROVEEDOR, OTRO_PROVEEDOR, UN_CLIENTE = 1, 3, 2
PROYECTO_A, PROYECTO_B = 10, 20
DISCO = 1
N_SOLDADURA, N_CEMENTO, N_DISCO, N_SIN_REVISAR, N_DEVUELTA = 1, 2, 3, 4, 5


def _con_id(objeto, **ids):
    """`build_model` ignora las llaves autoincrementales: se asignan despues."""
    for campo, valor in ids.items():
        setattr(objeto, campo, valor)
    return objeto


def _hoy() -> date:
    return datetime.now(timezone.utc).date()


def _pdf(semilla="a") -> bytes:
    """Un PDF distinto por semilla: la huella del archivo es lo que se compara."""
    return b"%PDF-1.4\n" + semilla.encode() + b"\n%%EOF"


def _cfdi(uuid="AAAAAAAA-0000-4000-8000-000000000001", total="10000.00", rfc="FNO010101AB1",
          fecha=None, serie="A", folio="1234", moneda="MXN", tipo="I", relleno="") -> bytes:
    fecha = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
        'xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" '
        f'Serie="{serie}" Folio="{folio}" Fecha="{fecha}" SubTotal="{total}" Total="{total}" '
        f'Moneda="{moneda}" TipoDeComprobante="{tipo}">'
        f'<cfdi:Emisor Rfc="{rfc}" Nombre="Ferreteria Norte" RegimenFiscal="601"/>'
        '<cfdi:Receptor Rfc="ADS010101AA1" Nombre="Adser" UsoCFDI="G03"/>'
        '<cfdi:Conceptos><cfdi:Concepto ClaveProdServ="01010101" Cantidad="1" ClaveUnidad="H87" '
        f'Descripcion="Material" ValorUnitario="{total}" Importe="{total}"/></cfdi:Conceptos>'
        f'<cfdi:Complemento><tfd:TimbreFiscalDigital Version="1.1" UUID="{uuid}" '
        f'FechaTimbrado="{fecha}"/></cfdi:Complemento>{relleno}'
        '</cfdi:Comprobante>'
    ).encode()


class BaseOrdenes(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Compras: arma, envia y compra; la politica solo la consulta.
                EntityPermission(id_permission=COMPRAS, entity_name="purchase_order",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=COMPRAS, entity_name="purchase_policy",
                                 scope_read=4, created_by=1),
                # Y ve lo que falta por comprar, de donde salen los renglones.
                EntityPermission(id_permission=COMPRAS, entity_name="purchase_planning",
                                 scope_read=4, scope_update=4, created_by=1),
                # El supervisor captura la lista de SU proyecto.
                EntityPermission(id_permission=SUPERVISOR, entity_name="proyect_material_need",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                # Gerente: lo mismo, fija la politica y ademas autoriza.
                EntityPermission(id_permission=GERENTE, entity_name="purchase_order",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=GERENTE, entity_name="purchase_policy",
                                 scope_create=4, scope_read=4, scope_update=4, created_by=1),
                EntityPermission(id_permission=GERENTE, entity_name="purchase_authorize",
                                 scope_read=4, scope_update=4, created_by=1),
                # Almacen: ve lo que va a llegar, no escribe.
                EntityPermission(id_permission=ALMACEN, entity_name="purchase_order",
                                 scope_read=4, created_by=1),
                _con_id(build_model(CustomerSupplier, name="Ferreteria Norte", type="supplier",
                                    tax_id="FNO010101AB1"), id_customer_supplier=PROVEEDOR),
                _con_id(build_model(CustomerSupplier, name="Constructora Cliente", type="client",
                                    tax_id="CCL010101AA1"), id_customer_supplier=UN_CLIENTE),
                _con_id(build_model(CustomerSupplier, name="Cementos del Sur", type="supplier",
                                    tax_id="CSU010101AA1"), id_customer_supplier=OTRO_PROVEEDOR),
                _con_id(build_model(Proyect, created_by=11, leader=11, proyect_status="authorized",
                                    folio="PRJ-10", title="Obra A"), id_proyect=PROYECTO_A),
                _con_id(build_model(Proyect, created_by=12, leader=12, proyect_status="authorized",
                                    folio="PRJ-20", title="Obra B"), id_proyect=PROYECTO_B),
                _con_id(build_model(Material, material_description="Disco de corte"),
                        id_material=DISCO),
            ])
            db.flush()
            db.add_all([
                self._necesidad(N_SOLDADURA, PROYECTO_A, "Soldadura 6013", 10, "kg", "buy"),
                self._necesidad(N_CEMENTO, PROYECTO_B, "Cemento gris", 40, "saco", "buy"),
                self._necesidad(N_DISCO, PROYECTO_A, None, 5, None, "linked", id_material=DISCO),
                self._necesidad(N_SIN_REVISAR, PROYECTO_A, "Cinta de enmascarar", 3, "rollo", None),
                self._necesidad(N_DEVUELTA, PROYECTO_A, "Varilla corrugada", 8, "pza", "returned"),
            ])
        self._upload_dir = tempfile.mkdtemp()
        self.app.config["UPLOAD_ROOT"] = self._upload_dir

    def tearDown(self):
        shutil.rmtree(self._upload_dir, ignore_errors=True)
        super().tearDown()

    @staticmethod
    def _necesidad(id_need, id_proyecto, descripcion, cantidad, unidad, revision, id_material=None):
        return _con_id(ProyectMaterialNeed(
            id_proyect=id_proyecto, id_material=id_material, description=descripcion,
            unit=unidad, quantity=cantidad, need_status="open", review_result=revision,
            created_by=11), id_proyect_material_need=id_need)

    # --- ayudas --------------------------------------------------------------

    def _h(self, id_user, id_permission):
        token = jwt.encode({"id_user": id_user, "id_permission": id_permission},
                           SECRET_KEY, algorithm="HS256")
        return {"Authorization": "Bearer %s" % token}

    def _compras(self, n=1):
        return self._h(COMPRAS_1 if n == 1 else COMPRAS_2, COMPRAS)

    def _gerente(self, n=1):
        return self._h(GERENTE_1 if n == 1 else GERENTE_2, GERENTE)

    def _almacen(self):
        return self._h(ALMACEN_1, ALMACEN)

    def _nadie(self):
        return self._h(NADIE_1, NADIE)

    def _politica(self, authorize_above=0, manager_buys_above=None, overrun=10):
        with transaction_context() as db:
            fila = db.get(PurchasePolicy, 1)
            if fila is None:
                fila = PurchasePolicy(id_purchase_policy=1)
                db.add(fila)
            fila.authorize_above = authorize_above
            fila.manager_buys_above = manager_buys_above
            fila.overrun_percent = overrun

    def _renglones(self, costo_soldadura=400, costo_cemento=150):
        """10 x 400 + 40 x 150 = 10,000, repartido en DOS proyectos."""
        return [
            {"id_proyect_material_need": N_SOLDADURA, "unit_cost": costo_soldadura},
            {"id_proyect_material_need": N_CEMENTO, "unit_cost": costo_cemento},
        ]

    def _crear(self, headers=None, lineas=None, proveedor=PROVEEDOR, **extra):
        return self.client.post("/purchase-orders", json={
            "id_customer_supplier": proveedor,
            "lines": self._renglones() if lineas is None else lineas, **extra,
        }, headers=headers or self._compras())

    def _id(self, respuesta):
        return self.json(respuesta)["id_purchase_order"]

    def _accion(self, id_orden, accion, headers=None, **cuerpo):
        return self.client.post("/purchase-orders/%s/%s" % (id_orden, accion),
                                json=cuerpo, headers=headers or self._compras())

    def _por_autorizar(self, **kw):
        id_orden = self._id(self._crear(**kw))
        respuesta = self._accion(id_orden, "submit")
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return id_orden

    def _autorizada(self, **kw):
        id_orden = self._por_autorizar(**kw)
        respuesta = self._accion(id_orden, "authorize", self._gerente(2))
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        return id_orden

    def _subir(self, id_orden, tipo="invoice", archivo=None, nombre="factura.pdf", headers=None,
               **campos):
        datos = {"kind": tipo, "file": (BytesIO(archivo if archivo is not None else _pdf()), nombre)}
        datos.update({k: str(v) for k, v in campos.items() if v is not None})
        return self.client.post("/purchase-orders/%s/vouchers" % id_orden, data=datos,
                                content_type="multipart/form-data",
                                headers=headers or self._compras())

    def _factura(self, id_orden, folio="F-100", monto="10000.00", semilla="a", **extra):
        campos = {"folio": folio, "amount": monto, "issue_date": _hoy().isoformat()}
        campos.update(extra)
        respuesta = self._subir(id_orden, "invoice", _pdf(semilla), **campos)
        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        return respuesta

    def _comprar(self, id_orden, headers=None, **extra):
        cuerpo = {"purchase_date": _hoy().isoformat(), "payment_method": "transfer",
                  "payment_reference": "SPEI-12345"}
        cuerpo.update(extra)
        return self._accion(id_orden, "purchase", headers, **cuerpo)

    def _orden_completa(self, **kw):
        """Autorizada, con su factura por 10,000, lista para comprar."""
        id_orden = self._autorizada(**kw)
        self._factura(id_orden)
        return id_orden

    def _leer(self, id_orden, headers=None):
        return self.json(self.client.get("/purchase-orders/%s" % id_orden,
                                         headers=headers or self._compras()))

    def _eventos(self, id_orden):
        return [e["event_type"] for e in self._leer(id_orden)["events"]]

    def _error(self, respuesta):
        return self.json(respuesta).get("error_key")


class TestArmarLaOrden(BaseOrdenes):
    def test_it_creates_a_draft_with_a_folio_and_the_total_of_its_lines(self):
        respuesta = self._crear(description="Material de obra", expected_date="2026-11-01")
        self.assertEqual(201, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual("draft", cuerpo["order_status"])
        self.assertRegex(cuerpo["folio"], r"^OC-\d{4}-\d{5}$")
        self.assertEqual(10000.0, cuerpo["quoted_total"])
        self.assertEqual(2, len(cuerpo["lines"]))
        self.assertEqual("Ferreteria Norte", cuerpo["supplier"]["name"])
        self.assertEqual(["created"], [e["event_type"] for e in cuerpo["events"]])

    def test_it_only_buys_from_a_registered_supplier(self):
        self.assertEqual(409, self._crear(proveedor=UN_CLIENTE).status_code)
        self.assertEqual(404, self._crear(proveedor=999).status_code)
        self.assertEqual(400, self._crear(proveedor="").status_code)

    def test_a_line_from_a_need_carries_its_project_and_what_was_asked(self):
        cuerpo = self.json(self._crear())
        por_necesidad = {r["id_proyect_material_need"]: r for r in cuerpo["lines"]}
        self.assertEqual(PROYECTO_A, por_necesidad[N_SOLDADURA]["id_proyect"])
        self.assertEqual("Soldadura 6013", por_necesidad[N_SOLDADURA]["description"])
        self.assertEqual(10, por_necesidad[N_SOLDADURA]["quantity"])
        self.assertEqual(PROYECTO_B, por_necesidad[N_CEMENTO]["id_proyect"])
        self.assertEqual(4000.0, por_necesidad[N_SOLDADURA]["line_total"])
        self.assertEqual({PROYECTO_A, PROYECTO_B}, {p["id_proyect"] for p in cuerpo["projects"]})

    def test_a_linked_need_takes_its_name_from_the_catalog(self):
        cuerpo = self.json(self._crear(lineas=[
            {"id_proyect_material_need": N_DISCO, "unit_cost": 50}]))
        self.assertEqual("Disco de corte", cuerpo["lines"][0]["description"])
        self.assertEqual(DISCO, cuerpo["lines"][0]["id_material"])

    def test_what_nobody_has_reviewed_is_not_bought(self):
        """Sin revisar o devuelto al supervisor: nadie confirmo que se entienda."""
        for id_need in (N_SIN_REVISAR, N_DEVUELTA):
            with self.subTest(id_need=id_need):
                respuesta = self._crear(lineas=[
                    {"id_proyect_material_need": id_need, "unit_cost": 10}])
                self.assertEqual(409, respuesta.status_code)
                self.assertEqual("errors.need_not_purchasable", self._error(respuesta))

    def test_a_line_cannot_ask_for_more_than_the_project_did(self):
        respuesta = self._crear(lineas=[
            {"id_proyect_material_need": N_SOLDADURA, "quantity": 11, "unit_cost": 400}])
        self.assertEqual(400, respuesta.status_code)

    def test_it_may_buy_less_than_the_project_asked(self):
        cuerpo = self.json(self._crear(lineas=[
            {"id_proyect_material_need": N_SOLDADURA, "quantity": 4, "unit_cost": 400}]))
        self.assertEqual(4, cuerpo["lines"][0]["quantity"])
        self.assertEqual(1600.0, cuerpo["quoted_total"])

    def test_a_need_is_not_on_two_orders_at_once(self):
        self._crear()
        respuesta = self._crear(lineas=[{"id_proyect_material_need": N_SOLDADURA}])
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_already_in_order", self._error(respuesta))
        self.assertIn("order_folio", self.json(respuesta)["meta"])

    def test_the_same_need_twice_in_one_order_is_rejected(self):
        respuesta = self._crear(lineas=[
            {"id_proyect_material_need": N_SOLDADURA}, {"id_proyect_material_need": N_SOLDADURA}])
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_duplicate_line", self._error(respuesta))

    def test_cancelling_the_order_releases_its_needs(self):
        id_orden = self._id(self._crear())
        self.assertEqual(200, self._accion(id_orden, "cancel", note="se cancelo el pedido").status_code)
        self.assertEqual(201, self._crear().status_code)

    def test_a_rejected_order_still_holds_its_needs_until_it_is_cancelled(self):
        id_orden = self._por_autorizar()
        self._accion(id_orden, "reject", self._gerente(2), note="falta cotizar otro proveedor")
        self.assertEqual(409, self._crear().status_code)

    def test_a_line_added_by_compras_needs_a_description_that_looks_like_one(self):
        respuesta = self._crear(lineas=[
            {"description": "12o3pifsfjg", "quantity": 3, "unit_cost": 10}])
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.need_description_invalid", self._error(respuesta))

    def test_a_line_added_by_compras_has_no_need_behind_it(self):
        cuerpo = self.json(self._crear(lineas=[
            {"description": "Guantes de carnaza", "quantity": 12, "unit": "par",
             "unit_cost": 35, "id_proyect": PROYECTO_A}]))
        linea = cuerpo["lines"][0]
        self.assertFalse(linea["from_need"])
        self.assertEqual(PROYECTO_A, linea["id_proyect"])
        self.assertEqual(420.0, cuerpo["quoted_total"])

    def test_a_free_line_uses_the_closed_list_of_units(self):
        respuesta = self._crear(lineas=[
            {"description": "Guantes de carnaza", "quantity": 12, "unit": "furlongs"}])
        self.assertEqual(400, respuesta.status_code)

    def test_absurd_amounts_and_quantities_are_rejected(self):
        for linea in ({"id_proyect_material_need": N_SOLDADURA, "unit_cost": -5},
                      {"id_proyect_material_need": N_SOLDADURA, "unit_cost": "abc"},
                      {"id_proyect_material_need": N_SOLDADURA, "unit_cost": "NaN"},
                      {"id_proyect_material_need": N_SOLDADURA, "unit_cost": 99999999999},
                      {"description": "Guantes de carnaza", "quantity": 0},
                      {"description": "Guantes de carnaza", "quantity": 9999999}):
            with self.subTest(linea=linea):
                self.assertEqual(400, self._crear(lineas=[linea]).status_code)

    def test_editing_a_draft_replaces_its_lines_and_the_total(self):
        id_orden = self._id(self._crear())
        respuesta = self.client.put("/purchase-orders/%s" % id_orden, json={
            "lines": [{"id_proyect_material_need": N_SOLDADURA, "unit_cost": 500}],
            "description": "Solo soldadura"}, headers=self._compras())
        self.assertEqual(200, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual(1, len(cuerpo["lines"]))
        self.assertEqual(5000.0, cuerpo["quoted_total"])
        self.assertIn("updated", [e["event_type"] for e in cuerpo["events"]])
        # Y la necesidad que salio quedo libre para otra orden.
        self.assertEqual(201, self._crear(lineas=[
            {"id_proyect_material_need": N_CEMENTO, "unit_cost": 150}]).status_code)

    def test_an_order_in_review_cannot_be_edited(self):
        id_orden = self._por_autorizar()
        respuesta = self.client.put("/purchase-orders/%s" % id_orden,
                                    json={"description": "otra cosa"}, headers=self._compras())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_not_editable", self._error(respuesta))

    def test_the_orders_can_be_listed_and_filtered(self):
        id_uno = self._id(self._crear())
        id_dos = self._por_autorizar(lineas=[{"description": "Guantes de carnaza",
                                              "quantity": 2, "unit_cost": 40}])
        todas = self.json(self.client.get("/purchase-orders", headers=self._compras()))
        self.assertEqual(2, todas["total"])
        self.assertEqual({id_uno, id_dos}, {o["id_purchase_order"] for o in todas["items"]})
        por_estado = self.json(self.client.get(
            "/purchase-orders?status=pending_authorization", headers=self._compras()))
        self.assertEqual([id_dos], [o["id_purchase_order"] for o in por_estado["items"]])
        buscadas = self.json(self.client.get(
            "/purchase-orders?q=norte", headers=self._compras()))
        self.assertEqual(2, buscadas["total"])
        self.assertEqual(2, todas["items"][1]["projects_count"])
        # El resumen de arriba de la pantalla cuenta por estado, sin los filtros.
        self.assertEqual({"pending_authorization": 1}, {
            k: v for k, v in por_estado["by_status"].items() if k == "pending_authorization"})
        self.assertEqual(2, sum(por_estado["by_status"].values()))

    def test_only_the_registered_suppliers_are_offered(self):
        respuesta = self.client.get("/purchase-orders/suppliers", headers=self._compras())
        self.assertEqual(200, respuesta.status_code)
        nombres = sorted(p["name"] for p in self.json(respuesta))
        self.assertEqual(["Cementos del Sur", "Ferreteria Norte"], nombres)

    def test_the_warehouse_sees_the_orders_but_does_not_write_them(self):
        id_orden = self._id(self._crear())
        self.assertEqual(200, self.client.get("/purchase-orders", headers=self._almacen()).status_code)
        self.assertEqual(200, self.client.get("/purchase-orders/%s" % id_orden,
                                              headers=self._almacen()).status_code)
        self.assertEqual(403, self._crear(headers=self._almacen()).status_code)
        self.assertEqual(403, self._accion(id_orden, "submit", self._almacen()).status_code)

    def test_whoever_has_no_purchasing_access_sees_nothing(self):
        self.assertEqual(403, self.client.get("/purchase-orders", headers=self._nadie()).status_code)
        self.assertEqual(403, self._crear(headers=self._nadie()).status_code)


class TestLaPoliticaDeMontos(BaseOrdenes):
    def test_the_default_policy_is_the_strictest(self):
        cuerpo = self.json(self.client.get("/purchase-policy", headers=self._compras()))
        self.assertEqual(0.0, cuerpo["authorize_above"])
        self.assertIsNone(cuerpo["manager_buys_above"])
        self.assertEqual(10.0, cuerpo["overrun_percent"])

    def test_by_default_every_order_goes_to_authorization(self):
        id_orden = self._id(self._crear(lineas=[
            {"description": "Guantes de carnaza", "quantity": 1, "unit_cost": 1}]))
        cuerpo = self.json(self._accion(id_orden, "submit"))
        self.assertEqual("pending_authorization", cuerpo["order_status"])
        self.assertTrue(cuerpo["requires_authorization"])
        self.assertFalse(cuerpo["requires_manager_purchase"])

    def test_below_the_limit_the_order_is_authorized_on_its_own_and_says_so(self):
        self._politica(authorize_above=20000)
        id_orden = self._id(self._crear())
        cuerpo = self.json(self._accion(id_orden, "submit"))
        self.assertEqual("authorized", cuerpo["order_status"])
        self.assertFalse(cuerpo["requires_authorization"])
        self.assertIsNone(cuerpo["authorized_by"])
        self.assertEqual(10000.0, cuerpo["authorized_total"])
        self.assertEqual(["created", "auto_authorized"],
                         [e["event_type"] for e in cuerpo["events"]])

    def test_above_the_limit_it_waits_for_someone_to_authorize(self):
        self._politica(authorize_above=5000)
        cuerpo = self.json(self._accion(self._id(self._crear()), "submit"))
        self.assertEqual("pending_authorization", cuerpo["order_status"])

    def test_above_the_manager_amount_only_a_manager_buys(self):
        self._politica(authorize_above=0, manager_buys_above=5000)
        cuerpo = self.json(self._accion(self._id(self._crear()), "submit"))
        self.assertTrue(cuerpo["requires_manager_purchase"])

    def test_the_policy_is_edited_by_the_manager_and_not_by_purchasing(self):
        sin_permiso = self.client.put("/purchase-policy", json={"authorize_above": 99999},
                                      headers=self._compras())
        self.assertEqual(403, sin_permiso.status_code)
        self.assertEqual(0.0, self.json(self.client.get(
            "/purchase-policy", headers=self._compras()))["authorize_above"])

        respuesta = self.client.put("/purchase-policy", json={
            "authorize_above": 20000, "manager_buys_above": 50000, "overrun_percent": 5},
            headers=self._gerente())
        self.assertEqual(200, respuesta.status_code)
        cuerpo = self.json(respuesta)
        self.assertEqual(20000.0, cuerpo["authorize_above"])
        self.assertEqual(50000.0, cuerpo["manager_buys_above"])
        self.assertEqual(5.0, cuerpo["overrun_percent"])
        self.assertEqual(GERENTE_1, cuerpo["updated_by"])
        self.assertEqual(0.0, cuerpo["previous"]["authorize_above"])

    def test_the_policy_rejects_numbers_that_make_no_sense(self):
        for cuerpo in ({"authorize_above": -1}, {"authorize_above": "mucho"},
                       {"overrun_percent": 150},
                       {"authorize_above": 20000, "manager_buys_above": 1000}):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.client.put("/purchase-policy", json=cuerpo,
                                            headers=self._gerente())
                self.assertEqual(400, respuesta.status_code)
        # Quitar el monto de gerencia (nadie compra por su cuenta) si se puede.
        self.assertEqual(200, self.client.put(
            "/purchase-policy", json={"manager_buys_above": None},
            headers=self._gerente()).status_code)

    def test_changing_the_policy_does_not_rewrite_an_order_already_sent(self):
        id_orden = self._por_autorizar()
        self._politica(authorize_above=1000000)
        cuerpo = self._leer(id_orden)
        self.assertEqual("pending_authorization", cuerpo["order_status"])
        self.assertTrue(cuerpo["requires_authorization"])

    def test_an_order_cannot_be_sent_without_lines_or_without_costs(self):
        sin_renglones = self._id(self._crear(lineas=[]))
        respuesta = self._accion(sin_renglones, "submit")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_without_lines", self._error(respuesta))

        sin_costo = self._id(self._crear(lineas=[
            {"id_proyect_material_need": N_SOLDADURA}]))
        respuesta = self._accion(sin_costo, "submit")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_without_costs", self._error(respuesta))


class TestAutorizar(BaseOrdenes):
    def test_purchasing_cannot_authorize(self):
        id_orden = self._por_autorizar()
        respuesta = self._accion(id_orden, "authorize", self._compras(2))
        self.assertEqual(403, respuesta.status_code)

    def test_who_asks_for_the_money_does_not_authorize_it(self):
        """Vale tambien para el gerente: no autoriza la orden que el mismo escribio."""
        id_orden = self._por_autorizar(headers=self._gerente(1))
        respuesta = self._accion(id_orden, "authorize", self._gerente(1))
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.purchase_same_person", self._error(respuesta))
        self.assertEqual(200, self._accion(id_orden, "authorize", self._gerente(2)).status_code)

    def test_the_manager_authorizes_and_it_is_recorded(self):
        id_orden = self._por_autorizar()
        respuesta = self._accion(id_orden, "authorize", self._gerente(2), note="va")
        cuerpo = self.json(respuesta)
        self.assertEqual("authorized", cuerpo["order_status"])
        self.assertEqual(GERENTE_2, cuerpo["authorized_by"])
        self.assertEqual(10000.0, cuerpo["authorized_total"])
        self.assertEqual(["created", "submitted", "authorized"],
                         [e["event_type"] for e in cuerpo["events"]])

    def test_only_an_order_in_review_can_be_authorized(self):
        id_orden = self._autorizada()
        respuesta = self._accion(id_orden, "authorize", self._gerente(1))
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.order_not_pending", self._error(respuesta))
        borrador = self._id(self._crear(lineas=[
            {"description": "Guantes de carnaza", "quantity": 1, "unit_cost": 1}]))
        self.assertEqual(409, self._accion(borrador, "authorize", self._gerente(2)).status_code)

    def test_rejecting_asks_for_a_reason_and_the_order_can_be_fixed_and_resent(self):
        id_orden = self._por_autorizar()
        self.assertEqual(400, self._accion(id_orden, "reject", self._gerente(2)).status_code)
        self.assertEqual(400, self._accion(id_orden, "reject", self._gerente(2),
                                           note="no").status_code)
        respuesta = self._accion(id_orden, "reject", self._gerente(2),
                                 note="el cemento esta caro, cotizar otro")
        self.assertEqual("rejected", self.json(respuesta)["order_status"])

        editada = self.client.put("/purchase-orders/%s" % id_orden, json={
            "lines": self._renglones(costo_cemento=120)}, headers=self._compras())
        cuerpo = self.json(editada)
        self.assertEqual("draft", cuerpo["order_status"])
        self.assertEqual(8800.0, cuerpo["quoted_total"])
        reenviada = self.json(self._accion(id_orden, "submit"))
        self.assertEqual("pending_authorization", reenviada["order_status"])
        self.assertIsNone(reenviada["authorized_total"])
        self.assertEqual(
            ["created", "submitted", "rejected", "reopened", "submitted"],
            [e["event_type"] for e in reenviada["events"] if e["event_type"] != "resubmitted"])

    def test_the_screen_is_told_what_each_person_can_do(self):
        id_orden = self._por_autorizar()
        compras = self._leer(id_orden, self._compras())["actions"]
        gerente = self._leer(id_orden, self._gerente(2))["actions"]
        self.assertFalse(compras["authorize"])
        self.assertFalse(compras["edit"])
        self.assertTrue(gerente["authorize"])
        self.assertTrue(gerente["reject"])
        self.assertFalse(gerente["purchase"])


class TestLosComprobantes(BaseOrdenes):
    def test_a_quote_can_be_attached_to_a_draft_but_an_invoice_cannot_yet(self):
        id_orden = self._id(self._crear())
        self.assertEqual(201, self._subir(id_orden, "quote", _pdf("cot")).status_code)
        respuesta = self._subir(id_orden, "invoice", folio="F-1", amount="10000",
                                issue_date=_hoy().isoformat())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_not_allowed_now", self._error(respuesta))

    def test_an_invoice_is_attached_to_an_authorized_order_and_its_path_is_not_shown(self):
        id_orden = self._autorizada()
        cuerpo = self.json(self._factura(id_orden))
        factura = cuerpo["vouchers"][0]
        self.assertEqual("invoice", factura["kind"])
        self.assertEqual("F-100", factura["folio"])
        self.assertEqual(10000.0, factura["amount"])
        self.assertNotIn("file_path", factura)
        self.assertEqual(64, len(factura["sha256"]))

    def test_the_file_can_be_downloaded_as_it_was_uploaded(self):
        id_orden = self._autorizada()
        cuerpo = self.json(self._factura(id_orden))
        descarga = self.client.get(
            "/purchase-vouchers/%s/content" % cuerpo["vouchers"][0]["id_purchase_voucher"],
            headers=self._almacen())
        self.assertEqual(200, descarga.status_code)
        self.assertEqual(_pdf(), descarga.get_data())
        self.assertEqual("application/pdf", descarga.mimetype)

    def test_an_invoice_needs_folio_amount_and_date(self):
        id_orden = self._autorizada()
        respuesta = self._subir(id_orden, "invoice", folio="F-1")
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.voucher_incomplete", self._error(respuesta))
        self.assertEqual({"amount", "issue_date"}, set(self.json(respuesta)["meta"]["missing"]))

    def test_an_invoice_dated_before_the_order_existed_is_a_recycled_one(self):
        id_orden = self._autorizada()
        vieja = (_hoy() - timedelta(days=10)).isoformat()
        respuesta = self._subir(id_orden, "invoice", folio="F-1", amount="10000", issue_date=vieja)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_predates_order", self._error(respuesta))

    def test_an_invoice_dated_in_the_future_is_rejected(self):
        id_orden = self._autorizada()
        futura = (_hoy() + timedelta(days=10)).isoformat()
        respuesta = self._subir(id_orden, "invoice", folio="F-1", amount="10000", issue_date=futura)
        self.assertEqual(400, respuesta.status_code)

    def test_the_same_file_cannot_justify_two_orders(self):
        primera = self._autorizada()
        self._factura(primera, folio="F-1", semilla="mismo")
        segunda = self._autorizada(lineas=[{"description": "Guantes de carnaza",
                                            "quantity": 10, "unit_cost": 1000}])
        respuesta = self._subir(segunda, "invoice", _pdf("mismo"), folio="F-2",
                                amount="10000", issue_date=_hoy().isoformat())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_duplicate", self._error(respuesta))
        meta = self.json(respuesta)["meta"]
        self.assertEqual("file", meta["matched_on"])
        self.assertEqual(primera, meta["id_purchase_order"])

    def test_the_same_folio_from_the_same_supplier_cannot_justify_two_orders(self):
        primera = self._autorizada()
        self._factura(primera, folio="F-100", semilla="uno")
        segunda = self._autorizada(lineas=[{"description": "Guantes de carnaza",
                                            "quantity": 10, "unit_cost": 1000}])
        # Otro archivo, mismo folio -tambien con otra capitalizacion-: el mismo papel.
        respuesta = self._subir(segunda, "invoice", _pdf("dos"), folio="f-100",
                                amount="10000", issue_date=_hoy().isoformat())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("folio", self.json(respuesta)["meta"]["matched_on"])

    def test_the_same_folio_from_another_supplier_is_a_different_invoice(self):
        primera = self._autorizada()
        self._factura(primera, folio="F-100", semilla="uno")
        otra = self._autorizada(proveedor=OTRO_PROVEEDOR, lineas=[
            {"description": "Guantes de carnaza", "quantity": 10, "unit_cost": 1000}])
        self.assertEqual(201, self._subir(
            otra, "invoice", _pdf("dos"), folio="F-100", amount="10000",
            issue_date=_hoy().isoformat()).status_code)

    def test_an_order_has_one_invoice_but_may_serve_several_projects(self):
        """El comprobante es de UNA orden; la orden reparte sus renglones por proyecto."""
        id_orden = self._autorizada()
        self.assertEqual(2, len(self._leer(id_orden)["projects"]))
        self._factura(id_orden)
        segunda = self._subir(id_orden, "invoice", _pdf("otra"), folio="F-101",
                              amount="10000", issue_date=_hoy().isoformat())
        self.assertEqual(409, segunda.status_code)
        self.assertEqual("errors.voucher_one_per_order", self._error(segunda))

    def test_only_pdf_and_images_are_accepted_and_they_must_be_what_they_say(self):
        id_orden = self._autorizada()
        campos = dict(folio="F-1", amount="10000", issue_date=_hoy().isoformat())
        self.assertEqual(400, self._subir(id_orden, "invoice", b"hola", "nota.txt", **campos).status_code)
        # Un PDF disfrazado de imagen.
        self.assertEqual(400, self._subir(id_orden, "invoice", _pdf(), "foto.png", **campos).status_code)
        self.assertEqual(400, self._subir(id_orden, "invoice", b"", "vacio.pdf", **campos).status_code)

    def test_a_voucher_taken_off_by_mistake_leaves_a_trace_and_frees_the_file(self):
        id_orden = self._autorizada()
        cuerpo = self.json(self._factura(id_orden, semilla="x"))
        id_voucher = cuerpo["vouchers"][0]["id_purchase_voucher"]
        sin_motivo = self.client.post("/purchase-vouchers/%s/remove" % id_voucher, json={},
                                      headers=self._compras())
        self.assertEqual(400, sin_motivo.status_code)
        quitada = self.client.post("/purchase-vouchers/%s/remove" % id_voucher,
                                   json={"note": "era de otra orden"}, headers=self._compras())
        self.assertEqual(200, quitada.status_code)
        self.assertEqual([], self.json(quitada)["vouchers"])
        self.assertIn("voucher_removed", self._eventos(id_orden))
        # Una vez quitada, el archivo puede subirse donde si corresponde.
        self.assertEqual(201, self._subir(
            id_orden, "invoice", _pdf("x"), folio="F-100", amount="10000",
            issue_date=_hoy().isoformat()).status_code)

    def test_a_voucher_is_not_removed_once_the_order_was_bought(self):
        id_orden = self._orden_completa()
        self.assertEqual(200, self._comprar(id_orden).status_code)
        id_voucher = self._leer(id_orden)["vouchers"][0]["id_purchase_voucher"]
        respuesta = self.client.post("/purchase-vouchers/%s/remove" % id_voucher,
                                     json={"note": "ya no la quiero"}, headers=self._compras())
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_not_removable", self._error(respuesta))

    def test_the_proof_of_payment_still_arrives_after_buying(self):
        id_orden = self._orden_completa()
        self._comprar(id_orden)
        respuesta = self._subir(id_orden, "payment_proof", _pdf("spei"), "spei.pdf")
        self.assertEqual(201, respuesta.status_code)


class TestElCfdi(BaseOrdenes):
    def _xml(self, id_orden, xml, **campos):
        return self._subir(id_orden, "invoice", xml, "factura.xml", **campos)

    def test_the_xml_is_read_and_what_the_file_says_wins(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, _cfdi(total="10000.00"))
        self.assertEqual(201, respuesta.status_code, respuesta.get_data(as_text=True))
        factura = self.json(respuesta)["vouchers"][0]
        self.assertEqual("AAAAAAAA-0000-4000-8000-000000000001", factura["cfdi_uuid"])
        self.assertEqual("A1234", factura["folio"])
        self.assertEqual(10000.0, factura["amount"])
        self.assertEqual("FNO010101AB1", factura["rfc_emisor"])
        self.assertEqual("application/xml", factura["mime_type"])

    def test_a_typed_amount_that_disagrees_with_the_file_is_rejected(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, _cfdi(total="10000.00"), amount="5000")
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_amount_mismatch", self._error(respuesta))

    def test_an_invoice_from_a_different_company_than_the_supplier_is_rejected(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, _cfdi(rfc="XXX010101AA1"))
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_supplier_mismatch", self._error(respuesta))

    def test_the_same_cfdi_cannot_justify_two_orders_even_with_a_different_file(self):
        primera = self._autorizada()
        self._xml(primera, _cfdi())
        segunda = self._autorizada(lineas=[{"description": "Guantes de carnaza",
                                            "quantity": 10, "unit_cost": 1000}])
        # Mismo UUID, otro serie/folio y otros bytes: la huella del archivo no lo atrapa.
        respuesta = self._xml(segunda, _cfdi(serie="B", folio="999", relleno="<!-- copia -->"))
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("cfdi", self.json(respuesta)["meta"]["matched_on"])

    def test_a_cfdi_in_another_currency_than_the_order_is_rejected(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, _cfdi(moneda="USD"))
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.voucher_currency_mismatch", self._error(respuesta))

    def test_a_cfdi_that_is_not_an_invoice_is_rejected(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, _cfdi(tipo="E"))
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.voucher_not_an_invoice", self._error(respuesta))

    def test_a_broken_xml_is_rejected(self):
        id_orden = self._autorizada()
        respuesta = self._xml(id_orden, b"<esto no es un cfdi")
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("errors.voucher_invalid_cfdi", self._error(respuesta))

    def test_an_xml_is_only_for_the_invoice(self):
        id_orden = self._id(self._crear())
        respuesta = self._subir(id_orden, "quote", _cfdi(), "cotizacion.xml")
        self.assertEqual(400, respuesta.status_code)


class TestComprar(BaseOrdenes):
    def test_it_cannot_be_bought_without_the_invoice(self):
        id_orden = self._autorizada()
        respuesta = self._comprar(id_orden)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.purchase_needs_voucher", self._error(respuesta))

    def test_only_an_authorized_order_is_bought(self):
        for id_orden in (self._id(self._crear()), self._por_autorizar(lineas=[
                {"description": "Guantes de carnaza", "quantity": 1, "unit_cost": 40}])):
            respuesta = self._comprar(id_orden)
            self.assertEqual(409, respuesta.status_code)
            self.assertEqual("errors.order_not_authorized", self._error(respuesta))

    def test_buying_takes_folio_and_amount_from_the_voucher(self):
        id_orden = self._orden_completa()
        respuesta = self._comprar(id_orden, total_amount=1, purchase_folio="inventado")
        cuerpo = self.json(respuesta)
        self.assertEqual(200, respuesta.status_code, respuesta.get_data(as_text=True))
        self.assertEqual("purchased", cuerpo["order_status"])
        self.assertEqual("F-100", cuerpo["purchase_folio"])
        self.assertEqual(10000.0, cuerpo["total_amount"])
        self.assertEqual(COMPRAS_1, cuerpo["purchased_by"])
        self.assertEqual("transfer", cuerpo["payment_method"])
        self.assertEqual("SPEI-12345", cuerpo["payment_reference"])
        self.assertFalse(cuerpo["reauthorization_required"])
        self.assertEqual(
            ["created", "submitted", "authorized", "voucher_added", "purchased"],
            [e["event_type"] for e in cuerpo["events"]])

    def test_a_transfer_or_a_card_needs_its_reference_but_cash_does_not(self):
        id_orden = self._orden_completa()
        for metodo in ("transfer", "check", "card"):
            with self.subTest(metodo=metodo):
                respuesta = self._comprar(id_orden, payment_method=metodo, payment_reference="")
                self.assertEqual(400, respuesta.status_code)
        self.assertEqual(200, self._comprar(id_orden, payment_method="cash",
                                            payment_reference="").status_code)

    def test_the_purchase_data_is_validated(self):
        id_orden = self._orden_completa()
        for cuerpo in ({"payment_method": "bitcoin"},
                       {"purchase_date": ""},
                       {"purchase_date": (_hoy() + timedelta(days=30)).isoformat()},
                       {"purchase_date": (_hoy() - timedelta(days=400)).isoformat()}):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(400, self._comprar(id_orden, **cuerpo).status_code)

    def test_who_authorized_does_not_also_buy(self):
        id_orden = self._autorizada(headers=self._compras(1))
        self._factura(id_orden)
        # El gerente que la autorizo no la compra; otro usuario con acceso si.
        respuesta = self._comprar(id_orden, self._gerente(2))
        self.assertEqual(403, respuesta.status_code)
        self.assertEqual("errors.purchase_same_person", self._error(respuesta))
        self.assertEqual(200, self._comprar(id_orden, self._compras(2)).status_code)

    def test_an_order_authorized_by_the_policy_may_be_bought_by_purchasing(self):
        self._politica(authorize_above=20000)
        id_orden = self._id(self._crear())
        self._accion(id_orden, "submit")
        self._factura(id_orden)
        self.assertEqual(200, self._comprar(id_orden).status_code)

    def test_above_the_manager_amount_purchasing_cannot_buy(self):
        self._politica(authorize_above=0, manager_buys_above=5000)
        id_orden = self._autorizada()
        self._factura(id_orden)
        respuesta = self._comprar(id_orden, self._compras(2))
        self.assertEqual(403, respuesta.status_code)
        # El gerente si: es justo lo que la politica le reserva, y puede ser quien
        # tambien autorizo (aqui el segundo gerente autorizo y el primero compra).
        self.assertEqual(200, self._comprar(id_orden, self._gerente(1)).status_code)
        self.assertTrue(self._leer(id_orden)["requires_manager_purchase"])

    def test_the_manager_may_buy_what_he_himself_authorized_when_the_policy_reserves_it(self):
        self._politica(authorize_above=0, manager_buys_above=5000)
        id_orden = self._autorizada()
        self._factura(id_orden)
        self.assertEqual(200, self._comprar(id_orden, self._gerente(2)).status_code)

    def test_a_voucher_above_the_manager_amount_forces_a_manager_even_if_the_quote_was_below(self):
        self._politica(authorize_above=0, manager_buys_above=12000, overrun=50)
        id_orden = self._autorizada()
        self._factura(id_orden, monto="13000.00")
        # Dentro de la tolerancia del 50%, pero ya sobre el monto de gerencia.
        self.assertEqual(403, self._comprar(id_orden, self._compras(2)).status_code)
        self.assertEqual(200, self._comprar(id_orden, self._gerente(1)).status_code)

    def test_cheaper_than_authorized_is_bought_at_the_real_price(self):
        id_orden = self._autorizada()
        self._factura(id_orden, monto="8000.00")
        cuerpo = self.json(self._comprar(id_orden))
        self.assertEqual("purchased", cuerpo["order_status"])
        self.assertEqual(8000.0, cuerpo["total_amount"])
        self.assertEqual(10000.0, cuerpo["authorized_total"])

    def test_within_the_tolerance_it_is_bought(self):
        id_orden = self._autorizada()
        self._factura(id_orden, monto="10900.00")
        self.assertEqual("purchased", self.json(self._comprar(id_orden))["order_status"])

    def test_more_expensive_than_authorized_goes_back_to_authorization_with_the_real_amount(self):
        id_orden = self._autorizada()
        self._factura(id_orden, monto="12000.00")
        respuesta = self._comprar(id_orden)
        cuerpo = self.json(respuesta)
        self.assertEqual(200, respuesta.status_code)
        self.assertTrue(cuerpo["reauthorization_required"])
        self.assertEqual("pending_authorization", cuerpo["order_status"])
        self.assertEqual(12000.0, cuerpo["quoted_total"])
        self.assertIsNone(cuerpo["authorized_total"])
        self.assertIsNone(cuerpo["authorized_by"])
        self.assertIsNone(cuerpo["purchased_by"])
        self.assertIn("reauthorization_required", self._eventos(id_orden))

        # La factura cara no se quita para subir otra mas barata.
        id_voucher = cuerpo["vouchers"][0]["id_purchase_voucher"]
        quitar = self.client.post("/purchase-vouchers/%s/remove" % id_voucher,
                                  json={"note": "mejor otra factura"}, headers=self._compras())
        self.assertEqual(409, quitar.status_code)

        # Autoriza el monto real y ahora si se compra.
        self.assertEqual(200, self._accion(id_orden, "authorize", self._gerente(2)).status_code)
        final = self.json(self._comprar(id_orden, self._compras(2)))
        self.assertEqual("purchased", final["order_status"])
        self.assertEqual(12000.0, final["total_amount"])

    def test_below_the_authorization_limit_the_overrun_does_not_matter(self):
        self._politica(authorize_above=20000)
        id_orden = self._id(self._crear())
        self._accion(id_orden, "submit")
        self._factura(id_orden, monto="15000.00")
        self.assertEqual("purchased", self.json(self._comprar(id_orden))["order_status"])

    def test_the_overrun_follows_the_tolerance_of_the_policy(self):
        self._politica(authorize_above=0, overrun=0)
        id_orden = self._autorizada()
        self._factura(id_orden, monto="10000.01")
        self.assertTrue(self.json(self._comprar(id_orden))["reauthorization_required"])

    def test_a_bought_order_cannot_be_cancelled_or_edited(self):
        id_orden = self._orden_completa()
        self._comprar(id_orden)
        cancelar = self._accion(id_orden, "cancel", note="me arrepenti")
        self.assertEqual(409, cancelar.status_code)
        self.assertEqual("errors.order_not_cancellable", self._error(cancelar))
        editar = self.client.put("/purchase-orders/%s" % id_orden, json={"description": "x"},
                                 headers=self._compras())
        self.assertEqual(409, editar.status_code)

    def test_cancelling_asks_for_a_reason(self):
        id_orden = self._autorizada()
        self.assertEqual(400, self._accion(id_orden, "cancel").status_code)
        cuerpo = self.json(self._accion(id_orden, "cancel", note="el proveedor ya no surte"))
        self.assertEqual("cancelled", cuerpo["order_status"])
        self.assertEqual("cancelled", cuerpo["events"][-1]["event_type"])

    def test_the_purchase_button_shows_up_only_when_there_is_evidence_and_it_is_allowed(self):
        id_orden = self._autorizada(headers=self._compras(1))
        sin_factura = self._leer(id_orden, self._compras(2))["actions"]
        self.assertFalse(sin_factura["purchase"])
        self._factura(id_orden)
        self.assertTrue(self._leer(id_orden, self._compras(2))["actions"]["purchase"])
        # Quien autorizo no ve el boton.
        self.assertFalse(self._leer(id_orden, self._gerente(2))["actions"]["purchase"])


class TestLoQueVeCadaQuien(BaseOrdenes):
    """Lo que Compras ya esta comprando se ve desde donde se pidio y desde donde se compra."""

    def _por_comprar(self, headers=None):
        respuesta = self.client.get("/material-needs/to-buy?only_missing=0",
                                    headers=headers or self._compras())
        self.assertEqual(200, respuesta.status_code)
        entradas = {}
        for grupo in self.json(respuesta)["items"]:
            for p in grupo["projects"]:
                entradas[p["id_proyect_material_need"]] = p
        return entradas

    def test_to_buy_says_what_can_go_on_an_order_and_what_already_is(self):
        antes = self._por_comprar()
        self.assertTrue(antes[N_SOLDADURA]["purchasable"])
        self.assertIsNone(antes[N_SOLDADURA]["order"])
        # Sin revisar o devuelto: no se puede comprar todavia.
        self.assertFalse(antes[N_SIN_REVISAR]["purchasable"])

        self._crear()
        despues = self._por_comprar()
        self.assertEqual("draft", despues[N_SOLDADURA]["order"]["order_status"])
        self.assertRegex(despues[N_SOLDADURA]["order"]["folio"], r"^OC-")
        self.assertIsNone(despues[N_DISCO]["order"])

    def test_a_cancelled_order_gives_its_needs_back_to_the_list(self):
        id_orden = self._id(self._crear())
        self._accion(id_orden, "cancel", note="se cancelo el pedido")
        self.assertIsNone(self._por_comprar()[N_SOLDADURA]["order"])

    def test_the_supervisor_sees_which_order_holds_his_need(self):
        id_orden = self._por_autorizar()
        self._accion(id_orden, "authorize", self._gerente(2))
        respuesta = self.client.get("/proyect/%s/material-needs" % PROYECTO_A,
                                    headers=self._h(USUARIO_SUPERVISOR, SUPERVISOR))
        self.assertEqual(200, respuesta.status_code)
        por_id = {n["id_proyect_material_need"]: n for n in self.json(respuesta)["items"]}
        self.assertEqual("authorized", por_id[N_SOLDADURA]["order"]["order_status"])
        self.assertIsNone(por_id[N_DISCO]["order"])

    def test_a_need_that_is_being_bought_cannot_be_cancelled_from_the_project(self):
        id_orden = self._id(self._crear())
        headers = self._h(USUARIO_SUPERVISOR, SUPERVISOR)
        respuesta = self.client.delete("/material-needs/%s" % N_SOLDADURA, headers=headers)
        self.assertEqual(409, respuesta.status_code)
        self.assertEqual("errors.need_in_purchase_order", self._error(respuesta))
        # Cancelada la orden, la necesidad queda libre y ahi si se cancela.
        self._accion(id_orden, "cancel", note="se cancelo el pedido")
        self.assertEqual(200, self.client.delete(
            "/material-needs/%s" % N_SOLDADURA, headers=headers).status_code)

    def test_the_warehouse_gets_no_buttons_on_an_order(self):
        id_orden = self._autorizada()
        self._factura(id_orden)
        acciones = self._leer(id_orden, self._almacen())["actions"]
        for boton in ("edit", "submit", "authorize", "reject", "attach_voucher", "purchase", "cancel"):
            with self.subTest(boton=boton):
                self.assertFalse(acciones[boton])
        self.assertEqual([], acciones["removable_vouchers"])

    def test_purchasing_is_told_which_vouchers_it_can_still_remove(self):
        id_orden = self._autorizada()
        self._factura(id_orden)
        cuerpo = self._leer(id_orden)
        self.assertEqual([cuerpo["vouchers"][0]["id_purchase_voucher"]],
                         cuerpo["actions"]["removable_vouchers"])
        self._comprar(id_orden)
        self.assertEqual([], self._leer(id_orden)["actions"]["removable_vouchers"])


class TestElRegistroDeRoles(BaseOrdenes):
    """Lo que el registro concede, para que cambiarlo sea una decision y no un descuido."""

    def _rol(self, nombre):
        return next(r for r in registry.ROLES if r.nombre == nombre)

    def test_purchasing_authorizes_nothing_and_does_not_set_the_policy(self):
        compras = self._rol("Compras")
        self.assertNotIn("purchase_authorize", compras.capacidades)
        self.assertEqual(registry.CONSULTA, compras.excepciones["purchase_policy"])
        self.assertTrue(compras.modulos["compras"] & registry.CREAR)

    def test_the_manager_authorizes(self):
        # Gerencia son dos roles: autoriza las compras el general (revision).
        self.assertIn("purchase_authorize", self._rol("Gerente Comercial").capacidades)
        self.assertTrue(self._rol("Gerente Comercial").modulos["compras"] & registry.CREAR)
        # El tecnico es de campo: ve compras pero no las autoriza.
        self.assertNotIn("purchase_authorize", self._rol("Gerente Tecnico").capacidades)

    def test_the_warehouse_only_looks(self):
        self.assertEqual(registry.CONSULTA, self._rol("Almacenista").modulos["compras"])

    def test_nobody_but_administration_deletes_orders(self):
        for rol in registry.ROLES:
            if rol.nombre == "Administrator":
                continue
            with self.subTest(rol=rol.nombre):
                self.assertFalse(rol.modulos.get("compras", 0) & registry.BORRAR)
