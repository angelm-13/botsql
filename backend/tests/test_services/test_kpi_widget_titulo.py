"""El titulo propio de un grafico: `parametros.titulo`, corto, recortado y sin HTML.

Corre en SQLite: solo ejerce la validacion. El guardado de punta a punta (crear, editar, limite) por la API esta en
`tests/test_api/test_api_kpi.py`, que necesita PostgreSQL.
"""

from __future__ import annotations

import unittest

from app.services.kpi_dashboard_widget_service import TITULO_MAX, KpiDashboardWidgetService, validar_titulo
from app.utils.errors import AppError


class ValidarTituloTest(unittest.TestCase):
    def _rechaza(self, valor, clave):
        with self.assertRaises(AppError) as contexto:
            validar_titulo(valor)
        self.assertEqual(clave, contexto.exception.message_key, repr(valor))
        self.assertEqual(400, contexto.exception.status_code)
        self.assertEqual("titulo", contexto.exception.meta["field"])
        return contexto.exception

    def test_un_titulo_normal_se_guarda_tal_cual(self):
        self.assertEqual("Entradas de Manzanillo", validar_titulo("Entradas de Manzanillo"))

    def test_se_recorta_de_espacios_por_los_lados_y_no_por_dentro(self):
        self.assertEqual("Entradas  de Manzanillo", validar_titulo("   Entradas  de Manzanillo  "))

    def test_vacio_o_solo_espacios_o_nulo_es_sin_titulo(self):
        for valor in (None, "", "   ", "  "):
            with self.subTest(valor=valor):
                self.assertIsNone(validar_titulo(valor))

    def test_el_limite_son_80_caracteres_y_80_si_caben(self):
        self.assertEqual(80, TITULO_MAX)
        self.assertEqual("a" * 80, validar_titulo("a" * 80))
        self.assertEqual("á" * 80, validar_titulo("á" * 80), "cuenta caracteres, no bytes")

    def test_81_caracteres_no_caben_y_dicen_cuanto_miden(self):
        error = self._rechaza("a" * 81, "errors.field_too_long")
        self.assertEqual(80, error.meta["max_length"])
        self.assertEqual(81, error.meta["actual_length"])

    def test_los_espacios_de_los_lados_no_cuentan_para_el_limite(self):
        self.assertEqual("a" * 80, validar_titulo("  " + "a" * 80 + "  "))

    def test_html_se_rechaza(self):
        for valor in ("<b>Entradas</b>", "Entradas <script>alert(1)</script>", "</div>", "x <!-- nota -->", "<?xml version", "<IMG src=x>", "a<b"):
            with self.subTest(valor=valor):
                self._rechaza(valor, "errors.invalid_field")

    def test_un_menor_que_de_texto_no_es_html(self):
        for valor in ("Menos de <12 h", "a < b", "5 < 6 > 4", "Entradas (<8 h)", "x<"):
            with self.subTest(valor=valor):
                self.assertEqual(valor, validar_titulo(valor))

    def test_un_titulo_de_una_sola_linea(self):
        for valor in ("uno\ndos", "uno\r\ndos", "col\tuna", "nulo\x00", "borrar\x7f"):
            with self.subTest(valor=valor):
                self._rechaza(valor, "errors.invalid_field")

    def test_solo_acepta_texto(self):
        for valor in (7, 7.5, True, ["a"], {"a": 1}):
            with self.subTest(valor=valor):
                self._rechaza(valor, "errors.invalid_field")


class ValidarParametrosTest(unittest.TestCase):
    validar = staticmethod(KpiDashboardWidgetService._validar_parametros)

    def test_regresa_una_copia_con_el_titulo_recortado_y_el_resto_intacto(self):
        entrada = {"fecha_inicio": "2026-10-01", "id_teams": [4], "titulo": "  Mi grafico  "}

        salida = self.validar(entrada)

        self.assertEqual({"fecha_inicio": "2026-10-01", "id_teams": [4], "titulo": "Mi grafico"}, salida)
        self.assertEqual("  Mi grafico  ", entrada["titulo"], "no muta lo que recibe")

    def test_un_titulo_vacio_no_deja_la_llave(self):
        self.assertEqual({"id_teams": [4]}, self.validar({"id_teams": [4], "titulo": "   "}))
        self.assertEqual({}, self.validar({"titulo": None}))

    def test_sin_titulo_no_inventa_uno(self):
        self.assertEqual({"fecha_inicio": "2026-10-01"}, self.validar({"fecha_inicio": "2026-10-01"}))

    def test_un_titulo_malo_rechaza_todo_el_parametros(self):
        with self.assertRaises(AppError):
            self.validar({"fecha_inicio": "2026-10-01", "titulo": "x" * 81})

    def test_el_orden_de_la_tabla_se_sigue_validando(self):
        with self.assertRaises(AppError):
            self.validar({"orden_tabla": {"campo": "nada", "direccion": "asc"}, "titulo": "ok"})

    def test_parametros_que_no_son_un_diccionario_siguen_siendo_400(self):
        for valor in ("x", 7, ["titulo"]):
            with self.subTest(valor=valor), self.assertRaises(AppError):
                self.validar(valor)
