"""El relleno de las marcas de un grafico: `parametros.relleno`, `solido` o `textura`.

Corre en SQLite: solo ejerce la validacion (el guardado de punta a punta por la API necesita PostgreSQL).
"""

from __future__ import annotations

import unittest

from app.services.kpi_dashboard_widget_service import RELLENOS, KpiDashboardWidgetService, validar_relleno
from app.utils.errors import AppError


class ValidarRellenoTest(unittest.TestCase):
    validar = staticmethod(KpiDashboardWidgetService._validar_parametros)

    def test_los_dos_valores_validos(self):
        self.assertEqual(("solido", "textura"), RELLENOS)
        for valor in RELLENOS:
            with self.subTest(valor=valor):
                self.assertEqual(valor, validar_relleno(valor))

    def test_cualquier_otra_cosa_es_400_y_dice_que_se_permite(self):
        for valor in ("Solido", "textura ", "rayas", "", None, 1, True, ["textura"], {"a": 1}):
            with self.subTest(valor=valor), self.assertRaises(AppError) as contexto:
                validar_relleno(valor)
            self.assertEqual("errors.invalid_field", contexto.exception.message_key)
            self.assertEqual(400, contexto.exception.status_code)
            self.assertEqual("relleno", contexto.exception.meta["field"])
            self.assertEqual(["solido", "textura"], contexto.exception.meta["allowed"])

    def test_en_los_parametros_se_conserva_y_el_resto_queda_intacto(self):
        entrada = {"fecha_inicio": "2026-10-01", "relleno": "textura", "titulo": "  Mi grafico  "}
        self.assertEqual({"fecha_inicio": "2026-10-01", "relleno": "textura", "titulo": "Mi grafico"}, self.validar(entrada))

    def test_sin_relleno_no_inventa_uno(self):
        self.assertEqual({"fecha_inicio": "2026-10-01"}, self.validar({"fecha_inicio": "2026-10-01"}))

    def test_un_relleno_malo_rechaza_todos_los_parametros(self):
        for valor in ("rayas", None, 7):
            with self.subTest(valor=valor), self.assertRaises(AppError):
                self.validar({"fecha_inicio": "2026-10-01", "relleno": valor})
