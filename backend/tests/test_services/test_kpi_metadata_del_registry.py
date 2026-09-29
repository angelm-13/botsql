from __future__ import annotations

import unittest

from app.kpis.registry import KPI_POR_CLAVE
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
