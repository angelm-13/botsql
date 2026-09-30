from __future__ import annotations

import unittest

from app.kpis.registry import ETIQUETA_DIMENSION_POR_OMISION, KPI_POR_CLAVE, KPI_REGISTRY
from app.models.kpi_definition import KpiDefinition
from app.routes.kpi import _con_metadatos_del_registry

# `_con_metadatos_del_registry` no toca la base -- solo lee atributos de una
# instancia y busca en KPI_POR_CLAVE por clave. No hace falta fixture de BD
# ni Postgres para probarla (y por eso vive en su propio archivo: mezclar una
# clase unittest.TestCase simple con las BackendTestCase de
# tests/test_api/test_api_kpi.py rompe el clasificador de
# backend/ci/run_postgres_tests.sh, que rechaza un archivo que mezcle ambas).


class ConMetadatosDelRegistryTest(unittest.TestCase):
    def test_expone_colores_categoria_de_material_por_estado(self):
        fila = KpiDefinition(clave="material_por_estado", etiqueta="Material por estado",
                              modulo="operaciones", dimensiones=["estado"], unidad="numero")
        fila.id_kpi_definition = 999

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual("dona", resultado["grafica_default"])
        self.assertEqual("neutral", resultado["direccion"])
        self.assertEqual(
            {"Entrada", "Salida", "Dañado", "Extraviado", "Destruccion"},
            set(resultado["colores_categoria"]),
        )
        self.assertIsNotNone(resultado["descripcion"])

    def test_expone_colores_categoria_de_incidencias_abiertas_vs_cerradas(self):
        fila = KpiDefinition(clave="incidencias_abiertas_vs_cerradas", etiqueta="Incidencias abiertas vs. cerradas",
                              modulo="operaciones", dimensiones=["estado"], unidad="numero")
        fila.id_kpi_definition = 996

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual({"abierta", "cerrada"}, set(resultado["colores_categoria"]))

    def test_expone_modo_vivo_de_material_prestado_actual(self):
        fila = KpiDefinition(clave="material_prestado_actual", etiqueta="Material prestado ahora",
                              modulo="operaciones", dimensiones=["empleado"], unidad="numero")
        fila.id_kpi_definition = 998

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual("vivo", resultado["modo"])
        self.assertEqual(["tabla"], resultado["graficas_permitidas"])

    def test_clave_huerfana_cae_a_defaults_neutros(self):
        fila = KpiDefinition(clave="no_existe_en_el_registro", etiqueta="x",
                              modulo="operaciones", dimensiones=["empleado"], unidad="numero")
        fila.id_kpi_definition = 997

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual("neutral", resultado["direccion"])
        self.assertEqual("snapshot", resultado["modo"])
        self.assertEqual([], resultado["graficas_permitidas"])
        self.assertIsNone(resultado["colores_categoria"])
        self.assertIsNone(resultado["descripcion"])


if __name__ == "__main__":
    unittest.main()


class EtiquetaDeIncidenciasAbiertasTest(unittest.TestCase):
    def test_se_llama_por_responsable_porque_es_id_user_no_quien_capturo(self):
        # id_user es el usuario a cuyo nombre esta el vale (quien TIENE el
        # material), no quien lo capturo. La clave no cambia: hay widgets y
        # permisos que la referencian.
        kpi = KPI_POR_CLAVE["incidencias_abiertas_por_empleado"]
        self.assertEqual("Incidencias abiertas por responsable", kpi.etiqueta)
        self.assertIn("responsable", kpi.descripcion.lower())
        self.assertNotIn("levanto", kpi.descripcion.lower())
        self.assertNotIn("empleado", kpi.etiqueta.lower())


class EtiquetaDeDimensionTest(unittest.TestCase):
    def test_incidencias_abiertas_declara_responsable_no_empleado(self):
        # La dimension interna sigue siendo "empleado"; lo que cambia es como se
        # llama en el selector "Agrupar por".
        kpi = KPI_POR_CLAVE["incidencias_abiertas_por_empleado"]
        self.assertEqual(("empleado",), kpi.dimensiones)
        self.assertEqual("Responsable", kpi.etiqueta_dimension)

    def test_los_kpis_por_responsable_y_por_tecnico_lo_dicen(self):
        for clave, esperada in {
            "vales_vencidos_por_responsable": "Responsable",
            "material_prestado_por_responsable": "Responsable",
            "prestamos_vencidos_por_responsable": "Responsable",
            "documentos_vencidos_por_responsable": "Responsable",
            "material_prestado_actual": "Responsable",
            "ordenes_laboratorio_entregadas_por_tecnico": "Técnico",
            "tiempo_promedio_reparacion_laboratorio_por_tecnico": "Técnico",
            "costo_promedio_reparacion_laboratorio_por_tecnico": "Técnico",
        }.items():
            self.assertEqual(esperada, KPI_POR_CLAVE[clave].etiqueta_dimension, clave)

    def test_un_kpi_sin_etiqueta_propia_toma_la_de_su_dimension(self):
        self.assertEqual("Empleado", KPI_POR_CLAVE["ventas_por_empleado"].etiqueta_dimension)
        self.assertEqual("Producto", KPI_POR_CLAVE["articulos_bajo_stock"].etiqueta_dimension)
        self.assertEqual("Estado", KPI_POR_CLAVE["material_por_estado"].etiqueta_dimension)
        self.assertEqual("Total", KPI_POR_CLAVE["ingresos_totales"].etiqueta_dimension)

    def test_todos_los_kpis_tienen_etiqueta_de_dimension(self):
        for kpi in KPI_REGISTRY:
            self.assertTrue(kpi.etiqueta_dimension, kpi.clave)
            self.assertLessEqual(len(kpi.etiqueta_dimension), 30, kpi.clave)
        self.assertEqual({"empleado", "producto", "estado", "global"}, set(ETIQUETA_DIMENSION_POR_OMISION))

    def test_la_api_la_expone(self):
        fila = KpiDefinition(clave="incidencias_abiertas_por_empleado", etiqueta="x", modulo="operaciones",
                              dimensiones=["empleado"], unidad="numero")
        fila.id_kpi_definition = 997
        self.assertEqual("Responsable", _con_metadatos_del_registry(fila)["etiqueta_dimension"])
        huerfana = KpiDefinition(clave="ya_no_existe", etiqueta="x", modulo="operaciones", dimensiones=["empleado"], unidad="numero")
        huerfana.id_kpi_definition = 996
        self.assertEqual("", _con_metadatos_del_registry(huerfana)["etiqueta_dimension"])
