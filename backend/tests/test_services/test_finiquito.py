"""Finiquito y liquidacion (Etapa E; diseño aprobado 2026-11-02).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) gana 500 diarios,
entro el 1 de marzo de 2024 y trabaja L-V desde el 1 de octubre de 2026; no hay
nomina calculada, asi que los dias pendientes empiezan el 1 de octubre. Baja el
15 de octubre de 2026.

Cuentas a mano (renuncia):
  Dias pendientes: 7 pagados x 500 = 3,500.00; IMSS de 7 dias = 92.33.
  Aguinaldo: 500 x 15 x 288 / 365 = 5,917.81 (del 1 de enero al 15 de octubre).
  Vacaciones: 14 disponibles + 16 x 229 / 365 = 10.04 proporcionales = 24.04 dias
  = 12,020.00; prima solo de las proporcionales: 500 x 10.04 x 25 % = 1,255.00.
  Sin prima de antigüedad (menos de 15 años).
  ISR mensual sobre 3,500 + 12,020 + 2,398.51 gravado del aguinaldo = 17,918.51:
  1,856.84 + (17,918.51 - 17,533.65) x 21.36 % = 1,939.05. Neto 20,661.43.
Despido injustificado con 20 dias (2.6274 años, salario integrado 526.05):
  prima de antigüedad 12 x 500 x 2.6274 = 15,764.38; 3 meses = 47,344.50;
  20 dias por año = 27,642.85. Exento 90 UMA x 3 años (mas de 6 meses cuenta) =
  31,673.70; grava 59,078.03 a la tasa del sueldo mensual de 15,000 (9.35 %):
  ISR de la separacion 5,525.06.
"""
from __future__ import annotations

from app.services.termination_service import EmployeeTerminationService, calcular
from app.utils.errors import AppError
from tests.test_services.test_solicitudes_de_vacaciones import ANA, _ConEquipo


class _ConBaja(_ConEquipo):
    def baja(self, motivo="resignation", **extra):
        creada = EmployeeTerminationService.create({"id_user": ANA, "termination_date": "2026-10-15",
                                                     "reason": motivo, **extra}, user_id=1)
        return calcular(creada["id_employee_termination"])

    @staticmethod
    def de(conceptos):
        return {c["code"]: c["amount"] for c in conceptos}


class TestFiniquito(_ConBaja):
    def test_renuncia(self):
        f = self.baja()
        self.assertEqual({"pending_days": 3500.0, "aguinaldo": 5917.81, "vacations": 12020.0,
                          "vacation_premium": 1255.0}, self.de(f["earnings"]))
        self.assertEqual({"isr": 1939.05, "imss": 92.33}, self.de(f["deductions"]))
        self.assertEqual((14.0, 10.04, 20661.43),
                         (f["vacation_days_available"], f["vacation_days_proportional"], f["net_pay"]))

    def test_despido_injustificado_con_20_dias(self):
        f = self.baja("unjustified_dismissal", pay_twenty_days=True)
        ganado = self.de(f["earnings"])
        self.assertEqual((15764.38, 47344.50, 27642.85), (ganado["seniority_premium"],
                                                          ganado["severance_three_months"],
                                                          ganado["severance_twenty_days"]))
        self.assertEqual((59078.03, 9.35, 5525.06),
                         (f["taxable_severance"], f["severance_tax_rate"], self.de(f["deductions"])["isr_severance"]))

    def test_despido_justificado_paga_prima_de_antiguedad_sin_indemnizacion(self):
        ganado = self.de(self.baja("justified_dismissal", pay_twenty_days=True)["earnings"])
        self.assertEqual(15764.38, ganado["seniority_premium"])
        self.assertNotIn("severance_three_months", ganado)
        self.assertNotIn("severance_twenty_days", ganado)


class TestValidaciones(_ConBaja):
    def test_una_baja_por_persona_y_no_antes_de_su_ingreso(self):
        self.baja()
        with self.assertRaises(AppError) as error:
            self.baja("mutual_agreement")
        self.assertEqual("errors.termination_duplicate", error.exception.message_key)
        with self.assertRaises(AppError) as error:
            EmployeeTerminationService.create({"id_user": 81, "termination_date": "2026-10-15", "reason": "resignation"},
                                              user_id=1)
        self.assertEqual("errors.termination_before_hire_date", error.exception.message_key)   # sin fecha de ingreso

    def test_los_20_dias_solo_en_despido_injustificado(self):
        creada = EmployeeTerminationService.create({"id_user": ANA, "termination_date": "2026-10-15",
                                                     "reason": "resignation", "pay_twenty_days": True}, user_id=1)
        self.assertFalse(creada["pay_twenty_days"])
