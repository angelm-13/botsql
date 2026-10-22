"""Solicitudes de vacaciones y permisos: el empleado pide, su jefe o RH autoriza.

Ana (71): salario 500, horario L-V desde el 1 de octubre, ingreso 2024-03-01 (le
tocan 14 dias); su jefe es Beto (80). Periodo 5 = 1 al 15 de octubre de 2026.
Decisiones de RH (2026-10-22): el empleado pide vacaciones y permisos (no
incapacidad); autoriza su supervisor o RH; lo pedido aparta dias del saldo.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import jwt

from app.models import EmployeeLeave, EntityPermission, Notification, PayrollPeriod, User
from app.models.session import transaction_context
from app.services.employee_leave_service import EmployeeLeaveService
from app.services.payroll_calculation_service import calcular_periodo
from app.utils.auth import SECRET_KEY
from tests.test_services import test_attendance_schedules as horarios
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba

ANA, BETO, CARLA, RH = 71, 80, 81, 82


class _ConEquipo(_ConPeriodoDePrueba):
    def setUp(self):
        super().setUp()
        horarios.TestHorariosEnLaNomina._asignar_horario_lunes_a_viernes(self)
        with transaction_context() as db:
            ana = db.get(User, ANA)
            ana.hire_date, ana.supervisor = date(2024, 3, 1), BETO
            for id_user, nombre, permiso in ((BETO, "Beto", 2), (CARLA, "Carla", 2), (RH, "Rocio RH", 961)):
                db.add(User(id_user=id_user, created_by=1, full_name=nombre, id_permission=permiso, id_proyect=1,
                            id_status=1, supervisor=1, user_type="employee", is_employee=True,
                            base_salary=Decimal("400.00"), username=f"u{id_user}"))
            db.add(EntityPermission(id_permission=961, entity_name="employee_leave", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=4, created_by=1))

    def h(self, id_user):
        permiso = 961 if id_user == RH else 2
        token = jwt.encode({"id_user": id_user, "id_permission": permiso}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def pedir(self, desde="2026-10-06", hasta="2026-10-09", tipo="vacation", quien=ANA):
        return self.client.post("/employee_leave/request", headers=self.h(quien),
                                json={"leave_type": tipo, "start_date": desde, "end_date": hasta, "notes": "viaje"})

    def saldo(self):
        return self.json(self.client.get("/employee_leave/mine", headers=self.h(ANA)))["balance"]


class TestSolicitar(_ConEquipo):
    def test_lo_pedido_queda_pendiente_aparta_saldo_y_no_cuenta_en_la_nomina(self):
        r = self.pedir()
        self.assertEqual(201, r.status_code)
        self.assertEqual("requested", self.json(r)["leave_status"])
        s = self.saldo()
        self.assertEqual((14, 0, 4, 10), (s["entitled"], s["taken"], s["pending"], s["available"]))
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(0, ana["vacation_days"])     # pendiente: todavia no justifica los dias
        self.assertEqual(8, ana["absences"])
        with transaction_context() as db:
            aviso = db.query(Notification).filter_by(id_user_recipient=BETO).one()
            self.assertEqual(("employee_leave", "leave_requested"), (aviso.target_entity, aviso.notification_type))

    def test_no_pide_incapacidad_ni_mas_de_su_saldo(self):
        self.assertEqual(400, self.pedir(tipo="disability").status_code)
        self.assertEqual(201, self.pedir("2026-10-01", "2026-10-09").status_code)   # 7 laborables
        r = self.pedir("2026-10-12", "2026-10-21")                                   # 8 mas: pasa de 14
        self.assertEqual(409, r.status_code)
        self.assertEqual("errors.employee_leave_insufficient_balance", self.json(r)["error_key"])

    def test_mis_ausencias_son_solo_las_propias(self):
        self.pedir()
        self.assertEqual(201, self.pedir("2026-10-13", "2026-10-14", tipo="paid_leave", quien=CARLA).status_code)
        mias = self.json(self.client.get("/employee_leave/mine", headers=self.h(ANA)))["leaves"]
        self.assertEqual({ANA}, {a["id_user"] for a in mias})


class TestRevisar(_ConEquipo):
    def _pendiente(self):
        return self.json(self.pedir())["id_employee_leave"]

    def test_el_jefe_aprueba_y_ya_cuenta(self):
        ident = self._pendiente()
        r = self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(BETO), json={})
        self.assertEqual(200, r.status_code)
        self.assertEqual(("approved", BETO), (self.json(r)["leave_status"], self.json(r)["reviewed_by"]))
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(4, ana["vacation_days"])
        s = self.saldo()
        self.assertEqual((4, 0, 10), (s["taken"], s["pending"], s["available"]))
        with transaction_context() as db:
            self.assertEqual(1, db.query(Notification).filter_by(id_user_recipient=ANA,
                                                                 notification_type="leave_reviewed").count())

    def test_rechazar_libera_el_saldo(self):
        ident = self._pendiente()
        r = self.client.post(f"/employee_leave/{ident}/reject", headers=self.h(BETO), json={"review_note": "cierre de mes"})
        self.assertEqual(("rejected", "cierre de mes"), (self.json(r)["leave_status"], self.json(r)["review_note"]))
        self.assertEqual(14, self.saldo()["available"])

    def test_solo_su_jefe_o_rh_y_nunca_el_propio_empleado(self):
        ident = self._pendiente()
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(CARLA)).status_code)
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(ANA)).status_code)
        self.assertEqual(200, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(RH)).status_code)
        self.assertEqual(409, self.client.post(f"/employee_leave/{ident}/reject", headers=self.h(BETO)).status_code)

    def test_por_autorizar_el_jefe_ve_su_equipo_y_rh_todo(self):
        self._pendiente()
        self.assertEqual(201, self.pedir("2026-10-13", "2026-10-14", tipo="paid_leave", quien=CARLA).status_code)
        del_jefe = self.json(self.client.get("/employee_leave/pending", headers=self.h(BETO)))["requests"]
        de_rh = self.json(self.client.get("/employee_leave/pending", headers=self.h(RH)))["requests"]
        self.assertEqual([ANA], [x["id_user"] for x in del_jefe])
        self.assertEqual("Ana", del_jefe[0]["full_name"])
        self.assertEqual({ANA, CARLA}, {x["id_user"] for x in de_rh})

    def test_al_aprobar_se_vuelve_a_validar(self):
        ident = self._pendiente()
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).period_state = "closed"
        r = self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(BETO))
        self.assertEqual(409, r.status_code)
        self.assertEqual("errors.payroll_period_closed", self.json(r)["error_key"])


class TestCancelarYCapturaDeRh(_ConEquipo):
    def test_cancelar_solo_lo_propio_y_pendiente(self):
        ident = self.json(self.pedir())["id_employee_leave"]
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/cancel", headers=self.h(CARLA)).status_code)
        self.assertEqual("cancelled", self.json(self.client.post(f"/employee_leave/{ident}/cancel", headers=self.h(ANA)))["leave_status"])
        self.assertEqual(409, self.client.post(f"/employee_leave/{ident}/cancel", headers=self.h(ANA)).status_code)
        self.assertEqual(14, self.saldo()["available"])

    def test_lo_que_registra_rh_queda_aprobado_y_el_estado_no_se_escribe_a_mano(self):
        hecha = EmployeeLeaveService.create({"id_user": ANA, "leave_type": "paid_leave", "start_date": "2026-10-06",
                                             "end_date": "2026-10-06", "leave_status": "requested"}, user_id=RH)
        self.assertEqual(("approved", RH), (hecha["leave_status"], hecha["reviewed_by"]))
        EmployeeLeaveService.update(hecha["id_employee_leave"], {"leave_status": "rejected"}, user_id=RH)
        with transaction_context() as db:
            self.assertEqual("approved", db.get(EmployeeLeave, hecha["id_employee_leave"]).leave_status)

    def test_una_solicitud_pendiente_ya_ocupa_las_fechas(self):
        self.pedir()
        from app.utils.errors import AppError
        with self.assertRaises(AppError) as error:
            EmployeeLeaveService.create({"id_user": ANA, "leave_type": "disability", "start_date": "2026-10-08",
                                         "end_date": "2026-10-08"}, user_id=RH)
        self.assertEqual("errors.employee_leave_overlap", error.exception.message_key)
