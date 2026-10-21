from __future__ import annotations

import unittest
from unittest import mock

from app.kpis import registry
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

    def test_expone_el_orden_de_categorias_solo_de_los_kpis_de_categorias_ordenadas(self):
        fila = KpiDefinition(clave="prestamos_abiertos_por_antiguedad", etiqueta="Prestamos abiertos por antiguedad",
                              modulo="operaciones", dimensiones=["estado"], unidad="numero")
        fila.id_kpi_definition = 995

        resultado = _con_metadatos_del_registry(fila)

        # Una LISTA, en el orden de lectura: no por valor ni el de un dict.
        self.assertEqual(["0-30", "31-60", "61-90", "+90"], resultado["orden_categorias"])
        # Los demas KPIs de estado siguen sin orden propio (el Dashboard los ordena por valor).
        for clave in ("material_por_estado", "incidencias_abiertas_vs_cerradas"):
            with self.subTest(clave=clave):
                self.assertIsNone(KPI_POR_CLAVE[clave].orden_categorias)
        # Solo los de categorias con un orden de lectura propio: las ordinales de antiguedad y los
        # estados de la pieza (de lo normal a lo grave).
        self.assertEqual(
            ["prestamos_abiertos_por_antiguedad", "piezas_por_estado", "pedidos_del_dia", "mesas_ocupadas"],
            [kpi.clave for kpi in KPI_REGISTRY if kpi.orden_categorias is not None],
        )

    def test_expone_el_limite_de_categorias_solo_de_perdidas_por_familia(self):
        fila = KpiDefinition(clave="perdidas_por_familia", etiqueta="Perdidas por familia",
                              modulo="operaciones", dimensiones=["familia"], unidad="piezas")
        fila.id_kpi_definition = 994

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual(10, resultado["limite_categorias"])
        self.assertEqual("Familia", resultado["etiqueta_dimension"])
        # Entre los 24 de siempre, solo uno corta categorias; los de restaurante cortan sus "top 10".
        self.assertEqual(["perdidas_por_familia"], [k.clave for k in KPI_REGISTRY[:24] if k.limite_categorias is not None])
        self.assertEqual(
            {"platillos_mas_vendidos", "frecuencia_por_platillo", "top_mesas"},
            {k.clave for k in KPI_REGISTRY[24:] if k.limite_categorias is not None},
        )

    def test_un_limite_de_categorias_malo_falla_al_importar(self):
        for malo in (0, -3, 2.5, True, "10"):
            kpi = registry.KpiDefinition(
                "kpi_de_prueba", "Prueba", "operaciones", ("familia",), lambda *a: [],
                direccion="neutral", graficas_permitidas=("barras",), grafica_default="barras",
                agregacion="suma", limite_categorias=malo,
            )
            with self.subTest(limite=malo), mock.patch.object(registry, "KPI_REGISTRY", (kpi,)):
                with self.assertRaisesRegex(RuntimeError, "limite_categorias"):
                    registry._validar()

    def test_ocultar_ceros_solo_tiene_sentido_en_un_kpi_snapshot_con_entidades(self):
        def kpi(dimension, **extra):
            return registry.KpiDefinition(
                "kpi_de_prueba", "Prueba", "operaciones", (dimension,), lambda *a: [],
                direccion="neutral", graficas_permitidas=("barras",), grafica_default="barras",
                **{"agregacion": "ultimo", **extra, "ocultar_ceros": True},
            )

        for dimension in ("empleado", "equipo", "mesero"):
            with self.subTest(dimension=dimension), mock.patch.object(registry, "KPI_REGISTRY", (kpi(dimension),)):
                registry._validar()  # no revienta
        for dimension in ("global", "estado"):
            with self.subTest(dimension=dimension), mock.patch.object(registry, "KPI_REGISTRY", (kpi(dimension),)):
                with self.assertRaisesRegex(RuntimeError, "ocultar_ceros"):
                    registry._validar()
        with self.subTest(modo="vivo"), mock.patch.object(registry, "KPI_REGISTRY", (kpi("empleado", modo="vivo", agregacion=None),)):
            with self.assertRaisesRegex(RuntimeError, "ocultar_ceros"):
                registry._validar()

    def test_ocultar_ceros_es_false_por_omision_y_el_mapa_lo_refleja(self):
        for kpi in KPI_REGISTRY:
            self.assertEqual(kpi.ocultar_ceros, registry.OCULTAR_CEROS_POR_CLAVE[kpi.clave], kpi.clave)
        self.assertFalse(KPI_POR_CLAVE["ventas_por_empleado"].ocultar_ceros, "un KPI de siempre no cambia")

    def test_sin_asignar_solo_tiene_sentido_con_entidades_que_puedan_faltar(self):
        def kpi(dimension, sin_asignar):
            return registry.KpiDefinition(
                "kpi_de_prueba", "Prueba", "operaciones", (dimension,), lambda *a: [],
                direccion="neutral", graficas_permitidas=("barras",), grafica_default="barras",
                agregacion="suma", sin_asignar=sin_asignar,
            )

        for dimension in ("mesero", "empleado", "platillo"):
            with self.subTest(dimension=dimension), mock.patch.object(registry, "KPI_REGISTRY", (kpi(dimension, True),)):
                registry._validar()  # no revienta
        for dimension in ("global", "estado"):
            with self.subTest(dimension=dimension), mock.patch.object(registry, "KPI_REGISTRY", (kpi(dimension, True),)):
                with self.assertRaisesRegex(RuntimeError, "sin_asignar"):
                    registry._validar()

    def test_los_24_kpis_de_siempre_no_muestran_sin_asignar(self):
        self.assertEqual([], [k.clave for k in KPI_REGISTRY[:24] if k.sin_asignar])
        self.assertEqual({k.clave: k.sin_asignar for k in KPI_REGISTRY}, registry.SIN_ASIGNAR_POR_CLAVE)

    def test_la_unidad_minutos_es_valida(self):
        self.assertIn("minutos", registry.UNIDADES)
        self.assertEqual("minutos", KPI_POR_CLAVE["tiempo_de_entrega"].unidad)

    def test_un_orden_de_categorias_malo_falla_al_importar(self):
        def kpi(orden, colores):
            return registry.KpiDefinition(
                "kpi_de_prueba", "Prueba", "operaciones", ("estado",), lambda *a: [],
                direccion="neutral", graficas_permitidas=("barras",), grafica_default="barras",
                agregacion="suma", colores_categoria=colores, orden_categorias=orden,
            )

        bueno = kpi(["a", "b"], {"a": "#111111", "b": "#222222"})
        with mock.patch.object(registry, "KPI_REGISTRY", (bueno,)):
            registry._validar()  # no revienta
        for orden, colores, motivo in (
            (["a", "a"], None, "repite una categoria"),
            (["a", "c"], {"a": "#111111", "b": "#222222"}, "categorias distintas"),
        ):
            with self.subTest(motivo=motivo), mock.patch.object(registry, "KPI_REGISTRY", (kpi(orden, colores),)):
                with self.assertRaisesRegex(RuntimeError, motivo):
                    registry._validar()

    def test_clave_huerfana_cae_a_defaults_neutros(self):
        fila = KpiDefinition(clave="no_existe_en_el_registro", etiqueta="x",
                              modulo="operaciones", dimensiones=["empleado"], unidad="numero")
        fila.id_kpi_definition = 997

        resultado = _con_metadatos_del_registry(fila)

        self.assertEqual("neutral", resultado["direccion"])
        self.assertEqual("snapshot", resultado["modo"])
        self.assertEqual([], resultado["graficas_permitidas"])
        self.assertIsNone(resultado["colores_categoria"])
        self.assertIsNone(resultado["orden_categorias"])
        self.assertIsNone(resultado["limite_categorias"])
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
        # Las cinco de siempre mas las de restaurante, logistica y equipos (catalogo en app/kpis/dimensiones.py).
        self.assertEqual(
            {"empleado", "producto", "estado", "familia", "global",
             "mesero", "platillo", "mesa", "cliente", "unidad", "operador", "equipo"},
            set(ETIQUETA_DIMENSION_POR_OMISION),
        )

    def test_la_api_la_expone(self):
        fila = KpiDefinition(clave="incidencias_abiertas_por_empleado", etiqueta="x", modulo="operaciones",
                              dimensiones=["empleado"], unidad="numero")
        fila.id_kpi_definition = 997
        self.assertEqual("Responsable", _con_metadatos_del_registry(fila)["etiqueta_dimension"])
        huerfana = KpiDefinition(clave="ya_no_existe", etiqueta="x", modulo="operaciones", dimensiones=["empleado"], unidad="numero")
        huerfana.id_kpi_definition = 996
        self.assertEqual("", _con_metadatos_del_registry(huerfana)["etiqueta_dimension"])


CHECADAS = (
    "checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo", "checadas_entradas_por_equipo",
    "checadas_salidas_por_equipo", "checadas_en_turno_por_empleado", "horas_trabajadas_por_empleado",
    "checadas_con_duracion_anomala",
)


class GrupoDelSelectorTest(unittest.TestCase):
    """`grupo`: la pestana del selector de KPI donde sale un KPI en vez de la de su modulo. Solo agrupa en pantalla."""

    def test_los_siete_kpis_de_checadas_van_a_asistencias_sin_dejar_de_ser_de_operaciones(self):
        for clave in CHECADAS:
            kpi = KPI_POR_CLAVE[clave]
            self.assertEqual("asistencias", kpi.grupo, clave)
            self.assertEqual("operaciones", kpi.modulo, f"{clave}: el modulo real no cambia (licencias, permisos, job)")

    def test_ningun_otro_kpi_declara_grupo(self):
        self.assertEqual(set(CHECADAS), {kpi.clave for kpi in KPI_REGISTRY if kpi.grupo is not None})

    def test_la_api_entrega_el_grupo_junto_al_modulo_real(self):
        agrupado = KpiDefinition(clave="checadas_en_turno_por_equipo", etiqueta="x", modulo="operaciones",
                                  dimensiones=["equipo"], unidad="numero")
        agrupado.id_kpi_definition = 990
        resultado = _con_metadatos_del_registry(agrupado)
        self.assertEqual("asistencias", resultado["grupo"])
        self.assertEqual("operaciones", resultado["modulo"])

        de_siempre = KpiDefinition(clave="ventas_por_empleado", etiqueta="x", modulo="facturacion",
                                    dimensiones=["empleado"], unidad="moneda")
        de_siempre.id_kpi_definition = 991
        self.assertIsNone(_con_metadatos_del_registry(de_siempre)["grupo"])

        huerfana = KpiDefinition(clave="ya_no_existe", etiqueta="x", modulo="operaciones",
                                  dimensiones=["empleado"], unidad="numero")
        huerfana.id_kpi_definition = 992
        self.assertIsNone(_con_metadatos_del_registry(huerfana)["grupo"])

    def test_un_grupo_desconocido_falla_al_importar(self):
        def kpi(grupo):
            return registry.KpiDefinition(
                "kpi_de_prueba", "Prueba", "operaciones", ("empleado",), lambda *a: [],
                direccion="neutral", graficas_permitidas=("barras",), grafica_default="barras",
                agregacion="suma", grupo=grupo,
            )

        with mock.patch.object(registry, "KPI_REGISTRY", (kpi("asistencias"),)):
            registry._validar()  # no revienta
        for malo in ("asistenciass", "operaciones", ""):
            with self.subTest(grupo=malo), mock.patch.object(registry, "KPI_REGISTRY", (kpi(malo),)):
                with self.assertRaisesRegex(RuntimeError, "grupo desconocido"):
                    registry._validar()

    def test_un_grupo_no_se_llama_como_un_modulo_real(self):
        # La pestana se identifica por una sola clave: la de su grupo o, si no tiene, la de su modulo. Si un grupo
        # se llamara como un modulo, el selector fundiria las dos pestanas en una.
        from app.modules.registry import MODULO_POR_CLAVE

        self.assertEqual(set(), set(registry.GRUPOS_DE_SELECTOR) & set(MODULO_POR_CLAVE))

    def test_el_grupo_no_es_una_columna_de_kpi_definition(self):
        # Vive en el registry y la API lo entrega desde ahi (como `direccion` o `descripcion`): no hay migracion.
        self.assertNotIn("grupo", KpiDefinition.__table__.columns)
