"""Horario, grupo de pago y forma de salario desde el perfil del usuario (2026-11-02).

RH elige el valor nuevo y desde cuando (services/vigencias.py): la asignacion
vigente se cierra el dia anterior y la nueva sigue hasta donde llegaba aquella.

Pepe (74) es obrero (grupo catorcenal) desde el 1 de enero de 2026, sin fin.
"""
from __future__ import annotations

from datetime import date

import jwt

from app.models import EmployeePayrollGroup, EmployeeSalary, EmployeeSchedule, EntityPermission, WorkSchedule
from app.models.session import transaction_context
from app.services.payroll_group_service import EmployeePayrollGroupService
from app.services.salary_service import EmployeeSalaryService
from app.services.vigencias import cambiar_desde
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.test_services.test_grupos_de_pago import _ConGrupos
from tests.test_services.test_payroll_calculation_service import dar_todos_los_campos

PEPE = 74


class _ConPerfil(_ConGrupos):
    @staticmethod
    def vigencias(modelo, campo):
        with transaction_context() as db:
            filas = db.query(modelo).filter(modelo.id_user == PEPE, modelo.deletion_date.is_(None)) \
                .order_by(modelo.valid_from).all()
            return [(getattr(f, campo), f.valid_from.isoformat(), f.valid_to.isoformat() if f.valid_to else None)
                    for f in filas]

    def grupo(self, grupo, desde):
        return cambiar_desde(EmployeePayrollGroupService,
                             {"id_user": PEPE, "id_payroll_group": grupo, "valid_from": desde}, user_id=1)

    def sueldo(self, monto, desde, forma="daily", frecuencia=None):
        return cambiar_desde(EmployeeSalaryService, {"id_user": PEPE, "salary_type": forma, "amount": monto,
                                                     "fixed_frequency": frecuencia, "valid_from": desde}, user_id=1)


class TestCambioConVigencia(_ConPerfil):
    def test_cierra_la_vigente_el_dia_anterior_y_abre_la_nueva(self):
        self.grupo(self.general, "2026-11-16")
        self.assertEqual([(self.obreros, "2026-01-01", "2026-11-15"), (self.general, "2026-11-16", None)],
                         self.vigencias(EmployeePayrollGroup, "id_payroll_group"))

    def test_el_mismo_dia_corrige_en_su_lugar(self):
        self.grupo(self.general, "2026-11-16")
        self.grupo(self.obreros, "2026-11-16")
        self.assertEqual([(self.obreros, "2026-01-01", "2026-11-15"), (self.obreros, "2026-11-16", None)],
                         self.vigencias(EmployeePayrollGroup, "id_payroll_group"))

    def test_la_nueva_llega_hasta_donde_llegaba_la_anterior(self):
        with transaction_context() as db:
            fila = db.query(EmployeePayrollGroup).filter(EmployeePayrollGroup.id_user == PEPE).one()
            fila.valid_to = date(2026, 12, 31)
            db.add(EmployeePayrollGroup(id_user=PEPE, id_payroll_group=self.general, valid_from=date(2027, 1, 1),
                                        created_by=1))
        self.grupo(self.general, "2026-11-16")
        self.assertEqual([(self.obreros, "2026-01-01", "2026-11-15"), (self.general, "2026-11-16", "2026-12-31"),
                          (self.general, "2027-01-01", None)],
                         self.vigencias(EmployeePayrollGroup, "id_payroll_group"))

    def test_sin_asignacion_previa_solo_crea_y_un_aumento_cierra_el_sueldo_anterior(self):
        self.sueldo("400.00", "2026-11-01")
        self.sueldo("15000.00", "2026-12-01", forma="fixed", frecuencia="monthly")
        self.assertEqual([("daily", "2026-11-01", "2026-11-30"), ("fixed", "2026-12-01", None)],
                         self.vigencias(EmployeeSalary, "salary_type"))

    def test_una_asignacion_futura_encimada_se_rechaza_sin_tocar_nada(self):
        with transaction_context() as db:
            db.add(EmployeeSalary(id_user=PEPE, salary_type="daily", amount=450, valid_from=date(2027, 1, 1),
                                  created_by=1))
        with self.assertRaises(AppError) as error:
            self.sueldo("400.00", "2026-11-01")
        self.assertEqual("errors.employee_salary_overlap", error.exception.message_key)
        self.assertEqual([("daily", "2027-01-01", None)], self.vigencias(EmployeeSalary, "salary_type"))


class TestRutaDelCambio(_ConPerfil):
    """El cambio crea una fila y acorta otra: el Gestor tiene que dar alta Y actualizacion."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            oficina = WorkSchedule(schedule_name="Oficina", created_by=1)
            db.add(oficina)
            db.flush()
            self.oficina = oficina.id_work_schedule
            db.add(EmployeeSchedule(id_user=PEPE, id_work_schedule=self.oficina, valid_from=date(2026, 1, 1),
                                    created_by=1))
            db.add(EntityPermission(id_permission=971, entity_name="employee_schedule", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=0, created_by=1))
            dar_todos_los_campos(db, 971, ["employee_schedule"])
            db.add(EntityPermission(id_permission=972, entity_name="employee_schedule", scope_create=4,
                                    scope_read=4, scope_update=0, scope_delete=0, created_by=1))
            turno = WorkSchedule(schedule_name="Turno tarde", created_by=1)
            db.add(turno)
            db.flush()
            self.turno = turno.id_work_schedule

    def cambiar(self, permiso):
        token = jwt.encode({"id_user": 1, "id_permission": permiso}, SECRET_KEY, algorithm="HS256")
        return self.client.post("/employee_schedule/change", headers={"Authorization": f"Bearer {token}"},
                                json={"id_user": PEPE, "id_work_schedule": self.turno, "valid_from": "2026-11-16"})

    def test_con_alta_y_actualizacion_cambia_el_horario(self):
        r = self.cambiar(971)
        self.assertEqual(201, r.status_code)
        self.assertEqual([(self.oficina, "2026-01-01", "2026-11-15"), (self.turno, "2026-11-16", None)],
                         self.vigencias(EmployeeSchedule, "id_work_schedule"))

    def test_sin_actualizacion_no_puede(self):
        r = self.cambiar(972)
        self.assertEqual(403, r.status_code)
        self.assertEqual([(self.oficina, "2026-01-01", None)], self.vigencias(EmployeeSchedule, "id_work_schedule"))
