"""Suplente del jefe y aviso de equipo para RH (decisiones de RH del 2026-11-04).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) con su jefe Beto (80),
Carla (81) de otro jefe y Rocio (82) de RH. Aqui se agregan Dora (83), jefa de
Beto, y Eva (84), compañera de Ana con el mismo jefe.

* Si el jefe directo esta de vacaciones HOY, el primer paso lo puede dar el jefe
  de su jefe (y el propio jefe sigue pudiendo). Si no hay a quien suplir, va a RH.
* RH siempre al final, y ve quien mas del equipo falta esas fechas.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.models import EmployeeLeave, User
from app.models.session import transaction_context
from app.utils.tiempo import ahora_negocio
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, CARLA, RH, _ConEquipo

DORA, EVA = 83, 84


class _ConSuplente(_ConEquipo):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for id_user, nombre, jefe in ((DORA, "Dora", 1), (EVA, "Eva", BETO)):
                db.add(User(id_user=id_user, created_by=1, full_name=nombre, id_permission=2, id_proyect=1,
                            id_status=1, supervisor=jefe, user_type="employee", is_employee=True,
                            base_salary=Decimal("400.00"), username=f"u{id_user}"))
            db.get(User, BETO).supervisor = DORA

    def ausencia(self, id_user, desde, hasta, estado="approved"):
        with transaction_context() as db:
            db.add(EmployeeLeave(id_user=id_user, leave_type="vacation", start_date=desde, end_date=hasta,
                                 leave_status=estado, requested_by=id_user, created_by=1))

    def beto_de_vacaciones_hoy(self):
        hoy = ahora_negocio().date()
        self.ausencia(BETO, hoy - timedelta(days=1), hoy + timedelta(days=2))

    def pendientes(self, quien):
        return self.json(self.client.get("/employee_leave/pending", headers=self.h(quien)))["requests"]

    def solicitud_de_ana(self):
        r = self.pedir()
        self.assertEqual(201, r.status_code)
        return self.json(r)["id_employee_leave"]


class TestSuplente(_ConSuplente):
    def test_con_su_jefe_presente_la_jefa_de_su_jefe_no_aprueba(self):
        ident = self.solicitud_de_ana()
        self.assertEqual([], self.pendientes(DORA))
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(DORA)).status_code)

    def test_con_su_jefe_de_vacaciones_aprueba_la_jefa_de_su_jefe_y_luego_rh(self):
        self.beto_de_vacaciones_hoy()
        ident = self.solicitud_de_ana()
        fila = next(x for x in self.pendientes(DORA) if x["id_employee_leave"] == ident)
        self.assertEqual(("boss", True), (fila["step"], fila["boss_absent"]))
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(CARLA)).status_code)
        r = self.json(self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(DORA), json={"review_note": "Suplo a Beto"}))
        self.assertEqual(("boss_approved", DORA), (r["leave_status"], r["boss_reviewed_by"]))
        r = self.json(self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(RH)))
        self.assertEqual(("approved", RH), (r["leave_status"], r["reviewed_by"]))   # RH siempre al final

    def test_su_jefe_aunque_este_de_vacaciones_tambien_puede(self):
        self.beto_de_vacaciones_hoy()
        ident = self.solicitud_de_ana()
        self.assertEqual("boss_approved", self.json(self.client.post(
            f"/employee_leave/{ident}/approve", headers=self.h(BETO)))["leave_status"])

    def test_sin_a_quien_suplir_va_directo_a_rh(self):
        with transaction_context() as db:
            db.get(User, BETO).supervisor = BETO
        self.beto_de_vacaciones_hoy()
        ident = self.solicitud_de_ana()
        self.assertEqual("hr", next(x for x in self.pendientes(RH) if x["id_employee_leave"] == ident)["step"])


class TestEquipo(_ConSuplente):
    def test_rh_ve_quien_mas_del_equipo_falta_esas_fechas(self):
        from datetime import date
        self.ausencia(EVA, date(2026, 10, 8), date(2026, 10, 12))                 # se cruza con Ana (6 al 9)
        self.ausencia(EVA, date(2026, 10, 20), date(2026, 10, 21))                # no se cruza
        self.ausencia(CARLA, date(2026, 10, 6), date(2026, 10, 9))                # otro equipo
        ident = self.solicitud_de_ana()
        self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(BETO))
        fila = next(x for x in self.pendientes(RH) if x["id_employee_leave"] == ident)
        self.assertEqual(2, fila["team_size"])                                    # Ana y Eva
        self.assertEqual([("Eva", "2026-10-08", "2026-10-12")],
                         [(x["full_name"], x["start_date"], x["end_date"]) for x in fila["team_off"]])
