"""Avisos cuando alguien no checa (revision contable, punto 3).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) trabaja L-V de 9 a 18
desde el 1 de octubre de 2026 y su jefe es Beto (80). El martes 6 de octubre no
checa nada. Por omision: aviso a Ana a los 15 minutos de su entrada, a Beto a los
30, y a Ana 30 minutos despues de su salida si entro y no salio.
"""
from __future__ import annotations

from datetime import date, datetime

from app.models import AttendanceRecord, Notification, PayrollParameter
from app.models.session import transaction_context
from app.services.avisos_de_checada import avisar_checadas_faltantes
from app.services.employee_leave_service import EmployeeLeaveService
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, _ConEquipo


def _a_las(hora, minuto=0, dia=6):
    return datetime(2026, 10, dia, hora, minuto)


class TestAvisosDeChecada(_ConEquipo):
    def avisos(self):
        with transaction_context() as db:
            return sorted((n.id_user_recipient, n.notification_type, n.target_id, n.created_by)
                          for n in db.query(Notification).filter(Notification.notification_type.like("attendance_%")))

    def test_entrada_al_empleado_a_los_15_y_al_jefe_a_los_30_una_sola_vez(self):
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(9, 14)))
        self.assertEqual(1, avisar_checadas_faltantes(_a_las(9, 15)))
        self.assertEqual(1, avisar_checadas_faltantes(_a_las(9, 30)))    # solo el del jefe: el de Ana ya salio
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(9, 35)))
        self.assertEqual([(ANA, "attendance_missing_check_in", ANA, ANA),
                          (BETO, "attendance_missing_check_in_team", ANA, BETO)], self.avisos())

    def test_salida_si_entro_y_no_salio(self):
        with transaction_context() as db:
            db.add(AttendanceRecord(id_user=ANA, employee_no="71", check_time=_a_las(9), source="kronos",
                                    source_ref="t:solo-entrada", created_by=1))
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(18, 29)))
        self.assertEqual(1, avisar_checadas_faltantes(_a_las(18, 30)))
        self.assertEqual([(ANA, "attendance_missing_check_out", ANA, ANA)], self.avisos())

    def test_no_se_avisa_en_descanso_ni_en_ausencia(self):
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(10, dia=10)))     # sabado
        EmployeeLeaveService.create({"id_user": ANA, "leave_type": "paid_leave", "start_date": "2026-10-06",
                                     "end_date": "2026-10-06"}, user_id=1)
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(10)))

    def test_cada_empresa_cambia_los_minutos_y_0_es_sin_aviso(self):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="attendance_warning_entry_minutes", value=0,
                                    valid_from=date(2026, 1, 1), created_by=1))
            db.add(PayrollParameter(parameter_key="attendance_warning_supervisor_minutes", value=60,
                                    valid_from=date(2026, 1, 1), created_by=1))
        self.assertEqual(0, avisar_checadas_faltantes(_a_las(9, 59)))
        self.assertEqual(1, avisar_checadas_faltantes(_a_las(10)))
        self.assertEqual([(BETO, "attendance_missing_check_in_team", ANA, BETO)], self.avisos())
