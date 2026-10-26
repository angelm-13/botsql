"""La pantalla de Productos pinta el mismo estado que Localizar.

El caso real es MARR01 en adser-prod: `product_status` decia ENTRADA (los vales de
prestamo no lo escriben), el vale 182 estaba abierto y no quedaba nada en el
almacen. Localizar decia "Salio del almacen" y Productos "En almacen". La regla es
una sola, `estatus_efectivo`; Productos la consume por `agregar_estado_efectivo`.
"""

from __future__ import annotations

from datetime import datetime

from app.models import Incident, IncidentType, Invoice, NmIncidentProduct, Product
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement
from app.services.inventory_trace_service import estatus_efectivo_en_lote, localizar
from app.services.product_service import ProductService
from tests.conftest import BackendTestCase
from tests.model_factory import dar_capacidad
from tests.test_services.test_inventory_trace import _sembrar_lo_minimo

ACTOR = {"id_user": 1, "id_proyect": 70, "id_permission": 910}
ALMACEN = 1
COMPRA = 55
TIPO_PRESTAMO = 60
DENTRO, PRESTADO, DAÑADO = 81, 82, 83


class TestProductosPintanElEstadoDeLocalizar(BackendTestCase):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            dar_capacidad(db, 910)
            _sembrar_lo_minimo(db, id_invoice=COMPRA, ubicaciones={ALMACEN: "Almacen Central"})
            db.add(IncidentType(id_incident_type=TIPO_PRESTAMO,
                                incident_type_description="Prestamo Material", created_by=1))
            db.flush()
            for id_producto, codigo, estado in (
                (DENTRO, "DEN-1", "ENTRADA"),
                (PRESTADO, "PRE-1", "ENTRADA"),
                (DAÑADO, "DAN-1", "DANADO"),
            ):
                db.add(Product(id_product=id_producto, id_invoice=COMPRA, id_location=ALMACEN,
                               id_material=1, is_directly_related_to_product_service=True,
                               product_code=codigo, descripcion="Marro", stock_purpose="uso_interno",
                               product_status=estado, created_by=1))
        # Uno en el almacen, uno que salio y se quedo sin nada, y uno danado.
        for id_producto in (DENTRO, PRESTADO, DAÑADO):
            apply_inventory_movement(id_producto, {
                "movement_type": "receive", "quantity": 1, "id_location": ALMACEN,
                "reference_type": "purchase", "reference_id": str(COMPRA),
                "reason": "Compra", "idempotency_key": f"entrada-{id_producto}",
            }, ACTOR)
        apply_inventory_movement(PRESTADO, {
            "movement_type": "loan", "quantity": 1, "id_location": ALMACEN,
            "reference_type": "incident", "reference_id": "182",
            "reason": "Prestamo", "idempotency_key": "salida-prestado",
        }, ACTOR)
        self._abrir_salida(PRESTADO, id_vale=182, id_renglon=3322)

    def _abrir_salida(self, id_producto, *, id_vale, id_renglon):
        with transaction_context() as db:
            db.add(Incident(id_incident=id_vale, id_incident_type=TIPO_PRESTAMO, id_user=1,
                            incident_status="abierta", incident_date=datetime.utcnow(),
                            created_by=1))
            db.flush()
            db.add(NmIncidentProduct(id_nm_incident_product=id_renglon, id_incident=id_vale,
                                     id_product=id_producto, quantity=1, direction="salida",
                                     created_by=1))

    def _lista(self):
        items = [{"id_product": i, "product_status": e}
                 for i, e in ((DENTRO, "ENTRADA"), (PRESTADO, "ENTRADA"), (DAÑADO, "DANADO"))]
        return {i["id_product"]: i for i in ProductService.agregar_estado_efectivo(items)}

    def test_un_producto_prestado_sin_nada_en_el_almacen_sale_como_salida(self):
        lista = self._lista()
        self.assertEqual("SALIDA", lista[PRESTADO]["effective_status"])
        # El texto guardado no se toca: se manda tal cual.
        self.assertEqual("ENTRADA", lista[PRESTADO]["product_status"])

    def test_uno_en_el_almacen_sigue_como_entrada(self):
        self.assertEqual("ENTRADA", self._lista()[DENTRO]["effective_status"])

    def test_un_estado_decidido_no_se_pisa(self):
        self.assertEqual("DANADO", self._lista()[DAÑADO]["effective_status"])

    def test_coincide_con_lo_que_dice_localizar(self):
        """Una sola regla: lo que pinta Productos es lo que pinta Localizar."""
        lista = self._lista()
        for id_producto in (DENTRO, PRESTADO, DAÑADO):
            codigo = {DENTRO: "DEN-1", PRESTADO: "PRE-1", DAÑADO: "DAN-1"}[id_producto]
            with self.subTest(producto=codigo):
                en_localizar = localizar(codigo, ACTOR)["items"][0]["effective_status"]
                self.assertEqual(en_localizar, lista[id_producto]["effective_status"])

    def test_una_devolucion_lo_vuelve_a_poner_en_el_almacen(self):
        with transaction_context() as db:
            db.get(NmIncidentProduct, 3322).close_date = datetime.utcnow()
        apply_inventory_movement(PRESTADO, {
            "movement_type": "return", "quantity": 1, "id_location": ALMACEN,
            "reference_type": "incident", "reference_id": "182",
            "reason": "Devolucion", "idempotency_key": "regreso-prestado",
        }, ACTOR)
        self.assertEqual("ENTRADA", self._lista()[PRESTADO]["effective_status"])

    def test_sin_productos_no_consulta_ni_falla(self):
        self.assertEqual([], ProductService.agregar_estado_efectivo([]))
        with transaction_context() as db:
            self.assertEqual({}, estatus_efectivo_en_lote(db, {}))
