"""Descanso o festivo trabajado y prima dominical (Etapa C; decisiones de RH 2026-11-02).

Mismo equipo que test_horas_extra: Ana (71) gana 500 diarios, trabaja L-V de 9 a
18; sabado 10 y domingo 11 de octubre son su descanso y el lunes 12 se marca como
festivo. Periodo 5 = 1 al 15 de octubre.

Cuentas a mano:
  Prima dominical: 500 x 25 % = 125.00 por domingo; no grava hasta 1 UMA (117.31):
  grava 7.69. Con 35 %: 175.00, grava 57.69.
  Descanso trabajado y aprobado: el doble del dia = 1,000.00; exento la mitad (500),
  bajo el tope de 5 UMA (586.55): grava 500.00.
  Misma semana con 2.5 h extra dobles (312.50) + descanso (1,000): lo doble suma
  1,312.50 y el exento es el tope, 586.55; grava 725.95 en total
  (172.85 de las horas extra y 553.10 del descanso, repartido por lo doble de cada uno).
"""
from __future__ import annotations

from datetime import date, datetime

from app.models import AttendanceRecord, PayrollHoliday, PayrollParameter
from app.models.session import transaction_context
from app.services.overtime_service import del_rango, registrar
from tests.test_services.test_horas_extra import JEFE, _ConHorasExtra
from tests.test_services.test_solicitudes_de_vacaciones import ANA


class _ConDescansos(_ConHorasExtra):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(PayrollHoliday(holiday_date=date(2026, 10, 12), description="Festivo de prueba", created_by=1))

    def descanso(self, dia, **extra):
        return registrar(JEFE, {"id_user": ANA, "work_date": f"2026-10-{dia:02d}", "kind": "rest_day", **extra})


class TestPrimaDominical(_ConDescansos):
    def test_cada_domingo_checado_se_paga_sin_autorizacion(self):
        self.checa(11, (14, 0))
        ana = self.ana()
        self.assertEqual((1, 125.0, 7.69), (ana["sundays_worked"], ana["sunday_premium"], ana["sunday_premium_taxable"]))
        self.assertEqual(0.0, ana["rest_day_pay"])     # el descanso trabajado si necesita autorizacion

    def test_la_empresa_puede_dar_mas_del_25(self):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="sunday_premium_pct", value=35, valid_from=date(2026, 1, 1),
                                    created_by=1))
        self.checa(11, (14, 0))
        self.assertEqual((175.0, 57.69), (self.ana()["sunday_premium"], self.ana()["sunday_premium_taxable"]))


class TestDescansoTrabajado(_ConDescansos):
    def test_aparece_sin_autorizar_y_al_aprobarlo_se_paga_doble(self):
        self.checa(11, (14, 0))
        self.checa(12, (18, 0))
        sin = del_rango(JEFE, "2026-10-01", "2026-10-15")["unauthorized_rest_days"]
        self.assertEqual([("2026-10-11", False), ("2026-10-12", True)], [(d["work_date"], d["holiday"]) for d in sin])
        self.descanso(11, origin="detected")
        datos = del_rango(JEFE, "2026-10-01", "2026-10-15")
        self.assertEqual(["2026-10-12"], [d["work_date"] for d in datos["unauthorized_rest_days"]])
        self.assertEqual(("rest_day", "verified"), (datos["overtime"][0]["kind"], datos["overtime"][0]["status"]))
        ana = self.ana()
        self.assertEqual((1, 1000.0, 500.0), (ana["rest_days_worked"], ana["rest_day_pay"], ana["rest_day_taxable"]))

    def test_autorizado_pero_no_vino_no_se_paga(self):
        self.descanso(10)
        self.assertEqual("not_worked", del_rango(JEFE, "2026-10-01", "2026-10-15")["overtime"][0]["status"])
        self.assertEqual(0.0, self.ana()["rest_day_pay"])

    def test_compensado_no_se_paga(self):
        self.checa(10, (14, 0))
        self.descanso(10, settlement="compensate", notes="Descansa el miercoles 14")
        self.assertEqual(0.0, self.ana()["rest_day_pay"])

    def test_comparte_el_tope_exento_con_las_horas_extra_de_la_semana(self):
        self.checa(6, (20, 30))
        self.autoriza(6, 150)
        self.checa(11, (14, 0))
        self.descanso(11)
        ana = self.ana()
        self.assertEqual((312.50, 172.85), (ana["overtime_pay"], ana["overtime_taxable"]))
        self.assertEqual((1000.0, 553.10), (ana["rest_day_pay"], ana["rest_day_taxable"]))
