"""Validacion de `parametros` de un widget de KPI (S2) y desempate numerico del ranking (K3).

Corre en SQLite: solo ejerce las funciones puras (`_validar_parametros`, `_orden_de_desempate`). El guardado de punta a punta por la
API esta en `tests/test_api/test_api_kpi.py`, que necesita PostgreSQL.

`FRONTEND_REAL` NO esta escrito a mano: son los `parametros` que producen `armarParametros` (`kpi/kpiParametros.js`) y
`parametrosConRangoRelativo` (`kpi/kpiFechasFijas.js`) con `hoy = 2026-11-04`, corridos con Node. Si el editor empieza a guardar
una llave nueva, esta prueba lo dice (400) antes de que lo haga un usuario.
"""

from __future__ import annotations

import json
import unittest

from app.routes.kpi import _orden_de_desempate
from app.services.kpi_dashboard_widget_service import (
    CLAVES_DE_PARAMETROS, PARAMETROS_BYTES_MAX, KpiDashboardWidgetService,
)
from app.utils.errors import AppError

FRONTEND_REAL = json.loads(r'''{
 "relativo_vs_periodo_anterior": {
  "fecha_inicio": "2026-10-06",
  "fecha_fin": "2026-11-04",
  "rango_relativo": "30_dias",
  "comparar_anterior": true,
  "fecha_inicio_b": "2026-09-06",
  "fecha_fin_b": "2026-10-05",
  "empleados": [
   5,
   7
  ],
  "id_teams": [
   4
  ],
  "colores_kpi": {
   "3": "#2a78d6",
   "4": "#eb6834"
  },
  "orientacion": "horizontal",
  "titulo": "Mi gráfico",
  "umbral_bajo_stock": 12
 },
 "relativo_vs_hace_30_dias": {
  "fecha_inicio": "2026-10-06",
  "fecha_fin": "2026-11-04",
  "rango_relativo": "30_dias",
  "comparar_desfase_dias": 30,
  "fecha_inicio_b": "2026-09-06",
  "fecha_fin_b": "2026-10-05",
  "empleados": [
   5,
   7
  ],
  "id_teams": [
   4
  ],
  "colores_kpi": {
   "3": "#2a78d6",
   "4": "#eb6834"
  },
  "orientacion": "horizontal",
  "titulo": "Mi gráfico"
 },
 "personalizado_con_rango_b": {
  "fecha_inicio": "2026-08-01",
  "fecha_fin": "2026-08-31",
  "fecha_inicio_b": "2026-07-01",
  "fecha_fin_b": "2026-07-31",
  "empleados": [
   5,
   7
  ],
  "id_teams": [
   4
  ],
  "colores_kpi": {
   "3": "#2a78d6",
   "4": "#eb6834"
  },
  "orientacion": "horizontal",
  "titulo": "Mi gráfico",
  "umbral_bajo_stock": 12
 },
 "tabla_doble_con_orden": {
  "columnas": 2,
  "filas": 2,
  "orden_tabla": {
   "campo": "dias_prestado",
   "direccion": "desc"
  },
  "titulo": "Mi gráfico"
 },
 "hacer_relativo_conserva_todo": {
  "fecha_inicio": "2026-10-06",
  "fecha_fin": "2026-11-04",
  "fecha_inicio_b": "2026-09-06",
  "fecha_fin_b": "2026-10-05",
  "empleados": [
   5,
   7
  ],
  "id_teams": [
   4
  ],
  "colores_kpi": {
   "3": "#2a78d6",
   "4": "#eb6834"
  },
  "orientacion": "horizontal",
  "titulo": "Mi gráfico",
  "umbral_bajo_stock": 12,
  "clave_vieja_que_ya_traia": 1,
  "rango_relativo": "30_dias",
  "comparar_anterior": true
 }
}''')


def _validar(parametros, existentes=()):
    return KpiDashboardWidgetService._validar_parametros(parametros, existentes=existentes)


class ParametrosValidosTest(unittest.TestCase):
    def test_lo_que_guarda_el_editor_real_se_acepta_tal_cual(self):
        for nombre, parametros in FRONTEND_REAL.items():
            if nombre == "hacer_relativo_conserva_todo":
                continue   # lleva una llave vieja a proposito: ver abajo
            with self.subTest(escenario=nombre):
                self.assertEqual(parametros, _validar(parametros))

    def test_comparar_contra_el_periodo_anterior_y_contra_hace_30_dias(self):
        anterior = _validar(FRONTEND_REAL["relativo_vs_periodo_anterior"])
        self.assertIs(True, anterior["comparar_anterior"])
        self.assertEqual(("2026-09-06", "2026-10-05"), (anterior["fecha_inicio_b"], anterior["fecha_fin_b"]))
        desfase = _validar(FRONTEND_REAL["relativo_vs_hace_30_dias"])
        self.assertEqual(30, desfase["comparar_desfase_dias"])

    def test_un_widget_sin_nada_o_con_solo_el_tamano_de_una_tabla(self):
        self.assertEqual({}, _validar({}))
        self.assertEqual({"columnas": 2, "filas": 2}, _validar({"columnas": 2, "filas": 2}))

    def test_el_rango_b_vacio_se_tolera_como_ausente(self):
        parametros = {"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-31", "fecha_inicio_b": "", "fecha_fin_b": None}
        self.assertEqual(parametros, _validar(parametros))

    def test_el_umbral_acepta_cero_y_decimales(self):
        for valor in (0, 12, 12.5):
            with self.subTest(valor=valor):
                self.assertEqual(valor, _validar({"umbral_bajo_stock": valor})["umbral_bajo_stock"])

    def test_los_ids_pueden_llegar_como_numero_o_como_texto_numerico(self):
        self.assertEqual({"empleados": [5, "7"]}, _validar({"empleados": [5, "7"]}))

    def test_las_llaves_permitidas_son_exactamente_las_del_editor(self):
        usadas = set()
        for parametros in FRONTEND_REAL.values():
            usadas |= set(parametros)
        usadas -= {"clave_vieja_que_ya_traia"}
        self.assertLessEqual(usadas, CLAVES_DE_PARAMETROS, "el editor guarda una llave que el servidor rechazaria")


class ParametrosRechazadosTest(unittest.TestCase):
    def _rechaza(self, parametros, clave="errors.invalid_field", campo=None, existentes=()):
        with self.assertRaises(AppError, msg=repr(parametros)) as contexto:
            _validar(parametros, existentes)
        self.assertEqual(clave, contexto.exception.message_key, repr(parametros))
        self.assertEqual(400, contexto.exception.status_code)
        if campo is not None:
            self.assertEqual(campo, contexto.exception.meta["field"], repr(parametros))
        return contexto.exception

    def test_tipo_invalido(self):
        casos = {
            "parametros.fecha_inicio": [{"fecha_inicio": 20261001}, {"fecha_inicio": ["2026-10-01"]}, {"fecha_inicio": "01/10/2026"}, {"fecha_inicio": "2026-1-1"}],
            "parametros.comparar_anterior": [{"comparar_anterior": "si"}, {"comparar_anterior": 1}],
            "parametros.empleados": [{"empleados": "5"}, {"empleados": None}, {"empleados": {"a": 1}}],
            "parametros.id_teams": [{"id_teams": [True]}, {"id_teams": [1.5]}, {"id_teams": ["x"]}],
            "parametros.colores_kpi": [{"colores_kpi": [1]}, {"colores_kpi": None}, {"colores_kpi": {"3": "rojo"}}, {"colores_kpi": {"3": 7}}],
            "parametros.umbral_bajo_stock": [{"umbral_bajo_stock": "12"}, {"umbral_bajo_stock": True}, {"umbral_bajo_stock": None}, {"umbral_bajo_stock": float("nan")}],
            "parametros.agrupar_por": [{"agrupar_por": "mes"}, {"agrupar_por": {}}],
            "parametros.rango_relativo": [{"rango_relativo": "ayer"}, {"rango_relativo": []}],
            "parametros.comparar_desfase_dias": [{"comparar_desfase_dias": "30"}, {"comparar_desfase_dias": 7.5}, {"comparar_desfase_dias": True}],
            "parametros.columnas": [{"columnas": "2"}, {"columnas": None}],
        }
        for campo, lista in casos.items():
            for parametros in lista:
                with self.subTest(parametros=parametros):
                    self._rechaza(parametros, campo=campo)

    def test_una_fecha_que_no_existe_no_es_un_500(self):
        error = self._rechaza({"fecha_fin": "2026-02-30"}, campo="parametros.fecha_fin")
        self.assertEqual("fecha_inexistente", error.meta["reason"])

    def test_no_es_un_diccionario(self):
        for valor in (None, [], "texto", 7):
            with self.subTest(valor=valor):
                self._rechaza(valor, campo="parametros")

    def test_clave_desconocida_dice_cual_y_cuales_si_se_permiten(self):
        error = self._rechaza({"fecha_inicio": "2026-10-01", "foo": 1, "bar": 2}, campo="parametros")
        self.assertEqual("claves_desconocidas", error.meta["reason"])
        self.assertEqual(["bar", "foo"], error.meta["unknown_keys"])
        self.assertIn("fecha_inicio", error.meta["allowed"])

    def test_valor_fuera_de_rango(self):
        for parametros, campo in (
            ({"comparar_desfase_dias": 0}, "parametros.comparar_desfase_dias"),
            ({"comparar_desfase_dias": -30}, "parametros.comparar_desfase_dias"),
            ({"comparar_desfase_dias": 367}, "parametros.comparar_desfase_dias"),
            ({"columnas": 0}, "parametros.columnas"),
            ({"filas": 3}, "parametros.filas"),
            ({"empleados": [0]}, "parametros.empleados"),
            ({"empleados": [-4]}, "parametros.empleados"),
            ({"umbral_bajo_stock": 1e30}, "parametros.umbral_bajo_stock"),
            ({"empleados": list(range(1, 502))}, "parametros.empleados"),
            ({"colores_kpi": {str(i): "#aabbcc" for i in range(1, 52)}}, "parametros.colores_kpi"),
            ({"fecha_inicio": "2026-10-31", "fecha_fin": "2026-10-01"}, "parametros.fecha_fin"),
            ({"fecha_inicio_b": "2026-10-31", "fecha_fin_b": "2026-10-01"}, "parametros.fecha_fin_b"),
        ):
            with self.subTest(parametros=str(parametros)[:60]):
                self._rechaza(parametros, campo=campo)

    def test_un_rango_de_mas_de_un_anio_usa_el_mismo_mensaje_que_la_consulta(self):
        error = self._rechaza({"fecha_inicio": "2024-01-01", "fecha_fin": "2026-01-01"}, clave="errors.rango_excede_limite")
        self.assertEqual(365, error.meta["dias_maximo"])
        self._rechaza({"fecha_inicio_b": "2024-01-01", "fecha_fin_b": "2026-01-01"}, clave="errors.rango_excede_limite")
        _validar({"fecha_inicio": "2025-11-05", "fecha_fin": "2026-11-05"})   # justo 365 dias: cabe

    def test_un_parametros_gigante_se_corta_antes_de_revisarlo(self):
        error = self._rechaza({"titulo": "x" * (PARAMETROS_BYTES_MAX + 1)}, clave="errors.field_too_long", campo="parametros")
        self.assertEqual(PARAMETROS_BYTES_MAX, error.meta["max_bytes"])

    def test_nada_de_lo_anterior_es_un_error_distinto_de_un_400(self):
        raros = [{"fecha_inicio": []}, {"rango_relativo": {}}, {"colores_kpi": {"abc": "#aabbcc"}}, {"empleados": [[1]]}, {"orden_tabla": 5}, {"relleno": None}]
        for parametros in raros:
            with self.subTest(parametros=str(parametros)):
                with self.assertRaises(AppError) as contexto:
                    _validar(parametros)
                self.assertEqual(400, contexto.exception.status_code)


class UpdateConLlavesViejasTest(unittest.TestCase):
    """Al convertir un rango a relativo el editor reenvia TODO lo que el widget ya traia (`parametrosConRangoRelativo`)."""

    def test_una_llave_que_el_widget_ya_tenia_se_tolera_en_un_update(self):
        reenviado = FRONTEND_REAL["hacer_relativo_conserva_todo"]
        self.assertIn("clave_vieja_que_ya_traia", reenviado)
        self.assertEqual(reenviado, _validar(reenviado, existentes={"clave_vieja_que_ya_traia"}))

    def test_la_misma_llave_se_rechaza_en_un_alta_o_si_el_widget_no_la_traia(self):
        reenviado = FRONTEND_REAL["hacer_relativo_conserva_todo"]
        with self.assertRaises(AppError) as contexto:
            _validar(reenviado)
        self.assertEqual(["clave_vieja_que_ya_traia"], contexto.exception.meta["unknown_keys"])

    def test_tolerar_una_llave_no_exime_de_validar_las_conocidas(self):
        with self.assertRaises(AppError):
            _validar({"vieja": 1, "comparar_desfase_dias": 0}, existentes={"vieja"})


class DesempateNumericoTest(unittest.TestCase):
    """K3: el empate entre entidades se resuelve por el id MENOR como numero, no como texto ("10" antes que "9")."""

    @staticmethod
    def _top(por_entidad, limite):
        return [e for e, _ in sorted(por_entidad.items(), key=lambda par: (-par[1], _orden_de_desempate(par[0])))[:limite]]

    def test_el_nueve_va_antes_que_el_diez(self):
        self.assertEqual(["9", "10"], self._top({"10": 5, "9": 5}, 2))

    def test_el_valor_manda_y_el_id_solo_desempata(self):
        self.assertEqual(["30", "9", "10"], self._top({"9": 5, "10": 5, "30": 6}, 3))

    def test_las_etiquetas_de_texto_van_despues_de_los_ids_y_ordenadas_entre_si(self):
        self.assertEqual(["2", "10", "Entrada", "Salida"], self._top({"Salida": 1, "10": 1, "Entrada": 1, "2": 1}, 4))

    def test_el_caso_de_perdidas_por_familia_de_los_datos_de_prueba(self):
        # 14 familias con perdidas: 0 y 1 (4), 8 y 10 (2) y diez familias empatadas en 1 que compiten por 6 lugares.
        valores = {"0": 4, "1": 4, "8": 2, "10": 2, **{str(i): 1 for i in (2, 3, 4, 5, 6, 7, 9, 11, 12, 13)}}
        self.assertEqual(["0", "1", "8", "10", "2", "3", "4", "5", "6", "7"], self._top(valores, 10))
        # Por texto salia ["0", "1", "10", "8", "11", "12", "13", "2", "3", "4"]: otro top 10.
        por_texto = [e for e, _ in sorted(valores.items(), key=lambda par: (-par[1], str(par[0])))[:10]]
        self.assertNotEqual(por_texto, self._top(valores, 10))

    def test_una_llave_numerica_de_verdad_tambien_sirve(self):
        self.assertEqual((0, 7, ""), _orden_de_desempate(7))


if __name__ == "__main__":
    unittest.main()
