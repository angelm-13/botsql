"""La orientacion de las barras: `parametros.orientacion`, `auto`, `horizontal` o `vertical`.

Corre en SQLite: solo ejerce la validacion (el guardado de punta a punta por la API necesita PostgreSQL).
"""

from __future__ import annotations

import unittest

from app.services.kpi_dashboard_widget_service import ORIENTACIONES, KpiDashboardWidgetService, validar_orientacion
from app.utils.errors import AppError


class ValidarOrientacionTest(unittest.TestCase):
    validar = staticmethod(KpiDashboardWidgetService._validar_parametros)

    def test_los_tres_valores_validos(self):
        self.assertEqual(("auto", "horizontal", "vertical"), ORIENTACIONES)
        for valor in ORIENTACIONES:
            with self.subTest(valor=valor):
                self.assertEqual(valor, validar_orientacion(valor))

    def test_cualquier_otra_cosa_es_400_y_dice_que_se_permite(self):
        for valor in ("Horizontal", "horizontal ", "diagonal", "", None, 1, True, ["vertical"], {"a": 1}):
            with self.subTest(valor=valor), self.assertRaises(AppError) as contexto:
                validar_orientacion(valor)
            self.assertEqual("errors.invalid_field", contexto.exception.message_key)
            self.assertEqual(400, contexto.exception.status_code)
            self.assertEqual("orientacion", contexto.exception.meta["field"])
            self.assertEqual(["auto", "horizontal", "vertical"], contexto.exception.meta["allowed"])

    def test_en_los_parametros_se_conserva_junto_al_relleno_y_el_resto_queda_intacto(self):
        entrada = {"fecha_inicio": "2026-10-01", "orientacion": "horizontal", "relleno": "textura", "titulo": "  Mi grafico  "}
        self.assertEqual(
            {"fecha_inicio": "2026-10-01", "orientacion": "horizontal", "relleno": "textura", "titulo": "Mi grafico"}, self.validar(entrada),
        )

    def test_sin_orientacion_no_inventa_una(self):
        self.assertEqual({"fecha_inicio": "2026-10-01"}, self.validar({"fecha_inicio": "2026-10-01"}))

    def test_una_orientacion_mala_rechaza_todos_los_parametros(self):
        for valor in ("diagonal", None, 7):
            with self.subTest(valor=valor), self.assertRaises(AppError):
                self.validar({"fecha_inicio": "2026-10-01", "orientacion": valor})
