"""Un vale de destruccion o extravio registra lo que paso, no un prestamo.

Antes un vale de baja hacia lo mismo que uno de prestamo: sacar una unidad del almacen.
Eso fallaba con la herramienta que mas se pierde -la que YA esta en manos de alguien,
con existencia 0-, que se rechazaba con "existencia insuficiente"; y para la que si
estaba en el almacen dejaba el libro diciendo "prestamo" de algo que no iba a volver.

Lo que estas pruebas fijan:

* si el producto esta PRESTADO, el prestamo se cierra y la existencia no se mueve;
* si estaba en el ALMACEN, sale con el movimiento de baja del libro (`destroy`/`loss`);
* lo destruido nace con su renglon cerrado; lo extraviado queda abierto hasta que aparezca;
* sin existencia y sin prestamo, se rechaza: no hay nada que dar de baja.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import IncidentType, Incident, NmIncidentProduct
from app.models.inventory_ledger import InventoryLedger
from app.models.session import transaction_context
from app.services.warehouse_voucher_service import devolver_renglon
from app.utils.errors import AppError
from tests.test_services.test_vale_de_almacen import ACTOR, CEMENTO, NAVE, BaseVale

TIPO_DESTRUCCION, TIPO_EXTRAVIADO = 91, 92


class BaseBaja(BaseVale):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                IncidentType(id_incident_type=TIPO_DESTRUCCION,
                             incident_type_description="Destruccion", created_by=1),
                IncidentType(id_incident_type=TIPO_EXTRAVIADO,
                             incident_type_description="Extraviado", created_by=1),
            ])

    def prestar(self, cantidad=1):
        return self._vale([self._linea_cantidad(cantidad)])

    def baja(self, tipo, cantidad=1, nota="Se perdio en obra"):
        return self._vale([self._linea_cantidad(cantidad)], id_incident_type=tipo, note=nota)

    def linea(self, resultado, n=0):
        return resultado["lines"][n]["id_nm_incident_product"]

    def cierre_de(self, id_linea):
        with transaction_context() as db:
            return db.get(NmIncidentProduct, id_linea).close_date

    def estado_del_vale(self, resultado):
        with transaction_context() as db:
            return db.get(Incident, resultado["voucher"]["id_incident"]).incident_status

    def movimientos(self):
        with transaction_context() as db:
            return [(m.movement_type, m.quantity_delta, m.reason) for m in db.scalars(
                select(InventoryLedger).where(InventoryLedger.id_product == CEMENTO)
                .order_by(InventoryLedger.id_inventory_ledger)).all()]


class TestLaHerramientaYaEstabaPrestada(BaseBaja):

    def test_la_baja_de_algo_prestado_ya_no_se_rechaza_y_cierra_el_prestamo(self):
        self.surtir(1)
        prestamo = self.prestar()
        self.assertEqual(0, self._saldo())            # la unica pieza salio

        baja = self.baja(TIPO_DESTRUCCION)            # antes: 409 existencia insuficiente

        self.assertIsNotNone(self.cierre_de(self.linea(prestamo)),
                             "el prestamo se cierra: la herramienta ya no esta con esa persona")
        self.assertEqual(0, self._saldo(), "una pieza prestada ya no contaba en el almacen")
        self.assertEqual("cerrado", self.estado_del_vale(prestamo),
                         "el vale del prestamo se cierra solo al quedarse sin renglones abiertos")
        self.assertEqual("cerrado", self.estado_del_vale(baja))
        tipos = [m[0] for m in self.movimientos()]
        self.assertNotIn("destroy", tipos)

    def test_lo_extraviado_que_aparece_regresa_por_el_camino_de_siempre(self):
        self.surtir(1)
        self.prestar()
        baja = self.baja(TIPO_EXTRAVIADO)
        linea_baja = self.linea(baja)
        self.assertIsNone(self.cierre_de(linea_baja), "lo extraviado queda abierto: puede aparecer")
        self.assertEqual("abierto", self.estado_del_vale(baja))

        devolver_renglon(linea_baja, {"id_location": NAVE}, ACTOR)   # aparecio

        self.assertEqual(1, self._saldo())
        self.assertEqual("cerrado", self.estado_del_vale(baja))


class TestLaHerramientaEstabaEnElAlmacen(BaseBaja):

    def test_una_destruccion_sale_con_su_movimiento_y_nace_cerrada(self):
        self.surtir(10)
        baja = self.baja(TIPO_DESTRUCCION, cantidad=3, nota="Se rompio en el taller")

        self.assertEqual(7, self._saldo())
        self.assertIn(("destroy", -3, "Se rompio en el taller"), self.movimientos())
        self.assertIsNotNone(self.cierre_de(self.linea(baja)))
        self.assertEqual("cerrado", self.estado_del_vale(baja))

    def test_un_extravio_sale_como_perdida_y_queda_abierto(self):
        self.surtir(10)
        baja = self.baja(TIPO_EXTRAVIADO, cantidad=2, nota="No aparece en la nave")

        self.assertEqual(8, self._saldo())
        self.assertIn(("loss", -2, "No aparece en la nave"), self.movimientos())
        self.assertIsNone(self.cierre_de(self.linea(baja)))
        self.assertEqual("abierto", self.estado_del_vale(baja))


class TestSinNadaQueDarDeBaja(BaseBaja):

    def test_sin_existencia_y_sin_prestamo_se_rechaza(self):
        self.surtir(1)
        self.baja(TIPO_DESTRUCCION)                   # la unica pieza, del almacen
        with self.assertRaises(AppError) as contexto:
            self.baja(TIPO_DESTRUCCION)               # ya no hay nada
        self.assertEqual(contexto.exception.message_key, "errors.inventory_insufficient_stock")


class TestCualPrestamoSeCierra(BaseBaja):

    def test_se_cierra_el_prestamo_mas_antiguo(self):
        self.surtir(2)
        primero, segundo = self.prestar(), self.prestar()

        self.baja(TIPO_EXTRAVIADO)

        self.assertIsNotNone(self.cierre_de(self.linea(primero)))
        self.assertIsNone(self.cierre_de(self.linea(segundo)))

    def test_un_prestamo_parcial_no_se_cierra_a_ciegas(self):
        """Prestar 5 y perder 2 no es cerrar el renglon de 5: se rechaza en vez de inventar."""
        self.surtir(6)
        prestamo = self.prestar(5)                     # quedan 1 en el almacen
        with self.assertRaises(AppError) as contexto:
            self.baja(TIPO_EXTRAVIADO, cantidad=2)
        self.assertEqual(contexto.exception.message_key, "errors.inventory_insufficient_stock")
        self.assertIsNone(self.cierre_de(self.linea(prestamo)))


class TestUnReporteNoLlevaFechaNiQuienRecoge(BaseBaja):
    """Dañado, extraviado, destruccion y reparacion reportan un suceso: no hay "se necesita el"
    ni quien recoge, que son del prestamo."""

    def _cabecera(self, resultado):
        with transaction_context() as db:
            vale = db.get(Incident, resultado["voucher"]["id_incident"])
            return vale.needed_date, vale.pickup_name

    def test_un_reporte_descarta_la_fecha_y_quien_recoge(self):
        self.surtir(10)
        baja = self._vale([self._linea_cantidad(1)], id_incident_type=TIPO_EXTRAVIADO,
                          note="Se perdio en obra", needed_date="2099-01-01",
                          pickup_name="Chofer externo")

        self.assertEqual((None, None), self._cabecera(baja))

    def test_un_prestamo_si_conserva_fecha_y_quien_recoge(self):
        self.surtir(10)
        prestamo = self._vale([self._linea_cantidad(1)], needed_date="2099-01-01",
                              pickup_name="Chofer externo")

        needed, pickup = self._cabecera(prestamo)
        self.assertEqual("2099-01-01", str(needed))
        self.assertEqual("Chofer externo", pickup)
