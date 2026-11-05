"""`_estado_del_renglon` reconoce los tipos de baja con o sin acento y siempre devuelve la MISMA llave.

La etiqueta del renglon es tambien la llave de `material_por_estado` (`colores_categoria`, snapshots y
esperados usan "Dañado" y "Destruccion"). Antes, "Danado" (sin enie) y "Destrucción" (con acento) caian en
"Salida": el KPI y los reportes de vales contaban el mismo vale en categorias distintas. Se normaliza solo la
ENTRADA; la salida conserva las llaves de siempre.
"""

from __future__ import annotations

from app.models.session import transaction_context
from app.models import IncidentType
from app.services.warehouse_voucher_service import (
    _estado_del_renglon, reporte_por_almacen, reporte_por_persona, reporte_por_producto, reporte_vales_pendientes,
)
from tests.test_services import test_vale_de_almacen as base

ACTOR = base.ACTOR
TIPO_ESPECIAL = 999

CASOS = (
    ("Dañado", "Dañado"), ("Danado", "Dañado"), ("DAÑADO", "Dañado"), ("  dañado ", "Dañado"),
    ("Destruccion", "Destruccion"), ("Destrucción", "Destruccion"), ("DESTRUCCIÓN", "Destruccion"),
    ("Extraviado", "Extraviado"), (" extraviado", "Extraviado"),
)


class TestElEstadoDelRenglonNormalizaLaEntrada(base.BaseVale):
    def test_los_tipos_especiales_dan_siempre_la_misma_llave(self):
        for escrito, llave in CASOS:
            for direccion in ("entrada", "salida", None):
                self.assertEqual(llave, _estado_del_renglon(direccion, escrito), (escrito, direccion))

    def test_lo_demas_sigue_siendo_entrada_o_salida(self):
        self.assertEqual("Entrada", _estado_del_renglon("entrada", "Prestamo"))
        self.assertEqual("Salida", _estado_del_renglon("salida", "Prestamo"))
        self.assertEqual("Salida", _estado_del_renglon(None, None))
        self.assertEqual("Entrada", _estado_del_renglon("ENTRADA", "Reparacion"))

    def _vale_de_tipo(self, descripcion):
        with transaction_context() as db:
            db.add(IncidentType(id_incident_type=TIPO_ESPECIAL, incident_type_description=descripcion, created_by=1))
        self.surtir(100)
        return self._vale([self._linea_cantidad(10)], id_incident_type=TIPO_ESPECIAL)

    def _estados(self, reporte):
        if "items" in reporte:
            return {r["status"] for r in reporte["items"]}
        return {r["status"] for g in reporte["groups"] for r in g["items"]}

    def test_los_cuatro_reportes_usan_la_llave_con_un_tipo_sin_enie(self):
        self._vale_de_tipo("Danado")
        for reporte in (reporte_por_producto, reporte_por_almacen, reporte_por_persona, reporte_vales_pendientes):
            self.assertEqual({"Dañado"}, self._estados(reporte(ACTOR)), reporte.__name__)

    def test_tres_reportes_usan_la_llave_con_un_tipo_con_acento(self):
        # La destruccion cierra su renglon al registrarse: no sale en "pendientes", que solo lista salidas abiertas.
        self._vale_de_tipo("Destrucción")
        for reporte in (reporte_por_producto, reporte_por_almacen, reporte_por_persona):
            self.assertEqual({"Destruccion"}, self._estados(reporte(ACTOR)), reporte.__name__)
