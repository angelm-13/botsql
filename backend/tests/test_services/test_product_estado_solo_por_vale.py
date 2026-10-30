"""El estado del producto a mano solo pasa a "En almacen", y no con un vale abierto.

Danado, extraviado, retirado y en reparacion los pone unicamente el vale correspondiente.
A mano se corrige lo contrario: lo que la migracion dejo como extraviado o danado y esta
fisicamente en el almacen, o la pieza que regresa o se encuentra.
"""

from __future__ import annotations

from app.models import InventoryStatus, Product
from app.models.incident import Incident
from app.models.nm_incident_product import NmIncidentProduct
from app.models.session import transaction_context
from app.services.product_service import ProductService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase
from tests.model_factory import build_model, build_payload


class TestEstadoSoloPorVale(BackendTestCase):

    def _crear(self, codigo, estado="ENTRADA", cantidad=3, id_estado=None):
        id_producto = ProductService.create(build_payload(
            ProductService, {"created_by": 1, "descripcion": "broca", "cantidad": cantidad,
                             "product_code": codigo}))["id_product"]
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            producto.product_status = estado
            producto.id_inventory_status = id_estado
        return id_producto

    def _estado(self, id_producto):
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            return producto.product_status, producto.id_inventory_status

    def _estado_de_catalogo(self, codigo):
        with transaction_context() as db:
            existente = db.query(InventoryStatus).filter_by(
                inventory_status_code=codigo, entity_scope="product").first()
            if existente is not None:
                return existente.id_inventory_status
            fila = build_model(InventoryStatus, inventory_status_code=codigo,
                               inventory_status_description=codigo, entity_scope="product",
                               flow_scope="inventory", is_active=True)
            db.add(fila)
            db.flush()
            return fila.id_inventory_status

    def _vale_abierto(self, id_producto, estado_del_vale="abierta"):
        with transaction_context() as db:
            vale = build_model(Incident)
            vale.incident_status = estado_del_vale
            vale.deletion_date = None
            db.add(vale)
            db.flush()
            renglon = build_model(NmIncidentProduct, id_incident=vale.id_incident,
                                  id_product=id_producto)
            renglon.direction = "salida"
            renglon.close_date = None
            renglon.deletion_date = None
            db.add(renglon)
            return vale.id_incident

    def test_a_mano_no_se_pone_danado_extraviado_retirado_ni_en_reparacion(self):
        id_producto = self._crear("EV-1")
        for texto in ("DAÑADO", "EXTRAVIADO", "danado", "retirado", "en reparacion", "SALIDA"):
            with self.subTest(estado=texto), self.assertRaises(AppError) as raised:
                ProductService.update(id_producto, {"product_status": texto}, user_id=1)
            self.assertEqual("errors.product_status_via_voucher", raised.exception.message_key)
            self.assertEqual(409, raised.exception.status_code)
        self.assertEqual(("ENTRADA", None), self._estado(id_producto))

    def test_tampoco_por_el_estado_de_catalogo(self):
        id_producto = self._crear("EV-2")
        with self.assertRaises(AppError) as raised:
            ProductService.update(
                id_producto, {"id_inventory_status": self._estado_de_catalogo("danado")}, user_id=1)
        self.assertEqual("errors.product_status_via_voucher", raised.exception.message_key)

    def test_una_pieza_extraviada_que_esta_en_el_almacen_se_regresa_a_en_almacen(self):
        extraviado = self._estado_de_catalogo("extraviado")
        id_producto = self._crear("EV-3", estado="EXTRAVIADO", id_estado=extraviado)

        ProductService.update(
            id_producto, {"product_status": "ENTRADA", "id_inventory_status": None}, user_id=1)

        self.assertEqual(("ENTRADA", None), self._estado(id_producto))

    def test_con_un_vale_abierto_no_se_cambia_a_mano(self):
        id_producto = self._crear("EV-4", estado="EXTRAVIADO")
        id_vale = self._vale_abierto(id_producto)

        with self.assertRaises(AppError) as raised:
            ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)

        self.assertEqual("errors.product_status_in_open_voucher", raised.exception.message_key)
        self.assertEqual(id_vale, raised.exception.meta["id_incident"])
        self.assertEqual("EXTRAVIADO", self._estado(id_producto)[0])

    def test_un_vale_cancelado_o_cerrado_no_estorba(self):
        for n, estado_del_vale in enumerate(("cancelado", "cerrada")):
            id_producto = self._crear(f"EV-5{n}", estado="EXTRAVIADO")
            self._vale_abierto(id_producto, estado_del_vale)

            ProductService.update(id_producto, {"product_status": "ENTRADA"}, user_id=1)

            self.assertEqual("ENTRADA", self._estado(id_producto)[0])

    def test_editar_otro_campo_de_un_producto_con_estado_heredado_sigue_funcionando(self):
        id_producto = self._crear("EV-6", estado="EXTRAVIADO")
        self._vale_abierto(id_producto)

        ProductService.update(
            id_producto, {"product_status": "EXTRAVIADO", "color": "rojo"}, user_id=1)

        self.assertEqual("EXTRAVIADO", self._estado(id_producto)[0])

    def test_el_alta_no_acepta_un_estado_de_catalogo(self):
        with self.assertRaises(AppError) as raised:
            ProductService.create(build_payload(
                ProductService, {"created_by": 1, "descripcion": "broca", "cantidad": 1,
                                 "product_code": "EV-7", "product_status": "DAÑADO"}))
        self.assertEqual("errors.product_status_via_voucher", raised.exception.message_key)
