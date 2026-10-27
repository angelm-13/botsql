"""Horarios, retardos, faltas y dias pagados (services/attendance_rules.py).

Decisiones de RH (2026-10-20): con horario se pagan los dias del periodo menos
las faltas (descansos y festivos pagados); sin horario, solo los dias con
checada. Los retardos son solo un reporte. Tolerancia por omision: 10 minutos.
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, time

import jwt

from app.models import (AttendanceRecord, EmployeeSchedule, EntityPermission, PayrollHoliday, WorkSchedule,
                        WorkScheduleDay)
from app.models.session import transaction_context
from app.services import attendance_rules as reglas
from app.services.payroll_calculation_service import calcular_periodo
from app.utils.auth import SECRET_KEY
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba, dar_todos_los_campos

NUEVE, SEIS = time(9, 0), time(18, 0)


class TestReglasDelDia(unittest.TestCase):
    def test_llegar_despues_de_la_tolerancia_es_retardo(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [datetime(2026, 10, 6, 9, 15), datetime(2026, 10, 6, 18, 0)],
                                    (NUEVE, SEIS), False, 10, True)
        self.assertTrue(dia.retardo)
        self.assertEqual(15, dia.minutos_retardo)
        self.assertFalse(dia.falta)

    def test_dentro_de_la_tolerancia_no_es_retardo(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [time(9, 10), time(18, 0)], (NUEVE, SEIS), False, 10, True)
        self.assertFalse(dia.retardo)

    def test_dia_laboral_sin_checadas_es_falta_y_no_se_paga(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [], (NUEVE, SEIS), False, 10, True)
        self.assertTrue(dia.falta)
        self.assertFalse(dia.pagado)

    def test_una_sola_checada_es_incompleta(self):
        dia = reglas.clasificar_dia(date(2026, 10, 6), [time(9, 0)], (NUEVE, SEIS), False, 10, True)
        self.assertTrue(dia.incompleta)
        self.assertFalse(dia.falta)

    def test_festivo_sin_checadas_no_es_falta_y_se_paga(self):
        dia = reglas.clasificar_dia(date(2026, 11, 16), [], (NUEVE, SEIS), True, 10, True)
        self.assertFalse(dia.falta)
        self.assertTrue(dia.pagado)

    def test_descanso_se_paga_y_checar_en_descanso_se_reporta(self):
        descanso = reglas.clasificar_dia(date(2026, 10, 11), [], None, False, 10, True)
        self.assertTrue(descanso.pagado)
        trabajado = reglas.clasificar_dia(date(2026, 10, 11), [time(10, 0)], None, False, 10, True)
        self.assertTrue(trabajado.trabajo_en_descanso)

    def test_sin_horario_solo_se_paga_con_checada(self):
        self.assertFalse(reglas.clasificar_dia(date(2026, 10, 6), [], None, False, 0, False).pagado)
        self.assertTrue(reglas.clasificar_dia(date(2026, 10, 6), [time(8, 0)], None, False, 0, False).pagado)


class TestHorariosEnLaNomina(_ConPeriodoDePrueba):
    """Ana: salario diario 500, checadas los dias 1, 2 y 5 de octubre (8:00 y 17:00)."""

    def _asignar_horario_lunes_a_viernes(self, desde=date(2026, 10, 1)):
        with transaction_context() as db:
            horario = WorkSchedule(schedule_name="Oficina L-V", tolerance_minutes=10, created_by=1)
            db.add(horario)
            db.flush()
            for dia in range(5):
                db.add(WorkScheduleDay(id_work_schedule=horario.id_work_schedule, weekday=dia,
                                       start_time=NUEVE, end_time=SEIS, created_by=1))
            db.add(EmployeeSchedule(id_user=71, id_work_schedule=horario.id_work_schedule,
                                    valid_from=desde, created_by=1))

    def test_con_horario_se_pagan_los_dias_del_periodo_menos_faltas(self):
        self._asignar_horario_lunes_a_viernes()
        ana = calcular_periodo(5, 1)["employees"][0]
        # 1 al 15 de octubre de 2026: 11 dias laborales (L-V), checo 3 -> 8 faltas.
        # Se pagan los 15 dias menos 8 faltas = 7.
        self.assertEqual(8, ana["absences"])
        self.assertEqual(7, ana["days_worked"])
        self.assertEqual(3500.0, ana["salary"])

    def test_un_festivo_no_cuenta_como_falta(self):
        self._asignar_horario_lunes_a_viernes()
        with transaction_context() as db:
            db.add(PayrollHoliday(holiday_date=date(2026, 10, 12), description="Festivo de prueba", created_by=1))
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(7, ana["absences"])
        self.assertEqual(8, ana["days_worked"])

    def test_un_retardo_no_cambia_la_nomina(self):
        self._asignar_horario_lunes_a_viernes()
        with transaction_context() as db:
            db.add(AttendanceRecord(id_user=71, employee_no="71", check_time=datetime(2026, 10, 6, 9, 25),
                                    source="kronos", source_ref="t:tarde", created_by=1))
        ana = calcular_periodo(5, 1)["employees"][0]
        # El 6 ya no es falta (checo, aunque tarde): 7 faltas, 8 dias pagados.
        self.assertEqual(7, ana["absences"])
        self.assertEqual(8, ana["days_worked"])

    def test_sin_horario_queda_como_antes(self):
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(0, ana["absences"])
        self.assertEqual(3, ana["days_worked"])


class TestReporteDeIncidencias(_ConPeriodoDePrueba):
    def setUp(self):
        super().setUp()
        TestHorariosEnLaNomina._asignar_horario_lunes_a_viernes(self)
        with transaction_context() as db:
            db.add(AttendanceRecord(id_user=71, employee_no="71", check_time=datetime(2026, 10, 6, 9, 25),
                                    source="kronos", source_ref="t:tarde", created_by=1))
            db.add(EntityPermission(id_permission=951, entity_name="attendance_record", scope_create=0,
                                    scope_read=4, scope_update=0, scope_delete=0, created_by=1))

    def _headers(self, id_permission):
        token = jwt.encode({"id_user": 41, "id_permission": id_permission}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def test_el_reporte_cuenta_retardos_faltas_e_incompletas(self):
        respuesta = self.client.get("/kronos/attendance/incidences?startDate=2026-10-05&endDate=2026-10-09",
                                    headers=self._headers(951))
        self.assertEqual(200, respuesta.status_code)
        ana = next(e for e in self.json(respuesta)["employees"] if e["id_user"] == 71)
        # Semana del 5 al 9: el 5 checo completo, el 6 llego 9:25 (una sola checada),
        # 7, 8 y 9 no checo.
        self.assertEqual(5, ana["workdays"])
        self.assertEqual(3, ana["absences"])
        self.assertEqual(1, ana["late"])
        self.assertEqual(25, ana["late_minutes"])
        self.assertEqual(1, ana["incomplete"])
        self.assertEqual(5, len(ana["days"]))

    def test_el_reporte_exige_permiso(self):
        respuesta = self.client.get("/kronos/attendance/incidences?startDate=2026-10-05&endDate=2026-10-09",
                                    headers=self._headers(999))
        self.assertEqual(403, respuesta.status_code)


class TestValidacionesDeHorarios(_ConPeriodoDePrueba):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for entidad in ("work_schedule", "work_schedule_day", "employee_schedule", "payroll_holiday"):
                db.add(EntityPermission(id_permission=952, entity_name=entidad, scope_create=4,
                                        scope_read=4, scope_update=4, scope_delete=4, created_by=1))
            dar_todos_los_campos(db, 952, ("work_schedule", "work_schedule_day", "employee_schedule",
                                           "payroll_holiday"))
        token = jwt.encode({"id_user": 1, "id_permission": 952}, SECRET_KEY, algorithm="HS256")
        self.h = {"Authorization": f"Bearer {token}"}
        self.horario = self.json(self.client.post("/work_schedule/", json={"schedule_name": "L-V"}, headers=self.h))

    def test_un_horario_nuevo_trae_10_minutos_de_tolerancia(self):
        self.assertEqual(10, self.horario["tolerance_minutes"])

    def test_un_dia_con_horas_y_sin_duplicar(self):
        cuerpo = {"id_work_schedule": self.horario["id_work_schedule"], "weekday": 0,
                  "start_time": "09:00", "end_time": "18:00"}
        primero = self.client.post("/work_schedule_day/", json=cuerpo, headers=self.h)
        self.assertEqual(201, primero.status_code)
        self.assertEqual("09:00", self.json(primero)["start_time"])
        self.assertEqual(409, self.client.post("/work_schedule_day/", json=cuerpo, headers=self.h).status_code)
        al_reves = {**cuerpo, "weekday": 1, "start_time": "18:00", "end_time": "09:00"}
        self.assertEqual(400, self.client.post("/work_schedule_day/", json=al_reves, headers=self.h).status_code)

    def test_las_asignaciones_de_un_empleado_no_se_enciman(self):
        base = {"id_user": 71, "id_work_schedule": self.horario["id_work_schedule"], "valid_from": "2026-10-01"}
        self.assertEqual(201, self.client.post("/employee_schedule/", json=base, headers=self.h).status_code)
        otra = {**base, "valid_from": "2026-11-01"}
        self.assertEqual(409, self.client.post("/employee_schedule/", json=otra, headers=self.h).status_code)

    def test_solo_se_asigna_horario_a_empleados(self):
        cuerpo = {"id_user": 73, "id_work_schedule": self.horario["id_work_schedule"], "valid_from": "2026-10-01"}
        self.assertEqual(400, self.client.post("/employee_schedule/", json=cuerpo, headers=self.h).status_code)

    def test_un_festivo_por_fecha(self):
        cuerpo = {"holiday_date": "2026-12-12", "description": "Prueba"}
        self.assertEqual(201, self.client.post("/payroll_holiday/", json=cuerpo, headers=self.h).status_code)
        self.assertEqual(409, self.client.post("/payroll_holiday/", json=cuerpo, headers=self.h).status_code)
