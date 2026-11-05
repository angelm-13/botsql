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


class TestOtrosPagosYDescuentos(_ConBaja):
    """Bonos y descuentos que RH captura, como en el Excel de la contadora (2026-11-05).

    Renuncia + bono de 1,000 que grava + pago de 500 que no + Infonavit 500:
    ISR sobre 17,918.51 + 1,000 = 18,918.51: 1,856.84 + 1,384.86 x 21.36 % = 2,152.65.
    Neto 20,661.43 + 1,500 - 213.60 (ISR de mas) - 500 = 21,447.83.
    """

    def test_se_suman_se_restan_y_solo_grava_el_pago_que_lo_dice(self):
        from app.services.termination_service import agregar_renglon, quitar_renglon
        creada = EmployeeTerminationService.create({"id_user": ANA, "termination_date": "2026-10-15",
                                                     "reason": "resignation"}, user_id=1)
        ident = creada["id_employee_termination"]
        agregar_renglon(ident, {"line_kind": "earning", "description": "Bono de productividad", "amount": 1000})
        agregar_renglon(ident, {"line_kind": "earning", "description": "Pago pendiente", "amount": 500,
                                "taxable": False})
        infonavit = agregar_renglon(ident, {"line_kind": "deduction", "description": "Infonavit", "amount": "500",
                                            "taxable": True})
        self.assertFalse(infonavit["taxable"])   # un descuento nunca grava
        f = calcular(ident)
        otros = [(c["description"], c["amount"]) for c in f["earnings"] + f["deductions"] if c["code"] == "extra"]
        self.assertEqual([("Bono de productividad", 1000.0), ("Pago pendiente", 500.0), ("Infonavit", 500.0)], otros)
        self.assertEqual((2152.65, 21447.83), (self.de(f["deductions"])["isr"], f["net_pay"]))
        self.assertEqual(3, len(f["extra_lines"]))
        # Quitar el descuento lo saca del calculo.
        quitar_renglon(ident, infonavit["id_employee_termination_line"])
        self.assertEqual(21947.83, calcular(ident)["net_pay"])

    def test_validaciones(self):
        from app.services.termination_service import agregar_renglon, quitar_renglon
        ident = EmployeeTerminationService.create({"id_user": ANA, "termination_date": "2026-10-15",
                                                    "reason": "resignation"}, user_id=1)["id_employee_termination"]
        for malo in ({"line_kind": "otro", "description": "x", "amount": 1},
                     {"line_kind": "earning", "description": "  ", "amount": 1},
                     {"line_kind": "earning", "description": "x" * 121, "amount": 1},
                     {"line_kind": "earning", "description": "Bono", "amount": 0},
                     {"line_kind": "earning", "description": "Bono", "amount": "abc"},
                     {"line_kind": "earning", "description": "Bono", "amount": "NaN"}):
            with self.subTest(malo=malo), self.assertRaises(AppError):
                agregar_renglon(ident, malo)
        with self.assertRaises(AppError) as error:
            quitar_renglon(ident, 999999)
        self.assertEqual(404, error.exception.status_code)


class TestRutasDeOtrosPagos(_ConBaja):
    """Se editan con el permiso de actualizar Bajas del Gestor; sin el, 403."""

    def setUp(self):
        super().setUp()
        from app.models import EntityPermission
        from app.models.session import transaction_context
        with transaction_context() as db:
            for permiso, editar in ((971, 4), (972, 0)):
                db.add(EntityPermission(id_permission=permiso, entity_name="employee_termination", scope_create=4,
                                        scope_read=4, scope_update=editar, scope_delete=0, created_by=1))
        self.ident = EmployeeTerminationService.create({"id_user": ANA, "termination_date": "2026-10-15",
                                                         "reason": "resignation"}, user_id=1)["id_employee_termination"]

    def test_con_y_sin_permiso_de_actualizar(self):
        cuerpo = {"line_kind": "deduction", "description": "Fonacot", "amount": 300}
        url = f"/employee_termination/{self.ident}/lines"
        self.assertEqual(403, self.client.post(url, headers=self.h(ANA, 972), json=cuerpo).status_code)
        r = self.client.post(url, headers=self.h(ANA, 971), json=cuerpo)
        self.assertEqual(201, r.status_code)
        linea = self.json(r)["id_employee_termination_line"]
        self.assertEqual(403, self.client.delete(f"{url}/{linea}", headers=self.h(ANA, 972)).status_code)
        self.assertEqual(200, self.client.delete(f"{url}/{linea}", headers=self.h(ANA, 971)).status_code)
