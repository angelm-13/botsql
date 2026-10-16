"""Reglas de ley de la nomina (payroll_tax_rules.py), con resultados calculados a mano.

Tarifas: Anexo 8 de la RMF 2026. UMA 2026: 117.31 diaria / 3,566.22 mensual.
"""
from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from app.services import payroll_tax_rules as ley
from tests.fixtures.cifras_nomina_2026 import TARIFAS_2026

P_IMSS = {"imss_em_surplus_pct": "0.400", "imss_em_cash_pct": "0.250", "imss_em_pensioners_pct": "0.375",
          "imss_iv_pct": "0.625", "imss_cv_pct": "1.125", "imss_surplus_umas": "3"}


class TestIsr(unittest.TestCase):
    def test_quincena_de_10_mil(self):
        # Tramo 8,651.41-17,448.75: 916.20 + (10,000 - 8,651.41) x 21.36% = 1,204.26
        self.assertEqual(Decimal("1204.26"), ley.isr_por_tarifa(10000, TARIFAS_2026[15]))

    def test_mes_de_20_mil(self):
        # Tramo 17,533.65-35,362.83: 1,856.84 + (20,000 - 17,533.65) x 21.36% = 2,383.65
        self.assertEqual(Decimal("2383.65"), ley.isr_por_tarifa(20000, TARIFAS_2026[30]))

    def test_ultimo_tramo_sin_limite_superior(self):
        # 500,000 al mes: 133,488.54 + (500,000 - 425,642.00) x 35% = 159,513.84
        self.assertEqual(Decimal("159513.84"), ley.isr_por_tarifa(500000, TARIFAS_2026[30]))

    def test_cero_no_paga(self):
        self.assertEqual(Decimal("0.00"), ley.isr_por_tarifa(0, TARIFAS_2026[15]))

    def test_tarifa_diaria_por_dias(self):
        # 5 dias, 2,500 con la tarifa diaria x5: cae en el tramo 481.74-576.76 x5
        # (2,408.70-2,883.80): 44.05 x 5 + (2,500 - 2,408.70) x 17.92% = 236.61
        self.assertEqual(Decimal("236.61"), ley.isr_por_tarifa(2500, TARIFAS_2026[1], Decimal(5)))

    def test_que_tabla_toca_segun_los_dias(self):
        self.assertEqual((7, 1), ley.tabla_para_dias(7))
        self.assertEqual((15, 1), ley.tabla_para_dias(16))
        self.assertEqual((30, 1), ley.tabla_para_dias(31))
        self.assertEqual((1, 5), ley.tabla_para_dias(5))


class TestSubsidio(unittest.TestCase):
    def test_mes_bajo_el_limite(self):
        # 3,566.22 x 15.02% = 535.65
        self.assertEqual(Decimal("535.65"), ley.subsidio_para_el_empleo(10000, 30, "3566.22", "15.02", "11492.66"))

    def test_mes_sobre_el_limite(self):
        self.assertEqual(Decimal("0.00"), ley.subsidio_para_el_empleo(12000, 30, "3566.22", "15.02", "11492.66"))

    def test_quincena_proporcional(self):
        # 535.6462... / 30.4 x 15 = 264.30
        self.assertEqual(Decimal("264.30"), ley.subsidio_para_el_empleo(5000, 15, "3566.22", "15.02", "11492.66"))

    def test_quincena_que_llevada_a_mes_pasa_el_limite(self):
        # 6,000 / 15 x 30.4 = 12,160 > 11,492.66
        self.assertEqual(Decimal("0.00"), ley.subsidio_para_el_empleo(6000, 15, "3566.22", "15.02", "11492.66"))


class TestImss(unittest.TestCase):
    def test_vacaciones_por_antiguedad(self):
        self.assertEqual([12, 14, 16, 18, 20, 22, 22, 24, 26],
                         [ley.dias_de_vacaciones(a) for a in (0, 1, 2, 3, 4, 5, 9, 10, 15)])

    def test_anios_cumplidos(self):
        self.assertEqual(2, ley.anios_cumplidos(date(2024, 3, 1), date(2026, 10, 15)))
        self.assertEqual(1, ley.anios_cumplidos(date(2024, 11, 1), date(2026, 10, 15)))
        self.assertEqual(0, ley.anios_cumplidos(None, date(2026, 10, 15)))

    def test_factor_de_integracion_primer_anio(self):
        # 1 + (15 + 12 x 25%) / 365 = 1.0493
        self.assertEqual(Decimal("1.0493"), ley.factor_de_integracion(15, 12, 25))

    def test_sbc_con_piso_y_tope(self):
        self.assertEqual(Decimal("524.65"), ley.salario_base_de_cotizacion(500, "1.0493", "315.04", "117.31", 25))
        self.assertEqual(Decimal("315.04"), ley.salario_base_de_cotizacion(200, "1.0493", "315.04", "117.31", 25))
        # Tope: 25 UMA = 2,932.75
        self.assertEqual(Decimal("2932.75"), ley.salario_base_de_cotizacion(5000, "1.0493", "315.04", "117.31", 25))

    def test_cuota_obrera(self):
        # SBC 524.65: 524.65 x 2.375% = 12.4604 + (524.65 - 351.93) x 0.40% = 0.6909 -> 13.1513/dia; x 3 = 39.45
        self.assertEqual(Decimal("39.45"), ley.cuota_obrera_imss("524.65", 3, 500, "315.04", "117.31", P_IMSS))

    def test_salario_minimo_no_paga_cuota_obrera(self):
        self.assertEqual(Decimal("0.00"), ley.cuota_obrera_imss("330.57", 15, "315.04", "315.04", "117.31", P_IMSS))


if __name__ == "__main__":
    unittest.main()
