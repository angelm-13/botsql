"""El tipo del vale le pone estado al producto: reparacion, destruccion, dañado, extraviado.

El sistema anterior fijaba `producto.estado` segun el tipo de la incidencia -en adser,
el ultimo vale de 80 de 83 productos de "Destruccion" los dejo en DESTRUCCION-; el
sistema nuevo perdio ese efecto y el tipo solo etiquetaba reportes. Estas pruebas
fijan lo que vuelve:

* un vale de esos tipos deja el producto con su estado de catalogo (y el texto
  historico), al abrirse -no al pedirse: un borrador no mueve nada-;
* reparacion y extraviado se limpian cuando la cosa regresa; dañado y destruido no;
* un estado puesto a mano entre tanto no se pisa;
* un producto serializado no se toca: su estado es de cada pieza;
* un catalogo sin sembrar no tumba el vale.
"""

from __future__ import annotations

from app.models import IncidentType, Product
from app.models.inventory_status import InventoryStatus
from app.models.session import transaction_context
from app.services.warehouse_voucher_service import (
    autorizar_vale,
    crear_vale,
    devolver_renglon,
)
from tests.test_services.test_vale_de_almacen import (
    ACTOR,
    CEMENTO,
    DESARMADOR,
    NAVE,
    OTRO_ACTOR,
    BaseVale,
)

TIPO_REPARACION, TIPO_DESTRUCCION, TIPO_DANADO, TIPO_EXTRAVIADO = 71, 72, 73, 74

CATALOGO = (
    ("nuevo", "Nuevo"), ("en_reparacion", "En reparacion"), ("danado", "Danado"),
    ("retirado", "Retirado"), ("extraviado", "Extraviado"),
)


class BaseEstado(BaseVale):

    sembrar_catalogo = True

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                IncidentType(id_incident_type=TIPO_REPARACION,
                             incident_type_description="Reparacion", created_by=1),
                IncidentType(id_incident_type=TIPO_DESTRUCCION,
                             incident_type_description="Destruccion", created_by=1),
                # Con la ñ, como esta en el catalogo real de adser.
                IncidentType(id_incident_type=TIPO_DANADO,
                             incident_type_description="Dañado", created_by=1),
                IncidentType(id_incident_type=TIPO_EXTRAVIADO,
                             incident_type_description="Extraviado", created_by=1),
            ])
            if self.sembrar_catalogo:
                db.add_all([
                    InventoryStatus(
                        inventory_status_code=codigo, inventory_status_description=nombre,
                        color="#000000", entity_scope="product", flow_scope="inventory",
                        id_department=1, id_minimum_level=1, is_active=True,
                        is_terminal=codigo == "retirado",
                        visible_to_other_departments=False, sort_order=10, created_by=1)
                    for codigo, nombre in CATALOGO
                ])
        self.surtir()

    def codigo_del_producto(self, id_producto=CEMENTO):
        with transaction_context() as db:
            producto = db.get(Product, id_producto)
            if producto.id_inventory_status is None:
                return None, producto.product_status
            estado = db.get(InventoryStatus, producto.id_inventory_status)
            return estado.inventory_status_code, producto.product_status

    def poner_estado_a_mano(self, codigo, id_producto=CEMENTO):
        with transaction_context() as db:
            estado = db.query(InventoryStatus).filter_by(inventory_status_code=codigo).one()
            db.get(Product, id_producto).id_inventory_status = estado.id_inventory_status


class TestElTipoFijaElEstadoDelProducto(BaseEstado):

    def test_cada_tipo_deja_su_estado_de_catalogo_y_su_texto(self):
        casos = (
            (TIPO_REPARACION, "en_reparacion", "EN REPARACION"),
            (TIPO_DESTRUCCION, "retirado", "DESTRUCCION"),
            (TIPO_DANADO, "danado", "DAÑADO"),
            (TIPO_EXTRAVIADO, "extraviado", "EXTRAVIADO"),
        )
        for id_tipo, codigo, texto in casos:
            with self.subTest(tipo=id_tipo):
                with transaction_context() as db:
                    producto = db.get(Product, CEMENTO)
                    producto.id_inventory_status = None
                    producto.product_status = "ENTRADA"
                self._vale([self._linea_cantidad(1)], id_incident_type=id_tipo)
                self.assertEqual(self.codigo_del_producto(), (codigo, texto))

    def test_un_prestamo_normal_no_cambia_el_estado(self):
        self._vale([self._linea_cantidad(1)])
        self.assertEqual(self.codigo_del_producto(), (None, None))

    def test_un_borrador_no_mueve_nada_y_al_autorizarlo_si(self):
        borrador = crear_vale({
            "id_incident_type": TIPO_EXTRAVIADO, "id_user": 1, "note": "Se perdio",
            "lines": [self._linea_cantidad(1)],
            "due_date": "2099-01-01 00:00:00",
        }, ACTOR, como_borrador=True)
        self.assertEqual(self.codigo_del_producto(), (None, None))
        autorizar_vale(borrador["voucher"]["id_incident"], {}, OTRO_ACTOR)
        self.assertEqual(self.codigo_del_producto()[0], "extraviado")


class TestAlRegresar(BaseEstado):

    def _devolver(self, vale):
        linea = vale["lines"][0]["id_nm_incident_product"]
        return devolver_renglon(linea, {"id_location": NAVE}, ACTOR)

    def test_lo_reparado_y_lo_extraviado_que_regresan_se_limpian(self):
        for id_tipo, codigo, texto in (
            (TIPO_REPARACION, "en_reparacion", "EN REPARACION"),
            (TIPO_EXTRAVIADO, "extraviado", "EXTRAVIADO"),
        ):
            with self.subTest(tipo=id_tipo):
                vale = self._vale([self._linea_cantidad(1)], id_incident_type=id_tipo)
                self.assertEqual(self.codigo_del_producto(), (codigo, texto))
                self._devolver(vale)
                self.assertEqual(self.codigo_del_producto(), (None, "ENTRADA"))

    def test_lo_dañado_y_lo_destruido_siguen_asi_al_volver(self):
        for id_tipo, codigo in ((TIPO_DANADO, "danado"), (TIPO_DESTRUCCION, "retirado")):
            with self.subTest(tipo=id_tipo):
                vale = self._vale([self._linea_cantidad(1)], id_incident_type=id_tipo)
                self._devolver(vale)
                self.assertEqual(self.codigo_del_producto()[0], codigo)

    def test_un_estado_puesto_a_mano_no_se_pisa(self):
        vale = self._vale([self._linea_cantidad(1)], id_incident_type=TIPO_REPARACION)
        self.poner_estado_a_mano("danado")
        self._devolver(vale)
        self.assertEqual(self.codigo_del_producto()[0], "danado")


class TestLoQueNoSeToca(BaseEstado):

    def test_un_producto_serializado_no_se_marca(self):
        """El estado es de la pieza, no del producto: se perdio UN desarmador."""
        pieza = self._pieza("DES-001")
        self._vale([self._linea_pieza(pieza)], id_incident_type=TIPO_EXTRAVIADO)
        self.assertEqual(self.codigo_del_producto(DESARMADOR), (None, None))

    def test_un_catalogo_sin_sembrar_no_tumba_el_vale(self):
        with transaction_context() as db:
            db.query(InventoryStatus).delete()
        vale = self._vale([self._linea_cantidad(1)], id_incident_type=TIPO_DESTRUCCION)
        self.assertEqual(vale["voucher"]["incident_status"], "abierto")
        self.assertEqual(self.codigo_del_producto(), (None, None))
