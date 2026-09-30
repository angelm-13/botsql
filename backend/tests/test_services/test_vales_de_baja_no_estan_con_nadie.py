"""Un vale de baja no cuenta como "alguien lo tiene".

En el sistema anterior un vale de destruccion o extravio quedaba cerrado y sus
renglones seguian sin fecha de cierre, porque lo destruido o perdido nunca se
devuelve. Contarlos como "alguien lo tiene" ponia a la persona con mas herramientas
a un marcador ("ESTANCIA EN EL TALLER", 169 renglones) y a 173 de 329 renglones
"en manos de alguien" que eran bajas.

Decision del 2026-09-29: se excluyen Destruccion y Extraviado. **Dañado sigue dentro**
-no se sabe si quien lo daño todavia lo tiene- y Reparacion tambien -la pieza esta
fuera, en alguien-. Estas pruebas fijan que las cuatro consultas que cuentan "lo que
esta con alguien" usan la MISMA regla.
"""

from __future__ import annotations

from decimal import Decimal

from app.models import IncidentType, Product
from app.models.session import transaction_context
from app.services.inventory_service import apply_inventory_movement
from app.services.warehouse_voucher_service import (
    ABIERTO,
    buscar_vales,
    crear_vale,
    quien_tiene_que,
    reporte_vales_pendientes,
    vales_vencidos,
)
from tests.test_services.test_vale_de_almacen import (
    ACTOR, CEMENTO, COMPRA, MAT_CEMENTO, NAVE, BaseVale,
)

TIPOS = {"Destruccion": 81, "Extraviado": 82, "Dañado": 83, "Reparacion": 84}
# Un producto por vale: con el mismo producto en todos, un vale de baja cerraria el
# prestamo abierto del anterior (justo lo que hace en la vida real, y ver
# test_vale_de_baja_registra_lo_que_paso.py), y aqui se prueba otra cosa.
PRODUCTOS = {"Prestamo": CEMENTO, "Destruccion": 701, "Extraviado": 702, "Dañado": 703, "Reparacion": 704}
CUENTAN = ("Prestamo", "Dañado", "Reparacion")
NO_CUENTAN = ("Destruccion", "Extraviado")


class BaseBaja(BaseVale):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                IncidentType(id_incident_type=i, incident_type_description=nombre, created_by=1)
                for nombre, i in TIPOS.items()
            ])
        with transaction_context() as db:
            db.add_all([
                Product(id_product=i, id_invoice=COMPRA, id_location=NAVE, id_material=MAT_CEMENTO,
                        is_directly_related_to_product_service=True, product_code="BAJ-%s" % i,
                        descripcion="Herramienta %s" % i, stock_purpose="uso_interno",
                        tracking_mode="fungible", gross_price=Decimal("10.00"), created_by=1)
                for i in PRODUCTOS.values() if i != CEMENTO
            ])
        self.surtir()
        for i in PRODUCTOS.values():
            if i != CEMENTO:
                apply_inventory_movement(i, {
                    "movement_type": "receive", "quantity": 5, "id_location": NAVE,
                    "reason": "Surtido inicial", "idempotency_key": "surtido-baja:%s" % i,
                }, ACTOR)
        # Un vale de cada tipo, con un renglon de cemento. El de "Prestamo" es el
        # `TIPO_PRESTAMO` que ya trae la base de las pruebas.
        self.vales = {}
        for nombre in ("Prestamo", *TIPOS):
            carga = {} if nombre == "Prestamo" else {"id_incident_type": TIPOS[nombre]}
            linea = {"id_product": PRODUCTOS[nombre], "quantity": 1, "id_location_from": NAVE}
            resultado = self._vale([linea], **carga)
            self.vales[nombre] = (
                resultado["voucher"]["id_incident"],
                resultado["lines"][0]["id_nm_incident_product"],
            )

    def id_vale(self, nombre):
        return self.vales[nombre][0]

    def ids_de(self, nombres):
        return {self.id_vale(n) for n in nombres}


class TestQuienTieneQue(BaseBaja):

    def test_las_bajas_no_estan_con_nadie_y_lo_danado_si(self):
        resultado = quien_tiene_que(ACTOR)
        vales_con_algo = {
            r["id_incident"] for h in resultado["holders"] for r in h["items"]
        }
        self.assertEqual(self.ids_de(CUENTAN), vales_con_algo)
        self.assertEqual(len(CUENTAN), resultado["total_items"])

    def test_el_vale_de_baja_sigue_consultable(self):
        """No se esconde el vale: solo deja de contarse como prestamo. Una destruccion
        nace cerrada (lo destruido no vuelve); un extravio queda abierto hasta que
        aparezca."""
        vales = {v["id_incident"]: v for v in buscar_vales(ACTOR)["items"]}
        self.assertEqual("cerrado", vales[self.id_vale("Destruccion")]["incident_status"])
        self.assertEqual(ABIERTO, vales[self.id_vale("Extraviado")]["incident_status"])


class TestVencidos(BaseBaja):

    def test_una_baja_no_se_reclama_aunque_su_fecha_haya_pasado(self):
        for nombre in ("Prestamo", *TIPOS):
            self.vencer(self.vales[nombre][1])
        vencidos = vales_vencidos(ACTOR)
        ids = {r["id_incident"] for r in vencidos["items"]}
        self.assertEqual(self.ids_de(CUENTAN), ids)
        self.assertEqual(len(CUENTAN), vencidos["total"])


class TestBusquedaConPendientes(BaseBaja):

    def test_solo_con_pendientes_deja_fuera_las_bajas(self):
        con_pendientes = buscar_vales(ACTOR, solo_con_pendientes=True)
        self.assertEqual(self.ids_de(CUENTAN), {v["id_incident"] for v in con_pendientes["items"]})

    def test_los_renglones_pendientes_de_una_baja_son_cero(self):
        vales = {v["id_incident"]: v for v in buscar_vales(ACTOR)["items"]}
        for nombre in NO_CUENTAN:
            fila = vales[self.id_vale(nombre)]
            self.assertEqual(0, fila["open_lines"])
            self.assertEqual(1, fila["total_lines"])
        for nombre in CUENTAN:
            self.assertEqual(1, vales[self.id_vale(nombre)]["open_lines"])


class TestReporteDePendientes(BaseBaja):

    def test_el_reporte_de_pendientes_deja_fuera_las_bajas(self):
        reporte = reporte_vales_pendientes(ACTOR)
        renglones = {r["id_nm_incident_product"] for r in reporte["items"]}
        esperados = {self.vales[n][1] for n in CUENTAN}
        self.assertEqual(esperados, renglones)
