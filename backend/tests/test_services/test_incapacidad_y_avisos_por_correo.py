"""Opciones de incapacidad por empresa y avisos por correo (2026-11-05).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71), diario 500, con
horario L-V; el periodo 5 es del 1 al 15 de octubre de 2026.
"""
from __future__ import annotations

from datetime import date
from unittest import mock

from app.models import EmployeeLeave, Notification, PayrollParameter, User
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, _ConEquipo


class TestPagoDeIncapacidad(_ConEquipo):
    def incapacidad(self, desde, hasta, tipo="general_illness"):
        with transaction_context() as db:
            db.add(EmployeeLeave(id_user=ANA, leave_type="disability", disability_type=tipo, start_date=desde,
                                 end_date=hasta, leave_status="approved", requested_by=ANA, created_by=1))

    def opcion(self, clave, valor):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key=clave, value=valor, valid_from=date(2026, 1, 1), created_by=1))

    def ana(self):
        return next(e for e in calcular_periodo(5, 1)["employees"] if e["id_user"] == ANA)

    def test_por_omision_la_empresa_no_paga_nada(self):
        self.incapacidad(date(2026, 10, 6), date(2026, 10, 10))
        self.assertEqual(0.0, self.ana()["disability_pay"])

    def test_dias_de_espera_y_complemento(self):
        self.incapacidad(date(2026, 10, 6), date(2026, 10, 10))      # 5 dias naturales
        self.opcion("disability_pay_waiting_days", 1)
        self.assertEqual(1500.0, self.ana()["disability_pay"])      # dias 1 a 3 al 100 %: 3 x 500
        self.opcion("disability_complement_pct", 40)
        ana = self.ana()
        self.assertEqual(1900.0, ana["disability_pay"])             # + dias 4 y 5 al 40 %: 2 x 200
        self.assertGreaterEqual(ana["taxable_income"], 1900.0)       # grava como sueldo

    def test_cuenta_desde_que_empezo_aunque_sea_del_periodo_anterior(self):
        self.incapacidad(date(2026, 9, 29), date(2026, 10, 3))        # en el periodo: dias 3, 4 y 5
        self.opcion("disability_pay_waiting_days", 1)
        self.opcion("disability_complement_pct", 50)
        self.assertEqual(1000.0, self.ana()["disability_pay"])      # 500 + 250 + 250

    def test_riesgo_de_trabajo_lo_paga_el_imss(self):
        self.incapacidad(date(2026, 10, 6), date(2026, 10, 10), tipo="work_risk")
        self.opcion("disability_pay_waiting_days", 1)
        self.assertEqual(0.0, self.ana()["disability_pay"])


class TestAvisosPorCorreo(_ConEquipo):
    def aviso(self, para=ANA):
        with transaction_context() as db:
            n = Notification(id_user_recipient=para, notification_type="custom", title="Solicitud aprobada",
                             message="Del 06/10 al 10/10.", created_by=1)
            db.add(n)
            db.flush()
            return n.id_notification

    def correo(self, para, valor, recibir=True):
        with transaction_context() as db:
            u = db.get(User, para)
            u.email, u.receive_email_notifications = valor, recibir

    def mandar(self, id_aviso):
        from app.jobs.tasks_notifications import send_notification_email
        with mock.patch("app.jobs.tasks_notifications.send_email", return_value=True) as envio:
            resultado = send_notification_email.run(id_aviso)
        return resultado, envio

    def test_con_correo_se_manda_una_sola_vez(self):
        self.correo(ANA, "ana@example.com")
        ident = self.aviso()
        resultado, envio = self.mandar(ident)
        self.assertEqual("jobs.notifications.email_sent", resultado["message_key"])
        para, asunto, cuerpo = envio.call_args.args
        self.assertEqual(("ana@example.com", "TYAKXA · Solicitud aprobada"), (para, asunto))
        self.assertIn("Del 06/10 al 10/10.", cuerpo)
        with transaction_context() as db:
            self.assertIsNotNone(db.get(Notification, ident).email_sent_at)
        resultado, envio = self.mandar(ident)
        self.assertEqual("jobs.notifications.already_sent", resultado["message_key"])
        envio.assert_not_called()

    def test_sin_correo_o_apagado_solo_queda_en_la_campana(self):
        self.correo(ANA, None)
        resultado, envio = self.mandar(self.aviso())
        self.assertEqual("jobs.notifications.no_email", resultado["message_key"])
        self.correo(BETO, "beto@example.com", recibir=False)
        resultado, envio = self.mandar(self.aviso(BETO))
        self.assertEqual("jobs.notifications.no_email", resultado["message_key"])
        envio.assert_not_called()

    def test_en_pruebas_y_sin_cuenta_no_se_encola(self):
        from app.services.notification_service import create_notification
        with mock.patch("app.jobs.tasks_notifications.send_notification_email.delay") as encolar:
            create_notification(id_user_recipient=ANA, notification_type="custom", title="x", created_by=1)
        encolar.assert_not_called()
