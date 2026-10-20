"""Lo que los KPIs de checadas declaran en el registro (sin base de datos).

Va aparte de test_kpi_checadas.py porque `backend/ci/run_postgres_tests.sh` clasifica cada archivo por su clase base y
rechaza uno que mezcle `BackendTestCase` con `unittest.TestCase`.
"""

from __future__ import annotations

import inspect
import unittest

from app.kpis import frecuencia
from app.kpis.modulos import checadas
from app.kpis.modulos.checadas import UMBRAL_SIN_SALIDA_HORAS
from app.kpis.registry import KPI_POR_CLAVE


class DefinicionesDeChecadasTest(unittest.TestCase):
    CLAVES_DE_FOTO = ("checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo")

    def test_el_criterio_de_checada_vive_en_un_solo_lugar(self):
        # `es_checada()` es la unica que nombra `Incident.latitude`; las consultas la reutilizan.
        fuente = inspect.getsource(checadas)
        self.assertEqual(1, fuente.count("Incident.latitude"), "el criterio no se repite en cada consulta")
        self.assertIn("es_checada()", inspect.getsource(checadas.checadas_vigentes))

    def test_los_kpis_de_foto_son_de_operaciones_por_equipo_y_solo_barras(self):
        for clave in self.CLAVES_DE_FOTO:
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, clave)
            self.assertEqual(("equipo",), kpi.dimensiones, clave)
            self.assertEqual("ultimo", kpi.agregacion, clave)
            self.assertEqual("snapshot", kpi.modo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertTrue(kpi.sin_asignar, f"{clave}: la gente sin equipo sale en la fila 'Sin equipo'")
            # Una persona en dos equipos cuenta en cada uno: el total entre equipos la contaria dos veces. Solo
            # barras (un valor por equipo); "numero" y "linea" usan ese total.
            self.assertEqual(("barras",), tuple(kpi.graficas_permitidas), clave)
            self.assertEqual("barras", kpi.grafica_default, clave)

    def test_los_kpis_que_entran_a_la_corrida_frecuente_son_estos_y_no_las_horas(self):
        esperados = {
            "checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo", "checadas_entradas_por_equipo",
            "checadas_salidas_por_equipo", "checadas_en_turno_por_empleado",
        }
        self.assertEqual([], [c for c in frecuencia.KPIS_FRECUENTES if c not in KPI_POR_CLAVE])
        self.assertEqual(esperados, set(frecuencia.KPIS_FRECUENTES))
        self.assertNotIn("horas_trabajadas_por_empleado", frecuencia.KPIS_FRECUENTES, "las horas siguen solo nocturnas")
        for clave in frecuencia.KPIS_FRECUENTES:
            self.assertEqual("snapshot", KPI_POR_CLAVE[clave].modo, clave)
            self.assertNotIn(KPI_POR_CLAVE[clave].modulo, frecuencia.MODULOS_FRECUENTES, "entra por su clave, no por su modulo")

    def test_sin_salida_es_mejor_cuando_baja(self):
        self.assertEqual("bajo_es_mejor", KPI_POR_CLAVE["checadas_sin_salida_por_equipo"].direccion)
        self.assertEqual("neutral", KPI_POR_CLAVE["checadas_en_turno_por_equipo"].direccion)


class DefinicionesDeFlujosTest(unittest.TestCase):
    def test_entradas_y_salidas_son_flujos_por_equipo_de_operaciones_y_solo_barras(self):
        for clave in ("checadas_entradas_por_equipo", "checadas_salidas_por_equipo"):
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("operaciones", kpi.modulo, clave)
            self.assertEqual(("equipo",), kpi.dimensiones, clave)
            self.assertEqual("suma", kpi.agregacion, clave)
            self.assertEqual("snapshot", kpi.modo, clave)
            self.assertFalse(kpi.alcance_proyecto, clave)
            self.assertTrue(kpi.sin_asignar, f"{clave}: tambien llevan la fila 'Sin equipo', como las fotos")
            self.assertEqual(("barras",), tuple(kpi.graficas_permitidas), clave)


class DefinicionDeEnTurnoPorEmpleadoTest(unittest.TestCase):
    def test_es_una_foto_por_empleado_en_minutos_que_oculta_a_quien_ya_salio(self):
        kpi = KPI_POR_CLAVE["checadas_en_turno_por_empleado"]
        self.assertEqual("operaciones", kpi.modulo)
        self.assertEqual(("empleado",), kpi.dimensiones)
        self.assertEqual("ultimo", kpi.agregacion)
        self.assertEqual("snapshot", kpi.modo)
        self.assertEqual("minutos", kpi.unidad)
        self.assertFalse(kpi.alcance_proyecto)
        self.assertEqual(("barras",), tuple(kpi.graficas_permitidas))
        self.assertTrue(kpi.ocultar_ceros, "la API no pinta a quien ya salio de turno")
        self.assertFalse(kpi.sin_asignar, "una persona siempre es alguien: no hay fila 'sin asignar'")
        self.assertIn(str(UMBRAL_SIN_SALIDA_HORAS), kpi.descripcion)

    def test_solo_este_kpi_de_checadas_oculta_ceros(self):
        # Los equipos en cero SI se pintan (un parque sin nadie es un dato); solo la foto por persona los oculta.
        con_ceros_ocultos = [k.clave for k in KPI_POR_CLAVE.values() if k.ocultar_ceros]
        self.assertEqual(["checadas_en_turno_por_empleado"], con_ceros_ocultos)

