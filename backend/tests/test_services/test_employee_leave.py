"""Vacaciones, permisos e incapacidades (employee_leave), con cuentas a mano.

Ana: salario diario 500, horario L-V desde el 1 de octubre, checadas los dias 1,
2 y 5. Periodo 5 = 1 al 15 de octubre de 2026 (15 dias, 11 laborales L-V).
Sin ausencias: 8 faltas (6, 7, 8, 9, 12, 13, 14 y 15) y 7 dias pagados.

Decisiones de RH (2026-10-21): no hay vacaciones antes del primer año, los dias
no usados no se acumulan, la incapacidad no paga ningun dia del rango y no se
registra ni edita una ausencia dentro de un periodo cerrado.
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, time

import jwt

from app.models import EmployeeLeave, EntityPermission, Field, NmFieldPermission, PayrollPeriod, User
from app.models.session import transaction_context
from app.services import attendance_rules as reglas
from app.services.employee_leave_service import EmployeeLeaveService, saldo_de_vacaciones
from app.services.payroll_calculation_service import calcular_periodo
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.test_services import test_attendance_schedules as horarios
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba

NUEVE, SEIS = time(9, 0), time(18, 0)


class TestReglasConAusencia(unittest.TestCase):
    def test_vacaciones_no_son_falta_y_se_pagan(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [], (NUEVE, SEIS), False, 10, True, "vacation")
        self.assertFalse(dia.falta)
        self.assertTrue(dia.pagado)
        self.assertTrue(dia.cuenta_como_ausencia)

    def test_incapacidad_no_paga_ni_el_descanso(self):
        domingo = reglas.clasificar_dia(date(2026, 10, 11), [], None, False, 10, True, "disability")
        self.assertFalse(domingo.pagado)
        self.assertTrue(domingo.cuenta_como_ausencia)   # cuenta dias naturales

    def test_permiso_sin_goce_no_paga_el_laborable_pero_si_el_descanso(self):
        laborable = reglas.clasificar_dia(date(2026, 10, 9), [], (NUEVE, SEIS), False, 10, True, "unpaid_leave")
        domingo = reglas.clasificar_dia(date(2026, 10, 11), [], None, False, 10, True, "unpaid_leave")
        self.assertFalse(laborable.falta)
        self.assertFalse(laborable.pagado)
        self.assertTrue(domingo.pagado)
        self.assertFalse(domingo.cuenta_como_ausencia)

    def test_checar_estando_de_vacaciones_se_avisa_y_no_es_retardo(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [time(9, 40)], (NUEVE, SEIS), False, 10, True, "vacation")
        self.assertTrue(dia.checo_en_ausencia)
        self.assertFalse(dia.retardo)


class _ConAusencias(_ConPeriodoDePrueba):
    """El periodo de las pruebas de nomina con el horario L-V de las de horarios.

    Hereda de _ConPeriodoDePrueba y no de la clase de pruebas de horarios: si no,
    esas pruebas se volverian a correr aqui con un horario ya asignado.
    """

    def setUp(self):
        super().setUp()
        horarios.TestHorariosEnLaNomina._asignar_horario_lunes_a_viernes(self)
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2024, 3, 1)   # 2 años cumplidos: le tocan 14 dias

    def _ausencia(self, tipo, desde, hasta, id_user=71):
        return EmployeeLeaveService.create({"id_user": id_user, "leave_type": tipo,
                                            "start_date": desde, "end_date": hasta}, user_id=1)

    def _error(self, tipo, desde, hasta, id_user=71):
        with self.assertRaises(AppError) as error:
            self._ausencia(tipo, desde, hasta, id_user)
        return error.exception


class TestAusenciasEnLaNomina(_ConAusencias):
    def test_vacaciones_quitan_faltas_y_se_pagan(self):
        self._ausencia("vacation", "2026-10-06", "2026-10-09")   # mar a vie: 4 laborables
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(4, ana["vacation_days"])
        self.assertEqual(4, ana["absences"])        # 12, 13, 14 y 15
        self.assertEqual(11, ana["days_worked"])    # 15 - 4 faltas
        self.assertEqual(5500.0, ana["salary"])

    def test_incapacidad_no_paga_ningun_dia_del_rango(self):
        self._ausencia("disability", "2026-10-09", "2026-10-12")   # vie a lun, con sabado y domingo
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(4, ana["disability_days"])
        self.assertEqual(6, ana["absences"])        # 6, 7, 8, 13, 14 y 15
        self.assertEqual(5, ana["days_worked"])     # 15 - 6 faltas - 4 de incapacidad
        self.assertEqual(2500.0, ana["salary"])

    def test_permiso_sin_goce_solo_quita_los_laborables(self):
        self._ausencia("unpaid_leave", "2026-10-09", "2026-10-12")
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(2, ana["unpaid_leave_days"])   # viernes 9 y lunes 12
        self.assertEqual(7, ana["days_worked"])         # 15 - 6 faltas - 2 sin goce
        self.assertEqual(3500.0, ana["salary"])

    def test_permiso_con_goce_se_paga(self):
        self._ausencia("paid_leave", "2026-10-06", "2026-10-08")
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(3, ana["paid_leave_days"])
        self.assertEqual(5, ana["absences"])
        self.assertEqual(10, ana["days_worked"])

    def test_el_recibo_y_el_reporte_muestran_las_ausencias(self):
        self._ausencia("vacation", "2026-10-06", "2026-10-09")
        calcular_periodo(5, 1)
        from app.services.payroll_calculation_service import datos_del_recibo
        from app.services.attendance_record_service import incidencias
        self.assertEqual(4, datos_del_recibo(5, 71)["vacation_days"])
        ana = next(e for e in incidencias(date(2026, 10, 1), date(2026, 10, 15)) if e["id_user"] == 71)
        self.assertEqual(4, ana["vacation_days"])
        self.assertEqual(3, ana["attended"])
        self.assertEqual("vacation", next(d for d in ana["days"] if d["date"] == "2026-10-06")["leave"])


class TestSaldoDeVacaciones(_ConAusencias):
    def _saldo(self, al_dia=date(2026, 10, 20)):
        with transaction_context() as db:
            return saldo_de_vacaciones(db, db.get(User, 71), al_dia)

    def test_el_saldo_segun_antiguedad_y_lo_tomado(self):
        self._ausencia("vacation", "2026-10-09", "2026-10-12")   # vie a lun: el fin de semana no gasta saldo
        saldo = self._saldo()
        self.assertEqual((2, 14, 2, 12), (saldo["service_years"], saldo["entitled"], saldo["taken"], saldo["available"]))
        self.assertEqual(("2026-03-01", "2027-02-28"), (saldo["year_start"], saldo["year_end"]))

    def test_no_se_pasa_del_saldo(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2025, 3, 1)   # 1 año: le tocan 12
        # Del 1 al 19 de octubre hay 13 dias laborables.
        error = self._error("vacation", "2026-10-01", "2026-10-19")
        self.assertEqual("errors.employee_leave_insufficient_balance", error.message_key)
        self.assertEqual((12, 13), (error.meta["available"], error.meta["requested"]))

    def test_no_hay_vacaciones_antes_del_primer_anio(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2026, 1, 1)
        self.assertEqual("errors.employee_leave_first_year",
                         self._error("vacation", "2026-10-06", "2026-10-07").message_key)

    def test_las_vacaciones_no_cruzan_el_aniversario(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2024, 10, 10)
        error = self._error("vacation", "2026-10-06", "2026-10-12")
        self.assertEqual("errors.employee_leave_crosses_anniversary", error.message_key)
        self.assertEqual("2026-10-10", error.meta["anniversary"])

    def test_vacaciones_sin_fecha_de_ingreso_o_sin_horario(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = None
        self.assertEqual("errors.employee_leave_no_hire_date",
                         self._error("vacation", "2026-10-06", "2026-10-07").message_key)
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2024, 3, 1)
        # Antes del 1 de octubre no tiene horario asignado.
        self.assertEqual("errors.employee_leave_needs_schedule",
                         self._error("vacation", "2026-09-28", "2026-10-02").message_key)


class TestValidacionesDeAusencias(_ConAusencias):
    def test_las_ausencias_no_se_enciman(self):
        self._ausencia("paid_leave", "2026-10-06", "2026-10-08")
        self.assertEqual("errors.employee_leave_overlap",
                         self._error("disability", "2026-10-08", "2026-10-09").message_key)

    def test_solo_empleados_y_tipos_validos(self):
        self.assertEqual("errors.invalid_field", self._error("paid_leave", "2026-10-06", "2026-10-06", id_user=73).message_key)
        self.assertEqual("leave_type", self._error("vacaciones", "2026-10-06", "2026-10-06").meta["field"])
        self.assertEqual("end_date", self._error("paid_leave", "2026-10-08", "2026-10-06").meta["field"])

    def test_nada_se_registra_ni_borra_dentro_de_un_periodo_cerrado(self):
        ausencia = self._ausencia("paid_leave", "2026-10-06", "2026-10-06")
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).period_state = "closed"
        self.assertEqual("errors.payroll_period_closed",
                         self._error("disability", "2026-10-13", "2026-10-14").message_key)
        for accion in (lambda: EmployeeLeaveService.delete(ausencia["id_employee_leave"], user_id=1),
                       lambda: EmployeeLeaveService.update(ausencia["id_employee_leave"],
                                                           {"end_date": "2026-10-07"}, user_id=1)):
            with self.assertRaises(AppError) as error:
                accion()
            self.assertEqual("errors.payroll_period_closed", error.exception.message_key)
        # Fuera del periodo cerrado si se puede.
        self._ausencia("disability", "2026-10-20", "2026-10-21")

    def test_las_rutas_exigen_permiso(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=951, entity_name="employee_leave", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=4, created_by=1))
            # Permiso de CAMPO: la ruta descarta del cuerpo lo que el rol no puede escribir.
            for nombre in ("id_user", "leave_type", "start_date", "end_date"):
                campo = Field(table_name="employee_leave", field_name=nombre, created_by=1)
                db.add(campo)
                db.flush()
                db.add(NmFieldPermission(id_field=campo.id_field, id_permission=951, control_type="7", created_by=1))

        def headers(id_permission, **extra):
            token = jwt.encode({"id_user": 41, "id_permission": id_permission, **extra}, SECRET_KEY, algorithm="HS256")
            return {"Authorization": f"Bearer {token}"}

        cuerpo = {"id_user": 71, "leave_type": "paid_leave", "start_date": "2026-10-06", "end_date": "2026-10-06"}
        self.assertEqual(403, self.client.post("/employee_leave/", json=cuerpo, headers=headers(999)).status_code)
        self.assertEqual(403, self.client.get("/employee_leave/balances", headers=headers(999)).status_code)
        self.assertEqual(201, self.client.post("/employee_leave/", json=cuerpo, headers=headers(951)).status_code)
        saldos = self.json(self.client.get("/employee_leave/balances", headers=headers(951)))["employees"]
        self.assertIn(71, [s["id_user"] for s in saldos])
        with transaction_context() as db:
            self.assertEqual(1, db.query(EmployeeLeave).count())
